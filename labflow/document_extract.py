"""Extract retained text with source hashes and page-local evidence locations.

This module does not interpret documents, execute their contents, or adapt PDF
citations to the existing intake analysis contract.
"""

from dataclasses import asdict, dataclass
import hashlib
from io import BytesIO
import logging
from pathlib import PurePath
import re
import threading


TEXT_SUFFIXES = {'.txt', '.md', '.csv', '.tsv', '.json'}


@dataclass(frozen=True)
class ExtractionLimits:
    max_input_bytes: int = 16 * 1024 * 1024
    max_pages: int = 200
    max_output_chars: int = 1_000_000
    max_page_content_bytes: int = 8 * 1024 * 1024

    def __post_init__(self):
        for name, value in asdict(self).items():
            if type(value) is not int or value <= 0:
                raise ValueError(name + ' must be a positive integer')


def _sha256(payload):
    return hashlib.sha256(payload).hexdigest()


def _line_spans(text):
    spans, start = [], 0
    for number, part in enumerate(text.splitlines(keepends=True), 1):
        content = part.splitlines()[0]
        spans.append({'line_number': number, 'start': start, 'end': start + len(content)})
        start += len(part)
    return spans


def _page(number, text, status):
    return {'page_number': number, 'status': status, 'text': text,
            'text_sha256': _sha256(text.encode('utf-8')), 'line_spans': _line_spans(text)}


def _new_result(filename, source_hash, size_bytes, limits):
    suffix = PurePath(filename).suffix.lower()
    format_name = 'pdf' if suffix == '.pdf' else 'text' if suffix in TEXT_SUFFIXES else 'unsupported'
    return {
        'schema_version': 1,
        'source': {'filename': filename, 'sha256': source_hash,
                   'size_bytes': size_bytes, 'format': format_name},
        'parser': {'name': 'utf-8-sig' if format_name == 'text' else format_name, 'version': '1' if format_name == 'text' else None},
        'status': 'unsupported_format', 'complete': False,
        'total_pages': None, 'processed_pages': 0, 'pages': [], 'issues': [],
        'limits': asdict(limits),
    }


def _issue(result, code, page_number=None):
    issue = {'code': code}
    if page_number is not None:
        issue['page_number'] = page_number
    result['issues'].append(issue)


def _status(result, status):
    result['status'] = status
    result['complete'] = status in {'ok', 'empty'}
    result['processed_pages'] = len(result['pages'])
    return result


class _ContentLimit(Exception):
    pass


class _EncryptedPdf(Exception):
    pass


class _PdfWarnings(logging.Handler):
    """Keep warning locations, never document-bearing log message strings."""

    def __init__(self):
        super().__init__(logging.WARNING)
        self.thread_id = threading.get_ident()
        self.page_number = None
        self.pages = set()

    def emit(self, record):
        if record.thread == self.thread_id:
            self.pages.add(self.page_number)


def _warnings_observable():
    loggers = [logging.getLogger('pypdf')]
    loggers.extend(logger for name, logger in logging.root.manager.loggerDict.copy().items()
                   if name.startswith('pypdf.') and isinstance(logger, logging.Logger))
    return all(not logger.disabled and not logger.filters and logger.isEnabledFor(logging.WARNING)
               and (logger.name == 'pypdf' or logger.propagate) for logger in loggers)


def _inspect_content(content, resources, reader, limit):
    """Check decoded page/form streams; never decode embedded image pixels."""
    from pypdf.generic import (ArrayObject, ByteStringObject, ContentStream,
                               DictionaryObject, NameObject, TextStringObject)

    remaining = limit
    active_forms = set()
    missing_form_resources = False
    text_types = (TextStringObject, ByteStringObject)
    paint_operators = {b'S', b's', b'f', b'F', b'f*', b'B', b'B*', b'b', b'b*',
                       b'sh', b'Tj', b'TJ', b"'", b'"'}

    def visit(stream, scope, depth):
        nonlocal remaining, missing_form_resources
        if stream is None:
            return False, False
        remaining -= len(stream.get_data())
        if remaining < 0 or depth > 32:
            raise _ContentLimit()
        has_image = has_marks = False
        for operands, operator in stream.operations:
            if operator == b'INLINE IMAGE':
                has_image = has_marks = True
            elif operator == b'Tf':
                # pypdf otherwise silently ignores missing font/size operands.
                if (len(operands) != 2 or not isinstance(operands[0], NameObject)
                        or not isinstance(operands[1], (int, float))
                        or operands[0] not in scope.get('/Font', {})):
                    raise ValueError('Invalid PDF text font operation')
                if not isinstance(scope['/Font'][operands[0]], DictionaryObject):
                    raise ValueError('Invalid PDF font resource')
            elif operator == b'Tj':
                if len(operands) != 1 or not isinstance(operands[0], text_types):
                    raise ValueError('Invalid PDF text string operand')
                has_marks = True
            elif operator == b'TJ':
                if (len(operands) != 1 or not isinstance(operands[0], ArrayObject)
                        or any(not isinstance(item, text_types + (int, float)) for item in operands[0])):
                    raise ValueError('Invalid PDF text array operand')
                has_marks = True
            elif operator == b'Do':
                has_marks = True
                resource = scope['/XObject'][operands[0]].get_object()
                if resource.get('/Subtype') == '/Image':
                    has_image = True
                elif resource.get('/Subtype') == '/Form':
                    # pypdf does not inherit our parent scope while extracting
                    # such a Form. Retain available text but report the gap.
                    if '/Resources' not in resource:
                        missing_form_resources = True
                        continue
                    identity = id(resource)
                    if identity in active_forms:
                        raise _ContentLimit()
                    active_forms.add(identity)
                    try:
                        nested_image, _ = visit(ContentStream(resource, reader),
                                                resource['/Resources'], depth + 1)
                        has_image = has_image or nested_image
                    finally:
                        active_forms.remove(identity)
            elif operator in paint_operators:
                has_marks = True
        return has_image, has_marks

    has_image, has_marks = visit(content, resources, 0)
    return has_image, has_marks, missing_form_resources


def _pdf_status(result):
    statuses = {page['status'] for page in result['pages']}
    has_text = any(page['text'].strip() for page in result['pages'])
    codes = {issue['code'] for issue in result['issues']}
    if codes & {'page_limit', 'output_limit', 'content_limit', 'page_error', 'parser_warning',
                'parser_warnings_unobservable', 'form_resources_missing'}:
        if has_text:
            return 'partial'
        return 'limit_exceeded' if codes & {'page_limit', 'output_limit', 'content_limit'} else 'parser_error'
    if statuses & {'image_only', 'no_text'}:
        if has_text:
            return 'partial'
        return 'no_text' if 'no_text' in statuses else 'image_only'
    return 'ok' if has_text else 'empty'


def _read_pdf(payload, result, limits, pypdf, warnings):
    class RejectEncryptedReader(pypdf.PdfReader):
        # Pinned pypdf normally tries the empty password in its constructor.
        # Stop at this hook before any password verification or decryption.
        def _handle_encryption(self, password):
            raise _EncryptedPdf()

    try:
        reader = RejectEncryptedReader(BytesIO(payload), strict=True)
    except _EncryptedPdf:
        _issue(result, 'encrypted_pdf')
        return _status(result, 'encrypted')
    except Exception:
        _issue(result, 'malformed_pdf')
        return _status(result, 'malformed_pdf')
    try:
        if reader.is_encrypted:
            _issue(result, 'encrypted_pdf')
            return _status(result, 'encrypted')
        try:
            result['total_pages'] = len(reader.pages)
        except Exception:
            _issue(result, 'invalid_page_tree')
            return _status(result, 'malformed_pdf')
        count = min(result['total_pages'], limits.max_pages)
        if count < result['total_pages']:
            _issue(result, 'page_limit')
        remaining = limits.max_output_chars
        for index in range(count):
            number = index + 1
            if not remaining:
                _issue(result, 'output_limit', number)
                break
            warnings.page_number = number
            try:
                page = reader.pages[index]
                has_image, has_marks, missing_form_resources = _inspect_content(
                    page.get_contents(), page.get('/Resources', {}), reader, limits.max_page_content_bytes)
                if missing_form_resources:
                    _issue(result, 'form_resources_missing', number)
                text = page.extract_text()
                if not isinstance(text, str):
                    raise ValueError('Unexpected PDF text result')
                truncated = len(text) > remaining
                status = ('truncated' if truncated else 'ok' if text.strip() else
                          'image_only' if has_image else 'no_text' if has_marks else 'empty')
                result['pages'].append(_page(number, text[:remaining], status))
                remaining -= min(len(text), remaining)
                if status in {'image_only', 'no_text'}:
                    _issue(result, 'ocr_required' if status == 'image_only' else 'no_text', number)
                if truncated:
                    _issue(result, 'output_limit', number)
                    break
            except _ContentLimit:
                result['pages'].append(_page(number, '', 'limit_exceeded'))
                _issue(result, 'content_limit', number)
            except Exception:
                result['pages'].append(_page(number, '', 'error'))
                _issue(result, 'page_error', number)
        return _status(result, _pdf_status(result))
    finally:
        reader.close()


def _extract_pdf(payload, result, limits):
    try:
        import pypdf
    except ImportError:
        result['parser']['name'] = 'pypdf'
        _issue(result, 'parser_unavailable')
        return _status(result, 'parser_unavailable')
    result['parser'] = {'name': 'pypdf', 'version': pypdf.__version__}
    if not payload:
        result['total_pages'] = 0
        _issue(result, 'empty_input')
        return _status(result, 'empty')
    warnings = _PdfWarnings()
    logger = logging.getLogger('pypdf')
    observable = _warnings_observable()
    logger.addHandler(warnings)
    try:
        _read_pdf(payload, result, limits, pypdf, warnings)
    finally:
        logger.removeHandler(warnings)
        warnings.close()
    for number in sorted(warnings.pages, key=lambda page: page or 0):
        _issue(result, 'parser_warning', number)
    observable = observable and _warnings_observable()
    if not observable:
        _issue(result, 'parser_warnings_unobservable')
    if (warnings.pages or not observable) and result['status'] in {'ok', 'empty'}:
        _status(result, _pdf_status(result))
    return result


def extract_document(payload: bytes, filename: str, *, limits: ExtractionLimits | None = None) -> dict:
    """Return a deterministic JSON-compatible extraction of provided bytes.

    The caller retains the original bytes. Text hashes cover the UTF-8 encoding
    of retained text; they are distinct from the original file's hash.
    """
    if not isinstance(payload, bytes):
        raise TypeError('payload must be bytes')
    if not isinstance(filename, str) or not filename.strip():
        raise ValueError('filename must be a non-empty string')
    if limits is None:
        limits = ExtractionLimits()
    if not isinstance(limits, ExtractionLimits):
        raise TypeError('limits must be ExtractionLimits')
    result = _new_result(filename, _sha256(payload), len(payload), limits)
    if len(payload) > limits.max_input_bytes:
        _issue(result, 'input_limit')
        return _status(result, 'limit_exceeded')
    if result['source']['format'] == 'unsupported':
        _issue(result, 'unsupported_format')
        return result
    if result['source']['format'] == 'pdf':
        return _extract_pdf(payload, result, limits)
    result['total_pages'] = 1
    try:
        text = payload.decode('utf-8-sig', errors='strict')
    except UnicodeError:
        _issue(result, 'invalid_utf8')
        return _status(result, 'invalid_encoding')
    if '\x00' in text:
        _issue(result, 'nul_in_text')
        return _status(result, 'invalid_text')
    truncated = len(text) > limits.max_output_chars
    retained = text[:limits.max_output_chars]
    page_status = 'truncated' if truncated else 'ok' if text.strip() else 'empty'
    result['pages'].append(_page(1, retained, page_status))
    if truncated:
        _issue(result, 'output_limit', 1)
    return _status(result, 'partial' if truncated else 'ok' if text.strip() else 'empty')


def page_citation(result: dict, page_number: int, line_start: int, line_end: int) -> dict:
    """Build a page-local quote; this is NOT an intake_analysis citation.

    The check proves internal text/hash consistency, not source authenticity.
    The integration layer must retain and verify the original file separately.
    """
    if any(type(value) is not int for value in (page_number, line_start, line_end)):
        raise ValueError('Citation page and lines must be integers')
    if result.get('schema_version') != 1 or result.get('status') not in {'ok', 'partial'}:
        raise ValueError('Citation requires a supported text extraction')
    pages = [p for p in result.get('pages', []) if p['page_number'] == page_number]
    if len(pages) != 1 or pages[0]['status'] not in {'ok', 'truncated'}:
        raise ValueError('Citation requires a retained text page')
    page = pages[0]
    text = page['text']
    if _sha256(text.encode('utf-8')) != page['text_sha256']:
        raise ValueError('Citation text hash mismatch')
    if page['line_spans'] != _line_spans(text):
        raise ValueError('Citation line positions mismatch')
    source = result['source']
    if not re.fullmatch(r'[0-9a-f]{64}', source['sha256']):
        raise ValueError('Invalid source hash')
    lines = text.splitlines()
    if not 1 <= line_start <= line_end <= len(lines):
        raise ValueError('Invalid citation line range')
    return {'schema_version': 1, 'filename': source['filename'],
            'source_sha256': source['sha256'], 'parser': dict(result['parser']),
            'page_number': page_number, 'text_sha256': page['text_sha256'],
            'line_start': line_start, 'line_end': line_end,
            'quote': '\n'.join(lines[line_start - 1:line_end]),
            'extraction_status': result['status'], 'page_status': page['status']}


def _extract_file(path, limits):
    """Hash the full stream but retain input bytes only within the size limit."""
    digest, size, payload = hashlib.sha256(), 0, bytearray()
    with path.open('rb') as stream:
        while chunk := stream.read(64 * 1024):
            digest.update(chunk)
            size += len(chunk)
            if size <= limits.max_input_bytes:
                payload.extend(chunk)
            else:
                payload.clear()
    if size > limits.max_input_bytes:
        result = _new_result(path.name, digest.hexdigest(), size, limits)
        _issue(result, 'input_limit')
        return _status(result, 'limit_exceeded')
    return extract_document(bytes(payload), path.name, limits=limits)


def main(argv=None):
    """Independent file-to-JSON command; does not write to the intake store."""
    import argparse
    import json
    from pathlib import Path
    import sys

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', type=Path, help='One local PDF or UTF-8 text file')
    for name, default in asdict(ExtractionLimits()).items():
        parser.add_argument('--' + name.replace('_', '-'), type=int, default=default)
    args = parser.parse_args(argv)
    try:
        limits = ExtractionLimits(**{name: getattr(args, name) for name in asdict(ExtractionLimits())})
    except ValueError as error:
        parser.error(str(error))
    try:
        result = _extract_file(args.file, limits)
    except OSError as error:
        print('Cannot read input: ' + type(error).__name__, file=sys.stderr)
        return 1
    output = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + '\n'
    sys.stdout.buffer.write(output.encode('utf-8'))
    return 0 if result['status'] in {'ok', 'empty'} else 2


if __name__ == '__main__':
    raise SystemExit(main())

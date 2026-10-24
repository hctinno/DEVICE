"""One synthetic loopback contract exchange; never a worker or model adapter."""
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import http.client
import json
import math
import multiprocessing
import os
from pathlib import Path
import re
import socket
import stat
import time

from .intake_model_boundary import build_analysis_prompt, decode_analysis_response
from . import intake_model_boundary
from .store import canonical


_LIMIT = 2 * 1024 * 1024
_ENDPOINT = re.compile(r'http://127\.0\.0\.1:([0-9]{1,5})/analysis\Z')
_SHA = re.compile(r'[a-f0-9]{64}\Z')
_CODES = {'ok', 'http_status', 'transport_error', 'response_too_large', 'response_incomplete'}
_FILENAMES = ('prompt.json', 'response-prefix.bin', 'transport.json', 'result.json', 'manifest.json')


def _plain(value):
    path = Path(value).absolute()
    if str(path).startswith(('\\\\', '//')):
        raise ValueError('probe_output_invalid')
    for current in (path, *path.parents):
        try:
            info = current.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 1024:
            raise ValueError('probe_output_invalid')
    return path.resolve()


def _output(value):
    try:
        if type(value) not in (str, type(Path())):
            raise ValueError()
        path = Path(value)
        if (path.drive and not path.is_absolute()) or any(
                part in {'.', '..'} or part.endswith((' ', '.')) or ':' in part
                for part in path.parts if part != path.anchor):
            raise ValueError()
        path = _plain(path)
        if path.exists() or not path.parent.is_dir():
            raise ValueError()
        if os.name == 'nt' and any(len(str(path/name).encode('utf-16-le'))//2 >= 260 for name in _FILENAMES):
            raise ValueError()
        path.mkdir(mode=0o700, exist_ok=False)
        return _plain(path)
    except (OSError, ValueError, TypeError):
        raise ValueError('probe_output_invalid') from None


def _new_stream(path):
    _plain(path.parent)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_BINARY', 0)
    return os.fdopen(os.open(path, flags, 0o600), 'wb')


def _write_new(path, data):
    with _new_stream(path) as stream:
        if stream.write(data) != len(data):
            raise OSError()
        stream.flush()
        os.fsync(stream.fileno())


class _HeaderReader:
    def __init__(self, stream):
        self.stream, self.complete = stream, False

    def readline(self, *args):
        line = self.stream.readline(*args)
        line.decode('utf-8', errors='strict')
        if line.startswith(b'HTTP/'):
            self.complete = False
        elif line in (b'\r\n', b'\n'):
            self.complete = True
        return line

    def __getattr__(self, name):
        return getattr(self.stream, name)


class _StrictResponse(http.client.HTTPResponse):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reader = _HeaderReader(self.fp)
        self.fp = self.reader

    def begin(self):
        super().begin()
        if not self.reader.complete:
            raise http.client.HTTPException()


def _length(response):
    lengths = response.headers.get_all('Content-Length', [])
    transfers = response.headers.get_all('Transfer-Encoding', [])
    if len(lengths) > 1 or len(transfers) > 1 or lengths and transfers:
        raise http.client.HTTPException()
    if transfers and transfers[0].strip().lower() != 'chunked':
        raise http.client.HTTPException()
    if lengths:
        value = lengths[0].strip()
        if not re.fullmatch(r'[0-9]{1,20}', value):
            raise http.client.HTTPException()
        return int(value)
    return None


def _exchange(port, body, prefix_path, timeout):
    meta = {'code': 'transport_error', 'bytes': 0, 'sha256': None, 'complete': False, 'http_status': None}
    digest, connection = hashlib.sha256(), None
    with _new_stream(Path(prefix_path)) as stream:
        def retain(chunk):
            chunk = chunk[:_LIMIT+1-meta['bytes']]
            if stream.write(chunk) != len(chunk):
                raise OSError()
            stream.flush()
            os.fsync(stream.fileno())
            digest.update(chunk)
            meta['bytes'] += len(chunk)
        try:
            wire = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            wire.settimeout(timeout)
            connection = http.client.HTTPConnection('127.0.0.1', port, timeout=timeout)
            connection.response_class = _StrictResponse
            connection.auto_open = False
            connection.sock = wire
            wire.connect(('127.0.0.1', port))
            connection.request('POST', '/analysis', body=body, headers={
                'Content-Type': 'application/json', 'Content-Length': str(len(body))})
            response = connection.getresponse()
            meta['http_status'] = response.status
            expected = _length(response)
            while True:
                try:
                    chunk = response.read1(min(64*1024, _LIMIT+1-meta['bytes']))
                except http.client.IncompleteRead as error:
                    retain(error.partial)
                    meta['code'] = 'response_incomplete'
                    break
                if not chunk:
                    meta['complete'] = expected is None or meta['bytes'] == expected
                    meta['code'] = ('ok' if response.status == 200 else 'http_status') if meta['complete'] else 'response_incomplete'
                    break
                retain(chunk)
                if meta['bytes'] > _LIMIT:
                    meta['code'] = 'response_too_large'
                    break
        except BaseException:
            meta['code'] = 'transport_error'
            meta['complete'] = False
        finally:
            if connection is not None:
                try:
                    connection.close()
                except BaseException:
                    pass
        meta['sha256'] = digest.hexdigest()
    return meta


def _probe_child(port, body, prefix_path, metadata_path, timeout):
    with open(os.devnull, 'w', encoding='utf-8') as sink, redirect_stdout(sink), redirect_stderr(sink):
        os.dup2(sink.fileno(), 1)
        os.dup2(sink.fileno(), 2)
        try:
            meta = _exchange(port, body, prefix_path, timeout)
        except BaseException:
            meta = {'code': 'transport_error', 'bytes': 0, 'sha256': None, 'complete': False, 'http_status': None}
        try:
            _write_new(Path(metadata_path), canonical(meta).encode('utf-8'))
        except BaseException:
            pass


def _stop(process):
    try:
        if process.is_alive():
            process.terminate()
            process.join(.25)
        if process.is_alive():
            process.kill()
            process.join(.25)
        return not process.is_alive()
    except BaseException:
        return False


def _read(path, limit):
    path = _plain(path)
    if not path.exists():
        return None
    if not path.is_file():
        raise ValueError()
    with path.open('rb') as stream:
        data = stream.read(limit+1)
    if len(data) > limit:
        raise ValueError()
    return data


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError()
        result[key] = value
    return result


def _metadata(data, prefix):
    if data is None:
        raise ValueError()
    value = json.loads(data.decode('utf-8'), object_pairs_hook=_pairs,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    if (type(value) is not dict or set(value) != {'code', 'bytes', 'sha256', 'complete', 'http_status'}
            or type(value['code']) is not str or value['code'] not in _CODES
            or type(value['bytes']) is not int or not 0 <= value['bytes'] <= _LIMIT+1
            or type(value['complete']) is not bool
            or value['http_status'] is not None and type(value['http_status']) is not int):
        raise ValueError()
    if prefix is None:
        if value['bytes'] != 0 or value['sha256'] is not None or value['complete']:
            raise ValueError()
    elif (type(value['sha256']) is not str or not _SHA.fullmatch(value['sha256'])
          or value['bytes'] != len(prefix) or hashlib.sha256(prefix).hexdigest() != value['sha256']):
        raise ValueError()
    if value['complete'] and (len(prefix) > _LIMIT or value['code'] not in {'ok', 'http_status'}):
        raise ValueError()
    return value


def _preflight(context, endpoint, producer_name, timeout):
    try:
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 60:
            raise ValueError()
    except (ValueError, OverflowError):
        raise ValueError('probe_configuration_invalid') from None
    if type(endpoint) is not str or not (match := _ENDPOINT.fullmatch(endpoint)) or not 1 <= int(match[1]) <= 65535:
        raise ValueError('probe_endpoint_invalid')
    try:
        prompt = build_analysis_prompt(context, producer_name=producer_name)
        snapshot = json.loads(prompt['messages'][1]['content'])
        if snapshot['synthetic'] is not True:
            raise ValueError()
        body = canonical(prompt).encode('utf-8')
    except Exception:
        raise ValueError('probe_context_invalid') from None
    return int(match[1]), prompt, snapshot, body


def _publish(folder, result, prompt, body, prefix, transport):
    try:
        # Evidence must still match the bytes sent and consumed by the parent.
        if (_read(folder/'prompt.json', len(body)) != body
                or _read(folder/'response-prefix.bin', _LIMIT+1) != prefix
                or _read(folder/'transport.json', 16*1024) != transport):
            raise ValueError()
        result_bytes = canonical(result).encode('utf-8')
        files = []
        for name, data in (('prompt.json', body), ('response-prefix.bin', prefix),
                           ('transport.json', transport), ('result.json', result_bytes)):
            if data is not None:
                files.append({'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
        implementation = {path.name: hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
                          for path in (Path(__file__), Path(intake_model_boundary.__file__))}
        manifest = {'schema_version': 1, 'kind': 'private_loopback_contract_evidence',
            'synthetic': True, 'model_execution_verified': False, 'state_mutations': 0,
            'context_sha256': prompt['binding']['context_sha256'], 'request_sha256': result['request_sha256'],
            'response_complete': result['response_complete'], 'response_sha256': result['response_sha256'],
            'source_hashes': sorted({document['sha256'] for document in json.loads(prompt['messages'][1]['content'])['documents']}),
            'implementation_sha256': implementation,
            'files': files, 'scope': 'loopback contract exchange; no model or hardware attestation'}
        _write_new(folder/'result.json', result_bytes)
        _write_new(folder/'manifest.json', canonical(manifest).encode('utf-8'))
    except Exception:
        raise ValueError('probe_evidence_error') from None
    return result


def probe_loopback_analysis(context, *, endpoint, producer_name, output_dir, timeout_seconds=5):
    """Run one child exchange and decode only its verified complete response.

    Configuration/path failures raise sanitized ValueError before transmission.
    Evidence-write failures retain partial files and raise probe_evidence_error.
    """
    port, prompt, snapshot, body = _preflight(context, endpoint, producer_name, timeout_seconds)
    folder = _output(output_dir)
    try:
        _write_new(folder/'prompt.json', body)
    except Exception:
        raise ValueError('probe_evidence_error') from None
    result = {'schema_version': 1, 'kind': 'loopback_analysis_contract_probe',
        'execution_mode': 'loopback_contract_probe', 'synthetic': True, 'hardware_verified': False,
        'model_execution_verified': False, 'state_mutations': 0, 'status': 'rejected',
        'reason_code': 'child_failed', 'request_sha256': hashlib.sha256(body).hexdigest(),
        'response_sha256': None, 'response_complete': False, 'analysis': None}
    process, stopped, timed_out, exit_code = None, True, False, None
    deadline = time.monotonic()+timeout_seconds
    try:
        process = multiprocessing.get_context('spawn').Process(target=_probe_child, args=(
            port, body, str(folder/'response-prefix.bin'), str(folder/'transport.json'), timeout_seconds), daemon=True)
        process.start()
        while process.is_alive():
            remaining = deadline-time.monotonic()
            if remaining <= 0:
                timed_out = True
                break
            process.join(remaining)
        timed_out = timed_out or time.monotonic() >= deadline
        exit_code = process.exitcode
    except BaseException:
        result['reason_code'] = 'child_start_failed'
    finally:
        if process is not None:
            stopped = _stop(process)
            if stopped:
                try:
                    exit_code = process.exitcode
                    process.close()
                except BaseException:
                    pass
    if not stopped:
        result['reason_code'] = 'termination_failed'
        # Do not read files while an unconfirmed child may still be writing.
        try:
            _write_new(folder/'result.json', canonical(result).encode('utf-8'))
        except Exception:
            raise ValueError('probe_evidence_error') from None
        return result
    prefix, meta_bytes = None, None
    try:
        prefix = _read(folder/'response-prefix.bin', _LIMIT+1)
        meta_bytes = _read(folder/'transport.json', 16*1024)
        if timed_out:
            result.update(status='timeout', reason_code='deadline_exceeded')
        elif exit_code == 0:
            meta = _metadata(meta_bytes, prefix)
            result['reason_code'] = meta['code']
            if meta['complete']:
                result.update(response_complete=True, response_sha256=meta['sha256'])
            if meta['code'] == 'ok':
                if not meta['complete'] or meta['http_status'] != 200:
                    raise ValueError()
                try:
                    analysis = decode_analysis_response(prefix, snapshot, producer_name=prompt['expected_producer']['name'])
                    result.update(status='validated_response', reason_code='validated', analysis=analysis)
                except ValueError:
                    result['reason_code'] = 'invalid_response'
        if time.monotonic() >= deadline:
            result.update(status='timeout', reason_code='deadline_exceeded', analysis=None,
                          response_complete=False, response_sha256=None)
    except Exception:
        result.update(status='rejected', reason_code='evidence_error', analysis=None,
                      response_complete=False, response_sha256=None)
        try:
            prefix = _read(folder/'response-prefix.bin', _LIMIT+1)
        except Exception:
            prefix = None
    return _publish(folder, result, prompt, body, prefix, meta_bytes)

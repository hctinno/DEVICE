"""New-only synthetic intake and manual reference fixture, using public APIs."""
from datetime import datetime, timedelta, timezone
import json
from io import UnsupportedOperation
import os
from pathlib import Path
import stat
import sys
import time
import uuid

from .active_intake import register_source, scan_source
from .fcc_case_review import build_case_review_context, decode_case_review_response
from .fcc_report_cases import FccReportCaseCatalog
from .intake_jobs import respond
from .intake_worker import SyntheticTextProvider, run_worker
from .store import Store
from . import ui_server as _ui


_PREFIX = 'intake_reference_demo_'
_CODES = frozenset(_PREFIX + suffix for suffix in
    ('invalid_argument', 'unavailable', 'output_failed', 'shutdown_failed'))
_HELP = ('Create a new synthetic PDF/TXT intake and manual reference fixture.\n'
    'Usage: python -X utf8 -B -m labflow.intake_reference_demo [--intent-view] [--output NEW_ABS_DIR]\n'
    'Only 127.0.0.1 and an owned ephemeral port are used. Open the ready URL.\n'
    '--intent-view shows manually supplied candidates without citation or basis grounds.\n'
    'Click prepare, register, then replay the original request in the existing UI.\n'
    'No candidate, real model, hardware, RF run, or operational authority.\n'
    'Ctrl+C drains the server; all new originals and state remain in output.\n')
_PRODUCER = 'DGM-SYNTHETIC-REFERENCE-DEMO-v1'
_PURPOSE = ('Synthetic manual/fixture 025 review; schema producer.kind=model; '
            'actual model calls=0; no hardware')
_LINES = ('SYNTHETIC / NO REAL MODEL OR HARDWARE', 'product_type: sensor_node',
          'market: FCC', 'model: DEMO-REFERENCE-ONLY', 'purpose: ' + _PURPOSE)
_FLAGS = {'synthetic': True, 'ai_model_called': False, 'hardware_verified': False,
          'operational_authority_granted': False}


class _Failure(ValueError):
    pass


def _fail(suffix):
    raise _Failure(_PREFIX + suffix)


def _json(value):
    return (json.dumps(value, ensure_ascii=False, allow_nan=False,
                       separators=(',', ':')) + '\n').encode('utf-8')


def _write(stream, raw):
    text = raw.decode('utf-8')
    count = stream.write(text)
    if type(count) is not int or count != len(text):
        raise OSError()
    stream.flush()


def _save(path, value):
    with path.open('xb') as stream:
        stream.write(_json(value))


def _arguments(argv):
    if type(argv) not in (list, tuple) or any(type(value) is not str for value in argv):
        _fail('invalid_argument')
    if argv.count('--intent-view') > 1:
        _fail('invalid_argument')
    intent_view = '--intent-view' in argv
    if intent_view and argv[0] != '--intent-view' and argv[-1] != '--intent-view':
        _fail('invalid_argument')
    argv = [value for value in argv if value != '--intent-view']
    if not argv:
        return None, intent_view
    if len(argv) != 2 or argv[0] != '--output':
        _fail('invalid_argument')
    value = argv[1]
    try:
        if not value or len(value.encode('utf-8')) > 32768:
            _fail('invalid_argument')
    except UnicodeError:
        _fail('invalid_argument')
    # Reject lexical aliases before pathlib can normalize them away.
    if (value.startswith(('\\\\', '//')) or '\x00' in value
            or any(part in ('.', '..') for part in value.replace('\\', '/').split('/'))):
        _fail('invalid_argument')
    path = Path(value)
    if not path.is_absolute():
        _fail('invalid_argument')
    if os.name == 'nt':
        for part in path.parts[1:]:
            if (part.endswith((' ', '.')) or any(char in part for char in ':*?"<>|')
                    or Path(part).is_reserved()):
                _fail('invalid_argument')
    return path, intent_view


def _plain_directory(path):
    """Check each existing ancestor without following a link or a junction."""
    if not path.is_absolute() or str(path).startswith(('\\\\', '//')):
        _fail('invalid_argument')
    for parent in reversed((path, *path.parents)):
        info = parent.lstat()
        if (not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode)
                or getattr(info, 'st_file_attributes', 0) & 0x400):
            _fail('invalid_argument')


def _new_leaf(path):
    _plain_directory(path.parent)
    try:
        path.lstat()
    except FileNotFoundError:
        return
    _fail('invalid_argument')


def _dependencies():
    # Optional dependencies already used by the existing synthetic PDF tools.
    import pypdf
    from reportlab.pdfgen import canvas
    if not callable(pypdf.PdfReader) or not callable(canvas.Canvas):
        _fail('unavailable')


def _reserve(custom):
    if custom is None:
        parent = Path.cwd()
        _plain_directory(parent)
        for name in ('.local', 'intake-reference-demo'):
            parent = parent / name
            try:
                parent.mkdir(exist_ok=False)
            except FileExistsError:
                pass
            _plain_directory(parent)
        output = parent / uuid.uuid4().hex
    else:
        output = custom
    _new_leaf(output)
    output.mkdir(exist_ok=False)
    return output


def _close_owned(resource, method, first, *, remember_interrupt=False):
    failures = 0
    while failures < 2:
        try:
            if getattr(resource, method)() is not None:
                raise RuntimeError()
            return True
        except KeyboardInterrupt as error:
            if remember_interrupt and first[0] is None:
                first[0] = error
            continue
        except Exception:
            if first[0] is None:
                first[0] = _PREFIX + 'shutdown_failed'
            failures += 1
    return False


def _prepare_demo(output: Path, *, intent_view=False):
    """Create only this module's sealed synthetic P0 inputs, then close P0."""
    from reportlab.pdfgen import canvas

    started = datetime.now(timezone(timedelta(hours=9))).isoformat()
    declaration = {'schema_version': 1, 'kind': 'intake_reference_demo_declaration',
        **_FLAGS, 'authoring': 'manual_fixture', 'schema_producer_kind': 'model',
        'purpose': _PURPOSE, 'started_at': started, 'resumable': False}
    _save(output / 'declaration.json', declaration)
    inbox, state = output / 'inbox', output / 'state'
    bundle = inbox / '057 합성 수동참고 데모(모델호출0)'
    bundle.mkdir(parents=True, exist_ok=False)
    with (bundle / 'request.txt').open('xb') as stream:
        stream.write(('\n'.join(_LINES) + '\n').encode('ascii'))
    # Canvas receives an exclusive stream, and the extractor reads these bytes.
    with (bundle / 'request.pdf').open('xb') as stream:
        pdf = canvas.Canvas(stream)
        text = pdf.beginText(48, 790)
        text.setFont('Courier', 7)
        for line in _LINES:
            text.textLine(line)
        pdf.drawText(text)
        pdf.showPage()
        pdf.save()

    store = Store(state)
    preparation_failed = False
    try:
        register_source(store, 'DEMO-REFERENCE-INBOX', inbox, synthetic=True, settle_seconds=0.001)
        now = time.time()
        scan_source(store, 'DEMO-REFERENCE-INBOX', now=now)
        accepted = scan_source(store, 'DEMO-REFERENCE-INBOX', now=now + 0.002)['accepted']
        if len(accepted) != 1:
            _fail('unavailable')
        intake_id = accepted[0]['intake_id']
        if intent_view:
            from .intake_jobs import claim_job, complete_job
            from .active_intake import intake_status
            from .intake_reference_snapshot import read_intake_reference_snapshot

            job = claim_job(store, 'demo-reference-analysis', synthetic_only=True)
            if type(job) is not dict or job.get('intake_id') != intake_id or job.get('synthetic') is not True:
                _fail('unavailable')
            context = {key: job[key] for key in ('job_id', 'intake_id', 'revision', 'synthetic',
                'documents', 'analysis_contract', 'instructions')}
            if 'analysis_context_id' in job:
                context['analysis_context_id'] = job['analysis_context_id']
            analysis = SyntheticTextProvider().analyze(context)
            complete_job(store, job['job_id'], job['token'], analysis)
        else:
            result = run_worker(store, SyntheticTextProvider(), worker_id='demo-reference-analysis', max_jobs=1)
            if len(result['results']) != 1 or result['results'][0]['status'] != 'completed':
                _fail('unavailable')
        response = respond(store, 'DEMO-PROCEED-' + uuid.uuid4().hex, 'proceed', intake_id=intake_id)
        if response['status'] != 'recorded':
            _fail('unavailable')
        if intent_view:
            intake = {'context': context, 'analysis': analysis,
                'projection': intake_status(store, intake_id)['analysis'],
                'observation': read_intake_reference_snapshot(store, intake_id)}
    except BaseException:
        preparation_failed = True
        raise
    finally:
        errors = [None]
        closed = _close_owned(store, 'close', errors, remember_interrupt=True)
        if not preparation_failed and isinstance(errors[0], KeyboardInterrupt):
            raise errors[0]
        if not preparation_failed and (not closed or errors[0] is not None):
            _fail('shutdown_failed')

    packet = {'schema_version': 1, 'corpus_id': 'DGM-SYNTHETIC-REFERENCE-DEMO-v1',
        'scope': {'issue_date_from': '2025-01-01', 'cutoff_at': started,
            'timezone': 'Asia/Seoul', 'population_status': 'unconfirmed',
            'search_scope_notes': ['Synthetic manual fixture; no real report or rule search'],
            'unverified_ranges': ['All real reports, rules, methods, model execution and hardware'],
            'synthetic': True}, 'searches': [], 'documents': [], 'cases': []}
    catalog = FccReportCaseCatalog(packet, {})
    query = {'product_family': 'sensor_node', 'rule': 'DEMO-RULE-NONNORMATIVE',
             'method': 'DEMO-METHOD-NONNORMATIVE-v1', 'model': 'DEMO-REFERENCE-ONLY'}
    context = build_case_review_context(catalog, query=query, case_ids=[])
    wire = {'schema_version': 1, 'kind': 'fcc_case_review_response',
        'context_id': context['context_id'], 'producer': {'kind': 'model', 'name': _PRODUCER},
        'status': 'no_candidate', 'references': [], 'reason_codes': ['no_reviewed_case']}
    validated = decode_case_review_response(_json(wire).decode('utf-8'), context, producer_name=_PRODUCER)
    inputs = ({'intake_id': intake_id, 'case_context': context,
               'validated_response': validated, 'producer_name': _PRODUCER},)
    _save(output / 'review-input.json', {'authoring': 'manual_fixture', **_FLAGS,
        'packet': packet, 'query': query, 'wire': wire, 'review_inputs': list(inputs)})
    intent_inputs = ()
    if intent_view:
        proposal = {'as_of': None, 'institution_scope': None, 'workflow_scope_id': None,
            'fields': {field: [{'literal': literal, 'origin': 'explicit_supplied',
                'intake_refs': [], 'basis_refs': []}] for field, literal in (
                    ('rule', 'DEMO-RULE-NONNORMATIVE'), ('method', 'DEMO-METHOD-NONNORMATIVE-v1'))}}
        sources = []
        intent_inputs = ((intake, proposal, sources),)
        _save(output / 'intent-input.json', {'authoring': 'manual_fixture', **_FLAGS,
            'intake': intake, 'proposal': proposal, 'sources': sources})
    return state, intake_id, catalog, inputs, intent_inputs


def _cleanup(server, store, first, *, remember_interrupt=False):
    # The official host closes admission and drains parent finally before return.
    if server is not None and not _close_owned(server, 'server_close', first, remember_interrupt=remember_interrupt):
        return False
    if store is not None and not _close_owned(store, 'close', first, remember_interrupt=remember_interrupt):
        return False
    return True


def _emit_error(code):
    try:
        _write(sys.stderr, _json({'error': {'code': code}}))
    except (Exception, KeyboardInterrupt):
        pass  # Delivery unknown: never retry a possibly delivered frame.


def _execute(argv):
    """Share one execution path and its ready phase with the process wrapper."""
    output = server = store = None
    first = [None]
    ready = False
    interrupted = False
    phase = _PREFIX + 'invalid_argument'
    try:
        arguments = sys.argv[1:] if argv is None else argv
        if (type(arguments) in (list, tuple) and len(arguments) == 1
                and type(arguments[0]) is str and arguments[0] == '--help'):
            phase = _PREFIX + 'output_failed'
            _write(sys.stdout, _HELP.encode('utf-8'))
            return 0, False
        custom, intent_view = _arguments(arguments)
        if custom is not None:
            _new_leaf(custom)
        else:
            _plain_directory(Path.cwd())
            for parent in (Path.cwd() / '.local', Path.cwd() / '.local' / 'intake-reference-demo'):
                try:
                    parent.lstat()
                except FileNotFoundError:
                    break
                _plain_directory(parent)
        phase = _PREFIX + 'output_failed'
        try:
            descriptor = sys.stdout.fileno()
        except (AttributeError, UnsupportedOperation):
            pass  # Caller-owned in-memory streams need no OS descriptor.
        else:
            os.fstat(descriptor)
        phase = _PREFIX + 'unavailable'
        _dependencies()
        phase = _PREFIX + 'invalid_argument'
        output = _reserve(custom)
        phase = _PREFIX + 'unavailable'
        state, intake_id, catalog, inputs, intent_inputs = _prepare_demo(output, intent_view=intent_view)
        store = Store.open_existing(str(state))
        if type(store) is not Store:
            store = None
            _fail('unavailable')
        server = _ui.create_server(store.root, host='127.0.0.1', port=0,
            intake_reference_store=store, fcc_case_catalog=catalog,
            intake_reference_read_scope=(intake_id,), intake_reference_append_scope=(intake_id,),
            intake_reference_review_inputs=inputs, intake_test_intent_inputs=intent_inputs)
        port = server.server_port
        if type(port) is not int or not 1 <= port <= 65535 or port in (8765, 8766):
            _fail('unavailable')
        phase = _PREFIX + 'output_failed'
        _write(sys.stdout, _json({'schema_version': 1, 'kind': 'intake_reference_demo_ready',
            'url': 'http://127.0.0.1:' + str(port) + '/#' + intake_id,
            'workspace': str(state), **_FLAGS}))
        ready = True
        phase = _PREFIX + 'unavailable'
        server.serve_forever()
    except KeyboardInterrupt as error:
        interrupted = True
        if not ready and first[0] is None:
            first[0] = error
    except Exception as error:
        code = error.args[0] if type(error) is _Failure and len(error.args) == 1 else None
        first[0] = code if type(code) is str and code in _CODES else phase
    finally:
        closed = _cleanup(server, store, first, remember_interrupt=not ready)

    # Only fixed status and resource results are recorded; no session or wire data.
    if output is not None:
        try:
            if first[0] is None and closed and ready:
                _save(output / 'closed.json', {'schema_version': 1, 'kind': 'intake_reference_demo_closed',
                    **_FLAGS, 'graceful': True})
            else:
                _save(output / ('failure-' + uuid.uuid4().hex + '.json'), {'schema_version': 1,
                    'kind': 'intake_reference_demo_incomplete', **_FLAGS, 'graceful': False,
                    'code': first[0] if type(first[0]) is str else _PREFIX + 'unavailable'})
        except (Exception, KeyboardInterrupt):
            if first[0] is None:
                first[0] = _PREFIX + 'output_failed'
    if isinstance(first[0], KeyboardInterrupt):
        return 130, ready
    if first[0] is not None:
        _emit_error(first[0])
        return (2 if first[0] == _PREFIX + 'invalid_argument' else 1), ready
    return (130 if interrupted and not ready else 0), ready


def main(argv=None) -> int:
    """Return fixed codes without replacing, reconfiguring or closing caller I/O."""
    return _execute(argv)[0]


def _process_main():
    # Only a standalone module process owns stream configuration and final flush.
    ready = False
    try:
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.reconfigure(encoding='utf-8', errors='strict', newline='\n')
            except Exception:
                pass
        status, ready = _execute(None)
    except KeyboardInterrupt:
        status = 130
    for stream in (sys.stdout, sys.stderr):
        while True:
            try:
                stream.flush()
                break
            except KeyboardInterrupt:
                if status == 0 and not ready:
                    status = 130
                continue
            except Exception:
                if status == 0:
                    status = 1
                    _emit_error(_PREFIX + 'output_failed')
                os._exit(status)  # Owned cleanup is finished; prevent exit120.
    return status


if __name__ == '__main__':
    raise SystemExit(_process_main())

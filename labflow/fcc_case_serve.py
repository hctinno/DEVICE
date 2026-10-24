"""Start one explicit source-checked FCC catalog on the existing loopback UI."""
import json
import os
from pathlib import Path
import re
import sys

from . import control_packet_prepare as _native
from . import fcc_case_catalog_host as _host
from . import fcc_report_cases as _cases
from . import ui_server as _ui


_MIB = 1024 * 1024
_RECEIPT_BYTES = 8 * _MIB
_READY_BYTES = _RECEIPT_BYTES + 1024
_OPTIONS = frozenset(('--config', '--config-sha256', '--state-dir', '--port'))
_DB_NAMES = ('lab.sqlite3', 'lab.sqlite3-wal', 'lab.sqlite3-shm', 'lab.sqlite3-journal')
_VERIFICATION = frozenset(('authority_or_rights_verified', 'hardware_verified',
                          'normative_compliance_verified', 'currentness_verified', 'execution_authorized'))
_HOST_FIELDS = frozenset(('schema_version', 'kind', 'config_sha256', 'metadata_preparation',
                         'inputs', 'page_scopes', 'construction', 'verification'))
_HOST_CODES = frozenset(('fcc_case_host_invalid_argument', 'fcc_case_host_path_invalid',
                        'fcc_case_host_unavailable', 'fcc_case_host_pin_mismatch',
                        'fcc_case_host_input_changed', 'fcc_case_host_backend_unavailable'))
_CASE_CODES = frozenset(('fcc_case_invalid_packet', 'fcc_case_invalid_sources', 'fcc_case_limit_exceeded',
                        'fcc_case_pdf_invalid', 'fcc_case_extraction_unavailable', 'fcc_case_invalid_evidence',
                        'fcc_case_invalid_query', 'fcc_case_not_found', 'fcc_case_invalid_intake'))
_HELP = (
    'Start an explicit FCC catalog on 127.0.0.1 using an existing no-Store directory.\n'
    'Usage: python -B -m labflow.fcc_case_serve --config ABS_JSON --config-sha256 SHA256 '
    '--state-dir ABS_DIR --port PORT\n'
    'All four options are required exactly once, with separate values. No defaults.\n'
    'PORT is canonical ASCII 0..65535; use 0 for test-owned ephemeral ports.\n'
    'No directory/Store/DB creation, browser, scan, retry, reload, hardware, or model.\n'
    'Usage: python -B -m labflow.fcc_case_serve --help\n'
)


class _Failure(ValueError):
    pass


def _fail(code):
    raise _Failure(code)


def _text(value):
    return (type(value) is str and bool(value) and value.strip() == value
            and not any(ord(c) < 32 or ord(c) == 127 for c in value))


def _arguments(argv):
    if type(argv) not in (list, tuple) or len(argv) != 8 or any(type(v) is not str for v in argv):
        _fail('fcc_case_server_invalid_argument')
    result = {}
    for option, value in zip(argv[::2], argv[1::2]):
        if option not in _OPTIONS or option in result or not value or value.isspace():
            _fail('fcc_case_server_invalid_argument')
        result[option] = value
    if set(result) != _OPTIONS:
        _fail('fcc_case_server_invalid_argument')
    config, pin, port = result['--config'], result['--config-sha256'], result['--port']
    if (not _text(config) or not _text(pin) or not re.fullmatch('[0-9a-f]{64}', pin, re.ASCII)
            or not re.fullmatch('0|[1-9][0-9]{0,4}', port, re.ASCII) or int(port) > 65535):
        _fail('fcc_case_server_invalid_argument')
    try:
        path = Path(config)
        if not path.is_absolute() or path.suffix.lower() != '.json':
            _fail('fcc_case_server_invalid_argument')
        path = _native._local_path(config)
    except Exception:
        _fail('fcc_case_server_invalid_argument')
    return path, pin, result['--state-dir'], int(port)


def _state_snapshot(value):
    """Check only native directory components and four fixed entry attributes."""
    if not _text(value) or not Path(value).is_absolute():
        raise ValueError()
    # GetFullPathNameW can erase a trailing dot before the native helper sees it.
    components = re.split(r'[\\/]', value[len(Path(value).drive):])
    if any(not _native._valid_segment(part) for part in components if part):
        raise ValueError()
    path = _native._local_path(value)
    backend = None
    try:
        backend = _native._WindowsIO()
        tree = _native._Tree(path, backend)
        for name in _DB_NAMES:
            try:
                backend.stat_file(path / name)
            except FileNotFoundError:
                continue
            raise ValueError()
        snapshot = tuple(tree.directories.items())
    finally:
        if backend is not None:
            backend.close()
    return path, snapshot


def _json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')


def _ready(catalog, receipt, pin, port):
    failed, raw = False, None
    try:
        # Preserve the complete parent's byte budget; do not impose a smaller string/node budget.
        receipt = _cases._plain(receipt, byte_limit=_RECEIPT_BYTES, string_limit=_RECEIPT_BYTES,
                                node_limit=_RECEIPT_BYTES, depth_limit=32)
        if (type(receipt) is not dict or set(receipt) != _HOST_FIELDS
                or type(receipt['schema_version']) is not int or receipt['schema_version'] != 1
                or receipt['kind'] != 'fcc_case_catalog_host_load' or receipt['config_sha256'] != pin
                or type(receipt['verification']) is not dict or set(receipt['verification']) != _VERIFICATION
                or any(receipt['verification'][key] is not False for key in _VERIFICATION)
                or type(receipt['construction']) is not dict
                or type(receipt['construction'].get('case_count')) is not int
                or type(port) is not int or not 1 <= port <= 65535):
            raise ValueError()
        count = _cases.FccReportCaseCatalog.summary(catalog)['counts']['case_count']
        if receipt['construction']['case_count'] != count:
            raise ValueError()
        result = {'schema_version': 1, 'kind': 'fcc_case_catalog_server_ready',
                  'url': 'http://127.0.0.1:' + str(port) + '/fcc-cases/', 'config_sha256': pin,
                  'catalog_state': 'configured' if count else 'configured_empty', 'state_mode': 'no_store_at_startup',
                  'host_receipt': receipt, 'verification': dict(receipt['verification'])}
        raw = _json(result) + b'\n'
        if len(raw) > _READY_BYTES:
            raise ValueError()
    except Exception:
        failed = True
    if failed:
        _fail('fcc_case_server_output_failed')
    return raw


def _write(stream, raw):
    value = raw.decode('utf-8')
    if stream.write(value) != len(value):
        raise OSError()
    stream.flush()


def main(argv=None) -> int:
    """Return 0/1/2, keeping caller streams and every startup input unmodified."""
    server, code, status = None, None, 0
    phase = 'fcc_case_server_invalid_argument'
    try:
        arguments = sys.argv[1:] if argv is None else argv
        if type(arguments) in (list, tuple) and len(arguments) == 1 and type(arguments[0]) is str and arguments[0] == '--help':
            phase = 'fcc_case_server_output_failed'
            _write(sys.stdout, _HELP.encode('utf-8'))
            return 0
        config, pin, state_value, port = _arguments(arguments)
        phase = 'fcc_case_server_state_invalid'
        state, snapshot = _state_snapshot(state_value)
        phase = 'fcc_case_server_unavailable'
        catalog, receipt = _host.load_fcc_case_catalog(config, expected_config_sha256=pin)
        if type(catalog) is not _cases.FccReportCaseCatalog:
            _fail('fcc_case_server_unavailable')
        phase = 'fcc_case_server_input_changed'
        after_state, after_snapshot = _state_snapshot(state_value)
        if state != after_state or snapshot != after_snapshot:
            _fail('fcc_case_server_input_changed')
        phase = 'fcc_case_server_bind_failed'
        server = _ui.create_server(state, host='127.0.0.1', port=port, fcc_case_catalog=catalog)
        phase = 'fcc_case_server_output_failed'
        _write(sys.stdout, _ready(catalog, receipt, pin, server.server_port))
        phase = 'fcc_case_server_unavailable'
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    except _Failure as error:
        code = error.args[0]
    except (_host.FccCaseCatalogHostError, _cases.FccReportCaseError) as error:
        value = error.code
        allowed = _HOST_CODES if isinstance(error, _host.FccCaseCatalogHostError) else _CASE_CODES
        code = value if type(value) is str and value in allowed else 'fcc_case_server_unavailable'
    except Exception:
        code = phase
    finally:
        if server is not None:
            try:
                server.server_close()
            except Exception:
                if code is None:
                    code = 'fcc_case_server_unavailable'
    if code is not None:
        status = 2 if code in ('fcc_case_server_invalid_argument', 'fcc_case_server_state_invalid') else 1
        try:
            _write(sys.stderr, _json({'error': {'code': code}}) + b'\n')
        except Exception:
            pass
    return status


def _process_main():
    """Configure/finalize only this CLI process; main() does not replace caller I/O."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8', errors='strict', newline='\n')
        except Exception:
            pass
    status = main()
    for stream in (sys.stdout, sys.stderr):
        if stream is None:
            continue
        try:
            stream.flush()
        except Exception:
            if status == 0:
                status = 1
                try:
                    _write(sys.stderr, _json({'error': {'code': 'fcc_case_server_output_failed'}}) + b'\n')
                except Exception:
                    pass
            try:
                target = stream.fileno()
                sink = os.open(os.devnull, os.O_WRONLY)
                try:
                    if sink != target:
                        os.dup2(sink, target)
                finally:
                    if sink != target:
                        os.close(sink)
            except Exception:
                os._exit(status)
    return status


if __name__ == '__main__':
    raise SystemExit(_process_main())

"""Print one stored RF observation without executing or reassessing it."""
import json
import os
import sys


_PREFIX = 'rf_signal_read_cli_'
_PARENT_CODES = frozenset('rf_signal_read_' + name for name in (
    'invalid_argument', 'path_invalid', 'not_found', 'input_changed', 'evidence_invalid', 'unavailable'))
_SELECTION_CODES = frozenset('rf_signal_read_' + name for name in ('invalid_argument', 'path_invalid', 'not_found'))
_KEYS = frozenset('schema_version kind selection metadata storage historical_assessment measurement '
                  'measurement_goal_succeeded outcome failure verification execution_authorized '
                  'rerun_authorized error_code'.split())
_STORAGE = frozenset('status manifest_sha256 verified_file_count journal_status binding_verified'.split())
_STATUS = {'complete_verified': 0, 'incomplete': 3, 'invalid': 4}
_HELP = ('보존 가상 RF 기록 조회: print one stored observation; never execute or reassess.\n'
         'Usage: python -B -m labflow.virtual_fleet.rf_signal_read_cli --run-name NAME\n'
         'Specify --run-name exactly once with a separate value; no defaults or other options.\n'
         'The read API owns name validation and this clone/.local/rf-signal-runs/NAME.\n'
         'JSON body <=8192 UTF-8 bytes plus one LF; original DTO14, no envelope or rewriting.\n'
         'Exit: complete observation 0, incomplete 3, invalid DTO 4; past verdict is separate.\n'
         'No run/evaluation/retry/scan/source read/file write/server/model/hardware.\n'
         'Usage: python -B -m labflow.virtual_fleet.rf_signal_read_cli --help\n')


class _Failure(ValueError):
    pass


def _fail(suffix):
    raise _Failure(_PREFIX + suffix)


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(',', ':')).encode('utf-8')


def _write(stream, raw):
    value = raw.decode('utf-8')
    if stream.write(value) != len(value):
        raise OSError()
    stream.flush()


def _argument(argv):
    if (type(argv) not in (list, tuple) or len(argv) != 2
            or any(type(value) is not str for value in argv) or argv[0] != '--run-name'):
        _fail('invalid_argument')
    return argv[1]


def _result_status(value):
    if (type(value) is not dict or set(value) != _KEYS or type(value['schema_version']) is not int
            or value['schema_version'] != 1 or value['kind'] != 'virtual_rf_signal_run_read'
            or type(value['storage']) is not dict or set(value['storage']) != _STORAGE
            or type(value['storage']['status']) is not str or value['storage']['status'] not in _STATUS):
        _fail('unavailable')
    return _STATUS[value['storage']['status']]


def main(argv=None) -> int:
    """Return query/delivery status; retain caller streams and parent DTO values."""
    code, status, parent_error = None, 0, None
    phase = _PREFIX + 'invalid_argument'
    try:
        arguments = sys.argv[1:] if argv is None else argv
        if (type(arguments) in (list, tuple) and len(arguments) == 1
                and type(arguments[0]) is str and arguments[0] == '--help'):
            phase = _PREFIX + 'output_failed'
            _write(sys.stdout, _HELP.encode('utf-8'))
            return 0
        name = _argument(arguments)
        phase = _PREFIX + 'unavailable'
        from . import rf_signal_read as reader
        parent_error = reader.RfSignalReadError
        if not isinstance(parent_error, type) or not issubclass(parent_error, Exception) or not callable(reader.read_rf_signal_run):
            _fail('unavailable')
        result = reader.read_rf_signal_run(name)
        status = _result_status(result)
        phase = _PREFIX + 'output_failed'
        raw = _json(result)
        if len(raw) > 8192:
            _fail('output_failed')
        _write(sys.stdout, raw + b'\n')
    except KeyboardInterrupt:
        code, status = _PREFIX + 'interrupted', 130
    except _Failure as error:
        code = error.args[0]
        status = 2 if code == _PREFIX + 'invalid_argument' else 1
    except Exception as error:
        if parent_error is not None and type(error) is parent_error:
            value = getattr(error, 'code', None)
            code = value if type(value) is str and value in _PARENT_CODES else _PREFIX + 'unavailable'
            status = 2 if code in _SELECTION_CODES else 1
        else:
            code = phase
            status = 2 if phase == _PREFIX + 'invalid_argument' else 1
    if code is not None:
        try:
            _write(sys.stderr, _json({'error': {'code': code}}) + b'\n')
        except Exception:
            pass
    return status


def _process_main():
    """Configure only this process and preserve its first operating failure."""
    configured = True
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8', errors='strict', newline='\n')
        except Exception:
            configured = False
    if configured:
        status = main()
    else:
        status = 1
        try:
            _write(sys.stderr, _json({'error': {'code': _PREFIX + 'output_failed'}}) + b'\n')
        except Exception:
            pass
    for stream in (sys.stdout, sys.stderr):
        if stream is None:
            continue
        try:
            stream.flush()
        except Exception:
            if status in (0, 3, 4):
                status = 1
                try:
                    _write(sys.stderr, _json({'error': {'code': _PREFIX + 'output_failed'}}) + b'\n')
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

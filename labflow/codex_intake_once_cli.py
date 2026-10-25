"""Noauth intake CLI. Actual issuer and budget admission remain unimplemented.

Native metadata is never authority. Production main cannot open a Store, consume
a reservation or call once. Finite composition is confined to the owned tests.
"""
from datetime import datetime, timezone
import hashlib
import json
import math
import ntpath
import os
from pathlib import Path
import re
import stat
import sys

from .intake_model_boundary import build_analysis_prompt
from .store import canonical, identifier


__all__ = ['main']
_PREFIX = 'codex_intake_host_'
_CONTROL = (KeyboardInterrupt, SystemExit, GeneratorExit, MemoryError)
_MODELS = ('gpt-6.1-sol', 'gpt-6-astra')
_PATH = type(Path())
_SHA = re.compile(r'[a-f0-9]{64}\Z', re.ASCII)
_PUBLIC = set('job_id intake_id revision synthetic documents analysis_context_id analysis_contract instructions'.split())
_HELP = ('Usage: python -B -m labflow.codex_intake_once_cli '
         '--scenario-id ID --model gpt-6.1-sol|gpt-6-astra\n'
         'Each option is required once with a separate value. No stdin input.\n'
         'Actual issuer is unavailable: not_run, authorization unknown, model0.\n')


class _Failure(ValueError):
    def __init__(self, suffix, *, status='not_run', exit_code=2):
        self.code = _PREFIX + suffix
        self.status, self.exit_code = status, exit_code
        super().__init__(self.code)


def _invalid():
    raise _Failure('invalid_input')


def _arguments(argv):
    if type(argv) not in (list, tuple) or len(argv) != 4 or any(type(v) is not str for v in argv):
        _invalid()
    values = {}
    for option, value in zip(argv[::2], argv[1::2]):
        if option not in ('--scenario-id', '--model') or option in values:
            _invalid()
        values[option] = value
    if set(values) != {'--scenario-id', '--model'} or values['--model'] not in _MODELS:
        _invalid()
    try:
        identifier(values['--scenario-id'])
    except ValueError:
        _invalid()
    return values['--scenario-id'], values['--model']


def _keys(value, names):
    if (type(value) is not dict or any(type(key) is not str for key in value)
            or set(value) != set(names.split())):
        _invalid()


def _id(value):
    if type(value) is not str:
        _invalid()
    try:
        return identifier(value)
    except ValueError:
        _invalid()


def _hash(value):
    if type(value) is not str or not _SHA.fullmatch(value):
        _invalid()


def _path_shape(value, *, native):
    if (native and type(value) is not _PATH) or (not native and type(value) is not str):
        _invalid()
    text = str(value)
    try:
        if len(text.encode('utf-8')) > 16384 or any(ord(c) < 32 or 127 <= ord(c) <= 159 for c in text):
            _invalid()
    except UnicodeError:
        _invalid()
    drive, tail = ntpath.splitdrive(text)
    if (not re.fullmatch(r'[A-Za-z]:', drive, re.ASCII) or not tail.startswith(('\\', '/'))
            or any(p in ('.', '..') or p.endswith((' ', '.')) or any(c in '<>:"|?*' for c in p)
                   for p in re.split(r'[\\/]', tail) if p)):
        _invalid()


def _utc_now():
    return datetime.now(timezone.utc)


def _check_expiry(binding):
    value = binding['expires_at']
    if type(value) is not str or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z', value):
        _invalid()
    try:
        deadline = datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    except ValueError:
        _invalid()
    if _utc_now() >= deadline:
        raise _Failure('not_authorized', exit_code=3)


def _validate_authorization(value, scenario, model):
    """Validate metadata only. Returning a snapshot never authenticates an issuer."""
    _keys(value, 'authorization_ref registered_intake execution expires_at reservation')
    registered, execution, reservation = value['registered_intake'], value['execution'], value['reservation']
    _keys(registered, 'scenario_id registration_sha256 input_bundle_sha256')
    _keys(execution, 'store_root approved_context worker_id producer_name executable requested_model evidence_root timeout_seconds')
    _keys(reservation, 'budget_id reservation_id reservation_record_ref reservation_record_sha256 scope_sha256 reserved_model_attempts state consumption_root')
    for item in (value['authorization_ref'], registered['scenario_id'], execution['worker_id'],
                 reservation['budget_id'], reservation['reservation_id'], reservation['reservation_record_ref']):
        _id(item)
    for item in (registered['registration_sha256'], registered['input_bundle_sha256'],
                 reservation['reservation_record_sha256'], reservation['scope_sha256']):
        _hash(item)
    if (type(execution['requested_model']) is not str or execution['requested_model'] not in _MODELS or
            type(reservation['reserved_model_attempts']) is not int or reservation['reserved_model_attempts'] != 1 or
            type(reservation['state']) is not str or reservation['state'] != 'reserved' or
            type(execution['timeout_seconds']) not in (int, float) or
            not 0 < execution['timeout_seconds'] <= 60 or not math.isfinite(execution['timeout_seconds'])):
        _invalid()
    _path_shape(execution['store_root'], native=False)
    for path in (execution['executable'], execution['evidence_root'], reservation['consumption_root']):
        _path_shape(path, native=True)
    if execution['executable'].name.lower() != 'codex.exe':
        _invalid()
    context = execution['approved_context']
    _keys(context, ' '.join(_PUBLIC))
    if context.get('synthetic') is not True:
        _invalid()
    try:
        prompt = build_analysis_prompt(context, producer_name=execution['producer_name'])
        context = json.loads(prompt['messages'][1]['content'])
        if context['analysis_contract']['schema_version'] != 1 or len(canonical(prompt).encode('utf-8')) > 262144:
            _invalid()
    except _CONTROL:
        raise
    except ValueError:
        _invalid()
    binding = dict(authorization_ref=value['authorization_ref'], registered_intake=registered.copy(),
                   execution={**execution, 'approved_context': context}, expires_at=value['expires_at'],
                   reservation=reservation.copy())
    scope_execution = {k: v for k, v in binding['execution'].items() if k != 'approved_context'}
    scope_execution.update(context_sha256=hashlib.sha256(canonical(context).encode('utf-8')).hexdigest(),
        executable=str(execution['executable']), evidence_root=str(execution['evidence_root']))
    scope = dict(authorization_ref=binding['authorization_ref'], registered_intake=binding['registered_intake'],
                 execution=scope_execution, expires_at=binding['expires_at'])
    if hashlib.sha256(canonical(scope).encode('utf-8')).hexdigest() != reservation['scope_sha256']:
        _invalid()
    if registered['scenario_id'] != scenario or execution['requested_model'] != model:
        raise _Failure('not_authorized', exit_code=3)
    _check_expiry(binding)
    return binding


def _safe_path(path, *, directory):
    for parent in reversed(path.parents):
        info = parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            _invalid()
    info = path.lstat()
    if (stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400 or
            (not stat.S_ISDIR(info.st_mode) if directory else not stat.S_ISREG(info.st_mode) or info.st_nlink != 1)):
        _invalid()


def _check_paths(binding):
    """Finite test composition preflight; never called by production main."""
    execution = binding['execution']
    directories = (Path(execution['store_root']), execution['evidence_root'], binding['reservation']['consumption_root'])
    if len(set(directories)) != 3:
        _invalid()
    try:
        for directory in directories:
            _safe_path(directory, directory=True)
        _safe_path(execution['executable'], directory=False)
        with os.scandir(execution['evidence_root']) as entries:
            if next(entries, None) is not None:
                _invalid()
    except OSError:
        _invalid()


def _consume_reservation(binding):
    """Exclusive tokenless marker for test composition; not a budget reservation."""
    _check_expiry(binding)
    reservation, execution = binding['reservation'], binding['execution']
    parent = reservation['consumption_root']
    _safe_path(parent, directory=True)
    key = canonical([reservation['budget_id'], reservation['reservation_id']]).encode('utf-8')
    path = parent / (hashlib.sha256(key).hexdigest() + '.json')
    payload = canonical(dict(schema_version=1, kind='codex_intake_reservation_consumption',
        authorization_ref=binding['authorization_ref'], budget_id=reservation['budget_id'],
        reservation_id=reservation['reservation_id'], scope_sha256=reservation['scope_sha256'],
        evidence_ref=hashlib.sha256(str(execution['evidence_root']).encode('utf-8')).hexdigest())).encode('utf-8')
    if len(payload) > 65536:
        raise _Failure('evidence_error', status='unknown', exit_code=5)
    try:
        stream = path.open('xb')
    except FileExistsError:
        raise _Failure('reservation_unavailable', exit_code=3) from None
    except _CONTROL:
        raise
    except Exception:
        raise _Failure('evidence_error', status='unknown', exit_code=5) from None
    try:
        try:
            if stream.write(payload) != len(payload):
                raise OSError()
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            try:
                stream.close()
            except BaseException:
                pass
            raise
        else:
            stream.close()
    except _CONTROL:
        raise
    except Exception:
        raise _Failure('evidence_error', status='unknown', exit_code=5) from None
    return path


def _error(phase, code, *, status='not_run', attempts=0, secondary=()):
    return dict(schema_version=1, kind='codex_intake_host_error', status=status,
                phase=phase, code=code, authorization_status='unknown',
                model_process_attempts=attempts, secondary_codes=list(secondary)[:2])


def _write(stream, payload):
    count = stream.write(payload)
    if type(count) is not int or count != len(payload):
        raise OSError()
    stream.flush()


def _json_frame(value, limit):
    text = canonical(value) + '\n'
    if len(text.encode('utf-8')) > limit + 1:
        raise OSError()
    return text


def main(argv=None, *, authorization=None) -> int:
    """Validate explicit input and report unavailable actual authority; no dispatch."""
    phase = 'arguments'
    try:
        args = sys.argv[1:] if argv is None else argv
        if type(args) in (list, tuple) and len(args) == 1 and type(args[0]) is str and args[0] == '--help':
            payload, stream, status = _HELP, sys.stdout, 0
        else:
            scenario, model = _arguments(args)
            phase = 'authorization'
            if authorization is not None:
                _validate_authorization(authorization, scenario, model)
            # No issuer exists. This is a terminal refusal, not a stub gate.
            payload = _json_frame(_error(phase, _PREFIX + 'not_authorized'), 4096)
            stream, status = sys.stderr, 3
    except _CONTROL:
        raise
    except _Failure as error:
        payload = _json_frame(_error(phase, error.code, status=error.status), 4096)
        stream, status = sys.stderr, error.exit_code
    except Exception:
        payload = _json_frame(_error(phase, _PREFIX + 'internal_error', status='unknown'), 4096)
        stream, status = sys.stderr, 5
    try:
        _write(stream, payload)
    except _CONTROL:
        raise
    except Exception:
        return 5
    return status


def _process_main():
    """Configure only owned process streams; suppress interpreter retry on error."""
    control_status, status = None, 5
    try:
        for stream in (sys.stdout, sys.stderr):
            stream.reconfigure(encoding='utf-8', errors='strict', newline='\n')
        status = main()
    except KeyboardInterrupt:
        control_status, status = 130, 130
    except (SystemExit, GeneratorExit, MemoryError):
        control_status, status = 5, 5
    except Exception:
        status = 5
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.flush()
        except _CONTROL as error:
            if control_status is None:
                control_status = 130 if isinstance(error, KeyboardInterrupt) else 5
            os._exit(control_status)
        except Exception:
            os._exit(5 if control_status is None else control_status)
    return status


if __name__ == '__main__':
    raise SystemExit(_process_main())

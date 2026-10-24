"""Explicit entry for one authored synthetic RF scenario, never hardware."""
import hashlib
import json
import math
import ntpath
import os
from pathlib import Path
import re
import stat
import sys
import uuid

from .. import control_packet_prepare as _native
from . import catalog as _catalog, journal as _journal, rf_signal_scenario as _scenario


_SCENARIOS = ('pulsed_on_mean', 'pulsed_time_mean', 'pulsed_peak', 'cw_peak',
              'shifted_frequency', 'sensor_uncalibrated', 'meter_frequency_conflict')
_OPTIONS = frozenset(('--scenario', '--seed', '--run-name'))
_ENGINE_FILES = (
    '__init__.py', '__main__.py', 'catalog.py', 'core.py', 'evaluation.py',
    'facility.py', 'frequency_psd.py', 'frequency_psd_max.py', 'frequency_source.py',
    'harness.py', 'harness_check.py', 'instruments.py', 'integration.py', 'journal.py',
    'method_adapter.py', 'policies.py', 'rf.py', 'spectrum_capture.py', 'spectrum_math.py')
_ENGINE_SHA = '9b128c2e397efffd118a0be05b856d489b6da7ba96b808acc369dc77d3780c42'
_CATALOG_SHA = '6f27b5d9ac3d3805b7f198dc0d186865cbfdcaf489d4bceba0572f99709313ff'
_CATALOG_PATH = 'virtual_profiles/sm_a176u_unlicensed.json'
_CODE_PINS = {
    'labflow/virtual_fleet/rf_signal_scenario.py':
        (44423, 'bae395d27975dcfe5a64c5a4ea2ae86dccfa87f6d88c9e2c25b2283333a77cae'),
    'labflow/control_packet_prepare.py':
        (28907, 'c6fcc54fbac917a5a24a1b07e4ff2b3f82945383ca01d581c1829e9ed0341e6c')}
_PARENT_CODES = frozenset('rf_signal_scenario_' + name for name in (
    'invalid_request', 'unsupported_catalog', 'output_unavailable',
    'execution_incomplete', 'evidence_invalid', 'evidence_unavailable'))
_FLAGS = dict(data_origin='authored_synthetic', execution_mode='synthetic_virtual_execution',
              synthetic=True, hardware_verified=False, physical_verified=False, ai_model_called=False,
              normative_compliance_verified=False, method_approval='not_assessed',
              regulatory_scope_complete=False, waveform_implemented=False)
_OUTER_KEYS = set('schema_version kind scenario_id status declared_setup report assessment artifacts '
                  'error_code verification'.split())
_ASSESSMENT_KEYS = set('status verdict evaluator_id evidence_refs summary_code'.split())
_REPORT_KEYS = set('schema_version kind run_id runtime_instance_id synthetic hardware_verified '
                   'ai_model_called policy termination task_outcome cleanup usage evidence '
                   'unresolved_request_ids assessment'.split())
_MANIFEST_KEYS = set('schema_version kind complete request catalog_sha256 topology_sha256 engine_sha256 files'.split())
_FILES = {'public-result.json': (327680, 'operator'), 'operator/events.jsonl': (33554432, 'operator'),
          'private/author.json': (1048576, 'evaluator_private')}
_HELP = ('가상 합성 RF 실행: one explicit authored synthetic scenario, never hardware.\n'
         'Usage: python -B -m labflow.virtual_fleet.rf_signal_cli '
         '--scenario ID --seed ASCII_INT --run-name NAME\n'
         'All three options are required exactly once with separate values; no defaults.\n'
         'Scenarios: ' + ', '.join(_SCENARIOS) + '\n'
         'Seed: canonical ASCII 0..2147483647. NAME: ASCII alphanumeric start, '
         'then alphanumeric/_/-, at most 64 characters; no Windows reserved names.\n'
         'Output: this clone/.local/rf-signal-runs/NAME; existing names are rejected.\n'
         'No catalog, hardware, model, server, or retry options.\n'
         'Usage: python -B -m labflow.virtual_fleet.rf_signal_cli --help\n')


class _Failure(ValueError):
    pass


def _fail(code):
    raise _Failure('rf_signal_cli_' + code)


def _json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')


def _write(stream, raw):
    value = raw.decode('utf-8')
    if stream.write(value) != len(value):
        raise OSError()
    stream.flush()


def _arguments(argv):
    if type(argv) not in (list, tuple) or len(argv) != 6 or any(type(v) is not str for v in argv):
        _fail('invalid_argument')
    options = {}
    for option, value in zip(argv[::2], argv[1::2]):
        if option not in _OPTIONS or option in options:
            _fail('invalid_argument')
        options[option] = value
    seed, name = options['--seed'], options['--run-name']
    if (options['--scenario'] not in _SCENARIOS
            or re.fullmatch('0|[1-9][0-9]{0,9}', seed, re.ASCII) is None or int(seed) > 2147483647
            or re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{0,63}', name, re.ASCII) is None
            or not _native._valid_segment(name)):
        _fail('invalid_argument')
    return dict(schema_version=1, scenario_id=options['--scenario'], seed=int(seed)), name


def _require(condition):
    if not condition:
        raise ValueError()


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False,
                      sort_keys=True, separators=(',', ':')).encode('utf-8')


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _stamp(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_mode


def _root():
    # Check lexical segments before abspath/Path could hide a Windows alias.
    value = __file__
    tail = ntpath.splitdrive(value)[1]
    if (not value or not Path(value).is_absolute() or value.startswith(('\\\\', '//'))
            or re.search(r'[\\/]{2}', tail)
            or any(not _native._valid_segment(part) for part in re.split(r'[\\/]', tail) if part)):
        _fail('output_invalid')
    return _native._local_path(str(Path(value).absolute().parents[2]))


def _absent(tree, path):
    if path.parent not in tree.directories:
        return
    try:
        tree.backend.stat_file(path)
    except FileNotFoundError:
        return
    _fail('output_invalid')


def _identities(tree):
    # Fresh relative entry observations complement the held ancestor handles.
    for path, identity in tuple(tree.directories.items()):
        descriptor = tree.backend.directories[path]
        held = tree.backend.info(descriptor, directory=True)
        current = held if path == Path(path.anchor) else tree.backend.stat_file(path)
        _require(stat.S_ISDIR(current.st_mode)
                 and (held.st_dev, held.st_ino) == identity == (current.st_dev, current.st_ino))


def _source(tree, relative):
    path = tree.root / relative
    tree.directory(path.parent)
    before = tree.file_stat(path)
    with path.open('rb') as stream:
        _require(_stamp(os.fstat(stream.fileno())) == _stamp(before))
        raw = stream.read(1048577)
    after = tree.file_stat(path)
    if len(raw) > 1048576 or _stamp(before) != _stamp(after):
        _fail('input_changed')
    return raw, (_stamp(after), _sha(raw))


def _inputs(tree):
    snapshot, engine = {}, hashlib.sha256()
    for name in _ENGINE_FILES:
        relative = 'labflow/virtual_fleet/' + name
        raw, snapshot[relative] = _source(tree, relative)
        engine.update(name.encode('utf-8') + b'\0' + raw.replace(b'\r\n', b'\n') + b'\0')
    if engine.hexdigest() != _ENGINE_SHA:
        _fail('input_changed')
    for relative, expected in _CODE_PINS.items():
        raw, snapshot[relative] = _source(tree, relative)
        normalized = raw.replace(b'\r\n', b'\n')
        if (len(normalized), _sha(normalized)) != expected:
            _fail('input_changed')
    _, snapshot[_CATALOG_PATH] = _source(tree, _CATALOG_PATH)
    return snapshot


def _plain(value):
    nodes = 0
    def copy(item, depth=0):
        nonlocal nodes
        nodes += 1
        _require(nodes <= 16384 and depth <= 20)
        if type(item) is dict:
            _require(all(type(key) is str for key in item))
            return {key: copy(val, depth + 1) for key, val in item.items()}
        if type(item) is list:
            return [copy(val, depth + 1) for val in item]
        _require(item is None or type(item) in (bool, str, int, float))
        if type(item) is float:
            _require(math.isfinite(item))
        if type(item) is str:
            _require(len(item) <= 16384)
        return item
    result = copy(value)
    _require(len(_json(result)) <= 327680)
    return result


def _returned(value, request, run_id, instance):
    result = _plain(value)
    _require(type(result) is dict and set(result) == _OUTER_KEYS
             and type(result['schema_version']) is int and result['schema_version'] == 1
             and result['kind'] == 'virtual_rf_signal_scenario'
             and result['scenario_id'] == request['scenario_id']
             and result['status'] in ('executed', 'rejected', 'failed')
             and _canonical(result['verification']) == _canonical(_FLAGS))
    assessment = result['assessment']
    _require(type(assessment) is dict and set(assessment) == _ASSESSMENT_KEYS
             and type(assessment['evidence_refs']) is list
             and all(type(ref) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}', ref)
                     for ref in assessment['evidence_refs'])
             and len(set(assessment['evidence_refs'])) == len(assessment['evidence_refs'])
             and assessment['summary_code'] in (None, 'expected_sensor_blocked', 'expected_meter_frequency_conflict',
                                                 'observed_signal_satisfied', 'scenario_expectation_mismatch',
                                                 'operator_evidence_invalid'))
    if result['status'] == 'executed':
        _require(assessment['status'] == 'completed' and assessment['verdict'] in ('pass', 'fail')
                 and assessment['evaluator_id'] == 'rf_signal_scenario_v1' and result['error_code'] is None
                 and _canonical(result['declared_setup']) ==
                 _canonical(_scenario.describe_rf_signal_scenario(request['scenario_id'])))
    else:
        _require(result['error_code'] in _PARENT_CODES and assessment['verdict'] is None
                 and assessment['status'] in ('not_assessed', 'failed')
                 and assessment['evaluator_id'] in (None, 'rf_signal_scenario_v1'))
    report = result['report']
    if report is not None:
        _require(type(report) is dict and set(report) == _REPORT_KEYS
                 and report['run_id'] == run_id and report['runtime_instance_id'] == instance
                 and report['synthetic'] is True and report['hardware_verified'] is False
                 and report['ai_model_called'] is False)
    else:
        _require(result['status'] != 'executed')
    return result


def _unique(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result)
        result[key] = value
    return result


def _parse(raw):
    def constant(_):
        raise ValueError()
    return json.loads(raw.decode('utf-8'), object_pairs_hook=_unique, parse_constant=constant)


def _evidence_file(tree, path, limit):
    tree.directory(path.parent)
    before = tree.file_stat(path)
    descriptor = tree.backend.open_read(path, pin=True)
    _require(_stamp(tree.backend.info(descriptor, directory=False)) == _stamp(before)
             and before.st_size <= limit)
    data = bytearray()
    while len(data) <= limit:
        part = os.read(descriptor, min(65536, limit + 1 - len(data)))
        if not part:
            break
        data.extend(part)
    _require(len(data) <= limit and _stamp(tree.file_stat(path)) == _stamp(before))
    return bytes(data), _stamp(before)


def _completed(tree, output, request, result, run_id, instance):
    manifest_raw, manifest_stamp = _evidence_file(tree, output / 'private-manifest.json', 65536)
    manifest = _parse(manifest_raw)
    _require(type(manifest) is dict and set(manifest) == _MANIFEST_KEYS
             and type(manifest['schema_version']) is int and manifest['schema_version'] == 1
             and manifest['kind'] == 'private_rf_signal_scenario_manifest'
             and manifest['complete'] is True and _canonical(manifest['request']) == _canonical(request)
             and manifest['catalog_sha256'] == _CATALOG_SHA and manifest['engine_sha256'] == _ENGINE_SHA
             and type(manifest['topology_sha256']) is str
             and re.fullmatch('[0-9a-f]{64}', manifest['topology_sha256']) is not None
             and type(manifest['files']) is list and len(manifest['files']) == 3)
    rows = {}
    for row in manifest['files']:
        _require(type(row) is dict and set(row) == {'path', 'bytes', 'sha256', 'visibility'}
                 and type(row['path']) is str and row['path'] in _FILES and row['path'] not in rows
                 and type(row['bytes']) is int and row['bytes'] >= 0
                 and type(row['sha256']) is str and re.fullmatch('[0-9a-f]{64}', row['sha256']) is not None
                 and row['visibility'] == _FILES[row['path']][1])
        rows[row['path']] = row
    checked, public_raw = {output / 'private-manifest.json': manifest_stamp}, None
    for relative, (limit, _) in _FILES.items():
        raw, checked[output / relative] = _evidence_file(tree, output / relative, limit)
        _require((len(raw), _sha(raw)) == (rows[relative]['bytes'], rows[relative]['sha256']))
        if relative == 'public-result.json':
            public_raw = raw
    _require(_canonical(_parse(public_raw)) == _canonical(result))
    stored = _journal.read_operator_journal(output / 'operator/events.jsonl')
    header = stored['header']
    _require(stored['complete'] is True and stored['unresolved_request_ids'] == []
             and stored['integrity']['status'] == 'verified'
             and stored['integrity']['file_sha256'] == rows['operator/events.jsonl']['sha256']
             and header['run_id'] == run_id and header['runtime_instance_id'] == instance
             and header['provenance']['catalog_sha256'] == _CATALOG_SHA
             and header['provenance']['engine_sha256'] == _ENGINE_SHA
             and header['provenance']['topology_sha256'] == manifest['topology_sha256'])
    observations = [event for event in stored['events'] if event['type'] == 'observation']
    _require(bool(observations) and result['assessment']['evidence_refs'] == [observations[-1]['event_id']])
    meter = observations[-1]['payload']['observation']['devices']['meter']['values']['outputs'].get('measurement')
    measurement = None
    if meter is not None:
        _require(type(meter) is dict and type(meter['value']) in (int, float)
                 and math.isfinite(meter['value']) and meter['unit'] == 'dBm'
                 and meter['quantity'] in ('on_average', 'time_average', 'peak'))
        measurement = dict(value=meter['value'], unit=meter['unit'], quantity=meter['quantity'],
                           reference_plane=result['declared_setup']['reference_plane'])
    for path, stamp in checked.items():
        _require(_stamp(tree.file_stat(path)) == stamp)
    return measurement


def _summary(request, run_id, output, result, measurement, complete):
    goal = (complete and result['assessment']['verdict'] == 'pass' and measurement is not None
            and result['report']['termination']['policy_claim'] == 'completed')
    value = dict(schema_version=1, kind='virtual_rf_signal_cli_result', request=request, run_id=run_id,
                 status=result['status'], assessment=result['assessment'], measurement=measurement,
                 measurement_goal_succeeded=goal, output=output, manifest_verified=complete,
                 verification=result['verification'], execution_authorized=False, rerun_authorized=False,
                 error_code=result['error_code'])
    raw = _json(value) + b'\n'
    _require(len(raw) <= 8192)
    return raw


def main(argv=None) -> int:
    """Return a CLI status without replacing or closing caller streams."""
    backend, code, status = None, None, 0
    phase = 'rf_signal_cli_invalid_argument'
    try:
        arguments = sys.argv[1:] if argv is None else argv
        if (type(arguments) in (list, tuple) and len(arguments) == 1
                and type(arguments[0]) is str and arguments[0] == '--help'):
            phase = 'rf_signal_cli_output_failed'
            _write(sys.stdout, _HELP.encode('utf-8'))
            return 0
        request, name = _arguments(arguments)
        root = _root()
        phase = 'rf_signal_cli_unavailable'
        backend = _native._WindowsIO()
        phase = 'rf_signal_cli_output_invalid'
        tree = _native._Tree(root, backend)
        namespace = root / '.local/rf-signal-runs'
        output = namespace / name
        tree.directory(namespace, missing_ok=True)
        _absent(tree, output)
        phase = 'rf_signal_cli_unavailable'
        inputs = _inputs(tree)
        loaded = _catalog.load_catalog(root / _CATALOG_PATH, max_bytes=1048576)
        canonical = _canonical(loaded)
        if len(canonical) != 56970 or _sha(canonical) != _CATALOG_SHA:
            _fail('input_changed')
        if _source(tree, _CATALOG_PATH)[1] != inputs[_CATALOG_PATH]:
            _fail('input_changed')
        phase = 'rf_signal_cli_output_invalid'
        _identities(tree)
        tree.directory(namespace, create=True)
        _absent(tree, output)
        phase = 'rf_signal_cli_unavailable'
        run_id, instance = str(uuid.uuid4()), str(uuid.uuid4())
        _require(run_id != instance)
        returned = _scenario.run_rf_signal_scenario(loaded, request, output,
                                                    run_id=run_id, runtime_instance_id=instance)
        phase = 'rf_signal_cli_input_changed'
        _identities(tree)
        if _inputs(tree) != inputs:
            _fail('input_changed')
        phase = 'rf_signal_cli_unavailable'
        result = _returned(returned, request, run_id, instance)
        complete, measurement = False, None
        if result['status'] == 'executed':
            phase = 'rf_signal_cli_output_failed'
            measurement = _completed(tree, output, request, result, run_id, instance)
            complete = True
        phase = 'rf_signal_cli_input_changed'
        _identities(tree)
        if _inputs(tree) != inputs:
            _fail('input_changed')
        phase = 'rf_signal_cli_output_failed'
        raw = _summary(request, run_id, output.relative_to(root).as_posix(), result, measurement, complete)
        status = 0 if complete and result['assessment']['verdict'] == 'pass' else 1
        _write(sys.stdout, raw)
    except KeyboardInterrupt:
        code = 'rf_signal_cli_interrupted'
    except _Failure as error:
        code = error.args[0]
    except Exception:
        code = phase
    finally:
        if backend is not None:
            try:
                backend.close()
            except Exception:
                if code is None and status == 0:
                    code = 'rf_signal_cli_unavailable'
    if code is not None:
        status = (130 if code == 'rf_signal_cli_interrupted'
                  else 2 if code in ('rf_signal_cli_invalid_argument', 'rf_signal_cli_output_invalid') else 1)
        try:
            _write(sys.stderr, _json({'error': {'code': code}}) + b'\n')
        except Exception:
            pass
    return status


def _process_main():
    """Configure/finalize only this process, retaining the first failure status."""
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
            _write(sys.stderr, _json({'error': {'code': 'rf_signal_cli_output_failed'}}) + b'\n')
        except Exception:
            pass
    for stream in (sys.stdout, sys.stderr):
        if stream is None:
            continue
        try:
            stream.flush()
        except Exception:
            if status == 0:
                status = 1
                try:
                    _write(sys.stderr, _json({'error': {'code': 'rf_signal_cli_output_failed'}}) + b'\n')
                except Exception:
                    pass
            # Avoid Python shutdown replacing our status with flush-error exit 120.
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

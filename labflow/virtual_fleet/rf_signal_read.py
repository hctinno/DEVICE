"""Read one stored synthetic RF attempt; never execute or reassess one."""
import hashlib
import json
import math
import ntpath
import os
from pathlib import Path
import re
import stat

from .. import control_packet_prepare as _native
from . import journal as _journal


_PREFIX = 'rf_signal_read_'
_CODES = frozenset(_PREFIX + code for code in (
    'invalid_argument', 'path_invalid', 'not_found', 'input_changed', 'evidence_invalid', 'unavailable'))
_SCENARIOS = ('pulsed_on_mean', 'pulsed_time_mean', 'pulsed_peak', 'cw_peak',
              'shifted_frequency', 'sensor_uncalibrated', 'meter_frequency_conflict')
_ENGINE = (
    '__init__.py', '__main__.py', 'catalog.py', 'core.py', 'evaluation.py', 'facility.py',
    'frequency_psd.py', 'frequency_psd_max.py', 'frequency_source.py', 'harness.py',
    'harness_check.py', 'instruments.py', 'integration.py', 'journal.py', 'method_adapter.py',
    'policies.py', 'rf.py', 'spectrum_capture.py', 'spectrum_math.py')
_ENGINE_SHA = '7816f87dcf8aa648d628935493f74dee3a54f993ba2bae87f9a1e102a8b4ccab'
# Live source pins and the generating engine of a stored run are separate checks.
_RECORDED_ENGINE_SHAS = frozenset((_ENGINE_SHA,
    '9b128c2e397efffd118a0be05b856d489b6da7ba96b808acc369dc77d3780c42'))
_CATALOG_SHA = '6f27b5d9ac3d3805b7f198dc0d186865cbfdcaf489d4bceba0572f99709313ff'
_HELPER_SHA = '8cb516b60caf0f0c4655649415cc37fce4e47318c74f6916985756c2b97c3fa7'
_FILES = {'private-manifest.json': 65536, 'public-result.json': 327680,
          'operator/events.jsonl': 33554432, 'private/author.json': 1048576, 'failure.json': 65536}
_ROWS = {'public-result.json': 'operator', 'operator/events.jsonl': 'operator',
         'private/author.json': 'evaluator_private'}
_FLAGS = dict(data_origin='authored_synthetic', execution_mode='synthetic_virtual_execution', synthetic=True,
              hardware_verified=False, physical_verified=False, ai_model_called=False,
              normative_compliance_verified=False, method_approval='not_assessed',
              regulatory_scope_complete=False, waveform_implemented=False)
_PARENT_CODES = frozenset('rf_signal_scenario_' + code for code in (
    'invalid_request', 'unsupported_catalog', 'output_unavailable',
    'execution_incomplete', 'evidence_invalid', 'evidence_unavailable'))
_ASSESSMENT = set('status verdict evaluator_id evidence_refs summary_code'.split())
_OUTER = set('schema_version kind scenario_id status declared_setup report assessment artifacts error_code verification'.split())
_REPORT = set('schema_version kind run_id runtime_instance_id synthetic hardware_verified ai_model_called '
              'policy termination task_outcome cleanup usage evidence unresolved_request_ids assessment'.split())
_MANIFEST = set('schema_version kind complete request catalog_sha256 topology_sha256 engine_sha256 files'.split())
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z', re.ASCII)
_SHA = re.compile(r'[0-9a-f]{64}\Z', re.ASCII)


class RfSignalReadError(ValueError):
    """A fixed public code, without supplier exception text or paths."""
    def __init__(self, code):
        self.code = code if type(code) is str and code in _CODES else _PREFIX + 'unavailable'
        super().__init__(self.code)


class _Invalid(ValueError):
    pass


def _fail(code):
    raise RfSignalReadError(_PREFIX + code) from None


def _require(condition):
    if not condition:
        raise _Invalid()


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(',', ':')).encode('utf-8')


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _stamp(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_mode


def _root():
    value = __file__
    tail = ntpath.splitdrive(value)[1]
    if (not Path(value).is_absolute() or value.startswith(('\\\\', '//')) or re.search(r'[\\/]{2}', tail)
            or any(not _native._valid_segment(part) for part in re.split(r'[\\/]', tail) if part)):
        _fail('path_invalid')
    return _native._local_path(str(Path(value).absolute().parents[2]))


def _identities(tree):
    for path, identity in tuple(tree.directories.items()):
        held = tree.backend.info(tree.backend.directories[path], directory=True)
        current = held if path == Path(path.anchor) else tree.backend.stat_file(path)
        if (not stat.S_ISDIR(current.st_mode)
                or (held.st_dev, held.st_ino) != identity or (current.st_dev, current.st_ino) != identity):
            _fail('input_changed')


def _source(tree, path):
    tree.directory(path.parent)
    before = tree.file_stat(path)
    with path.open('rb') as stream:
        if _stamp(os.fstat(stream.fileno())) != _stamp(before):
            _fail('input_changed')
        raw = stream.read(1048577)
    after = tree.file_stat(path)
    if len(raw) > 1048576 or _stamp(before) != _stamp(after):
        _fail('input_changed')
    return raw, (_stamp(after), _sha(raw))


def _sources(tree):
    result, engine = {}, hashlib.sha256()
    for name in _ENGINE:
        path = tree.root / 'labflow/virtual_fleet' / name
        raw, result[path] = _source(tree, path)
        engine.update(name.encode('utf-8') + b'\0' + raw.replace(b'\r\n', b'\n') + b'\0')
    if engine.hexdigest() != _ENGINE_SHA:
        _fail('input_changed')
    path = tree.root / 'labflow/control_packet_prepare.py'
    raw, result[path] = _source(tree, path)
    raw = raw.replace(b'\r\n', b'\n')
    if len(raw) != 29100 or _sha(raw) != _HELPER_SHA:
        _fail('input_changed')
    return result


def _read(descriptor, limit):
    result = bytearray()
    while len(result) <= limit:
        raw = os.read(descriptor, min(65536, limit + 1 - len(result)))
        if not raw:
            break
        result.extend(raw)
    return bytes(result)


def _files(tree, folder):
    """Pin this profile's fixed existing files; record absences without creating."""
    files = {}
    for name, limit in _FILES.items():
        path = folder / name
        try:
            tree.directory(path.parent)
            info = tree.file_stat(path)
        except FileNotFoundError:
            files[name] = None
            continue
        descriptor = tree.backend.open_read(path, pin=True)
        if _stamp(tree.backend.info(descriptor, directory=False)) != _stamp(info):
            _fail('input_changed')
        raw = _read(descriptor, limit) if info.st_size <= limit else None
        files[name] = dict(stamp=_stamp(info), descriptor=descriptor, raw=raw,
                           oversized=raw is None or len(raw) > limit)
    return files


def _unchanged(tree, folder, files):
    _identities(tree)
    for name, before in files.items():
        path = folder / name
        try:
            tree.directory(path.parent)
            after = tree.file_stat(path)
        except FileNotFoundError:
            if before is not None:
                _fail('input_changed')
            continue
        if before is None or _stamp(after) != before['stamp']:
            _fail('input_changed')
        descriptor = before['descriptor']
        if _stamp(tree.backend.info(descriptor, directory=False)) != before['stamp']:
            _fail('input_changed')
        if not before['oversized']:
            os.lseek(descriptor, 0, os.SEEK_SET)
            if _read(descriptor, _FILES[name]) != before['raw']:
                _fail('input_changed')
    _identities(tree)


def _parse(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            _require(key not in result)
            result[key] = value
        return result
    def constant(_):
        raise _Invalid()
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=unique, parse_constant=constant)
    nodes = 0
    def bounded(item, depth=0):
        nonlocal nodes
        nodes += 1
        _require(depth <= 20 and nodes <= 16384)
        if type(item) is dict:
            for key, val in item.items():
                _require(type(key) is str and len(key) <= 16384)
                key.encode('utf-8')
                bounded(val, depth + 1)
        elif type(item) is list:
            for val in item: bounded(val, depth + 1)
        else:
            _require(item is None or type(item) in (bool, int, float, str))
            if type(item) is str:
                _require(len(item) <= 16384)
                item.encode('utf-8')
            if type(item) is float: _require(math.isfinite(item))
    bounded(value)
    return value


def _keys(value, expected):
    _require(type(value) is dict and set(value) == expected)


def _identifier(value):
    return type(value) is str and _ID.fullmatch(value) is not None


def _hash(value):
    return type(value) is str and _SHA.fullmatch(value) is not None


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _manifest(value):
    _keys(value, _MANIFEST)
    _require(type(value['schema_version']) is int and value['schema_version'] == 1
             and value['kind'] == 'private_rf_signal_scenario_manifest' and value['complete'] is True
             and _hash(value['engine_sha256']) and value['engine_sha256'] in _RECORDED_ENGINE_SHAS
             and value['catalog_sha256'] == _CATALOG_SHA
             and _hash(value['topology_sha256']))
    request = value['request']
    _keys(request, {'schema_version', 'scenario_id', 'seed'})
    _require(type(request['schema_version']) is int and request['schema_version'] == 1
             and type(request['scenario_id']) is str and request['scenario_id'] in _SCENARIOS
             and type(request['seed']) is int and 0 <= request['seed'] <= 2147483647)
    _require(type(value['files']) is list and len(value['files']) == 3)
    paths = set()
    for row in value['files']:
        _keys(row, {'path', 'bytes', 'sha256', 'visibility'})
        _require(type(row['path']) is str and row['path'] in _ROWS and row['path'] not in paths
                 and type(row['bytes']) is int and 0 <= row['bytes'] <= _FILES[row['path']]
                 and _hash(row['sha256']) and row['visibility'] == _ROWS[row['path']])
        paths.add(row['path'])
    return value


def _outer(value):
    _keys(value, _OUTER)
    _require(type(value['schema_version']) is int and value['schema_version'] == 1
             and value['kind'] == 'virtual_rf_signal_scenario' and value['status'] == 'executed'
             and type(value['scenario_id']) is str and value['scenario_id'] in _SCENARIOS
             and value['error_code'] is None and _json(value['verification']) == _json(_FLAGS))
    declared = value['declared_setup']
    _keys(declared, {'source_signal', 'sensor', 'meter', 'reference_plane', 'basis'})
    _require(declared['reference_plane'] == 'sensor_input' and declared['basis'] == 'declared_synthetic_policy')
    _keys(declared['source_signal'], set('frequency_hz power_dbm bandwidth_hz duty_cycle crest_factor_db modulation'.split()))
    _require(all(_number(val) for key, val in declared['source_signal'].items() if key != 'modulation')
             and type(declared['source_signal']['modulation']) is str)
    _keys(declared['sensor'], {'calibration_valid', 'acquisition_policy'})
    _require(type(declared['sensor']['calibration_valid']) is bool and declared['sensor']['acquisition_policy'] == 'triggered')
    _keys(declared['meter'], {'frequency_hz', 'measurement_mode', 'unit'})
    _require(_number(declared['meter']['frequency_hz']) and declared['meter']['frequency_hz'] > 0
             and declared['meter']['measurement_mode'] in ('on_average', 'time_average', 'peak')
             and declared['meter']['unit'] == 'dBm')
    report = value['report']
    _keys(report, _REPORT)
    _require(type(report['schema_version']) is int and report['schema_version'] == 1
             and report['kind'] == 'virtual_fleet_harness_result' and report['synthetic'] is True
             and report['hardware_verified'] is False and report['ai_model_called'] is False
             and _identifier(report['run_id']) and _identifier(report['runtime_instance_id'])
             and report['run_id'] != report['runtime_instance_id']
             and report['policy'] == dict(kind='fixture', id='rf_signal_scenario_v1')
             and report['task_outcome'] == 'not_assessed'
             and report['cleanup'] == dict(status='not_assessed', evidence_refs=[]))
    _keys(report['termination'], {'reason', 'policy_claim'})
    _require(report['termination']['reason'] == 'policy_stop'
             and report['termination']['policy_claim'] in ('completed', 'blocked', 'failed', 'unsupported'))
    _keys(report['usage'], set('decisions logical_requests transport_retries tick_delta reserved_ticks elapsed_ms'.split()))
    _require(all(_number(v) and v >= 0 if k == 'elapsed_ms' else type(v) is int and v >= 0
                 for k, v in report['usage'].items()))
    _keys(report['evidence'], {'measurement_refs', 'operator_transcript_ref'})
    _require(type(report['evidence']['measurement_refs']) is list
             and all(_identifier(ref) for ref in report['evidence']['measurement_refs'])
             and report['evidence']['operator_transcript_ref'] == 'artifact:operator_events'
             and report['unresolved_request_ids'] == [] and report['usage']['reserved_ticks'] == 0
             and report['assessment'] == dict(status='not_assessed', verdict=None, evaluator_id=None,
                                               evidence_refs=[], summary_code=None))
    assessment = value['assessment']
    _keys(assessment, _ASSESSMENT)
    _require(assessment['status'] == 'completed' and assessment['verdict'] in ('pass', 'fail')
             and assessment['evaluator_id'] == 'rf_signal_scenario_v1'
             and type(assessment['evidence_refs']) is list and len(assessment['evidence_refs']) == 1
             and _identifier(assessment['evidence_refs'][0])
             and assessment['summary_code'] in ('observed_signal_satisfied', 'expected_sensor_blocked',
                                                'expected_meter_frequency_conflict', 'scenario_expectation_mismatch'))
    _require(type(value['artifacts']) is list and len(value['artifacts']) == 1)
    row = value['artifacts'][0]
    _keys(row, {'path', 'bytes', 'sha256', 'visibility'})
    _require(row['path'] == 'operator/events.jsonl' and row['visibility'] == 'operator'
             and type(row['bytes']) is int and 0 <= row['bytes'] <= _FILES['operator/events.jsonl'] and _hash(row['sha256']))
    return value


def _failure(value):
    _keys(value, {'schema_version', 'kind', 'scenario_id', 'error_code', 'phase', 'dispatched'})
    _require(type(value['schema_version']) is int and value['schema_version'] == 1
             and value['kind'] == 'rf_signal_scenario_failure'
             and type(value['scenario_id']) is str and value['scenario_id'] in _SCENARIOS
             and type(value['error_code']) is str and value['error_code'] in _PARENT_CODES
             and value['phase'] in ('bootstrap', 'setup', 'harness', 'journal_close', 'artifact_write', 'evaluation')
             and (value['dispatched'] is None or value['dispatched'] is True))
    return {key: value[key] for key in ('scenario_id', 'error_code', 'phase', 'dispatched')}


def _header(stored):
    header = stored['header']
    provenance = header['provenance']
    _keys(provenance, {'runtime_origin', 'catalog_sha256', 'engine_sha256', 'topology_sha256'})
    _require(provenance['runtime_origin'] == 'preinitialized' and provenance['catalog_sha256'] == _CATALOG_SHA
             and _hash(provenance['engine_sha256']) and provenance['engine_sha256'] in _RECORDED_ENGINE_SHAS
             and _hash(provenance['topology_sha256'])
             and _identifier(header['run_id']) and _identifier(header['runtime_instance_id'])
             and header['run_id'] != header['runtime_instance_id'])


def _binding(manifest, outer, stored):
    report = outer['report']
    _require(stored['complete'] is True and stored['unresolved_request_ids'] == []
             and manifest['request']['scenario_id'] == outer['scenario_id'])
    observations = [event for event in stored['events'] if event['type'] == 'observation']
    _require(bool(observations) and outer['assessment']['evidence_refs'] == [observations[-1]['event_id']]
             and set(report['evidence']['measurement_refs']) <= {event['event_id'] for event in observations})
    observed = observations[-1]['payload']['observation']
    _keys(observed, {'tick', 'setup_revision', 'synthetic', 'hardware_verified', 'devices'})
    _require(observed['synthetic'] is True and observed['hardware_verified'] is False
             and type(observed['tick']) is int and observed['tick'] >= 0
             and type(observed['setup_revision']) is int and observed['setup_revision'] >= 0)
    _require(type(observed['devices']) is dict)
    meter = observed['devices']['meter']
    _require(type(meter) is dict and type(meter.get('values')) is dict
             and type(meter['values'].get('outputs')) is dict)
    sample = meter['values']['outputs'].get('measurement')
    measurement = None
    if sample is not None:
        _require(type(sample) is dict and _number(sample['value']) and sample['unit'] == 'dBm'
                 and sample['quantity'] == outer['declared_setup']['meter']['measurement_mode'])
        measurement = dict(value=sample['value'], unit=sample['unit'], quantity=sample['quantity'], reference_plane='sensor_input')
    assessment = outer['assessment']
    if assessment['verdict'] == 'pass':
        if measurement is None:
            expected = {'sensor_uncalibrated': 'expected_sensor_blocked',
                        'meter_frequency_conflict': 'expected_meter_frequency_conflict'}
            _require(outer['scenario_id'] in expected and assessment['summary_code'] == expected[outer['scenario_id']]
                     and report['termination']['policy_claim'] == 'blocked')
        else:
            _require(outer['scenario_id'] in _SCENARIOS[:5] and assessment['summary_code'] == 'observed_signal_satisfied'
                     and report['termination']['policy_claim'] == 'completed')
    return measurement


def _base(name):
    return dict(schema_version=1, kind='virtual_rf_signal_run_read', selection=dict(run_name=name),
                metadata=dict(request=None, run_id=None, runtime_instance_id=None, execution_status='unconfirmed'),
                storage=dict(status='incomplete', manifest_sha256=None, verified_file_count=0,
                             journal_status='absent', binding_verified=False),
                historical_assessment=None, measurement=None, measurement_goal_succeeded=False, outcome='incomplete',
                failure=None, verification=dict(saved=None, current_scope='partial_metadata_only', source_pins_verified=True,
                fresh_offline_evaluation_performed=False, producer_cli_exit_status=None),
                execution_authorized=False, rerun_authorized=False, error_code=None)


def _content(name, files, stored, journal_invalid):
    result = _base(name)
    invalid = journal_invalid or any(row is not None and row['oversized'] for row in files.values())
    parsed = {}
    for filename, validate in (('private-manifest.json', _manifest), ('public-result.json', _outer), ('failure.json', _failure)):
        row = files[filename]
        if row is None or row['oversized']:
            parsed[filename] = None
            continue
        try:
            parsed[filename] = validate(_parse(row['raw']))
        except (ValueError, TypeError, KeyError, IndexError, OverflowError, RecursionError, UnicodeError):
            parsed[filename] = None
            invalid = True
    manifest, outer, failure = (parsed[key] for key in ('private-manifest.json', 'public-result.json', 'failure.json'))
    result['failure'] = failure
    if failure is not None:
        result['metadata']['execution_status'] = 'failed_recorded'
    if stored is not None:
        try:
            _header(stored)
            result['metadata'].update({key: stored['header'][key] for key in ('run_id', 'runtime_instance_id')})
            result['storage']['journal_status'] = 'complete' if stored['complete'] else 'partial'
        except (ValueError, TypeError, KeyError):
            stored = None
            journal_invalid = invalid = True
    if journal_invalid:
        result['storage']['journal_status'] = 'invalid'
    elif files['operator/events.jsonl'] is not None and stored is None:
        result['storage']['journal_status'] = 'not_checked'
    complete, measurement = False, None
    try:
        if manifest is not None:
            result['storage']['manifest_sha256'] = _sha(files['private-manifest.json']['raw'])
            verified = 0
            for row in manifest['files']:
                entry = files[row['path']]
                if entry is None or entry['oversized']:
                    continue
                raw = entry['raw']
                _require((len(raw), _sha(raw)) == (row['bytes'], row['sha256']))
                verified += 1
            if verified == 3:
                result['storage']['verified_file_count'] = 3
        if outer is not None and stored is not None:
            _require(all(outer['report'][key] == stored['header'][key] for key in ('run_id', 'runtime_instance_id')))
            row = outer['artifacts'][0]
            raw = files['operator/events.jsonl']['raw']
            _require((len(raw), _sha(raw)) == (row['bytes'], row['sha256']))
        if manifest is not None and outer is not None:
            _require(manifest['request']['scenario_id'] == outer['scenario_id'])
        if manifest is not None and stored is not None:
            _require(all(manifest[key] == stored['header']['provenance'][key]
                         for key in ('catalog_sha256', 'engine_sha256', 'topology_sha256')))
        if failure is not None:
            _require((outer is None or failure['scenario_id'] == outer['scenario_id'])
                     and (manifest is None or failure['scenario_id'] == manifest['request']['scenario_id']))
        if result['storage']['verified_file_count'] == 3 and outer is not None and stored is not None:
            measurement = _binding(manifest, outer, stored)
            complete = True
    except (ValueError, TypeError, KeyError, IndexError, OverflowError, RecursionError):
        invalid = True
    if invalid:
        result['storage']['status'] = result['outcome'] = 'invalid'
        result['verification']['current_scope'] = 'not_verified'
        result['error_code'] = _PREFIX + 'evidence_invalid'
    elif complete:
        result['storage'].update(status='complete_verified', binding_verified=True)
        result['metadata'].update(request=manifest['request'], execution_status='failed_recorded' if failure else 'executed')
        result['verification']['current_scope'] = 'stored_hashes_and_public_journal'
        if failure is None:
            result['historical_assessment'] = outer['assessment']
            result['measurement'] = measurement
            result['verification']['saved'] = outer['verification']
            passed = outer['assessment']['verdict'] == 'pass'
            result['measurement_goal_succeeded'] = passed and measurement is not None
            result['outcome'] = 'assessment_failed' if not passed else 'expected_blocked' if measurement is None else 'measurement_observed'
    if failure is not None and not invalid:
        result['outcome'] = 'failure_recorded'
    return result


def read_rf_signal_run(run_name, *, workspace_root=None) -> dict:
    """Return one stable, read-only storage view; never infer an unrecorded exit."""
    backend, result, code = None, None, None
    phase = 'unavailable'
    try:
        if (type(run_name) is not str or re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{0,63}', run_name, re.ASCII) is None
                or not _native._valid_segment(run_name)):
            _fail('invalid_argument')
        root = _root()
        backend = _native._WindowsIO()
        phase = 'path_invalid'
        source_tree = _native._Tree(root, backend)
        from ..managed_artifact_workspace import artifact_local_root
        local = artifact_local_root(workspace_root=workspace_root)
        phase = 'not_found'
        tree = _native._Tree(local, backend)
        folder = local / 'rf-signal-runs' / run_name
        tree.directory(folder)
        phase = 'input_changed'
        before = _sources(source_tree)
        phase = 'unavailable'
        files = _files(tree, folder)
        stored, journal_invalid, storage_error = None, False, False
        row = files['operator/events.jsonl']
        if row is not None and not row['oversized']:
            try:
                stored = _journal.read_operator_journal(folder / 'operator/events.jsonl')
                if stored['integrity']['file_sha256'] != _sha(row['raw']):
                    _fail('input_changed')
            except _journal.JournalIntegrityError:
                journal_invalid = True
            except _journal.JournalStorageError:
                storage_error = True
        result = _content(run_name, files, stored, journal_invalid)
        phase = 'input_changed'
        _unchanged(tree, folder, files)
        if _sources(source_tree) != before:
            _fail('input_changed')
        _identities(tree)
        _identities(source_tree)
        if storage_error:
            _fail('unavailable')
        if len(_json(result)) > 8192:
            _fail('evidence_invalid')
    except RfSignalReadError as error:
        code = error.code
    except _native.ControlPacketPrepareError:
        code = _PREFIX + ('input_changed' if phase == 'input_changed' else 'path_invalid')
    except FileNotFoundError:
        code = _PREFIX + phase if phase in ('not_found', 'input_changed') else _PREFIX + 'unavailable'
    except OSError as error:
        code = _PREFIX + ('path_invalid' if getattr(error, 'winerror', None) == 267 or error.errno == 20 else 'unavailable')
    except Exception:
        code = _PREFIX + ('input_changed' if phase == 'input_changed' else 'unavailable')
    finally:
        if backend is not None:
            try:
                backend.close()
            except Exception:
                if code is None and (result is None or result['error_code'] is None):
                    code = _PREFIX + 'unavailable'
    if code is not None:
        raise RfSignalReadError(code) from None
    return result

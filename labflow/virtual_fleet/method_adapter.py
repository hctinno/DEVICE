"""One explicitly synthetic sensor recipe; no case, hardware or replay backend."""

from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import re

from .catalog import load_catalog
from .evaluation import evaluate_sensor_run, prepare_sensor_trial
from .harness import FleetHarness
from .integration import get_role_actions
from .journal import OperatorJournal, read_operator_journal
from .policies import RFSensorFixturePolicy


RECIPE_ID = 'conducted_sensor_fixture_v1'
_MODEL = 'SM-A176U'
_CATALOG = Path(__file__).resolve().parents[2] / 'virtual_profiles/sm_a176u_unlicensed.json'
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z')
_SHA = re.compile(r'[0-9a-f]{64}\Z')
_REQUEST_FIELDS = {'request_id', 'intake_id', 'revision', 'readiness_fingerprint', 'recipe_id',
                   'settings', 'model', 'source_synthetic'}
_REPORT_FIELDS = {'schema_version', 'kind', 'run_id', 'runtime_instance_id', 'synthetic', 'hardware_verified',
                  'ai_model_called', 'policy', 'termination', 'task_outcome', 'cleanup', 'usage', 'evidence',
                  'unresolved_request_ids', 'assessment'}
_FLAGS = {'synthetic': True, 'hardware_verified': False, 'ai_model_called': False}
_QUANTITY = {'reference_plane': 'sensor_input', 'metric': 'on_mean_power', 'unit': 'dBm'}
_PRIVATE_FIELDS = {'author', 'author_control', 'fault', 'seed', 'truth', 'expected', 'expected_sensor_dbm',
                    'expected_values', 'comparison_tolerance_db', 'author_events', 'password', 'secret',
                    'token', 'source_path', 'file_path', 'decrypted_path', 'path', 'traceback'}


class FixtureMethodError(RuntimeError):
    """Sanitized host failure. dispatched includes synchronous virtual bootstrap."""

    def __init__(self, code, *, dispatched):
        super().__init__(code)
        self.code, self.dispatched = code, bool(dispatched)


def _identifier(value):
    if type(value) is not str or not _ID.fullmatch(value):
        raise ValueError('invalid_fixture_identifier')
    return value


def _finite(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False, indent=2) + '\n').encode('utf-8')


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(',', ':')).encode('utf-8')


def describe_fixture_method(recipe_id, *, model, settings):
    """Describe support without files, initialization, or untrusted input echo."""
    reasons = []
    if type(recipe_id) is not str or recipe_id != RECIPE_ID:
        reasons.append('unsupported_recipe')
    if type(model) is not str or model != _MODEL:
        reasons.append('unsupported_model')
    if (type(settings) is not dict or set(settings) != {'power_dbm'} or
            not _finite(settings.get('power_dbm')) or not -30 <= settings['power_dbm'] <= 20):
        reasons.append('unsupported_settings')
    result = {'schema_version': 1, 'kind': 'virtual_fixture_method', 'recipe_id': RECIPE_ID, 'model': _MODEL,
              'supported': not reasons, 'reason_codes': reasons,
              'settings': None if reasons else {'power_dbm': float(settings['power_dbm'])},
              'quantity': dict(_QUANTITY),
              'synthetic_setup': {'frequency_hz': 2.45e9, 'bandwidth_hz': 20e6, 'modulation': 'OFDM',
                                  'duty_cycle': .25, 'crest_factor_db': 3, 'attenuation_db': 10,
                                  'switch_loss_db': .5, 'coupling_db': 20,
                                  'coupling_basis': 'declared_synthetic_policy'},
              'method_approval': 'not_assessed', 'regulatory_scope_complete': False, 'resumable': False,
              **_FLAGS}
    return result


def _request(value):
    if type(value) is not dict or set(value) != _REQUEST_FIELDS:
        raise ValueError('invalid_fixture_request_fields')
    for name in ('request_id', 'intake_id'):
        _identifier(value[name])
    if type(value['revision']) is not int or value['revision'] < 1 or type(value['source_synthetic']) is not bool:
        raise ValueError('invalid_fixture_request_source')
    if type(value['readiness_fingerprint']) is not str or not _SHA.fullmatch(value['readiness_fingerprint']):
        raise ValueError('invalid_readiness_fingerprint')
    descriptor = describe_fixture_method(value['recipe_id'], model=value['model'], settings=value['settings'])
    if not descriptor['supported']:
        raise ValueError('unsupported_fixture_method')
    result = deepcopy(value)
    result['settings'] = descriptor['settings'].copy()
    return result, descriptor


class _Gate:
    def __init__(self, callback):
        if callback is not None and not callable(callback):
            raise ValueError('invalid_can_continue_callback')
        self.callback, self.denied = callback, False

    def allowed(self):
        if self.denied:
            return False
        if self.callback is None:
            return True
        try:
            allowed = self.callback() is True
        except BaseException:
            allowed = False
        self.denied = not allowed
        return allowed


class _GuardedRuntime:
    def __init__(self, runtime, gate):
        self.actual, self.gate, self.stopper = runtime, gate, None

    def _permit(self):
        if not self.gate.allowed():
            self.stopper()
            raise RuntimeError('continuation_unavailable')

    def execute(self, request_id, device_id, action, parameters):
        self._permit()
        return self.actual.execute(request_id, device_id, action, parameters)

    def advance(self, request_id, ticks):
        self._permit()
        return self.actual.advance(request_id, ticks)

    def observations(self):
        return self.actual.observations()


class _GuardedPolicy:
    policy_id = RFSensorFixturePolicy.policy_id

    def __init__(self, gate):
        self.actual, self.gate, self.stopper = RFSensorFixturePolicy(), gate, None

    def __call__(self, context):
        if not self.gate.allowed():
            self.stopper()
            return {'kind': 'stop', 'claim': 'blocked', 'reason': 'continuation_unavailable'}
        return self.actual(context)


def _write_new(path, value):
    data = _json_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        if stream.write(data) != len(data):
            raise OSError('short artifact write')
        stream.flush()
        os.fsync(stream.fileno())


def _engine_sha256():
    digest = hashlib.sha256()
    for path in sorted(Path(__file__).parent.glob('*.py')):
        digest.update(path.name.encode('utf-8') + b'\0' + path.read_bytes().replace(b'\r\n', b'\n') + b'\0')
    return digest.hexdigest()


def _artifact(output, path, kind):
    resolved = path.resolve()
    if path.is_symlink() or not resolved.is_relative_to(output.resolve()):
        raise ValueError('invalid_generated_artifact')
    raw = resolved.read_bytes()
    return {'kind': kind, 'path': str(resolved), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def _report(value, run_id, instance_id):
    def public(item):
        if type(item) is dict:
            return all(type(key) is str and key.lower() not in _PRIVATE_FIELDS and public(child)
                       for key, child in item.items())
        if type(item) is list:
            return all(public(child) for child in item)
        return True
    if (type(value) is not dict or set(value) != _REPORT_FIELDS or not public(value)
            or type(value.get('schema_version')) is not int or value['schema_version'] != 1
            or value.get('kind') != 'virtual_fleet_harness_result'
            or value.get('run_id') != run_id or value.get('runtime_instance_id') != instance_id
            or any(value.get(key) is not flag for key, flag in _FLAGS.items())):
        raise ValueError('invalid_fixture_report')
    raw = _canonical(value)
    if len(raw) > 256 * 1024:
        raise ValueError('fixture_report_size')
    return json.loads(raw)


def _graded_report(trial, report, events, run_id, instance_id):
    assessment = evaluate_sensor_run(trial, report, events)
    fields = {'status', 'verdict', 'evaluator_id', 'evidence_refs', 'summary_code'}
    if type(assessment) is not dict or set(assessment) != fields:
        raise ValueError('invalid_fixture_assessment')
    status, verdict, refs = assessment['status'], assessment['verdict'], assessment['evidence_refs']
    if (type(status) is not str or status not in {'not_assessed', 'completed', 'failed'}
            or status == 'completed' and verdict not in {'pass', 'fail', 'inconclusive'}
            or status != 'completed' and verdict is not None or type(refs) is not list):
        raise ValueError('invalid_fixture_assessment')
    observed = {event['event_id'] for event in events if event['type'] == 'observation'}
    if any(type(ref) is not str or ref not in observed for ref in refs) or len(set(refs)) != len(refs):
        raise ValueError('invalid_assessment_evidence')
    candidate = deepcopy(report)
    candidate['assessment'] = deepcopy(assessment)
    candidate['evidence']['measurement_refs'] = []
    if (candidate['termination'].get('policy_claim') == 'completed'
            and status == 'completed' and verdict == 'pass'):
        if not refs:
            raise ValueError('missing_measurement_evidence')
        candidate['evidence']['measurement_refs'] = list(refs)
    return _report(candidate, run_id, instance_id)


def _catalog_bytes():
    with _CATALOG.open('rb') as stream:
        raw = stream.read(4 * 1024 * 1024 + 1)
    if len(raw) > 4 * 1024 * 1024:
        raise ValueError('catalog_size_limit')
    return raw


def _manifest(output, request, run_id, instance_id, *, complete):
    files = []
    for name, visibility in [('public-result.json', 'operator'), ('operator/events.jsonl', 'operator'),
                              ('private/author.json', 'evaluator_private'), ('failure.json', 'host_private')]:
        path = output / name
        if path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(output.resolve()):
            raw = path.read_bytes()
            files.append({'path': name, 'sha256': hashlib.sha256(raw).hexdigest(),
                          'bytes': len(raw), 'visibility': visibility})
    return {'schema_version': 1, 'kind': 'private_fixture_method_manifest', 'run_id': run_id,
            'runtime_instance_id': instance_id, 'request': request, 'files': files,
            'evidence_written': complete, 'runtime_origin': 'preinitialized', 'resumable': False,
            'scope': 'artifact hashes; no signature or hardware attestation', **_FLAGS}


def _retain_failure(output, request, run_id, instance_id, trial, report, code, dispatched):
    candidates = [(output / 'failure.json', {'schema_version': 1, 'code': code, 'run_id': run_id,
                   'runtime_instance_id': instance_id, 'dispatched': dispatched, 'resumable': False, **_FLAGS})]
    if trial is not None:
        try:
            candidates.append((output / 'private/author.json', trial.author_record()))
        except BaseException:
            pass
    if report is not None:
        try:
            candidates.append((output / 'public-result.json', _report(report, run_id, instance_id)))
        except BaseException:
            pass
    for path, payload in candidates:
        try:
            if not path.exists() and not path.is_symlink():
                _write_new(path, payload)
        except BaseException:
            pass
    try:
        path = output / 'private-manifest.json'
        if not path.exists() and not path.is_symlink():
            _write_new(path, _manifest(output, request, run_id, instance_id, complete=False))
    except BaseException:
        pass


def run_fixture_method(request, output_dir, *, run_id, runtime_instance_id, can_continue=None):
    """Run one normal synthetic trial; returned artifact paths are host-only."""
    request, descriptor = _request(request)
    run_id, runtime_instance_id = _identifier(run_id), _identifier(runtime_instance_id)
    gate = _Gate(can_continue)
    if not gate.allowed():
        raise FixtureMethodError('continuation_denied', dispatched=False)
    output = Path(output_dir).absolute()
    if output.exists() or output.is_symlink():
        raise FileExistsError('fixture output directory already exists')
    try:
        catalog_bytes = _catalog_bytes()
        catalog = load_catalog(_CATALOG)
        if _catalog_bytes() != catalog_bytes or _canonical(catalog) != _canonical(json.loads(catalog_bytes.decode('utf-8'))):
            raise ValueError('catalog_changed_during_load')
        actions = get_role_actions()
    except Exception:
        raise FixtureMethodError('fixture_inputs_unavailable', dispatched=False) from None
    try:
        output.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        raise FileExistsError('fixture output directory already exists') from None
    except OSError:
        raise FixtureMethodError('output_unavailable', dispatched=False) from None
    trial = journal = report = None
    dispatched = False
    code = 'initialization_failed'
    try:
        dispatched = True
        trial = prepare_sensor_trial(catalog, condition='normal', seed=0,
                                     power_dbm=request['settings']['power_dbm'])
        trial.runtime_instance_id = runtime_instance_id
        after_initialization = gate.allowed()
        topology = deepcopy(trial.topology)
        provenance = {'runtime_origin': 'preinitialized', 'catalog_sha256': hashlib.sha256(catalog_bytes).hexdigest(),
                      'topology_sha256': hashlib.sha256(_canonical(topology)).hexdigest(),
                      'engine_sha256': _engine_sha256(), 'recipe_id': RECIPE_ID, 'model': _MODEL,
                      'settings': deepcopy(request['settings']), 'topology': topology,
                      'quantity': descriptor['quantity'], 'synthetic_setup': descriptor['synthetic_setup']}
        code = 'operator_evidence_failed'
        journal_path = output / 'operator/events.jsonl'
        journal_path.parent.mkdir(parents=True, exist_ok=False)
        journal = OperatorJournal(journal_path, run_id=run_id, runtime_instance_id=runtime_instance_id,
                                  provenance=provenance)
        guarded_runtime, policy = _GuardedRuntime(trial.runtime, gate), _GuardedPolicy(gate)
        code = 'harness_failed'
        harness = FleetHarness(guarded_runtime, policy, goal=trial.goal, catalog=trial.catalog,
                               topology=topology, role_actions=actions, event_sink=journal,
                               run_id=run_id, runtime_instance_id=runtime_instance_id)
        guarded_runtime.stopper = policy.stopper = harness.stop
        if not after_initialization:
            harness.stop()
        report = _report(harness.run(), run_id, runtime_instance_id)
        code = 'operator_evidence_failed'
        journal.close()
        journal = None
        code = 'evaluation_failed'
        report = _graded_report(trial, report, harness.events(), run_id, runtime_instance_id)
        code = 'operator_evidence_inconsistent'
        stored = read_operator_journal(journal_path)
        if (stored['header']['run_id'] != run_id or stored['header']['runtime_instance_id'] != runtime_instance_id
                or _canonical(stored['events']) != _canonical(harness.events())
                or sorted(stored['unresolved_request_ids']) != sorted(report['unresolved_request_ids'])
                or not stored['complete'] and not report['unresolved_request_ids']):
            raise ValueError('operator_evidence_mismatch')
        code = 'artifact_write_failed'
        _write_new(output / 'private/author.json', trial.author_record())
        _write_new(output / 'public-result.json', report)
        artifacts = [_artifact(output, output / 'public-result.json', 'result'),
                     _artifact(output, journal_path, 'operator_journal')]
        _write_new(output / 'private-manifest.json', _manifest(output, request, run_id, runtime_instance_id, complete=True))
        return {'report': deepcopy(report), 'artifacts': artifacts}
    except BaseException:
        if journal is not None:
            try:
                journal.close()
            except BaseException:
                pass
        _retain_failure(output, request, run_id, runtime_instance_id, trial, report, code, dispatched)
        raise FixtureMethodError(code, dispatched=dispatched) from None

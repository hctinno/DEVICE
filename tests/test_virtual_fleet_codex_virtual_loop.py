"""Persistent real virtual core + genuine producer with only native child replaced."""
import copy
from contextlib import ExitStack
import hashlib
import importlib
import importlib.util
import inspect
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
import uuid
from unittest.mock import patch
import zipfile

try:
    api = importlib.import_module('labflow.virtual_fleet.codex_virtual_loop')
except ModuleNotFoundError as error:
    if error.name != 'labflow.virtual_fleet.codex_virtual_loop':
        raise
    api = None

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / '.local' / 'codex-virtual-loop-fixtures' / ('run-' + uuid.uuid4().hex)
PROOF = LOCAL / 'DEV2-CONDUCTED-EXECUTION-PROVENANCE-001'
SCHEMA = json.loads((ROOT / 'docs/fcc/codex_first_decision_contract.json').read_text(encoding='utf-8'))['response_schema']['literal_utf8'].encode('utf-8')


def C(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def H(data):
    return hashlib.sha256(data).hexdigest()


class _ProofBudget:
    def __init__(self, root):
        self.root = root.resolve()
        self.files, self.reserved = {}, {}
        self.total = 0
        self.lock = threading.RLock()
        self.checkpoint()

    def path(self, path):
        path = path.resolve()
        if not path.is_relative_to(self.root):
            raise AssertionError('OWNER_PROOF_PATH_OUTSIDE_LOCAL')
        return path

    @staticmethod
    def check(count, total):
        if count > 512 or total > 33554432:
            raise AssertionError('OWNER_PROOF_ADMISSION_EXCEEDED')

    def charge(self, path, size, *, replace=False):
        self.charge_known(self.path(path), size, replace=replace)

    def charge_known(self, path, size, *, replace=False):
        with self.lock:
            previous = self.files.get(path, 0)
            size = size if replace else max(previous, size)
            total = self.total - previous + size
            self.check(len(self.files) + int(path not in self.files), total)
            self.files[path] = size
            self.total = total

    def checkpoint(self):
        with self.lock:
            observed = {}
            total = 0
            for path in self.root.rglob('*'):
                if path.is_symlink():
                    raise AssertionError('OWNER_PROOF_LINK_FORBIDDEN')
                if path.is_file():
                    size = path.stat().st_size
                    observed[path.resolve()] = size
                    total += size
                    self.check(len(observed), total)
            for path, size in self.reserved.items():
                observed[path] = max(observed.get(path, 0), size)
            total = sum(observed.values())
            self.check(len(observed), total)
            self.files, self.total = observed, total

    def reserve_native(self, path, size):
        path = self.path(path)
        with self.lock:
            self.charge(path, size)
            self.reserved[path] = size

    def settle_native(self, path):
        path = self.path(path)
        with self.lock:
            self.reserved.pop(path, None)
            if path.exists():
                self.charge(path, path.stat().st_size, replace=True)
            elif path in self.files:
                self.total -= self.files.pop(path)

    def forget_removed(self, folder):
        folder = self.path(folder)
        if folder.exists():
            return
        with self.lock:
            for path in list(self.files):
                if path.is_relative_to(folder):
                    self.total -= self.files.pop(path)
                    self.reserved.pop(path, None)


_ACCOUNTING = None


def _proof_budget():
    global _ACCOUNTING
    if _ACCOUNTING is None or _ACCOUNTING.root != LOCAL.resolve():
        _ACCOUNTING = _ProofBudget(LOCAL)
    return _ACCOUNTING


def admit(path, size):
    _proof_budget().charge(path, size)


class _Writer:
    def __init__(self, handle, path):
        self.handle = handle
        self.budget = _proof_budget()
        self.path = self.budget.path(path)

    def write(self, data):
        if type(data) is str:
            size = len(data.encode(self.handle.encoding or 'utf-8'))
            if os.name == 'nt':
                size += data.count('\n')  # Reserve Windows text newline expansion conservatively.
        else:
            size = len(data)
        self.budget.charge_known(self.path, self.handle.tell() + size)
        return self.handle.write(data)

    def __getattr__(self, name):
        return getattr(self.handle, name)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return self.handle.__exit__(*args)


class LoopTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(api, 'Assigned persistent virtual loop API is absent')
        self.stack = self.enterContext(ExitStack())
        scratch = LOCAL / 'persistent-loop-test-scratch'
        scratch.mkdir(parents=True, exist_ok=True)
        PROOF.mkdir(parents=True, exist_ok=True)
        self.stack.enter_context(patch.object(tempfile, 'tempdir', str(scratch)))
        self.stack.enter_context(patch.dict(os.environ, TMP=str(scratch), TEMP=str(scratch), PYTHONDONTWRITEBYTECODE='1'))
        original_open = Path.open
        def bounded(path, mode='r', *args, **kwargs):
            if any(x in mode for x in 'wax+'):
                admit(path, path.stat().st_size if path.exists() else 0)
                return _Writer(original_open(path, mode, *args, **kwargs), path)
            return original_open(path, mode, *args, **kwargs)
        self.stack.enter_context(patch.object(Path, 'open', bounded))
        for target in ('socket.socket.connect', 'socket.getaddrinfo'):
            self.stack.enter_context(patch(target, side_effect=AssertionError('ACTUAL_NETWORK_FORBIDDEN')))
        from tests.test_codex_cli_response import ProducerTests
        self.driver = ProducerTests('test_success_tuple_receipt_and_original_artifacts')
        self.addCleanup(self.preserve_then_cleanup)
        self.driver.setUp()
        self.catalog = self.driver.root / 'catalog.json'
        self.catalog_bytes = (ROOT / 'virtual_profiles/sm_a176u_unlicensed.json').read_bytes()
        self.catalog.write_bytes(self.catalog_bytes)
        self.options = dict(catalog_path=self.catalog, catalog_sha256=H(self.catalog_bytes), response_schema_bytes=SCHEMA,
            executable=self.driver.exe, requested_model='gpt-6.1-sol', scenario='normal',
            evidence_dir=self.driver.root / 'run-1', execution_origin='mock_subprocess')
        self.prompts, self.trials, self.evaluated, self.original_execute = [], [], [], []
        self.sequence = None
        self.producer_mode = 'normal'
        self.wrong_binding = False
        self.after_produce = None
        self.timeout_override = None
        self.runtime_fault = None
        self.observation_fault = None
        self.observation_invalid = False
        self.observation_after_tool = False
        self.invocations = 0
        self.real_produce, self.real_prepare, self.real_evaluate = api._produce, api._prepare, api._evaluate

    def preserve_then_cleanup(self):
        if not hasattr(self.driver, 'root'):
            self.driver.doCleanups()
            return
        folder = self.driver.root.resolve()
        self.assertTrue(folder.is_relative_to((LOCAL / 'persistent-loop-test-scratch').resolve()))
        PROOF.mkdir(parents=True, exist_ok=True)
        archive = PROOF / (self._testMethodName + '-' + folder.name + '.zip')
        try:
            _proof_budget().checkpoint()
            admit(archive, 0)
            with archive.open('xb') as output, zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as saved:
                for file in sorted(folder.rglob('*')):
                    if file.is_file() and not file.is_symlink():
                        saved.write(file, file.relative_to(folder).as_posix())
        except BaseException:
            # Preserve failed preparation raw, even when archive admission fails.
            self.driver.temp._finalizer.detach()
            self.driver._cleanups = [c for c in self.driver._cleanups if getattr(c[0], '__self__', None) is not self.driver.temp]
            self.driver.doCleanups()
            raise
        self.driver.doCleanups()
        _proof_budget().forget_removed(folder)

    @staticmethod
    def adaptive(prompt):
        context = json.loads(prompt['messages'][1]['content'])['request']['user_input']['public_context']
        obs, goal = context['observations'], context['goal']
        dut = obs['devices'][goal['dut_id']]
        sensor = obs['devices'][goal['sensor_id']]
        measurement = sensor['values'].get('outputs', {}).get('measurement', {})
        if (measurement.get('valid') is True and measurement.get('acquisition_tick', -1) >= goal['minimum_acquisition_tick']
                and measurement.get('acquisition_setup_revision') == obs['setup_revision']):
            return dict(kind='stop', claim='completed', reason='fresh public measurement observed')
        if dut['status'] == 'disconnected':
            return dict(kind='stop', claim='blocked', reason='public DUT disconnected')
        state = dut['values'].get('state', dut.get('state'))
        if state == 'idle':
            return dict(kind='execute', device_id=goal['dut_id'], action='start', parameters={})
        if state in {'arming', 'settling'}:
            return dict(kind='advance', ticks=1)
        sensor_state = sensor['values'].get('state', sensor.get('state'))
        if sensor_state in {'measuring', 'acquiring', 'pending', 'running'}:
            return dict(kind='advance', ticks=1)
        return dict(kind='execute', device_id=goal['sensor_id'], action='acquire', parameters={})

    def produce(self, prompt_bytes, schema_bytes, **kwargs):
        prompt = json.loads(prompt_bytes)
        self.prompts.append(copy.deepcopy(prompt))
        index = len(self.prompts) - 1
        proposal = copy.deepcopy(self.sequence[min(index, len(self.sequence) - 1)]) if self.sequence else self.adaptive(prompt)
        wire = dict(schema_version=1, kind='virtual_operator_response', request_sha256=prompt['binding']['request_sha256'],
                    producer=prompt['expected_producer'], proposal=proposal)
        if self.wrong_binding:
            wire['request_sha256'] = '0' * 64
        self.driver.mode = self.producer_mode
        self.driver.control.write_bytes(C(dict(mode=self.producer_mode, wire=C(wire).hex())))
        if self.timeout_override is not None:
            kwargs['timeout_seconds'] = self.timeout_override
        native = kwargs['evidence_dir'] / 'last-message.bin'
        _proof_budget().reserve_native(native, 2097153)
        try:
            response = self.real_produce(prompt_bytes, schema_bytes, **kwargs)
        except BaseException:
            if self.after_produce:
                self.after_produce()
            raise
        finally:
            _proof_budget().settle_native(native)
        if self.after_produce:
            self.after_produce()
        return response

    def call(self, **overrides):
        self.invocations += 1
        options = dict(self.options, evidence_dir=self.driver.root / ('run-' + str(self.invocations)))
        options.update(overrides)
        def prepare(*args, **kwargs):
            trial = self.real_prepare(*args, **kwargs)
            self.trials.append(trial)
            if self.runtime_fault is not None:
                fault = self.runtime_fault
                def execute(*args, **kwargs):
                    raise fault
                trial.runtime.execute = execute
            if self.observation_fault is not None or self.observation_invalid:
                observed = trial.runtime.observations
                executed = trial.runtime.execute
                armed = [not self.observation_after_tool]
                fault, invalid = self.observation_fault, self.observation_invalid
                def execute(*args, **kwargs):
                    result = executed(*args, **kwargs)
                    armed[0] = True
                    return result
                def observations():
                    if armed[0]:
                        if invalid:
                            return {}
                        raise fault
                    return observed()
                trial.runtime.execute = execute
                trial.runtime.observations = observations
            self.original_execute.append(trial.runtime.execute)
            return trial
        def evaluate(trial, result, events):
            self.evaluated.append(trial)
            return self.real_evaluate(trial, result, events)
        with patch.object(api, '_prepare', side_effect=prepare), patch.object(api, '_evaluate', side_effect=evaluate), \
                patch.object(api, '_produce', side_effect=self.produce), \
                patch('labflow.codex_cli_response.subprocess.Popen', side_effect=self.driver.spawn):
            return api.run_codex_virtual_loop(**options)

    def failure(self, suffix, **kwargs):
        code = suffix if suffix.startswith(('codex_cli_response_', 'model_operator_boundary_')) else 'operator_virtual_loop_' + suffix
        with self.assertRaises(api.CodexVirtualLoopError) as got:
            self.call(**kwargs)
        error = got.exception
        self.assertEqual((error.code, str(error), error.args), (code, code, (code,)))
        self.assertIsNone(error.__cause__)
        self.assertIsNone(error.__context__)
        self.assertNotIn('FAKE_SECRET', str(error))
        if error.receipt:
            self.assertEqual(error.receipt['failure']['code'], code)
        return error

    def shape(self, r):
        self.assertEqual(set(r), set('schema_version kind run_id status failure declaration budget steps termination evidence_assessment execution cleanup artifacts verification'.split()))
        self.assertEqual(r['kind'], 'codex_virtual_loop_result')
        self.assertEqual(r['execution']['origin_declaration'], 'mock_subprocess')
        self.assertFalse(r['execution']['origin_authenticated'])
        self.assertIsNone(r['execution']['ai_model_called'])
        self.assertIsNone(r['evidence_assessment']['score'])
        self.assertLessEqual(len(r['steps']), 8)
        self.assertLessEqual(len(C(r)), 262144)
        for step in r['steps']:
            self.assertEqual(set(step), set('index binding before after producer wire dispatch stage status failure artifacts verification'.split()))

    def test_public_signature_and_exports(self):
        self.assertEqual(api.__all__, ['run_codex_virtual_loop', 'CodexVirtualLoopError'])
        signature = inspect.signature(api.run_codex_virtual_loop)
        self.assertEqual(list(signature.parameters), ['catalog_path', 'catalog_sha256', 'response_schema_bytes', 'executable', 'requested_model', 'scenario', 'evidence_dir', 'execution_origin', 'cancel_event', 'source_settings', 'plan_binding', 'quantity', 'evidence_reservation', 'model_process_limit', 'wall_seconds_limit'])
        self.assertIsNone(signature.parameters['source_settings'].default)
        self.assertIsNone(signature.parameters['plan_binding'].default)
        self.assertIsNone(signature.parameters['quantity'].default)
        self.assertIsNone(signature.parameters['evidence_reservation'].default)
        self.assertTrue(all(p.kind == inspect.Parameter.KEYWORD_ONLY for p in signature.parameters.values()))

    def test_proof_admission_uses_only_this_execution_namespace(self):
        self.assertNotEqual(LOCAL, ROOT / '.local')
        original_rglob = Path.rglob
        visited = []
        def scoped(path, pattern, *args, **kwargs):
            self.assertNotEqual(path, ROOT / '.local', 'Historical root evidence must never be scanned')
            visited.append(path)
            return original_rglob(path, pattern, *args, **kwargs)
        with patch.object(Path, 'rglob', scoped):
            admit(PROOF / 'namespace-admission-probe', 1)
            self.assertEqual(visited, [])
            _proof_budget().checkpoint()
        self.assertEqual(visited, [LOCAL])
        with self.assertRaisesRegex(AssertionError, 'OWNER_PROOF_ADMISSION_EXCEEDED'):
            admit(PROOF / 'namespace-size-probe', 33554433)
        spec = importlib.util.spec_from_file_location('second_pure_loop_fixture_import', Path(__file__))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertNotEqual(module.LOCAL, LOCAL)

    def test_proof_write_accounting_and_native_reservation(self):
        budget = _proof_budget()
        path = self.driver.root / 'accounted-writes.bin'
        text = self.driver.root / 'accounted-text.txt'
        native = self.driver.root / 'reserved-native.bin'
        with patch.object(Path, 'rglob', side_effect=AssertionError('HOTPATH_INVENTORY_FORBIDDEN')):
            with path.open('xb') as stream:
                stream.write(b'a' * 31); stream.write(b'b' * 17)
                stream.seek(0); stream.write(b'c')
            self.assertEqual(budget.files[path.resolve()], 48)
            with text.open('w', encoding='utf-8') as stream:
                stream.write('a\nb\n')
            self.assertGreaterEqual(budget.files[text.resolve()], text.stat().st_size)
            budget.reserve_native(native, 2097153)
            self.assertEqual(budget.files[native.resolve()], 2097153)
            with open(native, 'xb') as stream:
                stream.write(b'child')
            budget.settle_native(native)
            self.assertEqual(budget.files[native.resolve()], 5)
        with self.assertRaisesRegex(AssertionError, 'OWNER_PROOF_ADMISSION_EXCEEDED'):
            budget.reserve_native(self.driver.root / 'oversize-native.bin', 33554433)
        fake = {LOCAL / ('reserved-' + str(i)): 0 for i in range(512)}
        with patch.object(budget, 'files', fake), patch.object(budget, 'total', 0):
            with self.assertRaisesRegex(AssertionError, 'OWNER_PROOF_ADMISSION_EXCEEDED'):
                admit(PROOF / 'file513', 0)

    def declared_source(self):
        return dict(frequency_hz=2.412e9, power_dbm=11, bandwidth_hz=20e6,
                    duty_cycle=.5, modulation='OFDM', crest_factor_db=4)

    def test_source_settings_rejected_before_side_effects(self):
        class DictSubclass(dict):
            pass
        class IntSubclass(int):
            pass
        source = self.declared_source()
        invalid = [True, [], 'source', DictSubclass(source), {},
                   {**source, 'extra': 1}, {k: v for k, v in source.items() if k != 'power_dbm'}]
        for key in ('frequency_hz', 'power_dbm', 'bandwidth_hz', 'duty_cycle', 'crest_factor_db'):
            invalid.extend({**source, key: value} for value in (True, '11', float('nan'), float('inf'), 10**400, IntSubclass(11)))
        invalid.extend({**source, **change} for change in [dict(frequency_hz=0), dict(bandwidth_hz=0),
            dict(frequency_hz=1, bandwidth_hz=3), dict(frequency_hz=1.7e308, bandwidth_hz=1.7e308),
            dict(duty_cycle=0), dict(duty_cycle=1.01), dict(crest_factor_db=-1),
            dict(modulation=None), dict(modulation=' '), dict(modulation='a'*201), dict(modulation='\ud800')])
        for value in invalid:
            with self.subTest(value_type=type(value).__name__):
                e = self.failure('invalid_input', source_settings=value)
                self.assertIsNone(e.receipt)
                self.assertFalse((self.driver.root / ('run-' + str(self.invocations))).exists())
        self.assertEqual(self.trials, [])
        self.assertEqual(self.driver.calls, [])

    def test_source_settings_none_preserves_factory_and_shape(self):
        calls = []
        original = self.real_prepare
        def prepare(catalog, **options):
            calls.append(copy.deepcopy(options))
            return original(catalog, **options)
        self.real_prepare = prepare
        self.sequence = [dict(kind='stop', claim='blocked', reason='legacy factory')]
        r = self.call(source_settings=None, plan_binding=None, quantity=None); self.shape(r)
        self.assertEqual(calls, [dict(condition='normal', seed=0, power_dbm=12.5)])
        self.assertEqual(set(r['artifacts']), {'request', 'schema', 'legacy_report', 'legacy_events', 'assessment'})
        request = json.loads((self.driver.root / 'run-1/caller-request.json').read_bytes())
        self.assertEqual(set(request['execution']), {'catalog_path', 'executable'})

    def test_source_settings_same_trial_fresh_observation(self):
        source = self.declared_source(); before = C(source); calls = []
        original = self.real_prepare
        def prepare(catalog, **options):
            calls.append(options)
            return original(catalog, **options)
        self.real_prepare = prepare
        r = self.call(source_settings=source); self.shape(r)
        self.assertEqual(C(source), before)
        self.assertEqual(len(calls), 1)
        self.assertEqual(set(calls[0]), {'condition', 'seed', 'power_dbm', 'source_settings'})
        self.assertEqual(C(calls[0]['source_settings']), before)
        self.assertIsNot(calls[0]['source_settings'], source)
        self.assertIs(type(calls[0]['power_dbm']), int)
        self.assertEqual(len(self.trials), 1); self.assertEqual(self.evaluated, self.trials)
        self.assertTrue(r['evidence_assessment']['goal_observed'])
        measurement = self.trials[0].runtime.observations()['devices']['sensor']['values']['outputs']['measurement']
        self.assertEqual(measurement['frequency_hz'], source['frequency_hz'])
        self.assertEqual(measurement['duty_cycle'], source['duty_cycle'])
        request = json.loads((self.driver.root / 'run-1/caller-request.json').read_bytes())
        self.assertEqual(C(request['execution']['source_settings']), before)

    def test_source_settings_detached_from_late_caller_mutation(self):
        source = self.declared_source(); original = C(source)
        self.after_produce = lambda: source.update(power_dbm=99)
        r = self.call(source_settings=source); self.shape(r)
        self.assertEqual(source['power_dbm'], 99)
        self.assertTrue(r['evidence_assessment']['goal_observed'])
        self.assertEqual(len(self.trials), 1)
        request = json.loads((self.driver.root / 'run-1/caller-request.json').read_bytes())
        self.assertEqual(C(request['execution']['source_settings']), original)

    def bound_plan(self):
        from test_intake_conducted_twin_plan import fixture
        from labflow.intake_conducted_twin_plan import build_conducted_twin_plan_input
        context, analysis, options = fixture()
        options['source_settings'] = self.declared_source()
        for key, value in options['source_settings'].items():
            options['basis'][key]['value'] = value
        plan = build_conducted_twin_plan_input(context, analysis, **options)
        self.assertEqual(plan['status'], 'ready_for_simulation')
        return plan

    def test_bound_setup_and_postrun_journal_use_same_trial(self):
        from labflow.virtual_fleet.journal import read_operator_journal
        plan = self.bound_plan(); collector = []; snapshots = []; calls = []
        original = self.real_prepare
        def prepare(catalog, **options):
            self.assertEqual(options['setup_records'], [])
            collector.append(options['setup_records']); calls.append(options)
            trial = original(catalog, **options)
            getter = trial.setup_snapshot
            def capture():
                value = getter(); snapshots.append(value); return value
            trial.setup_snapshot = capture
            return trial
        self.real_prepare = prepare
        quantity = dict(metric='on', reference_plane='sensor_input', loss_compensation_applied=False, loss_compensation_sign=1)
        result = self.call(source_settings=plan['plan']['source_settings'], plan_binding=plan['binding'], quantity=quantity)
        self.shape(result)
        self.assertEqual(len(calls), 1); self.assertEqual(len(snapshots), 1); self.assertEqual(len(self.trials), 1)
        folder = self.driver.root / 'run-1'
        setup = json.loads((folder / 'setup-snapshot.json').read_bytes())
        self.assertTrue(setup); self.assertLessEqual(len(setup), 32)
        self.assertEqual(C(setup), C(collector[0])); self.assertEqual(C(setup), C(snapshots[0]))
        self.assertIsNot(collector[0], snapshots[0])
        journal = read_operator_journal(folder / 'operator-journal.jsonl')
        header = journal['header']; provenance = header['provenance']
        self.assertEqual((header['run_id'], header['runtime_instance_id']), (result['run_id'], self.trials[0].runtime_instance_id))
        self.assertEqual(C(provenance['plan_binding']), C(plan['binding']))
        self.assertEqual(provenance['setup_sha256'], H(C(setup)))
        self.assertEqual(provenance['topology_sha256'], H(C(provenance['topology'])))
        self.assertEqual(provenance['quantity'], quantity)
        self.assertEqual(provenance['recording_mode'], 'post_run_from_retained_events')
        self.assertEqual(C(journal['events']), C(json.loads((folder / 'legacy-harness-events.json').read_bytes())))
        self.assertTrue(journal['complete'])
        self.assertFalse(header['ai_model_called']); self.assertIsNone(result['execution']['ai_model_called'])
        self.assertTrue(result['execution']['host_evidence']['binding_verified'])
        self.assertTrue(result['evidence_assessment']['goal_observed'])

    def test_quantity_missing_or_wrong_is_never_filled(self):
        from labflow.virtual_fleet.journal import read_operator_journal
        plan = self.bound_plan()
        self.sequence = [dict(kind='stop', claim='blocked', reason='quantity declaration only')]
        self.call(source_settings=plan['plan']['source_settings'], plan_binding=plan['binding'])
        journal = read_operator_journal(self.driver.root / 'run-1/operator-journal.jsonl')
        self.assertNotIn('quantity', journal['header']['provenance'])
        wrong = dict(metric='peak', reference_plane='source_output', loss_compensation_applied=True, loss_compensation_sign=False)
        self.call(source_settings=plan['plan']['source_settings'], plan_binding=plan['binding'], quantity=wrong)
        journal = read_operator_journal(self.driver.root / 'run-2/operator-journal.jsonl')
        self.assertEqual(C(journal['header']['provenance']['quantity']), C(wrong))
        self.assertIs(journal['header']['provenance']['quantity']['loss_compensation_sign'], False)

    def test_bound_input_rejected_before_artifacts_or_factory(self):
        plan = self.bound_plan()
        cases = [dict(plan_binding={}, source_settings=self.declared_source()),
                 dict(plan_binding=plan['binding']), dict(quantity=dict(metric='on'))]
        for field, value in [('revision',True),('context_sha256','bad'),('intake_id',1)]:
            cases.append(dict(source_settings=self.declared_source(), plan_binding={**plan['binding'], field:value}))
        for options in cases:
            self.failure('invalid_input', **options)
            self.assertFalse((self.driver.root / ('run-' + str(self.invocations))).exists())
        self.assertEqual(self.trials, []); self.assertEqual(self.driver.calls, [])

    def test_actual_partial_setup_retains_null_receipt(self):
        from labflow.virtual_fleet.core import VirtualFleet
        plan = self.bound_plan(); original = VirtualFleet.execute; counter = [0]
        def execute(fleet, *args, **kwargs):
            counter[0] += 1
            if counter[0] == 4:
                raise RuntimeError('AUTHORED_SETUP_FAILURE')
            return original(fleet, *args, **kwargs)
        with patch.object(VirtualFleet, 'execute', execute):
            error = self.failure('capture_failed', source_settings=plan['plan']['source_settings'], plan_binding=plan['binding'])
        setup = json.loads((self.driver.root / 'run-1/setup-snapshot.json').read_bytes())
        self.assertTrue(setup)
        self.assertIsNone(setup[-1]['receipt']); self.assertIsNone(setup[-1]['tick'])
        self.assertEqual(error.receipt['execution']['host_evidence']['setup_status'], 'partial')
        self.assertIsNone(error.receipt['execution']['runtime_instance_id'])
        self.assertFalse(error.receipt['artifacts']['operator_journal']['present'])
        self.assertEqual(error.receipt['budget']['producer_calls_started'], 0)

    def test_setup_control_identity_and_raw_prefix(self):
        from labflow.virtual_fleet.core import VirtualFleet
        plan = self.bound_plan(); original = VirtualFleet.execute; counter = [0]
        control = KeyboardInterrupt('AUTHORED_SETUP_CONTROL')
        def execute(fleet, *args, **kwargs):
            counter[0] += 1
            if counter[0] == 4:raise control
            return original(fleet, *args, **kwargs)
        with patch.object(VirtualFleet, 'execute', execute):
            with self.assertRaises(KeyboardInterrupt) as got:
                self.call(source_settings=plan['plan']['source_settings'], plan_binding=plan['binding'])
        self.assertIs(got.exception, control)
        setup = json.loads((self.driver.root / 'run-1/setup-snapshot.json').read_bytes())
        self.assertIsNone(setup[-1]['receipt'])
        self.assertEqual(self.driver.calls, [])

    def test_journal_failure_keeps_original_producer_code(self):
        from labflow.virtual_fleet.journal import read_operator_journal
        plan = self.bound_plan(); original = api._Journal.__call__; counter = [0]
        self.producer_mode = 'nonzero'
        def append(journal, event):
            counter[0] += 1
            if counter[0] == 2:raise OSError('AUTHORED_JOURNAL_FAILURE')
            return original(journal, event)
        with patch.object(api._Journal, '__call__', append):
            error = self.failure('codex_cli_response_process_failed', source_settings=plan['plan']['source_settings'], plan_binding=plan['binding'])
        self.assertGreater(counter[0], 1)
        self.assertEqual(error.receipt['budget']['reserved_model_calls'], 1)
        journal = read_operator_journal(self.driver.root / 'run-1/operator-journal.jsonl')
        self.assertFalse(journal['complete'])
        self.assertTrue(error.receipt['artifacts']['operator_journal']['present'])
        self.assertIn('post_run_journal_failed', error.receipt['cleanup']['secondary_errors'])

    def test_preflight_before_factory_or_process(self):
        for change in [dict(execution_origin=True), dict(scenario='other'), dict(requested_model='other'),
                       dict(catalog_path=str(self.catalog)), dict(response_schema_bytes=C(json.loads(SCHEMA))),
                       dict(catalog_sha256='0' * 64), dict(evidence_dir=self.driver.root)]:
            suffix = 'unsupported_source' if 'catalog_sha256' in change else 'invalid_input'
            e = self.failure(suffix, **change)
            self.assertIsNone(e.receipt)
        self.assertEqual(self.trials, []); self.assertEqual(self.driver.calls, [])

    def test_same_runtime_fresh_context_until_observed_goal(self):
        r = self.call(); self.shape(r)
        self.assertEqual(len(self.trials), 1); self.assertEqual(self.evaluated, self.trials)
        self.assertTrue(r['evidence_assessment']['goal_observed'])
        self.assertEqual(r['evidence_assessment']['result']['summary_code'], 'observed_goal_satisfied')
        self.assertGreater(len(self.prompts), 1)
        ids = [p['binding']['runtime_instance_id'] for p in self.prompts]
        self.assertEqual(set(ids), {self.trials[0].runtime_instance_id})
        self.assertEqual(len({p['binding']['model_request_id'] for p in self.prompts}), len(self.prompts))
        folder = self.driver.root / 'run-1/calls'
        for step, prompt in zip(r['steps'], self.prompts):
            step_folder = folder / f'{step["index"]:04d}'
            full = json.loads((step_folder / 'context8.json').read_bytes())
            compact = json.loads((step_folder / 'public-context7.json').read_bytes())
            user = json.loads(prompt['messages'][1]['content'])['request']['user_input']
            self.assertEqual(len(full['topology']['devices']), 64)
            self.assertEqual(len(full['catalog']['profiles']), 64)
            self.assertIn('remaining_budget', full)
            self.assertNotIn('remaining_budget', compact)
            self.assertEqual(len(compact['topology']['devices']), 11)
            self.assertEqual(len(compact['topology']['connections']), 13)
            self.assertEqual(len(compact['catalog']['profiles']), 11)
            self.assertEqual(len(compact['observations']['devices']), 11)
            self.assertEqual(user['public_context'], compact)
            self.assertEqual(prompt['binding']['context_sha256'], H(C(compact)))
            self.assertEqual(user['delegation']['scope'], 'rf_sensor_proposal_v1')
            self.assertEqual(H(C(full['observations'])), step['before']['sha256'])
        for previous, next_step in zip(r['steps'], r['steps'][1:]):
            full = json.loads((folder / f'{next_step["index"]:04d}' / 'context8.json').read_bytes())
            self.assertEqual(H(C(full['observations'])), previous['after']['sha256'])

    def test_completed_claim_without_measurement_is_not_goal(self):
        self.sequence = [dict(kind='stop', claim='completed', reason='claim only')]
        r = self.call(); self.shape(r)
        self.assertFalse(r['evidence_assessment']['goal_observed'])
        self.assertEqual(r['evidence_assessment']['result']['verdict'], 'fail')
        self.assertEqual(r['budget']['harness_usage']['logical_requests'], 0)

    def test_eight_model_and_tool_caps_no_budget_reset(self):
        self.sequence = [dict(kind='advance', ticks=1)]
        r = self.call(); self.shape(r)
        self.assertEqual((r['budget']['producer_calls_started'], r['budget']['reserved_model_calls']), (8, 8))
        self.assertEqual((r['budget']['harness_usage']['logical_requests'], r['budget']['harness_usage']['tick_delta']), (8, 8))
        self.assertEqual(r['termination']['reason'], 'decision_budget')
        self.assertFalse(r['budget']['reservation_refunded']); self.assertFalse(r['budget']['new_budget_granted'])

    def test_known_rejection_and_recovery_noncompletion(self):
        self.sequence = [dict(kind='execute', device_id='dut', action='start', parameters={}),
                         dict(kind='stop', claim='blocked', reason='known disconnect')]
        r = self.call(scenario='persistent_disconnect'); self.shape(r)
        self.assertEqual(r['steps'][0]['dispatch']['receipt_status'], 'disconnected')
        self.assertEqual(r['evidence_assessment']['result']['summary_code'], 'bounded_noncompletion_confirmed')
        self.assertFalse(r['evidence_assessment']['goal_observed'])
        self.sequence = [dict(kind='advance', ticks=1)]
        r = self.call(scenario='restored_disconnect')
        self.assertFalse(r['evidence_assessment']['goal_observed'])
        self.assertEqual(len(self.trials), 2)
        self.sequence = [dict(kind='execute', device_id='dut', action='start', parameters={})]
        self.runtime_fault = RuntimeError('FAKE_SECRET_RUNTIME')
        e = self.failure('runtime_uncertain')
        self.assertIsNone(e.receipt['steps'][0]['dispatch']['runtime_call_attempts'])

    def test_invalid_binding_never_dispatches(self):
        self.wrong_binding = True
        e = self.failure('model_operator_boundary_response_binding_mismatch')
        self.assertEqual(e.receipt['budget']['harness_usage']['logical_requests'], 0)
        self.assertEqual(e.receipt['budget']['producer_calls_started'], 1)

    def test_forbidden_tool_and_missing_fresh_read(self):
        self.sequence = [dict(kind='execute', device_id='sensor', action='configure', parameters={})]
        self.failure('model_operator_boundary_proposal_invalid')
        self.sequence = [dict(kind='execute', device_id='sensor', action='read', parameters={}), dict(kind='stop', claim='completed', reason='stale read')]
        r = self.call(); self.assertFalse(r['evidence_assessment']['goal_observed'])

    def test_producer_failure_consumes_attempt_and_preserves_raw(self):
        self.producer_mode = 'nonzero'
        event = threading.Event(); self.after_produce = event.set
        e = self.failure('codex_cli_response_process_failed', cancel_event=event)
        self.assertEqual((e.receipt['budget']['reserved_model_calls'], e.receipt['budget']['producer_calls_started']), (1, 1))
        self.assertEqual(e.receipt['budget']['application_retries'], 0)
        self.assertIsNotNone(e.receipt['steps'][0]['producer']['receipt'])
        self.assertTrue((self.driver.root / 'run-1/calls/0001/producer/stdout.jsonl').exists())
        self.assertTrue(e.receipt['execution']['cancellation']['requested'])

    def test_deadline_and_stage_cancel(self):
        event = threading.Event(); event.set()
        self.failure('cancelled', cancel_event=event)
        self.assertEqual(self.trials, [])
        self.assertEqual(self.driver.calls, [])
        self.producer_mode = 'late_exit'; self.timeout_override = .25
        e = self.failure('codex_cli_response_timeout')
        self.assertEqual(e.receipt['budget']['producer_calls_started'], 1)

    def test_cancel_after_producer_no_refund(self):
        event = threading.Event(); self.after_produce = event.set
        e = self.failure('cancelled', cancel_event=event)
        self.assertEqual(e.receipt['budget']['producer_calls_started'], 1)
        self.assertEqual(e.receipt['budget']['harness_usage']['logical_requests'], 0)
        self.assertEqual(e.receipt['execution'].get('cancellation'), dict(scope='between_stages_and_owned_producer_waits',
            requested=True, producer_inflight_cancelled=None, remote_hard_cancelled=None))

    def test_inflight_cancel_forwards_event_and_never_dispatches_wire(self):
        from labflow import codex_cli_response as producer
        event=threading.Event();self.producer_mode='hang'
        consume=producer._Exchange.stdout;produce=self.produce
        def consumed(owner,data):consume(owner,data);event.set()
        def forwarded(*args,**kwargs):
            self.assertIs(kwargs.get('cancel_event'),event)
            return produce(*args,**kwargs)
        with patch.object(self,'produce',side_effect=forwarded),patch.object(producer._Exchange,'stdout',new=consumed):
            error=self.failure('cancelled',cancel_event=event)
        result=error.receipt;step=result['steps'][0];receipt=step['producer']['receipt']
        self.assertEqual(receipt['failure']['code'],'codex_cli_response_cancelled')
        self.assertEqual((result['budget']['reserved_model_calls'],result['budget']['producer_calls_started'],
                          result['budget']['model_process_attempts']),(1,1,1))
        self.assertEqual((step['dispatch']['runtime_call_attempts'],step['dispatch']['reserved_logical_requests']),(0,0))
        self.assertIsNone(step['wire']);self.assertFalse(step['verification']['wire_accepted'])
        self.assertEqual(result['execution']['cancellation'],dict(scope='between_stages_and_owned_producer_waits',
            requested=True,producer_inflight_cancelled=True,remote_hard_cancelled=None))
        self.assertIsNone(receipt['cleanup']['remote_cancelled'])

    def test_inflight_cancel_unconfirmed_cleanup_and_cleared_event_stay_unknown(self):
        from labflow import codex_cli_response as producer
        event=threading.Event();self.producer_mode='hang';self.after_produce=event.clear
        consume=producer._Exchange.stdout;spawn=self.driver.spawn;waits=[];produce=self.produce
        def consumed(owner,data):consume(owner,data);event.set()
        def forwarded(*args,**kwargs):
            self.assertIs(kwargs.get('cancel_event'),event)
            return produce(*args,**kwargs)
        def started(argv,**kwargs):
            child=spawn(argv,**kwargs)
            if len(argv)>2:
                wait=child.wait;waits.append((child,wait))
                def unconfirmed(*args,**options):wait(*args,**options);raise OSError('FAKE_WAIT_SECRET')
                child.wait=unconfirmed
            return child
        try:
            with patch.object(self,'produce',side_effect=forwarded),patch.object(self.driver,'spawn',new=started),patch.object(producer._Exchange,'stdout',new=consumed):
                error=self.failure('cancelled',cancel_event=event)
        finally:
            for child,wait in waits:child.wait=wait
        self.assertFalse(event.is_set())
        result=error.receipt;receipt=result['steps'][0]['producer']['receipt']
        self.assertFalse(receipt['cleanup']['model_child_reaped'])
        self.assertTrue(result['execution']['cancellation']['requested'])
        self.assertIsNone(result['execution']['cancellation']['producer_inflight_cancelled'])
        self.assertIsNone(result['execution']['cancellation']['remote_hard_cancelled'])
        self.assertEqual(result['budget']['model_process_attempts'],1)
        self.assertEqual(result['steps'][0]['dispatch']['runtime_call_attempts'],0)

    def test_original_schema_and_producer_artifacts(self):
        self.sequence = [dict(kind='stop', claim='blocked', reason='scope check')]
        self.producer_mode = 'no_usage'
        r = self.call(); directory = self.driver.root / 'run-1'
        self.assertEqual((directory / 'response-schema.json').read_bytes(), SCHEMA)
        producer = directory / 'calls/0001/producer'
        receipt = r['steps'][0]['producer']['receipt']
        self.assertIsNone(receipt['usage'])
        self.assertIsNone(receipt['cost']['amount'])
        self.assertEqual(json.loads((producer / 'receipt.json').read_bytes()), receipt)
        for desc in receipt['artifacts'].values():
            data = (producer / desc['path']).read_bytes()
            self.assertEqual((len(data), H(data)), (desc['bytes'], desc['sha256']))
        self.assertEqual((producer / 'response-schema.json').read_bytes(), SCHEMA)

    def test_native_caps_and_changed_capture(self):
        tiny = self.driver.root / 'tiny-file-cap'
        with patch.dict(api._LIMITS, max_known_evidence_files=1):
            self.failure('limit_exceeded', evidence_dir=tiny)
        self.assertLessEqual(len([p for p in tiny.rglob('*') if p.is_file()]), 1)
        with patch.dict(api._LIMITS, max_known_evidence_files=8):
            self.failure('limit_exceeded')
        self.assertEqual(self.driver.calls, [], 'Insufficient retained-file capacity must refuse before model start')
        self.after_produce = lambda: self.trials[-1].runtime.advance('test-out-of-band', 1)
        e = self.failure('capture_failed')
        self.assertEqual(e.receipt['budget']['harness_usage']['logical_requests'], 0)
        self.after_produce = None
        with patch.dict(api._LIMITS, max_output_bytes=1):
            self.failure('limit_exceeded')

    def test_cleanup_first_error_and_control_identity(self):
        for control in [KeyboardInterrupt('CONTROL'), SystemExit(7), GeneratorExit('CONTROL'), MemoryError('CONTROL')]:
            with patch.object(api, '_produce', side_effect=control):
                # call() normally installs the genuine lifecycle wrapper; invoke directly here.
                options = dict(self.options, evidence_dir=self.driver.root / ('control-' + type(control).__name__))
                with self.assertRaises(type(control)) as got:
                    api.run_codex_virtual_loop(**options)
            self.assertIs(got.exception, control)
        control = KeyboardInterrupt('RUNTIME_CONTROL')
        self.runtime_fault = control
        self.sequence = [dict(kind='execute', device_id='dut', action='start', parameters={})]
        with self.assertRaises(KeyboardInterrupt) as got:
            self.call()
        self.assertIs(got.exception, control)
        self.runtime_fault = None
        original_open = Path.open
        class CloseFailure:
            def __init__(self, handle):
                self.handle = handle
            def __getattr__(self, name):
                return getattr(self.handle, name)
            def close(self):
                self.handle.close()
                raise OSError('FAKE_SECRET_CLOSE')
        def opened(path, mode='r', *args, **kwargs):
            handle = original_open(path, mode, *args, **kwargs)
            return CloseFailure(handle) if path.name == 'loop-receipt.json' and 'x' in mode else handle
        self.producer_mode = 'nonzero'
        with patch.object(Path, 'open', opened):
            e = self.failure('codex_cli_response_process_failed')
        self.assertIn('host_close_failed', e.receipt['cleanup']['secondary_errors'])
        self.assertFalse(e.receipt['cleanup']['host_artifacts_closed'])
        self.producer_mode = 'normal'
        self.sequence = [dict(kind='stop', claim='blocked', reason='close failure')]
        with patch.object(Path, 'open', opened):
            self.failure('cleanup_failed')

    def test_origin_and_legacy_flags_do_not_claim_actual(self):
        self.sequence = [dict(kind='stop', claim='blocked', reason='scope')]
        r = self.call(); self.shape(r)
        legacy = json.loads((self.driver.root / 'run-1/legacy-harness-report.json').read_bytes())
        self.assertFalse(legacy['ai_model_called']); self.assertEqual(legacy['policy']['kind'], 'fixture')
        self.assertNotEqual(r['kind'], legacy['kind'])
        self.assertIsNone(r['execution']['ai_model_called'])

    def test_public_evaluator_original_trial_only(self):
        self.sequence = [dict(kind='stop', claim='completed', reason='claim only')]
        r = self.call()
        self.assertEqual(self.evaluated, self.trials)
        self.assertEqual(len(self.evaluated), 1)
        self.assertTrue(r['evidence_assessment']['evaluator_called'])
        self.assertIsNone(r['evidence_assessment']['score'])

    def test_cleanup_result_control_restores_original_runtime(self):
        self.sequence = [dict(kind='stop', claim='blocked', reason='cleanup boundary')]
        control = KeyboardInterrupt('RESULT_CONTROL')
        original = api._Loop.finalize
        def finalize(loop):
            def result():
                raise control
            if loop.harness is not None:
                loop.harness.result = result
            return original(loop)
        with patch.object(api._Loop, 'finalize', finalize):
            with self.assertRaises(KeyboardInterrupt) as got:
                self.call()
        self.assertIs(got.exception, control)
        self.assertEqual(self.trials[0].runtime.execute, self.original_execute[0])

    def test_source_read_error_survives_later_close_error(self):
        original_open = Path.open
        fault = OSError('FAKE_SECRET_SOURCE_READ')
        later = OSError('FAKE_SECRET_SOURCE_CLOSE')
        target_name = 'codex_virtual_loop.py'
        class BrokenRead:
            def __init__(self, handle):
                self.handle = handle
            def __getattr__(self, name):
                return getattr(self.handle, name)
            def read(self, *args):
                raise fault
            def close(self):
                self.handle.close()
                raise later
        def opened(path, mode='r', *args, **kwargs):
            handle = original_open(path, mode, *args, **kwargs)
            return BrokenRead(handle) if path.name == target_name and mode == 'rb' else handle
        with patch.object(Path, 'open', opened):
            e = self.failure('unsupported_source')
        self.assertIn('host_close_failed', e.receipt['cleanup']['secondary_errors'])
        fault = KeyboardInterrupt('SOURCE_READ_CONTROL')
        later = KeyboardInterrupt('SOURCE_CLOSE_CONTROL')
        with patch.object(Path, 'open', opened):
            with self.assertRaises(KeyboardInterrupt) as got:
                self.call()
        self.assertIs(got.exception, fault)
        target_name = self.catalog.name
        with patch.object(Path, 'open', opened):
            with self.assertRaises(KeyboardInterrupt) as got:
                self.call()
        self.assertIs(got.exception, fault)
        self.assertEqual(self.driver.calls, [])

    def test_observation_failure_is_not_normal_bounded_completion(self):
        self.observation_invalid = True
        e = self.failure('capture_failed')
        self.assertEqual(e.receipt['budget']['producer_calls_started'], 0)
        self.assertEqual(self.driver.calls, [])
        self.observation_invalid = False
        control = KeyboardInterrupt('OBSERVATION_CONTROL')
        self.observation_fault = control
        with self.assertRaises(KeyboardInterrupt) as got:
            self.call()
        self.assertIs(got.exception, control)
        self.observation_fault = RuntimeError('FAKE_SECRET_OBSERVATION')
        self.observation_after_tool = True
        self.sequence = [dict(kind='execute', device_id='dut', action='start', parameters={})]
        e = self.failure('runtime_uncertain')
        self.assertEqual(e.receipt['budget']['producer_calls_started'], 1)
        self.assertIsNone(e.receipt['steps'][0]['after'])
        self.assertEqual(e.receipt['steps'][0]['dispatch']['effect'], 'unknown')


class ReservationLoopTests(unittest.TestCase):
    def setUp(self):
        self.folder=ROOT/'.local/ers'/uuid.uuid4().hex[:8];self.folder.mkdir(parents=True)
        self.proof_files=0;self.proof_bytes=0
        for name in ('_prepare','_produce'):
            self.enterContext(patch.object(api,name,side_effect=AssertionError('NO_RUNTIME_OR_PRODUCER')))
        for name in ('socket.socket.connect','socket.getaddrinfo'):
            self.enterContext(patch(name,side_effect=AssertionError('NO_NETWORK')))

    def file(self,name,raw):
        self.assertLess(self.proof_files,128);self.assertLessEqual(self.proof_bytes+len(raw),8388608)
        self.proof_files+=1;self.proof_bytes+=len(raw);path=self.folder/name;path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as stream:stream.write(raw)
        return path

    def options(self):
        return dict(catalog_path=self.folder/'unused-catalog',catalog_sha256='a'*64,response_schema_bytes=b'{}',
            executable=self.folder/'unused-executable',requested_model='gpt-6-astra',scenario='normal',
            evidence_dir=self.folder/'loop',execution_origin='mock_subprocess')

    def runner(self,reservation=None,*,omitted=False,binding=None):
        captured=[];constructor=api._Loop;entries=[]
        def construct(*args,**kwargs):captured.append(kwargs.copy());return constructor(*args,**kwargs)
        def no_run(owner):entries.append(owner)
        options=self.options()
        if not omitted:options['evidence_reservation']=reservation
        fixed=type('FixedUUID',(),dict(hex='a'*32))()
        start=api._now()
        with patch.object(api,'_preflight',return_value=(None,binding,None)),patch.object(api,'_now',return_value=start), \
                patch.object(api.uuid,'uuid4',return_value=fixed),patch.object(api,'_Loop',side_effect=construct), \
                patch.object(constructor,'run',no_run),patch.object(constructor,'finalize'),patch.object(constructor,'restore_runtime'):
            result=api.run_codex_virtual_loop(**options)
        self.assertEqual(len(entries),1);return entries[0],result,captured[0]

    def reservation_file_byte_equalities_and_no_double_count(self):
        runner,_,_=self.runner(dict(files=1,bytes=7));known=self.file('loop/known.bin',b'abc');self.file('external-host.bin',b'1234567')
        runner.known.add(known)
        runner.space(33554432-7-3,192-1-1)
        for byte_count,file_count in ((33554432-7-3+1,0),(0,192-1)):
            with self.subTest(bytes=byte_count,files=file_count):
                with self.assertRaises(api._Fault) as got:runner.space(byte_count,file_count)
                self.assertEqual(got.exception.code,'operator_virtual_loop_limit_exceeded')
        full,_,_=self.runner(dict(files=192,bytes=33554432));full.space()
        with self.assertRaises(api._Fault):full.space(1,0)
        with self.assertRaises(api._Fault):full.space(0,1)

    def reservation_none_shape_caps_and_alias_isolation(self):
        old,omitted,old_args=self.runner(omitted=True);none,explicit_none,none_args=self.runner(None)
        self.assertEqual(C(omitted),C(explicit_none));self.assertNotIn('evidence_reservation',old_args);self.assertNotIn('evidence_reservation',none_args)
        old.space(33554432,192);none.space(33554432,192)
        reservation=dict(files=2,bytes=9);owner,result,_=self.runner(reservation);reservation.update(files=0,bytes=0)
        owner.space(33554432-9,192-2)
        with self.assertRaises(api._Fault):owner.space(33554432-9+1,0)
        self.assertEqual(set(result),set(omitted));self.assertEqual(result['budget']['limits'],omitted['budget']['limits'])
        self.assertEqual(api._BUDGET,dict(decisions=8,logical_requests=8,ticks=8,wall_seconds=180,transport_retries=0))

    def reservation_invalid_precedes_preflight_io(self):
        class Number(int):pass
        class Mapping(dict):pass
        values=[{},[],True,Mapping(files=0,bytes=0),dict(files=Number(1),bytes=0),dict(files=False,bytes=0),
            dict(files=0,bytes=True),dict(files=0,bytes=0.0),dict(files=-1,bytes=0),dict(files=193,bytes=0),
            dict(files=0,bytes=-1),dict(files=0,bytes=33554433),dict(files=0),dict(files=0,bytes=0,extra=0)]
        with patch.object(api,'_preflight',side_effect=AssertionError('NO_PREFLIGHT_IO')) as preflight, \
                patch.object(api,'_Loop',side_effect=AssertionError('NO_LOOP')) as loop, \
                patch.object(Path,'open',side_effect=AssertionError('NO_FILE')):
            for value in values:
                with self.subTest(value=repr(value)):
                    with self.assertRaises(api.CodexVirtualLoopError) as got:api.run_codex_virtual_loop(**self.options(),evidence_reservation=value)
                    self.assertEqual(got.exception.code,'operator_virtual_loop_invalid_input');self.assertIsNone(got.exception.receipt)
            self.assertFalse(preflight.called);self.assertFalse(loop.called)

    def reservation_control_and_final_write_admission(self):
        control=MemoryError('ORIGINAL_CONTROL')
        with patch.object(api,'_preflight',side_effect=control):
            with self.assertRaises(MemoryError) as got:api.run_codex_virtual_loop(**self.options(),evidence_reservation=dict(files=0,bytes=0))
        self.assertIs(got.exception,control)
        owner,_,_=self.runner(dict(files=0,bytes=33554432))
        with patch.object(Path,'open',side_effect=AssertionError('NO_XB_BEFORE_ADMISSION')) as opened:
            with self.assertRaises(api._Fault):owner.write(self.folder/'loop-receipt.json',b'{}',262144,final=True)
        self.assertFalse(opened.called)
        producer_bytes=sum(cap for _,cap in api._PRODUCER_FILES.values())+2097152
        owner,_,_=self.runner(dict(files=0,bytes=33554432-producer_bytes+1))
        with self.assertRaises(api._Fault):owner.space(producer_bytes,len(api._PRODUCER_FILES)+4)

    def reservation_journal_exact_header_rows_before_creation(self):
        from labflow.virtual_fleet.journal import OperatorJournal,read_operator_journal
        binding=dict(intake_id='RES',revision=1,analysis_context_id='context:typed',context_sha256='a'*64,analysis_sha256='b'*64,plan_sha256='c'*64)
        topology=dict(label='x'*440000)
        def configured(reservation):
            owner,_,_=self.runner(reservation,binding=binding);owner.host_topology=topology;owner.setup_snapshot=[{}]
            owner.r['execution']['runtime_instance_id']='runtime:reservation';host=owner.r['execution']['host_evidence']
            host.update(topology_sha256=H(C(topology)),setup_sha256='d'*64);owner.r['artifacts']['setup_snapshot']['complete']=True
            event=dict(schema_version=1,kind='operator_event',event_id='event:one',run_id=owner.r['run_id'],
                runtime_instance_id='runtime:reservation',sequence=1,type='termination',payload=dict(code='run_terminated',unresolved_request_ids=[]))
            owner.events=[event];owner.event_bytes=len(C(event));return owner
        sample=configured(dict(files=0,bytes=0));host=sample.r['execution']['host_evidence']
        provenance=dict(runtime_origin='preinitialized',catalog_sha256=sample.catalog_sha,topology=topology,topology_sha256=host['topology_sha256'],
            engine_sha256=H(C(sample.source_pins)),engine_fingerprint_kind='sha256_canonical_host_source_pins_v1',source_pins=sample.source_pins,
            plan_binding=binding,setup_sha256=host['setup_sha256'],recording_mode='post_run_from_retained_events')
        reference=self.folder/'reference.jsonl';self.assertLessEqual(self.proof_bytes+1048576,8388608);self.proof_files+=1;self.proof_bytes+=1048576
        with OperatorJournal(reference,run_id=sample.r['run_id'],runtime_instance_id='runtime:reservation',provenance=provenance) as journal:journal(sample.events[0])
        actual=reference.read_bytes();self.assertTrue(read_operator_journal(reference)['complete']);size=len(actual)
        self.assertGreater(size,sample.event_bytes);self.assertLess(size,sample.event_bytes+1048576)
        owner=configured(dict(files=191,bytes=33554432-size));owner.directory.mkdir(parents=True,exist_ok=True)
        self.assertLess(self.proof_files,128);self.assertLessEqual(self.proof_bytes+size,8388608);self.proof_files+=1;self.proof_bytes+=size
        with patch.object(api,'_Journal',wraps=OperatorJournal) as writer:owner.capture_journal()
        path=owner.directory/'operator-journal.jsonl';self.assertTrue(writer.called);self.assertEqual(path.read_bytes(),actual)
        self.assertTrue(owner.r['execution']['host_evidence']['binding_verified']);self.assertIsNone(owner.first)
        denied=configured(dict(files=191,bytes=33554432-size+1));denied.directory=self.folder/'denied';denied.directory.mkdir()
        with patch.object(api,'_Journal',side_effect=AssertionError('JOURNAL_MUST_NOT_OPEN')) as writer:denied.capture_journal()
        self.assertFalse(writer.called);self.assertFalse((denied.directory/'operator-journal.jsonl').exists());self.assertIsNotNone(denied.first)

    test_reservation_file_byte_equalities_and_no_double_count=reservation_file_byte_equalities_and_no_double_count
    test_reservation_none_shape_caps_and_alias_isolation=reservation_none_shape_caps_and_alias_isolation
    test_reservation_invalid_precedes_preflight_io=reservation_invalid_precedes_preflight_io
    test_reservation_control_and_final_write_admission=reservation_control_and_final_write_admission
    test_reservation_journal_exact_header_rows_before_creation=reservation_journal_exact_header_rows_before_creation


if __name__ == '__main__':
    unittest.main()

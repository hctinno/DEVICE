"""041 genuine synthetic execution, independent evidence and storage boundaries."""
from copy import deepcopy
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from labflow.virtual_fleet import integration, journal
from labflow.virtual_fleet.catalog import load_catalog


ROOT = Path(__file__).resolve().parents[1]
MODULE = 'labflow.virtual_fleet.rf_signal_scenario'
SCENARIOS = (
    ('pulsed_on_mean', -18.0, 'on_average', 2450000000.0),
    ('pulsed_time_mean', -24.020599913279625, 'time_average', 2450000000.0),
    ('pulsed_peak', -15.0, 'peak', 2450000000.0),
    ('cw_peak', -18.0, 'peak', 2450000000.0),
    ('shifted_frequency', -18.0, 'on_average', 2460000000.0),
    ('sensor_uncalibrated', None, None, 2450000000.0),
    ('meter_frequency_conflict', None, None, 2450000000.0),
)
OUTER = set('schema_version kind scenario_id status declared_setup report assessment artifacts error_code verification'.split())
PREFIX = 'rf_signal_scenario_'
UNSET = object()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def rehash(path, change):
    """Independent test writer: retain the public chain format, alter semantics."""
    records = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
    change(records)
    previous = '0' * 64
    with path.open('wb') as stream:
        for record in records:
            record.pop('sha256', None)
            record['previous_sha256'] = previous
            record['sha256'] = hashlib.sha256(canonical(record)).hexdigest()
            previous = record['sha256']
            stream.write(canonical(record) + b'\n')


def observations(records):
    return [r['event']['payload']['observation'] for r in records
            if r['record_type'] == 'event' and r['event']['type'] == 'observation']


def packets(value):
    if type(value) is dict:
        yield value
        for child in value.values():
            yield from packets(child)
    elif type(value) is list:
        for child in value:
            yield from packets(child)


def paired_receipt(records, device, action):
    rid = next(r['event']['payload']['request_id'] for r in records
               if r.get('event', {}).get('type') == 'intent'
               and r['event']['payload']['body'].get('device_id') == device
               and r['event']['payload']['body'].get('action') == action)
    return next(r['event']['payload']['result'] for r in records
                if r.get('event', {}).get('type') == 'receipt'
                and r['event']['payload']['request_id'] == rid)


class SignalScenarioTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec(MODULE),
                             '041 genuine scenario service is not implemented')
        self.api = importlib.import_module(MODULE)
        self.catalog = load_catalog(ROOT / 'virtual_profiles/sm_a176u_unlicensed.json')
        self.original_catalog = deepcopy(self.catalog)
        self.temp = tempfile.TemporaryDirectory(prefix='rf-signal041-')
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / 'run'
        self.request = {'schema_version': 1, 'scenario_id': 'pulsed_on_mean', 'seed': 7}

    def run_case(self, scenario='pulsed_on_mean', output=None, catalog=UNSET, request=UNSET):
        req = dict(self.request, scenario_id=scenario) if request is UNSET else request
        result = self.api.run_rf_signal_scenario(
            self.catalog if catalog is UNSET else catalog, req, self.output if output is None else output,
            run_id='run:041', runtime_instance_id='runtime:041')
        self.assertEqual(set(result), OUTER)
        self.assertEqual(self.catalog, self.original_catalog)
        return result

    def evaluate(self, result, output=None, request=None):
        return self.api.evaluate_rf_signal_scenario(
            self.request if request is None else request, result['declared_setup'],
            result['report'], self.output if output is None else output)

    def test_seven_genuine_runs_have_fresh_meter_or_expected_noncompletion(self):
        # A missing runtime call or copying declared values cannot supply these journals.
        for sid, expected, quantity, frequency in SCENARIOS:
            with self.subTest(scenario=sid):
                output = Path(self.temp.name) / sid
                result = self.run_case(sid, output=output)
                self.assertEqual(result['status'], 'executed')
                self.assertIsNone(result['error_code'])
                self.assertEqual(result['assessment']['verdict'], 'pass')
                self.assertEqual(result, read(output / 'public-result.json'))
                author = read(output / 'private/author.json')
                current_engine = '7816f87dcf8aa648d628935493f74dee3a54f993ba2bae87f9a1e102a8b4ccab'
                self.assertEqual(author['provenance']['engine_sha256'], current_engine)
                self.assertEqual(len(author['phases']['bootstrap']), 23)
                self.assertEqual(len(author['phases']['scenario_setup']), 4)
                self.assertEqual(author['seed'], 7)
                self.assertNotIn('frequency_hz', result['declared_setup']['sensor'])
                stored = journal.read_operator_journal(output / 'operator/events.jsonl')
                self.assertEqual(stored['header']['provenance']['engine_sha256'], current_engine)
                self.assertTrue(stored['complete'])
                self.assertEqual(stored['unresolved_request_ids'], [])
                final = next(e['payload']['observation'] for e in reversed(stored['events'])
                             if e['type'] == 'observation')
                meter = final['devices']['meter']['values']['outputs'].get('measurement')
                sensor = final['devices']['sensor']['values']['outputs'].get('measurement')
                duty, crest, modulation = (1.0, 0.0, 'CW') if sid == 'cw_peak' else (0.25, 3.0, 'OFDM')
                self.assertEqual(result['declared_setup'], dict(
                    source_signal=dict(frequency_hz=frequency, power_dbm=12.5, bandwidth_hz=20000000.0,
                                       duty_cycle=duty, crest_factor_db=crest, modulation=modulation),
                    sensor=dict(calibration_valid=sid != 'sensor_uncalibrated', acquisition_policy='triggered'),
                    meter=dict(frequency_hz=2460000000.0 if sid == 'meter_frequency_conflict' else frequency,
                               measurement_mode='on_average' if quantity is None else quantity, unit='dBm'),
                    reference_plane='sensor_input', basis='declared_synthetic_policy'))
                for identity, port, power in (('dut', 'rf', 12.5), ('coupler', 'coupled', -18.0)):
                    packet = final['devices'][identity]['values']['outputs'][port]
                    self.assertEqual(packet, dict(
                        frequency_hz=frequency, power_dbm=power, bandwidth_hz=20000000.0,
                        duty_cycle=duty, crest_factor_db=crest, modulation=modulation,
                        source_id=identity, status='ok', valid=True))
                if sensor is not None:
                    self.assertEqual((sensor['value'], sensor['power_dbm'], sensor['unit'],
                                      sensor['frequency_hz'], sensor['duty_cycle'], sensor['crest_factor_db']),
                                     (-18.0, -18.0, 'dBm', frequency, duty, crest))
                if expected is None:
                    self.assertIsNone(meter)
                    self.assertEqual(result['report']['termination']['policy_claim'], 'blocked')
                    if sid == 'sensor_uncalibrated':
                        self.assertIsNone(sensor)
                    else:
                        self.assertEqual(sensor['value'], -18.0)
                else:
                    self.assertAlmostEqual(meter['value'], expected, delta=1e-9)
                    self.assertEqual(meter['quantity'], quantity)
                    self.assertEqual(meter['unit'], 'dBm')
                    self.assertEqual(meter['frequency_hz'], frequency)
                    self.assertEqual(meter['source_id'], 'meter')
                    self.assertEqual(meter['input_source_id'], 'sensor')
                    self.assertGreater(sensor['acquisition_tick'], author['initial_context']['tick'])
                    self.assertGreater(meter['acquisition_tick'], sensor['acquisition_tick'])
                self.assertEqual(result['report']['assessment']['status'], 'not_assessed')
                manifest = read(output / 'private-manifest.json')
                self.assertIs(manifest['complete'], True)
                self.assertEqual(manifest['engine_sha256'], current_engine)
                self.assertEqual({r['path'] for r in manifest['files']},
                                 {'public-result.json', 'operator/events.jsonl', 'private/author.json'})
                for row in manifest['files']:
                    data = (output / row['path']).read_bytes()
                    self.assertEqual(row['bytes'], len(data))
                    self.assertEqual(row['sha256'], hashlib.sha256(data).hexdigest())
                self.assertEqual(result['verification']['data_origin'], 'authored_synthetic')
                self.assertIs(result['verification']['hardware_verified'], False)

    def test_unknown_actual_engine_is_rejected_before_runtime_without_relabelling(self):
        names = ('__init__.py __main__.py catalog.py core.py evaluation.py facility.py frequency_psd.py '
                 'frequency_psd_max.py frequency_source.py harness.py harness_check.py instruments.py '
                 'integration.py journal.py method_adapter.py policies.py rf.py spectrum_capture.py spectrum_math.py').split()
        package = Path(self.temp.name) / 'engine'
        package.mkdir()
        for name in names:
            shutil.copyfile(ROOT / 'labflow/virtual_fleet' / name, package / name)
        path = package / 'rf.py'
        path.write_bytes(path.read_bytes() + b'\n# unknown source, not an approved engine\n')
        with patch.object(self.api, '__file__', str(package / 'rf_signal_scenario.py')), patch.object(
                integration, 'create_conducted_example', side_effect=AssertionError('unapproved runtime')) as factory:
            result = self.run_case()
        self.assertEqual((result['status'], result['error_code']), ('failed', PREFIX + 'evidence_invalid'))
        self.assertIsNone(result['report'])
        factory.assert_not_called()
        self.assertFalse((self.output / 'private-manifest.json').exists())

    def test_one_harness_reuses_parent_policy_and_setup_before_fresh_acquire(self):
        real = integration.create_conducted_example
        fleets = []
        def observe(catalog, **kwargs):
            fleet, topology, receipts = real(catalog, **kwargs)
            fleets.append(fleet)
            return fleet, topology, receipts
        with patch.object(integration, 'create_conducted_example', new=observe):
            result = self.run_case()
        self.assertEqual(result['status'], 'executed')
        self.assertEqual(len(fleets), 1)
        history = fleets[0].history()
        meter_setup = [i for i, x in enumerate(history)
                       if x.get('device_id') == 'meter' and x.get('action') == 'configure'][-1]
        sensor_acquire = [i for i, x in enumerate(history)
                          if x.get('device_id') == 'sensor' and x.get('action') == 'acquire'][-1]
        self.assertLess(meter_setup, sensor_acquire)
        stored = journal.read_operator_journal(self.output / 'operator/events.jsonl')
        intents = [x['payload']['body'] for x in stored['events'] if x['type'] == 'intent'
                   and x['payload']['operation'] == 'execute']
        self.assertIn({'device_id': 'meter', 'action': 'fetch', 'parameters': {}}, intents)
        self.assertFalse(any(x['action'] == 'configure' for x in intents))
        self.assertEqual(result['report']['policy']['id'], 'rf_signal_scenario_v1')

    def test_describe_is_detached_and_has_no_oracle(self):
        described = self.api.describe_rf_signal_scenario('cw_peak')
        self.assertEqual(set(described), set('source_signal sensor meter reference_plane basis'.split()))
        self.assertEqual(described['reference_plane'], 'sensor_input')
        self.assertEqual(described['source_signal']['crest_factor_db'], 0.0)
        described['sensor']['calibration_valid'] = 'changed'
        self.assertIs(self.api.describe_rf_signal_scenario('cw_peak')['sensor']['calibration_valid'], True)
        with self.assertRaises(self.api.RfSignalScenarioError) as caught:
            self.api.describe_rf_signal_scenario('../private')
        self.assertEqual(caught.exception.args, (PREFIX + 'invalid_request',))

    def test_invalid_requests_never_construct_runtime_or_output(self):
        class DictSubclass(dict):
            pass
        bad = [None, [], DictSubclass(self.request), dict(self.request, schema_version=True),
               dict(self.request, seed=True), dict(self.request, seed=-1),
               dict(self.request, seed=2147483648), dict(self.request, extra=0),
               dict(self.request, scenario_id='PULSED_ON_MEAN'),
               dict(self.request, scenario_id='x' * 2048),
               dict(self.request, scenario_id='\\ud800'),
               dict(self.request, seed=float('nan'))]
        with patch.object(integration, 'create_conducted_example', side_effect=AssertionError('must not dispatch')):
            for request in bad:
                with self.subTest(type=type(request).__name__):
                    result = self.run_case(request=request)
                    self.assertEqual(result['status'], 'rejected')
                    self.assertEqual(result['error_code'], PREFIX + 'invalid_request')
                    self.assertIsNone(result['scenario_id'])
                    self.assertFalse(self.output.exists())
        result = self.api.run_rf_signal_scenario(self.catalog, self.request, self.output,
                                                run_id='bad/id', runtime_instance_id='x')
        self.assertEqual(result['error_code'], PREFIX + 'invalid_request')
        self.assertFalse(self.output.exists())

    def test_seed_limits_and_request_copies_survive_genuine_execution(self):
        request = dict(self.request, seed=2147483647)
        result = self.run_case(request=request)
        request['seed'] = 0
        self.assertEqual(read(self.output / 'private/author.json')['seed'], 2147483647)
        result['declared_setup']['source_signal']['power_dbm'] = 999
        self.assertEqual(read(self.output / 'public-result.json')['declared_setup']['source_signal']['power_dbm'], 12.5)

    def test_exact_catalog_gate_rejects_noise_timing_ports_metadata_types_and_arrays(self):
        changes = [
            lambda c: c['profiles'].reverse(),
            lambda c: c['profiles'][0].update(manufacturer='changed'),
            lambda c: next(p for p in c['profiles'] if p['role'] == 'power_meter')['simulation_parameters'].update(noise_db=1),
            lambda c: next(p for p in c['profiles'] if p['role'] == 'emi_receiver')['simulation_parameters'].update(unknown_parameter=True),
            lambda c: next(p for p in c['profiles'] if p['role'] == 'power_meter')['simulation_parameters'].update(measurement_ticks=3),
            lambda c: c['profiles'][0]['ports']['outputs'].update(new_rf='rf'),
            lambda c: next(p for p in c['profiles'] if 'attenuation_db' in p['simulation_parameters'])['simulation_parameters'].update(attenuation_db=10),
        ]
        with patch.object(integration, 'create_conducted_example', side_effect=AssertionError('gate must precede all factories')):
            for change in changes:
                catalog = deepcopy(self.catalog)
                change(catalog)
                with self.subTest(change=changes.index(change)):
                    result = self.run_case(catalog=catalog)
                    self.assertEqual(result['status'], 'rejected')
                    self.assertEqual(result['error_code'], PREFIX + 'unsupported_catalog')
                    self.assertFalse(self.output.exists())
            cyclic = {}; cyclic['cycle'] = cyclic
            for invalid in (None, cyclic, {'x': 'a' * 1025}, {'schema_version': float('inf')}):
                result = self.run_case(catalog=invalid)
                self.assertEqual(result['error_code'], PREFIX + 'unsupported_catalog')
                self.assertFalse(self.output.exists())

    def test_catalog_key_order_and_whitespace_equivalence_is_accepted(self):
        catalog = json.loads(json.dumps(self.catalog, ensure_ascii=False, indent=4))
        catalog = {k: catalog[k] for k in reversed(list(catalog))}
        result = self.run_case(catalog=catalog)
        self.assertEqual(result['status'], 'executed')

    def test_same_meter_setup_preserves_invalid_historical_result_before_new_acquisition(self):
        # Rejecting every invalid configure response wrongly loses time_average.
        result = self.run_case('pulsed_time_mean')
        self.assertEqual(result['status'], 'executed')
        setup = read(self.output / 'private/author.json')['phases']['scenario_setup']
        receipt = setup[-1]
        self.assertEqual(receipt['status'], 'invalid')
        self.assertIs(receipt['setup_changed'], False)
        self.assertEqual(receipt['values']['reason'], 'configuration_changed')
        self.assertEqual(receipt['values']['outputs'], {})
        self.assertEqual(receipt['values']['configuration']['measurement_mode'], 'time_average')
        self.assertEqual(result['assessment']['verdict'], 'pass')

    def test_existing_output_is_preserved_and_no_runtime_constructed(self):
        self.output.mkdir()
        marker = self.output / 'original'
        marker.write_bytes(b'keep')
        with patch.object(integration, 'create_conducted_example', side_effect=AssertionError('no factory')):
            result = self.run_case()
        self.assertEqual(result['status'], 'rejected')
        self.assertEqual(result['error_code'], PREFIX + 'output_unavailable')
        self.assertEqual(marker.read_bytes(), b'keep')
        self.assertEqual(list(self.output.iterdir()), [marker])

    def test_evaluator_reads_evidence_without_reexecuting_models(self):
        result = self.run_case()
        with patch.object(integration, 'create_conducted_example', side_effect=AssertionError('no runtime in evaluator')):
            assessment = self.evaluate(result)
        self.assertEqual(assessment, result['assessment'])
        (self.output / 'operator/events.jsonl').unlink()
        with self.assertRaises(self.api.RfSignalScenarioError) as caught:
            self.evaluate(result)
        self.assertEqual(str(caught.exception), PREFIX + 'evidence_unavailable')

    def test_valid_rehash_semantic_eight_groups_are_rejected(self):
        result = self.run_case()
        source = self.output
        variants = [
            ('value', lambda rs: observations(rs)[-1]['devices']['meter']['values']['outputs']['measurement'].update(value=0.0)),
            ('frequency', lambda rs: observations(rs)[-1]['devices']['sensor']['values']['outputs']['measurement'].update(frequency_hz=1.0)),
            ('duty_crest', lambda rs: observations(rs)[-1]['devices']['dut']['values']['outputs']['rf'].update(duty_cycle=0.5)),
            ('quantity_unit', lambda rs: observations(rs)[-1]['devices']['meter']['values']['outputs']['measurement'].update(quantity='peak', unit='W')),
            ('source_plane', lambda rs: observations(rs)[-1]['devices']['meter']['values']['outputs']['measurement'].update(input_source_id='dut')),
            ('acquisition', lambda rs: observations(rs)[-1]['devices']['meter']['values']['outputs']['measurement'].update(acquisition_setup_revision=0)),
            ('receipt', lambda rs: next(r['event']['payload']['result'] for r in rs if r.get('event', {}).get('type') == 'receipt').update(profile_id='wrong-profile')),
            ('ACK_only', lambda rs: [o['devices']['meter']['values']['outputs'].clear() for o in observations(rs)]),
        ]
        for group, change in variants:
            with self.subTest(group=group):
                out = Path(self.temp.name) / group
                shutil.copytree(source, out)
                rehash(out / 'operator/events.jsonl', change)
                journal.read_operator_journal(out / 'operator/events.jsonl')  # real valid chain
                assessment = self.evaluate(result, output=out)
                self.assertNotEqual(assessment['verdict'], 'pass')

    def test_evaluator_binds_request_seed_declaration_author_and_provenance(self):
        result = self.run_case()
        for field, value in (('seed', 8), ('scenario_id', 'pulsed_peak')):
            with self.subTest(field=field):
                assessment = self.evaluate(result, request=dict(self.request, **{field: value}))
                self.assertIsNone(assessment['verdict'])
        author_path = self.output / 'private/author.json'
        original = author_path.read_bytes()
        author = read(author_path)
        author['provenance']['engine_sha256'] = '0' * 64
        author_path.write_bytes(canonical(author))
        self.assertIsNone(self.evaluate(result)['verdict'])
        author_path.write_bytes(original)
        report = deepcopy(result['report'])
        report['run_id'] = 'another-run'
        self.assertIsNone(self.api.evaluate_rf_signal_scenario(self.request, result['declared_setup'], report, self.output)['verdict'])

    def test_valid_rehash_fetch_receipt_must_match_current_observation(self):
        # Trusting only receipt identity/time misses a corrupted measurement.
        result = self.run_case()
        def change(records):
            receipt = next(r['event']['payload']['result'] for r in reversed(records)
                           if r.get('event', {}).get('type') == 'receipt')
            receipt['values']['outputs']['measurement']['value'] = 999.0
        rehash(self.output / 'operator/events.jsonl', change)
        journal.read_operator_journal(self.output / 'operator/events.jsonl')
        self.assertNotEqual(self.evaluate(result)['verdict'], 'pass')

    def test_I1_sample_configuration_revision_binds_visible_meter_context(self):
        # Reviewer exact variant: change all three copies, keep visible revision2.
        result = self.run_case()
        changed = []
        def change(records):
            for item in packets(records):
                if item.get('source_id') == 'meter' and item.get('input_source_id') == 'sensor' and 'configuration_revision' in item:
                    item['configuration_revision'] = 999
                    changed.append(True)
        rehash(self.output / 'operator/events.jsonl', change)
        self.assertEqual(len(changed), 3)
        self.assertTrue(journal.read_operator_journal(self.output / 'operator/events.jsonl')['complete'])
        self.assertIsNone(self.evaluate(result)['verdict'])

    def test_I1_latest_visible_mode_must_match_declared_and_sample_mode(self):
        result = self.run_case()
        def change(records):
            observations(records)[-1]['devices']['meter']['values']['configuration']['measurement_mode'] = 'peak'
        rehash(self.output / 'operator/events.jsonl', change)
        self.assertTrue(journal.read_operator_journal(self.output / 'operator/events.jsonl')['complete'])
        self.assertIsNone(self.evaluate(result)['verdict'])

    def test_I1_ok_author_meter_setup_does_not_override_declared_frequency(self):
        result = self.run_case()
        path = self.output / 'private/author.json'
        author = read(path)
        author['phases']['scenario_setup'][-1]['values']['configuration']['frequency_hz'] = 2460000000.0
        self.assertEqual(author['phases']['scenario_setup'][-1]['status'], 'ok')
        path.write_bytes(canonical(author))
        self.assertTrue(journal.read_operator_journal(self.output / 'operator/events.jsonl')['complete'])
        self.assertIsNone(self.evaluate(result)['verdict'])

    def test_I1_author_current_nodes_and_paired_receipts_bind_public_configuration(self):
        result = self.run_case()
        variants = (
            ('bootstrap_meter_mode', 'author',
             lambda a: a['phases']['bootstrap'][21]['values']['configuration'].update(measurement_mode='peak')),
            ('author_dut_configured', 'author',
             lambda a: a['phases']['scenario_setup'][1]['values'].update(configured=False)),
            ('author_sensor_configured', 'author',
             lambda a: a['phases']['scenario_setup'][2]['values'].update(configured=False)),
            ('author_meter_revision', 'author',
             lambda a: a['phases']['scenario_setup'][3]['values'].update(configuration_revision=999)),
            ('author_meter_unit', 'author',
             lambda a: a['phases']['scenario_setup'][3]['values']['configuration'].update(unit='W')),
            ('visible_dut_configured', 'journal',
             lambda rs: observations(rs)[-1]['devices']['dut']['values'].update(configured=False)),
            ('visible_sensor_configured', 'journal',
             lambda rs: observations(rs)[-1]['devices']['sensor']['values'].update(configured=False)),
            ('visible_meter_revision', 'journal',
             lambda rs: observations(rs)[-1]['devices']['meter']['values'].update(configuration_revision=999)),
            ('paired_meter_mode', 'journal',
             lambda rs: paired_receipt(rs, 'meter', 'fetch')['values']['configuration'].update(measurement_mode='peak')),
            ('paired_sensor_configured', 'journal',
             lambda rs: paired_receipt(rs, 'sensor', 'read')['values'].update(configured=False)),
            ('paired_dut_configured', 'journal',
             lambda rs: paired_receipt(rs, 'dut', 'start')['values'].update(configured=False)),
        )
        for label, role, change in variants:
            with self.subTest(label=label):
                output = Path(self.temp.name) / label
                shutil.copytree(self.output, output)
                if role == 'author':
                    path = output / 'private/author.json'
                    value = read(path); change(value); path.write_bytes(canonical(value))
                else:
                    rehash(output / 'operator/events.jsonl', change)
                self.assertTrue(journal.read_operator_journal(output / 'operator/events.jsonl')['complete'])
                self.assertIsNone(self.evaluate(result, output=output)['verdict'])

    def test_latest_source_must_be_present_and_ok_even_with_historical_valid_samples(self):
        result = self.run_case()
        for label in ('missing_dut', 'disconnected_coupler'):
            with self.subTest(label=label):
                out = Path(self.temp.name) / label
                shutil.copytree(self.output, out)
                def change(records):
                    devices = observations(records)[-1]['devices']
                    if label == 'missing_dut':
                        devices['dut']['values']['outputs'].clear()
                    else:
                        devices['coupler']['status'] = 'disconnected'
                rehash(out / 'operator/events.jsonl', change)
                journal.read_operator_journal(out / 'operator/events.jsonl')
                self.assertNotEqual(self.evaluate(result, output=out)['verdict'], 'pass')

    def test_invalid_semantics_and_unresolved_or_ack_only_claims_are_not_pass(self):
        result = self.run_case()
        report = deepcopy(result['report'])
        report['unresolved_request_ids'] = ['missing-receipt']
        self.assertIsNone(self.api.evaluate_rf_signal_scenario(self.request, result['declared_setup'], report, self.output)['verdict'])
        path = self.output / 'operator/events.jsonl'
        path.write_bytes(path.read_bytes().replace(b'\"previous_sha256\"', b'\"bad_previous\"', 1))
        self.assertIsNone(self.evaluate(result)['verdict'])

    def test_manifest_write_failure_preserves_saved_executed_and_failed_return(self):
        opened = Path.open
        saved = {}
        attempts = []
        def deny_manifest(path, mode='r', *args, **kwargs):
            if path.name == 'private-manifest.json' and 'x' in mode:
                attempts.append(path)
                for name in ('public-result.json', 'operator/events.jsonl', 'private/author.json'):
                    saved[name] = (self.output / name).read_bytes()
                raise OSError('private filesystem detail')
            return opened(path, mode, *args, **kwargs)
        with patch.object(Path, 'open', new=deny_manifest):
            result = self.run_case()
        self.assertEqual(len(attempts), 1)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['error_code'], PREFIX + 'evidence_unavailable')
        self.assertIsNone(result['assessment']['verdict'])
        self.assertEqual(result['artifacts'], [])
        self.assertEqual(read(self.output / 'public-result.json')['status'], 'executed')
        for name, data in saved.items():
            self.assertEqual((self.output / name).read_bytes(), data)
        self.assertFalse((self.output / 'private-manifest.json').exists())
        self.assertEqual(read(self.output / 'failure.json')['error_code'], result['error_code'])

    def test_failure_sidecar_write_failure_never_overwrites_or_retries(self):
        opened = Path.open
        attempts = []
        def deny(path, mode='r', *args, **kwargs):
            if path.name in {'private-manifest.json', 'failure.json'} and 'x' in mode:
                attempts.append(path.name)
                raise OSError('unavailable')
            return opened(path, mode, *args, **kwargs)
        with patch.object(Path, 'open', new=deny):
            result = self.run_case()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(attempts, ['private-manifest.json', 'failure.json'])
        self.assertEqual(read(self.output / 'public-result.json')['status'], 'executed')
        self.assertIsNone(result['assessment']['verdict'])

    def test_manifest_read_failure_keeps_original_manifest_and_returns_failed(self):
        opened = Path.open
        def deny(path, mode='r', *args, **kwargs):
            if path.name == 'private-manifest.json' and 'r' in mode:
                raise OSError('read unavailable')
            return opened(path, mode, *args, **kwargs)
        with patch.object(Path, 'open', new=deny):
            result = self.run_case()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['error_code'], PREFIX + 'evidence_unavailable')
        self.assertIs(read(self.output / 'private-manifest.json')['complete'], True)

    def test_manifest_hash_mismatch_never_accepts_complete_true(self):
        opened = Path.open
        corrupted = []
        def alter(path, mode='r', *args, **kwargs):
            if path.name == 'private-manifest.json' and 'r' in mode and not corrupted:
                data = read(self.output / 'public-result.json')
                (self.output / 'public-result.json').write_bytes(canonical(dict(data, scenario_id='pulsed_peak')))
                corrupted.append(True)
            return opened(path, mode, *args, **kwargs)
        with patch.object(Path, 'open', new=alter):
            result = self.run_case()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['error_code'], PREFIX + 'evidence_invalid')
        self.assertIsNone(result['assessment']['verdict'])

    def test_malformed_manifest_is_invalid_evidence_and_preserves_saved_outer(self):
        opened = Path.open
        corrupted = []
        def alter(path, mode='r', *args, **kwargs):
            if path.name == 'private-manifest.json' and 'r' in mode and not corrupted:
                with opened(path, 'wb') as stream:
                    stream.write(b'not-json')
                corrupted.append(True)
            return opened(path, mode, *args, **kwargs)
        with patch.object(Path, 'open', new=alter):
            result = self.run_case()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['error_code'], PREFIX + 'evidence_invalid')
        self.assertEqual(read(self.output / 'public-result.json')['status'], 'executed')
        self.assertEqual((self.output / 'private-manifest.json').read_bytes(), b'not-json')
        self.assertIsNone(result['assessment']['verdict'])

    def test_publication_hashes_are_bound_to_bytes_the_evaluator_actually_read(self):
        # Re-hashing changed author bytes after evaluation must not publish a PASS.
        opened = Path.open
        changed = []
        def alter(path, mode='r', *args, **kwargs):
            if path.name == 'public-result.json' and 'x' in mode and not changed:
                author_path = self.output / 'private/author.json'
                with opened(author_path, 'r', encoding='utf-8') as stream:
                    author = json.load(stream)
                author['seed'] = 8
                with opened(author_path, 'wb') as stream:
                    stream.write(canonical(author))
                changed.append(True)
            return opened(path, mode, *args, **kwargs)
        with patch.object(Path, 'open', new=alter):
            result = self.run_case()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['error_code'], PREFIX + 'evidence_invalid')
        self.assertIsNone(result['assessment']['verdict'])
        self.assertEqual(read(self.output / 'public-result.json')['status'], 'executed')
        self.assertEqual(read(self.output / 'private/author.json')['seed'], 8)

    def test_outer_write_failure_preserves_partial_file(self):
        opened = Path.open
        def deny(path, mode='r', *args, **kwargs):
            if path.name == 'public-result.json' and 'x' in mode:
                with opened(path, mode, *args, **kwargs) as stream:
                    stream.write(b'{\"partial\":')
                raise OSError('short outer write')
            return opened(path, mode, *args, **kwargs)
        with patch.object(Path, 'open', new=deny):
            result = self.run_case()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual((self.output / 'public-result.json').read_bytes(), b'{\"partial\":')
        self.assertFalse((self.output / 'private-manifest.json').exists())

    def test_bootstrap_and_author_failures_preserve_failure_instead_of_success(self):
        with patch.object(integration, 'create_conducted_example', side_effect=RuntimeError('secret error')):
            result = self.run_case()
        self.assertEqual(result['error_code'], PREFIX + 'execution_incomplete')
        self.assertEqual(result['status'], 'failed')
        self.assertNotIn('secret', canonical(result).decode())
        self.assertIsNone(result['assessment']['verdict'])
        output = Path(self.temp.name) / 'author-fails'
        opened = Path.open
        def deny(path, mode='r', *args, **kwargs):
            if path.name == 'author.json' and 'x' in mode:
                raise OSError('author write blocked')
            return opened(path, mode, *args, **kwargs)
        with patch.object(Path, 'open', new=deny):
            result = self.run_case(output=output)
        self.assertEqual(result['error_code'], PREFIX + 'evidence_unavailable')
        self.assertTrue((output / 'operator/events.jsonl').is_file())
        self.assertFalse((output / 'public-result.json').exists())

    def test_setup_failure_retains_known_receipts_and_unknown_initial_context(self):
        # Losing setup evidence in the exception path makes failed attempts unauditable.
        real = integration.create_conducted_example
        def fail_last_setup(catalog, **kwargs):
            fleet, topology, receipts = real(catalog, **kwargs)
            execute = fleet.execute
            def corrupt(request_id, device, action, parameters):
                receipt = execute(request_id, device, action, parameters)
                if request_id == 'scenario:setup:3':
                    receipt['status'] = 'error'
                return receipt
            fleet.execute = corrupt
            return fleet, topology, receipts
        with patch.object(integration, 'create_conducted_example', new=fail_last_setup):
            result = self.run_case()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['error_code'], PREFIX + 'execution_incomplete')
        self.assertTrue((self.output / 'private/author.json').is_file(),
                        'known setup receipts must survive a failed attempt')
        author = read(self.output / 'private/author.json')
        self.assertEqual(len(author['phases']['bootstrap']), 23)
        self.assertEqual(len(author['phases']['scenario_setup']), 4)
        self.assertEqual(author['phases']['scenario_setup'][-1]['status'], 'error')
        self.assertIsNone(author['initial_context'])
        self.assertFalse((self.output / 'private-manifest.json').exists())

    def test_uncertain_dispatch_preserves_parent_unresolved_report_and_journal(self):
        real = integration.create_conducted_example
        def lose_sensor_receipt(catalog, **kwargs):
            fleet, topology, receipts = real(catalog, **kwargs)
            execute = fleet.execute
            def lose(request_id, device, action, parameters):
                result = execute(request_id, device, action, parameters)
                if device == 'sensor' and action == 'acquire':
                    raise RuntimeError('receipt lost after dispatch')
                return result
            fleet.execute = lose
            return fleet, topology, receipts
        with patch.object(integration, 'create_conducted_example', new=lose_sensor_receipt):
            result = self.run_case()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['error_code'], PREFIX + 'execution_incomplete')
        self.assertIsNotNone(result['report'])
        self.assertEqual(result['report']['termination']['reason'], 'runtime_mutation_uncertain')
        self.assertEqual(len(result['report']['unresolved_request_ids']), 1)
        stored = journal.read_operator_journal(self.output / 'operator/events.jsonl')
        self.assertFalse(stored['complete'])
        self.assertEqual(stored['unresolved_request_ids'], result['report']['unresolved_request_ids'])
        self.assertFalse((self.output / 'private-manifest.json').exists())

    def test_author_semantic_corruption_during_run_fails_before_outer_publication(self):
        opened = Path.open
        changed = []
        def corrupt(path, mode='r', *args, **kwargs):
            if path.name == 'author.json' and 'r' in mode and not changed:
                with opened(path, 'r', encoding='utf-8') as stream:
                    author = json.load(stream)
                author['oracle']['sensor_dbm'] = 123.0
                with opened(path, 'wb') as stream:
                    stream.write(canonical(author))
                changed.append(True)
            return opened(path, mode, *args, **kwargs)
        with patch.object(Path, 'open', new=corrupt):
            result = self.run_case()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['error_code'], PREFIX + 'evidence_invalid')
        self.assertFalse((self.output / 'public-result.json').exists())
        self.assertEqual(read(self.output / 'private/author.json')['oracle']['sensor_dbm'], 123.0)

    def test_journal_close_failure_is_preserved_without_pass(self):
        close = journal.OperatorJournal.close
        def fail_after_close(instance):
            close(instance)
            raise OSError('close reporting failure')
        with patch.object(journal.OperatorJournal, 'close', new=fail_after_close):
            result = self.run_case()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['error_code'], PREFIX + 'evidence_unavailable')
        self.assertTrue((self.output / 'operator/events.jsonl').is_file())
        self.assertFalse((self.output / 'public-result.json').exists())


if __name__ == '__main__':
    unittest.main()

"""D2-owned retained-byte replay checks; --fresh is a separate scripted mock run."""
import copy
from decimal import Decimal
import hashlib
import importlib
import inspect
import json
import os
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from labflow.store import canonical
from labflow.virtual_fleet.journal import read_operator_journal
from labflow.virtual_fleet.conducted_twin_result import build_conducted_twin_result

try:
    api = importlib.import_module('labflow.conducted_execution_result_finalizer')
except ModuleNotFoundError as error:
    if error.name != 'labflow.conducted_execution_result_finalizer':
        raise
    api = None


def C(value):
    return canonical(value).encode('utf-8')


def H(raw):
    return hashlib.sha256(raw).hexdigest()


FILES = {'request':'caller-request.json', 'setup_snapshot':'setup-snapshot.json',
         'operator_journal':'operator-journal.jsonl', 'legacy_report':'legacy-harness-report.json',
         'legacy_events':'legacy-harness-events.json'}
RUN = ROOT / '.local/DEV2-CONDUCTED-RESULT-FINALIZER-001' / ('checks-' + uuid.uuid4().hex)


class FinalizerTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(api, 'Assigned finalizer API is absent')
        value = os.environ.get('DGM_FINALIZER_REPLAY_ROOT')
        self.assertTrue(value, 'Provide explicit retained D2 replay fixtures; no execution fallback')
        self.fixtures = Path(value)
        self.work = RUN / self._testMethodName
        self.work.mkdir(parents=True)
        self.sequence = 0
        self.load('recorded')

    def load(self, case):
        self.sequence += 1
        source = self.fixtures / case
        self.evidence = self.work / ('evidence-' + str(self.sequence))
        self.evidence.mkdir()
        for leaf in FILES.values():
            if (source / leaf).is_file():
                shutil.copyfile(source / leaf, self.evidence / leaf)
        self.execution = json.loads((source / 'execution-receipt.json').read_bytes())
        self.original = C(self.execution)

    def call(self, **changes):
        pin = changes.pop('expected_execution_sha256',None)
        options = dict(expected_execution_sha256=H(C(self.execution)) if pin is None else pin, evidence_dir=self.evidence,
                       measurement_ref='event:17', workspace_root=self.work, artifact_name='result')
        options.update(changes)
        return api.finalize_conducted_execution_result(self.execution, **options)

    def failure(self, suffix=None, **changes):
        with self.assertRaises(api.ConductedExecutionResultFinalizerError) as got:
            self.call(**changes)
        error = got.exception
        if suffix:
            self.assertEqual(error.code, 'conducted_execution_result_finalizer_' + suffix)
        self.assertEqual(str(error), error.code)
        self.assertEqual(error.receipt['status'], 'held')
        self.assertFalse(error.receipt['execution_authority'])
        self.assertNotIn('SECRET_EXCEPTION', str(error))
        return error.receipt

    def repin(self, key, value):
        raw = C(value)
        (self.evidence / FILES[key]).write_bytes(raw)
        meta = self.execution['loop']['artifacts'][key]
        meta.update(bytes=len(raw), sha256=H(raw))
        self.execution['artifacts']['loop'] = copy.deepcopy(self.execution['loop']['artifacts'])

    def expected(self, ref='event:17'):
        return build_conducted_twin_result(self.execution['plan_input'],
            json.loads((self.evidence/'setup-snapshot.json').read_bytes()),
            read_operator_journal(self.evidence/'operator-journal.jsonl'),
            json.loads((self.evidence/'legacy-harness-report.json').read_bytes()), measurement_ref=ref)

    def test_public_contract_and_original_dto(self):
        self.assertEqual(api.__all__, ['finalize_conducted_execution_result', 'ConductedExecutionResultFinalizerError'])
        signature = inspect.signature(api.finalize_conducted_execution_result)
        self.assertEqual(list(signature.parameters), 'execution_receipt expected_execution_sha256 evidence_dir measurement_ref workspace_root artifact_name'.split())
        self.assertTrue(all(p.kind == inspect.Parameter.KEYWORD_ONLY for p in list(signature.parameters.values())[1:]))
        result = self.call()
        self.assertEqual(set(result), set('schema_version kind status execution_receipt input_files result artifact failure secondary_errors verification execution_authority'.split()))
        self.assertEqual(C(result['execution_receipt']), self.original)
        self.assertEqual(C(self.execution), self.original)
        result['execution_receipt']['status'] = 'caller_mutation'
        self.assertEqual(C(self.execution), self.original)

    def test_genuine_same_run_result_and_native_manifest(self):
        expected = self.expected()
        result = self.call()
        self.assertEqual(C(result['result']), C(expected))
        self.assertEqual(result['status'], 'stored')
        self.assertEqual(result['result']['status'], 'recorded')
        self.assertEqual(result['artifact']['storage']['status'], 'complete')
        marker = self.work/result['artifact']['storage']['commit_marker']
        self.assertEqual(H(marker.read_bytes()), result['artifact']['storage']['sha256'])
        for row in result['artifact']['files']:
            raw = (self.work/row['path']).read_bytes()
            self.assertEqual((len(raw),H(raw)), (row['bytes'],row['sha256']))
            if row['path'].endswith('result.json'):
                self.assertEqual(json.loads(raw), expected)
        # Independent arithmetic for this explicitly configured synthetic RF path.
        power = expected['raw_measurement']['packet']['power_dbm']
        loss = Decimal('10') + Decimal('0.5') + Decimal('20')
        self.assertEqual(Decimal(str(power)) + loss, Decimal('11'))
        self.assertFalse(result['verification']['full_task_verified'])
        self.assertEqual(expected['calculation']['conformity']['status'], 'not_assessed')

    def test_missing_and_unlisted_ref_are_not_selected(self):
        for index,ref in enumerate((None,'event:999')):
            with self.subTest(ref=ref):
                result = self.call(measurement_ref=ref,artifact_name='missing'+str(index))
                self.assertEqual(C(result['result']), C(self.expected(ref)))
                self.assertEqual(result['status'], 'stored')
                self.assertNotEqual(result['result']['status'], 'recorded')
                self.assertIsNone(result['result']['calculation']['corrected'])
                self.assertIsNone(result['result']['raw_measurement'])

    def test_missing_and_wrong_quantity_remain_original(self):
        for case in ('missing_quantity','wrong_quantity'):
            with self.subTest(case=case):
                self.load(case)
                result = self.call(artifact_name=case)
                self.assertEqual(C(result['result']), C(self.expected()))
                self.assertIsNone(result['result']['calculation']['corrected'])
                self.assertEqual(C(result['execution_receipt']), self.original)
                q = result['execution_receipt']['loop']['execution']['host_evidence']['quantity']
                if case == 'wrong_quantity':
                    self.assertIs(q['loss_compensation_sign'],False)
                    self.assertIs(q['loss_compensation_applied'],True)

    def test_receipt_pin_and_artifact_descriptor_cannot_escape(self):
        with patch.object(api, '_build_result', side_effect=AssertionError('BUILDER_MUST_NOT_RUN')):
            self.failure('execution_hash_mismatch',expected_execution_sha256='0'*64)
            self.execution['loop']['artifacts']['setup_snapshot']['path'] = '../canary'
            self.execution['artifacts']['loop'] = copy.deepcopy(self.execution['loop']['artifacts'])
            self.failure('artifact_descriptor_invalid')

    def test_tampered_fixed_file_is_refused_before_builder(self):
        path = self.evidence/'setup-snapshot.json'
        raw = path.read_bytes(); path.write_bytes(raw+b' ')
        with patch.object(api, '_build_result', side_effect=AssertionError('BUILDER_MUST_NOT_RUN')):
            self.failure('artifact_hash_mismatch')
        self.assertEqual(path.read_bytes(), raw+b' ')

    def test_same_run_report_swaps_are_refused_after_repin(self):
        report = json.loads((self.evidence/'legacy-harness-report.json').read_bytes())
        report['runtime_instance_id'] = 'different-runtime'
        self.repin('legacy_report', report)
        self.failure('binding_mismatch')

    def test_source6_and_host_topology_pin_are_checked(self):
        request = json.loads((self.evidence/'caller-request.json').read_bytes())
        request['execution']['source_settings']['power_dbm'] = 99
        self.repin('request',request)
        self.failure('binding_mismatch')
        self.load('recorded')
        self.execution['loop']['execution']['host_evidence']['topology_sha256'] = '0'*64
        self.failure('binding_mismatch')

    def test_original_producer_failure_survives_storage_and_writer_failure(self):
        self.load('producer_failure')
        original = copy.deepcopy(self.execution['failure'])
        result = self.call(measurement_ref=None)
        self.assertEqual(result['status'],'stored')
        self.assertEqual(result['failure'],original)
        self.assertEqual(result['execution_receipt']['loop']['budget']['producer_calls_started'],1)
        held = self.failure(measurement_ref=None)
        self.assertEqual(held['failure'],original)
        self.assertEqual(held['secondary_errors'][-1]['code'],'conducted_result_artifact_destination_exists')
        self.assertIsNotNone(held['result'])

    def test_partial_setup_and_journal_prefix_are_preserved(self):
        for case in ('partial_setup','journal_prefix'):
            with self.subTest(case=case):
                self.load(case)
                before = {p.name:p.read_bytes() for p in self.evidence.iterdir()}
                held = self.failure(measurement_ref=None)
                self.assertEqual(held['failure'],self.execution['failure'])
                self.assertEqual(C(held['execution_receipt']), self.original)
                self.assertEqual(before,{p.name:p.read_bytes() for p in self.evidence.iterdir()})

    def test_no_nested_ref_or_wildcard_file_search(self):
        step = self.execution['loop']['steps'][0]
        step['producer']['receipt']['artifacts']['stderr']['path'] = '../DO_NOT_OPEN_SECRET'
        original = Path.open
        opened = []
        def bounded(path,*args,**kwargs):
            opened.append(path)
            self.assertNotIn('DO_NOT_OPEN_SECRET',str(path))
            return original(path,*args,**kwargs)
        with patch.object(Path,'open',bounded), patch.object(Path,'rglob',side_effect=AssertionError('NO_SCAN')):
            result = self.call()
        self.assertEqual(result['status'],'stored')
        self.assertEqual([p.name for p in opened if p.name=='operator-journal.jsonl'],['operator-journal.jsonl'])

    def test_control_identity_at_read_builder_writer_and_close(self):
        for target,attribute in ((api._native,'_read_descriptor'),(api,'_build_result'),
                                  (api,'_write_result'),(api._native._WindowsIO,'close')):
            for control in (KeyboardInterrupt('CONTROL'),SystemExit(9),GeneratorExit(),MemoryError('CONTROL')):
                with self.subTest(stage=attribute,control=type(control).__name__):
                    close = api._native._WindowsIO.close
                    def closed_control(backend):
                        close(backend)
                        raise control
                    effect = closed_control if attribute=='close' else control
                    with patch.object(target,attribute,side_effect=effect,autospec=attribute=='close'):
                        with self.assertRaises(type(control)) as got:
                            self.call(artifact_name='control'+uuid.uuid4().hex)
                    self.assertIs(got.exception,control)

    def test_native_bounds_and_unsupported_platform_do_not_fallback(self):
        self.execution['too_large'] = 'x'*262145
        self.failure('input_invalid')
        self.execution = json.loads(self.original)
        self.execution['cycle'] = self.execution
        self.failure('input_invalid',expected_execution_sha256='0'*64)
        self.execution = json.loads(self.original)
        with patch.object(api._native, '_WINDOWS_BACKEND_AVAILABLE',False):
            self.failure('unsupported_platform')

    def test_first_read_error_survives_later_close_error(self):
        close = api._native._WindowsIO.close
        def fail_after_close(backend):
            close(backend)
            raise OSError('SECRET_EXCEPTION_CLOSE')
        with patch.object(api._native,'_read_descriptor',side_effect=OSError('SECRET_EXCEPTION_READ')), \
                patch.object(api._native._WindowsIO,'close',fail_after_close):
            held = self.failure('evidence_read_failed')
        self.assertEqual(held['secondary_errors'][-1]['code'],'conducted_execution_result_finalizer_evidence_close_failed')

    def test_invalid_genuine_builder_result_is_saved_without_repair(self):
        from labflow.virtual_fleet.journal import OperatorJournal
        journal = read_operator_journal(self.evidence/'operator-journal.jsonl')
        setup = json.loads((self.evidence/'setup-snapshot.json').read_bytes())
        # Explicit tamper fixture: change an actual setup source number to bool,
        # then rebind the caller-declared file hashes. No runtime is constructed.
        row = next(row for row in reversed(setup) if row['device_id']=='dut' and row['action']=='configure')
        row['parameters']['power_dbm'] = True
        self.repin('setup_snapshot',setup)
        host = self.execution['loop']['execution']['host_evidence']
        host['setup_sha256'] = H(C(setup))
        provenance = journal['header']['provenance']; provenance['setup_sha256'] = H(C(setup))
        path = self.evidence/'operator-journal.jsonl'
        path.rename(self.evidence/'original-operator-journal.jsonl')
        writer = OperatorJournal(path,run_id=journal['header']['run_id'],
            runtime_instance_id=journal['header']['runtime_instance_id'],provenance=provenance)
        try:
            for event in journal['events']:
                writer(event)
        finally:
            writer.close()
        observed = read_operator_journal(path)
        meta = self.execution['loop']['artifacts']['operator_journal']
        meta.update(bytes=path.stat().st_size,sha256=H(path.read_bytes()))
        self.execution['artifacts']['loop'] = copy.deepcopy(self.execution['loop']['artifacts'])
        host.update(journal_file_sha256=observed['integrity']['file_sha256'],journal_head_sha256=observed['integrity']['head_sha256'])
        expected = self.expected()
        self.assertEqual(expected['status'],'invalid')
        result = self.call()
        self.assertEqual(C(result['result']),C(expected))
        self.assertEqual(result['status'],'stored')
        self.assertEqual(result['artifact']['result_status'],'invalid')
        scope = 'full_bound' if len(expected['binding'])==11 else 'report_ids_only'
        self.assertEqual(result['artifact']['verification']['binding_scope'],scope)

    def test_missing_fixed_file_never_uses_other_directory(self):
        path = self.evidence/'legacy-harness-report.json'
        other = self.work/'different-run'; other.mkdir()
        path.rename(other/path.name)
        with patch.object(Path,'rglob',side_effect=AssertionError('NO_FALLBACK_SEARCH')):
            held = self.failure('evidence_read_failed')
        self.assertIsNone(held['result'])
        self.assertTrue((other/path.name).is_file())

    def test_native_read_pin_blocks_in_place_write(self):
        original = api._native._read_descriptor
        attempted = []
        def read(*args,**kwargs):
            if not attempted:
                try:
                    with (self.evidence/'caller-request.json').open('wb'):
                        self.fail('Native read pin permitted a writer')
                except OSError:
                    attempted.append('write_denied')
            return original(*args,**kwargs)
        with patch.object(api._native,'_read_descriptor',side_effect=read):
            result = self.call()
        self.assertEqual(attempted,['write_denied'])
        self.assertEqual(result['status'],'stored')

    def test_read_close_failure_prevents_builder_and_publication(self):
        original = api._native._WindowsIO.close
        def close(backend):
            original(backend)
            raise OSError('SECRET_EXCEPTION_CLOSE')
        with patch.object(api._native._WindowsIO,'close',close), \
                patch.object(api,'_build_result',side_effect=AssertionError('NO_BUILD_AFTER_CLOSE_FAILURE')):
            held = self.failure('evidence_close_failed')
        self.assertIsNone(held['result'])
        self.assertFalse((self.work/'.local/conducted-result-artifacts/result').exists())

    def test_non_synthetic_and_unknown_loop_envelopes_are_rejected(self):
        self.execution['loop']['execution']['synthetic'] = False
        self.failure('unbound_execution')
        self.execution = json.loads(self.original)
        self.execution['loop']['unknown'] = 'unverified'
        self.failure('unbound_execution')

    def test_bool_measurement_ref_cannot_become_event_id(self):
        with patch.object(api,'_read_journal',side_effect=AssertionError('NO_READ')):
            self.failure('input_invalid',measurement_ref=True)


def prepare_facts_demo(root):
    """Saved synthetic request -> genuine context -> scripted strict analysis -> facts plan."""
    from labflow.active_intake import register_source, scan_source
    from labflow.intake_jobs import prepare_registered_synthetic_context
    from labflow.intake_model_boundary import build_analysis_prompt, decode_analysis_response
    from labflow.intake_facts_to_conducted_plan import build_conducted_plan_from_intake_facts
    from labflow.store import Store
    inbox = root/'synthetic-inbox'
    bundle = inbox/'SM-A176U-US-WIFI24-SYN'; bundle.mkdir(parents=True)
    lines = ['Synthetic engineering request; no physical or FCC approval.',
        'product_type: smartphone','model: SM-A176U','market: US',
        'purpose: Wi-Fi 2.4 GHz conducted engineering simulation',
        'Condition SYN-WIFI24-CH1; single authored synthetic operating condition.',
        'frequency: 2412 MHz; bandwidth: 20 MHz; on_average_power: 11 dBm; duty_cycle: 50 %; modulation: OFDM; crest_factor: 4 dB']
    (bundle/'request.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    # Keep the existing Store's hash filenames below this host's path limit.
    # This is a new disposable synthetic Store, never an operational database.
    store = Store(root/'is')
    try:
        register_source(store,'FINALIZER-FACTS-SYN',inbox,synthetic=True,settle_seconds=1)
        first = scan_source(store,'FINALIZER-FACTS-SYN',now=100,synthetic_only=True)
        second = scan_source(store,'FINALIZER-FACTS-SYN',now=101,synthetic_only=True)
        assert len(second['accepted'])==1
        item = second['accepted'][0]
        with store.connection() as con:
            revision = con.execute('SELECT fingerprint,files_json FROM intake_revisions WHERE intake_id=? AND revision=?',
                                   (item['intake_id'],item['revision'])).fetchone()
        selection = dict(source_id='FINALIZER-FACTS-SYN',intake_id=item['intake_id'],revision=item['revision'],
            job_id=item['job_id'],revision_fingerprint=revision['fingerprint'],files=json.loads(revision['files_json']))
        producer = 'SCRIPTED-MOCK-FINALIZER-FACTS'
        context = prepare_registered_synthetic_context(store,selection,producer_name=producer)
        prompt = build_analysis_prompt(context,producer_name=producer)
        document = context['documents'][0]
        def fact(field,value,line):
            return dict(field=field,value=value,status='explicit',evidence=[dict(path=document['path'],
                sha256=document['sha256'],line_start=line,line_end=line,quote=lines[line-1],role='request')])
        raw = dict(schema_version=1,producer=dict(kind='model',name=producer),identity='single',missing_fields=[],
            facts=[fact('product_type','smartphone',2),fact('model','SM-A176U',3),fact('market','US',4),
                   fact('purpose','Wi-Fi 2.4 GHz conducted engineering simulation',5),fact('features',lines[6],7)])
        response = C(raw)
        analysis = decode_analysis_response(response,context,producer_name=producer)
        method = dict(method_id='conducted_synthetic',method_version=1,metric='on',reference_plane='source_output')
        # This genuine facts API alone assembles source6 and source-cited basis.
        assembled = build_conducted_plan_from_intake_facts(context,analysis,expected_revision=context['revision'],
            expected_context_sha256=H(C(context)),method=method)
        artifacts = [('facts-scan-first.json',first),('facts-scan-accepted.json',second),('facts-selection.json',selection),
            ('facts-context.json',context),('facts-prompt.json',prompt),('facts-analysis.json',analysis),
            ('facts-plan-and-gaps.json',assembled)]
        (root/'facts-raw-scripted-response.json').write_bytes(response)
        for name,value in artifacts:
            (root/name).write_bytes(C(value))
        assert assembled['status']=='ready_for_simulation', 'Facts input is blocked; original gaps retained'
        return context,analysis,assembled['plan_input']
    finally:
        store.close()


def fresh_demo(measurement_ref, *, from_facts=False):
    """One new genuine runtime; patch only the declared mock producer boundary."""
    if not measurement_ref:
        raise ValueError('An explicit caller measurement_ref is required')
    import types
    if 'tests' not in sys.modules:
        namespace = types.ModuleType('tests'); namespace.__path__ = [str(ROOT/'tests')]
        sys.modules['tests'] = namespace
    from test_virtual_fleet_codex_virtual_loop import LoopTests, PROOF
    from labflow import intake_plan_virtual_execution as adapter
    from labflow.intake_conducted_twin_plan import build_conducted_twin_plan_input
    from labflow.virtual_fleet import codex_virtual_loop as loop
    from test_intake_conducted_twin_plan import fixture
    driver = LoopTests('test_public_signature_and_exports')
    driver._testMethodName = 'finalizer_fresh2_intake_facts_mock' if from_facts else 'finalizer_fresh_scripted_mock'
    try:
        driver.setUp()
        if from_facts:
            context,analysis,plan = prepare_facts_demo(driver.driver.root)
        else:
            context,analysis,options = fixture()
            options['source_settings'] = driver.declared_source()
            for key,value in options['source_settings'].items():
                options['basis'][key]['value'] = value
            plan = build_conducted_twin_plan_input(context,analysis,**options)
        assert plan['status']=='ready_for_simulation'
        directory = driver.driver.root/'fresh-execution'
        quantity = dict(metric='on',reference_plane='sensor_input',loss_compensation_applied=False,loss_compensation_sign=1)
        call_options = dict(driver.options,evidence_dir=directory,quantity=quantity,
            expected_revision=context['revision'],expected_context_sha256=H(C(context)),
            expected_plan_input_sha256=H(C(plan)))
        # Existing wrapper emits scripted proposals from public observations, then
        # calls the genuine concrete producer and strict decoder. No runtime,
        # configure, result, journal, builder, or writer monkeypatch is installed.
        with patch.object(loop,'_produce',side_effect=driver.produce), \
                patch('labflow.codex_cli_response.subprocess.Popen',side_effect=driver.driver.spawn):
            execution = adapter.run_intake_plan_virtual_execution(context,analysis,plan,**call_options)
        report = json.loads((directory/'legacy-harness-report.json').read_bytes())
        assert measurement_ref in report['evidence']['measurement_refs']
        original = C(execution)
        result = api.finalize_conducted_execution_result(execution,expected_execution_sha256=H(original),
            evidence_dir=directory,measurement_ref=measurement_ref,workspace_root=driver.driver.root,artifact_name='fresh-draft')
        assert C(execution)==original
        assert result['status']=='stored' and result['artifact']['storage']['status']=='complete'
        actual = result['result']
        assert actual['status']=='recorded'
        raw = Decimal(str(actual['raw_measurement']['packet']['power_dbm']))
        independent_loss = Decimal('10')+Decimal('0.5')+Decimal('20')
        corrected = actual['calculation']['corrected']
        assert corrected is not None and Decimal(str(corrected['value']))==raw+independent_loss==Decimal('11')
        expected_w = (Decimal(10)**(raw/Decimal(10)))/Decimal(1000)
        actual_w = Decimal(str(actual['calculation']['raw_power_w']['value']))
        assert abs(actual_w-expected_w)/expected_w < Decimal('1e-12')
        assert actual['calculation']['conformity']['status']=='not_assessed'
        assert not actual['verification']['hardware_verified']
        for name,value in [('fresh-plan.json',plan),('fresh-execution-receipt.json',execution),('fresh-finalizer-receipt.json',result)]:
            (driver.driver.root/name).write_bytes(C(value))
        summary = dict(kind='new_scripted_mock_intake_facts_integration' if from_facts else 'new_scripted_mock_integration',
            new_genuine_runtime_count=1,actual_model_calls=0,source6_assembly='genuine_cited_intake_facts' if from_facts else 'developer_declared',
            provider_calls=0,producer_mock_calls=execution['execution']['producer_calls_started'],
            run_id=report['run_id'],runtime_instance_id=report['runtime_instance_id'],measurement_ref=measurement_ref,
            raw_dbm=str(raw),independent_configured_loss_db=str(independent_loss),corrected_dbm=str(raw+independent_loss),
            result_status=actual['status'],storage_status=result['artifact']['storage']['status'],conformity='not_assessed',
            setup_journal_connected=execution['verification']['setup_journal_connected'],proof_directory=str(PROOF))
        (driver.driver.root/'fresh-summary.json').write_bytes(C(summary))
    finally:
        if not driver.doCleanups():
            raise RuntimeError('Fresh fixture cleanup failed; original evidence retained')
    print(json.dumps(summary,ensure_ascii=False))


if __name__ == '__main__':
    if '--fresh' in sys.argv or '--fresh-from-intake-facts' in sys.argv:
        import argparse
        parser = argparse.ArgumentParser()
        modes = parser.add_mutually_exclusive_group(required=True)
        modes.add_argument('--fresh',action='store_true')
        modes.add_argument('--fresh-from-intake-facts',action='store_true')
        parser.add_argument('--measurement-ref',required=True)
        arguments = parser.parse_args()
        fresh_demo(arguments.measurement_ref,from_facts=arguments.fresh_from_intake_facts)
    else:
        unittest.main()

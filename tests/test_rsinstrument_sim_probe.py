"""Synthetic boundary tests; no SDK installation, import or device operation."""
import copy
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from labflow import rsinstrument_sim_probe as sim


HASH = 'a'*64
KEYS = {'schema_version', 'kind', 'execution_mode', 'synthetic',
    'actual_vendor_simulation_executed', 'hardware_verified', 'model_execution_verified',
    'physical_model_verified', 'support_status', 'status', 'reason_code', 'sdk', 'observations', 'cleanup'}


def lock_fixture():
    versions = {'RsInstrument':'1.131.0','PyVISA':'1.15.0','typing_extensions':'4.12.2','defusedxml':'0.7.1'}
    files = [{'path': path, 'bytes': 0, 'sha256': hashlib.sha256(b'').hexdigest()} for path in
             ('RsInstrument/__init__.py', 'pyvisa/__init__.py','typing_extensions.py','defusedxml/__init__.py',
              *[name+'-'+version+'.dist-info/LICENSE' for name,version in versions.items()])]
    return {'schema_version': 1, 'kind': 'rsinstrument_simulation_dependency_lock', 'receipt_sha256': HASH,
        'python_version': '.'.join(map(str, sys.version_info[:3])), 'python_sha256': HASH, 'sdk_version': '1.131.0',
        'python_runtime':[{'path':path,'bytes':0,'sha256':hashlib.sha256(b'').hexdigest()} for path in
            ('Scripts/python.exe','Scripts/python312.dll','Scripts/python3.dll','Scripts/vcruntime140.dll',
             'Scripts/vcruntime140_1.dll','pyvenv.cfg','PYTHON-LICENSE.txt')],
        'distributions': [{'name': name, 'version': version, 'wheel_sha256': HASH,
            'license_path': name+'-'+version+'.dist-info/LICENSE', 'license_sha256': hashlib.sha256(b'').hexdigest()}
            for name,version in versions.items()], 'files': files}


def declared_receipt(configuration,pid=123):
    """Format-only declared fixture; never evidence that this test executed an SDK."""
    calls = [('open_simulation',None,'VisaSessionSim'),
        ('query_str','*IDN?','Rohde&Schwarz,SimulationDevice,100001,1.131.0.128'),
        ('query_str','DGM:UNVERIFIED:VALUE?','Simulating'),('write_str','SOURce:FREQuency 123456789',None),
        ('query_str','SOURce:FREQuency?','123456789'),('query_opc',None,True),('query_all_errors',None,None),
        ('reconnect',None,True),('query_str','SOURce:FREQuency?','Simulating'),('close',None,None)]
    observations,lines = [],[]
    for index,(api,command,response) in enumerate(calls):
        record = {'sequence':index,'api':api,'command':command,'state':'returned','response':response,'error_code':None}
        observations.append(record)
        lines.extend([{'event':'intent','sequence':index,'api':api,'command':command},
                      {'event':'observation','observation':record}])
    journal = b''.join(sim._json(value)+b'\n' for value in lines)
    receipt = {'schema_version':1,'kind':'rsinstrument_simulation_child_receipt','pid':pid,
        'dependency_lock_sha256':hashlib.sha256(configuration['lock_bytes']).hexdigest(),
        'implementation_sha256':sim._implementation_sha256(),'python_version':configuration['lock']['python_version'],
        'actual_vendor_simulation_executed':True,'status':'passed','reason_code':'validated',
        'sdk':{'name':'RsInstrument','version':'1.131.0','driver_build':'1.131.0.128','module_path':'RsInstrument/__init__.py',
               'module_sha256':hashlib.sha256(b'').hexdigest(),'simulation_selected':True,
               'session_class':'RsInstrument.Internal.VisaSessionSim.VisaSessionSim'},
        'observations':observations,'session_closed':True,'forbidden_io_attempts':[],
        'journal_sha256':hashlib.sha256(journal).hexdigest()}
    return receipt,journal


def receipt_prefix(receipt,observations):
    value = copy.deepcopy(receipt)
    value['observations'] = copy.deepcopy(observations)
    records = []
    for observation in value['observations']:
        records.extend([{'event':'intent','sequence':observation['sequence'],'api':observation['api'],
                         'command':observation['command']}, {'event':'observation','observation':observation}])
    journal = b''.join(sim._json(record)+b'\n' for record in records)
    value['journal_sha256'] = hashlib.sha256(journal).hexdigest()
    return value,journal


class SimulationBoundaryTests(unittest.TestCase):
    def setUp(self):
        local = Path(__file__).resolve().parents[1]/'.local/sdk-sim-tests'
        local.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=local)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.lock = lock_fixture()

    def call(self, **kwargs):
        return sim.probe_rsinstrument_simulation(
            python_executable=kwargs.pop('python_executable', str(self.root/'env/Scripts/python.exe')),
            dependency_manifest=kwargs.pop('dependency_manifest', self.lock),
            output_dir=kwargs.pop('output_dir', self.root/'output'), **kwargs)

    def assert_false_claims(self, result):
        self.assertEqual(set(result), KEYS)
        self.assertEqual((result['schema_version'], result['kind'], result['execution_mode']),
                         (1, 'rsinstrument_simulation_probe', 'vendor_sdk_simulation'))
        self.assertIs(result['synthetic'], True)
        for key in ('actual_vendor_simulation_executed', 'hardware_verified',
                    'model_execution_verified', 'physical_model_verified'):
            self.assertIs(result[key], False)
        self.assertEqual(result['support_status'], 'not_assessed')
        self.assertNotEqual(result['status'], 'passed')

    def test_configuration_errors_precede_filesystem_process_and_network(self):
        cases = [{'timeout_seconds': value} for value in (True, 0, -1, 61, float('nan'), float('inf'), '1')]
        cases += [{'python_executable': value} for value in (None, [], 'python', 'https://vendor.invalid/python.exe', 'C:relative/python.exe')]
        for kwargs in cases:
            with self.subTest(kwargs=kwargs), patch.object(Path, 'stat') as stat, \
                 patch.object(Path, 'lstat') as lstat, patch('os.open') as writes, \
                 patch.object(sim, '_launch_child') as child, patch('socket.socket') as network:
                with self.assertRaisesRegex(ValueError, '^simulation_configuration_invalid$'):
                    self.call(**kwargs)
                for call in (stat, lstat, writes, child, network): call.assert_not_called()

    def test_manifest_errors_are_pure_and_never_launch(self):
        bad = []
        for key, value in [('schema_version', True), ('receipt_sha256','X'*64), ('python_sha256','0'*63),
                           ('kind','other'), ('sdk_version',''), ('files', []), ('distributions', [])]:
            manifest = copy.deepcopy(self.lock)
            manifest[key] = value
            bad.append(manifest)
        manifest = copy.deepcopy(self.lock)
        manifest['device_address'] = 'TCPIP::secret::INSTR'
        bad.append(manifest)
        manifest = copy.deepcopy(self.lock)
        manifest['files'][0]['path'] = '../arbitrary.py'
        bad.append(manifest)
        manifest = copy.deepcopy(self.lock)
        manifest['files'][0]['bytes'] = True
        bad.append(manifest)
        manifest = copy.deepcopy(self.lock)
        manifest['files'].append(copy.deepcopy(manifest['files'][0]))
        bad.append(manifest)
        manifest = copy.deepcopy(self.lock)
        manifest['distributions'][0]['name'] = 'arbitrary_module'
        bad.append(manifest)
        for manifest in bad:
            with self.subTest(manifest=manifest), patch.object(Path, 'stat') as reads, \
                 patch.object(Path, 'lstat') as lstats, patch.object(sim, '_launch_child') as child:
                with self.assertRaisesRegex(ValueError, '^simulation_manifest_invalid$'):
                    self.call(dependency_manifest=manifest)
                reads.assert_not_called()
                lstats.assert_not_called()
                child.assert_not_called()

    def test_lock_snapshot_is_detached_and_strict_json(self):
        frozen = sim._configuration(str(self.root/'env/Scripts/python.exe'), self.lock, 1)
        self.lock['files'][0]['sha256'] = 'b'*64
        self.assertEqual(frozen['lock']['files'][0]['sha256'], hashlib.sha256(b'').hexdigest())
        cycle = lock_fixture()
        cycle['files'].append(cycle)
        with self.assertRaisesRegex(ValueError, '^simulation_manifest_invalid$'):
            self.call(dependency_manifest=cycle)

    def test_unapproved_receipt_has_evidence_without_runtime_or_child(self):
        with patch.object(sim, '_verify_runtime') as runtime, patch.object(sim, '_launch_child') as child:
            result = self.call()
            runtime.assert_not_called()
            child.assert_not_called()
        self.assert_false_claims(result)
        self.assertEqual((result['status'], result['reason_code']), ('unavailable', 'dependency_receipt_unapproved'))
        output = self.root/'output'
        self.assertEqual(json.loads((output/'dependency-lock.json').read_text(encoding='utf-8')), self.lock)
        self.assertEqual(json.loads((output/'result.json').read_text(encoding='utf-8')), result)
        self.assertTrue((output/'manifest.json').is_file())

    def test_existing_output_and_missing_parent_are_never_changed(self):
        existing = self.root/'existing'
        existing.mkdir()
        sentinel = existing/'sentinel'
        sentinel.write_bytes(b'unchanged')
        for output in (existing, sentinel, self.root/'missing/leaf'):
            with patch.object(sim, '_launch_child') as child, patch('os.open') as writes:
                with self.assertRaisesRegex(ValueError, '^simulation_output_invalid$'):
                    self.call(output_dir=output)
                child.assert_not_called()
                writes.assert_not_called()
        self.assertEqual(sentinel.read_bytes(), b'unchanged')

    def test_reparse_parent_is_rejected_before_writing(self):
        from types import SimpleNamespace
        original = Path.lstat
        def reparse(path):
            value = original(path)
            return SimpleNamespace(st_mode=value.st_mode, st_file_attributes=1024) if path == self.root else value
        with patch.object(Path, 'lstat', reparse), patch('os.open') as writes, patch.object(sim,'_launch_child') as child:
            with self.assertRaisesRegex(ValueError, '^simulation_output_invalid$'):
                self.call()
            writes.assert_not_called()
            child.assert_not_called()

    def test_approved_but_missing_runtime_is_distinguished(self):
        with patch.object(sim, '_APPROVED_RECEIPT_SHA256', HASH), patch.object(sim, '_launch_child') as child:
            result = self.call()
            child.assert_not_called()
        self.assert_false_claims(result)
        self.assertEqual(result['reason_code'], 'runtime_unavailable')

    def test_socket_and_dns_sentinels_block_before_native_io(self):
        with sim._Sentinels() as guard:
            for call, args in ((socket.socket, ()), (socket.create_connection, (('127.0.0.1', 1),)),
                               (socket.getaddrinfo, ('device.invalid', 5025)), (socket.gethostbyname, ('device.invalid',))):
                with self.assertRaises(sim._ForbiddenIO): call(*args)
        self.assertEqual(len(guard.attempts), 4)
        self.assertTrue(all(value in {'socket', 'dns'} for value in guard.attempts))

    def test_resource_manager_is_blocked_before_provider_creation(self):
        from types import SimpleNamespace
        calls = []
        original = lambda *args, **kwargs: calls.append('real provider')
        highlevel = SimpleNamespace(ResourceManager=original)
        visa = SimpleNamespace(ResourceManager=original, highlevel=highlevel)
        with sim._Sentinels() as guard:
            guard.guard_visa(visa)
            for call in (visa.ResourceManager, highlevel.ResourceManager):
                with self.assertRaises(sim._ForbiddenIO): call()
        self.assertEqual(calls, [])
        self.assertEqual(guard.attempts, ['visa_resource_manager', 'visa_resource_manager'])
        self.assertIs(visa.ResourceManager, original)

    def test_own_child_cleanup_kills_only_after_terminate_timeout(self):
        actions = []
        class Child:
            returncode = None
            def poll(self): return self.returncode
            def terminate(self): actions.append('terminate')
            def kill(self):
                actions.append('kill')
                self.returncode = 1
            def wait(self, timeout):
                actions.append(('wait',timeout))
                if self.returncode is None: raise subprocess.TimeoutExpired('owned',timeout)
        self.assertTrue(sim._stop(Child()))
        self.assertEqual(actions, ['terminate',('wait',.25),'kill',('wait',.25)])

    def test_journal_is_exclusive_and_bounded(self):
        path = self.root/'journal.jsonl'
        journal = sim._Journal(path)
        journal.append({'event':'fixture','response':'data'})
        with self.assertRaises(sim._OutputLimit): journal.append({'response':'x'*65536})
        journal.close()
        self.assertLessEqual(path.stat().st_size,65536)
        self.assertEqual(json.loads(path.read_text(encoding='utf-8')), {'event':'fixture','response':'data'})
        with self.assertRaises(FileExistsError): sim._Journal(path)

    def test_source_tree_cannot_be_changed_by_redeclaring_manifest_hashes(self):
        python = self.root/'env/Scripts/python.exe'
        python.parent.mkdir(parents=True)
        python.write_bytes(b'synthetic non-executable file')
        (python.parent.parent/'pyvenv.cfg').write_text('fixture',encoding='utf-8')
        site = python.parent.parent/'Lib/site-packages'
        site.mkdir(parents=True)
        self.lock['python_sha256'] = hashlib.sha256(python.read_bytes()).hexdigest()
        for item in self.lock['files']:
            path = site/item['path']
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(b'')
        with patch.object(sim,'_APPROVED_RECEIPT_SHA256',HASH), patch.object(sim,'_launch_child') as child:
            result = self.call(python_executable=python)
            child.assert_not_called()
        self.assert_false_claims(result)
        self.assertEqual(result['reason_code'],'runtime_pin_mismatch')

    def test_real_session_constructor_has_a_separate_latched_sentinel(self):
        calls = []
        class RealSession:
            def __init__(self,*args): calls.append('real session')
        with sim._Sentinels() as guard:
            guard.guard_real_session(RealSession)
            with self.assertRaises(sim._ForbiddenIO): RealSession()
        self.assertEqual(calls,[])
        self.assertEqual(guard.attempts,['visa_session'])

    def test_unconfirmed_child_is_not_read_as_closed_evidence(self):
        class Child:
            pid,returncode = 123,None
            def poll(self): return None
            def terminate(self): pass
            def kill(self): pass
            def wait(self,timeout): raise subprocess.TimeoutExpired('owned',timeout)
        original = sim._read
        def read(path,limit):
            if Path(path).name in {'journal.jsonl','child-receipt.json'}: raise AssertionError('live child read')
            return original(path,limit)
        with patch.object(sim,'_APPROVED_RECEIPT_SHA256',HASH), \
             patch.object(sim,'_verify_runtime',return_value={'site_packages':'fixture','python':'fixture'}), \
             patch.object(sim,'_launch_child',return_value=Child()), patch.object(sim,'_read',side_effect=read):
            result = self.call(timeout_seconds=.001)
        self.assert_false_claims(result)
        self.assertEqual(result['reason_code'],'termination_failed')
        self.assertFalse(result['cleanup']['child_stopped'])
        self.assertFalse((self.root/'output/manifest.json').exists())

    def test_start_failure_has_one_attempt_and_sanitized_evidence(self):
        with patch.object(sim,'_APPROVED_RECEIPT_SHA256',HASH), \
             patch.object(sim,'_verify_runtime',return_value={'site_packages':'fixture','python':'fixture'}), \
             patch.object(sim,'_launch_child',side_effect=OSError('PRIVATE_CANARY')) as child:
            result = self.call()
        self.assert_false_claims(result)
        self.assertEqual(result['reason_code'],'child_start_failed')
        self.assertEqual(child.call_count,1)
        self.assertNotIn('PRIVATE_CANARY',json.dumps(result))

    def test_child_receipt_cannot_claim_simulation_without_journal(self):
        configuration = sim._configuration(str(self.root/'env/Scripts/python.exe'),self.lock,1)
        for data in (b'{}',b'{"status":"passed","status":"passed"}',b'NaN',b'x'*32769):
            with self.assertRaises((ValueError,sim._OutputLimit)):
                sim._decode_receipt(data,b'',configuration,123)

    def test_parent_deadline_terminates_its_actual_stdlib_child(self):
        import time
        children = []
        def launch(*args):
            child = subprocess.Popen([sys._base_executable,'-I','-S','-B','-c','import time; time.sleep(30)'],
                stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            children.append(child)
            return child
        started = time.monotonic()
        with patch.object(sim,'_APPROVED_RECEIPT_SHA256',HASH), \
             patch.object(sim,'_verify_runtime',return_value={'site_packages':'fixture','python':'fixture'}), \
             patch.object(sim,'_launch_child',side_effect=launch):
            result = self.call(timeout_seconds=.15)
        self.assertLess(time.monotonic()-started,2)
        self.assert_false_claims(result)
        self.assertEqual(result['status'],'timeout')
        self.assertTrue(result['cleanup']['child_stopped'])
        self.assertEqual(len(children),1)
        self.assertIsNotNone(children[0].poll())

    def test_deadline_includes_child_creation_before_waiting(self):
        import time
        class Child:
            pid,returncode = 123,0
            def poll(self): return 0
        def launch(*args):
            time.sleep(.03)
            return Child()
        with patch.object(sim,'_APPROVED_RECEIPT_SHA256',HASH), \
             patch.object(sim,'_verify_runtime',return_value={'site_packages':'fixture','python':'fixture'}), \
             patch.object(sim,'_launch_child',side_effect=launch):
            result = self.call(timeout_seconds=.01)
        self.assert_false_claims(result)
        self.assertEqual((result['status'],result['reason_code']),('timeout','deadline_exceeded'))

    def test_os_spawn_discards_stdio_and_never_replays_caller_main(self):
        configuration = sim._configuration(str(self.root/'env/Scripts/python.exe'),self.lock,1)
        with patch.object(sim.subprocess,'Popen') as launch:
            sim._launch_child(configuration,self.root/'output')
        args, kwargs = launch.call_args
        command = args[0]
        self.assertEqual(command[:6],[configuration['python'],'-I','-S','-B','-X','utf8'])
        self.assertEqual(Path(command[6]).resolve(),Path(sim.__file__).resolve())
        self.assertEqual(command[7:],["--child",str(self.root/'output')])
        self.assertEqual([kwargs[key] for key in ('stdin','stdout','stderr')],[subprocess.DEVNULL]*3)
        self.assertNotIn('PYTHONPATH',kwargs['env'])

    def test_response_size_limit_never_becomes_actual_execution(self):
        class Child:
            pid,returncode = 123,0
            def poll(self): return 0
        def launch(configuration,folder):
            (folder/'journal.jsonl').write_bytes(b'')
            (folder/'child-receipt.json').write_bytes(b'x'*32769)
            return Child()
        with patch.object(sim,'_APPROVED_RECEIPT_SHA256',HASH), \
             patch.object(sim,'_verify_runtime',return_value={'site_packages':'fixture','python':'fixture'}), \
             patch.object(sim,'_launch_child',side_effect=launch):
            result = self.call()
        self.assert_false_claims(result)
        self.assertEqual(result['reason_code'],'output_limit_exceeded')

    def test_consumed_child_receipt_drift_is_never_published(self):
        class Child:
            pid,returncode = 123,0
            def poll(self): return 0
        def launch(configuration,folder):
            (folder/'journal.jsonl').write_bytes(b'')
            (folder/'child-receipt.json').write_bytes(b'{}')
            return Child()
        def decode(*args):
            (self.root/'output/child-receipt.json').write_bytes(b'changed')
            return {'actual_vendor_simulation_executed':False,'status':'unavailable','reason_code':'sdk_unavailable',
                'sdk':None,'observations':[],'session_closed':None,'forbidden_io_attempts':[]}
        with patch.object(sim,'_APPROVED_RECEIPT_SHA256',HASH), \
             patch.object(sim,'_verify_runtime',return_value={'site_packages':'fixture','python':'fixture'}), \
             patch.object(sim,'_launch_child',side_effect=launch), patch.object(sim,'_decode_receipt',side_effect=decode):
            with self.assertRaisesRegex(ValueError,'^simulation_evidence_error$'):
                self.call()
        self.assertFalse((self.root/'output/result.json').exists())

    def test_receipt_binding_and_observation_attacks_are_rejected(self):
        configuration = sim._configuration(str(self.root/'env/Scripts/python.exe'),self.lock,1)
        receipt,journal = declared_receipt(configuration)
        self.assertEqual(sim._decode_receipt(sim._json(receipt),journal,configuration,123)['status'],'passed')
        attacks = []
        for key,value in [('pid',124),('pid',True),('schema_version',True),('dependency_lock_sha256','b'*64),
                ('implementation_sha256','c'*64),('python_version','3.13.0'),('status',[]),('session_closed',1),
                ('journal_sha256','d'*64),('actual_vendor_simulation_executed',1),('forbidden_io_attempts',['dns'])]:
            modified = copy.deepcopy(receipt)
            modified[key] = value
            attacks.append(modified)
        for key,value in [('simulation_selected',1),('module_path','C:/foreign/RsInstrument/__init__.py'),
                          ('module_sha256','e'*64),('version','1.0.0')]:
            modified = copy.deepcopy(receipt)
            modified['sdk'][key] = value
            attacks.append(modified)
        for modified in attacks:
            with self.subTest(modified=modified):
                with self.assertRaises(ValueError): sim._decode_receipt(sim._json(modified),journal,configuration,123)

    def test_failed_receipt_cannot_assert_execution_without_successful_entry(self):
        configuration = sim._configuration(str(self.root/'env/Scripts/python.exe'),self.lock,1)
        original,_ = declared_receipt(configuration)
        original.update(status='rejected',reason_code='sdk_operation_failed')
        failed = copy.deepcopy(original['observations'][0])
        failed.update(state='raised',response=None,error_code='sdk_operation_failed')
        wrong_class = copy.deepcopy(original['observations'][0])
        wrong_class['response'] = 'VisaSession'
        missing_class = copy.deepcopy(original['observations'][0])
        missing_class['response'] = None
        for name,observations in (('empty',[]),('raised',[failed]),('wrong-class',[wrong_class]),('missing-class',[missing_class])):
            with self.subTest(case=name):
                value,journal = receipt_prefix(original,observations)
                with self.assertRaises(ValueError):
                    sim._decode_receipt(sim._json(value),journal,configuration,123)

    def test_proven_entry_is_preserved_for_partial_sdk_failure(self):
        configuration = sim._configuration(str(self.root/'env/Scripts/python.exe'),self.lock,1)
        original,_ = declared_receipt(configuration)
        original.update(status='rejected',reason_code='sdk_operation_failed')
        observations = copy.deepcopy(original['observations'][:2])
        observations[1].update(state='raised',response=None,error_code='sdk_operation_failed')
        value,journal = receipt_prefix(original,observations)
        decoded = sim._decode_receipt(sim._json(value),journal,configuration,123)
        self.assertTrue(decoded['actual_vendor_simulation_executed'])
        self.assertEqual((decoded['status'],decoded['reason_code']),('rejected','sdk_operation_failed'))
        original.update(actual_vendor_simulation_executed=False,sdk=None,session_closed=None)
        value,journal = receipt_prefix(original,[])
        self.assertFalse(sim._decode_receipt(sim._json(value),journal,configuration,123)['actual_vendor_simulation_executed'])

    def test_false_execution_flag_cannot_erase_a_proven_entry(self):
        configuration = sim._configuration(str(self.root/'env/Scripts/python.exe'),self.lock,1)
        original,_ = declared_receipt(configuration)
        original.update(status='rejected',reason_code='sdk_operation_failed',actual_vendor_simulation_executed=False,sdk=None)
        value,journal = receipt_prefix(original,original['observations'][:1])
        with self.assertRaises(ValueError): sim._decode_receipt(sim._json(value),journal,configuration,123)

    def test_parent_rejects_empty_failed_receipt_without_executed_claim(self):
        class Child:
            pid,returncode = 123,0
            def poll(self): return 0
        def launch(configuration,folder):
            value,_ = declared_receipt(configuration)
            value.update(status='rejected',reason_code='sdk_operation_failed')
            value,journal = receipt_prefix(value,[])
            (folder/'journal.jsonl').write_bytes(journal)
            (folder/'child-receipt.json').write_bytes(sim._json(value))
            return Child()
        with patch.object(sim,'_APPROVED_RECEIPT_SHA256',HASH), \
             patch.object(sim,'_verify_runtime',return_value={'site_packages':'fixture','python':'fixture'}), \
             patch.object(sim,'_launch_child',side_effect=launch):
            result = self.call()
        self.assert_false_claims(result)
        self.assertEqual((result['status'],result['reason_code']),('rejected','evidence_error'))
        retained = json.loads((self.root/'output/child-receipt.json').read_text(encoding='utf-8'))
        self.assertTrue(retained['actual_vendor_simulation_executed'])
        self.assertEqual(retained['observations'],[])

    def test_journal_boolean_alias_and_missing_final_newline_are_rejected(self):
        configuration = sim._configuration(str(self.root/'env/Scripts/python.exe'),self.lock,1)
        receipt,journal = declared_receipt(configuration)
        for changed in (journal.replace(b'"sequence":1}',b'"sequence":true}',1),journal.rstrip(b'\n')):
            modified = copy.deepcopy(receipt)
            modified['journal_sha256'] = hashlib.sha256(changed).hexdigest()
            with self.assertRaises(ValueError): sim._decode_receipt(sim._json(modified),changed,configuration,123)

    def test_runtime_file_pins_contamination_and_python_config_are_independent_gates(self):
        python = self.root/'env/Scripts/python.exe'
        python.parent.mkdir(parents=True)
        for item in self.lock['python_runtime']:
            path = python.parent.parent/item['path']
            path.parent.mkdir(parents=True,exist_ok=True)
            data = b'non-executable fixture' if item['path']=='Scripts/python.exe' else b'fixture'
            path.write_bytes(data)
            item.update(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
        self.lock['python_sha256'] = hashlib.sha256(python.read_bytes()).hexdigest()
        self.lock['python_version'] = '3.12.4'
        site = python.parent.parent/'Lib/site-packages'
        for item in self.lock['files']:
            path = site/item['path']
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(b'')
        configuration = sim._configuration(str(python),self.lock,1)
        core = {Path(item['path']).name:item['sha256'] for item in self.lock['python_runtime'] if item['path'].startswith('Scripts/')}
        distributions = {item['name']:(item['version'],item['wheel_sha256']) for item in self.lock['distributions']}
        files_hash = hashlib.sha256(sim._json(sorted(self.lock['files'],key=lambda item:item['path']))).hexdigest()
        with patch.object(sim,'_PYTHON_CORE_PINS',core), patch.object(sim,'_DISTRIBUTION_PINS',distributions), \
             patch.object(sim,'_APPROVED_FILES_SHA256',files_hash), patch.object(sim,'_launch_child') as child:
            self.assertEqual(Path(sim._verify_runtime(configuration)['site_packages']),site.resolve())
            for path,code in ((site/'RsInstrument/__init__.py','runtime_pin_mismatch'),
                              (python.parent.parent/'pyvenv.cfg','runtime_pin_mismatch'),
                              (python.parent/'python312.dll','runtime_pin_mismatch')):
                original = path.read_bytes()
                path.write_bytes(b'changed')
                with self.assertRaisesRegex(sim._ProbeFailure,'^'+code+'$'): sim._verify_runtime(configuration)
                path.write_bytes(original)
            poison = site/'poison.pth'
            poison.write_bytes(b'import socket')
            with self.assertRaisesRegex(sim._ProbeFailure,'^import_contamination$'): sim._verify_runtime(configuration)
            child.assert_not_called()

    def test_foreign_preimported_module_and_dependency_version_are_rejected(self):
        from types import SimpleNamespace
        configuration = sim._configuration(str(self.root/'env/Scripts/python.exe'),self.lock,1)
        site = self.root/'site'
        site.mkdir()
        with patch.dict(sys.modules,{'RsInstrument.poison':SimpleNamespace(__file__=str(self.root/'foreign.py'))}):
            with self.assertRaisesRegex(sim._ProbeFailure,'^import_contamination$'):
                sim._imports_clean(site,self.lock)
        journal = sim._Journal(self.root/'version-journal.jsonl')
        try:
            distribution = SimpleNamespace(metadata={'Name':'RsInstrument'},version='0.0.0')
            with patch('importlib.metadata.distributions',return_value=[distribution]):
                result = sim._run_vendor(configuration,{'site_packages':str(site)},journal)
            self.assertFalse(result['actual_vendor_simulation_executed'])
            self.assertEqual(result['reason_code'],'sdk_version_mismatch')
            self.assertEqual(result['observations'],[])
        finally:
            journal.close()

    def test_evidence_write_error_never_launches_or_overwrites(self):
        with patch.object(sim, '_write_new', side_effect=OSError('PRIVATE_CANARY')), patch.object(sim, '_launch_child') as child:
            with self.assertRaisesRegex(ValueError, '^simulation_evidence_error$'):
                self.call()
            child.assert_not_called()
        self.assertTrue((self.root/'output').is_dir())


if __name__ == '__main__':
    unittest.main()

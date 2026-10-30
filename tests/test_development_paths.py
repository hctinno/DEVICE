"""Path migration uses disposable state under the approved runs directory only."""
import hashlib
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from tests.managed_fixture_paths import fixture_root

try:
    from labflow import development_paths as paths
except ImportError:
    paths = None


TEST_ROOT = fixture_root('runtime-paths-tests')


class DevelopmentPathsTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(paths, 'managed development path resolver is not implemented')
        TEST_ROOT.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=TEST_ROOT)
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name) / 'project'
        self.root = self.project / '.local' / 'development'
        self.repo = self.root / 'workspaces' / 'fixture'
        self.repo.mkdir(parents=True)
        self.layout = dict(schema_version=1, project_root_relative='../..',
            directories={k:k for k in ('integration','workspaces','runs','toolchains','archive')},
            workspaces=[dict(path='workspaces/fixture', role='migration', temporary=True)],
            path_aliases=[dict(from_='C:/autolab-original', to='integration'),
                dict(from_='C:/autolab-original/.local', to='runs/legacy/original/.local')],
            control_root='runs/control/DGMAutoLab')
        self.layout['path_aliases'] = [{'from': x['from_'], 'to': x['to']} for x in self.layout['path_aliases']]
        self.save_layout()

    def save_layout(self):
        (self.root / 'layout.json').write_text(json.dumps(self.layout), encoding='utf-8')

    def load(self):
        return paths.load_layout(self.repo)

    def test_discovers_managed_ancestor_and_resolves_relative_directories(self):
        p = self.load()
        self.assertEqual(p.project_root, self.project)
        self.assertEqual(p.directory('toolchains', 'python/3.14'), self.root / 'toolchains/python/3.14')
        self.assertEqual(p.output('case/results.json'), self.root / 'runs/case/results.json')
        self.assertEqual(p.control_root(), self.root / 'runs/control/DGMAutoLab')

    def test_alias_longest_prefix_is_case_insensitive_and_preserves_input(self):
        original = {'store_root': 'c:\\AUTOLAB-ORIGINAL\\.local\\u01', 'remaining': 0}
        raw = json.dumps(original).encode()
        self.assertEqual(self.load().reference(original['store_root']), self.root / 'runs/legacy/original/.local/u01')
        self.assertEqual(json.dumps(original).encode(), raw)
        self.assertEqual(self.load().reference('C:/autolab-original/labflow/a.py'), self.root / 'integration/labflow/a.py')

    def test_alias_is_component_bounded_and_unknown_old_checkout_is_rejected(self):
        for text in ['C:/autolab-original-other/u01', 'C:/autolab-unregistered/u01']:
            with self.subTest(text=text), self.assertRaises(paths.DevelopmentPathError):
                self.load().reference(text)

    def test_registered_managed_workspace_local_alias_can_use_short_run_id(self):
        self.layout['path_aliases'].append({'from':str(self.root/'workspaces/fixture/.local'),'to':'runs/d1'})
        self.save_layout()
        self.assertEqual(self.load().reference(self.root/'workspaces/fixture/.local/u01'),self.root/'runs/d1/u01')

    def test_traversal_absolute_output_and_device_paths_are_rejected(self):
        for text in ['../control', 'case/../control', '/outside', 'C:/outside', 'case//x', 'case/./x', 'NUL.txt']:
            with self.subTest(text=text), self.assertRaises(paths.DevelopmentPathError):
                self.load().output(text)
        for text in ['C:/autolab-original/.local/../escape', '\\\\?\\C:\\autolab-original\\u01']:
            with self.subTest(text=text), self.assertRaises(paths.DevelopmentPathError):
                self.load().reference(text)

    def test_layout_without_registration_or_with_escaping_alias_fails_closed(self):
        self.layout['path_aliases'][0]['to'] = '../outside'
        self.save_layout()
        with self.assertRaises(paths.DevelopmentPathError): self.load()
        (self.root/'layout.json').unlink()
        with self.assertRaises(paths.DevelopmentPathError): self.load()
        self.assertFalse((self.root/'runs/control').exists())

    def test_arbitrary_external_alias_cannot_convert_auth_or_cache_to_project_scope(self):
        self.layout['path_aliases'][0]['from'] = 'C:/Users/example/.codex/auth.json'
        self.save_layout()
        with self.assertRaises(paths.DevelopmentPathError): self.load()

    def test_native_control_root_missing_layout_has_no_appdata_fallback(self):
        from labflow import codex_registered_intake_host as native
        (self.root/'layout.json').unlink()
        with patch.object(paths, 'load_layout', side_effect=paths.DevelopmentPathError('layout_missing')):
            with self.assertRaises(native._Failure): native._control_root()
        self.assertFalse((self.root/'runs/control').exists())

    def test_managed_control_root_keeps_existing_spent_profile_in_place(self):
        from labflow import codex_registered_intake_host as native
        expected = self.root/'runs/control/DGMAutoLab/codex-intake-host'
        expected.mkdir(parents=True)
        marker = expected/'finished.json'; marker.write_bytes(b'{"remaining":0,"status":"finished"}')
        before = marker.read_bytes()
        with patch.object(paths, 'load_layout', return_value=self.load()):
            self.assertEqual(native._control_root(), expected)
        self.assertEqual(marker.read_bytes(), before)

    def test_unregistered_workspace_and_outside_cwd_do_not_pass_role_guard(self):
        for cwd in [self.root/'workspaces/unknown', self.project]:
            with self.subTest(cwd=cwd), self.assertRaises(paths.DevelopmentPathError):
                self.load().check_workspace(cwd, role='migration')
        self.assertEqual(self.load().check_workspace(self.repo, role='migration')['role'], 'migration')
        with self.assertRaises(paths.DevelopmentPathError):
            self.load().check_workspace(self.repo, role='integration')

    def test_workspace_guard_requires_an_existing_directory_for_cwd(self):
        file=self.repo/'file.txt'; file.write_bytes(b'fixture')
        for cwd in [self.repo/'missing',file]:
            with self.subTest(cwd=cwd), self.assertRaises(paths.DevelopmentPathError):
                self.load().check_workspace(cwd,role='migration')

    def test_reparse_target_is_rejected_before_file_io(self):
        outside = Path(self.temp.name)/'outside'; outside.mkdir()
        link = self.root/'runs'/'link'; link.parent.mkdir()
        if os.name == 'nt':
            command = "New-Item -ItemType Junction -Path '%s' -Target '%s' | Out-Null" % (link, outside)
            subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',command], check=True, capture_output=True)
            self.addCleanup(lambda: os.rmdir(link) if link.exists() else None)
        else:
            link.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(paths.DevelopmentPathError): self.load().output('link/new.json')

    def test_spent_sqlite_and_budget_bytes_read_back_without_reset(self):
        target = self.root/'runs/legacy/original/.local/u01'; target.mkdir(parents=True)
        ledger = target/'history.sqlite3'
        with closing(sqlite3.connect(ledger)) as con:
            con.execute('CREATE TABLE history(kind TEXT, payload TEXT)')
            con.executemany('INSERT INTO history VALUES(?,?)', [(k,json.dumps({'remaining':0})) for k in ['baseline','permit','reserved','consumed','finished']])
            con.commit()
        budget = target/'budget.json'; budget.write_text('{"calls":25,"limit":25,"remaining":0,"vertex_reserved_calls":6,"vertex_reserved_tokens":3072}')
        before = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [ledger,budget]}
        actual = self.load().reference('C:/autolab-original/.local/u01/history.sqlite3')
        with closing(sqlite3.connect(actual.as_uri()+'?mode=ro', uri=True)) as con:
            con.execute('PRAGMA query_only=ON')
            self.assertEqual(con.execute('SELECT kind FROM history').fetchall(), [(k,) for k in ['baseline','permit','reserved','consumed','finished']])
        self.assertEqual(json.loads(budget.read_text())['remaining'], 0)
        self.assertEqual({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [ledger,budget]}, before)

    def test_native_file_read_and_store_open_apply_alias_only_at_io_boundary(self):
        from labflow import codex_registered_intake_host as native
        from labflow.store import Store
        target = self.root/'runs/legacy/original/.local/u01'
        store = Store(target); store.close()
        artifact = target/'sample.json'; artifact.write_bytes(b'{"remaining":0}')
        before = hashlib.sha256((target/'lab.sqlite3').read_bytes()).hexdigest()
        with patch.object(paths, 'load_layout', return_value=self.load()):
            self.assertEqual(native._read(Path('C:/autolab-original/.local/u01/sample.json'), 100), b'{"remaining":0}')
            with Store.open_existing('C:/autolab-original/.local/u01') as opened:
                self.assertEqual(opened.root, target)
        self.assertEqual(hashlib.sha256((target/'lab.sqlite3').read_bytes()).hexdigest(), before)

    def test_authored_native_reservation_retains_original_config_path_binding(self):
        from tests.test_codex_registered_intake_host import RegisteredNativeHostTests
        helper=RegisteredNativeHostTests('test_genuine_once_with_known_fake_child_extends_history_and_closes_store')
        self.addCleanup(helper.doCleanups)
        parent=self.root/'runs/t';parent.mkdir(parents=True)
        temporary_directory=tempfile.TemporaryDirectory
        def local_temp(*args,**kwargs):
            kwargs.update(dir=parent,prefix='n')
            return temporary_directory(*args,**kwargs)
        with patch.object(tempfile,'TemporaryDirectory',side_effect=local_temp): helper.setUp()
        old='C:/autolab-original/.local/native-store'
        self.layout['path_aliases'].append({'from':old,'to':'runs/t/'+helper.root.name+'/store'})
        self.save_layout()
        helper.config['store_root']=old;helper.permit['store_root']=old
        helper.put('operator-control-v1.json',helper.config);helper.replace_event('permit',helper.permit)
        with patch.object(paths,'load_layout',return_value=self.load()):
            status,result,_,_=helper.invoke()
        self.assertEqual((status,result['status']),(0,'completed'),result)
        reserved=next(body for kind,_,body in helper.events() if kind=='reserved')
        self.assertEqual(reserved['store_root'],old)
        self.assertEqual(helper.config['store_root'],old)
        self.assertEqual(helper.calls,['version','model'])  # Known Python transport double only.

    def _typed_migrated_anchor(self):
        from tests.test_codex_registered_intake_host import RegisteredNativeHostTests
        helper=RegisteredNativeHostTests('test_genuine_once_with_known_fake_child_extends_history_and_closes_store')
        self.addCleanup(helper.doCleanups)
        parent=self.root/'runs/a';parent.mkdir(parents=True)
        temporary_directory=tempfile.TemporaryDirectory
        def local_temp(*args,**kwargs):
            kwargs.update(dir=parent,prefix='n')
            return temporary_directory(*args,**kwargs)
        with patch.object(tempfile,'TemporaryDirectory',side_effect=local_temp): helper.setUp()
        old=str(Path('C:/Users/TypedFixture/AppData/Local/DGMAutoLab/codex-intake-host'))
        self.layout['path_aliases'].append({'from':old,'to':'runs/a/'+helper.root.name+'/native-control'})
        self.save_layout()
        anchor=json.loads(json.dumps(helper.anchor))
        anchor['trust_boundary']['operator_control_directory']=old
        anchor['inherited_history']['actual_codex_model_processes']=25
        anchor['inherited_history']['known_total_before_this_host']=25
        return helper,anchor,old

    def test_migrated_appdata_anchor_matches_only_registered_actual_control_without_rewrite(self):
        helper,anchor,old=self._typed_migrated_anchor()
        raw=json.dumps(anchor,sort_keys=True).encode();before=hashlib.sha256(raw).hexdigest()
        with patch.object(paths,'load_layout',return_value=self.load()):
            helper.api()._anchor(anchor,helper.control)
        self.assertEqual(anchor['trust_boundary']['operator_control_directory'],old)
        self.assertEqual(hashlib.sha256(json.dumps(anchor,sort_keys=True).encode()).hexdigest(),before)
        self.assertFalse(anchor['admission']['permitted_to_dispatch_now'])
        self.assertEqual(anchor['new_model_processes'],0)
        self.assertFalse(anchor['new_budget_or_active_permit_issued'])

    def test_migrated_anchor_rejects_a_different_existing_host_directory(self):
        helper,anchor,_=self._typed_migrated_anchor()
        wrong=helper.root/'codex-conducted-workflow-host';wrong.mkdir()
        with patch.object(paths,'load_layout',return_value=self.load()):
            with self.assertRaises(helper.api()._Failure): helper.api()._anchor(anchor,wrong)

    def test_migrated_anchor_rejects_malformed_or_unregistered_boundary_references(self):
        helper,anchor,old=self._typed_migrated_anchor()
        for value in [old+'-other', 'C:/autolab-unregistered/control', old+'/../other',
                '\\\\server\\share\\control', '\\\\?\\C:\\control', {'path':old}]:
            body=json.loads(json.dumps(anchor));body['trust_boundary']['operator_control_directory']=value
            with self.subTest(value=value), patch.object(paths,'load_layout',return_value=self.load()):
                with self.assertRaises(helper.api()._Failure): helper.api()._anchor(body,helper.control)

    def test_migrated_anchor_rejects_a_reparse_inserted_after_alias_registration(self):
        helper,anchor,old=self._typed_migrated_anchor()
        link=helper.root/'alias';other=helper.root/'other';other.mkdir()
        self.layout['path_aliases'][-1]['to']='runs/a/'+helper.root.name+'/alias'
        self.save_layout();layout=self.load()
        if os.name=='nt':
            command="New-Item -ItemType Junction -Path '%s' -Target '%s' | Out-Null"%(link,other)
            subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',command],check=True,capture_output=True)
            self.addCleanup(lambda:os.rmdir(link) if link.exists() else None)
        else: link.symlink_to(other,target_is_directory=True)
        with patch.object(paths,'load_layout',return_value=layout):
            with self.assertRaises(helper.api()._Failure): helper.api()._anchor(anchor,helper.control)

    def test_migrated_anchor_rejects_same_path_with_changed_native_directory_identity(self):
        helper,anchor,_=self._typed_migrated_anchor();api=helper.api();native_path=api._path;calls=[]
        def swap_after_first(value,*,directory):
            result=native_path(value,directory=directory);calls.append(result)
            if len(calls)==1:
                helper.control.rename(helper.root/'retained-control');helper.control.mkdir()
            return result
        with patch.object(paths,'load_layout',return_value=self.load()),patch.object(api,'_path',side_effect=swap_after_first):
            with self.assertRaises(api._Failure): api._anchor(anchor,helper.control)
        self.assertEqual(len(calls),2)

    def test_typed_spent_migrated_anchor_reaches_history_guard_before_any_producer(self):
        from labflow.store import canonical
        helper,anchor,_=self._typed_migrated_anchor();helper.anchor=anchor
        helper.put('root-continuation-anchor-20261026-v1.json',anchor)
        anchor_sha=hashlib.sha256(canonical(anchor).encode()).hexdigest()
        helper.config['anchor_sha256']=anchor_sha;helper.permit['anchor_sha256']=anchor_sha
        helper.put('operator-control-v1.json',helper.config)
        baseline=dict(schema_version=1,kind='codex_intake_continuation_baseline',journal_id=helper.config['journal_id'],
            anchor_sha256=anchor_sha,inherited_history=anchor['inherited_history'])
        permit_id=helper.config['permit_id']
        reserved=dict(permit_id=permit_id,context_sha256='1'*64,registration_sha256=helper.config['registration_sha256'],
            store_root=helper.config['store_root'],requested_model=helper.permit['requested_model'],reserved_model_attempts=1)
        consumed=dict(permit_id=permit_id,reservation_sha256=hashlib.sha256(canonical(reserved).encode()).hexdigest())
        finished=dict(permit_id=permit_id,status='unknown',local_model_processes=0,cleanup_confirmed=True,
            producer_receipt=None,caller_receipt=None,once=None,errors=[])
        with closing(sqlite3.connect(helper.journal)) as con:
            con.execute('DELETE FROM codex_intake_history')
            con.executemany('INSERT INTO codex_intake_history(kind,permit_id,payload) VALUES(?,?,?)',
                [(k,None if k=='baseline' else permit_id,canonical(v)) for k,v in
                    [('baseline',baseline),('permit',helper.permit),('reserved',reserved),('consumed',consumed),('finished',finished)]])
            con.commit()
        protected=[helper.journal,helper.control/'operator-control-v1.json',helper.control/'root-continuation-anchor-20261026-v1.json']
        before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
        with patch.object(paths,'load_layout',return_value=self.load()): status,result,_,_=helper.invoke()
        self.assertEqual((status,result['status']),(3,'not_run'),result)
        self.assertEqual(result['phase'],'history')
        self.assertEqual(result['errors'][0]['code'],'codex_registered_intake_host_history_unsettled')
        self.assertEqual(result['history']['known_total_model_processes'],25)
        self.assertEqual(helper.calls,[])
        self.assertEqual([kind for kind,_,_ in helper.events()],['baseline','permit','reserved','consumed','finished'])
        self.assertEqual({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected},before)
        self.assertFalse((helper.control/'active-run.json').exists())

    def test_cli_checks_actual_branch_without_pin_to_old_task_branch(self):
        subprocess.run(['git','init','-b','codex/new-task',str(self.repo)], check=True, capture_output=True)
        script = Path(__file__).parents[1]/'scripts/check_development_paths.py'
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        base = [sys.executable, '-X', 'utf8', '-B', str(script), '--cwd', str(self.repo), '--role', 'migration']
        accepted = subprocess.run(base+['--expected-branch','codex/new-task'], cwd=self.repo, capture_output=True, text=True, encoding='utf-8', env=env)
        self.assertEqual(accepted.returncode, 0, accepted.stderr+accepted.stdout)
        result = json.loads(accepted.stdout)
        self.assertEqual(result['branch'], 'codex/new-task')
        self.assertFalse(result['execution_authority'])
        rejected = subprocess.run(base+['--expected-branch','codex/old-task'], cwd=self.repo, capture_output=True, text=True, encoding='utf-8', env=env)
        self.assertNotEqual(rejected.returncode, 0)


if __name__ == '__main__': unittest.main()

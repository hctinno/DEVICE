"""Managed runtime IO using synthetic files only; no SDK/auth/model execution."""
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from labflow import development_paths as paths

REPO=Path(__file__).parents[1]
FIXTURES=REPO.parents[1]/'runs/migration-20261031/toolchains/tests'


class ManagedRuntimeIOTests(unittest.TestCase):
    def setUp(self):
        FIXTURES.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=FIXTURES,prefix='m')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'.local/development'
        self.root.mkdir(parents=True)
        previous_cwd=Path.cwd();os.chdir(self.root);self.addCleanup(os.chdir,previous_cwd)
        self.doc=dict(schema_version=1,project_root_relative='../..',
            directories={k:k for k in ('integration','workspaces','runs','toolchains','archive')},
            workspaces=[],path_aliases=[{'from':'C:/autolab-toolchains/.local','to':'runs/i'},
                {'from':'C:/autolab-android/.local/android-runtime','to':'toolchains/android'}],
            control_root='runs/control/DGMAutoLab')
        self.layout=paths.DevelopmentPaths(self.root,self.doc)
        self.enterContext(patch.object(paths,'load_layout',return_value=self.layout))

    def test_default_core_init_creates_only_managed_state(self):
        from labflow import __main__ as cli
        out=io.StringIO()
        with patch.object(sys,'argv',['labflow','init']),redirect_stdout(out):
            self.assertEqual(cli.main(),0)
        observed=json.loads(out.getvalue())
        self.assertEqual(Path(observed['workspace']),self.root/'runs/state/labflow')
        self.assertTrue((self.root/'runs/state/labflow/lab.sqlite3').is_file())
        self.assertFalse((self.root/'data').exists())

    def test_core_virtual_default_and_explicit_output_reach_same_public_leaf(self):
        from labflow import __main__ as cli,virtual_scenarios
        seen=[]
        def run(output):seen.append(Path(output));return {'failed':0}
        with patch.object(virtual_scenarios,'run_virtual_scenarios',side_effect=run),redirect_stdout(io.StringIO()):
            with patch.object(sys,'argv',['labflow','virtual-check']):self.assertEqual(cli.main(),0)
            explicit=self.root/'runs/custom'
            with patch.object(sys,'argv',['labflow','virtual-check','--out',str(explicit)]):self.assertEqual(cli.main(),0)
        self.assertEqual(seen,[self.root/'runs/exports/virtual',explicit])

    def test_fixture_and_harness_default_outputs_are_fresh_managed_runs(self):
        from labflow import intake_fixture_check as intake
        from labflow.virtual_fleet import harness_check as harness
        from labflow import managed_harness_check as managed_harness
        seen=[]
        def intake_run(output,**kwargs):seen.append(Path(output));return {'summary':{'fixture_acceptance':'pass'},'workspace':None}
        def harness_run(output,**kwargs):seen.append(Path(output));return {'summary':{'passed':1,'fixture_trials':1}}
        with patch.object(intake,'run_fixture_flow',side_effect=intake_run),patch.object(harness,'run_fixture_suite',side_effect=harness_run), \
                patch.object(managed_harness,'check_development_workspace',return_value={'status':'ready'}), \
                patch.object(managed_harness,'load_layout',return_value=self.layout),redirect_stdout(io.StringIO()):
            self.assertEqual(intake.main([]),0);self.assertEqual(intake.main([]),0);self.assertEqual(managed_harness.main([]),0)
        self.assertEqual([p.parent for p in seen],[self.root/'runs/intake-fixture-check']*2+[self.root/'runs/fleet-harness-check'])
        self.assertNotEqual(seen[0],seen[1])

    def test_reference_demo_reservation_uses_managed_parent_without_server(self):
        from labflow import intake_reference_demo as demo
        reserved=demo._reserve(None)
        self.assertEqual(reserved.parent,self.root/'runs/intake-reference-demo')
        self.assertTrue(reserved.is_dir());self.assertEqual(len(reserved.name),32)

    def test_session_default_is_managed_and_reopen_preserves_checkpoint(self):
        from labflow import virtual_session
        VirtualSession=virtual_session.VirtualSession
        self.enterContext(patch.object(virtual_session,'_PRIVATE_ROOT',self.root/'legacy-private'))
        with VirtualSession.create('managed') as session:
            self.assertEqual(session._path,self.root/'runs/virtual_sessions/managed.session.json')
            before=session._path.read_bytes()
        with VirtualSession.open('managed') as reopened:
            self.assertEqual(reopened._path.read_bytes(),before)

    def test_package_default_writes_a_verified_zip_outside_source(self):
        spec=importlib.util.spec_from_file_location('package_handoff_test',REPO/'scripts/package_handoff.py')
        package=importlib.util.module_from_spec(spec);spec.loader.exec_module(package)
        source=self.root/'source';source.mkdir();(source/'README.md').write_bytes(b'controlled handoff')
        with patch.object(package,'ROOT',source),patch.object(package,'FILES',('README.md',)),patch.object(package.subprocess,'run'),redirect_stdout(io.StringIO()):
            self.assertEqual(package.main(),0)
        archives=list((self.root/'runs/handoff').rglob('*.zip'))
        self.assertEqual(len(archives),1);self.assertFalse((source/'dist').exists())

    def test_vertex_explicit_synthetic_credentials_resolve_alias_without_refresh(self):
        from labflow import vertex_response as vertex
        from test_vertex_response import settings
        target=self.root/'runs/i/vertex/adc.json';target.parent.mkdir(parents=True)
        raw=json.dumps(dict(type='authorized_user',client_id='typed-id',client_secret='typed-secret',
            refresh_token='typed-not-a-real-token',quota_project_id=settings()['quota_project_id'])).encode()
        target.write_bytes(raw)
        metadata=vertex.inspect_vertex_credentials(Path('C:/autolab-toolchains/.local/vertex/adc.json'),settings=settings())
        self.assertTrue(metadata['metadata_valid']);self.assertFalse(metadata['refresh_attempted'])
        self.assertEqual(target.read_bytes(),raw)
        with self.assertRaises(vertex.VertexResponseError):
            vertex.inspect_vertex_credentials(Path('C:/autolab-unregistered/adc.json'),settings=settings())

    def test_ui_and_profile_aliases_resolve_before_existing_validation(self):
        from labflow import ai_connection_ui as ui,ai_connection_profiles as profiles
        target=self.root/'runs/i/vertex/profile.json';target.parent.mkdir(parents=True)
        profile=profiles._defaults();profile['revision']=1
        raw=json.dumps(profile).encode();target.write_bytes(raw)
        old=Path('C:/autolab-toolchains/.local/vertex/profile.json')
        self.assertEqual(ui._private_path(old),target)
        self.assertEqual(profiles.load_profile(old),profile)
        self.assertEqual(target.read_bytes(),raw)

    def test_comparison_maps_all_four_paths_before_overlap_and_output_checks(self):
        from labflow import model_comparison as comparison
        parent=self.root/'runs/i/vertex';parent.mkdir(parents=True)
        old=Path('C:/autolab-toolchains/.local/vertex')
        actual=comparison._prepare_paths(old/'adc.json',old/'evidence',old/'budget.json',old/'approval.json',None)
        self.assertEqual(actual,(parent/'adc.json',parent/'evidence',parent/'budget.json',parent/'approval.json'))
        self.assertTrue((parent/'evidence').is_dir())
        with self.assertRaises(comparison.ModelComparisonError):
            comparison._prepare_paths(old/'same.json',old/'other-evidence',old/'same.json',old/'approval.json',None)

    def test_store_alias_is_admitted_by_store_before_frozen_native_io(self):
        from labflow.store import Store
        target=self.root/'runs/i/store'
        created=Store(target);created.close()
        before=hashlib.sha256((target/'lab.sqlite3').read_bytes()).hexdigest()
        with Store.open_existing('C:/autolab-toolchains/.local/store') as opened:
            self.assertEqual(opened.root,target)
        self.assertEqual(hashlib.sha256((target/'lab.sqlite3').read_bytes()).hexdigest(),before)

    def test_managed_packet_caller_refuses_a_source_checkout_as_new_output_workspace(self):
        from labflow.managed_control_packet_prepare import prepare_control_packet
        from labflow.control_packet_prepare import ControlPacketPrepareError
        with self.assertRaises(ControlPacketPrepareError) as caught:
            prepare_control_packet(self.root/'runs/source',expected_index_sha256='a'*64,
                workspace_root=self.root/'integration',packet_id='typed')
        self.assertEqual(caught.exception.code,'packet_prepare_path_invalid')
        self.assertFalse((self.root/'integration').exists())

    def test_android_owner_raw_legacy_path_is_not_rewritten_or_executed(self):
        from labflow import android_emulator_check as android
        runtime=self.root/'toolchains/android';runtime.mkdir(parents=True)
        inventory={}
        for name in android.NATIVE_PATHS:
            path=runtime/'sdk'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'TYPED NONEXECUTABLE')
            inventory[name]=hashlib.sha256(path.read_bytes()).hexdigest()
        owner=dict(runtime=str(Path('C:/autolab-android/.local/android-runtime')),completed=True,
            executables=inventory,inventory_version=2,file_inventory=inventory)
        raw=json.dumps(owner).encode();(runtime/android.OWNER_FILE).write_bytes(raw)
        with patch.object(android,'native',side_effect=AssertionError('SDK EXECUTION FORBIDDEN')):
            self.assertEqual(android.validate_runtime(runtime),owner)
            self.assertEqual(android.validate_runtime(Path(owner['runtime'])),owner)
        self.assertEqual((runtime/android.OWNER_FILE).read_bytes(),raw)
        owner['runtime']='C:/autolab-unregistered/runtime';(runtime/android.OWNER_FILE).write_text(json.dumps(owner))
        with self.assertRaises(android.BoundaryError):android.validate_runtime(runtime)


if __name__=='__main__':unittest.main()

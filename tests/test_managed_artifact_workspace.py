"""RF artifact default/legacy IO separation; no source-pin or SDK bypass."""
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stderr,redirect_stdout
from unittest.mock import patch
from labflow import development_paths as paths
from labflow import control_packet_prepare as native

REPO=Path(__file__).parents[1]
FIXTURES=REPO.parents[1]/'runs/migration-20261031/toolchains/artifact-tests'

class ManagedArtifactWorkspaceTests(unittest.TestCase):
    def setUp(self):
        FIXTURES.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=FIXTURES,prefix='a');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'.local/development';self.root.mkdir(parents=True)
        self.layout=paths.DevelopmentPaths(self.root,dict(schema_version=1,project_root_relative='../..',
            directories={k:k for k in ('integration','workspaces','runs','toolchains','archive')},
            workspaces=[],path_aliases=[{'from':'C:/autolab-legacy/.local','to':'runs/legacy'}],
            control_root='runs/control/DGMAutoLab'))
        self.enterContext(patch.object(paths,'load_layout',return_value=self.layout))

    def test_default_native_storage_creation_is_managed_and_does_not_create_source_local(self):
        from labflow.managed_artifact_workspace import artifact_local_root
        backend=native._WindowsIO();self.addCleanup(backend.close)
        root=artifact_local_root(backend=backend,create=True)
        self.assertEqual(root,self.root/'runs/rf-artifacts/.local')
        self.assertTrue(root.is_dir());self.assertTrue(root in backend.directories)

    def test_legacy_workspace_reference_maps_local_only_for_read_and_never_creates(self):
        from labflow.managed_artifact_workspace import artifact_local_root
        root=artifact_local_root(workspace_root='C:/autolab-legacy')
        self.assertEqual(root,self.root/'runs/legacy');self.assertFalse(root.exists())
        with self.assertRaises(ValueError):artifact_local_root(workspace_root='C:/autolab-legacy',create=True)
        with self.assertRaises(ValueError):artifact_local_root(workspace_root='C:/Users/fixture/.codex')

    def test_reader_missing_default_and_explicit_legacy_do_not_create_either_namespace(self):
        from labflow.virtual_fleet.rf_signal_read import read_rf_signal_run,RfSignalReadError
        for kwargs in ({},{'workspace_root':'C:/autolab-legacy'}):
            with self.assertRaises(RfSignalReadError) as caught:read_rf_signal_run('Missing',**kwargs)
            self.assertEqual(caught.exception.code,'rf_signal_read_not_found')
        self.assertFalse((self.root/'runs').exists())

    def test_writer_frozen_source_pin_mismatch_fails_before_any_storage_creation(self):
        from labflow.virtual_fleet import rf_signal_cli as cli
        out,err=io.StringIO(),io.StringIO()
        with redirect_stdout(out),redirect_stderr(err):
            status=cli.main(['--scenario','cw_peak','--seed','0','--run-name','FrozenPinCheck'])
        self.assertNotEqual(status,0)
        self.assertEqual(json.loads(err.getvalue())['error']['code'],'rf_signal_cli_input_changed')
        self.assertFalse((self.root/'runs').exists())

    def test_typed_native_publication_and_genuine_reader_share_managed_namespace(self):
        from labflow.managed_artifact_workspace import artifact_local_root
        from labflow.virtual_fleet import rf_signal_waveform_observation as writer
        from labflow.virtual_fleet import rf_signal_waveform_observation_read as reader
        from tests.test_virtual_fleet_rf_signal_waveform_observation_read import literal
        backend=native._WindowsIO();self.addCleanup(backend.close)
        local=artifact_local_root(backend=backend,create=True)
        tree=native._Tree(local,backend)
        bundle=literal();state=dict(phase=None,operation='typed_io_only',attempted=False,leaf=None)
        # A typed prebuilt historical bundle tests publication IO only. The live
        # producer/source gate is tested separately and is never bypassed here.
        summary=writer._persist(tree,[],bundle,state)
        folder=local/'rf-waveform-observations/literal_obs'
        before=(folder/'observation.json').read_bytes()
        self.assertEqual(summary['storage']['path'],'.local/rf-waveform-observations/literal_obs/observation.json')
        observed=reader.read_rf_baseband_observation('literal_obs',expected_summary=summary)
        self.assertIs(observed['execution_authorized'],False)
        self.assertIs(observed['rerun_authorized'],False)
        self.assertEqual((folder/'observation.json').read_bytes(),before)
        self.assertEqual((folder/'observation.pending.json').stat().st_ino,(folder/'observation.json').stat().st_ino)
        legacy=self.root/'runs/legacy/rf-waveform-observations/literal_obs';legacy.mkdir(parents=True)
        (legacy/'observation.pending.json').write_bytes(before)
        os.link(legacy/'observation.pending.json',legacy/'observation.json')
        historical=reader.read_rf_baseband_observation('literal_obs',expected_summary=summary,workspace_root='C:/autolab-legacy')
        self.assertEqual(historical,observed)
        self.assertEqual((legacy/'observation.json').read_bytes(),before)

if __name__=='__main__':unittest.main()

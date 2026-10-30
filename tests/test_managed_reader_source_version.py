"""Explicit reader-source revision; old records are never current authority."""
from copy import deepcopy
import hashlib
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from labflow import control_packet_prepare as native,development_paths as paths
from labflow.virtual_fleet import rf_signal_waveform_observation as writer
from labflow.virtual_fleet import rf_signal_waveform_observation_read as reader
from tests.test_virtual_fleet_rf_signal_waveform_observation_read import literal,canonical,summary_of,PINS,CURRENT_PINS

REPO=Path(__file__).parents[1]
ROOT=REPO.parents[1]/'runs/migration-20261031/toolchains/reader-version-tests'
VERSION='read048-managed-storage-v1'
NEW_PINS=[
    dict(role='read048',lf_bytes=26502,lf_sha256='f8c75251910a241bcc4557fe74c034c3e554726334f42f98cbab1d7ef0c6f77a'),
    dict(role='describe041',lf_bytes=44423,lf_sha256='f5471dde9786983152992e04fa2dade8b5ac927b1c25e5c0303c30bb664db1aa'),
    dict(role='waveform054',lf_bytes=7581,lf_sha256='7566fb5a90c538275d5f511a3335a68cf3b9e85d7f1cd92b44a11d992f569d1d'),
    dict(role='native_helper',lf_bytes=29100,lf_sha256='8cb516b60caf0f0c4655649415cc37fce4e47318c74f6916985756c2b97c3fa7')]

class ManagedReaderSourceVersionTests(unittest.TestCase):
    def setUp(self):
        ROOT.mkdir(parents=True,exist_ok=True)
        temp=tempfile.TemporaryDirectory(dir=ROOT,prefix='v');self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)/'.local/development';self.root.mkdir(parents=True)
        layout=paths.DevelopmentPaths(self.root,dict(schema_version=1,project_root_relative='../..',
            directories={k:k for k in ('integration','workspaces','runs','toolchains','archive')},
            workspaces=[],path_aliases=[],control_root='runs/control/DGMAutoLab'))
        self.enterContext(patch.object(paths,'load_layout',return_value=layout))

    def decode(self,bundle):
        raw=canonical(bundle)+b'\n'
        return reader._bundle(bundle,summary_of(bundle,raw),bundle['request']['observation_name'])

    def new_bundle(self):
        source=literal()
        return writer._bundle(source['request'],source['source_snapshot'],source['declared_setup'],
            source['packet'],source['analysis'],source['recipe'])

    def test_current_writer_emits_named_coherent_tuple_accepted_by_readonly_reader(self):
        bundle=self.new_bundle()
        self.assertEqual(bundle['provenance']['dependency_source_version'],VERSION)
        self.assertEqual(bundle['provenance']['dependency_pins'],NEW_PINS)
        result=self.decode(bundle)
        self.assertIs(result['execution_authorized'],False)
        self.assertIs(result['rerun_authorized'],False)
        from labflow.managed_artifact_workspace import artifact_local_root
        backend=native._WindowsIO();self.addCleanup(backend.close)
        local=artifact_local_root(backend=backend,create=True)
        state=dict(phase=None,operation='typed_named_bundle_io',attempted=False,leaf=None)
        summary=writer._persist(native._Tree(local,backend),[],bundle,state)
        native_result=reader.read_rf_baseband_observation(bundle['request']['observation_name'],expected_summary=summary)
        self.assertEqual(native_result,result)
        stored=local/'rf-waveform-observations'/bundle['request']['observation_name']/'observation.json'
        self.assertEqual(stored.read_bytes(),canonical(bundle)+b'\n')

    def test_both_old_tuples_remain_readable_without_becoming_current_version(self):
        for pins in (PINS,CURRENT_PINS):
            bundle=literal();bundle['provenance']['dependency_pins']=deepcopy(pins)
            before=canonical(bundle)
            self.assertIs(self.decode(bundle)['execution_authorized'],False)
            self.assertEqual(canonical(bundle),before)
            self.assertNotIn('dependency_source_version',bundle['provenance'])

    def test_unknown_mixed_unlabelled_new_and_relabelled_old_tuples_are_rejected(self):
        bundle=literal();bundle['provenance']['dependency_pins']=deepcopy(NEW_PINS)
        bundle['provenance']['dependency_source_version']=VERSION
        cases=[]
        unknown=deepcopy(bundle);unknown['provenance']['dependency_source_version']='unapproved-next';cases.append(unknown)
        mixed=deepcopy(bundle);mixed['provenance']['dependency_pins'][1]=deepcopy(PINS[1]);cases.append(mixed)
        unlabelled=deepcopy(bundle);del unlabelled['provenance']['dependency_source_version'];cases.append(unlabelled)
        old=deepcopy(bundle);old['provenance']['dependency_pins']=deepcopy(CURRENT_PINS);cases.append(old)
        bad=deepcopy(bundle);bad['provenance']['dependency_pins'][0]['lf_sha256']='0'*64;cases.append(bad)
        for index,value in enumerate(cases):
            with self.subTest(index=index),self.assertRaises(ValueError):self.decode(value)

    def test_exact_current_source_gate_passes_then_rejects_drift_and_old_reader(self):
        fixture=self.root/'runs/source';fixture.mkdir(parents=True)
        for role,relative,size,digest in writer._PINS:
            target=fixture/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(REPO/relative,target)
        def check():
            backend=native._WindowsIO()
            try:return writer._pin_sources(native._Tree(fixture,backend))
            finally:backend.close()
        self.assertEqual(len(check()),4)
        target=fixture/'labflow/virtual_fleet/rf_signal_read.py'
        good=target.read_bytes();target.write_bytes(good+b'\n')
        with self.assertRaises(writer.RfSignalWaveformObservationError):check()
        old=REPO.parents[1]/'archive/toolchain-originals/20261031/source/labflow/virtual_fleet/rf_signal_read.py'
        target.write_bytes(old.read_bytes())
        with self.assertRaises(writer.RfSignalWaveformObservationError):check()

    def test_restored_parent_read_boundary_precedes_original_engine_mismatch(self):
        (self.root/'runs/rf-artifacts/.local/rf-signal-runs/Existing').mkdir(parents=True)
        request=dict(schema_version=1,run_name='Existing',observation_name='NoNewObservation',sample_rate_hz=8,sample_count=2,seed=7)
        with patch.object(writer._reader,'read_rf_signal_run',wraps=writer._reader.read_rf_signal_run) as read, \
                patch.object(writer._scenario,'describe_rf_signal_scenario',wraps=writer._scenario.describe_rf_signal_scenario) as describe, \
                patch.object(writer._waveform,'generate_rf_baseband_envelope',wraps=writer._waveform.generate_rf_baseband_envelope) as generate, \
                patch.object(writer._waveform,'analyze_rf_baseband_envelope',wraps=writer._waveform.analyze_rf_baseband_envelope) as analyze:
            with self.assertRaises(writer.RfSignalWaveformObservationError) as caught:writer.record_rf_baseband_observation(request)
        self.assertEqual([read.call_count,describe.call_count,generate.call_count,analyze.call_count],[1,0,0,0])
        self.assertEqual(caught.exception.code,'rf_signal_waveform_observation_dependency_changed')
        self.assertFalse((self.root/'runs/rf-artifacts/.local/rf-waveform-observations').exists())

if __name__=='__main__':unittest.main()

"""Literal-format unit fixtures; fake IO is not retained native acceptance."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
import errno
import hashlib
import importlib
import json
import os
import stat
import tempfile
import unittest

try:
    reader = importlib.import_module("labflow.virtual_fleet.rf_signal_waveform_observation_read")
except ModuleNotFoundError as error:
    if error.name != "labflow.virtual_fleet.rf_signal_waveform_observation_read":
        raise
    reader = None

PINS = [
    dict(role="read048",lf_bytes=25927,lf_sha256="3999ab598acdc86639d82f2e451295f378ebb3dc827f070c6d670f8cd2a59540"),
    dict(role="describe041",lf_bytes=44423,lf_sha256="bae395d27975dcfe5a64c5a4ea2ae86dccfa87f6d88c9e2c25b2283333a77cae"),
    dict(role="waveform054",lf_bytes=7581,lf_sha256="7566fb5a90c538275d5f511a3335a68cf3b9e85d7f1cd92b44a11d992f569d1d"),
    dict(role="native_helper",lf_bytes=29100,lf_sha256="8cb516b60caf0f0c4655649415cc37fce4e47318c74f6916985756c2b97c3fa7")]
FLAGS=dict(data_origin="authored_synthetic",synthetic=True,hardware_verified=False,
    physical_verified=False,ai_model_called=False,normative_compliance_verified=False,
    method_approval="not_assessed",regulatory_scope_complete=False,
    model_scope="normalized_baseband_sample_math_v1")

def canonical(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(",",":")).encode("utf-8")

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def literal():
    """Authored public-contract data, never obtained from a stored observation/API."""
    grid=dict(sample_rate_hz=8,sample_count=2,t0_seconds=0,interpolation="zero_order_hold")
    packet=dict(schema_version=1,kind="synthetic_rf_baseband_envelope",grid=deepcopy(grid),
        sample_unit="sqrt_mW",samples=[[0.0,-1.0],[0.0,-1.0]],verification=dict(FLAGS),
        execution_authorized=False,rerun_authorized=False)
    analysis=dict(schema_version=1,kind="synthetic_rf_baseband_analysis",grid=deepcopy(grid),
        input_sha256=sha(canonical(packet)),metrics=dict(window_seconds=0.25,
        observed_on_samples=2,observed_duty_cycle=1.0,time_mean_mw=1.0,on_mean_mw=1.0,
        peak_mw=1.0,energy_mw_s=0.25,time_mean_dbm=0.0,on_mean_dbm=0.0,peak_dbm=0.0),
        verification=dict(FLAGS),execution_authorized=False,rerun_authorized=False)
    saved={k:v for k,v in FLAGS.items() if k!="model_scope"}
    saved.update(execution_mode="synthetic_virtual_execution",waveform_implemented=False)
    source=dict(schema_version=1,kind="virtual_rf_signal_run_read",selection=dict(run_name="literal_run"),
        metadata=dict(request=dict(schema_version=1,scenario_id="cw_peak",seed=7),
        run_id="literal-run-id",runtime_instance_id="literal-runtime-id",execution_status="executed"),
        storage=dict(status="complete_verified",manifest_sha256="a"*64,verified_file_count=3,
        journal_status="complete",binding_verified=True),
        historical_assessment=dict(status="completed",verdict="pass",evaluator_id="rf_signal_scenario_v1",
        evidence_refs=["event:1"],summary_code="observed_signal_satisfied"),
        measurement=dict(value=-18.0,unit="dBm",quantity="peak",reference_plane="sensor_input"),
        measurement_goal_succeeded=True,outcome="measurement_observed",failure=None,
        verification=dict(saved=saved,current_scope="stored_hashes_and_public_journal",
        source_pins_verified=True,fresh_offline_evaluation_performed=False,producer_cli_exit_status=None),
        execution_authorized=False,rerun_authorized=False,error_code=None)
    declared=dict(source_signal=dict(frequency_hz=2450000000.0,power_dbm=0.0,bandwidth_hz=20000000.0,
        duty_cycle=1.0,crest_factor_db=0.0,modulation="CW"),
        sensor=dict(calibration_valid=True,acquisition_policy="triggered"),
        meter=dict(frequency_hz=2450000000.0,measurement_mode="peak",unit="dBm"),
        reference_plane="sensor_input",basis="declared_synthetic_policy")
    recipe=dict(schema_version=1,signal_kind="cw",sample_rate_hz=8,sample_count=2,on_power_dbm=0.0,pulse=None)
    bundle=dict(schema_version=1,kind="private_rf_baseband_math_observation",
        request=dict(schema_version=1,run_name="literal_run",observation_name="literal_obs",
        sample_rate_hz=8,sample_count=2,seed=7),source_snapshot=source,declared_setup=declared,
        recipe=recipe,packet=packet,analysis=analysis,provenance=dict(
        binding_scope="declared_source_projection_only",reference_plane="declared_dut_output",
        rf_manifest_sha256="a"*64,source_snapshot_sha256=sha(canonical(source)),
        packet_sha256=sha(canonical(packet)),dependency_pins=deepcopy(PINS)))
    return bundle

def summary_of(bundle,raw):
    p=bundle["provenance"];s=bundle["source_snapshot"];name=bundle["request"]["observation_name"]
    return dict(schema_version=1,kind="synthetic_rf_baseband_observation",observation_name=name,
        storage=dict(state="published",path=f".local/rf-waveform-observations/{name}/observation.json",
        bytes=len(raw),sha256=sha(raw)),
        source=dict(run_name=bundle["request"]["run_name"],run_id=s["metadata"]["run_id"],
        runtime_instance_id=s["metadata"]["runtime_instance_id"],manifest_sha256=p["rf_manifest_sha256"],
        snapshot_sha256=p["source_snapshot_sha256"]),
        math=dict(source_scenario_id="cw_peak",reference_plane="declared_dut_output",
        binding_scope="declared_source_projection_only",spec_sha256=sha(canonical(bundle["recipe"])),
        packet_sha256=p["packet_sha256"],analysis_sha256=sha(canonical(bundle["analysis"]))),
        verification=dict(FLAGS),execution_authorized=False,rerun_authorized=False)

class FakeIO:
    """Regular temp descriptors plus directory metadata; no Windows native evidence."""
    def __init__(self,root):
        self.root=root;self.directories={};self.held=[];self.paths={};self.close_calls=0
        self.after_open=None;self.close_error=None
        self.sentinel=root/"directory-fd";self.sentinel.write_bytes(b"fake-directory")
    def directory(self,path,*,create=False):
        assert not create
        if path not in self.directories:
            if not path.is_dir():raise FileNotFoundError()
            fd=os.open(self.sentinel,os.O_RDONLY);self.directories[path]=fd;self.paths[fd]=path;self.held.append(fd)
        return self.directories[path]
    def info(self,fd,*,directory=None):
        path=self.paths[fd]
        value=os.lstat(path)
        if stat.S_ISLNK(value.st_mode):raise reader._native.ControlPacketPrepareError("packet_prepare_path_invalid")
        if directory is True and not stat.S_ISDIR(value.st_mode):raise reader._native.ControlPacketPrepareError("packet_prepare_path_invalid")
        if directory is False and not stat.S_ISREG(value.st_mode):raise reader._native.ControlPacketPrepareError("packet_prepare_path_invalid")
        return value if directory is True else os.fstat(fd)
    def open_read(self,path,*,pin=False):
        assert pin
        fd=os.open(path,os.O_RDONLY|getattr(os,"O_BINARY",0));self.paths[fd]=path;self.held.append(fd)
        if self.after_open:self.after_open(path,fd)
        return fd
    def stat_file(self,path):
        raise AssertionError("transient stat_file is forbidden")
    def create_file(self,*args):
        raise AssertionError("reader writes")
    def link_receipt(self,*args):
        raise AssertionError("reader publishes")
    def close(self):
        self.close_calls+=1
        while self.held:os.close(self.held.pop())
        self.directories.clear()
        if self.close_error:raise self.close_error

_DEFAULT=object()

class ReaderContractTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(reader,"assigned reader API absent")
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.folder=self.root/".local/rf-waveform-observations/literal_obs"
        self.folder.mkdir(parents=True)
        helper=self.root/"labflow/control_packet_prepare.py";helper.parent.mkdir()
        helper.write_bytes((Path(__file__).resolve().parents[1]/"labflow/control_packet_prepare.py").read_bytes())
        self.bundle=literal();self.write()
        self.backends=[]
    def write(self,raw=None):
        raw=canonical(self.bundle)+b"\n" if raw is None else raw
        p=self.folder/"observation.pending.json";f=self.folder/"observation.json"
        for x in (p,f):
            if x.exists():x.unlink()
        p.write_bytes(raw);os.link(p,f)
        self.summary=summary_of(self.bundle,raw)
        return raw
    def run_reader(self,summary=_DEFAULT,name="literal_obs",configure=None):
        def factory():
            value=FakeIO(self.root);self.backends.append(value)
            if configure:configure(value)
            return value
        with mock.patch.object(reader,"_root",return_value=self.root),mock.patch.object(reader._native,"_WindowsIO",side_effect=factory):
            return reader.read_rf_baseband_observation(name,expected_summary=self.summary if summary is _DEFAULT else summary)
    def assert_code(self,suffix,**kwargs):
        with self.assertRaises(reader.RfSignalWaveformObservationReadError) as found:self.run_reader(**kwargs)
        self.assertEqual(found.exception.code,"rf_signal_waveform_observation_read_"+suffix)
    def test_public_shape_and_saved_math_copy(self):
        original=deepcopy(self.summary);value=self.run_reader()
        self.assertEqual(set(value),set("schema_version kind observation_name storage source math historical_context verification execution_authorized rerun_authorized".split()))
        self.assertEqual(value["math"],{k:self.bundle[k] for k in ("recipe","packet","analysis")})
        self.assertEqual(value["storage"]["scope"],"current_file_matches_recorded_summary")
        self.assertEqual(self.summary,original)
        self.assertFalse(value["execution_authorized"]);self.assertFalse(value["rerun_authorized"])
        self.assertEqual(self.backends[0].close_calls,1);self.assertFalse(self.backends[0].held)
        self.assertNotIn("request",value);self.assertNotIn("source_snapshot",value)
    def test_historical_fail_null_preserved(self):
        s=self.bundle["source_snapshot"];s["historical_assessment"].update(verdict="fail",summary_code="scenario_expectation_mismatch")
        s.update(outcome="assessment_failed",measurement_goal_succeeded=False)
        self.bundle["provenance"]["source_snapshot_sha256"]=sha(canonical(s));self.write()
        value=self.run_reader()["historical_context"]
        self.assertEqual(value["historical_assessment"]["verdict"],"fail")
        self.assertEqual(value["outcome"],"assessment_failed")
        self.assertIsNone(value["producer_cli_exit_status"])
        self.assertFalse(value["measurement_goal_succeeded"])
    def test_invalid_summary_before_backend(self):
        s=deepcopy(self.summary);s["extra"]=True
        self.assert_code("invalid_argument",summary=s);self.assertEqual(self.backends,[])
    def test_partial_and_marker_are_not_success(self):
        (self.folder/"observation.json").unlink();self.assert_code("incomplete")
        (self.folder/"observation.pending.json").unlink()
        (self.folder/"failure.json").write_bytes(b"do-not-parse")
        self.assert_code("incomplete")
    def test_recorded_hash_mismatch(self):
        s=deepcopy(self.summary);s["storage"]["sha256"]="0"*64
        self.assert_code("record_mismatch",summary=s)
    def test_internal_binding_is_not_recalculated(self):
        self.bundle["analysis"]["input_sha256"]="0"*64;self.write()
        self.assert_code("evidence_invalid")


    def test_cleanup_supervisor_exception_keeps_first_public_error(self):
        first=reader.RfSignalWaveformObservationReadError("rf_signal_waveform_observation_read_evidence_invalid")
        actual=reader._close
        def later(backend):
            actual(backend)
            raise KeyboardInterrupt("later observer")
        caught=None
        with mock.patch.object(reader,"_parse",side_effect=first),mock.patch.object(reader,"_close",side_effect=later):
            try:self.run_reader()
            except BaseException as e:caught=e
        self.assertIs(caught,first)

    def test_cleanup_supervisor_exception_keeps_first_systemexit(self):
        first=SystemExit(73);actual=reader._close
        def later(backend):
            actual(backend)
            raise RuntimeError("later")
        caught=None
        with mock.patch.object(reader,"_parse",side_effect=first),mock.patch.object(reader,"_close",side_effect=later):
            try:self.run_reader()
            except BaseException as e:caught=e
        self.assertIs(caught,first)

    def test_success_is_blocked_by_supervisor_exception(self):
        actual=reader._close
        def later(backend):
            actual(backend)
            raise RuntimeError("private observer")
        caught=None
        with mock.patch.object(reader,"_close",side_effect=later):
            try:self.run_reader()
            except BaseException as e:caught=e
        self.assertIsInstance(caught,reader.RfSignalWaveformObservationReadError)
        self.assertEqual(caught.code,"rf_signal_waveform_observation_read_unavailable")


    def test_names_and_plain_summary_limits_before_IO(self):
        class S(str):pass
        class D(dict):pass
        for name in (None,True,S("literal_obs"),"", "CON","../x","a"*65):
            with self.subTest(name=repr(name)):self.assert_code("invalid_argument",name=name)
        for s in (None,D(self.summary),{**self.summary,"schema_version":True}):
            with self.subTest(summary=type(s).__name__):self.assert_code("invalid_argument",summary=s)
        self.assertEqual(self.backends,[])

    def test_nested_summary_fields_are_exact(self):
        cases=[]
        for block,key,value in (("storage","bytes",True),("storage","sha256","F"*64),
                ("verification","hardware_verified",True),("source","run_id","x"*129),
                ("math","reference_plane","sensor_input")):
            s=deepcopy(self.summary);s[block][key]=value;cases.append(s)
        s=deepcopy(self.summary);s["storage"]["extra"]=None;cases.append(s)
        for s in cases:
            with self.subTest(summary=s):self.assert_code("invalid_argument",summary=s)
        self.assertFalse(self.backends)

    def test_parser_rejects_noncanonical_and_unbounded_JSON(self):
        original=canonical(self.bundle)
        samples=[original+b"\n\n",b"\xef\xbb\xbf"+original+b"\n",b"\xff\n",
            b'{"x":1,"x":2}\n',b'{"x":NaN}\n',original+b" {}\n",
            b"["*22+b"0"+b"]"*22+b"\n",b'{"x":'+b"1"*513+b"}\n",
            b'{"x":"'+b"a"*16385+b'"}\n',b"["+b"0,"*32768+b"0]\n"]
        for raw in samples:
            with self.subTest(raw_length=len(raw)):
                self.write(raw);self.assert_code("evidence_invalid")

    def test_size_cap_precedes_expected_record_mismatch(self):
        (self.folder/"observation.json").write_bytes(b"x"*3145730)
        self.assert_code("evidence_invalid")

    def test_empty_and_absent_storage(self):
        for p in self.folder.iterdir():p.unlink()
        self.assert_code("not_found")
        self.folder.rmdir();self.assert_code("not_found")

    def test_pending_and_final_must_be_same_object(self):
        p=self.folder/"observation.json";raw=p.read_bytes();p.unlink();p.write_bytes(raw)
        self.assert_code("incomplete")

    def test_marker_is_not_decoded(self):
        (self.folder/"failure.json").write_bytes(b"\xff"*32)
        original=reader._read
        def checked(fd,*args):
            for b in self.backends:self.assertNotEqual(b.paths.get(fd,Path("none")).name,"failure.json")
            return original(fd,*args)
        with mock.patch.object(reader,"_read",side_effect=checked):self.assert_code("incomplete")

    def test_bindings_pin_and_flags_are_checked(self):
        original=deepcopy(self.bundle)
        changes=[
          lambda b:b["request"].update(seed=6),
          lambda b:b["source_snapshot"]["metadata"].update(run_id="different-id"),
          lambda b:b["provenance"].update(source_snapshot_sha256="0"*64),
          lambda b:b["provenance"]["dependency_pins"][0].update(lf_bytes=True),
          lambda b:b["provenance"]["dependency_pins"][1].update(lf_sha256="0"*64),
          lambda b:b["recipe"].update(sample_count=1),
          lambda b:b["packet"]["grid"].update(t0_seconds=1),
          lambda b:b["packet"].update(samples=[[True,0.0],[0.0,0.0]]),
          lambda b:b["analysis"]["verification"].update(ai_model_called=True),
          lambda b:b["analysis"]["metrics"].update(observed_on_samples=True)]
        for change in changes:
            self.bundle=deepcopy(original);change(self.bundle);self.write()
            with self.subTest(change=change):self.assert_code("evidence_invalid")

    def test_metrics_are_copied_without_numerical_repair(self):
        self.bundle["analysis"]["metrics"].update(time_mean_mw=0.125,on_mean_dbm=None)
        self.write();got=self.run_reader()
        self.assertEqual(got["math"]["analysis"]["metrics"]["time_mean_mw"],0.125)
        self.assertIsNone(got["math"]["analysis"]["metrics"]["on_mean_dbm"])

    def test_no_private_seed_or_full_snapshot_is_projected(self):
        got=self.run_reader()
        self.assertNotIn(b'"seed":',canonical(got))
        self.assertNotIn(b'"declared_setup":',canonical(got))
        self.assertNotIn(b'"source_snapshot":',canonical(got))
        self.assertNotIn(b'"dependency_pins":',canonical(got))

    def test_argument_snapshot_is_detached_before_native_construction(self):
        original_id=self.summary["source"]["run_id"]
        got=self.run_reader(configure=lambda b:self.summary["source"].update(run_id="late-mutated"))
        self.assertEqual(got["source"]["run_id"],original_id)

    def test_initial_IO_failure_is_not_guessed_as_change(self):
        def configure(io):
            original=io.open_read
            def opening(path,**kwargs):
                if path.name=="observation.json":raise PermissionError(errno.EACCES,"private path")
                return original(path,**kwargs)
            io.open_read=opening
        self.assert_code("unavailable",configure=configure)

    def test_reparse_failure_is_fixed_path_error(self):
        def configure(io):
            original=io.info
            def info(fd,**kwargs):
                if io.paths.get(fd,Path("none")).name=="observation.json":
                    raise reader._native.ControlPacketPrepareError("packet_prepare_path_invalid")
                return original(fd,**kwargs)
            io.info=info
        self.assert_code("path_invalid",configure=configure)

    def test_post_marker_change_is_rejected(self):
        def configure(io):
            times={}
            def after(path,fd):
                times[path.name]=times.get(path.name,0)+1
                if path.name=="observation.json" and times[path.name]==2:
                    (self.folder/"failure.json").write_bytes(b"later")
            io.after_open=after
        self.assert_code("input_changed",configure=configure)

    def test_post_raw_and_helper_changes_are_rejected(self):
        actual=reader._bundle
        for target in (self.folder/"observation.json",self.root/"labflow/control_packet_prepare.py"):
            before=target.read_bytes()
            def changing(*args):
                result=actual(*args);target.write_bytes(before+b" ");return result
            with mock.patch.object(reader,"_bundle",side_effect=changing):
                self.assert_code("input_changed")
            target.write_bytes(before)

    def test_bad_helper_pin_blocks_before_observation_read(self):
        (self.root/"labflow/control_packet_prepare.py").write_bytes(b"unapproved")
        self.assert_code("unavailable")
        self.assertTrue(all(p.name not in ("observation.json","observation.pending.json") for b in self.backends for p in b.paths.values()))

    def test_first_BaseException_matrix_and_close_once(self):
        factories=[lambda:reader.RfSignalWaveformObservationReadError("rf_signal_waveform_observation_read_evidence_invalid"),
            lambda:KeyboardInterrupt("first"),lambda:SystemExit(71),lambda:GeneratorExit("first")]
        later=[lambda:RuntimeError("later"),lambda:KeyboardInterrupt("later"),lambda:SystemExit(72),lambda:GeneratorExit("later")]
        for make_first in factories:
            for make_later in later:
                first=make_first();second=make_later();caught=None
                with mock.patch.object(reader,"_parse",side_effect=first):
                    try:self.run_reader(configure=lambda b:setattr(b,"close_error",second))
                    except BaseException as e:caught=e
                with self.subTest(first=type(first).__name__,later=type(second).__name__):
                    self.assertIs(caught,first)
                    self.assertEqual(self.backends[-1].close_calls,1)
                    self.assertEqual(self.backends[-1].held,[])

    def test_close_only_failure_blocks_success(self):
        for error in (RuntimeError("private"),KeyboardInterrupt("k"),SystemExit(79),GeneratorExit("g")):
            caught=None
            try:self.run_reader(configure=lambda b:setattr(b,"close_error",error))
            except BaseException as e:caught=e
            if isinstance(error,Exception):
                self.assertIsInstance(caught,reader.RfSignalWaveformObservationReadError)
                self.assertEqual(caught.code,"rf_signal_waveform_observation_read_unavailable")
            else:self.assertIs(caught,error)
            self.assertFalse(self.backends[-1].held)

    def test_pop_then_interrupt_closes_independent_known_descriptors(self):
        first=KeyboardInterrupt("close pop");known=[]
        def configure(io):
            def interrupted():
                io.close_calls+=1;known.extend(io.held);io.held.pop();raise first
            io.close=interrupted
        caught=None
        try:self.run_reader(configure=configure)
        except BaseException as e:caught=e
        self.assertIs(caught,first);self.assertTrue(known)
        for fd in known:
            with self.assertRaises(OSError) as found:os.fstat(fd)
            self.assertEqual(found.exception.errno,errno.EBADF)

    def test_ineffective_native_close_is_actually_recovered(self):
        known=[]
        def configure(io):
            def ineffective():
                io.close_calls+=1;known.extend(io.held);io.held.clear();io.directories.clear()
            io.close=ineffective
        self.run_reader(configure=configure)
        for fd in known:
            with self.assertRaises(OSError) as found:os.fstat(fd)
            self.assertEqual(found.exception.errno,errno.EBADF)

    def test_persistent_close_failure_never_reports_success(self):
        close=os.close;blocked=set();counts={}
        def configure(io):
            original=io.open_read
            def opening(path,**kw):
                fd=original(path,**kw);blocked.add(fd);return fd
            io.open_read=opening
        def failing(fd):
            if fd in blocked:
                counts[fd]=counts.get(fd,0)+1
                raise PermissionError(errno.EACCES,"persistent")
            return close(fd)
        try:
            with mock.patch.object(reader.os,"close",side_effect=failing):
                self.assert_code("unavailable",configure=configure)
            self.assertTrue(self.backends[-1].held)
            self.assertTrue(all(n<=3 for n in counts.values()))
        finally:
            for fd in blocked:
                try:close(fd)
                except OSError:pass
            self.backends[-1].held.clear();self.backends[-1].directories.clear()

    def test_reused_descriptor_is_not_closed_as_old_owner(self):
        other=self.root/"other-owner";other.write_bytes(b"not reader-owned");opened=[]
        def configure(io):
            original=io.close
            def closing():
                original();opened.append(os.open(other,os.O_RDONLY))
            io.close=closing
        try:
            self.assert_code("unavailable",configure=configure)
            self.assertTrue(opened);self.assertEqual(os.fstat(opened[0]).st_ino,other.stat().st_ino)
        finally:
            for fd in opened:os.close(fd)

    def test_source_exposes_only_native_dependency(self):
        import ast
        tree=ast.parse(Path(reader.__file__).read_text(encoding="utf-8"))
        imports=[n for n in ast.walk(tree) if isinstance(n,ast.ImportFrom) and n.level]
        self.assertEqual([(n.module,[v.name for v in n.names]) for n in imports],[(None,["control_packet_prepare"])])
        forbidden={"stat_file","file_stat","_checked_read","record_rf_baseband_observation","read_rf_signal_run",
                   "generate_rf_baseband_envelope","analyze_rf_baseband_envelope"}
        self.assertFalse([n for n in ast.walk(tree) if isinstance(n,ast.Attribute) and n.attr in forbidden])


    def test_maximum_sample_count_is_read_without_metric_recalculation(self):
        self.bundle["request"]["sample_count"]=4096;self.bundle["recipe"]["sample_count"]=4096
        self.bundle["packet"]["grid"]["sample_count"]=4096;self.bundle["analysis"]["grid"]["sample_count"]=4096
        self.bundle["packet"]["samples"]=[[0.0,-1.0] for _ in range(4096)]
        packet_sha=sha(canonical(self.bundle["packet"]))
        self.bundle["analysis"]["input_sha256"]=packet_sha;self.bundle["provenance"]["packet_sha256"]=packet_sha
        self.bundle["analysis"]["metrics"]["observed_on_samples"]=4096
        self.write();value=self.run_reader()
        self.assertEqual(len(value["math"]["packet"]["samples"]),4096)
        self.assertEqual(value["math"]["analysis"]["metrics"]["window_seconds"],0.25)

    def test_root_rejects_ambiguous_or_different_loaded_clone(self):
        for name in ("relative.py",r"\\server\share\read.py",r"C:\bad..\labflow\virtual_fleet\read.py"):
            with mock.patch.object(reader,"__file__",name):
                with self.assertRaises(reader.RfSignalWaveformObservationReadError) as found:reader._root()
                self.assertEqual(found.exception.code,"rf_signal_waveform_observation_read_path_invalid")
        with mock.patch.object(reader._native,"__file__",r"C:\different\labflow\control_packet_prepare.py"):
            with self.assertRaises(reader.RfSignalWaveformObservationReadError) as found:reader._root()
            self.assertEqual(found.exception.code,"rf_signal_waveform_observation_read_path_invalid")

    def test_first_cleanup_probe_interrupt_keeps_identity_and_closes(self):
        import sys
        original=os.fstat;first=KeyboardInterrupt("probe");state={"raised":False}
        def probe(fd):
            if sys._getframe(1).f_code.co_name=="_close" and not state["raised"]:
                state["raised"]=True;raise first
            return original(fd)
        caught=None
        with mock.patch.object(reader.os,"fstat",new=probe):
            try:self.run_reader()
            except BaseException as e:caught=e
        self.assertIs(caught,first);self.assertFalse(self.backends[-1].held)


    def test_large_integer_in_numeric_field_is_evidence_invalid(self):
        self.bundle["analysis"]["metrics"]["time_mean_mw"]=10**400
        self.write()
        self.assert_code("evidence_invalid")

if __name__=="__main__":
    unittest.main()

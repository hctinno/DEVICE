"""Thin CLI delivery: fresh native fixture, separately labelled typed seams/children."""
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import importlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sqlite3
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from labflow import control_packet_prepare as native
from labflow import intake_conducted_artifact_readback as parent
from labflow.ui_read_model import ReadModelError
from labflow.virtual_fleet import conducted_result_artifact_read as artifact_reader
from labflow.virtual_fleet import conducted_twin_comparison_cli as shared

MODULE = "labflow.intake_conducted_artifact_readback_cli"
ROOT = Path(__file__).resolve().parents[1]
PROOF = []
CHILDREN = []


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")


def sample(status="matched"):
    # Explicit typed delivery seam, never represented as a genuine readback.
    return dict(schema_version=1, kind="intake_conducted_artifact_readback", status=status,
        current=dict(raw=["\ud55c\uae00", None]), artifact=dict(result=dict(status="invalid", raw_measurement=None), draft=dict(status="DRAFT")),
        relation=dict(status=status, fields=dict(plan_sha256=None), reasons=["provided"]),
        verification=dict(execution_authority=False, physical_verified=False, permanent_current_approval=False))


class Capture(io.StringIO):
    def __init__(self, before=None, short=False):
        super().__init__(); self.calls=0; self.before=before; self.short=short
    def write(self, value):
        self.calls+=1
        if self.before:self.before()
        super().write(value)
        return len(value)-1 if self.short else len(value)
    def reconfigure(self, **kwargs):
        raise AssertionError("borrowed main must not configure streams")


CHILD_PROCESS_RESULTS = []
CHILD_AUDIT_POLICY = []
MAX_CHILD_OBSERVATION_BYTES = 1024 * 1024
MAX_CHILD_AUDIT_BYTES = 64 * 1024
MAX_CHILD_OBSERVATION_FILES = 32
MAX_CHILD_OBSERVATION_TOTAL = 8 * 1024 * 1024


def _write_child_observation(audit_root, path, raw, *, limit):
    """Test observations only: bounded, one native exclusive plain-file write."""
    audit_root, path = Path(audit_root), Path(path)
    if (type(raw) is not bytes or type(limit) is not int or not 0 <= limit <= MAX_CHILD_OBSERVATION_BYTES
            or len(raw) > limit):
        raise ValueError("child observation limit")
    if (not audit_root.is_absolute() or audit_root != audit_root.resolve(strict=True)
            or not path.is_absolute() or path.parent != audit_root
            or not path.name or not all(c.isascii() and (c.isalnum() or c in "._-") for c in path.name)):
        raise ValueError("child observation path")
    root_info = audit_root.lstat()
    if (not stat.S_ISDIR(root_info.st_mode) or stat.S_ISLNK(root_info.st_mode)
            or getattr(root_info, "st_file_attributes", 0) & 0x400):
        raise ValueError("child observation root")
    entries = [p.lstat() for p in audit_root.iterdir()]
    if len(entries) >= MAX_CHILD_OBSERVATION_FILES or sum(s.st_size for s in entries) + len(raw) > MAX_CHILD_OBSERVATION_TOTAL:
        raise ValueError("child observation aggregate limit")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size != 0:
            raise ValueError("child observation plain file")
        if os.write(descriptor, raw) != len(raw):
            raise OSError("child observation short write")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _child_audit_root(case):
    directory = tempfile.TemporaryDirectory(prefix="public-cli-child-audit-")
    case.addCleanup(directory.cleanup)
    audit_root = Path(directory.name).resolve(strict=True)
    probe = audit_root / "exclusive-probe.bin"
    _write_child_observation(audit_root, probe, b"retained", limit=MAX_CHILD_AUDIT_BYTES)
    with case.assertRaises(FileExistsError):
        _write_child_observation(audit_root, probe, b"changed", limit=MAX_CHILD_AUDIT_BYTES)
    case.assertEqual(probe.read_bytes(), b"retained")
    limited = audit_root / "limit-probe.bin"
    with case.assertRaises(ValueError):
        _write_child_observation(audit_root, limited, b"x", limit=0)
    case.assertFalse(limited.exists())
    CHILD_AUDIT_POLICY.append(dict(exclusive_no_overwrite=True, oversized_rejected_before_create=True,
                                  explicit_disposable_root=True, private_helper_required=False))
    return audit_root


def _preserve_child_process(audit_root, audit, mode, completed, stdout):
    stderr = completed.stderr
    if type(stdout) is not bytes or type(stderr) is not bytes:
        raise TypeError("child process bytes required")
    if len(stdout) > MAX_CHILD_OBSERVATION_BYTES or len(stderr) > MAX_CHILD_OBSERVATION_BYTES:
        raise ValueError("child process observation limit")
    record = dict(mode=mode, returncode=completed.returncode, stdout_hex=stdout.hex(), stderr_hex=stderr.hex(),
        stdout_observation="closed_pipe_no_capture" if completed.stdout is None else "captured",
        audit_filename=audit.name, captured_before_audit_parse=True)
    CHILD_PROCESS_RESULTS.append(record)
    _write_child_observation(audit_root, audit.with_suffix(".stdout.bin"), stdout, limit=MAX_CHILD_OBSERVATION_BYTES)
    _write_child_observation(audit_root, audit.with_suffix(".stderr.bin"), stderr, limit=MAX_CHILD_OBSERVATION_BYTES)
    receipt = dict(mode=mode, returncode=completed.returncode, stdout_observation=record["stdout_observation"],
        stdout_bytes=len(stdout), stdout_sha256=hashlib.sha256(stdout).hexdigest(),
        stderr_bytes=len(stderr), stderr_sha256=hashlib.sha256(stderr).hexdigest(), captured_before_audit_parse=True)
    _write_child_observation(audit_root, audit.with_suffix(".process.json"), canonical(receipt) + b"\n", limit=MAX_CHILD_AUDIT_BYTES)
    return record


def _read_child_audit(audit, process):
    try:
        with audit.open("rb") as handle:
            raw = handle.read(MAX_CHILD_AUDIT_BYTES + 1)
        if len(raw) > MAX_CHILD_AUDIT_BYTES:
            raise ValueError("child audit limit")
        return json.loads(raw)
    except (OSError, ValueError, UnicodeError) as error:
        # A failed/missing audit must not erase the already observed process result.
        raise AssertionError("child audit unavailable; process_before_audit=" + canonical(process).decode("utf-8")) from error


class SmokeTests(unittest.TestCase):
    def test_module_exists(self):
        self.assertIsNotNone(importlib.util.find_spec(MODULE), "assigned readback CLI is absent")


class TypedBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.cli=importlib.import_module(MODULE)
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup)
        self.root=Path(directory.name);self.file=self.root/"readback.json"
        self.options=dict(method=dict(method_id="conducted_synthetic", method_version=1, metric="on", reference_plane="source_output"),
            expected_revision=1,expected_context_sha256="1"*64,artifact_workspace_root=str(self.root),
            artifact_name="explicit-one",expected_manifest_sha256="2"*64,expected_result_sha256="3"*64,
            run_id="explicit-run",runtime_instance_id="explicit-runtime")
        self.file.write_bytes(canonical(self.options))
        self.argv=["--workspace",str(self.root),"--intake-id","explicit-intake","--readback-json",str(self.file)]

    def invoke(self, value=None, *, argv=None, error=None, output=None):
        stdout=Capture() if output is None else output;stderr=Capture()
        with patch.object(sys,"stdout",stdout),patch.object(sys,"stderr",stderr),patch.object(
                parent,"read_current_conducted_artifact",side_effect=error,return_value=sample() if value is None else value) as api:
            status=self.cli.main(self.argv if argv is None else argv)
        return status,stdout,stderr,api

    def assert_rejected(self, *, argv=None, code=None):
        status,out,err,api=self.invoke(argv=argv)
        self.assertEqual(status,1);self.assertEqual(out.getvalue(),"");self.assertEqual(api.call_count,0)
        diagnostic=json.loads(err.getvalue());self.assertEqual(set(diagnostic),{"error"})
        if code:self.assertEqual(diagnostic["error"]["code"],"intake_conducted_artifact_readback_cli_"+code)
        self.assertNotIn(str(self.root),err.getvalue())

    def test_original_dto_and_statuses_are_delivered_once_without_rewriting(self):
        for status,exit_code in (("matched",0),("blocked",2),("different_intake",2),("different_plan",2),("stale",2)):
            with self.subTest(status=status):
                value=sample(status);before=deepcopy(value);options=deepcopy(self.options)
                code,out,err,api=self.invoke(value)
                self.assertEqual(code,exit_code);self.assertEqual(out.getvalue().encode(),canonical(value)+b"\n")
                self.assertEqual(out.calls,1);self.assertEqual(err.getvalue(),"");self.assertEqual(value,before)
                self.assertEqual(api.call_args.args,(str(self.root),"explicit-intake"))
                self.assertEqual(api.call_args.kwargs,options);self.assertEqual(api.call_count,1)
                self.assertFalse(out.closed);self.assertFalse(err.closed)

    def test_unknown_duplicate_equal_missing_and_foreign_arguments_call_parent_zero(self):
        for args in ([],None,["--help","extra"],self.argv+["--other","x"],
                ["--workspace=x",*self.argv[1:]],["--workspace",str(self.root)]*3,
                ["--workspace","relative",*self.argv[2:]],["--workspace",r"\\server\share",*self.argv[2:]],
                [*self.argv[:-1],"relative.json"],["--workspace",str(self.root), "--intake-id",object(),*self.argv[4:]]):
            with self.subTest(args=repr(args)):
                self.assert_rejected(argv=() if args is None else args)

    def test_strict_json_and_exact_keys_reject_before_parent(self):
        raws=[b"\xef\xbb\xbf"+canonical(self.options),b"\xff",b"{}",b"[]",b'{"method":0,"method":1}',
              canonical({**self.options,"extra":1}),canonical({k:v for k,v in self.options.items() if k!="method"}),
              canonical(self.options).replace(b'"expected_revision":1',b'"expected_revision":NaN'),
              canonical(self.options).replace(b'"expected_revision":1',b'"expected_revision":1e9999')]
        for raw in raws:
            with self.subTest(raw=raw[:40]):
                self.file.write_bytes(raw);self.assert_rejected()

    def test_raw_depth_node_caps_and_artifact_absolute_path_reject_before_parent(self):
        for options in ({**self.options,"method":[[[[[[[[[0]]]]]]]]]},
                        {**self.options,"method":[0]*2050},
                        {**self.options,"artifact_workspace_root":"relative"},
                        {**self.options,"artifact_workspace_root":r"\\server\share"},
                        {**self.options,"method":"x"*65536}):
            with self.subTest(options_type=type(options["method"]).__name__):
                self.file.write_bytes(canonical(options));self.assert_rejected()

    def test_missing_json_and_lexical_aliases_are_sanitized(self):
        for path in (str(self.root/"missing.json"),str(self.root/"bad."/ "readback.json"),str(self.root/".." / "readback.json")):
            with self.subTest(path=path):
                self.assert_rejected(argv=[*self.argv[:-1],path])

    def test_known_native_handles_closed_before_stdout(self):
        backends=[];original=native._WindowsIO
        def backend():
            value=original();backends.append(value);return value
        def closed():
            self.assertEqual(len(backends),1)
            self.assertEqual(backends[0].held,[]);self.assertEqual(backends[0].directories,{})
        with patch.object(native,"_WindowsIO",side_effect=backend):
            code,out,err,api=self.invoke(output=Capture(before=closed))
        self.assertEqual((code,out.calls,api.call_count),(0,1,1));self.assertEqual(err.getvalue(),"")

    def test_pin_raw_recheck_failure_has_no_stdout_or_retry(self):
        original=native._read_descriptor;reads=[]
        def read(*args,**kwargs):
            raw=original(*args,**kwargs);reads.append(raw)
            return raw if len(reads)==1 else raw+b" "
        with patch.object(native,"_read_descriptor",side_effect=read):
            code,out,err,api=self.invoke()
        self.assertEqual((code,api.call_count,len(reads)),(1,1,2));self.assertEqual(out.getvalue(),"")
        self.assertIn("input_changed",err.getvalue())

    def test_native_source_change_code_is_sanitized(self):
        error=native.ControlPacketPrepareError("packet_prepare_source_changed")
        with patch.object(shared,"_recheck",side_effect=error):
            code,out,err,api=self.invoke()
        self.assertEqual((code,api.call_count),(1,1));self.assertEqual(out.getvalue(),"")
        self.assertEqual(json.loads(err.getvalue()),{"error":{"code":"intake_conducted_artifact_readback_cli_input_changed"}})

    def test_short_write_and_flush_failure_are_not_retried(self):
        code,out,err,api=self.invoke(output=Capture(short=True))
        self.assertEqual((code,out.calls,api.call_count),(1,1,1));self.assertIn("output_failed",err.getvalue())
        output=Capture()
        output.flush=lambda:(_ for _ in ()).throw(OSError("do not echo "+str(self.root)))
        code,out,err,api=self.invoke(output=output)
        self.assertEqual((code,out.calls,api.call_count),(1,1,1));self.assertIn("output_failed",err.getvalue())
        self.assertNotIn(str(self.root),err.getvalue())

    def test_cleanup_failure_is_before_stdout_and_preserves_first_error(self):
        original=self.cli._cleanup._close
        def close(backend):
            original(backend);return OSError("secret "+str(self.root))
        with patch.object(self.cli._cleanup,"_close",side_effect=close):
            code,out,err,api=self.invoke()
        self.assertEqual((code,api.call_count),(1,1));self.assertEqual(out.getvalue(),"");self.assertNotIn(str(self.root),err.getvalue())

    def test_borrowed_controls_keep_same_first_object_after_cleanup(self):
        for error in (KeyboardInterrupt(),MemoryError(),SystemExit(7),GeneratorExit()):
            with self.subTest(error=type(error).__name__):
                original=self.cli._cleanup._close;backends=[]
                def close(backend):
                    backends.append(backend);original(backend);return RuntimeError("secondary")
                with patch.object(self.cli._cleanup,"_close",side_effect=close),self.assertRaises(type(error)) as caught:
                    self.invoke(error=error)
                self.assertIs(caught.exception,error);self.assertTrue(backends);self.assertEqual(backends[0].held,[])

    def test_fixed_exact_parent_typed_codes_only_map_unavailable_three(self):
        errors=(parent.IntakeConductedArtifactReadbackError("intake_conducted_artifact_readback_input_limit"),
                artifact_reader.ConductedResultArtifactReadError("conducted_result_artifact_read_binding_invalid"),
                ReadModelError("store_missing"))
        for error in errors:
            code,out,err,api=self.invoke(error=error)
            self.assertEqual((code,api.call_count),(3,1));self.assertEqual(out.getvalue(),"")
            self.assertEqual(json.loads(err.getvalue()),{"error":{"code":"intake_conducted_artifact_readback_cli_unavailable"}})
        class Foreign(ReadModelError):pass
        for error in (ReadModelError("secret "+str(self.root)),Foreign("store_missing"),RuntimeError("secret "+str(self.root))):
            code,out,err,api=self.invoke(error=error)
            self.assertEqual((code,api.call_count),(1,1));self.assertEqual(out.getvalue(),"");self.assertNotIn(str(self.root),err.getvalue())

    def test_bad_or_oversize_parent_dto_is_not_repaired(self):
        for value in ({},dict(sample(),schema_version=True),dict(sample(),status="PASS"),dict(sample(),extra=1),dict(sample(),current=object())):
            code,out,err,api=self.invoke(value)
            self.assertEqual((code,api.call_count),(1,1));self.assertEqual(out.getvalue(),"")
        with patch.object(self.cli,"MAX_OUTPUT_BYTES",1):
            code,out,err,api=self.invoke()
        self.assertEqual((code,api.call_count),(1,1));self.assertEqual(out.getvalue(),"")

    def test_help_uses_no_native_backend_or_parent_and_keeps_streams(self):
        with patch.object(native,"_WindowsIO",side_effect=AssertionError("help backend0")):
            code,out,err,api=self.invoke(argv=["--help"])
        self.assertEqual((code,api.call_count),(0,0));self.assertIn("matched",out.getvalue())
        self.assertEqual(err.getvalue(),"");self.assertFalse(out.closed)


class GenuineFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cli=importlib.import_module(MODULE)
        spec=importlib.util.spec_from_file_location("readback_cli_fixture",Path(__file__).with_name("test_intake_conducted_artifact_readback.py"))
        fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
        cls.data=fixture.CurrentArtifactReadbackTests
        cls.data.setUpClass();cls.addClassCleanup(cls.data.doClassCleanups)
        cls.options=dict(deepcopy(cls.data.pins),artifact_workspace_root=str(cls.data.artifact_root),**cls.data.artifact_pins)
        cls.file=cls.data.base/"cli-readback.json";cls.file.write_bytes(canonical(cls.options))
        cls.argv=["--workspace",str(cls.data.source_state),"--intake-id",cls.data.intake_id,"--readback-json",str(cls.file)]

    def inventory(self):
        return {p.relative_to(self.data.base).as_posix():(hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_size,
            p.stat().st_ino,p.stat().st_mtime_ns,p.stat().st_nlink,p.stat().st_file_attributes)
            for p in self.data.base.rglob("*") if p.is_file()}

    def test_genuine_authored_pdf_same_plan_saved_artifact_readback_once(self):
        before=self.inventory();seen=[];connections=[];backends=[]
        original=parent.read_current_conducted_artifact;connect=sqlite3.connect;backend=native._WindowsIO
        closed_ids=set();statements=[];write_actions=[]
        def profile(frame,event,method):
            if event=="c_return" and getattr(method,"__name__",None)=="close" and type(getattr(method,"__self__",None)) is sqlite3.Connection:
                closed_ids.add(id(method.__self__))
        def readonly(database,*args,**kwargs):
            self.assertIn("?mode=ro",str(database))
            con=connect(database,*args,**kwargs);connections.append(con)
            con.set_trace_callback(statements.append)
            def authorizer(action,first,second,database,origin):
                if action in (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE,
                        sqlite3.SQLITE_CREATE_TABLE,sqlite3.SQLITE_CREATE_INDEX,sqlite3.SQLITE_DROP_TABLE,
                        sqlite3.SQLITE_DROP_INDEX,sqlite3.SQLITE_ALTER_TABLE):
                    write_actions.append(action)
                return sqlite3.SQLITE_OK
            con.set_authorizer(authorizer)
            return con
        def tracked():
            value=backend();backends.append(value);return value
        def read(*args,**kwargs):
            try:output=original(*args,**kwargs)
            except BaseException as error:
                seen.append(dict(error_type=type(error).__name__,code=getattr(error,"code",None),cause=repr(error.__cause__)))
                raise
            seen.append(output);return output
        def closed():
            self.assertTrue(connections);self.assertTrue(all(id(c) in closed_ids for c in connections))
            self.assertTrue(backends);self.assertTrue(all(not b.held and not b.directories for b in backends))
        out,err=Capture(before=closed),Capture()
        previous=sys.getprofile();sys.setprofile(profile)
        try:
            with patch.object(sqlite3,"connect",side_effect=readonly),patch.object(native,"_WindowsIO",side_effect=tracked),patch.object(
                    parent,"read_current_conducted_artifact",side_effect=read) as api,patch.object(sys,"stdout",out),patch.object(sys,"stderr",err):
                status=self.cli.main(self.argv)
        finally:sys.setprofile(previous)
        self.assertTrue(statements)
        self.assertEqual(write_actions,[])
        self.assertEqual((status,api.call_count,out.calls),(0,1,1),repr(seen));self.assertEqual(err.getvalue(),"")
        self.assertEqual(out.getvalue().encode(),canonical(seen[0])+b"\n");self.assertEqual(seen[0]["status"],"matched")
        self.assertEqual(seen[0]["artifact"]["result"],self.data.result);self.assertEqual(self.inventory(),before)
        self.assertIs(seen[0]["verification"]["execution_authority"],False)
        PROOF.append(dict(origin="genuine authored synthetic PDF/native same-plan writer/readback once",options=deepcopy(self.options),
            argv=list(self.argv),output=deepcopy(seen[0]),stdout_hex=out.getvalue().encode().hex(),parent_calls=api.call_count,
            read_only_connections=len(connections),closed_connections=sum(id(c) in closed_ids for c in connections),native_connection_types_preserved=True,authorizer_write_actions=0,sql_trace_count=len(statements),comment_trace_count=sum(sql.lstrip().startswith("--") for sql in statements),
            native_backends=len(backends),known_native_closed=True,source_raw_native_unchanged=True,execution_authority=False))

    def test_real_python_processes_are_separate_from_typed_seams(self):
        child=r'''# DEV3_READBACK_CLI_CHILD
import hashlib,json,os,runpy,socket,sqlite3,sys
from pathlib import Path
root=Path.cwd();audit_root=Path(sys.argv[1]);audit_path=Path(sys.argv[2]);mode=sys.argv[3]
sys.path.insert(0,str(root))
from importlib.util import spec_from_file_location,module_from_spec
observer_spec=spec_from_file_location("public_child_observer",root/"tests/test_intake_conducted_artifact_readback_cli.py")
observer=module_from_spec(observer_spec);observer_spec.loader.exec_module(observer)
import labflow.intake_conducted_artifact_readback as parent
audit=dict(api_calls=0,readonly_connections=0,closed_connections=0,native_backends=0,known_native_closed=False,actual_model=0,network=0,business_writes=0,hardware=0)
def forbidden(*a,**k):raise AssertionError("forbidden actual execution")
socket.create_connection=forbidden;socket.socket.connect=forbidden
connect=sqlite3.connect;connections=[];closed_ids=set()
def profile(frame,event,method):
 if event=="c_return" and getattr(method,"__name__",None)=="close" and type(getattr(method,"__self__",None)) is sqlite3.Connection:
  closed_ids.add(id(method.__self__))
sys.setprofile(profile)
audit["sql_trace_count"]=0;audit["comment_trace_count"]=0
def sql_trace(sql):
 audit["sql_trace_count"]+=1
 if sql.lstrip().startswith("--"):audit["comment_trace_count"]+=1
def authorizer(action,first,second,database,origin):
 if action in (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE,sqlite3.SQLITE_CREATE_TABLE,sqlite3.SQLITE_CREATE_INDEX,sqlite3.SQLITE_DROP_TABLE,sqlite3.SQLITE_DROP_INDEX,sqlite3.SQLITE_ALTER_TABLE):audit["business_writes"]+=1
 return sqlite3.SQLITE_OK
def readonly(database,*a,**k):
 if "?mode=ro" not in str(database):forbidden()
 c=connect(database,*a,**k);connections.append(c);c.set_trace_callback(sql_trace);c.set_authorizer(authorizer);audit["readonly_connections"]+=1;return c
sqlite3.connect=readonly
from labflow import control_packet_prepare as native
backends=[];backend=native._WindowsIO
def tracked():
 b=backend();backends.append(b);audit["native_backends"]+=1;return b
native._WindowsIO=tracked
read=parent.read_current_conducted_artifact
def counted(*a,**k):
 audit["api_calls"]+=1
 if mode=="interrupt":raise KeyboardInterrupt()
 try:value=read(*a,**k)
 except BaseException as error:
  audit["parent_error_type"]=type(error).__name__;audit["parent_error_code"]=getattr(error,"code",None);audit["parent_error_cause"]=repr(error.__cause__)
  raise
 audit["parent_status"]=value["status"]
 audit["parent_sha256"]=hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,allow_nan=False,separators=(",",":")).encode()).hexdigest()
 return value
parent.read_current_conducted_artifact=counted
from labflow.store import Store
Store.__init__=forbidden
sys.argv=["labflow.intake_conducted_artifact_readback_cli",*sys.argv[4:]]
status=1
try:runpy.run_module("labflow.intake_conducted_artifact_readback_cli",run_name="__main__")
except SystemExit as error:status=error.code
finally:
 audit["known_native_closed"]=all(not b.held and not b.directories for b in backends)
 audit["closed_connections"]=sum(id(c) in closed_ids for c in connections)
 audit["native_connection_types_preserved"]=all(type(c) is sqlite3.Connection for c in connections)
 sys.setprofile(None)
 observer._write_child_observation(audit_root,audit_path,(json.dumps(audit,indent=2)+"\n").encode("utf-8"),limit=observer.MAX_CHILD_AUDIT_BYTES)
raise SystemExit(status)
'''
        audit_root=_child_audit_root(self)
        before=self.inventory()
        cases=(("matched",self.options,0,1),("blocked",{**self.options,"expected_revision":None},2,1),
               ("unavailable",{**self.options,"artifact_name":"missing-explicit-artifact"},3,1),
               ("interrupt",self.options,130,1),("closed",self.options,1,1),("help",None,0,0))
        for number,(mode,options,expected,calls) in enumerate(cases,1):
            with self.subTest(mode=mode):
                path=self.data.base/("child-"+str(number)+".json")
                if options is not None:path.write_bytes(canonical(options))
                args=["--help"] if options is None else [*self.argv[:-1],str(path)]
                audit=audit_root/("child-audit-"+str(number)+".json")
                self.assertFalse(audit.exists(),"preserve original child audit")
                command=[sys.executable,"-B","-X","utf8","-c",child,str(audit_root),str(audit),mode,*args]
                environment={**os.environ,"PYTHONUTF8":"0","PYTHONIOENCODING":"cp1252","PYTHONDONTWRITEBYTECODE":"1"}
                if mode=="closed":
                    read_fd,write_fd=os.pipe();os.close(read_fd)
                    try:completed=subprocess.run(command,cwd=ROOT,env=environment,stdout=write_fd,stderr=subprocess.PIPE,timeout=30)
                    finally:os.close(write_fd)
                    stdout=b""
                else:
                    completed=subprocess.run(command,cwd=ROOT,env=environment,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30);stdout=completed.stdout
                process=_preserve_child_process(audit_root,audit,mode,completed,stdout)
                details=_read_child_audit(audit,process)
                self.assertEqual(completed.returncode,expected,repr(details));self.assertEqual(details["api_calls"],calls)
                self.assertTrue(details["known_native_closed"]);self.assertEqual(details["readonly_connections"],details["closed_connections"])
                self.assertIs(details["native_connection_types_preserved"],True);self.assertEqual(details["business_writes"],0)
                self.assertNotIn(b"Traceback",completed.stderr);self.assertNotIn(str(self.data.base).encode(),completed.stderr)
                if mode in ("matched","blocked"):
                    value=json.loads(stdout);self.assertEqual(set(value),set("schema_version kind status current artifact relation verification".split()))
                    self.assertEqual(stdout,canonical(value)+b"\n");self.assertEqual(value["status"],mode)
                    self.assertEqual(hashlib.sha256(stdout[:-1]).hexdigest(),details["parent_sha256"]);self.assertEqual(completed.stderr,b"")
                elif mode=="help":
                    self.assertIn("\ubcf4\uc874".encode(),stdout);self.assertEqual(completed.stderr,b"");self.assertEqual(details["native_backends"],0)
                else:
                    self.assertEqual(stdout,b"");self.assertEqual(set(json.loads(completed.stderr)),{"error"})
                CHILDREN.append(dict(mode=mode,exit=completed.returncode,audit=details,stdout_hex=stdout.hex(),stderr_hex=completed.stderr.hex()))
        after=self.inventory()
        self.assertEqual({k:v for k,v in after.items() if not k.startswith("child-")},before)


OPTIONAL_PROOF = dict(genuine=[], children=[], typed=[])


def optional_sample(status="not_assessed"):
    """Explicit typed delivery seam; no comparison dataset or measured values."""
    from labflow.virtual_fleet import conducted_twin_comparison as compare
    rb=sample("blocked" if status=="blocked" else "matched")
    rb["relation"]=dict(status=rb["status"],current_binding=None,artifact_binding=None,
        fields=dict(plan_sha256=None),recheck=None,reasons=["typed-readback-reason"])
    rb["verification"].update(rerun_authority=False,business_writes=False)
    comparison=None if status=="blocked" else compare._base()
    if comparison is not None:comparison["reasons"]=[dict(code="reference_missing",field="reference",detail=None)]
    return dict(schema_version=1,kind="intake_conducted_artifact_comparison",status=status,readback=rb,comparison=comparison,
        reasons=dict(readback=rb["relation"]["reasons"],comparison=None if comparison is None else comparison["reasons"]),
        verification=dict(scope="current_readback_and_provided_comparison_only",readback_calls=1,
            comparison_calls=0 if comparison is None else 1,metadata_authenticity="unknown",method_approval="not_assessed",
            regulatory="not_assessed",hardware_verified=False,physical_verified=False,model_execution_verified=False,
            execution_authority=False,rerun_authority=False))


class OptionalComparisonTests(unittest.TestCase):
    def setUp(self):
        TypedBoundaryTests.setUp(self)
        self.bridge=importlib.import_module("labflow.intake_conducted_artifact_comparison")
        self.comparison_file=self.root/"comparison.json"
        self.comparison_options=dict(reference=None,comparator_policy=None,lineage=None)
        self.comparison_file.write_bytes(canonical(self.comparison_options))
        self.argv=[*self.argv,"--comparison-json",str(self.comparison_file)]

    def invoke_optional(self,value=None,*,argv=None,error=None,output=None):
        out=Capture() if output is None else output;err=Capture()
        with patch.object(self.bridge,"compare_current_conducted_artifact",return_value=optional_sample() if value is None else value,
                side_effect=error) as api,patch.object(parent,"read_current_conducted_artifact",side_effect=AssertionError("no direct readback fallback")) as direct,patch.object(
                sys,"stdout",out),patch.object(sys,"stderr",err):
            status=self.cli.main(self.argv if argv is None else argv)
        return status,out,err,api,direct

    def test_optional_null3_original_bridge_forwarding_and_known_close(self):
        backends=[];backend=native._WindowsIO
        def track():
            value=backend();backends.append(value);return value
        def closed():
            self.assertEqual(len(backends),1);self.assertEqual(backends[0].held,[]);self.assertEqual(backends[0].directories,{})
        value=optional_sample();before=deepcopy((self.options,self.comparison_options,value))
        with patch.object(native,"_WindowsIO",side_effect=track):
            status,out,err,api,direct=self.invoke_optional(value,output=Capture(before=closed))
        self.assertEqual((status,api.call_count,direct.call_count,out.calls),(2,1,0,1))
        self.assertEqual(out.getvalue().encode(),canonical(value)+b"\n");self.assertEqual(err.getvalue(),"")
        self.assertEqual(api.call_args.args,(str(self.root),"explicit-intake"))
        self.assertEqual(api.call_args.kwargs,dict(self.options,**self.comparison_options))
        self.assertEqual((self.options,self.comparison_options,value),before)
        OPTIONAL_PROOF["typed"].append(dict(origin="typed optional null3 forwarding",bridge_calls=1,direct_readback_calls=0,exit=2,stdout_once=True,known_closed=True))

    def test_optional_file_syntax_strict_json_and_caps_fail_without_fallback(self):
        bad_args=(self.argv+["--comparison-json",str(self.comparison_file)],
            [*self.argv[:-2],"--comparison-json="+str(self.comparison_file)],
            self.argv[:-1],[*self.argv[:-1],"relative.json"],[*self.argv[:-1],r"\\server\share\file.json"])
        for args in bad_args:
            with self.subTest(args=repr(args)):
                status,out,err,api,direct=self.invoke_optional(argv=args)
                self.assertEqual((status,api.call_count,direct.call_count),(1,0,0));self.assertEqual(out.getvalue(),"")
        for raw in (b"null",b"{}",canonical(dict(self.comparison_options,extra=None)),b'{"reference":null,"reference":null}',
                    b"\xef\xbb\xbf"+canonical(self.comparison_options),b"\xff",b'{"reference":NaN,"comparator_policy":null,"lineage":null}',
                    canonical(dict(self.comparison_options,reference="x"*(2*1024*1024))),
                    canonical(dict(self.comparison_options,reference=[0]*100001)),
                    b'{"reference":'+b"["*34+b"0"+b"]"*34+b',"comparator_policy":null,"lineage":null}'):
            with self.subTest(raw_bytes=len(raw)):
                self.comparison_file.write_bytes(raw)
                status,out,err,api,direct=self.invoke_optional()
                self.assertEqual((status,api.call_count,direct.call_count),(1,0,0));self.assertEqual(out.getvalue(),"")
                self.assertNotIn(str(self.root),err.getvalue())

    def test_optional_original_statuses_and_bad_success_contract(self):
        for value,expected in ((optional_sample("blocked"),2),(optional_sample(),2),
                               (dict(optional_sample(),status="compared"),1),(dict(optional_sample(),schema_version=True),1)):
            status,out,err,api,direct=self.invoke_optional(value)
            self.assertEqual((status,api.call_count,direct.call_count),(expected,1,0))
            if expected==2:self.assertEqual(out.getvalue().encode(),canonical(value)+b"\n");self.assertEqual(err.getvalue(),"")
            else:self.assertEqual(out.getvalue(),"")
        with patch.object(self.cli,"MAX_COMPARISON_OUTPUT_BYTES",1):
            status,out,err,api,direct=self.invoke_optional()
        self.assertEqual((status,api.call_count),(1,1));self.assertEqual(out.getvalue(),"")

    def test_both_original_source_pins_rechecked_without_retry(self):
        for fail_at in (3,4):
            calls=[];original=native._read_descriptor
            def read(*args,**kwargs):
                raw=original(*args,**kwargs);calls.append(raw)
                return raw+b" " if len(calls)==fail_at else raw
            with patch.object(native,"_read_descriptor",side_effect=read):
                status,out,err,api,direct=self.invoke_optional()
            self.assertEqual((status,api.call_count),(1,1));self.assertEqual(out.getvalue(),"")
            self.assertIn("input_changed",err.getvalue());self.assertEqual(len(calls),fail_at)

    def test_optional_error_whitelist_controls_and_short_write(self):
        error=self.bridge.IntakeConductedArtifactComparisonError("intake_conducted_artifact_comparison_parent_invalid")
        status,out,err,api,direct=self.invoke_optional(error=error)
        self.assertEqual((status,api.call_count),(3,1));self.assertEqual(out.getvalue(),"");self.assertIn("unavailable",err.getvalue())
        for error in (RuntimeError("private "+str(self.root)),ReadModelError("unknown")):
            status,out,err,api,direct=self.invoke_optional(error=error)
            self.assertEqual((status,api.call_count),(1,1));self.assertEqual(out.getvalue(),"");self.assertNotIn(str(self.root),err.getvalue())
        for error in (KeyboardInterrupt(),MemoryError(),SystemExit(7),GeneratorExit()):
            with self.assertRaises(type(error)) as caught:self.invoke_optional(error=error)
            self.assertIs(caught.exception,error)
        status,out,err,api,direct=self.invoke_optional(output=Capture(short=True))
        self.assertEqual((status,api.call_count,out.calls),(1,1,1));self.assertIn("output_failed",err.getvalue())

    def test_absent_option_preserves_default_wire_and_import_zero(self):
        import builtins
        original=builtins.__import__;value=sample()
        def guarded(name,globals=None,locals=None,fromlist=(),level=0):
            if fromlist and "intake_conducted_artifact_comparison" in fromlist:raise AssertionError("default bridge import0")
            return original(name,globals,locals,fromlist,level)
        out,err=Capture(),Capture()
        with patch.object(builtins,"__import__",side_effect=guarded),patch.object(
                self.bridge,"compare_current_conducted_artifact",side_effect=AssertionError("default bridge0")) as bridge,patch.object(
                parent,"read_current_conducted_artifact",return_value=value) as read,patch.object(sys,"stdout",out),patch.object(sys,"stderr",err):
            status=self.cli.main(self.argv[:-2])
        self.assertEqual((status,read.call_count,bridge.call_count),(0,1,0))
        self.assertEqual(out.getvalue().encode(),canonical(value)+b"\n");self.assertEqual(err.getvalue(),"")
        OPTIONAL_PROOF["typed"].append(dict(origin="default route preserved",exit=0,readback_calls=1,bridge_imports=0,bridge_calls=0,original_dto_equal=True))


class OptionalComparisonGenuineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        GenuineFlowTests.setUpClass.__func__(cls)
        cls.bridge=importlib.import_module("labflow.intake_conducted_artifact_comparison")
        cls.comparison=cls.data.base/"optional-comparison.json"
        cls.comparison_options=dict(reference=None,comparator_policy=None,lineage=None)
        cls.comparison.write_bytes(canonical(cls.comparison_options))
        cls.argv=[*cls.argv,"--comparison-json",str(cls.comparison)]

    def inventory(self):
        return GenuineFlowTests.inventory(self)

    def test_genuine_optional_no_reference_original_bridge_once(self):
        from labflow.virtual_fleet import conducted_twin_comparison as comparison_api
        before=self.inventory();seen=[];connections=[];closed_ids=set();write_actions=[];backends=[]
        bridge=self.bridge.compare_current_conducted_artifact;read=parent.read_current_conducted_artifact
        compare=comparison_api.compare_conducted_twin_result;connect=sqlite3.connect;backend=native._WindowsIO
        def profile(frame,event,method):
            if event=="c_return" and getattr(method,"__name__",None)=="close" and type(getattr(method,"__self__",None)) is sqlite3.Connection:
                closed_ids.add(id(method.__self__))
        def authorizer(action,first,second,database,origin):
            if action in (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE,sqlite3.SQLITE_CREATE_TABLE,
                    sqlite3.SQLITE_CREATE_INDEX,sqlite3.SQLITE_DROP_TABLE,sqlite3.SQLITE_DROP_INDEX,sqlite3.SQLITE_ALTER_TABLE):write_actions.append(action)
            return sqlite3.SQLITE_OK
        def readonly(database,*args,**kwargs):
            self.assertIn("?mode=ro",str(database));con=connect(database,*args,**kwargs);connections.append(con);con.set_authorizer(authorizer);return con
        def track():
            value=backend();backends.append(value);return value
        def capture(*args,**kwargs):
            value=bridge(*args,**kwargs);seen.append(value);return value
        def closed():
            self.assertTrue(connections);self.assertTrue(all(id(c) in closed_ids for c in connections))
            self.assertTrue(backends);self.assertTrue(all(not b.held and not b.directories for b in backends))
        out,err=Capture(before=closed),Capture();previous=sys.getprofile();sys.setprofile(profile)
        try:
            with patch.object(sqlite3,"connect",side_effect=readonly),patch.object(native,"_WindowsIO",side_effect=track),patch.object(
                    self.bridge,"compare_current_conducted_artifact",side_effect=capture) as api,patch.object(
                    parent,"read_current_conducted_artifact",wraps=read) as rb,patch.object(
                    comparison_api,"compare_conducted_twin_result",wraps=compare) as cmp,patch.object(sys,"stdout",out),patch.object(sys,"stderr",err):
                status=self.cli.main(self.argv)
        finally:sys.setprofile(previous)
        self.assertEqual((status,api.call_count,rb.call_count,cmp.call_count,out.calls),(2,1,1,1,1));self.assertEqual(err.getvalue(),"")
        self.assertEqual(out.getvalue().encode(),canonical(seen[0])+b"\n");self.assertEqual(seen[0]["readback"]["status"],"matched")
        self.assertEqual(seen[0]["status"],"not_assessed");self.assertTrue(all(v is None for v in seen[0]["comparison"]["comparison"].values()))
        self.assertEqual(len(connections),4);self.assertEqual(write_actions,[]);self.assertEqual(self.inventory(),before)
        OPTIONAL_PROOF["genuine"].append(dict(origin="fresh authored native artifact -> optional CLI -> bridge1/readback1/comparator1, null3 comparison inputs",
            argv=list(self.argv),comparison_options=deepcopy(self.comparison_options),output=deepcopy(seen[0]),stdout_hex=out.getvalue().encode().hex(),
            exit=2,bridge_calls=1,readback_calls=1,comparison_calls=1,readonly_connections=4,closed_connections=4,authorizer_writes=0,
            known_native_closed_before_stdout=True,source_raw_native_unchanged=True,extra_api=0))

    def test_actual_optional_python_children_are_distinct_from_default_regression(self):
        original_child=next(v for v in GenuineFlowTests.test_real_python_processes_are_separate_from_typed_seams.__code__.co_consts
            if type(v) is str and v.startswith("# DEV3_READBACK_CLI_CHILD"))
        child=original_child.replace("import labflow.intake_conducted_artifact_readback as parent","import labflow.intake_conducted_artifact_comparison as parent")
        child=child.replace("parent.read_current_conducted_artifact","parent.compare_current_conducted_artifact")
        audit_root=_child_audit_root(self);before=self.inventory()
        for number,(mode,expected,calls) in enumerate((("optional",2,1),("invalid",1,0),("closed",1,1),("interrupt",130,1)),1):
            with self.subTest(mode=mode):
                comparison=self.comparison
                if mode=="invalid":
                    comparison=self.data.base/"bad-optional.json";comparison.write_bytes(b"{}")
                args=[*self.argv[:-1],str(comparison)]
                audit=audit_root/("optional-child-"+str(number)+".json")
                self.assertFalse(audit.exists())
                command=[sys.executable,"-B","-X","utf8","-c",child,str(audit_root),str(audit),mode,*args]
                env={**os.environ,"PYTHONUTF8":"0","PYTHONIOENCODING":"cp1252","PYTHONDONTWRITEBYTECODE":"1"}
                if mode=="closed":
                    read_fd,write_fd=os.pipe();os.close(read_fd)
                    try:completed=subprocess.run(command,cwd=ROOT,env=env,stdout=write_fd,stderr=subprocess.PIPE,timeout=30)
                    finally:os.close(write_fd)
                    stdout=b""
                else:
                    completed=subprocess.run(command,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30);stdout=completed.stdout
                process=_preserve_child_process(audit_root,audit,mode,completed,stdout)
                details=_read_child_audit(audit,process)
                self.assertEqual(completed.returncode,expected,repr(details));self.assertEqual(details["api_calls"],calls)
                self.assertEqual(details["readonly_connections"],details["closed_connections"]);self.assertTrue(details["known_native_closed"])
                self.assertEqual(details["business_writes"],0);self.assertNotIn(b"Traceback",completed.stderr)
                self.assertNotIn(str(self.data.base).encode(),completed.stderr)
                if mode=="optional":
                    value=json.loads(stdout);self.assertEqual(value["status"],"not_assessed")
                    self.assertEqual(stdout,canonical(value)+b"\n");self.assertEqual(hashlib.sha256(stdout[:-1]).hexdigest(),details["parent_sha256"])
                    self.assertEqual(completed.stderr,b"")
                else:self.assertEqual(stdout,b"");self.assertEqual(set(json.loads(completed.stderr)),{"error"})
                OPTIONAL_PROOF["children"].append(dict(mode=mode,exit=completed.returncode,audit=details,stdout_hex=stdout.hex(),stderr_hex=completed.stderr.hex(),
                    real_bridge_delegations=0 if mode in ("invalid","interrupt") else 1))
        after=self.inventory()
        self.assertEqual({k:v for k,v in after.items() if k!="bad-optional.json"},before)

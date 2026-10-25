"""Small current readback->comparison bridge; no supplied measurement is invented."""
from copy import deepcopy
import importlib
import importlib.util
from pathlib import Path
import sqlite3
import sys
import unittest
from unittest.mock import patch

from labflow import control_packet_prepare as native
from labflow import intake_conducted_artifact_readback as readback_api
from labflow.virtual_fleet import conducted_twin_comparison as comparison_api

MODULE="labflow.intake_conducted_artifact_comparison"
PROOF=dict(genuine=[],typed=[])


def readback(status="matched",result_status="invalid"):
    # Explicit typed seam, never a real stored/native measurement.
    return dict(schema_version=1,kind="intake_conducted_artifact_readback",status=status,
        current=dict(provided=None),artifact=dict(result=dict(status=result_status,raw_measurement=None)),
        relation=dict(status=status,current_binding=None,artifact_binding=None,fields=dict(plan_sha256=None),
                      recheck=None,reasons=["original-readback-reason"]),
        verification=dict(execution_authority=False,rerun_authority=False,physical_verified=False,
                          business_writes=False,permanent_current_approval=False))


class SmokeTests(unittest.TestCase):
    def test_module_exists(self):
        self.assertIsNotNone(importlib.util.find_spec(MODULE),"assigned bridge is absent")


class BridgeBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.api=importlib.import_module(MODULE)
        self.options=dict(method=dict(explicit="caller-method"),expected_revision=7,expected_context_sha256="a"*64,
            artifact_workspace_root="C:/caller-explicit-artifacts",artifact_name="caller-explicit-one",
            expected_manifest_sha256="b"*64,expected_result_sha256="c"*64,run_id="caller-run",runtime_instance_id="caller-runtime")

    def call(self,**kwargs):
        return self.api.compare_current_conducted_artifact("C:/caller-explicit-current","caller-intake",**self.options,**kwargs)

    def test_nonmatched_readback_statuses_keep_original_reasons_and_null_without_comparison(self):
        for status in ("blocked","different_intake","different_plan","stale"):
            original=readback(status);before=deepcopy(original)
            with patch.object(readback_api,"read_current_conducted_artifact",return_value=original) as read,patch.object(
                    comparison_api,"compare_conducted_twin_result",side_effect=AssertionError("nonmatched comparison0")) as compare:
                output=self.call(reference=object(),comparator_policy=object(),lineage=object())
            self.assertEqual((read.call_count,compare.call_count),(1,0));self.assertEqual(output["status"],"blocked")
            self.assertIs(output["readback"],original);self.assertIsNone(output["comparison"])
            self.assertIs(output["reasons"]["readback"],original["relation"]["reasons"])
            self.assertIsNone(output["reasons"]["comparison"]);self.assertEqual(original,before)
            PROOF["typed"].append(dict(origin="typed nonmatched gate",readback_status=status,status="blocked",readback_calls=1,comparison_calls=0))

    def test_exact_call_arguments_and_original_parent_objects_are_retained(self):
        original=readback();comparison=comparison_api._base();comparison["reasons"]=[dict(code="reference_missing",field="reference",detail=None)]
        reference=dict(data_origin="unknown");policy=dict(explicit="caller-policy");lineage=dict(explicit="caller-lineage")
        before=deepcopy((self.options,reference,policy,lineage,original,comparison))
        with patch.object(readback_api,"read_current_conducted_artifact",return_value=original) as read,patch.object(
                comparison_api,"compare_conducted_twin_result",return_value=comparison) as compare:
            output=self.call(reference=reference,comparator_policy=policy,lineage=lineage)
        self.assertEqual(read.call_args.args,("C:/caller-explicit-current","caller-intake"))
        self.assertEqual(read.call_args.kwargs,self.options)
        self.assertIs(compare.call_args.args[0],original["artifact"]["result"])
        self.assertIs(compare.call_args.args[1],reference)
        self.assertIs(compare.call_args.kwargs["comparator_policy"],policy);self.assertIs(compare.call_args.kwargs["lineage"],lineage)
        self.assertEqual((read.call_count,compare.call_count),(1,1))
        self.assertEqual(set(output),set("schema_version kind status readback comparison reasons verification".split()))
        self.assertEqual(output["status"],"not_assessed");self.assertIs(output["readback"],original);self.assertIs(output["comparison"],comparison)
        self.assertIs(output["reasons"]["comparison"],comparison["reasons"])
        self.assertEqual((self.options,reference,policy,lineage,original,comparison),before)
        for key in ("execution_authority","rerun_authority","hardware_verified","physical_verified","model_execution_verified"):
            self.assertIs(output["verification"][key],False)
        self.assertEqual(output["verification"]["metadata_authenticity"],"unknown")

    def test_matched_original_invalid_and_incomplete_use_existing_comparator_without_promotion(self):
        for status in ("invalid","incomplete"):
            original=readback(result_status=status);seen=[];compare=comparison_api.compare_conducted_twin_result
            def capture(*args,**kwargs):
                value=compare(*args,**kwargs);seen.append(value);return value
            with patch.object(readback_api,"read_current_conducted_artifact",return_value=original),patch.object(
                    comparison_api,"compare_conducted_twin_result",side_effect=capture) as called:
                output=self.call()
            self.assertEqual(called.call_count,1);self.assertIs(output["comparison"],seen[0])
            self.assertEqual(output["status"],"not_assessed")
            self.assertEqual(output["readback"]["artifact"]["result"]["status"],status)
            self.assertIsNone(output["readback"]["artifact"]["result"]["raw_measurement"])
            self.assertTrue(all(value is None for value in seen[0]["comparison"].values()))
            self.assertIsNone(seen[0]["conformity"]["verdict"])
            PROOF["typed"].append(dict(origin="typed readback with genuine existing comparator",result_status=status,
                readback_calls=1,comparison_calls=1,status="not_assessed",numeric_values_null=True))

    def test_supplied_origin_labels_are_retained_without_authenticity_or_physical_grant(self):
        for origin in ("provided_synthetic","provided_measured","provided_replay","unknown"):
            original=readback();reference=dict(data_origin=origin)
            with patch.object(readback_api,"read_current_conducted_artifact",return_value=original):
                output=self.call(reference=reference)
            compared=output["comparison"]
            self.assertEqual(output["status"],"not_assessed");self.assertEqual(compared["reference"]["data_origin"],origin)
            self.assertIs(compared["reference"]["authenticity_verified"],False)
            self.assertIs(compared["verification"]["physical_verified"],False)
            self.assertIsNone(compared["conformity"]["verdict"])

    def test_parent_errors_and_controls_propagate_same_first_object_without_retry(self):
        errors=(ValueError("unexpected"),RuntimeError("unexpected"),KeyboardInterrupt(),MemoryError(),SystemExit(7),GeneratorExit(),
                readback_api.IntakeConductedArtifactReadbackError("intake_conducted_artifact_readback_parent_invalid"))
        for layer in ("readback","comparison"):
            for error in errors:
                with self.subTest(layer=layer,error=type(error).__name__):
                    original=readback()
                    with patch.object(readback_api,"read_current_conducted_artifact",return_value=original,
                            side_effect=error if layer=="readback" else None) as read,patch.object(
                            comparison_api,"compare_conducted_twin_result",
                            side_effect=error if layer=="comparison" else AssertionError("comparison0")) as compare:
                        with self.assertRaises(type(error)) as caught:self.call()
                    self.assertIs(caught.exception,error);self.assertEqual(read.call_count,1)
                    self.assertEqual(compare.call_count,0 if layer=="readback" else 1)

    def test_malformed_parent_contracts_and_caps_fail_without_fabricated_success(self):
        error_type=self.api.IntakeConductedArtifactComparisonError
        for original in ({},dict(readback(),schema_version=True),dict(readback(),status="PASS"),
                         dict(readback(),artifact=None),dict(readback(),verification=dict(execution_authority=True))):
            with patch.object(readback_api,"read_current_conducted_artifact",return_value=original) as read,patch.object(
                    comparison_api,"compare_conducted_twin_result",side_effect=AssertionError("bad readback comparison0")) as compare:
                with self.assertRaises(error_type) as caught:self.call()
            self.assertEqual(caught.exception.code,"intake_conducted_artifact_comparison_parent_invalid")
            self.assertEqual((read.call_count,compare.call_count),(1,0))
        for comparison in ({},dict(comparison_api._base(),status="PASS"),dict(comparison_api._base(),status="compared")):
            with patch.object(readback_api,"read_current_conducted_artifact",return_value=readback()),patch.object(
                    comparison_api,"compare_conducted_twin_result",return_value=comparison) as compare:
                with self.assertRaises(error_type):self.call()
            self.assertEqual(compare.call_count,1)
        with patch.object(readback_api,"read_current_conducted_artifact",return_value=readback("blocked")),patch.object(
                self.api,"MAX_OUTPUT_BYTES",1),patch.object(comparison_api,"compare_conducted_twin_result") as compare:
            with self.assertRaises(error_type) as caught:self.call()
        self.assertEqual(caught.exception.code,"intake_conducted_artifact_comparison_output_limit");self.assertEqual(compare.call_count,0)


class GenuineBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api=importlib.import_module(MODULE)
        spec=importlib.util.spec_from_file_location("bridge_native_fixture",Path(__file__).with_name("test_intake_conducted_artifact_readback.py"))
        fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
        cls.data=fixture.CurrentArtifactReadbackTests;cls.data.setUpClass();cls.addClassCleanup(cls.data.doClassCleanups)
        cls.options=dict(deepcopy(cls.data.pins),artifact_workspace_root=str(cls.data.artifact_root),**cls.data.artifact_pins)

    def inventory(self):
        import hashlib
        return {p.relative_to(self.data.base).as_posix():(hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_size,
                p.stat().st_ino,p.stat().st_mtime_ns,p.stat().st_nlink,p.stat().st_file_attributes)
                for p in self.data.base.rglob("*") if p.is_file()}

    def test_genuine_samefirstflow_no_reference_is_original_not_assessed(self):
        before=self.inventory();reads=[];comparisons=[];connections=[];closed_ids=set();write_actions=[]
        read=readback_api.read_current_conducted_artifact;compare=comparison_api.compare_conducted_twin_result;connect=sqlite3.connect
        def profile(frame,event,method):
            if event=="c_return" and getattr(method,"__name__",None)=="close" and type(getattr(method,"__self__",None)) is sqlite3.Connection:
                closed_ids.add(id(method.__self__))
        def authorizer(action,first,second,database,origin):
            if action in (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE,sqlite3.SQLITE_CREATE_TABLE,
                          sqlite3.SQLITE_CREATE_INDEX,sqlite3.SQLITE_DROP_TABLE,sqlite3.SQLITE_DROP_INDEX,sqlite3.SQLITE_ALTER_TABLE):
                write_actions.append(action)
            return sqlite3.SQLITE_OK
        def readonly(database,*args,**kwargs):
            self.assertIn("?mode=ro",str(database))
            value=connect(database,*args,**kwargs);connections.append(value);value.set_authorizer(authorizer);return value
        def captured_read(*args,**kwargs):
            value=read(*args,**kwargs);reads.append(value);return value
        def captured_compare(*args,**kwargs):
            self.assertIs(args[0],reads[0]["artifact"]["result"])
            self.assertIsNone(args[1]);self.assertIsNone(kwargs["comparator_policy"]);self.assertIsNone(kwargs["lineage"])
            value=compare(*args,**kwargs);comparisons.append(value);return value
        previous=sys.getprofile();sys.setprofile(profile)
        try:
            with patch.object(sqlite3,"connect",side_effect=readonly),patch.object(
                    readback_api,"read_current_conducted_artifact",side_effect=captured_read) as rb,patch.object(
                    comparison_api,"compare_conducted_twin_result",side_effect=captured_compare) as cmp:
                output=self.api.compare_current_conducted_artifact(str(self.data.source_state),self.data.intake_id,**self.options)
        finally:sys.setprofile(previous)
        self.assertEqual((rb.call_count,cmp.call_count),(1,1));self.assertEqual(output["readback"]["status"],"matched")
        self.assertEqual(output["status"],"not_assessed");self.assertIs(output["readback"],reads[0]);self.assertIs(output["comparison"],comparisons[0])
        self.assertTrue(any(r["code"]=="reference_missing" for r in comparisons[0]["reasons"]))
        self.assertTrue(all(value is None for value in comparisons[0]["comparison"].values()))
        self.assertEqual(len(connections),4);self.assertTrue(all(id(c) in closed_ids for c in connections));self.assertEqual(write_actions,[])
        self.assertEqual(self.inventory(),before)
        PROOF["genuine"].append(dict(origin="fresh authored synthetic PDF/native same-plan writer -> real readback1 -> real comparator1 without reference",
            workspace=str(self.data.source_state),intake_id=self.data.intake_id,options=deepcopy(self.options),output=deepcopy(output),
            readback_calls=1,comparison_calls=1,readonly_connections=4,closed_connections=4,authorizer_writes=0,
            source_raw_native_unchanged=True,reference_policy_lineage=None,numeric_null=True,extra_api=0))

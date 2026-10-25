"""Native journal ordering, no last-success heuristic, one original builder call."""
from copy import deepcopy
import builtins
import importlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from labflow.virtual_fleet import conducted_twin_result as result_api
from labflow.virtual_fleet.journal import OperatorJournal, read_operator_journal
from labflow.virtual_fleet.policies import RFSensorFixturePolicy

MODULE = "labflow.virtual_fleet.conducted_measurement_selector"


class NativePolicy:
    policy_id = "selector_native_fixture"
    def __init__(self, waits=0, reads=0, second=False, pending_stop=False):
        self.base = RFSensorFixturePolicy();self.waits=waits;self.reads=reads
        self.second=second;self.phase=None;self.pending_stop=pending_stop

    def __call__(self, context):
        if self.waits:
            self.waits-=1;return dict(kind="advance",ticks=1)
        if self.pending_stop and context["last_receipt"] and context["observations"]["devices"]["sensor"]["values"].get("state")=="acquiring":
            return dict(kind="stop",claim="completed",reason="explicit pending stop")
        if self.phase=="advance":
            self.phase="read";return dict(kind="advance",ticks=1)
        if self.phase=="read":
            self.phase="stop";return dict(kind="execute",device_id="sensor",action="read",parameters={})
        if self.phase=="stop":return dict(kind="stop",claim="completed",reason="two native acquisitions")
        proposed=self.base(context)
        if proposed["kind"]=="stop" and proposed["claim"]=="completed":
            if self.reads:
                self.reads-=1;return dict(kind="execute",device_id="sensor",action="read",parameters={})
            if self.second:
                self.phase="advance";return dict(kind="execute",device_id="sensor",action="acquire",parameters={})
        return proposed


class SelectorSmokeTests(unittest.TestCase):
    def test_module_exists(self):
        self.assertIsNotNone(importlib.util.find_spec(MODULE),"selector is absent")


class MeasurementSelectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api=importlib.import_module(MODULE)
        spec=importlib.util.spec_from_file_location("selector_native_fixture",Path(__file__).with_name("test_virtual_fleet_conducted_twin_result.py"))
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        case=module.ConductedTwinResultTests();cls.addClassCleanup(case.doCleanups)
        cls.normal=case.genuine(policy=NativePolicy(reads=2))[0]
        cls.shifted=case.genuine(policy=NativePolicy(waits=3,reads=3))[0]
        cls.multiple=case.genuine(policy=NativePolicy(second=True))[0]
        cls.zero=case.genuine(policy=lambda context:dict(kind="stop",claim="completed",reason="no acquisition"))[0]
        cls.pending=case.genuine(policy=NativePolicy(pending_stop=True))[0]
        cls.noquantity=case.genuine(quantity=False,policy=NativePolicy(reads=2))[0]
        cls.peak=case.genuine(metric="peak",policy=NativePolicy(reads=2))[0]
        cls.other=case.genuine(power=-13,policy=NativePolicy(reads=2))[0]

    def call(self, args=None):
        return self.api.select_conducted_measurement(*(self.normal if args is None else args))

    def blocked(self,args,reason=None,calls=0):
        with patch.object(result_api,"build_conducted_twin_result",wraps=result_api.build_conducted_twin_result) as parent:
            value=self.call(args)
        self.assertEqual(value["status"],"blocked")
        self.assertIsNone(value["measurement_ref"]);self.assertIsNone(value["request_id"])
        self.assertEqual(parent.call_count,calls)
        self.assertEqual(value["verification"]["builder_calls"],calls)
        self.assertIs(value["verification"]["fallback_attempted"],False)
        self.assertTrue(value["reasons"])
        if reason:self.assertIn(reason,[r["code"] for r in value["reasons"]])
        return value

    def test_native_first_completion_not_fixed_event_or_last_report_ref(self):
        selected=[]
        for args in (self.normal,self.shifted):
            seen=[];build=result_api.build_conducted_twin_result
            def parent(*a,**k):
                value=build(*a,**k);seen.append((k,value));return value
            with patch.object(result_api,"build_conducted_twin_result",side_effect=parent) as wrapped:
                value=self.call(args)
            self.assertEqual(set(value),set("schema_version kind status candidate measurement_ref request_id reasons result verification".split()))
            self.assertEqual(value["status"],"selected")
            self.assertEqual(wrapped.call_count,1)
            self.assertEqual(value["measurement_ref"],args[3]["evidence"]["measurement_refs"][0])
            self.assertNotEqual(value["measurement_ref"],args[3]["evidence"]["measurement_refs"][-1])
            self.assertIs(value["result"],seen[0][1])
            self.assertEqual(value["result"]["status"],"recorded")
            self.assertEqual(set(value["candidate"]),set("request_id intent_ref receipt_ref measurement_ref sequence".split()))
            self.assertEqual(value["candidate"]["measurement_ref"],value["measurement_ref"])
            selected.append(value["measurement_ref"])
        self.assertNotEqual(*selected)

    def test_repeated_observations_do_not_become_multiple_acquisitions(self):
        value=self.call(self.shifted)
        intents=[e for e in self.shifted[2]["events"] if e["type"]=="intent" and e["payload"]["operation"]=="execute"
                 and e["payload"]["body"]["device_id"]=="sensor" and e["payload"]["body"]["action"]=="acquire"]
        self.assertEqual(len(intents),1)
        self.assertEqual(value["request_id"],intents[0]["payload"]["request_id"])
        self.assertGreater(len(self.shifted[3]["evidence"]["measurement_refs"]),2)

    def test_multiple_acquire_intents_are_blocked_before_parent(self):
        self.blocked(self.multiple,"acquisition_ambiguous")

    def test_zero_and_pending_without_completion_are_blocked(self):
        self.blocked(self.zero,"acquisition_missing")
        self.blocked(self.pending,"completion_missing")

    def test_genuine_parent_incomplete_preserved_and_no_fallback(self):
        for args in (self.noquantity,self.peak):
            value=self.blocked(args,"builder_incomplete",calls=1)
            self.assertEqual(value["result"]["status"],"incomplete")
            self.assertIsNone(value["result"]["calculation"]["corrected"])
            self.assertTrue(value["result"]["gaps"])
            self.assertEqual(value["candidate"]["measurement_ref"],args[3]["evidence"]["measurement_refs"][0])

    def test_genuine_foreign_plan_parent_invalid_is_preserved(self):
        mixed=[self.normal[0],*self.other[1:]]
        value=self.blocked(mixed,"builder_invalid",calls=1)
        self.assertEqual(value["result"]["status"],"invalid")
        self.assertEqual(value["result"]["failure"]["code"],"plan_binding_mismatch")

    def test_foreign_run_report_does_not_select(self):
        self.blocked([*self.normal[:3],self.other[3]],"run_binding_mismatch")

    def test_native_unterminated_prefix_is_not_repaired(self):
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup)
        path=Path(directory.name)/"prefix.jsonl"
        stored=self.normal[2];header=stored["header"]
        with OperatorJournal(path,run_id=header["run_id"],runtime_instance_id=header["runtime_instance_id"],provenance=header["provenance"]) as sink:
            for event in stored["events"][:-1]:sink(event)
        prefix=read_operator_journal(path)
        self.assertFalse(prefix["complete"])
        self.blocked([*self.normal[:2],prefix,self.normal[3]],"execution_incomplete")

    def test_input_immutable_and_pure_runtime_without_file_or_device_calls(self):
        before=deepcopy(self.normal)
        with patch.object(builtins,"open",side_effect=AssertionError("pure")), patch.object(io,"open",side_effect=AssertionError("pure")), patch.object(
                Path,"read_bytes",side_effect=AssertionError("no refs")):
            value=self.call()
        self.assertEqual(self.normal,before)
        value["result"]["binding"]["plan_input"]["plan"]["source_settings"]["power_dbm"]=999
        self.assertEqual(self.normal,before)
        flags=value["verification"]
        for name in ("model_execution_verified","hardware_verified","physical_verified","execution_authority"):
            self.assertIs(flags[name],False)

    def test_first_control_and_unexpected_builder_errors_propagate_same_object(self):
        for error in (KeyboardInterrupt(),MemoryError(),SystemExit(0),GeneratorExit(),RuntimeError("unexpected")):
            with self.subTest(error=type(error).__name__),patch.object(result_api,"build_conducted_twin_result",side_effect=error) as parent:
                with self.assertRaises(type(error)) as caught:self.call()
                self.assertIs(caught.exception,error);self.assertEqual(parent.call_count,1)

    def test_native_caps_and_bad_inputs_are_blocked_without_parent(self):
        with patch.object(self.api,"MAX_INPUT_BYTES",1):self.blocked(self.normal,"input_limit")
        self.blocked([None,*self.normal[1:]])
        class Foreign(list):pass
        self.blocked([self.normal[0],Foreign(self.normal[1]),*self.normal[2:]],"input_invalid")


FIX_PROOF = dict(ordinary=[], known=[])


class SelectorBuilderFailureFixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api=importlib.import_module(MODULE)
        spec=importlib.util.spec_from_file_location("selector_fix_native_fixture",Path(__file__).with_name("test_virtual_fleet_conducted_twin_result.py"))
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        case=module.ConductedTwinResultTests();cls.addClassCleanup(case.doCleanups)
        cls.args=case.genuine()[0]
        FIX_PROOF["native_inputs"]=deepcopy(cls.args)

    def test_unexpected_ordinary_builder_errors_preserve_first_object(self):
        for error in (ValueError("unexpected builder"),TypeError("unexpected builder"),KeyError("unexpected builder"),
                      OverflowError(),RecursionError(),UnicodeError(),StopIteration()):
            with self.subTest(error=type(error).__name__):
                before=deepcopy(self.args)
                with patch.object(result_api,"build_conducted_twin_result",side_effect=error) as parent:
                    with self.assertRaises(type(error)) as caught:
                        self.api.select_conducted_measurement(*self.args)
                self.assertIs(caught.exception,error);self.assertEqual(parent.call_count,1);self.assertEqual(self.args,before)
                FIX_PROOF["ordinary"].append(dict(error_type=type(error).__name__,same_object=True,parent_calls=1,inputs_unchanged=True))

    def test_malformed_native_input_and_known_parent_failure_still_block(self):
        for marker in (object(),"\ud800"):
            args=deepcopy(self.args);args[0]["extra"]=marker
            with patch.object(result_api,"build_conducted_twin_result",side_effect=AssertionError("input parent0")) as parent:
                value=self.api.select_conducted_measurement(*args)
            self.assertEqual(value["status"],"blocked");self.assertEqual(parent.call_count,0)
            self.assertIsNone(value["measurement_ref"]);self.assertIsNone(value["request_id"]);self.assertIsNone(value["result"])
            self.assertFalse(value["verification"]["fallback_attempted"])
            FIX_PROOF["known"].append(dict(origin="malformed provided native input",status="blocked",parent_calls=0))
        error=result_api._Failure("native_input_invalid","input")
        with patch.object(result_api,"build_conducted_twin_result",side_effect=error) as parent:
            value=self.api.select_conducted_measurement(*self.args)
        self.assertEqual(value["status"],"blocked");self.assertEqual(parent.call_count,1)
        self.assertEqual(value["reasons"][0]["code"],"parent_validation")
        self.assertEqual(value["reasons"][0]["detail"],dict(code="native_input_invalid"))
        self.assertIsNotNone(value["candidate"]);self.assertIsNone(value["result"])
        FIX_PROOF["known"].append(dict(origin="existing typed parent _Failure",status="blocked",parent_calls=1))

    def test_malformed_returned_dto_still_uses_known_validation_route(self):
        for returned in (dict(bad=float("nan")),dict(bad="\ud800")):
            with patch.object(result_api,"build_conducted_twin_result",return_value=returned) as parent:
                value=self.api.select_conducted_measurement(*self.args)
            self.assertEqual(value["status"],"blocked");self.assertEqual(parent.call_count,1)
            self.assertIsNotNone(value["candidate"]);self.assertIsNone(value["result"])
            self.assertIsNone(value["measurement_ref"]);self.assertIsNone(value["request_id"])
            self.assertFalse(value["verification"]["fallback_attempted"])
            FIX_PROOF["known"].append(dict(origin="malformed parent returned DTO",status="blocked",parent_calls=1))

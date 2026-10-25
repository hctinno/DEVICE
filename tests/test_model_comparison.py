"""Offline typed doubles. Actual auth, network and generation counts are zero."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import threading
import types
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from labflow import model_comparison as mc

PROJECT = "project-a6310591-f8cc-487c-9e3"
MODELS = ("gemini-4-argon", "gemini-3.8-flash")
LEVELS = ("LOW", "MEDIUM", "HIGH")
PROMPT = "{\"binding\":{\"scenario_id\":\"DGM-AI-CONNECTION-001\",\"scenario_version\":1},\"kind\":\"connection_model_prompt\",\"messages\":[{\"content\":\"This is a synthetic DGM AutoLab connection test. Do not call tools, inspect files, use networks, operate equipment, or claim operational authority. Return exactly one JSON object satisfying the supplied response schema. No Markdown or additional text.\",\"role\":\"system\"},{\"content\":\"Return schema_version 1, status \\\"ok\\\", synthetic true, and equipment_authorized false. This verifies only a bounded model connection, not test execution or business quality.\",\"role\":\"user\"}],\"schema_version\":1,\"synthetic\":true}".encode("utf-8")
SCHEMA = "{\"additionalProperties\":false,\"properties\":{\"equipment_authorized\":{\"const\":false,\"type\":\"boolean\"},\"schema_version\":{\"const\":1,\"type\":\"integer\"},\"status\":{\"const\":\"ok\",\"type\":\"string\"},\"synthetic\":{\"const\":true,\"type\":\"boolean\"}},\"required\":[\"schema_version\",\"status\",\"synthetic\",\"equipment_authorized\"],\"type\":\"object\"}".encode("utf-8")
ANSWER = b'{"equipment_authorized":false,"schema_version":1,"status":"ok","synthetic":true}'


def canonical(x):
    return json.dumps(x,ensure_ascii=False,sort_keys=True,
                      separators=(",",":"),allow_nan=False).encode("utf-8")


def sha(x):
    return hashlib.sha256(x).hexdigest()


def profile():
    return dict(schema_version=1,profile_id="vertex-trial",provider="vertex_ai",
        project_id=PROJECT,location="global",quota_project_id=PROJECT,
        auth_profile_id="vertex-trial",selected_model=MODELS[1],revision=0,
        models={m:dict(thinking_level="MEDIUM",max_output_tokens=512,timeout_seconds=60)
                for m in MODELS})


def resolve(p, *, model_id=None, overrides=None):
    """Fixed D1 typed seam, not its separately owned implementation."""
    m=p["selected_model"] if model_id is None else model_id
    options=dict(p["models"][m]); options.update({} if overrides is None else overrides)
    s=dict(schema_version=1,kind="ai_run_settings",profile_id=p["profile_id"],
        profile_revision=p["revision"],provider=p["provider"],
        service="aiplatform.googleapis.com",project_id=p["project_id"],
        location=p["location"],quota_project_id=p["quota_project_id"],
        auth_profile_id=p["auth_profile_id"],model_id=m,
        profile_sha256=sha(canonical(p)),**options)
    s["settings_sha256"]=sha(canonical(s))
    return s


class VertexError(RuntimeError):
    def __init__(self,suffix,receipt=None):
        self.code="vertex_response_"+suffix; self.receipt=receipt
        super().__init__(self.code)


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name).resolve()
        self.adc=self.root/"isolated-adc.json"
        self.adc.write_bytes(b'{"private":"not a real credential"}')
        self.evidence=self.root/"evidence"
        self.budget=self.root/"budget.json"; self.approval=self.root/"approval.json"
        self.p=profile(); self.calls=[]; self.inspections=[]
        self.response=ANSWER; self.injected_error=None
        d1=types.ModuleType("labflow.ai_connection_profiles"); d1.resolve_run_settings=resolve
        d2=types.ModuleType("labflow.vertex_response")
        d2.VertexResponseError=VertexError
        d2.inspect_vertex_credentials=self.inspect; d2.produce_vertex_response=self.produce
        modules=patch.dict(sys.modules,{"labflow.ai_connection_profiles":d1,"labflow.vertex_response":d2})
        modules.start(); self.addCleanup(modules.stop); self.seed()

    def seed(self):
        now=datetime.now(timezone.utc)
        a=dict(schema_version=1,kind="vertex_comparison_approval",approval_id="root-1",
            scope_id="synthetic-connection-v1",budget_id="shared-1",project_id=PROJECT,
            quota_project_id=PROJECT,auth_profile_id="vertex-trial",
            scenario_id="DGM-AI-CONNECTION-001",evaluator_id="connection-json-v1",
            prompt_sha256=sha(PROMPT),response_schema_sha256=sha(SCHEMA),execution_mode="actual",
            trial=dict(status="confirmed",source="root_console",observed_at=now.isoformat(),
                credit_amount="407626",credit_currency="KRW",remaining_days=90),
            limits=dict(generation_posts=6,max_output_tokens=512,reserved_output_tokens=3072,
                timeout_seconds=60,wall_seconds=300,retries=0,continuations=0),
            issued_at=(now-timedelta(minutes=1)).isoformat(),
            expires_at=(now+timedelta(hours=23)).isoformat())
        b=dict(schema_version=1,kind="vertex_comparison_budget",budget_id="shared-1",
            project_id=PROJECT,revision=0,call_limit=6,output_token_limit=3072,
            reserved_calls=0,reserved_output_tokens=0,active_run_id=None,entries=[])
        self.approval.write_bytes(canonical(a)); self.budget.write_bytes(canonical(b))

    def matrix(self,**kw):
        return mc.build_vertex_comparison_matrix(self.p,PROMPT,SCHEMA,
            batch_id=kw.pop("batch_id","batch-1"),scenario_id="DGM-AI-CONNECTION-001",
            evaluator_id="connection-json-v1",**kw)

    def run_batch(self,matrix=None,**kw):
        args=dict(adc_path=self.adc,evidence_dir=self.evidence,budget_path=self.budget,
                  approval_path=self.approval); args.update(kw)
        return mc.run_vertex_comparison_batch(self.matrix() if matrix is None else matrix,
                                              PROMPT,SCHEMA,**args)

    def inspect(self,adc_path,*,settings):
        self.inspections.append(copy.deepcopy(settings))
        return dict(schema_version=1,kind="vertex_credentials_metadata",
            settings_sha256=settings["settings_sha256"],auth_profile_id=settings["auth_profile_id"],
            credential_type="authorized_user",quota_project_id=PROJECT,
            token_endpoint="https://oauth2.googleapis.com/token",metadata_valid=True,
            refresh_attempted=False,model_access_verified=False,credit_status_verified=False)

    def produce(self,prompt_bytes,response_schema_bytes,*,settings,adc_path,evidence_dir,cancel_event=None):
        self.calls.append(copy.deepcopy(settings))
        if self.injected_error is not None: raise self.injected_error
        evidence_dir.mkdir()
        wrapper=canonical(dict(prompt_dto_utf8=prompt_bytes.decode("utf-8"),
                               response_schema_utf8=response_schema_bytes.decode("utf-8")))
        payload=canonical(dict(contents=[dict(role="user",parts=[dict(text=wrapper.decode("utf-8"))])],
            generationConfig=dict(maxOutputTokens=settings["max_output_tokens"],
                thinkingConfig=dict(thinkingLevel=settings["thinking_level"]))))
        artifacts={}
        blobs=dict(prompt=("request.json",prompt_bytes),response_schema=("response-schema.json",response_schema_bytes),
            settings=("settings.json",canonical(settings)),provider_request=("provider-request.json",payload),
            provider_response=("provider-response.bin",b'{"offline_fixture":true}'),
            final_text=("response-text.bin",self.response))
        for name,(filename,raw) in blobs.items():
            (evidence_dir/filename).write_bytes(raw)
            artifacts[name]=dict(path=filename,present=True,bytes=len(raw),sha256=sha(raw),
                                complete=True,overflow=False,extent="whole_file")
        receipt=dict(schema_version=1,kind="vertex_response_receipt",
            exchange_ref="vertex-exchange:"+format(len(self.calls),"032x"),status="complete",failure=None,
            bindings=dict(prompt_sha256=sha(prompt_bytes),schema_sha256=sha(response_schema_bytes),
                provider_payload_sha256=sha(payload),settings_sha256=settings["settings_sha256"]),
            settings=copy.deepcopy(settings),
            client=dict(transport="REST",api_version="v1",google_auth_version="2.62.0",
                        requests_version="2.34.2",google_genai_used=False),
            request=dict(method="POST",url="https://aiplatform.googleapis.com/v1/projects/"+PROJECT+
                "/locations/global/publishers/google/models/"+settings["model_id"]+":generateContent",
                quota_project_id=PROJECT,auth_profile_id="vertex-trial"),
            attempts=dict(worker_process_attempts=1,auth_refresh_attempts=1,auth_http_attempts=1,
                generation_post_attempts=1,auth_refresh_completed=True,auth_retry_blocked=False,application_retries=0),
            response=dict(http_status=200,auth_http_status=200,finish_reason="STOP",
                reported_model_version="provider-version-1",provider_response_id="response-1",
                text_parts=1,thought_parts=0),
            usage=None,cost=dict(kind="unknown",amount=None,currency=None,price_version=None),
            timing=dict(timeout_seconds=float(settings["timeout_seconds"]),local_elapsed_seconds=0.01),
            cancellation=dict(requested=False,local_worker_stopped=True,
                provider_completion="observed_stop",remote_cancel_verified=False),
            cleanup=dict(worker_reaped=True,worker_exit_code=0,transport_handles_closed=True,
                artifact_handles_closed=True,secondary_errors=[],remote_cancellation_verified=False),
            artifacts=artifacts,verification=dict(wire_complete=True,credential_metadata_verified=True,
                remote_identity_verified=False,semantic_quality_verified=False,credit_verified=False))
        return self.response,receipt

    def edit(self,path,fn):
        d=json.loads(path.read_bytes()); fn(d); path.write_bytes(canonical(d))

    def test_matrix_order_and_detached(self):
        m=self.matrix()
        self.assertEqual([(r["settings"]["model_id"],r["settings"]["thinking_level"]) for r in m["rows"]],
                         [(a,b) for a in MODELS for b in LEVELS])
        self.assertEqual(len(m),11); before=canonical(m)
        self.p["models"][MODELS[0]]["max_output_tokens"]=8192
        self.assertEqual(canonical(m),before)
        m["rows"][0]["settings"]["thinking_level"]="HIGH"
        self.assertEqual(m["rows"][1]["settings"]["thinking_level"],"MEDIUM")

    def test_selected_saved_model_override(self):
        m=self.matrix(selection="selected",overrides={"thinking_level":"HIGH","max_output_tokens":128})
        self.assertEqual(m["selection"]["row_indexes"],[5])
        self.assertEqual([i for i,r in enumerate(m["rows"]) if r["settings"] is not None],[5])
        out=self.run_batch(m)
        self.assertEqual([r["reason_code"] for r in out["rows"][:5]],["not_selected"]*5)
        self.assertEqual(len(self.calls),1); self.assertEqual(self.calls[0]["max_output_tokens"],128)

    def test_matrix_rejects_contradictory_selection(self):
        for kw in (dict(model_id=MODELS[0]),dict(overrides={"thinking_level":"HIGH"}),
                   dict(selection="other"),dict(overrides={"thinking_budget":10})):
            with self.subTest(kw=kw),self.assertRaises(mc.ModelComparisonError): self.matrix(**kw)

    def test_exact_registered_pair_only(self):
        for prompt,schema,scenario in ((PROMPT+b" ",SCHEMA,"DGM-AI-CONNECTION-001"),
                (PROMPT,SCHEMA,"different"),(bytearray(PROMPT),SCHEMA,"DGM-AI-CONNECTION-001")):
            with self.subTest(scenario=scenario),self.assertRaises(mc.ModelComparisonError):
                mc.build_vertex_comparison_matrix(self.p,prompt,schema,batch_id="b",
                    scenario_id=scenario,evaluator_id="connection-json-v1")

    def test_success_receipts_and_records(self):
        out=self.run_batch(); self.assertEqual(len(out),8); self.assertEqual(len(out["rows"]),6)
        self.assertEqual(len(self.calls),6); self.assertEqual(out["summary"]["success_rows"],6)
        self.assertEqual(out["business_assessment"],"not_assessed")
        self.assertEqual(out["summary"]["generation_post_attempts"],6)
        for i,r in enumerate(out["rows"]):
            self.assertEqual(len(r),15); self.assertEqual(r["strict_decode"]["status"],"checked")
            self.assertEqual(r["assessment"]["status"],"not_assessed")
            self.assertIsNone(r["receipt"]["usage"])
            self.assertEqual(r["receipt"]["response"]["reported_model_version"],"provider-version-1")
            self.assertEqual(json.loads((self.evidence/f"row-{i}.record.json").read_bytes()),r)
        b=json.loads(self.budget.read_bytes())
        self.assertEqual((b["reserved_calls"],b["reserved_output_tokens"]),(6,3072))
        self.assertIsNone(b["active_run_id"]); self.assertEqual(len(b["entries"]),6)

    def test_no_silent_clamp(self):
        self.p["models"][MODELS[0]]["max_output_tokens"]=8192
        out=self.run_batch()
        self.assertEqual(out["rows"][0]["settings"]["max_output_tokens"],8192)
        self.assertEqual(out["rows"][0]["reason_code"],"budget_rejected"); self.assertEqual(self.calls,[])

    def test_precancel_zero_inspection_reservation_dispatch(self):
        event=threading.Event(); event.set(); out=self.run_batch(cancel_event=event)
        self.assertEqual(self.calls,[]); self.assertEqual(self.inspections,[])
        self.assertEqual(out["rows"][0]["reason_code"],"cancelled")
        self.assertEqual(json.loads(self.budget.read_bytes())["reserved_calls"],0)

    def test_gate_refuses_invalid_scopes(self):
        changes=[lambda a:a.update(scenario_id="other"),lambda a:a.update(execution_mode="mock"),
            lambda a:a["trial"].update(status="unknown"),lambda a:a.update(quota_project_id="different"),
            lambda a:a["limits"].update(generation_posts=7),
            lambda a:a.update(expires_at=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat())]
        for i,change in enumerate(changes):
            self.seed(); self.edit(self.approval,change)
            out=self.run_batch(evidence_dir=self.root/f"gate-{i}")
            self.assertEqual(out["summary"]["not_run_rows"],6); self.assertEqual(self.calls,[])

    def test_missing_corrupt_budget_never_reinitialized(self):
        for i,raw in enumerate((None,b'{"reserved_calls":0}',b'{"x":1,"x":2}')):
            if self.budget.exists(): self.budget.unlink()
            if raw is not None: self.budget.write_bytes(raw)
            out=self.run_batch(evidence_dir=self.root/f"bad-{i}")
            self.assertEqual(out["summary"]["not_run_rows"],6); self.assertEqual(self.calls,[])
            self.assertEqual(self.budget.read_bytes() if self.budget.exists() else None,raw)

    def test_new_batch_cannot_reset_budget(self):
        self.run_batch()
        out=self.run_batch(self.matrix(batch_id="batch-2"),evidence_dir=self.root/"second")
        self.assertEqual(len(self.calls),6); self.assertEqual(out["rows"][0]["reason_code"],"budget_rejected")

    def test_scope_allows_profile_revision_batch_and_override(self):
        self.run_batch(self.matrix(selection="selected",model_id=MODELS[0],overrides={"thinking_level":"LOW"}))
        self.p["revision"]=1
        out=self.run_batch(self.matrix(batch_id="new",selection="selected",overrides={"thinking_level":"HIGH"}),
                           evidence_dir=self.root/"second")
        self.assertEqual(len(self.calls),2); self.assertEqual(out["summary"]["cumulative_reserved_calls"],2)

    def test_tampered_matrix_before_inspection(self):
        m=self.matrix(); m["rows"][0]["settings"]["thinking_level"]="HIGH"
        with self.assertRaises(mc.ModelComparisonError): self.run_batch(m)
        self.assertEqual(self.inspections,[])

    def test_strict_connection_decoder(self):
        bad=(b"true",ANSWER+b" text",bytes([96])*3+b"json\\n"+ANSWER+bytes([96])*3,
            ANSWER.replace(b'"schema_version":1',b'"schema_version":true'),
            ANSWER.replace(b'"schema_version":1',b'"schema_version":1.0'),
            ANSWER.replace(b'"status":"ok"',b'"status":"ok","status":"ok"'),
            ANSWER.replace(b'"synthetic":true',b'"synthetic":NaN'),
            ANSWER.replace(b'"equipment_authorized":false',b'"equipment_authorized":true'))
        for i,raw in enumerate(bad):
            self.seed(); self.response=raw; out=self.run_batch(evidence_dir=self.root/f"strict-{i}")
            self.assertEqual(out["rows"][0]["status"],"failed")
            self.assertEqual(out["rows"][0]["strict_decode"]["status"],"rejected")
            self.assertEqual(out["rows"][1]["status"],"not_run")

    def test_artifact_tamper(self):
        original=self.produce
        def corrupt(*a,**kw):
            raw,r=original(*a,**kw); (kw["evidence_dir"]/"response-text.bin").write_bytes(b"different")
            return raw,r
        with patch.object(sys.modules["labflow.vertex_response"],"produce_vertex_response",corrupt):
            out=self.run_batch()
        self.assertEqual(out["rows"][0]["reason_code"],"receipt_invalid")

    def test_receipt_tamper(self):
        original=self.produce
        changes=(lambda r:r["bindings"].update(settings_sha256="0"*64),
            lambda r:r["attempts"].update(generation_post_attempts=2),
            lambda r:r["response"].update(finish_reason="MAX_TOKENS"),
            lambda r:r["cleanup"].update(worker_reaped=False),lambda r:r["cost"].update(amount=0),
            lambda r:r.update(usage={"unknown":0}),lambda r:r.update(extra="untrusted"))
        for i,change in enumerate(changes):
            self.seed()
            def bad(*a,**kw):
                raw,r=original(*a,**kw); change(r); return raw,r
            with patch.object(sys.modules["labflow.vertex_response"],"produce_vertex_response",bad):
                out=self.run_batch(evidence_dir=self.root/f"receipt-{i}")
            self.assertEqual(out["rows"][0]["reason_code"],"receipt_invalid")

    def test_known_failure_no_refund(self):
        self.injected_error=VertexError("auth_failed"); out=self.run_batch()
        self.assertEqual(out["rows"][0]["reason_code"],"vertex_response_auth_failed")
        self.assertEqual(out["rows"][0]["status"],"unknown")
        self.assertIsNone(out["summary"]["generation_post_attempts"])
        self.assertEqual(json.loads(self.budget.read_bytes())["reserved_calls"],1)

    def test_controls_preserve_identity_and_reservation(self):
        for i,exc in enumerate((KeyboardInterrupt(),SystemExit(7),GeneratorExit(),MemoryError())):
            self.seed(); self.injected_error=exc
            with self.subTest(type=type(exc).__name__),self.assertRaises(type(exc)) as caught:
                self.run_batch(evidence_dir=self.root/f"control-{i}")
            self.assertIs(caught.exception,exc)
            b=json.loads(self.budget.read_bytes()); self.assertEqual(b["reserved_calls"],1)
            self.assertIsNotNone(b["active_run_id"])

    def test_unexpected_exception_not_swallowed(self):
        self.injected_error=RuntimeError("private unformatted failure")
        with self.assertRaises(RuntimeError) as caught: self.run_batch()
        self.assertIs(caught.exception,self.injected_error)
        self.assertEqual(json.loads(self.budget.read_bytes())["reserved_calls"],1)

    def test_duplicate_run_no_retry(self):
        m=self.matrix(selection="selected"); self.run_batch(m)
        out=self.run_batch(m,evidence_dir=self.root/"duplicate")
        self.assertEqual(len(self.calls),1); self.assertEqual(out["rows"][4]["reason_code"],"run_already_reserved")

    def test_timeout_not_reduced(self):
        with patch.object(mc.time,"monotonic",side_effect=[0]+[245]*100):
            out=self.run_batch()
        self.assertEqual(self.calls,[]); self.assertEqual(out["rows"][0]["reason_code"],"wall_limit")

    def test_row_api_index(self):
        m=self.matrix()
        r=mc.run_vertex_comparison_row(m,2,PROMPT,SCHEMA,adc_path=self.adc,evidence_dir=self.evidence,
                                      budget_path=self.budget,approval_path=self.approval)
        self.assertEqual(r["row_index"],2); self.assertEqual(len(self.calls),1)
        for bad in (-1,6,True,0.0):
            with self.assertRaises(mc.ModelComparisonError):
                mc.run_vertex_comparison_row(m,bad,PROMPT,SCHEMA,adc_path=self.adc,evidence_dir=self.root/"unused",
                                            budget_path=self.budget,approval_path=self.approval)

    def test_native_paths_event(self):
        for kw in (dict(adc_path=str(self.adc)),dict(budget_path=Path("relative")),dict(cancel_event=object())):
            with self.assertRaises(mc.ModelComparisonError): self.run_batch(**kw)
        self.assertEqual(self.calls,[])

    def test_fixed_clean_error_constructor(self):
        for value in ("invalid_input","limit_exceeded","state_error","dependency_unavailable","private",None,True):
            e=mc.ModelComparisonError(value); self.assertEqual(str(e),e.code); self.assertEqual(e.args,(e.code,))
            self.assertIsNone(e.__cause__); self.assertIsNone(e.__context__); self.assertTrue(e.__suppress_context__)

    def test_active_budget_blocks(self):
        def active(b):
            s=resolve(self.p,model_id=MODELS[0],overrides={"thinking_level":"LOW"})
            b.update(revision=1,reserved_calls=1,reserved_output_tokens=512,active_run_id="stale")
            b["entries"]=[dict(reservation_id="reserve-1",batch_id="old",run_id="stale",row_index=0,
                matrix_sha256="0"*64,settings_sha256=s["settings_sha256"],output_tokens=512,state="reserved",
                record_ref=None,receipt_ref=None)]
        self.edit(self.budget,active); out=self.run_batch()
        self.assertEqual(self.calls,[]); self.assertEqual(out["rows"][0]["reason_code"],"budget_busy")

    def test_missing_transport_closed(self):
        original=mc.importlib.import_module
        def missing(name):
            if name=="labflow.vertex_response": raise ModuleNotFoundError(name=name)
            return original(name)
        with patch.object(mc.importlib,"import_module",side_effect=missing): out=self.run_batch()
        self.assertEqual(self.calls,[]); self.assertEqual(out["rows"][0]["reason_code"],"dependency_unavailable")



    def test_invalid_native_profile_fields_use_fixed_error(self):
        for key,value in (("location",[]),("location",{}),("schema_version",True),
                          ("revision",True),("models",[])):
            self.p=profile(); self.p[key]=value
            with self.subTest(key=key,value=value),self.assertRaises(mc.ModelComparisonError):
                self.matrix()

    def test_input_native_tree_and_clean_raised_error(self):
        class Hostile(dict):
            def items(self):
                raise AssertionError("must not invoke subclass hooks")
        bad=[Hostile(),{"bad":"\ud800"},{"bad":float("nan")},{"bad":2**63}]
        cycle={}; cycle["cycle"]=cycle; bad.append(cycle)
        for value in bad:
            try:
                raise RuntimeError("outer private context")
            except RuntimeError:
                with self.assertRaises(mc.ModelComparisonError) as caught:
                    self.matrix(overrides=value)
            self.assertIsNone(caught.exception.__cause__)
            self.assertIsNone(caught.exception.__context__)

    def test_no_dispatch_when_reservation_consumes_remaining_wall(self):
        original=mc._reserve
        clock=[0]
        def slow(*a,**kw):
            result=original(*a,**kw); clock[0]=400; return result
        with patch.object(mc.time,"monotonic",side_effect=lambda:clock[0]),patch.object(mc,"_reserve",slow):
            out=self.run_batch()
        self.assertEqual(self.calls,[])
        self.assertEqual(out["rows"][0]["reason_code"],"wall_limit")
        self.assertEqual(json.loads(self.budget.read_bytes())["reserved_calls"],1)

    def test_expiry_rechecked_after_reservation(self):
        original=mc._reserve
        def revoke(*a,**kw):
            result=original(*a,**kw)
            self.edit(self.approval,lambda x:x.update(expires_at=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()))
            return result
        with patch.object(mc,"_reserve",revoke): out=self.run_batch()
        self.assertEqual(self.calls,[])
        self.assertEqual(out["rows"][0]["reason_code"],"gate_rejected")

    def test_known_failed_receipt_retained_without_decode(self):
        original=self.produce
        captured=[]
        def incomplete(*a,**kw):
            raw,r=original(*a,**kw)
            r.update(status="failed",failure=dict(code="vertex_response_incomplete",phase="collect"))
            r["response"]["finish_reason"]="MAX_TOKENS"
            r["verification"]["wire_complete"]=False
            r["cancellation"]["provider_completion"]="observed_incomplete"
            captured.append(copy.deepcopy(r)); raise VertexError("incomplete",r)
        with patch.object(sys.modules["labflow.vertex_response"],"produce_vertex_response",incomplete):
            out=self.run_batch()
        self.assertEqual(out["rows"][0]["receipt"],captured[0])
        self.assertEqual(out["rows"][0]["status"],"failed")
        self.assertEqual(out["rows"][0]["strict_decode"]["status"],"not_run")
        self.assertEqual(out["summary"]["generation_post_attempts"],1)
        self.assertIsNone(json.loads(self.budget.read_bytes())["active_run_id"])

    def test_concurrent_dispatch_blocked_without_rpc_lock(self):
        entered=threading.Event(); release=threading.Event()
        original=self.produce; outputs=[]; failures=[]
        def blocked(*a,**kw):
            entered.set()
            if not release.wait(5): raise AssertionError("test rendezvous failed")
            return original(*a,**kw)
        def first():
            try: outputs.append(self.run_batch(self.matrix(selection="selected",model_id=MODELS[0])))
            except BaseException as e: failures.append(e)
        with patch.object(sys.modules["labflow.vertex_response"],"produce_vertex_response",blocked):
            thread=threading.Thread(target=first); thread.start()
            try:
                self.assertTrue(entered.wait(5))
                with mc._locked(self.budget):
                    pass
                second=self.run_batch(self.matrix(batch_id="concurrent",selection="selected"),
                                      evidence_dir=self.root/"second")
                self.assertEqual(second["rows"][4]["reason_code"],"budget_busy")
            finally:
                release.set(); thread.join(5)
            self.assertFalse(thread.is_alive()); self.assertEqual(failures,[])
            self.assertEqual(len(outputs),1); self.assertEqual(len(self.calls),1)

    def test_budget_aggregate_tamper_fails_closed(self):
        self.edit(self.budget,lambda b:b.update(reserved_calls=1))
        out=self.run_batch()
        self.assertEqual(self.calls,[])
        self.assertEqual(out["rows"][0]["reason_code"],"gate_rejected")

    def test_path_alias_and_hardlink_denied(self):
        import os
        for name in ("alias~1","trailing.","name:stream"):
            with self.subTest(name=name),self.assertRaises(mc.ModelComparisonError):
                self.run_batch(budget_path=self.root/name)
        alias=self.root/"hardlink.json"; os.link(self.adc,alias)
        with self.assertRaises(mc.ModelComparisonError): self.run_batch(adc_path=alias)


    def test_missing_profile_dependency_fixed_error(self):
        with patch.object(mc.importlib,"import_module",
                          side_effect=ModuleNotFoundError(name="labflow.ai_connection_profiles")):
            with self.assertRaises(mc.ModelComparisonError) as caught: self.matrix()
        self.assertEqual(caught.exception.code,"model_comparison_dependency_unavailable")
        self.assertEqual(self.calls,[])

    def test_raw_transport_output_subclass_hooks_not_called(self):
        class Hostile:
            def __eq__(self,other):
                raise AssertionError("raw output hook must not run")
        original=self.produce
        def hostile(*a,**kw):
            raw,r=original(*a,**kw); return Hostile(),r
        with patch.object(sys.modules["labflow.vertex_response"],"produce_vertex_response",hostile):
            out=self.run_batch()
        self.assertEqual(out["rows"][0]["reason_code"],"receipt_invalid")

    def test_record_io_failure_keeps_reservation_and_fixed_error(self):
        real_record=mc._record
        def fail_record(*a,**kw):
            raise mc.ModelComparisonError("state_error")
        with patch.object(mc,"_record",fail_record),self.assertRaises(mc.ModelComparisonError):
            self.run_batch()
        self.assertEqual(json.loads(self.budget.read_bytes())["reserved_calls"],1)
        self.assertIsNotNone(json.loads(self.budget.read_bytes())["active_run_id"])

    def test_preset_cancel_after_reservation_no_dispatch_no_refund(self):
        event=threading.Event(); original=mc._reserve
        def cancel(*a,**kw):
            result=original(*a,**kw); event.set(); return result
        with patch.object(mc,"_reserve",cancel): out=self.run_batch(cancel_event=event)
        self.assertEqual(self.calls,[]); self.assertEqual(out["rows"][0]["reason_code"],"cancelled")
        self.assertEqual(out["rows"][0]["budget"]["generation_post_attempts"],0)
        self.assertEqual(json.loads(self.budget.read_bytes())["reserved_calls"],1)

if __name__=="__main__":
    unittest.main()

"""046 core only: trusted binding/RLock and genuine043/025/042, no fake host."""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch

from labflow import intake_reference_review_host as host
from labflow import intake_reference_review as parent042
from labflow.store import Store,canonical
from labflow.intake_jobs import respond
from tests import test_intake_reference_ledger as fixture

EPOCH='a'*64;SCOPE='b'*64
BIND={'host_epoch':EPOCH,'scope_epoch':SCOPE,'session_id':'c'*64}
ROOT=Path(__file__).resolve().parents[1]


class ReferenceReviewHostTests(unittest.TestCase):
    revision=fixture.ReferenceLedgerTests.revision
    base=fixture.ReferenceLedgerTests.base
    namespace=fixture.ReferenceLedgerTests.namespace
    counts=fixture.ReferenceLedgerTests.counts

    def setUp(self):
        fixture.ReferenceLedgerTests.setUp(self)
        self.legacy=self.store;self.store=Store.open_existing(str(self.legacy.root));self.addCleanup(self.store.close)
        self.lock=threading.RLock()

    def supplied(self):return {'intake_id':self.intake,'case_context':self.context,'validated_response':self.response,'producer_name':self.response['expected_producer']['name']}
    def create(self,**changes):
        options={'host_epoch':EPOCH,'scope_epoch':SCOPE,'runtime_lock':self.lock,'read_scope':'workspace','append_scope':'workspace','review_inputs':(self.supplied(),)}
        options.update(changes);actions=host.create_reference_review_actions(self.store,self.catalog,**options)
        self.addCleanup(actions.close);return actions
    def prepare(self,actions,binding=None,replace=None):
        binding=BIND if binding is None else binding;caps=actions.capabilities(binding,self.intake)
        return actions.prepare(binding,self.intake,{'schema_version':1,'review_input_id':caps['review_input_id'],'replace_handle_id':replace})
    def request(self,p):
        v=p['preview'];return {'schema_version':1,'handle_id':p['handle_id'],'intake_id':self.intake,'request_id':p['append_request_id'],
            'preparation_id':v['preparation_id'],'expected_snapshot_id':v['observation']['snapshot_id'],'expected_head_record_id':v['observation']['head_record_id']}
    def error(self,suffix,operation,status=None,prefix='intake_reference_review_host_'):
        with self.assertRaises(ValueError) as caught:operation()
        e=caught.exception;code=prefix+suffix
        self.assertEqual((getattr(e,'code',None),str(e),e.args),(code,code,(code,)))
        self.assertIsNone(e.__context__);self.assertIsNone(e.__cause__)
        if status is not None:self.assertEqual(e.status,status)
        self.assertNotIn('MODEL-A',repr(e));self.assertNotIn(str(self.root),repr(e))

    @contextmanager
    def paused_parent(self,function,*,append=False,parent_function=None):
        entered=threading.Event();release=threading.Event();finished=threading.Event();results=[]
        target=parent_function or (parent042.append_reference_review if append else parent042.prepare_reference_review)
        code=getattr(target,'__wrapped__',target).__code__
        def profiler(frame,event,arg):
            if event=='call' and frame.f_code is code:
                entered.set()
                if not release.wait(15):raise RuntimeError('test parent pause expired')
        def run():
            sys.setprofile(profiler)
            try:results.append(('result',function()))
            except BaseException as e:results.append(('error',e))
            finally:sys.setprofile(None);finished.set()
        worker=threading.Thread(target=run);worker.start()
        try:
            self.assertTrue(entered.wait(15));yield results,release
        finally:
            release.set();worker.join(20);self.assertFalse(worker.is_alive());self.assertTrue(finished.is_set())

    def test_real043_core_prepare_append_replay_and_capabilities(self):
        before=self.base();a=self.create();caps=a.capabilities(BIND,self.intake)
        self.assertEqual(set(caps),{'prepare_allowed','append_allowed','review_input_id'});self.assertTrue(caps['append_allowed'])
        p=self.prepare(a);self.assertEqual(set(p),{'schema_version','kind','handle_id','append_request_id','expires_in_seconds','preview'})
        self.assertEqual(p['kind'],'intake_reference_preparation_handle');self.assertEqual(len(p['preview']),11)
        self.assertTrue(1<=p['expires_in_seconds']<=900);self.assertEqual(len(p['handle_id']),64)
        request=self.request(p);r=a.append(BIND,self.intake,request);self.assertEqual(r['binding_status'],'current_at_append')
        replay=a.append(BIND,self.intake,request);self.assertTrue(replay['replayed']);self.assertEqual(r['append_observation'],replay['append_observation'])
        self.assertEqual(self.counts(),(1,1,1));self.assertEqual(self.base(),before)
        a.close();self.assertIs(self.store.__enter__(),self.store)

    def test_factory_input_id_canonical_and_detached(self):
        source=self.supplied();a=self.create(review_inputs=(source,));cap=a.capabilities(BIND,self.intake)
        digest=lambda x:hashlib.sha256(canonical(x).encode('utf-8')).hexdigest()
        expected=digest({'schema_version':1,'intake_id':self.intake,'case_context_sha256':digest(self.context),
            'validated_response_sha256':digest(self.response),'producer_name':source['producer_name']})
        self.assertEqual(cap['review_input_id'],expected)
        source['case_context']['query']['model']='PRIVATE';source['validated_response']['references'].clear()
        p=self.prepare(a);self.assertEqual(p['preview']['selection']['accepted_reference_count'],1)
        self.assertNotIn('PRIVATE',canonical(p));self.assertNotIn('MODEL-A',repr(a))

    def test_unconfigured_does_not_import_parent_or_create_store(self):
        a=host.create_reference_review_actions(None,None,host_epoch=EPOCH,scope_epoch=SCOPE,runtime_lock=self.lock)
        self.addCleanup(a.close);self.assertEqual(a.capabilities(None,self.intake),{'prepare_allowed':False,'append_allowed':False,'review_input_id':None})
        self.error('unconfigured',lambda:a.prepare(BIND,self.intake,{'schema_version':1,'review_input_id':'d'*64,'replace_handle_id':None}),503)
        self.assertEqual(self.namespace(),[])

    def test_read_append_scope_intersection_and_no_authority_in_request(self):
        a=self.create(append_scope=());p=self.prepare(a);self.assertFalse(a.capabilities(BIND,self.intake)['append_allowed'])
        self.error('access_denied',lambda:a.append(BIND,self.intake,self.request(p)),403)
        b=self.create(read_scope=());self.assertFalse(b.capabilities(BIND,self.intake)['prepare_allowed'])
        self.error('access_denied',lambda:self.prepare(b),403)
        c=self.create();request={'schema_version':1,'review_input_id':c.capabilities(BIND,self.intake)['review_input_id'],'replace_handle_id':None,'allow_append':True}
        self.error('invalid_request',lambda:c.prepare(BIND,self.intake,request),400)

    def test_exact_config_types_scopes_epochs_and_rlock(self):
        for changes in [{'runtime_lock':threading.Lock()},{'host_epoch':'X'*64},{'scope_epoch':False},{'read_scope':['workspace']},
                        {'append_scope':('DUP','DUP')},{'review_inputs':[self.supplied()]},{'review_inputs':(self.supplied(),self.supplied())}]:
            with self.subTest(changes=list(changes)):self.error('invalid_request',lambda:self.create(**changes),400)

    def test_startup_input_bounds_and_normal100(self):
        value=self.supplied();value['case_context']={'oversize':'x'*(8*1024*1024)}
        self.error('input_limit',lambda:self.create(review_inputs=(value,)),413)
        values=tuple({**self.supplied(),'intake_id':'I'+str(i)} for i in range(100));a=self.create(review_inputs=values)
        self.assertIsNotNone(a.capabilities(BIND,'I99')['review_input_id'])
        self.error('input_limit',lambda:self.create(review_inputs=values+({**self.supplied(),'intake_id':'I100'},)),413)

    def test_binding_exact_epochs_and_cross_session_handle(self):
        a=self.create();p=self.prepare(a);bad={**BIND,'session_id':'d'*64}
        self.error('access_denied',lambda:a.append(bad,self.intake,self.request(p)),403)
        self.error('access_denied',lambda:a.capabilities({**BIND,'scope_epoch':'e'*64},self.intake),403)
        self.error('invalid_request',lambda:a.capabilities({**BIND,'extra':'PRIVATE'},self.intake),400)

    def test_request_fields_expected_and_path_are_frozen(self):
        a=self.create();p=self.prepare(a);req=self.request(p)
        for key,value in [('request_id','OTHER'),('intake_id','OTHER'),('preparation_id','d'*64),('expected_snapshot_id','e'*64),('expected_head_record_id','f'*64)]:
            changed=dict(req);changed[key]=value;self.error('request_conflict',lambda:a.append(BIND,self.intake,changed),409)
        for key,value in [('schema_version',True),('handle_id','bad'),('permission',True)]:
            changed=dict(req);changed[key]=value;self.error('invalid_request',lambda:a.append(BIND,self.intake,changed),400)
        self.assertEqual(self.namespace(),[])

    def test_host3_session2_caps_and_expiry(self):
        a=self.create();now=[100.0]
        with patch.object(host,'_clock',side_effect=lambda:now[0]):
            p=self.prepare(a);self.prepare(a)
            self.error('unavailable',lambda:self.prepare(a),503)
            other={**BIND,'session_id':'d'*64};self.prepare(a,other)
            self.error('unavailable',lambda:self.prepare(a,{**BIND,'session_id':'e'*64}),503)
            now[0]=1000.0
            self.error('prepared_unavailable',lambda:a.append(BIND,self.intake,self.request(p)),410)
            self.assertEqual(self.prepare(a)['expires_in_seconds'],900)

    def test_replacement_success_old_handle_gone_and_failed_parent_restores_old(self):
        a=self.create();p=self.prepare(a);new=self.prepare(a,replace=p['handle_id'])
        self.error('prepared_unavailable',lambda:a.append(BIND,self.intake,self.request(p)),410)
        target=self.store.root/'blobs'/hashlib.sha256((self.inbox/'one/request.pdf').read_bytes()).hexdigest()
        raw=target.read_bytes();target.write_bytes(b'CORRUPT-SYNTHETIC')
        try:
            self.error('source_integrity_invalid',lambda:self.prepare(a,replace=new['handle_id']),prefix='intake_reference_state_')
        finally:target.write_bytes(raw)
        self.assertEqual(a.append(BIND,self.intake,self.request(new))['binding_status'],'current_at_append')

    def test_successful_replacement_uses_slot_credit_at_cap(self):
        a=self.create();p=self.prepare(a);self.prepare(a);self.prepare(a,{**BIND,'session_id':'d'*64})
        new=self.prepare(a,replace=p['handle_id']);self.assertNotEqual(p['handle_id'],new['handle_id'])
        self.error('unavailable',lambda:self.prepare(a),503)

    def test_source_change_historical_and_head_conflict_are_real_parent_results(self):
        a=self.create();p=self.prepare(a);q=self.prepare(a)
        first=a.append(BIND,self.intake,self.request(p));second=a.append(BIND,self.intake,self.request(q))
        self.assertEqual(first['binding_status'],'current_at_append');self.assertEqual(second['binding_status'],'head_conflict')
        respond(self.store,'ANSWER046','answer',intake_id=self.intake,answers={'purpose':'changed'})
        # A fresh actions object is an independent trusted core owner, not another HTTP/session provider.
        b=self.create();old=self.prepare(b);respond(self.store,'ANSWER046B','answer',intake_id=self.intake,answers={'purpose':'changed-again'})
        self.assertEqual(b.append(BIND,self.intake,self.request(old))['binding_status'],'historical_provided')

    def test_deferred_and_unbound_inputs_preserve_normal_semantics(self):
        respond(self.store,'DEFER046','defer',intake_id=self.intake);a=self.create();p=self.prepare(a)
        self.assertFalse(p['preview']['preparation_ready']);self.assertIn('intake_deferred',p['preview']['reason_codes'])
        self.assertEqual(a.append(BIND,self.intake,self.request(p))['binding_status'],'current_at_append')
        source=self.supplied();source['case_context']=deepcopy(source['case_context']);source['case_context']['query']['model']='OTHER'
        b=self.create(review_inputs=(source,));q=self.prepare(b);self.assertEqual(q['preview']['review_status'],'insufficient_evidence')
        self.assertEqual(b.append(BIND,self.intake,self.request(q))['binding_status'],'reference_unbound')

    def test_discard_session_clears_only_own_handles_and_borrowed_store_open(self):
        a=self.create();p=self.prepare(a);other={**BIND,'session_id':'d'*64};q=self.prepare(a,other)
        a.discard_session(BIND);self.error('prepared_unavailable',lambda:a.append(BIND,self.intake,self.request(p)),410)
        self.assertTrue(a.append(other,self.intake,self.request(q))['stored']);self.assertIs(self.store.__enter__(),self.store)

    def test_parent_io_releases_global_rlock_and_active_close_is_retryable(self):
        a=self.create()
        with self.paused_parent(lambda:self.prepare(a)) as (results,release):
            self.assertTrue(self.lock.acquire(timeout=1));self.lock.release()
            self.error('unavailable',a.close,503)
            self.assertFalse(a.capabilities(BIND,self.intake)['prepare_allowed'])
            self.assertIs(self.store.__enter__(),self.store);release.set()
        self.assertEqual(results[0][0],'error');self.assertEqual(results[0][1].code,'intake_reference_review_host_unavailable')
        self.assertIsNone(a.close());self.assertIsNone(a.close());self.assertIs(self.store.__enter__(),self.store)

    def test_prepare_expiry_while_real_parent_paused_never_publishes(self):
        a=self.create();now=[100.0]
        with patch.object(host,'_clock',side_effect=lambda:now[0]):
            with self.paused_parent(lambda:self.prepare(a)) as (results,release):now[0]=1000.0;release.set()
        self.assertEqual(results[0][0],'error');self.assertEqual(results[0][1].code,'intake_reference_review_host_prepared_unavailable')

    def test_discard_during_prepare_retires_after_finally(self):
        a=self.create()
        with self.paused_parent(lambda:self.prepare(a)) as (results,release):a.discard_session(BIND);release.set()
        self.assertEqual(results[0][0],'error');self.assertEqual(results[0][1].status,410)

    def test_error_contract_inside_outer_exception_context(self):
        a=self.create()
        try:raise RuntimeError('PRIVATE outer')
        except RuntimeError:self.error('prepared_unavailable',lambda:a.append(BIND,self.intake,{'schema_version':1,'handle_id':'f'*64,'intake_id':self.intake,
            'request_id':'R','preparation_id':'e'*64,'expected_snapshot_id':'d'*64,'expected_head_record_id':None}),410)

    def test_real_sqlite_authorizer_failure_keeps_uncertain_original_for_retry(self):
        a=self.create();p=self.prepare(a);request=self.request(p);connections=[];denied=[]
        ledger_path=str(ROOT/'labflow/intake_reference_ledger.py').casefold()
        def authorize(action,table,column,database,trigger):
            if action==sqlite3.SQLITE_INSERT and table=='intake_reference_records':
                denied.append(table);return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        def trace(frame,event,arg):
            if event=='line' and frame.f_code.co_filename.casefold()==ledger_path:
                con=frame.f_locals.get('con')
                if type(con) is sqlite3.Connection and all(con is not old for old in connections):
                    con.set_authorizer(authorize);connections.append(con)
            return trace
        previous=sys.gettrace();sys.settrace(trace)
        try:self.error('storage_error',lambda:a.append(BIND,self.intake,request),prefix='intake_reference_ledger_')
        finally:sys.settrace(previous)
        self.assertEqual(denied,['intake_reference_records']);self.assertEqual(self.namespace(),[])
        self.error('request_conflict',lambda:self.prepare(a,replace=p['handle_id']),409)
        retry=a.append(BIND,self.intake,request);self.assertTrue(retry['stored']);self.assertFalse(retry['replayed'])
        replay=a.append(BIND,self.intake,request);self.assertTrue(replay['replayed']);self.assertEqual(self.counts(),(1,1,1))
        self.assertEqual(retry['append_observation'],replay['append_observation'])

    def test_same_handle_busy_and_close_during_actual_append(self):
        a=self.create();p=self.prepare(a);request=self.request(p)
        with self.paused_parent(lambda:a.append(BIND,self.intake,request),append=True) as (results,release):
            self.assertTrue(self.lock.acquire(timeout=1));self.lock.release()
            self.error('unavailable',lambda:a.append(BIND,self.intake,request),429)
            self.error('request_conflict',lambda:self.prepare(a,replace=p['handle_id']),409)
            self.error('unavailable',a.close,503);self.assertIs(self.store.__enter__(),self.store);release.set()
        self.assertEqual(results[0][0],'result');self.assertTrue(results[0][1]['stored']);self.assertEqual(self.counts(),(1,1,1))
        self.assertIsNone(a.close());self.assertFalse(a.capabilities(BIND,self.intake)['append_allowed'])

    def test_replacement_is_busy_until_atomic_publication(self):
        a=self.create();p=self.prepare(a)
        with self.paused_parent(lambda:self.prepare(a,replace=p['handle_id'])) as (results,release):
            self.error('unavailable',lambda:a.append(BIND,self.intake,self.request(p)),429)
            self.error('unavailable',lambda:self.prepare(a,replace=p['handle_id']),429);release.set()
        self.assertEqual(results[0][0],'result')
        self.error('prepared_unavailable',lambda:a.append(BIND,self.intake,self.request(p)),410)
        self.assertTrue(a.append(BIND,self.intake,self.request(results[0][1]))['stored'])

    def test_replacement_failed_after_old_expiry_does_not_restore_it(self):
        a=self.create();now=[100.0]
        with patch.object(host,'_clock',side_effect=lambda:now[0]):
            p=self.prepare(a);now[0]=999.0
            target=self.store.blob_path(self.job['documents'][0]['sha256']);raw=target.read_bytes();target.write_bytes(b'BROKEN-SYNTHETIC')
            try:
                with self.paused_parent(lambda:self.prepare(a,replace=p['handle_id'])) as (results,release):now[0]=1000.0;release.set()
            finally:target.write_bytes(raw)
            self.assertEqual(results[0][0],'error');self.assertEqual(results[0][1].code,'intake_reference_state_source_integrity_invalid')
            self.error('prepared_unavailable',lambda:a.append(BIND,self.intake,self.request(p)),410)
            self.assertEqual(self.prepare(a)['expires_in_seconds'],900)

    def test_replacement_success_after_old_deadline_cannot_publish(self):
        a=self.create();now=[100.0]
        with patch.object(host,'_clock',side_effect=lambda:now[0]):
            p=self.prepare(a);now[0]=999.0
            with self.paused_parent(lambda:self.prepare(a,replace=p['handle_id'])) as (results,release):now[0]=1000.0;release.set()
            self.assertEqual(results[0][0],'error');self.assertEqual(results[0][1].status,410)
            self.error('prepared_unavailable',lambda:a.append(BIND,self.intake,self.request(p)),410)

    def test_replacement_failure_after_session_discard_preserves_retirement(self):
        a=self.create();p=self.prepare(a);target=self.store.blob_path(self.job['documents'][0]['sha256'])
        raw=target.read_bytes();target.write_bytes(b'BROKEN-SYNTHETIC')
        try:
            with self.paused_parent(lambda:self.prepare(a,replace=p['handle_id'])) as (results,release):a.discard_session(BIND);release.set()
        finally:target.write_bytes(raw)
        self.assertEqual(results[0][0],'error')
        self.error('prepared_unavailable',lambda:a.append(BIND,self.intake,self.request(p)),410)
        # The core owns no permanent revoked-session registry; the real host owns that table.
        self.assertEqual(self.prepare(a)['kind'],'intake_reference_preparation_handle')

    def test_genuine_provenance_inconsistency_is_preparation_unverified(self):
        with self.store.connection() as con:con.execute('UPDATE blobs SET synthetic=0 WHERE sha256=?',(self.job['documents'][0]['sha256'],))
        a=self.create();p=self.prepare(a);self.assertIn('source_provenance_unconfirmed',p['preview']['reason_codes'])
        self.assertEqual(p['preview']['source_modes']['intake_provenance_status'],'unconfirmed')
        registration=a.append(BIND,self.intake,self.request(p));self.assertEqual(registration['binding_status'],'preparation_unverified')
        self.assertFalse(registration['append_observation']['head_advanced']);self.assertEqual(self.counts(),(1,1,0))

    def test_strict_plain_input_unicode_numbers_depth_and_request_byte_budget(self):
        class Evil(dict):
            def items(self):raise AssertionError('user callback executed')
        for value in [Evil(),{'x':float('nan')},{'x':'\ud800'},{'x':object()}]:
            source={**self.supplied(),'case_context':value};self.error('invalid_request',lambda:self.create(review_inputs=(source,)),400)
        nested=[];cursor=nested
        for _ in range(26):child=[];cursor.append(child);cursor=child
        self.error('input_limit',lambda:self.create(review_inputs=({**self.supplied(),'case_context':nested},)),413)
        a=self.create();p=self.prepare(a);request=self.request(p);request['padding']='\x00'*3000
        self.error('input_limit',lambda:a.append(BIND,self.intake,request),413)
        self.assertEqual(self.namespace(),[])

    def test_startup_whole_list32mib_and_individual_node_budgets(self):
        source=deepcopy(self.supplied());source['case_context']['startup_budget_probe']='x'*(7*1024*1024)
        values=tuple({**source,'intake_id':'AGG'+str(i)} for i in range(5))
        self.error('input_limit',lambda:self.create(review_inputs=values),413)
        # Structural startup admission only; these additional fields are not a025 semantic receipt.
        source['case_context']['startup_budget_probe']=[0]*11000
        values=tuple({**source,'intake_id':'NODES'+str(i)} for i in range(100))
        a=self.create(review_inputs=values);self.assertTrue(a.capabilities(BIND,'NODES99')['prepare_allowed'])
        self.assertEqual(self.namespace(),[])

    def test_public_dto_guards_reject_private_fields_and_authority_escalation(self):
        a=self.create();p=self.prepare(a);registration=a.append(BIND,self.intake,self.request(p))
        for mutate in [lambda v:v.update(private='MODEL-A'),lambda v:v['verification'].update(model_execution_verified=True),
                       lambda v:v['selection'].update(accepted_reference_count=257),lambda v:v['observation'].update(snapshot_id='bad')]:
            value=deepcopy(p['preview']);mutate(value);self.error('unavailable',lambda:host._preview(value,self.intake),503)
        for mutate in [lambda v:v.update(private='MODEL-A'),lambda v:v.update(seq=True),
                       lambda v:v['verification'].update(operational_authority_granted=True),lambda v:v['append_observation'].update(head_after_record_id=None)]:
            value=deepcopy(registration);mutate(value);self.error('unavailable',lambda:host._registration(value,self.request(p)),503)
        p['preview']['verification']['model_execution_verified']=True
        # Caller-owned DTO mutations never mutate the stored private preparation/request.
        self.assertTrue(a.append(BIND,self.intake,self.request(p))['replayed'])

    def test_public043_liveness_and_field_identity_fail_before_parent(self):
        a=self.create();p=self.prepare(a);original=self.store.root;self.store.root=self.root/'OTHER'
        try:self.error('input_changed',lambda:a.append(BIND,self.intake,self.request(p)),prefix='store_open_')
        finally:self.store.root=original
        self.assertEqual(self.namespace(),[])
        self.store.close();self.error('closed',lambda:a.append(BIND,self.intake,self.request(p)),prefix='store_open_')

    def test_fresh_process_unconfigured_never_imports042(self):
        script="""import json,sys,threading
from labflow.intake_reference_review_host import create_reference_review_actions
a=create_reference_review_actions(None,None,host_epoch='a'*64,scope_epoch='b'*64,runtime_lock=threading.RLock())
print(json.dumps({'imported042':'labflow.intake_reference_review' in sys.modules,'capabilities':a.capabilities(None,'INTAKE')}))
a.close()
"""
        result=subprocess.run([sys.executable,'-X','utf8','-B','-c',script],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),{'imported042':False,'capabilities':{'prepare_allowed':False,'append_allowed':False,'review_input_id':None}})

    def test_missing_input_scope_and_request_input_mismatch_are_distinct(self):
        a=self.create(read_scope=(self.intake,),append_scope=(self.intake,));p=self.prepare(a)
        self.assertEqual(a.capabilities(BIND,'OUTSIDE'),{'prepare_allowed':False,'append_allowed':False,'review_input_id':None})
        self.error('access_denied',lambda:a.prepare(BIND,'OUTSIDE',{}),403)
        missing=self.create();self.error('review_input_unavailable',lambda:missing.prepare(BIND,'MISSING',{}),503)
        self.error('request_conflict',lambda:a.prepare(BIND,self.intake,{'schema_version':1,'review_input_id':'f'*64,'replace_handle_id':None}),409)
        self.error('access_denied',lambda:self.prepare(a,{**BIND,'session_id':'d'*64},p['handle_id']),403)

    def test_real_paired_snapshot_change_keeps_parent_error_without_retry(self):
        a=self.create()
        with self.paused_parent(lambda:self.prepare(a),parent_function=fixture.ledger.current_reference) as (results,release):
            respond(self.store,'BETWEEN-C1-C2','answer',intake_id=self.intake,answers={'purpose':'changed-between-reads'});release.set()
        self.assertEqual(results[0][0],'error');self.assertEqual(results[0][1].code,'intake_reference_review_review_state_changed')
        self.assertEqual(self.namespace(),[])
        self.assertEqual(self.prepare(a)['kind'],'intake_reference_preparation_handle')

    def test_expiry_after_append_dispatch_does_not_claim_rollback(self):
        a=self.create();now=[100.0]
        with patch.object(host,'_clock',side_effect=lambda:now[0]):
            p=self.prepare(a);request=self.request(p)
            with self.paused_parent(lambda:a.append(BIND,self.intake,request),append=True) as (results,release):now[0]=1000.0;release.set()
            self.assertEqual(results[0][0],'result');self.assertTrue(results[0][1]['stored']);self.assertEqual(self.counts(),(1,1,1))
            self.error('prepared_unavailable',lambda:a.append(BIND,self.intake,request),410)

    def test_maximum16_cases256_references_and_producer150_use_genuine025(self):
        packet,sources,_=fixture.report_fixture();original=packet['cases'][0]
        while len(original['claims'])<16:
            claim=deepcopy(original['claims'][0]);claim['claim_id']='EXTRA-'+str(len(original['claims']));original['claims'].append(claim)
        packet['corpus_id']='C'*128;packet['cases']=[]
        for i in range(16):
            case=deepcopy(original);case['case_id']='C'*126+f'{i:02}';packet['cases'].append(case)
        self.catalog=fixture.FccReportCaseCatalog(packet,sources)
        self.context=fixture.context_for(self.catalog,ids=[c['case_id'] for c in packet['cases']]);refs=[]
        for case in self.context['cases']:
            for claim in case['claims']:
                if not claim['evidence']:continue
                evidence=claim['evidence'][0]
                refs.append({'case_id':case['case_id'],'claim_id':claim['claim_id'],**{key:evidence[key] for key in
                    ('evidence_id','document_id','source_sha256','file_page','text_sha256','line_start','line_end')}})
        wire=fixture.response_wire(self.context,refs=refs[:256]);wire['producer']['name']='P'*150
        self.response=fixture.decode_case_review_response(json.dumps(wire),self.context,producer_name='P'*150)
        a=self.create();p=self.prepare(a);self.assertEqual(len(p['preview']['selection']['requested_case_ids']),16)
        self.assertEqual(p['preview']['selection']['accepted_reference_count'],256)
        registration=a.append(BIND,self.intake,self.request(p));self.assertEqual(registration['binding_status'],'current_at_append')
        self.assertEqual(self.counts(),(1,1,1))

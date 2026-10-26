"""Disposable native source tests; no installed CLI or provider process."""
import copy
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import sqlite3
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from test_codex_conducted_workflow_registration import RegistrationTests,C,H
from test_codex_registered_workflow_continuation import ContinuationTests,api
from labflow import codex_registered_conducted_workflow_host as host


class ExpiryReauthorizationTests(RegistrationTests):
    fixture=ContinuationTests.fixture
    attempt=ContinuationTests.attempt

    def setUp(self):
        super().setUp()
        self.make_completed_inputs()
        self.enterContext(patch('subprocess.Popen',side_effect=AssertionError('MODEL_VENDOR_FORBIDDEN')))

    def expired(self):
        self.fixture()
        original=(datetime.now(timezone.utc)-timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
        con=sqlite3.connect(self.journal)
        try:
            permit=json.loads(con.execute("SELECT payload FROM codex_conducted_workflow_history WHERE kind='permit'").fetchone()[0])
            permit['expires_at']=original
            con.execute("UPDATE codex_conducted_workflow_history SET payload=? WHERE kind='permit'",(C(permit).decode(),))
            con.commit()
        finally:con.close()
        self.manual['expires_at']=None
        self.put(self.operator/api._RECORD,self.manual)
        return original

    def source(self,original):
        pin=lambda p:dict(bytes=len(p.read_bytes()),sha256=H(p.read_bytes()))
        record=dict(schema_version=1,kind='codex_root_same_case_calendar_reauthorization',
            authority_source=self.authority['authority_source'],
            direct_user_expiry_reference=dict(kind='direct_human_instructions_to_this_root_thread',
                reply_id='e123f778ee58431abbcd9c5d3b11952b',
                instruction_literal='2시간유효기간이 왜필요해? 우리 목적을 위해서 전부다 진행해',
                action='continue_same_case_remaining_budget_without_calendar_expiry',
                calendar_expiry_removed_by_direct_user_instruction=True,
                authority_is_not_inferred_from_uploaded_documents_or_model_output=True),
            interpretation='root_interpretation_of_direct_user_instruction_calendar_only',
            original_operator_source=pin(self.operator/'root-delegation-v1.json'),
            original_publication=pin(self.operator/'preparation-complete-v1.json'),
            manual_record=pin(self.operator/api._RECORD),original=copy.deepcopy(self.manual['original']),
            case=copy.deepcopy(self.manual['case']),scope=copy.deepcopy(self.manual['scope']),
            current_schema_sha256=self.manual['current_schema_sha256'],original_expires_at=original,
            remaining_model_processes=7,calendar_expiry_removed_by_direct_user_instruction=True)
        self.put(self.operator/'root-expiry-reauthorization-v1.json',record)
        return record

    def test_null_manual_without_native_source_cannot_claim(self):
        self.expired()
        with patch.object(host,'_execute',side_effect=AssertionError('EXECUTION_FORBIDDEN')) as execute:
            result=self.attempt()
        self.assertEqual(result['status'],'not_run',result)
        self.assertEqual(result['phase'],'calendar_authority',result)
        self.assertEqual(execute.call_count,0)
        self.assertFalse((self.evidence/api._CLAIM).exists())

    def test_expired_finite_manual_without_source_still_denied(self):
        self.expired()
        self.manual['expires_at']=(datetime.now(timezone.utc)+timedelta(minutes=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
        self.put(self.operator/api._RECORD,self.manual)
        with patch.object(host,'_execute',side_effect=AssertionError('EXECUTION_FORBIDDEN')) as execute:
            result=self.attempt()
        self.assertEqual(result['status'],'not_run',result)
        self.assertEqual(result['phase'],'calendar_authority',result)
        self.assertEqual(execute.call_count,0)
        self.assertFalse((self.evidence/api._CLAIM).exists())

    def test_exact_direct_source_allows_one_calendarless_same_case_entry(self):
        original=self.expired();record=self.source(original)
        source_raw=(self.operator/'root-expiry-reauthorization-v1.json').read_bytes()
        expected=dict(bytes=len(source_raw),sha256=H(source_raw))
        with patch.object(host,'_execute',side_effect=RuntimeError('DELlBERATE_ENTRY_STOP')) as execute:
            result=self.attempt()
        self.assertEqual(execute.call_count,1,result)
        self.assertEqual(result['status'],'unknown',result)
        self.assertEqual(result['calendar_reauthorization'],expected)
        self.assertEqual(result['verification']['authority_scope'],'fixed_native_root_same_case_calendar_reauthorization')
        self.assertEqual(execute.call_args.kwargs['model_process_limit'],7)
        self.assertLess(execute.call_args.kwargs['wall_seconds_limit'],168)
        claim=json.loads((self.evidence/api._CLAIM).read_bytes())
        finished=json.loads((self.evidence/api._NAMESPACE/'finished-v1.json').read_bytes())
        self.assertEqual(claim['calendar_reauthorization'],expected)
        self.assertEqual(finished['calendar_reauthorization'],expected)
        self.assertEqual(self.attempt()['status'],'not_run')
        self.assertEqual(record['original_expires_at'],original)

    def test_direct_source_drift_or_ambiguous_words_cannot_claim(self):
        original=self.expired();base=self.source(original)
        mutations=[('reply_id','wrong'),('instruction_literal','do anything'),('action','retry_permit'),
            ('calendar_expiry_removed_by_direct_user_instruction',False)]
        for field,value in mutations:
            changed=copy.deepcopy(base)
            changed['direct_user_expiry_reference'][field]=value
            self.put(self.operator/'root-expiry-reauthorization-v1.json',changed)
            with patch.object(host,'_execute',side_effect=AssertionError('EXECUTION_FORBIDDEN')) as execute:
                result=self.attempt()
            self.assertEqual(result['status'],'not_run',(field,result))
            self.assertEqual(result['phase'],'calendar_authority',result)
            self.assertEqual(execute.call_count,0)
            self.assertFalse((self.evidence/api._CLAIM).exists())

    def test_source_original_case_schema_or_manual_pin_drift_cannot_claim(self):
        original=self.expired();base=self.source(original)
        changes=[dict(original_expires_at='2000-01-01T00:00:00Z'),dict(remaining_model_processes=8),
            dict(current_schema_sha256='f'*64),dict(case=dict(base['case'],scenario_id='OTHER')),
            dict(manual_record=dict(base['manual_record'],sha256='f'*64)),
            dict(original=dict(base['original'],finished_sha256='f'*64))]
        for change in changes:
            changed=copy.deepcopy(base);changed.update(change)
            self.put(self.operator/'root-expiry-reauthorization-v1.json',changed)
            with patch.object(host,'_execute',side_effect=AssertionError('EXECUTION_FORBIDDEN')) as execute:
                result=self.attempt()
            self.assertEqual(result['status'],'not_run',(change,result))
            self.assertEqual(result['phase'],'calendar_authority',result)
            self.assertEqual(execute.call_count,0)
            self.assertFalse((self.evidence/api._CLAIM).exists())


NAMES=['test_null_manual_without_native_source_cannot_claim',
       'test_expired_finite_manual_without_source_still_denied',
       'test_exact_direct_source_allows_one_calendarless_same_case_entry',
       'test_direct_source_drift_or_ambiguous_words_cannot_claim',
       'test_source_original_case_schema_or_manual_pin_drift_cannot_claim']

def load_tests(loader,tests,pattern):
    return unittest.TestSuite(ExpiryReauthorizationTests(name) for name in NAMES)

if __name__=='__main__':unittest.main()

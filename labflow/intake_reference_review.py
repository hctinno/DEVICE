"""Private paired preparation, explicit038 publication and sanitized durable views."""
from datetime import datetime,timedelta
from functools import wraps
import hashlib
import json
import math
from pathlib import Path
import re

from .store import Store
from .fcc_report_cases import FccReportCaseCatalog
from .fcc_case_review import FccCaseReviewError
from .intake_reference_snapshot import read_intake_reference_snapshot,IntakeReferenceStateError,REASON_CODES
from .intake_case_references import build_intake_case_reference_receipt,IntakeCaseReferencesError
from .intake_reference_ledger import record_intake_reference,current_reference,reference_history,IntakeReferenceLedgerError


_MIB=1024*1024
_ID=re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,149}\Z',re.ASCII)
_SHA=re.compile(r'[0-9a-f]{64}\Z',re.ASCII)
_MAXINT=2**63-1
_TOKEN=object()
_CODES={'invalid_argument','store_invalid','access_denied','prepared_invalid','review_state_changed','parent_invalid','input_limit','unavailable'}
_PARENT_CODES={
    IntakeReferenceLedgerError:('intake_reference_ledger_',{'invalid_argument','store_invalid','intake_not_found','input_limit','parent_invalid','origin_invalid','schema_mismatch','request_conflict','integrity_invalid','storage_error'}),
    IntakeReferenceStateError:('intake_reference_state_',{'invalid_argument','store_invalid','transaction_required','intake_not_found','input_limit','source_integrity_invalid','projection_inconsistent','delegation_invalid','storage_error'}),
    IntakeCaseReferencesError:('intake_case_references_',{'catalog_invalid','snapshot_invalid','context_invalid','response_invalid','producer_invalid','source_error','limit_exceeded'}),
    FccCaseReviewError:('fcc_case_review_',{'catalog_invalid','query_invalid','selection_invalid','source_invalid','source_error','limit_exceeded','context_invalid','context_mismatch','producer_invalid','response_invalid','reference_invalid'})}
_PREP_REASONS={'analysis_not_ready','profile_changed','delegation_missing','intake_deferred','delegation_evidence_missing','required_questions_open','unread_documents','source_provenance_unconfirmed','preparation_not_ready'}
_CURRENT_REASONS=set(REASON_CODES)|{'current_capture_unavailable','no_reference_head','reference_snapshot_stale'}
_STATUS={'current_at_append','historical_provided','preparation_unverified','head_conflict','reference_unbound'}
_FACTS={'product_type','market','model'}
_FACT_STATUS={'explicit','inferred','uncertain','user_confirmed'}
_RECEIPT_REASONS={'snapshot_binding_incomplete','projection_hash_mismatch','case_context_mismatch','case_response_not_bound','intake_query_insufficient','selected_reference_outside_intake_scope'}
_MATCH_REASONS={'query_context_missing','no_reviewed_case','exact_model_case_missing','intake_product_unconfirmed','intake_market_unconfirmed','intake_market_not_fcc','intake_model_unconfirmed','intake_product_conflict','intake_model_conflict','intake_identity_unresolved','no_selected_cases'}
_CASE_REASONS={'case_detail_not_requested','related_model','intake_match_insufficient','response_insufficient_evidence','response_no_candidate','source_context_unbound','snapshot_unbound','not_selected_in_response'}
_RESPONSE_REASONS={'query_insufficient','no_selected_cases','no_reviewed_evidence','additional_evidence_required','no_reviewed_case'}
_PARENT_FALSE={'source_facts_reverified','result_projection_reverified','database_currentness_verified','operational_authority_granted','model_execution_verified','model_quality_verified','independent_evaluation_approved','training_executed','evaluation_executed','hardware_verified','physical_verified'}
_PARENT_TRUE_FIELDS={'snapshot_dto_validated','projection_hash_verified','snapshot_metadata_complete','catalog_context_matched','response_revalidated','intake_match_checked','reference_scope_checked'}
_CAPTURE_VERIFY={'database_snapshot_observed','retained_analysis_verified','live_projection_recomputed','preparation_bound','source_integrity_observed','operational_authority_granted','model_execution_verified','evaluation_executed'}
_CAPTURE_FALSE={'operational_authority_granted','model_execution_verified','evaluation_executed'}
_CORE={'intake_id','revision','revision_fingerprint','origin_job_id','analysis_context_id','result_sha256','synthetic'}
_SNAPSHOT={'schema_version','kind','snapshot_scope',*_CORE,'readiness_fingerprint','projection','projection_sha256'}
_RECEIPT={'schema_version','kind','receipt_id','execution_mode','status','reason_codes','intake_binding','case_binding','intake_match','reference_selection','case_states','evaluation','verification','limits'}
_APPEND={'expected_snapshot_id','captured_snapshot_id','head_before_record_id','head_after_record_id','head_advanced','preparation_ready','observed_at'}
_SUMMARY={'record_id','seq','request_id','revision','origin_job_id','reference_receipt_id','binding_status','expected_snapshot_id','append_observation','source_modes','created_at'}
_MODES={'intake_revision_synthetic','catalog_synthetic','intake_provenance_status'}
_CAPTURE_LIMITS={'result_json_bytes':8*_MIB,'analysis_context_bytes':4*_MIB,'raw_manifest_bytes':4*_MIB,'source_file_bytes':16*_MIB,'projection_json_bytes':8*_MIB,'state_category_json_bytes':8*_MIB,'max_questions':10000,'max_user_response_events':10000,'max_answers':10,'snapshot_json_bytes':9*_MIB,'capture_json_bytes':12*_MIB}
_RECEIPT_LIMITS={'max_snapshot_bytes':9*_MIB,'max_projection_bytes':8*_MIB,'max_context_bytes':8*_MIB,'max_response_bytes':320*1024,'max_output_bytes':2*_MIB,'max_snapshot_depth':20,'max_projection_depth':16,'max_context_depth':24,'max_response_depth':16,'max_output_depth':16,'max_nodes':500000,'max_cases':128,'max_requested_cases':16,'max_references':256,'max_facts':3,'max_questions':200}


class IntakeReferenceReviewError(ValueError):
    def __init__(self,code):
        suffix=code.removeprefix('intake_reference_review_') if type(code) is str else 'parent_invalid'
        self.code='intake_reference_review_'+(suffix if suffix in _CODES else 'parent_invalid')
        super().__init__(self.code)


def _fail(code='parent_invalid'):raise IntakeReferenceReviewError(code)


def _public(function):
    @wraps(function)
    def call(*args,**kwargs):
        factory=IntakeReferenceReviewError;code='parent_invalid'
        try:return function(*args,**kwargs)
        except IntakeReferenceReviewError as error:
            if type(error) is IntakeReferenceReviewError:code=getattr(error,'code','parent_invalid')
        except tuple(_PARENT_CODES) as error:
            contract=_PARENT_CODES.get(type(error))
            if contract is not None:
                prefix,suffixes=contract
                candidate=getattr(error,'code',None)
                if type(candidate) is str and candidate in {prefix+s for s in suffixes}:factory=type(error);code=candidate
        except Exception:pass
        raise factory(code) from None
    return call


def _encoded(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def _hash(value):return hashlib.sha256(_encoded(value)).hexdigest()


def _copy(value,limit,depth_limit=28,node_limit=1000000,code='parent_invalid',shared=None):
    size=nodes=0;shared=[0] if shared is None else shared
    def consume(amount):
        nonlocal size
        size+=amount
        if size>limit:_fail('input_limit')
    def count():
        nonlocal nodes
        nodes+=1;shared[0]+=1
        if nodes>node_limit or shared[0]>1000000:_fail('input_limit')
    def scalar(item):
        if type(item) is str and len(item)>limit-size:_fail('input_limit')
        try:consume(len(_encoded(item)))
        except (ValueError,UnicodeError,OverflowError):_fail(code)
        return item
    def walk(item,depth=0):
        count()
        if depth>depth_limit:_fail('input_limit')
        if type(item) is dict:
            consume(2);result={}
            for index,(key,child) in enumerate(item.items()):
                if type(key) is not str:_fail(code)
                count();scalar(key);consume(1+(1 if index else 0));result[key]=walk(child,depth+1)
            return result
        if type(item) is list:
            consume(2);result=[]
            for index,child in enumerate(item):
                if index:consume(1)
                result.append(walk(child,depth+1))
            return result
        if item is None or type(item) in (str,int,bool):return scalar(item)
        if type(item) is float and math.isfinite(item):return scalar(item)
        _fail(code)
    return walk(value)


def _keys(value,fields,code='parent_invalid'):
    if type(value) is not dict or set(value)!=set(fields):_fail(code)
def _bool(value,code='parent_invalid'):
    if type(value) is not bool:_fail(code)
def _id(value,code='parent_invalid',*,maximum=150,nullable=False):
    if value is None and nullable:return
    if type(value) is not str or not _ID.fullmatch(value) or len(value)>maximum:_fail(code)
def _sha(value,code='parent_invalid',*,nullable=False):
    if value is None and nullable:return
    if type(value) is not str or not _SHA.fullmatch(value):_fail(code)
def _int(value,code='parent_invalid',*,minimum=1,maximum=_MAXINT,nullable=False):
    if value is None and nullable:return
    if type(value) is not int or not minimum<=value<=maximum:_fail(code)
def _text(value,maximum=4000,code='parent_invalid'):
    if type(value) is not str or not value.strip() or len(value)>maximum:_fail(code)
def _choice(value,choices,*,nullable=False):
    if value is None and nullable:return
    if type(value) is not str or value not in choices:_fail()
def _list(value,maximum):
    if type(value) is not list or len(value)>maximum:_fail()
def _reasons(value,allowed,*,ordered=True):
    _list(value,len(allowed))
    for item in value:_choice(item,allowed)
    if len(value)!=len(set(value)) or ordered and value!=sorted(value):_fail()
def _ids(value,maximum=128,*,ordered=False):
    _list(value,maximum)
    for item in value:_id(item,maximum=128)
    if len(value)!=len(set(value)) or ordered and value!=sorted(value):_fail()
def _time(value):
    _text(value,128)
    try:parsed=datetime.fromisoformat(value)
    except ValueError:_fail()
    if parsed.tzinfo is None or parsed.utcoffset()!=timedelta(0):_fail()
def _schema(value,fields,kind):
    _keys(value,fields);_int(value['schema_version'],maximum=1)
    if value['kind']!=kind:_fail()
def _flags(value,fields,false=(),true=()):
    _keys(value,fields)
    for child in value.values():_bool(child)
    if any(value[key] is not False for key in false) or any(value[key] is not True for key in true):_fail()
def _fixed(value,expected):
    if _encoded(value)!=_encoded(expected):_fail()
def _gate(*flags):
    for flag in flags:_bool(flag,'invalid_argument')
    if not all(flags):_fail('access_denied')
def _store(store):
    if type(store) is not Store or not isinstance(getattr(store,'db',None),Path) or not isinstance(getattr(store,'root',None),Path):_fail('store_invalid')
def _identity(store):
    _store(store)
    try:
        path=store.db.resolve(strict=True)
        if not path.is_file():raise OSError()
        stat=path.stat();return str(path),stat.st_dev,stat.st_ino,str(store.root.resolve())
    except OSError:pass
    raise IntakeReferenceLedgerError('storage_error')


def _snapshot(snapshot):
    _schema(snapshot,_SNAPSHOT,'intake_case_reference_snapshot')
    if snapshot['snapshot_scope']!='caller_provided':_fail()
    for key in ['intake_id','origin_job_id']:_id(snapshot[key])
    _int(snapshot['revision']);_bool(snapshot['synthetic'])
    for key in ['revision_fingerprint','analysis_context_id','result_sha256','readiness_fingerprint','projection_sha256']:_sha(snapshot[key])
    projection=snapshot['projection'];_keys(projection,{'facts','questions'})
    _copy(projection,8*_MIB,16,50000)
    if type(projection['facts']) is not dict or set(projection['facts'])-_FACTS:_fail()
    for fact in projection['facts'].values():
        if type(fact) is not dict or set(fact)-{'value','status','event_id'} or not {'value','status'}<=set(fact):_fail()
        _text(fact['value']);_choice(fact['status'],_FACT_STATUS)
        if fact['status']=='user_confirmed' and 'event_id' not in fact:_fail()
        if 'event_id' in fact:
            if type(fact['event_id']) is int:_int(fact['event_id'])
            else:_id(fact['event_id'],maximum=128)
    _list(projection['questions'],200)
    for question in projection['questions']:_keys(question,{'key'});_text(question['key'],_MIB)
    if _hash(projection)!=snapshot['projection_sha256']:_fail()


def _capture(value,intake_id):
    value=_copy(value,12*_MIB)
    _schema(value,{'schema_version','kind','status','reason_codes','snapshot_id','snapshot','origin','state','delegation','profile','readiness','verification','limits'},'intake_reference_snapshot_capture')
    _choice(value['status'],{'observed','unavailable'});_reasons(value['reason_codes'],set(REASON_CODES))
    _keys(value['origin'],{'source_id','origin_job_id','result_sha256','analysis_context_id','raw_manifest_sha256'})
    _keys(value['state'],{'intake_status','delegated','deferred','projection_sha256','answers_sha256','questions_sha256'})
    _keys(value['delegation'],{'event_id','history_sha256','verified'})
    _keys(value['profile'],{'stored_profile_id','current_profile_id','matches'})
    readiness=value['readiness'];_keys(readiness,{'kind','ready','reason_codes','reference_state_fingerprint','delegation_event_id'})
    if readiness['kind']!='reference_preparation_v1':_fail()
    _bool(readiness['ready']);_fixed(value['limits'],_CAPTURE_LIMITS)
    if value['status']=='unavailable':
        if value['snapshot'] is not None or value['snapshot_id'] is not None or readiness['ready']:_fail()
        _reasons(readiness['reason_codes'],{'analysis_not_completed','legacy_analysis','no_pdf_context'})
        if len(readiness['reason_codes'])!=1 or readiness['reason_codes']!=value['reason_codes']:_fail()
        for key in ['origin','state','delegation']:
            if any(child is not None for child in value[key].values()):_fail()
        _sha(value['profile']['current_profile_id'])
        if value['profile']['stored_profile_id'] is not None or value['profile']['matches'] is not None:_fail()
        if readiness['reference_state_fingerprint'] is not None or readiness['delegation_event_id'] is not None:_fail()
        _flags(value['verification'],_CAPTURE_VERIFY,_CAPTURE_VERIFY-{'database_snapshot_observed'},{'database_snapshot_observed'})
        return value
    _reasons(readiness['reason_codes'],_PREP_REASONS)
    if readiness['ready'] is not (not readiness['reason_codes']) or value['reason_codes']!=readiness['reason_codes']:_fail()
    _flags(value['verification'],_CAPTURE_VERIFY,_CAPTURE_FALSE,_CAPTURE_VERIFY-_CAPTURE_FALSE)
    _snapshot(value['snapshot']);snapshot=value['snapshot']
    if snapshot['intake_id']!=intake_id or snapshot['readiness_fingerprint']!=readiness['reference_state_fingerprint']:_fail()
    for key in ['source_id','origin_job_id']:_id(value['origin'][key])
    for key in ['result_sha256','analysis_context_id','raw_manifest_sha256']:_sha(value['origin'][key])
    for key in ['origin_job_id','result_sha256','analysis_context_id']:
        if snapshot[key]!=value['origin'][key]:_fail()
    _text(value['state']['intake_status'],150)
    for key in ['delegated','deferred']:_bool(value['state'][key])
    for key in ['projection_sha256','answers_sha256','questions_sha256']:_sha(value['state'][key])
    _id(value['delegation']['event_id'],nullable=True);_sha(value['delegation']['history_sha256']);_bool(value['delegation']['verified'])
    _id(readiness['delegation_event_id'],nullable=True);_sha(readiness['reference_state_fingerprint'])
    profile=value['profile'];_sha(profile['stored_profile_id']);_sha(profile['current_profile_id']);_bool(profile['matches'])
    if profile['matches'] is not (profile['stored_profile_id']==profile['current_profile_id']):_fail()
    basis={key:value[key] for key in ['schema_version','kind','snapshot','origin','state','delegation','profile','readiness']}
    if value['snapshot_id']!=_hash(basis):_fail()
    return value


def _receipt(value):
    value=_copy(value,2*_MIB,16,500000)
    _schema(value,_RECEIPT,'intake_case_reference_receipt')
    if value['execution_mode']!='provided_snapshot_read_only':_fail()
    _choice(value['status'],{'bound','insufficient_evidence'});_reasons(value['reason_codes'],_RECEIPT_REASONS)
    _sha(value['receipt_id'])
    if _hash({key:child for key,child in value.items() if key!='receipt_id'})!=value['receipt_id']:_fail()
    _flags(value['verification'],_PARENT_FALSE|_PARENT_TRUE_FIELDS,_PARENT_FALSE)
    _fixed(value['evaluation'],{'status':'not_executed','score':None,'actual_model_score':None,'scored_fixture_checks':0,'actual_model_checks':0,'independent_assignment_status':'not_assessed'})
    _fixed(value['limits'],_RECEIPT_LIMITS)
    binding=value['intake_binding'];_keys(binding,{*_CORE,'readiness_fingerprint','projection_sha256','snapshot_sha256','missing_fields'})
    for key in ['intake_id','origin_job_id']:_id(binding[key],nullable=True)
    _int(binding['revision'],nullable=True)
    for key in ['revision_fingerprint','analysis_context_id','result_sha256','readiness_fingerprint']:_sha(binding[key],nullable=True)
    for key in ['projection_sha256','snapshot_sha256']:_sha(binding[key])
    if binding['synthetic'] is not None:_bool(binding['synthetic'])
    _reasons(binding['missing_fields'],_CORE)
    if binding['missing_fields']!=sorted(key for key in _CORE if binding[key] is None):_fail()
    cases=value['case_binding'];_keys(cases,{'provided_context_sha256','provided_response_sha256','context_id','corpus_id','source_binding','query_sha256','producer','catalog_synthetic','context_status','search_status'})
    for key in ['provided_context_sha256','provided_response_sha256']:_sha(cases[key])
    for key in ['context_id','query_sha256']:_sha(cases[key],nullable=True)
    _id(cases['corpus_id'],maximum=128,nullable=True)
    _keys(cases['producer'],{'kind','name'})
    if cases['producer']['kind']!='model':_fail()
    _id(cases['producer']['name'])
    if cases['catalog_synthetic'] is not None:_bool(cases['catalog_synthetic'])
    _choice(cases['context_status'],{'ready','no_candidates','insufficient_evidence','no_selected_cases'},nullable=True)
    _choice(cases['search_status'],{'candidates','no_match','insufficient_evidence'},nullable=True)
    source=cases['source_binding']
    if source is not None:
        _keys(source,{'summary_sha256','matches_sha256','case_sha256s'})
        for key in ['summary_sha256','matches_sha256']:_sha(source[key])
        _list(source['case_sha256s'],16)
        for row in source['case_sha256s']:_keys(row,{'case_id','sha256'});_id(row['case_id'],maximum=128);_sha(row['sha256'])
    match=value['intake_match'];_keys(match,{'status','reason_codes','matched_case_ids','admitted_case_ids','fact_statuses'})
    _choice(match['status'],{'candidates','no_match','insufficient_evidence','not_assessed'});_reasons(match['reason_codes'],_MATCH_REASONS)
    for key in ['matched_case_ids','admitted_case_ids']:_ids(match[key],ordered=True)
    _keys(match['fact_statuses'],_FACTS)
    for status in match['fact_statuses'].values():_choice(status,_FACT_STATUS,nullable=True)
    selection=value['reference_selection'];_keys(selection,{'status','source_response_status','source_reason_codes','accepted_references','reported_reference_count'})
    _choice(selection['status'],{'selected','no_candidate','unknown'})
    _choice(selection['source_response_status'],{'selected','no_candidate','insufficient_evidence'},nullable=True)
    _reasons(selection['source_reason_codes'],_RESPONSE_REASONS,ordered=False)
    _int(selection['reported_reference_count'],minimum=0,maximum=256,nullable=True)
    _list(selection['accepted_references'],256);seen=set()
    for ref in selection['accepted_references']:
        _keys(ref,{'case_id','claim_id','evidence_id','document_id','source_sha256','file_page','text_sha256','line_start','line_end'})
        for key in ['case_id','claim_id','document_id']:_id(ref[key],maximum=128)
        for key in ['evidence_id','source_sha256','text_sha256']:_sha(ref[key])
        for key in ['file_page','line_start','line_end']:_int(ref[key])
        identity=ref['case_id'],ref['claim_id'],ref['evidence_id']
        if identity in seen or ref['line_end']<ref['line_start']:_fail()
        seen.add(identity)
    if selection['status']=='selected':
        if value['status']!='bound' or not seen or selection['source_response_status']!='selected' or selection['reported_reference_count']!=len(seen):_fail()
    elif seen:_fail()
    if (value['status']=='bound') is not (not value['reason_codes']):_fail()
    _list(value['case_states'],128)
    for case in value['case_states']:
        _keys(case,{'case_id','context_inclusion','context_exclusion_reason','context_model_relation','intake_model_relation','response_membership','selection_status','reason_codes'})
        _id(case['case_id'],maximum=128);_choice(case['context_inclusion'],{'detailed','preview_only'})
        _choice(case['context_exclusion_reason'],{'not_selected','related_model','query_insufficient'},nullable=True)
        for key in ['context_model_relation','intake_model_relation']:_choice(case[key],{'exact_model','related_family','unspecified'},nullable=True)
        _choice(case['response_membership'],{'referenced','not_referenced','not_assessed'})
        _choice(case['selection_status'],{'selected','not_selected_in_response','outside_intake_scope','unknown'});_reasons(case['reason_codes'],_CASE_REASONS)
    return value


def _append_observation(value,status,record_id):
    _keys(value,_APPEND)
    _sha(value['expected_snapshot_id']);_sha(value['captured_snapshot_id'],nullable=True)
    for key in ['head_before_record_id','head_after_record_id']:_sha(value[key],nullable=True)
    _bool(value['head_advanced']);_bool(value['preparation_ready']);_time(value['observed_at'])
    if value['head_advanced'] is not (status=='current_at_append'):_fail()
    if value['head_advanced']:
        if value['head_after_record_id']!=record_id or value['captured_snapshot_id']!=value['expected_snapshot_id']:_fail()
    elif value['head_after_record_id']!=value['head_before_record_id']:_fail()
    return {key:value[key] for key in sorted(_APPEND)}


def _summary(value):
    _keys(value,_SUMMARY)
    for key in ['record_id','reference_receipt_id','expected_snapshot_id']:_sha(value[key])
    for key in ['request_id','origin_job_id']:_id(value[key])
    for key in ['seq','revision']:_int(value[key])
    _choice(value['binding_status'],_STATUS);_time(value['created_at'])
    append=_append_observation(value['append_observation'],value['binding_status'],value['record_id'])
    if append['expected_snapshot_id']!=value['expected_snapshot_id'] or append['observed_at']!=value['created_at']:_fail()
    modes=value['source_modes'];_keys(modes,_MODES);_bool(modes['intake_revision_synthetic'])
    if modes['catalog_synthetic'] is not None:_bool(modes['catalog_synthetic'])
    _choice(modes['intake_provenance_status'],{'confirmed','unconfirmed','not_assessed'})
    result={key:value[key] for key in sorted(_SUMMARY-{'append_observation','source_modes'})}
    result.update(append_observation=append,source_modes={key:modes[key] for key in sorted(_MODES)})
    return result


def _registration(value,request_id):
    value=_copy(value,2*_MIB)
    fields={'schema_version','kind','request_id','record_id','seq','stored','replayed','binding_status','append_observation','verification'}
    _schema(value,fields,'intake_reference_registration');_id(value['request_id']);_sha(value['record_id']);_int(value['seq'])
    if value['request_id']!=request_id or value['stored'] is not True:_fail()
    _bool(value['replayed']);_choice(value['binding_status'],_STATUS)
    append=_append_observation(value['append_observation'],value['binding_status'],value['record_id'])
    false={'operational_authority_granted','model_execution_verified','evaluation_executed','independent_evaluation_approved'}
    flags=false|{'record_hash_verified','parent_revalidated_at_append','origin_revalidated_at_append','mutable_state_verified_at_append'}
    _flags(value['verification'],flags,false,{'record_hash_verified','parent_revalidated_at_append','origin_revalidated_at_append'})
    result={key:value[key] for key in sorted(fields-{'append_observation','verification'})}
    result.update(append_observation=append,verification={key:value['verification'][key] for key in sorted(flags)})
    return _copy(result,2*_MIB,20,200000)


def _history(value,intake_id):
    value=_copy(value,_MIB)
    _schema(value,{'schema_version','kind','intake_id','available','records','next_before_seq','verification'},'intake_reference_history')
    if value['intake_id']!=intake_id:_fail()
    _bool(value['available']);_list(value['records'],100);_int(value['next_before_seq'],nullable=True)
    flags={'record_metadata_verified','payloads_reverified','original_sources_reverified','database_currentness_verified'}
    _flags(value['verification'],flags,flags-{'record_metadata_verified'})
    if value['verification']['record_metadata_verified'] is not value['available']:_fail()
    records=[_summary(row) for row in value['records']]
    if not value['available'] and records:_fail()
    seqs=[row['seq'] for row in records]
    if seqs!=sorted(set(seqs),reverse=True):_fail()
    if value['next_before_seq'] is not None and (not records or value['next_before_seq']!=seqs[-1]):_fail()
    return _copy({'schema_version':1,'kind':'intake_reference_history','intake_id':intake_id,'available':value['available'],
        'records':records,'next_before_seq':value['next_before_seq'],'verification':{key:value['verification'][key] for key in sorted(flags)}},2*_MIB,20,200000)


def _current(value,intake_id):
    value=_copy(value,12*_MIB)
    _schema(value,{'schema_version','kind','intake_id','available','status','record','reference_receipt','current_observation','reason_codes','verification'},'intake_reference_current')
    if value['intake_id']!=intake_id:_fail()
    _bool(value['available']);_choice(value['status'],{'current','stale','none','unavailable'});_reasons(value['reason_codes'],_CURRENT_REASONS)
    observation=value['current_observation'];_keys(observation,{'snapshot_id','head_record_id','preparation_ready','observed_at'})
    _sha(observation['snapshot_id'],nullable=True);_sha(observation['head_record_id'],nullable=True)
    _bool(observation['preparation_ready']);_time(observation['observed_at'])
    false={'reference_source_currentness_verified','operational_authority_granted','model_execution_verified','evaluation_executed'}
    flags=false|{'record_hash_verified','database_snapshot_observed'};_flags(value['verification'],flags,false,{'database_snapshot_observed'})
    record=None;reference=None
    if value['record'] is not None:
        record=_summary(value['record']);receipt=_receipt(value['reference_receipt'])
        if not value['available'] or record['record_id']!=observation['head_record_id'] or record['binding_status']!='current_at_append' or record['reference_receipt_id']!=receipt['receipt_id']:_fail()
        reference={'receipt_id':receipt['receipt_id'],'status':receipt['status'],'context_id':receipt['case_binding']['context_id'],
            'selected_case_ids':sorted({ref['case_id'] for ref in receipt['reference_selection']['accepted_references']}),
            'accepted_reference_count':len(receipt['reference_selection']['accepted_references'])}
    elif value['reference_receipt'] is not None or observation['head_record_id'] is not None:_fail()
    if value['verification']['record_hash_verified'] is not (record is not None):_fail()
    if (value['status']=='unavailable') is not (observation['snapshot_id'] is None):_fail()
    if value['status'] in {'current','stale'} and record is None:_fail()
    if value['status']=='none' and record is not None:_fail()
    if value['status']=='current' and (record['expected_snapshot_id']!=observation['snapshot_id'] or 'reference_snapshot_stale' in value['reason_codes']):_fail()
    return _copy({'schema_version':1,'kind':'intake_reference_review_current','intake_id':intake_id,'available':value['available'],
        'status':value['status'],'record':record,'reference_summary':reference,
        'current_observation':{key:observation[key] for key in ['snapshot_id','head_record_id','preparation_ready','observed_at']},
        'reason_codes':list(value['reason_codes']),'verification':{key:value['verification'][key] for key in sorted(flags)}},2*_MIB,20,200000)


def _preparation_id(intake_id,snapshot_id,head_id,hashes,producer):
    return _hash({'schema_version':1,'intake_id':intake_id,'snapshot_id':snapshot_id,'head_record_id':head_id,
        'case_context_sha256':hashes[1],'validated_response_sha256':hashes[2],'reference_receipt_sha256':hashes[3],'producer_name':producer})


class PreparedReferenceReview:
    """Opaque process-local value; no persistent registry and no raw-data repr."""
    __slots__=('__payloads','__hashes','__meta','__identity','__catalog')

    def __init__(self,token=None,*,payloads=None,hashes=None,meta=None,identity=None,catalog=None):
        if token is not _TOKEN:_fail('prepared_invalid')
        for name,value in [('payloads',payloads),('hashes',hashes),('meta',meta),('identity',identity),('catalog',catalog)]:
            object.__setattr__(self,'_PreparedReferenceReview__'+name,value)

    def __setattr__(self,name,value):raise AttributeError('PreparedReferenceReview is immutable')
    def __repr__(self):return '<PreparedReferenceReview>'
    def __reduce_ex__(self,protocol):_fail('prepared_invalid')


@_public
def prepare_reference_review(store,catalog,intake_id,*,case_context,validated_response,producer_name,allow_retained_reads=False):
    """Explicitly read retained bytes; return private preparation and public exact11."""
    _gate(allow_retained_reads);_store(store);_id(intake_id,'invalid_argument');_id(producer_name,'invalid_argument')
    if type(catalog) is not FccReportCaseCatalog:_fail('invalid_argument')
    shared=[0]
    context=_copy(case_context,8*_MIB,24,200000,code='invalid_argument',shared=shared)
    response=_copy(validated_response,320*1024,16,60000,code='invalid_argument',shared=shared)
    identity=_identity(store);c1=_capture(read_intake_reference_snapshot(store,intake_id),intake_id)
    if c1['snapshot'] is None:_fail('unavailable')
    snapshot=c1['snapshot'];receipt=_receipt(build_intake_case_reference_receipt(snapshot,catalog,context,response,producer_name=producer_name))
    c2=_current(current_reference(store,intake_id),intake_id);observation=c2['current_observation']
    if observation['snapshot_id'] is None:_fail('unavailable')
    if c1['snapshot_id']!=observation['snapshot_id'] or c1['readiness']['ready'] is not observation['preparation_ready']:_fail('review_state_changed')
    if _identity(store)!=identity:_fail('review_state_changed')
    _ids(context['requested_case_ids'],16)
    payloads=tuple(_encoded(value) for value in [snapshot,context,response,receipt])
    if sum(map(len,payloads))>20*_MIB:_fail('input_limit')
    hashes=tuple(hashlib.sha256(raw).hexdigest() for raw in payloads)
    preparation_id=_preparation_id(intake_id,c1['snapshot_id'],observation['head_record_id'],hashes,producer_name)
    prepared=PreparedReferenceReview(_TOKEN,payloads=payloads,hashes=hashes,
        meta=(intake_id,c1['snapshot_id'],observation['head_record_id'],preparation_id,producer_name),identity=identity,catalog=catalog)
    preview={'schema_version':1,'kind':'intake_reference_review_preview','intake_id':intake_id,'preparation_id':preparation_id,
        'observation':{'kind':'paired_public_reads','snapshot_id':c1['snapshot_id'],'head_record_id':observation['head_record_id'],'observed_at':observation['observed_at']},
        'preparation_ready':c1['readiness']['ready'],'reason_codes':list(c1['readiness']['reason_codes']),'review_status':receipt['status'],
        'selection':{'context_id':receipt['case_binding']['context_id'],'corpus_id':receipt['case_binding']['corpus_id'],
            'requested_case_ids':list(context['requested_case_ids']),'status':receipt['reference_selection']['status'],
            'accepted_reference_count':len(receipt['reference_selection']['accepted_references']),'receipt_id':receipt['receipt_id']},
        'source_modes':{'intake_revision_synthetic':snapshot['synthetic'],'catalog_synthetic':receipt['case_binding']['catalog_synthetic'],
            'intake_provenance_status':'unconfirmed' if 'source_provenance_unconfirmed' in c1['readiness']['reason_codes'] else 'confirmed'},
        'verification':{'reference_receipt_validated':True,'retained_snapshot_observed':True,'reference_source_currentness_verified':False,
            'operational_authority_granted':False,'model_execution_verified':False,'evaluation_executed':False}}
    return prepared,_copy(preview,32768,12,4096)


@_public
def append_reference_review(store,catalog,prepared,request,*,allow_retained_reads=False,allow_append=False):
    """One explicit038 publication/replay, using the original private preparation."""
    _gate(allow_retained_reads,allow_append);_store(store)
    request=_copy(request,16384,8,256,code='invalid_argument')
    _keys(request,{'schema_version','intake_id','request_id','preparation_id','expected_snapshot_id','expected_head_record_id'},'invalid_argument')
    _int(request['schema_version'],'invalid_argument',maximum=1)
    for key in ['intake_id','request_id']:_id(request[key],'invalid_argument')
    for key in ['preparation_id','expected_snapshot_id']:_sha(request[key],'invalid_argument')
    _sha(request['expected_head_record_id'],'invalid_argument',nullable=True)
    if type(prepared) is not PreparedReferenceReview:_fail('prepared_invalid')
    for name in ['payloads','hashes','meta','identity','catalog']:
        if not hasattr(prepared,'_PreparedReferenceReview__'+name):_fail('prepared_invalid')
    if type(prepared._PreparedReferenceReview__meta) is not tuple or len(prepared._PreparedReferenceReview__meta)!=5:_fail('prepared_invalid')
    if type(catalog) is not FccReportCaseCatalog or catalog is not prepared._PreparedReferenceReview__catalog:_fail('prepared_invalid')
    if _identity(store)!=prepared._PreparedReferenceReview__identity:_fail('prepared_invalid')
    intake_id,snapshot_id,head_id,preparation_id,producer=prepared._PreparedReferenceReview__meta
    _id(intake_id,'prepared_invalid');_id(producer,'prepared_invalid')
    _sha(snapshot_id,'prepared_invalid');_sha(head_id,'prepared_invalid',nullable=True);_sha(preparation_id,'prepared_invalid')
    if any(request[key]!=expected for key,expected in [('intake_id',intake_id),('preparation_id',preparation_id),('expected_snapshot_id',snapshot_id),('expected_head_record_id',head_id)]):_fail('prepared_invalid')
    payloads=prepared._PreparedReferenceReview__payloads;hashes=prepared._PreparedReferenceReview__hashes
    if type(payloads) is not tuple or len(payloads)!=4 or type(hashes) is not tuple or len(hashes)!=4:_fail('prepared_invalid')
    if any(type(raw) is not bytes for raw in payloads) or sum(map(len,payloads))>20*_MIB:_fail('prepared_invalid')
    if tuple(hashlib.sha256(raw).hexdigest() for raw in payloads)!=hashes or _preparation_id(intake_id,snapshot_id,head_id,hashes,producer)!=preparation_id:_fail('prepared_invalid')
    shared=[0];values=[]
    for raw,limit,depth,nodes in zip(payloads,[9*_MIB,8*_MIB,320*1024,2*_MIB],[20,24,16,16],[500000,200000,60000,500000]):
        value=_copy(json.loads(raw),limit,depth,nodes,shared=shared)
        if _encoded(value)!=raw:_fail('prepared_invalid')
        values.append(value)
    snapshot,context,response,receipt=values
    result=record_intake_reference(store,request['request_id'],expected_snapshot_id=snapshot_id,expected_head_record_id=head_id,
        intake_snapshot=snapshot,catalog=catalog,case_context=context,validated_response=response,reference_receipt=receipt,producer_name=producer)
    return _registration(result,request['request_id'])


@_public
def read_reference_review(store,intake_id,request,*,allow_retained_reads=False):
    """Metadata history, or separately authorized fresh retained-integrity current view."""
    _bool(allow_retained_reads,'invalid_argument');_store(store);_id(intake_id,'invalid_argument')
    request=_copy(request,16384,8,256,code='invalid_argument')
    if type(request) is not dict or type(request.get('action')) is not str:_fail('invalid_argument')
    if request['action']=='history':
        _keys(request,{'schema_version','action','limit','before_seq'},'invalid_argument');_int(request['schema_version'],'invalid_argument',maximum=1)
        _int(request['limit'],'invalid_argument',maximum=100);_int(request['before_seq'],'invalid_argument',nullable=True)
        return _history(reference_history(store,intake_id,limit=request['limit'],before_seq=request['before_seq']),intake_id)
    if request['action']=='current':
        _keys(request,{'schema_version','action'},'invalid_argument');_int(request['schema_version'],'invalid_argument',maximum=1)
        _gate(allow_retained_reads)
        return _current(current_reference(store,intake_id),intake_id)
    _fail('invalid_argument')

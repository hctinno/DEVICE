"""Bind references to a caller snapshot; no Store, execution, or evaluation authority."""
import hashlib
import json
import math
import re

from .fcc_report_cases import FccReportCaseCatalog,FccReportCaseError
from .fcc_case_review import build_case_review_context,decode_case_review_response,FccCaseReviewError


_MIB=1024*1024
_LIMITS={'max_snapshot_bytes':9*_MIB,'max_projection_bytes':8*_MIB,'max_context_bytes':8*_MIB,
    'max_response_bytes':320*1024,'max_output_bytes':2*_MIB,'max_snapshot_depth':20,'max_projection_depth':16,
    'max_context_depth':24,'max_response_depth':16,'max_output_depth':16,'max_nodes':500000,
    'max_cases':128,'max_requested_cases':16,'max_references':256,'max_facts':3,'max_questions':200}
_CORE=('intake_id','revision','revision_fingerprint','origin_job_id','analysis_context_id','result_sha256','synthetic')
_SNAPSHOT={'schema_version','kind','snapshot_scope',*_CORE,'readiness_fingerprint','projection','projection_sha256'}
_CONTEXT={'schema_version','kind','context_id','corpus_id','execution_mode','synthetic','query','requested_case_ids',
    'search_status','status','reason_codes','source_binding','source_scope','verification','limits','cases','excluded_candidates','case_previews','documents'}
_RESPONSE={'schema_version','kind','context_id','corpus_id','status','reason_codes','references','expected_producer','source_binding','verification'}
_REF={'case_id','claim_id','evidence_id','document_id','source_sha256','file_page','text_sha256','line_start','line_end'}
_FACTS={'product_type','market','model'}
_FALSE=('source_facts_reverified','result_projection_reverified','database_currentness_verified','operational_authority_granted',
    'model_execution_verified','model_quality_verified','independent_evaluation_approved','training_executed','evaluation_executed','hardware_verified','physical_verified')
_CODES={'catalog_invalid','snapshot_invalid','context_invalid','response_invalid','producer_invalid','source_error','limit_exceeded'}
_ID=re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,149}\Z',re.ASCII)
_CASE_ID=re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z',re.ASCII)
_SHA=re.compile(r'[0-9a-f]{64}\Z',re.ASCII)


class IntakeCaseReferencesError(ValueError):
    def __init__(self,code):
        suffix=code.removeprefix('intake_case_references_') if type(code) is str else 'source_error'
        self.code='intake_case_references_'+(suffix if suffix in _CODES else 'source_error')
        super().__init__(self.code)


def _fail(code):raise IntakeCaseReferencesError(code)
def _encoded(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def _hash(value):return hashlib.sha256(_encoded(value)).hexdigest()
def _same(a,b):return _encoded(a)==_encoded(b)


def _copy(value,code,limit,depth_limit,nodes,local_limit=500000):
    size=local_nodes=0
    def consume(amount):
        nonlocal size
        size+=amount
        if size>limit:_fail('limit_exceeded')
    def count():
        nonlocal local_nodes
        nodes[0]+=1;local_nodes+=1
        if nodes[0]>500000 or local_nodes>local_limit:_fail('limit_exceeded')
    def scalar(item):
        if type(item) is str and len(item)>limit-size:_fail('limit_exceeded')
        try:amount=len(_encoded(item))
        except (ValueError,UnicodeError,OverflowError):_fail(code)
        consume(amount)
        return item
    def walk(item,depth=0):
        count()
        if depth>depth_limit:_fail('limit_exceeded')
        if type(item) is dict:
            consume(2);result={}
            for index,(key,child) in enumerate(item.items()):
                if type(key) is not str:_fail(code)
                count()
                if index:consume(1)
                scalar(key);consume(1);result[key]=walk(child,depth+1)
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


def _keys(value,keys,code):
    if type(value) is not dict or set(value)!=keys:_fail(code)
def _schema(value,keys,kind,code):
    _keys(value,keys,code)
    if type(value['schema_version']) is not int or value['schema_version']!=1 or value['kind']!=kind:_fail(code)
def _text(value,code,maximum=None,empty=False):
    if type(value) is not str or not empty and not value.strip():_fail(code)
    if maximum is not None and len(value)>maximum:_fail(code)
def _id(value,code,case=False):
    if type(value) is not str or not (_CASE_ID if case else _ID).fullmatch(value):_fail(code)
def _sha(value,code):
    if type(value) is not str or not _SHA.fullmatch(value):_fail(code)
def _integer(value,code,minimum=1):
    if type(value) is not int or value<minimum:_fail(code)
def _array(value,code,maximum):
    if type(value) is not list:_fail(code)
    if len(value)>maximum:_fail('limit_exceeded')
def _choice(value,options,code):
    if type(value) is not str or value not in options:_fail(code)


def _snapshot(value):
    code='snapshot_invalid';_schema(value,_SNAPSHOT,'intake_case_reference_snapshot',code)
    if value['snapshot_scope']!='caller_provided':_fail(code)
    for key in ['intake_id','origin_job_id']:
        if value[key] is not None:_id(value[key],code)
    if value['revision'] is not None:_integer(value['revision'],code)
    for key in ['revision_fingerprint','analysis_context_id','result_sha256','readiness_fingerprint']:
        if value[key] is not None:_sha(value[key],code)
    if value['synthetic'] is not None and type(value['synthetic']) is not bool:_fail(code)
    _sha(value['projection_sha256'],code);projection=value['projection']
    _copy(projection,code,8*_MIB,16,[0],50000)
    _keys(projection,{'facts','questions'},code)
    facts=projection['facts']
    if type(facts) is not dict or set(facts)-_FACTS:_fail(code)
    for fact in facts.values():
        if type(fact) is not dict or not {'value','status'}<=set(fact) or set(fact)-{'value','status','event_id'}:_fail(code)
        _text(fact['value'],code,4000);_choice(fact['status'],{'explicit','inferred','uncertain','user_confirmed'},code)
        if fact['status']=='user_confirmed' and 'event_id' not in fact:_fail(code)
        if 'event_id' in fact:
            if type(fact['event_id']) is int:_integer(fact['event_id'],code)
            else:_id(fact['event_id'],code,case=True)
    _array(projection['questions'],code,200)
    for question in projection['questions']:
        _keys(question,{'key'},code);_text(question['key'],code,empty=True)
        if len(question['key'])>_MIB:_fail('limit_exceeded')


def _response(value):
    code='response_invalid';_schema(value,_RESPONSE,'validated_fcc_case_review',code)
    _sha(value['context_id'],code);_id(value['corpus_id'],code,case=True)
    _choice(value['status'],{'selected','insufficient_evidence','no_candidate'},code)
    _array(value['reason_codes'],code,4)
    for item in value['reason_codes']:_text(item,code,128)
    _array(value['references'],code,256)
    for ref in value['references']:
        _keys(ref,_REF,code)
        for key in ['case_id','claim_id','document_id']:_id(ref[key],code,case=True)
        for key in ['evidence_id','source_sha256','text_sha256']:_sha(ref[key],code)
        for key in ['file_page','line_start','line_end']:_integer(ref[key],code)
    _keys(value['expected_producer'],{'kind','name'},code)
    _text(value['expected_producer']['kind'],code);_text(value['expected_producer']['name'],code)
    _keys(value['source_binding'],{'summary_sha256','matches_sha256','case_sha256s'},code)
    for key in ['summary_sha256','matches_sha256']:_sha(value['source_binding'][key],code)
    _array(value['source_binding']['case_sha256s'],code,16)
    for row in value['source_binding']['case_sha256s']:
        _keys(row,{'case_id','sha256'},code);_id(row['case_id'],code,case=True);_sha(row['sha256'],code)
    flags={'source_dto_validated','source_page_literals_reverified','structured_interpretation_verified','institution_identity_verified',
        'normative_compliance_verified','model_execution_verified','model_quality_verified','independent_evaluation_approved',
        'training_executed','evaluation_executed','hardware_verified','physical_verified'}
    _keys(value['verification'],flags,code)
    if any(type(v) is not bool for v in value['verification'].values()):_fail(code)


def _wire(response):
    return {'schema_version':1,'kind':'fcc_case_review_response','context_id':response['context_id'],
        'producer':response['expected_producer'],'status':response['status'],'references':response['references'],'reason_codes':response['reason_codes']}


def _parent_limit(error):
    if error.code in {'fcc_case_limit_exceeded','fcc_case_review_limit_exceeded'}:_fail('limit_exceeded')


def _cases(context,matching,response,bound,snapshot_bound,response_valid,match_checked):
    details={c['case_id']:c for c in context['cases']}
    excluded={c['case_id']:c for c in context['excluded_candidates']}
    relations={row['preview']['case_id']:row['model_relation'] for row in matching['matches']} if matching else {}
    admitted={key for key,value in relations.items() if value!='related_family'} if matching and matching['status']=='candidates' else set()
    referenced={r['case_id'] for r in response['references']} if response_valid and response['status']=='selected' else set()
    rows=[]
    for preview in sorted(context['case_previews'],key=lambda row:row['case_id']):
        identity=preview['case_id'];detail=details.get(identity);exclusion=excluded.get(identity);relation=relations.get(identity)
        membership=('referenced' if identity in referenced else 'not_referenced') if response_valid and response['status']=='selected' else 'not_assessed'
        reasons=set();status='unknown'
        if not detail:reasons.add('case_detail_not_requested')
        if not snapshot_bound:reasons.add('snapshot_unbound')
        if not response_valid:reasons.add('source_context_unbound')
        elif response['status']=='insufficient_evidence':reasons.add('response_insufficient_evidence')
        elif response['status']=='no_candidate':reasons.add('response_no_candidate')
        if match_checked and matching['status']=='insufficient_evidence':reasons.add('intake_match_insufficient')
        if relation=='related_family':status='outside_intake_scope';reasons.add('related_model')
        elif bound and identity in admitted and response_valid and response['status']=='selected':
            if identity in referenced:status='selected'
            elif detail:status='not_selected_in_response';reasons.add('not_selected_in_response')
        rows.append({'case_id':identity,'context_inclusion':'detailed' if detail else 'preview_only',
            'context_exclusion_reason':exclusion['reason'] if exclusion else None,
            'context_model_relation':detail['model_relation'] if detail else exclusion['model_relation'] if exclusion else None,
            'intake_model_relation':relation,'response_membership':membership,'selection_status':status,'reason_codes':sorted(reasons)})
    return rows


def build_intake_case_reference_receipt(intake_snapshot,catalog,case_context,validated_response,*,producer_name):
    """Bind only to the provided snapshot; never establishes current DB or authority."""
    try:return _build(intake_snapshot,catalog,case_context,validated_response,producer_name)
    except IntakeCaseReferencesError as error:code=error.code
    except Exception:code='source_error'
    raise IntakeCaseReferencesError(code) from None


def _build(snapshot,catalog,context,response,name):
    if type(catalog) is not FccReportCaseCatalog:_fail('catalog_invalid')
    _text(name,'producer_invalid',200)
    try:name.encode('utf-8')
    except UnicodeError:_fail('producer_invalid')
    nodes=[0];snapshot=_copy(snapshot,'snapshot_invalid',9*_MIB,20,nodes)
    context=_copy(context,'context_invalid',8*_MIB,24,nodes,200000)
    response=_copy(response,'response_invalid',320*1024,16,nodes,60000)
    _snapshot(snapshot);_schema(context,_CONTEXT,'fcc_case_review_context','context_invalid');_response(response)
    reasons=set();missing=sorted(key for key in _CORE if snapshot[key] is None);complete=not missing
    if missing:reasons.add('snapshot_binding_incomplete')
    projection_valid=snapshot['projection_sha256']==_hash(snapshot['projection'])
    if not projection_valid:reasons.add('projection_hash_mismatch')
    fresh=None
    try:fresh=build_case_review_context(catalog,query=context['query'],case_ids=context['requested_case_ids'])
    except FccCaseReviewError as error:
        _parent_limit(error)
        if error.code=='fcc_case_review_query_invalid':_fail('context_invalid')
        if error.code!='fcc_case_review_selection_invalid':_fail('source_error')
    context_matched=fresh is not None and _same(fresh,context)
    if not context_matched:reasons.add('case_context_mismatch')
    decoded=None
    try:decoded=decode_case_review_response(_encoded(_wire(response)),context,producer_name=name)
    except FccCaseReviewError as error:_parent_limit(error)
    response_valid=context_matched and decoded is not None and _same(decoded,response)
    if not response_valid:reasons.add('case_response_not_bound')
    matching=None;match_checked=False;scope_checked=False;admitted=set()
    if projection_valid and context_matched:
        try:matching=catalog.match_intake(snapshot['projection'],context['query'])
        except FccReportCaseError as error:
            _parent_limit(error)
            _fail('source_error')
        match_checked=True
        if matching['status']=='insufficient_evidence':reasons.add('intake_query_insufficient')
        elif matching['status']=='candidates':admitted={row['preview']['case_id'] for row in matching['matches'] if row['model_relation']!='related_family'}
        if response_valid and matching['status']!='insufficient_evidence':
            outside=response['status']=='selected' and any(ref['case_id'] not in admitted for ref in response['references'])
            if outside:reasons.add('selected_reference_outside_intake_scope')
            else:scope_checked=True
    bound=not reasons
    intake_match={'status':matching['status'] if matching else 'not_assessed','reason_codes':sorted(matching['reason_codes']) if matching else [],
        'matched_case_ids':sorted(row['preview']['case_id'] for row in matching['matches']) if matching else [],
        'admitted_case_ids':sorted(admitted),'fact_statuses':matching['intake_binding']['fact_statuses'] if matching else {key:None for key in sorted(_FACTS)}}
    selection_status='selected' if bound and response['status']=='selected' else 'no_candidate' if bound and response['status']=='no_candidate' else 'unknown'
    selection={'status':selection_status,'source_response_status':response['status'] if response_valid else None,
        'source_reason_codes':response['reason_codes'] if response_valid else [],
        'accepted_references':response['references'] if selection_status=='selected' else [],
        'reported_reference_count':len(response['references']) if response_valid else None}
    verification={key:False for key in _FALSE}
    verification.update(snapshot_dto_validated=True,projection_hash_verified=projection_valid,snapshot_metadata_complete=complete,
        catalog_context_matched=context_matched,response_revalidated=response_valid,intake_match_checked=match_checked,reference_scope_checked=scope_checked)
    intake_binding={key:snapshot[key] for key in [*_CORE,'readiness_fingerprint','projection_sha256']}
    intake_binding.update(snapshot_sha256=_hash(snapshot),missing_fields=missing)
    case_binding={'provided_context_sha256':_hash(context),'provided_response_sha256':_hash(response),
        'context_id':context['context_id'] if context_matched else None,'corpus_id':context['corpus_id'] if context_matched else None,
        'source_binding':context['source_binding'] if context_matched else None,'query_sha256':_hash(context['query']) if context_matched else None,
        'producer':{'kind':'model','name':name},'catalog_synthetic':context['synthetic'] if context_matched else None,
        'context_status':context['status'] if context_matched else None,'search_status':context['search_status'] if context_matched else None}
    result={'schema_version':1,'kind':'intake_case_reference_receipt','execution_mode':'provided_snapshot_read_only',
        'status':'bound' if bound else 'insufficient_evidence','reason_codes':sorted(reasons),'intake_binding':intake_binding,
        'case_binding':case_binding,'intake_match':intake_match,'reference_selection':selection,
        'case_states':_cases(context,matching,response,bound,complete and projection_valid,response_valid,match_checked) if context_matched else [],
        'evaluation':{'status':'not_executed','score':None,'actual_model_score':None,'scored_fixture_checks':0,'actual_model_checks':0,
                      'independent_assignment_status':'not_assessed'},'verification':verification,'limits':dict(_LIMITS)}
    result['receipt_id']=_hash(result)
    return _copy(result,'source_error',2*_MIB,16,[0])

"""Pure fixture reference checks; never executes a model or authenticates labels."""
import hashlib
import json
import math
import re

from .fcc_case_evaluation import build_case_evaluation_split
from .fcc_case_review import FccCaseReviewError, decode_case_review_response


_MIB=1024*1024
_LIMITS={'max_split_bytes':16*_MIB,'max_context_bytes':8*_MIB,'max_response_bytes':320*1024,
    'max_expectation_bytes':256*1024,'max_output_bytes':4*_MIB,'max_split_depth':12,'max_context_depth':24,
    'max_response_depth':16,'max_expectation_depth':12,'max_output_depth':16,'max_nodes':4500000,
    'max_split_cases':4096,'max_exposed_cases':4352,'max_references':256}
_CODES={'input_invalid','split_invalid','context_invalid','response_invalid','expectation_invalid','producer_invalid','limit_exceeded'}
_BASE={'case_id','product_family_group_id','fcc_ids','report_group_id','original_sha256s','reuse_group_ids',
    'group_review_status','unresolved_relations'}
_SPLIT={'schema_version','kind','algorithm','status','input_fingerprint','scope','fact_review_verified',
    'model_execution_verified','training_executed','evaluation_executed','hardware_verified','independent_assignment_status',
    'case_count','component_count','eligible_component_count','ineligible_component_count','denominators','cases',
    'components','development','independent','unassigned'}
_CONTEXT={'schema_version','kind','context_id','corpus_id','execution_mode','synthetic','query','requested_case_ids',
    'search_status','status','reason_codes','source_binding','source_scope','verification','limits','cases',
    'excluded_candidates','case_previews','documents'}
_RESPONSE={'schema_version','kind','context_id','corpus_id','status','reason_codes','references','expected_producer',
    'source_binding','verification'}
_EXPECTATION={'schema_version','kind','context_id','label_review_status','references'}
_REFERENCE={'case_id','claim_id','evidence_id','document_id','source_sha256','file_page','text_sha256','line_start','line_end'}
_ID=re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z',re.ASCII)
_SHA=re.compile(r'[0-9a-f]{64}\Z',re.ASCII)
_FALSE_FLAGS={'source_facts_reverified','group_facts_reverified','label_correctness_verified','model_execution_verified',
    'model_quality_verified','independent_evaluation_approved','training_executed','evaluation_executed',
    'hardware_verified','physical_verified'}


class FccCaseReviewEvaluationError(ValueError):
    def __init__(self,code):
        suffix=code.removeprefix('fcc_case_review_evaluation_') if type(code) is str else 'input_invalid'
        self.code='fcc_case_review_evaluation_'+(suffix if suffix in _CODES else 'input_invalid')
        super().__init__(self.code)


def _fail(code):raise FccCaseReviewEvaluationError(code)
def _encoded(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def _hash(value):return hashlib.sha256(_encoded(value)).hexdigest()
def _same(left,right):return _encoded(left)==_encoded(right)


def _clone(value,code,limit,depth_limit,nodes):
    size=0
    def consume(amount):
        nonlocal size
        size+=amount
        if size>limit:_fail('limit_exceeded')
    def scalar(item):
        if type(item) is str and len(item)>limit-size:_fail('limit_exceeded')
        try:amount=len(_encoded(item))
        except (ValueError,UnicodeError,OverflowError):_fail(code)
        consume(amount)
        return item
    def walk(item,depth=0):
        nodes[0]+=1
        if nodes[0]>_LIMITS['max_nodes'] or depth>depth_limit:_fail('limit_exceeded')
        if type(item) is dict:
            result={};consume(2)
            for index,(key,child) in enumerate(item.items()):
                if type(key) is not str:_fail(code)
                nodes[0]+=1
                if nodes[0]>_LIMITS['max_nodes']:_fail('limit_exceeded')
                if index:consume(1)
                scalar(key);consume(1);result[key]=walk(child,depth+1)
            return result
        if type(item) is list:
            result=[];consume(2)
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
def _str(value,code):
    if type(value) is not str or not value.strip():_fail(code)
def _sha(value,code):
    if type(value) is not str or not _SHA.fullmatch(value):_fail(code)
def _id(value,code):
    if type(value) is not str or not _ID.fullmatch(value):_fail(code)
def _integer(value,code,minimum=0):
    if type(value) is not int or value<minimum:_fail(code)
def _array(value,code,maximum=None):
    if type(value) is not list:_fail(code)
    if maximum is not None and len(value)>maximum:_fail('limit_exceeded')
def _strings(value,code,maximum=None,validator=_str):
    _array(value,code,maximum)
    for item in value:validator(item,code)
def _bool(value,code):
    if type(value) is not bool:_fail(code)
def _choice(value,choices,code):
    if type(value) is not str or value not in choices:_fail(code)


def _split_shape(value):
    code='split_invalid';_schema(value,_SPLIT,'fcc_case_evaluation_split',code)
    if value['algorithm']!='namespaced_connected_components_v1' or value['status']!='configured' or value['scope']!='provided_metadata_only':_fail(code)
    _sha(value['input_fingerprint'],code)
    for key in ['fact_review_verified','model_execution_verified','training_executed','evaluation_executed','hardware_verified']:_bool(value[key],code)
    _choice(value['independent_assignment_status'],{'assigned','not_assigned'},code)
    for key in ['case_count','component_count','eligible_component_count','ineligible_component_count']:_integer(value[key],code)
    denominator={'provided_cases','provided_components','eligible_cases','ineligible_cases','eligible_components',
        'ineligible_components','development_cases','independent_cases','unassigned_cases'}
    _keys(value['denominators'],denominator,code)
    for item in value['denominators'].values():_integer(item,code)
    _array(value['cases'],code,4096)
    for case in value['cases']:
        _keys(case,_BASE|{'group_id','eligible','case_ineligibility_reasons','component_ineligibility_reasons'},code)
        _id(case['case_id'],code);_str(case['group_id'],code);_bool(case['eligible'],code)
        for key in ['product_family_group_id','report_group_id']:
            if case[key] is not None:_str(case[key],code)
        for key in ['fcc_ids','original_sha256s','reuse_group_ids','unresolved_relations']:_strings(case[key],code,64)
        _choice(case['group_review_status'],{'reviewed','pending'},code)
        for key in ['case_ineligibility_reasons','component_ineligibility_reasons']:_strings(case[key],code)
    _array(value['components'],code,4096)
    for component in value['components']:
        _keys(component,{'group_id','group_sha256','case_ids','keys','eligible','ineligibility_reasons','ineligible_case_ids'},code)
        _str(component['group_id'],code);_sha(component['group_sha256'],code);_bool(component['eligible'],code)
        for key in ['case_ids','ineligible_case_ids']:_strings(component[key],code,4096,_id)
        _strings(component['ineligibility_reasons'],code)
        _keys(component['keys'],{'product_family_group_ids','fcc_ids','report_group_ids','original_sha256s','reuse_group_ids'},code)
        for values in component['keys'].values():_strings(values,code)
    for name in ['development','independent','unassigned']:
        _keys(value[name],{'case_ids','group_ids'},code)
        _strings(value[name]['case_ids'],code,4096,_id);_strings(value[name]['group_ids'],code,4096)


def _refs_shape(refs,code):
    _array(refs,code,256)
    for ref in refs:
        _keys(ref,_REFERENCE,code)
        for key in ['case_id','claim_id','document_id']:_id(ref[key],code)
        for key in ['evidence_id','source_sha256','text_sha256']:_sha(ref[key],code)
        for key in ['file_page','line_start','line_end']:_integer(ref[key],code,1)


def _response_shape(value):
    code='response_invalid';_schema(value,_RESPONSE,'validated_fcc_case_review',code)
    _sha(value['context_id'],code);_id(value['corpus_id'],code)
    _choice(value['status'],{'selected','insufficient_evidence','no_candidate'},code)
    _strings(value['reason_codes'],code,4);_refs_shape(value['references'],code)
    _keys(value['expected_producer'],{'kind','name'},code)
    _str(value['expected_producer']['kind'],code);_str(value['expected_producer']['name'],code)
    _keys(value['source_binding'],{'summary_sha256','matches_sha256','case_sha256s'},code)
    for key in ['summary_sha256','matches_sha256']:_sha(value['source_binding'][key],code)
    _array(value['source_binding']['case_sha256s'],code,16)
    for row in value['source_binding']['case_sha256s']:
        _keys(row,{'case_id','sha256'},code);_id(row['case_id'],code);_sha(row['sha256'],code)
    flags={'source_dto_validated','source_page_literals_reverified','structured_interpretation_verified',
        'institution_identity_verified','normative_compliance_verified','model_execution_verified','model_quality_verified',
        'independent_evaluation_approved','training_executed','evaluation_executed','hardware_verified','physical_verified'}
    _keys(value['verification'],flags,code)
    for flag in value['verification'].values():_bool(flag,code)


def _recompute(split):
    rows=[{key:row[key] for key in _BASE} for row in split['cases']]
    try:result=build_case_evaluation_split(rows,development_case_ids=split['development']['case_ids'],
                                        independent_case_ids=split['independent']['case_ids'])
    except ValueError as error:
        if str(error)=='fcc_case_evaluation_budget_exceeded':_fail('limit_exceeded')
        return False
    return _same(result,split)


def _decode(wire,context,name):
    try:return decode_case_review_response(_encoded(wire),context,producer_name=name),None
    except FccCaseReviewError as error:
        if error.code=='fcc_case_review_limit_exceeded':_fail('limit_exceeded')
        return None,error.code


def _exposure(split,context):
    reasons=set();rows={row['case_id']:row for row in split['cases']}
    previews={row['case_id']:row for row in context['case_previews']}
    visible=set(previews)|set(context['requested_case_ids'])
    for key in ['cases','excluded_candidates']:visible.update(row['case_id'] for row in context[key])
    visible.update(row['case_id'] for row in context['source_binding']['case_sha256s'])
    documents={row['document_id']:row for row in context['documents']}
    document_shas={row['sha256'] for row in documents.values()}
    linked={identity for identity,row in rows.items() if document_shas&set(row['original_sha256s'])}
    exposed=visible|linked
    if len(exposed)>4352:_fail('limit_exceeded')
    if not exposed:reasons.add('empty_exposure')
    if exposed-set(rows):reasons.add('unknown_exposed_case')
    used=set()
    for identity,preview in previews.items():
        used.update(preview['document_ids'])
        if set(preview['document_ids'])-set(documents):reasons.add('unlinked_context_document')
        if identity not in rows:continue
        row=rows[identity]
        for document_id in preview['document_ids']:
            if document_id in documents and documents[document_id]['sha256'] not in row['original_sha256s']:reasons.add('document_source_mismatch')
        if preview['report_group_id'] is not None and preview['report_group_id'].strip().casefold()!=row['report_group_id']:reasons.add('report_group_mismatch')
        if {v.strip().upper() for v in preview['fcc_ids']}!=set(row['fcc_ids']):reasons.add('fcc_id_mismatch')
    if set(documents)-used:reasons.add('unlinked_context_document')
    development=set(split['development']['case_ids']);independent=set(split['independent']['case_ids'])
    if exposed&development:reasons.add('development_case_exposed')
    if (exposed&set(rows))-development-independent:reasons.add('unassigned_case_exposed')
    if any(not rows[identity]['eligible'] for identity in exposed&set(rows)):reasons.add('ineligible_component_exposed')
    components=[group for group in split['components'] if set(group['case_ids'])&exposed]
    required={identity for group in components for identity in group['case_ids']}
    if required-set(previews):reasons.add('partial_component_exposure')
    return {'case_ids':sorted(exposed),'document_linked_case_ids':sorted(linked),
        'required_component_case_ids':sorted(required),'component_ids':sorted(group['group_id'] for group in components)},reasons


def evaluate_case_review_references(split,context,validated_response,*,expectation,producer_name):
    """Compare synthetic reference fixtures after complete independent-exposure gates."""
    try:return _evaluate(split,context,validated_response,expectation,producer_name)
    except FccCaseReviewEvaluationError as error:code=error.code
    except Exception:code='input_invalid'
    raise FccCaseReviewEvaluationError(code) from None


def _evaluate(split,context,response,expectation,name):
    _str(name,'producer_invalid')
    if len(name)>200:_fail('producer_invalid')
    try:name.encode('utf-8')
    except UnicodeError:_fail('producer_invalid')
    nodes=[0]
    split=_clone(split,'split_invalid',16*_MIB,12,nodes)
    context=_clone(context,'context_invalid',8*_MIB,24,nodes)
    response=_clone(response,'response_invalid',320*1024,16,nodes)
    expectation=_clone(expectation,'expectation_invalid',256*1024,12,nodes)
    _split_shape(split);_schema(context,_CONTEXT,'fcc_case_review_context','context_invalid')
    _response_shape(response);_schema(expectation,_EXPECTATION,'fcc_case_review_expectation','expectation_invalid')
    _sha(expectation['context_id'],'expectation_invalid')
    _choice(expectation['label_review_status'],{'reviewed','pending'},'expectation_invalid')
    if expectation['references'] is not None:_refs_shape(expectation['references'],'expectation_invalid')
    elif expectation['label_review_status']!='pending':_fail('expectation_invalid')
    reasons=set();split_valid=_recompute(split)
    if not split_valid:reasons.add('split_not_consistent')
    producer={'kind':'model','name':name}
    wire={'schema_version':1,'kind':'fcc_case_review_response','context_id':response['context_id'],
        'producer':response['expected_producer'],'status':response['status'],'references':response['references'],
        'reason_codes':response['reason_codes']}
    decoded,error=_decode(wire,context,name)
    context_valid=error!='fcc_case_review_context_invalid'
    response_valid=decoded is not None and _same(decoded,response)
    if not context_valid:reasons.add('context_not_validated')
    elif not response_valid:reasons.add('response_not_bound')
    reviewed=expectation['label_review_status']=='reviewed';expected_valid=False
    if not reviewed:reasons.add('label_review_pending')
    if not expectation['references']:reasons.add('expected_references_missing')
    if context_valid:
        if expectation['context_id']!=context['context_id']:reasons.add('expected_context_mismatch')
        elif reviewed and expectation['references']:
            expected_wire={'schema_version':1,'kind':'fcc_case_review_response','context_id':expectation['context_id'],
                'producer':producer,'status':'selected','references':expectation['references'],'reason_codes':[]}
            result,_=_decode(expected_wire,context,name);expected_valid=result is not None
            if not expected_valid:reasons.add('expected_references_not_bound')
        if context['status']!='ready':reasons.add('context_not_ready')
        if context['synthetic'] is not True:reasons.add('non_synthetic_context')
    exposure={key:[] for key in ['case_ids','document_linked_case_ids','required_component_case_ids','component_ids']}
    exposure_valid=False
    if split_valid and context_valid:
        exposure,issues=_exposure(split,context);reasons.update(issues);exposure_valid=not issues
    checked=not reasons
    counts={key:None for key in ['expected_references','observed_references','matched_references','missing_references','unexpected_references']}
    counts.update(scored_fixture_checks=int(checked),actual_model_checks=0)
    differences={'missing':[],'unexpected':[]};score=None
    if checked:
        expected={_encoded(ref):ref for ref in expectation['references']}
        observed={_encoded(ref):ref for ref in response['references']}
        missing=set(expected)-set(observed);unexpected=set(observed)-set(expected)
        score=int(not missing and not unexpected)
        counts.update(expected_references=len(expected),observed_references=len(observed),matched_references=len(set(expected)&set(observed)),
                      missing_references=len(missing),unexpected_references=len(unexpected))
        differences={'missing':[expected[key] for key in sorted(missing)],'unexpected':[observed[key] for key in sorted(unexpected)]}
    verification={key:False for key in _FALSE_FLAGS}
    verification.update(split_dto_recomputed=split_valid,context_response_revalidated=context_valid and response_valid,
        expectation_references_validated=expected_valid,whole_independent_exposure_eligible=exposure_valid,
        caller_label_review_declared=reviewed,fixture_reference_check_executed=checked)
    output={'schema_version':1,'kind':'fcc_case_review_reference_check','execution_mode':'fixture_reference_check',
        'status':'checked' if checked else 'insufficient_evidence','reason_codes':sorted(reasons),
        'synthetic':context['synthetic'] if context_valid else None,'bindings':{'split_sha256':_hash(split),
        'split_input_fingerprint':split['input_fingerprint'] if split_valid else None,'context_sha256':_hash(context),
        'context_id':context['context_id'] if context_valid else None,'corpus_id':context['corpus_id'] if context_valid else None,
        'response_sha256':_hash(response),'expectation_sha256':_hash(expectation),'expected_producer':producer},
        'exposure':exposure,'label_review_status':expectation['label_review_status'],'score':score,'actual_model_score':None,
        'counts':counts,'reference_differences':differences,'verification':verification,'limits':dict(_LIMITS)}
    return _clone(output,'input_invalid',4*_MIB,16,[0])

"""Pure, bounded grouping of provided FCC case metadata; no model evaluation."""
import hashlib
import json
import math
import re
import unicodedata


_ALGORITHM='namespaced_connected_components_v1'
_INPUT_LIMIT,_OUTPUT_LIMIT=4*1024*1024,16*1024*1024
_MAX_CASES,_MAX_ARRAY=4096,64
_FIELDS={'case_id','product_family_group_id','fcc_ids','report_group_id','original_sha256s','reuse_group_ids',
         'group_review_status','unresolved_relations'}
_ID=re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z')
_SHA=re.compile(r'[0-9a-f]{64}\Z')
_NAMESPACES=('product_family_group_ids','fcc_ids','report_group_ids','original_sha256s','reuse_group_ids')


class _Reject(Exception):
    pass


def _reject(code):raise _Reject(code)


def _encoded(value):
    try:return json.dumps(value,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(',',':')).encode('utf-8')
    except (ValueError,TypeError,UnicodeError,OverflowError,RecursionError):_reject('input_invalid')


def _bounded(value,limit,depth_limit):
    size=0
    def consume(amount):
        nonlocal size
        size+=amount
        if size>limit:_reject('budget_exceeded')
    def scalar(item):
        if type(item) is str and len(item)>limit-size:_reject('budget_exceeded')
        consume(len(_encoded(item)))
        return item
    def walk(item,depth=0):
        if depth>depth_limit:_reject('budget_exceeded')
        if type(item) is dict:
            consume(2);result={}
            for index,(key,child) in enumerate(item.items()):
                if type(key) is not str:_reject('input_invalid')
                if index:consume(1)
                scalar(key);consume(1);result[key]=walk(child,depth+1)
            return result
        if type(item) is list:
            consume(2);result=[]
            for index,child in enumerate(item):
                if index:consume(1)
                result.append(walk(child,depth+1))
            return result
        if item is None or type(item) in (str,bool,int):return scalar(item)
        if type(item) is float and math.isfinite(item):return scalar(item)
        _reject('input_invalid')
    encoded=_encoded(walk(value))
    if len(encoded)>limit:_reject('budget_exceeded')
    return json.loads(encoded)


def _case_id(value,code='input_invalid'):
    if type(value) is not str or not _ID.fullmatch(value):_reject(code)
    return value


def _group_id(value,*,fcc=False):
    if type(value) is not str or not 1<=len(value)<=128 or len(value.encode('utf-8'))>512:_reject('input_invalid')
    normalized=value.strip().upper() if fcc else value.strip().casefold()
    if (not 1<=len(normalized)<=128 or len(normalized.encode('utf-8'))>512
            or any(unicodedata.category(character) in {'Cc','Cs'} for character in normalized)):_reject('input_invalid')
    return normalized


def _array(value,*,sha=False,fcc=False):
    if type(value) is not list:_reject('input_invalid')
    if len(value)>_MAX_ARRAY:_reject('budget_exceeded')
    result=[]
    for item in value:
        if sha:
            if type(item) is not str or not _SHA.fullmatch(item):_reject('input_invalid')
            result.append(item)
        else:result.append(_group_id(item,fcc=fcc))
    if len(set(result))!=len(result):_reject('input_invalid')
    return sorted(result)


def _case(value):
    if type(value) is not dict or set(value)!=_FIELDS:_reject('input_invalid')
    result={'case_id':_case_id(value['case_id'])}
    for key in ('product_family_group_id','report_group_id'):
        result[key]=None if value[key] is None else _group_id(value[key])
    for key in ('fcc_ids','original_sha256s','reuse_group_ids','unresolved_relations'):
        result[key]=_array(value[key],sha=key=='original_sha256s',fcc=key=='fcc_ids')
    if type(value['group_review_status']) is not str or value['group_review_status'] not in {'reviewed','pending'}:_reject('input_invalid')
    result['group_review_status']=value['group_review_status']
    return result


def _selection(value):
    if type(value) is not list:_reject('selection_invalid')
    if len(value)>_MAX_CASES:_reject('budget_exceeded')
    result=[_case_id(item,'selection_invalid') for item in value]
    if len(set(result))!=len(result):_reject('duplicate_selection')
    return sorted(result)


def _keys(case):
    return {'product_family_group_ids':[] if case['product_family_group_id'] is None else [case['product_family_group_id']],
        'fcc_ids':case['fcc_ids'],'report_group_ids':[] if case['report_group_id'] is None else [case['report_group_id']],
        'original_sha256s':case['original_sha256s'],'reuse_group_ids':case['reuse_group_ids']}


def _issues(case):
    reasons=[]
    for field,reason in [('product_family_group_id','missing_product_family_group'),('report_group_id','missing_report_group'),
                         ('fcc_ids','missing_fcc_id'),('original_sha256s','missing_source_sha256')]:
        if not case[field]:reasons.append(reason)
    if case['group_review_status']=='pending':reasons.append('group_review_pending')
    if case['unresolved_relations']:reasons.append('unresolved_relations')
    return sorted(reasons)


def build_case_evaluation_split(cases,*,development_case_ids,independent_case_ids):
    """Group all provided cases before validating complete, disjoint assignments."""
    try:return _build(cases,development_case_ids,independent_case_ids)
    except _Reject as error:raise ValueError('fcc_case_evaluation_'+str(error)) from None


def _build(cases,development_case_ids,independent_case_ids):
    if type(cases) is not list:_reject('input_invalid')
    if len(cases)>_MAX_CASES:_reject('budget_exceeded')
    development,independent=_selection(development_case_ids),_selection(independent_case_ids)
    payload={'schema_version':1,'algorithm':_ALGORITHM,'cases':cases,
        'development_case_ids':development,'independent_case_ids':independent}
    copied=_bounded(payload,_INPUT_LIMIT,8)
    canonical=sorted((_case(case) for case in copied['cases']),key=lambda case:case['case_id'])
    identities=[case['case_id'] for case in canonical]
    if len(set(identities))!=len(identities):_reject('duplicate_case_id')
    known=set(identities)
    if (set(development)|set(independent))-known:_reject('unknown_case_id')
    if set(development)&set(independent):_reject('overlapping_selection')
    payload['cases']=canonical
    payload['development_case_ids'],payload['independent_case_ids']=development,independent
    normalized=_bounded(payload,_INPUT_LIMIT,8)
    fingerprint=hashlib.sha256(_encoded(normalized)).hexdigest()

    parent=list(range(len(canonical)))
    def find(index):
        while parent[index]!=index:
            parent[index]=parent[parent[index]];index=parent[index]
        return index
    def union(left,right):
        left,right=find(left),find(right)
        if left!=right:parent[max(left,right)]=min(left,right)
    first={}
    for index,case in enumerate(canonical):
        for namespace,values in _keys(case).items():
            for value in values:
                key=(namespace,value)
                if key in first:union(index,first[key])
                else:first[key]=index
    members={}
    for index,case in enumerate(canonical):members.setdefault(find(index),[]).append(case)
    components=[]
    by_case={}
    direct={case['case_id']:_issues(case) for case in canonical}
    for group_cases in members.values():
        ids=[case['case_id'] for case in group_cases]
        key_sets={namespace:set() for namespace in _NAMESPACES}
        for case in group_cases:
            for namespace,values in _keys(case).items():key_sets[namespace].update(values)
        keys={namespace:sorted(values) for namespace,values in key_sets.items()}
        group_hash=hashlib.sha256(_encoded({'schema_version':1,'case_ids':ids,'keys':keys})).hexdigest()
        reasons=sorted({reason for identity in ids for reason in direct[identity]})
        component={'group_id':'case-group:'+group_hash,'group_sha256':group_hash,'case_ids':ids,'keys':keys,
            'eligible':not reasons,'ineligibility_reasons':reasons,'ineligible_case_ids':[identity for identity in ids if direct[identity]]}
        components.append(component)
        for identity in ids:by_case[identity]=component
    components.sort(key=lambda component:component['group_id'])

    dev,ind=set(development),set(independent)
    groups=[(component,set(component['case_ids'])) for component in components]
    if any(ids&dev and ids&ind for _,ids in groups):_reject('cross_split_component')
    if any(ids&(dev|ind) and not ids<=(dev|ind) for _,ids in groups):_reject('partial_component')
    if any(ids&(dev|ind) and not component['eligible'] for component,ids in groups):_reject('ineligible_component')
    splits={name:{'case_ids':[],'group_ids':[]} for name in ('development','independent','unassigned')}
    for component,ids in groups:
        split=splits['development' if ids&dev else 'independent' if ids&ind else 'unassigned']
        split['case_ids'].extend(component['case_ids']);split['group_ids'].append(component['group_id'])
    for split in splits.values():
        split['case_ids'].sort();split['group_ids'].sort()
    rows=[{**case,'group_id':by_case[case['case_id']]['group_id'],'eligible':by_case[case['case_id']]['eligible'],
        'case_ineligibility_reasons':direct[case['case_id']],
        'component_ineligibility_reasons':by_case[case['case_id']]['ineligibility_reasons']} for case in canonical]
    eligible_components=sum(component['eligible'] for component in components)
    eligible_cases=sum(case['eligible'] for case in rows)
    denominators={'provided_cases':len(rows),'provided_components':len(components),'eligible_cases':eligible_cases,
        'ineligible_cases':len(rows)-eligible_cases,'eligible_components':eligible_components,
        'ineligible_components':len(components)-eligible_components,'development_cases':len(development),
        'independent_cases':len(independent),'unassigned_cases':len(splits['unassigned']['case_ids'])}
    result={'schema_version':1,'kind':'fcc_case_evaluation_split','algorithm':_ALGORITHM,'status':'configured',
        'input_fingerprint':fingerprint,'scope':'provided_metadata_only','fact_review_verified':False,
        'model_execution_verified':False,'training_executed':False,'evaluation_executed':False,'hardware_verified':False,
        'independent_assignment_status':'assigned' if independent else 'not_assigned','case_count':len(rows),'component_count':len(components),
        'eligible_component_count':eligible_components,'ineligible_component_count':len(components)-eligible_components,
        'denominators':denominators,'cases':rows,'components':components,**splits}
    return _bounded(result,_OUTPUT_LIMIT,12)

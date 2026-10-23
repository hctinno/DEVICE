"""Common workflow; method applicability and technical reviews are explicit inputs."""
from datetime import datetime
import hashlib
import json
import sqlite3

from .calculations import calculate, number
from .store import canonical, identifier

SCOPES={f'F{i:02d}' for i in range(1,21)}
CALCULATORS={'emc_field_strength':'dBuV/m','rf_power':'W'}


def _mapping(value,label):
    if not isinstance(value,dict):raise ValueError(label+' must be an object')


def _text(value,label):
    if not isinstance(value,str) or not value.strip():raise ValueError(label+' is required')
    return value


def _ids(value,label,allow_empty=False):
    if not isinstance(value,list) or (not value and not allow_empty):raise ValueError(label+' must be a list of IDs')
    for item in value:identifier(item)
    if len(set(value))!=len(value):raise ValueError('Duplicate '+label)
    return value


def _insert(store,table,key,data,extra):
    identifier(data[key]);serialized=canonical(data)
    with store.connection() as con:
        old=con.execute(f'SELECT data_json FROM {table} WHERE {key}=?',(data[key],)).fetchone()
        if old:
            if old[0]!=serialized:raise ValueError('Existing ID is immutable; use a new revision ID')
            return store.row(table,data[key])['data']
        columns=[key,'data_json',*extra]
        try:con.execute(f'INSERT INTO {table}({",".join(columns)}) VALUES({",".join("?" for _ in columns)})',[data[key],serialized,*extra.values()])
        except sqlite3.IntegrityError as exc:raise ValueError('Invalid relationship or duplicate ID') from exc
        store.event(con,table+'.create',data[key],{'data_sha256':hashlib.sha256(serialized.encode()).hexdigest()})
    return data


def create_case(store,data):
    _mapping(data,'case')
    if data.get('authorization_route') not in {'certification','sdoc','mixed','undetermined'}:raise ValueError('Unknown authorization route')
    _mapping(data.get('product'),'product')
    for key in ['manufacturer','model']:_text(data['product'].get(key),key)
    scopes=_ids(data.get('scope_ids'),'scope_ids')
    if not set(scopes)<=SCOPES:raise ValueError('Unsupported scope identifier')
    if not isinstance(data.get('synthetic'),bool):raise ValueError('Declare synthetic true or false explicitly')
    return _insert(store,'cases','case_id',data,{'synthetic':int(data['synthetic'])})


def register_method(store,data):
    _mapping(data,'method')
    if data.get('scope_id') not in SCOPES:raise ValueError('Unsupported scope identifier')
    if data.get('calculator') not in CALCULATORS:raise ValueError('Unsupported calculator')
    sources=_ids(data.get('source_document_ids'),'source_document_ids')
    limit=data.get('limit');_mapping(limit,'limit');number(limit.get('value'))
    if limit.get('operator') not in {'<=','>='}:raise ValueError('Only explicit upper/lower inclusive limits are supported')
    if limit.get('unit')!=CALCULATORS[data['calculator']]:raise ValueError('Limit unit does not match calculator output')
    if limit.get('source_document_id') not in sources:raise ValueError('Limit must reference a method source document')
    _text(limit.get('clause'),'limit clause')
    return _insert(store,'methods','method_id',data,{})


def add_plan(store,case_id,data):
    _mapping(data,'plan');case=store.row('cases',case_id)['data'];method=store.row('methods',data.get('method_id'))['data']
    if method['scope_id'] not in case['scope_ids']:raise ValueError('Method scope is outside this case')
    if data.get('applicability') not in {'applicable','not_applicable','undetermined'}:raise ValueError('Applicability is required')
    _mapping(data.get('configuration'),'configuration');_text(data.get('rationale'),'applicability rationale')
    if data['applicability']=='applicable' and not data['configuration']:raise ValueError('Test configuration is required')
    if 'case_id' in data and data['case_id']!=case_id:raise ValueError('Cross-case plan')
    return _insert(store,'plans','plan_id',{**data,'case_id':case_id},{'case_id':case_id,'method_id':data['method_id']})


def _time(value):
    try:
        result=datetime.fromisoformat(value.replace('Z','+00:00'))
        if result.tzinfo is None:raise ValueError('Timezone is required')
        return result
    except (AttributeError,TypeError,ValueError) as exc:raise ValueError('Invalid timezone-aware timestamp') from exc


def record_run(store,plan_id,data,raw_path=None):
    _mapping(data,'run');plan=store.row('plans',plan_id)
    if plan['data']['applicability']!='applicable':raise ValueError('Only applicable plan items can run')
    if data.get('case_id')!=plan['case_id']:raise ValueError('Cross-case run')
    if data.get('execution_status') not in {'completed','aborted','error'}:raise ValueError('Record a finished attempt, including failures')
    if _time(data.get('ended_at'))<_time(data.get('started_at')):raise ValueError('Run ends before it starts')
    for key in ['settings','environment']:_mapping(data.get(key),key)
    for key in ['equipment_ids','setup_artifact_ids','calibration_artifact_ids']:_ids(data.get(key),key,allow_empty=True)
    for sha in data['setup_artifact_ids']+data['calibration_artifact_ids']:store.verify_blob(sha)
    raw_sha=store.import_artifact(raw_path,'raw') if raw_path is not None else None
    # The raw hash is part of the immutable run record, so retry cannot replace raw bytes.
    record={**data,'plan_id':plan_id,'raw_sha256':raw_sha}
    return _insert(store,'runs','run_id',record,{'plan_id':plan_id,'raw_sha256':raw_sha})


def _source_state(store,method):
    blockers=[];sources=[]
    for source_id in method['source_document_ids']:
        try:
            doc=store.document(source_id);sources.append(doc)
            if doc['status']!='downloaded' or doc['representation']!='original':blockers.append('source_original_missing:'+source_id)
            elif doc['rights'] not in {'public','licensed_internal'}:blockers.append('source_rights_unconfirmed:'+source_id)
            if doc['review_status']!='reviewed':blockers.append('source_unreviewed:'+source_id)
            if doc['sha256']:
                try:store.verify_blob(doc['sha256'])
                except ValueError:blockers.append('source_corrupt:'+source_id)
        except ValueError:blockers.append('source_missing:'+source_id)
    return blockers,sources


def _review(store,table,key,reviewer,note):
    _text(reviewer,'reviewer');_text(note,'review note')
    id_column={'methods':'method_id','runs':'run_id'}[table]
    with store.connection() as con:
        con.execute(f"UPDATE {table} SET review_status='reviewed' WHERE {id_column}=?",(key,))
        store.event(con,table+'.review',key,{'reviewer':reviewer,'note':note})
    return {'id':key,'review_status':'reviewed'}


def review_method(store,method_id,reviewer,note):
    method=store.row('methods',method_id)['data'];blockers,_=_source_state(store,method)
    if blockers:raise ValueError('Method sources are not ready: '+', '.join(blockers))
    return _review(store,'methods',method_id,reviewer,note)


def _run_blockers(store,run):
    data=run['data'];blockers=[]
    if data['execution_status']!='completed':blockers.append('execution_not_completed')
    for field in ['settings','environment','equipment_ids','setup_artifact_ids','calibration_artifact_ids']:
        if not data[field]:blockers.append('evidence_missing:'+field)
    for sha in data['setup_artifact_ids']+data['calibration_artifact_ids']:
        try:store.verify_blob(sha)
        except ValueError:blockers.append('evidence_corrupt:'+sha)
    if not run['raw_sha256']:blockers.append('raw_missing')
    else:
        try:store.verify_blob(run['raw_sha256'])
        except ValueError:blockers.append('raw_corrupt')
    return blockers


def review_run(store,run_id,reviewer,note):
    run=store.row('runs',run_id);blockers=_run_blockers(store,run)
    if blockers:raise ValueError('Run evidence not ready: '+', '.join(blockers))
    return _review(store,'runs',run_id,reviewer,note)


def _invalid_number(value):
    raise ValueError('JSON contains nonfinite numeric literal: '+value)


def evaluate(store,run_id):
    run=store.row('runs',run_id);plan=store.row('plans',run['plan_id']);case=store.row('cases',plan['case_id'])
    method=store.row('methods',plan['method_id']);profile=method['data']
    blockers,sources=_source_state(store,profile)
    if method['review_status']!='reviewed':blockers.append('method_unreviewed')
    if run['review_status']!='reviewed':blockers.append('run_unreviewed')
    blockers+=_run_blockers(store,run)
    if case['data']['authorization_route']=='undetermined':blockers.append('authorization_route_undetermined')
    synthetic=bool(case['synthetic']) or any(d['synthetic'] for d in sources)
    if synthetic and not case['synthetic']:blockers.append('synthetic_source_in_real_case')
    calculations=[];limit=profile['limit']
    if run['raw_sha256'] and 'raw_corrupt' not in blockers:
        try:
            raw=json.loads(store.verify_blob(run['raw_sha256']).read_text(),parse_constant=_invalid_number)
            observations=raw.get('observations',[raw]) if isinstance(raw,dict) else None
            if not isinstance(observations,list) or not observations:raise ValueError('No observations')
            for index,observation in enumerate(observations):
                computed=calculate(profile['calculator'],observation)
                if computed['unit']!=limit['unit']:raise ValueError('Result and limit unit mismatch')
                margin=(number(limit['value'])-computed['value']) if limit['operator']=='<=' else (computed['value']-number(limit['value']))
                calculations.append({**computed,'index':index,'source_locator':f'/observations/{index}' if 'observations' in raw else '/',
                    'margin':number(margin),'within_limit':margin>=0})
        except (ValueError,UnicodeError,TypeError,KeyError) as exc:blockers.append('invalid_measurement:'+str(exc))
    if not calculations:blockers.append('no_valid_calculations')
    blockers=sorted(set(blockers))
    decision='blocked' if blockers else ('pass' if all(c['within_limit'] for c in calculations) else 'fail')
    if synthetic and decision!='blocked':decision='simulated_'+decision
    result={'run_id':run_id,'case_id':plan['case_id'],'plan_id':run['plan_id'],'method_id':plan['method_id'],
            'raw_sha256':run['raw_sha256'],'synthetic':synthetic,'decision':decision,'blockers':blockers,
            'calculations':calculations,'limit':limit,'source_document_ids':profile['source_document_ids'],
            'official_release_available':False}
    serialized=canonical(result);fingerprint=hashlib.sha256(serialized.encode()).hexdigest()
    with store.connection() as con:
        cursor=con.execute('INSERT OR IGNORE INTO evaluations(run_id,fingerprint,data_json) VALUES(?,?,?)',(run_id,fingerprint,serialized))
        if cursor.rowcount:store.event(con,'run.evaluate',run_id,{'fingerprint':fingerprint,'decision':decision})
    return result


def case_status(store,case_id):
    case=store.row('cases',case_id)
    with store.connection() as con:
        plans=[dict(r) for r in con.execute('SELECT * FROM plans WHERE case_id=? ORDER BY rowid',(case_id,))]
        runs=[dict(r) for r in con.execute('SELECT r.* FROM runs r JOIN plans p USING(plan_id) WHERE p.case_id=? ORDER BY r.rowid',(case_id,))]
    blockers=['scope_completeness_unreviewed'];results=[]
    if not plans:blockers.append('no_test_plan')
    if case['data']['authorization_route']=='undetermined':blockers.append('authorization_route_undetermined')
    for plan in plans:
        data=json.loads(plan['data_json']);attempts=[r for r in runs if r['plan_id']==plan['plan_id']]
        if data['applicability']!='applicable':blockers.append('applicability_review_required:'+plan['plan_id'])
        elif not attempts:blockers.append('run_missing:'+plan['plan_id'])
        else:
            result=evaluate(store,attempts[-1]['run_id']);results.append(result)
            blockers.extend(result['blockers'])
    return {'case_id':case_id,'case':case['data'],'plans':[json.loads(p['data_json']) for p in plans],
            'runs':[json.loads(r['data_json']) for r in runs],'results':results,
            'blockers':sorted(set(blockers)),'workflow_status':'draft_report_available',
            'official_release_available':False,'hardware_connected':False,
            'regulatory_scope_complete':False,'synthetic':bool(case['synthetic']) or any(r['synthetic'] for r in results)}

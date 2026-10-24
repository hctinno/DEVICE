"""Observe retained intake state in one read transaction, without execution authority."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import re
import sqlite3

from .store import Store
from .intake_analysis import FIELDS,validate_analysis,project_analysis
from .intake_documents import current_extraction_profile_id
from .intake_generation import validate_retained_analysis


_MIB=1024*1024
_LIMITS={'result_json_bytes':8*_MIB,'analysis_context_bytes':4*_MIB,'raw_manifest_bytes':4*_MIB,
    'source_file_bytes':16*_MIB,'projection_json_bytes':8*_MIB,'state_category_json_bytes':8*_MIB,
    'max_questions':10000,'max_user_response_events':10000,'max_answers':len(FIELDS),
    'snapshot_json_bytes':9*_MIB,'capture_json_bytes':12*_MIB}
_CODES={'invalid_argument','store_invalid','transaction_required','intake_not_found','input_limit',
    'source_integrity_invalid','projection_inconsistent','delegation_invalid','storage_error'}
REASON_CODES=frozenset({'analysis_not_completed','legacy_analysis','no_pdf_context','expected_revision_changed',
    'expected_result_changed','analysis_not_ready','profile_changed','delegation_missing','intake_deferred',
    'delegation_evidence_missing','required_questions_open','unread_documents','source_provenance_unconfirmed','preparation_not_ready'})
_ID=re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,149}\Z',re.ASCII)
_SHA=re.compile(r'[0-9a-f]{64}\Z',re.ASCII)


class IntakeReferenceStateError(ValueError):
    def __init__(self,code):
        suffix=code.removeprefix('intake_reference_state_') if type(code) is str else 'storage_error'
        self.code='intake_reference_state_'+(suffix if suffix in _CODES else 'storage_error')
        super().__init__(self.code)


def _fail(code):raise IntakeReferenceStateError(code)
def _encoded(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def _hash(value):return hashlib.sha256(_encoded(value)).hexdigest()
def _same(a,b):return _encoded(a)==_encoded(b)
def _bounded(value,limit,code):
    try:raw=_encoded(value)
    except (ValueError,TypeError,UnicodeError,OverflowError,RecursionError):_fail(code)
    if len(raw)>limit:_fail('input_limit')
    return raw
def _pairs(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError()
        result[key]=value
    return result
def _json(raw,limit,code):
    if type(raw) is not str:_fail(code)
    try:
        if len(raw.encode('utf-8'))>limit:_fail('input_limit')
        def constant(_):raise ValueError()
        result=json.loads(raw,object_pairs_hook=_pairs,parse_constant=constant)
    except IntakeReferenceStateError:raise
    except (ValueError,TypeError,UnicodeError,OverflowError,RecursionError):_fail(code)
    _bounded(result,limit,code)
    return result
def _keys(value,keys,code):
    if type(value) is not dict or set(value)!=set(keys):_fail(code)
def _identifier(value,code='invalid_argument',maximum=150):
    if type(value) is not str or not _ID.fullmatch(value) or len(value)>maximum:_fail(code)
def _sha(value,code):
    if type(value) is not str or not _SHA.fullmatch(value):_fail(code)
def _current_profile():
    try:value=current_extraction_profile_id()
    except (OSError,ValueError,RuntimeError):_fail('source_integrity_invalid')
    _sha(value,'source_integrity_invalid')
    return value
def _positive(value,code):
    if type(value) is not int or value<1:_fail(code)
def _flag(value,code):
    if type(value) is not int or value not in (0,1):_fail(code)
def _text(value,code):
    if type(value) is not str or not value.strip() or len(value)>4000:_fail(code)


def _arguments(store,intake_id,revision,result_sha):
    if type(store) is not Store:_fail('store_invalid')
    _identifier(intake_id)
    if (revision is None)!=(result_sha is None):_fail('invalid_argument')
    if revision is not None:_positive(revision,'invalid_argument');_sha(result_sha,'invalid_argument')
def _db(store):
    if not isinstance(store.db,Path):_fail('store_invalid')
    try:
        path=store.db.resolve(strict=True)
        if not path.is_file():_fail('storage_error')
        return path
    except OSError:_fail('storage_error')
def _db_identity(path):
    try:
        stat=path.stat()
        return stat.st_dev,stat.st_ino
    except OSError:_fail('storage_error')
def _select(con,sql,args=()):
    cursor=con.cursor()
    try:
        cursor.row_factory=sqlite3.Row
        cursor.execute(sql,args)
        return [dict(row) for row in cursor.fetchall()]
    finally:cursor.close()
def _one(con,sql,args=()):
    values=_select(con,sql,args)
    return values[0] if values else None


def _rows(con,table,columns,where,args,maximum,code):
    # Names and predicates are module constants, never caller SQL.
    measure='+'.join('coalesce(length(CAST('+name+' AS BLOB)),0)' for name in columns)
    size=_one(con,'SELECT count(*) AS n,coalesce(sum('+measure+'),0) AS bytes FROM '+table+' WHERE '+where,args)
    if size['n']>maximum or size['bytes']>8*_MIB:_fail('input_limit')
    rows=_select(con,'SELECT '+','.join(columns)+' FROM '+table+' WHERE '+where+' ORDER BY '+columns[0],args)
    _bounded(rows,8*_MIB,code)
    return rows


def _origin(con,intake_id):
    row=_one(con,"""SELECT i.intake_id,i.source_id,i.revision,i.status AS intake_status,i.delegated,i.deferred,
        s.synthetic AS source_synthetic,r.synthetic,r.fingerprint,j.job_id,j.state,
        length(CAST(r.files_json AS BLOB)) AS manifest_bytes,
        CASE WHEN typeof(r.files_json)='text' AND length(CAST(r.files_json AS BLOB))<=4194304 THEN r.files_json END AS files_json,
        length(CAST(j.result_json AS BLOB)) AS result_bytes,
        CASE WHEN typeof(j.result_json)='text' AND length(CAST(j.result_json AS BLOB))<=8388608 THEN j.result_json END AS result_json,
        length(CAST(i.analysis_json AS BLOB)) AS projection_bytes,
        CASE WHEN typeof(i.analysis_json)='text' AND length(CAST(i.analysis_json AS BLOB))<=8388608 THEN i.analysis_json END AS analysis_json
        FROM intakes i LEFT JOIN intake_revisions r ON r.intake_id=i.intake_id AND r.revision=i.revision
        LEFT JOIN intake_jobs j ON j.intake_id=i.intake_id AND j.revision=i.revision
        LEFT JOIN intake_sources s ON s.source_id=i.source_id WHERE i.intake_id=?""",(intake_id,))
    if row is None:_fail('intake_not_found')
    for key,ceiling in [('manifest_bytes',4*_MIB),('result_bytes',8*_MIB),('projection_bytes',8*_MIB)]:
        if row[key] is not None and row[key]>ceiling:_fail('input_limit')
    return row


def _blob(store,sha,limit):
    _sha(sha,'source_integrity_invalid')
    try:
        path=store.blob_path(sha);before=path.stat()
        if before.st_size>limit:_fail('input_limit')
        with path.open('rb') as stream:raw=stream.read(limit+1)
        after=path.stat()
    except IntakeReferenceStateError:raise
    except (OSError,ValueError):_fail('source_integrity_invalid')
    if len(raw)>limit:_fail('input_limit')
    fields=lambda s:(s.st_size,s.st_mtime_ns,s.st_mode,s.st_dev,s.st_ino)
    if fields(before)!=fields(after) or hashlib.sha256(raw).hexdigest()!=sha:_fail('source_integrity_invalid')
    return raw,fields(after)


def _graph(store,row,analysis):
    code='source_integrity_invalid';files=_json(row['files_json'],4*_MIB,code)
    if type(files) is not list or _hash(files)!=row['fingerprint']:_fail(code)
    context_id=analysis.get('context_id');raw,meta=_blob(store,context_id,4*_MIB)
    try:context=_json(raw.decode('utf-8'),4*_MIB,code)
    except UnicodeError:_fail(code)
    _keys(context,{'schema_version','binding','profile','extraction_profile_id','documents'},code)
    if type(context['documents']) is not list:_fail(code)
    limits={context_id:4*_MIB};initial={context_id:meta}
    for item in files:
        _keys(item,{'path','sha256','bytes'},code);_sha(item['sha256'],code)
        if type(item['bytes']) is not int or item['bytes']<0:_fail(code)
        if item['bytes']>16*_MIB:_fail('input_limit')
        limits[item['sha256']]=min(limits.get(item['sha256'],16*_MIB),16*_MIB)
    for document in context['documents']:
        if type(document) is not dict:_fail(code)
        if document.get('format')=='pdf':
            sha=document.get('extraction_id');_sha(sha,code);limits[sha]=min(limits.get(sha,4*_MIB),4*_MIB)
    for sha,limit in limits.items():
        if sha not in initial:_,initial[sha]=_blob(store,sha,limit)
        elif initial[sha][0]>limit:_fail('input_limit')
    if any(initial[item['sha256']][0]!=item['bytes'] for item in files):_fail(code)
    return files,context,limits,initial


def _provenance(con,row,graph):
    _flag(row['synthetic'],'source_integrity_invalid');_flag(row['source_synthetic'],'source_integrity_invalid')
    values=[]
    for sha,meta in sorted(graph.items()):
        value=_one(con,'SELECT sha256,bytes,kind,synthetic FROM blobs WHERE sha256=?',(sha,))
        if value is None or type(value['bytes']) is not int or value['bytes']!=meta[0] or type(value['kind']) is not str:_fail('source_integrity_invalid')
        _flag(value['synthetic'],'source_integrity_invalid');values.append(value)
    consistent=row['source_synthetic']==row['synthetic'] and all(v['synthetic']==row['synthetic'] for v in values)
    return {'source_synthetic':row['source_synthetic'],'revision_synthetic':row['synthetic'],'blobs':values},consistent


def _events(con,intake_id,row,answers):
    code='delegation_invalid'
    join="""events e LEFT JOIN intake_responses r ON r.event_id=
        CASE WHEN json_valid(e.details_json) THEN json_extract(e.details_json,'$.event_id') END"""
    where="e.action='intake.user_response' AND e.subject_id=?"
    columns=['e.event_id','e.created_at','e.action','e.subject_id','e.details_json','r.event_id AS response_id','r.request_json','r.result_json']
    size=_one(con,"SELECT count(*) AS n,coalesce(sum(coalesce(length(CAST(e.details_json AS BLOB)),0)+coalesce(length(CAST(e.created_at AS BLOB)),0)+coalesce(length(CAST(r.request_json AS BLOB)),0)+coalesce(length(CAST(r.result_json AS BLOB)),0)),0) AS bytes FROM "+join+' WHERE '+where,(intake_id,))
    if size['n']>10000 or size['bytes']>8*_MIB:_fail('input_limit')
    events=_select(con,'SELECT '+','.join(columns)+' FROM '+join+' WHERE '+where+' ORDER BY e.event_id',(intake_id,))
    _bounded(events,8*_MIB,code);proofs={};latest_answers={};delegated=deferred=0;latest=None;active=None
    for event in events:
        _positive(event['event_id'],code)
        details=_json(event['details_json'],8*_MIB,code);_keys(details,{'event_id','action'},code);_identifier(details['event_id'],code)
        if details['event_id'] in proofs or event['response_id']!=details['event_id']:_fail(code)
        request=_json(event['request_json'],8*_MIB,code);result=_json(event['result_json'],8*_MIB,code)
        _keys(request,{'action','intake_id','answers'},code);_keys(result,{'status','intake_id','action','next_action'},code)
        action=details['action']
        if (type(action) is not str or action not in {'proceed','defer','answer'} or request['action']!=action or result['action']!=action
                or request['intake_id'] not in (None,intake_id) or result['intake_id']!=intake_id or result['status']!='recorded'
                or result['next_action'] not in {'awaiting_analysis','prepare_plan','needs_information','deferred','propose_start'}):_fail(code)
        if action=='answer':
            if type(request['answers']) is not dict or not request['answers'] or set(request['answers'])-set(FIELDS):_fail(code)
            for field,value in request['answers'].items():
                _text(value,code);latest_answers[field]=(details['event_id'],value.strip())
        elif request['answers'] is not None:_fail(code)
        if action=='proceed':delegated=1;deferred=0;latest=details['event_id'];active=latest
        elif action=='defer':deferred=1;latest=details['event_id'];active=None
        proofs[details['event_id']]=request
    if delegated!=row['delegated'] or deferred!=row['deferred']:_fail(code)
    for answer in answers:
        if answer['field'] not in FIELDS:_fail(code)
        _text(answer['value'],code);_identifier(answer['event_id'],code)
        basis=_json(answer['basis_json'],8*_MIB,code);_keys(basis,{'identity','facts'},code)
        if basis['identity'] not in {'single','ambiguous','unknown'} or type(basis['facts']) is not list:_fail(code)
        for fact in basis['facts']:
            if type(fact) is not list or len(fact)!=3 or fact[0] not in FIELDS or fact[2] not in {'explicit','inferred','uncertain'}:_fail(code)
            _text(fact[1],code)
        if latest_answers.get(answer['field'])!=(answer['event_id'],answer['value']):_fail(code)
    if set(latest_answers)!={answer['field'] for answer in answers}:_fail(code)
    return {'event_id':latest,'history_sha256':_hash(events),'verified':latest is not None},active


def _unavailable(reason,current_profile):
    return {'schema_version':1,'kind':'intake_reference_snapshot_capture','status':'unavailable','reason_codes':[reason],
        'snapshot_id':None,'snapshot':None,'origin':{key:None for key in ['source_id','origin_job_id','result_sha256','analysis_context_id','raw_manifest_sha256']},
        'state':{key:None for key in ['intake_status','delegated','deferred','projection_sha256','answers_sha256','questions_sha256']},
        'delegation':{'event_id':None,'history_sha256':None,'verified':None},
        'profile':{'stored_profile_id':None,'current_profile_id':current_profile,'matches':None},
        'readiness':{'kind':'reference_preparation_v1','ready':False,'reason_codes':[reason],'reference_state_fingerprint':None,'delegation_event_id':None},
        'verification':{key:key=='database_snapshot_observed' for key in ['database_snapshot_observed','retained_analysis_verified','live_projection_recomputed','preparation_bound','source_integrity_observed','operational_authority_granted','model_execution_verified','evaluation_executed']},
        'limits':dict(_LIMITS)}


def _capture(store,con,intake_id,expected_revision,expected_sha):
    current_profile=_current_profile()
    row=_origin(con,intake_id)
    if row['state']!='completed':return _unavailable('analysis_not_completed',current_profile)
    for key in ['source_id','job_id']:_identifier(row[key],'source_integrity_invalid')
    _positive(row['revision'],'source_integrity_invalid');_sha(row['fingerprint'],'source_integrity_invalid')
    for key in ['delegated','deferred']:_flag(row[key],'delegation_invalid')
    result=_json(row['result_json'],8*_MIB,'source_integrity_invalid');_keys(result,{'submission','summary'},'source_integrity_invalid')
    analysis=result['submission']
    if type(analysis) is not dict or type(analysis.get('schema_version')) is not int:_fail('source_integrity_invalid')
    if analysis['schema_version']==1:
        try:status,reason,_,_=validate_retained_analysis(store,row)
        except (ValueError,TypeError,KeyError,OSError,RuntimeError):_fail('source_integrity_invalid')
        if status!='legacy_unbound':_fail('source_integrity_invalid')
        return _unavailable(reason,current_profile)
    files,context,graph_limits,graph=_graph(store,row,analysis)
    try:status,reason,context_id,stored_profile=validate_retained_analysis(store,row)
    except (ValueError,TypeError,KeyError,OSError,RuntimeError):_fail('source_integrity_invalid')
    if status=='legacy_unbound':return _unavailable(reason,current_profile)
    if status!='verified':_fail('source_integrity_invalid')
    provenance,provenance_ok=_provenance(con,row,graph)
    answers=_rows(con,'intake_answers',['field','intake_id','value','basis_json','event_id'],'intake_id=?',(intake_id,),len(FIELDS),'delegation_invalid')
    questions=_rows(con,'intake_questions',['question_key','intake_id','question_json','state','last_revision'],'intake_id=?',(intake_id,),10000,'projection_inconsistent')
    for question in questions:
        if type(question['question_key']) is not str or question['state'] not in {'open','resolved'}:_fail('projection_inconsistent')
        parsed=_json(question['question_json'],8*_MIB,'projection_inconsistent')
        if type(parsed) is not dict or parsed.get('key')!=question['question_key']:_fail('projection_inconsistent')
        _positive(question['last_revision'],'projection_inconsistent')
        if question['last_revision']>row['revision']:_fail('projection_inconsistent')
    delegation,active=_events(con,intake_id,row,answers)
    try:
        unread=validate_analysis(analysis,context['documents'],bool(row['synthetic']),context_id=context_id)
        projection=project_analysis(analysis,unread,{a['field']:a for a in answers},delegated=bool(row['delegated']),deferred=bool(row['deferred']),
            required_fields=[q['question_key'][8:] for q in questions if q['question_key'].startswith('missing_')])
    except (ValueError,TypeError,KeyError,RuntimeError):_fail('projection_inconsistent')
    projection.update(intake_id=intake_id,revision=row['revision'])
    live=_json(row['analysis_json'],8*_MIB,'projection_inconsistent')
    if not _same(live,projection):_fail('projection_inconsistent')
    for sha,limit in graph_limits.items():
        _,after=_blob(store,sha,limit)
        if after!=graph[sha]:_fail('source_integrity_invalid')
    profile={'stored_profile_id':stored_profile,'current_profile_id':current_profile,'matches':stored_profile==current_profile}
    state={'intake_status':row['intake_status'],'delegated':bool(row['delegated']),'deferred':bool(row['deferred']),
        'projection_sha256':_hash(projection),'answers_sha256':_hash(answers),'questions_sha256':_hash(questions)}
    origin={'source_id':row['source_id'],'origin_job_id':row['job_id'],'result_sha256':hashlib.sha256(row['result_json'].encode('utf-8')).hexdigest(),
        'analysis_context_id':context_id,'raw_manifest_sha256':hashlib.sha256(row['files_json'].encode('utf-8')).hexdigest()}
    reasons=set()
    if row['intake_status']!='analyzed':reasons.add('analysis_not_ready')
    if not profile['matches']:reasons.add('profile_changed')
    if not row['delegated']:reasons.add('delegation_missing')
    if row['deferred']:reasons.add('intake_deferred')
    if active is None and not row['deferred']:reasons.add('delegation_evidence_missing')
    if projection['questions']:reasons.add('required_questions_open')
    if unread:reasons.add('unread_documents')
    if not provenance_ok:reasons.add('source_provenance_unconfirmed')
    if projection['next_action']!='prepare_plan':reasons.add('preparation_not_ready')
    preparation={'schema_version':1,'kind':'reference_preparation_v1','intake_id':intake_id,'revision':row['revision'],
        'revision_fingerprint':row['fingerprint'],'origin':origin,'state':state,'delegation':delegation,'profile':profile,'provenance':provenance}
    readiness={'kind':'reference_preparation_v1','ready':not reasons,'reason_codes':sorted(reasons),
        'reference_state_fingerprint':_hash(preparation),'delegation_event_id':active}
    minimal={'facts':{k:v for k,v in projection['facts'].items() if k in {'product_type','market','model'}},'questions':[{'key':q['key']} for q in projection['questions']]}
    if len(minimal['questions'])>200:_fail('input_limit')
    for fact in minimal['facts'].values():
        if fact.get('status')=='user_confirmed':_identifier(fact.get('event_id'),'input_limit',128)
    private={'schema_version':1,'kind':'intake_case_reference_snapshot','snapshot_scope':'caller_provided','intake_id':intake_id,
        'revision':row['revision'],'revision_fingerprint':row['fingerprint'],'origin_job_id':row['job_id'],'analysis_context_id':context_id,
        'result_sha256':origin['result_sha256'],'readiness_fingerprint':readiness['reference_state_fingerprint'],'synthetic':bool(row['synthetic']),
        'projection':minimal,'projection_sha256':_hash(minimal)}
    _bounded(private,9*_MIB,'projection_inconsistent')
    stale=False
    if expected_revision is not None:
        if expected_revision!=row['revision']:reasons.add('expected_revision_changed');stale=True
        if expected_sha!=origin['result_sha256']:reasons.add('expected_result_changed');stale=True
    result={'schema_version':1,'kind':'intake_reference_snapshot_capture','status':'stale' if stale else 'observed','reason_codes':sorted(reasons),
        'snapshot':private,'origin':origin,'state':state,'delegation':delegation,'profile':profile,'readiness':readiness,
        'verification':{key:key not in {'operational_authority_granted','model_execution_verified','evaluation_executed'} for key in
            ['database_snapshot_observed','retained_analysis_verified','live_projection_recomputed','preparation_bound','source_integrity_observed','operational_authority_granted','model_execution_verified','evaluation_executed']},'limits':dict(_LIMITS)}
    result['snapshot_id']=_hash({key:result[key] for key in ['schema_version','kind','snapshot','origin','state','delegation','profile','readiness']})
    return result


def _in_transaction(store,con,intake_id,expected_revision,expected_sha,expected_identity=None):
    _arguments(store,intake_id,expected_revision,expected_sha)
    if type(con) is not sqlite3.Connection or not con.in_transaction:_fail('transaction_required')
    path=_db(store);identity=_db_identity(path)
    if expected_identity is not None and expected_identity!=identity:_fail('storage_error')
    database=_one(con,"SELECT file FROM pragma_database_list WHERE name='main'")
    if not database or not database['file']:_fail('transaction_required')
    try:matches=Path(database['file']).resolve(strict=True)==path
    except OSError:_fail('transaction_required')
    if not matches:_fail('transaction_required')
    result=_capture(store,con,intake_id,expected_revision,expected_sha)
    if _current_profile()!=result['profile']['current_profile_id']:_fail('source_integrity_invalid')
    if _db_identity(path)!=identity:_fail('storage_error')
    raw=_bounded(result,12*_MIB,'source_integrity_invalid')
    return json.loads(raw)


def capture_intake_reference_snapshot_in_transaction(store,con,intake_id,*,expected_revision=None,expected_result_sha256=None):
    """SELECT only in the caller's existing transaction; never changes ownership."""
    try:return _in_transaction(store,con,intake_id,expected_revision,expected_result_sha256)
    except IntakeReferenceStateError as error:code=error.code
    except Exception:code='storage_error'
    raise IntakeReferenceStateError(code) from None


def read_intake_reference_snapshot(store,intake_id,*,expected_revision=None,expected_result_sha256=None):
    """Open an existing live SQLite DB in mode=ro; never initializes a Store."""
    try:
        _arguments(store,intake_id,expected_revision,expected_result_sha256);path=_db(store);identity=_db_identity(path)
        with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=30)) as con:
            con.execute('BEGIN')
            return _in_transaction(store,con,intake_id,expected_revision,expected_result_sha256,identity)
    except IntakeReferenceStateError as error:code=error.code
    except Exception:code='storage_error'
    raise IntakeReferenceStateError(code) from None

"""Explicit immutable reference publication and fresh, separate current observation."""
from contextlib import contextmanager
from datetime import datetime,timezone,timedelta
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3

from .store import Store
from .fcc_report_cases import FccReportCaseCatalog
from .intake_case_references import build_intake_case_reference_receipt,IntakeCaseReferencesError
from .intake_reference_snapshot import capture_intake_reference_snapshot_in_transaction,IntakeReferenceStateError,REASON_CODES
from .intake_generation import validate_retained_analysis


_MIB=1024*1024
_LIMITS={'input_json_bytes':20*_MIB,'snapshot_json_bytes':9*_MIB,'receipt_json_bytes':2*_MIB,
    'append_observation_json_bytes':65536,'stored_payload_json_bytes':12*_MIB,'record_summary_json_bytes':4096,
    'history_summary_bytes':_MIB,'max_history_records':100,'max_input_nodes':1000000,'max_input_depth':28,
    'sqlite_busy_timeout_seconds':30}
_CODES={'invalid_argument','store_invalid','intake_not_found','input_limit','parent_invalid','origin_invalid',
    'schema_mismatch','request_conflict','integrity_invalid','storage_error'}
_STATUS={'current_at_append','historical_provided','preparation_unverified','head_conflict','reference_unbound'}
_ID=re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,149}\Z',re.ASCII)
_SHA=re.compile(r'[0-9a-f]{64}\Z',re.ASCII)
_MAXINT=2**63-1
_R='intake_reference_records';_H='intake_reference_heads';_E='intake_reference_events'
_CORE=('intake_id','revision','revision_fingerprint','origin_job_id','analysis_context_id','result_sha256','synthetic')
_SNAPSHOT={'schema_version','kind','snapshot_scope',*_CORE,'readiness_fingerprint','projection','projection_sha256'}
_APPEND={'expected_snapshot_id','captured_snapshot_id','head_before_record_id','head_after_record_id','head_advanced','preparation_ready','observed_at'}
_MODES={'intake_revision_synthetic','catalog_synthetic','intake_provenance_status'}
_SUMMARY={'record_id','seq','request_id','revision','origin_job_id','reference_receipt_id','binding_status','expected_snapshot_id','append_observation','source_modes','created_at'}
_PARENT={'schema_version','kind','receipt_id','execution_mode','status','reason_codes','intake_binding','case_binding',
    'intake_match','reference_selection','case_states','evaluation','verification','limits'}
_PARENT_FALSE={'source_facts_reverified','result_projection_reverified','database_currentness_verified','operational_authority_granted',
    'model_execution_verified','model_quality_verified','independent_evaluation_approved','training_executed','evaluation_executed','hardware_verified','physical_verified'}
_EVALUATION={'status':'not_executed','score':None,'actual_model_score':None,'scored_fixture_checks':0,
    'actual_model_checks':0,'independent_assignment_status':'not_assessed'}

_DDL={
_R:('table',_R,"""CREATE TABLE intake_reference_records(
 seq INTEGER PRIMARY KEY CHECK(seq>0),
 record_id TEXT NOT NULL UNIQUE, request_id TEXT NOT NULL UNIQUE,
 request_fingerprint TEXT NOT NULL, intake_id TEXT NOT NULL,
 revision INTEGER NOT NULL CHECK(typeof(revision)='integer' AND revision>0),
 origin_job_id TEXT NOT NULL, expected_snapshot_id TEXT NOT NULL,
 expected_head_record_id TEXT,
 snapshot_json TEXT NOT NULL, snapshot_sha256 TEXT NOT NULL,
 receipt_json TEXT NOT NULL, receipt_sha256 TEXT NOT NULL, receipt_id TEXT NOT NULL,
 context_sha256 TEXT NOT NULL, response_sha256 TEXT NOT NULL,
 producer_name TEXT NOT NULL,
 binding_status TEXT NOT NULL CHECK(binding_status IN
 ('current_at_append','historical_provided','preparation_unverified','head_conflict','reference_unbound')),
 mutable_state_verified INTEGER NOT NULL CHECK(mutable_state_verified IN (0,1)),
 append_json TEXT NOT NULL, append_sha256 TEXT NOT NULL,
 source_modes_json TEXT NOT NULL, source_modes_sha256 TEXT NOT NULL,
 summary_json TEXT NOT NULL, summary_sha256 TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(intake_id,record_id,seq,expected_snapshot_id,binding_status),
 FOREIGN KEY(intake_id,revision) REFERENCES intake_revisions(intake_id,revision)
 ON DELETE NO ACTION ON UPDATE NO ACTION,
 FOREIGN KEY(origin_job_id) REFERENCES intake_jobs(job_id)
 ON DELETE NO ACTION ON UPDATE NO ACTION
)"""),
_H:('table',_H,"""CREATE TABLE intake_reference_heads(
 intake_id TEXT PRIMARY KEY NOT NULL, record_id TEXT NOT NULL,
 seq INTEGER NOT NULL, expected_snapshot_id TEXT NOT NULL,
 binding_status TEXT NOT NULL CHECK(binding_status='current_at_append'),
 updated_at TEXT NOT NULL,
 FOREIGN KEY(intake_id,record_id,seq,expected_snapshot_id,binding_status)
 REFERENCES intake_reference_records(intake_id,record_id,seq,expected_snapshot_id,binding_status)
 ON DELETE NO ACTION ON UPDATE NO ACTION
)"""),
_E:('table',_E,"""CREATE TABLE intake_reference_events(
 record_id TEXT PRIMARY KEY NOT NULL,
 kind TEXT NOT NULL CHECK(kind='append_recorded'),
 request_fingerprint TEXT NOT NULL, binding_status TEXT NOT NULL,
 append_sha256 TEXT NOT NULL, head_advanced INTEGER NOT NULL CHECK(head_advanced IN (0,1)),
 created_at TEXT NOT NULL,
 FOREIGN KEY(record_id) REFERENCES intake_reference_records(record_id)
 ON DELETE NO ACTION ON UPDATE NO ACTION
)"""),
_R+'_intake_seq':('index',_R,'CREATE INDEX intake_reference_records_intake_seq ON intake_reference_records(intake_id,seq DESC)'),
}
for _table in (_R,_E):
    for _verb in ('UPDATE','DELETE'):
        _name=_table+'_no_'+_verb.lower()
        _DDL[_name]=('trigger',_table,f"CREATE TRIGGER {_name} BEFORE {_verb} ON {_table} BEGIN SELECT RAISE(ABORT,'immutable_reference_history'); END")
_AUTO={
    'sqlite_autoindex_'+_R+'_1':(_R,'u',['record_id']),
    'sqlite_autoindex_'+_R+'_2':(_R,'u',['request_id']),
    'sqlite_autoindex_'+_R+'_3':(_R,'u',['intake_id','record_id','seq','expected_snapshot_id','binding_status']),
    'sqlite_autoindex_'+_H+'_1':(_H,'pk',['intake_id']),
    'sqlite_autoindex_'+_E+'_1':(_E,'pk',['record_id']),
}
_COLUMNS=('seq','record_id','request_id','request_fingerprint','intake_id','revision','origin_job_id','expected_snapshot_id',
    'expected_head_record_id','snapshot_json','snapshot_sha256','receipt_json','receipt_sha256','receipt_id','context_sha256',
    'response_sha256','producer_name','binding_status','mutable_state_verified','append_json','append_sha256',
    'source_modes_json','source_modes_sha256','summary_json','summary_sha256','created_at')
_JSON_LIMITS={'snapshot_json':9*_MIB,'receipt_json':2*_MIB,'append_json':65536,'source_modes_json':4096,'summary_json':4096}
_INTEGERS={'seq','revision','mutable_state_verified'}


class IntakeReferenceLedgerError(ValueError):
    def __init__(self,code):
        suffix=code.removeprefix('intake_reference_ledger_') if type(code) is str else 'storage_error'
        self.code='intake_reference_ledger_'+(suffix if suffix in _CODES else 'storage_error')
        super().__init__(self.code)


def _fail(code):raise IntakeReferenceLedgerError(code)
def _encoded(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def _hash(value):return hashlib.sha256(_encoded(value)).hexdigest()
def _same(a,b):
    try:return _encoded(a)==_encoded(b)
    except (ValueError,TypeError,UnicodeError,OverflowError,RecursionError):return False
def _keys(value,keys,code='integrity_invalid'):
    if type(value) is not dict or set(value)!=set(keys):_fail(code)
def _id(value,code='invalid_argument',maximum=150):
    if type(value) is not str or len(value)>maximum or not _ID.fullmatch(value):_fail(code)
def _sha(value,code='integrity_invalid',nullable=False):
    if nullable and value is None:return
    if type(value) is not str or not _SHA.fullmatch(value):_fail(code)
def _positive(value,code='invalid_argument'):
    if type(value) is not int or not 1<=value<=_MAXINT:_fail(code)
def _choice(value,options,code='integrity_invalid'):
    if type(value) is not str or value not in options:_fail(code)
def _timestamp(value):
    if type(value) is not str or len(value)>64:_fail('integrity_invalid')
    try:parsed=datetime.fromisoformat(value)
    except ValueError:_fail('integrity_invalid')
    if parsed.tzinfo is None or parsed.utcoffset()!=timedelta(0):_fail('integrity_invalid')
def _now():return datetime.now(timezone.utc).isoformat()


def _copy(value,limit,code,depth_limit=28,nodes=None,node_limit=1000000):
    nodes=[0] if nodes is None else nodes;size=0;local_nodes=0
    def consume(amount):
        nonlocal size
        size+=amount
        if size>limit:_fail('input_limit')
    def count():
        nonlocal local_nodes
        nodes[0]+=1;local_nodes+=1
        if nodes[0]>1000000 or local_nodes>node_limit:_fail('input_limit')
    def scalar(item):
        if type(item) is str and len(item)>limit-size:_fail('input_limit')
        try:raw=_encoded(item)
        except (ValueError,UnicodeError,OverflowError,RecursionError):_fail(code)
        consume(len(raw));return item
    def walk(item,depth=0):
        count()
        if depth>depth_limit:_fail('input_limit')
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


def _pairs(pairs):
    value={}
    for key,child in pairs:
        if key in value:raise ValueError()
        value[key]=child
    return value


def _json(raw,limit,code='integrity_invalid',*,stored_sha=None,depth=28,nodes=1000000):
    if type(raw) is not str:_fail(code)
    try:
        encoded=raw.encode('utf-8')
        if len(encoded)>limit:_fail('input_limit')
        def constant(_):raise ValueError()
        value=json.loads(raw,object_pairs_hook=_pairs,parse_constant=constant)
    except IntakeReferenceLedgerError:raise
    except (ValueError,UnicodeError,TypeError,OverflowError,RecursionError):_fail(code)
    value=_copy(value,limit,code,depth_limit=depth,node_limit=nodes)
    if stored_sha is not None:
        _sha(stored_sha,code)
        if _encoded(value)!=encoded or hashlib.sha256(encoded).hexdigest()!=stored_sha:_fail(code)
    return value


def _select(con,sql,args=()):return [dict(row) for row in con.execute(sql,args)]
def _one(con,sql,args=()):
    rows=_select(con,sql,args);return rows[0] if rows else None
def _measure(columns):return '+'.join('coalesce(length(CAST('+name+' AS BLOB)),0)' for name in columns)
def _store(store):
    if type(store) is not Store or not isinstance(store.db,Path):_fail('store_invalid')
def _identity(path):
    try:stat=path.stat();return stat.st_dev,stat.st_ino
    except OSError:_fail('storage_error')


@contextmanager
def _connection(store,*,writer=False):
    _store(store)
    try:
        path=store.db.resolve(strict=True)
        if not path.is_file():_fail('storage_error')
    except OSError:_fail('storage_error')
    identity=_identity(path);con=None
    try:
        con=sqlite3.connect(path.as_uri()+('?mode=rw' if writer else '?mode=ro'),uri=True,timeout=30)
        con.row_factory=sqlite3.Row
        if writer:
            con.execute('PRAGMA foreign_keys=ON')
            if con.execute('PRAGMA foreign_keys').fetchone()[0]!=1:_fail('storage_error')
        con.execute('BEGIN IMMEDIATE' if writer else 'BEGIN')
        if _identity(path)!=identity:_fail('storage_error')
        yield con
        if _identity(path)!=identity:_fail('storage_error')
        if writer:con.commit()
        else:con.rollback()
    finally:
        if con is not None:
            try:
                if con.in_transaction:con.rollback()
            finally:con.close()


def _schema(con,*,create=False):
    rows=_select(con,"SELECT name,type,tbl_name,sql FROM sqlite_master WHERE lower(substr(name,1,16))='intake_reference' OR lower(tbl_name) IN (?,?,?)",(_R,_H,_E))
    if not rows:
        if not create:return False
        for _,_,sql in _DDL.values():con.execute(sql)
        return _schema(con)
    normalize=lambda sql:' '.join(sql.strip().rstrip(';').split()) if type(sql) is str else None
    actual={row['name']:(row['type'],row['tbl_name'],normalize(row['sql'])) for row in rows}
    expected={name:(kind,table,normalize(sql)) for name,(kind,table,sql) in _DDL.items()}
    expected.update({name:('index',table,None) for name,(table,_,_) in _AUTO.items()})
    if actual!=expected:_fail('schema_mismatch')
    for name,(table,origin,columns) in _AUTO.items():
        info=_one(con,'SELECT "unique",origin,partial FROM pragma_index_list(?) WHERE name=?',(table,name))
        actual_columns=[row['name'] for row in _select(con,'SELECT name FROM pragma_index_info(?) ORDER BY seqno',(name,))]
        if info!={'unique':1,'origin':origin,'partial':0} or actual_columns!=columns:_fail('schema_mismatch')
    return True


def _intake(con,intake_id):
    if _one(con,'SELECT 1 AS found FROM intakes WHERE intake_id=?',(intake_id,)) is None:_fail('intake_not_found')


def _fingerprint(row):
    return _hash({'schema_version':1,'request_id':row['request_id'],'expected_snapshot_id':row['expected_snapshot_id'],
        'expected_head_record_id':row['expected_head_record_id'],'intake_snapshot_sha256':row['snapshot_sha256'],
        'case_context_sha256':row['context_sha256'],'validated_response_sha256':row['response_sha256'],
        'reference_receipt_sha256':row['receipt_sha256'],'producer_name':row['producer_name']})


def _summary(row,append,modes):
    return {**{key:row[key] for key in ['record_id','seq','request_id','revision','origin_job_id','binding_status','expected_snapshot_id','created_at']},
        'reference_receipt_id':row['receipt_id'],'append_observation':append,'source_modes':modes}


def _prior_head(con,intake_id,before=None):
    where='intake_id=? AND binding_status=\'current_at_append\'';args=[intake_id]
    if before is not None:where+=' AND seq<?';args.append(before)
    value=_one(con,'SELECT CASE WHEN length(CAST(record_id AS BLOB))<=64 THEN record_id END AS record_id FROM '+_R+' WHERE '+where+' ORDER BY seq DESC LIMIT 1',tuple(args))
    if value is None:return None
    _sha(value['record_id']);return value['record_id']


def _metadata(con,row):
    code='integrity_invalid'
    for key in ['seq','revision']:_positive(row[key],code)
    for key in ['request_id','intake_id','origin_job_id','producer_name']:_id(row[key],code)
    for key in ['record_id','request_fingerprint','expected_snapshot_id','snapshot_sha256','receipt_sha256','receipt_id',
                'context_sha256','response_sha256','append_sha256','source_modes_sha256','summary_sha256']:_sha(row[key])
    _sha(row['expected_head_record_id'],nullable=True);_timestamp(row['created_at'])
    _choice(row['binding_status'],_STATUS)
    if type(row['mutable_state_verified']) is not int or row['mutable_state_verified'] not in (0,1):_fail(code)
    if _fingerprint(row)!=row['request_fingerprint'] or _hash({'schema_version':1,'request_id':row['request_id'],'request_fingerprint':row['request_fingerprint']})!=row['record_id']:_fail(code)
    append=_json(row['append_json'],65536,stored_sha=row['append_sha256']);_keys(append,_APPEND)
    modes=_json(row['source_modes_json'],4096,stored_sha=row['source_modes_sha256']);_keys(modes,_MODES)
    summary=_json(row['summary_json'],4096,stored_sha=row['summary_sha256']);_keys(summary,_SUMMARY)
    for key in ['captured_snapshot_id','head_before_record_id','head_after_record_id']:_sha(append[key],nullable=True)
    if append['expected_snapshot_id']!=row['expected_snapshot_id'] or append['observed_at']!=row['created_at']:_fail(code)
    if type(append['head_advanced']) is not bool or type(append['preparation_ready']) is not bool:_fail(code)
    advanced=row['binding_status']=='current_at_append'
    if append['head_advanced']!=advanced or append['head_after_record_id']!=(row['record_id'] if advanced else append['head_before_record_id']):_fail(code)
    if append['head_before_record_id']!=_prior_head(con,row['intake_id'],row['seq']):_fail(code)
    if row['mutable_state_verified'] and append['captured_snapshot_id']!=row['expected_snapshot_id']:_fail(code)
    if advanced and (not row['mutable_state_verified'] or append['captured_snapshot_id']!=row['expected_snapshot_id']):_fail(code)
    if row['binding_status']=='historical_provided' and row['mutable_state_verified']:_fail(code)
    if row['binding_status'] in {'preparation_unverified','head_conflict'} and not row['mutable_state_verified']:_fail(code)
    if type(modes['intake_revision_synthetic']) is not bool or modes['catalog_synthetic'] is not None and type(modes['catalog_synthetic']) is not bool:_fail(code)
    _choice(modes['intake_provenance_status'],{'confirmed','unconfirmed','not_assessed'})
    if not _same(summary,_summary(row,append,modes)):_fail(code)
    size=_one(con,'SELECT count(*) AS n,coalesce(sum('+_measure(['record_id','kind','request_fingerprint','binding_status','append_sha256','head_advanced','created_at'])+'),0) AS bytes FROM '+_E+' WHERE record_id=?',(row['record_id'],))
    if size['bytes']>4096:_fail('input_limit')
    if size['n']!=1:_fail(code)
    event=_one(con,'SELECT * FROM '+_E+' WHERE record_id=?',(row['record_id'],))
    expected={'record_id':row['record_id'],'kind':'append_recorded','request_fingerprint':row['request_fingerprint'],
        'binding_status':row['binding_status'],'append_sha256':row['append_sha256'],'head_advanced':int(advanced),'created_at':row['created_at']}
    if not _same(event,expected):_fail(code)
    return {'row':row,'append':append,'modes':modes,'summary':summary}


def _record_rows(con,where,args,*,full=False,limit=1,budget=None):
    columns=[name for name in _COLUMNS if full or name not in {'snapshot_json','receipt_json'}]
    measure=_measure([name for name in columns if name not in _INTEGERS])
    bounded=' FROM '+_R+' WHERE '+where+' ORDER BY seq DESC LIMIT ?'
    size=_one(con,'SELECT count(*) AS n,coalesce(sum('+measure+'),0) AS bytes FROM (SELECT '+','.join(columns)+bounded+')',(*args,limit))
    if budget is not None and size['bytes']>budget:_fail('input_limit')
    parts=[]
    for name in columns:
        if name in _INTEGERS:parts.append(name);continue
        cap=_JSON_LIMITS.get(name,150 if name in {'request_id','intake_id','origin_job_id','producer_name'} else 64)
        parts.extend(['length(CAST('+name+' AS BLOB)) AS size_'+name,
            "CASE WHEN typeof("+name+")='text' AND length(CAST("+name+' AS BLOB))<='+str(cap)+' THEN '+name+' END AS '+name])
    rows=_select(con,'SELECT '+','.join(parts)+bounded,(*args,limit))
    result=[]
    for row in rows:
        for name in columns:
            if name in _INTEGERS:continue
            cap=_JSON_LIMITS.get(name,150 if name in {'request_id','intake_id','origin_job_id','producer_name'} else 64)
            value=row.pop('size_'+name)
            if value is not None and value>cap:_fail('input_limit')
        if full and sum(len(row[name].encode('utf-8')) for name in _JSON_LIMITS if type(row[name]) is str)>12*_MIB:_fail('input_limit')
        value=_metadata(con,row)
        if full:_payloads(con,value)
        result.append(value)
    return result


def _head(con,intake_id):
    size=_one(con,'SELECT coalesce(sum('+_measure(['intake_id','record_id','seq','expected_snapshot_id','binding_status','updated_at'])+'),0) AS bytes FROM '+_H+' WHERE intake_id=?',(intake_id,))
    if size['bytes']>4096:_fail('input_limit')
    row=_one(con,'SELECT * FROM '+_H+' WHERE intake_id=?',(intake_id,));latest=_prior_head(con,intake_id)
    if row is None:
        if latest is not None:_fail('integrity_invalid')
        return None
    _keys(row,{'intake_id','record_id','seq','expected_snapshot_id','binding_status','updated_at'})
    values=_record_rows(con,'record_id=?',(row['record_id'],))
    if not values:_fail('integrity_invalid')
    record=values[0];primitive=record['row']
    expected={key:primitive[key] for key in ['intake_id','record_id','seq','expected_snapshot_id','binding_status']};expected['updated_at']=primitive['created_at']
    if latest!=row['record_id'] or row['binding_status']!='current_at_append' or not _same(row,expected):_fail('integrity_invalid')
    return record


def _snapshot(value,code):
    _keys(value,_SNAPSHOT,code)
    if type(value['schema_version']) is not int or value['schema_version']!=1 or value['kind']!='intake_case_reference_snapshot' or value['snapshot_scope']!='caller_provided':_fail(code)
    for key in ['intake_id','origin_job_id']:_id(value[key],code)
    _positive(value['revision'],code)
    for key in ['revision_fingerprint','analysis_context_id','result_sha256','projection_sha256']:_sha(value[key],code)
    _sha(value['readiness_fingerprint'],code,nullable=True)
    if type(value['synthetic']) is not bool:_fail(code)
    projection=_copy(value['projection'],8*_MIB,code,depth_limit=16,node_limit=50000);_keys(projection,{'facts','questions'},code)
    if type(projection['facts']) is not dict or set(projection['facts'])-{'product_type','market','model'}:_fail(code)
    for fact in projection['facts'].values():
        if type(fact) is not dict or not {'value','status'}<=set(fact) or set(fact)-{'value','status','event_id'}:_fail(code)
        if type(fact['value']) is not str or not fact['value'].strip() or len(fact['value'])>4000:_fail(code)
        _choice(fact['status'],{'explicit','inferred','uncertain','user_confirmed'},code)
        if fact['status']=='user_confirmed' and 'event_id' not in fact:_fail(code)
        if 'event_id' in fact:
            if type(fact['event_id']) is int:_positive(fact['event_id'],code)
            else:_id(fact['event_id'],code,128)
    if type(projection['questions']) is not list or len(projection['questions'])>200:_fail(code)
    for question in projection['questions']:
        _keys(question,{'key'},code)
        if type(question['key']) is not str or not question['key'].strip():_fail(code)
        if len(question['key'].encode('utf-8'))>_MIB:_fail('input_limit')
    if _hash(projection)!=value['projection_sha256']:_fail(code)


def _origin_meta(con,snapshot,code='origin_invalid'):
    _snapshot(snapshot,code)
    row=_one(con,"""SELECT i.source_id,j.intake_id,j.revision,j.job_id,j.state,r.fingerprint,r.synthetic,
        length(CAST(r.files_json AS BLOB)) AS manifest_bytes,
        CASE WHEN typeof(r.files_json)='text' AND length(CAST(r.files_json AS BLOB))<=4194304 THEN r.files_json END AS files_json,
        length(CAST(j.result_json AS BLOB)) AS result_bytes,
        CASE WHEN typeof(j.result_json)='text' AND length(CAST(j.result_json AS BLOB))<=8388608 THEN j.result_json END AS result_json
        FROM intake_jobs j JOIN intakes i ON i.intake_id=j.intake_id
        JOIN intake_revisions r ON r.intake_id=j.intake_id AND r.revision=j.revision WHERE j.job_id=?""",(snapshot['origin_job_id'],))
    if row is None:_fail(code)
    if row['manifest_bytes'] is not None and row['manifest_bytes']>4*_MIB or row['result_bytes'] is not None and row['result_bytes']>8*_MIB:_fail('input_limit')
    if (row['intake_id']!=snapshot['intake_id'] or type(row['revision']) is not int or row['revision']!=snapshot['revision']
            or row['fingerprint']!=snapshot['revision_fingerprint'] or row['state']!='completed'
            or type(row['synthetic']) is not int or row['synthetic'] not in (0,1) or bool(row['synthetic'])!=snapshot['synthetic']):_fail(code)
    files=_json(row['files_json'],4*_MIB,code);result=_json(row['result_json'],8*_MIB,code)
    if _hash(files)!=snapshot['revision_fingerprint'] or hashlib.sha256(row['result_json'].encode('utf-8')).hexdigest()!=snapshot['result_sha256']:_fail(code)
    _keys(result,{'submission','summary'},code)
    analysis=result['submission']
    if type(analysis) is not dict or type(analysis.get('schema_version')) is not int or analysis['schema_version']!=2 or analysis.get('context_id')!=snapshot['analysis_context_id']:_fail(code)
    return row,files


def _origin_sources(store,con,snapshot):
    code='origin_invalid';row,files=_origin_meta(con,snapshot)
    if type(files) is not list:_fail(code)
    limits={snapshot['analysis_context_id']:4*_MIB}
    for item in files:
        _keys(item,{'path','sha256','bytes'},code);_sha(item['sha256'],code)
        if type(item['bytes']) is not int or item['bytes']<0:_fail(code)
        if item['bytes']>16*_MIB:_fail('input_limit')
        limits[item['sha256']]=min(limits.get(item['sha256'],16*_MIB),16*_MIB)
    try:
        context_path=store.blob_path(snapshot['analysis_context_id'])
        if context_path.stat().st_size>4*_MIB:_fail('input_limit')
        with context_path.open('rb') as stream:raw=stream.read(4*_MIB+1)
        if len(raw)>4*_MIB:_fail('input_limit')
        context=_json(raw.decode('utf-8'),4*_MIB,code)
        if type(context) is not dict or type(context.get('documents')) is not list:_fail(code)
        for document in context['documents']:
            if type(document) is not dict:_fail(code)
            if document.get('format')=='pdf':
                sha=document.get('extraction_id');_sha(sha,code);limits[sha]=min(limits.get(sha,4*_MIB),4*_MIB)
        def states():
            values={}
            for sha,limit in limits.items():
                stat=store.blob_path(sha).stat()
                if stat.st_size>limit:_fail('input_limit')
                values[sha]=(stat.st_size,stat.st_mtime_ns,stat.st_mode,stat.st_dev,stat.st_ino)
            return values
        before=states()
        verified,_,context_id,_=validate_retained_analysis(store,row)
        if verified!='verified' or context_id!=snapshot['analysis_context_id'] or states()!=before:_fail(code)
    except IntakeReferenceLedgerError:raise
    except Exception:_fail(code)
    return _hash({key:row[key] for key in ['source_id','intake_id','revision','job_id','state','fingerprint','synthetic','files_json','result_json']})


def _payloads(con,value):
    code='integrity_invalid';row=value['row']
    snapshot=_json(row['snapshot_json'],9*_MIB,stored_sha=row['snapshot_sha256'],depth=20,nodes=500000)
    receipt=_json(row['receipt_json'],2*_MIB,stored_sha=row['receipt_sha256'],depth=16,nodes=500000)
    _origin_meta(con,snapshot,code)
    if any(snapshot[key]!=row[key] for key in ['intake_id','revision','origin_job_id']):_fail(code)
    _keys(receipt,_PARENT)
    if type(receipt['schema_version']) is not int or receipt['schema_version']!=1 or receipt['kind']!='intake_case_reference_receipt' or receipt['execution_mode']!='provided_snapshot_read_only':_fail(code)
    _choice(receipt['status'],{'bound','insufficient_evidence'})
    if receipt['receipt_id']!=row['receipt_id'] or _hash({key:child for key,child in receipt.items() if key!='receipt_id'})!=row['receipt_id']:_fail(code)
    binding=receipt['intake_binding'];cases=receipt['case_binding']
    _keys(binding,{*_CORE,'readiness_fingerprint','projection_sha256','snapshot_sha256','missing_fields'})
    _keys(cases,{'provided_context_sha256','provided_response_sha256','context_id','corpus_id','source_binding','query_sha256','producer','catalog_synthetic','context_status','search_status'})
    if any(binding[key]!=snapshot[key] for key in [*_CORE,'readiness_fingerprint','projection_sha256']) or binding['snapshot_sha256']!=row['snapshot_sha256'] or binding['missing_fields']!=[]:_fail(code)
    if cases['provided_context_sha256']!=row['context_sha256'] or cases['provided_response_sha256']!=row['response_sha256'] or not _same(cases['producer'],{'kind':'model','name':row['producer_name']}):_fail(code)
    if cases['catalog_synthetic'] is not value['modes']['catalog_synthetic'] or snapshot['synthetic'] is not value['modes']['intake_revision_synthetic']:_fail(code)
    if not _same(receipt['evaluation'],_EVALUATION) or type(receipt['verification']) is not dict or any(receipt['verification'].get(key) is not False for key in _PARENT_FALSE):_fail(code)
    if (row['binding_status']=='reference_unbound')!=(receipt['status']=='insufficient_evidence'):_fail(code)
    value.update(snapshot=snapshot,receipt=receipt)


def _capture(store,con,intake_id):
    try:return capture_intake_reference_snapshot_in_transaction(store,con,intake_id)
    except IntakeReferenceStateError as error:
        suffix=error.code.removeprefix('intake_reference_state_')
        if suffix in {'input_limit','storage_error','store_invalid','intake_not_found'}:_fail(suffix)
        _fail('origin_invalid' if suffix=='source_integrity_invalid' else 'parent_invalid')
    except Exception:_fail('parent_invalid')


def _parent(snapshot,catalog,context,response,provided,name):
    try:actual=build_intake_case_reference_receipt(snapshot,catalog,context,response,producer_name=name)
    except IntakeCaseReferencesError as error:_fail('input_limit' if error.code.endswith('limit_exceeded') else 'parent_invalid')
    except Exception:_fail('parent_invalid')
    if not _same(actual,provided):_fail('parent_invalid')
    return actual


def _registration(value,*,replayed):
    row=value['row']
    return {'schema_version':1,'kind':'intake_reference_registration','request_id':row['request_id'],'record_id':row['record_id'],
        'seq':row['seq'],'stored':True,'replayed':replayed,'binding_status':row['binding_status'],'append_observation':value['append'],
        'verification':{'record_hash_verified':True,'parent_revalidated_at_append':True,'origin_revalidated_at_append':True,
            'mutable_state_verified_at_append':bool(row['mutable_state_verified']),'operational_authority_granted':False,
            'model_execution_verified':False,'evaluation_executed':False,'independent_evaluation_approved':False}}


def _record(store,request_id,expected_snapshot_id,expected_head_record_id,snapshot,catalog,context,response,receipt,producer_name):
    _store(store);_id(request_id);_id(producer_name);_sha(expected_snapshot_id,'invalid_argument');_sha(expected_head_record_id,'invalid_argument',nullable=True)
    if type(catalog) is not FccReportCaseCatalog:_fail('parent_invalid')
    nodes=[0]
    snapshot=_copy(snapshot,9*_MIB,'parent_invalid',20,nodes,500000)
    context=_copy(context,8*_MIB,'parent_invalid',24,nodes,500000)
    response=_copy(response,320*1024,'parent_invalid',16,nodes,500000)
    receipt=_copy(receipt,2*_MIB,'parent_invalid',16,nodes,500000)
    if sum(len(_encoded(value)) for value in [snapshot,context,response,receipt])>20*_MIB:_fail('input_limit')
    if type(snapshot) is not dict:_fail('parent_invalid')
    intake_id=snapshot.get('intake_id');_id(intake_id,'origin_invalid')
    row={'request_id':request_id,'expected_snapshot_id':expected_snapshot_id,'expected_head_record_id':expected_head_record_id,
        'snapshot_sha256':_hash(snapshot),'receipt_sha256':_hash(receipt),'context_sha256':_hash(context),'response_sha256':_hash(response),'producer_name':producer_name}
    row['request_fingerprint']=_fingerprint(row)
    with _connection(store,writer=True) as con:
        _intake(con,intake_id);_schema(con,create=True)
        old=_record_rows(con,'request_id=?',(request_id,))
        if old:
            if old[0]['row']['request_fingerprint']!=row['request_fingerprint']:_fail('request_conflict')
            value=_record_rows(con,'request_id=?',(request_id,),full=True)[0];_head(con,intake_id)
            return _copy(_registration(value,replayed=True),_MIB,'integrity_invalid')
        parent=_parent(snapshot,catalog,context,response,receipt,producer_name)
        first=_capture(store,con,intake_id);origin=_origin_sources(store,con,snapshot);head=_head(con,intake_id)
        head_id=head['row']['record_id'] if head else None
        matched=first['snapshot_id']==expected_snapshot_id and first['snapshot'] is not None and _same(first['snapshot'],snapshot)
        if parent['status']=='insufficient_evidence':status='reference_unbound'
        elif not matched:status='historical_provided'
        elif not first['profile']['matches'] or 'source_provenance_unconfirmed' in first['readiness']['reason_codes']:status='preparation_unverified'
        elif head_id!=expected_head_record_id:status='head_conflict'
        else:status='current_at_append'
        advanced=status=='current_at_append';created=_now()
        seq=_one(con,'SELECT coalesce(max(seq),0)+1 AS seq FROM '+_R)['seq'];_positive(seq,'input_limit')
        row.update(seq=seq,record_id=_hash({'schema_version':1,'request_id':request_id,'request_fingerprint':row['request_fingerprint']}),
            intake_id=intake_id,revision=snapshot['revision'],origin_job_id=snapshot['origin_job_id'],receipt_id=parent['receipt_id'],
            binding_status=status,mutable_state_verified=int(matched),created_at=created)
        append={'expected_snapshot_id':expected_snapshot_id,'captured_snapshot_id':first['snapshot_id'],'head_before_record_id':head_id,
            'head_after_record_id':row['record_id'] if advanced else head_id,'head_advanced':advanced,
            'preparation_ready':first['readiness']['ready'],'observed_at':created}
        provenance='not_assessed' if not matched else 'unconfirmed' if 'source_provenance_unconfirmed' in first['readiness']['reason_codes'] else 'confirmed'
        modes={'intake_revision_synthetic':snapshot['synthetic'],'catalog_synthetic':parent['case_binding']['catalog_synthetic'],'intake_provenance_status':provenance}
        summary=_summary(row,append,modes)
        payloads={'snapshot':snapshot,'receipt':parent,'append':append,'source_modes':modes,'summary':summary}
        for name,value in payloads.items():
            raw=_encoded(_copy(value,_JSON_LIMITS[name+'_json'],'integrity_invalid'))
            row[name+'_json']=raw.decode('utf-8');row[name+'_sha256']=hashlib.sha256(raw).hexdigest()
        if sum(len(row[name].encode('utf-8')) for name in _JSON_LIMITS)>12*_MIB:_fail('input_limit')
        con.execute('INSERT INTO '+_R+'('+','.join(_COLUMNS)+') VALUES('+','.join('?' for _ in _COLUMNS)+')',tuple(row[name] for name in _COLUMNS))
        con.execute('INSERT INTO '+_E+' VALUES(?,?,?,?,?,?,?)',(row['record_id'],'append_recorded',row['request_fingerprint'],status,row['append_sha256'],int(advanced),created))
        if advanced:
            if head is None:con.execute('INSERT INTO '+_H+' VALUES(?,?,?,?,?,?)',(intake_id,row['record_id'],seq,expected_snapshot_id,status,created))
            else:
                changed=con.execute('UPDATE '+_H+' SET record_id=?,seq=?,expected_snapshot_id=?,binding_status=?,updated_at=? WHERE intake_id=? AND record_id=?',
                    (row['record_id'],seq,expected_snapshot_id,status,created,intake_id,expected_head_record_id)).rowcount
                if changed!=1:_fail('integrity_invalid')
        value=_record_rows(con,'record_id=?',(row['record_id'],),full=True)[0];_head(con,intake_id)
        second=_capture(store,con,intake_id)
        if not _same(second,first):_fail('origin_invalid')
        if _origin_sources(store,con,snapshot)!=origin:_fail('origin_invalid')
        return _copy(_registration(value,replayed=False),_MIB,'integrity_invalid')


def record_intake_reference(store,request_id,*,expected_snapshot_id,expected_head_record_id,
        intake_snapshot,catalog,case_context,validated_response,reference_receipt,producer_name):
    """Explicit append or immutable replay; append_observation always names its old time."""
    try:return _record(store,request_id,expected_snapshot_id,expected_head_record_id,intake_snapshot,catalog,case_context,validated_response,reference_receipt,producer_name)
    except IntakeReferenceLedgerError as error:code=error.code
    except Exception:code='storage_error'
    raise IntakeReferenceLedgerError(code) from None


def _history(store,intake_id,limit,before_seq):
    _store(store);_id(intake_id);_positive(limit)
    if limit>100:_fail('invalid_argument')
    if before_seq is not None:_positive(before_seq)
    with _connection(store) as con:
        _intake(con,intake_id);available=_schema(con);records=[];next_seq=None
        if available:
            _head(con,intake_id)
            where='intake_id=?';args=[intake_id]
            if before_seq is not None:where+=' AND seq<?';args.append(before_seq)
            values=_record_rows(con,where,tuple(args),limit=limit,budget=_MIB)
            records=[value['summary'] for value in values]
            if records and _one(con,'SELECT 1 AS found FROM '+_R+' WHERE intake_id=? AND seq<? LIMIT 1',(intake_id,records[-1]['seq'])) is not None:next_seq=records[-1]['seq']
        result={'schema_version':1,'kind':'intake_reference_history','intake_id':intake_id,'available':available,'records':records,
            'next_before_seq':next_seq,'verification':{'record_metadata_verified':available,'payloads_reverified':False,'original_sources_reverified':False,'database_currentness_verified':False}}
        return _copy(result,_MIB,'integrity_invalid')


def reference_history(store,intake_id,*,limit=20,before_seq=None):
    """Bounded metadata only, with summary/event/head integrity and no source revalidation."""
    try:return _history(store,intake_id,limit,before_seq)
    except IntakeReferenceLedgerError as error:code=error.code
    except Exception:code='storage_error'
    raise IntakeReferenceLedgerError(code) from None


def _current(store,intake_id):
    _store(store);_id(intake_id)
    with _connection(store) as con:
        _intake(con,intake_id);available=_schema(con);head=_head(con,intake_id) if available else None
        value=_record_rows(con,'record_id=?',(head['row']['record_id'],),full=True)[0] if head else None
        capture=_capture(store,con,intake_id);reasons=set(capture['reason_codes'])
        if capture['snapshot'] is None:status='unavailable';reasons.add('current_capture_unavailable')
        elif value is None:status='none';reasons.add('no_reference_head')
        elif (value['row']['expected_snapshot_id']==capture['snapshot_id'] and value['row']['snapshot_sha256']==_hash(capture['snapshot'])
                and capture['profile']['matches'] and 'source_provenance_unconfirmed' not in capture['readiness']['reason_codes']):status='current'
        else:status='stale';reasons.add('reference_snapshot_stale')
        if reasons-set(REASON_CODES)-{'current_capture_unavailable','no_reference_head','reference_snapshot_stale'}:_fail('parent_invalid')
        result={'schema_version':1,'kind':'intake_reference_current','intake_id':intake_id,'available':available,'status':status,
            'record':value['summary'] if value else None,'reference_receipt':value['receipt'] if value else None,
            'current_observation':{'snapshot_id':capture['snapshot_id'],'head_record_id':head['row']['record_id'] if head else None,
                'preparation_ready':capture['readiness']['ready'],'observed_at':_now()},'reason_codes':sorted(reasons),
            'verification':{'record_hash_verified':value is not None,'database_snapshot_observed':capture['verification']['database_snapshot_observed'],
                'reference_source_currentness_verified':False,'operational_authority_granted':False,'model_execution_verified':False,'evaluation_executed':False}}
        return _copy(result,12*_MIB,'integrity_invalid')


def current_reference(store,intake_id):
    """Fresh same-con A observation, independent of immutable historical append time."""
    try:return _current(store,intake_id)
    except IntakeReferenceLedgerError as error:code=error.code
    except Exception:code='storage_error'
    raise IntakeReferenceLedgerError(code) from None

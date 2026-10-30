"""Fixed native profile -> one existing conducted permit -> genuine public APIs."""
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import sys
import threading

from . import codex_registered_intake_host as _native_host
from .intake_jobs import prepare_registered_synthetic_context
from .intake_current_facts_plan import read_current_conducted_plan_from_facts as _current_facts
from .intake_conducted_twin_plan import build_conducted_twin_plan_input
from .intake_plan_virtual_execution import (
    IntakePlanVirtualExecutionError, run_intake_plan_virtual_execution as _execute)
from .conducted_execution_result_finalizer import (
    ConductedExecutionResultFinalizerError, finalize_conducted_execution_result as _finalize)
from .store import Store, StoreOpenError, canonical
from .virtual_fleet.operator_response_schema import (
    CURRENT_SCHEMA_SHA256, is_current_response_schema_bytes, is_known_response_schema_bytes)

__all__=['main']
_PREFIX='codex_registered_conducted_workflow_host_'
_CONTROL=(KeyboardInterrupt,SystemExit,GeneratorExit,MemoryError)
_MODELS=('gpt-6.1-sol','gpt-6-astra')
_TOOLS=['dut.start','sensor.acquire','sensor.read','advance1','stop']
_SCHEMA_SHA=CURRENT_SCHEMA_SHA256
_HANDOFF_CAP=8388608
_TAIL_FILES,_TAIL_BYTES=10,5505024
_DDL='CREATE TABLE codex_conducted_workflow_history(seq INTEGER PRIMARY KEY, kind TEXT NOT NULL, permit_id TEXT, payload TEXT NOT NULL, UNIQUE(kind,permit_id))'
_C=lambda value:canonical(value).encode('utf-8')
_H=_native_host._H
_read=_native_host._read
_path=_native_host._path
_json=_native_host._json
_integer=_native_host._int


class _Failure(ValueError):pass
def _fail(code):raise _Failure(_PREFIX+code)
def _keys(value,keys):
    if type(value) is not dict or set(value)!=set(keys.split()):_fail('profile_invalid')
def _same(left,right):
    if _C(left)!=_C(right):_fail('binding_mismatch')
def _profile_root():
    # Sibling managed control; never create a replacement for historical state.
    return _native_host._control_root().with_name('codex-conducted-workflow-host')
def _close_ledger(con):con.close()
def _load(root,name,cap):return _json(_read(root/name,cap))
def _pin(raw):return dict(bytes=len(raw),sha256=_H(raw))


def _anchor(value):
    _keys(value,'schema_version kind inherited_history')
    if not _integer(value['schema_version'],1,1) or value['kind']!='codex_conducted_workflow_root_anchor':_fail('scope_mismatch')
    inherited=value['inherited_history']
    _keys(inherited,'actual_codex_model_processes known_total_before_this_host unknown_usage_components usage_complete cost provenance_level source_rollup published_source')
    if (not _integer(inherited['actual_codex_model_processes'],17,17)
            or not _integer(inherited['known_total_before_this_host'],17,17)
            or inherited['unknown_usage_components'] is not None or inherited['usage_complete'] is not False
            or inherited['cost'] is not None
            or inherited['provenance_level']!='previous_verified_root_rollup_not_fresh_original_receipt_reaudit'):_fail('history_invalid')
    for name,fields in [('source_rollup','path bytes sha256'),('published_source','commit path bytes sha256')]:
        row=inherited[name];_keys(row,fields)
        if type(row['path']) is not str or not 0<len(row['path'])<=2048 or not _integer(row['bytes']):_fail('history_invalid')
        _native_host._hash(row['sha256'])
        if name=='published_source' and (type(row['commit']) is not str or not re.fullmatch('[a-f0-9]{40}',row['commit'])):_fail('history_invalid')


def _history(con,anchor,config):
    objects=con.execute("SELECT type,name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
    if len(objects)!=1 or objects[0][:2]!=('table','codex_conducted_workflow_history'):_fail('history_invalid')
    normalize=lambda text:re.sub(r'\s','',text).lower().rstrip(';')
    if normalize(objects[0][2])!=normalize(_DDL):_fail('history_invalid')
    if con.execute('SELECT 1 FROM codex_conducted_workflow_history WHERE length(CAST(payload AS BLOB))>65536 LIMIT 1').fetchone():_fail('history_invalid')
    rows=con.execute('SELECT seq,kind,permit_id,payload FROM codex_conducted_workflow_history ORDER BY seq LIMIT 6').fetchall()
    kinds=[row[1] for row in rows]
    if not 2<=len(rows)<=5 or kinds!=['baseline','permit','reserved','consumed','finished'][:len(rows)]:_fail('history_invalid')
    bodies={}
    for index,(seq,kind,permit_id,raw) in enumerate(rows,1):
        if seq!=index or type(raw) is not str:_fail('history_invalid')
        body=_json(raw.encode('utf-8'))
        if _C(body).decode('utf-8')!=raw:_fail('history_invalid')
        if kind=='baseline':
            _same(body,dict(schema_version=1,kind='codex_conducted_workflow_continuation_baseline',journal_id=config['journal_id'],
                anchor_sha256=config['anchor_sha256'],inherited_history=anchor['inherited_history']))
            if permit_id is not None:_fail('history_invalid')
        elif permit_id!=config['permit_id'] or body.get('permit_id')!=permit_id:_fail('history_invalid')
        bodies[kind]=body
    permit=bodies['permit']
    _keys(permit,'schema_version kind journal_id permit_id anchor_sha256 workflow_sha256 registration_sha256 requested_model expires_at')
    if not _integer(permit['schema_version'],1,1) or permit['kind']!='codex_conducted_workflow_single_use_permit':_fail('scope_mismatch')
    for key in ('journal_id','permit_id','anchor_sha256','workflow_sha256','registration_sha256'):_same(permit[key],config[key])
    if permit['requested_model'] not in _MODELS:_fail('permit_invalid')
    if 'reserved' in bodies:
        row=bodies['reserved'];_keys(row,'permit_id context_sha256 workflow_sha256 plan_input_sha256 requested_model maximum_model_processes')
        _same(row['workflow_sha256'],config['workflow_sha256'])
        if not _integer(row['maximum_model_processes'],8,8):_fail('history_invalid')
        for key in ('context_sha256','plan_input_sha256'):_native_host._hash(row[key])
        _same(row['requested_model'],permit['requested_model'])
    if 'consumed' in bodies:_same(bodies['consumed'],dict(permit_id=config['permit_id'],reservation_sha256=_H(_C(bodies['reserved']))))
    if 'finished' in bodies:
        row=bodies['finished']
        _keys(row,'permit_id status local_model_processes cleanup_confirmed execution_receipt finalizer_receipt producer_receipts errors')
        if row['status'] not in ('completed','failed','unknown') or type(row['cleanup_confirmed']) is not bool:_fail('history_invalid')
        if row['local_model_processes'] is not None and not _integer(row['local_model_processes'],0,8):_fail('history_invalid')
    return bodies


def _append(con,journal,kind,permit,body):
    raw=_C(body)
    # O(1) reservation before each durable write; no hot directory inventory.
    if len(raw)>65536 or journal.stat().st_size+len(raw)+65536>33554432:_fail('evidence_limit')
    con.execute('INSERT INTO codex_conducted_workflow_history(kind,permit_id,payload) VALUES(?,?,?)',(kind,permit,raw.decode('utf-8')))


class _Cancel:
    def __init__(self,root):
        self.root=root;self.event=threading.Event();self.stop=threading.Event();self.thread=None;self.error=None
    def is_set(self):
        value=_load(self.root,'cancel-request.json',1024);_keys(value,'requested')
        if type(value['requested']) is not bool:_fail('cancel_invalid')
        return value['requested']
    def start(self):
        def watch():
            try:
                while not self.stop.wait(.02):
                    if self.is_set():self.event.set();return
            except BaseException as error:
                self.error=error;self.event.set()
        if self.is_set():self.event.set()
        self.thread=threading.Thread(target=watch,daemon=True,name='conducted-native-cancel')
        self.thread.start()
    def close(self):
        self.stop.set()
        if self.thread is not None:
            self.thread.join(2)
            if self.thread.is_alive():_fail('cancellation_unknown')
        if self.error is not None:raise self.error


class _OutputBudget:
    def __init__(self,root):
        self.files=self.bytes=0
        pending=[root];directories=0
        while pending:
            directory=pending.pop();directories+=1
            if directories>192:_fail('evidence_limit')
            with os.scandir(directory) as entries:
                for entry in entries:
                    info=entry.stat(follow_symlinks=False)
                    if info.st_file_attributes&0x400 or stat.S_ISLNK(info.st_mode):_fail('evidence_changed')
                    if stat.S_ISDIR(info.st_mode):
                        if len(Path(entry.path).relative_to(root).parts)>32:_fail('evidence_limit')
                        pending.append(Path(entry.path))
                    elif stat.S_ISREG(info.st_mode):self.files+=1;self.bytes+=info.st_size
                    else:_fail('evidence_changed')
                    if self.files>192 or self.bytes>33554432 or len(pending)>192:_fail('evidence_limit')
    def reserve(self,files,size):
        if self.files+files>192 or self.bytes+size>33554432:_fail('evidence_limit')
        self.files+=files;self.bytes+=size


def _save(path,value,budget,cap):
    raw=_C(value)
    if len(raw)>cap:_fail('evidence_limit')
    budget.reserve(1,len(raw))
    _native_host._active_guard(path,raw)
    if _read(path,cap)!=raw:_fail('evidence_changed')
    return _pin(raw)


def _handoff_raw(workflow_sha256,current,execution_pin,finalizer_pin):
    raw=_C(dict(schema_version=1,kind='codex_conducted_workflow_current_handoff',workflow_sha256=workflow_sha256,
        current_facts_plan=current,execution_receipt=execution_pin,finalizer_receipt=finalizer_pin))
    if len(raw)>_HANDOFF_CAP:_fail('evidence_limit')
    _json(raw)
    return raw


def _completed_scope(store,selection,config):
    with store.connection() as con:
        con.execute('PRAGMA query_only=ON');con.execute('BEGIN')
        if con.execute("SELECT 1 FROM intake_jobs WHERE state IN ('queued','running') LIMIT 1").fetchone():_fail('scope_mismatch')
        row=con.execute('''SELECT j.*,r.fingerprint,r.files_json,r.synthetic AS revision_synthetic,
            i.source_id,i.bundle,i.revision AS current_revision,i.status AS intake_status,i.analysis_json,
            s.root AS source_root,s.synthetic AS source_synthetic
            FROM intake_jobs j JOIN intake_revisions r ON r.intake_id=j.intake_id AND r.revision=j.revision
            JOIN intakes i ON i.intake_id=j.intake_id JOIN intake_sources s ON s.source_id=i.source_id
            WHERE j.job_id=? AND length(CAST(r.files_json AS BLOB))<=262144
            AND length(CAST(j.result_json AS BLOB))<=8388608
            AND length(CAST(i.analysis_json AS BLOB))<=8388608''',(selection['job_id'],)).fetchone()
        if (row is None or row['state']!='completed' or row['source_synthetic']!=1 or row['revision_synthetic']!=1
                or row['intake_status']=='upload_incomplete' or row['current_revision']!=selection['revision']):_fail('scope_mismatch')
        if type(row['source_root']) is not str or type(row['bundle']) is not str:_fail('scope_mismatch')
        source,bundle=Path(row['source_root']),Path(row['bundle'])
        if (not source.is_absolute() or '..' in source.parts or bundle.anchor or len(bundle.parts)!=1
                or row['bundle'] in ('.','..')):_fail('scope_mismatch')
        # Compare concrete references, retaining raw row/config strings and all
        # canonical payload/hash comparisons exactly as originally recorded.
        if _path(source/bundle,directory=True)[0]!=_path(config['registered_input_root'],directory=True)[0]:
            _fail('scope_mismatch')
        actual=dict(source_id=row['source_id'],intake_id=row['intake_id'],revision=row['revision'],job_id=row['job_id'],
            revision_fingerprint=row['fingerprint'],files=_json(row['files_json'].encode('utf-8')))
        _same(actual,selection)
        return dict(row)


def _prepare_current(store,selection,config,workflow,analysis,plan,owned):
    before=_completed_scope(store,selection,config)
    _same(plan['plan']['source_settings'],workflow['source_settings'])
    method={key:plan['plan'][key] for key in ('method_id','method_version','metric','reference_plane')}
    _same(method,dict(method_id='conducted_synthetic',method_version=1,metric='on',reference_plane='source_output'))
    current=_current_facts(config['store_root'],selection['intake_id'],method=method,
        expected_revision=selection['revision'],expected_context_sha256=workflow['context_sha256'])
    raw=_C(current)
    if len(raw)>8388608:_fail('evidence_limit')
    current=_json(raw);_keys(current,'context analysis facts_plan')
    facts=current['facts_plan'];_keys(facts,'schema_version kind status plan_input assembly_gaps questions')
    if facts['status']!='ready_for_simulation' or facts['plan_input']['status']!='ready_for_simulation':_fail('plan_not_ready')
    context=current['context']
    _same({key:context[key] for key in ('job_id','intake_id','revision')},
        {key:selection[key] for key in ('job_id','intake_id','revision')})
    _same(context['synthetic'],True);_same(_H(_C(context)),workflow['context_sha256'])
    _same(current['analysis'],analysis);_same(facts['plan_input'],plan)
    _same(_completed_scope(store,selection,config),before)
    owned['current_facts_plan']=current;owned['completed_scope']=before
    return context


def _prepare(root,config,scenario,owned):
    workflow_raw=_read(root/'registered-workflow.json',65536)
    if _H(workflow_raw)!=config['workflow_sha256']:_fail('binding_mismatch')
    workflow=_json(workflow_raw)
    fields='schema_version kind scenario_id context_sha256 analysis_sha256 plan_input_sha256 source_settings quantity allowed_tools measurement_ref catalog_sha256 schema_sha256'
    if type(workflow) is dict and _integer(workflow.get('schema_version'),2,3):fields+=' measurement_selection_policy'
    if type(workflow) is dict and _integer(workflow.get('schema_version'),3,3):fields+=' context_scope'
    _keys(workflow,fields)
    if (not _integer(workflow['schema_version'],1,3) or workflow['kind']!='codex_registered_conducted_workflow'
            or workflow['scenario_id']!=scenario):_fail('scope_mismatch')
    if workflow['schema_version']==3 and workflow['context_scope']!='completed_current_provided':_fail('scope_mismatch')
    _same(workflow['allowed_tools'],_TOOLS)
    quantity=workflow['quantity']
    _same(quantity,dict(metric='on',reference_plane='sensor_input',loss_compensation_applied=False,loss_compensation_sign=1))
    if workflow['schema_version']==1:
        if type(workflow['measurement_ref']) is not str or not 0<len(workflow['measurement_ref'])<=200:_fail('binding_mismatch')
    else:
        if workflow['measurement_ref'] is not None:_fail('binding_mismatch')
        policy=workflow['measurement_selection_policy'];_keys(policy,'schema_version kind')
        if (not _integer(policy['schema_version'],1,1)
                or policy['kind']!='unique_same_run_sensor_acquisition'):_fail('scope_mismatch')
    manifest=_load(root,'registered-intake-v1.json',262144)
    files=manifest['registered_intake']['files']
    if type(files) is not list or len(files)>192 or sum(item['bytes'] for item in files)>33554432:_fail('evidence_limit')
    selection=_native_host._registration(root,config,scenario)
    if workflow['schema_version']==3:
        if any(Path(row['path']).suffix.lower() not in ('.txt','.pdf') for row in selection['files']):_fail('unsupported_schema')
    analysis_raw=_read(root/'analysis.json',262144);plan_raw=_read(root/'plan-input.json',262144)
    if _H(analysis_raw)!=workflow['analysis_sha256'] or _H(plan_raw)!=workflow['plan_input_sha256']:_fail('binding_mismatch')
    analysis,plan=_json(analysis_raw),_json(plan_raw)
    if _C(plan)!=plan_raw or _C(analysis)!=analysis_raw:_fail('binding_mismatch')
    store=Store.open_existing(config['store_root']);owned['store']=store
    if workflow['schema_version']==3:
        context=_prepare_current(store,selection,config,workflow,analysis,plan,owned)
    else:
        _native_host._dedicated(store,selection['job_id'])
        context=prepare_registered_synthetic_context(store,selection,producer_name=analysis['producer']['name'])
        _native_host._dedicated(store,selection['job_id'])
        _same(_H(_C(context)),workflow['context_sha256'])
        _same(plan['plan']['source_settings'],workflow['source_settings'])
        method={key:plan['plan'][key] for key in ('method_id','method_version','metric','reference_plane')}
        _same(method,dict(method_id='conducted_synthetic',method_version=1,metric='on',reference_plane='source_output'))
        rebuilt=build_conducted_twin_plan_input(context,analysis,expected_revision=context['revision'],expected_context_sha256=workflow['context_sha256'],
            source_settings=workflow['source_settings'],basis=plan['plan']['basis_refs'],method=method)
        _same(plan,rebuilt)
        if plan['status']!='ready_for_simulation':_fail('plan_not_ready')
    catalog=_read(root/'catalog.json',1048576);schema=_read(root/'response-schema.json',65536)
    if _H(catalog)!=workflow['catalog_sha256'] or _H(schema)!=workflow['schema_sha256']:_fail('binding_mismatch')
    # Historical profiles are read without migration; the native fresh-run
    # boundary below still requires the current exact provider profile.
    if not is_known_response_schema_bytes(schema):_fail('unsupported_schema')
    return workflow,context,analysis,plan,schema


def _observe(execution,evidence,model,entered):
    if not entered:return 0,True,[]
    try:
        loop=execution['loop'];started=loop['budget']['producer_calls_started'];steps=loop['steps']
        if not _integer(started,0,8) or type(steps) is not list or len(steps)!=started:return None,False,[]
        total=0;pins=[];cleanup=True
        for index,step in enumerate(steps,1):
            if step['index']!=index:return None,False,pins
            raw=_read(evidence/'loop/calls'/f'{index:04d}'/'producer/receipt.json',262144)
            receipt=_json(raw)
            _same(receipt,step['producer']['receipt'])
            original_pin=step['producer']['receipt_sha256']
            if (receipt['kind']!='codex_cli_response_receipt' or receipt['model']['requested']!=model
                    or receipt['bindings']['prompt_sha256']!=step['artifacts']['prompt']['sha256']
                    or receipt['bindings']['schema_sha256']!=loop['declaration']['schema_sha256']
                    or original_pin is not None and _H(_C(receipt))!=original_pin):return None,False,pins
            if original_pin is None and receipt['status']!='failed':return None,False,pins
            actual=receipt['lifecycle']['model_process_started']
            if type(actual) is not bool:return None,False,pins
            attempts=receipt['attempts']['model_process_attempts']
            if not _integer(attempts,0,1) or actual and attempts!=1:return None,False,pins
            if not actual and attempts!=0:return None,False,pins
            total+=int(actual)
            cleanup=cleanup and all(receipt['cleanup'][key] is True for key in ('version_child_reaped','readers_joined','pipes_closed','artifacts_closed'))
            cleanup=cleanup and (receipt['cleanup']['model_child_reaped'] is True or not actual and receipt['cleanup']['model_child_reaped'] is None)
            pins.append(dict(index=index,**_pin(raw)))
        cleanup=cleanup and all(loop['cleanup'][key] is True for key in ('host_artifacts_closed','runtime_references_released'))
        return total,cleanup,pins
    except _CONTROL:raise
    except Exception:return None,False,[]


def _run(scenario,model):
    record=dict(schema_version=1,kind='codex_registered_conducted_workflow_host_receipt',status='not_run',phase='profile',scenario_id=scenario,
        requested_model=model,history=None,reservation=None,execution=None,finalization=None,errors=[],verification=dict(
            operator_scope='not_validated',execution_scope='one_registered_synthetic_conducted_workflow',origin_authenticated=False,
            remote_model_identity_verified=False,measurement='not_assessed',hardware_verified=False))
    con=guard=primary=cancel=None;consumed=entered=claimed=rollback_attempted=False;owned=dict(store=None)
    execution=finalized=None;execution_pin=finalizer_pin=None;actual=None;cleanup=False;pins=[]
    handoff=None;budget=None;handoff_merged=False;execution_options={}
    root=config=anchor=journal=evidence=None
    def error(exc,phase):
        nonlocal primary
        if primary is None:primary=exc
        if type(exc) is _Failure:code=str(exc)
        elif isinstance(exc,(IntakePlanVirtualExecutionError,ConductedExecutionResultFinalizerError,StoreOpenError)):code=exc.code
        elif isinstance(exc,_native_host._Failure):
            literal=str(exc);code=_PREFIX+literal.removeprefix('codex_registered_intake_host_') if re.fullmatch('codex_registered_intake_host_[a-z_]+',literal) else _PREFIX+'native_input_rejected'
        else:code=_PREFIX+('profile_missing' if isinstance(exc,FileNotFoundError) else 'interrupted' if isinstance(exc,_CONTROL) else 'operation_failed')
        if len(record['errors'])<8:record['errors'].append(dict(phase=phase,code=code))
        record['status']='unknown' if claimed or entered else 'not_run'
        if record['history'] is not None and claimed:record['history']['actual_total_model_processes']=None
    try:
        root,_=_path(_profile_root(),directory=True)
        try:(root/'workflow-claimed.json').lstat()
        except FileNotFoundError:pass
        else:_fail('permit_already_consumed')
        anchor_raw=_read(root/'root-continuation-anchor.json',65536);anchor=_json(anchor_raw);_anchor(anchor)
        config_raw=_read(root/'operator-control.json',16384);config=_json(config_raw)
        _keys(config,'schema_version kind anchor_sha256 journal_id permit_id registration_sha256 workflow_sha256 registered_input_root store_root executable')
        if not _integer(config['schema_version'],1,1) or config['kind']!='codex_registered_conducted_workflow_control':_fail('scope_mismatch')
        _same(config['anchor_sha256'],_H(anchor_raw))
        for key in ('journal_id','permit_id'):_native_host._id(config[key])
        for key in ('registration_sha256','workflow_sha256'):_native_host._hash(config[key])
        source,_=_path(config['registered_input_root'],directory=True);state,_=_path(config['store_root'],directory=True)
        executable,_=_path(config['executable'],directory=False)
        if executable.name.lower()!='codex.exe' or any(a==b or a.is_relative_to(b) or b.is_relative_to(a) for a,b in ((root,source),(root,state),(source,state))):_fail('invalid_path')
        evidence,_=_path(root/'runs'/config['permit_id'],directory=True)
        if any(evidence.iterdir()):_fail('evidence_not_empty')
        record['phase']='history';journal,info=_path(root/'workflow-continuation.sqlite3',directory=False)
        if info.st_size>33554432:_fail('evidence_limit')
        guard=journal.open('rb');con=sqlite3.connect(journal.as_uri()+'?mode=rw',uri=True,timeout=0,isolation_level=None)
        con.execute('PRAGMA trusted_schema=OFF')
        _,after=_path(journal,directory=False)
        if ((after.st_dev,after.st_ino)!=(info.st_dev,info.st_ino)
                or (os.fstat(guard.fileno()).st_dev,os.fstat(guard.fileno()).st_ino)!=(info.st_dev,info.st_ino)):_fail('binding_mismatch')
        con.execute('BEGIN IMMEDIATE');events=_history(con,anchor,config)
        if len(events)!=2:_fail('permit_already_consumed')
        permit=events['permit'];_same(permit['requested_model'],model);_native_host._expiry(permit['expires_at'])
        record['phase']='registration';workflow,context,analysis,plan,schema=_prepare(root,config,scenario,owned)
        if not is_current_response_schema_bytes(schema):_fail('unsupported_schema')
        closing_store=owned['store'];owned['store']=None;closing_store.close()
        cancel=_Cancel(root)
        if cancel.is_set():_fail('cancelled')
        if _read(root/'root-continuation-anchor.json',65536)!=anchor_raw or _read(root/'operator-control.json',16384)!=config_raw:_fail('binding_mismatch')
        selection=_native_host._registration(root,config,scenario);_native_host._expiry(permit['expires_at'])
        if workflow['schema_version']==3:
            store=Store.open_existing(config['store_root']);owned['store']=store
            _same(_completed_scope(store,selection,config),owned['completed_scope'])
            owned['store']=None;store.close()
            current=owned['current_facts_plan']
            maximum=_handoff_raw(config['workflow_sha256'],current,
                dict(bytes=262144,sha256='0'*64),dict(bytes=2097152,sha256='0'*64))
            budget=_OutputBudget(evidence);budget.reserve(1,len(maximum))
            reservation=dict(files=budget.files+_TAIL_FILES,bytes=budget.bytes+_TAIL_BYTES)
            if reservation['files']>192 or reservation['bytes']>33554432:_fail('evidence_limit')
            handoff=(current,len(maximum));execution_options['evidence_reservation']=reservation
        record['verification']['operator_scope']='native_operator_control'
        reserved=dict(permit_id=config['permit_id'],context_sha256=workflow['context_sha256'],workflow_sha256=config['workflow_sha256'],
            plan_input_sha256=workflow['plan_input_sha256'],requested_model=model,maximum_model_processes=8)
        record['phase']='reserve';claimed=True
        _native_host._active_guard(root/'workflow-claimed.json',_C(reserved))
        _append(con,journal,'reserved',config['permit_id'],reserved);con.commit()
        record['reservation']=dict(permit_id=config['permit_id'],state='reserved',reservation_sha256=_H(_C(reserved)))
        record['phase']='consume';con.execute('BEGIN IMMEDIATE');events=_history(con,anchor,config)
        _same(events.get('reserved'),reserved)
        if len(events)!=3:_fail('permit_already_consumed')
        _native_host._expiry(permit['expires_at'])
        _append(con,journal,'consumed',config['permit_id'],dict(permit_id=config['permit_id'],reservation_sha256=_H(_C(reserved))));con.commit();consumed=True
        record['reservation']['state']='consumed';record['phase']='execution';cancel.start();entered=True
        try:
            execution=_execute(context,analysis,plan,expected_revision=context['revision'],expected_context_sha256=workflow['context_sha256'],
                expected_plan_input_sha256=workflow['plan_input_sha256'],catalog_path=root/'catalog.json',catalog_sha256=workflow['catalog_sha256'],
                response_schema_bytes=schema,executable=executable,requested_model=model,scenario='normal',evidence_dir=evidence/'loop',
                execution_origin='actual_cli',cancel_event=cancel.event,quantity=workflow['quantity'],**execution_options)
        except IntakePlanVirtualExecutionError as exc:
            execution=exc.receipt;error(exc,'execution')
        closing_cancel=cancel;cancel=None;closing_cancel.close()
        if handoff is None:budget=_OutputBudget(evidence)
        else:
            observed=_OutputBudget(evidence);budget.reserve(observed.files,observed.bytes);handoff_merged=True
        execution_pin=_save(evidence/'execution-receipt.json',execution,budget,262144)
        actual,cleanup,pins=_observe(execution,evidence,model,entered)
        record['execution']=dict(run_id=execution['binding']['run_id'],runtime_instance_id=execution['binding']['runtime_instance_id'],
            status=execution['status'],failure=execution['failure'],receipt=execution_pin,producer_receipts=pins)
        if actual is None or not cleanup:_fail('execution_unknown')
        record['phase']='finalizer'
        budget.reserve(8,3*1048576)
        selection_options={}
        if workflow['schema_version'] in (2,3):selection_options['measurement_selection_policy']=workflow['measurement_selection_policy']
        try:
            finalized=_finalize(execution,expected_execution_sha256=_H(_C(execution)),evidence_dir=evidence/'loop',measurement_ref=workflow['measurement_ref'],
                workspace_root=evidence,artifact_name='conducted-draft',**selection_options)
        except ConductedExecutionResultFinalizerError as exc:
            finalized=exc.receipt
        finalizer_pin=_save(evidence/'finalizer-receipt.json',finalized,budget,2097152)
        result=finalized['result'];artifact=finalized['artifact']
        record['finalization']=dict(status=finalized['status'],result_status=result['status'] if result else None,artifact=artifact,failure=finalized['failure'],receipt=finalizer_pin)
        record['status']='completed' if execution['failure'] is None and finalized['status']=='stored' and result and result['status']=='recorded' else 'failed'
    except BaseException as exc:error(exc,record['phase'])
    finally:
        if owned['store'] is not None:
            closing_store=owned['store'];owned['store']=None
            try:closing_store.close()
            except BaseException as exc:error(exc,'store_close')
        if cancel is not None:
            try:cancel.close()
            except BaseException as exc:error(exc,'cancellation_close')
        if handoff is not None:
            try:
                if not handoff_merged:
                    observed=_OutputBudget(evidence);budget.reserve(observed.files,observed.bytes);handoff_merged=True
                raw=_handoff_raw(config['workflow_sha256'],handoff[0],execution_pin,finalizer_pin)
                if len(raw)>handoff[1]:_fail('evidence_limit')
                path=evidence/'current-handoff.json';_native_host._active_guard(path,raw)
                if _read(path,_HANDOFF_CAP)!=raw:_fail('evidence_changed')
            except BaseException as exc:error(exc,'current_handoff')
        if consumed:
            try:
                actual,cleanup,pins=_observe(execution,evidence,model,entered)
                if actual is None or not cleanup:record['status']='unknown'
                if con.in_transaction:rollback_attempted=True;con.rollback()
                con.execute('BEGIN IMMEDIATE');events=_history(con,anchor,config)
                if len(events)!=4:_fail('history_unsettled')
                finished=dict(permit_id=config['permit_id'],status=record['status'],local_model_processes=actual,cleanup_confirmed=cleanup,
                    execution_receipt=execution_pin,finalizer_receipt=finalizer_pin,producer_receipts=pins,errors=record['errors'].copy())
                _append(con,journal,'finished',config['permit_id'],finished);con.commit();_history(con,anchor,config)
                record['reservation']['state']='finished';record['phase']='finished'
                record['history']=dict(inherited_model_processes=17,local_model_processes=actual,known_total_model_processes=17+actual if actual is not None else 17,
                    actual_total_model_processes=17+actual if actual is not None and cleanup else None,usage_complete=False,unknown_usage_components=None,cost=None)
            except BaseException as exc:error(exc,'finish');record['history']=None
        if con is not None:
            try:
                if con.in_transaction and not rollback_attempted:rollback_attempted=True;con.rollback()
            except BaseException as exc:error(exc,'ledger_rollback')
            finally:
                try:_close_ledger(con)
                except BaseException as exc:error(exc,'ledger_close')
        if guard is not None:
            try:guard.close()
            except BaseException as exc:error(exc,'ledger_guard_close')
    if isinstance(primary,_CONTROL):raise primary
    return record


def main(argv=None)->int:
    args=sys.argv[1:] if argv is None else argv
    if type(args) is list and len(args)==1 and type(args[0]) is str and args[0] in ('--help','-h'):
        sys.stdout.write('Usage: --scenario-id ID --model gpt-6.1-sol|gpt-6-astra\n');return 0
    try:
        if type(args) is not list or len(args)!=4 or not all(type(x) is str for x in args):_fail('invalid_arguments')
        options=dict(zip(args[::2],args[1::2]))
        if set(options)!= {'--scenario-id','--model'} or options['--model'] not in _MODELS:_fail('invalid_arguments')
        _native_host._id(options['--scenario-id'])
    except Exception:
        sys.stderr.write(canonical(dict(schema_version=1,kind='codex_registered_conducted_workflow_host_error',status='not_run',phase='arguments',code=_PREFIX+'invalid_arguments'))+'\n');return 2
    record=_run(options['--scenario-id'],options['--model'])
    stream=sys.stdout if record['status']=='completed' else sys.stderr
    raw=_C(record)
    if len(raw)>69632:_fail('output_limit')
    stream.write(raw.decode('utf-8')+'\n')
    return {'completed':0,'not_run':3,'failed':4,'unknown':5}[record['status']]


def _process_main():
    status=5;control_status=None
    try:
        for stream in (sys.stdout,sys.stderr):stream.reconfigure(encoding='utf-8',errors='strict',newline='\n')
        status=main()
    except KeyboardInterrupt:status=control_status=130
    except (SystemExit,GeneratorExit,MemoryError):status=control_status=5
    except Exception:status=5
    for stream in (sys.stdout,sys.stderr):
        try:stream.flush()
        except BaseException as error:
            if control_status is None:control_status=130 if isinstance(error,KeyboardInterrupt) else 5
            os._exit(control_status)
    return status


if __name__=='__main__':raise SystemExit(_process_main())

"""One explicit operator preparation; data validation never grants authority."""
import errno
import os
from pathlib import Path
import sqlite3
import sys

from . import control_packet_prepare as _native
from . import codex_registered_conducted_workflow_host as _host
from .intake_plan_virtual_execution import _snapshot
from .intake_conducted_twin_plan import build_conducted_twin_plan_input
from .intake_jobs import prepare_registered_synthetic_context
from .store import Store,canonical

__all__=['preflight_conducted_workflow_inputs','prepare_registered_conducted_workflow','main']
_PREFIX='codex_conducted_workflow_registration_'
_CONTROL=(KeyboardInterrupt,SystemExit,GeneratorExit,MemoryError)
_C=lambda value:canonical(value).encode('utf-8')
_H=_host._H
_read=_host._read
_json=_host._json
_keys=_host._keys
_MODELS=_host._MODELS
_TARGET='codex-conducted-workflow-host'
_STAGE=_TARGET+'.preparing'
_OPERATOR='codex-conducted-workflow-operator'
_FILES={'registered-intake-v1.json':262144,'analysis.json':262144,'plan-input.json':262144,'catalog.json':1048576,'response-schema.json':65536}
_LIMITS=dict(allowed_models=list(_MODELS),maximum_workflows=1,maximum_model_processes=8,loop_seconds=180,producer_seconds=60,automatic_retries=0,
    output_bytes=262144,evidence_files=192,evidence_bytes=33554432,synthetic_only=True,hardware_network_output_motion_submission=False,scope_is_existing_delegation_not_new_global_budget=True)


class _Failure(ValueError):pass
def _fail(code):raise _Failure(_PREFIX+code)
def _same(left,right):
    if _C(left)!=_C(right):_fail('binding_mismatch')
def _operator_parent():return _host._native_host._control_root().parent
def _pin(raw):return dict(bytes=len(raw),sha256=_H(raw))
def _close_directory(fd):
    os.close(fd)
    try:os.fstat(fd)
    except OSError as error:
        if error.errno==errno.EBADF:return
        raise
    _fail('close_uncertain')
def _text(value):
    if type(value) is not str or not value.strip() or len(value)>2048:_fail('delegation_invalid')


def preflight_conducted_workflow_inputs(context,analysis,plan_input,*,quantity,allowed_tools,measurement_ref):
    result=dict(schema_version=1,kind='conducted_workflow_input_preflight',status='invalid',pins=None,gaps=[],failure=None,execution_authority=False)
    try:
        context,analysis,plan,quantity,tools,ref=_snapshot([context,analysis,plan_input,quantity,allowed_tools,measurement_ref])
        if type(plan) is not dict or plan.get('status')!='ready_for_simulation':
            result['gaps']=plan.get('gaps',[]) if type(plan) is dict else [];_fail('plan_not_ready')
        _same(quantity,dict(metric='on',reference_plane='sensor_input',loss_compensation_applied=False,loss_compensation_sign=1))
        _same(tools,_host._TOOLS)
        if type(ref) is not str or not 0<len(ref)<=200:_fail('reference_invalid')
        method={key:plan['plan'][key] for key in ('method_id','method_version','metric','reference_plane')}
        _same(method,dict(method_id='conducted_synthetic',method_version=1,metric='on',reference_plane='source_output'))
        rebuilt=build_conducted_twin_plan_input(context,analysis,expected_revision=context['revision'],expected_context_sha256=_H(_C(context)),
            source_settings=plan['plan']['source_settings'],basis=plan['plan']['basis_refs'],method=method)
        _same(plan,rebuilt)
        if context['synthetic'] is not True or rebuilt['status']!='ready_for_simulation':_fail('plan_not_ready')
        result.update(status='validated',pins=dict(context_sha256=_H(_C(context)),analysis_sha256=_H(_C(analysis)),
            plan_input_sha256=_H(_C(plan)),source_settings_sha256=_H(_C(plan['plan']['source_settings'])),quantity_sha256=_H(_C(quantity))))
    except _CONTROL:raise
    except Exception as error:
        result['failure']=dict(code=str(error) if type(error) is _Failure else _PREFIX+'input_invalid')
    return result


class _IO:
    """Native pinned inputs, exclusive writes, once-only owned close, NX rename."""
    def __init__(self,parent):
        self.backend=_native._WindowsIO();self.parent=parent
        self.files={};self.reads=[];self.close_errors=[];self.dir_attempted=set();self.output_files=0;self.output_bytes=0
        self.claimed=False;self.published=False;self.publication_attempted=False
        try:self.tree=_native._Tree(parent,self.backend)
        except BaseException:
            try:self.close_dirs()
            except BaseException:pass
            raise
    def adopt(self,fd):
        token=dict(fd=fd,attempted=False);self.files[fd]=token;return token
    def close_file(self,token):
        if token['attempted']:return
        token['attempted']=True;fd=token['fd']
        try:
            os.close(fd)
            try:os.fstat(fd)
            except OSError as error:
                if error.errno==errno.EBADF:return
                raise
            _fail('close_uncertain')
        except BaseException as error:self.close_errors.append(error);raise
    def read(self,path,cap):
        path=_native._local_path(path);tree=_native._Tree(path.parent,self.backend)
        before=tree.file_stat(path)
        if before.st_nlink!=1 or before.st_size>cap:_fail('input_limit')
        fd=self.backend._relative(self.backend.directories[path.parent],path.name,directory=False,share=1)
        token=self.adopt(fd)
        if _native._stamp(self.backend.info(fd,directory=False))!=_native._stamp(before):_fail('source_changed')
        raw=_read(path,cap)
        self.reads.append((path,tree,token,_native._stamp(before),_H(raw)))
        return raw
    def current(self):
        for path,tree,token,stamp,sha in self.reads:
            if (_native._stamp(tree.file_stat(path))!=stamp or _native._stamp(self.backend.info(token['fd'],directory=False))!=stamp
                    or _H(_read(path,stamp[2]))!=sha):_fail('source_changed')
    def reserve(self,files,size):
        if self.output_files+files>32 or self.output_bytes+size>8388608:_fail('output_limit')
        self.output_files+=files;self.output_bytes+=size
    def write(self,path,raw):
        self.reserve(1,len(raw));self.tree.directory(path.parent,create=True)
        fd=self.backend.create_file(path);token=self.adopt(fd);primary=None
        try:
            if _native._write_all(fd,raw,'packet_prepare_copy_failed')!=_H(raw):_fail('write_failed')
            os.fsync(fd)
            if self.backend.info(fd,directory=False).st_size!=len(raw):_fail('write_failed')
        except BaseException as error:primary=error;raise
        finally:
            try:self.close_file(token)
            except BaseException:
                if primary is None:raise
        if _read(path,len(raw))!=raw:_fail('write_failed')
        return _pin(raw)
    def claim(self,stage):
        if stage.parent!=self.parent or stage.name!=_STAGE:_fail('path_invalid')
        fd=self.backend._relative(self.backend.directories[self.parent],stage.name,directory=True,create=True,access=0x1100A1,share=3)
        self.backend.directories[stage]=fd;self.backend.held.append(fd);self.claimed=True
        self.tree.directory(stage)
        if stage.resolve(strict=True)!=stage:_fail('path_invalid')
    def database(self,path,baseline,permit,config,anchor):
        self.reserve(2,2097152)  # New DB plus its bounded transient rollback journal.
        fd=self.backend._relative(self.backend.directories[path.parent],path.name,directory=False,create=True,access=0xC0100000,share=3)
        token=self.adopt(fd);con=None;primary=None
        try:
            con=sqlite3.connect(path.as_uri()+'?mode=rw',uri=True,timeout=0,isolation_level=None)
            con.execute('PRAGMA trusted_schema=OFF');con.execute('PRAGMA synchronous=FULL');con.execute('BEGIN IMMEDIATE')
            con.execute(_host._DDL)
            for kind,identifier,body in [('baseline',None,baseline),('permit',permit['permit_id'],permit)]:
                raw=_C(body)
                if len(raw)>65536:_fail('output_limit')
                con.execute('INSERT INTO codex_conducted_workflow_history(kind,permit_id,payload) VALUES(?,?,?)',(kind,identifier,raw.decode('utf-8')))
            con.commit();events=_host._history(con,anchor,config)
            if set(events)!= {'baseline','permit'}:_fail('sql_invalid')
            closing=con;con=None;_close_sql(closing)
            os.fsync(fd)
            if self.backend.info(fd,directory=False).st_size>1048576:_fail('output_limit')
        except BaseException as error:primary=error;raise
        finally:
            if con is not None:
                try:_close_sql(con)
                except BaseException as error:
                    self.close_errors.append(error)
                    if primary is None:primary=error
            try:self.close_file(token)
            except BaseException as error:
                if primary is None:primary=error
            if primary is not None and sys.exc_info()[0] is None:raise primary
        raw=_read(path,1048576);return _pin(raw)
    def close_files(self):
        first=None
        for token in list(self.files.values()):
            if not token['attempted']:
                try:self.close_file(token)
                except BaseException as error:
                    if first is None:first=error
        if first is not None:raise first
    def publish(self,stage,target):
        if stage.parent!=self.parent or target.parent!=self.parent or stage.name!=_STAGE or target.name!=_TARGET:_fail('path_invalid')
        if stage.resolve(strict=True)!=stage or target.resolve(strict=False)!=target:_fail('path_invalid')
        if _native._destination_exists(self.tree,target):_fail('destination_exists')
        # Windows directory rename requires descendant directory handles closed.
        first=None
        for path,fd in list(self.backend.directories.items()):
            if path!=stage and path.is_relative_to(stage):
                self.dir_attempted.add(fd)
                try:_close_directory(fd)
                except BaseException as error:
                    self.close_errors.append(error)
                    if first is None:first=error
                self.backend.directories.pop(path);self.tree.directories.pop(path,None)
        if first is not None:raise first
        self.backend.info(self.backend.directories[stage],directory=True);self.backend.info(self.backend.directories[self.parent],directory=True)
        self.publication_attempted=True
        _publish_directory(self.backend,self.backend.directories[stage],self.backend.directories[self.parent],target.name)
        self.published=True
        for old in list(self.backend.directories):
            if old.is_relative_to(stage):self.backend.directories[target/old.relative_to(stage)]=self.backend.directories.pop(old)
        for old in list(self.tree.directories):
            if old.is_relative_to(stage):self.tree.directories[target/old.relative_to(stage)]=self.tree.directories.pop(old)
    def close_dirs(self):
        first=None
        for fd in reversed(self.backend.held):
            if fd in self.dir_attempted:continue
            self.dir_attempted.add(fd)
            try:_close_directory(fd)
            except BaseException as error:
                self.close_errors.append(error)
                if first is None:first=error
        if first is not None:raise first


def _publish_directory(backend,descriptor,parent,name):
    # FileRenameInformation, ReplaceIfExists=0, held DELETE-capable source dir.
    c=backend.ctypes;encoded=name.encode('utf-16-le')
    buffer=c.create_string_buffer(backend.LinkInformation.FileName.offset+len(encoded))
    info=c.cast(buffer,c.POINTER(backend.LinkInformation)).contents
    info.ReplaceIfExists=0;info.RootDirectory=backend.crt.get_osfhandle(parent);info.FileNameLength=len(encoded)
    c.memmove(c.addressof(buffer)+backend.LinkInformation.FileName.offset,encoded,len(encoded))
    status=backend.IOStatus()
    backend._status(backend.native.NtSetInformationFile(backend.crt.get_osfhandle(descriptor),c.byref(status),buffer,len(buffer),10))


def _close_sql(con):
    con.close()
    try:con.execute('SELECT 1')
    except sqlite3.ProgrammingError:return
    _fail('sql_close_uncertain')


def _authority(value):
    _keys(value,'schema_version kind authority_source manual_preparation_reference action scope prepared_manifest_sha256 inherited_history')
    if type(value['schema_version']) is not int or value['schema_version']!=1 or value['kind']!='codex_root_conducted_workflow_manual_preparation':_fail('delegation_invalid')
    _keys(value['authority_source'],'kind instruction_reference authority_is_not_inferred_from_uploaded_documents_or_model_output')
    source=value['authority_source']
    if source['kind']!='direct_human_instructions_to_this_root_thread' or source['authority_is_not_inferred_from_uploaded_documents_or_model_output'] is not True:_fail('delegation_invalid')
    _text(source['instruction_reference']);_text(value['manual_preparation_reference'])
    if value['action']!='prepare_one_registered_synthetic_conducted_workflow_profile':_fail('scope_mismatch')
    _same(value['scope'],_LIMITS);_host._native_host._hash(value['prepared_manifest_sha256'])
    anchor=dict(schema_version=1,kind='codex_conducted_workflow_root_anchor',inherited_history=value['inherited_history'])
    _host._anchor(anchor);return anchor


def prepare_registered_conducted_workflow(*,scenario_id,requested_model):
    result=dict(schema_version=1,kind='codex_conducted_workflow_registration',status='not_prepared',phase='operator',scenario_id=scenario_id if type(scenario_id) is str else None,
        requested_model=requested_model if type(requested_model) is str else None,operator_source=None,profile=None,files={},errors=[],verification=dict(
            authority_scope='not_validated',data_preflight='not_run',dispatch='not_invoked',same_account_arbitrary_code_defense=False))
    io=store=None;control=None;primary=None;source=None;operator=stage=target=None;filepins={};seen_errors=set()
    def error(exc,phase):
        nonlocal control,primary
        if id(exc) in seen_errors:return
        seen_errors.add(id(exc))
        if primary is None:primary=exc
        if isinstance(exc,_CONTROL) and control is None:control=exc
        code=str(exc) if type(exc) is _Failure else _PREFIX+('missing_input' if isinstance(exc,FileNotFoundError) else 'existing_destination' if isinstance(exc,FileExistsError) else 'interrupted' if isinstance(exc,_CONTROL) else 'native_or_data_rejected')
        if len(result['errors'])<8:result['errors'].append(dict(phase=phase,code=code))
        result['status']='publication_uncertain' if io is not None and io.publication_attempted else 'failed' if io is not None and io.claimed else 'not_prepared'
    try:
        _host._native_host._id(scenario_id)
        if type(requested_model) is not str or requested_model not in _MODELS:_fail('model_invalid')
        parent=_native._local_path(_operator_parent());operator=parent/_OPERATOR;stage=parent/_STAGE;target=parent/_TARGET
        io=_IO(parent);io.tree.directory(operator)
        for path in (stage,target,operator/'preparation-record-v1.json',operator/'preparation-complete-v1.json',operator/'preparation-failure-v1.json'):
            if _native._destination_exists(io.tree,path):_fail('destination_exists')
        source_raw=io.read(operator/'root-delegation-v1.json',65536);source=_json(source_raw);anchor=_authority(source)
        result['operator_source']=_pin(source_raw)
        meta_raw=io.read(operator/'prepared-inputs-v1.json',65536)
        if _H(meta_raw)!=source['prepared_manifest_sha256']:_fail('binding_mismatch')
        meta=_json(meta_raw);_keys(meta,'schema_version kind scenario_id requested_model journal_id permit_id registered_input_root store_root executable expires_at quantity allowed_tools measurement_ref files')
        if type(meta['schema_version']) is not int or meta['schema_version']!=1 or meta['kind']!='codex_conducted_workflow_prepared_data':_fail('data_invalid')
        _same((meta['scenario_id'],meta['requested_model']),(scenario_id,requested_model))
        for key in ('journal_id','permit_id'):_host._native_host._id(meta[key])
        _native._valid_segment(meta['permit_id'])
        _host._native_host._expiry(meta['expires_at'])
        original,_=_host._native_host._path(meta['registered_input_root'],directory=True)
        state,_=_host._native_host._path(meta['store_root'],directory=True)
        executable,_=_host._native_host._path(meta['executable'],directory=False)
        if executable.name.lower()!='codex.exe':_fail('path_invalid')
        for a,b in [(original,state)]+[(a,b) for a in (original,state) for b in (operator,stage,target)]:
            if a==b or a.is_relative_to(b) or b.is_relative_to(a):_fail('path_overlap')
        if type(meta['files']) is not dict or set(meta['files'])!=set(_FILES):_fail('data_invalid')
        rawfiles={}
        for leaf,cap in _FILES.items():
            raw=io.read(operator/'prepared-data'/leaf,cap);_same(_pin(raw),meta['files'][leaf]);rawfiles[leaf]=raw
        analysis=_json(rawfiles['analysis.json']);plan=_json(rawfiles['plan-input.json'])
        if _C(analysis)!=rawfiles['analysis.json'] or _C(plan)!=rawfiles['plan-input.json']:_fail('canonical_required')
        schema=rawfiles['response-schema.json']
        if len(schema)!=3052 or _H(schema)!=_host._SCHEMA_SHA:_fail('unsupported_schema')
        registration=_json(rawfiles['registered-intake-v1.json'])
        _keys(registration,'schema_version kind scenario_id synthetic registered_intake')
        if (type(registration['schema_version']) is not int or registration['schema_version']!=1
                or registration['kind']!='codex_registered_synthetic_intake' or registration['synthetic'] is not True
                or registration['scenario_id']!=scenario_id):_fail('data_invalid')
        selection=registration['registered_intake']
        if type(selection['files']) is not list or len(selection['files'])>192 or sum(row['bytes'] for row in selection['files'])>33554432:_fail('input_limit')
        check_config=dict(registration_sha256=_H(rawfiles['registered-intake-v1.json']),registered_input_root=str(original))
        # Genuine G3 verifies the Store's synthetic registration before reading
        # the original filesystem folder, rather than trusting manifest.synthetic.
        store=Store.open_existing(str(state));_host._native_host._dedicated(store,selection['job_id'])
        context=prepare_registered_synthetic_context(store,selection,producer_name=analysis['producer']['name'])
        _host._native_host._dedicated(store,selection['job_id'])
        preflight=preflight_conducted_workflow_inputs(context,analysis,plan,quantity=meta['quantity'],allowed_tools=meta['allowed_tools'],measurement_ref=meta['measurement_ref'])
        if preflight['status']!='validated':_fail('preflight_rejected')
        closing=store;store=None;closing.close()
        _host._native_host._registration(operator/'prepared-data',check_config,scenario_id)
        for row in selection['files']:
            raw=io.read(original/row['path'],33554432)
            if _pin(raw)!=dict(bytes=row['bytes'],sha256=row['sha256']):_fail('source_changed')
        result['verification'].update(authority_scope='fixed_native_root_manual_preparation',data_preflight='validated')
        workflow=dict(schema_version=1,kind='codex_registered_conducted_workflow',scenario_id=scenario_id,context_sha256=preflight['pins']['context_sha256'],
            analysis_sha256=_H(rawfiles['analysis.json']),plan_input_sha256=_H(rawfiles['plan-input.json']),source_settings=plan['plan']['source_settings'],
            quantity=meta['quantity'],allowed_tools=meta['allowed_tools'],measurement_ref=meta['measurement_ref'],catalog_sha256=_H(rawfiles['catalog.json']),schema_sha256=_H(schema))
        config=dict(schema_version=1,kind='codex_registered_conducted_workflow_control',anchor_sha256=_H(_C(anchor)),journal_id=meta['journal_id'],permit_id=meta['permit_id'],
            registration_sha256=_H(rawfiles['registered-intake-v1.json']),workflow_sha256=_H(_C(workflow)),registered_input_root=str(original),store_root=str(state),executable=str(executable))
        baseline=dict(schema_version=1,kind='codex_conducted_workflow_continuation_baseline',journal_id=meta['journal_id'],anchor_sha256=config['anchor_sha256'],inherited_history=source['inherited_history'])
        permit=dict(schema_version=1,kind='codex_conducted_workflow_single_use_permit',journal_id=meta['journal_id'],permit_id=meta['permit_id'],anchor_sha256=config['anchor_sha256'],
            workflow_sha256=config['workflow_sha256'],registration_sha256=config['registration_sha256'],requested_model=requested_model,expires_at=meta['expires_at'])
        result['phase']='staging';io.claim(stage)
        io.write(operator/'preparation-record-v1.json',_C(dict(schema_version=1,kind='conducted_workflow_manual_preparation_record',operator_source=_pin(source_raw),prepared_input=_pin(meta_raw),scenario_id=scenario_id,requested_model=requested_model)))
        for leaf,raw in rawfiles.items():filepins[leaf]=io.write(stage/leaf,raw)
        for leaf,value in [('root-continuation-anchor.json',anchor),('operator-control.json',config),('registered-workflow.json',workflow),('cancel-request.json',dict(requested=False))]:filepins[leaf]=io.write(stage/leaf,_C(value))
        io.tree.directory(stage/'runs'/meta['permit_id'],create=True)
        result['phase']='sql';filepins['workflow-continuation.sqlite3']=io.database(stage/'workflow-continuation.sqlite3',baseline,permit,config,anchor)
        result['phase']='current'
        owned=dict(store=None)
        try:_host._prepare(stage,config,scenario_id,owned)
        except BaseException:
            store=owned['store'];raise
        closing=owned['store'];closing.close()
        if {p.name for p in stage.iterdir()}!=set(filepins)|{'runs'}:_fail('profile_shape_invalid')
        if {p.name for p in (stage/'runs').iterdir()}!={meta['permit_id']} or any((stage/'runs'/meta['permit_id']).iterdir()):_fail('profile_shape_invalid')
        for leaf,pin in filepins.items():
            if _pin(io.read(stage/leaf,1048576))!=pin:_fail('source_changed')
        _host._native_host._expiry(meta['expires_at']);io.current();io.close_files()
        result['phase']='publish';io.publish(stage,target)
        result['files']=filepins
        result['profile']=dict(relative_directory=_TARGET,permit_id=meta['permit_id'],journal_id=meta['journal_id'])
        io.write(operator/'preparation-complete-v1.json',_C(dict(schema_version=1,kind='conducted_workflow_preparation_publication',operator_source=_pin(source_raw),prepared_input=_pin(meta_raw),files=filepins,profile=_TARGET)))
        result['status']='prepared';result['phase']='prepared'
    except BaseException as exc:error(exc,result['phase'])
    finally:
        if store is not None:
            try:store.close()
            except BaseException as exc:error(exc,'store_close')
        if io is not None:
            if primary is not None and io.claimed and operator is not None:
                try:io.write(operator/'preparation-failure-v1.json',_C(dict(schema_version=1,kind='conducted_workflow_preparation_failure',phase=result['phase'],code=result['errors'][0]['code'],publication_attempted=io.publication_attempted)))
                except BaseException as exc:
                    if isinstance(exc,_CONTROL) and control is None:control=exc
            try:io.close_files()
            except BaseException as exc:error(exc,'file_close')
            try:io.close_dirs()
            except BaseException as exc:error(exc,'directory_close')
            for close_error in io.close_errors:error(close_error,'known_close')
    if isinstance(primary,_CONTROL):raise primary
    return result


def main(argv=None):
    args=sys.argv[1:] if argv is None else argv
    try:
        if type(args) is not list or len(args)!=4 or not all(type(x) is str for x in args):_fail('invalid_arguments')
        options=dict(zip(args[::2],args[1::2]))
        if set(options)!= {'--scenario-id','--model'}:_fail('invalid_arguments')
        _host._native_host._id(options['--scenario-id'])
        if options['--model'] not in _MODELS:_fail('invalid_arguments')
    except Exception:
        sys.stderr.write(canonical(dict(schema_version=1,kind='conducted_workflow_registration_error',status='not_prepared',code=_PREFIX+'invalid_arguments'))+'\n');return 2
    result=prepare_registered_conducted_workflow(scenario_id=options['--scenario-id'],requested_model=options['--model'])
    (sys.stdout if result['status']=='prepared' else sys.stderr).write(canonical(result)+'\n')
    return {'prepared':0,'not_prepared':3,'failed':4,'publication_uncertain':5}[result['status']]


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

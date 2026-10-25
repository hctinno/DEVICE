"""One exclusively owned fresh virtual trial; at most one decoded proposal is applied."""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import threading
import time
import uuid

from ..codex_cli_response import CodexCliResponseError, produce_codex_cli_response as _produce
from .catalog import load_catalog as _load
from .evaluation import prepare_sensor_trial as _prepare
from .harness import FleetHarness as _Harness
from .integration import get_role_actions as _actions
from .model_operator_boundary import (ModelOperatorBoundaryError,
    build_operator_prompt as _build, decode_operator_response as _decode)

__all__ = ['run_codex_virtual_one_action', 'CodexVirtualOneActionError']

_P = 'operator_virtual_one_action_'
_HOST = set('invalid_input delegation_denied unsupported_source capture_failed budget_exhausted cancelled timeout retention_failed runtime_rejected runtime_uncertain cleanup_failed internal_error'.split())
_CLI = set('invalid_input limit_exceeded unsupported_client evidence_error spawn_failed timeout stream_invalid process_failed final_mismatch cleanup_failed internal_error'.split())
_BOUNDARY = set('invalid_input invalid_prompt response_invalid response_binding_mismatch response_producer_mismatch proposal_invalid limit_exceeded internal_error'.split())
_CODES = {_P+x for x in _HOST} | {'codex_cli_response_'+x for x in _CLI} | {'model_operator_boundary_'+x for x in _BOUNDARY}
_CONTROL = (KeyboardInterrupt, SystemExit, GeneratorExit, MemoryError)
_HASH = re.compile(r'[a-f0-9]{64}\Z', re.ASCII)
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z', re.ASCII)
_EXCHANGE = re.compile(r'codex-cli-exchange:[a-f0-9]{32}\Z', re.ASCII)
_MODELS = {'gpt-6.1-sol', 'gpt-6-astra'}
_SCENARIOS = {'normal', 'restored_disconnect'}
_PRODUCER = 'dgm-virtual-operator-v1'
_SCHEMA_HASH = 'aa321fa55e0d21af0c3992c5b6a91a78fd108d4a006e463a9bd3761ff21c0edb'
_BUDGETS = dict(decisions=1,logical_requests=1,ticks=1,wall_seconds=30,transport_retries=0)
_DELEGATION = dict(scope='rf_sensor_proposal_v1', harness_budgets=_BUDGETS,
                   outer_limits=dict(wall_seconds=60, model_calls=8))
_FILES = dict(context8=('context8.json',1048576),context7=('public-context7.json',1048576),
    binding=('binding.json',65536),prompt=('prompt.json',262144),before=('before.json',1048576),
    after=('after.json',1048576),wire=('wire.json',65536),harness_report=('harness-report.json',262144),
    harness_events=('harness-events.json',2097152),dispatch_receipt=('dispatch-receipt.json',65536))
_PRODUCER_FILES = dict(prompt=('request.json',262144), response_schema=('response-schema.json',65536),
    invocation=('invocation.json',131072), version_stdout=('version.stdout',4096), version_stderr=('version.stderr',65536),
    stdout_jsonl=('stdout.jsonl',8388608), stderr=('stderr.bin',1048576),
    final_text=('final-text.bin',2097152), last_message=('last-message.bin',2097152))
_RECEIPT = set('schema_version kind exchange_ref status failure bindings client model attempts lifecycle usage cost timing controls cleanup artifacts limits verification'.split())
_CLI_LIMITS = dict(max_prompt_bytes=262144,max_schema_bytes=65536,max_stdout_bytes=8388608,max_stderr_bytes=1048576,
    max_last_message_bytes=2097152,max_line_bytes=4194304,max_events=4096,max_json_depth=32,max_json_nodes=200000,
    min_json_integer=-9223372036854775808,max_json_integer=9223372036854775807,max_version_stdout_bytes=4096,
    max_version_stderr_bytes=65536,max_timeout_seconds=60.0,max_version_seconds=5.0,terminate_wait_seconds=2.0,
    kill_wait_seconds=2.0,reader_close_seconds=2.0)
_CLI_UNKNOWN = ['ignore_user_config_effect','ignore_rules_effect','sandbox_effect','ephemeral_effect',
    'all_tools_off','all_mcp_off','all_hooks_off','global_context_absent','managed_overrides_absent',
    'remote_endpoint','remote_account','remote_resolved_model','cli_internal_retries',
    'descendants_reaped','remote_hard_cancel','remote_billing_stopped']


class CodexVirtualOneActionError(RuntimeError):
    """Fixed original interface code, with an optional detached batch receipt."""
    def __init__(self, code, receipt=None):
        self.code = code if type(code) is str and code in _CODES else _P+'invalid_input'
        self.receipt = receipt
        super().__init__(self.code)


class _Fault(Exception):
    def __init__(self, code):
        self.code = code


def _fail(suffix):
    raise _Fault(suffix if suffix in _CODES else _P+suffix)


def _C(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def _H(data):
    return hashlib.sha256(data).hexdigest()


def _copy(value, cap=262144, code='retention_failed'):
    active = set()
    nodes = 0
    def walk(item, depth):
        nonlocal nodes
        nodes += 1
        if nodes > 200000 or depth > 32:
            _fail(code)
        kind = type(item)
        if kind in (dict, list):
            if id(item) in active or len(item) > 200000:
                _fail(code)
            active.add(id(item))
            try:
                if kind is dict:
                    if any(type(key) is not str for key in item):
                        _fail(code)
                    return {walk(key,depth+1):walk(child,depth+1) for key,child in item.items()}
                return [walk(child,depth+1) for child in item]
            finally:
                active.remove(id(item))
        if kind is str:
            if len(item) > cap:
                _fail(code)
            try: item.encode('utf-8', errors='strict')
            except UnicodeError: _fail(code)
        elif kind is int:
            if not -9223372036854775808 <= item <= 9223372036854775807:
                _fail(code)
        elif kind is float:
            if not math.isfinite(item): _fail(code)
        elif kind is not bool and item is not None:
            _fail(code)
        return item
    result = walk(value,0)
    if len(_C(result)) > cap:
        _fail(code)
    return result


def _fixed(code, receipt):
    try:
        raise CodexVirtualOneActionError(code, receipt) from None
    except CodexVirtualOneActionError as error:
        error.__context__ = None
        error.__cause__ = None
        raise


def _chain(path, code):
    for part in (path, *path.parents):
        info = part.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&stat.FILE_ATTRIBUTE_REPARSE_POINT:
            _fail(code)


def _read(path, cap, code, owner=None):
    handle = None
    primary = None
    try:
        _chain(path, code)
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode) or before.st_size>cap: _fail(code)
        handle = path.open('rb', buffering=0)
        opened = os.fstat(handle.fileno())
        if (opened.st_dev,opened.st_ino) != (before.st_dev,before.st_ino): _fail(code)
        data = handle.read(cap+1)
        after = os.fstat(handle.fileno())
        current = path.lstat()
        if ((current.st_dev,current.st_ino) != (before.st_dev,before.st_ino)
                or before.st_size != after.st_size or after.st_size != current.st_size
                or len(data)!=after.st_size
                or before.st_mtime_ns != after.st_mtime_ns or after.st_mtime_ns != current.st_mtime_ns
                or getattr(current,'st_file_attributes',0)&stat.FILE_ATTRIBUTE_REPARSE_POINT or len(data)>cap):
            _fail(code)
        return data
    except OSError:
        primary = True
        _fail(code)
    except BaseException as error:
        primary = error
        raise
    finally:
        if handle is not None:
            if owner is not None:
                owner.close(handle)
            else:
                try: handle.close()
                except BaseException:
                    if primary is None: raise


def _preflight(catalog_path, catalog_sha256, schema, executable, model, scenario, grant, directory, event):
    if type(grant) is not bool: _fail('invalid_input')
    if not grant: _fail('delegation_denied')
    if (type(catalog_path) is not type(Path()) or type(executable) is not type(Path())
            or type(directory) is not type(Path()) or not all(p.is_absolute() for p in (catalog_path,executable,directory))
            or type(catalog_sha256) is not str or not _HASH.fullmatch(catalog_sha256)
            or type(schema) is not bytes or type(model) is not str or model not in _MODELS
            or type(scenario) is not str or scenario not in _SCENARIOS
            or event is not None and type(event) is not threading.Event):
        _fail('invalid_input')
    if len(schema)!=3052 or _H(schema)!=_SCHEMA_HASH: _fail('invalid_input')
    if event is not None and event.is_set(): _fail('cancelled')
    try:
        _chain(catalog_path,'invalid_input'); _chain(executable,'invalid_input'); _chain(directory.parent,'invalid_input')
        if (os.name!='nt' or executable.name.lower()!='codex.exe' or not stat.S_ISREG(executable.lstat().st_mode)
                or not directory.parent.is_dir() or directory.exists() or directory.is_symlink()): _fail('invalid_input')
    except OSError: _fail('invalid_input')
    if _H(_read(catalog_path,1048576,'unsupported_source'))!=catalog_sha256: _fail('unsupported_source')


def _absent(path):
    return dict(path=path, present=False, bytes=0, sha256=None, complete=False, overflow=False, extent='absent')


def _complete_receipt(value, model, timeout):
    """The fixed supported producer profile, not a general schema engine."""
    shapes=dict(bindings='prompt_sha256 schema_sha256 invocation_sha256 producer_declaration',
        client='name supported_version observed_version binary_content_sha256',
        model='requested resolved cli_thread_id remote_request_id',
        attempts='version_process_attempts model_process_attempts application_retries internal_network_requests internal_network_retries',
        lifecycle='model_process_started exit_code thread_started turn_started turn_completed agent_messages reasoning_items tool_items stdout_eof stderr_eof',
        cost='kind amount currency price_version',timing='timeout_seconds local_elapsed_seconds',
        controls='requested documented observed unknown',
        cleanup='version_child_reaped model_child_reaped readers_joined pipes_closed artifacts_closed descendants_reaped remote_cancelled secondary_errors',
        verification='wire_complete remote_identity_verified semantic_quality_verified external_data_authority_verified storage_authenticity_verified')
    for key,names in shapes.items():
        if type(value.get(key)) is not dict or set(value[key])!=set(names.split()): _fail('retention_failed')
    constants=dict(client=dict(name='codex_cli',supported_version='0.163.0-alpha.11.2',observed_version='0.163.0-alpha.11.2',binary_content_sha256=None),
        attempts=dict(version_process_attempts=1,model_process_attempts=1,application_retries=0,internal_network_requests=None,internal_network_retries=None),
        cost=dict(kind='unknown',amount=None,currency=None,price_version=None),
        controls=dict(requested=dict(ignore_user_config=True,ignore_rules=True,sandbox='read-only',ephemeral=True,empty_cwd=True,model_local_attempt_cap=1,automatic_retries=0),
            documented=dict(ignore_user_config='config_toml_only',ignore_rules='execpolicy_rules_only',sandbox='model_command_policy',ephemeral='session_rollout_only'),
            observed=dict(argv_submitted=True,argv_exit0=True,empty_cwd_at_spawn=True,tool_items=0),unknown=_CLI_UNKNOWN),
        cleanup=dict(version_child_reaped=True,model_child_reaped=True,readers_joined=True,pipes_closed=True,artifacts_closed=True,descendants_reaped=None,remote_cancelled=None,secondary_errors=[]),
        verification=dict(wire_complete=True,remote_identity_verified=False,semantic_quality_verified=False,external_data_authority_verified=False,storage_authenticity_verified=False),
        limits=_CLI_LIMITS)
    for key,wanted in constants.items():
        if _C(value.get(key))!=_C(wanted): _fail('retention_failed')
    reported=value['model']
    if (reported['requested']!=model or reported['resolved'] is not None or reported['remote_request_id'] is not None
            or type(reported['cli_thread_id']) is not str or not _ID.fullmatch(reported['cli_thread_id'])): _fail('retention_failed')
    lifecycle=value['lifecycle']; reasoning=lifecycle['reasoning_items']
    if type(reasoning) is not int or not 0<=reasoning<=4096: _fail('retention_failed')
    expected=dict(model_process_started=True,exit_code=0,thread_started=1,turn_started=1,turn_completed=1,
        agent_messages=1,reasoning_items=reasoning,tool_items=0,stdout_eof=True,stderr_eof=True)
    if _C(lifecycle)!=_C(expected): _fail('retention_failed')
    timing=value['timing']
    if (type(timing['timeout_seconds']) is not float or timing['timeout_seconds']!=float(timeout)
            or type(timing['local_elapsed_seconds']) is not float or timing['local_elapsed_seconds']<0): _fail('retention_failed')
    usage=value.get('usage')
    if usage is not None:
        keys={'input_tokens','cached_input_tokens','cache_write_input_tokens','output_tokens','reasoning_output_tokens'}
        if type(usage) is not dict or set(usage)!=keys or any(x is not None and (type(x) is not int or x<0) for x in usage.values()): _fail('retention_failed')
        cached,total=usage['cached_input_tokens'],usage['input_tokens']
        if cached is not None and total is not None and cached>total: _fail('retention_failed')



class _Run:
    def __init__(self,catalog_path,catalog_sha256,schema,executable,model,scenario,directory,event,start):
        self.catalog_path=catalog_path; self.catalog_sha256=catalog_sha256; self.schema=schema
        self.executable=executable; self.model=model; self.scenario=scenario; self.directory=directory; self.event=event
        self.start=start; self.deadline=start+60; self.harness_deadline=None
        self.stage='setup'; self.first=None; self.control=None; self.attempts=[]; self.source_pins={}
        self.trial=None; self.runtime=None; self.harness=None; self.finished=False; self.before=None; self.policy_entries=0
        self.dispatch_armed=False
        self.r=dict(schema_version=1,kind='codex_virtual_one_action_result',run_id='operator-one-run:'+uuid.uuid4().hex,
            status='failed',failure=None,
            declaration=dict(scenario=scenario,requested_model=model,producer_name=_PRODUCER,catalog_sha256=catalog_sha256,
                schema_sha256=_H(schema),virtual_dispatch_authorized=True,scope='rf_sensor_proposal_v1'),
            budget=dict(limits=dict(model_calls=8,wall_seconds=60.0,producer_cleanup_allowance_seconds=6.0,harness_budgets=_copy(_BUDGETS)),
                reserved_model_calls=0,producer_calls_started=0,version_process_attempts=0,model_process_attempts=0,
                elapsed_seconds=0.0,reservation_refunded=False,application_retries=0,new_budget_granted=False),
            step=dict(stage='setup',binding=None,before=None,after=None,transport=None,wire=None,
                dispatch=dict(intent_seen=False,request_id=None,operation=None,reserved_logical_requests=0,
                    confirmed_receipts=0,runtime_call_attempts=0,receipt_status=None,effect='not_applicable'),
                harness=None,artifacts={key:_absent(name) for key,(name,_) in _FILES.items()},failure=None),
            cancellation=dict(requested=False,scope='between_stages_only',observed_stage=None,remote_cancel_verified=False),
            cleanup=dict(supervisor_stop_requested=False,terminal_report_observed=False,host_artifacts_closed=None,
                virtual_outputs_disabled=None,remote_cancel_verified=False,secondary_errors=[]),
            execution=dict(mode='virtual_one_action',synthetic=True,model_proposal_dispatches=0,
                task_assessment_status='not_executed',task_score=None,closed_loop_complete=False,
                hardware_verified=False,physical_cleanup_verified=False),
            verification=dict(wire_accepted=False,dispatch_trace_complete=False,source_inputs_unchanged=False,
                remote_identity_verified=False,semantic_quality_verified=False,hardware_verified=False))
        self.slot=self.r['step']

    def error(self,code,stage=None):
        if self.first is None:
            code=code if code in _CODES else _P+code
            self.first=dict(code=code,stage=stage or self.stage)
            self.slot['failure']=dict(self.first); self.slot['stage']=self.first['stage']

    def phase(self,stage):
        self.stage=stage
        if self.first is None: self.slot['stage']=stage

    def check(self):
        if self.event is not None and self.event.is_set():
            self.r['cancellation'].update(requested=True,observed_stage=self.stage)
            if self.harness is not None: self.harness.stop()
            _fail('cancelled')
        now=time.monotonic()
        if now>=self.deadline or self.harness_deadline is not None and now>=self.harness_deadline: _fail('timeout')


    def signal(self, error):
        if self.control is None: self.control=error
        self.error('internal_error')

    def observe(self, error):
        if isinstance(error,_CONTROL): self.signal(error)
        elif type(error) is _Fault: self.error(error.code)
        elif isinstance(error,(CodexCliResponseError,ModelOperatorBoundaryError)) and error.code in _CODES: self.error(error.code)
        elif isinstance(error,OSError): self.error('retention_failed')
        else: self.error('internal_error')

    def throw(self):
        if self.control is not None: raise self.control
        if self.first is not None: raise _Fault(self.first['code'])

    def secondary(self, code):
        values=self.r['cleanup']['secondary_errors']
        if code not in values:
            if len(values)<8: values.append(code)
            else: values[-1]='secondary_overflow'

    def close(self, handle, *, receipt=False):
        errors=[]
        code='receipt_write_failed' if receipt else 'artifact_close_failed'
        def close():
            try: handle.close()
            except BaseException as error: errors.append(error)
        try:
            thread=threading.Thread(target=close,daemon=True,name='codex-one-close-'+self.r['run_id'][-8:])
            thread.start()
            thread.join(max(0.0,min(2.0,self.deadline-time.monotonic())))
            good=not thread.is_alive() and not errors
        except BaseException as error:
            good=False; errors.append(error)
        prior=self.r['cleanup']['host_artifacts_closed']
        self.r['cleanup']['host_artifacts_closed']=good if prior is None else prior and good
        if not good:
            if time.monotonic()>=self.deadline: self.error('timeout')
            for error in errors:
                if isinstance(error,_CONTROL): self.signal(error)
            self.secondary(code)
            self.error('retention_failed' if receipt else 'cleanup_failed','cleanup')

    def write(self, path, data, cap, desc=None, *, final=False):
        if len(data)>cap: _fail('retention_failed')
        handle=None
        try:
            if not final: self.check()
            handle=path.open('xb',buffering=0)
            view=memoryview(data);digest=hashlib.sha256();count=0
            if desc is not None: desc.update(present=True,sha256=digest.hexdigest(),extent='prefix')
            while view:
                amount=handle.write(view)
                if not amount: raise OSError('host_write_failed')
                digest.update(view[:amount]);count+=amount;view=view[amount:]
                if desc is not None: desc.update(bytes=count,sha256=digest.hexdigest())
            if desc is not None: desc.update(complete=True,extent='whole_file')
        except BaseException as error:
            self.observe(error)
            raise
        finally:
            if handle is not None: self.close(handle,receipt=final and path.name=='one-action-receipt.json')
        if not final: self.throw()

    def source(self):
        self.check()
        if _H(_read(self.catalog_path,1048576,'unsupported_source',self)) != self.catalog_sha256:
            _fail('unsupported_source')
        for path,wanted in self.source_pins.items():
            data=_read(path,1048576,'unsupported_source',self)
            if (len(data),_H(data))!=wanted: _fail('unsupported_source')
        self.throw()

    def attach(self, receipt):
        if type(receipt) is not dict:
            return None
        value=_copy(receipt)
        if set(value)!=_RECEIPT or type(value.get('exchange_ref')) is not str or not _EXCHANGE.fullmatch(value['exchange_ref']):
            _fail('retention_failed')
        artifacts=value.get('artifacts')
        if type(artifacts) is not dict or set(artifacts)!=set(_PRODUCER_FILES): _fail('retention_failed')
        for key,(name,cap) in _PRODUCER_FILES.items():
            desc=artifacts[key]
            if (type(desc) is not dict or set(desc)!=set(_absent(name)) or desc['path']!=name
                    or type(desc['present']) is not bool or type(desc['complete']) is not bool or type(desc['overflow']) is not bool
                    or type(desc['bytes']) is not int or not 0<=desc['bytes']<=cap
                    or desc['sha256'] is not None and (type(desc['sha256']) is not str or not _HASH.fullmatch(desc['sha256']))):
                _fail('retention_failed')
        self.slot['transport']=dict(exchange_ref=value['exchange_ref'],receipt=value,receipt_sha256=None)
        attempts=value.get('attempts')
        if type(attempts) is dict:
            pair=[attempts.get('version_process_attempts'),attempts.get('model_process_attempts')]
            if all(type(x) is int and x in (0,1) for x in pair): self.attempts[-1]=pair
        self.recount()
        return value

    def recount(self):
        for index,key in enumerate(('version_process_attempts','model_process_attempts')):
            self.r['budget'][key]=None if any(pair is None for pair in self.attempts) else sum(pair[index] for pair in self.attempts)

    def retain(self, folder, response, value, raw_prompt):
        self.phase('retain')
        if value is None: _fail('retention_failed')
        _complete_receipt(value,self.model,self.producer_timeout)
        if (type(response) is not bytes or value is None or value.get('schema_version')!=1 or type(value['schema_version']) is not int
                or value.get('kind')!='codex_cli_response_receipt' or value.get('status')!='complete' or value.get('failure') is not None
                or value.get('model',{}).get('requested')!=self.model
                or value.get('verification',{}).get('wire_complete') is not True
                or value.get('bindings',{}).get('prompt_sha256')!=_H(raw_prompt)
                or value.get('bindings',{}).get('schema_sha256')!=_H(self.schema)
                or value.get('bindings',{}).get('producer_declaration')!=dict(kind='model',name=_PRODUCER)
                or self.attempts[-1]!=[1,1]):
            _fail('retention_failed')
        for key in ('version_child_reaped','model_child_reaped','readers_joined','pipes_closed','artifacts_closed'):
            if value.get('cleanup',{}).get(key) is not True: _fail('retention_failed')
        producer=folder/'producer'
        receipt_bytes=_read(producer/'receipt.json',262144,'retention_failed',self)
        if receipt_bytes!=_C(value): _fail('retention_failed')
        self.slot['transport']['receipt_sha256']=_H(receipt_bytes)
        for key,(name,cap) in _PRODUCER_FILES.items():
            self.check()
            desc=value['artifacts'][key]
            if not desc['present'] or not desc['complete'] or desc['overflow'] or desc['extent']!='whole_file': _fail('retention_failed')
            data=_read(producer/name,cap,'retention_failed',self)
            if len(data)!=desc['bytes'] or _H(data)!=desc['sha256']: _fail('retention_failed')
            if key=='prompt' and data!=raw_prompt or key=='response_schema' and data!=self.schema: _fail('retention_failed')
            if key in {'final_text','last_message'} and data!=response: _fail('retention_failed')
            if key=='invocation' and _H(data)!=value['bindings'].get('invocation_sha256'): _fail('retention_failed')
        self.throw()

    def artifact(self,key,value,*,raw=False,terminal=False):
        name,cap=_FILES[key]
        self.write(self.directory/name,value if raw else _C(value),cap,self.slot['artifacts'][key],final=terminal)

    def observation(self,key,value,*,terminal=False):
        value=_copy(value,1048576,'capture_failed')
        if (set(value)!=set('tick setup_revision synthetic hardware_verified devices'.split())
                or type(value['tick']) is not int or value['tick']<0
                or type(value['setup_revision']) is not int or value['setup_revision']<0
                or value['synthetic'] is not True or value['hardware_verified'] is not False
                or type(value['devices']) is not dict or len(value['devices'])!=64): _fail('capture_failed')
        self.artifact(key,value,terminal=terminal)
        self.slot[key]=dict(tick=value['tick'],setup_revision=value['setup_revision'],device_count=64,sha256=_H(_C(value)),present=True)
        return value

    def current(self):
        if (self.trial.runtime is not self.runtime or self.trial.runtime_instance_id!=self.ids['runtime_instance_id']
                or _C(self.runtime.observations())!=_C(self.before)): _fail('capture_failed')

    def policy(self,context):
        try:
            self.phase('capture'); self.check(); self.policy_entries+=1
            if self.policy_entries!=1: _fail('capture_failed')
            snapshot=_copy(context,1048576,'capture_failed')
            if (snapshot['goal']!=self.trial.goal or snapshot['topology']!=self.trial.topology
                    or snapshot['role_actions']!=self.actions or snapshot['last_receipt'] is not None
                    or len(snapshot['catalog']['profiles'])!=64
                    or {p['profile_id'] for p in snapshot['catalog']['profiles']}!={p['profile_id'] for p in self.catalog['profiles']}):
                _fail('capture_failed')
            self.before=self.observation('before',snapshot['observations'])
            self.current(); self.artifact('context8',snapshot)
            context7=_copy(snapshot,1048576,'capture_failed'); remaining=context7.pop('remaining_budget')
            if any(remaining.get(k)!=v for k,v in dict(decisions=0,logical_requests=1,ticks=1,transport_retries=0).items()):
                _fail('capture_failed')
            self.artifact('context7',context7); self.phase('prompt')
            prompt=_build(context7,producer_name=_PRODUCER,delegation=_copy(_DELEGATION),**self.ids)
            self.slot['binding']=_copy(prompt['binding'])
            self.artifact('binding',dict(binding=prompt['binding'],delegation=_copy(_DELEGATION),remaining_budget=remaining,
                catalog_sha256=self.catalog_sha256,schema_sha256=_H(self.schema)))
            raw=_C(prompt); self.artifact('prompt',raw,raw=True)
            self.source(); self.current(); self.phase('reserve'); self.check()
            remaining_wall=min(self.deadline,self.harness_deadline)-time.monotonic()
            if remaining_wall<=6 or self.r['budget']['reserved_model_calls']!=0: _fail('budget_exhausted')
            self.r['budget']['reserved_model_calls']=1
            self.phase('producer'); self.r['budget']['producer_calls_started']=1
            self.attempts.append(None); self.recount(); self.producer_timeout=min(60.0,remaining_wall-6)
            try:
                result=_produce(raw,self.schema,executable=self.executable,requested_model=self.model,
                    evidence_dir=self.directory/'producer',timeout_seconds=self.producer_timeout)
            except CodexCliResponseError as error:
                self.error(error.code)
                try: self.attach(error.receipt)
                except BaseException as later: self.observe(later)
                self.throw()
            if type(result) is not tuple or len(result)!=2: _fail('retention_failed')
            response,receipt=result; receipt=self.attach(receipt); self.check()
            self.retain(self.directory,response,receipt,raw)
            self.source(); self.current(); self.phase('decode'); self.check()
            wire=_decode(response,prompt); self.slot['wire']=_copy(wire,65536)
            self.r['verification']['wire_accepted']=True; self.artifact('wire',wire)
            self.phase('gate'); self.source(); self.current(); self.check()
            if self.policy_entries!=1 or self.r['budget']['reserved_model_calls']!=1: _fail('budget_exhausted')
            if wire['proposal']['kind']!='stop':
                self.dispatch_armed=True
                self.slot['dispatch'].update(runtime_call_attempts=None,effect='unknown')
                self.r['execution']['model_proposal_dispatches']=None
            return _copy(wire['proposal'],65536)
        except BaseException as error:
            self.observe(error)
            raise

    def run(self):
        self.write(self.directory/'response-schema.json',self.schema,65536)
        sources={}
        for relative in ('codex_cli_response.py','virtual_fleet/codex_virtual_one_action.py',
                'virtual_fleet/model_operator_boundary.py','virtual_fleet/harness.py','virtual_fleet/evaluation.py',
                'virtual_fleet/integration.py','virtual_fleet/catalog.py','virtual_fleet/core.py','virtual_fleet/rf.py',
                'virtual_fleet/facility.py','virtual_fleet/instruments.py','virtual_fleet/journal.py'):
            path=Path(__file__).resolve().parents[1]/relative
            data=_read(path,1048576,'unsupported_source',self)
            self.source_pins[path]=(len(data),_H(data)); sources['labflow/'+relative]=dict(bytes=len(data),sha256=_H(data))
        self.write(self.directory/'caller-request.json',_C(dict(schema_version=1,kind='codex_virtual_one_action_request',
            run_id=self.r['run_id'],execution=dict(catalog_path=str(self.catalog_path),executable=str(self.executable)),
            declaration=self.r['declaration'],source_pins=sources,limits=self.r['budget']['limits'])),262144)
        self.source()
        try:
            self.catalog=_load(self.catalog_path); self.actions=_actions()
            if len(self.catalog['profiles'])!=64: _fail('unsupported_source')
            self.trial=_prepare(self.catalog,condition=self.scenario,seed=0,power_dbm=12.5)
            self.runtime=self.trial.runtime
            if len(self.trial.topology['devices'])!=64: _fail('capture_failed')
        except _CONTROL: raise
        except _Fault: raise
        except Exception: _fail('capture_failed')
        self.ids=dict(run_id=self.r['run_id'],runtime_instance_id=self.trial.runtime_instance_id,
            decision_id='operator-one-decision:'+uuid.uuid4().hex,model_request_id='operator-one-request:'+uuid.uuid4().hex)
        if any(type(v) is not str or not _ID.fullmatch(v) for v in self.ids.values()): _fail('capture_failed')
        def policy(context): return self.policy(context)
        policy.policy_id='codex_virtual_one_action'
        self.harness=_Harness(self.runtime,policy,goal=self.trial.goal,catalog=self.trial.catalog,topology=self.trial.topology,
            role_actions=self.actions,budgets=_copy(_BUDGETS),run_id=self.r['run_id'],runtime_instance_id=self.ids['runtime_instance_id'])
        self.harness_deadline=time.monotonic()+30
        try:
            self.harness.step()
            self.phase('observe')
        except BaseException as error: self.observe(error)
        finally: self.finish_harness()
        self.check(); self.throw(); self.source()
        self.r['verification']['source_inputs_unchanged']=True

    def finish_harness(self):
        if self.finished or self.harness is None: return
        self.finished=True
        try:
            self.harness.stop(); self.r['cleanup']['supervisor_stop_requested']=True
            self.harness.step()
        except BaseException as error:
            self.observe(error); self.secondary('supervisor_termination_unconfirmed'); self.error('cleanup_failed','cleanup')
        try:
            report=self.harness.result()
            valid=(type(report) is dict and report.get('ai_model_called') is False
                and report.get('policy',{}).get('kind')=='fixture' and report.get('assessment',{}).get('status')=='not_assessed')
            self.r['cleanup']['terminal_report_observed']=valid
            if not valid: _fail('cleanup_failed')
            self.slot['harness']=dict(termination=_copy(report['termination']),unresolved_request_ids=_copy(report['unresolved_request_ids']),legacy_ai_model_called=False)
            try:
                events=self.harness.events()
            except BaseException as error:
                if isinstance(error,_CONTROL): self.signal(error)
                elif self.dispatch_armed: self.error('runtime_uncertain','observe')
                else: self.observe(error)
                self.artifact('harness_report',report,terminal=True)
                return
            self.inspect_dispatch(report,events)
            for key,value in [('harness_report',report),('harness_events',events)]:
                try: self.artifact(key,value,terminal=True)
                except BaseException as error: self.observe(error)
        except BaseException as error:
            self.observe(error)
            if self.slot['dispatch']['intent_seen']: self.error('runtime_uncertain','observe')

    def inspect_dispatch(self,report,events):
        intents=[e for e in events if e['type']=='intent']
        receipts=[e for e in events if e['type']=='receipt']
        observations=[e for e in events if e['type']=='observation']
        decisions=[e for e in events if e['type']=='policy_decision']
        if (len(intents)>1 or len(receipts)>1 or len(decisions)>1
                or any(e['type']=='transport_retry' for e in events)): _fail('runtime_uncertain')
        d=self.slot['dispatch']; wire=self.slot['wire']
        if intents:
            intent=intents[0]['payload']; request=intent['request_id']
            d.update(intent_seen=True,request_id=request,operation=intent['operation'],reserved_logical_requests=1,
                runtime_call_attempts=None,effect='unknown')
            self.r['execution']['model_proposal_dispatches']=None
            self.phase('observe')
            try:
                if (wire is None or len(decisions)!=1 or _C(decisions[0]['payload']['proposal'])!=_C(wire['proposal'])
                        or len(receipts)!=1 or receipts[0]['payload']['request_id']!=request
                        or len(observations)!=2 or observations[-1]['payload'].get('cause_request_id')!=request):
                    _fail('runtime_uncertain')
                result=receipts[0]['payload']['result']; after=observations[-1]['payload']['observation']
                if result['status'] not in {'ok','pending'}: self.error('runtime_rejected','dispatch')
                self.artifact('dispatch_receipt',result,terminal=True)
                if (self.runtime is not self.trial.runtime or self.trial.runtime_instance_id!=self.ids['runtime_instance_id']
                        or _C(self.runtime.observations())!=_C(after)
                        or after['tick']!=self.before['tick']+int(d['operation']=='advance')
                        or after['setup_revision']<self.before['setup_revision']): _fail('runtime_uncertain')
                self.observation('after',after,terminal=True)
                d.update(confirmed_receipts=1,runtime_call_attempts=1,receipt_status=result['status'],
                    effect='unchanged' if _C(after)==_C(self.before) else 'changed')
                self.r['execution']['model_proposal_dispatches']=1
                self.r['verification']['dispatch_trace_complete']=True
                if result['status'] not in {'ok','pending'}: self.error('runtime_rejected','dispatch')
            except BaseException as error:
                if isinstance(error,_CONTROL): self.signal(error)
                elif isinstance(error,_Fault) and error.code in {_P+'retention_failed',_P+'cleanup_failed'}: self.observe(error)
                else: self.error('runtime_uncertain','observe')
        else:
            d.update(runtime_call_attempts=0,effect='not_applicable')
            self.r['execution']['model_proposal_dispatches']=0
        if not intents and wire is not None and wire['proposal']['kind']=='stop':
            if (len(decisions)!=1 or report['termination']!=dict(reason='policy_stop',policy_claim=wire['proposal']['claim'])
                    or report['unresolved_request_ids']!=[]): _fail('runtime_uncertain')
            after=self.runtime.observations()
            if _C(after)!=_C(self.before): _fail('capture_failed')
            self.observation('after',after,terminal=True)
            self.r['verification']['dispatch_trace_complete']=True
        elif not intents and self.first is None:
            self.error('timeout' if report['termination']['reason']=='wall_deadline' else 'runtime_uncertain','dispatch')

    def finalize(self):
        self.finish_harness()
        try: self.check()
        except BaseException as error: self.observe(error)
        self.stage='finalize'
        self.r['failure']=self.first
        self.r['status']=('rejected' if self.first and self.first['code']==_P+'runtime_rejected' else 'failed') if self.first else (
            'stopped' if self.slot['wire'] is not None and self.slot['wire']['proposal']['kind']=='stop' else 'observed')
        if self.first is None: self.slot['stage']='finalize'
        self.r['budget']['elapsed_seconds']=max(0.0,time.monotonic()-self.start)
        try: self.write(self.directory/'one-action-receipt.json',_C(self.r),262144,final=True)
        except BaseException as error: self.observe(error); self.secondary('receipt_write_failed')
        try: self.check()
        except BaseException as error: self.observe(error)
        if self.first is not None:
            self.r['failure']=self.first
            self.r['status']='rejected' if self.first['code']==_P+'runtime_rejected' else 'failed'
        self.trial=None; self.runtime=None; self.harness=None


def run_codex_virtual_one_action(*,catalog_path: Path,catalog_sha256: str,response_schema_bytes: bytes,
        executable: Path,requested_model: str,scenario: str,virtual_dispatch_authorized: bool,
        evidence_dir: Path,cancel_event: threading.Event | None=None) -> dict:
    """Apply at most one decoded proposal to an exclusively owned virtual trial."""
    owner=None; control=None; code=_P+'internal_error'; receipt=None
    try:
        _preflight(catalog_path,catalog_sha256,response_schema_bytes,executable,requested_model,scenario,
            virtual_dispatch_authorized,evidence_dir,cancel_event)
        start=time.monotonic()
        try: evidence_dir.mkdir()
        except OSError: _fail('retention_failed')
        owner=_Run(catalog_path,catalog_sha256,response_schema_bytes,executable,requested_model,scenario,evidence_dir,cancel_event,start)
        owner.run()
    except BaseException as error:
        if isinstance(error,_CONTROL): control=error
        if owner is not None: owner.observe(error)
        elif type(error) is _Fault: code=error.code
    if owner is not None:
        try: owner.finalize()
        except BaseException as error: owner.observe(error)
        if control is None: control=owner.control
        if owner.first is not None: code=owner.first['code']
        try: receipt=_copy(owner.r)
        except _CONTROL as error:
            if control is None: control=error
        if control is None and owner.first is None: return receipt
    if control is not None: raise control
    _fixed(code,receipt)

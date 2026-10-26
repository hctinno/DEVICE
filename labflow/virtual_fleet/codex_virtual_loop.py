"""Bounded Codex decisions on one original synthetic sensor runtime."""
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
from .evaluation import prepare_sensor_trial as _prepare, evaluate_sensor_run as _evaluate
from .harness import FleetHarness as _Harness
from .integration import get_role_actions as _actions
from .model_operator_boundary import (ModelOperatorBoundaryError,
    build_operator_prompt as _build, decode_operator_response as _decode)
from .journal import (OperatorJournal as _Journal, read_operator_journal as _read_journal,
    _header as _journal_header, _record as _journal_record)
from .codex_virtual_one_action import (_copy as _native_copy,
    _complete_receipt as _producer_profile, _Fault as _ParentFault)

__all__ = ['run_codex_virtual_loop', 'CodexVirtualLoopError']

_P = 'operator_virtual_loop_'
_HOST = set('invalid_input unsupported_source capture_failed budget_exhausted limit_exceeded cancelled timeout retention_failed runtime_uncertain cleanup_failed internal_error'.split())
_CLI = 'invalid_input limit_exceeded unsupported_client evidence_error spawn_failed timeout stream_invalid process_failed final_mismatch cleanup_failed internal_error'.split()
_BOUNDARY = 'invalid_input invalid_prompt response_invalid response_binding_mismatch response_producer_mismatch proposal_invalid limit_exceeded internal_error'.split()
_CODES = {_P + x for x in _HOST} | {'codex_cli_response_' + x for x in _CLI} | {'model_operator_boundary_' + x for x in _BOUNDARY}
_CONTROL = (KeyboardInterrupt, SystemExit, GeneratorExit, MemoryError)
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z', re.ASCII)
_SHA = re.compile(r'[a-f0-9]{64}\Z', re.ASCII)
_EXCHANGE = re.compile(r'codex-cli-exchange:[a-f0-9]{32}\Z', re.ASCII)
_MODELS = {'gpt-6.1-sol', 'gpt-6-astra'}
_SCENARIOS = {'normal', 'persistent_disconnect', 'restored_disconnect'}
_STATUSES = {'ok', 'pending', 'invalid', 'unsupported', 'error', 'disconnected'}
_PRODUCER = 'dgm-virtual-operator-v1'
_SCHEMA_SHA = 'aa321fa55e0d21af0c3992c5b6a91a78fd108d4a006e463a9bd3761ff21c0edb'
_BUDGET = dict(decisions=8, logical_requests=8, ticks=8, wall_seconds=180, transport_retries=0)
_LIMITS = dict(max_output_bytes=262144, max_steps=8, max_events=64, max_events_bytes=8388608,
    max_known_evidence_files=192, max_observed_evidence_bytes=33554432)
_FILES = dict(context8=('context8.json',1048576), context7=('public-context7.json',1048576),
    binding=('binding.json',65536), prompt=('prompt.json',262144), before=('before.json',1048576),
    after=('after.json',1048576), wire=('wire.json',65536), dispatch_receipt=('dispatch-receipt.json',65536))
_PRODUCER_FILES = dict(prompt=('request.json',262144), response_schema=('response-schema.json',65536),
    invocation=('invocation.json',131072), version_stdout=('version.stdout',4096), version_stderr=('version.stderr',65536),
    stdout_jsonl=('stdout.jsonl',8388608), stderr=('stderr.bin',1048576),
    final_text=('final-text.bin',2097152), last_message=('last-message.bin',2097152))
_RECEIPT_KEYS = set('schema_version kind exchange_ref status failure bindings client model attempts lifecycle usage cost timing controls cleanup artifacts limits verification'.split())
_SOURCE = ('codex_cli_response.py', 'virtual_fleet/codex_virtual_loop.py',
    'virtual_fleet/codex_virtual_one_action.py', 'virtual_fleet/model_operator_boundary.py',
    'virtual_fleet/harness.py', 'virtual_fleet/evaluation.py', 'virtual_fleet/catalog.py',
    'virtual_fleet/integration.py', 'virtual_fleet/core.py', 'virtual_fleet/rf.py',
    'virtual_fleet/facility.py', 'virtual_fleet/instruments.py', 'virtual_fleet/journal.py')


class CodexVirtualLoopError(RuntimeError):
    """A fixed code with optional bounded detached execution receipt."""
    def __init__(self, code, receipt=None):
        self.code = code if type(code) is str and code in _CODES else _P + 'invalid_input'
        self.receipt = receipt
        super().__init__(self.code)


class _Fault(Exception):
    def __init__(self, code):
        self.code = code


def _fail(code):
    raise _Fault(code if code in _CODES else _P + code)


def _C(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def _reservation(value):
    if value is None:return None
    if type(value) is not dict:_fail('invalid_input')
    value=value.copy()
    if (set(value)!={'files','bytes'} or type(value['files']) is not int or type(value['bytes']) is not int
            or not 0<=value['files']<=192 or not 0<=value['bytes']<=33554432):_fail('invalid_input')
    return value


def _H(data):
    return hashlib.sha256(data).hexdigest()


def _copy(value, cap=262144, code='retention_failed'):
    try:
        return _native_copy(value, cap)
    except _ParentFault:
        _fail(code)


def _now():
    value = time.monotonic()
    if type(value) not in (int, float) or not math.isfinite(value):
        _fail('internal_error')
    return value


def _fixed(code, receipt):
    try:
        raise CodexVirtualLoopError(code, receipt) from None
    except CodexVirtualLoopError as error:
        error.__cause__ = error.__context__ = None
        raise


def _path(path):
    if type(path) is not type(Path()) or not path.is_absolute():
        _fail('invalid_input')
    if str(path).startswith(('\\\\', '//')):
        _fail('invalid_input')
    for part in path.parts[1:]:
        if (part in {'.', '..'} or part.endswith((' ', '.')) or ':' in part or '\0' in part
                or re.fullmatch(r'(?i:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?', part)):
            _fail('invalid_input')


def _chain(path, code):
    for part in (path, *path.parents):
        info = part.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 1024:
            _fail(code)


def _close_handle(handle, deadline):
    outcome = []
    def close():
        try:
            handle.close()
        except BaseException as error:
            outcome.append(error)
    worker = threading.Thread(target=close, daemon=True)
    worker.start()
    worker.join(max(0.0, min(2.0, deadline - time.monotonic())))
    return _Fault(_P + 'cleanup_failed') if worker.is_alive() else outcome[0] if outcome else None


def _read(path, cap, code, owner=None):
    handle, first = None, None
    try:
        _chain(path, code)
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode) or before.st_size > cap:
            _fail(code)
        handle = path.open('rb', buffering=0)
        opened = os.fstat(handle.fileno())
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            _fail(code)
        data = handle.read(cap + 1)
        after = os.fstat(handle.fileno()); current = path.lstat()
        if ((current.st_dev,current.st_ino) != (before.st_dev,before.st_ino)
                or before.st_size != after.st_size or after.st_size != current.st_size or len(data) != after.st_size
                or before.st_mtime_ns != after.st_mtime_ns or after.st_mtime_ns != current.st_mtime_ns
                or getattr(current,'st_file_attributes',0) & 1024 or len(data) > cap):
            _fail(code)
        return data
    except BaseException as error:
        first = error
        if owner is not None:
            owner.error(code) if isinstance(error, OSError) else owner.observe(error)
        if isinstance(error, OSError):
            _fail(code)
        raise
    finally:
        if handle is not None:
            if owner:
                owner.close(handle)
            else:
                error = _close_handle(handle, time.monotonic() + 2)
                if isinstance(error, _CONTROL) and not isinstance(first, _CONTROL):
                    raise error
                if error is not None and first is None:
                    _fail(code)


def _settings(value):
    if value is None:
        return None
    keys = {'frequency_hz', 'power_dbm', 'bandwidth_hz', 'duty_cycle', 'modulation', 'crest_factor_db'}
    if type(value) is not dict or any(type(key) is not str for key in value) or set(value) != keys:
        _fail('invalid_input')
    for key in keys - {'modulation'}:
        number = value[key]
        try:
            valid = type(number) in (int, float) and math.isfinite(number)
        except OverflowError:
            valid = False
        if not valid:
            _fail('invalid_input')
    text = value['modulation']
    if (type(text) is not str or not text.strip() or len(text) > 200
            or value['frequency_hz'] <= 0 or value['bandwidth_hz'] <= 0
            or not 0 < value['duty_cycle'] <= 1 or value['crest_factor_db'] < 0
            or value['frequency_hz'] - value['bandwidth_hz'] / 2 < 0
            or not math.isfinite(value['frequency_hz'] + value['bandwidth_hz'] / 2)):
        _fail('invalid_input')
    return _copy(value, 65536, 'invalid_input')


def _host_binding(value):
    if value is None:
        return None
    keys = {'intake_id', 'revision', 'analysis_context_id', 'context_sha256', 'analysis_sha256', 'plan_sha256'}
    value = _copy(value, 65536, 'invalid_input')
    if (type(value) is not dict or set(value) != keys or type(value['revision']) is not int
            or value['revision'] < 1
            or any(type(value[key]) is not str or not _ID.fullmatch(value[key])
                   for key in ('intake_id', 'analysis_context_id'))
            or any(type(value[key]) is not str or not _SHA.fullmatch(value[key])
                   for key in ('context_sha256', 'analysis_sha256', 'plan_sha256'))):
        _fail('invalid_input')
    return value


def _preflight(catalog_path, catalog_sha, schema, executable, model, scenario, directory, origin, event,
               source_settings, plan_binding, quantity):
    source = _settings(source_settings)
    binding = _host_binding(plan_binding)
    quantity = None if quantity is None else _copy(quantity, 65536, 'invalid_input')
    if binding is not None and source is None or binding is None and quantity is not None:
        _fail('invalid_input')
    for path in (catalog_path, executable, directory):
        _path(path)
    if (type(catalog_sha) is not str or not _SHA.fullmatch(catalog_sha) or type(schema) is not bytes
            or len(schema) != 3052 or _H(schema) != _SCHEMA_SHA
            or type(model) is not str or model not in _MODELS or type(scenario) is not str or scenario not in _SCENARIOS
            or type(origin) is not str or origin not in {'actual_cli', 'mock_subprocess'}
            or event is not None and type(event) is not threading.Event):
        _fail('invalid_input')
    if event is not None and event.is_set():
        _fail('cancelled')
    try:
        _chain(catalog_path, 'invalid_input'); _chain(executable, 'invalid_input'); _chain(directory.parent, 'invalid_input')
        if (os.name != 'nt' or executable.name.lower() != 'codex.exe' or not stat.S_ISREG(executable.lstat().st_mode)
                or not directory.parent.is_dir() or directory.exists() or directory.is_symlink()):
            _fail('invalid_input')
    except OSError:
        _fail('invalid_input')
    if _H(_read(catalog_path, 1048576, 'unsupported_source')) != catalog_sha:
        _fail('unsupported_source')
    return source, binding, quantity


def _absent(path):
    return dict(path=path, present=False, bytes=0, sha256=None, complete=False, overflow=False, extent='absent')


class _Loop:
    def __init__(self, catalog, catalog_sha, schema, executable, model, scenario, directory, origin, event,
                 start, source_settings, plan_binding, quantity, evidence_reservation=None):
        self.catalog_path, self.catalog_sha, self.schema = catalog, catalog_sha, schema
        self.executable, self.model, self.scenario, self.directory = executable, model, scenario, directory
        self.origin, self.event, self.start, self.deadline = origin, event, start, start + 180
        self.source_settings = source_settings
        self.plan_binding, self.quantity = plan_binding, quantity
        self.evidence_reservation=(0,0) if evidence_reservation is None else (evidence_reservation['files'],evidence_reservation['bytes'])
        self.setup_records = self.setup_snapshot = self.host_topology = None
        self.source_pins = {}
        self.stage = 'setup'; self.first = self.control = None
        self.trial = self.runtime = self.harness = None
        self.step = None; self.before = None; self.sources = {}; self.events = []; self.event_bytes = 0
        self.attempts = []; self.known = set(); self.finished = False
        self.guards = []
        self.r = dict(schema_version=1, kind='codex_virtual_loop_result', run_id='operator-loop-run:' + uuid.uuid4().hex,
            status='failed', failure=None,
            declaration=dict(goal_kind='acquire_fresh_rf_sensor', scope='rf_sensor_proposal_v1', scenario=scenario,
                requested_model=model, producer_name=_PRODUCER, catalog_sha256=catalog_sha, schema_sha256=_H(schema),
                origin_declaration=origin),
            budget=dict(limits=dict(model_calls=8,tool_intents=8,tick_delta=8,wall_seconds=180,producer_seconds=60,
                                   transport_retries=0,data=dict(_LIMITS)),
                reserved_model_calls=0, producer_calls_started=0, version_process_attempts=0, model_process_attempts=0,
                elapsed_seconds=0.0, reservation_refunded=False, application_retries=0, new_budget_granted=False,
                harness_usage=None),
            steps=[], termination=dict(reason='error',policy_claim=None,unresolved_request_ids=None),
            evidence_assessment=dict(scope='acquire_fresh_rf_sensor_public_evidence',evaluator_called=False,
                                     result=None,goal_observed=None,score=None),
            execution=dict(mode='persistent_virtual_rf_sensor_loop',runtime_instance_id=None,synthetic=True,
                origin_declaration=origin,origin_authenticated=False,ai_model_called=None,
                cancellation=dict(scope='between_stages_only',requested=False,
                                  producer_inflight_cancelled=None,remote_hard_cancelled=None)),
            cleanup=dict(supervisor_stop_requested=False,terminal_report_observed=False,host_artifacts_closed=None,
                         runtime_references_released=False,virtual_outputs_disabled=None,remote_cancel_verified=False,secondary_errors=[]),
            artifacts={k:_absent(p) for k,p in dict(request='caller-request.json',schema='response-schema.json',
                legacy_report='legacy-harness-report.json',legacy_events='legacy-harness-events.json',
                assessment='evidence-assessment.json').items()},
            verification=dict(same_runtime_observed=False,source_inputs_unchanged=False,wire_and_trace_bound=False,
                root_authority_verified=False,remote_identity_verified=False,actual_wall_time_verified=False,
                model_quality_verified=False,hardware_verified=False,physical_cleanup_verified=False,
                full_task_verified=False,storage_authenticity_verified=False))
        if plan_binding is not None:
            self.r['artifacts'].update(setup_snapshot=_absent('setup-snapshot.json'),
                                       operator_journal=_absent('operator-journal.jsonl'))
            self.r['execution']['host_evidence'] = dict(plan_binding=_copy(plan_binding), setup_status='not_started',
                setup_sha256=None, topology_sha256=None, quantity=quantity,
                recording_mode='post_run_from_retained_events', journal_file_sha256=None,
                journal_head_sha256=None, journal_complete=None, binding_verified=False)

    def phase(self, stage):
        self.stage = stage
        if self.step and self.step['failure'] is None:
            self.step['stage'] = stage

    def error(self, code, stage=None):
        if self.first is None:
            code = code if code in _CODES else _P + code
            self.first = dict(code=code,stage=stage or self.stage)
            self.r['failure'] = dict(self.first); self.r['status'] = 'failed'
            if self.step:
                self.step['failure'] = dict(self.first); self.step['stage'] = self.first['stage']; self.step['status'] = 'failed'

    def secondary(self, code):
        if code not in self.r['cleanup']['secondary_errors']:
            self.r['cleanup']['secondary_errors'].append(code)

    def observe(self, error):
        if isinstance(error, _CONTROL):
            if self.control is None:
                self.control = error
            self.error('internal_error')
        elif isinstance(error, (_Fault,CodexCliResponseError,ModelOperatorBoundaryError)):
            self.error(error.code)
        else:
            self.error('retention_failed' if isinstance(error,OSError) else 'internal_error')

    def throw(self):
        if self.first:
            raise _Fault(self.first['code'])

    def check(self):
        self.throw()
        if self.event is not None and self.event.is_set():
            self.r['execution']['cancellation']['requested']=True
            _fail('cancelled')
        if _now() >= self.deadline:
            _fail('timeout')

    def close(self, handle):
        error = _close_handle(handle, self.deadline)
        good = error is None
        prior = self.r['cleanup']['host_artifacts_closed']
        self.r['cleanup']['host_artifacts_closed'] = good if prior is None else prior and good
        if error is not None:
            self.observe(error) if isinstance(error,_CONTROL) else self.error('cleanup_failed','cleanup')
            self.secondary('host_close_failed')
        return good

    def space(self, reserve=0, reserve_files=0):
        count = total = 0
        for path in self.known:
            try:
                info = path.lstat()
            except FileNotFoundError:
                continue
            if not stat.S_ISREG(info.st_mode) or getattr(info,'st_file_attributes',0) & 1024:
                _fail('retention_failed')
            count += 1; total += info.st_size
        if (count + reserve_files + self.evidence_reservation[0] > _LIMITS['max_known_evidence_files']
                or total + reserve + self.evidence_reservation[1] > _LIMITS['max_observed_evidence_bytes']):
            _fail('limit_exceeded')

    def write(self, path, data, cap, desc=None, *, final=False):
        if len(data) > cap:
            _fail('limit_exceeded')
        self.space(len(data), 1)
        handle = None; complete = False
        try:
            if not final:
                self.check()
            _chain(path.parent, 'retention_failed')
            handle = path.open('xb',buffering=0); self.known.add(path)
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode) or getattr(info,'st_file_attributes',0) & 1024:
                _fail('retention_failed')
            digest = hashlib.sha256(); view = memoryview(data); count = 0
            if desc is not None:
                desc.update(present=True,sha256=digest.hexdigest(),extent='prefix')
            while view:
                amount = handle.write(view)
                if not amount:
                    _fail('retention_failed')
                digest.update(view[:amount]); view=view[amount:]; count+=amount
                if desc is not None:
                    desc.update(bytes=count,sha256=digest.hexdigest())
            complete = True
        except BaseException as error:
            self.observe(error)
            raise
        finally:
            if handle is not None:
                self.close(handle)
        if desc is not None and complete and self.r['cleanup']['host_artifacts_closed']:
            desc.update(complete=True,extent='whole_file')
        if not final:
            self.throw()

    def artifact(self, key, value, *, raw=False, final=False):
        if self.step and key in _FILES:
            filename, cap = _FILES[key]; desc=self.step['artifacts'][key]
            path=self.directory/'calls'/f"{self.step['index']:04d}"/filename
        else:
            desc=self.r['artifacts'][key]; path=self.directory/desc['path']
            cap=8388608 if key=='legacy_events' else 1048576 if key=='setup_snapshot' else 65536 if key in {'schema','assessment'} else 262144
        self.write(path,value if raw else _C(value),cap,desc,final=final)

    def observation(self, key, value, *, final=False):
        value=_copy(value,1048576,'capture_failed')
        if (set(value)!=set('tick setup_revision synthetic hardware_verified devices'.split())
                or type(value['tick']) is not int or value['tick']<0 or type(value['setup_revision']) is not int
                or value['setup_revision']<0 or value['synthetic'] is not True or value['hardware_verified'] is not False
                or type(value['devices']) is not dict or len(value['devices'])!=64):
            _fail('capture_failed')
        self.artifact(key,value,final=final)
        self.step[key]=dict(tick=value['tick'],setup_revision=value['setup_revision'],device_count=64,
                            sha256=_H(_C(value)),present=True)
        return value

    def current(self):
        if (self.trial.runtime is not self.runtime or self.trial.runtime_instance_id!=self.r['execution']['runtime_instance_id']
                or any(getattr(self.runtime,name) is not guard for name,_,_,guard in self.guards)
                or _C(self.runtime.observations())!=_C(self.before)):
            _fail('capture_failed')
        self.r['verification']['same_runtime_observed']=True

    def guard_runtime(self):
        # The same original runtime is passed to the harness. Capture exceptions
        # before its compatibility layer catches BaseException; no second runtime.
        for name in ('execute','advance','observations'):
            original=getattr(self.runtime,name)
            had=name in vars(self.runtime); previous=vars(self.runtime).get(name)
            def guarded(*args,_original=original,_name=name,**kwargs):
                try:
                    self.check()
                    return _original(*args,**kwargs)
                except BaseException as error:
                    if isinstance(error,(_CONTROL+(_Fault,))):
                        self.observe(error)
                    elif _name=='observations' and not (self.step and self.step['dispatch']['intent_seen']):
                        self.error('capture_failed','capture')
                    else:
                        self.error('runtime_uncertain','dispatch')
                    raise
            setattr(self.runtime,name,guarded)
            self.guards.append((name,had,previous,guarded))

    def restore_runtime(self):
        for name,had,previous,guard in reversed(self.guards):
            try:
                if getattr(self.runtime,name) is not guard:
                    self.error('capture_failed','cleanup')
                    self.secondary('runtime_guard_changed')
                elif had:
                    setattr(self.runtime,name,previous)
                else:
                    delattr(self.runtime,name)
            except BaseException as error:
                self.observe(error); self.secondary('runtime_guard_restore_unconfirmed')
        self.guards.clear()

    def capture_setup(self, success):
        if self.plan_binding is None or self.setup_snapshot is not None or self.setup_records is None:
            return
        value = self.trial.setup_snapshot() if success else self.setup_records
        value = _copy(value, 1048576, 'capture_failed')
        if (type(value) is not list or len(value) > 32
                or success and _C(value) != _C(self.setup_records)):
            _fail('capture_failed')
        self.setup_snapshot = value
        host = self.r['execution']['host_evidence']
        host['setup_status'] = 'complete' if success and value else 'partial'
        host['setup_sha256'] = _H(_C(value))
        self.artifact('setup_snapshot', value, final=True)
        if success:
            if not value:
                _fail('capture_failed')
            self.host_topology = _copy(self.trial.topology, 1048576, 'capture_failed')
            host['topology_sha256'] = _H(_C(self.host_topology))

    def capture_journal(self):
        if (self.plan_binding is None or self.host_topology is None or self.setup_snapshot is None
                or not self.r['artifacts']['setup_snapshot']['complete']):
            return
        host = self.r['execution']['host_evidence']
        provenance = dict(runtime_origin='preinitialized', catalog_sha256=self.catalog_sha,
            topology=self.host_topology, topology_sha256=host['topology_sha256'],
            engine_sha256=_H(_C(self.source_pins)),
            engine_fingerprint_kind='sha256_canonical_host_source_pins_v1', source_pins=self.source_pins,
            plan_binding=self.plan_binding, setup_sha256=host['setup_sha256'],
            recording_mode='post_run_from_retained_events')
        if self.quantity is not None:
            provenance['quantity'] = self.quantity
        path = self.directory / 'operator-journal.jsonl'
        desc = self.r['artifacts']['operator_journal']
        journal = None; appended = closed = False
        try:
            header=_journal_header(self.r['run_id'],self.r['execution']['runtime_instance_id'],provenance)
            # Fixed-width chain hashes have the same serialized size as zeros.
            reserved=len(_journal_record('header',header,'0'*64)[1])
            reserved+=sum(len(_journal_record('event',event,'0'*64)[1]) for event in self.events)
            self.space(reserved, 1)
            self.known.add(path)
            journal = _Journal(path, run_id=self.r['run_id'],
                runtime_instance_id=self.r['execution']['runtime_instance_id'], provenance=provenance)
            for event in self.events:
                journal(event)
            appended = True
        except BaseException as error:
            self.observe(error) if isinstance(error, _CONTROL) else self.error('retention_failed', 'journal')
            self.secondary('post_run_journal_failed')
        finally:
            if journal is not None:
                closed = self.close(journal)
        try:
            raw = _read(path, 9437184, 'retention_failed', self)
            desc.update(present=True, bytes=len(raw), sha256=_H(raw), complete=appended and closed,
                        extent='whole_file' if appended and closed else 'prefix')
            observed = _read_journal(path)
            if observed['integrity']['file_sha256'] != _H(raw):
                _fail('retention_failed')
            header = observed['header']; actual = header['provenance']
            if (header['run_id'] != self.r['run_id']
                    or header['runtime_instance_id'] != self.r['execution']['runtime_instance_id']
                    or _C(actual) != _C(provenance) or appended and _C(observed['events']) != _C(self.events)):
                _fail('retention_failed')
            host.update(journal_file_sha256=_H(raw), journal_head_sha256=observed['integrity']['head_sha256'],
                        journal_complete=observed['complete'], binding_verified=appended and closed)
            self.space()
        except BaseException as error:
            self.observe(error) if isinstance(error, _CONTROL) else self.error('retention_failed', 'journal')
            self.secondary('post_run_journal_unconfirmed')

    def source(self):
        self.check()
        if _H(_read(self.catalog_path,1048576,'unsupported_source',self))!=self.catalog_sha:
            _fail('unsupported_source')
        for path,pin in self.sources.items():
            raw=_read(path,1048576,'unsupported_source',self)
            if (len(raw),_H(raw))!=pin:
                _fail('unsupported_source')
        self.throw()

    def event_sink(self, event):
        try:
            event=_copy(event,524288); size=len(_C(event))
            if len(self.events)>=_LIMITS['max_events'] or self.event_bytes+size>_LIMITS['max_events_bytes']:
                _fail('limit_exceeded')
            self.events.append(event); self.event_bytes+=size
            if self.step and event['type']=='intent':
                intent=event['payload']
                self.step['dispatch'].update(intent_seen=True,request_id=intent['request_id'],operation=intent['operation'],
                    reserved_logical_requests=1,runtime_call_attempts=None,effect='unknown')
        except BaseException as error:
            self.observe(error)
            raise

    def attach(self, value):
        if value is None:
            return None
        value=_copy(value)
        if (type(value) is not dict or set(value)!=_RECEIPT_KEYS or type(value.get('exchange_ref')) is not str
                or not _EXCHANGE.fullmatch(value['exchange_ref'])):
            _fail('retention_failed')
        self.step['producer']['receipt']=value
        attempts=value.get('attempts',{})
        pair=[attempts.get('version_process_attempts'),attempts.get('model_process_attempts')]
        if all(type(x) is int and x in (0,1) for x in pair):
            self.attempts[-1]=pair
        for index,key in enumerate(('version_process_attempts','model_process_attempts')):
            self.r['budget'][key]=None if any(p is None for p in self.attempts) else sum(p[index] for p in self.attempts)
        return value

    def retain(self, response, receipt, prompt_raw, timeout):
        try:
            _producer_profile(receipt,self.model,timeout)
        except _ParentFault:
            _fail('retention_failed')
        if (type(response) is not bytes or len(response)>65536 or receipt['kind']!='codex_cli_response_receipt'
                or receipt['status']!='complete' or receipt['failure'] is not None
                or receipt['bindings']['prompt_sha256']!=_H(prompt_raw)
                or receipt['bindings']['schema_sha256']!=_H(self.schema)
                or receipt['bindings']['producer_declaration']!=dict(kind='model',name=_PRODUCER)):
            _fail('retention_failed')
        folder=self.directory/'calls'/f"{self.step['index']:04d}"/'producer'
        if type(receipt['artifacts']) is not dict or set(receipt['artifacts'])!=set(_PRODUCER_FILES):
            _fail('retention_failed')
        for key,(name,cap) in _PRODUCER_FILES.items():
            desc=receipt['artifacts'][key]
            if (type(desc) is not dict or set(desc)!=set(_absent(name)) or desc['path']!=name
                    or desc['present'] is not True or desc['complete'] is not True or desc['overflow'] is not False
                    or desc['extent']!='whole_file' or type(desc['bytes']) is not int or not 0<=desc['bytes']<=cap):
                _fail('retention_failed')
            path=folder/name; self.known.add(path)
            raw=_read(path,cap,'retention_failed',self)
            if len(raw)!=desc['bytes'] or _H(raw)!=desc['sha256']:
                _fail('retention_failed')
            if key=='prompt' and raw!=prompt_raw or key=='response_schema' and raw!=self.schema:
                _fail('retention_failed')
            if key in {'final_text','last_message'} and raw!=response:
                _fail('retention_failed')
        path=folder/'receipt.json'; self.known.add(path)
        raw=_read(path,262144,'retention_failed',self)
        if raw!=_C(receipt):
            _fail('retention_failed')
        self.step['producer']['receipt_sha256']=_H(raw)
        self.step['producer']['response']=dict(present=True,bytes=len(response),sha256=_H(response))
        self.space(); self.throw()

    def policy(self, context):
        try:
            self.check()
            index=len(self.r['steps'])+1
            if index>8:
                _fail('budget_exhausted')
            step=dict(index=index,binding=None,before=None,after=None,
                producer=dict(origin_declaration=self.origin,receipt=None,receipt_sha256=None,response=None),wire=None,
                dispatch=dict(intent_seen=False,request_id=None,operation=None,reserved_logical_requests=0,
                              confirmed_receipts=0,runtime_call_attempts=0,receipt_status=None,effect='not_applicable'),
                stage='capture',status='pending',failure=None,
                artifacts={k:_absent(n) for k,(n,_) in _FILES.items()},
                verification=dict(wire_accepted=False,causal_after_observed=False,event_refs=[]))
            self.r['steps'].append(step); self.step=step
            folder=self.directory/'calls'/f'{index:04d}'; folder.mkdir()
            self.phase('capture'); snapshot=_copy(context,1048576,'capture_failed')
            if (snapshot['goal']!=self.trial.goal or snapshot['topology']!=self.trial.topology
                    or snapshot['role_actions']!=self.actions or len(snapshot['catalog']['profiles'])!=64):
                _fail('capture_failed')
            self.before=self.observation('before',snapshot['observations']); self.current()
            self.artifact('context8',snapshot)
            public=_copy(snapshot,1048576); remaining=public.pop('remaining_budget')
            self.artifact('context7',public)
            self.phase('prompt')
            wall=min(self.deadline-_now(),remaining['wall_seconds'])
            budgets=dict(decisions=remaining['decisions']+1,logical_requests=remaining['logical_requests'],
                         ticks=remaining['ticks'],wall_seconds=wall,transport_retries=0)
            delegation=dict(scope='rf_sensor_proposal_v1',harness_budgets=budgets,
                            outer_limits=dict(model_calls=8-self.r['budget']['reserved_model_calls'],wall_seconds=wall))
            ids=dict(run_id=self.r['run_id'],runtime_instance_id=self.trial.runtime_instance_id,
                     decision_id='operator-loop-decision:'+uuid.uuid4().hex,model_request_id='operator-loop-request:'+uuid.uuid4().hex)
            prompt=_build(public,producer_name=_PRODUCER,delegation=delegation,**ids)
            step['binding']=_copy(prompt['binding'])
            self.artifact('binding',dict(binding=prompt['binding'],delegation=delegation,remaining_budget=remaining))
            prompt_raw=_C(prompt); self.artifact('prompt',prompt_raw,raw=True)
            self.phase('reserve'); self.source(); self.current()
            available=min(self.deadline-_now(),remaining['wall_seconds'])
            if available<=6 or self.r['budget']['reserved_model_calls']>=8:
                _fail('budget_exhausted')
            self.space(sum(cap for _,cap in _PRODUCER_FILES.values())+2097152,
                       len(_PRODUCER_FILES)+1+3)
            # Register fixed original paths before invoking D2, including failed/partial output.
            self.known.update(folder/'producer'/name for name,_ in _PRODUCER_FILES.values())
            self.known.add(folder/'producer'/'receipt.json')
            timeout=float(min(60,available-6))
            self.r['budget']['reserved_model_calls']+=1
            self.r['budget']['producer_calls_started']+=1
            self.attempts.append(None)
            self.r['budget']['version_process_attempts']=self.r['budget']['model_process_attempts']=None
            self.phase('producer')
            try:
                result=_produce(prompt_raw,self.schema,executable=self.executable,requested_model=self.model,
                    evidence_dir=folder/'producer',timeout_seconds=timeout)
            except CodexCliResponseError as error:
                self.error(error.code)
                try:
                    self.attach(error.receipt)
                except BaseException as later:
                    self.observe(later); self.secondary('partial_receipt_unavailable')
                self.throw()
            if type(result) is not tuple or len(result)!=2:
                _fail('retention_failed')
            response,receipt=result; receipt=self.attach(receipt)
            if receipt is None:
                _fail('retention_failed')
            self.phase('retain'); self.retain(response,receipt,prompt_raw,timeout)
            self.check(); self.source(); self.current()
            self.phase('decode'); wire=_decode(response,prompt)
            step['wire']=_copy(wire,65536); step['verification']['wire_accepted']=True
            self.artifact('wire',wire)
            self.phase('gate'); self.source(); self.current(); self.check()
            self.phase('dispatch')
            return _copy(wire['proposal'],65536)
        except BaseException as error:
            self.observe(error)
            raise

    def inspect(self, events):
        if not self.step:
            return
        step=self.step; d=step['dispatch']; wire=step['wire']
        step['verification']['event_refs']=[e['event_id'] for e in events]
        intents=[e for e in events if e['type']=='intent']; receipts=[e for e in events if e['type']=='receipt']
        decisions=[e for e in events if e['type']=='policy_decision']
        if len(intents)>1 or len(receipts)>1 or len(decisions)>1 or any(e['type']=='transport_retry' for e in events):
            _fail('runtime_uncertain')
        if intents:
            intent=intents[0]['payload']; request=intent['request_id']
            d.update(intent_seen=True,request_id=request,operation=intent['operation'],reserved_logical_requests=1,
                     runtime_call_attempts=None,effect='unknown')
            observations=[e for e in events if e['type']=='observation' and e['payload'].get('cause_request_id')==request]
            if (wire is None or len(decisions)!=1 or _C(decisions[0]['payload']['proposal'])!=_C(wire['proposal'])
                    or len(receipts)!=1 or receipts[0]['payload']['request_id']!=request or len(observations)!=1):
                _fail('runtime_uncertain')
            receipt=receipts[0]['payload']['result']; after=observations[0]['payload']['observation']
            self.artifact('dispatch_receipt',receipt,final=True)
            if (receipt['status'] not in _STATUSES or self.runtime is not self.trial.runtime
                    or self.trial.runtime_instance_id!=self.r['execution']['runtime_instance_id']
                    or _C(self.runtime.observations())!=_C(after)
                    or after['tick']!=self.before['tick']+int(d['operation']=='advance')
                    or after['setup_revision']<self.before['setup_revision']):
                _fail('runtime_uncertain')
            self.observation('after',after,final=True)
            d.update(confirmed_receipts=1,runtime_call_attempts=1,receipt_status=receipt['status'],
                     effect='unchanged' if _C(after)==_C(self.before) else 'changed')
            step['verification']['causal_after_observed']=True
            if step['failure'] is None:
                step['status']='observed' if receipt['status'] in {'ok','pending'} else 'rejected'
                step['stage']='observe'
        elif wire is not None and wire['proposal']['kind']=='stop':
            report=self.harness.result()
            if (len(decisions)!=1 or report is None
                    or report['termination']!=dict(reason='policy_stop',policy_claim=wire['proposal']['claim'])
                    or report['unresolved_request_ids']):
                _fail('runtime_uncertain')
            after=self.runtime.observations()
            if _C(after)!=_C(self.before):
                _fail('capture_failed')
            self.observation('after',after,final=True)
            if step['failure'] is None:
                step['status']='stopped'; step['stage']='observe'
        elif self.first is None and wire is not None:
            _fail('runtime_uncertain')

    def run(self):
        self.directory.mkdir(); _chain(self.directory,'retention_failed')
        (self.directory/'calls').mkdir()
        self.artifact('schema',self.schema,raw=True)
        pins={}
        for name in _SOURCE:
            path=Path(__file__).resolve().parents[1]/name
            raw=_read(path,1048576,'unsupported_source',self)
            self.sources[path]=(len(raw),_H(raw)); pins['labflow/'+name]=dict(bytes=len(raw),sha256=_H(raw))
        self.source_pins = pins
        execution = dict(catalog_path=str(self.catalog_path), executable=str(self.executable))
        if self.source_settings is not None:
            execution['source_settings'] = self.source_settings
        if self.plan_binding is not None:
            execution['plan_binding'] = self.plan_binding
            if self.quantity is not None:
                execution['quantity'] = self.quantity
        self.artifact('request',dict(schema_version=1,kind='codex_virtual_loop_request',run_id=self.r['run_id'],
            declaration=self.r['declaration'],limits=self.r['budget']['limits'],source_pins=pins,
            execution=execution))
        self.source()
        try:
            catalog=_load(self.catalog_path); self.actions=_actions()
            if len(catalog['profiles'])!=64:
                _fail('unsupported_source')
            if self.plan_binding is not None:
                self.setup_records = []
                self.r['execution']['host_evidence']['setup_status'] = 'initializing'
                self.trial=_prepare(catalog,condition=self.scenario,seed=0,
                    power_dbm=self.source_settings['power_dbm'],source_settings=self.source_settings,
                    setup_records=self.setup_records)
            elif self.source_settings is None:
                self.trial=_prepare(catalog,condition=self.scenario,seed=0,power_dbm=12.5)
            else:
                self.trial=_prepare(catalog,condition=self.scenario,seed=0,
                    power_dbm=self.source_settings['power_dbm'],source_settings=self.source_settings)
            self.runtime=self.trial.runtime
            if len(self.trial.topology['devices'])!=64 or not _ID.fullmatch(self.trial.runtime_instance_id):
                _fail('capture_failed')
        except _CONTROL:
            raise
        except _Fault:
            raise
        except Exception:
            _fail('capture_failed')
        self.r['execution']['runtime_instance_id']=self.trial.runtime_instance_id
        self.capture_setup(True)
        self.guard_runtime()
        def policy(context):
            return self.policy(context)
        def clock():
            try:
                return _now()
            except BaseException as error:
                self.observe(error)
                raise
        policy.policy_id='codex_persistent_virtual_loop'
        self.harness=_Harness(self.runtime,policy,goal=self.trial.goal,catalog=self.trial.catalog,
            topology=self.trial.topology,role_actions=self.actions,budgets=dict(_BUDGET),run_id=self.r['run_id'],
            runtime_instance_id=self.trial.runtime_instance_id,event_sink=self.event_sink,clock=clock)
        for _ in range(9):
            self.check()
            start=len(self.events); previous=len(self.r['steps'])
            self.harness.step()
            self.phase('observe')
            if len(self.r['steps'])>previous:
                self.inspect(self.events[start:])
            self.check()
            report=self.harness.result()
            if report is not None:
                if report.get('termination',{}).get('reason') not in {
                        'policy_stop','decision_budget','request_budget','tick_budget','wall_deadline'}:
                    self.error('runtime_uncertain' if self.step else 'capture_failed', 'observe' if self.step else 'capture')
                    self.throw()
                break
        else:
            _fail('budget_exhausted')
        self.source(); self.r['verification']['source_inputs_unchanged']=True

    def finalize(self):
        if self.finished:
            return
        self.finished=True
        self.stage='cleanup'
        self.r['execution']['cancellation']['requested']=bool(self.event is not None and self.event.is_set())
        report=events=None
        if self.plan_binding is not None and self.setup_snapshot is None:
            try:
                self.capture_setup(False)
            except BaseException as error:
                self.observe(error); self.secondary('setup_capture_unconfirmed')
        if self.harness is not None:
            if self.harness.result() is None:
                try:
                    self.harness.stop(); self.r['cleanup']['supervisor_stop_requested']=True; self.harness.step()
                except BaseException as error:
                    self.observe(error); self.secondary('supervisor_termination_unconfirmed')
            try:
                report=self.harness.result(); events=self.harness.events()
                if (type(report) is not dict or report.get('kind')!='virtual_fleet_harness_result'
                        or report.get('ai_model_called') is not False or report.get('policy',{}).get('kind')!='fixture'
                        or _C(events)!=_C(self.events)):
                    _fail('runtime_uncertain')
                self.r['cleanup']['terminal_report_observed']=True
                self.r['budget']['harness_usage']=_copy(report['usage'])
                self.r['termination']=dict(_copy(report['termination']),unresolved_request_ids=_copy(report['unresolved_request_ids']))
                self.artifact('legacy_report',report,final=True); self.artifact('legacy_events',events,final=True)
                self.r['verification']['wire_and_trace_bound']=bool(self.r['steps']) and not report['unresolved_request_ids'] and all(
                    s['verification']['wire_accepted'] and s['failure'] is None for s in self.r['steps'])
                self.r['evidence_assessment']['evaluator_called']=True
                result=_copy(_evaluate(self.trial,report,events),65536)
                self.r['evidence_assessment']['result']=result
                self.r['evidence_assessment']['goal_observed']=result.get('summary_code')=='observed_goal_satisfied' and result.get('verdict')=='pass'
                self.artifact('assessment',self.r['evidence_assessment'],final=True)
            except BaseException as error:
                self.observe(error)
        self.capture_journal()
        self.restore_runtime()
        self.trial=self.runtime=self.harness=None
        self.r['cleanup']['runtime_references_released']=True
        self.r['failure']=_copy(self.first) if self.first else None
        self.r['status']='failed' if self.first else 'stopped' if self.r['termination']['reason']=='policy_stop' else 'bounded'
        self.r['budget']['elapsed_seconds']=max(0.0,_now()-self.start)
        if self.r['budget']['elapsed_seconds']>=180:
            self.error('timeout','finalize')
        self.stage='finalize'
        try:
            raw=_C(self.r)
            self.write(self.directory/'loop-receipt.json',raw,_LIMITS['max_output_bytes'],final=True)
        except BaseException as error:
            self.observe(error); self.secondary('receipt_write_failed')
        if self.first:
            self.r['failure']=dict(self.first); self.r['status']='failed'


def run_codex_virtual_loop(*, catalog_path: Path, catalog_sha256: str, response_schema_bytes: bytes,
        executable: Path, requested_model: str, scenario: str, evidence_dir: Path,
        execution_origin: str, cancel_event=None, source_settings=None, plan_binding=None, quantity=None, evidence_reservation=None) -> dict:
    """Run one explicitly delegated synthetic loop; provenance declarations grant no authority."""
    runner=None; receipt=None; code=None; control=None
    try:
        reservation=_reservation(evidence_reservation)
        options={} if reservation is None else dict(evidence_reservation=reservation)
        start=_now()
        source,binding,declared_quantity=_preflight(catalog_path,catalog_sha256,response_schema_bytes,executable,requested_model,scenario,
                          evidence_dir,execution_origin,cancel_event,source_settings,plan_binding,quantity)
        runner=_Loop(catalog_path,catalog_sha256,response_schema_bytes,executable,requested_model,scenario,
                     evidence_dir,execution_origin,cancel_event,start,source,binding,declared_quantity,**options)
        try:
            runner.run()
        except BaseException as error:
            runner.observe(error)
        finally:
            try:
                runner.finalize()
            except BaseException as error:
                runner.observe(error)
            finally:
                # Even a failing compatibility result()/cleanup boundary must
                # release this run's guards and references, without a new trial.
                try:
                    runner.restore_runtime()
                except BaseException as error:
                    runner.observe(error)
                runner.trial=runner.runtime=runner.harness=None
                runner.r['cleanup']['runtime_references_released']=True
        control=runner.control
        code=runner.first['code'] if runner.first else None
        try:
            receipt=_copy(runner.r,262144,'limit_exceeded')
        except _Fault as error:
            if code is None:
                code=error.code
    except _CONTROL as error:
        control=error
    except _Fault as error:
        code=error.code
    except Exception:
        code=_P+'internal_error'
    if control is not None:
        raise control
    if code is not None:
        _fixed(code,receipt)
    return receipt

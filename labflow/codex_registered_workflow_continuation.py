"""One manually recorded same-case continuation; never retry a consumed permit."""
import math
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
import sys
import time

from . import codex_registered_conducted_workflow_host as _host
from . import codex_conducted_workflow_registration as _registration
from . import codex_registered_workflow_expiry_reauthorization as _calendar
from . import control_packet_prepare as _native
from .store import Store, canonical

__all__=['continue_registered_workflow','main']
_PREFIX='codex_registered_workflow_continuation_'
_CONTROL=_host._CONTROL
_C=_host._C
_H=_host._H
_keys=_host._keys
_same=_host._same
_NAMESPACE='manual-continuation-01'
_CLAIM='manual-continuation-claimed-v1.json'
_RECORD='root-manual-continuation-v1.json'
_INTERPRETATION='root_interpretation_of_existing_same_case_grant_not_direct_user_continuation_words'
_TAIL_FILES=14
_TAIL_BYTES=5505024+262144+2097152


class _Failure(ValueError):pass
def _fail(code):raise _Failure(_PREFIX+code)


def _remaining_budget(count,elapsed,files,size):
    if type(count) is not int or count!=1:_fail('original_spending_unknown')
    if type(elapsed) not in (int,float) or not math.isfinite(elapsed) or not 0<=elapsed<174:_fail('original_elapsed_unknown_or_exhausted')
    if (type(files) is not int or type(size) is not int or files<0 or size<0
            or files+_TAIL_FILES>=192 or size+_TAIL_BYTES>=33554432):_fail('evidence_limit')
    return dict(model_process_limit=7,wall_seconds_limit=180.0-float(elapsed),
        known_total_before_continuation=18,maximum_known_total=25,
        evidence_reservation=dict(files=files+_TAIL_FILES,bytes=size+_TAIL_BYTES))


def _read(io,path,cap):return _host._json(io.read(path,cap))
def _pin(raw):return _host._pin(raw)


def _history(io,root,anchor,config):
    journal=root/'workflow-continuation.sqlite3'
    io.read(journal,33554432)
    # Immutable original ledger: this entry never connects mode=rw or appends.
    con=sqlite3.connect(journal.as_uri()+'?mode=ro',uri=True,timeout=0)
    primary=None
    try:
        con.execute('PRAGMA trusted_schema=OFF');con.execute('PRAGMA query_only=ON');con.execute('BEGIN')
        events=_host._history(con,anchor,config)
        if len(events)!=5:_fail('original_history_not_finished')
        _same(_read(io,root/'workflow-claimed.json',65536),events['reserved'])
        finished=events['finished']
        if finished['status']!='failed' or finished['local_model_processes']!=1 or type(finished['local_model_processes']) is not int or finished['cleanup_confirmed'] is not True:
            _fail('original_failure_not_eligible')
        return events
    except BaseException as error:primary=error;raise
    finally:
        try:_registration._close_sql(con)
        except BaseException:
            if primary is None:raise


def _failed_execution(io,evidence,events,model,workflow,original_schema_sha):
    finished=events['finished']
    raw=io.read(evidence/'execution-receipt.json',262144)
    _same(_pin(raw),finished['execution_receipt']);execution=_host._json(raw)
    final_raw=io.read(evidence/'finalizer-receipt.json',2097152)
    _same(_pin(final_raw),finished['finalizer_receipt'])
    finalizer=_host._json(final_raw)
    failure=dict(code='codex_cli_response_stream_invalid',stage='producer')
    if execution['status']!='failed' or execution['failure']!=failure or finalizer['status']!='held' or finalizer['failure']!=failure:
        _fail('original_failure_not_eligible')
    binding=execution['binding']
    _same(binding['context_sha256'],workflow['context_sha256'])
    _same(binding['analysis_sha256'],workflow['analysis_sha256'])
    _same(binding['plan_input_sha256'],workflow['plan_input_sha256'])
    actual,cleanup,pins=_host._observe(execution,evidence,model,True)
    if actual!=1 or not cleanup:_fail('original_spending_unknown')
    _same(pins,finished['producer_receipts'])
    loop=execution['loop'];steps=loop['steps']
    # The retained failure must have used the exact historical profile that
    # _prepare verified, even when its own receipt/ledger pins agree internally.
    _same(original_schema_sha,workflow['schema_sha256'])
    _same(loop['declaration'],dict(goal_kind='acquire_fresh_rf_sensor',scope='rf_sensor_proposal_v1',
        scenario='normal',requested_model=model,producer_name='dgm-virtual-operator-v1',
        catalog_sha256=workflow['catalog_sha256'],schema_sha256=original_schema_sha,
        origin_declaration='actual_cli'))
    if len(steps)!=1 or loop['budget']['producer_calls_started']!=1:_fail('original_failure_not_eligible')
    step=steps[0];receipt=step['producer']['receipt']
    _same(receipt['bindings']['schema_sha256'],original_schema_sha)
    io.read(evidence/'loop/calls/0001/producer/receipt.json',262144)
    lifecycle=receipt['lifecycle']
    if (receipt['status']!='failed' or receipt['failure']!=dict(code='codex_cli_response_stream_invalid',phase='collect')
            or type(lifecycle['agent_messages']) is not int or lifecycle['agent_messages']!=0
            or type(lifecycle['tool_items']) is not int or lifecycle['tool_items']!=0
            or receipt['attempts']['application_retries']!=0):_fail('original_failure_not_eligible')
    _same(step['dispatch'],dict(intent_seen=False,request_id=None,operation=None,reserved_logical_requests=0,
        confirmed_receipts=0,runtime_call_attempts=0,receipt_status=None,effect='not_applicable'))
    if step['wire'] is not None:_fail('original_failure_not_eligible')
    # Read the actual retained producer stdout, never a root boolean/error label.
    descriptor=receipt['artifacts']['stdout_jsonl']
    wire=io.read(evidence/'loop/calls/0001/producer/stdout.jsonl',8388608)
    if (descriptor['complete'] is not True or descriptor['overflow'] is not False
            or descriptor['bytes']!=len(wire) or descriptor['sha256']!=_H(wire)):_fail('original_failure_not_eligible')
    errors=[]
    for line in wire.splitlines():
        event=_host._json(line)
        if event.get('type') in ('error','turn.failed'):errors.append(event)
        elif event.get('type') not in ('thread.started','turn.started'):_fail('original_failure_not_eligible')
    if not errors or not any(all(word in canonical(event) for word in ('400','oneOf','schema')) for event in errors):
        _fail('original_schema_error_not_verified')
    return execution,loop['budget']['elapsed_seconds']


def _manual_record(io,operator,source_raw,publication_raw,config,workflow,events,scenario,model,current_sha):
    raw=io.read(operator/_RECORD,65536);value=_host._json(raw)
    _keys(value,'schema_version kind authority_source manual_continuation_reference interpretation action original_operator_source original_publication original case scope current_schema_sha256 remaining_model_processes expires_at')
    if (type(value['schema_version']) is not int or value['schema_version']!=1
            or value['kind']!='codex_root_same_case_manual_continuation'
            or value['action']!='continue_same_registered_synthetic_workflow_once'
            or value['interpretation']!=_INTERPRETATION):_fail('manual_authority_invalid')
    original_source=_host._json(source_raw)
    _same(value['authority_source'],original_source['authority_source'])
    _registration._text(value['manual_continuation_reference'])
    _same(value['original_operator_source'],_pin(source_raw));_same(value['original_publication'],_pin(publication_raw))
    _same(value['scope'],_registration._LIMITS)
    if type(value['remaining_model_processes']) is not int or value['remaining_model_processes']!=7:_fail('budget_invalid')
    _same(value['current_schema_sha256'],current_sha)
    _same(value['original'],dict(journal_id=config['journal_id'],permit_id=config['permit_id'],
        workflow_sha256=config['workflow_sha256'],registration_sha256=config['registration_sha256'],
        finished_sha256=_H(_C(events['finished'])),execution_receipt=events['finished']['execution_receipt'],
        finalizer_receipt=events['finished']['finalizer_receipt'],producer_receipts=events['finished']['producer_receipts']))
    _same(value['case'],dict(scenario_id=scenario,requested_model=model,context_sha256=workflow['context_sha256'],
        analysis_sha256=workflow['analysis_sha256'],plan_input_sha256=workflow['plan_input_sha256'],
        source_settings_sha256=_H(_C(workflow['source_settings'])),catalog_sha256=workflow['catalog_sha256']))
    if value['expires_at'] is not None:_host._native_host._expiry(value['expires_at'])
    return raw,value


def continue_registered_workflow(*,scenario_id,requested_model):
    result=dict(schema_version=1,kind='codex_registered_workflow_continuation_receipt',status='not_run',phase='authority',
        scenario_id=scenario_id if type(scenario_id) is str else None,requested_model=requested_model if type(requested_model) is str else None,
        original=None,manual_record=None,calendar_reauthorization=None,reservation=None,execution=None,finalization=None,history=None,errors=[],
        verification=dict(authority_scope='not_validated',dispatch='not_invoked',same_account_arbitrary_code_defense=False,
            origin_authenticated=False,remote_model_identity_verified=False,hardware_verified=False,measurement='not_assessed'))
    io=cancel=None;owned=dict(store=None);primary=None;claimed=entered=namespace_created=False;execution=finalized=None
    root=evidence=target=budget=workflow=config=manual=None;old_execution=None;actual=None;cleanup=False;pins=[];handoff=None
    calendar_deadline=calendar_pin=None
    started=time.monotonic();execution_pin=finalizer_pin=None
    def error(exc,phase):
        nonlocal primary
        if primary is None:primary=exc
        if type(exc) is _Failure:code=str(exc)
        elif isinstance(exc,(_host.IntakePlanVirtualExecutionError,_host.ConductedExecutionResultFinalizerError)):code=exc.code
        else:code=_PREFIX+('missing_input' if isinstance(exc,FileNotFoundError) else 'already_claimed' if isinstance(exc,FileExistsError)
            else 'interrupted' if isinstance(exc,_CONTROL) else 'native_or_binding_rejected')
        if len(result['errors'])<8:result['errors'].append(dict(phase=phase,code=code))
        result['status']='unknown' if claimed or entered else 'not_run'
        if claimed and result['history'] is not None:result['history']['actual_total_model_processes']=None
    try:
        _host._native_host._id(scenario_id)
        if type(requested_model) is not str or requested_model not in _host._MODELS:_fail('model_invalid')
        parent=_native._local_path(_registration._operator_parent());operator=parent/_registration._OPERATOR
        root,_=_host._path(_host._profile_root(),directory=True)
        if root!=parent/_registration._TARGET:_fail('fixed_profile_mismatch')
        io=_registration._IO(parent);io.tree.directory(operator);io.namespace(root)
        source_raw=io.read(operator/'root-delegation-v1.json',65536)
        anchor=_registration._authority(_host._json(source_raw))
        meta_raw=io.read(operator/'prepared-inputs-v1.json',65536)
        _same(_H(meta_raw),_host._json(source_raw)['prepared_manifest_sha256'])
        meta=_host._json(meta_raw)
        publication_raw=io.read(operator/'preparation-complete-v1.json',65536)
        publication=_host._json(publication_raw)
        _keys(publication,'schema_version kind operator_source prepared_input files profile')
        _same(publication['operator_source'],_pin(source_raw));_same(publication['prepared_input'],_pin(meta_raw))
        if (type(publication['schema_version']) is not int or publication['schema_version']!=1
                or publication['kind']!='conducted_workflow_preparation_publication' or publication['profile']!=_registration._TARGET):_fail('publication_invalid')
        expected=set(_registration._FILES)|{'root-continuation-anchor.json','operator-control.json','registered-workflow.json','cancel-request.json','workflow-continuation.sqlite3'}
        if set(publication['files'])!=expected:_fail('publication_invalid')
        for leaf in expected-{'workflow-continuation.sqlite3','cancel-request.json'}:
            raw=io.read(root/leaf,1048576);_same(_pin(raw),publication['files'][leaf])
        _same(_read(io,root/'root-continuation-anchor.json',65536),anchor)
        config=_read(io,root/'operator-control.json',16384)
        _keys(config,'schema_version kind anchor_sha256 journal_id permit_id registration_sha256 workflow_sha256 registered_input_root store_root executable')
        if type(config['schema_version']) is not int or config['schema_version']!=1 or config['kind']!='codex_registered_conducted_workflow_control':_fail('profile_invalid')
        _same(config['anchor_sha256'],_H(_C(anchor)))
        for key in ('journal_id','permit_id'):_host._native_host._id(config[key])
        _same({key:meta[key] for key in ('scenario_id','requested_model','journal_id','permit_id','registered_input_root','store_root','executable')},
            dict(scenario_id=scenario_id,requested_model=requested_model,**{key:config[key] for key in ('journal_id','permit_id','registered_input_root','store_root','executable')}))
        if set(meta['files'])!=set(_registration._FILES):_fail('prepared_binding_invalid')
        for leaf in _registration._FILES:_same(meta['files'][leaf],publication['files'][leaf])
        evidence,_=_host._path(root/'runs'/config['permit_id'],directory=True)
        target=evidence/_NAMESPACE
        if (_native._destination_exists(io.tree,target) or
                _native._destination_exists(io.tree,evidence/_CLAIM)):_fail('already_claimed')
        result['phase']='history';events=_history(io,root,anchor,config)
        _same(events['permit']['requested_model'],requested_model)
        result['phase']='current';workflow,context,analysis,plan,historical_schema=_host._prepare(root,config,scenario_id,owned)
        if workflow['schema_version']!=3:_fail('completed_current_profile_required')
        selection=_host._native_host._registration(root,config,scenario_id)
        _same(_host._completed_scope(owned['store'],selection,config),owned['completed_scope'])
        closing=owned['store'];owned['store']=None;closing.close()
        from .virtual_fleet.operator_response_schema import current_response_schema_bytes,CURRENT_SCHEMA_SHA256,LEGACY_SCHEMA_SHA256
        if _H(historical_schema)!=LEGACY_SCHEMA_SHA256:_fail('original_schema_not_legacy')
        result['phase']='original_failure';old_execution,elapsed=_failed_execution(
            io,evidence,events,requested_model,workflow,_H(historical_schema))
        schema=current_response_schema_bytes()
        result['phase']='manual_record'
        manual_raw,manual=_manual_record(io,operator,source_raw,publication_raw,config,workflow,events,scenario_id,requested_model,CURRENT_SCHEMA_SHA256)
        result['manual_record']=_pin(manual_raw)
        result['phase']='calendar_authority'
        calendar_deadline,calendar_pin=_calendar.calendar_deadline(
            io,operator,source_raw,publication_raw,manual_raw,manual,events,CURRENT_SCHEMA_SHA256)
        result['calendar_reauthorization']=calendar_pin
        original_budget=_host._OutputBudget(evidence)
        limits=_remaining_budget(1,elapsed,original_budget.files,original_budget.bytes)
        current=owned['current_facts_plan']
        maximum_handoff=_host._handoff_raw(config['workflow_sha256'],current,
            dict(bytes=262144,sha256='0'*64),dict(bytes=2097152,sha256='0'*64))
        limits['evidence_reservation']['files']+=1
        limits['evidence_reservation']['bytes']+=len(maximum_handoff)
        if limits['evidence_reservation']['files']>=192 or limits['evidence_reservation']['bytes']>=33554432:_fail('evidence_limit')
        handoff=current
        result['original']=dict(permit_id=config['permit_id'],workflow_sha256=config['workflow_sha256'],
            finished_sha256=_H(_C(events['finished'])),execution_receipt=events['finished']['execution_receipt'],
            run_id=old_execution['binding']['run_id'],runtime_instance_id=old_execution['binding']['runtime_instance_id'])
        result['history']=dict(inherited_model_processes=17,original_model_processes=1,continuation_model_processes=None,
            known_total_model_processes=18,actual_total_model_processes=None,usage_complete=False,unknown_usage_components=None,cost=None)
        # Fresh source/current read immediately before the native create-once claim.
        store=Store.open_existing(config['store_root']);owned['store']=store
        _same(_host._completed_scope(store,selection,config),owned['completed_scope'])
        closing=owned['store'];owned['store']=None;closing.close()
        _host._native_host._registration(root,config,scenario_id)
        executable,_=_host._path(config['executable'],directory=False)
        if executable.name.lower()!='codex.exe':_fail('executable_invalid')
        cancel=_host._Cancel(root)
        if cancel.is_set():_fail('cancelled')
        io.current()
        ttl=lambda value:(datetime.strptime(value,'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)-datetime.now(timezone.utc)).total_seconds()
        calendar_remaining=lambda:float('inf') if calendar_deadline is None else min(ttl(manual['expires_at']),ttl(calendar_deadline))
        wall=min(limits['wall_seconds_limit']-(time.monotonic()-started),calendar_remaining())
        if wall<=6:_fail('wall_budget_exhausted')
        result['phase']='claim'
        # Two fixed create-once objects: losing a directory or one marker does
        # not make a previous attempt fresh. A partial prefix stays terminal.
        io.tree.directory(evidence)
        claim=dict(schema_version=1,kind='same_case_manual_continuation_claim',attempt=1,original=result['original'],
            manual_record=result['manual_record'],calendar_reauthorization=calendar_pin,
            prior_model_processes=1,maximum_additional_model_processes=7,
            current_schema_sha256=CURRENT_SCHEMA_SHA256,original_elapsed_seconds=elapsed,wall_seconds_limit=wall)
        # Mark claimed before the first possible partial write; the resulting
        # marker or namespace is never removed by this API.
        claimed=True
        io.write(evidence/_CLAIM,_C(claim))
        fd=io.backend._relative(io.backend.directories[evidence],_NAMESPACE,directory=True,create=True,access=0x1000A1,share=3)
        io.backend.directories[target]=fd;io.backend.held.append(fd);namespace_created=True
        budget=_host._OutputBudget(evidence)
        io.write(target/'claim-v1.json',_C(claim))
        result['reservation']=dict(state='claimed',claim=_pin(_C(claim)),namespace=_NAMESPACE,maximum_additional_model_processes=7)
        result['verification']['authority_scope']='fixed_native_root_same_case_calendar_reauthorization' if calendar_pin else 'fixed_native_root_same_case_manual_record'
        result['phase']='execution';cancel.start();entered=True;result['verification']['dispatch']='invoked'
        wall=min(limits['wall_seconds_limit']-(time.monotonic()-started),calendar_remaining())-1.0
        if wall<=6:_fail('wall_budget_exhausted')
        try:
            execution=_host._execute(context,analysis,plan,expected_revision=context['revision'],expected_context_sha256=workflow['context_sha256'],
                expected_plan_input_sha256=workflow['plan_input_sha256'],catalog_path=root/'catalog.json',catalog_sha256=workflow['catalog_sha256'],
                response_schema_bytes=schema,executable=executable,requested_model=requested_model,scenario='normal',evidence_dir=target/'loop',
                execution_origin='actual_cli',cancel_event=cancel.event,quantity=workflow['quantity'],
                model_process_limit=7,wall_seconds_limit=wall,evidence_reservation=limits['evidence_reservation'])
        except _host.IntakePlanVirtualExecutionError as exc:execution=exc.receipt;error(exc,'execution')
        closing=cancel;cancel=None;closing.close()
        observed=_host._OutputBudget(evidence);budget=observed
        execution_pin=_host._save(target/'execution-receipt.json',execution,budget,262144)
        actual,cleanup,pins=_host._observe(execution,target,requested_model,True)
        if actual is None or not cleanup or not 0<=actual<=7:_fail('execution_unknown')
        if (execution['binding']['run_id']==old_execution['binding']['run_id']
                or execution['binding']['runtime_instance_id']==old_execution['binding']['runtime_instance_id']):_fail('runtime_lineage_invalid')
        result['execution']=dict(run_id=execution['binding']['run_id'],runtime_instance_id=execution['binding']['runtime_instance_id'],
            status=execution['status'],failure=execution['failure'],receipt=execution_pin,producer_receipts=pins)
        result['phase']='finalizer';budget.reserve(8,3*1048576)
        try:
            finalized=_host._finalize(execution,expected_execution_sha256=_H(_C(execution)),evidence_dir=target/'loop',measurement_ref=None,
                measurement_selection_policy=workflow['measurement_selection_policy'],workspace_root=target,artifact_name='conducted-draft')
        except _host.ConductedExecutionResultFinalizerError as exc:finalized=exc.receipt
        finalizer_pin=_host._save(target/'finalizer-receipt.json',finalized,budget,2097152)
        result['finalization']=dict(status=finalized['status'],result_status=finalized['result']['status'] if finalized['result'] else None,
            artifact=finalized['artifact'],failure=finalized['failure'],receipt=finalizer_pin)
        result['status']='completed' if execution['failure'] is None and finalized['status']=='stored' and finalized['result'] and finalized['result']['status']=='recorded' else 'failed'
    except BaseException as exc:error(exc,result['phase'])
    finally:
        if owned['store'] is not None:
            closing=owned['store'];owned['store']=None
            try:closing.close()
            except BaseException as exc:error(exc,'store_close')
        if cancel is not None:
            try:cancel.close()
            except BaseException as exc:error(exc,'cancel_close')
        if namespace_created:
            try:
                actual,cleanup,pins=_host._observe(execution,target,requested_model,entered)
                if actual is None or not cleanup or actual>7:result['status']='unknown';actual=None
                result['history'].update(continuation_model_processes=actual,known_total_model_processes=18+actual if actual is not None else 18,
                    actual_total_model_processes=18+actual if actual is not None and cleanup else None)
                io.current()
                finish=dict(schema_version=1,kind='same_case_manual_continuation_finished',attempt=1,status=result['status'],
                    original=result['original'],manual_record=result['manual_record'],calendar_reauthorization=calendar_pin,
                    local_model_processes=actual,cleanup_confirmed=cleanup,
                    execution_receipt=execution_pin,finalizer_receipt=finalizer_pin,producer_receipts=pins,errors=result['errors'].copy(),
                    current_valid_result='continuation' if result['status']=='completed' else None,original_failure_preserved=True)
                if handoff is not None:
                    raw=_host._handoff_raw(config['workflow_sha256'],handoff,execution_pin,finalizer_pin)
                    io.write(target/'current-handoff.json',raw)
                io.write(target/'finished-v1.json',_C(finish))
                if result['reservation'] is not None:result['reservation']['state']='finished'
            except BaseException as exc:error(exc,'finish')
        if io is not None:
            for phase,close in [('file_close',io.close_files),('directory_close',io.close_dirs)]:
                try:close()
                except BaseException as exc:error(exc,phase)
    if isinstance(primary,_CONTROL):raise primary
    return result


def main(argv=None):
    args=sys.argv[1:] if argv is None else argv
    if args in (['--help'],['-h']):
        sys.stdout.write('Usage: --scenario-id ID --model gpt-6.1-sol|gpt-6-astra\n');return 0
    try:
        if type(args) is not list or len(args)!=4 or not all(type(x) is str for x in args):_fail('arguments_invalid')
        options=dict(zip(args[::2],args[1::2]))
        if set(options)!={'--scenario-id','--model'} or options['--model'] not in _host._MODELS:_fail('arguments_invalid')
        _host._native_host._id(options['--scenario-id'])
    except Exception:
        sys.stderr.write(canonical(dict(kind='codex_registered_workflow_continuation_error',status='not_run',code=_PREFIX+'arguments_invalid'))+'\n');return 2
    result=continue_registered_workflow(scenario_id=options['--scenario-id'],requested_model=options['--model'])
    raw=_C(result)
    if len(raw)>69632:_fail('output_limit')
    (sys.stdout if result['status']=='completed' else sys.stderr).write(raw.decode('utf-8')+'\n')
    return dict(completed=0,not_run=3,failed=4,unknown=5)[result['status']]


if __name__=='__main__':raise SystemExit(main())

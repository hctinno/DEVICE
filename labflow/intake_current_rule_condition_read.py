"""Bind one original condition review to two observed current Store snapshots."""
import hashlib
from pathlib import Path

from . import fcc_report_cases as _json
from .intake_current_facts_plan import read_current_conducted_plan_from_facts
from .intake_rule_condition_gate import evaluate_intake_rule_conditions
from .store import canonical
from .ui_read_model import IntakeReadModel,ReadModelError


__all__=['read_current_rule_conditions']
_BYTES=16*1024*1024
_PREFIX='intake_current_rule_condition_read_'
_GATE_KEYS={'schema_version','kind','status','binding','rule_results','gaps','questions','snapshots',
    'normative_verdict','verification'}


def _invalid():raise ReadModelError(_PREFIX+'result_invalid') from None


def _bounded(value):
    try:
        return _json._plain(value,byte_limit=_BYTES,depth_limit=48,node_limit=400000,
            string_limit=_BYTES,detach=False)
    except _json.FccReportCaseError as error:
        suffix='result_limit' if error.code=='fcc_case_limit_exceeded' else 'result_invalid'
        raise ReadModelError(_PREFIX+suffix) from None


def _parts(value,keys):
    _bounded(value)
    if type(value) is not dict or set(value)!=keys:_invalid()
    context,analysis=value['context'],value['analysis']
    if (type(context) is not dict or type(analysis) is not dict
            or type(context.get('revision')) is not int or context['revision']<1):_invalid()
    return context,analysis


def _binding(context,analysis):
    return dict(revision=context['revision'],
        context_sha256=hashlib.sha256(canonical(context).encode('utf-8')).hexdigest(),
        analysis_sha256=hashlib.sha256(canonical(analysis).encode('utf-8')).hexdigest())


def read_current_rule_conditions(workspace,intake_id,*,method,rules,rule_sources,inputs,execution_context,
        expected_revision=None,expected_context_sha256=None) -> dict:
    """One facts read, one unchanged gate, one post-read; never grant authority.

    A changed observed current snapshot holds the compound while retaining the
    original review. Parent read/gate errors and controls propagate unchanged.
    """
    workspace=Path(workspace).resolve()
    native=read_current_conducted_plan_from_facts(workspace,intake_id,method=method,
        expected_revision=expected_revision,expected_context_sha256=expected_context_sha256)
    context,analysis=_parts(native,{'context','analysis','facts_plan'})
    wrapper=native['facts_plan']
    if (type(wrapper) is not dict or wrapper.get('status') not in ('ready_for_simulation','blocked')
            or type(wrapper.get('plan_input')) is not dict):_invalid()
    before=_binding(context,analysis)
    gate=evaluate_intake_rule_conditions(wrapper,wrapper['plan_input'],context=context,analysis=analysis,
        expected_revision=context['revision'] if expected_revision is None else expected_revision,
        expected_context_sha256=before['context_sha256'] if expected_context_sha256 is None else expected_context_sha256,
        rules=rules,rule_sources=rule_sources,inputs=inputs,execution_context=execution_context)
    _bounded(gate)
    if (type(gate) is not dict or set(gate)!=_GATE_KEYS or gate.get('status') not in ('REVIEW_RULE_BRANCH','NOT_SELECTED','HOLD')
            or gate['normative_verdict'] is not None or type(gate.get('verification')) is not dict
            or any(gate['verification'].get(key) is not False for key in
                ('execution_authority','worker_generation_authority','physical_permission'))):_invalid()
    current=IntakeReadModel(workspace).current_conducted_plan_context(intake_id)
    after=_binding(*_parts(current,{'context','analysis'}))
    same=before==after
    questions=[] if same else [dict(key='current_snapshot_changed',field='current_relation',
        reason='current_snapshot_changed',message='현재 접수 문맥·분석이 변경되었습니다. 같은 현재 자료로 조건을 다시 검토해 주세요.')]
    return _bounded(dict(status=gate['status'] if same else 'HOLD',context=context,analysis=analysis,
        facts_plan=wrapper,rule_conditions=gate,current_relation=dict(
            status='same_current_snapshot' if same else 'current_snapshot_changed',
            before=before,after=after,questions=questions)))

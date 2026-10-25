"""Bounded caller-snapshot condition review; no regulatory or execution grant."""
import hashlib
import json
import math
import re

from . import intake_conducted_twin_plan as _plan
from .intake_facts_to_conducted_plan import build_conducted_plan_from_intake_facts
from .store import canonical


__all__ = ['evaluate_intake_rule_conditions']
_NAME = re.compile(r'[A-Za-z][A-Za-z0-9_]{0,79}\Z')
_CONTEXT = (
    'current_validity_approved', 'case_applicability_approved', 'metric_method_approved',
    'reference_plane_verified', 'correction_ledger_verified', 'conditional_limit_resolved',
    'uncertainty_decision_rule_approved', 'independent_holdout_available',
)
_PAYLOAD = {'rule_id', 'declared_predicate', 'input_types', 'units'}
_INPUT_FAILURES = {
    'native_input_invalid', 'analysis_invalid', 'context_invalid', 'analysis_evidence_invalid',
    'expected_revision_changed_or_invalid', 'expected_context_changed_or_invalid',
}


def _problem(gaps, code, field):
    if not any(g['field'] == field for g in gaps):
        gaps.append(dict(code=code, field=field, blocking=True))


def _questions(gaps):
    def message(gap):
        field, code = gap['field'], gap['code']
        if code == 'current_plan_mismatch':
            return '같은 현재 접수 revision·C1·analysis에 대응하는 원래 wrapper와 plan을 제공해 주세요.'
        if code.startswith('rule_source'):
            return field + ': 해시가 일치하는 제공 JSON 원문과 해당 rule index의 AST·타입·단위를 확인해 주세요.'
        if code.startswith('predicate') or code == 'rule_invalid':
            return field + ': 지원되는 명시 조건식(eq/in/gt/gte/all)과 타입·단위를 제공해 주세요.'
        if code == 'execution_context_unconfirmed':
            return field + ': 확인 결과와 같은 현재 접수의 명시 근거를 제공해 주세요.'
        return field + ': 명시 값·타입·단위와 같은 현재 접수의 일치 근거를 제공해 주세요.'
    return [dict(key='condition_' + str(index), field=g['field'], reason=g['code'], message=message(g))
            for index, g in enumerate(gaps)]


def _json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate_json_key')
            result[key] = value
        return result
    def constant(value):
        raise ValueError('non_native_json_number')
    return _plan._snapshot(json.loads(text, object_pairs_hook=pairs, parse_constant=constant))


def _same(left, right):
    # Canonical equality keeps native bool distinct from numeric 0/1.
    return canonical(left) == canonical(right)


def _typed(value, kind):
    if kind == 'boolean':
        return type(value) is bool
    if kind == 'string':
        return type(value) is str and 0 < len(value) <= 200
    if kind == 'number':
        return ((type(value) is int and len(str(value)) <= 128)
                or (type(value) is float and math.isfinite(value)))
    return False


def _current(snapshots, revision, context_sha256):
    wrapper, current, context, analysis = (snapshots[k] for k in ('intake_plan', 'current_plan', 'context', 'analysis'))
    try:
        if (type(wrapper) is not dict or type(current) is not dict or type(context) is not dict
                or type(revision) is not int or revision < 1 or revision != context['revision']
                or type(context_sha256) is not str or not _plan._SHA.fullmatch(context_sha256)
                or context_sha256 != _plan._hash(context)):
            return False
        method = {key: current['plan'][key] for key in _plan._METHOD}
        rebuilt = build_conducted_plan_from_intake_facts(context, analysis, expected_revision=revision,
            expected_context_sha256=context_sha256, method=method)
        parent = rebuilt['plan_input']
        return (_same(rebuilt, wrapper) and _same(parent, current)
                and parent['binding']['context_sha256'] == context_sha256
                and parent['binding']['analysis_sha256'] == _plan._hash(analysis)
                and parent['binding']['plan_sha256'] == _plan._hash(parent['plan'])
                and not any(g['code'] in _INPUT_FAILURES for g in parent['gaps']))
    except (KeyError, TypeError, ValueError, IndexError, OverflowError):
        return False


def _sources(provided, gaps):
    sources = {}
    if type(provided) is not list or not 1 <= len(provided) <= 6:
        _problem(gaps, 'rule_source_invalid', 'rule_sources')
        return sources
    for index, item in enumerate(provided):
        field = 'rule_sources.' + str(index)
        try:
            if (type(item) is not dict or set(item) != {'source_id', 'sha256', 'text'}
                    or type(item['source_id']) is not str or not 0 < len(item['source_id']) <= 200
                    or item['source_id'] in sources or type(item['sha256']) is not str
                    or not _plan._SHA.fullmatch(item['sha256']) or type(item['text']) is not str
                    or len(item['text'].encode('utf-8')) > 1024 * 1024
                    or hashlib.sha256(item['text'].encode('utf-8')).hexdigest() != item['sha256']):
                raise ValueError('source_snapshot')
            document = _json(item['text'])
            if type(document) is not dict or type(document.get('rules')) is not list or not 1 <= len(document['rules']) <= 6:
                raise ValueError('source_rules')
            sources[item['source_id']] = (item['sha256'], document['rules'])
        except (KeyError, TypeError, ValueError, RecursionError, OverflowError):
            _problem(gaps, 'rule_source_invalid', field)
    return sources


def _source_bound(rule, sources):
    ref = rule['source_ref']
    if (type(ref) is not dict or set(ref) != {'source_id', 'sha256', 'rule_index'}
            or type(ref['source_id']) is not str or ref['source_id'] not in sources
            or type(ref['rule_index']) is not int):
        return False
    sha256, entries = sources[ref['source_id']]
    index = ref['rule_index']
    if not 0 <= index < len(entries) or ref['sha256'] != sha256:
        return False
    source_rule = entries[index]
    return (type(source_rule) is dict and _PAYLOAD <= set(source_rule)
            and _same({key: source_rule[key] for key in _PAYLOAD}, {key: rule[key] for key in _PAYLOAD}))


def _predicate_fields(predicate, kinds, units):
    """Validate the whole small AST before reading values; never short circuit gaps."""
    nodes, used = 0, set()
    def visit(node, depth):
        nonlocal nodes
        nodes += 1
        if nodes > 128 or depth > 8 or type(node) is not dict:
            raise ValueError('predicate_limit_or_shape')
        operator = node.get('operator')
        if operator == 'all':
            if (set(node) != {'operator', 'operands'} or type(node['operands']) is not list
                    or not 1 <= len(node['operands']) <= 8):
                raise ValueError('predicate_all')
            for operand in node['operands']:
                visit(operand, depth+1)
            return
        if (type(operator) is not str or operator not in ('eq', 'in', 'gt', 'gte')
                or set(node) != {'operator', 'input', 'value'} or type(node['input']) is not str
                or node['input'] not in kinds):
            raise ValueError('predicate_leaf')
        name, value = node['input'], node['value']
        used.add(name)
        if operator == 'in':
            if type(value) is not list or not 1 <= len(value) <= 16 or not all(_typed(v, kinds[name]) for v in value):
                raise ValueError('predicate_members')
        elif not _typed(value, kinds[name]) or (operator in ('gt', 'gte') and kinds[name] != 'number'):
            raise ValueError('predicate_type')
    if (type(kinds) is not dict or type(units) is not dict or not 1 <= len(kinds) <= 32
            or set(kinds) != set(units) or any(not _NAME.fullmatch(k) for k in kinds)
            or any(type(v) is not str or v not in ('number', 'boolean', 'string') for v in kinds.values())
            or any(type(v) is not str or not 0 < len(v) <= 40 or any(ord(c) < 32 for c in v) for v in units.values())):
        raise ValueError('predicate_declarations')
    visit(predicate, 0)
    if used != set(kinds):
        raise ValueError('predicate_unused_or_missing_declaration')
    return sorted(used)


def _value(entry, name, kind, unit, context, version, gaps, field):
    if entry is None or (type(entry) is dict and entry.get('value') is None):
        _problem(gaps, 'input_missing', field)
        return None
    if type(entry) is not dict or set(entry) != {'value', 'unit', 'status', 'evidence'}:
        _problem(gaps, 'input_invalid', field)
        return None
    if entry['status'] != 'explicit':
        _problem(gaps, 'input_conflicting' if entry['status'] == 'conflict' else 'input_unconfirmed', field)
        return None
    if not _typed(entry['value'], kind) or type(entry['unit']) is not str or entry['unit'] != unit:
        _problem(gaps, 'input_type_or_unit_mismatch', field)
        return None
    refs = entry['evidence']
    try:
        if type(refs) is not list or not 1 <= len(refs) <= 16:
            raise ValueError('evidence_required')
        _plan._citation_check(refs, context, version)
        expected = dict(field=name, value=entry['value'], unit=unit)
        if not all(_same(_json(ref['quote']), expected) for ref in refs):
            raise ValueError('evidence_literal_mismatch')
    except (KeyError, TypeError, ValueError, RecursionError, OverflowError):
        _problem(gaps, 'input_evidence_invalid', field)
        return None
    return entry['value']


def _evaluate(node, values):
    operator = node['operator']
    if operator == 'all':
        return all([_evaluate(child, values) for child in node['operands']])
    actual, expected = values[node['input']], node['value']
    if operator == 'eq':
        return actual == expected
    if operator == 'in':
        return actual in expected
    if operator == 'gt':
        return actual > expected
    return actual >= expected


def evaluate_intake_rule_conditions(intake_plan, current_plan, *, context, analysis,
        expected_revision, expected_context_sha256, rules, rule_sources, inputs, execution_context) -> dict:
    """Review provided source-bound predicates against the same caller current plan.

    Context approval flags are unverified caller snapshots. Even a selected review
    branch confers no normative verdict, worker generation, or physical authority.
    """
    result = dict(schema_version=1, kind='intake_rule_condition_gate', status='HOLD', binding=None,
        rule_results=[], gaps=[], questions=[], snapshots=None, normative_verdict=None,
        verification=dict(current_version='caller_snapshot_only', source_bytes='provided_text_hash_only',
            approval='caller_snapshot_only', regulatory='not_assessed', measurement='not_assessed',
            execution_authority=False, worker_generation_authority=False, physical_permission=False))
    gaps = result['gaps']
    try:
        snapshots, revision, context_sha256 = _plan._snapshot([dict(intake_plan=intake_plan, current_plan=current_plan,
            context=context, analysis=analysis, rules=rules, rule_sources=rule_sources, inputs=inputs,
            execution_context=execution_context), expected_revision, expected_context_sha256])
    except (ValueError, TypeError, RecursionError, OverflowError):
        _problem(gaps, 'native_input_invalid', 'input')
        result['questions'] = _questions(gaps)
        return result
    result['snapshots'] = snapshots
    snapshots.update(expected_revision=revision, expected_context_sha256=context_sha256)
    current_ok = _current(snapshots, revision, context_sha256)
    if current_ok:
        result['binding'] = snapshots['current_plan']['binding'].copy()
    else:
        _problem(gaps, 'current_plan_mismatch', 'current_plan')
    sources = _sources(snapshots['rule_sources'], gaps)
    provided_context = snapshots['execution_context']
    if type(provided_context) is not dict or set(provided_context) - set(_CONTEXT):
        _problem(gaps, 'execution_context_invalid', 'execution_context')
    elif current_ok:
        for name in _CONTEXT:
            field = 'execution_context.' + name
            value = _value(provided_context.get(name), name, 'boolean', 'boolean', snapshots['context'],
                snapshots['analysis']['schema_version'], gaps, field)
            if value is not True:
                _problem(gaps, 'execution_context_unconfirmed', field)
    if type(snapshots['inputs']) is not dict or len(snapshots['inputs']) > 64:
        _problem(gaps, 'input_invalid', 'inputs')
    rules = snapshots['rules']
    if type(rules) is not list or not 1 <= len(rules) <= 6:
        _problem(gaps, 'rule_invalid', 'rules')
        result['questions'] = _questions(gaps)
        return result
    ids = [r.get('rule_id') for r in rules if type(r) is dict and type(r.get('rule_id')) is str]
    for index, rule in enumerate(rules):
        own, value = [], None
        item = dict(rule_id=rule.get('rule_id') if type(rule) is dict else None, status='HOLD',
                    predicate_value=None, source_ref=rule.get('source_ref') if type(rule) is dict else None,
                    gaps=own, questions=[])
        field = 'rules.' + str(index)
        if (type(rule) is not dict or set(rule) != _PAYLOAD | {'source_ref'} or type(rule['rule_id']) is not str
                or not 0 < len(rule['rule_id']) <= 200 or ids.count(rule['rule_id']) != 1):
            _problem(own, 'rule_invalid', field)
        elif not _source_bound(rule, sources):
            _problem(own, 'rule_source_mismatch', field + '.source_ref')
        else:
            try:
                names = _predicate_fields(rule['declared_predicate'], rule['input_types'], rule['units'])
            except (ValueError, TypeError, KeyError, RecursionError):
                _problem(own, 'predicate_invalid', field + '.declared_predicate')
            else:
                if current_ok and type(snapshots['inputs']) is dict:
                    values = {name: _value(snapshots['inputs'].get(name), name, rule['input_types'][name],
                        rule['units'][name], snapshots['context'], snapshots['analysis']['schema_version'],
                        own, 'inputs.' + name) for name in names}
                    if not own:
                        value = _evaluate(rule['declared_predicate'], values)
        item['predicate_value'] = value
        if not gaps and not own and value is not None:
            item['status'] = 'REVIEW_RULE_BRANCH' if value else 'NOT_SELECTED'
        item['questions'] = _questions(own)
        result['rule_results'].append(item)
    all_gaps = gaps.copy()
    for item in result['rule_results']:
        for gap in item['gaps']:
            _problem(all_gaps, gap['code'], gap['field'])
    result['questions'] = _questions(all_gaps)
    if not all_gaps:
        result['status'] = ('REVIEW_RULE_BRANCH' if any(item['status'] == 'REVIEW_RULE_BRANCH'
            for item in result['rule_results']) else 'NOT_SELECTED')
    return result

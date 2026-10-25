"""Pure intake evidence to explicit conducted-synthetic input; no execution grant."""
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
import math
import re

from .intake_analysis import REQUIRED_FIELDS, project_analysis, validate_analysis
from .intake_model_boundary import build_analysis_prompt
from .store import canonical
from .virtual_fleet.rf import _rf_signal as _validate_rf_signal, _text as _rf_text


__all__ = ['build_conducted_twin_plan_input']
_PUBLIC = set('job_id intake_id revision synthetic documents analysis_context_id analysis_contract instructions'.split())
_SETTINGS = ('frequency_hz', 'power_dbm', 'bandwidth_hz', 'duty_cycle', 'modulation', 'crest_factor_db')
_METHOD = ('method_id', 'method_version', 'metric', 'reference_plane')
_UNITS = {
    'frequency_hz': {'Hz': Decimal(1), 'kHz': Decimal(1000), 'MHz': Decimal(1000000), 'GHz': Decimal(1000000000)},
    'bandwidth_hz': {'Hz': Decimal(1), 'kHz': Decimal(1000), 'MHz': Decimal(1000000), 'GHz': Decimal(1000000000)},
    'power_dbm': {'dBm': Decimal(1)}, 'duty_cycle': {'ratio': Decimal(1), '%': Decimal('0.01')},
    'modulation': {'label': None}, 'crest_factor_db': {'dB': Decimal(1)},
}
_SHA = re.compile(r'[0-9a-f]{64}\Z')
_NUMBER = r'(?<![\w.])([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*'


def _hash(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def _snapshot(value):
    ancestors, nodes = set(), 0
    def copy(item, depth=0):
        nonlocal nodes
        nodes += 1
        if nodes > 100000 or depth > 32:
            raise ValueError('input_limit')
        if item is None or type(item) in (str, bool, int):
            return item
        if type(item) is float and math.isfinite(item):
            return item
        if type(item) not in (dict, list) or id(item) in ancestors:
            raise ValueError('native_input_required')
        ancestors.add(id(item))
        try:
            if type(item) is dict:
                if any(type(key) is not str for key in item):
                    raise ValueError('native_keys_required')
                return {key: copy(child, depth+1) for key, child in item.items()}
            return [copy(child, depth+1) for child in item]
        finally:
            ancestors.remove(id(item))
    detached = copy(value)
    if len(canonical(detached).encode('utf-8')) > 8*1024*1024:
        raise ValueError('input_limit')
    return detached


def _result():
    return dict(schema_version=1, kind='intake_conducted_twin_plan_input', status='blocked',
        binding=dict(intake_id=None, revision=None, analysis_context_id=None, context_sha256=None,
                     analysis_sha256=None, plan_sha256=None),
        intake=dict(facts={}, source_facts=[], missing_fields=[], follow_up_missing_fields=[], questions=[]),
        plan=dict(schema_version=1, method_id=None, method_version=None, metric=None, reference_plane=None,
                  source_settings={key: None for key in _SETTINGS}, basis_refs={key: None for key in _SETTINGS},
                  numeric_limit_dbm=None, uncertainty_db=None, assessment='not_assessed'),
        gaps=[], verification=dict(evidence='not_validated', current_version='caller_snapshot_only',
            source_bytes='not_reopened', regulatory='not_assessed', measurement_prediction='not_assessed',
            execution_authority=False))


def _gap(result, code, field, provided=None, *, blocking=True):
    result['gaps'].append(dict(code=code, field=field, provided=provided, blocking=blocking))


def _finish(result):
    result['gaps'].sort(key=lambda g: (g['field'], g['code'], canonical(g['provided'])))
    result['binding']['plan_sha256'] = _hash(result['plan'])
    if not any(g['blocking'] for g in result['gaps']):
        result['status'] = 'ready_for_simulation'
        result['verification']['evidence'] = 'validated_in_memory'
    return json.loads(canonical(result))


def _number(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _source_settings(result, settings):
    if type(settings) is not dict:
        _gap(result, 'invalid_source_settings', 'source_settings')
        return
    for key in sorted(set(settings)-set(_SETTINGS)):
        _gap(result, 'unknown_source_field', 'source_settings.'+key)
    for key in _SETTINGS:
        value = settings.get(key)
        if key not in settings or value is None:
            _gap(result, 'missing_setting', 'source_settings.'+key)
            continue
        valid = False
        if key == 'modulation' and type(value) is str:
            try:
                _rf_text(value)
                valid = True
            except ValueError:
                pass
        if key != 'modulation' and _number(value):
            valid = (value > 0 if key in ('frequency_hz', 'bandwidth_hz') else
                     0 < value <= 1 if key == 'duty_cycle' else value >= 0 if key == 'crest_factor_db' else True)
        if not valid:
            _gap(result, 'unsupported_modulation' if key == 'modulation' else 'invalid_setting',
                 'source_settings.'+key, value)
        else:
            result['plan']['source_settings'][key] = value
    validated = result['plan']['source_settings']
    if all(value is not None for value in validated.values()):
        try:
            # The RF frame flags are internal numeric-validation inputs, never
            # caller approval or a returned execution grant. CW defaults stay off.
            _validate_rf_signal(dict(validated, valid=True, status='ok', source_id='conducted-plan-input'))
        except MemoryError:
            raise
        except Exception:
            _gap(result, 'invalid_rf_domain', 'source_settings', validated.copy())
            validated['frequency_hz'] = validated['bandwidth_hz'] = None


def _method(result, method):
    if type(method) is not dict:
        _gap(result, 'invalid_method', 'method')
        return
    for key in sorted(set(method)-set(_METHOD)):
        _gap(result, 'unknown_method_field', 'method.'+key)
    for key in _METHOD:
        value = method.get(key)
        valid = (type(value) is int and value == 1 if key == 'method_version' else
                 type(value) is str and value in ('on', 'time', 'peak') if key == 'metric' else
                 type(value) is str and value == 'source_output' if key == 'reference_plane' else
                 type(value) is str and value == 'conducted_synthetic')
        if not valid:
            _gap(result, 'unsupported_method_field' if key in method else 'missing_method_field', 'method.'+key, value)
        else:
            result['plan'][key] = value


def _citation_check(refs, context, version):
    # Reuse the genuine citation validator; this temporary validation fact is
    # never added to intake intent/projection or returned as a discovered fact.
    check = dict(schema_version=version, producer=dict(kind='manual', name='synthetic-plan-citation-check'),
                 identity='unknown', missing_fields=[], facts=[dict(field='features', value='source setting citation',
                     status='explicit', evidence=refs)])
    if version == 2:
        check['context_id'] = context['analysis_context_id']
    validate_analysis(check, context['documents'], context['synthetic'], context_id=context['analysis_context_id'])


def _quoted_value(basis, key):
    if key == 'modulation':
        pattern = r'(?<!\w)'+re.escape(basis['value'])+r'(?!\w)'
        return any(re.search(pattern, ref['quote']) for ref in basis['evidence'])
    quantity = r'(?<!\w)on(?:_|[- ]+)average(?:_|[- ]+)power\s*[:=]?\s*' if key == 'power_dbm' else ''
    pattern = quantity+_NUMBER+re.escape(basis['unit'])+r'(?!\w)'
    expected = Decimal(str(basis['value']))
    return any(Decimal(match.group(1)) == expected for ref in basis['evidence']
               for match in re.finditer(pattern, ref['quote'], re.I if key == 'power_dbm' else 0))


def _basis(result, basis, context, version):
    provided_settings = result['plan']['source_settings'].copy()
    result['plan']['source_settings'] = {key: None for key in _SETTINGS}
    if type(basis) is not dict:
        _gap(result, 'invalid_basis', 'basis', provided_settings)
        return
    for key in sorted(set(basis)-set(_SETTINGS)):
        _gap(result, 'unknown_basis_field', 'basis.'+key)
    for key in _SETTINGS:
        provided = provided_settings[key]
        item = basis.get(key)
        if type(item) is not dict or set(item) != {'kind', 'value', 'unit', 'evidence'}:
            _gap(result, 'missing_or_invalid_basis', 'basis.'+key, provided)
            continue
        kind, value, unit, refs = (item[k] for k in ('kind', 'value', 'unit', 'evidence'))
        if (type(kind) is not str or kind not in ('source_cited', 'developer_declared_synthetic')
                or type(unit) is not str or unit not in _UNITS[key] or type(refs) is not list
                or (kind == 'source_cited' and not refs) or (kind == 'developer_declared_synthetic' and refs)):
            _gap(result, 'unsupported_or_invalid_basis', 'basis.'+key, provided)
            continue
        if provided is None:
            continue  # Basis never supplies a missing setting.
        if key == 'modulation':
            same = type(value) is str and value == provided
        else:
            same = _number(value) and Fraction(str(value))*Fraction(str(_UNITS[key][unit])) == Fraction(str(provided))
        if not same:
            _gap(result, 'basis_value_mismatch', 'basis.'+key, provided)
            continue
        if kind == 'source_cited':
            try:
                _citation_check(refs, context, version)
                if not _quoted_value(item, key):
                    _gap(result, 'basis_quote_value_mismatch', 'basis.'+key, provided)
                    continue
            except MemoryError:
                raise
            except Exception:
                _gap(result, 'basis_evidence_invalid', 'basis.'+key, provided)
                continue
        result['plan']['source_settings'][key] = provided
        result['plan']['basis_refs'][key] = item


def _intake(result, analysis, unread):
    projection = project_analysis(analysis, unread, {}, delegated=False, deferred=False)
    result['intake'].update(facts=projection['facts'], questions=projection['questions'],
        source_facts=analysis['facts'], missing_fields=analysis['missing_fields'],
        follow_up_missing_fields=[f for f in analysis['missing_fields'] if f not in REQUIRED_FIELDS])
    seen = set()
    for question in projection['questions']:
        field = question.get('field')
        seen.add(field)
        if question['key'].startswith('conflict_'):
            _gap(result, 'conflicting_intake_fact', 'intake.'+field, question['values'])
        elif field:
            _gap(result, 'missing_intake_field' if field in REQUIRED_FIELDS else 'follow_up_missing_field',
                 'intake.'+field, blocking=field in REQUIRED_FIELDS)
        else:
            _gap(result, question['key'], 'intake.identity' if question['key']=='product_identity' else 'intake.documents')
    for field in analysis['missing_fields']:
        if field not in seen:
            _gap(result, 'missing_intake_field' if field in REQUIRED_FIELDS else 'follow_up_missing_field',
                 'intake.'+field, blocking=field in REQUIRED_FIELDS)
    for fact in analysis['facts']:
        if fact['status'] == 'uncertain':
            _gap(result, 'uncertain_intake_fact', 'intake.'+fact['field'], blocking=fact['field'] in REQUIRED_FIELDS)
    for field in ('market', 'purpose'):
        if field not in projection['facts']:
            continue
        value = projection['facts'][field]['value']
        candidates = [f for f in analysis['facts'] if f['field']==field and f['value'].strip()==value
                      and f['status']=='explicit' and all(e['role']=='request' for e in f['evidence'])]
        def quoted(fact):
            if field == 'market' and re.fullmatch('[A-Za-z]{2,3}', value):
                return all(re.search(r'(?<![A-Za-z])'+re.escape(value)+r'(?![A-Za-z])', e['quote'], re.I)
                           for e in fact['evidence'])
            return all(value.casefold() in e['quote'].casefold() for e in fact['evidence'])
        if not any(quoted(fact) for fact in candidates):
            _gap(result, 'intent_value_not_in_request_quote', 'intake.'+field)


def build_conducted_twin_plan_input(context, analysis, *, expected_revision,
        expected_context_sha256, source_settings, basis, method) -> dict:
    """Validate caller snapshots and explicit settings; return synthetic readiness only.

    Matching caller version pins never observes Store current state or authenticates
    original source bytes. No Store/model/hardware execution or approval occurs.
    """
    result = _result()
    try:
        context, analysis, settings, basis, method, revision, expected_hash = _snapshot(
            [context, analysis, source_settings, basis, method, expected_revision, expected_context_sha256])
    except MemoryError:
        raise
    except Exception:
        _gap(result, 'native_input_invalid', 'input')
        return _finish(result)
    if (type(analysis) is not dict or type(analysis.get('producer')) is not dict
            or type(analysis['producer'].get('name')) is not str):
        _gap(result, 'analysis_invalid', 'analysis')
        return _finish(result)
    try:
        if type(context) is not dict or set(context) != _PUBLIC:
            raise ValueError('context_shape')
        prompt = build_analysis_prompt(context, producer_name=analysis['producer']['name'])
        context = json.loads(prompt['messages'][1]['content'])
    except MemoryError:
        raise
    except Exception:
        _gap(result, 'context_invalid', 'context')
        return _finish(result)
    result['binding'].update(intake_id=context['intake_id'], revision=context['revision'],
        analysis_context_id=context['analysis_context_id'], context_sha256=_hash(context), analysis_sha256=_hash(analysis))
    if type(revision) is not int or revision < 1 or revision != context['revision']:
        _gap(result, 'expected_revision_changed_or_invalid', 'binding.revision')
    if type(expected_hash) is not str or not _SHA.fullmatch(expected_hash) or expected_hash != _hash(context):
        _gap(result, 'expected_context_changed_or_invalid', 'binding.context_sha256')
    try:
        unread = validate_analysis(analysis, context['documents'], context['synthetic'], context_id=context['analysis_context_id'])
        if analysis['schema_version'] != context['analysis_contract']['schema_version']:
            raise ValueError('analysis_context_schema')
    except MemoryError:
        raise
    except Exception:
        _gap(result, 'analysis_evidence_invalid', 'analysis')
        return _finish(result)
    _intake(result, analysis, unread)
    _source_settings(result, settings)
    _method(result, method)
    _basis(result, basis, context, analysis['schema_version'])
    return _finish(result)

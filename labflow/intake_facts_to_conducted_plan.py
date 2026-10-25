"""Closed cited RF statements to the existing pure conducted plan contract."""
from decimal import Decimal, DecimalException
from fractions import Fraction
import json
import re

from . import intake_conducted_twin_plan as _plan
from .intake_analysis import validate_analysis
from .intake_model_boundary import build_analysis_prompt
from .store import canonical


__all__=['build_conducted_plan_from_intake_facts']
_FIELDS=_plan._SETTINGS
_LABELS=dict(frequency='frequency_hz',on_average_power='power_dbm',bandwidth='bandwidth_hz',
             duty_cycle='duty_cycle',modulation='modulation',crest_factor='crest_factor_db')
_KNOWN_OTHER_POWER={'report_peak','reported_peak','peak_power','time_average_power'}
_OTHER_POWER={'power','power_dbm'}|_KNOWN_OTHER_POWER
_QUANTITY=re.compile(_plan._NUMBER+r'([A-Za-z%]+)\Z')
_TOKEN=re.compile(r'[\w.+-]+\Z',re.UNICODE)
_INPUT_CODES={'native_input_invalid','analysis_invalid','context_invalid','analysis_evidence_invalid',
              'expected_revision_changed_or_invalid','expected_context_changed_or_invalid'}
_MESSAGES=dict(frequency_hz='같은 조건의 명시 주파수와 단위를 확인해 주세요.',
    power_dbm='같은 조건의 명시 on-average source 출력과 단위를 확인해 주세요.',
    bandwidth_hz='같은 조건의 명시 대역폭과 단위를 확인해 주세요.',
    duty_cycle='같은 조건의 명시 duty 값과 단위를 확인해 주세요.',
    modulation='같은 조건의 명시 변조 label을 확인해 주세요.',
    crest_factor_db='같은 조건의 명시 crest factor와 단위를 확인해 주세요.')


class _Unsupported(ValueError):
    pass


def _reject(code):
    raise _Unsupported(code)


def _native_fraction(value):
    if value.denominator==1:
        result=value.numerator
    else:
        result=float(value)
        if not _plan._number(result) or Fraction(str(result))!=value:
            _reject('source_number_unrepresentable')
    if not _plan._number(result):_reject('source_number_unrepresentable')
    return result


def _quantity(rhs,key):
    if key=='modulation':
        if len(rhs)>=2 and rhs[0]==rhs[-1]=='"' and '\\' not in rhs[1:-1] and '"' not in rhs[1:-1]:
            label=rhs[1:-1]
        elif _TOKEN.fullmatch(rhs):label=rhs
        else:_reject('source_statement_unsupported')
        try:_plan._rf_text(label)
        except ValueError:_reject('source_statement_unsupported')
        return label,label,'label',label
    if len(rhs)>256:_reject('source_number_unrepresentable')
    match=_QUANTITY.fullmatch(rhs)
    if not match:_reject('source_statement_unsupported')
    token,unit=match.groups()
    if len(token)>128:_reject('source_number_unrepresentable')
    exponent=token.lower().partition('e')[2]
    if exponent and abs(int(exponent))>400:_reject('source_number_unrepresentable')
    if unit not in _plan._UNITS[key]:_reject('source_unit_unsupported')
    try:
        number=Decimal(token)
        if not number.is_finite():_reject('source_number_unrepresentable')
        original=_native_fraction(Fraction(number))
        scaled=Fraction(number)*Fraction(str(_plan._UNITS[key][unit]))
        setting=_native_fraction(scaled)
    except (DecimalException,OverflowError,ValueError) as error:
        if type(error) is _Unsupported:raise
        _reject('source_number_unrepresentable')
    return original,setting,unit,token


def _block(text):
    if text.count(';')+text.count('\n')>=128:return {},False,True
    records={};unknown=False
    for segment in re.finditer(r'[^;\n]+',text):
        statement=segment.group().strip()
        if not statement:continue
        colon,equal=statement.find(':'),statement.find('=')
        positions=[p for p in (colon,equal) if p>=0]
        if not positions:unknown=True;continue
        at=min(positions);raw_label=statement[:at].strip()
        if len(raw_label)>64:unknown=True;continue
        label='_'.join(raw_label.casefold().replace('-',' ').replace('_',' ').split())
        key=_LABELS.get(label)
        other=label in _OTHER_POWER
        if other:key='power_dbm'
        if key is None:unknown=True;continue
        rhs=statement[at+1:].strip()
        row=dict(span=[segment.start(),segment.end()],label=label,raw_value=None,unit=None,problem=None,
                 value=None,setting=None,normal=None)
        if other:
            row['problem']='source_power_quantity_unsupported'
            if len(rhs)<=256:
                match=_QUANTITY.fullmatch(rhs)
                if match:
                    token,unit=match.groups()
                    row.update(raw_value=token if len(token)<=128 else None,unit=unit if len(unit)<=16 else None)
        else:
            try:
                value,setting,unit,raw=_quantity(rhs,key)
                row.update(value=value,setting=setting,unit=unit,raw_value=raw,
                    normal=setting if key=='modulation' else Fraction(str(setting)))
            except _Unsupported as error:
                row['problem']=str(error)
                if len(rhs)<=256:
                    match=_QUANTITY.fullmatch(rhs)
                    if match:
                        token,unit=match.groups()
                        row.update(raw_value=token if len(token)<=128 else None,unit=unit if len(unit)<=16 else None)
        records.setdefault(key,[]).append(row)
    return records,unknown,False


def _metadata(index,evidence,vr,qr,value,quote):
    source=qr or vr or {}
    return dict(fact_index=index,evidence_index=evidence,raw_value=source.get('raw_value'),unit=source.get('unit'),
        value_span=vr['span'] if vr else [0,len(value)],quote_span=qr['span'] if qr else [0,len(quote)])


def _gap(code,field,provided=None):
    return dict(code=code,field=field,provided=provided,blocking=True)


def _collect(analysis):
    nodes={key:[] for key in _FIELDS};problems={key:[] for key in _FIELDS};groups={}
    cache={};count=0;unrecognized=[]
    def parse(text):
        if text not in cache:cache[text]=_block(text)
        return cache[text]
    for i,fact in enumerate(analysis['facts']):
        if fact['field'] not in ('features','power_target'):continue
        values,unknown_value,limit=parse(fact['value'])
        if limit:return nodes,problems,groups,[_gap('source_candidate_limit','source_settings')],unrecognized
        wanted=set(values)
        if fact['field']=='power_target':wanted={'power_dbm'}
        seen=set()
        for j,ref in enumerate(fact['evidence']):
            quotes,unknown_quote,limit=parse(ref['quote'])
            if limit:return nodes,problems,groups,[_gap('source_candidate_limit','source_settings',[
                _metadata(i,j,None,None,fact['value'],ref['quote'])])],unrecognized
            keys=(wanted & set(quotes)) if wanted else set(quotes)
            if fact['field']=='power_target':keys &= {'power_dbm'}
            if not wanted and not keys:
                unrecognized.append(_metadata(i,j,None,None,fact['value'],ref['quote']));count+=1
                if count>4096:return nodes,problems,groups,[_gap('source_candidate_limit','source_settings')],unrecognized
            identity={key:value for key,value in ref.items() if key!='role'}
            group=_plan._hash(identity)
            for key in _FIELDS:
                if key not in keys:continue
                vs=values.get(key,[]);qs=quotes.get(key,[])
                if key=='power_dbm' and any(r['label']=='on_average_power' for r in vs):
                    # A separately labeled report quantity never replaces or
                    # changes the explicitly cited source on-average input.
                    vs=[r for r in vs if r['label'] not in _KNOWN_OTHER_POWER]
                    qs=[r for r in qs if r['label'] not in _KNOWN_OTHER_POWER]
                    if not qs:continue
                seen.add(key)
                metadata=[_metadata(i,j,vs[0] if vs else None,q,fact['value'],ref['quote']) for q in qs]
                metadata.extend(_metadata(i,j,v,None,fact['value'],ref['quote']) for v in vs[1:])
                count+=len(metadata)
                if count>4096:return nodes,problems,groups,[_gap('source_candidate_limit','source_settings')],unrecognized
                code=None
                if fact['status']!='explicit':code='source_fact_unverified'
                elif unknown_value or unknown_quote:code='source_statement_unsupported'
                elif not vs or not qs:code='source_quote_mismatch'
                elif any(r['problem'] for r in vs+qs):code=next(r['problem'] for r in vs+qs if r['problem'])
                else:
                    nv={r['normal'] for r in vs};nq={r['normal'] for r in qs}
                    if len(nv)>1 or len(nq)>1:code='source_value_conflict'
                    elif nv!=nq:code='source_quote_mismatch'
                if code:
                    problems[key].append((code,metadata));continue
                quote=qs[0]
                node=dict(normal=quote['normal'],setting=quote['setting'],metadata=metadata,
                    basis=dict(kind='source_cited',value=quote['value'],unit=quote['unit'],evidence=[ref]),group=group)
                nodes[key].append(node);groups.setdefault(group,{}).setdefault(key,node)
        for key in wanted-seen:
            metadata=[_metadata(i,j,values[key][0] if values.get(key) else None,None,fact['value'],ref['quote'])
                      for j,ref in enumerate(fact['evidence'])]
            count+=len(metadata)
            if count>4096:return nodes,problems,groups,[_gap('source_candidate_limit','source_settings')],unrecognized
            code='source_fact_unverified' if fact['status']!='explicit' else 'source_quote_mismatch'
            problems[key].append((code,metadata))
    return nodes,problems,groups,[],unrecognized


def _assemble(analysis):
    settings={key:None for key in _FIELDS};basis=settings.copy()
    nodes,problems,groups,gaps,unrecognized=_collect(analysis)
    if gaps:return settings,basis,gaps
    resolved=set()
    for key in _FIELDS:
        candidates=nodes[key];issues=problems[key]
        distinct={n['normal'] for n in candidates}
        provided=[m for n in candidates for m in n['metadata']]+[m for _,items in issues for m in items]
        if len(distinct)>1:gaps.append(_gap('source_value_conflict','source_settings.'+key,provided))
        elif issues:gaps.append(_gap(issues[0][0],'source_settings.'+key,provided))
        elif not candidates:gaps.append(_gap('source_fact_missing','source_settings.'+key,unrecognized or None))
        else:resolved.add(key)
    coherent=next((group for group in groups.values() if resolved<=set(group)),None) if resolved else {}
    if coherent is None:
        provided=[m for key in _FIELDS for n in nodes[key] for m in n['metadata']]
        return settings,basis,[_gap('source_condition_unbound','source_settings',provided)]+gaps
    for key in resolved:
        settings[key]=coherent[key]['setting'];basis[key]=coherent[key]['basis']
    return settings,basis,gaps


def _questions(parent,gaps):
    if any(g['code'] in _INPUT_CODES for g in parent['gaps']):return []
    global_gap=next((g for g in gaps if g['field']=='source_settings'),None)
    if global_gap:
        return [dict(key='source_condition',field='source_settings',reason=global_gap['code'],
            message='같은 시험 조건에 결합된 명시 RF 값과 인용 블록을 확인해 주세요.')]
    if any(g['code']=='invalid_rf_domain' for g in parent['gaps']):
        return [dict(key='source_domain',field='source_settings',reason='invalid_rf_domain',
            message='같은 조건의 주파수와 대역폭 범위를 확인해 주세요.')]
    questions=[]
    for key in _FIELDS:
        if parent['plan']['source_settings'][key] is not None:continue
        field='source_settings.'+key
        issue=next((g for g in gaps if g['field']==field),None) or next((g for g in parent['gaps'] if g['field']==field),None)
        questions.append(dict(key='source_'+key,field=field,reason=issue['code'] if issue else 'source_fact_missing',message=_MESSAGES[key]))
    return questions


def _wrapped(parent,gaps,questions):
    return json.loads(canonical(dict(schema_version=1,kind='intake_facts_to_conducted_plan',status=parent['status'],
        plan_input=parent,assembly_gaps=gaps,questions=questions)))


def build_conducted_plan_from_intake_facts(context,analysis,*,expected_revision,expected_context_sha256,method)->dict:
    """Only literal same-condition facts supply settings; parent remains authority."""
    empty={key:None for key in _FIELDS}
    original=(context,analysis,expected_revision,expected_context_sha256,method)
    def parent(c,a,r,h,m,settings,basis):
        return _plan.build_conducted_twin_plan_input(c,a,expected_revision=r,expected_context_sha256=h,
            method=m,source_settings=settings,basis=basis)
    try:
        context,analysis,revision,pin,method=_plan._snapshot(list(original))
    except MemoryError:raise
    except Exception:
        return _wrapped(parent(*original,empty,empty),[],[])
    usable=False
    try:
        if type(context) is not dict or set(context)!=_plan._PUBLIC:raise ValueError()
        prompt=build_analysis_prompt(context,producer_name=analysis['producer']['name'])
        normalized=json.loads(prompt['messages'][1]['content'])
        validate_analysis(analysis,normalized['documents'],normalized['synthetic'],context_id=normalized['analysis_context_id'])
        usable=(analysis['schema_version']==normalized['analysis_contract']['schema_version'] and
            type(revision) is int and revision>=1 and revision==normalized['revision'] and
            type(pin) is str and pin==_plan._hash(normalized) and type(method) is dict and
            set(method)==set(_plan._METHOD) and method['method_id']=='conducted_synthetic' and
            type(method['method_version']) is int and method['method_version']==1 and
            method['metric'] in ('on','time','peak') and method['reference_plane']=='source_output')
    except MemoryError:raise
    except Exception:pass
    if not usable:return _wrapped(parent(context,analysis,revision,pin,method,empty,empty),[],[])
    settings,basis,gaps=_assemble(analysis)
    result=parent(context,analysis,revision,pin,method,settings,basis)
    return _wrapped(result,gaps,_questions(result,gaps))

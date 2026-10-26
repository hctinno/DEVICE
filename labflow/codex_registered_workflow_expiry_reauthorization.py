"""Read one fixed root native source that removes only the calendar deadline."""
from datetime import datetime
import re

from . import codex_conducted_workflow_registration as _registration
from . import codex_registered_conducted_workflow_host as _host

__all__=['calendar_deadline']
_LEAF='root-expiry-reauthorization-v1.json'
_DIRECT=dict(kind='direct_human_instructions_to_this_root_thread',
    reply_id='e123f778ee58431abbcd9c5d3b11952b',
    instruction_literal='2시간유효기간이 왜필요해? 우리 목적을 위해서 전부다 진행해',
    action='continue_same_case_remaining_budget_without_calendar_expiry',
    calendar_expiry_removed_by_direct_user_instruction=True,
    authority_is_not_inferred_from_uploaded_documents_or_model_output=True)
_INTERPRETATION='root_interpretation_of_direct_user_instruction_calendar_only'


def _timestamp(value):
    if type(value) is not str or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ',value,re.ASCII):
        _host._fail('original_expiry_invalid')
    try:datetime.strptime(value,'%Y-%m-%dT%H:%M:%SZ')
    except ValueError:_host._fail('original_expiry_invalid')


def calendar_deadline(io,operator,source_raw,publication_raw,manual_raw,manual,events,current_sha):
    """Return finite original deadline or (None, pinned root calendar source)."""
    original_expiry=events['permit']['expires_at']
    _timestamp(original_expiry)
    if manual['expires_at'] is not None:
        _host._native_host._expiry(original_expiry)
        _host._native_host._expiry(manual['expires_at'])
        return original_expiry,None

    try:raw=io.read(operator/_LEAF,65536)
    except FileNotFoundError:
        # Preserve the original expired-permit refusal when no new native
        # source exists. A still-valid permit cannot make a null manual expiry.
        _host._native_host._expiry(original_expiry)
        _host._fail('calendar_source_required')
    value=_host._json(raw)
    _host._keys(value,'schema_version kind authority_source direct_user_expiry_reference interpretation '
        'original_operator_source original_publication manual_record original case scope '
        'current_schema_sha256 original_expires_at remaining_model_processes '
        'calendar_expiry_removed_by_direct_user_instruction')
    if (type(value['schema_version']) is not int or value['schema_version']!=1
            or value['kind']!='codex_root_same_case_calendar_reauthorization'
            or value['interpretation']!=_INTERPRETATION
            or value['calendar_expiry_removed_by_direct_user_instruction'] is not True
            or type(value['remaining_model_processes']) is not int
            or value['remaining_model_processes']!=7):_host._fail('calendar_authority_invalid')
    _host._same(value['authority_source'],_host._json(source_raw)['authority_source'])
    _host._same(value['direct_user_expiry_reference'],_DIRECT)
    _host._same(value['original_operator_source'],_host._pin(source_raw))
    _host._same(value['original_publication'],_host._pin(publication_raw))
    _host._same(value['manual_record'],_host._pin(manual_raw))
    _host._same(value['original'],manual['original'])
    _host._same(value['case'],manual['case'])
    _host._same(value['scope'],_registration._LIMITS)
    _host._same(value['current_schema_sha256'],current_sha)
    _host._same(value['original_expires_at'],original_expiry)
    return None,_host._pin(raw)

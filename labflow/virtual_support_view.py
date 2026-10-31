"""Project pinned public metadata, without creating or operating a virtual lab."""
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from .control_source_catalog import ControlSourceCatalog, SOURCE_COMMIT
from .n1914a_virtual_adapter import describe_virtual_n1914a_contract
from .virtual_fleet.catalog import ROLES, validate_catalog
from .virtual_fleet.integration import get_role_actions


CATALOG_PATH = 'virtual_profiles/sm_a176u_unlicensed.json'
CATALOG_SHA256 = '0d2de78fafb496b746105aa852b25d4854fcf04fa32520cea858a315e5147967'
MAX_RESPONSE_BYTES = 524288
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,149}\Z')
_SHA = re.compile(r'[a-f0-9]{64}\Z')
_CANDIDATES = ('normalized_label_candidates', 'same_model_other_manufacturer_candidates')
_ACCESS = {'search_index_only', 'content_read', 'download_read', 'blocked', 'redirected'}
_MATCH = {'exact_model', 'documented_family', 'generic_vendor', 'family_candidate', 'discovery_only'}
_SCOPE = {'included', 'excluded_passive', 'identity_unresolved', 'needs_scope_review'}
_RESEARCH = {'exact_source', 'family_source', 'vendor_only', 'searched_no_public_control_source',
             'excluded_passive', 'identity_unresolved', 'needs_scope_review'}


def _need(condition):
    if not condition:
        raise ValueError('virtual_support_unavailable')


def _native(value):
    """Copy bounded native JSON values; subclasses and custom accessors are refused."""
    nodes = 0
    def copy(item, depth=0):
        nonlocal nodes
        nodes += 1
        _need(nodes <= 50000 and depth <= 20)
        kind = type(item)
        if kind is dict:
            _need(len(item) <= 1024 and all(type(key) is str for key in item))
            return {copy(key, depth + 1): copy(child, depth + 1) for key, child in item.items()}
        if kind is list:
            _need(len(item) <= 4096)
            return [copy(child, depth + 1) for child in item]
        if kind is str:
            _need(len(item) <= 4096)
            item.encode('utf-8', 'strict')
        else:
            _need(item is None or kind in (bool, int, float))
        return item
    result = copy(value)
    # Also refuse NaN/Infinity, including values inside metadata not projected.
    json.dumps(result, allow_nan=False, ensure_ascii=False)
    return result


def _safe_url(value):
    _need(type(value) is str and 1 <= len(value) <= 2048
          and not re.search(r'[\x00-\x20\x7f\\]', value))
    url = urlsplit(value)
    _need(url.scheme in ('http', 'https') and bool(url.hostname)
          and url.username is None and url.password is None)
    url.port  # Validate malformed/out-of-range ports without resolving a host.
    return value


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _need(key not in result)
        result[key] = value
    return result


def _catalog(root):
    with (root / CATALOG_PATH).open('rb') as stream:
        raw = stream.read(4 * 1024 * 1024 + 1)
    _need(len(raw) <= 4 * 1024 * 1024 and hashlib.sha256(raw).hexdigest() == CATALOG_SHA256)
    return validate_catalog(json.loads(raw.decode('utf-8', 'strict'), object_pairs_hook=_pairs))


def _material(profile, crosswalk, controls, detail_cache):
    _need(crosswalk['manufacturer_as_recorded'] == profile['manufacturer']
          and crosswalk['model_as_recorded'] == profile['model'] and crosswalk['role'] == profile['role']
          and crosswalk['installed_equipment_binding_established'] is False
          and crosswalk['simulation_profile_retained'] is True
          and crosswalk['profile_evidence_refs'] == profile['evidence_refs'])
    status = crosswalk['text_comparison_status']
    _need(status in (*_CANDIDATES, 'no_text_candidate'))
    candidates, seen = [], set()
    for kind in _CANDIDATES:
        values = crosswalk[kind]
        _need(type(values) is list and len(values) <= 100)
        for candidate in values:
            item = candidate['item_id']
            _need(type(item) is str and _ID.fullmatch(item) and item not in seen)
            seen.add(item)
            if item not in detail_cache:
                detail_cache[item] = _native(controls.detail(item))
            record = detail_cache[item]['record']['research_record']
            _need(record['item_id'] == item and all(record[key] == candidate[key]
                  for key in ('manufacturer', 'model', 'scope', 'research_status')))
            _need(record['scope'] in _SCOPE and record['research_status'] in _RESEARCH
                  and type(record['sources']) is list and len(record['sources']) <= 100)
            sources = []
            for source in record['sources']:
                selected = _native({key: source[key] for key in ('url', 'access', 'match_level')})
                _safe_url(selected['url'])
                _need(selected['access'] in _ACCESS and selected['match_level'] in _MATCH)
                sources.append(selected)
            _need([s['url'] for s in sources] == candidate['source_urls'])
            candidates.append(_native({key: record[key] for key in
                              ('item_id', 'manufacturer', 'model', 'scope', 'research_status')}) | {'sources': sources})
    expected = _CANDIDATES[0] if crosswalk[_CANDIDATES[0]] else _CANDIDATES[1] if crosswalk[_CANDIDATES[1]] else 'no_text_candidate'
    _need(status == expected)
    return {'candidate_status': status, 'installed_equipment_binding_established': False, 'candidates': candidates}


def _contract():
    descriptor = _native(describe_virtual_n1914a_contract())
    keys = ('schema_version model profile_id synthetic hardware_verified vendor_binary_executed units '
            'window synthetic_input sensor_compatibility calibration firmware options real_support commands source').split()
    result = {key: descriptor[key] for key in keys}
    _need(type(result['schema_version']) is int and result['schema_version'] == 1
          and result['model'] == 'N1914A' and result['profile_id'] == 'n1914a-a-ascii-v1'
          and result['synthetic'] is True and result['hardware_verified'] is False
          and result['vendor_binary_executed'] is False and result['units'] == ['DBM', 'W']
          and type(result['window']) is int and result['window'] == 1 and result['synthetic_input'] == 'A'
          and all(result[key] == 'not_assessed' for key in ('sensor_compatibility', 'calibration', 'firmware', 'options', 'real_support')))
    commands = result['commands']
    _need(type(commands) is list and len(commands) == 12 and len(set(commands)) == 12
          and all(type(c) is str and 1 <= len(c) <= 128 and c.isascii() and not re.search(r'[\x00-\x1f;]', c) for c in commands))
    source = result['source']
    _need(type(source) is dict and set(source) == {'document', 'edition', 'date', 'sha256'}
          and source['document'] == 'N1913-90008.pdf' and type(source['edition']) is int
          and source['edition'] == 19 and source['date'] == '2025-06-11'
          and type(source['sha256']) is str and _SHA.fullmatch(source['sha256']))
    return result


def build_virtual_support_view(control_sources=None, *, repo_root=None):
    """Build detached declarations. No test receipts, asset identity or live state."""
    try:
        root = Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[1]
        controls = ControlSourceCatalog(root) if control_sources is None else control_sources
        _need(type(controls) is ControlSourceCatalog)
        catalog = _catalog(root)
        crosswalk = _native(controls.profiles())
        _need(type(crosswalk) is list and len(crosswalk) == 64)
        by_id = {row['profile_id']: row for row in crosswalk}
        _need(len(by_id) == 64 and set(by_id) == {p['profile_id'] for p in catalog['profiles']})
        actions = _native(get_role_actions())
        _need(type(actions) is dict and set(actions) <= ROLES)
        details, rows = {}, []
        for profile in catalog['profiles']:
            declared = actions.get(profile['role'], {})
            _need(type(declared) is dict and len(declared) <= 64
                  and all(_ID.fullmatch(key) and type(value) is dict for key, value in declared.items()))
            row = {key: profile[key] for key in ('profile_id', 'profile_kind', 'manufacturer', 'model', 'role', 'variant', 'evidence_refs')}
            row.update(materials=_material(profile, by_id[profile['profile_id']], controls, details),
                       virtual_role={'status': 'declared' if declared else 'not_assessed', 'scope': 'virtual_case_actions',
                                     'action_names': sorted(declared), 'protocol_scope': False},
                       protocol={'status': 'not_assessed', 'reason': 'no_registered_pure_contract_for_this_profile'},
                       virtual_verification='not_assessed', hardware_verified=False, execution_authority=False)
            rows.append(row)
        result = _native({'schema_version': 1, 'kind': 'virtual_support_view',
                  'provenance': {'material_source_commit': SOURCE_COMMIT, 'catalog_path': CATALOG_PATH,
                                 'catalog_sha256': CATALOG_SHA256,
                                 'role_declaration': 'labflow.virtual_fleet.integration.get_role_actions',
                                 'protocol_declaration': 'labflow.n1914a_virtual_adapter.describe_virtual_n1914a_contract'},
                  'snapshot_scope': 'first_success_host_snapshot', 'profile_count': len(rows), 'profiles': rows,
                  'adapter_contracts': [_contract()], 'virtual_verification': 'not_assessed',
                  'hardware_verified': False, 'execution_authority': False})
        _need(len(json.dumps(result, ensure_ascii=False, allow_nan=False).encode('utf-8')) <= MAX_RESPONSE_BYTES)
        return result
    except Exception:
        raise ValueError('virtual_support_unavailable') from None

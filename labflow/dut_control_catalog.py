"""Pinned DUT source metadata and routes; no dispatcher or collected-code execution."""
import copy
import hashlib
import json
import math
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import stat
from urllib.parse import urlsplit


_INPUTS = (
    ('control_sources/dut_sources.json',
     'e561182cf35b72ed47c45de28bf921b53b3eb7d662a226f686535c346c6b9858', 256 * 1024),
    ('control_sources/dut_paths.json',
     '3eb9d1d7623ddaa1f99ca1d3d50c749f184e7bb6a09767fc87800a9288dfe77b', 32 * 1024),
)
_SOURCE_ID = re.compile(r'DUT-[AGS][0-9]{2}\Z')
_BACKEND = re.compile(r'[a-z][a-z0-9_]{0,79}\Z')
_COUNTS = {'source_units': 30, 'github_projects': 25, 'aosp_components': 4,
           'pinned_submodules': 1, 'archive_files': 32, 'archive_bytes': 74333207,
           'snapshot_files_verified': 10538, 'stable_source_distributions': 2}
_ROUTES = {
    'adb': (False, ['DUT-A01', 'DUT-G08', 'DUT-G09']),
    'android_ui_and_test': ('usually_no_for_standard_bootstrap',
        ['DUT-G01', 'DUT-G02', 'DUT-G03', 'DUT-G04', 'DUT-G05', 'DUT-G06',
         'DUT-G07', 'DUT-G10', 'DUT-G11', 'DUT-G12', 'DUT-A03']),
    'oem_sdk_cli': ('unknown_per_tool', []),
    'windows_vendor_gui': (True, ['DUT-G13', 'DUT-G14']),
    'serial_at_or_documented_protocol': (True, ['DUT-G15']),
    'usb_hid_documented_protocol': (True, ['DUT-G16', 'DUT-G17', 'DUT-G18', 'DUT-G22', 'DUT-S01']),
    'chipset_rf_reference': ('depends_on_host_driver_and_firmware', ['DUT-G19', 'DUT-G20', 'DUT-G21', 'DUT-A02']),
    'firmware_service_reference': (True, ['DUT-G25', 'DUT-A04']),
    'future_ios': (True, ['DUT-G23', 'DUT-G24']),
}
_SOURCE_IDS = {value for _, values in _ROUTES.values() for value in values}
_COMMON = {'support_status': 'not_assessed', 'hardware_verified': False,
           'source_code_executed': False, 'automatic_fallback_enabled': False}


class DutControlCatalogError(ValueError):
    """Only a fixed public code; never attach an input-read exception."""
    def __init__(self, code):
        self.code = code
        super().__init__(code)
        self.__suppress_context__ = True


def _require(condition):
    if not condition:
        raise ValueError('invalid_dut_catalog_data')


def _fixed(value, expected):
    return type(value) is type(expected) and value == expected


def _text(value):
    return type(value) is str and bool(value)


def _strings(value):
    return type(value) is list and all(type(item) is str for item in value)


def _positive(value):
    return type(value) is int and value > 0


def _hex(value, length):
    return type(value) is str and re.fullmatch('[0-9a-f]{' + str(length) + '}', value) is not None


def _member(value):
    return (_text(value) and '\\' not in value and '\x00' not in value
            and not PurePosixPath(value).is_absolute() and not PureWindowsPath(value).drive
            and all(part not in ('', '.', '..') for part in value.split('/')))


def _url(value):
    if not _text(value) or any(c in value for c in '\r\n\x00'):
        return False
    parsed = urlsplit(value)
    return parsed.scheme in ('https', 'http') and bool(parsed.hostname) and parsed.username is None and parsed.password is None


def _unique(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result)
        result[key] = value
    return result


def _json_tree(value, depth=0):
    _require(depth <= 32)
    if type(value) is dict:
        _require(all(type(key) is str for key in value))
        for item in value.values():
            _json_tree(item, depth + 1)
    elif type(value) is list:
        for item in value:
            _json_tree(item, depth + 1)
    else:
        _require(value is None or type(value) in (str, int, bool)
                 or type(value) is float and math.isfinite(value))


def _read(root, relative, pin, cap):
    path = (root / relative).resolve(strict=True)
    _require(path.is_relative_to(root))
    info = path.stat()
    _require(stat.S_ISREG(info.st_mode) and info.st_size <= cap)
    with path.open('rb') as stream:
        raw = stream.read(cap + 1)
    _require(len(raw) <= cap and hashlib.sha256(raw).hexdigest() == pin)
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite_json')))
    _json_tree(value)
    json.dumps(value, ensure_ascii=False, allow_nan=False).encode('utf-8')
    return value


def _source_records(rows):
    _require(type(rows) is list and len(rows) == 30)
    required = {'id', 'category', 'commit', 'status', 'archive_bytes', 'archive_sha256',
                'snapshot_scope', 'license_evidence_files', 'license_review_status',
                'device_or_firmware_supported', 'adapter_integrated', 'vendor_code_executed', 'hardware_verified'}
    optional = {'base_url', 'repository', 'repository_url', 'git_ref', 'snapshot_file_count',
                'source_file_count', 'symlink_entries_retained_in_archive_only', 'license_review',
                'installed_product_support', 'application_boundary', 'subtree', 'parent_source_id', 'parent_path'}
    result = {}
    for row in rows:
        _require(type(row) is dict and required <= set(row) <= required | optional)
        source_id = row['id']
        _require(type(source_id) is str and source_id in _SOURCE_IDS and source_id not in result)
        _require(all(_text(row[key]) for key in ('category', 'snapshot_scope', 'license_review_status'))
                 and _hex(row['commit'], 40) and _hex(row['archive_sha256'], 64)
                 and _positive(row['archive_bytes']) and row['device_or_firmware_supported'] == 'not_assessed')
        _require(all(row[key] is False for key in ('adapter_integrated', 'vendor_code_executed', 'hardware_verified')))
        if source_id == 'DUT-G13':
            _require(row['status'] == 'source_files_and_release_acquired'
                     and _fixed(row.get('source_file_count'), 258) and 'snapshot_file_count' not in row)
        else:
            _require(row['status'] == 'acquired' and _positive(row.get('snapshot_file_count'))
                     and 'source_file_count' not in row)
        for key in ('base_url', 'repository_url'):
            if key in row:
                _require(_url(row[key]))
        for key in ('license_review', 'application_boundary'):
            if key in row:
                _require(_text(row[key]))
        if 'repository' in row:
            _require(_member(row['repository'])
                     and re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', row['repository']) is not None)
        if 'git_ref' in row:
            _require(_member(row['git_ref']) and row['git_ref'].startswith('refs/'))
        for key in ('subtree', 'parent_path'):
            if key in row:
                _require(_member(row[key]))
        if 'installed_product_support' in row:
            _require(row['installed_product_support'] == 'not_assessed')
        if 'symlink_entries_retained_in_archive_only' in row:
            _require(_strings(row['symlink_entries_retained_in_archive_only'])
                     and all(_member(p) for p in row['symlink_entries_retained_in_archive_only']))
        licenses = row['license_evidence_files']
        _require(type(licenses) is list)  # An empty list does not grant reuse rights.
        for item in licenses:
            _require(type(item) is dict and set(item) == {'path', 'sha256', 'bytes'}
                     and _member(item['path']) and _hex(item['sha256'], 64)
                     and type(item['bytes']) is int and item['bytes'] >= 0
                     and (item['bytes'] != 0 or item['sha256'] == hashlib.sha256(b'').hexdigest()))
        result[source_id] = row
    _require(set(result) == _SOURCE_IDS
             and result['DUT-S01'].get('parent_source_id') == 'DUT-G18'
             and result['DUT-S01'].get('parent_path') == 'hidapi'
             and result['DUT-S01']['category'] == 'pinned_submodule'
             and result['DUT-S01']['commit'] != result['DUT-G17']['commit'])
    _require(all('parent_source_id' not in row for key, row in result.items() if key != 'DUT-S01'))
    _require(sum(row.get('snapshot_file_count', row.get('source_file_count', 0)) for row in rows) == 10538)
    return result


def _releases(rows, sources):
    _require(type(rows) is list and len(rows) == 2)
    seen = set()
    for row in rows:
        fields = {'source_id', 'release_version', 'metadata_url', 'archive_bytes', 'archive_sha256'}
        _require(type(row) is dict and fields <= set(row) <= fields | {'requires_python'})
        key = row['source_id']
        _require(type(key) is str and key in {'DUT-G01', 'DUT-G13'} and key not in seen and key in sources
                 and row['release_version'] == {'DUT-G01': '1.13.1', 'DUT-G13': '0.6.9'}[key]
                 and _url(row['metadata_url']) and _positive(row['archive_bytes']) and _hex(row['archive_sha256'], 64))
        _require(row.get('requires_python') == '>=3.11' if key == 'DUT-G01' else 'requires_python' not in row)
        seen.add(key)


def _text_map(value):
    return type(value) is dict and all(_text(k) and _text(v) for k, v in value.items())


def _dependencies(rows, sources):
    _require(type(rows) is list and len(rows) == 3)
    seen = set()
    for row in rows:
        _require(type(row) is dict and set(row) == {'source_id', 'member_path', 'sha256', 'declarations',
                                                  'installed_dependency_lock_verified'})
        key = row['source_id']
        _require(type(key) is str and key in {'DUT-G01', 'DUT-G05', 'DUT-G06'} and key not in seen
                 and key in sources and _member(row['member_path']) and _hex(row['sha256'], 64)
                 and row['installed_dependency_lock_verified'] is False)
        seen.add(key)
        declared = row['declarations']
        allowed = {'name', 'version', 'requires-python', 'dependencies', 'optional-dependencies',
                   'build_requires', 'engines', 'optionalDependencies', 'peerDependencies'}
        _require(type(declared) is dict and {'name', 'version'} <= set(declared) <= allowed
                 and _text(declared['name']) and _text(declared['version']))
        for name, value in declared.items():
            if name in ('name', 'version', 'requires-python'):
                _require(_text(value))
            elif name in ('engines', 'optionalDependencies', 'peerDependencies'):
                _require(_text_map(value))
            elif name == 'dependencies':
                _require(_strings(value) or _text_map(value))
            elif name == 'build_requires':
                _require(_strings(value))
            else:
                _require(type(value) is dict and all(_text(k) and _strings(v) for k, v in value.items()))


def _manufacturing(value, sources):
    fields = {'additional_reviewed_references', 'additional_reviewed_reference_count',
              'newly_acquired_repository_archives', 'new_links_in_equipment_url_index',
              'anyway_official_public_sdk_or_complete_protocol', 'sm_a176u_chipset_or_transport_support',
              'samsung_legacy_muic_resistance_ohm_to_code', 'etsi_reference_version', 'clac', 'cfun',
              'unverified_user_supplied_claims', 'already_acquired_member_checks'}
    _require(type(value) is dict and set(value) == fields
             and _fixed(value['additional_reviewed_reference_count'], 9)
             and _fixed(value['newly_acquired_repository_archives'], 0)
             and value['new_links_in_equipment_url_index'] is False
             and value['anyway_official_public_sdk_or_complete_protocol'] == 'not_verified'
             and value['sm_a176u_chipset_or_transport_support'] == 'not_established_by_this_review')
    for key in ('etsi_reference_version', 'clac', 'cfun'):
        _require(_text(value[key]))
    _require(_strings(value['unverified_user_supplied_claims']))
    _require(value['samsung_legacy_muic_resistance_ohm_to_code'] == {
        '255000': 'ADC_JIG_USB_OFF', '301000': 'ADC_JIG_USB_ON',
        '523000': 'ADC_JIG_UART_OFF', '619000': 'ADC_JIG_UART_ON'})
    references = value['additional_reviewed_references']
    _require(type(references) is list and len(references) == 9)
    seen = set()
    for row in references:
        _require(type(row) is dict and set(row) == {
            'reference_id', 'url', 'review_scope', 'file_path_if_known', 'file_blob_oid_if_verified',
            'repository_commit_pinned', 'whole_repository_archive_acquired', 'new_local_source_copy_saved',
            'target_device_support', 'reuse_license_review'})
        key = row['reference_id']
        _require(type(key) is str and _BACKEND.fullmatch(key) is not None and key not in seen
                 and _url(row['url']) and _text(row['review_scope'])
                 and row['whole_repository_archive_acquired'] is False
                 and row['new_local_source_copy_saved'] is False
                 and row['target_device_support'] == 'not_verified'
                 and row['reuse_license_review'] == 'required_per_file_before_reuse')
        _require(row['file_path_if_known'] is None or _member(row['file_path_if_known']))
        _require(row['file_blob_oid_if_verified'] is None or _hex(row['file_blob_oid_if_verified'], 40))
        _require(row['repository_commit_pinned'] is None or _hex(row['repository_commit_pinned'], 40))
        seen.add(key)
    members = value['already_acquired_member_checks']
    _require(type(members) is list and len(members) == 2)
    seen = set()
    for row in members:
        _require(type(row) is dict and set(row) == {
            'source_id', 'commit', 'member_path', 'member_sha256', 'member_git_blob_oid',
            'acquisition_scope', 'manufacturing_test_code_present', 'product_support'})
        key = row['source_id']
        _require(type(key) is str and key in {'DUT-G19', 'DUT-G21'} and key not in seen
                 and row['commit'] == sources[key]['commit'] and _member(row['member_path'])
                 and _hex(row['member_sha256'], 64) and _hex(row['member_git_blob_oid'], 40)
                 and row['acquisition_scope'] == 'already_acquired_archive_member_independently_verified'
                 and row['manufacturing_test_code_present'] is True and row['product_support'] == 'not_assessed')
        seen.add(key)


def _validate(data, paths):
    _require(type(data) is dict and set(data) == {
        'schema_version', 'kind', 'provenance', 'counts', 'sources', 'stable_releases',
        'dependency_declarations', 'reference_environment', 'manufacturing_references',
        'support_status', 'hardware_verified', 'source_code_executed', 'automatic_fallback_enabled',
        'remaining_public_source_gaps'})
    _require(_fixed(data['schema_version'], 1) and data['kind'] == 'dut_control_source_metadata'
             and all(_fixed(data[k], v) for k, v in _COMMON.items()))
    _require(type(data['counts']) is dict and set(data['counts']) == set(_COUNTS)
             and all(_fixed(data['counts'][k], v) for k, v in _COUNTS.items()))
    provenance = data['provenance']
    _require(type(provenance) is dict and set(provenance) == {
        'source_catalog_sha256', 'control_paths_sha256', 'main_prompt_v5_sha256', 'manufacturer_addendum_sha256'}
        and all(_hex(v, 64) for v in provenance.values()) and _strings(data['remaining_public_source_gaps']))
    sources = _source_records(data['sources'])
    _releases(data['stable_releases'], sources)
    _dependencies(data['dependency_declarations'], sources)
    _require(sum(row['archive_bytes'] for row in data['sources'] + data['stable_releases']) == 74333207)
    environment = {'python_version': '3.12.4', 'node_version': '24.16.0',
        'comparison_scope': 'declared_interpreter_constraints_only_not_install_or_product_support',
        'mobly_master_python_constraint_satisfied': False, 'mobly_1_13_1_python_constraint_satisfied': True,
        'appium_and_uiautomator2_node_constraint_satisfied': True,
        'npm_android_sdk_jdk_device_requirements_checked': False}
    _require(type(data['reference_environment']) is dict and set(data['reference_environment']) == set(environment)
             and all(_fixed(data['reference_environment'][k], v) for k, v in environment.items()))
    _manufacturing(data['manufacturing_references'], sources)
    _require(type(paths) is dict and set(paths) == {
        'schema_version', 'source_catalog', 'kind', 'unconditional_fallback_enabled',
        'bench_validation_performed', 'selection_rule', 'paths'})
    _require(_fixed(paths['schema_version'], 1) and paths['source_catalog'] == 'dut_sources.json'
             and paths['kind'] == 'proposed_DUT_backend_capability_catalog_not_running_dispatcher'
             and paths['unconditional_fallback_enabled'] is False and paths['bench_validation_performed'] is False
             and _text(paths['selection_rule']) and type(paths['paths']) is list and len(paths['paths']) == 9)
    by_backend = {}
    for row in paths['paths']:
        base = {'backend', 'sources', 'independent_of_adb', 'use', 'conditions'}
        _require(type(row) is dict and base <= set(row) <= base | {'acquisition_status'})
        key = row['backend']
        _require(type(key) is str and key in _ROUTES and key not in by_backend)
        independence, ids = _ROUTES[key]
        _require(_fixed(row['independent_of_adb'], independence) and _strings(row['sources'])
                 and row['sources'] == ids and all(i in sources for i in ids)
                 and _text(row['use']) and _strings(row['conditions']) and bool(row['conditions']))
        _require(row.get('acquisition_status') == 'public_anyway_interface_not_verified'
                 if key == 'oem_sdk_cli' else 'acquisition_status' not in row)
        by_backend[key] = row
    _require(set(by_backend) == set(_ROUTES))
    return sources, by_backend


class DutControlCatalog:
    """Successful local snapshot with detached metadata-only queries."""
    def __init__(self, repo_root=None):
        failed = False
        try:
            root = Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[1]
            data, paths = [_read(root, *entry) for entry in _INPUTS]
            sources, backends = _validate(data, paths)
        except Exception:
            failed = True
        # Outside the handler: no private filesystem/parser exception context.
        if failed:
            raise DutControlCatalogError('dut_catalog_unavailable')
        self._data, self._paths = data, paths
        self._sources, self._backends = sources, backends

    @staticmethod
    def _wrapper(kind):
        return {'schema_version': 1, 'kind': kind, 'catalog_state': 'read_only_metadata_catalog', **_COMMON}

    def summary(self):
        return copy.deepcopy({
            **self._wrapper('dut_control_summary'), 'counts': self._data['counts'],
            'route_count': len(self._backends), 'provenance': self._data['provenance'],
            'reference_environment': self._data['reference_environment'],
            'remaining_public_source_gaps': self._data['remaining_public_source_gaps'],
        })

    def routes(self):
        return copy.deepcopy(self._paths['paths'])

    def route(self, backend):
        if type(backend) is not str or _BACKEND.fullmatch(backend) is None:
            raise DutControlCatalogError('dut_catalog_invalid_query')
        if backend not in self._backends:
            raise DutControlCatalogError('dut_catalog_item_not_found')
        route = self._backends[backend]
        return copy.deepcopy({
            **self._wrapper('dut_control_route'), 'route': route,
            'sources': [self._sources[key] for key in route['sources']],
            'stable_releases': [row for row in self._data['stable_releases'] if row['source_id'] in route['sources']],
        })

    def source(self, source_id):
        if type(source_id) is not str or _SOURCE_ID.fullmatch(source_id) is None:
            raise DutControlCatalogError('dut_catalog_invalid_query')
        if source_id not in self._sources:
            raise DutControlCatalogError('dut_catalog_item_not_found')
        return copy.deepcopy({
            **self._wrapper('dut_control_source'), 'record': self._sources[source_id],
            'stable_releases': [r for r in self._data['stable_releases'] if r['source_id'] == source_id],
            'dependency_declarations': [r for r in self._data['dependency_declarations'] if r['source_id'] == source_id],
            'manufacturing_member_checks': [r for r in self._data['manufacturing_references']['already_acquired_member_checks']
                                            if r['source_id'] == source_id],
            'backends': [r['backend'] for r in self._paths['paths'] if source_id in r['sources']],
        })

    def manufacturing_references(self):
        return copy.deepcopy(self._data['manufacturing_references'])

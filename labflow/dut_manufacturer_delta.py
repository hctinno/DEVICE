"""Read-only composition of original DUT references and later selected-file metadata."""
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import stat

from labflow.dut_control_catalog import DutControlCatalog


_DELTA_INPUT = (
    'control_sources/dut_manufacturer_delta.json',
    'bf70269ae9f021830811c67be3b3c8daf929e61c07170dbec3ab4db25a311cdf', 64 * 1024,
)
_PARENT_PINS = {
    'dut_sources.json': 'e561182cf35b72ed47c45de28bf921b53b3eb7d662a226f686535c346c6b9858',
    'dut_paths.json': '3eb9d1d7623ddaa1f99ca1d3d50c749f184e7bb6a09767fc87800a9288dfe77b',
}
_PROMPT = 'b1cb4f3ddaf32dd11227a039eadee889835594210796e7a544948acd327148df'
_PUBLIC_COMMIT = 'ade1b91395c17f382e02cb1ae70f37daa04154c7'
_PUBLIC_PATH = 'materials/inventory/FCC-PUBLIC-DUT-CONTROL-20261024-001-review.json'
_PUBLIC_SHA = '5ee6223b65febdc4273cd94aaf43b46154e20acf0b19c2db0d3bdab5d2491b20'
_ETSI_URL = 'https://www.etsi.org/deliver/etsi_ts/127000_127099/127007/18.08.00_60/ts_127007v180800p.pdf'
_ID = re.compile(r'[a-z][a-z0-9_]{0,95}\Z')
_REPOSITORIES = {
    'qualcomm_diag': (
        'DUT-CONTROL-QCSUPER-001', 'P1sec/QCSuper', '65e14771804cec8fe70ffb55552da9d85721f0eb',
        ('README.md', 'pyproject.toml', 'src/qcsuper/inputs/_base_input.py',
         'src/qcsuper/inputs/usb_modem_pyusb.py', 'src/qcsuper/inputs/adb.py',
         'src/qcsuper/inputs/dlf_read.py', 'LICENSE'), 'community_project_primary_source'),
    'samsung_at_legacy': (
        'DUT-CONTROL-GALAXY-AT-001', 'apeppels/galaxy-at-tool', 'a4247497cca7da96b9aaa7f533cff23e13ad6437',
        ('README.md', 'galaxy_at_tool.py'), 'community_project_primary_source'),
    'android_at_research': (
        'DUT-CONTROL-FICS-AT-001', 'FICS/atcmd', '766a6b918289f5c2f4c3e1b82a65b964e4a0c8f5',
        ('README.md', 'extract/README.md', 'send/at_cmds.py', 'interact/atinteract.py',
         'send/atsend.py', 'usbswitch/usbswitcher.c'), 'community_research_project_primary_source'),
    'qualcomm_ath10k_testmode': (
        'DUT-CONTROL-ATH10K-001', 'torvalds/linux', '17bb0e2f6c8043f70a693a5f3797471cbed354c8',
        ('drivers/net/wireless/ath/ath10k/testmode.c', 'drivers/net/wireless/ath/ath10k/testmode.h',
         'drivers/net/wireless/ath/ath10k/testmode_i.h', 'LICENSES/deprecated/ISC'),
        'upstream_OS_project_primary_source'),
    'samsung_legacy_muic': (
        'DUT-CONTROL-LEGACY-MUIC-001', 'LineageOS/android_kernel_samsung_universal8890',
        '33ca16cbaf4bd144df3beef64283302c0aa35eed',
        ('include/linux/muic/muic.h', 'COPYING'), 'community_OS_project_primary_source'),
}
_ACQUIRED_IDS = set(_REPOSITORIES) | {'etsi_at_reference'}
_SNAPSHOT_IDS = _ACQUIRED_IDS | {'usb_type_c_reference', 'samsung_diagnostic_reference', 'qualcomm_sdk_distribution'}
_STATE = {'support_status': 'not_assessed', 'hardware_verified': False, 'source_code_executed': False,
          'automatic_fallback_enabled': False, 'source_reuse_publication_approved': False}
_COUNTS = {'source_groups': 6, 'source_file_references': 22,
           'new_whole_repository_archives': 0, 'public_original_or_code_payload_files': 0}


class DutManufacturerDeltaError(ValueError):
    """Fixed public code without private input error cause/context."""
    def __init__(self, code):
        self.code = code
        super().__init__(code)
        self.__suppress_context__ = True


def _require(condition):
    if not condition:
        raise ValueError('invalid_dut_delta_data')


def _fixed(value, expected):
    return type(value) is type(expected) and value == expected


def _text(value):
    return type(value) is str and bool(value)


def _strings(value):
    return type(value) is list and all(_text(v) for v in value)


def _unique(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result)
        result[key] = value
    return result


def _tree(value, depth=0):
    _require(depth <= 32)
    if type(value) is dict:
        _require(all(type(key) is str for key in value))
        for item in value.values():
            _tree(item, depth + 1)
    elif type(value) is list:
        for item in value:
            _tree(item, depth + 1)
    else:
        _require(value is None or type(value) in (str, bool, int)
                 or type(value) is float and math.isfinite(value))


def _read(root):
    relative, pin, cap = _DELTA_INPUT
    path = (root / relative).resolve(strict=True)
    _require(path.is_relative_to(root))
    info = path.stat()
    _require(stat.S_ISREG(info.st_mode) and info.st_size <= cap)
    with path.open('rb') as stream:
        raw = stream.read(cap + 1)
    _require(len(raw) <= cap and hashlib.sha256(raw).hexdigest() == pin)
    data = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite_json')))
    _tree(data)
    json.dumps(data, ensure_ascii=False, allow_nan=False).encode('utf-8')
    return data


def _files(rows, ref, urls):
    expected = (_ETSI_URL,) if ref == 'etsi_at_reference' else _REPOSITORIES[ref][3]
    _require(type(rows) is list and len(rows) == len(expected))
    members = set()
    for file in rows:
        base = {'primary_source_url', 'sha256', 'bytes', 'public_payload_included'}
        _require(type(file) is dict and base <= set(file))
        primary = file['primary_source_url']
        _require(type(primary) is str and primary not in urls)
        if ref == 'etsi_at_reference':
            _require(primary == _ETSI_URL)
            member, download = _ETSI_URL, _ETSI_URL
        else:
            _, repository, commit, _, _ = _REPOSITORIES[ref]
            prefixes = (f'https://github.com/{repository}/blob/{commit}/',
                        f'https://raw.githubusercontent.com/{repository}/{commit}/')
            matches = [prefix for prefix in prefixes if primary.startswith(prefix)]
            _require(len(matches) == 1)
            member = primary[len(matches[0]):]
            download = f'https://raw.githubusercontent.com/{repository}/{commit}/{member}'
        _require(member in expected and member not in members)
        special = ref == 'qualcomm_diag' and member == 'LICENSE'
        if special:
            _require(set(file) == base | {'scope', 'new_distinct_payload_original'}
                     and _text(file['scope']) and file['new_distinct_payload_original'] is False
                     and file['sha256'] == '8ceb4b9ee5adedde47b31e975c1d90c73ad27b6b165a1dcd80c7c545eb65b903'
                     and _fixed(file['bytes'], 35147))
        else:
            _require(set(file) == base | {'download_url'} and file['download_url'] == download)
        _require(type(file['sha256']) is str and re.fullmatch(r'[0-9a-f]{64}', file['sha256']) is not None
                 and type(file['bytes']) is int and file['bytes'] > 0 and file['public_payload_included'] is False)
        members.add(member); urls.add(primary)
    _require(members == set(expected))


def _record(record, reference_id, urls):
    common = {'source_id', 'authority', 'license_basis', 'scope', 'limits', 'files',
              'source_reuse_publication_approved', 'device_or_Firmware_support', 'runtime_or_physical_validation'}
    _require(type(record) is dict)
    if reference_id == 'etsi_at_reference':
        _require(set(record) == common | {'title', 'physical_pages', 'printed_pages'}
                 and record['source_id'] == 'DUT-CONTROL-ETSI-REFERENCE-001'
                 and record['authority'] == 'official_standard_publisher'
                 and record['title'] == 'ETSI TS127007V18.8.0(2025-01)')
        for key, values in (('physical_pages', [119, 120, 152]), ('printed_pages', [118, 119, 151])):
            _require(type(record[key]) is list and all(type(v) is int for v in record[key]) and record[key] == values)
    else:
        source_id, repository, commit, _, authority = _REPOSITORIES[reference_id]
        fields = common | {'repository', 'repository_commit', 'commit_url'}
        if reference_id == 'qualcomm_diag':
            fields |= {'declared_package_version', 'requires_python'}
            _require(record.get('declared_package_version') == '2.1.4' and record.get('requires_python') == '>=3.7')
        _require(set(record) == fields and record['source_id'] == source_id
                 and record['repository'] == repository and record['repository_commit'] == commit
                 and record['commit_url'] == f'https://github.com/{repository}/commit/{commit}'
                 and record['authority'] == authority)
    _require(_text(record['license_basis']) and _text(record['scope']) and _strings(record['limits'])
             and bool(record['limits']) and record['source_reuse_publication_approved'] is False
             and record['device_or_Firmware_support'] == 'not_assessed'
             and record['runtime_or_physical_validation'] is False)
    _files(record['files'], reference_id, urls)


def _validate(data, parent_summary, parent_references):
    _require(type(parent_summary) is dict
             and parent_summary['provenance']['main_prompt_v5_sha256'] == _PROMPT)
    refs = parent_references['additional_reviewed_references']
    _require(type(refs) is list and len(refs) == 9)
    snapshot = {}
    for record in refs:
        _require(type(record) is dict and type(record.get('reference_id')) is str)
        key = record['reference_id']
        _require(key in _SNAPSHOT_IDS and key not in snapshot)
        snapshot[key] = record
    _require(set(snapshot) == _SNAPSHOT_IDS)
    _require(type(data) is dict and set(data) == {
        'schema_version', 'kind', 'provenance', 'counts', 'records', *_STATE})
    _require(_fixed(data['schema_version'], 1) and data['kind'] == 'dut_manufacturer_acquisition_delta'
             and all(_fixed(data[k], v) for k, v in _STATE.items()))
    _require(type(data['counts']) is dict and set(data['counts']) == set(_COUNTS)
             and all(_fixed(data['counts'][k], v) for k, v in _COUNTS.items()))
    provenance = {
        'public_collection_commit': _PUBLIC_COMMIT, 'public_collection_path': _PUBLIC_PATH,
        'public_collection_sha256': _PUBLIC_SHA, 'source_request_id': 'DEV-DUT-MANUFACTURER-010',
        'main_prompt_sha256': _PROMPT, 'parent_catalog_sha256': _PARENT_PINS,
        'relationship': 'later_acquisition_metadata_without_rewriting_the_parent_snapshot',
    }
    _require(type(data['provenance']) is dict and data['provenance'] == provenance)
    _require(type(data['records']) is list and len(data['records']) == 6)
    by_reference, source_ids, urls = {}, set(), set()
    for wrapper in data['records']:
        _require(type(wrapper) is dict and set(wrapper) == {
            'reference_id', 'acquisition_scope', 'selected_file_hashes_independently_verified',
            'whole_repository_archive_acquired', 'record'})
        key = wrapper['reference_id']
        _require(type(key) is str and key in _ACQUIRED_IDS and key not in by_reference
                 and wrapper['acquisition_scope'] == 'selected_private_source_files_or_reference_document'
                 and wrapper['selected_file_hashes_independently_verified'] is True
                 and wrapper['whole_repository_archive_acquired'] is False)
        _record(wrapper['record'], key, urls)
        source_id = wrapper['record']['source_id']
        _require(source_id not in source_ids)
        source_ids.add(source_id); by_reference[key] = wrapper
    _require(set(by_reference) == _ACQUIRED_IDS and len(urls) == 22)
    return snapshot, by_reference


class DutManufacturerDeltaCatalog:
    """Successful snapshots only; original and later evidence remain distinct."""
    def __init__(self, repo_root=None):
        failed = False
        try:
            root = Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[1]
            parent = DutControlCatalog(root)
            parent_summary, references = parent.summary(), parent.manufacturing_references()
            data = _read(root)
            snapshot, by_reference = _validate(data, parent_summary, references)
        except Exception:
            failed = True
        if failed:
            raise DutManufacturerDeltaError('dut_delta_unavailable')
        self._data, self._snapshot, self._by_reference = data, snapshot, by_reference

    @staticmethod
    def _base(kind):
        return {'schema_version': 1, 'kind': kind, 'catalog_state': 'read_only_acquisition_delta',
                **{k: _STATE[k] for k in ('support_status', 'hardware_verified',
                                        'source_code_executed', 'automatic_fallback_enabled')}}

    def summary(self):
        return copy.deepcopy({**self._base('dut_manufacturer_delta_summary'),
            'counts': self._data['counts'], 'provenance': self._data['provenance'],
            'source_reuse_publication_approved': False})

    def records(self):
        return copy.deepcopy(self._data['records'])

    def reference(self, reference_id):
        if type(reference_id) is not str or _ID.fullmatch(reference_id) is None:
            raise DutManufacturerDeltaError('dut_delta_invalid_query')
        if reference_id not in self._snapshot:
            raise DutManufacturerDeltaError('dut_delta_item_not_found')
        return copy.deepcopy({**self._base('dut_manufacturer_reference'), 'reference_id': reference_id,
            'snapshot_reference': self._snapshot[reference_id],
            'acquisition_delta': self._by_reference.get(reference_id)})

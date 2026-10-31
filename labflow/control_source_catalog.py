"""Pinned, detached research metadata; never assesses or operates equipment."""
import copy
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re


SOURCE_COMMIT = '8dec2d783b99609b27fb37f82752f17146206f4d'
MAX_FILE_BYTES = 32 * 1024 * 1024
_RESEARCH_SHA = 'fe895ac47431d9f4f8b407f6e007492b0f4b0e395ad48c9a7eb10b1dcd8418ea'
_INPUTS = (
    ('research', 'research/equipment-control-2026-10-24/deliverables/model_control_sources.json', (_RESEARCH_SHA,)),
    ('overlay', 'control_sources/registry_overlay.json', ('6c0baae239563993c9ac1b194ff94ca25e2130e917d034a6065b01f3440eb33f',)),
    ('urls', 'control_sources/source_url_index.json', ('0f8130d42878a4be170e32fd2d7a6139f75431cde0fb977e7373dfb8c60f612a',)),
    ('prior', 'control_sources/prior_vendor_references.json', ('e58d8ad9994ddb7dc8c5fe2de3ac1254bb4d9a0b16f1a34247ac2b510f92d2ae',)),
    ('reviews', 'control_sources/review_notes.json', ('8ddb3268f38d54cb1cec6674b4e807946190eb36076f64a4e4b7c9479115ba52',)),
)
_ID = re.compile(r'[A-Za-z0-9_.-]{1,150}\Z')
_SHA = re.compile(r'[a-f0-9]{64}\Z')
_SCOPES = {'included': 1433, 'excluded_passive': 1480, 'identity_unresolved': 176, 'needs_scope_review': 48}
_CANDIDATES = ('normalized_label_candidates', 'same_model_other_manufacturer_candidates')
_PROFILE_COUNTS = {'normalized_label_candidates': 37, 'same_model_other_manufacturer_candidates': 9, 'no_text_candidate': 18}
_SOURCE_FIELDS = {'url', 'kind', 'authority', 'match_level', 'access', 'license', 'evidence'}


class ControlSourceCatalogError(ValueError):
    """Public code only; untrusted payloads and filesystem errors are suppressed."""
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _require(condition):
    if not condition:
        raise ValueError('invalid_catalog_data')


def _id(value):
    return type(value) is str and _ID.fullmatch(value) is not None


def _strings(value):
    return type(value) is list and all(type(item) is str for item in value)


def _count(value, expected):
    return type(value) is int and value == expected


def _sha(value):
    return type(value) is str and _SHA.fullmatch(value) is not None


def _unique(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result)
        result[key] = value
    return result


def _read(root, relative, pins):
    path = root / relative
    _require(path.resolve().is_relative_to(root) and path.stat().st_size <= MAX_FILE_BYTES)
    with path.open('rb') as stream:
        raw = stream.read(MAX_FILE_BYTES + 1)
    _require(len(raw) <= MAX_FILE_BYTES and hashlib.sha256(raw).hexdigest() in pins)
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite_json')))
    # Also reject overflowed JSON numbers and escaped lone UTF-16 surrogates.
    json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')
    return value


def _normalized(value):
    return ''.join(character for character in value.casefold() if character.isalnum())


def _research(records):
    _require(type(records) is list and len(records) == 3137)
    by_id, equipment, models, associations = {}, {}, set(), {}
    required = {'item_id','model_id','manufacturer','model','names','equipment_ids','register_numbers',
                'registration_rows','scope','research_status','public_code_status','sources','notes','hardware_verified'}
    statuses = {'family_source','exact_source','vendor_only','searched_no_public_control_source',
                'excluded_passive','identity_unresolved','needs_scope_review'}
    for record in records:
        _require(type(record) is dict and required <= set(record))
        item_id, model_id = record['item_id'], record['model_id']
        _require(_id(item_id) and item_id not in by_id and (model_id is None or _id(model_id)))
        if model_id is not None:
            _require(model_id == item_id and model_id not in models)
            models.add(model_id)
        _require(all(type(record[key]) is str for key in ('manufacturer','model','scope','research_status','public_code_status','notes'))
                 and _strings(record['names']) and record['scope'] in _SCOPES and record['research_status'] in statuses
                 and record['hardware_verified'] is False)
        for key in ('hardware_tested', 'registered_unit_interface_verified'):
            if key in record:
                _require(record[key] is False)
        ids, numbers = record['equipment_ids'], record['register_numbers']
        _require(type(ids) is list and type(numbers) is list and len(ids) == len(numbers)
                 and type(record['registration_rows']) is int and record['registration_rows'] == len(ids) and len(ids) > 0)
        for equipment_id, number in zip(ids, numbers):
            _require(_id(equipment_id) and equipment_id not in equipment and type(number) is int and number > 0
                     and equipment_id == f'EQ-{number:06d}')
            equipment[equipment_id] = item_id
        _require(type(record['sources']) is list)
        for index, source in enumerate(record['sources']):
            _require(type(source) is dict and set(source) == _SOURCE_FIELDS
                     and all(type(value) is str for value in source.values()) and bool(source['url']))
            _require(source['kind'] in {'product_interface','sdk_api','programming_manual','source_code','support_portal','driver','control_software'}
                     and source['authority'] in {'third_party_hosted_vendor_document','official','community'}
                     and source['match_level'] in {'exact_model','documented_family','generic_vendor','family_candidate','discovery_only'}
                     and source['access'] in {'search_index_only','content_read','download_read','blocked','redirected'})
            associations[(item_id, index)] = source['url']
        by_id[item_id] = record
    _require(len(models) == 2867 and len(records) - len(models) == 270 and len(equipment) == 6470
             and Counter(record['scope'] for record in records) == _SCOPES and len(associations) == 2260)
    return by_id, equipment, associations


def _overlay(value, research):
    _require(type(value) is dict and type(value.get('schema_version')) is int and value['schema_version'] == 1
             and value['kind'] == 'equipment_control_registry_overlay' and _count(value['record_count'], len(research))
             and value['catalog_state'] == 'read_only_metadata_catalog' and value['support_state_is_separate'] is True)
    source = value['source']
    _require(type(source) is dict and source['commit'] == SOURCE_COMMIT and source['model_json_sha256'] == _RESEARCH_SHA
             and source['research_json'] == _INPUTS[0][1])
    snapshot = value['registry_snapshot']
    _require(type(snapshot) is dict and snapshot['path'] == 'data/equipment.sqlite3'
             and _sha(snapshot['sha256']) and type(snapshot['inspection_mode']) is str
             and _count(snapshot['model_count'], 2867) and _count(snapshot['equipment_count'], 6470)
             and _count(snapshot['identity_item_count'], 270) and _count(snapshot['missing_or_mismatched_ids'], 0))
    rows = value['records']; _require(type(rows) is list and len(rows) == len(research))
    result = {}
    fields = {'item_id','registry_reconciliation','candidate_virtual_profile_ids','integration_state',
              'adapter_support_status','vendor_binary_executed','hardware_verified'}
    reconciliation_fields = {'item_id','model_id','existing_model_id_matched','missing_equipment_ids','equipment_model_mismatches',
                             'identity_record','automatic_new_model_creation_permitted','mapping_status'}
    for row in rows:
        _require(type(row) is dict and set(row) == fields and _id(row['item_id'])
                 and row['item_id'] in research and row['item_id'] not in result)
        record = research[row['item_id']]; identity = record['model_id'] is None
        _require(row['adapter_support_status'] == 'not_assessed' and row['vendor_binary_executed'] is False
                 and row['hardware_verified'] is False and row['integration_state'] == 'handoff_overlay_not_imported_into_application'
                 and type(row['candidate_virtual_profile_ids']) is list
                 and all(_id(profile) for profile in row['candidate_virtual_profile_ids'])
                 and len(set(row['candidate_virtual_profile_ids'])) == len(row['candidate_virtual_profile_ids']))
        reconciliation = row['registry_reconciliation']
        _require(type(reconciliation) is dict and set(reconciliation) == reconciliation_fields
                 and reconciliation['item_id'] == row['item_id'] and reconciliation['model_id'] == record['model_id']
                 and reconciliation['identity_record'] is identity
                 and reconciliation['automatic_new_model_creation_permitted'] is False
                 and reconciliation['missing_equipment_ids'] == [] and reconciliation['equipment_model_mismatches'] == [])
        _require((reconciliation['existing_model_id_matched'] is None if identity else reconciliation['existing_model_id_matched'] is True)
                 and reconciliation['mapping_status'] == ('source_equipment_ids_match_identity_not_resolved' if identity else 'existing_model_and_equipment_ids_match'))
        result[row['item_id']] = row
    return result


def _profiles(crosswalk, research, overlay):
    _require(type(crosswalk) is dict and type(crosswalk['schema_version']) is int and crosswalk['schema_version'] == 1
             and _count(crosswalk['profile_count'], 64) and type(crosswalk['status_counts']) is dict
             and set(crosswalk['status_counts']) == set(_PROFILE_COUNTS)
             and all(_count(crosswalk['status_counts'][key], value) for key, value in _PROFILE_COUNTS.items())
             and type(crosswalk['profiles']) is list and len(crosswalk['profiles']) == 64)
    profiles, by_item, direct = {}, defaultdict(list), defaultdict(set)
    counts = Counter()
    fields = {'item_id','model_id','manufacturer','model','scope','research_status','public_code_status','source_urls'}
    for profile in crosswalk['profiles']:
        _require(type(profile) is dict and _id(profile['profile_id']) and profile['profile_id'] not in profiles
                 and all(type(profile[key]) is str for key in ('manufacturer_as_recorded','model_as_recorded','role','text_comparison_status'))
                 and profile['installed_equipment_binding_established'] is False and profile['simulation_profile_retained'] is True
                 and _strings(profile['review_notes']) and type(profile['profile_evidence_refs']) is list)
        for evidence in profile['profile_evidence_refs']:
            _require(type(evidence) is dict and _sha(evidence['sha256']) and type(evidence['kind']) is str and bool(evidence['kind']))
            for key in ('table', 'row'):
                if key in evidence:
                    _require(type(evidence[key]) is int and evidence[key] > 0)
            if 'part' in evidence:
                _require(type(evidence['part']) is str and bool(evidence['part']))
        counts[profile['text_comparison_status']] += 1
        seen = set()
        for kind in _CANDIDATES:
            candidates = profile[kind]; _require(type(candidates) is list)
            for candidate in candidates:
                _require(type(candidate) is dict and set(candidate) == fields and candidate['item_id'] in research
                         and candidate['item_id'] not in seen)
                record = research[candidate['item_id']]
                _require(all(candidate[key] == record[key] for key in fields - {'source_urls'})
                         and candidate['source_urls'] == [source['url'] for source in record['sources']]
                         and _normalized(record['model']) == _normalized(profile['model_as_recorded']))
                same_manufacturer = _normalized(record['manufacturer']) == _normalized(profile['manufacturer_as_recorded'])
                _require(same_manufacturer == (kind == 'normalized_label_candidates'))
                seen.add(candidate['item_id']); by_item[candidate['item_id']].append(profile)
                if kind == 'normalized_label_candidates':
                    direct[candidate['item_id']].add(profile['profile_id'])
        status = ('normalized_label_candidates' if profile[_CANDIDATES[0]] else
                  'same_model_other_manufacturer_candidates' if profile[_CANDIDATES[1]] else 'no_text_candidate')
        _require(profile['text_comparison_status'] == status)
        profiles[profile['profile_id']] = profile
    _require(counts == _PROFILE_COUNTS)
    for item_id, row in overlay.items():
        _require(set(row['candidate_virtual_profile_ids']) == direct[item_id])
    return profiles, {item: sorted(values, key=lambda value: value['profile_id']) for item, values in by_item.items()}


def _urls(value, prior, source, associations):
    _require(type(prior) is dict and type(prior['schema_version']) is int and prior['schema_version'] == 1
             and prior['kind'] == 'equipment_control_prior_references' and type(prior['links']) is list)
    links = {}
    for link in prior['links']:
        _require(type(link) is dict and _id(link['id']) and link['id'] not in links and type(link['url']) is str and bool(link['url']))
        links[link['id']] = link['url']
    research_urls, prior_urls = set(associations.values()), set(links.values())
    _require(len(links) == 83 and len(prior_urls) == 83 and _count(prior['unique_url_count'], 83) and len(research_urls) == 1624)
    _require(type(value) is dict and type(value['schema_version']) is int and value['schema_version'] == 1
             and value['source'] == source and _count(value['prior_reference_url_count'], 83)
             and _count(value['research_unique_url_count'], 1624) and _count(value['overlapping_url_count'], 17)
             and _count(value['unique_url_count'], 1690) and _count(value['research_model_source_associations'], 2260)
             and type(value['sources']) is list and len(value['sources']) == 1690)
    seen_urls, seen_associations, seen_prior = set(), set(), set()
    for row in value['sources']:
        _require(type(row) is dict and type(row['url']) is str and row['url'] not in seen_urls
                 and row['source_id'] == 'URL-' + hashlib.sha256(row['url'].encode('utf-8')).hexdigest()[:16]
                 and type(row['research_associations']) is list and type(row['prior_reference_ids']) is list
                 and type(row['content_collection_status']) is str
                 and row['execution_and_hardware_verification'] == 'not_established_by_research')
        for association in row['research_associations']:
            _require(type(association) is dict and set(association) == {'item_id','source_index'}
                     and _id(association['item_id']) and type(association['source_index']) is int)
            key = (association['item_id'], association['source_index'])
            _require(key in associations and key not in seen_associations and associations[key] == row['url'])
            seen_associations.add(key)
        for reference in row['prior_reference_ids']:
            _require(_id(reference) and reference in links and reference not in seen_prior and links[reference] == row['url'])
            seen_prior.add(reference)
        seen_urls.add(row['url'])
    _require(seen_urls == research_urls | prior_urls and len(research_urls & prior_urls) == 17
             and seen_associations == set(associations) and seen_prior == set(links))


def _reviews(value, research):
    _require(type(value) is dict and type(value['schema_version']) is int and value['schema_version'] == 1
             and value['kind'] == 'equipment_control_intake_review_notes' and value['source_commit'] == SOURCE_COMMIT
             and type(value['notes']) is list)
    notes, ids = defaultdict(list), set()
    for note in value['notes']:
        _require(type(note) is dict and _id(note['note_id']) and note['note_id'] not in ids
                 and type(note['item_ids']) is list and len(set(note['item_ids'])) == len(note['item_ids'])
                 and type(note['title']) is str and type(note['explanation']) is str and type(note['evidence']) is list)
        for evidence in note['evidence']:
            _require(type(evidence) is dict and _sha(evidence['sha256'])
                     and type(evidence['kind']) is str and bool(evidence['kind'])
                     and type(evidence['url']) is str and bool(evidence['url'])
                     and type(evidence['pdf_pages_1based']) is list
                     and all(type(page) is int and page > 0 for page in evidence['pdf_pages_1based']))
        for item_id in note['item_ids']:
            _require(_id(item_id) and item_id in research)
            notes[item_id].append(note)
        ids.add(note['note_id'])
    return notes


class ControlSourceCatalog:
    """An immutable input snapshot with detached read-only DTO responses."""
    def __init__(self, repo_root=None):
        try:
            root = Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[1]
            data = {key: _read(root, relative, pins) for key, relative, pins in _INPUTS}
            research, equipment, associations = _research(data['research'])
            overlay = _overlay(data['overlay'], research)
            profiles, profiles_by_item = _profiles(data['overlay']['profile_crosswalk'], research, overlay)
            _urls(data['urls'], data['prior'], data['overlay']['source'], associations)
            notes = _reviews(data['reviews'], research)
            records = {item: {'research_record': row, **{key: value for key, value in overlay[item].items() if key != 'item_id'}} for item, row in research.items()}
            items = {item: {'item_id': item, **{key: row[key] for key in ('model_id','manufacturer','model','scope','research_status','public_code_status','registration_rows')},
                'source_count': len(row['sources']), 'equipment_id_count': len(row['equipment_ids']),
                **{key: overlay[item][key] for key in ('candidate_virtual_profile_ids','adapter_support_status','vendor_binary_executed','hardware_verified')}} for item, row in research.items()}
            search = {item: tuple(value.casefold() for value in [item, row['model_id'] or '', row['manufacturer'], row['model'], *row['names']]) for item, row in research.items()}
            profile_items = {key: {candidate['item_id'] for kind in _CANDIDATES for candidate in profile[kind]} for key, profile in profiles.items()}
            summary = {'schema_version': 1, 'kind': 'control_source_summary', 'source_commit': SOURCE_COMMIT,
                'catalog_state': 'read_only_metadata_catalog', 'item_count': len(research), 'model_count': 2867,
                'identity_item_count': 270, 'equipment_id_count': len(equipment), 'scope_counts': dict(_SCOPES),
                'source_association_count': len(associations), 'research_unique_url_count': 1624,
                'prior_reference_unique_url_count': 83, 'overlapping_url_count': 17, 'unique_url_count': 1690,
                'profile_count': len(profiles), 'profile_candidate_counts': data['overlay']['profile_crosswalk']['status_counts'],
                'adapter_support_status': 'not_assessed', 'vendor_binary_executed': False, 'hardware_verified': False,
                'profile_binding_established': False, 'registry_snapshot': data['overlay']['registry_snapshot']}
        except (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError, RuntimeError):
            raise ControlSourceCatalogError('catalog_unavailable') from None
        self._records, self._items, self._search = records, items, search
        self._profiles_by_item, self._profile_items, self._notes = profiles_by_item, profile_items, notes
        self._equipment, self._ids, self._summary = equipment, sorted(research), summary
        self._profile_metadata = copy.deepcopy(data['overlay']['profile_crosswalk']['profiles'])

    def profiles(self):
        """Return validated text crosswalk metadata; never an installed binding."""
        return copy.deepcopy(self._profile_metadata)

    def summary(self):
        return copy.deepcopy(self._summary)

    def find_items(self, *, query='', scope=None, model_id=None, equipment_id=None, profile_id=None, offset=0, limit=25):
        if (type(query) is not str or len(query) > 200
                or scope is not None and (type(scope) is not str or scope not in _SCOPES)
                or any(value is not None and not _id(value) for value in (model_id, equipment_id, profile_id))
                or type(offset) is not int or not 0 <= offset <= 1000000
                or type(limit) is not int or not 1 <= limit <= 100):
            raise ControlSourceCatalogError('catalog_invalid_query')
        folded = query.casefold()
        candidates = self._profile_items.get(profile_id, set()) if profile_id is not None else None
        matched = [item for item in self._ids
            if (scope is None or self._items[item]['scope'] == scope)
            and (model_id is None or self._items[item]['model_id'] == model_id)
            and (equipment_id is None or self._equipment.get(equipment_id) == item)
            and (candidates is None or item in candidates)
            and any(folded in value for value in self._search[item])]
        return {'schema_version': 1, 'kind': 'control_source_items', 'source_commit': SOURCE_COMMIT,
                'total': len(matched), 'offset': offset, 'limit': limit,
                'next_offset': offset + limit if offset + limit < len(matched) else None,
                'items': copy.deepcopy([self._items[item] for item in matched[offset:offset + limit]])}

    def detail(self, item_id):
        if not _id(item_id):
            raise ControlSourceCatalogError('catalog_invalid_query')
        if item_id not in self._records:
            raise ControlSourceCatalogError('catalog_item_not_found')
        return copy.deepcopy({'schema_version': 1, 'kind': 'control_source_detail', 'source_commit': SOURCE_COMMIT,
                'catalog_state': 'read_only_metadata_catalog', 'record': self._records[item_id],
                'profile_candidates': self._profiles_by_item.get(item_id, []), 'review_notes': self._notes.get(item_id, [])})

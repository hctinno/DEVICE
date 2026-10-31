"""Public metadata declarations only; never instantiate a virtual bench."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from labflow.control_source_catalog import ControlSourceCatalog
from labflow.virtual_support_view import build_virtual_support_view


ROOT = Path(__file__).resolve().parents[1]


class VirtualSupportViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = ControlSourceCatalog(ROOT)

    def test_real_fixed_metadata_separates_roles_protocol_and_verification(self):
        with patch('labflow.virtual_fleet.core.VirtualFleet.__init__', side_effect=AssertionError('no_fleet')), \
             patch('labflow.virtual_lab.VirtualLab.__init__', side_effect=AssertionError('no_lab')):
            dto = build_virtual_support_view(self.sources)
        self.assertEqual(dto['kind'], 'virtual_support_view')
        self.assertEqual(dto['snapshot_scope'], 'first_success_host_snapshot')
        self.assertEqual(dto['profile_count'], 64)
        self.assertEqual(len(dto['profiles']), 64)
        self.assertEqual(dto['provenance']['material_source_commit'], '8dec2d783b99609b27fb37f82752f17146206f4d')
        self.assertEqual(dto['provenance']['catalog_sha256'], '0d2de78fafb496b746105aa852b25d4854fcf04fa32520cea858a315e5147967')
        meter = next(p for p in dto['profiles'] if p['model'] == 'N1911A')
        self.assertEqual(meter['virtual_role']['status'], 'declared')
        self.assertIn('acquire', meter['virtual_role']['action_names'])
        self.assertFalse(meter['virtual_role']['protocol_scope'])
        self.assertEqual(meter['protocol']['status'], 'not_assessed')
        self.assertNotIn('N1914A', [p['model'] for p in dto['profiles']])
        contract, = dto['adapter_contracts']
        self.assertEqual(contract['model'], 'N1914A')
        self.assertEqual(contract['profile_id'], 'n1914a-a-ascii-v1')
        self.assertEqual(len(contract['commands']), 12)
        self.assertEqual((contract['synthetic_input'], contract['window']), ('A', 1))
        for row in [dto, *dto['profiles']]:
            self.assertEqual(row['virtual_verification'], 'not_assessed')
            self.assertIs(row['hardware_verified'], False)
            self.assertIs(row['execution_authority'], False)

    def test_material_access_and_text_candidates_never_become_installed_support(self):
        dto = build_virtual_support_view(self.sources)
        counts, access = {}, set()
        for row in dto['profiles']:
            material = row['materials']
            status = material['candidate_status']
            counts[status] = counts.get(status, 0) + 1
            self.assertIs(material['installed_equipment_binding_established'], False)
            for candidate in material['candidates']:
                for source in candidate['sources']:
                    access.add(source['access'])
                    self.assertTrue(source['url'].startswith(('https://', 'http://')))
            self.assertTrue(row['evidence_refs'])
        self.assertEqual(counts, {'normalized_label_candidates': 37,
                                 'same_model_other_manufacturer_candidates': 9, 'no_text_candidate': 18})
        self.assertTrue({'search_index_only', 'content_read', 'download_read', 'blocked'} <= access)

    def test_profiles_getter_and_builder_return_detached_native_metadata(self):
        profiles = self.sources.profiles()
        self.assertEqual(len(profiles), 64)
        old = copy.deepcopy(profiles[0])
        profiles[0]['model_as_recorded'] = 'CHANGED'
        self.assertEqual(self.sources.profiles()[0], old)
        first = build_virtual_support_view(self.sources)
        first['profiles'][0]['virtual_role']['action_names'].clear()
        first['adapter_contracts'][0]['commands'].clear()
        second = build_virtual_support_view(self.sources)
        self.assertTrue(second['profiles'][0]['virtual_role']['action_names'])
        self.assertEqual(len(second['adapter_contracts'][0]['commands']), 12)
        self.assertLess(len(json.dumps(second).encode()), 524288)

    def test_changed_catalog_bytes_are_rejected_before_publication(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / 'virtual_profiles/sm_a176u_unlicensed.json'
            target.parent.mkdir()
            raw = (ROOT / 'virtual_profiles/sm_a176u_unlicensed.json').read_bytes()
            target.write_bytes(raw + b' ')
            with self.assertRaisesRegex(ValueError, '^virtual_support_unavailable$'):
                build_virtual_support_view(self.sources, repo_root=root)

    def test_unsafe_links_promoted_binding_and_non_native_metadata_fail_closed(self):
        original = self.sources.detail
        def unsafe(item_id):
            result = original(item_id)
            result['record']['research_record']['sources'][0]['url'] = 'https://user:password@example.com/private'
            return result
        with patch.object(self.sources, 'detail', side_effect=unsafe):
            with self.assertRaisesRegex(ValueError, '^virtual_support_unavailable$'):
                build_virtual_support_view(self.sources)
        profiles = self.sources.profiles()
        profiles[0]['installed_equipment_binding_established'] = True
        with patch.object(self.sources, 'profiles', return_value=profiles):
            with self.assertRaisesRegex(ValueError, '^virtual_support_unavailable$'):
                build_virtual_support_view(self.sources)
        class DictionarySubclass(dict):
            pass
        with patch('labflow.virtual_support_view.get_role_actions', return_value=DictionarySubclass()):
            with self.assertRaisesRegex(ValueError, '^virtual_support_unavailable$'):
                build_virtual_support_view(self.sources)

    def test_missing_role_declaration_is_unknown_not_unsupported_or_verified(self):
        with patch('labflow.virtual_support_view.get_role_actions', return_value={}):
            dto = build_virtual_support_view(self.sources)
        for row in dto['profiles']:
            self.assertEqual(row['virtual_role']['status'], 'not_assessed')
            self.assertEqual(row['virtual_role']['action_names'], [])
            self.assertEqual(row['virtual_verification'], 'not_assessed')

    def test_nested_detail_metadata_is_native_before_field_access(self):
        original = self.sources.detail
        accessed = []
        class DictionarySubclass(dict):
            def __getitem__(self, key):
                accessed.append(key)
                return super().__getitem__(key)
        def substituted(item_id):
            result = original(item_id)
            result['record']['research_record'] = DictionarySubclass(result['record']['research_record'])
            return result
        with patch.object(self.sources, 'detail', side_effect=substituted):
            with self.assertRaisesRegex(ValueError, '^virtual_support_unavailable$'):
                build_virtual_support_view(self.sources)
        self.assertEqual(accessed, [])


if __name__ == '__main__':
    unittest.main()

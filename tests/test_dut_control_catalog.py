"""Pinned DUT metadata queries, not execution of collected sources or tools."""
from contextlib import contextmanager, ExitStack
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from labflow import dut_control_catalog as module


ROOT = Path(__file__).resolve().parents[1]
FILES = ('control_sources/dut_sources.json', 'control_sources/dut_paths.json')


def encode(value):
    return json.dumps(value, ensure_ascii=True, allow_nan=True).encode('utf-8')


class DutControlCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = {name: (ROOT / name).read_bytes() for name in FILES}
        cls.data = {name: json.loads(raw) for name, raw in cls.raw.items()}
        cls.sources = cls.data[FILES[0]]
        cls.paths = cls.data[FILES[1]]
        cls.by_id = {row['id']: row for row in cls.sources['sources']}
        cls.catalog = module.DutControlCatalog()

    @classmethod
    def tearDownClass(cls):
        for name, raw in cls.raw.items():
            if (ROOT / name).read_bytes() != raw:
                raise AssertionError('pinned input changed')

    @contextmanager
    def private_inputs(self):
        local = ROOT / '.local' / 'DUT-CATALOG-010'
        local.mkdir(parents=True, exist_ok=True)
        root = Path(tempfile.mkdtemp(prefix='test-inputs-', dir=local))
        self.assertTrue(root.resolve().is_relative_to(local.resolve()))
        for name, raw in self.raw.items():
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        # Keep failed/tampered fixtures in ignored private storage.
        yield root

    @contextmanager
    def repinned(self, root, name, payload):
        (root / name).write_bytes(payload)
        inputs = tuple((path, hashlib.sha256(payload).hexdigest() if path == name else pin, cap)
                       for path, pin, cap in module._INPUTS)
        with patch.object(module, '_INPUTS', inputs):
            yield

    def assert_error(self, function, code):
        with self.assertRaises(module.DutControlCatalogError) as caught:
            function()
        error = caught.exception
        self.assertIsInstance(error, ValueError)
        self.assertEqual(error.code, code)
        self.assertEqual(str(error), code)
        self.assertEqual(error.args, (code,))
        self.assertIsNone(error.__cause__)
        self.assertIsNone(error.__context__)
        self.assertNotIn('PRIVATE_CANARY', str(error))

    def unavailable(self, root):
        self.assert_error(lambda: module.DutControlCatalog(root), 'dut_catalog_unavailable')

    def bad_document(self, name, value):
        with self.private_inputs() as root, self.repinned(root, name, encode(value)):
            self.unavailable(root)

    def assert_wrapper(self, value, kind):
        self.assertEqual(value['schema_version'], 1)
        self.assertEqual(value['kind'], kind)
        self.assertEqual(value['catalog_state'], 'read_only_metadata_catalog')
        self.assertEqual(value['support_status'], 'not_assessed')
        self.assertIs(value['hardware_verified'], False)
        self.assertIs(value['source_code_executed'], False)
        self.assertIs(value['automatic_fallback_enabled'], False)

    def test_summary_exact_dto_counts_provenance_and_recorded_environment(self):
        value = self.catalog.summary()
        self.assertEqual(set(value), set('schema_version kind catalog_state counts route_count provenance '
            'support_status hardware_verified source_code_executed automatic_fallback_enabled '
            'reference_environment remaining_public_source_gaps'.split()))
        self.assert_wrapper(value, 'dut_control_summary')
        self.assertEqual(value['counts'], self.sources['counts'])
        self.assertEqual(value['counts'], {
            'source_units': 30, 'github_projects': 25, 'aosp_components': 4,
            'pinned_submodules': 1, 'archive_files': 32, 'archive_bytes': 74333207,
            'snapshot_files_verified': 10538, 'stable_source_distributions': 2,
        })
        self.assertEqual(value['route_count'], 9)
        for field in ('provenance', 'reference_environment', 'remaining_public_source_gaps'):
            self.assertEqual(value[field], self.sources[field])

    def test_routes_are_original_order_and_types_without_truthiness_coercion(self):
        routes = self.catalog.routes()
        self.assertIs(type(routes), list)
        self.assertEqual(routes, self.paths['paths'])
        self.assertEqual(len(routes), 9)
        self.assertEqual([r['backend'] for r in routes], [r['backend'] for r in self.paths['paths']])
        android = self.catalog.route('android_ui_and_test')['route']
        self.assertEqual(android['independent_of_adb'], 'usually_no_for_standard_bootstrap')
        self.assertIs(type(android['independent_of_adb']), str)
        self.assertIs(self.catalog.route('adb')['route']['independent_of_adb'], False)

    def test_every_route_exact_wrapper_restores_all_source_and_release_relationships(self):
        for original in self.paths['paths']:
            with self.subTest(backend=original['backend']):
                value = self.catalog.route(original['backend'])
                self.assertEqual(set(value), set('schema_version kind catalog_state route sources '
                    'stable_releases support_status hardware_verified source_code_executed automatic_fallback_enabled'.split()))
                self.assert_wrapper(value, 'dut_control_route')
                self.assertEqual(value['route'], original)
                self.assertEqual(value['sources'], [self.by_id[i] for i in original['sources']])
                self.assertEqual(value['stable_releases'], [r for r in self.sources['stable_releases']
                    if r['source_id'] in original['sources']])

    def test_all_thirty_sources_keep_exact_records_declarations_members_and_backends(self):
        for source_id, original in self.by_id.items():
            with self.subTest(source_id=source_id):
                value = self.catalog.source(source_id)
                self.assertEqual(set(value), set('schema_version kind catalog_state record stable_releases '
                    'dependency_declarations manufacturing_member_checks backends support_status '
                    'hardware_verified source_code_executed automatic_fallback_enabled'.split()))
                self.assert_wrapper(value, 'dut_control_source')
                self.assertEqual(value['record'], original)
                for field in ('stable_releases', 'dependency_declarations'):
                    self.assertEqual(value[field], [r for r in self.sources[field] if r['source_id'] == source_id])
                self.assertEqual(value['manufacturing_member_checks'], [
                    r for r in self.sources['manufacturing_references']['already_acquired_member_checks']
                    if r['source_id'] == source_id])
                self.assertEqual(value['backends'], [r['backend'] for r in self.paths['paths']
                                                     if source_id in r['sources']])

    def test_oem_empty_route_stays_unverified_without_fallback(self):
        value = self.catalog.route('oem_sdk_cli')
        self.assertEqual(value['sources'], [])
        self.assertEqual(value['stable_releases'], [])
        self.assertEqual(value['route']['sources'], [])
        self.assertEqual(value['route']['acquisition_status'], 'public_anyway_interface_not_verified')
        self.assertEqual(value['route']['independent_of_adb'], 'unknown_per_tool')
        self.assert_wrapper(value, 'dut_control_route')

    def test_service_ios_and_chipset_references_keep_conditions_and_unassessed_support(self):
        for backend in ('firmware_service_reference', 'future_ios', 'chipset_rf_reference',
                        'windows_vendor_gui', 'serial_at_or_documented_protocol', 'usb_hid_documented_protocol'):
            value = self.catalog.route(backend)
            original = next(r for r in self.paths['paths'] if r['backend'] == backend)
            self.assertEqual(value['route']['conditions'], original['conditions'])
            self.assertTrue(value['route']['conditions'])
            for record in value['sources']:
                self.assertEqual(record['device_or_firmware_supported'], 'not_assessed')
                self.assertIs(record['adapter_integrated'], False)
                self.assertIs(record['vendor_code_executed'], False)
                self.assertIs(record['hardware_verified'], False)

    def test_partial_pywinauto_and_stable_release_are_distinct_and_no_missing_flags_added(self):
        value = self.catalog.source('DUT-G13')
        self.assertEqual(value['record']['source_file_count'], 258)
        self.assertNotIn('snapshot_file_count', value['record'])
        self.assertEqual(value['record']['status'], 'source_files_and_release_acquired')
        self.assertEqual(value['stable_releases'][0]['release_version'], '0.6.9')
        self.assertNotIn('requires_python', value['stable_releases'][0])
        for field in ('source_code_executed', 'code_executed', 'hardware_verified'):
            self.assertNotIn(field, value['stable_releases'][0])

    def test_exact_hid_submodule_is_not_current_hid_head(self):
        child = self.catalog.source('DUT-S01')['record']
        self.assertEqual(child['parent_source_id'], 'DUT-G18')
        self.assertEqual(child['parent_path'], 'hidapi')
        self.assertEqual(child['commit'], 'd6b2a974608dec3b76fb1e36c189f22b9cf3650c')
        self.assertNotEqual(child['commit'], self.catalog.source('DUT-G17')['record']['commit'])

    def test_zero_byte_license_markers_preserve_empty_hash_and_pending_reuse_review(self):
        found = []
        for source_id in self.by_id:
            record = self.catalog.source(source_id)['record']
            for item in record['license_evidence_files']:
                if item['bytes'] == 0:
                    self.assertEqual(item['sha256'], hashlib.sha256(b'').hexdigest())
                    self.assertEqual(record['device_or_firmware_supported'], 'not_assessed')
                    found.append((source_id, item['path']))
        self.assertEqual(found, [('DUT-A01', 'MODULE_LICENSE_APACHE2'), ('DUT-G10', 'uibox/LICENSE')])

    def test_dependency_constraints_and_environment_are_snapshots_not_current_host_checks(self):
        with patch('platform.python_version', side_effect=AssertionError('host query')):
            catalog = module.DutControlCatalog()
            mobly = catalog.source('DUT-G01')
            env = catalog.summary()['reference_environment']
        self.assertEqual(mobly['dependency_declarations'][0]['declarations']['requires-python'], '>=3.14')
        self.assertEqual(mobly['stable_releases'][0]['requires_python'], '>=3.11')
        self.assertEqual(env['python_version'], '3.12.4')
        self.assertEqual(env['node_version'], '24.16.0')
        self.assertIs(env['mobly_master_python_constraint_satisfied'], False)
        self.assertIs(env['mobly_1_13_1_python_constraint_satisfied'], True)
        self.assertIs(env['appium_and_uiautomator2_node_constraint_satisfied'], True)
        self.assertIs(env['npm_android_sdk_jdk_device_requirements_checked'], False)

    def test_manufacturing_code_presence_and_license_gaps_do_not_establish_product_support(self):
        for source_id in ('DUT-G19', 'DUT-G21'):
            value = self.catalog.source(source_id)
            self.assertEqual(len(value['manufacturing_member_checks']), 1)
            member = value['manufacturing_member_checks'][0]
            self.assertIs(member['manufacturing_test_code_present'], True)
            self.assertEqual(member['commit'], value['record']['commit'])
            self.assertEqual(member['product_support'], 'not_assessed')
            self.assert_wrapper(value, 'dut_control_source')
        for source_id in ('DUT-A02', 'DUT-G21'):
            self.assertEqual(self.catalog.source(source_id)['record']['license_evidence_files'], [])
            self.assertEqual(self.catalog.source(source_id)['record']['license_review_status'],
                             self.by_id[source_id]['license_review_status'])

    def test_references_are_original_and_not_counted_as_acquired_archives(self):
        value = self.catalog.manufacturing_references()
        self.assertEqual(value, self.sources['manufacturing_references'])
        self.assertEqual(value['additional_reviewed_reference_count'], 9)
        self.assertEqual(len(value['already_acquired_member_checks']), 2)
        self.assertEqual(value['newly_acquired_repository_archives'], 0)
        self.assertIs(value['new_links_in_equipment_url_index'], False)
        for row in value['additional_reviewed_references']:
            self.assertIsNone(row['repository_commit_pinned'])
            self.assertIs(row['whole_repository_archive_acquired'], False)
            self.assertIs(row['new_local_source_copy_saved'], False)
            self.assertEqual(row['target_device_support'], 'not_verified')
        self.assertEqual(self.catalog.summary()['counts']['source_units'], 30)
        self.assertEqual(value['samsung_legacy_muic_resistance_ohm_to_code']['255000'], 'ADC_JIG_USB_OFF')
        self.assertTrue(value['unverified_user_supplied_claims'])

    def test_query_types_and_syntax_are_exact_without_aliases_or_path_inputs(self):
        for bad in (None, True, 1, b'adb', [], {}, '', 'ADB', ' adb', 'adb ', 'a' * 81,
                    '../PRIVATE_CANARY', 'C:/PRIVATE_CANARY', 'https://example.com', '가상', '\ud800'):
            self.assert_error(lambda: self.catalog.route(bad), 'dut_catalog_invalid_query')
        for bad in (None, False, 1, [], '', 'dut-G01', 'DUT-g01', 'DUT-G1', 'DUT-G001',
                    'DUT-G01 ', 'DUT-G０１', '../PRIVATE_CANARY', 'C:\\PRIVATE_CANARY', '\ud800'):
            self.assert_error(lambda: self.catalog.source(bad), 'dut_catalog_invalid_query')

    def test_well_formed_unknown_queries_are_not_found_without_fallback(self):
        for backend in ('unknown', 'a' * 80, 'adb_unsupported'):
            self.assert_error(lambda: self.catalog.route(backend), 'dut_catalog_item_not_found')
        for source_id in ('DUT-G00', 'DUT-A99', 'DUT-S02'):
            self.assert_error(lambda: self.catalog.source(source_id), 'dut_catalog_item_not_found')

    def test_all_returns_are_detached_deep_copies(self):
        calls = [
            self.catalog.summary, self.catalog.routes, lambda: self.catalog.route('android_ui_and_test'),
            lambda: self.catalog.source('DUT-G01'), self.catalog.manufacturing_references,
        ]
        for function in calls:
            original, changed = function(), function()
            def mutate(value):
                if type(value) is dict:
                    for child in list(value.values()):
                        mutate(child)
                    value['PRIVATE_CANARY'] = True
                elif type(value) is list:
                    for child in list(value):
                        mutate(child)
                    value.append('PRIVATE_CANARY')
            mutate(changed)
            self.assertEqual(function(), original)

    def test_constructor_snapshot_survives_input_change_without_query_io(self):
        with self.private_inputs() as root:
            catalog = module.DutControlCatalog(root)
            expected = catalog.source('DUT-G01')
            (root / FILES[0]).write_bytes(b'PRIVATE_CANARY')
            with patch.object(Path, 'open', side_effect=AssertionError('query reopened file')), \
                 patch.object(Path, 'stat', side_effect=AssertionError('query stat')):
                self.assertEqual(catalog.source('DUT-G01'), expected)
                self.assertEqual(len(catalog.routes()), 9)
                self.assertEqual(catalog.summary()['counts']['source_units'], 30)
            self.unavailable(root)

    def test_only_fixed_two_files_are_read_and_tools_databases_network_never_used(self):
        opened = []
        original = Path.open
        def inspect(path, *args, **kwargs):
            opened.append(path.resolve())
            self.assertIn(path.resolve(), {(ROOT / f).resolve() for f in FILES})
            self.assertEqual(args, ('rb',))
            return original(path, *args, **kwargs)
        with ExitStack() as stack:
            for target in ('sqlite3.connect', 'socket.create_connection', 'subprocess.run',
                           'subprocess.Popen', 'importlib.import_module'):
                stack.enter_context(patch(target, side_effect=AssertionError('unexpected execution')))
            stack.enter_context(patch.object(Path, 'open', inspect))
            catalog = module.DutControlCatalog()
            self.assertEqual(len(opened), 2)
            for source_id in self.by_id:
                catalog.source(source_id)
            for route in self.paths['paths']:
                catalog.route(route['backend'])
            catalog.summary(); catalog.routes(); catalog.manufacturing_references()
            self.assertEqual(len(opened), 2)

    def test_missing_inputs_and_invalid_roots_never_use_default_inputs(self):
        with self.private_inputs() as root:
            (root / FILES[1]).rename(root / 'retained-original.json')
            self.unavailable(root)
        for value in (123, [], b'PRIVATE_CANARY', ROOT / '.local' / 'missing-PRIVATE_CANARY'):
            self.unavailable(value)

    def test_read_errors_and_path_conversion_errors_have_no_raw_exception_context(self):
        with patch.object(Path, 'open', side_effect=OSError('PRIVATE_CANARY C:/secret')):
            self.unavailable(ROOT)
        class BadPath:
            def __fspath__(self):
                raise RuntimeError('PRIVATE_CANARY C:/secret')
        self.unavailable(BadPath())

    def test_pin_mismatch_and_crlf_are_rejected_without_normalization(self):
        for name in FILES:
            for payload in (self.raw[name] + b' ', self.raw[name].replace(b'\n', b'\r\n')):
                with self.private_inputs() as root:
                    (root / name).write_bytes(payload)
                    self.unavailable(root)

    def test_file_caps_are_enforced_before_open_and_never_read_archives(self):
        for name, cap in ((FILES[0], 256 * 1024), (FILES[1], 32 * 1024)):
            with self.private_inputs() as root:
                (root / name).write_bytes(b'x' * (cap + 1))
                original = Path.open
                def guarded(path, *args, **kwargs):
                    self.assertNotEqual(path, root / name, 'oversize file opened')
                    return original(path, *args, **kwargs)
                with patch.object(Path, 'open', guarded):
                    self.unavailable(root)

    def test_bounded_read_rejects_extra_bytes_when_stat_size_is_stale(self):
        with self.private_inputs() as root:
            target = root / FILES[0]
            target.write_bytes(b'x' * (256 * 1024 + 10))
            old_stat, old_open, reads = Path.stat, Path.open, []
            def stale(path, *args, **kwargs):
                result = old_stat(path, *args, **kwargs)
                if path == target:
                    fields = list(result); fields[6] = 1
                    return os.stat_result(fields)
                return result
            class Stream:
                def __init__(self, wrapped):
                    self.wrapped = wrapped
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    self.wrapped.close()
                def read(self, size):
                    reads.append(size)
                    return self.wrapped.read(size)
            def opened(path, *args, **kwargs):
                return Stream(old_open(path, *args, **kwargs))
            with patch.object(Path, 'stat', stale), patch.object(Path, 'open', opened):
                self.unavailable(root)
            self.assertEqual(reads, [256 * 1024 + 1])

    def test_resolved_fixed_file_outside_root_is_rejected_before_open(self):
        with self.private_inputs() as root:
            original = Path.resolve
            def resolved(path, *args, **kwargs):
                if path == root / FILES[0]:
                    return ROOT.parent / 'PRIVATE_CANARY.json'
                return original(path, *args, **kwargs)
            with patch.object(Path, 'resolve', resolved), \
                 patch.object(Path, 'open', side_effect=AssertionError('outside file opened')):
                self.unavailable(root)

    def test_repository_locators_cannot_be_local_paths(self):
        for field in ('repository', 'git_ref'):
            value = deepcopy(self.sources)
            value['sources'][4][field] = 'C:/PRIVATE_CANARY/secret'
            self.bad_document(FILES[0], value)

    def test_duplicate_keys_invalid_utf8_and_nonfinite_json_fail_even_if_repinned(self):
        for name in FILES:
            duplicate = b'{"schema_version":1,' + self.raw[name].lstrip()[1:]
            self.assertEqual(json.loads(duplicate)['schema_version'], 1)
            for payload in (duplicate, b'\xff', b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1e999}'):
                with self.private_inputs() as root, self.repinned(root, name, payload):
                    self.unavailable(root)
        bad = deepcopy(self.sources)
        bad['sources'][0]['snapshot_scope'] = '\ud800'
        self.bad_document(FILES[0], bad)

    def test_invalid_depth_and_non_object_documents_are_sanitized(self):
        for name in FILES:
            for payload in (b'null', b'[]', b'[' * 1100 + b'0' + b']' * 1100):
                with self.private_inputs() as root, self.repinned(root, name, payload):
                    self.unavailable(root)

    def test_source_structure_ids_pins_counts_flags_license_and_private_fields_are_validated(self):
        changes = [
            lambda x: x.update(schema_version=True),
            lambda x: x['counts'].update(pinned_submodules=True),
            lambda x: x['counts'].update(snapshot_files_verified=10539),
            lambda x: x['sources'].pop(),
            lambda x: x['sources'][0].update(id=x['sources'][1]['id']),
            lambda x: x['sources'][0].update(commit='PRIVATE_CANARY'),
            lambda x: x['sources'][0].update(archive_sha256='f' * 63),
            lambda x: x['sources'][0].update(archive_bytes=True),
            lambda x: x['sources'][0].update(hardware_verified=True),
            lambda x: x['sources'][0].update(adapter_integrated=True),
            lambda x: x['sources'][0].update(vendor_code_executed=True),
            lambda x: x['sources'][0].update(device_or_firmware_supported='supported'),
            lambda x: x['sources'][0].update(archive_relative='C:/PRIVATE_CANARY'),
            lambda x: x['sources'][0]['license_evidence_files'][0].update(sha256='PRIVATE_CANARY'),
            lambda x: x['sources'][0]['license_evidence_files'][0].update(bytes=True),
            lambda x: x['sources'][0]['license_evidence_files'][0].update(path='C:/PRIVATE_CANARY'),
            lambda x: x.update(source_code_executed=True),
            lambda x: x.update(automatic_fallback_enabled=True),
            lambda x: x['provenance'].update(main_prompt_v5_sha256='PRIVATE_CANARY'),
        ]
        for i, change in enumerate(changes):
            with self.subTest(case=i):
                value = deepcopy(self.sources); change(value); self.bad_document(FILES[0], value)

    def test_route_reference_types_duplicates_oem_and_independence_are_validated(self):
        changes = [
            lambda x: x.update(schema_version=True),
            lambda x: x.update(unconditional_fallback_enabled=True),
            lambda x: x.update(bench_validation_performed=True),
            lambda x: x['paths'].pop(),
            lambda x: x['paths'][0].update(backend=x['paths'][1]['backend']),
            lambda x: x['paths'][0]['sources'].append('DUT-G99'),
            lambda x: x['paths'][0]['sources'].append('DUT-A01'),
            lambda x: x['paths'][2]['sources'].append('DUT-A01'),
            lambda x: x['paths'][0].update(independent_of_adb=0),
            lambda x: x['paths'][1].update(independent_of_adb=True),
        ]
        for i, change in enumerate(changes):
            with self.subTest(case=i):
                value = deepcopy(self.paths); change(value); self.bad_document(FILES[1], value)

    def test_stable_submodule_dependency_and_member_relations_are_validated(self):
        changes = [
            lambda x: x['sources'][-1].update(parent_source_id='DUT-G17'),
            lambda x: x['stable_releases'][0].update(source_id='DUT-G99'),
            lambda x: x['stable_releases'][0].update(release_version='other'),
            lambda x: x['dependency_declarations'][0].update(installed_dependency_lock_verified=True),
            lambda x: x['dependency_declarations'][0].update(source_id='DUT-G99'),
            lambda x: x['manufacturing_references']['already_acquired_member_checks'][0].update(commit='f' * 40),
            lambda x: x['manufacturing_references']['already_acquired_member_checks'][0].update(product_support='supported'),
            lambda x: x['manufacturing_references']['already_acquired_member_checks'][0].update(member_path='../PRIVATE_CANARY'),
            lambda x: x['manufacturing_references']['additional_reviewed_references'][0].update(whole_repository_archive_acquired=True),
            lambda x: x['manufacturing_references'].update(new_links_in_equipment_url_index=True),
            lambda x: x['reference_environment'].update(npm_android_sdk_jdk_device_requirements_checked=True),
        ]
        for i, change in enumerate(changes):
            with self.subTest(case=i):
                value = deepcopy(self.sources); change(value); self.bad_document(FILES[0], value)


if __name__ == '__main__':
    unittest.main()

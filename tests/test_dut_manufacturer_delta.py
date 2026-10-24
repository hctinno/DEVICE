"""Literal old references and selected-file delta; no collected program execution."""
from contextlib import contextmanager, ExitStack
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from labflow import dut_manufacturer_delta as module
from labflow.dut_control_catalog import DutControlCatalog


ROOT = Path(__file__).resolve().parents[1]
PARENTS = ('control_sources/dut_sources.json', 'control_sources/dut_paths.json')
DELTA = 'control_sources/dut_manufacturer_delta.json'
FILES = (*PARENTS, DELTA)


def payload(value):
    return json.dumps(value, ensure_ascii=True, allow_nan=True).encode('utf-8')


class DutManufacturerDeltaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = {name: (ROOT / name).read_bytes() for name in FILES}
        cls.data = json.loads(cls.raw[DELTA])
        cls.parent = DutControlCatalog()
        cls.old = {r['reference_id']: r for r in cls.parent.manufacturing_references()['additional_reviewed_references']}
        cls.new = {r['reference_id']: r for r in cls.data['records']}
        cls.catalog = module.DutManufacturerDeltaCatalog()

    @classmethod
    def tearDownClass(cls):
        for name, raw in cls.raw.items():
            if (ROOT / name).read_bytes() != raw:
                raise AssertionError('original fixed input changed')

    @contextmanager
    def inputs(self):
        local = ROOT / '.local' / 'DUT-CATALOG-DELTA-015'
        local.mkdir(parents=True, exist_ok=True)
        root = Path(tempfile.mkdtemp(prefix='test-inputs-', dir=local))
        self.assertTrue(root.resolve().is_relative_to(local.resolve()))
        for name, raw in self.raw.items():
            path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
        # Preserve tampered private fixtures and failure history.
        yield root

    @contextmanager
    def repinned(self, root, raw):
        (root / DELTA).write_bytes(raw)
        path, _, cap = module._DELTA_INPUT
        with patch.object(module, '_DELTA_INPUT', (path, hashlib.sha256(raw).hexdigest(), cap)):
            yield

    def error(self, call, code):
        with self.assertRaises(module.DutManufacturerDeltaError) as caught:
            call()
        exc = caught.exception
        self.assertIsInstance(exc, ValueError)
        self.assertEqual((exc.code, str(exc), exc.args), (code, code, (code,)))
        self.assertIsNone(exc.__cause__); self.assertIsNone(exc.__context__)
        self.assertNotIn('PRIVATE_CANARY', str(exc))

    def unavailable(self, root):
        self.error(lambda: module.DutManufacturerDeltaCatalog(root), 'dut_delta_unavailable')

    def bad_data(self, value):
        with self.inputs() as root, self.repinned(root, payload(value)):
            self.unavailable(root)

    def common(self, value, kind):
        self.assertEqual(value['schema_version'], 1)
        self.assertEqual(value['kind'], kind)
        self.assertEqual(value['catalog_state'], 'read_only_acquisition_delta')
        self.assertEqual(value['support_status'], 'not_assessed')
        for key in ('hardware_verified', 'source_code_executed', 'automatic_fallback_enabled'):
            self.assertIs(value[key], False)

    def test_summary_has_exact_ten_keys_and_new_counts_only(self):
        value = self.catalog.summary()
        self.assertEqual(set(value), set('schema_version kind catalog_state counts provenance support_status '
            'hardware_verified source_code_executed automatic_fallback_enabled source_reuse_publication_approved'.split()))
        self.common(value, 'dut_manufacturer_delta_summary')
        self.assertIs(value['source_reuse_publication_approved'], False)
        self.assertEqual(value['counts'], self.data['counts'])
        self.assertEqual(value['counts'], {'source_groups': 6, 'source_file_references': 22,
            'new_whole_repository_archives': 0, 'public_original_or_code_payload_files': 0})
        self.assertEqual(value['provenance'], self.data['provenance'])

    def test_records_preserve_all_six_original_wrappers_and_twenty_two_files(self):
        values = self.catalog.records()
        self.assertIs(type(values), list)
        self.assertEqual(values, self.data['records'])
        self.assertEqual(len(values), 6)
        self.assertEqual(sum(len(v['record']['files']) for v in values), 22)
        for value in values:
            self.assertEqual(set(value), {'reference_id', 'acquisition_scope',
                'selected_file_hashes_independently_verified', 'whole_repository_archive_acquired', 'record'})
            self.assertIs(value['selected_file_hashes_independently_verified'], True)
            self.assertIs(value['whole_repository_archive_acquired'], False)

    def test_every_old_reference_is_literal_and_only_explicit_six_have_deltas(self):
        found = 0
        for reference_id, original in self.old.items():
            value = self.catalog.reference(reference_id)
            self.assertEqual(set(value), set('schema_version kind catalog_state reference_id snapshot_reference '
                'acquisition_delta support_status hardware_verified source_code_executed automatic_fallback_enabled'.split()))
            self.common(value, 'dut_manufacturer_reference')
            self.assertEqual(value['reference_id'], reference_id)
            self.assertEqual(value['snapshot_reference'], original)
            self.assertEqual(value['acquisition_delta'], self.new.get(reference_id))
            self.assertIsNone(value['snapshot_reference']['repository_commit_pinned'])
            found += value['acquisition_delta'] is not None
        self.assertEqual((len(self.old), found), (9, 6))
        for reference_id in ('usb_type_c_reference', 'samsung_diagnostic_reference', 'qualcomm_sdk_distribution'):
            self.assertIsNone(self.catalog.reference(reference_id)['acquisition_delta'])

    def test_five_exact_commits_and_reference_source_mapping_do_not_backfill_snapshot(self):
        expected = {
            'qualcomm_diag': ('DUT-CONTROL-QCSUPER-001', '65e14771804cec8fe70ffb55552da9d85721f0eb'),
            'samsung_at_legacy': ('DUT-CONTROL-GALAXY-AT-001', 'a4247497cca7da96b9aaa7f533cff23e13ad6437'),
            'android_at_research': ('DUT-CONTROL-FICS-AT-001', '766a6b918289f5c2f4c3e1b82a65b964e4a0c8f5'),
            'qualcomm_ath10k_testmode': ('DUT-CONTROL-ATH10K-001', '17bb0e2f6c8043f70a693a5f3797471cbed354c8'),
            'samsung_legacy_muic': ('DUT-CONTROL-LEGACY-MUIC-001', '33ca16cbaf4bd144df3beef64283302c0aa35eed'),
        }
        for ref, (source_id, commit) in expected.items():
            value = self.catalog.reference(ref)
            record = value['acquisition_delta']['record']
            self.assertEqual((record['source_id'], record['repository_commit']), (source_id, commit))
            self.assertEqual(record['commit_url'], 'https://github.com/' + record['repository'] + '/commit/' + commit)
            self.assertIsNone(value['snapshot_reference']['repository_commit_pinned'])
            self.assertIs(value['snapshot_reference']['whole_repository_archive_acquired'], False)

    def test_qcsuper_license_reuse_is_exact_sparse_variant(self):
        record = self.catalog.reference('qualcomm_diag')['acquisition_delta']['record']
        self.assertEqual(record['declared_package_version'], '2.1.4')
        self.assertEqual(record['requires_python'], '>=3.7')
        license_file = record['files'][-1]
        self.assertEqual(set(license_file), {'primary_source_url', 'sha256', 'bytes',
            'public_payload_included', 'scope', 'new_distinct_payload_original'})
        self.assertNotIn('download_url', license_file)
        self.assertIs(license_file['new_distinct_payload_original'], False)
        for file in record['files'][:-1]:
            self.assertEqual(set(file), {'primary_source_url', 'download_url', 'sha256', 'bytes', 'public_payload_included'})
        self.assertEqual(record, self.new['qualcomm_diag']['record'])

    def test_etsi_pages_and_nonrepository_record_are_preserved(self):
        record = self.catalog.reference('etsi_at_reference')['acquisition_delta']['record']
        self.assertNotIn('repository_commit', record); self.assertNotIn('repository', record)
        self.assertEqual(record['physical_pages'], [119, 120, 152])
        self.assertEqual(record['printed_pages'], [118, 119, 151])
        self.assertEqual(record['title'], 'ETSI TS127007V18.8.0(2025-01)')
        self.assertEqual(len(record['files']), 1)
        self.assertEqual(record, self.new['etsi_at_reference']['record'])

    def test_rights_runtime_support_limits_and_original_capitalization_stay_separate(self):
        for wrapper in self.catalog.records():
            record = wrapper['record']
            self.assertIs(record['source_reuse_publication_approved'], False)
            self.assertEqual(record['device_or_Firmware_support'], 'not_assessed')
            self.assertNotIn('device_or_firmware_support', record)
            self.assertIs(record['runtime_or_physical_validation'], False)
            self.assertEqual(record['limits'], self.new[wrapper['reference_id']]['record']['limits'])
            self.assertTrue(record['limits'])
            for file in record['files']:
                self.assertIs(file['public_payload_included'], False)
        self.assertEqual(self.parent.summary()['counts']['source_units'], 30)
        self.assertEqual(self.parent.summary()['counts']['archive_files'], 32)

    def test_nested_outputs_are_detached_from_parent_delta_and_each_other(self):
        for call in (self.catalog.summary, self.catalog.records,
                     lambda: self.catalog.reference('qualcomm_diag'),
                     lambda: self.catalog.reference('usb_type_c_reference')):
            expected, changed = call(), call()
            def mutate(value):
                if type(value) is dict:
                    for v in list(value.values()): mutate(v)
                    value['PRIVATE_CANARY'] = True
                if type(value) is list:
                    for v in list(value): mutate(v)
                    value.append('PRIVATE_CANARY')
            mutate(changed)
            self.assertEqual(call(), expected)
        self.assertEqual({r['reference_id']: r for r in self.parent.manufacturing_references()[
            'additional_reviewed_references']}, self.old)

    def test_invalid_id_types_aliases_urls_and_paths_are_rejected(self):
        for value in (None, 1, True, b'qualcomm_diag', [], {}, '', 'QCSUPER', 'Qualcomm_diag',
                      ' qualcomm_diag', 'qualcomm_diag ', 'DUT-CONTROL-QCSUPER-001',
                      '../PRIVATE_CANARY', 'C:\\PRIVATE_CANARY', 'https://example.com',
                      'a' * 97, '가상', '\ud800'):
            self.error(lambda: self.catalog.reference(value), 'dut_delta_invalid_query')

    def test_unknown_well_formed_ids_are_not_found(self):
        for value in ('unknown', 'a' * 96, 'qualcomm_diag_other'):
            self.error(lambda: self.catalog.reference(value), 'dut_delta_item_not_found')

    def test_exact_parent_composition_and_only_three_fixed_reads(self):
        opened = []
        original = Path.open
        def inspect(path, *args, **kwargs):
            self.assertIn(path.resolve(), {(ROOT / f).resolve() for f in FILES})
            self.assertEqual(args, ('rb',)); opened.append(path.resolve())
            return original(path, *args, **kwargs)
        with patch.object(module, 'DutControlCatalog', wraps=DutControlCatalog) as parent, \
             patch.object(Path, 'open', inspect):
            catalog = module.DutManufacturerDeltaCatalog()
            parent.assert_called_once_with(ROOT)
            self.assertEqual(len(opened), 3)
            for reference_id in self.old:
                catalog.reference(reference_id)
            catalog.records(); catalog.summary()
            self.assertEqual(len(opened), 3)

    def test_all_queries_work_after_three_files_removed_without_parent_or_io(self):
        with self.inputs() as root:
            catalog = module.DutManufacturerDeltaCatalog(root)
            expected = {key: catalog.reference(key) for key in self.old}
            for i, name in enumerate(FILES):
                (root / name).rename(root / ('retained-original-' + str(i) + '.json'))
            with ExitStack() as stack:
                for name in ('open', 'stat', 'resolve'):
                    stack.enter_context(patch.object(Path, name, side_effect=AssertionError('query I/O')))
                stack.enter_context(patch.object(module, 'DutControlCatalog', side_effect=AssertionError('parent reopen')))
                for key, value in expected.items(): self.assertEqual(catalog.reference(key), value)
                self.assertEqual(catalog.records(), self.data['records'])
                self.assertEqual(catalog.summary()['counts'], self.data['counts'])
            self.unavailable(root)

    def test_parent_failures_and_corrupt_parent_context_are_sanitized(self):
        for failure in (ValueError('PRIVATE_CANARY'), OSError('PRIVATE_CANARY C:/secret')):
            with patch.object(module, 'DutControlCatalog', side_effect=failure):
                self.unavailable(ROOT)
        changed = self.parent.summary()
        changed['provenance']['main_prompt_v5_sha256'] = 'f' * 64
        with patch.object(DutControlCatalog, 'summary', return_value=changed):
            self.unavailable(ROOT)
        old = self.parent.manufacturing_references()
        old['additional_reviewed_references'][0] = old['additional_reviewed_references'][1]
        with patch.object(DutControlCatalog, 'manufacturing_references', return_value=old):
            self.unavailable(ROOT)

    def test_missing_and_pin_or_lf_drift_in_any_input_never_fallback(self):
        for name in FILES:
            for raw in (self.raw[name] + b' ', self.raw[name].replace(b'\n', b'\r\n')):
                with self.inputs() as root:
                    (root / name).write_bytes(raw); self.unavailable(root)
        with self.inputs() as root:
            (root / DELTA).rename(root / 'retained-delta.json')
            self.unavailable(root)

    def test_read_and_path_errors_have_no_private_cause_or_context(self):
        original = Path.open
        def fail(path, *args, **kwargs):
            if path.name == 'dut_manufacturer_delta.json':
                raise OSError('PRIVATE_CANARY C:/secret')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'open', fail): self.unavailable(ROOT)
        class BadRoot:
            def __fspath__(self): raise RuntimeError('PRIVATE_CANARY')
        self.unavailable(BadRoot())

    def test_size_limit_and_stale_stat_still_use_bounded_read(self):
        with self.inputs() as root:
            target = root / DELTA
            target.write_bytes(b'x' * (65536 + 10))
            self.unavailable(root)
            old_stat, old_open, sizes = Path.stat, Path.open, []
            def stale(path, *args, **kwargs):
                result = old_stat(path, *args, **kwargs)
                if path == target:
                    fields = list(result); fields[6] = 1; return os.stat_result(fields)
                return result
            class Read:
                def __init__(self, stream): self.stream = stream
                def __enter__(self): return self
                def __exit__(self, *args): self.stream.close()
                def read(self, size): sizes.append(size); return self.stream.read(size)
            def opened(path, *args, **kwargs):
                stream = old_open(path, *args, **kwargs)
                return Read(stream) if path == target else stream
            with patch.object(Path, 'stat', stale), patch.object(Path, 'open', opened):
                self.unavailable(root)
            self.assertEqual(sizes, [65537])

    def test_resolved_delta_outside_root_is_rejected(self):
        with self.inputs() as root:
            old_resolve = Path.resolve
            def resolved(path, *args, **kwargs):
                return ROOT.parent / 'PRIVATE_CANARY.json' if path == root / DELTA else old_resolve(path, *args, **kwargs)
            with patch.object(Path, 'resolve', resolved): self.unavailable(root)

    def test_duplicate_utf8_nonfinite_depth_and_unicode_fail_even_if_repinned(self):
        duplicate = b'{"schema_version":1,' + self.raw[DELTA].lstrip()[1:]
        for raw in (duplicate, b'\xff', b'{"x":NaN}', b'{"x":1e999}', b'null', b'[]',
                    b'[' * 1100 + b'0' + b']' * 1100):
            with self.inputs() as root, self.repinned(root, raw): self.unavailable(root)
        value = deepcopy(self.data); value['records'][0]['record']['scope'] = '\ud800'; self.bad_data(value)

    def test_exact_provenance_parent_and_count_types_are_validated(self):
        changes = [
            lambda x: x.update(schema_version=True),
            lambda x: x['counts'].update(new_whole_repository_archives=False),
            lambda x: x['counts'].update(source_file_references=23),
            lambda x: x['provenance'].update(public_collection_commit='f' * 40),
            lambda x: x['provenance'].update(public_collection_sha256='f' * 64),
            lambda x: x['provenance'].update(main_prompt_sha256='f' * 64),
            lambda x: x['provenance']['parent_catalog_sha256'].update({'dut_sources.json': 'f' * 64}),
            lambda x: x.update(source_reuse_publication_approved=True),
            lambda x: x.update(hardware_verified=0),
            lambda x: x.update(source_code_executed=True),
            lambda x: x.update(automatic_fallback_enabled=True),
            lambda x: x.update(raw_path='C:/PRIVATE_CANARY'),
        ]
        for i, change in enumerate(changes):
            with self.subTest(case=i):
                value = deepcopy(self.data); change(value); self.bad_data(value)

    def test_wrapper_ids_flags_and_literal_source_relationships_are_validated(self):
        changes = [
            lambda x: x['records'].pop(),
            lambda x: x['records'][1].update(reference_id=x['records'][0]['reference_id']),
            lambda x: x['records'][0].update(reference_id='usb_type_c_reference'),
            lambda x: x['records'][0].update(selected_file_hashes_independently_verified=1),
            lambda x: x['records'][0].update(whole_repository_archive_acquired=True),
            lambda x: x['records'][0]['record'].update(source_id='DUT-CONTROL-UNKNOWN-001'),
            lambda x: x['records'][0]['record'].update(repository_commit='f' * 40),
            lambda x: x['records'][0]['record'].update(commit_url='https://example.com'),
            lambda x: x['records'][0]['record'].update(device_or_Firmware_support='supported'),
            lambda x: x['records'][0]['record'].update(runtime_or_physical_validation=True),
            lambda x: x['records'][0]['record'].update(source_reuse_publication_approved=True),
            lambda x: x['records'][1]['record'].update(declared_package_version='2.1.4'),
            lambda x: x['records'][-1]['record'].update(physical_pages=[True, 120, 152]),
            lambda x: x['records'][-1]['record'].update(printed_pages=[119, 120, 152]),
        ]
        for i, change in enumerate(changes):
            with self.subTest(case=i):
                value = deepcopy(self.data); change(value); self.bad_data(value)

    def test_file_metadata_and_sparse_license_are_strict_without_filling_missing_fields(self):
        changes = [
            lambda x: x['records'][0]['record']['files'].pop(),
            lambda x: x['records'][0]['record']['files'][0].update(bytes=True),
            lambda x: x['records'][0]['record']['files'][0].update(sha256='f' * 63),
            lambda x: x['records'][0]['record']['files'][0].update(public_payload_included=True),
            lambda x: x['records'][0]['record']['files'][0].update(download_url='file:///PRIVATE_CANARY'),
            lambda x: x['records'][0]['record']['files'][1].update(
                primary_source_url=x['records'][0]['record']['files'][0]['primary_source_url']),
            lambda x: x['records'][0]['record']['files'][-1].update(download_url='https://example.com'),
            lambda x: x['records'][0]['record']['files'][-1].pop('scope'),
            lambda x: x['records'][0]['record']['files'][-1].update(new_distinct_payload_original=True),
            lambda x: x['records'][-1]['record']['files'][0].update(primary_source_url='https://example.com'),
        ]
        for i, change in enumerate(changes):
            with self.subTest(case=i):
                value = deepcopy(self.data); change(value); self.bad_data(value)

    def test_no_raw_source_database_network_tool_or_process_access(self):
        with ExitStack() as stack:
            for target in ('sqlite3.connect', 'socket.create_connection', 'subprocess.run',
                           'subprocess.Popen', 'importlib.import_module'):
                stack.enter_context(patch(target, side_effect=AssertionError('unexpected execution')))
            catalog = module.DutManufacturerDeltaCatalog()
            self.assertEqual(len(catalog.records()), 6)
            self.assertEqual(len(catalog.reference('qualcomm_diag')['acquisition_delta']['record']['files']), 7)


if __name__ == '__main__':
    unittest.main()

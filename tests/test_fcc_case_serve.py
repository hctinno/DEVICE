"""040 CLI behavior with genuine synthetic037 inputs; fault doubles are explicit."""
from copy import deepcopy
import errno
import hashlib
import http.client
import importlib
import importlib.util
from io import StringIO
import json
import os
from pathlib import Path
import queue
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock

from pypdf._page import PageObject

from labflow import control_packet_prepare as native
from labflow import fcc_case_catalog_host as host
from labflow import fcc_report_cases as cases
from labflow import ui_server
from tests.test_fcc_report_cases import fixture

serve = (importlib.import_module('labflow.fcc_case_serve')
         if importlib.util.find_spec('labflow.fcc_case_serve') else None)
DB_NAMES = ('lab.sqlite3', 'lab.sqlite3-wal', 'lab.sqlite3-shm', 'lab.sqlite3-journal')
FLAGS = ('authority_or_rights_verified', 'hardware_verified', 'normative_compliance_verified',
         'currentness_verified', 'execution_authorized')
HOST_CODES = ('fcc_case_host_invalid_argument', 'fcc_case_host_path_invalid', 'fcc_case_host_unavailable',
              'fcc_case_host_pin_mismatch', 'fcc_case_host_input_changed', 'fcc_case_host_backend_unavailable')
CASE_CODES = ('fcc_case_invalid_packet', 'fcc_case_invalid_sources', 'fcc_case_limit_exceeded',
              'fcc_case_pdf_invalid', 'fcc_case_extraction_unavailable', 'fcc_case_invalid_evidence',
              'fcc_case_invalid_query', 'fcc_case_not_found', 'fcc_case_invalid_intake')


def encoded(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def synthetic_inputs(base, *, empty=False):
    inputs = base / 'inputs'; inputs.mkdir()
    state = base / 'state'; state.mkdir()
    packet, pdfs, _ = fixture()
    if empty:
        packet['documents'] = []; packet['cases'] = []; pdfs = {}
    scope = {'schema_version': 1, 'sources': {sha: {'pages': [1], 'mode': 'accessibility',
             'basis_id': 'SYNTHETIC-SERVE040', 'basis_sha256': 'e' * 64} for sha in pdfs}}
    files = []
    for name, value in [('packet.json', packet), ('scope.json', scope)]:
        path = inputs / name; path.write_bytes(encoded(value)); files.append(path)
    manifest = {'request_id': 'DEV-HCT-FCC-CORPUS-012', 'revision': 'SYNTHETIC-SERVE040',
                'files': [{'path': p.name, 'sha256': digest(p.read_bytes()), 'bytes': len(p.read_bytes())} for p in files]}
    manifest_file = inputs / 'manifest.json'; manifest_file.write_bytes(encoded(manifest))
    def descriptor(path):
        raw = path.read_bytes()
        return {'path': str(path), 'sha256': digest(raw), 'bytes': len(raw)}
    sources = []
    for index, raw in enumerate(pdfs.values()):
        path = inputs / ('synthetic-' + str(index) + '.pdf'); path.write_bytes(raw); sources.append(descriptor(path))
    config = {'schema_version': 1, 'kind': 'fcc_case_catalog_host_input',
              'manifest': descriptor(manifest_file), 'packet': descriptor(files[0]),
              'page_scope': descriptor(files[1]), 'packet_path': 'packet.json',
              'page_scope_path': 'scope.json', 'pdf_sources': sources}
    path = base / 'config.json'; path.write_bytes(encoded(config))
    return path, digest(path.read_bytes()), state


class FccCaseServeTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(serve, '040 explicit catalog server CLI is absent')
        self.assertEqual(os.name, 'nt', 'Windows native state path execution contract')
        parent = Path(__file__).resolve().parents[1] / '.local' / 's040'
        parent.mkdir(parents=True, exist_ok=True)
        temp = tempfile.TemporaryDirectory(dir=parent); self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.config, self.pin, self.state = synthetic_inputs(self.base)
        self.args = ['--config', str(self.config), '--config-sha256', self.pin,
                     '--state-dir', str(self.state), '--port', '0']
        self.cached = None

    def result(self):
        if self.cached is None:
            self.cached = host.load_fcc_case_catalog(self.config, expected_config_sha256=self.pin)
        return self.cached

    def fail_before_load(self, args, code='fcc_case_server_invalid_argument', status=2):
        out, err = StringIO(), StringIO()
        with mock.patch.object(host, 'load_fcc_case_catalog', side_effect=AssertionError('037 called')) as loaded, \
                mock.patch.object(ui_server, 'create_server', side_effect=AssertionError('bound')) as created, \
                mock.patch('sqlite3.connect', side_effect=AssertionError('database')), \
                mock.patch('labflow.store.Store', side_effect=AssertionError('Store')), \
                mock.patch.object(sys, 'stdout', out), mock.patch.object(sys, 'stderr', err):
            actual = serve.main(args)
        self.assertEqual((actual, out.getvalue(), json.loads(err.getvalue())),
                         (status, '', {'error': {'code': code}}))
        loaded.assert_not_called(); created.assert_not_called()
        self.assertNotIn(str(self.base), err.getvalue())

    def run_main(self, *, result=None, loader_effect=None, serve_effect=KeyboardInterrupt,
                 output=None, close_error=False):
        if result is None and loader_effect is None:
            result = self.result()
        out, err, servers = output if output is not None else StringIO(), StringIO(), []
        original = ui_server.create_server
        def build(workspace, **kwargs):
            self.assertEqual(workspace, self.state)
            self.assertEqual(kwargs['host'], '127.0.0.1'); self.assertEqual(kwargs['port'], 0)
            server = original(workspace, **kwargs); servers.append(server)
            server.serve_forever = mock.Mock(side_effect=serve_effect)
            server.shutdown = mock.Mock(side_effect=AssertionError('same-thread shutdown'))
            closer = server.server_close
            def close():
                closer()
                if close_error:
                    raise OSError('PRIVATE cleanup ' + str(self.base))
            server.server_close = mock.Mock(side_effect=close)
            return server
        with mock.patch.object(host, 'load_fcc_case_catalog', side_effect=loader_effect, return_value=result) as loaded, \
                mock.patch.object(ui_server, 'create_server', side_effect=build) as created, \
                mock.patch.object(sys, 'stdout', out), mock.patch.object(sys, 'stderr', err):
            status = serve.main(self.args)
        for server in servers:
            server.server_close.assert_called_once(); server.shutdown.assert_not_called()
            self.assertEqual(server.fileno(), -1)
        return status, out, err.getvalue(), servers, loaded, created

    def snapshot(self):
        return {p.relative_to(self.base).as_posix():
                (p.read_bytes(), p.stat().st_dev, p.stat().st_ino, p.stat().st_size, p.stat().st_mtime_ns, p.stat().st_mode)
                for p in self.base.rglob('*') if p.is_file()}

    def test_missing_duplicate_unknown_abbreviation_equal_and_atfile_are_rejected_before037(self):
        invalid = [[], self.args[:-2], self.args + ['--port', '0'], self.args + ['--host', '127.0.0.1'],
                   ['--conf', *self.args[1:]], ['--config=' + str(self.config), *self.args[2:]],
                   ['@' + str(self.config)], self.args + ['--help'], ['--help', '--help']]
        for args in invalid:
            with self.subTest(args=args): self.fail_before_load(args)

    def test_non_plain_argv_values_never_invoke_callbacks(self):
        class Hostile(str):
            def __str__(self): raise AssertionError('str callback')
        for args in [False, ' '.join(self.args), {k: 'x' for k in self.args[::2]},
                     [*self.args[:-1], False], [Hostile('--config'), *self.args[1:]]]:
            self.fail_before_load(args)

    def test_blank_control_relative_config_and_invalid_pin_are_rejected_before037(self):
        for index, values in [(1, ['', ' ', ' ' + str(self.config), str(self.config) + ' ',
                                    'config.json', 'C:config.json', r'\\server\share\x.json', r'\\?\C:\x.json',
                                    str(self.config) + '\n', str(self.base / 'x.txt')]),
                              (3, ['', 'A' * 64, 'f' * 63, ' ' + self.pin])]:
            for value in values:
                args = self.args[:]; args[index] = value; self.fail_before_load(args)

    def test_port_ascii_canonical_range_has_no_fallback(self):
        for value in ['', '-1', '+1', '00', '01', '65536', '1.0', ' 0', '0 ', '１２', '٠', '1\n']:
            args = self.args[:]; args[-1] = value; self.fail_before_load(args)

    def test_high_valid_port_is_forwarded_only_to_a_no_bind_fault_double(self):
        self.args[-1] = '65535'
        with mock.patch.object(host, 'load_fcc_case_catalog', return_value=self.result()), \
                mock.patch.object(ui_server, 'create_server', side_effect=OSError(errno.EADDRINUSE, 'PRIVATE')) as created, \
                mock.patch.object(sys, 'stdout', StringIO()), mock.patch.object(sys, 'stderr', StringIO()) as err:
            self.assertEqual(serve.main(self.args), 1)
        self.assertEqual(created.call_args.kwargs['port'], 65535)
        self.assertEqual(json.loads(err.getvalue()), {'error': {'code': 'fcc_case_server_bind_failed'}})

    def test_help_is_static_without_state_or_loader_or_server(self):
        with mock.patch.object(host, 'load_fcc_case_catalog', side_effect=AssertionError('037')), \
                mock.patch.object(native, '_WindowsIO', side_effect=AssertionError('native')), \
                mock.patch.object(ui_server, 'create_server', side_effect=AssertionError('bind')), \
                mock.patch.object(sys, 'stdout', StringIO()) as out, mock.patch.object(sys, 'stderr', StringIO()) as err:
            self.assertEqual(serve.main(['--help']), 0)
        self.assertIn('--config-sha256', out.getvalue()); self.assertIn('--state-dir', out.getvalue())
        self.assertEqual(err.getvalue(), '')

    def test_all_four_database_entries_including_directory_are_rejected_without_content_reads(self):
        for name in DB_NAMES:
            path = self.state / name; path.write_bytes(b'PRIVATE DB bytes')
            with mock.patch.object(os, 'read', side_effect=AssertionError('content read')):
                self.fail_before_load(self.args, 'fcc_case_server_state_invalid')
            path.unlink()
        directory = self.state / 'lab.sqlite3'; directory.mkdir()
        self.fail_before_load(self.args, 'fcc_case_server_state_invalid')

    def test_missing_file_relative_unc_device_and_bad_segment_state_are_rejected(self):
        for value in [str(self.base / 'missing'), str(self.config), 'state', 'C:state', r'\\server\share\state',
                      r'\\?\C:\state', str(self.state / '..' / 'state'), str(self.state / 'NUL'),
                      str(self.state) + '.', str(self.state) + ' ']:
            args = self.args[:]; args[5] = value
            self.fail_before_load(args, 'fcc_case_server_state_invalid')

    def test_final_and_ancestor_junctions_are_rejected_before037(self):
        target = self.base / 'target'; target.mkdir(); (target / 'child').mkdir()
        junction = self.base / 'junction'
        subprocess.run(['cmd', '/c', 'mklink', '/J', str(junction), str(target)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
        for path in [junction, junction / 'child']:
            args = self.args[:]; args[5] = str(path)
            self.fail_before_load(args, 'fcc_case_server_state_invalid')

    def test_mapped_remote_drive_is_rejected_by_native_drive_type_without_scanning(self):
        backend = native._WindowsIO; opened = []
        def remote():
            instance = backend(); opened.append(instance)
            instance.kernel.GetDriveTypeW = lambda _: 4
            return instance
        with mock.patch.object(native, '_WindowsIO', side_effect=remote):
            self.fail_before_load(self.args, 'fcc_case_server_state_invalid')
        self.assertTrue(opened); self.assertTrue(all(not b.held for b in opened))

    def test_database_created_during_preparation_is_input_changed_before_bind(self):
        result = self.result()
        def changed(*args, **kwargs):
            (self.state / 'lab.sqlite3-wal').write_bytes(b'SYNTHETIC new entry'); return result
        status, out, err, servers, loaded, created = self.run_main(loader_effect=changed)
        self.assertEqual((status, out.getvalue(), json.loads(err)),
                         (1, '', {'error': {'code': 'fcc_case_server_input_changed'}}))
        created.assert_not_called(); self.assertEqual(servers, []); loaded.assert_called_once()

    def test_state_replaced_with_new_directory_is_input_changed_before_bind(self):
        result = self.result()
        def changed(*args, **kwargs):
            self.state.rename(self.base / 'old-state'); self.state.mkdir(); return result
        status, _, err, _, _, created = self.run_main(loader_effect=changed)
        self.assertEqual((status, json.loads(err)), (1, {'error': {'code': 'fcc_case_server_input_changed'}}))
        created.assert_not_called()

    def test_removed_state_and_new_junction_during_preparation_are_input_changed(self):
        result = self.result()
        def changed(*args, **kwargs):
            self.state.rename(self.base / 'old-state'); return result
        status, _, err, _, _, created = self.run_main(loader_effect=changed)
        self.assertEqual((status, json.loads(err)), (1, {'error': {'code': 'fcc_case_server_input_changed'}}))
        created.assert_not_called()
        self.state.mkdir()
        target = self.base / 'junction-target'; target.mkdir()
        def junction(*args, **kwargs):
            self.state.rmdir()
            subprocess.run(['cmd', '/c', 'mklink', '/J', str(self.state), str(target)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
            return result
        status, _, err, _, _, created = self.run_main(loader_effect=junction)
        self.assertEqual((status, json.loads(err)), (1, {'error': {'code': 'fcc_case_server_input_changed'}}))
        created.assert_not_called()

    def test_037_six_and_parent_nine_codes_are_preserved_with_no_raw_context(self):
        for cls, codes in [(host.FccCaseCatalogHostError, HOST_CODES), (cases.FccReportCaseError, CASE_CODES)]:
            for code in codes:
                error = cls(code); error.args = ('PRIVATE ' + str(self.base),)
                status, out, err, _, loaded, created = self.run_main(loader_effect=error)
                self.assertEqual((status, out.getvalue(), json.loads(err)), (1, '', {'error': {'code': code}}))
                self.assertNotIn('PRIVATE', err); created.assert_not_called(); loaded.assert_called_once()

    def test_unknown_or_hostile_exception_code_is_unavailable_without_string_callbacks(self):
        class Hostile:
            def __str__(self): raise AssertionError('str')
            def __hash__(self): raise AssertionError('hash')
        errors = [OSError('PRIVATE ' + str(self.base)), host.FccCaseCatalogHostError('fcc_case_host_unavailable')]
        errors[1].code = Hostile()
        for error in errors:
            status, out, err, _, _, created = self.run_main(loader_effect=error)
            self.assertEqual((status, out.getvalue(), json.loads(err)),
                             (1, '', {'error': {'code': 'fcc_case_server_unavailable'}}))
            created.assert_not_called()

    def test_none_or_nonexact_catalog_cannot_become_an_unconfigured_server(self):
        receipt = self.result()[1]
        for catalog in [None, object()]:
            status, out, err, _, _, created = self.run_main(result=(catalog, receipt))
            self.assertEqual((status, out.getvalue(), json.loads(err)),
                             (1, '', {'error': {'code': 'fcc_case_server_unavailable'}}))
            created.assert_not_called()

    def test_ready_is_exact_compact_detached_metadata_and_not_source_text_or_path(self):
        catalog, receipt = self.result(); before = deepcopy(receipt)
        status, out, err, servers, loaded, created = self.run_main()
        raw = out.getvalue().encode('utf-8'); ready = json.loads(raw)
        self.assertEqual((status, err), (0, ''))
        self.assertEqual(set(ready), {'schema_version', 'kind', 'url', 'config_sha256', 'catalog_state',
                                     'state_mode', 'host_receipt', 'verification'})
        self.assertEqual(raw, encoded(ready) + b'\n')
        self.assertEqual(ready['kind'], 'fcc_case_catalog_server_ready')
        self.assertEqual(ready['config_sha256'], self.pin)
        self.assertEqual((ready['catalog_state'], ready['state_mode']), ('configured', 'no_store_at_startup'))
        self.assertEqual(ready['host_receipt'], before); self.assertEqual(receipt, before)
        self.assertEqual(ready['verification'], dict.fromkeys(FLAGS, False))
        self.assertNotIn(str(self.base), out.getvalue()); self.assertNotIn('PRIVATE-SYNTHETIC', out.getvalue())
        self.assertEqual(ready['url'], 'http://127.0.0.1:' + str(servers[0].server_port) + '/fcc-cases/')
        loaded.assert_called_once_with(self.config, expected_config_sha256=self.pin)
        self.assertIs(created.call_args.kwargs['fcc_case_catalog'], catalog)

    def test_real_config_pin_mismatch_fails_before_bind_without_none_fallback(self):
        self.args[3] = '0' * 64
        out, err = StringIO(), StringIO()
        with mock.patch.object(host, 'load_fcc_case_catalog', wraps=host.load_fcc_case_catalog) as loaded, \
                mock.patch.object(ui_server, 'create_server', side_effect=AssertionError('bind')) as created, \
                mock.patch.object(sys, 'stdout', out), mock.patch.object(sys, 'stderr', err):
            status = serve.main(self.args)
        self.assertEqual((status, out.getvalue(), json.loads(err.getvalue())),
                         (1, '', {'error': {'code': 'fcc_case_host_pin_mismatch'}}))
        loaded.assert_called_once(); created.assert_not_called()

    def test_state_path_with_internal_space_is_passed_without_adding_a_subdirectory(self):
        self.state.rename(self.base / 'state with space'); self.state = self.base / 'state with space'
        self.args[5] = str(self.state)
        status, _, err, _, _, created = self.run_main()
        self.assertEqual((status, err), (0, ''))
        self.assertEqual(created.call_args.args, (self.state,))

    def test_reordered_options_and_main_none_use_explicit_values(self):
        self.args = self.args[4:] + self.args[:4]
        status, _, err, _, _, _ = self.run_main()
        self.assertEqual((status, err), (0, ''))
        with mock.patch.object(sys, 'argv', ['fcc_case_serve', '--help']), \
                mock.patch.object(sys, 'stdout', StringIO()), mock.patch.object(sys, 'stderr', StringIO()):
            self.assertEqual(serve.main(), 0)

    def test_real_configured_empty_is_distinct_from_none(self):
        empty_base = self.base / 'empty'; empty_base.mkdir()
        self.config, self.pin, self.state = synthetic_inputs(empty_base, empty=True)
        self.args = ['--config', str(self.config), '--config-sha256', self.pin, '--state-dir', str(self.state), '--port', '0']
        status, out, err, _, _, _ = self.run_main()
        self.assertEqual((status, err, json.loads(out.getvalue())['catalog_state']), (0, '', 'configured_empty'))

    def test_invalid_ready_receipt_closes_bound_socket_without_serve(self):
        catalog, receipt = self.result()
        invalid = [{}, {**receipt, 'extra': True}, {**receipt, 'config_sha256': '0' * 64},
                   {**receipt, 'schema_version': True}, {**receipt, 'verification': {**receipt['verification'], FLAGS[0]: True}},
                   {**receipt, 'verification': {**receipt['verification'], FLAGS[0]: 0}},
                   {**receipt, 'construction': {**receipt['construction'], 'case_count': 0}}]
        for value in invalid:
            status, out, err, servers, _, _ = self.run_main(result=(catalog, value))
            self.assertEqual((status, out.getvalue(), json.loads(err)),
                             (1, '', {'error': {'code': 'fcc_case_server_output_failed'}}))
            self.assertEqual(len(servers), 1); servers[0].serve_forever.assert_not_called()

    def test_parent_receipt_8mib_budget_is_not_reduced_by_wrapper_metadata_double(self):
        catalog, receipt = self.result(); value = deepcopy(receipt)
        # This shapes the serializer budget only; it is not a new genuine037 input acceptance claim.
        provenance = value['metadata_preparation']['provenance']['consumed_files'][0]
        key = 'path'
        self.assertIn(key, provenance)
        old = provenance[key]; provenance[key] = ''
        provenance[key] = 'M' * (8 * 1024 * 1024 - len(encoded(value)))
        self.assertEqual(len(encoded(value)), 8 * 1024 * 1024)
        status, out, err, _, _, _ = self.run_main(result=(catalog, value))
        self.assertEqual((status, err), (0, ''))
        self.assertGreater(len(out.getvalue().encode('utf-8')), 8 * 1024 * 1024)
        self.assertLessEqual(len(out.getvalue().encode('utf-8')), 8 * 1024 * 1024 + 1024)
        provenance[key] += 'M'
        status, _, err, servers, _, _ = self.run_main(result=(catalog, value))
        self.assertEqual((status, json.loads(err)), (1, {'error': {'code': 'fcc_case_server_output_failed'}}))
        servers[0].serve_forever.assert_not_called(); self.assertNotEqual(old, provenance[key])

    def test_ready_write_flush_and_short_write_fail_without_starting_loop(self):
        class Failing(StringIO):
            def write(self, value): raise OSError('PRIVATE write')
        class FlushFailing(StringIO):
            def flush(self): raise OSError('PRIVATE flush')
        class Short(StringIO):
            def write(self, value): return super().write(value[:-1])
        for output in [Failing(), FlushFailing(), Short()]:
            status, _, err, servers, _, _ = self.run_main(output=output)
            self.assertEqual((status, json.loads(err)), (1, {'error': {'code': 'fcc_case_server_output_failed'}}))
            servers[0].serve_forever.assert_not_called()

    def test_help_output_failure_and_unwritable_error_stream_return_without_traceback(self):
        class Closed(StringIO):
            def write(self, value): raise OSError('PRIVATE write')
        with mock.patch.object(sys, 'stdout', Closed()), mock.patch.object(sys, 'stderr', StringIO()) as err:
            self.assertEqual(serve.main(['--help']), 1)
        self.assertEqual(json.loads(err.getvalue()), {'error': {'code': 'fcc_case_server_output_failed'}})
        with mock.patch.object(sys, 'stdout', StringIO()), mock.patch.object(sys, 'stderr', Closed()):
            self.assertEqual(serve.main([]), 2)

    def test_bind_address_in_use_fault_double_is_once_and_has_no_ready_or_retry(self):
        with mock.patch.object(host, 'load_fcc_case_catalog', return_value=self.result()) as loaded, \
                mock.patch.object(ui_server.ThreadingHTTPServer, 'server_bind', side_effect=OSError(errno.EADDRINUSE, 'PRIVATE')) as bound, \
                mock.patch.object(sys, 'stdout', StringIO()) as out, mock.patch.object(sys, 'stderr', StringIO()) as err:
            self.assertEqual(serve.main(self.args), 1)
        self.assertEqual((out.getvalue(), json.loads(err.getvalue())), ('', {'error': {'code': 'fcc_case_server_bind_failed'}}))
        bound.assert_called_once(); loaded.assert_called_once()

    def test_serve_failure_closes_socket_and_first_output_failure_survives_close_failure(self):
        status, _, err, servers, _, _ = self.run_main(serve_effect=OSError('PRIVATE serve'))
        self.assertEqual((status, json.loads(err)), (1, {'error': {'code': 'fcc_case_server_unavailable'}}))
        servers[0].serve_forever.assert_called_once()
        class Failing(StringIO):
            def write(self, value): raise OSError('PRIVATE output')
        status, _, err, _, _, _ = self.run_main(output=Failing(), close_error=True)
        self.assertEqual((status, json.loads(err)), (1, {'error': {'code': 'fcc_case_server_output_failed'}}))

    def test_interrupt_is_zero_with_owned_socket_closed_and_no_same_thread_shutdown(self):
        status, _, err, servers, _, _ = self.run_main()
        self.assertEqual((status, err, len(servers)), (0, '', 1))
        status, _, err, _, _, _ = self.run_main(close_error=True)
        self.assertEqual((status, json.loads(err)), (1, {'error': {'code': 'fcc_case_server_unavailable'}}))

    def test_real_loader_real_HTTP_has_released_pins_and_no_request_input_or_DB_IO(self):
        before = self.snapshot(); observed = []; servers = []; faults = []
        original_create, original_load = ui_server.create_server, host.load_fcc_case_catalog
        source = next((self.base / 'inputs').glob('*.pdf'))
        identity = source.stat().st_dev, source.stat().st_ino
        hash_read_bytes, text_pages, constructors = [], [], []
        original_read, original_extract, original_init = os.read, PageObject.extract_text, cases.FccReportCaseCatalog.__init__
        def read(descriptor, count):
            info = os.fstat(descriptor); raw = original_read(descriptor, count)
            if (info.st_dev, info.st_ino) == identity and raw: hash_read_bytes.append(len(raw))
            return raw
        def extract(page, *args, **kwargs):
            text_pages.append(page.pdf.get_page_number(page) + 1)
            return original_extract(page, *args, **kwargs)
        def construct(instance, *args, **kwargs):
            constructors.append(True); return original_init(instance, *args, **kwargs)
        def load(*args, **kwargs):
            result = original_load(*args, **kwargs); observed.append('loaded'); return result
        def build(workspace, **kwargs):
            self.assertEqual(observed, ['loaded']); self.assertEqual(kwargs['port'], 0)
            # Genuine037 has returned: every input file is now renameable and can be restored.
            for path in [self.config, *sorted((self.base / 'inputs').iterdir()), self.base / 'inputs', self.state]:
                moved = path.with_name(path.name + '.moved'); path.rename(moved); moved.rename(path)
            server = original_create(workspace, **kwargs); servers.append(server)
            original_serve = server.serve_forever
            def running():
                def query_all():
                    try:
                        for method, target, expected in [('GET', '/fcc-cases/', 200), ('HEAD', '/fcc-cases/', 200),
                            ('GET', '/api/fcc-cases/summary', 200), ('HEAD', '/api/fcc-cases/summary', 200),
                            ('GET', '/api/fcc-cases/cases/CASE-A', 200), ('GET', '/api/intakes', 503)]:
                            conn = http.client.HTTPConnection(*server.server_address, timeout=3)
                            try:
                                conn.request(method, target); response = conn.getresponse(); raw = response.read()
                                self.assertEqual(response.status, expected)
                                if method == 'HEAD': self.assertEqual(raw, b'')
                                if target == '/api/intakes': self.assertEqual(json.loads(raw), {'error': {'code': 'store_missing'}})
                            finally: conn.close()
                            observed.append(method + ':' + target)
                    except BaseException as error:
                        faults.append(error)
                    finally: server.shutdown()  # Different thread from the real serve loop.
                original_open = Path.open
                inputs = {self.config, *list((self.base / 'inputs').iterdir())}
                def guarded_open(path, *args, **kwargs):
                    if path in inputs: raise AssertionError('request input Path.open')
                    return original_open(path, *args, **kwargs)
                with mock.patch.object(native._WindowsIO, 'open_read', side_effect=AssertionError('request source IO')), \
                        mock.patch.object(Path, 'open', new=guarded_open), \
                        mock.patch.object(os, 'read', side_effect=AssertionError('request descriptor read')), \
                        mock.patch('pypdf.PdfReader', side_effect=AssertionError('request parser')), \
                        mock.patch('sqlite3.connect', side_effect=AssertionError('request DB')), \
                        mock.patch('labflow.store.Store', side_effect=AssertionError('Store')):
                    worker = threading.Thread(target=query_all, daemon=True); worker.start()
                    original_serve(poll_interval=0.02); worker.join(5); self.assertFalse(worker.is_alive())
            server.serve_forever = running
            return server
        with mock.patch.object(host, 'load_fcc_case_catalog', side_effect=load) as loaded, \
                mock.patch.object(os, 'read', new=read), mock.patch.object(PageObject, 'extract_text', new=extract), \
                mock.patch.object(cases.FccReportCaseCatalog, '__init__', new=construct), \
                mock.patch.object(ui_server, 'create_server', side_effect=build), \
                mock.patch.object(sys, 'stdout', StringIO()) as out, mock.patch.object(sys, 'stderr', StringIO()) as err:
            status = serve.main(self.args)
        if faults: raise faults[0]
        self.assertEqual((status, err.getvalue(), len(observed)), (0, '', 7))
        self.assertEqual(json.loads(out.getvalue())['catalog_state'], 'configured'); loaded.assert_called_once()
        self.assertEqual(servers[0].fileno(), -1); self.assertEqual(self.snapshot(), before)
        self.assertTrue(all(not (self.state / name).exists() for name in DB_NAMES))
        self.assertEqual(text_pages, [1]); self.assertEqual(len(constructors), 1)
        self.assertEqual(sum(hash_read_bytes), source.stat().st_size * 2)
        self.evidence = {'kind': 'genuine_synthetic_in_process_HTTP', 'public037_calls': loaded.call_count,
                         'public_constructor_calls': len(constructors), 'selected_native_text_attempt_pages': text_pages,
                         'source_hash_bytes': sum(hash_read_bytes), 'source_hash_passes': 2,
                         'outside_selected_native_attempts': 0, 'completed_HTTP_requests': 6,
                         'request_input_PDF_DB_IO': 0, 'inputs_and_state_handles_renameable_before_bind': True,
                         'input_bytes_identity_mtime_mode_equal': True, 'own_listener_closed': True,
                         'state_database_entries_created': 0, 'actual_LG_calls': 0}

    def test_existing_none_HTTP_remains_unconfigured_503(self):
        server = ui_server.create_server(self.state, port=0)
        worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
        try:
            conn = http.client.HTTPConnection(*server.server_address, timeout=3)
            try:
                conn.request('GET', '/api/fcc-cases/summary'); response = conn.getresponse()
                self.assertEqual((response.status, json.loads(response.read())),
                                 (503, {'error': {'code': 'fcc_case_catalog_unconfigured'}}))
            finally: conn.close()
        finally:
            server.shutdown(); server.server_close(); worker.join(5)
        self.assertFalse(worker.is_alive())

    def child(self, *, bounded=False, empty=False, closed_output=False):
        if empty:
            folder = self.base / 'child-empty'; folder.mkdir()
            self.config, self.pin, self.state = synthetic_inputs(folder, empty=True)
            self.args = ['--config', str(self.config), '--config-sha256', self.pin, '--state-dir', str(self.state), '--port', '0']
        before = self.snapshot()
        command = [sys.executable, '-B', '-m', 'labflow.fcc_case_serve', *self.args]
        if bounded:
            # Test-owned wrapper only: real module entry/loader/server; interrupt main after 4 s.
            script = ("import _thread,runpy,sys,threading;from socketserver import BaseServer;"
                      "original=BaseServer.serve_forever;"
                      "exec('def bounded(self,*args,**kwargs):\\n t=threading.Timer(4,_thread.interrupt_main);t.daemon=True;t.start()\\n try:return original(self,poll_interval=0.05)\\n finally:t.cancel()');"
                      "BaseServer.serve_forever=bounded;sys.argv=['labflow.fcc_case_serve']+sys.argv[1:];"
                      "runpy.run_module('labflow.fcc_case_serve',run_name='__main__')")
            command = [sys.executable, '-B', '-c', script, *self.args]
        process = subprocess.Popen(command, cwd=Path(__file__).resolve().parents[1], stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, env={**os.environ, 'PYTHONIOENCODING': 'cp949'})
        try:
            if closed_output:
                process.stdout.close(); error = process.stderr.read(); process.wait(timeout=10)
                self.assertEqual(process.returncode, 1)
                self.assertEqual(json.loads(error), {'error': {'code': 'fcc_case_server_output_failed'}})
                self.assertNotIn(b'Traceback', error)
                self.evidence = {'kind': 'real_CLI_closed_stdout', 'returncode': process.returncode,
                                 'not_interpreter_flush120': True, 'actual_LG_calls': 0}
                return
            messages = queue.Queue()
            thread = threading.Thread(target=lambda: messages.put(process.stdout.readline()), daemon=True); thread.start()
            raw = messages.get(timeout=10); self.assertTrue(raw, process.stderr.read(2048) if process.poll() is not None else b'no ready')
            ready = json.loads(raw.decode('utf-8')); self.assertEqual(raw, encoded(ready) + b'\n')
            self.assertEqual(ready['catalog_state'], 'configured_empty' if empty else 'configured')
            port = int(ready['url'].split(':')[2].split('/')[0])
            self.assertGreater(port, 0)
            conn = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
            try:
                conn.request('GET', '/api/fcc-cases/summary'); response = conn.getresponse(); payload = json.loads(response.read())
                self.assertEqual(response.status, 200); self.assertEqual(payload['counts']['case_count'], 0 if empty else 1)
            finally: conn.close()
            tail, error = process.communicate(timeout=10); thread.join(2)
            self.assertEqual((process.returncode, tail, error), (0, b'', b''))
            with socket.socket() as probe:
                probe.settimeout(1); self.assertNotEqual(probe.connect_ex(('127.0.0.1', port)), 0)
            self.evidence = {'kind': 'real_module_entry_controlled_interrupt_child', 'genuine_synthetic037': True,
                             'catalog_state': ready['catalog_state'], 'ready_keys': sorted(ready),
                             'UTF8_compact_one_line': True, 'HTTP_summary_status': 200,
                             'case_count': payload['counts']['case_count'], 'returncode': process.returncode,
                             'loopback_ephemeral_requested_port': 0, 'own_listener_closed': True,
                             'child_exited': True, 'inputs_preserved': True, 'state_DB_entries_created': 0,
                             'interrupt_is_test_owned_wrapper': True, 'actual_LG_calls': 0}
        finally:
            if process.poll() is None:
                process.kill(); process.wait(timeout=5)
            if process.stdout is not None: process.stdout.close()
            process.stderr.close()
            self.assertEqual(self.snapshot(), before)
            self.assertTrue(all(not (self.state / name).exists() for name in DB_NAMES))

    def test_real_CLI_child_genuine_configured_HTTP_then_controlled_interrupt_exits_and_closes(self):
        self.child(bounded=True)

    def test_real_CLI_child_genuine_empty_HTTP_then_controlled_interrupt_exits_and_closes(self):
        self.child(bounded=True, empty=True)

    def test_real_CLI_closed_stdout_is_code1_not_interpreter_flush120(self):
        self.child(closed_output=True)

    def test_real_CLI_help_and_argument_error_have_no_private_traceback(self):
        for args, status in [(['--help'], 0), (['--config', str(self.config)], 2)]:
            child = subprocess.run([sys.executable, '-B', '-m', 'labflow.fcc_case_serve', *args],
                                   cwd=Path(__file__).resolve().parents[1], capture_output=True, timeout=10,
                                   env={**os.environ, 'PYTHONIOENCODING': 'cp949'})
            self.assertEqual(child.returncode, status)
            self.assertNotIn(b'Traceback', child.stderr); self.assertNotIn(str(self.base).encode(), child.stderr)
            if status == 2:
                self.assertEqual(json.loads(child.stderr), {'error': {'code': 'fcc_case_server_invalid_argument'}})

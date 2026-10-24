"""Owned port-0 contract servers; no external model, worker or device control."""
import copy
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
from unittest.mock import patch
import unittest

from labflow.active_intake import register_source, scan_source
from labflow.intake_jobs import claim_job
from labflow.intake_model_boundary import build_analysis_prompt
from labflow import intake_model_probe as probe
from labflow.store import Store, canonical


NAME = 'offline-loopback-contract'
CANARY = 'PRIVATE_LOOPBACK_PROBE_CANARY'
RESULT_KEYS = {'schema_version', 'kind', 'execution_mode', 'synthetic', 'hardware_verified',
               'model_execution_verified', 'state_mutations', 'status', 'reason_code',
               'request_sha256', 'response_sha256', 'response_complete', 'analysis'}


def response_for(prompt):
    context = json.loads(prompt['messages'][1]['content'])
    version, facts = context['analysis_contract']['schema_version'], []
    for document in context['documents']:
        sources = [(document['text'], {})] if document.get('format') != 'pdf' else [
            (page['text'], {'kind': 'pdf_page', 'extraction_id': document['extraction_id'],
                           'page_number': page['page_number'], 'text_sha256': page['text_sha256']})
            for page in document['pages']]
        for text, page in sources:
            for n, line in enumerate((text or '').splitlines(), 1):
                field, separator, value = line.partition(':')
                if separator and field in {'product_type', 'market', 'purpose', 'model'}:
                    facts.append({'field': field, 'value': value.strip(), 'status': 'explicit', 'evidence': [{
                        **(page or ({'kind': 'text_line'} if version == 2 else {})),
                        'path': document['path'], 'sha256': document['sha256'], 'line_start': n,
                        'line_end': n, 'quote': line, 'role': 'request'}]})
    return {'schema_version': version, **({'context_id': context['analysis_context_id']} if version == 2 else {}),
            'producer': prompt['expected_producer'], 'identity': 'single', 'facts': facts, 'missing_fields': []}


class FakeServer(ThreadingHTTPServer):
    daemon_threads = True
    block_on_close = False

    def handle_error(self, request, client_address):
        pass


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, *args):
        pass

    def do_POST(self):
        try:
            data = self.rfile.read(int(self.headers['Content-Length']))
            prompt = json.loads(data.decode('utf-8'))
            self.server.requests.append({'path': self.path, 'body': data, 'headers': dict(self.headers)})
            if self.server.callback:
                self.server.callback(prompt)
            value = response_for(prompt)
            mode = self.server.mode
            if mode == 'wrong_producer': value['producer'] = {'kind': 'model', 'name': 'wrong'}
            if mode == 'wrong_quote': value['facts'][0]['evidence'][0]['quote'] = CANARY
            if mode == 'wrong_page': value['facts'][0]['evidence'][0]['page_number'] = 999
            if mode == 'wrong_context': value['context_id'] = '0'*64
            body = canonical(value).encode('utf-8')
            if mode == 'bad_utf8': body = b'\xff'+CANARY.encode('ascii')
            if mode == 'duplicate': body = body.replace(b'"schema_version":1', b'"schema_version":1,"schema_version":1')
            if mode == 'nan': body = body.replace(b'"schema_version":1', b'"schema_version":NaN')
            if mode == 'bad_unicode':
                value['facts'][0]['value'] = '\ud800'
                body = json.dumps(value, ensure_ascii=True).encode('utf-8')
            if mode == 'exact_limit': body += b' '*(2*1024*1024-len(body))
            if mode == 'too_large': body += b' '*(2*1024*1024+100-len(body))
            if mode in {'http_error', 'redirect'}: body = CANARY.encode('ascii')
            self.server.response_body = body
            if mode == 'close_header':
                self.request.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: 200\r\n')
                self.close_connection = True
                return
            if mode == 'slow_header' and self.server.stopped.wait(3):
                return
            self.send_response(500 if mode == 'http_error' else 302 if mode == 'redirect' else 200)
            self.send_header('Content-Type', 'application/json')
            if mode.startswith('chunked'):
                self.send_header('Transfer-Encoding', 'chunked')
            elif mode != 'close_delimited':
                self.send_header('Content-Length', str(len(body)+(100 if mode == 'partial' else 0)))
            if mode == 'duplicate_length': self.send_header('Content-Length', str(len(body)))
            self.send_header('Connection', 'close')
            if mode == 'redirect': self.send_header('Location', self.server.location)
            if mode == 'bad_header_utf8': self.send_header('X-Bad', '\xff')
            self.end_headers()
            if mode == 'slow_body':
                for byte in body:
                    self.wfile.write(bytes([byte]))
                    self.wfile.flush()
                    if self.server.stopped.wait(.15): break
            elif mode.startswith('chunked'):
                wire = b''
                for offset in range(0, len(body), 71):
                    chunk = body[offset:offset+71]
                    wire += format(len(chunk), 'x').encode('ascii')+b'\r\n'+chunk+b'\r\n'
                wire += {'chunked': b'0\r\n\r\n',
                         'chunked_trailer': b'0\r\nX-Probe: complete\r\n\r\n',
                         'chunked_extensions': b'0;end=ok\r\nX-Probe: complete\r\n\r\n',
                         'chunked_zero_eof': b'0\r\n',
                         'chunked_trailer_eof': b'0\r\nX-Probe: partial',
                         'chunked_trailer_no_blank': b'0\r\nX-Probe: complete\r\n',
                         'chunked_lf_trailer': b'0\r\n\n',
                         'chunked_lf_size': b'0\n\r\n',
                         'chunked_bad_separator': b'0\r\n\r\n'}[mode]
                if mode == 'chunked_bad_separator':
                    wire = wire.replace(body[:71]+b'\r\n', body[:71]+b'XY', 1)
                self.server.response_wire = wire
                self.wfile.write(wire)
                self.wfile.flush()
            else:
                self.wfile.write(body)
                self.wfile.flush()
            self.close_connection = True
        except (OSError, ValueError):
            self.close_connection = True


class ModelProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        local = Path(__file__).resolve().parents[1]/'.local/model-probe-tests'
        local.mkdir(parents=True, exist_ok=True)
        cls.temporary = tempfile.TemporaryDirectory(dir=local)
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.base = Path(cls.temporary.name)
        cls.contexts, cls.stores = {}, []
        for kind in ('txt', 'pdf'):
            root = cls.base/kind
            folder = root/'inbox/bundle'
            folder.mkdir(parents=True)
            if kind == 'pdf':
                from reportlab.pdfgen import canvas
                document = canvas.Canvas(str(folder/'request.pdf'))
                for lines in [('product_type: industrial_sensor', 'model: PROBE-PDF'),
                              ('market: EU', 'purpose: development evaluation')]:
                    text = document.beginText(40, 790)
                    for line in lines: text.textLine(line)
                    document.drawText(text)
                    document.showPage()
                document.save()
            else:
                (folder/'request.txt').write_text('product_type: temperature_logger\nmarket: JP\n'
                    'purpose: engineering review\nmodel: PROBE-TXT\n', encoding='utf-8')
            store = Store(root/'state')
            register_source(store, 'PROBE-INBOX', root/'inbox', synthetic=True, settle_seconds=1)
            scan_source(store, 'PROBE-INBOX', now=100, synthetic_only=True)
            scan_source(store, 'PROBE-INBOX', now=101, synthetic_only=True)
            job = claim_job(store, 'prepare-context', now=102, synthetic_only=True)
            cls.contexts[kind] = {key: job[key] for key in ('job_id', 'intake_id', 'revision', 'synthetic',
                'documents', 'analysis_contract', 'instructions', 'analysis_context_id')}
            cls.stores.append(store)

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=self.base)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.context = copy.deepcopy(self.contexts['txt'])
        self.sequence = 0

    def server(self, mode='valid', callback=None):
        server = FakeServer(('127.0.0.1', 0), Handler)
        self.assertNotIn(server.server_port, {8765, 8766})
        server.mode, server.callback, server.requests = mode, callback, []
        server.stopped = threading.Event()
        server.location = 'http://127.0.0.1:1/analysis'
        server.response_body = b''
        thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
        thread.start()
        def close():
            server.stopped.set()
            server.shutdown()
            server.server_close()
            thread.join(1)
        self.addCleanup(close)
        return server, 'http://127.0.0.1:'+str(server.server_port)+'/analysis'

    def call(self, endpoint, **kwargs):
        self.sequence += 1
        output = kwargs.pop('output_dir', self.root/('run-'+str(self.sequence)))
        result = probe.probe_loopback_analysis(kwargs.pop('context', self.context), endpoint=endpoint,
            producer_name=kwargs.pop('producer_name', NAME), output_dir=output, **kwargs)
        return result, output

    def assert_result(self, result, status):
        self.assertEqual(set(result), RESULT_KEYS)
        self.assertEqual(result['status'], status)
        self.assertEqual((result['schema_version'], result['kind'], result['execution_mode']),
                         (1, 'loopback_analysis_contract_probe', 'loopback_contract_probe'))
        self.assertIs(result['synthetic'], True)
        self.assertIs(result['hardware_verified'], False)
        self.assertIs(result['model_execution_verified'], False)
        self.assertEqual(result['state_mutations'], 0)
        self.assertRegex(result['request_sha256'], r'^[a-f0-9]{64}$')
        if status != 'validated_response':
            self.assertIsNone(result['analysis'])
            self.assertNotIn(CANARY, canonical(result))
            self.assertNotIn(str(self.root), canonical(result))

    def test_actual_text_http_exchange_and_private_evidence(self):
        server, endpoint = self.server()
        result, output = self.call(endpoint)
        self.assert_result(result, 'validated_response')
        self.assertEqual(len(server.requests), 1)
        request = server.requests[0]
        self.assertEqual(request['path'], '/analysis')
        self.assertEqual(request['headers']['Content-Type'], 'application/json')
        self.assertEqual(request['body'], (output/'prompt.json').read_bytes())
        self.assertEqual(result['request_sha256'], hashlib.sha256(request['body']).hexdigest())
        self.assertEqual(result['response_sha256'], hashlib.sha256(server.response_body).hexdigest())
        self.assertIs(result['response_complete'], True)
        self.assertEqual((output/'response-prefix.bin').read_bytes(), server.response_body)
        self.assertEqual(json.loads((output/'result.json').read_text(encoding='utf-8')), result)
        manifest = json.loads((output/'manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(set(manifest['implementation_sha256']), {'intake_model_probe.py', 'intake_model_boundary.py'})
        self.assertEqual(manifest['source_hashes'], [self.context['documents'][0]['sha256']])
        for item in manifest['files']:
            data = (output/item['path']).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), item['sha256'])
            self.assertEqual(len(data), item['bytes'])

    def test_actual_pdf_page_context_is_decoded_by_parent(self):
        server, endpoint = self.server()
        result, _ = self.call(endpoint, context=copy.deepcopy(self.contexts['pdf']))
        self.assert_result(result, 'validated_response')
        market = next(fact for fact in result['analysis']['facts'] if fact['field'] == 'market')
        self.assertEqual(market['evidence'][0]['page_number'], 2)
        self.assertEqual(result['analysis']['schema_version'], 2)

    def test_pure_configuration_errors_have_no_filesystem_process_or_network_calls(self):
        endpoints = ['http://localhost:1234/analysis', 'https://127.0.0.1:1234/analysis',
            'http://127.0.0.2:1234/analysis', 'http://127.0.0.1:0/analysis',
            'http://127.0.0.1:65536/analysis', 'http://u:p@127.0.0.1:1234/analysis',
            'http://127.0.0.1:1234/analysis?x=1', 'http://127.0.0.1:1234/analysis#x',
            'http://127.0.0.1:1234/other', 'http://2130706433:1234/analysis']
        from contextlib import ExitStack
        targets = ['pathlib.Path.stat', 'pathlib.Path.lstat', 'pathlib.Path.open',
                   'labflow.intake_model_probe._start_child', 'socket.socket', 'os.open']
        with ExitStack() as stack:
            guards = [stack.enter_context(patch(target, side_effect=AssertionError(target))) for target in targets]
            for endpoint in endpoints:
                with self.assertRaises(ValueError) as error:
                    self.call(endpoint)
                self.assertNotIn(endpoint, str(error.exception))
            for timeout in [0, -1, 60.1, True, float('nan'), float('inf')]:
                with self.assertRaises(ValueError):
                    self.call('http://127.0.0.1:1234/analysis', timeout_seconds=timeout)
            context = copy.deepcopy(self.context)
            context['synthetic'] = False
            with self.assertRaises(ValueError):
                self.call('http://127.0.0.1:1234/analysis', context=context)
            context = copy.deepcopy(self.context)
            context['token'] = CANARY
            with self.assertRaises(ValueError):
                self.call('http://127.0.0.1:1234/analysis', context=context)
            for name in ('', None, 'x'*201):
                with self.assertRaises(ValueError):
                    self.call('http://127.0.0.1:1234/analysis', producer_name=name)
            for guard in guards: guard.assert_not_called()

    def test_existing_targets_and_missing_parent_preserve_everything_without_starting_child(self):
        existing = self.root/'existing'
        existing.mkdir()
        marker = existing/'marker'
        marker.write_bytes(CANARY.encode('ascii'))
        for output in (existing, marker, self.root/'missing/leaf'):
            with patch.object(probe, '_start_child') as process, patch('socket.socket') as network:
                with self.assertRaises(ValueError): self.call('http://127.0.0.1:1234/analysis', output_dir=output)
                process.assert_not_called()
                network.assert_not_called()
        self.assertEqual(marker.read_bytes(), CANARY.encode('ascii'))
        self.assertFalse((self.root/'missing').exists())

    def test_reparse_parent_is_rejected_without_writes_or_child(self):
        from types import SimpleNamespace
        actual = Path.lstat
        def reparse(path):
            info = actual(path)
            if path == self.root:
                return SimpleNamespace(st_mode=info.st_mode, st_file_attributes=1024)
            return info
        with patch.object(Path, 'lstat', reparse), patch('os.open') as writes, \
             patch.object(probe, '_start_child') as processes:
            with self.assertRaises(ValueError): self.call('http://127.0.0.1:1234/analysis')
            writes.assert_not_called()
            processes.assert_not_called()

    def test_parent_rejects_wrong_producer_quote_and_pdf_binding(self):
        for mode in ('wrong_producer', 'wrong_quote', 'wrong_page', 'wrong_context'):
            server, endpoint = self.server(mode)
            context = copy.deepcopy(self.contexts['pdf'] if mode in {'wrong_page', 'wrong_context'} else self.context)
            result, _ = self.call(endpoint, context=context)
            self.assert_result(result, 'rejected')
            self.assertEqual(result['reason_code'], 'invalid_response')
            self.assertEqual(len(server.requests), 1)

    def test_invalid_raw_utf8_duplicate_nan_and_unicode_are_rejected(self):
        for mode in ('bad_utf8', 'duplicate', 'nan', 'bad_unicode'):
            server, endpoint = self.server(mode)
            result, _ = self.call(endpoint)
            self.assert_result(result, 'rejected')
            self.assertEqual(result['reason_code'], 'invalid_response')

    def test_exact_two_mebibyte_response_is_complete_and_valid(self):
        server, endpoint = self.server('exact_limit')
        result, output = self.call(endpoint)
        self.assert_result(result, 'validated_response')
        self.assertEqual((output/'response-prefix.bin').stat().st_size, 2*1024*1024)
        self.assertIs(result['response_complete'], True)

    def test_valid_chunked_and_close_delimited_bodies_are_preserved_without_framing(self):
        for mode in ('chunked', 'close_delimited'):
            server, endpoint = self.server(mode)
            result, output = self.call(endpoint)
            self.assert_result(result, 'validated_response')
            self.assertEqual((output/'response-prefix.bin').read_bytes(), server.response_body)
            self.assertIs(result['response_complete'], True)

    def test_duplicate_content_length_header_is_rejected(self):
        server, endpoint = self.server('duplicate_length')
        result, _ = self.call(endpoint)
        self.assert_result(result, 'rejected')
        self.assertIs(result['response_complete'], False)

    def test_chunked_trailer_must_have_complete_final_crlf(self):
        for mode in ('chunked_zero_eof', 'chunked_trailer_eof', 'chunked_trailer_no_blank', 'chunked_lf_trailer'):
            with self.subTest(mode=mode):
                server, endpoint = self.server(mode)
                result, output = self.call(endpoint)
                self.assert_result(result, 'rejected')
                self.assertIs(result['response_complete'], False)
                self.assertIsNone(result['response_sha256'])
                self.assertEqual((output/'response-prefix.bin').read_bytes(), server.response_body)

    def test_valid_chunked_trailer_is_strictly_decoded_in_parent(self):
        for mode in ('chunked_trailer', 'chunked_extensions'):
            server, endpoint = self.server(mode)
            result, output = self.call(endpoint)
            self.assert_result(result, 'validated_response')
            self.assertIs(result['response_complete'], True)
            self.assertEqual((output/'response-prefix.bin').read_bytes(), server.response_body)

    def test_chunk_size_and_data_delimiters_must_be_complete_crlf(self):
        for mode in ('chunked_lf_size', 'chunked_bad_separator'):
            with self.subTest(mode=mode):
                server, endpoint = self.server(mode)
                result, _ = self.call(endpoint)
                self.assert_result(result, 'rejected')
                self.assertIs(result['response_complete'], False)
                self.assertIsNone(result['response_sha256'])

    def test_oversize_response_retains_only_bounded_unverified_prefix(self):
        server, endpoint = self.server('too_large')
        result, output = self.call(endpoint)
        self.assert_result(result, 'rejected')
        self.assertEqual(result['reason_code'], 'response_too_large')
        self.assertEqual((output/'response-prefix.bin').stat().st_size, 2*1024*1024+1)
        self.assertIsNone(result['response_sha256'])
        self.assertIs(result['response_complete'], False)

    def test_partial_body_and_incomplete_headers_are_not_complete(self):
        for mode in ('partial', 'close_header'):
            server, endpoint = self.server(mode)
            result, _ = self.call(endpoint)
            self.assert_result(result, 'rejected')
            self.assertIs(result['response_complete'], False)
            self.assertIsNone(result['response_sha256'])

    def test_invalid_header_utf8_is_not_accepted(self):
        server, endpoint = self.server('bad_header_utf8')
        result, _ = self.call(endpoint)
        self.assert_result(result, 'rejected')
        self.assertIs(result['response_complete'], False)

    def test_non_200_and_redirect_are_rejected_without_following(self):
        target, target_endpoint = self.server()
        for mode in ('http_error', 'redirect'):
            server, endpoint = self.server(mode)
            server.location = target_endpoint
            result, _ = self.call(endpoint)
            self.assert_result(result, 'rejected')
            self.assertEqual(result['reason_code'], 'http_status')
        self.assertEqual(target.requests, [])

    def test_proxy_environment_is_ignored_and_dns_is_not_called(self):
        proxy, proxy_endpoint = self.server()
        server, endpoint = self.server()
        with patch.dict(os.environ, {'HTTP_PROXY': proxy_endpoint, 'ALL_PROXY': proxy_endpoint,
                                    'http_proxy': proxy_endpoint, 'NO_PROXY': ''}), \
             patch.object(probe, '_BOOTSTRAP', "import socket; socket.getaddrinfo=lambda *a,**k: (_ for _ in ()).throw(AssertionError('DNS forbidden')); "+probe._BOOTSTRAP):
            result, _ = self.call(endpoint)
        self.assert_result(result, 'validated_response')
        self.assertEqual((len(server.requests), len(proxy.requests)), (1, 0))

    def test_slow_headers_and_body_obey_parent_total_deadline_and_cleanup(self):
        children = []
        actual = probe._start_child
        def start(*args):
            child = actual(*args)
            children.append(child)
            return child
        for mode in ('slow_header', 'slow_body'):
            server, endpoint = self.server(mode)
            started = time.monotonic()
            with patch.object(probe, '_start_child', side_effect=start):
                result, output = self.call(endpoint, timeout_seconds=1.2)
            self.assertLess(time.monotonic()-started, 3)
            self.assert_result(result, 'timeout')
            self.assertEqual(result['reason_code'], 'deadline_exceeded')
            self.assertIs(result['response_complete'], False)
            self.assertIsNone(result['response_sha256'])
            self.assertEqual(len(server.requests), 1)
            self.assertLessEqual((output/'response-prefix.bin').stat().st_size, 2*1024*1024+1)
        self.assertEqual(len(children), 2)
        self.assertTrue(all(child.pid and child.poll() is not None for child in children))

    def test_child_crash_is_sanitized_and_not_retried(self):
        server, endpoint = self.server()
        with patch.object(probe, '_BOOTSTRAP', 'import os; os._exit(7)'):
            result, _ = self.call(endpoint)
        self.assert_result(result, 'rejected')
        self.assertEqual(result['reason_code'], 'child_failed')
        self.assertEqual(server.requests, [])

    def test_caller_alias_changes_during_exchange_cannot_change_snapshot(self):
        expected = copy.deepcopy(self.context)
        def mutate(prompt):
            self.context['documents'][0]['text'] = CANARY
            self.context['documents'][0]['sha256'] = '0'*64
        server, endpoint = self.server(callback=mutate)
        result, output = self.call(endpoint)
        self.assert_result(result, 'validated_response')
        sent = json.loads(server.requests[0]['body'])
        self.assertEqual(json.loads(sent['messages'][1]['content']), expected)
        self.assertNotIn(CANARY, canonical(result))

    def test_domain_databases_and_worker_job_apis_are_unchanged(self):
        before = [store.db.read_bytes() for store in self.stores]
        server, endpoint = self.server()
        with patch('labflow.intake_worker.run_worker') as worker, \
             patch('labflow.intake_jobs.claim_job') as claim, patch('labflow.intake_jobs.complete_job') as complete:
            result, _ = self.call(endpoint)
            worker.assert_not_called()
            claim.assert_not_called()
            complete.assert_not_called()
        self.assert_result(result, 'validated_response')
        self.assertEqual([store.db.read_bytes() for store in self.stores], before)

    def test_child_native_output_and_raw_exceptions_are_not_forwarded(self):
        server, endpoint = self.server()
        context_file = self.root/'context.json'
        context_file.write_text(canonical(self.context), encoding='utf-8')
        noisy_bootstrap = "import os; os.write(1,b'"+CANARY+"'); os.write(2,b'"+CANARY+"'); raise RuntimeError('"+CANARY+"')"
        script = (
            "import sys,json; from pathlib import Path; "
            "from labflow import intake_model_probe as p; "
            "context=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')); "
            "p._BOOTSTRAP="+repr(noisy_bootstrap)+"; "
            "result=p.probe_loopback_analysis(context,endpoint=sys.argv[2],producer_name=sys.argv[3],output_dir=sys.argv[4]); "
            "print(result['reason_code'])"
        )
        completed = subprocess.run([sys.executable, '-X', 'utf8', '-B', '-c', script,
            str(context_file), endpoint, NAME, str(self.root/'noise-run')],
            cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, encoding='utf-8', timeout=15,
            env={**os.environ, 'PYTHONUTF8': '1', 'PYTHONDONTWRITEBYTECODE': '1'})
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertNotIn(CANARY, completed.stdout+completed.stderr)
        self.assertNotIn('Traceback', completed.stdout+completed.stderr)
        self.assertEqual(completed.stdout.strip(), 'child_failed')
        self.assertEqual(server.requests, [])

    def test_caller_main_is_not_replayed_or_leaked_before_child_target(self):
        server, endpoint = self.server()
        context_file = self.root/'bootstrap-context.json'
        context_file.write_text(canonical(self.context), encoding='utf-8')
        caller = self.root/'caller.py'
        caller.write_text(
            "import os,sys,json\nfrom pathlib import Path\n"
            "if __name__ == '__mp_main__':\n"
            "    os.write(1, b'"+CANARY+"')\n"
            "    os.write(2, b'"+CANARY+"')\n"
            "    raise RuntimeError('"+CANARY+"')\n"
            "if __name__ == '__main__':\n"
            "    sys.path.insert(0,sys.argv[1])\n"
            "    from labflow.intake_model_probe import probe_loopback_analysis\n"
            "    context=json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))\n"
            "    result=probe_loopback_analysis(context,endpoint=sys.argv[3],producer_name=sys.argv[4],output_dir=sys.argv[5])\n"
            "    print(result['status'])\n", encoding='utf-8')
        completed = subprocess.run([sys.executable, '-X', 'utf8', '-B', str(caller),
            str(Path(__file__).resolve().parents[1]), str(context_file), endpoint, NAME,
            str(self.root/'bootstrap-run')], capture_output=True, text=True, encoding='utf-8', timeout=15)
        self.assertNotIn(CANARY, completed.stdout+completed.stderr)
        self.assertNotIn('Traceback', completed.stdout+completed.stderr)
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout.strip(), 'validated_response')
        self.assertEqual(len(server.requests), 1)

    def test_reparse_response_file_is_rejected_before_following_exists_stat(self):
        from types import SimpleNamespace
        path = self.root/'response-prefix.bin'
        path.write_bytes(b'fixture')
        actual = Path.lstat
        def linked(current):
            value = actual(current)
            return SimpleNamespace(st_mode=value.st_mode, st_file_attributes=1024) if current == path else value
        with patch.object(Path, 'lstat', linked), \
             patch.object(Path, 'exists', side_effect=AssertionError('must not follow reparse')) as followed:
            with self.assertRaisesRegex(ValueError, '^probe_output_invalid$'):
                probe._read(path, 10)
            followed.assert_not_called()

    def test_child_start_failure_is_sanitized_without_retry_or_network(self):
        server, endpoint = self.server()
        with patch.object(probe, '_start_child', side_effect=OSError(CANARY)) as starts:
            result, output = self.call(endpoint)
        self.assert_result(result, 'rejected')
        self.assertEqual(result['reason_code'], 'child_start_failed')
        self.assertEqual(starts.call_count, 1)
        self.assertEqual(server.requests, [])
        self.assertTrue((output/'result.json').is_file())

    def test_parent_deadline_includes_process_startup_time(self):
        server, endpoint = self.server()
        actual = probe._start_child
        def slow_start(*args):
            time.sleep(.2)
            return actual(*args)
        with patch.object(probe, '_start_child', side_effect=slow_start):
            result, _ = self.call(endpoint, timeout_seconds=.1)
        self.assert_result(result, 'timeout')
        self.assertEqual(result['reason_code'], 'deadline_exceeded')
        self.assertLessEqual(len(server.requests), 1)

    def test_prompt_write_failure_preserves_new_leaf_without_starting_child(self):
        server, endpoint = self.server()
        output = self.root/'write-failure'
        with patch.object(probe, '_write_new', side_effect=OSError(CANARY)), \
             patch.object(probe, '_start_child') as processes:
            with self.assertRaisesRegex(ValueError, '^probe_evidence_error$'):
                self.call(endpoint, output_dir=output)
            processes.assert_not_called()
        self.assertTrue(output.is_dir())
        self.assertEqual(server.requests, [])

    def test_evidence_changed_during_decode_is_never_published_as_success(self):
        server, endpoint = self.server()
        output = self.root/'changed-evidence'
        actual = probe.decode_analysis_response
        def change(*args, **kwargs):
            result = actual(*args, **kwargs)
            (output/'response-prefix.bin').write_bytes(CANARY.encode('ascii'))
            return result
        with patch.object(probe, 'decode_analysis_response', side_effect=change):
            with self.assertRaisesRegex(ValueError, '^probe_evidence_error$'):
                self.call(endpoint, output_dir=output)
        self.assertFalse((output/'result.json').exists())
        self.assertEqual((output/'response-prefix.bin').read_bytes(), CANARY.encode('ascii'))

    def test_child_transport_record_changed_during_decode_cannot_be_committed(self):
        server, endpoint = self.server()
        output = self.root/'changed-transport'
        actual = probe.decode_analysis_response
        def change(*args, **kwargs):
            result = actual(*args, **kwargs)
            path = output/'transport.json'
            value = json.loads(path.read_text(encoding='utf-8'))
            value['complete'] = False
            path.write_text(canonical(value), encoding='utf-8')
            return result
        with patch.object(probe, 'decode_analysis_response', side_effect=change):
            with self.assertRaisesRegex(ValueError, '^probe_evidence_error$'):
                self.call(endpoint, output_dir=output)
        self.assertFalse((output/'result.json').exists())

    def test_owned_child_cleanup_uses_kill_only_after_terminate_did_not_stop(self):
        actions = []
        class Child:
            returncode = None
            def poll(self): return self.returncode
            def terminate(self): actions.append('terminate')
            def wait(self, timeout):
                actions.append(('wait', timeout))
                if self.returncode is None: raise subprocess.TimeoutExpired('owned', timeout)
            def kill(self):
                actions.append('kill')
                self.returncode = 0
        child = Child()
        self.assertIs(probe._stop(child), True)
        self.assertEqual(actions, ['terminate', ('wait', .25), 'kill', ('wait', .25)])

    def test_unconfirmed_child_is_quarantined_without_reading_live_response_files(self):
        actions = []
        class Child:
            returncode = None
            def poll(self): return None
            def wait(self, timeout):
                actions.append('wait')
                raise subprocess.TimeoutExpired('owned', timeout)
            def terminate(self): actions.append('terminate')
            def kill(self): actions.append('kill')
            def close(self): actions.append('close')
        def start(*args):
            actions.append('start')
            return Child()
        with patch.object(probe, '_start_child', side_effect=start), \
             patch.object(probe.time, 'monotonic', side_effect=[0, 1]), \
             patch.object(probe, '_read', side_effect=AssertionError('live response')) as reads, \
             patch('socket.socket') as network:
            result, output = self.call('http://127.0.0.1:1234/analysis', timeout_seconds=.1)
            reads.assert_not_called()
            network.assert_not_called()
        self.assert_result(result, 'rejected')
        self.assertEqual(result['reason_code'], 'termination_failed')
        self.assertNotIn('close', actions)
        self.assertEqual(actions.count('start'), 1)
        self.assertTrue((output/'result.json').is_file())

    @unittest.skipUnless(os.name == 'nt', 'Windows final-file length preflight')
    def test_impossible_windows_output_path_is_refused_before_leaf_creation(self):
        parent = self.root/('x'*max(1, 175-len(str(self.root))))
        parent.mkdir()
        target = parent/('y'*70)
        with patch.object(probe, '_start_child') as processes, patch('os.open') as writes:
            with self.assertRaisesRegex(ValueError, '^probe_output_invalid$'):
                self.call('http://127.0.0.1:1234/analysis', output_dir=target)
            processes.assert_not_called()
            writes.assert_not_called()
        self.assertFalse(target.exists())


if __name__ == '__main__':
    unittest.main()

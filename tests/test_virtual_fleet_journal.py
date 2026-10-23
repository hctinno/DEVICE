import hashlib
import json
import math
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import tempfile
import unittest
from unittest.mock import patch


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')


def event(sequence, kind, payload, **changes):
    result = {'schema_version': 1, 'kind': 'operator_event', 'event_id': f'event:{sequence}',
              'run_id': 'run-1', 'runtime_instance_id': 'instance-1', 'sequence': sequence,
              'type': kind, 'payload': payload}
    result.update(changes)
    return result


def intent(sequence=1, request_id='request-1', logical_request=1):
    return event(sequence, 'intent', {'request_id': request_id, 'operation': 'execute',
                 'body': {'device_id': 'sensor', 'action': 'acquire', 'parameters': {}},
                 'logical_request': logical_request})


def termination(sequence):
    return event(sequence, 'termination', {'code': 'run_terminated', 'unresolved_request_ids': []})


def wire_records(path):
    return [json.loads(line) for line in path.read_bytes().splitlines()]


def rewrite_chain(path, records, *, canonical=True):
    previous = '0' * 64
    lines = []
    for record in records:
        record.pop('sha256', None)
        record['previous_sha256'] = previous
        record['sha256'] = hashlib.sha256(encoded(record)).hexdigest()
        previous = record['sha256']
        lines.append(encoded(record) if canonical else json.dumps(record, ensure_ascii=False).encode('utf-8'))
    path.write_bytes(b'\n'.join(lines) + b'\n')


class OperatorJournalTests(unittest.TestCase):
    def setUp(self):
        from labflow.virtual_fleet import journal
        self.module = journal
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.path = self.root / 'operator.jsonl'
        self.provenance = {'runtime_origin': 'preinitialized', 'catalog_sha256': 'a' * 64,
                           'topology_sha256': 'b' * 64, 'engine_sha256': 'c' * 64}

    def writer(self, path=None, **kwargs):
        writer = self.module.OperatorJournal(path or self.path, run_id=kwargs.pop('run_id', 'run-1'),
                     runtime_instance_id=kwargs.pop('runtime_instance_id', 'instance-1'),
                     provenance=kwargs.pop('provenance', self.provenance), **kwargs)
        self.addCleanup(writer.close)
        return writer

    def read(self, path=None):
        return self.module.read_operator_journal(path or self.path)

    def test_canonical_utf8_lf_hash_chain_and_complete_round_trip(self):
        with self.writer() as writer:
            writer(event(1, 'observation', {'observation': {'source_id': 'sensor', 'reason': 'sensor_fault_symptom', 'label': '\uad00\uce21'}}))
            writer(intent(2))
            writer(event(3, 'transport_retry', {'request_id': 'request-1', 'retry': 1}))
            writer(event(4, 'receipt', {'request_id': 'request-1', 'result': {'status': 'pending', 'values': {}}}))
            writer(event(5, 'observation', {'observation': {'tick': 1}, 'cause_request_id': 'request-1'}))
            writer(termination(6))
        raw = self.path.read_bytes()
        self.assertNotIn(b'\r', raw)
        previous = '0' * 64
        for line in raw.splitlines(keepends=True):
            record = json.loads(line)
            self.assertEqual(line, encoded(record) + b'\n')
            self.assertEqual(record['previous_sha256'], previous)
            unsigned = {k: v for k, v in record.items() if k != 'sha256'}
            self.assertEqual(record['sha256'], hashlib.sha256(encoded(unsigned)).hexdigest())
            previous = record['sha256']
        result = self.read()
        self.assertEqual(len(result['events']), 6)
        self.assertTrue(result['complete'])
        self.assertFalse(result['resumable'])
        self.assertEqual(result['unresolved_request_ids'], [])
        self.assertEqual(result['integrity']['status'], 'verified')
        self.assertEqual(result['integrity']['head_sha256'], previous)
        self.assertEqual(result['integrity']['file_sha256'], hashlib.sha256(raw).hexdigest())
        self.assertTrue(result['header']['synthetic'])
        self.assertFalse(result['header']['hardware_verified'])
        self.assertFalse(result['header']['ai_model_called'])
        self.assertEqual(result['header']['provenance']['runtime_origin'], 'preinitialized')

    def test_pending_intent_survives_close_and_even_a_terminal_uncertain_run_is_not_complete(self):
        with self.writer() as writer:
            writer(intent())
            writer(event(2, 'error', {'code': 'runtime_mutation_uncertain'}))
            writer(event(3, 'termination', {'code': 'run_terminated', 'unresolved_request_ids': []}))
        result = self.read()
        self.assertFalse(result['complete'])
        self.assertEqual(result['unresolved_request_ids'], ['request-1'])
        self.assertFalse(result['resumable'])

    def test_header_only_and_closed_without_termination_are_incomplete(self):
        with self.writer():
            pass
        self.assertFalse(self.read()['complete'])
        self.assertEqual(self.read()['events'], [])

    def test_create_existing_file_never_truncates_or_appends(self):
        self.path.write_bytes(b'original evidence')
        with self.assertRaises(FileExistsError):
            self.writer()
        self.assertEqual(self.path.read_bytes(), b'original evidence')

    def test_concurrent_creation_allows_exactly_one_writer(self):
        def attempt(_):
            try:
                return self.writer()
            except FileExistsError:
                return None
        with ThreadPoolExecutor(max_workers=4) as pool:
            writers = [item for item in pool.map(attempt, range(4)) if item is not None]
        try:
            self.assertEqual(len(writers), 1)
        finally:
            for writer in writers:
                writer.close()
        self.assertEqual(len(self.path.read_bytes().splitlines()), 1)
        self.assertFalse(self.read()['complete'])

    def test_invalid_constructor_is_rejected_before_creating_any_file(self):
        cases = [{'run_id': '../bad'}, {'runtime_instance_id': True},
                 {'provenance': {'runtime_origin': 'resumed'}},
                 {'provenance': {'runtime_origin': 'preinitialized', 'nested': {'seed': 41}}},
                 {'provenance': {'runtime_origin': 'preinitialized', 'catalog_sha256': 'bad'}},
                 {'provenance': {k: v for k, v in self.provenance.items() if k != 'engine_sha256'}},
                 {'provenance': {**self.provenance, 'engine_sha256': 'A' * 64}}]
        for index, arguments in enumerate(cases):
            path = self.root / f'invalid-{index}.jsonl'
            with self.assertRaises(ValueError):
                self.writer(path, **arguments)
            self.assertFalse(path.exists())

    def test_invalid_event_envelope_never_writes_or_consumes_sequence(self):
        with self.writer() as writer:
            writer(event(1, 'observation', {'observation': {}}))
            bad = [event(3, 'observation', {'observation': {}}),
                   event(2, 'observation', {'observation': {}}, run_id='other'),
                   event(2, 'observation', {'observation': {}}, runtime_instance_id='other'),
                   event(2, 'observation', {'observation': {}}, event_id='event:1'),
                   event(2, 'observation', {'observation': {}}, extra=True),
                   event(2, 'author_control', {}),
                   event(True, 'observation', {'observation': {}}),
                   event(2, 'observation', {'observation': {}}, event_id='bad/id')]
            for candidate in bad:
                before = self.path.read_bytes()
                with self.assertRaises(ValueError):
                    writer(candidate)
                self.assertEqual(self.path.read_bytes(), before)
            writer(termination(2))
        self.assertTrue(self.read()['complete'])

    def test_request_references_duplicate_receipts_and_reused_intents_are_rejected(self):
        with self.writer() as writer:
            for payload in [event(1, 'receipt', {'request_id': 'missing', 'result': {}}),
                            event(1, 'transport_retry', {'request_id': 'missing', 'retry': 1}),
                            event(1, 'observation', {'observation': {}, 'cause_request_id': 'missing'})]:
                with self.assertRaises(ValueError):
                    writer(payload)
            writer(intent())
            writer(event(2, 'receipt', {'request_id': 'request-1', 'result': {'status': 'error'}}))
            for candidate in [intent(3, logical_request=2),
                              event(3, 'receipt', {'request_id': 'request-1', 'result': {}}),
                              event(3, 'transport_retry', {'request_id': 'request-1', 'retry': 1})]:
                with self.assertRaises(ValueError):
                    writer(candidate)
            writer(termination(3))
        self.assertEqual(self.read()['unresolved_request_ids'], [])

    def test_intent_operation_body_and_logical_request_are_strict(self):
        with self.writer() as writer:
            for change in [{'operation': 'author_control'}, {'logical_request': True}, {'logical_request': 2},
                           {'body': {'device_id': 'sensor', 'action': 'acquire'}},
                           {'operation': 'advance', 'body': {'ticks': 2}},
                           {'operation': 'advance', 'body': {'ticks': True}}]:
                candidate = intent(); candidate['payload'].update(change)
                with self.assertRaises(ValueError):
                    writer(candidate)
            writer(event(1, 'intent', {'request_id': 'tick-1', 'operation': 'advance',
                                      'body': {'ticks': 1}, 'logical_request': 1}))
        self.assertEqual(self.read()['unresolved_request_ids'], ['tick-1'])

    def test_transport_retry_numbers_are_consecutive_and_do_not_create_new_intents(self):
        with self.writer() as writer:
            writer(intent())
            for number in [0, True, 2, 1.0]:
                with self.assertRaises(ValueError):
                    writer(event(2, 'transport_retry', {'request_id': 'request-1', 'retry': number}))
            writer(event(2, 'transport_retry', {'request_id': 'request-1', 'retry': 1}))
            writer(event(3, 'transport_retry', {'request_id': 'request-1', 'retry': 2}))
        self.assertEqual(self.read()['unresolved_request_ids'], ['request-1'])

    def test_private_fields_at_any_depth_are_rejected_without_echoing_the_canary(self):
        keys = ['author', 'fault', 'seed', 'truth', 'expected', 'password', 'source_path', 'file_path',
                'private_path', 'decryptedPath', 'random_seed', 'hidden_fault', 'expected_values', 'authorControl']
        with self.writer() as writer:
            for key in keys:
                candidate = event(1, 'observation', {'observation': {'nested': [{key: 'CANARY_PRIVATE'}]}})
                before = self.path.read_bytes()
                with self.assertRaises(ValueError) as caught:
                    writer(candidate)
                self.assertNotIn('CANARY_PRIVATE', str(caught.exception))
                self.assertEqual(before, self.path.read_bytes())
            writer(event(1, 'observation', {'observation': {'source_id': 'sensor', 'reason': 'sensor_mismatch', 'default': True}}))
        self.assertEqual(self.read()['events'][0]['payload']['observation']['source_id'], 'sensor')

    def test_absolute_paths_and_non_json_or_nonfinite_values_never_enter_the_file(self):
        values = [r'C:\private\CANARY', '/home/private/CANARY', r'\\server\private\CANARY',
                  'file:///private/CANARY', math.nan, math.inf, (1, 2), {1: 'value'}, '\ud800']
        with self.writer() as writer:
            for value in values:
                with self.assertRaises(ValueError):
                    writer(event(1, 'observation', {'observation': {'note': value}}))
            self.assertNotIn(b'CANARY', self.path.read_bytes())

    def test_provenance_flags_cannot_be_forged_in_nested_observations(self):
        with self.writer() as writer:
            for flag, value in [('synthetic', False), ('hardware_verified', True), ('ai_model_called', True)]:
                with self.assertRaises(ValueError):
                    writer(event(1, 'observation', {'observation': {flag: value}}))

    def test_event_and_provenance_copies_are_isolated_from_callers_and_readers(self):
        evidence = event(1, 'observation', {'observation': {'value': 2}})
        with self.writer() as writer:
            writer(evidence)
            evidence['payload']['observation']['value'] = 999
            self.provenance['catalog_sha256'] = 'd' * 64
        result = self.read(); result['events'][0]['payload']['observation']['value'] = 888
        self.assertEqual(self.read()['events'][0]['payload']['observation']['value'], 2)
        self.assertEqual(self.read()['header']['provenance']['catalog_sha256'], 'a' * 64)

    def test_close_is_idempotent_and_no_event_can_follow_close_or_termination(self):
        writer = self.writer(); writer(termination(1))
        with self.assertRaises(ValueError):
            writer(event(2, 'error', {'code': 'late'}))
        writer.close(); writer.close()
        with self.assertRaises(OSError):
            writer(event(2, 'error', {'code': 'late'}))

    def test_fsync_failure_poison_closes_writer_and_keeps_uncertain_intent_evidence(self):
        writer = self.writer()
        with patch.object(self.module.os, 'fsync', side_effect=OSError('CANARY_STORAGE')):
            with self.assertRaises(OSError) as caught:
                writer(intent())
        self.assertNotIn('CANARY_STORAGE', str(caught.exception))
        with self.assertRaises(OSError):
            writer(termination(2))
        writer.close()
        self.assertEqual(self.read()['unresolved_request_ids'], ['request-1'])

    def test_partial_write_is_preserved_and_reader_never_repairs_it(self):
        original_fdopen = self.module.os.fdopen
        class PartialStream:
            def __init__(self, fd, mode):
                self.actual = original_fdopen(fd, mode)
                self.calls = 0
            def write(self, data):
                self.calls += 1
                if self.calls == 2:
                    self.actual.write(data[:len(data) // 2]); self.actual.flush()
                    raise OSError('partial evidence write')
                return self.actual.write(data)
            def flush(self): return self.actual.flush()
            def fileno(self): return self.actual.fileno()
            def close(self): return self.actual.close()
        with patch.object(self.module.os, 'fdopen', side_effect=PartialStream):
            writer = self.writer()
        with self.assertRaises(OSError):
            writer(intent())
        writer.close()
        before = self.path.read_bytes()
        self.assertFalse(before.endswith(b'\n'))
        with self.assertRaises(ValueError):
            self.read()
        self.assertEqual(self.path.read_bytes(), before)

    def test_constructor_write_failure_preserves_created_file_and_releases_handle(self):
        with patch.object(self.module.os, 'fsync', side_effect=OSError('header fsync')):
            with self.assertRaises(OSError):
                self.writer()
        self.assertTrue(self.path.is_file())
        with self.path.open('ab') as stream:
            stream.write(b'')

    def test_write_failure_closes_descriptor_even_without_caller_cleanup(self):
        original = self.module.os.fdopen
        streams = []
        def capture(fd, mode):
            stream = original(fd, mode); streams.append(stream); return stream
        with patch.object(self.module.os, 'fdopen', side_effect=capture):
            writer = self.writer()
        try:
            with patch.object(self.module.os, 'fsync', side_effect=OSError('uncertain')):
                with self.assertRaises(OSError):
                    writer(intent())
            self.assertTrue(streams[0].closed)
        finally:
            writer.close()

    def test_multiple_pending_intents_keep_order_and_receipt_resolves_only_its_id(self):
        with self.writer() as writer:
            writer(intent(1, 'first', 1)); writer(intent(2, 'second', 2))
            writer(event(3, 'receipt', {'request_id': 'first', 'result': {'status': 'invalid'}}))
            writer(event(4, 'termination', {'code': 'run_terminated', 'unresolved_request_ids': ['second']}))
        result = self.read()
        self.assertEqual(result['unresolved_request_ids'], ['second'])
        self.assertFalse(result['complete'])

    def test_private_and_noncanonical_data_are_rejected_even_with_valid_recomputed_chain(self):
        with self.writer() as writer:
            writer(termination(1))
        records = wire_records(self.path)
        records[0]['header']['provenance']['extra'] = {'expected_value': 'CANARY_PRIVATE'}
        target = self.root / 'private-header.jsonl'; rewrite_chain(target, records)
        with self.assertRaises(ValueError):
            self.read(target)
        self.assertIn(b'CANARY_PRIVATE', target.read_bytes())

    def test_line_file_and_event_limits_reject_before_append(self):
        with self.writer() as writer:
            before = self.path.read_bytes()
            with self.assertRaises(ValueError):
                writer(event(1, 'observation', {'observation': {'text': 'x' * (512 * 1024)}}))
            self.assertEqual(before, self.path.read_bytes())
            with patch.object(self.module, 'MAX_FILE_BYTES', len(before) + 10):
                with self.assertRaises(ValueError):
                    writer(event(1, 'observation', {'observation': {}}))
            with patch.object(self.module, 'MAX_EVENTS', 1):
                writer(event(1, 'observation', {'observation': {}}))
                with self.assertRaises(ValueError):
                    writer(termination(2))

    def test_reader_rejects_partial_corrupt_duplicate_key_and_noncanonical_bytes_without_writing(self):
        with self.writer() as writer:
            writer(termination(1))
        valid = self.path.read_bytes()
        malformed = [valid[:-1], valid.replace(b'run_terminated', b'run_fabricated'),
                     valid.replace(b'"schema_version":1', b'"schema_version":1,"schema_version":1', 1),
                     valid.replace(b'\n', b'\r\n'), b'\xff\n', b'']
        for index, raw in enumerate(malformed):
            path = self.root / f'bad-{index}.jsonl'; path.write_bytes(raw)
            with self.assertRaises(ValueError):
                self.read(path)
            self.assertEqual(path.read_bytes(), raw)
        self.assertEqual(self.path.read_bytes(), valid)

    def test_reader_checks_semantics_even_if_attacker_recomputes_the_hash_chain(self):
        with self.writer() as writer:
            writer(event(1, 'observation', {'observation': {}})); writer(termination(2))
        for index, mutate in enumerate([
            lambda r: r[1]['event'].update(sequence=3),
            lambda r: r[1]['event'].update(runtime_instance_id='other'),
            lambda r: r[2]['event'].update(event_id='event:1'),
            lambda r: r[1]['event']['payload']['observation'].update(seed='CANARY'),
            lambda r: r[0]['header'].update(resumable=True),
            lambda r: r[0]['header'].update(hardware_verified=True),
        ]):
            records = wire_records(self.path); mutate(records)
            path = self.root / f'forged-{index}.jsonl'; rewrite_chain(path, records)
            before = path.read_bytes()
            with self.assertRaises(ValueError):
                self.read(path)
            self.assertEqual(before, path.read_bytes())

    def test_reader_enforces_event_count_and_canonical_layout(self):
        with self.writer() as writer:
            writer(event(1, 'observation', {'observation': {}})); writer(termination(2))
        with patch.object(self.module, 'MAX_EVENTS', 1):
            with self.assertRaises(ValueError):
                self.read()
        with patch.object(self.module, 'MAX_FILE_BYTES', 1):
            with self.assertRaises(ValueError):
                self.read()
        first_line = self.path.read_bytes().splitlines(keepends=True)[0]
        with patch.object(self.module, 'MAX_LINE_BYTES', len(first_line) - 1):
            with self.assertRaises(ValueError):
                self.read()
        noncanonical = self.root / 'noncanonical.jsonl'
        rewrite_chain(noncanonical, wire_records(self.path), canonical=False)
        with self.assertRaises(ValueError):
            self.read(noncanonical)


if __name__ == '__main__':
    unittest.main()

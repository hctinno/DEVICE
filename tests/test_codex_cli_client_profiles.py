"""Two exact client profiles through real pipes and public transport doubles; model0."""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
import unittest
from unittest.mock import patch

from labflow import codex_cli_response as producer_api
from labflow import codex_intake_once as once_api
from labflow.virtual_fleet import codex_first_decision as first_api
from labflow.virtual_fleet import codex_virtual_one_action as action_api
from tests import test_codex_cli_response as producer_fixture
from tests import test_codex_intake_once as once_fixture
from tests import test_virtual_fleet_codex_first_decision as first_fixture
from tests import test_virtual_fleet_codex_virtual_one_action as action_fixture


LEGACY = '0.163.0-alpha.11.2'
CURRENT = '0.164.0-alpha.11.1'


@contextmanager
def fixture(case):
    value = case('runTest')
    try:
        value.setUp()
        yield value
    finally:
        if not value.doCleanups():
            raise AssertionError('Transport fixture cleanup failed')


def profile_result(original, selected, observed):
    """Keep a complete public double, including its original files and hashes."""
    def produce(prompt, schema, **kwargs):
        response, receipt = original(prompt, schema, **kwargs)
        receipt = deepcopy(receipt)
        directory = kwargs['evidence_dir']
        receipt['client'].update(supported_version=selected, observed_version=observed)
        invocation = json.loads((directory / 'invocation.json').read_bytes())
        if 'supported_version' in invocation:
            invocation['supported_version'] = selected
        payloads = dict(invocation=producer_api._canonical(invocation),
                        version_stdout=('codex-cli ' + observed + '\n').encode('utf-8'))
        for key, payload in payloads.items():
            descriptor = receipt['artifacts'][key]
            (directory / descriptor['path']).write_bytes(payload)
            descriptor.update(bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest())
        receipt['bindings']['invocation_sha256'] = receipt['artifacts']['invocation']['sha256']
        (directory / 'receipt.json').write_bytes(producer_api._canonical(receipt))
        return response, receipt
    return produce


class ClientProfileTests(unittest.TestCase):
    def accepted(self, call):
        try:
            return call()
        except (producer_api.CodexCliResponseError, first_api.CodexFirstDecisionError,
                action_api.CodexVirtualOneActionError) as error:
            self.fail('Exact allowed profile was rejected: ' + error.code)

    def native_double(self, value, banner, *, stderr=b'', exit_code=0):
        source = producer_fixture.CHILD.replace(
            "else: os.write(1,b'codex-cli 0.163.0-alpha.11.2\\n')",
            'else: os.write(1,' + repr(banner) + ')')
        source = source.replace('    sys.exit(0)',
                                '    os.write(2,' + repr(stderr) + ')\n    sys.exit(' + str(exit_code) + ')', 1)
        value.script.write_text(source, encoding='utf-8')

    def test_exact_profiles_select_matching_receipt_and_invocation_with_one_model_child(self):
        for version in (LEGACY, CURRENT):
            with self.subTest(version=version), fixture(producer_fixture.ProducerTests) as value:
                self.native_double(value, ('codex-cli ' + version + '\n').encode())
                response, receipt = self.accepted(value.call)
                self.assertEqual(response, producer_fixture.RAW)
                self.assertEqual(receipt['client']['supported_version'], version)
                self.assertEqual(receipt['client']['observed_version'], version)
                self.assertEqual(receipt['attempts']['model_process_attempts'], 1)
                self.assertEqual(len(value.calls), 2)
                self.assertEqual(value.calls[0], [str(value.exe), '--version'])
                invocation = json.loads((value.evidence / 'invocation.json').read_bytes())
                self.assertEqual(invocation['supported_version'], version)
                self.assertEqual(invocation['model_argv'], value.calls[1])
                self.assertEqual(len(invocation['model_argv']), 18)
                value.shape(receipt, producer_fixture.CONTRACT['receipt'])
                value.shape(invocation, producer_fixture.CONTRACT['invocation'])

    def test_unknown_suffix_crlf_missing_lf_stderr_and_exit_reject_before_model_child(self):
        cases = [
            (b'codex-cli 0.165.0-alpha.11.1\n', b'', 0),
            (b'codex-cli 0.164.0-alpha.11.1-extra\n', b'', 0),
            (b'codex-cli 0.164.0-alpha.11.1\r\n', b'', 0),
            (b'codex-cli 0.164.0-alpha.11.1', b'', 0),
            (b'codex-cli 0.164.0-alpha.11.1\n', b'warning', 0),
            (b'codex-cli 0.164.0-alpha.11.1\n', b'', 7),
            (b'codex-cli 0.163.0-alpha.11.2-extra\n', b'', 0),
        ]
        for banner, stderr, exit_code in cases:
            with self.subTest(banner=banner, stderr=stderr, exit_code=exit_code), fixture(producer_fixture.ProducerTests) as value:
                self.native_double(value, banner, stderr=stderr, exit_code=exit_code)
                error = value.failure('normal', 'unsupported_client')
                self.assertEqual(len(value.calls), 1)
                self.assertEqual(error.receipt['attempts']['model_process_attempts'], 0)
                self.assertIsNone(error.receipt['client']['observed_version'])
                self.assertEqual(error.receipt['cost']['kind'], 'not_applicable')

    def test_current_profile_preserves_final_text_last_message_equality_check(self):
        with fixture(producer_fixture.ProducerTests) as value:
            self.native_double(value, b'codex-cli 0.164.0-alpha.11.1\n')
            error = value.failure('last_mismatch', 'final_mismatch')
            self.assertEqual(error.receipt['client']['supported_version'], CURRENT)
            self.assertEqual(error.receipt['client']['observed_version'], CURRENT)
            self.assertEqual(error.receipt['attempts']['model_process_attempts'], 1)

    def test_once_consumes_current_profile_and_rejects_unknown_or_mismatched_versions(self):
        for selected, observed, accepted in ((CURRENT, CURRENT, True), ('0.165.0', '0.165.0', False),
                                               (LEGACY, CURRENT, False), (CURRENT, LEGACY, False)):
            with self.subTest(selected=selected, observed=observed), fixture(once_fixture.OnceTests) as value:
                wrapped = profile_result(value.fake_d2, selected, observed)
                with patch.object(once_api, 'produce_codex_cli_response', side_effect=wrapped):
                    result = value.run_once()
                self.assertEqual(result['status'], 'completed' if accepted else 'failed')
                self.assertEqual(result['strict_decode'], 'accepted' if accepted else 'not_run')
                if not accepted:
                    self.assertEqual(result['errors'][0]['code'], 'codex_intake_once_receipt_binding_mismatch')

    def test_first_decision_consumes_current_and_rejects_unknown_or_mismatched_versions(self):
        for selected, observed, accepted in ((CURRENT, CURRENT, True), ('0.165.0', '0.165.0', False),
                                               (LEGACY, CURRENT, False), (CURRENT, LEGACY, False)):
            with self.subTest(selected=selected, observed=observed), fixture(first_fixture.FirstDecisionTests) as value:
                value.fake_produce = profile_result(value.fake_produce, selected, observed)
                if accepted:
                    result = self.accepted(value.call)
                    self.assertEqual(result['status'], 'complete')
                    self.assertEqual(result['slots'][0]['transport']['receipt']['client']['observed_version'], CURRENT)
                else:
                    value.failure('operator_first_decision_retention_failed')

    def test_one_action_consumes_current_and_rejects_unknown_or_mismatched_versions(self):
        for selected, observed, accepted in ((CURRENT, CURRENT, True), ('0.165.0', '0.165.0', False),
                                               (LEGACY, CURRENT, False), (CURRENT, LEGACY, False)):
            with self.subTest(selected=selected, observed=observed), fixture(action_fixture.OneActionTests) as value:
                value.fake_produce = profile_result(value.fake_produce, selected, observed)
                if accepted:
                    result = self.accepted(value.call)
                    self.assertEqual(result['status'], 'observed')
                    self.assertEqual(result['step']['transport']['receipt']['client']['observed_version'], CURRENT)
                else:
                    value.failure('retention_failed')
                    self.assertEqual(value.runtime_calls, [])


if __name__ == '__main__':
    unittest.main()

"""Actual lead-owned acceptance; developer adapters must be integrated to pass."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from labflow.intake_fixture_check import run_fixture_flow


class IntakeFixtureCheckTests(unittest.TestCase):
    def test_existing_output_is_preserved_before_loading_executors(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / 'existing'
            folder.mkdir()
            marker = folder / 'marker'
            marker.write_bytes(b'preserve existing evidence')
            with self.assertRaises(ValueError):
                run_fixture_flow(folder)
            self.assertEqual(marker.read_bytes(), b'preserve existing evidence')
            self.assertEqual(list(folder.iterdir()), [marker])

    def test_actual_text_intake_to_single_fixture_result(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = run_fixture_flow(Path(temporary) / 'new-run', power_dbm=-4)
            summary = result['summary']
            self.assertEqual(summary['fixture_acceptance'], 'pass')
            self.assertEqual(summary['records'], 1)
            self.assertIs(summary['source_current'], True)
            self.assertIs(summary['historical'], False)
            self.assertIs(summary['intake_ready'], True)
            self.assertEqual(summary['current_revision'], summary['revision'])
            self.assertIs(summary['source_synthetic'], True)
            self.assertIs(summary['ai_model_called'], False)
            self.assertIs(summary['hardware_verified'], False)
            self.assertIs(summary['fixture_measurement_observed'], True)
            self.assertEqual(summary['task_outcome'], 'not_assessed')
            self.assertEqual(summary['cleanup_status'], 'not_assessed')
            saved = json.loads((result['output'] / 'public-summary.json').read_text(encoding='utf-8'))
            self.assertEqual(saved, summary)

    def test_completed_measurement_is_historical_after_defer_before_summary(self):
        from labflow.intake_fixture_bridge import run_fixture_worker
        from labflow.intake_jobs import respond

        def defer_after_execution(store, **kwargs):
            result = run_fixture_worker(store, **kwargs)
            with store.connection() as con:
                intake_id = con.execute('SELECT intake_id FROM intake_fixture_jobs').fetchone()[0]
            respond(store, 'FLOW-LATE-DEFER', 'defer', intake_id=intake_id)
            return result

        with tempfile.TemporaryDirectory() as temporary:
            with patch('labflow.intake_fixture_bridge.run_fixture_worker', side_effect=defer_after_execution):
                result = run_fixture_flow(Path(temporary) / 'new-run', power_dbm=-4)
            summary = result['summary']
            self.assertIs(summary.get('source_current'), False)
            self.assertIs(summary['historical'], True)
            self.assertIs(summary['intake_ready'], False)
            self.assertEqual(summary['current_revision'], summary['revision'])
            self.assertIs(summary['fixture_measurement_observed'], True)
            self.assertEqual(summary['execution_state'], 'completed')
            self.assertEqual(summary['fixture_acceptance'], 'fail')
            from labflow.ui_read_model import IntakeReadModel
            record = IntakeReadModel(result['workspace']).fixture_runs(summary['intake_id'])['records'][0]
            self.assertIs(record['source_current'], False)
            self.assertEqual(record['report']['assessment']['verdict'], 'pass')

    def test_actual_two_page_pdf_requires_and_preserves_page_citations(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = run_fixture_flow(Path(temporary) / 'new-pdf-run', document_kind='pdf')
            self.assertEqual(result['summary']['fixture_acceptance'], 'pass')
            from labflow.ui_read_model import IntakeReadModel
            intake = IntakeReadModel(result['workspace']).snapshot(result['summary']['intake_id'])['intake']
            self.assertEqual(intake['analysis']['submitted']['schema_version'], 2)
            facts = intake['analysis']['submitted']['facts']
            market = next(f for f in facts if f['field'] == 'market')
            self.assertEqual(market['evidence'][0]['kind'], 'pdf_page')
            self.assertEqual(market['evidence'][0]['page_number'], 2)


class ConductedWorkflowEntryTests(unittest.TestCase):
    def test_text_opt_in_is_explicitly_unsupported_without_runtime(self):
        from labflow.intake_fixture_check import run_conducted_flow
        with tempfile.TemporaryDirectory() as temporary:
            result = run_conducted_flow(Path(temporary) / 'text', document_kind='text', measurement_ref='event:17')
            self.assertEqual(result['summary']['status'], 'unsupported')
            self.assertEqual(result['summary']['reason'], 'conducted_workflow_pdf_required')
            self.assertEqual(result['summary']['runtime_calls'], 0)
            self.assertIsNone(result['workspace'])

    def test_missing_explicit_measurement_ref_never_selects_last_measurement(self):
        from labflow.intake_fixture_check import run_conducted_flow
        with tempfile.TemporaryDirectory() as temporary:
            result = run_conducted_flow(Path(temporary) / 'reference', document_kind='pdf', measurement_ref=None)
            self.assertEqual(result['summary']['status'], 'unsupported')
            self.assertEqual(result['summary']['reason'], 'conducted_workflow_measurement_ref_required')
            self.assertEqual(result['summary']['runtime_calls'], 0)
            self.assertIsNone(result['workspace'])

    def test_cli_serves_original_startup_bindings_and_closes_after_interrupt(self):
        from labflow.intake_fixture_check import main
        plan, snapshot = {'original': 'plan'}, {'original': 'result'}
        flow = {'summary': {'fixture_acceptance': 'pass', 'intake_id': 'I-MOCK'},
                'workspace': Path('owned-synthetic-state'),
                'server_options': {'conducted_plan_preview_inputs': plan, 'conducted_result_snapshot': snapshot}}
        with patch('labflow.intake_fixture_check.run_conducted_flow', create=True, return_value=flow), patch('labflow.ui_server.create_server') as create:
            server = create.return_value.__enter__.return_value
            server.server_port = 8123
            server.serve_forever.side_effect = KeyboardInterrupt
            code = main(['--conducted-workflow', '--document-kind', 'pdf', '--measurement-ref', 'event:17', '--port', '0'])
            self.assertEqual(code, 0)
            create.assert_called_once_with(flow['workspace'], port=0, **flow['server_options'])
            create.return_value.__exit__.assert_called_once_with(None, None, None)
            self.assertEqual(snapshot, {'original': 'result'})


if __name__ == '__main__':
    unittest.main()

"""End-to-end fixture execution, separate evidence and a fresh output directory."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from labflow.virtual_fleet.harness_check import run_fixture_suite


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'virtual_profiles/sm_a176u_unlicensed.json'


def all_keys(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from all_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from all_keys(item)


class HarnessCheckTests(unittest.TestCase):
    def test_actual_three_trials_persist_separate_evidence_and_hashes(self):
        from labflow.virtual_fleet.journal import read_operator_journal
        original = CATALOG.read_bytes()
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'fresh'
            suite = run_fixture_suite(output, seed=71, power_dbm=-4)
            summary = suite['summary']
            self.assertTrue(summary['synthetic'])
            self.assertFalse(summary['hardware_verified'])
            self.assertFalse(summary['ai_model_called'])
            self.assertEqual((summary['fixture_trials'], summary['passed']), (3, 3))
            manifest = json.loads((output / 'private-manifest.json').read_bytes())
            for item in manifest['files']:
                target = (output / item['path']).resolve()
                self.assertTrue(target.is_relative_to(output.resolve()))
                data = target.read_bytes()
                self.assertEqual(len(data), item['bytes'])
                self.assertEqual(hashlib.sha256(data).hexdigest(), item['sha256'])
            conditions = set()
            for run in summary['runs']:
                base = output / run['run_id']
                report = json.loads((base / 'public-result.json').read_bytes())
                journal = read_operator_journal(base / 'operator/events.jsonl')
                author = json.loads((base / 'private/author.json').read_bytes())
                conditions.add(author['condition'])
                self.assertTrue(journal['complete'])
                self.assertFalse(journal['resumable'])
                self.assertFalse(journal['unresolved_request_ids'])
                self.assertEqual(report['assessment']['verdict'], 'pass')
                self.assertAlmostEqual(author['expected_sensor_dbm'], -34.5)
                self.assertEqual(journal['header']['provenance']['catalog_sha256'], hashlib.sha256(original).hexdigest())
                public = [report, journal['header'], journal['events']]
                self.assertFalse(set(all_keys(public)) & {'seed', 'condition', 'expected_sensor_dbm',
                                                         'author_events', 'fault', 'source_path', 'simulation_parameters'})
            self.assertEqual(conditions, {'normal', 'persistent_disconnect', 'restored_disconnect'})
        self.assertEqual(CATALOG.read_bytes(), original)

    def test_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'existing'
            output.mkdir()
            sentinel = output / 'original.bin'
            sentinel.write_bytes(b'preserve-original')
            with self.assertRaises((OSError, ValueError)):
                run_fixture_suite(output)
            self.assertEqual(sentinel.read_bytes(), b'preserve-original')
            self.assertEqual([p.name for p in output.iterdir()], ['original.bin'])

    def test_cli_runs_without_source_raw_files_or_model_configuration(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'cli-run'
            process = subprocess.run([sys.executable, '-B', '-m', 'labflow.virtual_fleet.harness_check',
                                      '--output', str(output), '--seed', '9'], cwd=ROOT,
                                     capture_output=True, text=True, encoding='utf-8', timeout=45)
            self.assertEqual(process.returncode, 0, process.stderr + process.stdout)
            report = json.loads(process.stdout)
            self.assertEqual((report['fixture_trials'], report['passed']), (3, 3))
            self.assertFalse(report['ai_model_called'])
            self.assertTrue((output / 'public-summary.json').is_file())


if __name__ == '__main__':
    unittest.main()

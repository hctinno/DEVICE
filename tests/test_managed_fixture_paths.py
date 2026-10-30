"""Portable test locations for integration and workspaces checkouts."""
import json
from pathlib import Path
import tempfile
import unittest

from labflow.development_paths import load_layout
from tests.managed_fixture_paths import fixture_root, workspace_expectations

REPO = Path(__file__).parents[1]
ROOT = load_layout(REPO).directory('runs', 'migration-20261031/toolchains/fixture-path-tests')


class ManagedFixturePathTests(unittest.TestCase):
    def setUp(self):
        ROOT.mkdir(parents=True, exist_ok=True)
        temp = tempfile.TemporaryDirectory(dir=ROOT, prefix='p')
        self.addCleanup(temp.cleanup)
        self.development = Path(temp.name) / '.local/development'
        self.checkouts = [self.development / 'integration', self.development / 'workspaces/dev1']
        for checkout in self.checkouts:
            checkout.mkdir(parents=True)
        self.rows = [dict(path='integration', role='integration', branch='codex/integration-test'),
                     dict(path='workspaces/dev1', role='dev1', branch='codex/dev1-test')]
        (self.development / 'layout.json').write_text(json.dumps(dict(
            schema_version=1, project_root_relative='../..',
            directories={k:k for k in ('integration','workspaces','runs','toolchains','archive')},
            workspaces=self.rows, path_aliases=[], control_root='runs/control/DGMAutoLab')), encoding='utf-8')

    def test_integration_and_workspace_depths_resolve_to_same_managed_runs(self):
        expected = self.development / 'runs/migration-20261031/toolchains/example'
        for checkout in self.checkouts:
            with self.subTest(checkout=checkout):
                self.assertEqual(fixture_root('example', repo=checkout), expected)
        self.assertFalse(expected.exists())
        self.assertFalse((self.development.parent / 'runs').exists())

    def test_expected_role_and_branch_come_from_each_declared_workspace(self):
        for checkout, row in zip(self.checkouts, self.rows):
            with self.subTest(checkout=checkout):
                self.assertEqual(workspace_expectations(checkout), (row['role'], row['branch']))

    def test_unmanaged_and_unregistered_paths_fail_without_creating_outputs(self):
        with self.assertRaises(ValueError):
            fixture_root('example', repo=Path(ROOT.anchor))
        with self.assertRaises(ValueError):
            workspace_expectations(self.development / 'workspaces/unregistered')
        self.assertFalse((self.development / 'runs').exists())


if __name__ == '__main__':
    unittest.main()

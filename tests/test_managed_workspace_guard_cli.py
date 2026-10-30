"""Actual cwd guard against a spoofed --cwd; read-only Git probes only."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from tests.managed_fixture_paths import fixture_root, workspace_expectations

REPO=Path(__file__).parents[1]
FIXTURES=fixture_root('guard-tests')
SCRIPT=REPO/'scripts/check_development_paths.py'

class ActualWorkspaceGuardTests(unittest.TestCase):
    def invoke(self,cwd,target):
        role,branch=workspace_expectations(REPO)
        result=subprocess.run([sys.executable,'-X','utf8','-B',str(SCRIPT),'--cwd',str(target),
            '--role',role,'--expected-branch',branch],
            cwd=cwd,capture_output=True,text=True,encoding='utf-8',check=False)
        return result,json.loads(result.stdout)

    def test_outside_actual_cwd_cannot_claim_a_registered_workspace(self):
        FIXTURES.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=FIXTURES,prefix='g') as folder:
            result,report=self.invoke(folder,REPO)
            self.assertEqual(result.returncode,2)
            self.assertEqual(report['status'],'not_run')
            self.assertEqual(report['code'],'development_paths_actual_cwd_mismatch')
            self.assertEqual(Path(report['actual_cwd']),Path(folder))
            self.assertIs(report['execution_authority'],False)

    def test_matching_actual_cwd_reports_the_native_workspace_without_authority(self):
        result,report=self.invoke(REPO,REPO)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(Path(report['actual_cwd']),REPO)
        self.assertEqual(Path(report['workspace']),REPO)
        self.assertIs(report['execution_authority'],False)

    def test_relative_requested_cwd_remains_rejected(self):
        result,report=self.invoke(REPO,'.')
        self.assertEqual(result.returncode,2)
        self.assertEqual(report['status'],'not_run')
        self.assertIs(report['execution_authority'],False)

if __name__=='__main__':unittest.main()

"""Read-only managed workspace/cwd/role/current-branch check."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).parents[1]))
from labflow.development_paths import DevelopmentPathError, check_development_workspace, _absolute, _no_reparse


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cwd', default=str(Path.cwd()))
    parser.add_argument('--role')
    parser.add_argument('--expected-branch')
    options = parser.parse_args(argv)
    actual_cwd=Path.cwd()
    try:
        actual=_no_reparse(_absolute(actual_cwd));requested=_no_reparse(_absolute(options.cwd))
        actual_info=actual.stat();requested_info=requested.stat()
        if (actual!=requested or (actual_info.st_dev,actual_info.st_ino)!=(requested_info.st_dev,requested_info.st_ino)):
            raise DevelopmentPathError('actual_cwd_mismatch')
        result = check_development_workspace(options.cwd, role=options.role, expected_branch=options.expected_branch)
    except (DevelopmentPathError, OSError, ValueError, subprocess.TimeoutExpired) as error:
        print(json.dumps(dict(status='not_run', code=getattr(error,'code','development_paths_check_unavailable'), actual_cwd=str(actual_cwd), execution_authority=False)))
        return 2
    print(json.dumps(dict(result,actual_cwd=str(actual_cwd)), ensure_ascii=False))
    return 0


if __name__=='__main__':
    raise SystemExit(main())

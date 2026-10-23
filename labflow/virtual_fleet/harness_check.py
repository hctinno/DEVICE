"""Run blind fixture policies, retain evidence and optionally show a report."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import uuid

from .catalog import load_catalog
from .evaluation import CONDITIONS, evaluate_sensor_run, prepare_sensor_trial
from .integration import get_role_actions


_DEFAULT_CATALOG = Path(__file__).resolve().parents[2] / 'virtual_profiles/sm_a176u_unlicensed.json'


def _json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + '\n').encode('utf-8')


def _write_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(_json_bytes(value))


def _engine_sha256():
    digest = hashlib.sha256()
    for path in sorted(Path(__file__).parent.glob('*.py')):
        data = path.read_bytes().replace(b'\r\n', b'\n')
        digest.update(path.name.encode('utf-8') + b'\0' + data + b'\0')
    return digest.hexdigest()


def run_fixture_suite(output_dir, *, catalog_path=_DEFAULT_CATALOG, seed=0, power_dbm=12.5):
    """Host-only batch; returned trial objects never become policy context."""
    output = Path(output_dir).resolve()
    # Never silently append a new attempt to an earlier or failed run directory.
    if output.exists():
        raise ValueError('Output directory already exists')
    from .harness import FleetHarness
    from .journal import OperatorJournal
    from .policies import RFSensorFixturePolicy
    catalog_path = Path(catalog_path)
    raw_catalog = catalog_path.read_bytes()
    catalog = load_catalog(catalog_path)
    actions = get_role_actions()
    engine_hash = _engine_sha256()
    output.mkdir(parents=True, exist_ok=False)
    completed = []
    files = []

    def retain(path, visibility):
        data = path.read_bytes()
        files.append({'path': path.relative_to(output).as_posix(), 'bytes': len(data),
                      'sha256': hashlib.sha256(data).hexdigest(), 'visibility': visibility})

    try:
        for condition in CONDITIONS:
            trial = prepare_sensor_trial(catalog, condition=condition, seed=seed, power_dbm=power_dbm)
            run_id = uuid.uuid4().hex
            folder = output / run_id
            journal_path = folder / 'operator/events.jsonl'
            journal_path.parent.mkdir(parents=True, exist_ok=False)
            topology_bytes = json.dumps(trial.topology, ensure_ascii=False, allow_nan=False,
                                        sort_keys=True, separators=(',', ':')).encode('utf-8')
            provenance = {'runtime_origin': 'preinitialized',
                          'catalog_sha256': hashlib.sha256(raw_catalog).hexdigest(),
                          'topology_sha256': hashlib.sha256(topology_bytes).hexdigest(),
                          'engine_sha256': engine_hash, 'python_version': sys.version.split()[0]}
            journal = OperatorJournal(journal_path, run_id=run_id,
                                      runtime_instance_id=trial.runtime_instance_id, provenance=provenance)
            try:
                harness = FleetHarness(trial.runtime, RFSensorFixturePolicy(), goal=trial.goal,
                                       catalog=trial.catalog, topology=trial.topology, role_actions=actions,
                                       event_sink=journal, run_id=run_id,
                                       runtime_instance_id=trial.runtime_instance_id)
                report = deepcopy(harness.run())
                report['assessment'] = evaluate_sensor_run(trial, report, harness.events())
                if (report['termination'].get('policy_claim') == 'completed'
                        and report['assessment']['verdict'] == 'pass'):
                    report['evidence']['measurement_refs'] = list(report['assessment']['evidence_refs'])
            finally:
                journal.close()
                _write_new(folder / 'private/author.json', trial.author_record())
            _write_new(folder / 'public-result.json', report)
            retain(journal_path, 'operator')
            retain(folder / 'private/author.json', 'evaluator_private')
            retain(folder / 'public-result.json', 'operator')
            completed.append({'trial': trial, 'report': report})

        summary = {'schema_version': 1, 'kind': 'virtual_fleet_harness_suite',
                   'synthetic': True, 'hardware_verified': False, 'ai_model_called': False,
                   'fixture_trials': len(completed),
                   'passed': sum(item['report']['assessment']['status'] == 'completed'
                                 and item['report']['assessment']['verdict'] == 'pass' for item in completed),
                   'validation_scope': 'synthetic fixture acceptance; no model training or hardware validation',
                   'runs': [{'run_id': item['report']['run_id'],
                             'termination': deepcopy(item['report']['termination']),
                             'assessment': deepcopy(item['report']['assessment'])} for item in completed]}
        _write_new(output / 'public-summary.json', summary)
        retain(output / 'public-summary.json', 'operator')
        _write_new(output / 'private-manifest.json',
                   {'schema_version': 1, 'kind': 'private_fixture_manifest', 'synthetic': True,
                    'hardware_verified': False, 'ai_model_called': False, 'resumable': False,
                    'files': files, 'scope': 'artifact hashes; no signature or hardware attestation'})
        return {'summary': summary, 'runs': completed}
    except Exception:
        # Preserve partial evidence and give no raw supplier exception to callers.
        failure = output / 'failure.json'
        if not failure.exists():
            _write_new(failure, {'schema_version': 1, 'synthetic': True, 'hardware_verified': False,
                                 'code': 'fixture_suite_incomplete', 'completed_runs': len(completed),
                                 'resumable': False})
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description='관측 기반 가상 하네스 수용 검사')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--catalog', type=Path, default=_DEFAULT_CATALOG)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--power-dbm', type=float, default=12.5)
    parser.add_argument('--port', type=int, help='검사 후 마지막 완료 기록을 보여줄 loopback 포트')
    args = parser.parse_args(argv)
    output = args.output or Path('.local/fleet-harness-check') / uuid.uuid4().hex
    try:
        suite = run_fixture_suite(output, catalog_path=args.catalog, seed=args.seed, power_dbm=args.power_dbm)
        print(json.dumps(suite['summary'], ensure_ascii=False, allow_nan=False), flush=True)
        if args.port is not None:
            from labflow.virtual_fleet_server import create_server
            last = suite['runs'][-1]
            with create_server(last['trial'].runtime, catalog=last['trial'].catalog,
                               topology=last['trial'].topology, role_actions=get_role_actions(),
                               harness_report=last['report'], port=args.port) as server:
                print(f'가상 실행 기록 · 실장비 미검증: http://127.0.0.1:{server.server_port}', flush=True)
                try:
                    server.serve_forever()
                except KeyboardInterrupt:
                    pass
        return 0 if suite['summary']['passed'] == suite['summary']['fixture_trials'] else 1
    except Exception:
        print(json.dumps({'error': 'virtual_harness_check_failed', 'synthetic': True,
                          'hardware_verified': False, 'ai_model_called': False}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

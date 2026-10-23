"""A new-only synthetic intake-to-fixture flow, optionally served in the intake UI."""
import argparse
from contextlib import contextmanager
import json
import math
from pathlib import Path
import time
import uuid

from .active_intake import register_source, scan_source
from .intake_fixture_jobs import fixture_readiness, request_fixture_job
from .intake_jobs import respond
from .intake_worker import SyntheticTextProvider, run_worker
from .store import Store


_PAGE_ONE = ['product_type: smartphone', 'manufacturer: Samsung', 'model: SM-A176U']
_PAGE_TWO = ['market: US', 'purpose: synthetic fixture acceptance']


class _SnapshotStore:
    def __init__(self, connection):
        self._connection = connection

    @contextmanager
    def connection(self):
        yield self._connection


def _write_request(folder, document_kind):
    folder.mkdir(parents=True, exist_ok=False)
    if document_kind == 'text':
        (folder / 'request.txt').write_text('\n'.join(_PAGE_ONE + _PAGE_TWO) + '\n', encoding='utf-8')
    else:
        from reportlab.pdfgen import canvas
        output = canvas.Canvas(str(folder / 'request.pdf'))
        for lines in (_PAGE_ONE, _PAGE_TWO):
            text = output.beginText(48, 790)
            for line in lines:
                text.textLine(line)
            output.drawText(text)
            output.showPage()
        output.save()


def _write_json(path, value):
    with path.open('xb') as stream:
        stream.write((json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + '\n').encode('utf-8'))


def run_fixture_flow(output_dir, *, power_dbm=12.5, document_kind='text'):
    """Create explicit fixture inputs; never accept or label user originals here."""
    output = Path(output_dir).resolve()
    if output.exists():
        raise ValueError('Output directory already exists')
    if (document_kind not in {'text', 'pdf'} or type(power_dbm) not in (int, float)
            or not math.isfinite(power_dbm) or not -30 <= power_dbm <= 20):
        raise ValueError('Invalid fixture configuration')
    from .intake_fixture_bridge import run_fixture_worker
    output.mkdir(parents=True, exist_ok=False)
    phase = 'prepare_intake'
    try:
        inbox, workspace = output / 'inbox', output / 'state'
        _write_request(inbox / 'fixture-request', document_kind)
        store = Store(workspace)
        register_source(store, 'FLOW-INBOX', inbox, synthetic=True, settle_seconds=0.001)
        started = time.time()
        scan_source(store, 'FLOW-INBOX', now=started)
        accepted = scan_source(store, 'FLOW-INBOX', now=started + 0.002)['accepted']
        if len(accepted) != 1:
            raise ValueError('fixture_intake_not_accepted')
        intake_id = accepted[0]['intake_id']
        # This is a simulated trusted proceed event for a sealed synthetic demo.
        respond(store, 'FLOW-DELEGATION', 'proceed', intake_id=intake_id)
        phase = 'analyze_fixture'
        analysis = run_worker(store, SyntheticTextProvider(), worker_id='flow-analysis', max_jobs=1)
        if len(analysis['results']) != 1 or analysis['results'][0]['status'] != 'completed':
            raise ValueError('fixture_analysis_incomplete')
        ready = fixture_readiness(store, intake_id)
        if not ready['ready']:
            raise ValueError('fixture_intake_not_ready')
        phase = 'run_single_fixture'
        request_fixture_job(store, 'FLOW-REQUEST', intake_id, expected_revision=ready['revision'],
            expected_readiness_fingerprint=ready['readiness_fingerprint'],
            recipe_id='conducted_sensor_fixture_v1', settings={'power_dbm': power_dbm})
        run_fixture_worker(store, worker_id='flow-execution', output_root=output / 'artifacts', max_jobs=1)
        with store.connection() as con:
            con.execute('BEGIN')
            row = con.execute('SELECT * FROM intake_fixture_jobs WHERE request_id=?', ('FLOW-REQUEST',)).fetchone()
            records = con.execute('SELECT COUNT(*) FROM intake_fixture_jobs').fetchone()[0]
            current = fixture_readiness(_SnapshotStore(con), intake_id)
        source_current = bool(current['revision'] == row['revision']
            and current['readiness_fingerprint'] == row['readiness_fingerprint'])
        report = json.loads(row['result_json'])['report'] if row['result_json'] else None
        observed = bool(row['state'] == 'completed' and report
            and report['termination'] == {'reason': 'policy_stop', 'policy_claim': 'completed'}
            and report['assessment']['status'] == 'completed' and report['assessment']['verdict'] == 'pass'
            and report['evidence']['measurement_refs'] and not report['unresolved_request_ids'])
        summary = {'schema_version': 1, 'kind': 'intake_fixture_flow_check',
            'synthetic': True, 'hardware_verified': False, 'ai_model_called': False, 'resumable': False,
            'document_kind': document_kind, 'intake_id': intake_id, 'revision': row['revision'],
            'current_revision': current['revision'], 'source_current': source_current,
            'historical': not source_current, 'intake_ready': current['ready'],
            'source_synthetic': bool(row['source_synthetic']),
            'request_id': row['request_id'], 'run_id': row['run_id'], 'records': records,
            'execution_state': row['state'], 'fixture_measurement_observed': observed,
            'fixture_acceptance': 'pass' if observed and source_current and current['ready'] else 'fail',
            'task_outcome': report['task_outcome'] if report else 'not_assessed',
            'cleanup_status': report['cleanup']['status'] if report else 'not_assessed',
            'validation_scope': 'synthetic intake and single sensor fixture; no model or hardware validation'}
        _write_json(output / 'public-summary.json', summary)
        return {'summary': summary, 'workspace': workspace, 'output': output}
    except Exception:
        _write_json(output / 'failure.json', {'schema_version': 1, 'synthetic': True,
            'hardware_verified': False, 'ai_model_called': False, 'resumable': False,
            'code': 'intake_fixture_flow_incomplete', 'phase': phase})
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--power-dbm', type=float, default=12.5)
    parser.add_argument('--document-kind', choices=['text', 'pdf'], default='text')
    parser.add_argument('--port', type=int, help='After execution, serve the existing intake store on loopback')
    args = parser.parse_args(argv)
    if args.port is not None and not 0 <= args.port <= 65535:
        parser.error('port must be between 0 and 65535')
    output = args.output or Path('.local/intake-fixture-check') / uuid.uuid4().hex
    try:
        result = run_fixture_flow(output, power_dbm=args.power_dbm, document_kind=args.document_kind)
        print(json.dumps(result['summary'], ensure_ascii=False, allow_nan=False), flush=True)
        if args.port is not None:
            from .ui_server import create_server
            with create_server(result['workspace'], port=args.port) as server:
                print(f"DGM synthetic intake fixture: http://127.0.0.1:{server.server_port}/#{result['summary']['intake_id']}", flush=True)
                try:
                    server.serve_forever()
                except KeyboardInterrupt:
                    pass
        return 0 if result['summary']['fixture_acceptance'] == 'pass' else 1
    except Exception:
        print(json.dumps({'error': 'intake_fixture_flow_failed', 'synthetic': True,
                          'hardware_verified': False, 'ai_model_called': False}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

"""Isolated browser acceptance data; the queue/readiness are explicit test doubles."""
import argparse
from contextlib import ExitStack
import json
from pathlib import Path
import sys
import tempfile
import threading
from unittest.mock import patch

from frontend.demo_fixture import build_demo
from labflow.store import Store
from labflow.ui_server import create_server

# Share the dedicated SQL double, never a replacement production queue.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests'))
from test_intake_fixture_read_ui import add_record, install_queue_double


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=0)
    args = parser.parse_args()
    evidence = Path('.local/FLOW-003-IMPLEMENTATION').resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='browser-', dir=evidence) as directory, ExitStack() as stack:
        workspace = build_demo(Path(directory) / 'demo')
        empty = build_demo(Path(directory) / 'empty', empty=True)
        store = Store(workspace)
        install_queue_double(store)
        with store.connection() as con:
            intake_id = con.execute('SELECT intake_id FROM intakes ORDER BY bundle LIMIT 1').fetchone()[0]
        for index in range(23):
            add_record(store, intake_id, f'FIXTURE-{index:02}', created_at=index,
                       readiness_fingerprint='c'*64 if index == 22 else 'd'*64)

        def readiness(snapshot, selected):
            with snapshot.connection() as con:
                row = con.execute('SELECT revision FROM intakes WHERE intake_id=?', (selected,)).fetchone()
            return dict(intake_id=selected, revision=row['revision'], readiness_fingerprint='c'*64)

        stack.enter_context(patch('labflow.ui_read_model.fixture_readiness', readiness))
        servers = [stack.enter_context(create_server(workspace, port=args.port)),
                   stack.enter_context(create_server(empty, port=0))]
        threads = [threading.Thread(target=server.serve_forever, daemon=True) for server in servers]
        for thread in threads:
            thread.start()
        print(json.dumps(dict(origin=f'http://127.0.0.1:{servers[0].server_port}',
                              empty_origin=f'http://127.0.0.1:{servers[1].server_port}')), flush=True)
        try:
            threading.Event().wait()
        finally:
            for server, thread in zip(servers, threads):
                server.shutdown()
                thread.join(timeout=3)


if __name__ == '__main__':
    main()

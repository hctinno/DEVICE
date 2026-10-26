"""One finite, synthetic real-adbutils/host-wire demonstration. No SDK needed."""
import argparse
from contextlib import contextmanager
import hashlib
import importlib
import importlib.metadata
import json
from pathlib import Path
import sys
import threading

from .virtual_adb_host import SERIAL, VirtualAdbHost
from .virtual_fleet.catalog import load_catalog
from .virtual_fleet.integration import create_conducted_example

ADBUTILS_COMMIT = '2382f08ba9394c6a3410ed25ffb89c02801850ec'
ADBUTILS_PY_TREE_SHA256 = '5445be5120cdc6195e6631c4767a67ff9196e034f34864eed3e2a5f2ecdd1935'
_GUARDS = []
_GUARD_LOCK = threading.RLock()
_AUDIT_INSTALLED = False


def _audit(event, args):
    with _GUARD_LOCK:
        for guard in _GUARDS:
            denied = False
            if event == 'socket.connect':
                denied = args[1] != guard['endpoint']
                if not denied and len(guard['connections']) < 128:
                    guard['connections'].append(list(args[1]))
            elif event == 'socket.getaddrinfo':
                denied = (args[0], args[1]) != guard['endpoint']
            elif event in {'subprocess.Popen', 'os.system', 'os.exec', 'os.posix_spawn'}:
                denied = True
            if denied:
                if len(guard['denied']) < 32:
                    guard['denied'].append(event)
                raise PermissionError('DGM demonstration blocks non-owned I/O and process execution')


@contextmanager
def own_wire_only(endpoint, denied, connections):
    """Audit/deny fallback without replacing client methods or wire responses.

    Process-wide during this context; use in a dedicated demonstration process.
    The audit hook stays inert after exit and installs once. Trusted Python is
    assumed; this is a guard against accidental SDK fallback, not an OS sandbox.
    """
    global _AUDIT_INSTALLED
    if (type(endpoint) is not tuple or len(endpoint) != 2 or endpoint[0] != '127.0.0.1'
            or type(endpoint[1]) is not int or not 1024 <= endpoint[1] <= 65535 or endpoint[1] == 5037):
        raise ValueError('an explicit owned loopback ephemeral endpoint is required')
    guard = {'endpoint': endpoint, 'denied': denied, 'connections': connections}
    with _GUARD_LOCK:
        if not _AUDIT_INSTALLED:
            sys.addaudithook(_audit)
            _AUDIT_INSTALLED = True
        _GUARDS.append(guard)
    try:
        yield
    finally:
        with _GUARD_LOCK:
            _GUARDS.remove(guard)


def _pinned_client(source_path, deps_path):
    source, deps = Path(source_path).resolve(strict=True), Path(deps_path).resolve(strict=True)
    package = source / 'adbutils'
    digest = hashlib.sha256()
    for path in sorted(package.rglob('*.py')):
        if path.is_symlink() or not path.resolve().is_relative_to(package.resolve()):
            raise ValueError('source path redirection rejected')
        digest.update(path.relative_to(package).as_posix().encode() + b'\0' + path.read_bytes() + b'\0')
    if digest.hexdigest() != ADBUTILS_PY_TREE_SHA256:
        raise ValueError('adbutils Python source tree differs from pinned archive')
    previous = sys.path[:]
    try:
        sys.path[:0] = [str(source), str(deps)]
        adbutils = importlib.import_module('adbutils')
        if Path(adbutils.__file__).resolve() != (package / '__init__.py').resolve():
            raise ValueError('a different adbutils is already imported')
        versions = {name: importlib.metadata.version(name) for name in
                    ['deprecation', 'retry2', 'packaging', 'decorator', 'requests', 'Pillow']}
    finally:
        sys.path[:] = previous
    return adbutils, versions


def _write(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')


def run_check(output, *, source_path, deps_path):
    """Create a new output folder; preserve incomplete outcomes; never retry."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    result = {'schema_version': 1, 'kind': 'dgm_virtual_adb_host_check',
              'status': 'incomplete', 'synthetic': True, 'hardware_verified': False,
              'sdk_verified': False, 'android_os_verified': False,
              'samsung_firmware_verified': False, 'anyway_verified': False,
              'ai_model_called': False, 'client': 'pinned_adbutils_real_host_wire',
              'adbutils_commit': ADBUTILS_COMMIT,
              'adbutils_py_tree_sha256': ADBUTILS_PY_TREE_SHA256,
              'catalog_basis': 'shipped_report_inventory_metadata; synthetic_bench_only',
              'serial': SERIAL, 'denied_operations': [], 'connections': [], 'steps': []}
    server = None
    try:
        catalog_path = Path(__file__).resolve().parents[1] / 'virtual_profiles/sm_a176u_unlicensed.json'
        catalog = load_catalog(catalog_path)
        result['catalog_sha256'] = hashlib.sha256(catalog_path.read_bytes()).hexdigest()
        fleet, _, bootstrap = create_conducted_example(catalog, seed=19)
        result['bootstrap'] = bootstrap
        server = VirtualAdbHost(fleet, port=0)
        with server:
            result['endpoint'] = list(server.endpoint)
            with own_wire_only(server.endpoint, result['denied_operations'], result['connections']):
                adbutils, versions = _pinned_client(source_path, deps_path)
                result['dependency_versions'] = versions
                client = adbutils.AdbClient(host=server.endpoint[0], port=server.endpoint[1], socket_timeout=2)
                device = client.device(serial=SERIAL)
                result['state'] = device.get_state()
                source = {'frequency_hz': 2450000000, 'power_dbm': 16,
                          'bandwidth_hz': 20000000, 'duty_cycle': .25,
                          'modulation': 'DGM synthetic OFDM declaration', 'crest_factor_db': 3}
                commands = ['getprop ro.product.model',
                            'dgm-twin rf configure ' + json.dumps(source, separators=(',', ':')),
                            'dgm-twin rf start', 'dgm-twin advance 3',
                            'dgm-twin measurement acquire', 'dgm-twin advance 2',
                            'dgm-twin measurement read', 'dgm-twin rf stop',
                            'dgm-twin advance 2', 'dgm-twin rf status']
                for command in commands:
                    raw = device.shell(command, timeout=2)
                    value = raw if command.startswith('getprop ') else json.loads(raw)
                    result['steps'].append({'command': command, 'response': value})
                measured = result['steps'][6]['response']['meter']
                stopped = result['steps'][9]['response']
                if (result['state'] != 'device' or measured['status'] != 'ok'
                        or not measured['values'].get('outputs', {}).get('measurement')
                        or stopped['values'].get('outputs', {}).get('rf', {}).get('valid', False)
                        or result['denied_operations']):
                    raise ValueError('wire run did not complete its declared synthetic scenario')
                result['status'] = 'complete'
    except Exception as exc:
        result['error'] = {'type': type(exc).__name__, 'message': str(exc)[:2000]}
    finally:
        trace = server.trace() if server else []
        result['resources_after_close'] = server.resources() if server else None
        _write(output / 'trace.json', trace)
        result['trace_sha256'] = hashlib.sha256((output / 'trace.json').read_bytes()).hexdigest()
        _write(output / 'result.json', result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description='Own loopback ADB host / synthetic Fleet check; no Android SDK')
    parser.add_argument('--output', type=Path, required=True, help='new output directory (must not exist)')
    parser.add_argument('--adbutils-source', type=Path, required=True, help='opt in to pinned archive extraction root')
    parser.add_argument('--runtime-deps', type=Path, required=True, help='opt in to private dependency directory')
    args = parser.parse_args(argv)
    try:
        result = run_check(args.output, source_path=args.adbutils_source, deps_path=args.runtime_deps)
    except OSError as exc:
        print(json.dumps({'status': 'incomplete', 'error': type(exc).__name__}))
        return 3
    print(json.dumps({'status': result['status'], 'synthetic': True,
                      'sdk_verified': False, 'hardware_verified': False}, sort_keys=True))
    return 0 if result['status'] == 'complete' else 3


if __name__ == '__main__':
    raise SystemExit(main())

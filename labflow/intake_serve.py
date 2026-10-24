"""Explicit existing-Store intake reference CLI; no creation or source auto-read."""
import json
import os
from pathlib import Path
import re
import sys

from .store import Store, StoreOpenError
from . import ui_server as _ui


_PREFIX = 'intake_reference_server_'
_CODES = frozenset(_PREFIX + suffix for suffix in
    ('invalid_argument', 'host_unavailable', 'output_failed', 'unavailable'))
_STORE_CODES = frozenset('store_open_' + suffix for suffix in
    ('invalid_argument', 'path_invalid', 'unavailable', 'schema_mismatch', 'input_changed',
     'integrity_invalid', 'closed', 'backend_unavailable', 'mode_unsupported'))
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,149}\Z', re.ASCII)
_HELP = ('Start an existing intake reference workspace on 127.0.0.1.\n'
    'Usage: python -B -m labflow.intake_serve --workspace ABS_DIR --port PORT '
    '--read-scope metadata|workspace|intakes [--intake-id ID ...]\n'
    'All three singleton options are required exactly once, with separate values.\n'
    'PORT is canonical ASCII 0..65535. Use 0 for an owned ephemeral port.\n'
    'metadata denies retained reads; intakes requires 1..100 unique ASCII IDs.\n'
    'No Store/DB creation, source scan, model, hardware, or automatic current read.\n')


class _Failure(ValueError):
    pass


def _fail(suffix):
    raise _Failure(_PREFIX + suffix)


def _arguments(argv):
    if type(argv) not in (list, tuple) or not 6 <= len(argv) <= 206 or len(argv) % 2:
        _fail('invalid_argument')
    try:
        if any(type(value) is not str for value in argv) or any(len(value) > 32768 for value in argv):
            _fail('invalid_argument')
        size = 0
        for value in argv:
            size += len(value.encode('utf-8'))
            if size > 32768: _fail('invalid_argument')
    except UnicodeError:
        _fail('invalid_argument')
    values, ids = {}, []
    for option, value in zip(argv[::2], argv[1::2]):
        if option == '--intake-id':
            ids.append(value)
        elif option in ('--workspace', '--port', '--read-scope') and option not in values:
            values[option] = value
        else:
            _fail('invalid_argument')
    if set(values) != {'--workspace', '--port', '--read-scope'}:
        _fail('invalid_argument')
    workspace, port, mode = values['--workspace'], values['--port'], values['--read-scope']
    if (not workspace or not Path(workspace).is_absolute()
            or re.fullmatch(r'0|[1-9][0-9]{0,4}', port, re.ASCII) is None or int(port) > 65535
            or mode not in ('metadata', 'workspace', 'intakes')):
        _fail('invalid_argument')
    if mode == 'intakes':
        if not 1 <= len(ids) <= 100 or any(_ID.fullmatch(value) is None for value in ids) or len(set(ids)) != len(ids):
            _fail('invalid_argument')
        scope = tuple(ids)
    else:
        if ids: _fail('invalid_argument')
        scope = () if mode == 'metadata' else 'workspace'
    return workspace, int(port), scope


def _json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8') + b'\n'


def _write(stream, raw):
    value = raw.decode('utf-8')
    count = stream.write(value)
    if type(count) is not int or count != len(value): raise OSError()
    stream.flush()


def _ready(server):
    port = server.server_port
    if type(port) is not int or not 1 <= port <= 65535: _fail('output_failed')
    raw = _json({'schema_version':1, 'kind':'intake_reference_server_ready',
                 'url':'http://127.0.0.1:' + str(port) + '/', 'store_mode':'open_existing'})
    if len(raw) > 1024: _fail('output_failed')
    return raw


def _code(error, fallback):
    if type(error) is _Failure:
        value = error.args[0] if len(error.args) == 1 else None
        if type(value) is str and value in _CODES: return value
    if type(error) is StoreOpenError:
        value = error.__dict__.get('code')
        if type(value) is str and value in _STORE_CODES: return value
    return fallback


def _cleanup(server, store, first):
    # Keep per-resource ordinary retry budgets across repeated interrupts.
    resources = [(server, 'server_close'), (store, 'close')]
    attempts = [0, 0]; index = 0
    while index < len(resources):
        try:
            resource, method = resources[index]
            if resource is None or attempts[index] >= 2:
                index += 1; continue
            try:
                getattr(resource, method)()
            except KeyboardInterrupt:
                continue
            except Exception as error:
                if first[0] is None: first[0] = _code(error, _PREFIX + 'unavailable')
                attempts[index] += 1
                continue
            index += 1
        except KeyboardInterrupt:
            continue


def _emit_error(code):
    try:
        _write(sys.stderr, _json({'error':{'code':code}}))
    except (Exception, KeyboardInterrupt):
        # Delivery is unknown; retrying may append a second error frame.
        pass


def main(argv=None) -> int:
    """Return a fixed exit code without replacing, reconfiguring or closing caller I/O."""
    server = store = None; first = [None]; phase = _PREFIX + 'invalid_argument'
    try:
        arguments = sys.argv[1:] if argv is None else argv
        if (type(arguments) in (list, tuple) and len(arguments) == 1
                and type(arguments[0]) is str and arguments[0] == '--help'):
            phase = _PREFIX + 'output_failed'; _write(sys.stdout, _HELP.encode('utf-8')); return 0
        workspace, port, scope = _arguments(arguments)
        phase = _PREFIX + 'unavailable'
        store = Store.open_existing(workspace)
        if type(store) is not Store:
            store = None; _fail('host_unavailable')
        phase = _PREFIX + 'host_unavailable'
        server = _ui.create_server(store.root, host='127.0.0.1', port=port,
            intake_reference_store=store, intake_reference_read_scope=scope)
        phase = _PREFIX + 'output_failed'; _write(sys.stdout, _ready(server))
        phase = _PREFIX + 'unavailable'; server.serve_forever()
    except KeyboardInterrupt:
        pass
    except Exception as error:
        first[0] = _code(error, phase)
    finally:
        while True:
            try: _cleanup(server, store, first); break
            except KeyboardInterrupt: continue
    emitted = False
    while True:
        try:
            if first[0] is None: return 0
            if not emitted:
                emitted = True; _emit_error(first[0])
            return 2 if first[0] in {_PREFIX + 'invalid_argument','store_open_invalid_argument','store_open_path_invalid'} else 1
        except KeyboardInterrupt:
            continue


def _process_main():
    """Only this module process configures UTF8/LF and avoids a second failed flush."""
    try:
        for stream in (sys.stdout, sys.stderr):
            try: stream.reconfigure(encoding='utf-8', errors='strict', newline='\n')
            except Exception: pass
        status = main()
    except KeyboardInterrupt:
        status = 0
    for stream in (sys.stdout, sys.stderr):
        while True:
            try: stream.flush(); break
            except KeyboardInterrupt: continue
            except Exception:
                if status == 0:
                    status = 1; _emit_error(_PREFIX + 'output_failed')
                # main has already drained the owned host and closed its Store.
                # A failed interpreter flush must not change the fixed status to120.
                os._exit(status)
    return status


if __name__ == '__main__':
    raise SystemExit(_process_main())

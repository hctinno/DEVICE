"""Bounded, opt-in ADB *host* protocol subset for an existing synthetic Fleet.

No adbd/Android OS, device discovery, SDK, USB, host shell or network fallback.
Protocol reference: pinned AOSP docs/dev/overview.md (client/server section).
"""
from collections import deque
import json
import math
import re
import socket
import threading
import time
import uuid

from .virtual_fleet.core import VirtualFleet

SERIAL = 'DGM-VIRTUAL-001'
MAX_FRAME = 4096
MAX_RESPONSE = 32768
MAX_CONNECTIONS = 128
MAX_ACTIVE = 4
MAX_ACTIONS = 64
SOURCE_FIELDS = frozenset({'frequency_hz', 'power_dbm', 'bandwidth_hz',
                           'duty_cycle', 'modulation', 'crest_factor_db'})
PROPERTIES = {'ro.product.model': 'DGM Virtual DUT',
              'ro.product.manufacturer': 'DGM Synthetic',
              'ro.serialno': SERIAL, 'ro.dgm.runtime': 'VirtualFleet'}


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False)


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON field')
        result[key] = value
    return result


class VirtualAdbHost:
    """Single-use server borrowing a trusted Fleet; explicit port=0 is required.

    Only the OS-selected loopback ephemeral endpoint is owned. Closing this
    server closes its sockets/threads, not the caller's Fleet. Author controls
    are never exposed. This Python API is not a sandbox for untrusted Python.
    """

    def __init__(self, fleet, *, port, connection_timeout=1.0, lifetime=30.0):
        if type(port) is not int or port != 0:
            raise ValueError('only explicit port=0 (own ephemeral listener) is allowed')
        for value, upper in [(connection_timeout, 3), (lifetime, 60)]:
            if type(value) not in (int, float) or not math.isfinite(value) or not .05 <= value <= upper:
                raise ValueError('invalid bounded timeout/lifetime')
        if not isinstance(fleet, VirtualFleet):
            raise ValueError('an existing VirtualFleet is required')
        devices = fleet.coverage()['devices']
        if any(devices.get(name, {}).get('role') != role for name, role in
               [('dut', 'dut'), ('sensor', 'power_sensor'), ('meter', 'power_meter')]):
            raise ValueError('explicit dut/sensor/meter fixture bindings required')
        self._fleet = fleet
        self._timeout, self._lifetime = connection_timeout, lifetime
        self._lock, self._fleet_lock = threading.RLock(), threading.RLock()
        self._stop = threading.Event()
        self._sockets, self._workers = set(), set()
        self._events = deque(maxlen=128)
        self._listener = self._thread = None
        self._endpoint = None
        self._entered = False
        self._connections = self._actions = 0
        self._prefix = 'adb:' + uuid.uuid4().hex

    @property
    def endpoint(self):
        if self._endpoint is None:
            raise RuntimeError('server is not started')
        return self._endpoint

    def trace(self):
        with self._lock:
            return json.loads(_json(list(self._events)))

    def resources(self):
        with self._lock:
            return {'active_connections': len(self._sockets),
                    'active_workers': sum(t.is_alive() for t in self._workers),
                    'thread_alive': bool(self._thread and self._thread.is_alive()),
                    'connections_total': self._connections,
                    'actions_total': self._actions}

    def _record(self, outcome, **values):
        with self._lock:
            self._events.append({'outcome': outcome, **values})

    def __enter__(self):
        if self._entered:
            raise RuntimeError('server is single-use')
        self._entered = True
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            listener.bind(('127.0.0.1', 0))
            self._endpoint = listener.getsockname()
            if self._endpoint[1] == 5037:
                raise RuntimeError('reserved native ADB endpoint rejected')
            listener.listen(MAX_ACTIVE)
            listener.settimeout(.05)
            self._listener = listener
            self._deadline = time.monotonic() + self._lifetime
            self._thread = threading.Thread(target=self._serve, name='dgm-virtual-adb-host', daemon=True)
            self._thread.start()
        except BaseException:
            listener.close()
            raise
        return self

    def _serve(self):
        try:
            while not self._stop.is_set() and time.monotonic() < self._deadline:
                try:
                    peer, _ = self._listener.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break
                with self._lock:
                    if len(self._sockets) >= MAX_ACTIVE or self._connections >= MAX_CONNECTIONS:
                        peer.close()
                        self._record('capacity_rejected')
                        continue
                    self._connections += 1
                    self._sockets.add(peer)
                    worker = threading.Thread(target=self._handle, args=(peer,),
                                              name='dgm-virtual-adb-peer', daemon=True)
                    self._workers.add(worker)
                    worker.start()
        finally:
            self._stop.set()
            self._listener.close()
            with self._lock:
                peers = list(self._sockets)
            for peer in peers:
                self._close_socket(peer)

    @staticmethod
    def _close_socket(peer):
        try:
            peer.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        peer.close()

    def close(self):
        self._stop.set()
        if self._listener:
            self._listener.close()
        with self._lock:
            peers = list(self._sockets)
        for peer in peers:
            self._close_socket(peer)
        if self._thread:
            self._thread.join(1)
        with self._lock:
            workers = list(self._workers)
        for worker in workers:
            worker.join(1)
        if self.resources()['thread_alive'] or self.resources()['active_workers']:
            raise RuntimeError('virtual server cleanup incomplete')

    def __exit__(self, kind, value, traceback):
        self.close()

    def _frame(self, peer, deadline):
        def read(size):
            data = b''
            while len(data) < size:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise ValueError('frame timeout')
                peer.settimeout(remaining)
                block = peer.recv(size - len(data))
                if not block:
                    raise ValueError('truncated frame')
                data += block
            return data
        header = read(4)
        if re.fullmatch(b'[0-9a-fA-F]{4}', header) is None:
            raise ValueError('malformed length')
        size = int(header, 16)
        if not 1 <= size <= MAX_FRAME:
            raise ValueError('frame length outside limit')
        return read(size).decode('utf-8', errors='strict')

    @staticmethod
    def _block(data):
        if len(data) > MAX_RESPONSE:
            raise ValueError('response outside limit')
        return f'{len(data):04x}'.encode() + data

    def _handle(self, peer):
        deadline = min(time.monotonic() + self._timeout, self._deadline)
        try:
            service = self._frame(peer, deadline)
            self._record('request', service=service)
            if service == 'host:version':
                # Compatibility level 40 selects the documented legacy
                # host:transport path in pinned adbutils, not a real SDK build.
                peer.sendall(b'OKAY' + self._block(b'0028'))
            elif service == f'host-serial:{SERIAL}:get-state':
                peer.sendall(b'OKAY' + self._block(b'device'))
            elif service == 'host:transport:' + SERIAL:
                peer.sendall(b'OKAY')
                service = self._frame(peer, deadline)
                self._record('request', service=service)
                if not service.startswith('shell:'):
                    raise ValueError('unsupported selected service')
                with self._fleet_lock:
                    output = self._shell(service[6:]).encode('utf-8')
                if len(output) > MAX_RESPONSE:
                    raise ValueError('response outside limit')
                peer.sendall(b'OKAY' + output)
            else:
                raise ValueError('unknown serial or unsupported service')
        except (ValueError, UnicodeError, OSError, RecursionError) as exc:
            self._record('protocol_error', error_type=type(exc).__name__, reason=str(exc)[:200])
            try:
                peer.settimeout(.05)
                peer.sendall(b'FAIL' + self._block(b'DGM virtual request rejected'))
            except OSError:
                pass
        finally:
            self._close_socket(peer)
            with self._lock:
                self._sockets.discard(peer)
                self._workers.discard(threading.current_thread())

    def _request_id(self):
        if self._actions >= MAX_ACTIONS:
            raise ValueError('virtual action budget exhausted')
        self._actions += 1
        return self._prefix + ':' + str(self._actions)

    def _execute(self, device, action, parameters=None):
        return self._fleet.execute(self._request_id(), device, action, parameters)

    def _shell(self, command):
        # Exact parser; no shlex, eval, subprocess, shell expansion or fallback.
        if command.startswith('getprop '):
            name = command[8:]
            if name not in PROPERTIES:
                raise ValueError('unsupported synthetic property')
            return PROPERTIES[name] + '\n'
        if command.startswith('dgm-twin rf configure '):
            text = command[len('dgm-twin rf configure '):]
            source = json.loads(text, object_pairs_hook=_unique,
                                parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
            if type(source) is not dict or set(source) != SOURCE_FIELDS:
                raise ValueError('exact six source fields required')
            reply = self._execute('dut', 'configure', source)
        elif command == 'dgm-twin rf start':
            reply = self._execute('dut', 'start')
        elif command == 'dgm-twin rf stop':
            reply = self._execute('dut', 'stop')
        elif command == 'dgm-twin rf status':
            reply = self._fleet.observations()['devices']['dut']
        elif command == 'dgm-twin measurement acquire':
            # The conducted fixture's sensor samples continuously. Restarting
            # it here would invalidate the very input the meter must acquire.
            reply = {'meter': self._execute('meter', 'acquire'),
                     'sensor': self._fleet.observations()['devices']['sensor']}
        elif command == 'dgm-twin measurement read':
            reply = {'meter': self._execute('meter', 'fetch'),
                     'sensor': self._fleet.observations()['devices']['sensor']}
        elif re.fullmatch(r'dgm-twin advance ([1-9]|1[0-6])', command):
            reply = self._fleet.advance(self._request_id(), int(command.rsplit(' ', 1)[1]))
        else:
            raise ValueError('unsupported DGM virtual extension')
        return _json(reply) + '\n'

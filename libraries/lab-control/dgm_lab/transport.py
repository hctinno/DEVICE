"""Explicit-address, bounded ASCII transports. Never discover or retry instruments."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import math
import socket
import threading
import time
from typing import Callable


class CommunicationError(RuntimeError):
    pass


def positive_timeout(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise ValueError('timeout must be finite and positive')
    return float(value)


class JsonlLog:
    """Caller owns the destination; raw command/response logs can contain identifiers."""
    def __init__(self, path):
        self.file = open(path, 'a', encoding='utf-8')
        self.lock = threading.Lock()

    def __call__(self, record):
        with self.lock:
            self.file.write(json.dumps(record, ensure_ascii=False) + '\n')
            self.file.flush()

    def close(self):
        self.file.close()


class Transport:
    """One session lock covers entire driver operations as well as query pairs.

    Any uncertain I/O poisons the session. Closing a connection is NOT RF OFF.
    A fresh, deliberately opened recovery connection is needed after a timeout.
    """
    def __init__(self, resource, timeout=10.0, log: Callable | None = None):
        self.resource = resource
        self.timeout = positive_timeout(timeout)
        self.log = log
        self.lock = threading.RLock()
        self.closed = False
        self.poisoned = False

    def _record(self, direction, payload):
        if self.log:
            self.log(dict(utc=datetime.now(timezone.utc).isoformat(),
                          monotonic_ns=time.monotonic_ns(), resource=self.resource,
                          direction=direction, payload=payload))

    def _check(self):
        if self.closed or self.poisoned:
            raise CommunicationError('Session closed or desynchronized; open a new connection')

    @staticmethod
    def _command(command):
        if not isinstance(command, str) or not command.strip() or any(c in command for c in '\r\n\x00'):
            raise ValueError('Expected one nonempty command without line terminators')
        command.encode('ascii', errors='strict')
        return command

    @contextmanager
    def transaction(self):
        with self.lock:
            self._check()
            yield self

    def write(self, command):
        command = self._command(command)
        if '?' in command:
            raise ValueError('A query must use query() so its reply is consumed')
        with self.transaction():
            try:
                self._record('tx', command)
                self._write(command)
            except BaseException:
                self.poisoned = True
                raise

    def query(self, command):
        command = self._command(command)
        with self.transaction():
            try:
                self._record('tx', command)
                self._write(command)
                answer = self._read()
                self._record('rx', answer)
                return answer.strip()
            except BaseException:
                self.poisoned = True
                raise

    def close(self):
        with self.lock:
            if not self.closed:
                self._close()
                self.closed = True

    def __enter__(self):
        self._check()
        return self

    def __exit__(self, *args):
        self.close()


class SocketTransport(Transport):
    """Raw ASCII socket, NOT VXI-11/HiSLIP. Use VISA for INSTR resources."""
    def __init__(self, host, port, *, timeout=10.0, termination=b'\n', max_bytes=4_000_000, log=None):
        if not isinstance(host, str) or not host.strip():
            raise ValueError('Explicit host required')
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError('port must be 1..65535')
        if termination not in (b'\n', b'\r', b'\r\n'):
            raise ValueError('Unsupported termination')
        if type(max_bytes) is not int or max_bytes < 16:
            raise ValueError('max_bytes must be >=16')
        super().__init__(f'tcp://{host}:{port}', timeout, log)
        self.termination = termination
        self.max_bytes = max_bytes
        self.socket = socket.create_connection((host, port), self.timeout)
        self.socket.settimeout(self.timeout)
        self.buffer = bytearray()

    def _write(self, command):
        self.socket.sendall(command.encode('ascii') + self.termination)

    def _read(self):
        deadline = time.monotonic() + self.timeout
        try:
            while True:
                end = self.buffer.find(self.termination)
                if end >= 0:
                    if end > self.max_bytes:
                        raise CommunicationError('Response exceeds max_bytes')
                    result = bytes(self.buffer[:end])
                    del self.buffer[:end + len(self.termination)]
                    if self.buffer:
                        raise CommunicationError('Unsolicited/trailing response; stream desynchronized')
                    return result.decode('ascii', errors='strict')
                if len(self.buffer) > self.max_bytes:
                    raise CommunicationError('Response exceeds max_bytes')
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError('Instrument response deadline expired')
                self.socket.settimeout(remaining)
                block = self.socket.recv(min(65536, self.max_bytes + 2))
                if not block:
                    raise CommunicationError('Instrument disconnected before response terminator')
                self.buffer.extend(block)
        finally:
            self.socket.settimeout(self.timeout)

    def _close(self):
        self.socket.close()


class VisaTransport(Transport):
    """GPIB/USB-TMC/VXI-11/HiSLIP/ASRL through an installed VISA implementation."""
    def __init__(self, resource, *, timeout=10.0, backend=None, termination='\n',
                 resource_options=None, log=None):
        if not isinstance(resource, str) or '::' not in resource:
            raise ValueError('Explicit VISA resource required')
        if termination not in ('\n', '\r', '\r\n'):
            raise ValueError('Unsupported termination')
        super().__init__(resource, timeout, log)
        import pyvisa
        self.manager = pyvisa.ResourceManager() if backend is None else pyvisa.ResourceManager(backend)
        self.instrument = None
        try:
            self.instrument = self.manager.open_resource(resource, **(resource_options or {}))
            self.instrument.timeout = int(self.timeout * 1000)
            self.instrument.read_termination = termination
            self.instrument.write_termination = termination
        except BaseException:
            try:
                if self.instrument is not None:
                    self.instrument.close()
            finally:
                self.manager.close()
            raise

    def _write(self, command):
        self.instrument.write(command)

    def _read(self):
        return self.instrument.read()

    def _close(self):
        try:
            self.instrument.close()
        finally:
            self.manager.close()


class SerialTransport(Transport):
    """Serial settings must come from the installed controller, not a brand default."""
    def __init__(self, port, *, baudrate, parity, bytesize, stopbits, timeout=10.0,
                 termination=b'\r\n', max_bytes=65536, log=None):
        if termination not in (b'\r', b'\n', b'\r\n'):
            raise ValueError('Unsupported termination')
        if type(max_bytes) is not int or max_bytes < 16:
            raise ValueError('max_bytes must be >=16')
        super().__init__(port, timeout, log)
        import serial
        self.serial = serial.Serial(port=port, baudrate=baudrate, parity=parity,
                                    bytesize=bytesize, stopbits=stopbits, timeout=self.timeout,
                                    write_timeout=self.timeout)
        self.termination = termination
        self.max_bytes = max_bytes

    def _write(self, command):
        data = command.encode('ascii') + self.termination
        if self.serial.write(data) != len(data):
            raise CommunicationError('Incomplete serial write')

    def _read(self):
        data = self.serial.read_until(self.termination, self.max_bytes)
        if not data.endswith(self.termination):
            raise CommunicationError('Missing serial response terminator (timeout/oversize)')
        return data[:-len(self.termination)].decode('ascii')

    def _close(self):
        self.serial.close()

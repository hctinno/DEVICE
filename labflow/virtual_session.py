"""Versioned JSON replay sessions for the synthetic, offline VirtualLab.

Checkpoints contain private scenario controls. Give operators/AI only execute()
results and observations(), never checkpoint bytes or the author control API.
This is an API boundary, not a sandbox for code with filesystem/Python access.
"""
import hashlib
import json
import os
from pathlib import Path
import random
import re
import sys
import tempfile
import threading

from . import virtual_lab


SCHEMA_VERSION = 2
MAX_EVENTS = 5000
MAX_FILE_BYTES = 16 * 1024 * 1024
_PRIVATE_ROOT = Path(__file__).resolve().parents[1] / '.local'
_OPERATOR_ACTIONS = {
    'configure_dut': {'mode', 'channel', 'power_dbm'},
    'set_path': {'connected', 'loss_db'},
    'start_tx': set(),
    'stop_tx': set(),
    'meter': {'command'},
    'advance': {'ticks'},
}
_AUTHOR_ACTIONS = {'inject_fault': {'name', 'value'}, 'set_path': {'connected', 'loss_db'}}
_BODY_KEYS = {'schema_version', 'engine', 'session_id', 'config', 'events',
              'synthetic', 'hardware_verified'}
_EVENT_KEYS = {'sequence', 'request_id', 'kind', 'action', 'arguments', 'result'}


class SessionError(RuntimeError):
    """Session cannot safely perform the requested operation."""


class SessionLockedError(SessionError):
    """Another owner holds this session's OS lock."""


class SessionStorageError(SessionError):
    """I/O failed; close and reopen before deciding whether to retry an ID."""


class SessionCorruptError(SessionError):
    """Invalid or changed checkpoint; the source was not overwritten."""


class SessionVersionError(SessionError):
    """Checkpoint format or replay engine is incompatible."""


class RequestConflictError(SessionError):
    """An existing request ID was reused with different content."""


def _encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def _copy(value):
    return json.loads(_encode(value))


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError('nonfinite JSON number')


def _engine():
    return {
        'profile_id': virtual_lab.VirtualLab.profile_id,
        'source_sha256': hashlib.sha256(Path(virtual_lab.__file__).read_bytes()).hexdigest(),
        'python': [sys.version_info.major, sys.version_info.minor],
        'rng_version': random.Random.VERSION,
    }


def _request(request_id, kind, action, arguments):
    if (type(request_id) is not str or len(request_id) > 128
            or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]*', request_id) is None):
        raise ValueError('request_id must be 1..128 ASCII identifier characters')
    allowed = _OPERATOR_ACTIONS if kind == 'operator' else _AUTHOR_ACTIONS
    if kind not in ('operator', 'author') or type(action) is not str or action not in allowed:
        raise ValueError('action is not allowed for this interface')
    if type(arguments) is not dict or set(arguments) != allowed[action]:
        raise ValueError('arguments do not match the allowed action')
    if any(type(value) not in (str, int, float, bool, type(None))
           for value in arguments.values()):
        raise ValueError('arguments must be JSON scalars')
    request = {'request_id': request_id, 'kind': kind, 'action': action,
               'arguments': arguments}
    try:
        if len(_encode(request)) > 4096:
            raise ValueError('request exceeds 4096 bytes')
    except (UnicodeError, OverflowError) as exc:
        raise ValueError('request is not valid finite JSON') from exc
    return _copy(request)


def _dispatch(lab, request):
    # The caller has validated the name against a closed set; no arbitrary
    # attribute, code, network or hardware dispatch is available.
    result = getattr(lab, request['action'])(**request['arguments'])
    return result if request['kind'] == 'operator' else None


def _replay(body):
    config = body['config']
    if type(config) is not dict or set(config) != {'seed', 'measurement_ticks', 'noise_db'}:
        raise ValueError('invalid configuration')
    lab = virtual_lab.VirtualLab(**config)
    events = body['events']
    if type(events) is not list or len(events) > MAX_EVENTS:
        raise ValueError('invalid event count')
    seen = {}
    legacy_ids = set()
    for sequence, event in enumerate(events, 1):
        if (type(event) is not dict or set(event) != _EVENT_KEYS
                or type(event['sequence']) is not int or event['sequence'] != sequence):
            raise ValueError('invalid event structure or sequence')
        request = _request(event['request_id'], event['kind'], event['action'], event['arguments'])
        key = (request['kind'], request['request_id'])
        if key in seen or (body['schema_version'] == 1 and request['request_id'] in legacy_ids):
            raise ValueError('duplicate stored request ID')
        result = _dispatch(lab, request)
        if _encode(result) != _encode(event['result']):
            raise ValueError('replay result differs from stored result')
        seen[key] = event
        legacy_ids.add(request['request_id'])
    return lab, seen


def _plain_path(path):
    # Resolve junctions as well as symbolic links. The session ID is a filename,
    # never a caller-supplied relative or absolute path.
    if path.is_symlink() or path.resolve() != path:
        raise ValueError('session paths must not redirect through links')


class VirtualSession:
    """Single writer replay session. Construct with create() or open().

    Each successful request is committed before its result is returned.
    Identical retries return their original observation (including original
    tick); a new request ID is needed to observe the current tick.
    """

    @classmethod
    def _allocate(cls, session_id, storage_root):
        if (type(session_id) is not str or len(session_id) > 64
                or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', session_id) is None
                or re.fullmatch(r'(?i:CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])', session_id)):
            raise ValueError('session_id must be a safe 1..64 ASCII filename')
        _plain_path(_PRIVATE_ROOT)
        from .development_paths import load_layout, reference_path
        allowed = reference_path(_PRIVATE_ROOT) if storage_root is not None else load_layout().directory('runs')
        root = reference_path(Path(storage_root).absolute()) if storage_root is not None else allowed / 'virtual_sessions'
        _plain_path(allowed)
        root = root.resolve()
        if not root.is_relative_to(allowed):
            raise ValueError('storage_root must be inside the selected private storage root')
        root.mkdir(parents=True, exist_ok=True)
        obj = cls.__new__(cls)
        obj._mutex = threading.RLock()
        obj._root = root
        obj._path = root / (session_id + '.session.json')
        obj._session_id = session_id
        obj._lock_fd = None
        obj._failed = False
        obj._pid = os.getpid()
        lock_path = root / (session_id + '.lock')
        _plain_path(obj._path)
        _plain_path(lock_path)
        try:
            fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        except OSError as exc:
            raise SessionStorageError('cannot open session lock') from exc
        try:
            if os.name == 'nt':
                import msvcrt
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            os.close(fd)
            raise SessionLockedError('session already has a writer') from exc
        obj._lock_fd = fd
        return obj

    @classmethod
    def create(cls, session_id, *, storage_root=None, seed=0, measurement_ticks=2, noise_db=0.0):
        config = {'seed': seed, 'measurement_ticks': measurement_ticks, 'noise_db': noise_db}
        lab = virtual_lab.VirtualLab(**config)  # Validate before creating any files.
        obj = cls._allocate(session_id, storage_root)
        try:
            if obj._path.exists():
                raise FileExistsError('session already exists; use open()')
            obj._body = {'schema_version': SCHEMA_VERSION, 'engine': _engine(),
                         'session_id': session_id, 'config': _copy(config), 'events': [],
                         'synthetic': True, 'hardware_verified': False}
            obj._lab, obj._seen = lab, {}
            obj._persist(obj._body)
            return obj
        except BaseException:
            obj.close()
            raise

    @classmethod
    def open(cls, session_id, *, storage_root=None):
        obj = cls._allocate(session_id, storage_root)
        try:
            raw = obj._read()
            try:
                document = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs,
                                      parse_constant=_reject_constant)
                if type(document) is not dict or set(document) != _BODY_KEYS | {'sha256'}:
                    raise ValueError('invalid checkpoint structure')
                body = {key: value for key, value in document.items() if key != 'sha256'}
                if document['sha256'] != hashlib.sha256(_encode(body)).hexdigest():
                    raise ValueError('checkpoint checksum mismatch')
                if type(body['schema_version']) is not int:
                    raise ValueError('invalid format version')
                if body['schema_version'] not in (1, SCHEMA_VERSION) or body['engine'] != _engine():
                    raise SessionVersionError('unsupported checkpoint format or replay engine')
                if (body['session_id'] != session_id or body['synthetic'] is not True
                        or body['hardware_verified'] is not False):
                    raise ValueError('invalid session identity or provenance')
                obj._lab, obj._seen = _replay(body)
            except (ValueError, TypeError, KeyError, OverflowError, RecursionError) as exc:
                raise SessionCorruptError('checkpoint validation or replay failed') from exc
            # Reading/retrying a v1 checkpoint does not rewrite it. The next
            # accepted new event commits v2 with all prior events preserved.
            obj._body = dict(body, schema_version=SCHEMA_VERSION)
            obj._disk_hash = hashlib.sha256(raw).hexdigest()
            return obj
        except BaseException:
            obj.close()
            raise

    def _read(self):
        try:
            _plain_path(self._root)
            _plain_path(self._path)
            with self._path.open('rb') as stream:
                raw = stream.read(MAX_FILE_BYTES + 1)
        except ValueError as exc:
            raise SessionCorruptError('session path changed') from exc
        except OSError as exc:
            raise SessionStorageError('cannot read checkpoint') from exc
        if len(raw) > MAX_FILE_BYTES:
            raise SessionCorruptError('checkpoint exceeds byte limit')
        return raw

    def _ensure_usable(self):
        if self._lock_fd is None or self._failed or self._pid != os.getpid():
            raise SessionError('session is closed or uncertain; reopen before retry')
        try:
            if hashlib.sha256(self._read()).hexdigest() != self._disk_hash:
                raise SessionCorruptError('checkpoint changed outside the session')
        except SessionError:
            self._failed = True
            raise

    def _persist(self, body):
        encoded = _encode(dict(body, sha256=hashlib.sha256(_encode(body)).hexdigest())) + b'\n'
        if len(encoded) > MAX_FILE_BYTES:
            raise SessionError('checkpoint exceeds byte limit')
        try:
            _plain_path(self._root)
            _plain_path(self._path)
            fd, temporary = tempfile.mkstemp(prefix=self._session_id + '-', suffix='.tmp',
                                             dir=self._root)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self._path)
            if os.name != 'nt':
                directory = os.open(self._root, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(directory)
                finally:
                    os.close(directory)
        except (OSError, ValueError) as exc:
            # Do not delete failed candidates or guess whether a replacement
            # committed. Opening the authoritative path resolves an uncertain ID.
            self._failed = True
            raise SessionStorageError('checkpoint commit failed; close and reopen') from exc
        self._disk_hash = hashlib.sha256(encoded).hexdigest()

    def _run(self, request_id, kind, action, arguments):
        with self._mutex:
            self._ensure_usable()
            request = _request(request_id, kind, action, arguments)
            key = (kind, request_id)
            old = self._seen.get(key)
            if old is not None:
                previous = {key: old[key] for key in request}
                if _encode(previous) != _encode(request):
                    raise RequestConflictError('request ID already has different content')
                return _copy(old['result'])
            if len(self._body['events']) >= MAX_EVENTS:
                raise SessionError('session event limit reached')
            try:
                result = _dispatch(self._lab, request)
                event = dict(request, sequence=len(self._body['events']) + 1, result=_copy(result))
                body = dict(self._body, events=self._body['events'] + [event])
                self._persist(body)
            except (ValueError, TypeError, OverflowError, SessionError):
                if not self._failed:
                    self._lab, self._seen = _replay(self._body)
                raise
            except BaseException:
                self._failed = True
                raise
            self._body = body
            self._seen[key] = event
            return _copy(result)

    def execute(self, request_id, action, **arguments):
        """Execute only operator actions; every accepted result is synthetic."""
        return self._run(request_id, 'operator', action, arguments)

    def scenario_control(self, request_id, action, **arguments):
        """Trusted author only: inject_fault/set_path; never export this to AI."""
        self._run(request_id, 'author', action, arguments)

    def observations(self):
        """Return only operator inputs/observations, without configuration/truth."""
        with self._mutex:
            self._ensure_usable()
            events = [{'request_id': event['request_id'], 'action': event['action'],
                       'arguments': event['arguments'], 'observation': event['result']}
                      for event in self._body['events'] if event['kind'] == 'operator']
            return _copy({'schema_version': SCHEMA_VERSION, 'synthetic': True,
                          'hardware_verified': False, 'events': events})

    def close(self):
        """Release the OS lock; keep the stable lock file to avoid inode races."""
        with self._mutex:
            if self._lock_fd is not None:
                os.close(self._lock_fd)
                self._lock_fd = None

    def __enter__(self):
        with self._mutex:
            self._ensure_usable()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

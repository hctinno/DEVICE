"""Secret-free local Vertex profiles and detached run settings snapshots.

No authentication, SDK, environment discovery, network or model calls occur here.
The caller supplies an existing private directory on a local filesystem.
"""
from contextlib import contextmanager
import errno
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import tempfile


_MODELS = ('gemini-4-argon', 'gemini-3.8-flash')
_PROJECT = 'project-a6310591-f8cc-487c-9e3'
_PROFILE_KEYS = {'schema_version', 'profile_id', 'provider', 'project_id', 'location',
                 'quota_project_id', 'auth_profile_id', 'selected_model', 'models', 'revision'}
_SETTING_KEYS = {'thinking_level', 'max_output_tokens', 'timeout_seconds'}
_LABEL = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z')
_PROJECT_LABEL = re.compile(r'[a-z0-9](?:[a-z0-9-]{0,126}[a-z0-9])?\Z')
_MAX_REVISION = 9007199254740991
_MAX_BYTES = 16384


class AIConnectionProfileError(ValueError):
    """Fixed code only: no supplied values, paths or underlying error text."""

    def __init__(self, code):
        self.code = 'ai_connection_profile_' + code
        super().__init__(self.code)


def _fail(code):
    raise AIConnectionProfileError(code)


def _invoke(call, *args, **kwargs):
    try:
        return call(*args, **kwargs)
    except AIConnectionProfileError:
        raise
    except Exception:
        # Raise outside the handler so raw filesystem exceptions are not retained.
        pass
    _fail('storage_error')


def _keys(value, expected, *, partial=False):
    if type(value) is not dict or any(type(key) is not str for key in value):
        _fail('invalid_profile')
    keys = set(value)
    if not (keys <= expected if partial else keys == expected):
        _fail('invalid_profile')


def _choice(value, choices):
    if type(value) is not str or value not in choices:
        _fail('invalid_profile')
    return value


def _label(value, pattern):
    if type(value) is not str or not pattern.fullmatch(value):
        _fail('invalid_profile')
    return value


def _settings(value, *, partial=False):
    _keys(value, _SETTING_KEYS, partial=partial)
    result = {}
    for key, item in value.items():
        if key == 'thinking_level':
            _choice(item, ('LOW', 'MEDIUM', 'HIGH'))
        elif key == 'max_output_tokens':
            if type(item) is not int or not 64 <= item <= 8192:
                _fail('invalid_profile')
        elif type(item) not in (int, float) or not 1 <= item <= 120 or not math.isfinite(item):
            _fail('invalid_profile')
        result[key] = item
    return result


def _validate_profile(profile, *, stored=False):
    _keys(profile, _PROFILE_KEYS)
    if type(profile['schema_version']) is not int or profile['schema_version'] != 1:
        _fail('invalid_profile')
    revision = profile['revision']
    if type(revision) is not int or not (1 if stored else 0) <= revision <= _MAX_REVISION:
        _fail('invalid_profile')
    _keys(profile['models'], set(_MODELS))
    return {
        'schema_version': 1,
        'profile_id': _label(profile['profile_id'], _LABEL),
        'provider': _choice(profile['provider'], ('vertex_ai',)),
        'project_id': _label(profile['project_id'], _PROJECT_LABEL),
        'location': _choice(profile['location'], ('global', 'us', 'eu')),
        'quota_project_id': _label(profile['quota_project_id'], _PROJECT_LABEL),
        'auth_profile_id': _label(profile['auth_profile_id'], _LABEL),
        'selected_model': _choice(profile['selected_model'], _MODELS),
        'models': {model: _settings(profile['models'][model]) for model in _MODELS},
        'revision': revision,
    }


def _defaults():
    return dict(schema_version=1, profile_id='vertex-trial', provider='vertex_ai',
                project_id=_PROJECT, location='global', quota_project_id=_PROJECT,
                auth_profile_id='vertex-trial', selected_model=_MODELS[1],
                models={model: dict(thinking_level='MEDIUM', max_output_tokens=512,
                                    timeout_seconds=60) for model in _MODELS}, revision=0)


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def _unsafe_stat(info):
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, 'st_file_attributes', 0) &
                                            getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400))


def _unsafe_component(part):
    device = part.split('.', 1)[0].rstrip(' ').upper()
    return (part.endswith((' ', '.')) or any(c in part for c in ':*?"<>|') or
            device in ('CON', 'PRN', 'AUX', 'NUL', 'CONIN$', 'CONOUT$') or
            len(device) == 4 and device[:3] in ('COM', 'LPT') and device[3] in '123456789¹²³')


def _path(value):
    if not isinstance(value, (str, Path)):
        _fail('invalid_path')
    text = str(value)
    if not text or text.startswith(('\\\\', '//')) or any(ord(c) < 32 or ord(c) == 127 for c in text):
        _fail('invalid_path')
    path = Path(text)
    if '..' in path.parts or path.drive and not path.root:
        _fail('invalid_path')
    if any(_unsafe_component(part) for part in path.parts if part != path.anchor):
        _fail('invalid_path')
    path = Path(os.path.abspath(path))
    for directory in reversed(path.parents):
        try:
            info = directory.lstat()
        except FileNotFoundError:
            info = None
        if info is None or _unsafe_stat(info) or not stat.S_ISDIR(info.st_mode):
            _fail('invalid_path')
    _file_info(path)
    return path


def _file_info(path):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    if _unsafe_stat(info) or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        _fail('invalid_path')
    return info


def _open_checked(path, flags, *, create=False):
    previous = _file_info(path)
    if create:
        flags |= os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    try:
        current = _file_info(path)
        actual = os.fstat(fd)
        if (current is None or _unsafe_stat(actual) or not stat.S_ISREG(actual.st_mode) or
                actual.st_nlink != 1 or (current.st_dev, current.st_ino) != (actual.st_dev, actual.st_ino) or
                previous is not None and (previous.st_dev, previous.st_ino) != (actual.st_dev, actual.st_ino)):
            _fail('invalid_path')
    except BaseException:
        os.close(fd)
        raise
    return fd


def _try_lock(fd):
    try:
        if os.name == 'nt':
            import msvcrt
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError as exc:
        if exc.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
            raise
    return False


def _release_lock(fd, locked):
    try:
        if locked:
            if os.name == 'nt':
                import msvcrt
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


@contextmanager
def _locked(path):
    lock_path = path.with_name(path.name + '.lock')
    if _file_info(lock_path) is None:
        try:
            fd = _open_checked(lock_path, os.O_RDWR, create=True)
        except FileExistsError:
            fd = _open_checked(lock_path, os.O_RDWR)
    else:
        fd = _open_checked(lock_path, os.O_RDWR)
    locked = False
    try:
        locked = _try_lock(fd)
        if not locked:
            _fail('locked')
        if not os.fstat(fd).st_size:
            os.write(fd, b'\0')
        yield
    except BaseException:
        try:
            _release_lock(fd, locked)
        except BaseException:
            pass  # Preserve the first failure/control while always attempting close.
        raise
    else:
        _release_lock(fd, locked)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate_key')
        result[key] = value
    return result


def _no_constant(value):
    raise ValueError('nonfinite_number')


def _read(path):
    info = _file_info(path)
    if info is None:
        return _defaults()
    if info.st_size > _MAX_BYTES:
        _fail('corrupt')
    fd = _open_checked(path, os.O_RDONLY)
    with os.fdopen(fd, 'rb') as stream:
        payload = stream.read(_MAX_BYTES + 1)
    if len(payload) > _MAX_BYTES:
        _fail('corrupt')
    try:
        value = json.loads(payload.decode('utf-8'), object_pairs_hook=_unique_object,
                           parse_constant=_no_constant)
        return _validate_profile(value, stored=True)
    except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
        pass
    _fail('corrupt')


def _load(path):
    path = _path(path)
    with _locked(path):
        return _read(path)


def load_profile(path) -> dict:
    """Load a valid profile, or detached revision-0 defaults only when absent."""
    return _invoke(_load, path)


def _save(path, profile, *, expected_revision):
    if type(expected_revision) is not int or not 0 <= expected_revision <= _MAX_REVISION:
        _fail('invalid_revision')
    profile = _validate_profile(profile)
    if profile['revision'] != expected_revision:
        _fail('revision_conflict')
    path = _path(path)
    with _locked(path):
        current = _read(path)
        if current['revision'] != expected_revision:
            _fail('revision_conflict')
        if expected_revision and current['profile_id'] != profile['profile_id']:
            _fail('invalid_profile')
        if expected_revision == _MAX_REVISION:
            _fail('revision_exhausted')
        profile['revision'] += 1
        payload = _canonical(profile) + b'\n'
        temp_path = None
        fd = None
        try:
            fd, temp_path = tempfile.mkstemp(prefix='.' + path.name + '.', suffix='.tmp', dir=path.parent)
            with os.fdopen(fd, 'wb') as stream:
                fd = None
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_path, path)
            temp_path = None
            observed = _read(path)
            if observed != profile:
                _fail('storage_error')
            return observed
        finally:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
            if temp_path is not None:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass


def save_profile(path, profile, *, expected_revision) -> dict:
    """Cooperative nonblocking lock + revision CAS + same-directory atomic replace."""
    return _invoke(_save, path, profile, expected_revision=expected_revision)


def _resolve(profile, *, model_id=None, overrides=None):
    profile = _validate_profile(profile)
    selected = profile['selected_model'] if model_id is None else _choice(model_id, _MODELS)
    settings = profile['models'][selected].copy()
    if overrides is not None:
        settings.update(_settings(overrides, partial=True))
    result = dict(schema_version=1, kind='ai_run_settings', profile_id=profile['profile_id'],
                  profile_revision=profile['revision'], provider='vertex_ai',
                  service='aiplatform.googleapis.com', project_id=profile['project_id'],
                  location=profile['location'], quota_project_id=profile['quota_project_id'],
                  auth_profile_id=profile['auth_profile_id'], model_id=selected, **settings,
                  profile_sha256=hashlib.sha256(_canonical(profile)).hexdigest())
    result['settings_sha256'] = hashlib.sha256(_canonical(result)).hexdigest()
    return result


def resolve_run_settings(profile, *, model_id=None, overrides=None) -> dict:
    """Return a detached scalar-only plain dict snapshot; never save overrides."""
    return _invoke(_resolve, profile, model_id=model_id, overrides=overrides)

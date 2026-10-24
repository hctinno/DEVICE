"""Read-only, revision-bound DOCX references; no analysis or authority changes."""
from contextlib import contextmanager
import hashlib
import json
import os
import re
import stat

from .reference_docx import read_docx
from .store import Store, StoreOpenError, _ExistingBinding, canonical, identifier
from .control_packet_prepare import ControlPacketPrepareError


_PREFIX = 'intake_docx_reference_'
_CODES = frozenset('invalid_argument store_invalid intake_not_found intake_unavailable revision_changed '
                   'document_not_found source_integrity_invalid input_limit storage_error'.split())
_MANIFEST_BYTES = 4*1024*1024
_FILES = 1000
_SOURCE_BYTES = 16*1024*1024
_PATH_BYTES = 1024
_CHUNK = 64*1024
_OUTPUT_BYTES = 9*1024*1024
_SHA = re.compile(r'[a-f0-9]{64}\Z',re.ASCII)


class IntakeDocxReferenceError(ValueError):
    def __init__(self, code):
        suffix = code.removeprefix(_PREFIX) if type(code) is str else 'storage_error'
        self.code = _PREFIX+(suffix if suffix in _CODES else 'storage_error')
        super().__init__(self.code)


def _fail(code):
    raise IntakeDocxReferenceError(code)


def _sha(value):
    return type(value) is str and _SHA.fullmatch(value) is not None


def _path(value):
    return (type(value) is str and bool(value) and not value.startswith('/')
            and '\\' not in value and ':' not in value
            and not any(ord(c)<32 or ord(c)==127 for c in value)
            and all(part not in {'','.','..'} for part in value.split('/')))


def _arguments(store,intake_id,path,revision,sha):
    try:
        if type(intake_id) is not str:
            _fail('invalid_argument')
        identifier(intake_id)
        if (not _path(path) or not path.lower().endswith('.docx') or len(path.encode('utf-8'))>_PATH_BYTES
                or type(revision) is not int or revision<1 or not _sha(sha)):
            _fail('invalid_argument')
    except (ValueError,UnicodeError):
        _fail('invalid_argument')
    if type(store) is not Store:
        _fail('store_invalid')
    binding = store.__dict__.get('_existing_binding')
    if type(binding) is not _ExistingBinding or binding.state!='open':
        _fail('store_invalid')
    return binding


def _pairs(items):
    result = {}
    for key,value in items:
        if key in result:
            _fail('source_integrity_invalid')
        result[key] = value
    return result


def _selection(store,intake_id,path,revision,sha):
    with store.connection() as con:
        con.execute('PRAGMA query_only=ON')
        con.execute('BEGIN')
        row = con.execute('SELECT i.source_id,i.revision,i.status,r.fingerprint,'
            'length(CAST(r.files_json AS BLOB)) AS manifest_bytes,'
            'CASE WHEN length(CAST(r.files_json AS BLOB))<=? THEN r.files_json END AS files_json '
            'FROM intakes i LEFT JOIN intake_revisions r ON r.intake_id=i.intake_id AND r.revision=i.revision '
            'WHERE i.intake_id=?',(_MANIFEST_BYTES,intake_id)).fetchone()
        if row is None:
            _fail('intake_not_found')
        if row['revision']!=revision:
            _fail('revision_changed')
        if row['status']=='upload_incomplete':
            _fail('intake_unavailable')
        if row['status'] not in {'awaiting_analysis','analyzed','analysis_failed'}:
            _fail('source_integrity_invalid')
        if type(row['manifest_bytes']) is not int or not _sha(row['fingerprint']):
            _fail('source_integrity_invalid')
        if row['manifest_bytes']>_MANIFEST_BYTES:
            _fail('input_limit')
        try:
            identifier(row['source_id'])
            entries = json.loads(row['files_json'],object_pairs_hook=_pairs,
                                 parse_constant=lambda value:_fail('source_integrity_invalid'))
            if type(entries) is not list:
                _fail('source_integrity_invalid')
            if len(entries)>_FILES:
                _fail('input_limit')
            seen, selected = set(), None
            for item in entries:
                if (type(item) is not dict or set(item)!={'path','sha256','bytes'}
                        or not _path(item['path']) or item['path'] in seen or not _sha(item['sha256'])
                        or type(item['bytes']) is not int or item['bytes']<0):
                    _fail('source_integrity_invalid')
                seen.add(item['path'])
                if item['path']==path:
                    selected = item
            if hashlib.sha256(canonical(entries).encode('utf-8')).hexdigest()!=row['fingerprint']:
                _fail('source_integrity_invalid')
        except (ValueError,TypeError,UnicodeError,RecursionError) as error:
            if isinstance(error,IntakeDocxReferenceError):
                raise
            _fail('source_integrity_invalid')
        if selected is None:
            _fail('document_not_found')
        if selected['sha256']!=sha:
            _fail('revision_changed')
        registered = con.execute('SELECT bytes FROM blobs WHERE sha256=?',(sha,)).fetchone()
        if registered is None or type(registered['bytes']) is not int or registered['bytes']!=selected['bytes']:
            _fail('source_integrity_invalid')
        if selected['bytes']>_SOURCE_BYTES:
            _fail('input_limit')
        return {'source_id':row['source_id'],'intake_id':intake_id,'revision':revision,
                'revision_fingerprint':row['fingerprint'],'document':dict(selected)}


def _stamp(info):
    if (not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode)
            or getattr(info,'st_file_attributes',0)&0x400 or info.st_nlink!=1):
        _fail('source_integrity_invalid')
    return info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_mode


def _info(binding,path,fd=None):
    try:
        binding.tree.directory(path.parent)
        return _stamp(os.lstat(path) if fd is None else binding.backend.info(fd,directory=False))
    except (OSError,ControlPacketPrepareError):
        _fail('source_integrity_invalid')


@contextmanager
def _source(binding,path,size):
    descriptor, primary = None, None
    try:
        before = _info(binding,path)
        if before[2]!=size:
            _fail('source_integrity_invalid')
        try:
            # Official Store pins this parent directory; the native relative open rejects reparse points.
            descriptor = binding.backend.open_read(path)
        except (OSError,ControlPacketPrepareError):
            _fail('source_integrity_invalid')
        if _info(binding,path,descriptor)!=before or _info(binding,path)!=before:
            _fail('source_integrity_invalid')
        yield descriptor,before
    except BaseException as error:
        primary = error
        raise
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except BaseException:
                if primary is None:
                    raise


def _read(descriptor,size,*,retain):
    digest, chunks, count = hashlib.sha256(), [], 0
    try:
        os.lseek(descriptor,0,os.SEEK_SET)
        while True:
            chunk = os.read(descriptor,min(_CHUNK,size-count+1))
            if not chunk:
                break
            count += len(chunk)
            if count>size:
                _fail('source_integrity_invalid')
            digest.update(chunk)
            if retain:
                chunks.append(chunk)
    except OSError:
        _fail('source_integrity_invalid')
    if count!=size:
        _fail('source_integrity_invalid')
    return digest.hexdigest(),b''.join(chunks) if retain else None


def _read_reference(store,intake_id,path,revision,sha):
    binding = _arguments(store,intake_id,path,revision,sha)
    selected = _selection(store,intake_id,path,revision,sha)
    item = selected['document']
    source_path = store.blob_path(sha)
    with _source(binding,source_path,item['bytes']) as (descriptor,before):
        actual,payload = _read(descriptor,item['bytes'],retain=True)
        if actual!=sha or _info(binding,source_path,descriptor)!=before or _info(binding,source_path)!=before:
            _fail('source_integrity_invalid')
    result = read_docx(payload,path)
    if (type(result) is not dict or result.get('source')!={'filename':path,'sha256':sha,'size_bytes':item['bytes']}):
        _fail('source_integrity_invalid')
    with _source(binding,source_path,item['bytes']) as (descriptor,after):
        if after!=before:
            _fail('source_integrity_invalid')
        if (_read(descriptor,item['bytes'],retain=False)[0]!=sha
                or _info(binding,source_path,descriptor)!=before or _info(binding,source_path)!=before):
            _fail('source_integrity_invalid')
    if _selection(store,intake_id,path,revision,sha)!=selected:
        _fail('revision_changed')
    answer = {'schema_version':1,'kind':'intake_docx_reference','binding':selected,'result':result}
    if len(canonical(answer).encode('utf-8'))>_OUTPUT_BYTES:
        _fail('input_limit')
    return answer


def read_intake_docx_reference(store,intake_id: str,document_path: str,*,
                              expected_revision: int,expected_sha256: str) -> dict:
    """Read one current retained DOCX; does not admit citations or change intake state."""
    try:
        return _read_reference(store,intake_id,document_path,expected_revision,expected_sha256)
    except IntakeDocxReferenceError as error:
        code = error.code
    except (MemoryError,KeyboardInterrupt,SystemExit):
        raise
    except StoreOpenError as error:
        code = 'storage_error' if error.code=='store_open_unavailable' else 'store_invalid'
    except Exception:
        code = 'storage_error'
    raise IntakeDocxReferenceError(code) from None

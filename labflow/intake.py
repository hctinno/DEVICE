"""Validate a collector ZIP without executing it or trusting its review claims."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
from urllib.parse import urlsplit
import zipfile

from jsonschema import Draft202012Validator, FormatChecker
from .store import canonical

MAX_EXPANDED_BYTES=512*1024*1024
MAX_ENTRIES=10000
MAX_MANIFEST_BYTES=16*1024*1024


def safe_member(name):
    if not name or '\\' in name or ':' in name or '\x00' in name:
        raise ValueError('Unsafe archive path')
    path=PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or path.as_posix()!=name.rstrip('/'):
        raise ValueError('Unsafe archive path: '+name)
    return name


def import_package(store,path):
    path=Path(path)
    if not path.is_file() or path.stat().st_size>MAX_EXPANDED_BYTES:raise ValueError('Missing or oversized archive')
    archive_sha=hashlib.sha256(path.read_bytes()).hexdigest()
    schema=json.loads((Path(__file__).resolve().parents[1]/'handoff/collection_manifest.schema.json').read_text())
    try:
        with zipfile.ZipFile(path) as archive:
            entries=archive.infolist()
            if len(entries)>MAX_ENTRIES or sum(e.file_size for e in entries)>MAX_EXPANDED_BYTES:
                raise ValueError('Archive expansion limit exceeded')
            names=[e.filename for e in entries]
            if len(names)!=len(set(names)):raise ValueError('Duplicate ZIP members')
            for entry in entries:
                safe_member(entry.filename)
                if stat.S_IFMT(entry.external_attr>>16)==stat.S_IFLNK:raise ValueError('Archive links are not accepted')
            if 'manifest.json' not in names or archive.getinfo('manifest.json').file_size>MAX_MANIFEST_BYTES:
                raise ValueError('Missing or oversized manifest')
            manifest=json.loads(archive.read('manifest.json'))
            errors=list(Draft202012Validator(schema,format_checker=FormatChecker()).iter_errors(manifest))
            if errors:raise ValueError('Manifest invalid: '+errors[0].message)
            ids=set();used={'manifest.json'};payloads={}
            for doc in manifest['documents']:
                if doc['document_id'] in ids:raise ValueError('Duplicate document ID')
                ids.add(doc['document_id'])
                if doc['status']!='downloaded':continue
                member=safe_member(doc['path'])
                if member in used:raise ValueError('Duplicate payload path')
                used.add(member)
                if member not in names or archive.getinfo(member).is_dir():raise ValueError('Missing payload: '+member)
                if archive.getinfo(member).file_size!=doc['bytes']:raise ValueError('Payload size mismatch')
                for field in ['source_url','download_url']:
                    url=urlsplit(doc[field])
                    if url.scheme not in {'https','http'} or not url.netloc or url.username or url.password:
                        raise ValueError('Source URLs must be public HTTP(S) locations without credentials')
                payload=archive.read(member)
                if hashlib.sha256(payload).hexdigest()!=doc['sha256']:raise ValueError('Payload hash mismatch')
                if (member.lower().endswith('.pdf') or doc['media_type']=='application/pdf') and not payload.startswith(b'%PDF-'):
                    raise ValueError('PDF payload does not contain a PDF header')
                payloads[member]=payload
            if {e.filename for e in entries if not e.is_dir()}!=used:raise ValueError('Unlisted archive files')
    except (zipfile.BadZipFile,KeyError,UnicodeError,json.JSONDecodeError) as exc:
        raise ValueError('Unreadable material package: '+str(exc)) from exc

    package_id=manifest['package_id']
    summary={'package_id':package_id,'downloaded':len(payloads),'unavailable':len(manifest['documents'])-len(payloads),'already_imported':False}
    with store.connection() as con:
        con.execute('BEGIN IMMEDIATE')
        existing=con.execute('SELECT * FROM packages WHERE package_id=?',(package_id,)).fetchone()
        if existing:
            if existing['sha256']!=archive_sha:raise ValueError('Package ID already used for a different archive')
            # Even an idempotent retry must not hide damaged retained evidence.
            for doc in manifest['documents']:
                if doc['status']=='downloaded':store.verify_blob(doc['sha256'])
            return {**json.loads(existing['summary_json']),'already_imported':True}
        for doc in manifest['documents']:
            old=con.execute('SELECT record_json,synthetic FROM documents WHERE document_id=?',(doc['document_id'],)).fetchone()
            if old and (old['record_json']!=canonical(doc) or bool(old['synthetic'])!=bool(manifest.get('synthetic',False))):
                raise ValueError('Document ID conflict: use a distinct revision ID')
        con.execute('INSERT INTO packages VALUES(?,?,?)',(package_id,archive_sha,canonical(summary)))
        for doc in manifest['documents']:
            sha=None
            if doc['status']=='downloaded':
                sha=store.write_blob(payloads[doc['path']])
                con.execute('INSERT OR IGNORE INTO blobs VALUES(?,?,?)',(sha,doc['bytes'],doc['kind']))
            con.execute('INSERT OR IGNORE INTO documents(document_id,package_id,sha256,record_json,synthetic) VALUES(?,?,?,?,?)',
                        (doc['document_id'],package_id,sha,canonical(doc),int(manifest.get('synthetic',False))))
        store.event(con,'package.import',package_id,summary)
    return summary

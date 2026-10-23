"""Read-only folder discovery and immutable, unclassified intake revisions.

A direct child directory is an upload bundle, not proof of product identity.
This module never creates measurement cases, assigns a market, or operates DUTs.
"""
import hashlib
import math
import os
from pathlib import Path
import stat
import time
import uuid

from .store import canonical, identifier
import json

EXCLUDED_DIRS = {'.git', '.local', '.venv', '__pycache__', 'blobs',
                 'output', 'outputs', 'reports', 'exports'}
TEMP_SUFFIXES = {'.tmp', '.part', '.partial', '.crdownload', '.download'}
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_BUNDLE_BYTES = 128 * 1024 * 1024
MAX_FILES = 1000


def timestamp(value=None):
    value = time.time() if value is None else value
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError('Expected a finite nonnegative timestamp')
    return value


def _linked(path):
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, 'st_file_attributes', 0) & 0x400)


def _plain_path(path):
    path = Path(os.path.abspath(path))
    if any(_linked(p) for p in (path, *path.parents)):
        raise ValueError('Input paths must not traverse links or junctions')
    return path


def register_source(store, source_id, root, *, synthetic, settle_seconds=5):
    identifier(source_id)
    root = _plain_path(root)
    if not root.is_dir():
        raise ValueError('Input root must be an existing directory')
    if root == store.root or root in store.root.parents or store.root in root.parents:
        raise ValueError('Input and state/output storage must be separate')
    if not isinstance(synthetic, bool):
        raise ValueError('Declare synthetic provenance explicitly')
    timestamp(settle_seconds)
    if settle_seconds <= 0:
        raise ValueError('A positive settle period is required')
    record = {'source_id': source_id, 'root': str(root), 'synthetic': int(synthetic),
              'settle_seconds': settle_seconds}
    with store.connection() as con:
        con.execute('BEGIN IMMEDIATE')
        old = con.execute('SELECT * FROM intake_sources WHERE source_id=?', (source_id,)).fetchone()
        if old:
            if dict(old) != record:
                raise ValueError('Source configuration is immutable; use a new source ID')
            return record
        for row in con.execute('SELECT root FROM intake_sources'):
            other = Path(row['root'])
            if root == other or root in other.parents or other in root.parents:
                raise ValueError('Input sources must not overlap')
        con.execute('INSERT INTO intake_sources VALUES(:source_id,:root,:synthetic,:settle_seconds)', record)
        store.event(con, 'intake.source_registered', source_id, {'synthetic': synthetic})
    return record


def _inventory(folder):
    entries, issues = [], []
    def visit(directory):
        for path in sorted(directory.iterdir()):
            relative = path.relative_to(folder).as_posix()
            info = path.lstat()
            if _linked(path):
                issues.append({'path': relative, 'reason': 'link_not_followed'})
            elif stat.S_ISDIR(info.st_mode):
                if path.name.lower() not in EXCLUDED_DIRS and not path.name.startswith('.'):
                    visit(path)
            elif not stat.S_ISREG(info.st_mode):
                issues.append({'path': relative, 'reason': 'not_regular_file'})
            elif path.suffix.lower() in TEMP_SUFFIXES or path.name.startswith('~$') or path.name.endswith('~'):
                issues.append({'path': relative, 'reason': 'copy_in_progress'})
            elif path.name.startswith('.'):
                continue
            elif info.st_size == 0 or info.st_size > MAX_FILE_BYTES:
                issues.append({'path': relative, 'reason': 'empty_or_oversized_file'})
            else:
                entries.append([relative, info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_ino])
                if len(entries) > MAX_FILES:
                    raise ValueError('Upload bundle file count limit exceeded')
    visit(folder)
    if sum(entry[1] for entry in entries) > MAX_BUNDLE_BYTES:
        raise ValueError('Upload bundle size limit exceeded')
    return entries, issues


def _digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def scan_source(store, source_id, *, now=None):
    now = timestamp(now)
    result = {'accepted': [], 'pending': [], 'issues': []}
    with store.connection() as con:
        con.execute('BEGIN IMMEDIATE')
        source = con.execute('SELECT * FROM intake_sources WHERE source_id=?', (source_id,)).fetchone()
        if source is None:
            raise ValueError('Unknown intake source')
        root = _plain_path(source['root'])
        seen = set()
        for folder in sorted(root.iterdir()):
            if _linked(folder):
                result['issues'].append({'path': folder.name, 'reason': 'link_not_followed'})
                continue
            if not folder.is_dir():
                result['issues'].append({'path': folder.name, 'reason': 'unassigned_file'})
                continue
            if folder.name.lower() in EXCLUDED_DIRS or folder.name.startswith('.'):
                continue
            bundle = folder.name
            seen.add(bundle)
            old = con.execute('SELECT * FROM intakes WHERE source_id=? AND bundle=?', (source_id, bundle)).fetchone()
            def pending(clear=False):
                result['pending'].append(bundle)
                if old:
                    con.execute("UPDATE intakes SET status='upload_incomplete' WHERE intake_id=?", (old['intake_id'],))
                if clear:
                    con.execute('DELETE FROM intake_observations WHERE source_id=? AND bundle=?', (source_id, bundle))
            try:
                entries, issues = _inventory(folder)
                result['issues'].extend({'path': bundle+'/'+item['path'], 'reason': item['reason']} for item in issues)
                if issues or not entries:
                    pending(clear=True)
                    continue
                fingerprint = _digest(entries)
                observation = con.execute('SELECT * FROM intake_observations WHERE source_id=? AND bundle=?', (source_id, bundle)).fetchone()
                if observation is None or observation['fingerprint'] != fingerprint or now < observation['stable_since']:
                    con.execute('INSERT OR REPLACE INTO intake_observations VALUES(?,?,?,?)', (source_id, bundle, fingerprint, now))
                    pending()
                    continue
                if now-observation['stable_since'] < source['settle_seconds']:
                    pending()
                    continue
                payloads = [(entry[0], _plain_path(folder/entry[0]).read_bytes()) for entry in entries]
                after, issues = _inventory(folder)
                if after != entries or issues:
                    pending(clear=True)
                    continue
            except OSError:
                result['issues'].append({'path': bundle, 'reason': 'file_changed_or_unreadable'})
                pending(clear=True)
                continue
            files = [{'path': path, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)} for path, data in payloads]
            content_hash = _digest(files)
            previous = con.execute('SELECT * FROM intake_revisions WHERE intake_id=? AND revision=?',
                                   (old['intake_id'], old['revision'])).fetchone() if old else None
            if previous and previous['fingerprint'] == content_hash:
                for item in files:
                    store.verify_blob(item['sha256'])
                if old['status'] == 'upload_incomplete':
                    con.execute("UPDATE intakes SET status=? WHERE intake_id=?",
                                ('analyzed' if old['analysis_json'] else 'awaiting_analysis', old['intake_id']))
                continue
            intake_id = old['intake_id'] if old else 'I-'+uuid.uuid4().hex
            revision = old['revision']+1 if old else 1
            synthetic = bool(source['synthetic'])
            for (_, data), item in zip(payloads, files):
                sha = store.write_blob(data)
                stored = con.execute('SELECT synthetic FROM blobs WHERE sha256=?', (sha,)).fetchone()
                synthetic = synthetic or bool(stored and stored['synthetic'])
                store.register_blob(con, sha, len(data), 'intake_document', bool(source['synthetic']))
            if not old:
                con.execute('INSERT INTO intakes(intake_id,source_id,bundle,status) VALUES(?,?,?,?)',
                            (intake_id, source_id, bundle, 'awaiting_analysis'))
            con.execute("UPDATE intakes SET revision=?,status='awaiting_analysis',analysis_json=NULL WHERE intake_id=?", (revision, intake_id))
            con.execute('INSERT INTO intake_revisions VALUES(?,?,?,?,?,?)',
                        (intake_id, revision, content_hash, canonical(files), int(synthetic), now))
            con.execute("UPDATE intake_jobs SET state='superseded' WHERE intake_id=? AND state IN ('queued','running','failed')", (intake_id,))
            job_id = 'J-'+uuid.uuid4().hex
            con.execute("INSERT INTO intake_jobs(job_id,intake_id,revision,state,created_at) VALUES(?,?,?,'queued',?)",
                        (job_id, intake_id, revision, now))
            item = {'intake_id': intake_id, 'revision': revision, 'job_id': job_id, 'kind': 'supplement' if old else 'new'}
            store.event(con, 'intake.revision_received', intake_id, item)
            result['accepted'].append(item)
        for row in con.execute('SELECT intake_id,bundle FROM intakes WHERE source_id=?', (source_id,)):
            if row['bundle'] not in seen:
                con.execute("UPDATE intakes SET status='upload_incomplete' WHERE intake_id=?", (row['intake_id'],))
                con.execute('DELETE FROM intake_observations WHERE source_id=? AND bundle=?', (source_id, row['bundle']))
                result['issues'].append({'path': row['bundle'], 'reason': 'bundle_missing'})
    return result


def intake_status(store, intake_id=None):
    with store.connection() as con:
        rows = con.execute('SELECT * FROM intakes ORDER BY source_id,bundle').fetchall() if intake_id is None else con.execute('SELECT * FROM intakes WHERE intake_id=?', (intake_id,)).fetchall()
        if intake_id is not None and not rows:
            raise ValueError('Unknown intake')
        result = []
        for row in rows:
            history = [{**dict(rev), 'files': json.loads(rev['files_json'])} for rev in con.execute(
                'SELECT * FROM intake_revisions WHERE intake_id=? ORDER BY revision', (row['intake_id'],))]
            for rev in history:
                del rev['files_json']
            result.append({'intake_id': row['intake_id'], 'source_id': row['source_id'], 'bundle': row['bundle'],
                           'revision': row['revision'], 'status': row['status'], 'delegated': bool(row['delegated']),
                           'deferred': bool(row['deferred']), 'analysis': json.loads(row['analysis_json']) if row['analysis_json'] else None,
                           'files': history[-1]['files'], 'synthetic': bool(history[-1]['synthetic']),
                           'measurement_support': 'unverified', 'history': history})
    return result if intake_id is None else result[0]

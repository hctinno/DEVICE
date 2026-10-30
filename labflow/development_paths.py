"""Managed development paths and explicit historical IO aliases.

This module creates no directory, Store, permit, history or budget. An alias
changes a filesystem lookup only; callers retain original signed/hashed values
and all existing admission and native-handle checks.
"""
import json
import ntpath
import os
from pathlib import Path
import re
import stat
import subprocess


class DevelopmentPathError(ValueError):
    def __init__(self, code):
        self.code = 'development_paths_' + code
        super().__init__(self.code)


def _fail(code):
    raise DevelopmentPathError(code)


_DIRECTORIES = ('integration', 'workspaces', 'runs', 'toolchains', 'archive')
_DEVICES = re.compile(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)', re.I)


def _segments(value):
    if (type(value) is not str or not value or '\\' in value or value.startswith('/')
            or any(not x or x in ('.', '..') or x.endswith((' ', '.'))
                or _DEVICES.match(x) or any(ord(c)<32 or c in '<>:"|?*' for c in x)
                for x in value.split('/'))):
        _fail('invalid_relative_path')
    return value.split('/')


def _absolute(value):
    if not isinstance(value, (str, os.PathLike)):
        _fail('invalid_path')
    text = os.fspath(value)
    if (type(text) is not str or not text or text.strip()!=text or text.startswith(('\\\\','//'))
            or any(ord(c)<32 for c in text)):
        _fail('invalid_path')
    # Inspect raw components before pathlib can erase '.' components.
    tail = ntpath.splitdrive(text)[1] if os.name=='nt' else text
    parts = re.split(r'[\\/]', tail)
    if any(p in ('.','..') or (p and (p.endswith((' ','.')) or _DEVICES.match(p)
            or any(c in '<>:"|?*' for c in p))) for p in parts):
        _fail('invalid_path')
    path = Path(text)
    if not path.is_absolute():
        _fail('invalid_path')
    return path


def _no_reparse(path):
    """Reject every existing ancestor; native consumers additionally hold handles."""
    for part in [*reversed(path.parents), path]:
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0)&0x400:
            _fail('reparse_path')
        if part!=path and not stat.S_ISDIR(info.st_mode):
            _fail('invalid_path')
    return path


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            _fail('layout_invalid')
        result[key] = value
    return result


def _windows_key(value):
    return ntpath.normcase(str(value).replace('/', '\\')).rstrip('\\')


class DevelopmentPaths:
    def __init__(self, root, document):
        self.root = _no_reparse(_absolute(root))
        if self.root.name!='development' or self.root.parent.name!='.local':
            _fail('layout_location')
        self.project_root = self.root.parent.parent
        if (type(document) is not dict or set(document)!={'schema_version','project_root_relative',
                'directories','workspaces','path_aliases','control_root'}
                or type(document['schema_version']) is not int or document['schema_version']!=1
                or document['project_root_relative']!='../..'
                or document['directories']!={k:k for k in _DIRECTORIES}
                or document['control_root']!='runs/control/DGMAutoLab'
                or type(document['workspaces']) is not list or type(document['path_aliases']) is not list):
            _fail('layout_invalid')
        self._document = document
        self._workspaces = []
        seen = set()
        for row in document['workspaces']:
            if (type(row) is not dict or not {'path','role'}<=set(row)
                    or set(row)-{'path','role','branch','temporary'}
                    or type(row['role']) is not str or not re.fullmatch(r'[a-z][a-z0-9_-]{0,63}', row['role'])
                    or ('temporary' in row and type(row['temporary']) is not bool)
                    or ('branch' in row and (type(row['branch']) is not str or not row['branch'].startswith('codex/')))):
                _fail('layout_invalid')
            parts = _segments(row['path'])
            if parts[0] not in ('integration','workspaces') or (parts[0]=='workspaces' and len(parts)<2):
                _fail('layout_invalid')
            target = self._managed(row['path'])
            if _windows_key(target) in seen:
                _fail('layout_invalid')
            seen.add(_windows_key(target)); self._workspaces.append((target, dict(row)))
        self._aliases = []
        seen = set()
        for row in document['path_aliases']:
            if type(row) is not dict or set(row)!={'from','to'}:
                _fail('layout_invalid')
            old = _absolute(row['from']); key = _windows_key(old)
            # An arbitrary account/cache/auth path cannot become project authority.
            normalized = str(old).replace('\\','/')
            managed_local = any(key==_windows_key(workspace/'.local') for workspace,_ in self._workspaces)
            if not (re.match(r'^[A-Za-z]:/autolab[^/]*(?:/|$)', normalized, re.I)
                    or re.match(r'^[A-Za-z]:/Users/[^/]+/AppData/Local/(?:Packages/[^/]+/LocalCache/Local/)?DGMAutoLab(?:/|$)', normalized, re.I)
                    or managed_local):
                _fail('alias_source_invalid')
            target = self._managed(row['to'])
            if managed_local and _segments(row['to'])[0]!='runs':
                _fail('alias_source_invalid')
            if key in seen:
                _fail('layout_invalid')
            seen.add(key); self._aliases.append((key,target))
        self._aliases.sort(key=lambda x:len(x[0]), reverse=True)

    def _managed(self, relative):
        parts = _segments(relative)
        if parts[0] not in _DIRECTORIES:
            _fail('outside_managed_directory')
        return _no_reparse(self.root.joinpath(*parts))

    def directory(self, kind, relative=None):
        if kind not in _DIRECTORIES:
            _fail('unknown_directory')
        if relative is not None:
            _segments(relative)
        return self._managed(kind if relative is None else kind+'/'+relative)

    def output(self, relative):
        return self.directory('runs', relative)

    def control_root(self):
        return self._managed(self._document['control_root'])

    def reference(self, value):
        original = _absolute(value)
        key = _windows_key(original)
        for old, target in self._aliases:
            if key==old or key.startswith(old+'\\'):
                suffix = str(original).replace('/','\\')[len(old):].lstrip('\\')
                result = target.joinpath(*suffix.split('\\')) if suffix else target
                return _no_reparse(result)
        if re.match(r'^[A-Za-z]:[\\/]autolab[^\\/]*(?:[\\/]|$)', str(original), re.I):
            _fail('unregistered_old_root')
        # Unmapped OS paths remain unchanged and subject to the existing caller's
        # admission/native checks. No alias is synthesized or authority issued.
        return _no_reparse(original)

    def check_workspace(self, cwd, *, role=None):
        cwd = _no_reparse(_absolute(cwd))
        if not cwd.is_dir():
            _fail('cwd_not_directory')
        matches = [(p,row) for p,row in self._workspaces if cwd==p or p in cwd.parents]
        if not matches:
            _fail('unregistered_workspace')
        root, row = max(matches, key=lambda x:len(x[0].parts))
        if role is not None and row['role']!=role:
            _fail('workspace_role_mismatch')
        return dict(workspace=str(root), role=row['role'], temporary=row.get('temporary',False))


def load_layout(start=None):
    path = _absolute(Path(__file__).parent if start is None else start)
    for candidate in [path,*path.parents]:
        if candidate.name=='development' and candidate.parent.name=='.local':
            layout = _no_reparse(candidate/'layout.json')
            try:
                before = layout.stat()
                if before.st_size>1024*1024 or not stat.S_ISREG(before.st_mode) or before.st_nlink!=1:
                    _fail('layout_invalid')
                raw = layout.read_bytes(); after = layout.stat()
                if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns):
                    _fail('layout_changed')
                value = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=_pairs)
            except FileNotFoundError:
                _fail('layout_missing')
            except (UnicodeError,json.JSONDecodeError):
                _fail('layout_invalid')
            return DevelopmentPaths(candidate,value)
    _fail('managed_ancestor_missing')


def reference_path(value):
    return load_layout().reference(value)


def check_development_workspace(cwd, *, role=None, expected_branch=None):
    layout = load_layout(cwd)
    result = layout.check_workspace(cwd, role=role)
    command = subprocess.run(['git','-C',result['workspace'],'rev-parse','--show-toplevel'],
        capture_output=True, text=True, encoding='utf-8', errors='strict', timeout=10, check=False)
    rows = command.stdout.splitlines()
    if command.returncode or len(rows)!=1 or _absolute(rows[0])!=Path(result['workspace']):
        _fail('git_workspace_mismatch')
    command = subprocess.run(['git','-C',result['workspace'],'symbolic-ref','--quiet','--short','HEAD'],
        capture_output=True, text=True, encoding='utf-8', errors='strict', timeout=10, check=False)
    if command.returncode:
        _fail('branch_mismatch')
    branch = command.stdout.strip()
    if not branch.startswith('codex/') or branch=='codex/' or (expected_branch is not None and branch!=expected_branch):
        _fail('branch_mismatch')
    return dict(status='ready', project_root=str(layout.project_root), development_root=str(layout.root),
        branch=branch, execution_authority=False, **result)

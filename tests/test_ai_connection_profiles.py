"""Local-only profile contract tests; no provider, auth or network calls."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from labflow.ai_connection_profiles import (
    AIConnectionProfileError, load_profile, resolve_run_settings, save_profile,
)


MODELS = ('gemini-4-argon', 'gemini-3.8-flash')
PROJECT = 'project-a6310591-f8cc-487c-9e3'
PROFILE_KEYS = {'schema_version', 'profile_id', 'provider', 'project_id', 'location',
                'quota_project_id', 'auth_profile_id', 'selected_model', 'models', 'revision'}
RUN_KEYS = {'schema_version', 'kind', 'profile_id', 'profile_revision', 'provider',
            'service', 'project_id', 'location', 'quota_project_id', 'auth_profile_id',
            'model_id', 'thinking_level', 'max_output_tokens', 'timeout_seconds',
            'profile_sha256', 'settings_sha256'}


def digest(value):
    data = json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')
    return hashlib.sha256(data).hexdigest()


class AIConnectionProfileTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'profile.json'

    def error(self, code, call, *args, **kwargs):
        with self.assertRaises(AIConnectionProfileError) as caught:
            call(*args, **kwargs)
        self.assertEqual(caught.exception.code, 'ai_connection_profile_' + code)
        self.assertEqual(str(caught.exception), caught.exception.code)
        self.assertIsNone(caught.exception.__cause__)
        self.assertIsNone(caught.exception.__context__)
        return caught.exception

    def test_missing_defaults_are_exact_detached_and_not_saved(self):
        profile = load_profile(self.path)
        self.assertEqual(set(profile), PROFILE_KEYS)
        self.assertEqual(profile, {
            'schema_version': 1, 'profile_id': 'vertex-trial', 'provider': 'vertex_ai',
            'project_id': PROJECT, 'quota_project_id': PROJECT, 'location': 'global',
            'auth_profile_id': 'vertex-trial', 'selected_model': MODELS[1],
            'models': {model: {'thinking_level': 'MEDIUM', 'max_output_tokens': 512,
                               'timeout_seconds': 60} for model in MODELS}, 'revision': 0,
        })
        self.assertFalse(self.path.exists())
        profile['models'][MODELS[0]]['thinking_level'] = 'LOW'
        self.assertEqual(load_profile(self.path)['models'][MODELS[0]]['thinking_level'], 'MEDIUM')

    def test_save_load_and_each_model_settings_persist_independently(self):
        profile = load_profile(self.path)
        profile['models'][MODELS[0]] = dict(thinking_level='HIGH', max_output_tokens=8192,
                                          timeout_seconds=120)
        profile['models'][MODELS[1]] = dict(thinking_level='LOW', max_output_tokens=64,
                                          timeout_seconds=1.5)
        original = copy.deepcopy(profile)
        saved = save_profile(self.path, profile, expected_revision=0)
        self.assertEqual(profile, original)
        self.assertEqual(saved['revision'], 1)
        self.assertEqual(load_profile(self.path), saved)
        saved['models'][MODELS[0]]['max_output_tokens'] = 1024
        self.assertEqual(load_profile(self.path)['models'][MODELS[0]]['max_output_tokens'], 8192)
        next_profile = load_profile(self.path)
        next_profile['selected_model'] = MODELS[0]
        next_profile = save_profile(self.path, next_profile, expected_revision=1)
        self.assertEqual(next_profile['revision'], 2)
        self.assertEqual(next_profile['models'], original['models'])

    def test_run_snapshot_uses_selection_or_override_without_mutating_saved_settings(self):
        profile = save_profile(self.path, load_profile(self.path), expected_revision=0)
        before = copy.deepcopy(profile)
        overrides = dict(thinking_level='HIGH', max_output_tokens=1024, timeout_seconds=5)
        snapshot = resolve_run_settings(profile, model_id=MODELS[0], overrides=overrides)
        self.assertEqual(set(snapshot), RUN_KEYS)
        self.assertEqual(snapshot['model_id'], MODELS[0])
        self.assertEqual(snapshot['thinking_level'], 'HIGH')
        self.assertEqual(snapshot['service'], 'aiplatform.googleapis.com')
        self.assertEqual(snapshot['provider'], 'vertex_ai')
        self.assertEqual(snapshot['schema_version'], 1)
        self.assertEqual(snapshot['kind'], 'ai_run_settings')
        self.assertEqual(snapshot['profile_id'], 'vertex-trial')
        self.assertEqual(snapshot['auth_profile_id'], 'vertex-trial')
        self.assertEqual(snapshot['location'], 'global')
        self.assertEqual(snapshot['project_id'], PROJECT)
        self.assertEqual(snapshot['quota_project_id'], PROJECT)
        self.assertEqual(snapshot['profile_revision'], 1)
        self.assertEqual(snapshot['profile_sha256'], digest(before))
        self.assertEqual(snapshot['settings_sha256'], digest({k: v for k, v in snapshot.items()
                                                              if k != 'settings_sha256'}))
        self.assertEqual(profile, before)
        self.assertEqual(load_profile(self.path), before)
        self.assertEqual(resolve_run_settings(profile)['model_id'], MODELS[1])
        self.assertEqual(resolve_run_settings(profile)['thinking_level'], 'MEDIUM')
        profile['models'][MODELS[0]]['thinking_level'] = 'LOW'
        overrides['thinking_level'] = 'LOW'
        self.assertEqual(snapshot['thinking_level'], 'HIGH')
        self.assertEqual(json.loads(json.dumps(snapshot)), dict(snapshot))
        self.assertIs(type(snapshot), dict)
        snapshot['thinking_level'] = 'LOW'
        self.assertEqual(load_profile(self.path), before)
        self.assertEqual(resolve_run_settings(before)['thinking_level'], 'MEDIUM')

    def test_revision_conflict_keeps_last_good_bytes(self):
        stale = load_profile(self.path)
        saved = save_profile(self.path, stale, expected_revision=0)
        before = self.path.read_bytes()
        self.error('revision_conflict', save_profile, self.path, stale, expected_revision=0)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(load_profile(self.path), saved)

    def saved(self):
        return save_profile(self.path, load_profile(self.path), expected_revision=0)

    def test_profile_has_exact_schema_at_every_object_level(self):
        good = self.saved()
        before = self.path.read_bytes()
        cases = []
        for key in PROFILE_KEYS:
            value = copy.deepcopy(good)
            del value[key]
            cases.append(value)
        for extra in ('credential_path', 'credentials', 'access_token', 'billing_account',
                      'api_key', 'service', 'thinking_budget', 'extra'):
            value = copy.deepcopy(good)
            value[extra] = 'PRIVATE_PROFILE_CANARY'
            cases.append(value)
        for value in (None, [], True, 'profile', {'revision': 1}):
            cases.append(value)
        for field, bad_values in {
            'schema_version': (True, 1.0, 2, '1', None),
            'provider': ('google_ai_studio', 'vertex', '', None, False),
            'location': ('us-central1', 'GLOBAL', '', None, True),
            'selected_model': ('gemini-3-flash', MODELS[0] + '-latest', '', None, True),
            'revision': (True, -1, 1.0, float('nan'), 9007199254740992),
        }.items():
            for bad in bad_values:
                value = copy.deepcopy(good)
                value[field] = bad
                cases.append(value)
        for field in ('profile_id', 'auth_profile_id', 'project_id', 'quota_project_id'):
            for bad in ('../secret', 'a/b', 'a\\b', 'a:b', 'a.b', '\x00', 'a\n', '', '한글', 'x' * 129,
                        None, True, 'PRIVATE_PROFILE_CANARY.json'):
                value = copy.deepcopy(good)
                value[field] = bad
                cases.append(value)
        for bad in ({}, {MODELS[0]: good['models'][MODELS[0]]}, [], None,
                    {**good['models'], 'gemini-3-flash': good['models'][MODELS[1]]}):
            value = copy.deepcopy(good)
            value['models'] = bad
            cases.append(value)
        for settings in ({}, None, [], {'thinking_level': 'HIGH'},
                         {**good['models'][MODELS[0]], 'thinking_budget': 1024}):
            value = copy.deepcopy(good)
            value['models'][MODELS[0]] = settings
            cases.append(value)
        for index, value in enumerate(cases):
            with self.subTest(case=index):
                self.error('invalid_profile', save_profile, self.path, value, expected_revision=1)
                self.error('invalid_profile', resolve_run_settings, value)
                self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(load_profile(self.path), good)

    def test_setting_rejections_never_save_or_substitute(self):
        good = self.saved()
        before = self.path.read_bytes()
        for field, bad_values in {
            'thinking_level': ('MINIMAL', 'OFF', 'low', '', None, True, 1),
            'max_output_tokens': (True, False, 63, 8193, 512.0, '512', None,
                                  float('nan'), float('inf'), 10 ** 500),
            'timeout_seconds': (True, False, 0, .9999, 120.001, '60', None,
                                float('nan'), float('inf'), -float('inf'), 10 ** 500),
        }.items():
            for bad in bad_values:
                with self.subTest(field=field, bad=repr(bad)):
                    value = copy.deepcopy(good)
                    value['models'][MODELS[0]][field] = bad
                    self.error('invalid_profile', save_profile, self.path, value, expected_revision=1)
                    self.error('invalid_profile', resolve_run_settings, good,
                               model_id=MODELS[0], overrides={field: bad})
                    self.assertEqual(self.path.read_bytes(), before)

    def test_all_model_level_location_and_numeric_boundaries_are_explicit(self):
        profile = load_profile(self.path)
        for location in ('global', 'us', 'eu'):
            profile['location'] = location
            for model in MODELS:
                for level in ('LOW', 'MEDIUM', 'HIGH'):
                    for tokens, timeout in ((64, 1), (8192, 120), (512, 1.25)):
                        with self.subTest(location=location, model=model, level=level, tokens=tokens):
                            run = resolve_run_settings(profile, model_id=model, overrides={
                                'thinking_level': level, 'max_output_tokens': tokens,
                                'timeout_seconds': timeout})
                            self.assertEqual((run['location'], run['model_id'], run['thinking_level'],
                                              run['max_output_tokens'], run['timeout_seconds']),
                                             (location, model, level, tokens, timeout))

    def test_override_keys_and_explicit_model_must_be_supported(self):
        profile = self.saved()
        for bad in ('', False, 0, 'gemini-3-flash', MODELS[1] + '-latest', [], {}):
            with self.subTest(model=bad):
                self.error('invalid_profile', resolve_run_settings, profile, model_id=bad)
        for bad in ([], False, '', {'model_id': MODELS[0]}, {'project_id': 'other'},
                    {'provider': 'ai_studio'}, {'thinking_budget': 0}, {'location': 'us'},
                    {'auth_profile_id': 'other'}, {'credential_path': 'PRIVATE_PROFILE_CANARY'}):
            with self.subTest(overrides=bad):
                self.error('invalid_profile', resolve_run_settings, profile, overrides=bad)
        self.assertEqual(resolve_run_settings(profile, overrides={}), resolve_run_settings(profile))

    def test_hashes_bind_profile_revision_other_model_and_run_override(self):
        profile = self.saved()
        first = resolve_run_settings(profile)
        reordered = {key: profile[key] for key in reversed(tuple(profile))}
        self.assertEqual(resolve_run_settings(reordered), first)
        profile['models'][MODELS[0]]['thinking_level'] = 'LOW'
        other = resolve_run_settings(profile)
        self.assertEqual(other['thinking_level'], first['thinking_level'])
        self.assertNotEqual(other['profile_sha256'], first['profile_sha256'])
        self.assertNotEqual(other['settings_sha256'], first['settings_sha256'])
        second = resolve_run_settings(profile, overrides={'timeout_seconds': 2})
        self.assertEqual(second['profile_sha256'], other['profile_sha256'])
        self.assertNotEqual(second['settings_sha256'], other['settings_sha256'])
        changed = save_profile(self.path, profile, expected_revision=1)
        latest = resolve_run_settings(changed)
        self.assertEqual(latest['profile_revision'], 2)
        self.assertNotEqual(latest['profile_sha256'], other['profile_sha256'])
        self.assertEqual(json.loads(json.dumps(first)), first)

    def test_run_profile_and_override_and_other_snapshot_have_no_aliases(self):
        profile = self.saved()
        profile['models'][MODELS[0]]['thinking_level'] = 'HIGH'
        profile['models'][MODELS[1]]['thinking_level'] = 'LOW'
        override = {'max_output_tokens': 2048}
        one = resolve_run_settings(profile, model_id=MODELS[0], overrides=override)
        two = resolve_run_settings(profile, model_id=MODELS[1])
        original = copy.deepcopy((profile, override, one, two))
        one['thinking_level'] = 'MEDIUM'
        self.assertEqual((profile, override, two), (original[0], original[1], original[3]))
        profile['models'][MODELS[0]]['thinking_level'] = 'LOW'
        override['max_output_tokens'] = 4096
        self.assertEqual(one['max_output_tokens'], 2048)
        self.assertEqual(two['thinking_level'], 'LOW')
        self.assertEqual(load_profile(self.path)['models'][MODELS[0]]['thinking_level'], 'MEDIUM')

    def test_invalid_expected_revision_and_input_revision_fail_before_sidecar_creation(self):
        profile = load_profile(self.path)
        lock_path = self.path.with_name(self.path.name + '.lock')
        lock_path.unlink()
        for bad in (None, True, False, -1, 1.0, '0', float('nan'), 9007199254740992):
            with self.subTest(revision=bad):
                self.error('invalid_revision', save_profile, self.path, profile, expected_revision=bad)
                self.assertFalse(lock_path.exists())
        self.error('revision_conflict', save_profile, self.path, profile, expected_revision=1)
        self.assertFalse(lock_path.exists())
        profile['access_token'] = 'PRIVATE_PROFILE_CANARY'
        self.error('invalid_profile', save_profile, self.path, profile, expected_revision=0)
        self.assertFalse(lock_path.exists())
        self.assertFalse(self.path.exists())

    def test_existing_profile_identity_is_stable_and_new_path_can_have_own_identity(self):
        profile = self.saved()
        before = self.path.read_bytes()
        profile['profile_id'] = 'other-profile'
        self.error('invalid_profile', save_profile, self.path, profile, expected_revision=1)
        self.assertEqual(self.path.read_bytes(), before)
        profile['revision'] = 0
        other_path = self.path.with_name('other.json')
        self.assertEqual(save_profile(other_path, profile, expected_revision=0)['profile_id'], 'other-profile')

    def test_revision_limit_is_fail_closed_without_overflow(self):
        profile = self.saved()
        profile['revision'] = 9007199254740991
        self.path.write_text(json.dumps(profile), encoding='utf-8')
        before = self.path.read_bytes()
        self.error('revision_exhausted', save_profile, self.path, profile,
                   expected_revision=9007199254740991)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(resolve_run_settings(load_profile(self.path))['profile_revision'], 9007199254740991)

    def test_corrupt_files_never_become_defaults_or_get_overwritten(self):
        profile = self.saved()
        text = json.dumps(profile)
        duplicate_model = text.replace('"models": {', '"models": {"gemini-4-argon": {},', 1)
        corrupt = [b'', b'not json', b'\xff', b'\xef\xbb\xbf' + text.encode(),
                   b'[]', b'null', b'true', b'{}', text.encode() + b'{}',
                   (text[:-1] + ', "revision": 2}').encode(),
                   duplicate_model.encode(), text.replace('"MEDIUM"', 'NaN', 1).encode(),
                   text.replace('"MEDIUM"', 'Infinity', 1).encode(),
                   text.replace('"revision": 1', '"revision": 0').encode(),
                   text.replace('"schema_version": 1', '"schema_version": true').encode(),
                   b'[' * 1100 + b']' * 1100, b' ' * 16385]
        for number, payload in enumerate(corrupt):
            with self.subTest(payload=number):
                self.path.write_bytes(payload)
                self.error('corrupt', load_profile, self.path)
                self.error('corrupt', save_profile, self.path, profile, expected_revision=1)
                self.assertEqual(self.path.read_bytes(), payload)

    def test_file_size_limit_accepts_exact_boundary_and_rejects_one_more(self):
        self.saved()
        body = self.path.read_bytes().rstrip()
        self.path.write_bytes(body + b' ' * (16384 - len(body)))
        self.assertEqual(load_profile(self.path)['revision'], 1)
        with self.path.open('ab') as stream:
            stream.write(b' ')
        self.error('corrupt', load_profile, self.path)

    def test_invalid_paths_do_not_create_directories_or_escape_to_another_file(self):
        for bad in (None, 1, '', self.path.parent / 'missing' / 'file.json',
                    str(self.path.parent / '..' / 'outside.json'),
                    str(self.path) + '\x00', '//server/share/profile.json', self.path.parent):
            with self.subTest(path=repr(bad)):
                self.error('invalid_path', load_profile, bad)
        self.assertFalse((self.path.parent / 'missing').exists())
        self.assertFalse(self.path.exists())

    def test_relative_path_is_resolved_in_caller_directory(self):
        # A relative private folder inside cwd avoids traversal components.
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
            path = Path(folder) / 'relative.json'
            relative = path.relative_to(Path.cwd())
            saved = save_profile(str(relative), load_profile(relative), expected_revision=0)
            self.assertEqual(load_profile(path), saved)

    def test_windows_alias_and_device_path_names_are_rejected_before_sidecar_write(self):
        for name in ('profile.json.', 'profile.json ', 'NUL', 'nul.json', 'CON', 'AUX.txt',
                     'COM1.json', 'LPT9', 'a:stream', 'q?.json'):
            with self.subTest(name=name):
                self.error('invalid_path', load_profile, self.path.parent / name)
        self.assertEqual(list(self.path.parent.iterdir()), [])

    def test_hardlinked_profile_or_lock_is_rejected_without_changing_original(self):
        self.saved()
        before = self.path.read_bytes()
        alias = self.path.with_name('alias.json')
        os.link(self.path, alias)
        self.error('invalid_path', load_profile, self.path)
        self.error('invalid_path', load_profile, alias)
        self.assertEqual(self.path.read_bytes(), before)
        alias.unlink()
        lock_path = self.path.with_name(self.path.name + '.lock')
        alias = self.path.with_name('lock-alias')
        os.link(lock_path, alias)
        self.error('invalid_path', load_profile, self.path)
        self.assertEqual(self.path.read_bytes(), before)

    def test_symlink_profile_and_parent_are_rejected_when_platform_permits_creation(self):
        self.saved()
        link = self.path.with_name('link.json')
        try:
            link.symlink_to(self.path)
        except OSError as exc:
            if os.name != 'nt' or getattr(exc, 'winerror', None) != 1314:
                raise
            self.skipTest('Windows symlink creation privilege unavailable (1314); junction tested separately')
        self.error('invalid_path', load_profile, link)
        link.unlink()
        directory_link = self.path.with_name('directory-link')
        directory_link.symlink_to(self.path.parent, target_is_directory=True)
        self.error('invalid_path', load_profile, directory_link / self.path.name)

    @unittest.skipUnless(os.name == 'nt', 'Windows junction is platform-specific')
    def test_windows_reparse_parent_junction_is_rejected(self):
        self.saved()
        link = self.path.with_name('junction')
        result = subprocess.run(['cmd', '/d', '/c', 'mklink', '/J', str(link), str(self.path.parent)],
                                capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        try:
            self.error('invalid_path', load_profile, link / self.path.name)
        finally:
            # Remove the verified junction itself only; never recurse into its target.
            os.rmdir(link)

    def test_atomic_replace_failure_preserves_last_good_and_removes_own_temp(self):
        profile = self.saved()
        before = self.path.read_bytes()
        profile['selected_model'] = MODELS[0]
        with patch('labflow.ai_connection_profiles.os.replace',
                   side_effect=OSError('PRIVATE_PROFILE_CANARY')):
            self.error('storage_error', save_profile, self.path, profile, expected_revision=1)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.path.parent.glob('.*.tmp')), [])
        self.assertEqual(save_profile(self.path, profile, expected_revision=1)['revision'], 2)

    def test_temp_fsync_failure_preserves_last_good_and_releases_lock(self):
        profile = self.saved()
        before = self.path.read_bytes()
        with patch('labflow.ai_connection_profiles.os.fsync',
                   side_effect=OSError('PRIVATE_PROFILE_CANARY')):
            self.error('storage_error', save_profile, self.path, profile, expected_revision=1)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.path.parent.glob('.*.tmp')), [])
        self.assertEqual(load_profile(self.path), profile)

    def test_failure_after_replace_is_reported_and_reload_reconciles_committed_revision(self):
        profile = self.saved()
        real_replace = os.replace

        def replace_then_fail(source, destination):
            real_replace(source, destination)
            raise OSError('PRIVATE_PROFILE_CANARY')

        with patch('labflow.ai_connection_profiles.os.replace', side_effect=replace_then_fail):
            self.error('storage_error', save_profile, self.path, profile, expected_revision=1)
        self.assertEqual(load_profile(self.path)['revision'], 2)
        self.error('revision_conflict', save_profile, self.path, profile, expected_revision=1)

    def test_control_exceptions_propagate_same_object_and_last_good_survives(self):
        profile = self.saved()
        before = self.path.read_bytes()
        for control in (KeyboardInterrupt('PRIVATE_PROFILE_CANARY'), SystemExit(7)):
            with self.subTest(control=type(control).__name__):
                with patch('labflow.ai_connection_profiles.os.replace', side_effect=control):
                    with self.assertRaises(type(control)) as caught:
                        save_profile(self.path, profile, expected_revision=1)
                self.assertIs(caught.exception, control)
                self.assertEqual(self.path.read_bytes(), before)
                self.assertEqual(list(self.path.parent.glob('.*.tmp')), [])
                self.assertEqual(load_profile(self.path), profile)

    def test_persistent_sidecar_remains_after_success_and_error(self):
        self.saved()
        sidecar = self.path.with_name(self.path.name + '.lock')
        identity = sidecar.stat().st_ino
        self.error('revision_conflict', save_profile, self.path, load_profile(self.path), expected_revision=0)
        self.assertEqual(sidecar.stat().st_ino, identity)
        self.assertEqual(sidecar.read_bytes(), b'\0')

    def test_no_auth_environment_sdk_or_network_is_needed(self):
        with patch.dict(os.environ, {}, clear=True), patch('socket.socket', side_effect=AssertionError('network')):
            saved = self.saved()
            self.assertEqual(resolve_run_settings(load_profile(self.path))['profile_revision'], saved['revision'])
            self.assertEqual(set(json.loads(self.path.read_text(encoding='utf-8'))), PROFILE_KEYS)

    def child(self, code, *args):
        child = subprocess.Popen([sys.executable, '-X', 'utf8', '-B', '-u', '-c', code, *map(str, args)],
                                 cwd=Path(__file__).resolve().parents[1], stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
        self.addCleanup(self.stop_child, child)
        return child

    @staticmethod
    def stop_child(child):
        if child.poll() is None:
            child.kill()
        child.communicate(timeout=10)

    def test_actual_subprocess_os_lock_blocks_load_save_and_releases_on_process_exit(self):
        profile = self.saved()
        before = self.path.read_bytes()
        code = '''
import os, sys
f = open(sys.argv[1], 'r+b', buffering=0)
if os.name == 'nt':
    import msvcrt
    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
else:
    import fcntl
    fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
print('locked', flush=True)
sys.stdin.readline()
os._exit(0)
'''
        child = self.child(code, self.path.with_name(self.path.name + '.lock'))
        self.assertEqual(child.stdout.readline().strip(), 'locked')
        self.error('locked', load_profile, self.path)
        self.error('locked', save_profile, self.path, profile, expected_revision=1)
        self.assertEqual(self.path.read_bytes(), before)
        child.communicate('\n', timeout=10)
        self.assertEqual(child.returncode, 0)
        self.assertEqual(save_profile(self.path, profile, expected_revision=1)['revision'], 2)

    def test_actual_concurrent_cas_writers_have_one_winner_and_no_lost_update(self):
        profile = self.saved()
        start = self.path.with_name('go')
        code = '''
import json, pathlib, sys, time
from labflow.ai_connection_profiles import AIConnectionProfileError, save_profile
profile = json.loads(sys.argv[2])
profile['models']['gemini-4-argon']['thinking_level'] = sys.argv[3]
print('ready', flush=True)
deadline = time.monotonic() + 10
while not pathlib.Path(sys.argv[4]).exists():
    if time.monotonic() > deadline: raise RuntimeError('barrier_timeout')
    time.sleep(.005)
try:
    result = save_profile(sys.argv[1], profile, expected_revision=1)
    print(json.dumps({'saved': result}), flush=True)
except AIConnectionProfileError as exc:
    print(json.dumps({'error': exc.code}), flush=True)
'''
        children = [self.child(code, self.path, json.dumps(profile), level, start)
                    for level in ('LOW', 'HIGH')]
        for child in children:
            self.assertEqual(child.stdout.readline().strip(), 'ready')
        start.write_text('go', encoding='ascii')
        outcomes = []
        for child in children:
            stdout, stderr = child.communicate(timeout=15)
            self.assertEqual(child.returncode, 0, stderr)
            outcomes.append(json.loads(stdout.strip()))
        winners = [item['saved'] for item in outcomes if 'saved' in item]
        losers = [item['error'] for item in outcomes if 'error' in item]
        self.assertEqual(len(winners), 1)
        self.assertEqual(len(losers), 1)
        self.assertIn(losers[0], ('ai_connection_profile_locked', 'ai_connection_profile_revision_conflict'))
        self.assertEqual(load_profile(self.path), winners[0])
        self.assertEqual(winners[0]['revision'], 2)
        self.assertEqual(winners[0]['models'][MODELS[1]], profile['models'][MODELS[1]])

    def test_cold_process_reads_saved_profile_and_identical_run_hash(self):
        saved = self.saved()
        expected = resolve_run_settings(saved, model_id=MODELS[0], overrides={'thinking_level': 'HIGH'})
        code = '''
import json, sys
from labflow.ai_connection_profiles import load_profile, resolve_run_settings
p = load_profile(sys.argv[1])
print(json.dumps(resolve_run_settings(p, model_id='gemini-4-argon', overrides={'thinking_level': 'HIGH'})))
'''
        child = self.child(code, self.path)
        stdout, stderr = child.communicate(timeout=10)
        self.assertEqual(child.returncode, 0, stderr)
        self.assertEqual(json.loads(stdout), expected)


if __name__ == '__main__':
    unittest.main()

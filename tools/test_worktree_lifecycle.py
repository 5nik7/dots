#!/usr/bin/env python3
"""Owned repositories/environments only; no installed CLI, home config or network."""

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('lifecycle', Path(__file__).with_name('worktree_lifecycle.py'))
lifecycle = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(lifecycle)
GIT = shutil.which('git')


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='dots-lifecycle-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        env = {'PATH': str(Path(GIT).parent), 'GIT_CONFIG_NOSYSTEM': '1',
               'GIT_CONFIG_GLOBAL': str(self.root / 'no-global-config'),
               'GIT_TERMINAL_PROMPT': '0', 'PYTHONDONTWRITEBYTECODE': '1',
               'LC_ALL': 'C', 'LANG': 'C', 'PYTHONUTF8': '1'}
        for key, name in {'HOME':'home', 'USERPROFILE':'home', 'XDG_CONFIG_HOME':'config',
                          'XDG_DATA_HOME':'data', 'XDG_STATE_HOME':'state', 'XDG_CACHE_HOME':'cache',
                          'APPDATA':'config', 'LOCALAPPDATA':'data', 'TMPDIR':'tmp', 'TMP':'tmp', 'TEMP':'tmp'}.items():
            p = self.root / name
            p.mkdir(exist_ok=True)
            env[key] = str(p)
        for key in ('SystemRoot', 'WINDIR', 'PREFIX'):
            if key in os.environ:
                env[key] = os.environ[key]
        self.env_patch = patch.dict(os.environ, env, clear=True)
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        self.original = self.root / 'original'
        self.remote = self.root / 'remote.git'
        self.candidate = self.root / 'development space'
        self.git(self.root, 'init', '--bare', str(self.remote))
        self.git(self.root, 'init', '-b', 'main', str(self.original))
        self.git(self.original, 'config', 'user.email', 'fixture@example.invalid')
        self.git(self.original, 'config', 'user.name', 'Fixture')
        # Preserve isolation even after the helper strips inherited Git routing.
        self.git(self.original, 'config', 'core.hooksPath', os.devnull)
        (self.original / 'tracked').write_text('initial\n')
        (self.original / '.gitignore').write_text('ignored*\n')
        self.git(self.original, 'add', 'tracked', '.gitignore')
        self.git(self.original, 'commit', '-m', 'fixture')
        self.git(self.original, 'remote', 'add', 'origin', str(self.remote))
        self.git(self.original, 'push', 'origin', 'HEAD:refs/heads/main')
        self.git(self.original, 'branch', 'recovery/fixture')
        self.git(self.original, 'worktree', 'add', '-b', 'feature', str(self.candidate), 'main')
        self.helper = self.root / 'helper.py'
        self.helper.write_text('test-owned helper identity\n')
        self.lc = lifecycle.Lifecycle(self.original, self.original, self.helper)
        self.lc.register(str(self.candidate))
        self.refs = self.git(self.original, 'for-each-ref', '--format=%(refname) %(objectname)', 'refs/heads')
        self.index = (self.original / '.git/index').read_bytes()
        (self.original / 'tracked').write_text('preserve original edit\n')

    def git(self, cwd, *args):
        result = subprocess.run([GIT, '-C', str(cwd), *args], capture_output=True, env=os.environ,
                                text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def result(self, apply=True, activity=None, **kwargs):
        # All positive synthetic eligibility cases inject a known idle process
        # snapshot. Native /proc inspection is independently exercised below.
        with patch.object(lifecycle, 'process_use', return_value=activity):
            results = self.lc.run(apply=apply, reviewed=True, **kwargs)
        return next(r for r in results if r['path'] == str(self.candidate))

    def preserved(self):
        self.assertEqual((self.original / 'tracked').read_text(), 'preserve original edit\n')
        self.assertEqual((self.original / '.git/index').read_bytes(), self.index)
        self.assertEqual(self.git(self.original, 'for-each-ref', '--format=%(refname) %(objectname)', 'refs/heads'), self.refs)

    def test_preview_no_fetch_or_mutation_and_eligible_removal(self):
        self.git(self.original, 'remote', 'set-url', 'origin', str(self.root / 'missing'))
        before = self.lc.registry.read_bytes()
        self.assertEqual(self.result(apply=False)['status'], 'candidate')
        self.assertEqual(self.lc.registry.read_bytes(), before)
        self.assertTrue(self.candidate.exists())
        self.assertEqual(self.result()['reason'], 'Git refused fetch')
        self.git(self.original, 'remote', 'set-url', 'origin', str(self.remote))
        self.assertEqual(self.result()['status'], 'removed')
        self.assertFalse(self.candidate.exists())
        self.assertEqual(self.lc.load(), [])
        self.preserved()

    def test_local_content_refused(self):
        cases = ('modified', 'staged', 'untracked', 'ignored', 'empty', 'ignored-empty', 'assume-unchanged')
        for case in cases:
            with self.subTest(case=case):
                p = self.candidate / ('tracked' if case in ('modified', 'staged', 'assume-unchanged') else
                                      'ignored-file' if case.startswith('ignored') else 'local')
                old = p.read_bytes() if p.exists() else None
                if case in ('empty', 'ignored-empty'):
                    p.mkdir()
                else:
                    p.write_text('unique local content\n')
                if case == 'staged':
                    self.git(self.candidate, 'add', 'tracked')
                if case == 'assume-unchanged':
                    self.git(self.candidate, 'update-index', '--assume-unchanged', 'tracked')
                self.assertEqual(self.result()['status'], 'skipped')
                self.assertTrue(p.exists())
                # Restore only explicit disposable fixtures, never git reset/clean.
                if case == 'assume-unchanged':
                    self.git(self.candidate, 'update-index', '--no-assume-unchanged', 'tracked')
                if old is not None:
                    p.write_bytes(old)
                    if case == 'staged':
                        self.git(self.candidate, 'add', 'tracked')
                elif p.is_dir():
                    p.rmdir()
                else:
                    p.unlink()
        self.preserved()

    def test_unmerged_then_fresh_remote_merge(self):
        (self.candidate / 'tracked').write_text('new commit\n')
        self.git(self.candidate, 'add', 'tracked')
        self.git(self.candidate, 'commit', '-m', 'unmerged')
        self.assertEqual(self.result()['reason'], 'HEAD not contained in origin/main')
        # Push to the local fixture remote without updating cached origin/main.
        self.git(self.candidate, 'push', str(self.remote), 'HEAD:refs/heads/main')
        self.assertEqual(self.result()['status'], 'removed')

    def test_unregistered_and_recreated_identity_refused(self):
        self.git(self.original, 'worktree', 'remove', str(self.candidate))
        self.candidate.mkdir()
        (self.candidate / 'unique').write_text('keep')
        self.assertEqual(self.result()['status'], 'skipped')
        self.assertEqual((self.candidate / 'unique').read_text(), 'keep')
        (self.candidate / 'unique').unlink()
        self.candidate.rmdir()
        self.git(self.original, 'worktree', 'add', str(self.candidate), 'feature')
        self.assertEqual(self.result()['reason'], 'managed identity mismatch')

    def test_unmanaged_and_original_refused(self):
        self.lc.save([])
        result = self.result()
        self.assertEqual(result['reason'], 'not explicitly managed')
        self.lc.save([{'path':str(self.original),'git_dir':str(self.lc.common),'token':'x'*32}])
        with patch.object(lifecycle, 'process_use', return_value=None):
            results = self.lc.run(apply=True, reviewed=True)
        self.assertTrue(any(r['path']==str(self.original) and r['status']=='skipped' for r in results))
        self.preserved()

    def test_active_and_uncertain_refused(self):
        for reason in ('active process reference', 'process inspection permission uncertainty',
                       'process inspection unavailable on this host'):
            self.assertEqual(self.result(activity=reason)['reason'], reason)
        self.assertTrue(self.candidate.exists())

    def test_session_helper_and_known_live_paths_refused(self):
        self.lc.session = self.candidate
        self.assertIn('protected', self.result()['reason'])
        self.lc.session = self.original
        self.lc.helper = self.candidate / 'tracked'
        self.assertIn('protected', self.result()['reason'])
        self.lc.helper = self.helper
        with patch.dict(os.environ, {'DOTS':str(self.candidate)}):
            self.assertIn('protected', self.result()['reason'])
        self.assertIn('protected', self.result(protects=[self.candidate / 'tracked'])['reason'])
        self.lc.cwd = self.candidate
        self.assertIn('protected', self.result()['reason'])

    def test_original_live_symlink_refused(self):
        if os.name == 'nt':
            self.skipTest('native Windows symlink privilege not altered')
        (self.original / 'live-link').symlink_to(self.candidate / 'tracked')
        self.assertEqual(self.result()['reason'], 'original checkout symlink uses candidate')

    def test_usage_review_required_and_git_refusal(self):
        self.assertIn('requires', self.lc.run(apply=True)[0]['reason'])
        original_git = self.lc.git
        def refuse(cwd, *args):
            if args[:2] == ('worktree','remove'):
                raise lifecycle.Refusal('Git refused worktree')
            return original_git(cwd, *args)
        with patch.object(self.lc, 'git', side_effect=refuse):
            self.assertEqual(self.result()['reason'], 'Git refused worktree')
        self.assertTrue(self.candidate.exists())
        self.assertEqual(len(self.lc.load()), 1)

    def test_registration_capacity_and_allowed_paths(self):
        with self.assertRaises(lifecycle.Refusal):
            self.lc.register(str(self.original))
        outside = self.root / 'nested' / 'worktree'
        outside.parent.mkdir()
        self.git(self.original, 'worktree', 'add', '-b', 'other', str(outside))
        with self.assertRaises(lifecycle.Refusal):
            self.lc.register(str(outside))
        self.lc.save([])
        with self.assertRaises(lifecycle.Refusal):
            self.lc.register(str(self.candidate))

    def test_native_active_process(self):
        if os.name != 'posix' or not Path('/proc/self/fd').is_dir():
            self.assertIsNotNone(lifecycle.process_use(self.candidate))
            return
        child = subprocess.Popen([sys.executable, '-B', '-c',
                                  'import time; print("ready", flush=True); time.sleep(5)'],
                                 cwd=self.candidate, env=os.environ, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        try:
            self.assertEqual(child.stdout.readline(), b'ready\n')
            self.assertEqual(lifecycle.process_use(self.candidate), 'active process reference')
        finally:
            child.stdin.close()
            child.terminate()
            child.wait(timeout=10)
            child.stdout.close()

    def test_native_eligible_removal_or_explicit_unavailability(self):
        reason = lifecycle.process_use(self.candidate)
        if reason:
            results = self.lc.run(apply=True, reviewed=True)
            self.assertEqual(results[0]['status'], 'skipped')
            self.assertTrue(self.candidate.exists())
            if os.name == 'posix':
                self.skipTest('native process inspection unavailable: ' + reason)
            return
        results = self.lc.run(apply=True, reviewed=True)
        self.assertEqual(results[0]['status'], 'removed', results)
        self.assertFalse(self.candidate.exists())
        self.preserved()

    def test_locked_and_malformed_registry_refused(self):
        self.git(self.original, 'worktree', 'lock', str(self.candidate))
        self.assertEqual(self.result()['reason'], 'unregistered, locked or prunable worktree')
        self.git(self.original, 'worktree', 'unlock', str(self.candidate))
        self.lc.registry.write_text('{broken')
        with self.assertRaises(lifecycle.Refusal):
            self.lc.run(apply=True, reviewed=True)
        self.assertTrue(self.candidate.exists())
        self.preserved()

    def test_cli_defaults_and_lock(self):
        command = [sys.executable, '-B', str(Path(lifecycle.__file__)), '--repo', str(self.original)]
        result = subprocess.run(command, env=os.environ, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.candidate.exists())
        self.lc.lock.write_text('fixture')
        result = subprocess.run(command + ['--apply', '--usage-reviewed', '--session-worktree', str(self.original)],
                                env=os.environ, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 1)
        self.assertTrue(self.candidate.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)

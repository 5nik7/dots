"""Low-level lifecycle planning/recovery tests; all mutations use temporary roots."""
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

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('lifecycle_under_test', ROOT/'scripts/install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


@unittest.skipUnless(os.name == 'posix' and shutil.which('bash'), 'Native POSIX fixture')
class LifecyclePlanning(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='blastoff-plan-tests-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.home = self.root/'home'
        self.home.mkdir()
        self.prefix = self.root/'target'
        self.tools = self.root/'tools'
        self.tools.mkdir()
        (self.tools/'bash').symlink_to(shutil.which('bash'))
        self.environment = patch.dict(os.environ, {
            'HOME': str(self.home), 'USERPROFILE': str(self.home),
            'XDG_CONFIG_HOME': str(self.home/'config'), 'XDG_DATA_HOME': str(self.home/'data'),
            'XDG_CACHE_HOME': str(self.home/'cache'), 'ZDOTDIR': str(self.home),
            'PATH': str(self.prefix/'bin')+os.pathsep+str(self.tools),
            'MANPATH': '',
            'BLASTOFF_HOME': str(self.home/'store'), 'STARSHIP_CONFIG': str(self.home/'starship.toml'),
            'BLASTOFF_PYTHON': sys.executable, 'PREFIX': str(self.root/'native'),
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def install(self, prefix=None, public=True):
        plan = installer.make_plan('install', prefix or self.prefix, public)
        installer.apply(plan)
        return plan

    def test_default_prefix_branches_and_explicit_path_validation(self):
        with patch.object(installer, 'native_termux', return_value=True):
            self.assertEqual(installer.default_prefix(), self.root/'native')
            with patch.dict(os.environ, PREFIX='relative'):
                with self.assertRaises(installer.core.Failure):
                    installer.default_prefix()
            with patch.dict(os.environ, PREFIX=''):
                with self.assertRaises(installer.core.Failure):
                    installer.default_prefix()
        with patch.object(installer, 'native_termux', return_value=False):
            self.assertEqual(installer.default_prefix(), self.home/'.local')

    def test_unrelated_shadowing_blocks(self):
        shadow = self.tools/'blastoff'
        shadow.write_text('#!/bin/sh\nexit 99\n')
        shadow.chmod(0o755)
        with patch.dict(os.environ, PATH=str(self.tools)+os.pathsep+str(self.prefix/'bin')):
            with self.assertRaisesRegex(installer.core.Failure, 'shadowing'):
                installer.make_plan('install', self.prefix, True)
        self.assertFalse(self.prefix.exists())

    def test_newer_installed_version_skips_everything(self):
        self.install()
        manifest = installer.manifest_path(self.prefix)
        doc = json.loads(manifest.read_bytes())
        doc['version'] = '99.0.0'
        manifest.write_text(json.dumps(doc))
        before = manifest.read_bytes()
        plan = installer.make_plan('install', self.prefix, True)
        self.assertTrue(plan.skip)
        installer.apply(plan)
        self.assertEqual(manifest.read_bytes(), before)

    def test_concurrent_edit_after_plan_is_preserved(self):
        self.install()
        plan = installer.make_plan('install', self.prefix, True)
        # Force a missing support repair so apply cannot take the no-op fast path.
        support = self.prefix/'share/man/man1/blastoff.1'
        support.unlink()
        plan = installer.make_plan('install', self.prefix, True)
        profile = self.home/'.bashrc'
        profile.write_bytes(profile.read_bytes()+b'\n# concurrent user edit\n')
        with self.assertRaisesRegex(installer.core.Failure, 'changed after planning'):
            installer.apply(plan)
        self.assertFalse(support.exists())
        self.assertIn(b'concurrent user edit', profile.read_bytes())

    def test_pending_migration_retries_after_target_commit(self):
        legacy = self.home/'.local'
        self.install(legacy, public=False)
        plan = installer.make_plan('install', self.prefix, True)
        old_launcher = legacy/'bin/blastoff'
        original_unlink = Path.unlink

        def fail_old_launcher(path, *args, **kwargs):
            if path == old_launcher:
                raise OSError('injected cleanup interruption')
            return original_unlink(path, *args, **kwargs)

        with patch.object(Path, 'unlink', fail_old_launcher):
            with self.assertRaisesRegex(OSError, 'injected cleanup'):
                installer.apply(plan)
        self.assertTrue((self.prefix/'bin/blastoff').exists())
        self.assertTrue(old_launcher.exists())
        manifest = installer.manifest_path(self.prefix)
        self.assertIn('migration', json.loads(manifest.read_bytes()))
        self.install()
        self.assertNotIn('migration', json.loads(manifest.read_bytes()))
        self.assertFalse(old_launcher.exists())
        self.assertFalse(installer.manifest_path(legacy).exists())

    def test_integrated_migration_resumes_after_partial_cleanup(self):
        legacy = self.home/'.local'
        self.install(legacy, public=True)
        old_core = legacy/'share/blastoff/versions'/installer.core.VERSION/'lib/blastoff.py'
        original_unlink = Path.unlink

        def interrupt(path, *args, **kwargs):
            if path == old_core:
                raise OSError('mid-cleanup interruption')
            return original_unlink(path, *args, **kwargs)

        plan = installer.make_plan('install', self.prefix, True)
        with patch.object(Path, 'unlink', interrupt):
            with self.assertRaisesRegex(OSError, 'mid-cleanup'):
                installer.apply(plan)
        self.assertFalse((legacy/'bin/blastoff').exists())
        self.assertTrue(old_core.exists())
        self.install()
        self.assertFalse(installer.manifest_path(legacy).exists())
        self.assertNotIn('migration', json.loads(installer.manifest_path(self.prefix).read_bytes()))

    def test_native_migration_retains_valid_external_completion_ownership(self):
        legacy = self.home/'.local'
        with patch.object(installer.integration, 'shell_prefix', return_value=self.root/'old-shell-prefix'):
            self.install(legacy, public=True)
        completion = self.home/'data/bash-completion/completions/blastoff'
        self.assertTrue(completion.exists())
        framework = self.prefix/'share/bash-completion/bash_completion'
        framework.parent.mkdir(parents=True)
        framework.write_text('# framework fixture')
        with patch.object(installer.integration, 'shell_prefix', return_value=self.prefix):
            self.install()
        doc = installer.load_manifest(installer.manifest_path(self.prefix), self.prefix)
        self.assertEqual(doc['files'][str(completion)], installer.digest(completion.read_bytes()))
        installer.apply(installer.make_plan('uninstall', self.prefix, True))
        self.assertFalse(completion.exists())

    def test_install_uninstall_reinstall_keeps_retained_backups(self):
        profile = self.home/'.bashrc'
        profile.write_text('# user profile\n')
        self.install()
        installer.apply(installer.make_plan('uninstall', self.prefix, True))
        backups = {p: p.read_bytes() for p in (self.prefix/'share/blastoff/profile-backups').glob('*.bak')}
        self.assertTrue(backups)
        self.install()
        self.assertTrue(all(p.read_bytes() == data for p, data in backups.items()))
        installer.apply(installer.make_plan('uninstall', self.prefix, True))
        self.assertEqual(profile.read_text(), '# user profile\n')

    def test_target_failure_leaves_legacy_intact(self):
        legacy = self.home/'.local'
        self.install(legacy, public=False)
        before = {name: Path(name).read_bytes() for name in json.loads(installer.manifest_path(legacy).read_bytes())['files']}
        plan = installer.make_plan('install', self.prefix, True)
        original = installer.replace
        count = 0

        def fail_second(path, data, mode, expected):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError('injected target failure')
            return original(path, data, mode, expected)

        with patch.object(installer, 'replace', fail_second):
            with self.assertRaisesRegex(OSError, 'injected target'):
                installer.apply(plan)
        self.assertEqual(before, {name: Path(name).read_bytes() for name in before})
        self.assertFalse(installer.manifest_path(self.prefix).exists())

    def test_profile_bom_crlf_and_user_edits_survive(self):
        profile = self.home/'.bashrc'
        original = b'\xef\xbb\xbf# original\r\n'
        profile.write_bytes(original)
        self.install()
        self.assertTrue(profile.read_bytes().startswith(original))
        self.assertNotIn(b'\n', profile.read_bytes().replace(b'\r\n', b''))
        added = b'# later\r\n'
        profile.write_bytes(profile.read_bytes()+added)
        installer.apply(installer.make_plan('uninstall', self.prefix, True))
        self.assertEqual(profile.read_bytes(), original+added)
        self.assertTrue(list((self.prefix/'share/blastoff/profile-backups').glob('*.bak')))

    def test_discovery_uses_native_bridge_without_profile_edits(self):
        # Filesystem projection of the actual native Termux Zsh autoload path.
        bridge = self.prefix/'share/zsh/functions/Completion/Unix'
        bridge.mkdir(parents=True)
        bash_framework = self.prefix/'share/bash-completion/bash_completion'
        bash_framework.parent.mkdir(parents=True)
        bash_framework.write_text('# fixture framework')
        real_zsh = shutil.which('zsh', path=os.defpath) or shutil.which('zsh', path=str(Path(sys.executable).parent))
        if not real_zsh:
            self.skipTest('native Zsh unavailable')
        (self.tools/'zsh').symlink_to(real_zsh)
        with patch.object(installer.integration, 'shell_prefix', return_value=self.prefix):
            plan = self.install()
        self.assertFalse(plan.profiles)
        self.assertTrue((bridge/'_blastoff').is_file())
        # Real compinit discovers the installed file, not a direct source call.
        result = subprocess.run([real_zsh, '-f', '-c',
            'fpath=("$1" $fpath); autoload -Uz compinit; compinit -D; print -r -- $_comps[blastoff]',
            'check', str(bridge)], env=dict(os.environ), cwd=self.home, capture_output=True,
            text=True, timeout=10, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), '_blastoff')


if __name__ == '__main__':
    unittest.main()

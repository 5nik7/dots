#!/usr/bin/env python3
"""Exercise optional Git plugin delivery with a local submodule and isolated setup."""
import json
import io
import os
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_installation as fixture


class GitItPlugin(unittest.TestCase):
    write = fixture.InstallationTests.write
    cli = fixture.InstallationTests.cli

    def setUp(self):
        fixture.InstallationTests.setUp(self)
        self.env.update(GIT_AUTHOR_NAME='Fixture', GIT_COMMITTER_NAME='Fixture',
                        GIT_AUTHOR_EMAIL='fixture@example.invalid', GIT_COMMITTER_EMAIL='fixture@example.invalid',
                        GIT_CONFIG_COUNT='1', GIT_CONFIG_KEY_0='protocol.file.allow', GIT_CONFIG_VALUE_0='always')
        root = fixture.ROOT
        shutil.copytree(root/'lib/dots', self.repo/'lib/dots',
                        ignore=shutil.ignore_patterns('__pycache__', 'setup.py', 'setup.bash'))
        shutil.copytree(root/'bin', self.repo/'bin', dirs_exist_ok=True, symlinks=True)
        (self.repo/'plugins').mkdir()
        self.plugin = self.repo/'plugins/git-it'
        declaration = json.loads((root/'plugins/manifest.json').read_text())['plugins']['git-it']
        self.write('plugins/manifest.json', {'schema': 1, 'plugins': {'git-it': declaration}})
        sources = json.loads((self.repo/'.dots/sources.json').read_text())
        sources['sources'].append(dict(id='git-it', path='plugins/git-it', platforms=declaration['platforms'], roots=[]))
        self.write('.dots/sources.json', sources)

    def git(self, cwd, *args):
        return subprocess.check_output(['git', '-C', str(cwd), *args], env=self.env, text=True,
                                       stderr=subprocess.PIPE).strip()

    def make_remote(self):
        src = self.base/'standalone'
        src.mkdir()
        self.git(src, 'init', '-b', 'main')
        (src/'completion').mkdir()
        for shell in ('bash', 'zsh', 'fish'):
            (src/'completion'/shell).write_text(shell + '\n')
        (src/'git-it.1').write_text('git-it manual\n')
        app = src/'git-it'
        app.write_text('#!' + shutil.which('bash') + '\nprintf "%s\\0" "$PWD" "$@"\nprintf "diagnostic\\n" >&2\nexit 7\n')
        app.chmod(0o755)
        self.git(src, 'add', '.')
        self.git(src, 'commit', '-m', 'Fixture plugin')
        origin = self.base/'public.git'
        self.git(self.base, 'clone', '--bare', str(src), str(origin))
        self.git(self.repo, 'init', '-b', 'main')
        self.git(self.repo, 'submodule', 'add', str(origin), 'plugins/git-it')
        self.git(self.repo, 'commit', '-m', 'Pin plugin', '--', '.gitmodules', 'plugins/git-it')
        return self.git(src, 'rev-parse', 'HEAD')

    def call(self, cmd, cwd=None):
        return subprocess.run(cmd, cwd=cwd or self.home, env=self.env, capture_output=True, timeout=40)

    @unittest.skipUnless(os.name != 'nt' and (fixture.ROOT/'plugins/git-it/.git').exists(),
                         'requires the initialized git-it submodule and POSIX Bash')
    def test_real_plugin_in_relocated_checkout(self):
        upstream = fixture.ROOT/'plugins/git-it'
        self.git(self.repo/'plugins', 'clone', '--no-local', str(upstream), str(self.plugin))
        self.git(self.repo, 'init', '-b', 'main')
        self.git(self.repo, 'submodule', 'add', str(upstream), 'plugins/git-it')
        self.cli('install', '--component', 'git-it', '--yes')
        installed = self.home/'.local/bin/git-it'
        work = self.home/'project'
        work.mkdir()
        self.git(work, 'init', '-b', 'main')
        self.git(work, 'remote', 'add', 'origin', 'git@github.com:team/tool.git')
        (work/'changed file').write_text('example')
        app = self.plugin/'git-it'
        (self.plugin/'logo.txt').write_text('live checkout\n second line\n')
        header = b'\n live checkout\n  second line\n Version '
        entries = ([installed], [self.repo/'bin/dots', 'git', 'it'],
                   [sys.executable, '-B', self.repo/'lib/dots/cli.py', 'git', 'it'])
        for args, expected in ((['-R', '--https'], b'https://github.com/team/tool.git\n'),
                               (['--help'], None), (['-s', '--json'], None), ([], None)):
            direct = self.call([app, *args], work)
            self.assertEqual(direct.returncode, 0, direct.stderr)
            for entry in entries:
                via = self.call([*entry, *args], work)
                self.assertEqual((via.returncode, via.stdout, via.stderr),
                                 (direct.returncode, direct.stdout, direct.stderr))
            if expected is not None:
                self.assertEqual(direct.stdout, expected)
            if not args or '--help' in args:
                self.assertNotIn(b'changed file', direct.stdout)
                self.assertIn(b'Usage:', direct.stdout)
                self.assertTrue(direct.stdout.startswith(header), direct.stdout)
            if '--json' in args:
                reference = self.call([self.repo/'bin/dots', 'git', 'status', '-C', work,
                                       '--no-wiki', '--json'])
                self.assertEqual(reference.returncode, 0, reference.stderr)
                self.assertEqual(json.loads(direct.stdout), json.loads(reference.stdout))
        for entry in entries:
            outside = self.call(entry)
            self.assertEqual((outside.returncode, outside.stdout), (3, b''))
            self.assertIn(header, outside.stderr)

    @unittest.skipIf(os.name == 'nt', 'the application requires POSIX Bash')
    def test_optional_setup_and_forwarding(self):
        self.assertNotIn('git-it', json.loads(self.cli('install', '--dry-run', '--json').stdout)['components'])
        help_result = self.call([self.repo/'bin/dots', 'git', 'it', 'status', '--help'])
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn(b'--view', help_result.stdout)
        unavailable = self.call([self.repo/'bin/dots', 'git', 'it', '-s'])
        self.assertEqual(unavailable.returncode, 3)
        self.assertIn(b'--with-source git-it', unavailable.stderr)
        pin = self.make_remote()
        self.git(self.repo, 'submodule', 'deinit', '-f', '--', 'plugins/git-it')
        (self.repo/'.git/modules').rename(self.base/'old submodule cache')
        preview = self.cli('install', '--with-source', 'git-it', '--dry-run', '--json')
        row, = json.loads(preview.stdout)['items']
        self.assertEqual((row['status'], row['pin']), ('recorded-commit', pin))
        self.assertFalse((self.plugin/'.git').exists())
        self.cli('install', '--with-source', 'git-it', '--component', 'git-it', '--yes')
        self.assertEqual(self.git(self.plugin, 'rev-parse', 'HEAD'), pin)
        self.assertIn('git-it', json.loads(self.cli('install', '--dry-run', '--json').stdout)['components'])
        target = self.home/'.local/bin/git-it'
        for asset in (target, self.home/'.data/fish/vendor_completions.d/git-it.fish',
                      self.home/'.data/zsh/site-functions/_git-it', self.home/'.data/bash-completion/completions/git-it',
                      self.home/'.local/share/man/man1/git-it.1'):
            self.assertTrue(asset.is_symlink(), asset)
            self.assertTrue(asset.resolve().is_relative_to(self.plugin))
        args = ['status', '-C', 'a b', '--', '']
        for cmd in ([target], [self.repo/'bin/dots', 'git', 'it'],
                    [sys.executable, '-B', self.repo/'lib/dots/cli.py', 'git', 'it']):
            result = self.call([*cmd, *args])
            self.assertEqual(result.returncode, 7, result.stderr)
            self.assertEqual(result.stderr, b'diagnostic\n')
            self.assertEqual(result.stdout.split(b'\0'), [os.fsencode(self.home), *map(os.fsencode, args), b''])
        repeat = json.loads(self.cli('install', '--component', 'git-it', '--dry-run', '--json').stdout)
        self.assertEqual({r['status'] for r in repeat['items'] if r['id'].startswith('dots:git-it:')}, {'unchanged'})
        self.cli('uninstall', '--component', 'git-it', '--yes')
        self.assertFalse(target.is_symlink())
        self.assertTrue((self.plugin/'git-it').exists())
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('separate installation')
        self.cli('install', '--component', 'git-it', '--yes', ok=False)
        self.assertEqual(target.read_text(), 'separate installation')

    @unittest.skipIf(os.name == 'nt', 'the application requires POSIX Bash')
    def test_source_preview_is_local_and_binds_recorded_pin(self):
        from install import update_sources
        pin = self.make_remote()
        self.git(self.plugin, 'status', '--porcelain')
        index = Path(self.git(self.plugin, 'rev-parse', '--path-format=absolute', '--git-path', 'index'))
        asset = self.plugin/'git-it'
        stamp = asset.stat()
        os.utime(asset, ns=(stamp.st_atime_ns, stamp.st_mtime_ns + 4_000_000_000))
        before = index.read_bytes()
        rows = json.loads(self.cli('install', '--with-source', 'git-it', '--dry-run', '--json').stdout)['items']
        self.assertEqual(index.read_bytes(), before)
        self.assertEqual(rows[0]['pin'], pin)
        self.git(self.plugin, 'commit', '--allow-empty', '-m', 'New local revision')
        new_pin = self.git(self.plugin, 'rev-parse', 'HEAD')
        self.git(self.repo, 'update-index', '--cacheinfo', '160000', new_pin, 'plugins/git-it')
        with patch.dict(os.environ, self.env, clear=True), self.assertRaisesRegex(ValueError, 'changed after preview'):
            update_sources(self.repo, rows)
        self.assertEqual(self.git(self.plugin, 'rev-parse', 'HEAD'), new_pin)
        # Registration must identify exactly one real path even when initialized.
        self.git(self.repo, 'config', '--file', '.gitmodules', 'submodule.duplicate.path', 'plugins/git-it')
        self.cli('install', '--with-source', 'git-it', '--dry-run', ok=False)

    @unittest.skipIf(os.name == 'nt', 'the application requires POSIX Bash')
    def test_preexisting_relative_launcher_is_unowned(self):
        self.make_remote()
        target = self.home/'.local/bin/git-it'
        target.parent.mkdir(parents=True, exist_ok=True)
        relative = os.path.relpath(self.plugin/'git-it', target.parent)
        target.symlink_to(relative)
        self.cli('install', '--component', 'git-it', '--yes')
        self.cli('uninstall', '--component', 'git-it', '--yes')
        self.assertEqual(os.readlink(target), relative)

    @unittest.skipIf(os.name == 'nt', 'the application requires POSIX Bash')
    def test_parent_update_replans_changed_gitlink(self):
        original = self.make_remote()
        (self.repo/'.gitignore').write_text('*\n')
        self.git(self.repo, 'add', '-f', '.gitignore')
        self.git(self.repo, 'commit', '-m', 'Ignore fixture support files')
        remote = self.base/'dots.git'
        writer = self.base/'dots writer'
        self.git(self.base, 'clone', '--bare', str(self.repo), str(remote))
        self.git(self.repo, 'remote', 'add', 'origin', str(remote))
        self.git(self.repo, 'fetch', 'origin')
        self.git(self.repo, 'branch', '--set-upstream-to', 'origin/main')
        self.git(self.base, 'clone', '--no-recurse-submodules', str(remote), str(writer))
        src = self.base/'standalone'
        self.git(src, 'commit', '--allow-empty', '-m', 'New plugin commit')
        self.git(src, 'push', str(self.base/'public.git'), 'main')
        new = self.git(src, 'rev-parse', 'HEAD')
        self.git(writer, 'update-index', '--cacheinfo', '160000', new, 'plugins/git-it')
        self.git(writer, 'commit', '-m', 'Advance the plugin')
        self.git(writer, 'push', 'origin', 'main')
        preview = self.cli('install', '--update', '--with-source', 'git-it', '--dry-run', '--json')
        self.assertEqual(json.loads(preview.stdout)['items'][-1]['pin'], original)
        self.cli('install', '--update', '--with-source', 'git-it', '--component', 'git-it', '--yes')
        self.assertEqual(self.git(self.plugin, 'rev-parse', 'HEAD'), new)

    @unittest.skipIf(os.name == 'nt', 'the application requires POSIX Bash')
    def test_occupied_directory_and_absent_gitlink(self):
        self.git(self.repo, 'init', '-b', 'main')
        self.cli('install', '--with-source', 'git-it', '--dry-run', ok=False)
        self.plugin.mkdir()
        self.git(self.plugin, 'init', '-b', 'main')
        result = self.cli('install', '--component', 'git-it', '--dry-run', '--json', ok=False)
        self.assertIn('occupied', result.stdout)
        self.assertNotIn('git-it', json.loads(self.cli('install', '--dry-run', '--json').stdout)['components'])
        independent = self.base/'independent'
        self.plugin.rename(independent)
        self.make_remote()
        self.plugin.rename(self.base/'actual submodule')
        independent.rename(self.plugin)
        self.assertIn('occupied', self.cli('install', '--with-source', 'git-it', '--dry-run', ok=False).stderr)
        self.assertNotIn('git-it', json.loads(self.cli('install', '--dry-run', '--json').stdout)['components'])

    def test_native_windows_static_help_and_runtime_capability(self):
        import bundled_apps
        self.plugin.mkdir()
        executable = self.plugin/'git-it'
        executable.write_text('fixture')
        executable.chmod(0o755)
        output, diagnostic = io.StringIO(), io.StringIO()
        with patch.dict(os.environ, self.env, clear=True), patch.object(bundled_apps, 'os') as runtime, \
                redirect_stdout(output), redirect_stderr(diagnostic):
            runtime.name = 'nt'
            self.assertEqual(bundled_apps.run_git_it(self.repo, ['status', '--help']), 0)
            self.assertIn('--view', output.getvalue())
            self.assertIn('dots git it status', output.getvalue())
            self.assertEqual(bundled_apps.run_git_it(self.repo, ['status']), 3)
            self.assertIn('requires Bash 5', diagnostic.getvalue())
            runtime.execve.assert_not_called()


if __name__ == '__main__':
    unittest.main()

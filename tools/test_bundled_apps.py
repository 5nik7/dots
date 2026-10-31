#!/usr/bin/env python3
"""Bundled routing and combined installation in disposable roots only."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_installation as setup_fixture
from test_installation import Installation, ROOT


class BundledApps(unittest.TestCase):
    write = setup_fixture.InstallationTests.write
    cli = setup_fixture.InstallationTests.cli
    receipt = setup_fixture.InstallationTests.receipt

    def setUp(self):
        setup_fixture.InstallationTests.setUp(self)
        self.env.update(BLASTOFF_HOME=str(self.home/'blastoff'), STARSHIP_CONFIG=str(self.home/'starship.toml'),
                        BLASTOFF_PYTHON=sys.executable, PKGS_FUZZY_TAB='0',
                        PATH=str(self.repo/'bin')+os.pathsep+os.environ['PATH'])
        shutil.copytree(ROOT/'lib/dots', self.repo/'lib/dots', ignore=shutil.ignore_patterns('__pycache__'))
        # Catalog/command installation tests do not need theme publication.
        for name in ('setup.py', 'setup.bash'):
            (self.repo/'lib/dots/themes'/name).unlink()
        shutil.copytree(ROOT/'bin', self.repo/'bin', dirs_exist_ok=True, symlinks=True)
        for name in ('install.sh', 'uninstall.sh', 'install.ps1', 'uninstall.ps1'):
            shutil.copy2(ROOT/name, self.repo/name)
        shutil.copytree(ROOT/'plugins', self.repo/'plugins', ignore=shutil.ignore_patterns('__pycache__', 'tests', '.build'))
        shutil.copy2(ROOT/'plugins/manifest.json', self.repo/'plugins/manifest.json')

    def call(self, argv, code=0):
        result = subprocess.run(list(map(str, argv)), cwd=self.home, env=self.env,
                                capture_output=True, timeout=30)
        self.assertEqual(result.returncode, code, (argv, result.stdout, result.stderr))
        return result.stdout, result.stderr, result.returncode

    def surfaces(self, app, args):
        if os.name != 'nt':
            yield [self.repo/'bin'/app, *args]
            yield [self.repo/'bin/dots', app, *args]
        yield [sys.executable, '-B', self.repo/'lib/dots/cli.py', app, *args]

    def test_real_help_version_and_raw_completion_equivalence(self):
        for app, examples in (
            ('blastoff', [[], ['--help'], ['--version'], ['theme', 'apply', '--help'],
                         ['--json'], ['completion', 'bash'], ['completion', 'zsh'], ['completion', 'fish']]),
            ('pkgs', [[], ['--help'], ['--version'], ['install', '--help']]),
        ):
            for args in examples:
                results = [self.call(command) for command in self.surfaces(app, args)]
                self.assertTrue(all(value == results[0] for value in results), (app, args))
                self.assertNotIn(b'\x1b', results[0][0])
        self.assertEqual(list(self.home.iterdir()), [])

    def test_all_routes_forward_literal_arguments_and_status(self):
        rows = json.loads((ROOT/'lib/dots/metadata/bundled-apps.json').read_text())
        for app, entry in (('blastoff', 'lib/blastoff.py'), ('pkgs', 'main.py')):
            (self.repo/'plugins'/app/entry).write_text("import json,sys\nprint(json.dumps(sys.argv[1:], ensure_ascii=True))\nprint('fixture stderr',file=sys.stderr)\nsys.exit(47)\n")
        literal = ['--help', '', 'two words', 'ü', 'quote\"', "single'quote", '--', '-leading', '$(touch escaped)']
        for stem in rows:
            app, *route = stem.split('-')
            for command in self.surfaces(app, [*route, *literal]):
                out, err, _ = self.call(command, 47)
                self.assertEqual(json.loads(out), [*route, *literal])
                self.assertEqual(err, b'fixture stderr\n')
        self.assertFalse((self.home/'escaped').exists())

    def test_static_completion_with_global_options_does_not_execute_apps(self):
        for app, entry in (('blastoff', 'lib/blastoff.py'), ('pkgs', 'main.py')):
            (self.repo/'plugins'/app/entry).write_text("raise SystemExit('must not execute')\n")
        cases = [(['blastoff', '--json', 'theme', 'a'], 'apply'),
                 (['blastoff', 'theme', 'apply', '--color', 'n'], 'never'),
                 (['pkgs', '--manager', 'npm', 'ins'], 'install'),
                 (['pkgs', 'install', '--manager=uv'], '--manager=uv-tool'),
                 (['pkgs', 'completion', 'zsh', 'un'], 'uninstall')]
        for words, expected in cases:
            native = self.call([sys.executable, '-B', self.repo/'lib/dots/cli.py', '__complete', *words])[0]
            self.assertIn(expected.encode(), native)
            if os.name != 'nt':
                bash = self.call([self.repo/'bin/dots', '__complete', 'bash', str(len(words)), '--', 'dots', *words])[0]
                self.assertEqual(bash, native)
        self.call([sys.executable, '-B', self.repo/'lib/dots/cli.py', 'commands', '--check'])
        self.assertEqual(list(self.home.iterdir()), [])

    def test_metadata_is_current(self):
        self.call([sys.executable, '-B', ROOT/'tools/generate_bundled_apps.py', '--check'])

    def test_missing_blastoff_runtime_preserves_dependency_status(self):
        self.env['BLASTOFF_PYTHON'] = str(self.home/'missing runtime')
        results = [self.call(command, 3) for command in self.surfaces('blastoff', ['--version'])]
        self.assertTrue(all(result == results[0] for result in results))
        self.assertIn(b'Python runtime unavailable', results[0][1])

    @unittest.skipIf(os.name == 'nt', 'POSIX runtime-free version shortcut')
    def test_pkgs_version_needs_no_python(self):
        bash = shutil.which('bash')
        self.env['PATH'] = ''
        version = (self.repo/'plugins/pkgs/VERSION').read_text().strip()
        self.assertEqual(self.call([bash, self.repo/'bin/pkgs', '--version'])[0], ('pkgs '+version+'\n').encode())

    @unittest.skipIf(os.name == 'nt', 'pkgs backend/completion management is POSIX-only')
    def test_fish_completion_status_and_shared_ownership(self):
        fish = self.repo/'shells/fish'
        (fish/'completions').mkdir(parents=True)
        target = fish/'completions/pkgs.fish'
        target.symlink_to('../../../plugins/pkgs/completions/pkgs.fish')
        config = self.home/'.config/fish'
        config.parent.mkdir(parents=True)
        config.symlink_to(fish, target_is_directory=True)
        data = json.loads(self.call([self.repo/'bin/pkgs', 'completion', 'fish', 'status', '--json'])[0])
        self.assertEqual(data['status'], 'current')
        self.assertIn('autoloads', data['activation'])
        result = self.call([self.repo/'bin/pkgs', 'completion', 'fish', 'uninstall'], 1)
        self.assertIn(b'Bundled Dots completion left untouched', result[1])
        self.assertTrue(target.is_symlink())
        self.assertFalse((self.home/'.state').exists())

    @unittest.skipIf(os.name == 'nt', 'POSIX public scripts; native adapters tested separately')
    def test_public_lifecycle_scripts_share_the_complete_plan(self):
        for action in ('install', 'uninstall'):
            root = self.call(['sh', self.repo/(action+'.sh'), '--dry-run', '--json'])
            for app in ('blastoff', 'pkgs'):
                self.assertEqual(self.call(['sh', self.repo/'plugins'/app/(action+'.sh'), '--dry-run', '--json']), root)
        self.assertFalse((self.home/'.state').exists())

    @unittest.skipIf(os.name == 'nt', 'Bash completion surface')
    def test_exact_root_completion_keeps_the_command_name(self):
        for app in ('blastoff', 'pkgs'):
            out = self.call([self.repo/'bin/dots', '__complete', 'bash', '1', '--', 'dots', app])[0]
            self.assertIn(('candidate\t'+app+'\t').encode(), out)
            self.assertNotIn(b'candidate\tinstall\t', out)

    def test_combined_install_idempotence_and_restore(self):
        for app in ('blastoff', 'pkgs'):
            target = self.home/'.local/bin'/app
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('original '+app)
        before = sorted(str(p) for p in self.home.rglob('*'))
        self.cli('install', '--dry-run', '--json')
        self.assertEqual(before, sorted(str(p) for p in self.home.rglob('*')))
        self.cli('install', '--yes')
        if os.name != 'nt':
            installed = self.call([self.home/'.local/bin/anodize', '--help'])
            prefixed = self.call([self.repo/'bin/dots', 'anodize', '--help'])
            self.assertIn(b'Anodize', installed[0])
            self.assertIn(b'anodize', prefixed[0].lower())
        receipt = self.receipt()
        self.assertEqual(json.loads(self.cli('install', '--yes', '--json').stdout)['status'], 'unchanged')
        self.assertEqual(receipt, self.receipt())
        if os.name != 'nt':
            for app in ('blastoff', 'pkgs'):
                target = self.home/'.local/bin'/app
                self.assertEqual(target.resolve(), (self.repo/'bin'/app).resolve())
                self.call([target, '--version'])
                self.assertTrue((self.home/'.data/bash-completion/completions'/app).is_symlink())
                self.assertTrue((self.home/'.data/zsh/site-functions'/('_'+app)).is_symlink())
                self.assertTrue((self.home/'.local/share/man/man1'/(app+'.1')).is_symlink())
        state = self.home/'blastoff/user-theme.toml'
        state.parent.mkdir(); state.write_text('retained user data')
        self.cli('uninstall', '--yes')
        self.assertEqual(state.read_text(), 'retained user data')
        for app in ('blastoff', 'pkgs'):
            self.assertEqual((self.home/'.local/bin'/app).read_text(), 'original '+app)
        self.assertEqual(self.receipt()['entries'], {})

    @unittest.skipIf(os.name == 'nt', 'POSIX link collision; native capability tested separately')
    def test_collision_and_missing_payload_block_all_targets(self):
        target = self.home/'.local/bin/pkgs'
        target.parent.mkdir(parents=True)
        target.symlink_to(self.home/'foreign missing command')
        result = self.cli('install', '--dry-run', '--json', ok=False)
        self.assertIn('unrelated link', result.stdout)
        self.cli('install', '--yes', '--json', ok=False)
        self.assertFalse(self.target.exists())
        self.assertFalse((self.home/'.state').exists())
        target.unlink()
        (self.repo/'plugins/blastoff/lib/blastoff.py').unlink()
        self.assertIn('incomplete', self.cli('install', '--dry-run', '--json', ok=False).stdout)
        self.assertFalse(self.target.exists())

    @unittest.skipIf(os.name == 'nt', 'POSIX link drift; native capability tested separately')
    def test_drift_preserved_and_preexisting_links_unowned(self):
        blastoff = self.home/'.local/bin/blastoff'
        blastoff.parent.mkdir(parents=True)
        blastoff.symlink_to(self.repo/'bin/blastoff')
        self.cli('install', '--yes')
        self.assertNotIn(str(blastoff), self.receipt()['entries'])
        pkgs = self.home/'.local/bin/pkgs'
        pkgs.unlink(); pkgs.write_text('changed after install')
        self.cli('uninstall', '--yes', ok=False)
        self.assertEqual(pkgs.read_text(), 'changed after install')
        self.assertTrue(blastoff.is_symlink())

    def test_native_windows_plan_uses_powershell_without_bash(self):
        with patch.dict(os.environ, self.env, clear=True):
            plan = Installation(self.repo)
            plan.platform = 'windows'
            plan.plan_bundled_apps(self.home)
            self.assertEqual(len(plan.operations), 3)
            for app, operation in zip(('anodize', 'blastoff', 'pkgs'), plan.operations):
                self.assertEqual(operation['path'], str(self.home/'.local/bin'/(app+'.ps1')))
                self.assertIn(app+'.ps1', operation['text'])
                self.assertNotIn('bash', operation['text'])

    def test_bundled_failure_rolls_back_commands_and_baseline(self):
        target = self.home/'.local/bin'/('blastoff.ps1' if os.name == 'nt' else 'blastoff')
        target.parent.mkdir(parents=True)
        target.write_text('original launcher')
        with patch.dict(os.environ, self.env, clear=True):
            plan = Installation(self.repo)
            plan.plan_install()
            save = plan.store.save
            failed = False
            def fail(record):
                nonlocal failed
                save(record)
                if not failed and record['status'] == 'applying' and any(
                        item['path'] == str(target) and item['phase'] == 'done'
                        for item in record['operations']):
                    failed = True
                    raise OSError('injected bundled failure')
            with patch.object(plan.store, 'save', side_effect=fail):
                with self.assertRaisesRegex(OSError, 'injected bundled failure'):
                    plan.apply('install')
        self.assertTrue(failed)
        self.assertEqual(target.read_text(), 'original launcher')
        self.assertFalse(self.target.exists())
        self.assertFalse((self.home/'.state/dots/installation.json').exists())

    def test_native_powershell_entrypoints(self):
        engine = os.environ.get('DOTS_TEST_POWERSHELL') or shutil.which('pwsh')
        if not engine:
            self.skipTest('native PowerShell unavailable')
        for app in ('blastoff', 'pkgs'):
            standalone = self.call([engine, '-NoLogo', '-NoProfile', '-File', self.repo/'bin'/(app+'.ps1'), '--version'])
            prefixed = self.call([engine, '-NoLogo', '-NoProfile', '-File', self.repo/'bin/dots.ps1', app, '--version'])
            self.assertEqual(standalone, prefixed)

    def test_native_pkgs_dispatch_reaches_shared_core(self):
        spec = importlib.util.spec_from_file_location('pkgs_windows_entry', self.repo/'plugins/pkgs/main.py')
        entry = importlib.util.module_from_spec(spec); spec.loader.exec_module(entry)
        from types import SimpleNamespace
        from unittest.mock import Mock
        run = Mock(return_value=7)
        for words in (['install','Vendor.App'],['in','Vendor.App'],['un','Vendor.App'],['up'],['xup'],['upls'],
                      ['upgrade','ls'],['upgrade','--list'],['cleanup','--json']):
            with self.subTest(words=words), patch.object(entry.os, 'name', 'nt'), \
                 patch.object(sys, 'argv', ['pkgs', *words]), patch.dict(sys.modules, {'pkgs_lib.cli':SimpleNamespace(main=run)}):
                self.assertEqual(entry.main(), 7)
        self.assertEqual(run.call_count,9)

    def test_blastoff_native_aliases_use_existing_transport(self):
        self.env['DOTS_POWERSHELL'] = str(self.home/'native shell must not run')
        native = [sys.executable, '-B', self.repo/'lib/dots/cli.py', 'blastoff']
        self.assertEqual(self.call([*native, '-help']), self.call([*native, '--help']))
        self.assertEqual(list(self.home.iterdir()), [])

    @unittest.skipIf(os.name == 'nt', 'POSIX package picker')
    def test_hosted_pkgs_picker_disables_only_supported_popup_mode(self):
        fake = self.home/'fzf'
        self.env['DOTS_MENU_SPOOL_DIR'] = str(self.home/'private host')
        source = "import sys,json;sys.path.insert(0,sys.argv[1]);from pkgs_lib.fzf import invocation;print(json.dumps(invocation(sys.argv[2])[0]))"
        for modern in (False, True):
            fake.write_text('#!'+sys.executable+'\nimport sys\nprint('+repr('0.74' if modern else '0.48')+" if '--version' in sys.argv else "+repr('--tmux' if modern else 'legacy help')+')\n')
            fake.chmod(0o755)
            out = self.call([sys.executable,'-B','-c',source,self.repo/'plugins/pkgs',fake])[0]
            self.assertEqual('--no-tmux' in json.loads(out), modern)


if __name__ == '__main__':
    unittest.main()

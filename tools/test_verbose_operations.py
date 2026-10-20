#!/usr/bin/env python3
"""Verbose action contracts in disposable file, setup and theme fixtures."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock

import test_file_operations as files
import test_installation as setup
import test_themes as themes
import test_progress as progress
import test_theme_picker as picker
import test_resources as resource_fixtures
from transactions import Store, digest
from events import OperationOutput

ROOT = Path(__file__).resolve().parents[1]


class FileVerbose(unittest.TestCase):
    setUp = files.Operations.setUp
    write = files.Operations.write
    run_cli = files.Operations.run_cli
    records = files.Operations.records

    def test_adoption_cleanup_and_json(self):
        before = self.run_cli('add', self.path, '--dry-run', '--json').stdout
        verbose = self.run_cli('add', self.path, '--dry-run', '--json', '-v', DOTS_COLOR='always', DOTS_ICONS='always')
        self.assertEqual(before, verbose.stdout)
        self.assertEqual(verbose.stderr, '')
        preview = self.run_cli('add', self.path, '--dry-run', '-v')
        self.assertIn('Would import', preview.stderr)
        self.assertNotIn('Recovery copy', preview.stderr)
        result = self.run_cli('add', self.path, '--yes', '-v')
        self.assertIn('Recovery copy', result.stderr)
        self.assertIn('Copied', result.stderr)
        self.assertIn('Linked', result.stderr)
        self.assertIn('Cleaned', result.stderr)
        self.assertNotIn('Backup kept', result.stderr)
        self.assertNotIn('\x1b', result.stderr)
        source = self.repo / self.records()[0]['source']
        self.assertEqual(self.path.resolve(), source)
        again = self.run_cli('add', self.path, '--yes', '--verbose')
        self.assertIn('Unchanged', again.stderr)
        self.assertNotIn('Linked', again.stderr)
        self.assertNotIn('Recovery copy', again.stderr)

    def test_retained_backup_undo_and_remove(self):
        result = self.run_cli('add', self.path, '--backup', '--yes', '-v')
        self.assertIn('Backup kept', result.stderr)
        self.assertLess(result.stderr.index('Recovery copy'), result.stderr.index('Linked'))
        self.assertLess(result.stderr.index('Linked'), result.stderr.index('Backup kept'))
        backups = json.loads(self.run_cli('backups-list', '--json').stdout)['items']
        identity = backups[0]['id']
        self.assertIn(identity, result.stderr.replace('\n      ', ''))
        for entry in backups[0]['objects']:
            self.assertIsNotNone(entry['before'])
        undo = self.run_cli('undo', identity, '--yes', '-v')
        self.assertIn('Restored', undo.stderr)
        self.assertFalse(self.path.is_symlink())
        self.assertEqual(self.path.read_text(), 'original\n')
        self.run_cli('add', self.path, '--yes')
        rid = 'dots:' + self.records()[0]['id']
        removed = self.run_cli('remove', rid, '--yes', '-v')
        self.assertIn('Copied', removed.stderr)
        self.assertTrue(self.path.is_file())
        self.assertFalse(self.path.is_symlink())

    def test_observer_failure_and_rollback_do_not_change_journals(self):
        state = self.home / '.state/dots'
        observer = mock.Mock(side_effect=RuntimeError('display unavailable'))
        store = Store(state, observer)
        result = store.apply('fixture', [dict(path=str(self.path), text='new')],
                             {str(self.path): digest(self.path)})
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(self.path.read_text(), 'new')
        self.assertNotIn('observer', json.dumps(result))
        events = []
        store.observer = lambda *args, **kw: events.append((args, kw))
        original = store.save
        def fail(doc):
            original(doc)
            if doc['status'] == 'applying' and any(e['phase'] == 'done' for e in doc['operations']):
                raise OSError('injected after replacement')
        with mock.patch.object(store, 'save', side_effect=fail):
            with self.assertRaisesRegex(OSError, 'injected'):
                store.apply('fixture', [dict(path=str(self.path), text='changed')],
                            {str(self.path): digest(self.path)}, retain=True)
        self.assertEqual(self.path.read_text(), 'new')
        self.assertIn('Rolled back', [event[0][0] for event in events])
        self.assertNotIn('Backup kept', [event[0][0] for event in events])

    def test_restore_and_recovery_trace(self):
        self.run_cli('add', self.path, '--yes', '--backup')
        backup = json.loads(self.run_cli('backups-list', '--json').stdout)['items'][0]['id']
        restored = self.run_cli('backups-restore', backup, '--yes', '-v')
        self.assertIn('Restored', restored.stderr)
        self.assertFalse(self.path.is_symlink())
        store = Store(self.home/'.state/dots')
        original = store.save
        def interrupted(doc):
            original(doc)
            if doc['status'] == 'applying' and any(e['phase'] == 'done' for e in doc['operations']):
                raise OSError('injected interruption')
        with mock.patch.object(store, 'save', side_effect=interrupted), mock.patch.object(store, 'rollback', side_effect=OSError('interrupted recovery')):
            with self.assertRaises(OSError):
                store.apply('fixture', [dict(path=str(self.path), text='interrupted')], {str(self.path): digest(self.path)})
        identity = next(row['id'] for row in store.records() if row['status'] == 'recovery-required')
        recovered = self.run_cli('recover', identity, '--yes', '-v')
        self.assertIn('Rolled back', recovered.stderr)
        self.assertIn('Cleaned', recovered.stderr)
        self.assertEqual(self.path.read_text(), 'original\n')

    def test_metadata_operations(self):
        self.run_cli('add', self.path, '--yes')
        identity = 'dots:' + self.records()[0]['id']
        def cli(script, *args):
            result = subprocess.run([sys.executable, '-B', str(ROOT/'lib/dots/files'/script), *args],
                                    env=self.env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            return result
        result = cli('mappings.py', 'edit', identity, '--source', self.records()[0]['source'], '--yes', '-v')
        self.assertNotIn('Linked', result.stderr)
        result = cli('mappings.py', 'stash', identity, '--yes', '-v')
        self.assertIn('Updated', result.stderr)
        self.assertIn('metadata', result.stderr)
        # Check reports absent sources but never deletes target data.
        self.path.unlink(missing_ok=True)
        (self.repo/self.records()[0]['source']).unlink()
        result = cli('check.py', '--yes', '--verbose')
        self.assertIn('Updated', result.stderr)
        self.assertIn('Removed', result.stderr)


class SetupVerbose(unittest.TestCase):
    setUp = setup.InstallationTests.setUp
    write = setup.InstallationTests.write
    cli = setup.InstallationTests.cli
    receipt = setup.InstallationTests.receipt

    def test_setup_replace_idempotence_uninstall(self):
        self.target.parent.mkdir(parents=True)
        self.target.write_text('before')
        result = self.cli('install', '--yes', '-v')
        self.assertIn('Backup kept', result.stderr)
        self.assertIn('Linked', result.stderr)
        receipt = self.receipt()
        again = self.cli('install', '--yes', '--verbose')
        self.assertEqual(receipt, self.receipt())
        self.assertIn('Unchanged', again.stderr)
        result = self.cli('uninstall', '--yes', '-v')
        self.assertIn('Restored', result.stderr)
        self.assertEqual(self.target.read_text(), 'before')

    def test_setup_dry_run_and_data(self):
        plain = self.cli('install', '--dry-run')
        verbose = self.cli('install', '--dry-run', '-v')
        self.assertEqual(plain.stdout, verbose.stdout)
        self.assertIn('Would create', verbose.stderr)
        self.assertFalse((self.home/'.state').exists())
        plain = self.cli('install', '--dry-run', '--json')
        verbose = self.cli('install', '--dry-run', '--json', '-v')
        self.assertEqual(plain.stdout, verbose.stdout)
        self.assertEqual(verbose.stderr, '')


class ThemeVerbose(unittest.TestCase):
    setUp = themes.Themes.setUp
    run_command = themes.Themes.run_command
    dots = themes.Themes.dots
    shell = themes.Themes.shell
    generation = themes.Themes.generation
    engine = themes.Themes.engine

    def test_theme_links_recovery_and_refresh(self):
        target = self.home/'config/kitty/dots-theme.conf'
        target.parent.mkdir(parents=True)
        target.write_text('original')
        self.env['DOTS_ICONS'] = 'never'
        preview = self.dots('theme', 'set', 'nord', '--dry-run', '-v')
        self.assertIn('Would link', preview.stderr)
        self.assertFalse(self.state.exists())
        result = self.dots('theme', 'set', 'nord', '--verbose')
        self.assertIn('Recovery copy', result.stderr)
        self.assertIn('Linked', result.stderr)
        self.assertIn('Published', result.stderr)
        self.assertIn('Skipped', result.stderr)
        generation = self.generation()
        result = self.dots('theme', 'refresh', '-v')
        self.assertEqual(self.generation(), generation)
        self.assertIn('Unchanged', result.stderr)
        self.assertNotIn('Recovery copy', result.stderr)
        result = self.dots('theme', 'refresh', '-v', '--commands-only')
        self.assertIn('Unchanged', result.stderr)
        result = self.engine('DOTS_OPERATION_VERBOSE=1; dt_restore "' + str(generation) + '"')
        self.assertIn('Rolled back', result.stderr)
        self.assertEqual(target.read_text(), 'original')

    def test_metadata_aliases_and_data_routes(self):
        for route in (('theme', 'set'), ('theme', 'refresh'), ('theme', 'switcher'), ('themes', 'switcher')):
            self.assertIn('--verbose', self.dots('help', *route).stdout)
            for shell in ('bash', 'zsh', 'fish'):
                args = ['dots', *route, '-']
                result = self.dots('__complete', shell, str(len(args)-1), '--', *args)
                self.assertIn('candidate\t--verbose\t', result.stdout)
                self.assertIn('candidate\t-v\t', result.stdout)
        family = self.dots('theme', 'catppuccin', 'mocha', 'set', '--dry-run', '-v')
        self.assertIn('Would publish', family.stderr)
        standalone = self.run_command([str(self.repo/'bin/theme'), 'set', 'nord', '--dry-run', '-v'])
        self.assertIn('Would publish', standalone.stderr)
        self.dots('commands', '--check')
        self.dots('theme', 'current', '--verbose', code=2)
        self.dots('theme', 'refresh', '--dry-run', '--verbose', code=2)
        self.assertFalse(self.state.exists())



class VerboseTerminal(unittest.TestCase):
    setUp = progress.ProgressTests.setUp
    terminal = progress.ProgressTests.terminal
    bash = progress.ProgressTests.bash
    python = progress.ProgressTests.python

    def test_progress_survives_permanent_rows(self):
        python = self.python("sys.path.insert(0, " + repr(str(ROOT/'lib/dots/files')) + ")\nfrom events import OperationOutput\noutput=OperationOutput(True)\nwith progress.Progress('Waiting'):\n time.sleep(.65)\n progress.report('Linking',1,3)\n output('Linked', os.environ['HOME']+'/source.toml', os.environ['HOME']+'/-target 界.toml', kind='file', target_kind='symlink')\n time.sleep(.2)\nprint('done')")
        bash = self.bash('source ' + str(ROOT/'lib/dots/verbose.bash') + '; DOTS_OPERATION_VERBOSE=1; dots::progress_start Waiting; sleep .65; dots::progress_update Linking 1 3; dots::operation Linked "$HOME/source.toml" "$HOME/-target 界.toml" "" file symlink; sleep .2; dots::progress_stop; echo done')
        for command in (python, bash):
            for width in (40,80,120):
                for color, icons in (('always','always'), ('never','never')):
                    env = dict(self.env, DOTS_COLOR=color, DOTS_ICONS=icons, COLUMNS=str(width))
                    code, data = self.terminal(command, env, width)
                    self.assertEqual(code, 0, data)
                    self.assertIn(b'Linked', data)
                    self.assertIn(b'1/3', data)
                    self.assertIn(b'->', data)
                    self.assertTrue(data.endswith(b'done\r\n'), data)
                    if color == 'never': self.assertNotIn(b'\x1b', data)
                    else: self.assertIn(b'\x1b', data)
                    clean = progress.ANSI.sub(b'', data).decode()
                    self.assertIn('source.toml', clean)
                    self.assertIn('-target', clean.replace('\r\n      ', ''))
                    # A resumed frame must appear after the persistent action.
                    self.assertIn('Linking', clean[clean.index('Linked'):])

    def test_disabled_progress_controls_and_interruption(self):
        python = self.python("sys.path.insert(0, " + repr(str(ROOT/'lib/dots/files')) + ")\nfrom events import OperationOutput\noutput=OperationOutput(True)\ntry:\n with progress.Progress('First'):\n  time.sleep(.6)\n  output('Linked', os.environ['HOME']+'/bad\\x1b[31m.toml', kind='file')\n  progress.report('Waiting')\n  time.sleep(.65)\nexcept KeyboardInterrupt: sys.exit(130)\nprint('done')")
        bash = self.bash('source ' + str(ROOT/'lib/dots/verbose.bash') + '; DOTS_OPERATION_VERBOSE=1; trap "dots::progress_stop; exit 130" INT; dots::progress_start First; sleep .6; dots::operation Linked "$HOME/source.toml"; dots::progress_update Waiting; sleep .65; dots::progress_stop; echo done')
        for command in (python, bash):
            for settings in (dict(DOTS_PROGRESS='never'), dict(TERM='dumb')):
                code, data = self.terminal(command, dict(self.env, DOTS_COLOR='never', **settings))
                self.assertEqual(code, 0, data)
                self.assertIn(b'Linked', data)
                self.assertNotIn(b'Waiting', data)
                self.assertNotIn(b'\x1b', data)
            code, data = self.terminal(command, interrupt=True)
            self.assertEqual(code, 130, data)
            self.assertIn(b'Linked', data)

    def test_published_file_styles_and_icon_independence(self):
        fixture = resource_fixtures.ResourcesTests('test_published_rules_and_native_kind_parity')
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        source = fixture.home/'settings.toml'
        source.write_text('fixture')
        python = self.python("sys.path.insert(0, " + repr(str(ROOT/'lib/dots/files')) + ")\nfrom events import OperationOutput\nOperationOutput(True)('Linked', " + repr(str(source)) + ", kind='file')")
        bash = self.bash('source ' + str(ROOT/'lib/dots/verbose.bash') + '; DOTS_OPERATION_VERBOSE=1; dots::operation Linked "$HOME/settings.toml" "" "" file')
        for foreground, sgr in (('#aabbcc', b'38;2;170;187;204'), ('#223344', b'38;2;34;51;68')):
            fixture.doc['styles']['extension']['.toml'] = {'fg':foreground}
            resource_fixtures.fc.write_snapshot(fixture.doc, fixture.theme)
            for command in (python, bash):
                for color, icons in (('always','never'), ('never','always'), ('always','always')):
                    env = dict(fixture.env, PYTHONPATH=str(ROOT/'lib/dots'), DOTS_COLOR=color, DOTS_ICONS=icons, NO_COLOR='1')
                    code, data = self.terminal(command, env)
                    self.assertEqual(code, 0, data)
                    if color == 'always': self.assertIn(sgr, data)
                    else: self.assertNotIn(b'\x1b', data)
                    plain = progress.ANSI.sub(b'', data).decode()
                    self.assertIn('~/settings.toml', plain)
                    glyph = resource_fixtures.Resources(fixture.theme).describe(source)[1]
                    self.assertEqual(glyph in plain, icons == 'always')

    def test_real_install_in_terminal(self):
        fixture = setup.InstallationTests('test_dry_run_and_idempotent_install_restore')
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.target.parent.mkdir(parents=True)
        fixture.target.write_text('original')
        env = dict(fixture.env, TERM='xterm-256color', DOTS_COLOR='always', DOTS_ICONS='always')
        command = [sys.executable, '-B', str(ROOT/'lib/dots/files/install.py'), 'install', '--yes', '-v']
        code, data = self.terminal(command, env)
        self.assertEqual(code, 0, data)
        self.assertIn(b'Linked', data)
        self.assertIn(b'Backup kept', data)
        self.assertTrue(fixture.target.is_symlink())


class SwitcherVerbose(unittest.TestCase):
    def setUp(self):
        self.fixture = picker.Picker(next(name for name in dir(picker.Picker) if name.startswith('test_')))
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        for name in ('home', 'state', 'env', 'fake', 'root', 'repo', 'calls', 'script'):
            setattr(self, name, getattr(self.fixture, name))
    fixture_ui = picker.Picker.fixture_ui
    queue = picker.Picker.queue
    terminal = picker.Picker.terminal

    def test_apply_and_cancel(self):
        self.fixture_ui()
        self.queue(actions=('Cancel',))
        script = self.script.replace('dt_command switcher\n', 'dt_command switcher --verbose\n')
        self.terminal(script)
        self.assertFalse(self.state.exists())
        self.queue(actions=('Apply',))
        data = self.terminal(script)
        self.assertIn(b'Published', data)
        self.assertTrue(self.state.exists())

if __name__ == '__main__':
    unittest.main(verbosity=2)

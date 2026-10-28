"""Theme-list appearance and bounded, read-only origin observations."""
import io
import json
import os
import re
import shutil
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch

from release_support import ReleaseHarness
from test_blastoff import ROOT, core


class ListOutput(ReleaseHarness):
    def loaded(self):
        self.theme('aurora', 'x=2\n')
        self.theme('blastoff', 'x=1\n')
        self.invoke('theme', 'apply', 'blastoff')

    def record(self):
        return next((self.store/'state/provenance').glob('*.json'))

    def in_process(self, arguments=('list',), presets=()):
        out, err = io.StringIO(), io.StringIO()
        with patch.dict(os.environ, self.env, clear=True), redirect_stdout(out), redirect_stderr(err), \
             patch.object(core.App, 'optional_presets', return_value=(list(presets), {'status':'ok', 'error':None})):
            self.assertEqual(core.run(list(arguments)), 0)
        return out.getvalue(), err.getvalue()

    def test_current_aliases_plain_and_read_only(self):
        self.loaded()
        self.theme('duplicate', 'x=1\n')
        before = self.tree()
        plain = self.invoke('list').stdout
        self.assertIn('THEMES\n  local:aurora\n  local:blastoff  [current]\n  local:duplicate\nPRESETS\n', plain)
        for arguments in [('theme','list'), ('-l',), ('--list',), ('list','--dry-run')]:
            self.assertEqual(self.invoke(*arguments).stdout, plain)
        self.assertNotIn('\x1b', plain)
        self.assertEqual(before, self.tree())

    def test_color_roles_controls_and_resets(self):
        self.loaded()
        self.env.pop('NO_COLOR')
        self.env['TERM'] = 'xterm-256color'
        self.env.update(DOTS_MENU_CAPTURE='1', DOTS_COLOR='never', DOTS_ICONS='never')
        plain = self.invoke('list').stdout
        colored = self.invoke('list', '--color', 'always').stdout
        self.assertIn('\x1b[2mlocal:\x1b[0m\x1b[94maurora\x1b[0m', colored)
        self.assertIn('\x1b[94mblastoff\x1b[0m', colored)
        self.assertIn('\x1b[92m  [current]\x1b[0m\n', colored)
        self.assertEqual(re.sub(r'\x1b\[[0-9;]*m', '', colored), plain)
        self.assertNotIn('\x1b', self.invoke('list','--color','never').stdout)
        self.env['DOTS_COLOR'] = 'auto'
        self.assertIn('\x1b', self.run_tty(['list'])[1])
        self.env['NO_COLOR'] = '1'
        self.assertIn('\x1b', self.invoke('list','--color','always').stdout)
        self.assertNotIn('\x1b', self.run_tty(['list'])[1])

    def test_modified_and_independently_changed_source(self):
        self.loaded()
        self.config.write_text('x=3\n')
        self.assertIn('local:blastoff  [last loaded; modified]', self.invoke('list').stdout)
        (self.store/'themes/blastoff.toml').write_text('x=4\n')
        self.assertIn('[last loaded; modified; source changed]', self.invoke('list').stdout)
        self.config.write_text('x=1\n')
        self.assertIn('[last loaded; source changed]', self.invoke('list').stdout)
        # A save destination must not replace the last-loaded identity.
        self.config.write_text('x=3\n')
        self.invoke('theme','save','copy')
        output = self.invoke('list').stdout
        self.assertIn('local:blastoff  [last loaded; modified; source changed]', output)
        self.assertIn('  local:copy\n', output)

    def test_missing_source_active_and_unavailable_preset(self):
        self.loaded()
        (self.store/'themes/blastoff.toml').unlink()
        self.assertIn('Origin: local:blastoff  [last loaded; source unavailable; not listed]', self.invoke('list').stdout)
        self.config.unlink()
        self.assertIn('[last loaded; active configuration missing; not listed]', self.invoke('list').stdout)

    def test_preset_identity_not_same_named_local(self):
        self.loaded()
        record = self.record()
        doc = json.loads(record.read_bytes())
        doc['last_loaded'] = {'kind':'preset', 'name':'blastoff', 'sha256':doc['active_sha256']}
        record.write_text(json.dumps(doc))
        output, err = self.in_process(presets=['blastoff'])
        self.assertIn('  local:blastoff\n', output)
        self.assertIn('  preset:blastoff  [current]', output)
        self.assertEqual(err, '')
        self.assertIn('Origin: preset:blastoff  [current; not listed]', self.in_process()[0])
        self.config.write_text('x=4\n')
        self.assertIn('preset:blastoff  [last loaded; modified]', self.in_process(presets=['blastoff'])[0])

    def test_unknown_corrupt_pending_and_future_state(self):
        self.loaded()
        record = self.record()
        original = record.read_bytes()
        for data in (b'bad json', b'[]', original.replace(b'"version": 1', b'"version": 999')):
            record.write_bytes(data)
            before = self.tree()
            output = self.invoke('list').stdout
            self.assertIn('Current theme: unknown', output)
            self.assertNotIn('[current]', output)
            self.assertEqual(before, self.tree())
        record.write_bytes(original)
        record.with_suffix('.pending').write_text('{}')
        self.assertIn('incomplete operation', self.invoke('list').stdout)
        record.with_suffix('.pending').unlink()
        record.unlink()
        self.assertIn('Use blastoff current for local matches.', self.invoke('list').stdout)

    def test_empty_and_missing_active_do_not_create_state(self):
        before = self.tree()
        output = self.invoke('list').stdout
        self.assertIn('THEMES\n  (none)', output)
        self.assertIn('active configuration missing', output)
        self.assertEqual(before, self.tree())

    def test_json_keeps_schema_and_skips_identification(self):
        self.loaded()
        before = self.tree()
        provenance = core.ui_module('provenance')
        with patch.object(provenance, 'list_identity', side_effect=AssertionError('human inspection in JSON')):
            for flags in [('list','--json'), ('--json','theme','list','--color','always','-v')]:
                output, _ = self.in_process(flags)
                self.assertEqual(json.loads(output), {'themes':['aurora','blastoff'], 'presets':[],
                    'starship_available':False, 'preset_discovery':{'status':'ok','error':None}})
                self.assertNotIn('\x1b', output)
        self.assertEqual(before, self.tree())

    def test_content_reads_bounded_with_large_library(self):
        self.loaded()
        for n in range(100):
            self.theme('unused'+str(n), 'x=0\n')
        read = core.read
        paths = []
        def counted(p, *args, **kwargs):
            paths.append(p)
            return read(p, *args, **kwargs)
        with patch.object(core, 'read', side_effect=counted):
            self.assertIn('[current]', self.in_process()[0])
        self.assertEqual(paths.count(self.config), 1)
        self.assertEqual(paths.count(self.record()), 1)
        self.assertEqual([p for p in paths if p.parent == self.store/'themes'], [self.store/'themes/blastoff.toml'])

    def test_concurrent_changes_suppress_current(self):
        self.loaded()
        read = core.read
        record = self.record()
        for target in (self.config, self.store/'themes/blastoff.toml', record, record.with_suffix('.pending')):
            with self.subTest(target=target):
                self.invoke('theme','apply','blastoff')
                def raced(p, *args, **kwargs):
                    result = read(p, *args, **kwargs)
                    if p == self.store/'themes/blastoff.toml':
                        if target == record:
                            target.write_bytes(target.read_bytes()+b' ')
                        else:
                            target.write_text('x=999\n')
                    return result
                with patch.object(core, 'read', side_effect=raced):
                    output, _ = self.in_process()
                self.assertIn('files changed during inspection', output)
                self.assertNotIn('[current]', output)
                record.with_suffix('.pending').unlink(missing_ok=True)

    def test_unreadable_config_preserves_choices_and_verbose_stderr(self):
        self.loaded()
        read = core.read
        def blocked(p, *args, **kwargs):
            if p == self.config:
                raise PermissionError('fixture permission denial')
            return read(p, *args, **kwargs)
        with patch.object(core, 'read', side_effect=blocked):
            output, err = self.in_process(('list','-v'))
        self.assertIn('  local:blastoff\n', output)
        self.assertIn('could not be read', output)
        self.assertNotIn('fixture permission', output)
        self.assertIn('fixture permission', err)

    def test_linked_active_and_unsafe_source(self):
        if os.name != 'posix':
            self.skipTest('POSIX symlink fixture')
        self.loaded()
        target = self.write(self.home/'config target with spaces.toml', self.config.read_text())
        self.config.unlink()
        self.config.symlink_to(target)
        before = self.tree()
        self.assertIn('[current]', self.invoke('list').stdout)
        self.assertEqual(before, self.tree())
        source = self.store/'themes/blastoff.toml'
        source.unlink()
        source.symlink_to(target)
        self.assertIn('source unavailable; not listed', self.invoke('list').stdout)
        target.unlink()
        self.assertIn('Current theme: unavailable', self.invoke('list').stdout)

    def test_native_bash_terminal(self):
        if os.name != 'posix' or not shutil.which('bash'):
            self.skipTest('native POSIX Bash terminal unavailable')
        from pty_support import terminal
        self.loaded()
        self.env.pop('NO_COLOR')
        self.env['TERM'] = 'xterm-256color'
        code, screen = terminal([shutil.which('bash'),str(ROOT/'bin/blastoff'),'list'], self.env, columns=40)
        self.assertEqual(code, 0)
        self.assertIn(b'[current]', screen)
        self.assertIn(b'\x1b[2mlocal:\x1b[0m', screen)

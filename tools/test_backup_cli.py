#!/usr/bin/env python3
"""Backup entry points, native data transport and effective profile preferences."""
import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

import test_profile_config as fixtures


class BackupCLI(unittest.TestCase):
    def setUp(self):
        fixtures.ProfileConfig.setUp(self)
        shutil.copytree(fixtures.ROOT / 'default', self.root / 'default')
        for path in [*fixtures.ROOT.glob('bin/dots-bak*'), fixtures.ROOT / 'bin/bak']:
            shutil.copy2(path, self.root / 'bin' / path.name)
        self.env['DOTS_PROGRESS'] = 'never'

    def run_bak(self, *args, code=0, native=False, direct=False, **env):
        if native:
            encoded = base64.b64encode(json.dumps(list(args)).encode()).decode()
            command = [sys.executable, '-B', str(self.root / 'lib/dots/native.py'), 'bak', encoded]
        elif direct:
            command = [str(self.root / 'bin/bak'), *args]
        else:
            command = [shutil.which('bash'), str(self.root / 'bin/dots'), 'bak', *args]
        result = subprocess.run(command, env=dict(self.env, **env), text=True, capture_output=True, timeout=30, cwd=self.home)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result

    def source(self, name='source', text='original'):
        source = self.home / name
        source.write_text(text)
        return source

    def test_data_literal_native_move_and_retained_restore(self):
        source = self.source('雪 space "quotes"')
        result = self.run_bak('create', str(source), '--json', native=True, DOTS_COLOR='always', DOTS_ICONS='always')
        data = json.loads(result.stdout)
        self.assertNotIn('\x1b', result.stdout)
        self.assertFalse(source.exists())
        record = data['items'][0]
        self.assertTrue(Path(record['path']).is_file())
        self.run_bak('restore', record['id'], '--json')
        self.assertEqual(source.read_text(), 'original')
        self.assertTrue(Path(record['path']).exists())

    def test_quiet_copy_and_command_name_operand(self):
        source = self.source('list')
        result = self.run_bak('--copy','-q','--','list')
        self.assertEqual(result.stdout, '')
        self.assertEqual(result.stderr, '')
        self.assertEqual(source.read_text(), 'original')
        rows = json.loads(self.run_bak('list','--json').stdout)['items']
        self.assertEqual(len(rows), 1)
        self.run_bak('--quiet', '--', 'absent', code=1)

    def test_preview_help_and_list_are_inert(self):
        source = self.source()
        self.run_bak(str(source),'--dry-run','--json')
        self.run_bak('--help')
        self.run_bak(direct=True)
        self.run_bak('list','--json')
        self.assertTrue(source.exists())
        self.assertFalse((self.home / '.bakstore').exists())
        self.assertFalse((self.home / 'state').exists())

    def test_delete_requires_explicit_noninteractive_approval(self):
        row = json.loads(self.run_bak(str(self.source()),'--json').stdout)['items'][0]
        self.run_bak('delete',row['id'],'--json',code=1)
        self.run_bak('delete',row['id'],'--dry-run','--json')
        self.assertTrue(Path(row['path']).exists())
        self.run_bak('delete',row['id'],'--yes','--json')
        self.assertFalse(Path(row['path']).exists())

    def test_profile_preferences_and_flag_overrides(self):
        profile = json.loads(self.path.read_text())
        profile['apps'] = {'bak': {'mode': 'copy', 'location': 'store', 'store': str(self.home / 'custom backups')}}
        self.path.write_text(json.dumps(profile))
        source = self.source()
        row = json.loads(self.run_bak(str(source),'--json').stdout)['items'][0]
        self.assertTrue(source.exists())
        self.assertIn('custom backups', row['path'])
        row = json.loads(self.run_bak('--move','--in-place',str(source),'--json').stdout)['items'][0]
        self.assertFalse(source.exists())
        self.assertEqual(Path(row['path']).parent, source.parent)

    def test_standalone_ignores_stale_checkout_and_empty_path_refused(self):
        source = self.source()
        result = self.run_bak(str(source),'--json',direct=True,DOTS=str(self.home / 'stale'))
        self.assertEqual(json.loads(result.stdout)['status'], 'complete')
        self.run_bak('create','','--json',code=1)

    def test_browser_cancel_and_declined_restore_are_inert(self):
        from unittest.mock import patch
        sys.path.insert(0,str(fixtures.ROOT/'lib/dots'))
        import bak_cli
        from menus import Entry
        from interaction import SelectionEnded
        record=json.loads(self.run_bak(str(self.source()),'--json').stdout)['items'][0]
        before={p: p.read_bytes() for p in self.home.rglob('*') if p.is_file() and not p.is_symlink()}
        with patch.dict(os.environ,self.env), patch('bak_cli.terminal',return_value=True):
            with patch('menus.choose',return_value=None): bak_cli.main(['browse'])
            with patch('menus.choose',side_effect=[Entry(record['id'],'Source'),Entry('restore','Restore')]), patch('bak_cli.gum_confirm',return_value=False):
                with self.assertRaises(SelectionEnded) as caught: bak_cli.main(['browse'])
                self.assertEqual(caught.exception.status,130)
        self.assertEqual(before,{p:p.read_bytes() for p in self.home.rglob('*') if p.is_file() and not p.is_symlink()})


if __name__ == '__main__': unittest.main()

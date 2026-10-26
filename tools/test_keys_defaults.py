#!/usr/bin/env python3
"""Bundled references and override semantics in test-owned configuration roots."""
import io
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_keys
from keys.model import readable
from keys.providers import collect
from keys.codex import config_path, display, normalize

POWERSHELL = test_keys.shutil.which('pwsh') or test_keys.shutil.which('powershell')


class Defaults(unittest.TestCase):
    setUp = test_keys.Keys.setUp
    cli = test_keys.Keys.cli

    def configure(self, app, text):
        directory = self.base / ('-config ü ' + app)
        directory.mkdir(exist_ok=True)
        name = 'keymap.toml' if app == 'yazi' else 'config.toml'
        variable = 'YAZI_CONFIG_HOME' if app == 'yazi' else 'CODEX_HOME'
        self.env[variable] = str(directory)
        os.environ[variable] = str(directory)
        path = directory / name
        path.write_text(text)
        return path

    def test_yazi_complete_pinned_snapshot_and_offline(self):
        self.assertEqual(hashlib.sha256((self.root/'lib/dots/keys/data/yazi-default.toml').read_bytes()).hexdigest(),
                         '6308baf2eafe16f1d3f7c641e95a3bafe3951ec328dd530121d4895adb2f6b46')
        with patch('keys.providers.run', side_effect=AssertionError('application execution')):
            data = collect(self.root, 'yazi')
        expected = dict(mgr=116, tasks=12, spot=15, pick=10, input=68, confirm=12, cmp=11, help=10)
        self.assertEqual({m: sum(r['mode']==m for r in data['rows']) for m in expected}, expected)
        self.assertEqual(len(data['rows']), 254)
        self.assertEqual(data['coverage'][0]['count'], 254)
        self.assertTrue(all(r['default'] and r['evidence']=='configured' for r in data['rows']))
        self.assertTrue(any(r['key']==['g','g'] and r['display']=='g → g' for r in data['rows']))
        self.assertEqual(readable('<'), '<')
        self.assertEqual(readable('>'), '>')

    def test_yazi_replacement_prepend_append_and_empty_tables(self):
        self.configure('yazi', '''
[mgr]
keymap = [{ on = 'q', run = 'custom-base' }]
prepend_keymap = [{ on = ['q'], run = 'custom-first' }]
append_keymap = [{ on = 'q', run = 'custom-last' }, { on = 'z', run = 'custom-extra' }]
[input]
keymap = []
''')
        rows = collect(self.root, 'yazi')['rows']
        self.assertTrue(all(r['status']=='shadowed' for r in rows if r['default'] and r['mode'] in ('mgr','input')))
        statuses = {r['action']:r['status'] for r in rows if not r['default']}
        self.assertEqual(statuses['custom-base'], 'shadowed')
        self.assertEqual(statuses['custom-last'], 'shadowed')
        self.assertNotEqual(statuses['custom-first'], 'shadowed')
        self.assertNotEqual(statuses['custom-extra'], 'shadowed')
        self.assertTrue(all(r['status']!='shadowed' for r in rows if r['mode']=='help'))
        filtered = collect(self.root, 'yazi', defaults=False)['rows']
        self.assertEqual(filtered, [r for r in rows if not r['default']])

    def test_yazi_customizations_preserve_other_default_contexts(self):
        self.configure('yazi', '''[mgr]
prepend_keymap = [{on='X',run='plugin dots -- toggle-pane max-preview'}, {on='<A-m>',run='plugin dots -- preview toggle'}]
''')
        data = collect(self.root, 'yazi')
        self.assertEqual(sum(r['default'] for r in data['rows']), 254)
        default_x = next(r for r in data['rows'] if r['mode']=='mgr' and r['key']=='X' and r['default'])
        self.assertEqual(default_x['status'], 'shadowed')
        self.assertTrue(any(r['key']=='<A-m>' and not r['default'] for r in data['rows']))

    def test_codex_inventory_contexts_and_fixed_shortcuts(self):
        catalog = json.loads((self.root/'lib/dots/keys/data/codex-defaults.json').read_text())
        self.assertEqual(catalog['version'], '0.164.0')
        self.assertEqual(len(catalog['actions']), 156)
        self.assertEqual(sum(len(a['keys']) for a in catalog['actions']), 234)
        self.assertEqual(len({(a['mode'],a['action']) for a in catalog['actions']}), 156)
        with patch('keys.providers.run', side_effect=AssertionError('application execution')):
            data = collect(self.root, 'codex')
        self.assertTrue(all(r['default'] and r['evidence']=='configured' for r in data['rows']))
        for mode, key in [('composer','enter'),('editor','ctrl-a'),('approval','y'),('agents','o'),('transcript','ctrl-space'),('transcript_selection','super-c'),
                          ('vim_normal','g g'),('chat','esc esc'),('chat','ctrl-v'),('terminal','ctrl-z')]:
            self.assertTrue(any(r['mode']==mode and r['key']==key for r in data['rows']), (mode,key))
        self.assertEqual(data['coverage'][0]['count'], len(data['rows']))
        self.assertFalse(data['coverage'][0]['live'])

    def test_codex_remaps_unbinding_alternatives_and_global_fallback(self):
        self.configure('codex', '''[tui.keymap.global]
submit = 'ctrl-x ctrl-s'
queue = []
[tui.keymap.editor]
move_left = ['ctrl-q', 'alt-left']
move_right = []
[tui.keymap.composer]
submit = 'alt-enter'
''')
        rows = collect(self.root, 'codex')['rows']
        submit = [r for r in rows if r['mode']=='composer' and r['action']=='submit']
        self.assertEqual({r['key']:r['status'] for r in submit}, {
            'enter':'shadowed', 'ctrl-x ctrl-s':'shadowed', 'alt-enter':'configured; activation unverified'})
        disabled = {(r['mode'],r['action']) for r in rows if r['status']=='disabled'}
        self.assertIn(('composer','queue'), disabled)
        self.assertIn(('editor','move_right'), disabled)
        self.assertTrue(all(r['display']=='Unbound' and r['key']==[] for r in rows if r['status']=='disabled'))
        left = [r for r in rows if r['mode']=='editor' and r['action']=='move_left']
        self.assertEqual(len([r for r in left if r['status']=='shadowed']), 2)
        self.assertEqual({r['key'] for r in left if not r['default']}, {'ctrl-q','alt-left'})
        self.assertTrue(all(r['status']!='shadowed' for r in rows if r['mode']=='vim_normal' and r['action']=='move_left'))

    def test_codex_chords_leader_and_raw_notation(self):
        self.configure('codex', '''[tui.keymap.global]
leader = ['ctrl-b', 'alt-x']
submit = 'Control-X Control-S'
[tui.keymap.composer]
queue = 'leader q'
''')
        rows = collect(self.root, 'codex')['rows']
        row = next(r for r in rows if r['key']=='Control-X Control-S')
        self.assertEqual(row['display'], 'Ctrl+X → Ctrl+S')
        self.assertEqual(row['mode'], 'composer')
        row = next(r for r in rows if r['key']=='leader q')
        self.assertEqual(row['display'], 'Ctrl+B / Alt+X → q')
        for raw, expected in [('page-down','PageDown'),('ctrl-minus','Ctrl+-'),('shift-enter','Shift+Enter'),('f3','F3')]:
            self.assertEqual(display(normalize(raw), []), expected)
        self.configure('codex', '[tui.keymap.global]\nleader=[]\n')
        rows = collect(self.root, 'codex')['rows']
        self.assertEqual(next(r for r in rows if r['key']=='leader p')['status'], 'shadowed')

    def test_codex_unknown_invalid_and_malformed_inputs_do_not_leak(self):
        sentinel = 'PRIVATE_SENTINEL_VALUE'
        path = self.configure('codex', '[provider]\ntoken="'+sentinel+'"\n[tui.keymap.composer]\nsubmit="'+sentinel+'"\nqueue=12\nunknown="'+sentinel+'"\n')
        data = collect(self.root, 'codex')
        self.assertNotIn(sentinel, json.dumps(data))
        self.assertTrue(any('Invalid Codex' in n for n in data['coverage'][0]['notes']))
        self.assertTrue(any('Unsupported Codex' in n for n in data['coverage'][0]['notes']))
        for text in ('broken = [', 'x="'+'x'*(2*1024*1024)+'"'):
            path.write_text(text)
            data = collect(self.root, 'codex')
            self.assertGreater(len(data['rows']), 234)
            self.assertTrue(any('could not be read' in n for n in data['coverage'][0]['notes']))
        for text in ('[mgr]\nkeymap=12', '[mgr]\nkeymap=[12]', 'broken = ['):
            self.configure('yazi', text)
            self.assertEqual(len(collect(self.root,'yazi')['rows']), 254)

    def test_codex_native_home_and_explicit_missing_directory(self):
        with patch('keys.codex.Path.home', return_value=self.home/'Windows user'):
            self.assertEqual(config_path(), self.home/'Windows user/.codex/config.toml')
        with patch.dict(os.environ, {'CODEX_HOME':str(self.base/'absent ü')}):
            self.assertEqual(config_path(), self.base/'absent ü/config.toml')
            self.assertGreater(len(collect(self.root,'codex')['rows']), 234)

    def test_output_filters_and_both_controller_surfaces(self):
        self.env.update(DOTS_COLOR='always',DOTS_ICONS='always')
        for app in ('yazi','codex'):
            text = self.cli(app,'--json').stdout
            self.assertNotIn('\x1b',text)
            self.assertTrue(json.loads(text)['rows'])
            self.assertEqual(json.loads(self.cli(app,'--json','--source','live').stdout)['rows'],[])
            self.assertEqual(json.loads(self.cli(app,'--json','--no-defaults').stdout)['rows'],[])
            for native in (False,True):
                prefix=[sys.executable,'-B',str(self.root/'lib/dots/cli.py')] if native else [str(self.root/'bin/dots')]
                result=subprocess.run([*prefix,'keys',app,'--json'],env=self.env,capture_output=True,text=True,timeout=20)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(json.loads(result.stdout),json.loads(text))
            for width in (40,80,120):
                self.env.update(COLUMNS=str(width),DOTS_COLOR='never',DOTS_ICONS='never')
                output=self.cli(app,'--print','--query','help' if app=='yazi' else 'editor move').stdout
                self.assertNotIn('\x1b',output)
                self.assertIn('Result',output)
        filtered=json.loads(self.cli('codex','--json','--mode','approval','--query','session').stdout)['rows']
        self.assertTrue(filtered)
        self.assertTrue(all(r['mode']=='approval' for r in filtered))

    def test_codex_route_skips_shell_capture(self):
        for shell in ('bash','zsh'):
            executable=test_keys.shutil.which(shell)
            if not executable:continue
            code='source "$DOTS/lib/dots/shell/keys.bash"\n_dots_keys_snapshot() { printf capture-ran >&2; return 1; }\ndots keys codex --json\n'
            flags=['-dfc'] if shell=='zsh' else ['--noprofile','--norc','-c']
            result=subprocess.run([executable,*flags,code],env=self.env,capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertNotIn('capture-ran',result.stderr)
            self.assertTrue(json.loads(result.stdout)['rows'])

    @unittest.skipUnless(POWERSHELL, 'native PowerShell engine unavailable')
    def test_powershell_codex_route_skips_psreadline_capture(self):
        script=self.base/'keys smoke.ps1'
        script.write_text('''$ErrorActionPreference = 'Stop'
function Get-PSReadLineKeyHandler { throw 'Unrelated PSReadLine capture' }
. (Join-Path $env:DOTS 'lib/dots/shell/keys.ps1')
dots keys codex --json
exit $LASTEXITCODE
''')
        result=subprocess.run([POWERSHELL,'-NoProfile','-NonInteractive','-File',str(script)],
                              env=self.env,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue(json.loads(result.stdout)['rows'])


if __name__ == '__main__':unittest.main()

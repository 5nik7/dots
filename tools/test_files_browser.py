#!/usr/bin/env python3
"""Browser state/transaction tests and terminal UI checks in owned roots."""
import argparse
from contextlib import redirect_stdout
import importlib.util
import io
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib/dots/files'))
import browser
from transactions import Store, digest

spec = importlib.util.spec_from_file_location('operations', ROOT / 'tools/test_file_operations.py')
operations = importlib.util.module_from_spec(spec)
spec.loader.exec_module(operations)
spec = importlib.util.spec_from_file_location('picker', ROOT / 'tools/test_theme_picker.py')
picker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(picker)


class Scripted:
    def __init__(self, choices):
        self.queue = list(choices)
        self.menus = []

    def pick(self, kind, header, choices, initial=''):
        self.menus.append((kind, header, choices, initial))
        if not self.queue:
            raise AssertionError(('unexpected menu', header, choices))
        choice = self.queue.pop(0)
        if callable(choice):
            return choice(kind, header, choices, initial)
        if choice.startswith('RESOURCE:'):
            return next(x for x in choices if x.startswith(choice[9:] + ' |'))
        return choice


class Browser(operations.Operations):
    def setUp(self):
        super().setUp()
        self.env = {k: v for k, v in self.env.items() if k in (
            'HOME', 'DOTS', 'XDG_CONFIG_HOME', 'XDG_STATE_HOME', 'DOTS_COLOR', 'DOTS_ICONS', 'LD_PRELOAD')}
        self.env.update(PATH=os.environ['PATH'], TERM='xterm-256color', TMPDIR=str(self.base),
                        XDG_CACHE_HOME=str(self.home/'cache'), XDG_DATA_HOME=str(self.home/'data'))
        self.addCleanup(patch.stopall)
        patch.dict(os.environ, self.env, clear=True).start()
        self.source = self.repo / 'config/example/settings ü'
        self.source.parent.mkdir(parents=True)
        self.source.write_text('repository content\n')
        self.rows = [{'id': 'app', 'source': 'config/example/settings ü', 'app': 'example',
                      'category': 'config', 'platforms': ['termux', 'linux', 'wsl'],
                      'target': '${CONFIG}/example/settings ü', 'strategy': 'link'}]
        self.catalog_write()
        self.state = self.home / '.state'
        self.args = argparse.Namespace(repo=None, app=None, category=None, status=None)

    def catalog_write(self):
        self.write('.dots/files.json', {'schema': 1, 'repository': 'dots', 'resources': self.rows})

    def run_browser(self, choices):
        scripted = Scripted(choices)
        output = io.StringIO()
        with redirect_stdout(output):
            try:
                browser.Browser(self.args, scripted).run()
            except browser.EndBrowser as end:
                self.assertEqual(end.status, 0)
        self.assertFalse(scripted.queue, scripted.queue)
        return output.getvalue(), scripted.menus

    def test_read_only_details_back_toggle_exit(self):
        before = digest(self.repo)
        out, menus = self.run_browser(['RESOURCE:dots:app', 'Retained backups: off',
                                       'Back to list', 'RESOURCE:dots:app', 'Exit'])
        self.assertIn(re.sub(r'\s+', '', str(self.source).replace(str(self.home), '~')), re.sub(r'\s+', '', out))
        self.assertIn('existing file', out)
        self.assertTrue(any('Retained backups: on' in m[2] for m in menus))
        self.assertEqual(digest(self.repo), before)
        self.assertEqual(self.path.read_text(), 'original\n')
        self.assertFalse(self.state.exists())
        self.assertFalse((self.home/'.config/dots/files.json').exists())

    def test_filters_empty_sources_and_refresh(self):
        self.args.status = 'missing'
        out, _ = self.run_browser([])
        self.assertIn('No matching', out)
        self.path.unlink()
        self.run_browser(['RESOURCE:dots:app', 'Link', 'Apply', 'Return to list'])
        self.assertTrue(self.path.is_symlink())
        self.assertEqual(len(Store(self.state/'dots').records()), 1)
        self.assertEqual(self.source.read_text(), 'repository content\n')

    def test_catalog_filter_fields(self):
        for field, matching in (('repo', 'dots'), ('app', 'example'), ('category', 'config')):
            setattr(self.args, field, 'absent')
            out, _ = self.run_browser([])
            self.assertIn('No matching', out)
            setattr(self.args, field, matching)
            self.run_browser(['RESOURCE:dots:app', 'Exit'])
            setattr(self.args, field, None)
        self.assertFalse(self.state.exists())

    def test_existing_target_blocked_then_backup_apply(self):
        out, menus = self.run_browser(['RESOURCE:dots:app', 'Link', 'Back',
                                       'Retained backups: off', 'Link', 'Apply', 'Exit'])
        blocked = next(m for m in menus if m[1] == 'Operation blocked')
        self.assertNotIn('Apply', blocked[2])
        self.assertIn('requires --backup', out)
        self.assertTrue(self.path.is_symlink())
        self.assertEqual(len(list((self.state/'dots/backups').glob('*.json'))), 1)
        self.assertEqual(len(Store(self.state/'dots').records()), 1)
        self.assertFalse((self.home/'.config/dots/files.json').exists())

    def test_backup_preference_and_preview_back(self):
        config = self.home/'.config/dots/files.json'
        config.parent.mkdir()
        config.write_text('{"schema":1,"backup":true}')
        out, menus = self.run_browser(['RESOURCE:dots:app', 'Link', 'Back', 'Exit'])
        self.assertIn('Retained backups: on', menus[1][2])
        self.assertIn('enabled', out)
        self.assertFalse(self.state.exists())
        self.assertEqual(config.read_text(), '{"schema":1,"backup":true}')

    def test_link_noop_and_stop_managing(self):
        self.path.unlink(); self.path.symlink_to(self.source)
        out, _ = self.run_browser(['RESOURCE:dots:app', 'Link', 'Apply', 'Exit'])
        self.assertIn('unchanged', out)
        self.assertFalse(self.state.exists())
        out, _ = self.run_browser(['RESOURCE:dots:app', 'Stop managing', 'Apply', 'Return to list'])
        self.assertIn('No matching', out)
        self.assertFalse(self.path.is_symlink())
        self.assertEqual(self.path.read_text(), self.source.read_text())
        self.assertEqual(self.records(), [])
        self.assertTrue(self.source.exists())

    def test_invalid_result_and_cancel_before_apply(self):
        for choices in (['nonsense'], ['RESOURCE:dots:app', 'nonsense'],
                        ['RESOURCE:dots:app', 'Retained backups: off', 'Link', 'nonsense']):
            with self.subTest(choices=choices), self.assertRaisesRegex(ValueError, 'unknown choice'):
                self.run_browser(choices)
        self.run_browser(['RESOURCE:dots:app', 'Retained backups: off', 'Link', 'Exit'])
        self.assertFalse(self.state.exists())
        self.assertFalse(self.path.is_symlink())

    def test_drift_binds_source_target_and_catalogs(self):
        for kind in ('source', 'target', 'catalog', 'composition'):
            with self.subTest(kind=kind):
                self.source.write_text('repository content\n')
                self.path.write_text('original\n')
                self.catalog_write()
                composition = self.repo/'.dots/sources.json'
                original = composition.read_text()
                def drift(*_):
                    if kind == 'source': self.source.write_text('changed source')
                    elif kind == 'target': self.path.write_text('changed target')
                    elif kind == 'catalog':
                        p=self.repo/'.dots/files.json'; p.write_text(p.read_text()+'\n')
                    else: composition.write_text(original+'\n')
                    return 'Apply'
                with self.assertRaisesRegex(ValueError, 'changed after preview'):
                    self.run_browser(['RESOURCE:dots:app', 'Retained backups: off', 'Link', drift])
                composition.write_text(original)
                self.assertFalse(self.path.is_symlink())
                self.assertFalse(self.state.exists())

    def test_refusals_and_safe_display(self):
        for kind in ('unrelated-link', 'source-missing', 'copy', 'unmapped', 'conflict'):
            with self.subTest(kind=kind):
                self.path.unlink(missing_ok=True)
                self.source.write_text('repository content\n')
                self.rows[0]['strategy']='link'; self.rows[0]['target']='${CONFIG}/example/settings ü'
                if kind=='unrelated-link': self.path.symlink_to(self.home/'absent')
                if kind=='source-missing': self.source.unlink()
                if kind=='copy': self.rows[0]['strategy']='copy'
                if kind=='unmapped': self.rows[0]['target']=None
                if kind=='conflict': self.rows.append(dict(self.rows[0], id='other'))
                self.catalog_write()
                _, menus = self.run_browser(['RESOURCE:dots:app', 'Link', 'Back', 'Exit'])
                self.assertTrue(any(m[1]=='Operation blocked' for m in menus))
                self.assertFalse(self.state.exists())
                self.rows=self.rows[:1]
        weird = self.base / 'repo\n\x1b[31m'
        self.repo.rename(weird); self.repo = weird
        os.environ['DOTS'] = str(weird)
        self.rows[0]['source']='config/example/-odd ü'
        self.rows[0]['target']=None
        odd=self.repo/self.rows[0]['source']; odd.write_text('private contents not for display')
        self.catalog_write()
        out, menus=self.run_browser(['RESOURCE:dots:app','Exit'])
        self.assertNotIn('private contents',out)
        self.assertNotIn('\x1b',out)
        self.assertIn('\\n',menus[0][2][0])
        self.assertIn('\\x1b',menus[0][2][0])

    def test_apply_failure_stops_browsing_and_preserves_data(self):
        with patch.object(Store, 'apply', side_effect=ValueError('fixture failure')):
            with self.assertRaisesRegex(ValueError, 'fixture failure'):
                self.run_browser(['RESOURCE:dots:app', 'Retained backups: off', 'Link', 'Apply'])
        self.assertEqual(self.path.read_text(),'original\n')
        self.assertFalse(self.state.exists())

    def test_directory_removal_restrictions(self):
        directory = self.repo / 'config/folder'
        directory.mkdir()
        (directory/'nested-link').symlink_to(self.source)
        self.rows[0].update(source='config/folder', strategy='directory-link')
        self.catalog_write()
        self.path.unlink(); self.path.symlink_to(directory)
        out, _ = self.run_browser(['RESOURCE:dots:app', 'Stop managing', 'Back', 'Exit'])
        self.assertIn('materialize it manually', out)
        self.assertTrue(self.path.is_symlink())
        self.assertTrue(self.records())
        self.assertFalse(self.state.exists())

    def test_distinct_repository_ids_and_unavailable_sources(self):
        self.write('.dots/sources.json', {'schema':1,'sources':[
            {'id':'dots','path':'.','roots':['config'],'platforms':['termux','linux','wsl']},
            {'id':'child','path':'child','roots':['config'],'platforms':['termux','linux','wsl']},
            {'id':'missing','path':'missing','roots':['config'],'platforms':['termux','linux','wsl']}]})
        (self.repo/'child/.dots').mkdir(parents=True)
        (self.repo/'child/config').mkdir()
        (self.repo/'child/config/settings').write_text('child')
        self.write('child/.dots/files.json',{'schema':1,'repository':'child','resources':[
            dict(self.rows[0], source='config/settings',target='${CONFIG}/child')]})
        out,menus=self.run_browser(['RESOURCE:child:app','Exit'])
        self.assertIn('missing: unavailable',out)
        self.assertEqual(len(menus[0][2]),3)
        self.assertTrue(any(x.startswith('dots:app |') for x in menus[0][2]))
        self.assertTrue(any(x.startswith('child:app |') for x in menus[0][2]))


class Terminal(picker.Picker):
    def setUp(self):
        super().setUp()
        shutil.copytree(ROOT/'lib/dots', self.repo/'lib/dots', dirs_exist_ok=True)
        for path in ROOT.glob('bin/dots-files*'):
            shutil.copy2(path,self.repo/'bin'/path.name)
        (self.repo/'.dots').mkdir(exist_ok=True)
        (self.repo/'.dots/sources.json').write_text(json.dumps({'schema':1,'sources':[
            {'id':'dots','path':'.','roots':['config'],'platforms':['termux','linux','wsl']}]}))
        (self.repo/'config').mkdir()
        (self.repo/'config/settings ü').write_text('do not print file contents')
        (self.repo/'.dots/files.json').write_text(json.dumps({'schema':1,'repository':'dots','resources':[
            {'id':'app','source':'config/settings ü','app':'example','category':'config',
             'target':'${CONFIG}/example','strategy':'link','platforms':['termux','linux','wsl']}]}))
        self.script='"$DOTS/bin/dots" files browse'
        # An isolated PATH makes backend selection independent of installed tools.
        self.tools=self.root/'minimal tools'; self.tools.mkdir()
        for name in ('bash','python3','tail','mv'):
            (self.tools/name).symlink_to(shutil.which(name))
        self.env['PATH']=str(self.fake)+':'+str(self.tools)
        self.state=self.home/'state/dots'

    def test_plain_details_exit_and_input_refusal(self):
        out=self.terminal(steps=((b'Number (',b'1\r'),(b'Number [1]',b'5\r')))
        self.assertIn(b'File details',out)
        self.assertNotIn(b'do not print file contents',out)
        self.assertFalse(self.state.exists())
        self.terminal(steps=((b'Number (',b'\x04'),),code=130)
        result=self.dots('files','browse',code=1)
        self.assertEqual(result.stdout,'')
        self.assertIn('terminal input and output',result.stderr)
        self.terminal('"$DOTS/bin/dots" files browse > "$HOME/out"',code=1)
        self.terminal('"$DOTS/bin/dots" files browse < /dev/null',code=1)
        self.assertFalse(self.state.exists())

    def test_fake_tools_failure_and_metadata(self):
        self.fixture_ui();self.fixture_ui('fzf');self.queue(('EXIT:7',))
        self.terminal(code=1)
        self.assertEqual(len(self.calls.read_text().splitlines()),1)
        self.calls.unlink()
        self.dots('files','browse','--help')
        self.dots('commands','--check')
        self.dots('files','list','--json')
        self.dots('files','show','dots:app','--json')
        self.assertFalse(self.calls.exists())
        completion=self.dots('__complete','bash','2','--','dots','files','').stdout
        self.assertIn('browse',completion)
        self.assertIn('--repo',self.dots('__complete','bash','3','--','dots','files','browse','--').stdout)

    @unittest.skipUnless(picker.NATIVE_GUM,'native Gum unavailable')
    def test_native_gum_details_and_exit(self):
        (self.fake/'gum').symlink_to(picker.NATIVE_GUM)
        for width in (40,80,120):
            out=self.terminal(steps=((b'Type to filter',b'\r'),(b'Config action',b'jjjj\r')),width=width)
            self.assertIn(b'File details',out)
            self.assertNotIn(b'do not print file contents',out)
        self.assertFalse(self.state.exists())

    @unittest.skipUnless(picker.NATIVE_GUM,'native Gum unavailable')
    def test_native_gum_link_apply(self):
        (self.fake/'gum').symlink_to(picker.NATIVE_GUM)
        out=self.terminal(steps=((b'Type to filter',b'\r'),(b'Config action',b'j\r'),
                                 (b'Review operation',b'j\r'),(b'Operation finished',b'j\r')))
        self.assertIn(b'File operation complete',out)
        self.assertTrue((self.home/'config/example').is_symlink())
        self.assertEqual(len(list((self.state/'files/transactions').glob('*/journal.json'))),1)

    @unittest.skipUnless(picker.NATIVE_FZF,'native FZF unavailable')
    def test_native_fzf_details_and_exit(self):
        (self.fake/'fzf').symlink_to(picker.NATIVE_FZF)
        out=self.terminal(steps=((b'Filter:',b'\r'),(b'Number [1]',b'5\r')))
        self.assertIn(b'File details',out)
        self.assertFalse(self.state.exists())


for cls,parent in ((Browser,operations.Operations),(Terminal,picker.Picker)):
    for name in dir(parent):
        if name.startswith('test_') and name not in cls.__dict__:
            setattr(cls,name,None)

del cls, parent, name

if __name__=='__main__':
    unittest.main()

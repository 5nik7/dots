#!/usr/bin/env python3
"""Isolated adoption, backup, rollback and output regression tests."""
import json
import io
from contextlib import redirect_stdout
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import pty
import re
import unittest
from unittest import mock

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / 'lib/dots/files'))
from transactions import Store, digest


class Operations(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='dots files ü ')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.home = self.base / 'home'
        self.repo = self.base / 'repo'
        self.home.mkdir()
        (self.repo / '.dots').mkdir(parents=True)
        (self.repo / 'config').mkdir()
        self.env = dict(os.environ, HOME=str(self.home), DOTS=str(self.repo),
                        XDG_CONFIG_HOME=str(self.home / '.config'), XDG_STATE_HOME=str(self.home / '.state'),
                        DOTS_COLOR='never', DOTS_ICONS='never', PYTHONDONTWRITEBYTECODE='1')
        self.write('.dots/sources.json', {'schema':1,'sources':[{'id':'dots','path':'.','roots':['config'],'platforms':['termux','linux','wsl']}]})
        self.write('.dots/files.json', {'schema':1,'repository':'dots','resources':[]})
        self.write('.dots/file-locations.json', {'schema':1,'repository':'dots','locations':[{'id':'config','kind':'root','target':'${CONFIG}','source':'config','platforms':['termux','linux','wsl']}]})
        self.path = self.home / '.config/example/settings ü'
        self.path.parent.mkdir(parents=True)
        self.path.write_text('original\n')

    def write(self, path, data):
        (self.repo / path).write_text(json.dumps(data))

    def run_cli(self, *args, ok=True, **env):
        result = subprocess.run([sys.executable,'-B',str(PROJECT/'lib/dots/files/manage.py'),*map(str,args)],
            env=dict(self.env, **env),capture_output=True,text=True)
        if ok:
            self.assertEqual(result.returncode,0,result.stderr)
        else:
            self.assertNotEqual(result.returncode,0)
        return result

    def records(self):
        return json.loads((self.repo/'.dots/files.json').read_text())['resources']

    def test_discovery_dry_run_and_adopt_remove(self):
        out=json.loads(self.run_cli('system','--json').stdout)
        self.assertEqual(out['items'][0]['status'],'candidate')
        self.run_cli('add',self.path,'--dry-run')
        self.assertFalse((self.home/'.state').exists())
        self.assertEqual(self.records(),[])
        result=json.loads(self.run_cli('add',self.path,'--yes','--json',DOTS_COLOR='always').stdout)
        self.assertEqual(result['status'],'complete')
        self.assertTrue(self.path.is_symlink())
        source=self.repo/self.records()[0]['source']
        self.assertEqual(source.read_text(),'original\n')
        identity='dots:'+self.records()[0]['id']
        self.run_cli('remove',identity,'--yes')
        self.assertFalse(self.path.is_symlink())
        self.assertEqual(self.path.read_text(),'original\n')
        self.assertTrue(source.exists())
        self.assertEqual(self.records(),[])

    def test_backup_restore_and_undo(self):
        result=json.loads(self.run_cli('add',self.path,'--backup','--yes','--json').stdout)
        self.assertEqual(len(json.loads(self.run_cli('backups-list','--json').stdout)['items']),1)
        self.run_cli('undo',result['id'],'--yes')
        self.assertEqual(self.path.read_text(),'original\n')
        self.assertFalse(self.path.is_symlink())
        self.assertEqual(self.records(),[])

    def test_undo_refuses_source_drift(self):
        result=json.loads(self.run_cli('add',self.path,'--yes','--json').stdout)
        self.path.write_text('user edits')
        self.run_cli('undo',result['id'],'--yes',ok=False)
        self.assertEqual(self.path.read_text(),'user edits')

    def test_link_requires_backup_and_restore(self):
        source=self.repo/'config/owned';source.write_text('repository')
        self.write('.dots/files.json',{'schema':1,'repository':'dots','resources':[{'id':'owned','source':'config/owned','target':'${CONFIG}/example/settings ü','strategy':'link','app':'example','category':'config','platforms':['termux','linux','wsl']}]})
        self.run_cli('link','dots:owned','--yes',ok=False)
        result=json.loads(self.run_cli('link','dots:owned','--backup','--yes','--json').stdout)
        self.assertEqual(self.path.read_text(),'repository')
        self.run_cli('backups-restore',result['id'],'--yes')
        self.assertEqual(self.path.read_text(),'original\n')
        self.assertFalse(self.path.is_symlink())

    def test_conflict_secret_and_unrelated_symlink(self):
        dest=self.repo/'config/example/settings ü';dest.parent.mkdir();dest.write_text('other')
        self.run_cli('add',self.path,'--yes',ok=False)
        dest.unlink()
        self.path.write_text('api_key = abcdefg')
        self.run_cli('add',self.path,'--yes',ok=False)
        self.path.unlink();self.path.symlink_to(dest)
        self.run_cli('add',self.path,'--yes',ok=False)
        self.assertFalse((self.home/'.state').exists())

    def test_directory_files_and_explicit_directory(self):
        (self.path.parent/'second').write_text('two')
        self.run_cli('add',self.path.parent,'--yes')
        self.assertFalse(self.path.parent.is_symlink())
        self.assertTrue(self.path.is_symlink())
        self.assertEqual(len(self.records()),2)

    def test_rollback_after_first_replacement(self):
        store=Store(self.home/'.state/dots')
        second=self.home/'second';second.write_text('old second')
        original_save=store.save
        def failing(doc):
            original_save(doc)
            if doc['status']=='applying' and doc['operations'][0]['phase']=='done':
                raise OSError('injected failure')
        with mock.patch.object(store,'save',side_effect=failing):
            with self.assertRaises(OSError):
                store.apply('test',[{'path':str(self.path),'link':'elsewhere'},{'path':str(second),'link':'another'}],{str(self.path):digest(self.path),str(second):digest(second)})
        self.assertEqual(self.path.read_text(),'original\n')
        self.assertEqual(second.read_text(),'old second')
        self.assertEqual(store.records()[0]['status'],'rolled-back')

    def test_noop_and_confirmation(self):
        self.run_cli('add',self.path,ok=False)
        self.assertFalse((self.home/'.state').exists())
        self.run_cli('add',self.path,'--yes')
        count=len(list((self.home/'.state/dots/files/transactions').iterdir()))
        self.run_cli('add',self.path,'--yes')
        self.assertEqual(len(list((self.home/'.state/dots/files/transactions').iterdir())),count)

    def test_retention_preference_and_override(self):
        prefs=self.home/'.config/dots/files.json';prefs.parent.mkdir()
        prefs.write_text(json.dumps({'schema':1,'backup':True}))
        result=json.loads(self.run_cli('add',self.path,'--no-backup','--yes','--json').stdout)
        directory=self.home/'.state/dots/files/transactions'/result['id']
        self.assertFalse(list(directory.glob('*-before')))
        self.assertFalse(list(directory.glob('*-after')))
        self.assertFalse((self.home/'.state/dots/backups').exists())
        self.run_cli('undo',result['id'],'--yes')
        result=json.loads(self.run_cli('add',self.path,'--yes','--json').stdout)
        self.assertTrue((self.home/'.state/dots/backups'/(result['id']+'.json')).exists())

    def test_reuse_source_and_directory_link_undo(self):
        source=self.repo/'config/example/settings ü';source.parent.mkdir()
        source.write_bytes(self.path.read_bytes())
        result=json.loads(self.run_cli('add',self.path,'--yes','--json').stdout)
        self.run_cli('undo',result['id'],'--yes')
        self.assertTrue(source.exists())
        self.assertFalse(self.path.is_symlink())
        import shutil
        shutil.rmtree(source.parent)
        result=json.loads(self.run_cli('add',self.path.parent,'--directory-link','--yes','--json').stdout)
        self.assertTrue(self.path.parent.is_symlink())
        self.run_cli('undo',result['id'],'--yes')
        self.assertFalse(self.path.parent.is_symlink())
        self.assertEqual(self.path.read_text(),'original\n')

    def test_abrupt_interruption_and_recovery(self):
        # Stop after a real first rename, leaving only the durable journal.
        code = """
import os, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import transactions as t
store=t.Store(Path(sys.argv[2]))
p=Path(sys.argv[3])
original=t.os.rename
def crash(a,b):
    original(a,b)
    os._exit(77)
t.os.rename=crash
store.apply('test',[{'path':str(p),'link':'destination'}],{str(p):t.digest(p)})
"""
        proc=subprocess.run([sys.executable,'-B','-c',code,str(PROJECT/'lib/dots/files'),str(self.home/'.state/dots'),str(self.path)],env=self.env)
        self.assertEqual(proc.returncode,77)
        store=Store(self.home/'.state/dots')
        doc=store.records()[0]
        self.assertEqual(doc['status'],'applying')
        self.run_cli('recover',doc['id'],'--dry-run')
        self.assertFalse(self.path.exists())
        self.run_cli('recover',doc['id'],'--yes')
        self.assertEqual(self.path.read_text(),'original\n')
        self.assertEqual(store.load(doc['id'])['status'],'rolled-back')

    def test_changed_preview_and_failed_copy(self):
        store=Store(self.home/'.state/dots')
        before=digest(self.path)
        self.path.write_text('changed')
        with self.assertRaises(ValueError):
            store.apply('test',[{'path':str(self.path),'link':'target'}],{str(self.path):before})
        self.assertEqual(self.path.read_text(),'changed')
        import transactions
        with mock.patch.object(transactions,'copy_object',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                store.apply('test',[{'path':str(self.path),'link':'target'}],{str(self.path):digest(self.path)})
        self.assertEqual(self.path.read_text(),'changed')
        self.assertEqual(store.records()[0]['status'],'rolled-back')

    def test_scan_excludes_secrets_and_handles_spaces(self):
        blocked=self.path.parent/'credentials.json';blocked.write_text('private')
        rows=json.loads(self.run_cli('system','--json').stdout)['items']
        self.assertEqual(next(x for x in rows if x['path']==str(blocked))['status'],'excluded')
        self.run_cli('add','--scan','--yes')
        self.assertTrue(self.path.is_symlink())
        self.assertFalse(blocked.is_symlink())
        self.assertEqual(blocked.read_text(),'private')

    def test_terminal_views_and_plain_data(self):
        for width in (40,80,120):
            out=self.run_cli('add',self.path,'--dry-run',DOTS_COLOR='always',COLUMNS=str(width)).stdout
            self.assertIn('\x1b[',out)
            self.assertIn('Preview only',out)
        master,slave=pty.openpty()
        try:
            env=dict(self.env,DOTS_COLOR='auto',TERM='xterm-256color',NO_COLOR='1')
            proc=subprocess.Popen([sys.executable,'-B',str(PROJECT/'lib/dots/files/manage.py'),'add',str(self.path),'--dry-run'],env=env,stdout=slave,stderr=subprocess.PIPE)
            proc.communicate(timeout=10)
            data=os.read(master,65536)
            self.assertNotIn(b'\x1b[',data)
        finally:
            os.close(master);os.close(slave)
        data=json.loads(self.run_cli('add',self.path,'--dry-run','--json',DOTS_COLOR='always').stdout)
        self.assertEqual(data['items'][0]['path'],str(self.path))

    def test_system_compact_verbose_all_and_json(self):
        for n in range(80):
            (self.path.parent / f'config-{n}').write_text('setting=true')
        blocked = self.home / '.config/credentials.json'
        blocked.write_text('fixture')
        owned = self.repo / 'config/owned'
        owned.write_text('fixture')
        self.write('.dots/files.json', {'schema':1,'repository':'dots','resources':[
            {'id':'owned','source':'config/owned','target':'${CONFIG}/owned','strategy':'link',
             'app':'example','category':'config','platforms':['termux','linux','wsl']}]})
        (self.home / '.config/owned').symlink_to(owned)
        before = digest(self.home), digest(self.repo)
        compact = self.run_cli('system').stdout
        self.assertLess(len(compact.splitlines()), 10)
        self.assertIn('81', compact)
        self.assertIn('~/.config/example', compact)
        self.assertNotIn('config-0', compact)
        self.assertNotIn('credentials.json', compact)
        self.assertNotIn('~/.config/owned', compact)
        self.assertNotIn('Source', compact)
        verbose = self.run_cli('system', '--verbose').stdout
        self.assertIn('config-0', verbose)
        self.assertIn('Source', verbose)
        self.assertNotIn('Target', verbose)
        all_rows = self.run_cli('system', '--all').stdout
        self.assertIn('credentials.json', all_rows)
        self.assertIn('[+] managed', all_rows)
        self.assertNotIn('[!] candidate', all_rows)
        raw = self.run_cli('system', '--json').stdout
        self.assertEqual(raw, self.run_cli('system', '--json', '--all', '--verbose',
                                         DOTS_COLOR='always', DOTS_ICONS='always').stdout)
        self.assertEqual(len(json.loads(raw)['items']), 83)
        self.assertEqual(before, (digest(self.home), digest(self.repo)))
        self.run_cli('locations', '--verbose', ok=False)

    def test_system_prunes_generated_trees_but_keeps_configs(self):
        config = self.home / '.config'
        excluded = ['Code - OSS/CachedData/hash/chrome/js/index',
                    'Code - OSS/CachedExtensionVSIXs/extension',
                    'Code - OSS/Code Cache/js/index', 'Code - OSS/GPUCache/data_0',
                    'Code - OSS/User/workspaceStorage/id/state.vscdb',
                    'Code - OSS/User/globalStorage/storage.json',
                    'Code - OSS/Local Storage/leveldb/CURRENT',
                    'Code - OSS/Session Storage/LOCK', 'Code - OSS/Cookies',
                    'XfceThemeManager/frames/preview.png',
                    'yarn/global/node_modules/module/index.js', 'zellij/config.kdl.bak',
                    'pulse/cookie', 'ipinfo/cache.boltdb']
        kept = ['Code - OSS/User/settings.json', 'Code - OSS/User/keybindings.json',
                'Code - OSS/User/snippets/example.json', 'themes/intentional.png',
                'XfceThemeManager/custom/personal.png', 'zellij/config.kdl']
        for name in excluded + kept:
            path = config / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('fixture')
        rows = json.loads(self.run_cli('system', '--json').stdout)['items']
        candidates = {x['path'] for x in rows if x['status'] == 'candidate'}
        self.assertTrue(all(str(config / n) not in candidates for n in excluded))
        self.assertTrue(all(str(config / n) in candidates for n in kept))
        self.assertNotIn(str(config / excluded[0]), {x['path'] for x in rows})
        self.run_cli('add', config / excluded[0], '--dry-run', ok=False)
        preview = json.loads(self.run_cli('add', '--scan', '--dry-run', '--json').stdout)
        self.assertTrue(all(x['path'] in candidates for x in preview['items']))
        self.assertEqual(len(preview['items']), len(candidates))
        self.assertFalse((self.home / '.state').exists())

    def test_system_layout_colors_controls_and_empty(self):
        weird = self.home / '.config' / ('-long ü name ' * 8 + '\x1b[31m')
        weird.write_text('fixture')
        before = digest(self.home), digest(self.repo)
        for width in (40, 80, 120):
            out = self.run_cli('system', DOTS_COLOR='always', NO_COLOR='1', COLUMNS=str(width)).stdout
            for code in ('95', '96', '94'):
                self.assertIn('\x1b[' + code + 'm', out)
            plain = re.sub(r'\x1b\[[0-9;]*m', '', out)
            self.assertNotIn('\x1b', plain)
            self.assertIn(r'\x1b[31m', plain)
            self.assertTrue(all(len(line) <= width for line in plain.splitlines()), plain)
        for env in ({'DOTS_COLOR':'auto'}, {'DOTS_COLOR':'never'},
                    {'DOTS_COLOR':'auto','TERM':'dumb'}, {'DOTS_COLOR':'auto','NO_COLOR':'1'}):
            self.assertNotIn('\x1b', self.run_cli('system', **env).stdout)
        for extra, colored in (({}, True), ({'NO_COLOR':'1'}, False), ({'TERM':'dumb'}, False)):
            master, slave = pty.openpty()
            try:
                env = dict(self.env, DOTS_COLOR='auto', DOTS_ICONS='auto', TERM='xterm-256color', NO_COLOR='')
                env.update(extra)
                proc = subprocess.Popen([sys.executable, '-B', str(PROJECT/'lib/dots/files/manage.py'), 'system'],
                                        env=env, stdout=slave, stderr=subprocess.PIPE)
                proc.communicate(timeout=10)
                self.assertEqual(proc.returncode, 0)
                data = os.read(master, 65536)
                self.assertEqual(b'\x1b[' in data, colored)
            finally:
                os.close(master); os.close(slave)
        self.assertEqual(before, (digest(self.home), digest(self.repo)))
        self.path.unlink(); weird.unlink()
        self.assertIn('No config candidates found.', self.run_cli('system').stdout)
        from manage import show_system
        output = io.StringIO()
        with mock.patch.dict(os.environ, self.env), redirect_stdout(output):
            show_system([{'path':str(self.path), 'repository':'dots', 'status':'unavailable'}], [])
        self.assertIn('[x] unavailable', output.getvalue())
        self.assertIn('~/.config/example/settings ü', output.getvalue())

    def test_owned_original_changed_after_replacement_is_retained(self):
        store=Store(self.home/'.state/dots')
        save=store.save
        def write_to_open_original(doc):
            save(doc)
            if doc['status']=='complete':
                Path(doc['operations'][0]['old']).write_text('late application write')
        with mock.patch.object(store,'save',side_effect=write_to_open_original):
            with self.assertRaises(ValueError):
                store.apply('test',[{'path':str(self.path),'link':'elsewhere'}],{str(self.path):digest(self.path)})
        doc=store.records()[0]
        self.assertEqual(doc['status'],'recovery-required')
        self.assertEqual(Path(doc['operations'][0]['old']).read_text(),'late application write')
        with self.assertRaises(ValueError):store.recover(doc['id'])
        self.assertEqual(Path(doc['operations'][0]['old']).read_text(),'late application write')

    def test_androidots_owner_and_excluded_sources(self):
        child=self.repo/'androidots';(child/'.dots').mkdir(parents=True)
        (child/'termux').mkdir()
        (child/'.dots/files.json').write_text(json.dumps({'schema':1,'repository':'androidots','resources':[]}))
        (child/'.dots/file-locations.json').write_text(json.dumps({'schema':1,'repository':'androidots','locations':[{'id':'termux','kind':'root','target':'${TERMUX}','source':'termux','platforms':['termux']}]}))
        composition=json.loads((self.repo/'.dots/sources.json').read_text())
        composition['sources'].extend([{'id':'androidots','path':'androidots','roots':['termux'],'platforms':['termux']},{'id':'private','path':'private','roots':[],'platforms':['termux'],'excluded':True}])
        self.write('.dots/sources.json',composition)
        path=self.home/'.termux/termux.properties';path.parent.mkdir();path.write_text('setting=true')
        env={'TERMUX_VERSION':'fixture','PREFIX':'/fixture/usr'}
        self.run_cli('add',path,'--yes',**env)
        self.assertTrue(path.is_symlink())
        self.assertTrue((child/'termux/termux.properties').exists())
        self.assertEqual(self.records(),[])
        self.assertFalse((self.repo/'private').exists())

    def test_special_file_and_symlink_parent_refused(self):
        fifo=self.path.parent/'pipe';os.mkfifo(fifo)
        self.run_cli('add',fifo,'--yes',ok=False)
        alias=self.home/'.config/alias';alias.symlink_to(self.path.parent,target_is_directory=True)
        self.run_cli('add',alias/self.path.name,'--yes',ok=False)
        self.assertEqual(self.path.read_text(),'original\n')
        self.assertFalse((self.home/'.state').exists())

    def test_remove_missing_source_preserves_regular_config(self):
        self.write('.dots/files.json',{'schema':1,'repository':'dots','resources':[{'id':'missing','source':'config/missing','target':'${CONFIG}/example/settings ü','strategy':'link','app':'example','category':'config','platforms':['termux','linux','wsl']}]})
        self.run_cli('remove','dots:missing','--yes')
        self.assertEqual(self.path.read_text(),'original\n')
        self.assertEqual(self.records(),[])

if __name__=='__main__': unittest.main()

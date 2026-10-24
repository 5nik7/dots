#!/usr/bin/env python3
"""Generated theme inspection; every target, source and state root is test-owned."""
import contextlib
import io
import json
import os
import re
import struct
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib/dots/themes'))
import inspection as subject


class ThemeFiles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='dots theme files ü ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / 'home'; self.home.mkdir()
        self.repo = self.root / 'repo'; self.repo.mkdir()
        self.config = self.home / 'config'; self.config.mkdir()
        self.state = self.home / 'state/dots'
        self.active = self.state / 'current/theme'
        self.generation = self.state / 'themes/generations/g.fixture'
        self.generation.mkdir(parents=True)
        self.active.parent.mkdir()
        self.active.symlink_to(self.generation, target_is_directory=True)
        self.env = dict(HOME=str(self.home), USERPROFILE=str(self.home), DOTS=str(self.repo),
                        XDG_CONFIG_HOME=str(self.config), XDG_STATE_HOME=str(self.home/'state'),
                        XDG_CACHE_HOME=str(self.home/'cache'), XDG_DATA_HOME=str(self.home/'data'),
                        APPDATA=str(self.home/'Roaming'), LOCALAPPDATA=str(self.home/'Local'),
                        CODEX_HOME=str(self.home/'codex'), PI_CODING_AGENT_DIR=str(self.home/'pi'),
                        PATH=os.environ.get('PATH',''), TERM='xterm-256color', DOTS_COLOR='never', DOTS_ICONS='never',
                        TMPDIR=str(self.root), PYTHONDONTWRITEBYTECODE='1')
        if 'LD_PRELOAD' in os.environ: self.env['LD_PRELOAD'] = os.environ['LD_PRELOAD']
        self.environ = patch.dict(os.environ, self.env, clear=True); self.environ.start(); self.addCleanup(self.environ.stop)
        self.templates = self.repo/'default/themed'; self.templates.mkdir(parents=True)
        (self.repo/'themes/fixture').mkdir(parents=True)
        (self.repo/'themes/fixture/colors.toml').write_text('background = "#123456"\nforeground = "#eeeeee"\n')
        names = subject.SHARED | set(subject.DERIVED) | {r[2] for r in subject.registry()} | {'id', 'bat.tmTheme'}
        names.discard('yazi')
        for name in names:
            p = self.generation/name; p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text('fixture\n' if name == 'id' else 'generated '+name+'\n')
        (self.templates/'bat.tmTheme.tpl').write_text('default {{ foreground }}\n')

    def doc(self, app=None):
        return subject.Inspection().inventory(app)

    def row(self, name, app=None):
        return next(r for r in self.doc(app)['artifacts'] if r['id']==name)

    def command(self, *args, code=0, frontend='python'):
        if frontend == 'native': command = [sys.executable, '-B', str(ROOT/'lib/dots/cli.py'), 'theme', 'files']
        elif frontend == 'bash': command = [shutil.which('bash'), str(ROOT/'bin/dots'), 'theme', 'files']
        elif frontend == 'standalone': command = [shutil.which('bash'), str(ROOT/'bin/theme'), 'files']
        else: command = [sys.executable, '-B', str(ROOT/'lib/dots/themes/inspection.py')]
        # Real metadata/code, isolated theme sources and machine state.
        env = dict(os.environ)
        if frontend != 'python': env['DOTS'] = str(ROOT)
        result = subprocess.run([*command,*args],env=env,cwd=self.home,capture_output=True,timeout=20)
        self.assertEqual(result.returncode,code,result.stderr.decode()+result.stdout.decode(errors='replace'))
        return result

    def test_inventory_and_sources(self):
        (self.generation/'bat-cache').mkdir()
        (self.generation/'connectors').mkdir()
        (self.generation/'connectors/secret').write_text('private')
        (self.generation/'commands').mkdir()
        (self.generation/'status').write_text('committed')
        (self.generation/'custom.txt').write_text('custom')
        self.assertTrue(self.doc()['healthy'])
        names={r['id'] for r in self.doc()['artifacts']}
        self.assertIn('custom.txt',names); self.assertNotIn('status',names); self.assertNotIn('connectors',names)
        self.assertEqual(self.row('bat-cache')['kind'],'cache')
        self.assertEqual(self.row('yazi/tmtheme.xml')['source']['artifact'],'bat.tmTheme')
        self.assertEqual(self.row('bat.tmTheme')['source']['kind'],'default-template')
        personal=self.config/'dots/themed';personal.mkdir(parents=True)
        (personal/'bat.tmTheme.tpl').write_text('personal')
        self.assertEqual(self.row('bat.tmTheme')['source']['kind'],'personal-template')
        override=self.repo/'themes/fixture/bat.tmTheme';override.write_text('override')
        self.assertEqual(self.row('bat.tmTheme')['source']['kind'],'bundled-override')
        user=self.config/'dots/themes/fixture';user.mkdir(parents=True)
        self.assertEqual(self.row('bat.tmTheme')['source']['kind'],'unknown')
        (self.repo/'themes/fixture/colors.toml').unlink()
        (user/'colors.toml').write_text('background = "#123456"\nforeground = "#eeeeee"\n')
        self.assertEqual(self.row('bat.tmTheme')['source']['kind'],'personal-template')
        shutil.rmtree(personal);shutil.rmtree(self.templates)
        self.assertEqual(self.row('bat.tmTheme')['source']['kind'],'unknown')
        self.assertEqual(subject.text_content(self.row('bat.tmTheme')),b'generated bat.tmTheme\n')

    def test_connections_and_directory_links(self):
        source=self.repo/'tmux config ü';source.mkdir()
        (self.config/'tmux').symlink_to(source,target_is_directory=True)
        target=source/'dots-theme.conf'
        target.symlink_to(self.active/'tmux.conf')
        c=self.row('tmux.conf')['connections'][0]
        self.assertEqual(c['status'],'linked');self.assertEqual(c['resolved_target'],str(target))
        target.unlink();target.symlink_to(os.path.relpath(self.active/'tmux.conf',source))
        # Relative links are interpreted from their actual parent on disk.
        self.assertEqual(self.row('tmux.conf')['connections'][0]['status'],'linked')
        target.unlink();target.symlink_to(self.generation/'tmux.conf')
        self.assertEqual(self.row('tmux.conf')['connections'][0]['status'],'pinned')
        self.assertFalse(self.doc()['healthy'])
        target.unlink();target.symlink_to(self.root/'gone')
        self.assertEqual(self.row('tmux.conf')['connections'][0]['status'],'broken')
        target.unlink();target.write_text('unrelated')
        self.assertEqual(self.row('tmux.conf')['connections'][0]['status'],'regular-file')
        target.unlink();self.assertEqual(self.row('tmux.conf')['connections'][0]['status'],'missing')
        other=self.root/'other';other.write_text('other');target.symlink_to(other)
        self.assertEqual(self.row('tmux.conf')['connections'][0]['status'],'points-elsewhere')

    def test_supplementary_finalized_journal(self):
        bat=self.config/'bat/themes/Dots.tmTheme';bat.parent.mkdir(parents=True)
        bat.symlink_to(self.active/'bat.tmTheme')
        journal=self.state/('files/transactions/'+'a'*32)/'journal.json';journal.parent.mkdir(parents=True)
        journal.write_text(json.dumps(dict(schema=1,status='complete',operations=[dict(path=str(bat))])))
        connections=self.row('bat.tmTheme')['connections']
        self.assertTrue(any(c['app']=='bat' and c['origin']=='transaction' and c['status']=='linked' for c in connections))
        journal.write_text('{')
        self.assertFalse(self.doc()['healthy'])

    def test_missing_artifacts_pointer_and_source(self):
        (self.generation/'tmux.conf').unlink()
        self.assertEqual(self.row('tmux.conf')['status'],'missing')
        self.command('check','--json',code=1)
        self.active.unlink()
        doc=json.loads(self.command('list','--json').stdout)
        self.assertEqual(doc['generation']['status'],'absent');self.assertEqual(doc['artifacts'],[])
        self.command('check',code=1);self.command('path',code=1)
        self.active.symlink_to(self.root)
        doc=json.loads(self.command('check','--json',code=1).stdout)
        self.assertEqual(doc['generation']['status'],'unavailable')

    def test_pinned_snapshot_and_refresh(self):
        inspected=subject.Inspection()
        other=self.generation.with_name('g.other');shutil.copytree(self.generation,other)
        (other/'id').write_text('other\n')
        self.active.unlink();self.active.symlink_to(other,target_is_directory=True)
        self.assertEqual(inspected.inventory()['generation']['theme'],'fixture')
        self.assertEqual(self.doc()['generation']['theme'],'other')
        self.assertEqual(inspected.record('bat.tmTheme')['resolved_path'],str(self.generation/'bat.tmTheme'))

    def test_safe_content_and_literal_identifiers(self):
        for name in ('with spaces ü.txt','-leading'):
            (self.generation/name).write_text('literal\n')
            self.assertEqual(self.command('show','--',name).stdout,b'literal\n')
        for name in ('../id','/etc/passwd','yazi/../id','connectors/secret','yazi//flavor.toml','yazi\\flavor.toml'):
            self.command('show',name,code=1)
        (self.generation/'bad').symlink_to(self.root/'outside')
        self.command('show','bad',code=1)
        for data in (b'\0binary',b'api_key=secretvalue',b'x'*(subject.LIMIT+1), b'\xff'):
            (self.generation/'bad').unlink();(self.generation/'bad').write_bytes(data)
            self.command('show','bad','--raw',code=1)
        (self.generation/'bad').unlink()
        if hasattr(os,'mkfifo'):
            os.mkfifo(self.generation/'bad')
            self.command('show','bad',code=1)
        self.command('show','yazi/tmtheme.xml','--source',code=1)
        self.command('path','--source',code=2)
        self.command('path','bat.tmTheme','--source','--resolved',code=2)

    def test_json_paths_and_no_writes(self):
        def snapshot():
            return {str(p.relative_to(self.root)):(p.lstat().st_mode,p.lstat().st_mtime_ns,os.readlink(p) if p.is_symlink() else p.read_bytes() if p.is_file() else None)
                    for p in self.root.rglob('*')}
        before=snapshot()
        with patch.dict(os.environ,DOTS_COLOR='always',DOTS_ICONS='always',DOTS_THEME_SELECTION='wrong'):
            self.assertEqual(self.command('path').stdout,(str(self.active)+'\n').encode())
            self.assertEqual(self.command('path','bat.tmTheme','--resolved').stdout,(str(self.generation/'bat.tmTheme')+'\n').encode())
            self.assertEqual(self.command('show','bat.tmTheme','--raw').stdout,b'generated bat.tmTheme\n')
            for args in (('list','--json'),('check','--json'),('info','bat.tmTheme','--json'),('list',)):
                self.assertNotIn(b'\x1b',self.command(*args).stdout)
        self.assertEqual(before,snapshot())

    def test_frontends_metadata_and_completion(self):
        for frontend in ('bash','native','standalone'):
            doc=json.loads(self.command('info','bat.tmTheme','--json',frontend=frontend).stdout)
            self.assertEqual(doc['artifacts'][0]['id'],'bat.tmTheme')
            self.assertEqual(self.command('path',frontend=frontend).stdout,(str(self.active)+'\n').encode())
        env=dict(os.environ,DOTS=str(ROOT))
        for prefix,args in (([shutil.which('bash'),str(ROOT/'bin/dots')],['__complete','bash','4','--','dots','theme','files','info','bat']),
                            ([sys.executable,'-B',str(ROOT/'lib/dots/cli.py')],['__complete','theme','files','info','bat'])):
            result=subprocess.run(prefix+args,env=env,capture_output=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn(b'bat.tmTheme',result.stdout)
        self.command('--help',frontend='bash')
        self.command('browse',code=2)
        self.command('check','--app','unknown-app',code=1)

    def test_browser_reloads_and_cancels(self):
        class FakeSelector:
            def __init__(inner):inner.calls=0
            def pick(inner,kind,title,choices,initial=''):
                inner.calls+=1
                if inner.calls==1:return next(c for c in choices if c.endswith('bat.tmTheme'))
                if inner.calls==2:
                    (self.generation/'bat.tmTheme').write_text('changed\n')
                    return 'Generated contents'
                return 'Exit'
        output=io.StringIO()
        with contextlib.redirect_stdout(output):self.assertEqual(subject.browse(selector=FakeSelector()),0)
        self.assertIn('changed',output.getvalue())
        class Cancel:
            def pick(self,*args):raise subject.SelectionEnded(130)
        with self.assertRaises(subject.SelectionEnded):subject.browse(selector=Cancel())

    def test_native_destinations_and_errors(self):
        with patch.object(subject,'eza_config_directory',return_value=self.home/'Roaming/eza'):
            self.assertEqual(self.row('eza.yml')['connections'][0]['target'],str(self.home/'Roaming/eza/theme.yml'))
        with patch.object(subject,'television_config_directory',side_effect=ValueError('invalid')):
            self.assertFalse(self.doc('television')['healthy'])
        with patch.object(subject.Path,'lstat',side_effect=PermissionError('denied')):
            self.assertEqual(subject.Inspection().publication,'unavailable')


    @unittest.skipIf(os.name == 'nt', 'POSIX numbered-selector acceptance')
    def test_browser_plain_terminal_and_escape(self):
        import pty
        import select
        import time
        before = {str(p):p.lstat().st_mtime_ns for p in self.root.rglob('*')}
        for keys,code in ((b'1\n4\n',0),(b'\x1b',130)):
            master,slave=pty.openpty()
            proc=None
            try:
                env=dict(os.environ,TERM='dumb')
                proc=subprocess.Popen([sys.executable,'-B',str(ROOT/'lib/dots/themes/inspection.py'),'browse'],
                    stdin=slave,stdout=slave,stderr=slave,env=env)
                os.close(slave);slave=None
                output=b'';sent=False;deadline=time.monotonic()+15
                while time.monotonic()<deadline:
                    ready,_,_=select.select([master],[],[],0.1)
                    if ready:
                        try:chunk=os.read(master,65536)
                        except OSError:break
                        if not chunk:break
                        output+=chunk
                    if not sent and b'Esc cancels' in output:
                        os.write(master,keys);sent=True
                    if proc.poll() is not None:break
                self.assertEqual(proc.wait(timeout=2),code,output.decode())
                self.assertIn(b'Generated theme files',output)
                if code==0:self.assertIn(b'Theme file: bat.tmTheme',output)
            finally:
                if proc and proc.poll() is None:proc.kill();proc.wait()
                os.close(master)
                if slave is not None:os.close(slave)
        self.assertEqual(before,{str(p):p.lstat().st_mtime_ns for p in self.root.rglob('*')})

    def test_windows_connector_policy(self):
        inspect = subject.Inspection()
        with patch.dict(os.environ, XDG_CONFIG_HOME=''):
            inspect.fixed_connections(windows=True)
        connections = inspect.connections
        eza = next(c for c in connections if c['app'] == 'eza')
        self.assertEqual(eza['target'], str(self.home/'Roaming/eza/theme.yml'))
        tv = next(c for c in connections if c['app'] == 'television')
        self.assertEqual(tv['target'], str(self.home/'Local/television/config/themes/dots.toml'))
        leaf = next(c for c in connections if c['app'] == 'leaf')
        self.assertEqual(leaf['target'], str(self.home/'Roaming/leaf/themes/dots.toml'))
        self.assertEqual(next(c for c in connections if c['app']=='tmux')['status'], 'unavailable')
        self.assertFalse(any(c['app']=='termux' for c in connections))

    @unittest.skipIf(os.name == 'nt', 'POSIX terminal acceptance')
    def test_terminal_widths_and_sanitized_previews(self):
        import fcntl
        import pty
        import termios
        from resources import cells
        (self.generation/'control.txt').write_text('safe\x1b[31m text\n')
        cache = self.generation/'bat-cache'; cache.mkdir()
        (cache/('long Unicode ü ' * 5 + '.bin')).write_bytes(b'\0')
        for width in (40, 80, 120):
            for mode,background in (('always', '#101010'), ('always', '#eeeeee'), ('never', '#101010')):
                from palette_native import styles
                styles().write_snapshot(dict(schema=1, colors={'background':background},
                    styles={'type':{'file':{'fg':'#dddddd' if background=='#101010' else '#222222'}},'mime':{},'extension':{}},
                    ls_colors='', ls_rules=styles().parse_ls(''), provenance={}), self.generation)
                for args in (['info','bat.tmTheme'], ['list','--app','nothing'], ['list','--app','leaf'],
                             ['show','bat-cache'], ['show','control.txt'], ['show','missing']):
                    with self.subTest(width=width, mode=mode, background=background, args=args):
                        master, slave = pty.openpty()
                        try:
                            fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 24, width, 0, 0))
                            env=dict(os.environ,DOTS_COLOR=mode,DOTS_ICONS='never',COLUMNS=str(width))
                            result=subprocess.run([sys.executable,'-B',str(ROOT/'lib/dots/themes/inspection.py'),*args],
                                env=env,stdout=slave,stderr=slave,timeout=15)
                            os.close(slave);slave=None
                            output=b''
                            while True:
                                try:part=os.read(master,65536)
                                except OSError:break
                                if not part:break
                                output+=part
                            self.assertEqual(result.returncode,1 if args==['show','missing'] else 0,output)
                            text=output.decode().replace('\r\n','\n')
                            plain=re.sub(r'\x1b\[[0-9;]*m','',text)
                            self.assertTrue(all(cells(line)<=width for line in plain.splitlines()),plain)
                            if args==['show','control.txt']:
                                self.assertIn(r'\x1b[31m',text);self.assertNotIn('\x1b[31m',text)
                        finally:
                            os.close(master)
                            if slave is not None:os.close(slave)

    def test_all_completion_protocols(self):
        env=dict(os.environ,DOTS=str(ROOT))
        for shell in ('bash','zsh','fish'):
            for words,expected in ((['theme','files','info','bat'],b'bat.tmTheme'),
                                   (['theme','files','list','--app','ya'],b'yazi'),
                                   (['theme','files','check','--con'],b'--consumers')):
                result=subprocess.run([shutil.which('bash'),str(ROOT/'bin/dots'),'__complete',shell,str(len(words)),
                    '--','dots',*words],env=env,capture_output=True,timeout=15)
                self.assertEqual(result.returncode,0,result.stderr);self.assertIn(expected,result.stdout)
        native=subprocess.run([sys.executable,'-B',str(ROOT/'lib/dots/cli.py'),'__complete',
            'theme','files','check','--app','ya'],env=env,capture_output=True,timeout=15)
        self.assertEqual(native.returncode,0,native.stderr);self.assertIn(b'yazi',native.stdout)
        native=subprocess.run([sys.executable,'-B',str(ROOT/'lib/dots/cli.py'),'__complete',
            'theme','files','check','--con'],env=env,capture_output=True,timeout=15)
        self.assertEqual(native.returncode,0,native.stderr);self.assertIn(b'--consumers',native.stdout)


class PublicationInspection(unittest.TestCase):
    def test_bash_and_native_prepared_generations(self):
        import test_themes as fixture
        case = fixture.Themes('test_routes_values_and_plain_output')
        case.setUp()
        self.addCleanup(case.doCleanups)
        case.dots('theme', 'set', 'nord')
        for frontend in ([str(case.repo/'bin/dots')],
                         [sys.executable,'-B',str(case.repo/'lib/dots/cli.py')]):
            result=subprocess.run([*frontend,'theme','files','check','--json'],env=case.env,cwd=case.home,
                capture_output=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stderr.decode()+result.stdout.decode())
            self.assertTrue(json.loads(result.stdout)['healthy'])
        # Native renderer integration without desktop effects or live publication.
        from palette_native import Themes
        from theme_cli import shell_init
        with patch.dict(os.environ,case.env,clear=True):
            generation=case.state/'generations/g.native'
            generation.mkdir()
            palette=Themes().render('nord',generation)
            for shell,suffix in (('powershell','ps1'),('zsh','zsh'),('fish','fish')):
                (generation/('init.'+suffix)).write_text(shell_init(palette,shell))
            active=case.home/'state/dots/current/theme'
            active.unlink();active.symlink_to(generation,target_is_directory=True)
            self.assertTrue(subject.Inspection().inventory()['healthy'])


if __name__=='__main__': unittest.main()

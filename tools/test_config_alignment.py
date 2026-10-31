#!/usr/bin/env python3
"""Fresh completion processes and shared human column consumers in owned roots."""
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

import test_profile_config as fixtures
from config_values import current as controls
from style_config import current as styles
from files.catalog import Presentation
from resources import cells
from row_layout import width as column_width
from test_menus import NativeMenuFixture

ANSI=re.compile(r'\x1b\[[0-9;]*m')


class Alignment(unittest.TestCase):
    def setUp(self):
        fixtures.ProfileConfig.setUp(self)
        shutil.copytree(fixtures.ROOT/'default',self.root/'default')
        shutil.copytree(fixtures.ROOT/'config/wttr',self.root/'config/wttr')
        self.env.update(TERM='xterm-256color',DOTS_COLOR='always',DOTS_ICONS='never',PATH=str(self.root/'bin')+os.pathsep+self.env['PATH'])
        self.environment=patch.dict(os.environ,self.env,clear=True)
        self.environment.start();self.addCleanup(self.environment.stop)
        controls.cache_clear();styles.cache_clear()
        self.addCleanup(controls.cache_clear);self.addCleanup(styles.cache_clear)

    def configure(self,**formats):
        doc=json.loads(self.path.read_text());doc['formatting']={'apps':formats}
        self.path.write_text(json.dumps(doc));controls.cache_clear();styles.cache_clear()

    def cli(self,*args,**kwargs):return fixtures.ProfileConfig.run_config(self,*args,**kwargs)

    def test_fresh_completion_with_weather_and_invalid_optional_config(self):
        for route in ('get','set','unset','explain'):
            outputs=[]
            for shell in ('bash','zsh','fish','native'):
                cmd=([sys.executable,'-B',str(self.root/'lib/dots/cli.py'),'__complete','config',route,''] if shell=='native'
                     else [str(self.root/'bin/dots'),'__complete',shell,'3','--','dots','config',route,''])
                p=subprocess.run(cmd,env=self.env,text=True,capture_output=True,timeout=20)
                self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(p.stderr,'')
                keys=[row.split('\t')[1] for row in p.stdout.splitlines()]
                self.assertIn('apps.menu.popup.border',keys)
                self.assertIn('apps.wttr.icons["113"]',keys)
                self.assertIn('formatting.apps.cli.label_width',keys)
                self.assertNotIn('\x1b',p.stdout);outputs.append(keys)
            self.assertTrue(all(keys==outputs[0] for keys in outputs))
        code='import sys;sys.path.insert(0,sys.argv[1]);from config_wttr import Native;Native(sys.argv[2]).keys();assert "files.transactions" not in sys.modules'
        p=subprocess.run([sys.executable,'-B','-c',code,str(self.root/'lib/dots'),str(self.root)],env=self.env,capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        path=self.home/'config/wttr';path.mkdir(parents=True)
        (path/'config.toml').write_text('this is not TOML')
        p=subprocess.run([str(self.root/'bin/dots'),'__complete','zsh','3','--','dots','config','get','apps.menu.popup.'],env=self.env,capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr);self.assertIn('apps.menu.popup.border',p.stdout)

    @unittest.skipUnless(shutil.which('zsh') and os.name!='nt','native Zsh terminal unavailable')
    def test_real_zsh_tab_inserts_config_key(self):
        import pty,select,signal
        pid,fd=pty.fork()
        if pid==0:os.execve(shutil.which('zsh'),['zsh','-f'],dict(self.env,TERM='xterm-256color',PS1='START> '))
        def receive(needle):
            data=b'';deadline=time.monotonic()+20
            while needle not in data and time.monotonic()<deadline:
                if select.select([fd],[],[],.1)[0]:
                    try:data+=os.read(fd,65536)
                    except OSError:break
            self.assertIn(needle,data);return data
        try:
            receive(b'START>')
            os.write(fd,b'autoload -Uz compinit; compinit -D; source "$DOTS/lib/dots/completion/zsh"; PROMPT="READY> "\n')
            receive(b'READY>')
            os.write(fd,b'dots config get apps.menu.popup.bor\t')
            time.sleep(2)
            # Print the completed edit buffer instead of executing a command.
            os.write(fd,b'\x01print -r -- \x05\n')
            receive(b'dots config get apps.menu.popup.border')
        finally:
            try:os.kill(pid,signal.SIGTERM)
            except ProcessLookupError:pass
            os.close(fd);os.waitpid(pid,0)

    def test_cli_and_bash_columns_percent_fixed_spacing_and_plain_data(self):
        raw=self.cli('get','apps.menu.popup','--json').stdout
        for setting in ('40%',16,0):
            self.configure(cli={'label_width':setting,'label_gap':3,'alignment':'right','indent':4})
            for columns in (40,80,120):
                expected=column_width(setting,columns,indent=4,gap=3)
                stream=io.StringIO();ui=Presentation(stream,terminal=True);ui.width=columns;ui.color=False;ui.icons=False
                for label in ('Key','界'):
                    ui.detail(label,'VALUE');ui.resource_detail(label,None,display='VALUE')
                lines=stream.getvalue().splitlines()
                for line in lines:
                    label='Key' if 'Key' in line else '界'
                    self.assertEqual(cells(line[:line.index('VALUE')]),4+max(cells(label),expected)+3)
                    self.assertLessEqual(cells(line),columns)
                script='source "$DOTS/lib/dots/ui.bash"; dots::row Key VALUE; dots::row 界 VALUE; dots::resource_row Key /fixture VALUE'
                p=subprocess.run([shutil.which('bash'),'-c',script],env=dict(self.env,COLUMNS=str(columns)),text=True,capture_output=True,timeout=15)
                self.assertEqual(p.returncode,0,p.stderr)
                for line in ANSI.sub('',p.stdout).splitlines():
                    label='Key' if 'Key' in line else '界'
                    self.assertEqual(cells(line[:line.index('VALUE')]),4+max(cells(label),expected)+3,p.stdout)
                    self.assertLessEqual(cells(line),columns)
        self.assertEqual(self.cli('get','apps.menu.popup','--json').stdout,raw)
        self.assertEqual(self.cli('get','apps.menu.popup.border').stdout,'rounded\n')
        plain=io.StringIO()
        with patch.dict(os.environ,DOTS_COLOR='never',DOTS_ICONS='never'):
            Presentation(plain).detail('Key','VALUE')
        self.assertEqual(plain.getvalue(),'    Key        VALUE\n')

    def test_guarded_alignment_edits_and_long_labels(self):
        for key in ('formatting.apps.cli.label_width','formatting.apps.menu.label_width'):
            result=json.loads(self.cli('set',key,'40%','--json').stdout)
            self.assertEqual(result['refresh']['status'],'complete')
            self.assertIn(result['refresh']['consumers'][0]['status'],('next invocation','next popup'))
            self.assertEqual(self.cli('get',key,native=True).stdout,'40%\n')
            self.cli('set',key,'$(touch BAD)',code=1)
            self.cli('set',key,'101%',code=1)
            self.cli('unset',key)
        self.configure(cli={'label_width':12,'label_gap':2})
        stream=io.StringIO();ui=Presentation(stream,terminal=True);ui.color=False;ui.width=40
        label='long.界.key.'*5
        ui.detail(label,'VALUE')
        lines=stream.getvalue().splitlines()
        self.assertEqual(''.join(line[4:] for line in lines[:-1]),label)
        self.assertEqual(lines[-1],' '*18+'VALUE')
        self.assertTrue(all(cells(line)<=40 for line in lines))
        self.assertFalse((self.home/'BAD').exists())

    def test_config_popup_rows_use_menu_columns_and_keep_full_keys(self):
        from config_menu import Inventory,pick
        from menu_tmux import TmuxContext
        self.configure(menu={'label_width':'50%','label_gap':3})
        inventory=Inventory(self.root,self.platform)
        inventory.rows=[inventory.find('apps.menu.popup.width'),inventory.find('apps.menu.popup.border')]
        ctx=TmuxContext('/tmux','/private','/client',1,'%1','$1',str(self.home))
        from contextlib import nullcontext
        for columns in (40,80,120):
            with patch.object(TmuxContext,'verify',return_value=(columns,30)), \
                 patch.object(TmuxContext,'selector_environment',return_value=nullcontext({})), \
                 patch('config_menu.RichSelector.fzf',return_value=[0]) as select:
                self.assertEqual(pick(inventory,'apps',{},ctx).key,'apps.menu.popup.width')
            labels=select.call_args.args[1]
            text_width=columns-8
            start=1+column_width('50%',text_width,indent=1,gap=3)+3
            for label,value in zip(labels,('auto','rounded')):
                plain=ANSI.sub('',label)
                self.assertIn('apps.menu.popup.',plain)
                line=next(line for line in plain.splitlines() if value in line)
                self.assertEqual(cells(line[:line.index(value)]),start)

    def test_shared_menu_columns_keep_icons_and_alignment(self):
        from menu_popup import content_size
        from menus import Entry,Menu,styled_label
        self.assertEqual(content_size(['one\nsecond'],'','',(80,30),{'width':'fit'}),(12,7))
        menu=Menu('fixture','Fixture',(Entry('a','Key','VALUE',icon='界'),Entry('b','Key','VALUE')))
        for alignment in ('left','center','right'):
            self.configure(cli={'label_width':16,'label_gap':2,'alignment':alignment},
                           menu={'label_width':'40%','label_gap':2,'alignment':alignment})
            for columns in (40,80,120):
                ui=Presentation(io.StringIO(),terminal=True);ui.width=columns;ui.icons=True
                expected=1+column_width('40%',columns,indent=1,gap=2)+2
                for entry in menu.entries:
                    line=ANSI.sub('',styled_label(menu,entry,ui))
                    self.assertEqual(cells(line[:line.index('·')]),expected)
                    self.assertIn(entry.label,line)
                    if entry.icon:self.assertIn(entry.icon,line)
            for label in ('Key','界'):
                stream=io.StringIO();ui=Presentation(stream,terminal=True);ui.width=80;ui.color=False
                ui.detail(label,'VALUE')
                script='source "$DOTS/lib/dots/ui.bash"; dots::row "$1" VALUE'
                result=subprocess.run([shutil.which('bash'),'-c',script,'fixture',label],env=dict(self.env,COLUMNS='80'),capture_output=True,text=True,timeout=15)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(ANSI.sub('',result.stdout),stream.getvalue())

    def test_fit_popup_keeps_columns_at_the_resolved_width(self):
        from contextlib import nullcontext
        from menu_tmux import TmuxContext
        from menus import Menu,Entry,choose
        self.configure(menu={'label_width':'40%','label_gap':2})
        doc=json.loads(self.path.read_text());doc['apps']={'menu':{'popup':{'width':'fit','height':'fit'}}}
        self.path.write_text(json.dumps(doc));controls.cache_clear()
        menu=Menu('fixture','Fixture',(Entry('one','Key','VALUE'),))
        ctx=TmuxContext('/tmux','/private','/client',1,'%1','$1',str(self.home))
        for columns in (40,80,120):
            calls=[]
            def run(argv,**kw):
                if argv==['fzf','--help']:return subprocess.CompletedProcess(argv,0,b'--popup')
                calls.append((argv,kw));return subprocess.CompletedProcess(argv,0,b'0\tKey\0')
            with patch.object(TmuxContext,'verify',return_value=(columns,30)), \
                 patch.object(TmuxContext,'selector_environment',return_value=nullcontext({'DOTS_MENU_COLUMNS':str(columns),'DOTS_MENU_LINES':'30'})), \
                 patch('interaction.rich_fzf_available',return_value=True), \
                 patch('menus.subprocess.run',side_effect=run):
                self.assertEqual(choose(menu,mode='browse',context=ctx).id,'one')
            argv,kw=calls[-1]
            width=int(argv[argv.index('--popup')+1].split(',')[1])
            line=ANSI.sub('',kw['input'].decode().split('\t',1)[1].rstrip('\0'))
            start=1+column_width('40%',width-6,indent=1,gap=2)+2
            self.assertEqual(cells(line[:line.index('·')]),start)

    def test_compiled_shell_rows_are_literal_and_invalidate_with_defaults(self):
        from startup import Compiler,prepare
        defaults=self.root/'default/config.json'
        doc=json.loads(defaults.read_text());doc['formatting']['apps']['cli']['label_width']='40%'
        defaults.write_text(json.dumps(doc))
        for shell in ('bash','zsh'):
            executable=shutil.which(shell)
            if not executable:continue
            # No personal startup modules are included or executed by this fixture.
            with patch.object(Compiler,'expand',return_value=':'):
                destination=self.home/('compiled-'+shell)
                generation=prepare(self.root,shell,destination)
            script='python3() { return 99; }; source "$1"; printf "%s\\n" "${_DOTS_FORMATTING[label_width]}"'
            result=subprocess.run([executable,'-c',script,'fixture',str(generation/'bundle')],env=self.env,capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(result.stdout,'40%\n')
            self.assertIn(str(defaults),(generation/'guard').read_text())
            doc['formatting']['apps']['cli']['label_width']='50%';defaults.write_text(json.dumps(doc))
            with patch.object(Compiler,'expand',return_value=':'):updated=prepare(self.root,shell,destination)
            self.assertNotEqual(updated,generation)
            doc['formatting']['apps']['cli']['label_width']='40%';defaults.write_text(json.dumps(doc))


class NativeAlignment(NativeMenuFixture):
    def test_multiline_key_rows_still_select_their_identity(self):
        root=Path(self.env['DOTS']);root.mkdir()
        shutil.copytree(fixtures.ROOT/'default',root/'default')
        doc=json.loads((root/'default/config.json').read_text())
        doc['formatting']['apps']['menu'].update(label_width='40%',label_gap=2)
        (root/'default/config.json').write_text(json.dumps(doc))
        for name in ('termux','linux','wsl','windows'):
            path=root/'profiles'/name;path.mkdir(parents=True);(path/'profile.json').write_text(json.dumps(dict(schema=1,id=name)))
        code='''import os
from types import SimpleNamespace
from config_menu import Row,pick
from menu_tmux import TmuxContext
rows=[Row('apps.really_long.configuration_key','ONE','fixture','fixture'),Row('apps.short','TWO','fixture','fixture')]
item=pick(SimpleNamespace(scope='fixture',rows=rows),'apps',{},TmuxContext.capture(client=os.environ['CLIENT']))
print(item.key)
'''
        for columns in (40,80,120):
            self.fcntl.ioctl(self.first[1],self.termios.TIOCSWINSZ,self.struct.pack('HHHH',30,columns,0,0))
            time.sleep(.1);self.drain(self.first[1]);self.drain(self.second[1])
            worker=self.worker(code)
            self.receive(self.first[1],b'ONE');self.assertNotIn(b'ONE',self.drain(self.second[1]))
            os.write(self.first[1],b'\r');out,err=worker.communicate(timeout=10)
            self.assertEqual(worker.returncode,0,err);self.assertEqual(out.strip(),'apps.really_long.configuration_key')


if __name__=='__main__':unittest.main()

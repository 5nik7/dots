#!/usr/bin/env python3
"""Key browser acceptance in owned homes; never source personal startup."""
from contextlib import ExitStack
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
NVIM=shutil.which('nvim')
sys.path.insert(0,str(ROOT/'lib/dots'))
from debug.fixtures import fixture
from keys.model import readable,record,merge
from keys.providers import shell_dump,snapshot,toml_rows,kitty_rows,nvim_rows,collect,fzf_defaults


class Keys(unittest.TestCase):
    def setUp(self):
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.root,self.env,self.base=self.stack.enter_context(fixture(ROOT))
        for name in ('dots-keys','dots-menu-tmux-keys'):
            shutil.copy2(ROOT/'bin'/name,self.root/'bin'/name)
        if os.name!='nt':
            for name in ('dots','dots-keys','dots-menu-tmux-keys'):
                p=self.root/'bin'/name;p.write_text('#!'+shutil.which('bash')+'\n'+p.read_text().partition('\n')[2])
        self.env['PATH']=str(self.root/'bin')+os.pathsep+self.env['PATH']
        self.stack.enter_context(patch.dict(os.environ,self.env,clear=True))
        self.home=Path(self.env['HOME'])

    def cli(self,*args,code=0):
        result=subprocess.run([sys.executable,'-B',str(self.root/'lib/dots/keys_cli.py'),*args],env=self.env,capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,code,result.stderr+result.stdout)
        return result

    def test_notation(self):
        for raw,want in [('^G','Ctrl+G'),('^H','Ctrl+H (Backspace)'),('^?','Backspace (DEL)'),
                         ('\\C-g','Ctrl+G'),('\\e[1;5D','Ctrl+Left'),('<C-x>','Ctrl+X'),
                         ('<leader>ff','Leader → f → f'),('ctrl-up','Ctrl+Up'),(['g','g'],'g → g'),
                         ('^X^E','Ctrl+X → Ctrl+E'),('\\e.','Alt+.'),(' ','Space')]:
            self.assertEqual(readable(raw),want,raw)

    def test_shell_parsing_and_no_macros(self):
        rows=shell_dump('zsh','viins','bindkey -M viins "^H" vi-backward-delete-char\nbindkey -M viins -s "^X" "secret body"')
        self.assertEqual(rows[0]['display'],'Ctrl+H (Backspace)')
        self.assertNotIn('secret',json.dumps(rows));self.assertEqual(len(rows),2)
        rows=shell_dump('zsh','vicmd','bindkey -a "k" history-substring-search-up\nbindkey -a -s "x" "secret body"\nbindkey -a -R "0-9" digit-argument')
        self.assertEqual([r['mode'] for r in rows],['vicmd']*3)
        self.assertEqual([r['kind'] for r in rows],['widget','macro','range'])
        self.assertNotIn('secret',json.dumps(rows))
        rows=shell_dump('bash','emacs-standard','"\\C-g": abort\n"\\C-x": "secret body"')
        self.assertEqual(rows[0]['display'],'Ctrl+G');self.assertNotIn('secret',json.dumps(rows))

    def test_parent_shell_capture_and_transparent_forwarding(self):
        for shell in ('zsh','bash'):
            if not shutil.which(shell):continue
            with self.subTest(shell=shell):
                custom='bindkey -M viins "^G" fixture-widget' if shell=='zsh' else 'bind -m vi-insert "\\\"\\C-g\\\": backward-char"'
                code='source "$DOTS/lib/dots/shell/keys.bash"\n'+custom+'\ndots keys '+shell+' --source live --json\ndots --help\n'
                flags=['-df','-ic'] if shell=='zsh' else ['--noprofile','--norc','-ic']
                p=subprocess.run([shutil.which(shell),*flags,code],env=self.env,capture_output=True,text=True,timeout=20)
                self.assertEqual(p.returncode,0,p.stderr)
                data=json.loads(p.stdout.splitlines()[0]);self.assertTrue(data['rows'])
                self.assertTrue(any(r['action']==('fixture-widget' if shell=='zsh' else 'backward-char') and r['display']=='Ctrl+G' for r in data['rows']))
                self.assertTrue(all(r['evidence']=='live' for r in data['rows']))
                self.assertGreater(len(p.stdout.splitlines()),1)

    def test_existing_user_function_not_overwritten(self):
        for shell in ('bash','zsh'):
            if not shutil.which(shell):continue
            flags=['--noprofile','--norc','-c'] if shell=='bash' else ['-dfc']
            p=subprocess.run([shutil.which(shell),*flags,'dots() { printf original; }; source "$DOTS/lib/dots/shell/keys.bash"; dots'],env=self.env,capture_output=True,text=True)
            self.assertEqual(p.stdout,'original')

    def test_native_config_paths_and_explicit_missing_override(self):
        from keys.providers import config_root
        for name in ('APPDATA','LOCALAPPDATA'):
            Path(self.env[name]).mkdir(parents=True,exist_ok=True)
        nvim=Path(self.env['LOCALAPPDATA'])/'nvim';nvim.mkdir()
        yazi=Path(self.env['APPDATA'])/'yazi/config';yazi.mkdir(parents=True)
        self.assertEqual(config_root(self.root,'nvim',windows=True),nvim)
        self.assertEqual(config_root(self.root,'yazi',windows=True),yazi)
        target=self.base/'missing-config'
        with patch.dict(os.environ,{'YAZI_CONFIG_HOME':str(target)}):
            self.assertEqual(config_root(self.root,'yazi'),target)

    def test_data_configurations_and_includes(self):
        path=self.base/'keys ü.toml';path.write_text('[[mgr.prepend_keymap]]\non=["g","g"]\nrun="top"\ndesc="Go to the first file"\n')
        rows=toml_rows(path,'yazi');self.assertEqual(rows[0]['display'],'g → g');self.assertEqual(rows[0]['description_source'],'authored')
        path.write_text('[keybindings]\nctrl-up="select_prev_history"\n')
        self.assertEqual(toml_rows(path,'television')[0]['display'],'Ctrl+Up')
        child=self.base/'included.conf';child.write_text('map ctrl+g launch\ninclude kitty.conf\n')
        main=self.base/'kitty.conf';main.write_text('include included.conf\nmap ctrl+x>h neighboring_window left\n')
        rows=kitty_rows(main,[]);self.assertEqual(len(rows),2);self.assertEqual(rows[1]['display'],'Ctrl+X → h')
        path.write_text('broken = [');self.assertRaises(ValueError,toml_rows,path,'yazi')

    def test_nvim_static_never_executes_lua(self):
        directory=self.base/'nvim/lua/config';directory.mkdir(parents=True)
        path=directory/'keymaps.lua';path.write_text('os.execute("touch should-not-exist")\nvim.keymap.set("n", "<C-g>", "<cmd>help<cr>", { desc = "Open help" })\n')
        notes=[];rows=nvim_rows(directory.parent.parent,notes)
        self.assertEqual(rows[0]['description'],'Open help');self.assertTrue(notes);self.assertFalse((self.base/'should-not-exist').exists())
        path.write_text('''{ "<C-g>", "help", mode = { "n", "x" }, desc = "Open help" },
{ "<C-a>", "help", mode = "i", desc = "Insert help" },
{ "<C-b>", "help", mode = dynamic_mode, desc = "Unknown mode" },
''')
        rows=nvim_rows(directory.parent.parent,[])
        self.assertEqual([row['mode'] for row in rows],['n','x','i'])

    def test_live_overrides_and_native_snapshot(self):
        data={'version':1,'app':'nvim','rows':[{'key':'<C-g>','mode':'n','action':'Lua callback','description':'Buffer help','scope':'buffer 1'}]}
        rows,apps=snapshot(json.dumps(data).encode(),'json')
        rows=merge([record('nvim','n','<C-g>','help'),*rows])
        self.assertEqual({r['status'] for r in rows},{'active','shadowed'});self.assertEqual(apps,{'nvim'})
        self.assertRaises(ValueError,snapshot,b'bad','shell')

    def test_json_filters_and_unavailable_coverage(self):
        directory=self.root/'config/yazi';directory.mkdir(parents=True)
        (directory/'keymap.toml').write_text('[[mgr.prepend_keymap]]\non="<C-g>"\nrun="help"\ndesc="Open help"\n')
        self.env.update(DOTS_COLOR='always',DOTS_ICONS='always')
        data=json.loads(self.cli('yazi','--json','--query','help','--mode','mgr','--no-defaults').stdout)
        self.assertEqual(len(data['rows']),1)
        self.assertEqual(json.loads(self.cli('yazi','--json','--source','live').stdout)['rows'],[])
        self.assertIn('coverage',json.loads(self.cli('apps','--json').stdout))
        self.cli('--json','--browse',code=2)

    def test_tmux_native_records(self):
        def native(args):
            if '-F' in args:return 'dots-keys\tprefix\t?\t"Open help"\n'
            if 'list-keys' in args:return 'bind-key -r -T prefix -N "Open help" ? display-menu\nbind-key -T root C-g run-shell "secret-command"\n'
            return 'C-b\n' if args[-1]=='prefix' else 'None\n'
        with patch('keys.providers.run',native),patch('keys.providers.shutil.which',return_value='/fixture/tmux'):
            from keys.providers import tmux_rows
            rows,notes=tmux_rows()
        self.assertEqual(rows[0]['display'],'Ctrl+B → ?');self.assertNotIn('secret-command',json.dumps(rows));self.assertFalse(notes)

    def test_popup_and_plain_fzf_arguments_are_isolated(self):
        from interaction import RichSelector
        calls=[]
        def invoke(args,**kwargs):
            calls.append((args,kwargs));return subprocess.CompletedProcess(args,0,b'0\tlabel\0',b'')
        with patch('interaction.subprocess.run',invoke):
            for popup in (False,True):
                result=RichSelector.__new__(RichSelector).fzf('Keys',['label'],False,None,False,False,'',popup=popup)
                self.assertEqual(result,[0])
        self.assertNotIn('--popup',calls[0][0]);self.assertEqual(calls[1][0][calls[1][0].index('--popup')+1],'center,90%')
        self.assertEqual(calls[1][1]['env']['FZF_DEFAULT_OPTS'],'')

    def test_category_rows_dimensions_and_field_colors(self):
        from files.catalog import Presentation
        from keys.presentation import menu_rows,menu_dimensions,styles,binding_label,picker_colors
        ui=Presentation(stream=io.StringIO());ui.color=True;ui.icons=True
        from keys.model import APPS
        coverage=[dict(app=app,count=1) for app in APPS]
        categories=menu_rows(ui,coverage)
        self.assertEqual([row[0] for row in categories],['all','bash','codex','fzf','kitty','nvim','powershell','television','tmux','yazi','zsh'])
        self.assertTrue(all(any(ord(c)>0xe000 for c in label) for _,label in categories))
        ui.icons=False;ui.color=False;self.assertEqual(menu_rows(ui,coverage)[0],('all','All · [10]'))
        apps=menu_rows(ui,[dict(app='zsh',count=2,live=True),dict(app='tmux',count=0)],include_all=False)
        self.assertEqual(apps,[('zsh','Zsh · [2]')])
        self.assertEqual(menu_rows(ui,[]),[])
        for width,height in ((40,10),(80,24),(120,40)):
            with patch('keys.presentation.shutil.get_terminal_size',return_value=(width,height)):
                w,h=menu_dimensions([label for _,label in categories])
                self.assertLessEqual(w,width-2);self.assertEqual(h,min(17,height-2))
        ui.resources.root=self.base/'palette';ui.resources.root.mkdir()
        (ui.resources.root/'palette.json').write_text(json.dumps({'colors':{'muted':'#667788','bright_magenta':'#ff88cc'}}))
        ui.color=True
        colored=menu_rows(ui,coverage)
        self.assertIn('\x1b[38;2;102;119;136m · [10]\x1b[0m',colored[0][1])
        ui.color=False
        plain=menu_rows(ui,coverage)
        self.assertEqual(menu_dimensions([r[1] for r in colored]),menu_dimensions([r[1] for r in plain]))
        ui.color=True
        codes=styles(ui);row=record('zsh','viins','^G','help',description='Description')
        label=binding_label(ui,row,codes)
        self.assertIn('\x1b[1;38;2;255;136;204mCtrl+G\x1b[0m',label)
        self.assertIn('\x1b[38;2;102;119;136m · ',label)
        row['description']='unsafe\x1b[31m';self.assertNotIn('\x1b[31m',binding_label(ui,row,codes))
        ui.color=False;self.assertNotIn('\x1b',binding_label(ui,row,codes))
        self.assertEqual(picker_colors('bg:#000000,fg+:strip:#ffffff:bold'),'bg:#000000,fg+:-1:regular')
        (ui.resources.root/'palette.json').write_text('broken')
        self.assertEqual(styles(ui),('90','1;95','38;5;208'))

    def test_key_picker_layout_overrides_leave_other_pickers_unchanged(self):
        from interaction import RichSelector
        calls=[]
        def invoke(args,**kwargs):
            calls.append(args);return subprocess.CompletedProcess(args,0,b'0\tlabel\0',b'')
        preview=('preview',None,{})
        with patch('interaction.subprocess.run',invoke):
            for width in (40,80,120):
                with patch('interaction.shutil.get_terminal_size',return_value=os.terminal_size((width,30))):
                    RichSelector.__new__(RichSelector).fzf('Keys',['label'],False,preview,True,True,'',popup='center,99%',preview_size=45)
                    self.assertIn('--preview-window='+('down' if width<100 else 'right')+',45%',calls[-1])
                    self.assertIn('center,99%',calls[-1])
            RichSelector.__new__(RichSelector).fzf('Categories',['label'],False,None,True,True,'',height=17,header='Enter: open  Esc: cancel')
            self.assertIn('--height=17',calls[-1]);self.assertNotIn('--popup',calls[-1])
            self.assertIn('--header=Enter: open  Esc: cancel',calls[-1])
            RichSelector.__new__(RichSelector).fzf('Other',['label'],False,preview,True,True,'',popup=True)
            self.assertIn('center,90%',calls[-1]);self.assertTrue(any(',55%' in arg for arg in calls[-1]))

    def test_menu_navigation_retains_live_snapshot_and_filters(self):
        import keys_cli
        stream=io.TextIOWrapper(io.BytesIO(b'zsh\0viins\0bindkey -M viins "^G" fixture-widget\n\0'))
        with patch.dict(os.environ,dict(self.env,DOTS_KEYS_CAPTURE='shell'),clear=True),patch('sys.stdin',stream),patch('sys.stdout',io.StringIO()), \
             patch('keys_cli.shutil.which',return_value='/fixture/fzf'),patch('keys_cli.picker_ui',side_effect=lambda ui:ui), \
             patch('keys_cli.choose_category',return_value='zsh') as choose,patch('keys_cli.browse') as browse, \
             patch('keys_cli.collect',wraps=keys_cli.collect) as collection:
            self.assertEqual(keys_cli.main(['--browse','--source','live','--mode','viins']),0)
            self.assertEqual(choose.call_count,1);collection.assert_called_once()
            self.assertEqual(choose.call_args.kwargs,dict(include_all=True))
            self.assertEqual(next(c['count'] for c in choose.call_args.args[1] if c['app']=='zsh'),1)
            self.assertEqual([r['action'] for r in browse.call_args.args[1]['rows']],['fixture-widget'])
        self.assertEqual(json.loads(self.cli('all','--json').stdout),json.loads(self.cli('--json').stdout))

    def test_category_cancellation_collects_once_without_browsing(self):
        import keys_cli
        from interaction import SelectionEnded
        data=dict(rows=[record('zsh','viins','^G','fixture')],coverage=[dict(app='zsh',count=1,notes=[])])
        with patch('keys_cli.shutil.which',return_value='/fixture/fzf'),patch('keys_cli.picker_ui',side_effect=lambda ui:ui), \
             patch('keys_cli.choose_category',side_effect=SelectionEnded(130)),patch('keys_cli.collect',return_value=data) as collect_mock, \
             patch('keys_cli.browse') as browse:
            self.assertRaises(SelectionEnded,keys_cli.main,['--browse'])
            collect_mock.assert_called_once();browse.assert_not_called()

    def test_fzf_installed_defaults_and_override(self):
        directory=self.base/'fzf';(directory/'bin').mkdir(parents=True);(directory/'man/man1').mkdir(parents=True)
        executable=directory/'bin/fzf';executable.write_text('fixture')
        manual=directory/'man/man1/fzf.1'
        manual.write_text('.TH fzf 1 "Oct" "fzf 1.0"\n    \\fBabort\\fR    \\fIctrl\\-g esc\\fR\n')
        with patch('keys.providers.shutil.which',return_value=str(executable)),patch('keys.providers.run',return_value='1.0'):
            notes=[];rows=fzf_defaults(notes)
        self.assertEqual(len(rows),2);self.assertTrue(all(r['default'] for r in rows))
        combined=merge([*rows,record('fzf','picker','ctrl-g','accept')])
        self.assertEqual(next(r['status'] for r in combined if r['action']=='abort' and r['key']=='ctrl-g'),'shadowed')

    def test_popup_presentation_respects_color_policy(self):
        from files.catalog import Presentation
        with patch.dict(os.environ,{'DOTS_COLOR':'auto','DOTS_ICONS':'auto','TERM':'xterm-256color'}):
            self.assertTrue(Presentation(stream=io.StringIO(),terminal=True).color)
            with patch.dict(os.environ,{'NO_COLOR':'1'}):
                self.assertFalse(Presentation(stream=io.StringIO(),terminal=True).color)
            self.assertFalse(Presentation(stream=io.StringIO()).color)
        self.assertNotIn('secret',record('yazi','mgr','x','shell curl secret')['action'])

    def test_source_parsing_is_read_only_and_no_fifo(self):
        from keys.providers import read_file
        before=set(self.base.rglob('*'))
        self.cli('yazi','--json');self.assertEqual(set(self.base.rglob('*')),before)
        if hasattr(os,'mkfifo'):
            p=self.base/'fifo';os.mkfifo(p);self.assertRaises(ValueError,read_file,p)

    def test_backspace_callback_is_idempotent(self):
        if not shutil.which('zsh'):self.skipTest('Zsh unavailable')
        block=(ROOT/'shells/zsh/keys.zsh').read_text()
        code='zvm_after_init_commands=(existing)\nzvm_after_select_vi_mode_commands=(existing)\nzvm_after_lazy_keybindings_commands=(existing)\n'+block+'\n'+block+'''
[[ ${#zvm_after_init_commands} == 2 && ${#zvm_after_select_vi_mode_commands} == 2 && ${#zvm_after_lazy_keybindings_commands} == 2 ]] || exit 7
_dots_zsh_keys_apply
bindkey -M viins '^H'
bindkey -M viins '^?'
'''
        p=subprocess.run([shutil.which('zsh'),'-dfc',code],env=self.env,capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(p.stdout.count('backward-delete-char'),2)

    def test_nvim_live_buffer_override(self):
        nvim=NVIM
        if not nvim:self.skipTest('Neovim unavailable')
        output=self.base/'maps.json';script=self.base/'probe.lua'
        module=str(ROOT/'config/nvim/lua/util/dots_keys.lua')
        script.write_text('local m=dofile('+json.dumps(module)+')\nvim.keymap.set("n", "<F8>", "global", {desc="Global action"})\nvim.keymap.set("n", "<F8>", function() end, {buffer=0,desc="Buffer action"})\nvim.fn.writefile({vim.json.encode(m.snapshot())}, '+json.dumps(str(output))+')\n')
        p=subprocess.run([nvim,'--headless','-u','NONE','-i','NONE','-n','-c','luafile '+str(script),'-c','qa!'],env=self.env,capture_output=True,text=True,timeout=15)
        self.assertEqual(p.returncode,0,p.stderr)
        data=json.loads(output.read_text());rows=[r for r in data['rows'] if r['key']=='<F8>' and r['mode']=='n']
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['description'],'Buffer action');self.assertEqual(rows[0]['action'],'Lua callback')


if __name__=='__main__':unittest.main()

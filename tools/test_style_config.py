#!/usr/bin/env python3
"""Visual preference contracts, exclusively in owned configuration roots."""
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tomllib
import unittest
from unittest.mock import patch

import test_profile_config as fixtures
ROOT = fixtures.ROOT
from style_config import Styles, current, nested
from theme_styles import snapshot, tokens, write
from files.catalog import Catalog, Presentation
from profile_config import context
from transactions import Store


class StyleConfig(unittest.TestCase):
    run_config = fixtures.ProfileConfig.run_config

    def setUp(self):
        fixtures.ProfileConfig.setUp(self)
        shutil.copytree(ROOT/'default', self.root/'default')
        shutil.copytree(ROOT/'config/gitmux', self.root/'config/gitmux')
        current.cache_clear()
        self.addCleanup(current.cache_clear)

    def test_cli_inheritance_defaults_preview_and_undo(self):
        self.assertEqual(self.run_config('get','icons.git.branch').stdout,'\n')
        path=self.path.parent/'icons.toml'
        self.run_config('set','icons.git.branch','BR','--dry-run')
        self.assertFalse(path.exists())
        result=json.loads(self.run_config('set','icons.git.branch','BR','--json').stdout)
        self.assertEqual(self.run_config('get','icons.git.branch',native=True).stdout,'BR\n')
        self.assertEqual(self.run_config('get','icons.git.branch','--defaults').stdout,'\n')
        self.run_config('set','colors.ui.heading.bold','false')
        self.run_config('set','colors.apps.tmux.ui.heading.fg','#aabbcc')
        self.run_config('check',native=True)
        with patch.dict(os.environ,self.env,clear=True):
            store=Store(Path(self.env['XDG_STATE_HOME'])/'dots')
            ops,guards,catalogs=store.inverse(result['transaction'])
            store.apply('undo',ops,guards,retain=True,catalogs=catalogs)
        self.assertFalse(path.exists())
        self.run_config('set','icons.git.branch','D','--defaults')
        self.assertEqual(self.run_config('get','icons.git.branch').stdout,'D\n')
        self.run_config('set','icons.git.branch','P')
        self.run_config('unset','icons.git.branch')
        self.assertEqual(self.run_config('get','icons.git.branch').stdout,'D\n')

    def test_human_objects_json_scalars_and_safe_literals(self):
        self.run_config('set','files.dots',json.dumps([self.resource]),'--json-value')
        human=self.run_config('get','files.dots').stdout
        self.assertIn('dots:app',human)
        self.assertIn('${CONFIG}/app',human)
        self.assertNotIn('"source":',human)
        data=json.loads(self.run_config('get','files.dots','--json',native=True).stdout)
        self.assertEqual(data['value'],[self.resource])
        literal="$(touch escaped); '#{pane_id}' \\\"[]$"
        self.run_config('set','icons.git.branch',literal)
        self.assertEqual(self.run_config('get','icons.git.branch').stdout,literal+'\n')
        self.run_config('set','icons.git.branch','',native=True)
        self.assertEqual(self.run_config('get','icons.git.branch').stdout,'\n')
        self.run_config('set','icons.git.branch','\x1b[31m',code=1)
        self.run_config('set','colors.ui.heading.fg','$(bad)',code=1)
        self.run_config('get','icons','--defaults','--profile',self.platform,code=2)
        self.assertFalse((self.home/'escaped').exists())
        with patch.dict(os.environ,self.env,clear=True):
            result=subprocess.run([shutil.which('bash'),'-c','source "$DOTS/lib/dots/ui.bash"; dots::settings; dots::icon git.branch fallback; printf "<%s>" "$REPLY"'],env=self.env,text=True,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(result.stdout,'<>')

    def test_profile_inventory_without_legacy_fallback(self):
        data=json.loads(self.path.read_text());data['files']['dots']=[self.resource]
        self.path.write_text(json.dumps(data));(self.root/'.dots/files.json').unlink()
        with patch.dict(os.environ,self.env,clear=True):
            self.assertEqual(len(Catalog(self.root,self.platform).records()),1)
            data['files']['dots']=[];self.path.write_text(json.dumps(data))
            self.assertEqual(Catalog(self.root,self.platform).records(),[])
            del data['files']['dots'];self.path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'files.dots'):Catalog(self.root,self.platform)

    def test_parent_inheritance_and_generated_native_literals(self):
        parent=self.root/'profiles/linux'
        child=parent/'distros/example';child.mkdir(parents=True)
        (child/'profile.json').write_text(json.dumps(dict(schema=1,id='linux/example',extends=['linux'])))
        (parent/'icons.toml').write_text('[git]\nbranch="parent"\n')
        glyph='"\\$[]#{pane_id};'
        (child/'icons.toml').write_text('[git]\nbranch='+json.dumps(glyph)+'\n')
        palette={key:'#abcdef' for key in ['foreground','background','blue','cyan','magenta','muted','bright_foreground','selection_background','info','green','warning','error','accent']}
        with patch.dict(os.environ,dict(self.env,DOTS_PROFILE='linux/example'),clear=True):
            selected=context(self.root,'linux/example')
            style=Styles(self.root,selected,palette=palette)
            self.assertEqual(style.icon('git.branch'),glyph)
            self.assertEqual(Styles(self.root,context(self.root,'linux')).icon('git.branch'),'parent')
            self.addCleanup(patch.stopall)
            patch('style_config.context',return_value=selected).start()
            values=tokens(palette,self.root)
            parsed=tomllib.loads(values['file_icons_yazi'])
            self.assertIn('conds',parsed['icon'])
            self.assertIn('##{pane_id}',values['tmux_icon_git_branch'])
            out=self.home/'rendered';out.mkdir()
            doc=write(out,palette,self.root)
            self.assertEqual(json.loads((out/'preferences.json').read_text())['icons']['git.branch'],glyph)
            sys.path.insert(0,str(ROOT/'lib/dots/themes'))
            from starship import update_symbols
            original=b'palette="dots"\n[git_branch]\nsymbol="old" # preserved\nformat="$symbol"\n[git_status]\nahead="x"\n'
            changed=update_symbols(original,doc)
            self.assertIn(b'# preserved',changed)
            self.assertEqual(tomllib.loads(changed.decode())['git_branch']['symbol'],glyph)
            self.assertEqual(update_symbols(changed,doc),changed)
            self.assertEqual(tomllib.loads(changed.decode())['git_branch']['format'],'$symbol')

    def test_bash_python_preferences_and_narrow_reports(self):
        self.run_config('set','colors.ui.heading.fg','#123456')
        self.run_config('set','icons.files.python','PY')
        self.run_config('set','files.dots',json.dumps([self.resource]),'--json-value')
        with patch.dict(os.environ,dict(self.env,DOTS_COLOR='always',DOTS_ICONS='always'),clear=True):
            current.cache_clear()
            stream=io.StringIO();ui=Presentation(stream);ui.heading('Heading')
            self.assertIn('38;2;18;52;86',stream.getvalue())
            self.assertEqual(ui.resources.describe(self.home/'a.py')[1],'PY')
        result=subprocess.run([shutil.which('bash'),'-c','source "$DOTS/lib/dots/ui.bash"; dots::heading Heading'],env=dict(self.env,DOTS_COLOR='always'),text=True,capture_output=True)
        self.assertIn('38;2;18;52;86',result.stdout)
        for width in (40,80,120):
            result=self.run_config('get','files.dots',COLUMNS=str(width),DOTS_COLOR='always',DOTS_ICONS='always')
            for line in re.sub(r'\x1b\[[0-9;]*m','',result.stdout).splitlines():
                from resources import cells
                self.assertLessEqual(cells(line),width,line)

    @unittest.skipIf(os.name == 'nt', 'POSIX terminal fixture')
    def test_actual_terminal_widths_and_completion(self):
        import fcntl
        import pty
        import struct
        import termios
        self.run_config('set','files.dots',json.dumps([self.resource]),'--json-value')
        from resources import cells
        for width in (40,80,120):
            master, slave = pty.openpty()
            try:
                fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',30,width,0,0))
                process=subprocess.Popen([shutil.which('bash'),str(self.root/'bin/dots'),'config','get','files.dots'],
                    env=dict(self.env,TERM='xterm-256color',DOTS_COLOR='auto',DOTS_ICONS='auto'),stdout=slave,stderr=slave)
                os.close(slave);slave=-1
                output=b''
                while True:
                    try: chunk=os.read(master,65536)
                    except OSError: break
                    if not chunk:break
                    output+=chunk
                self.assertEqual(process.wait(timeout=10),0,output)
                text=output.decode();self.assertIn('\x1b[',text)
                for line in re.sub(r'\x1b\[[0-9;]*m','',text).splitlines(): self.assertLessEqual(cells(line),width,line)
            finally:
                os.close(master)
                if slave>=0:os.close(slave)
        keys=subprocess.check_output([sys.executable,'-B',str(self.root/'lib/dots/profile_config.py'),'__keys'],env=self.env,text=True)
        self.assertIn('icons.apps.tmux.git.branch\n',keys)
        self.assertIn('colors.ui.heading.fg\n',keys)

    def test_shell_preference_change_invalidates_warm_bundle(self):
        import test_profiles
        fixture=test_profiles.Profiles();fixture.setUp();self.addCleanup(fixture.doCleanups)
        fixture.public()
        shutil.copytree(ROOT/'default',fixture.root/'default')
        for shell in ('bash','zsh'):
            if not shutil.which(shell):continue
            code='source "$DOTS/lib/dots/shell/init.'+shell+'"; printf "%s" "${_DOTS_STYLE_ICONS[git.branch]}"'
            cold=fixture.run_shell(shell,code)
            self.assertEqual(cold.returncode,0,cold.stderr)
            self.assertEqual(cold.stdout,'')
            path=fixture.root/'default/icons.toml'
            original=path.read_text();path.write_text(original.replace('branch = ""','branch = "B"'))
            changed=fixture.run_shell(shell,code)
            self.assertEqual(changed.stdout,'B',changed.stderr)
            commands=fixture.home/('shims-'+shell);commands.mkdir()
            shim=commands/'python3';shim.write_text('#!'+shutil.which('sh')+'\nprintf UNEXPECTED_PYTHON >&2\nexit 99\n');shim.chmod(0o700)
            warm=fixture.run_shell(shell,code,PATH=str(commands)+os.pathsep+fixture.env['PATH'])
            self.assertEqual(warm.returncode,0,warm.stderr);self.assertEqual(warm.stdout,'B')
            self.assertNotIn('UNEXPECTED_PYTHON',warm.stderr)
            path.write_text(original)


if __name__=='__main__': unittest.main()

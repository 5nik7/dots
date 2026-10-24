#!/usr/bin/env python3
"""Leaf templates, two-artifact publication and real syntax loading in owned roots."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import tomllib
import unittest
from unittest.mock import patch

import test_themes as fixture
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib/dots/themes'))
from palette_native import Themes
from app_paths import leaf_config_directory, config_directory
import theme_cli
from transactions import Store

LEAF = os.environ.get('LEAF_TEST_BIN')
if LEAF:
    LEAF = str(Path(LEAF).resolve())


def colored_text(raw):
    """Project ANSI foreground onto characters, so fallback cannot pass on gutters."""
    fg = None; chars = []; colors = []; end = 0
    for match in re.finditer(r'\x1b\[([0-9;]*)m', raw):
        text = raw[end:match.start()]; chars.extend(text); colors.extend([fg] * len(text))
        values = [int(v) if v else 0 for v in match[1].split(';')]
        i = 0
        while i < len(values):
            if values[i] in (0, 39): fg = None
            if values[i:i+2] == [38, 2] and i+4 < len(values):
                fg = tuple(values[i+2:i+5]); i += 4
            elif values[i:i+2] == [48, 2]: i += 4
            i += 1
        end = match.end()
    chars.extend(raw[end:]); colors.extend([fg]*len(raw[end:]))
    return ''.join(chars), colors


class LeafTheme(unittest.TestCase):
    setUp = fixture.Themes.setUp
    run_command = fixture.Themes.run_command
    dots = fixture.Themes.dots
    engine = fixture.Themes.engine
    shell = fixture.Themes.shell
    generation = fixture.Themes.generation
    wal_export = fixture.Themes.wal_export

    def render(self, identity):
        out = self.root / ('render-' + identity); out.mkdir(exist_ok=True)
        self.env.update(RENDER_THEME=identity, RENDER_OUTPUT=str(out))
        self.engine('dt_load "$RENDER_THEME" && dt_render "$RENDER_OUTPUT"')
        return out

    def test_all_palettes_and_native_renderer(self):
        self.wal_export()
        (self.home/'cache/wal/colors.json').write_text(json.dumps({
            'special':{'background':'#102030','foreground':'#eeeeee','cursor':'#abcdef'},
            'colors':{f'color{i}': f'#{i+32:02x}{i+48:02x}{i+64:02x}' for i in range(16)}}))
        reference = tomllib.loads((ROOT/'config/leaf/themes/catppuccin-mocha.toml').read_text())
        for identity in self.dots('theme','list').stdout.splitlines():
            with self.subTest(theme=identity):
                out=self.render(identity); raw=(out/'leaf.toml').read_text(); doc=tomllib.loads(raw)
                self.assertNotIn('{{',raw)
                palette=json.loads((out/'palette.json').read_text()) if (out/'palette.json').exists() else json.loads(self.engine('dt_load "$RENDER_THEME" && dt_json').stdout)
                colors=json.loads((out/'colors.json').read_text())['colors']
                for section in ('ui','markdown'):
                    self.assertEqual(set(doc[section]),set(reference[section]))
                    for value in doc[section].values():self.assertRegex(value,r'^#[0-9a-fA-F]{6}$')
                self.assertEqual(doc['syntax'],'dots.tmTheme')
                self.assertEqual(doc['base'],'arctic' if palette['mode']=='light' else 'ocean')
                self.assertEqual(doc['ui']['content_bg'],colors['background'])
                self.assertEqual(doc['markdown']['text'],colors['foreground'])
                self.assertEqual(doc['ui']['status_brand_fg'],colors['foreground' if palette['mode']=='light' else 'background'])
                native=self.root/('native-'+identity);native.mkdir()
                with patch.dict(os.environ,self.env,clear=True):Themes().render(identity,native)
                self.assertEqual(tomllib.loads((native/'leaf.toml').read_text()),doc)

    def test_destinations_and_validation(self):
        with patch.dict(os.environ,self.env,clear=True):
            self.assertEqual(leaf_config_directory(),self.home/'config/leaf')
            self.assertIsNone(leaf_config_directory(windows=True))
            with patch.dict(os.environ,APPDATA=str(self.home/'Roaming')):
                self.assertEqual(config_directory('leaf'),self.home/'Roaming/leaf')
            with patch.dict(os.environ,DOTS_APP_LEAF_CONFIG=str(self.home/'-leaf ü')):
                self.assertEqual(leaf_config_directory(),self.home/'-leaf ü')
            for value in ('relative',str(self.home)+'/../escape',str(self.home)+'/./leaf',str(self.home)+'\nleaf'):
                with patch.dict(os.environ,DOTS_APP_LEAF_CONFIG=value),self.assertRaises(ValueError):leaf_config_directory()
        self.dots('theme','set','nord',env=dict(self.env,DOTS_APP_LEAF_CONFIG='relative'),code=1)
        self.assertFalse((self.home/'state/dots/current/theme').exists())

    def test_two_connectors_parent_backup_idempotence_and_restore(self):
        base=self.home/'config/leaf';base.mkdir(parents=True)
        target=base/'themes/dots.toml';syntax=base/'themes/dots.tmTheme'
        self.dots('theme','set','nord','--dry-run');self.assertFalse(target.parent.exists())
        self.dots('theme','set','nord');first=self.generation()
        self.assertEqual(target.resolve(),first/'leaf.toml');self.assertEqual(syntax.resolve(),first/'bat.tmTheme')
        before=[p.lstat().st_mtime_ns for p in (target,syntax)]
        self.dots('theme','refresh');self.assertEqual(first,self.generation())
        self.assertEqual(before,[p.lstat().st_mtime_ns for p in (target,syntax)])
        self.engine('dt_restore "'+str(first)+'"');self.assertFalse(target.parent.exists())
        target.parent.mkdir();target.write_text('original');syntax.symlink_to(base/'missing')
        self.dots('theme','set','nord');self.engine('dt_restore "'+str(self.generation())+'"')
        self.assertEqual(target.read_text(),'original');self.assertEqual(syntax.readlink(),base/'missing')

    def test_interruption_and_drift(self):
        base=self.home/'config/leaf';base.mkdir(parents=True)
        self.engine('''dt_record() {
 if [[ $2 == committed ]]; then kill -KILL "$BASHPID"; fi
 printf '%s\\n' "$2" > "$1/status"; sync -f "$1/status"
}
dt_set catppuccin mocha''',code=137)
        self.dots('theme','set','nord')
        target=base/'themes/dots.tmTheme';target.unlink();target.write_text('user edit')
        self.engine('dt_restore "'+str(self.generation())+'"',code=1)
        self.assertEqual(target.read_text(),'user edit')

    def test_overrides_optional_app_and_missing_consumers(self):
        self.dots('theme','set','nord');self.assertFalse((self.home/'config/leaf').exists())
        personal=self.home/'config/dots/themed/leaf.toml.tpl';personal.parent.mkdir(parents=True)
        personal.write_text('base = "{{ leaf_base }}"\n')
        self.dots('theme','refresh');first=self.generation()
        self.assertEqual((first/'leaf.toml').read_text(),'base = "ocean"\n')
        personal.write_text('base = "arctic"\n');self.dots('theme','refresh');self.assertNotEqual(first,self.generation())
        bundled=self.repo/'themes/nord/leaf.toml';bundled.write_text('base = "forest"\n')
        self.dots('theme','refresh');self.assertEqual((self.generation()/'leaf.toml').read_bytes(),bundled.read_bytes())
        with patch.dict(os.environ,self.env,clear=True):
            native=self.root/'native';native.mkdir();themes=Themes();themes.render('nord',native)
            self.assertEqual((native/'leaf.toml').read_bytes(),bundled.read_bytes())
            before=themes.fingerprint('nord');bundled.write_text('base = "ocean"\n')
            self.assertNotEqual(before,themes.fingerprint('nord'))
        bundled.unlink();personal.unlink()
        tools=self.root/'minimal-bin';tools.mkdir()
        for command in ('bash','python3','cp','mkdir','cat','uname','readlink','sha256sum','sort'):
            (tools/command).symlink_to(shutil.which(command))
        self.env['PATH']=str(tools);out=self.render('nord')
        self.assertNotIn('{{',(out/'leaf.toml').read_text())

    def test_native_transaction_failure_and_undo(self):
        base=self.home/'config/leaf';base.mkdir(parents=True)
        syntax=base/'themes/dots.tmTheme'
        with patch.dict(os.environ,self.env,clear=True),patch.object(theme_cli,'reload_apps'):
            themes=Themes();theme_cli.publication(themes,'nord',dry=True);self.assertFalse(syntax.parent.exists())
            save=Store.save;injected=[]
            def fail(store,doc):
                save(store,doc)
                if syntax.is_symlink() and doc['status']=='applying' and not injected:
                    injected.append(True);raise OSError('fixture interruption after syntax connector')
            with patch.object(Store,'save',fail),self.assertRaises(OSError):theme_cli.publication(themes,'nord')
            self.assertFalse(syntax.parent.exists())
            first=theme_cli.publication(themes,'nord');self.assertEqual(theme_cli.publication(themes,'nord'),first)
            store=Store(themes.state);record=next(r for r in store.records() if r['status']=='complete')
            operations,guards,_=store.inverse(record['id']);store.apply('test-undo',operations,guards,retain=True)
            self.assertFalse(syntax.is_symlink())

    def test_native_owned_directory_link(self):
        source=self.repo/'config/leaf';source.mkdir(parents=True)
        base=self.home/'config/leaf';base.parent.mkdir(parents=True);base.symlink_to(source,target_is_directory=True)
        catalog=self.repo/'.dots';catalog.mkdir()
        platforms=['termux','linux','wsl','windows']
        (catalog/'sources.json').write_text(json.dumps(dict(schema=1,sources=[dict(id='dots',path='.',roots=['config'],platforms=platforms)])))
        (catalog/'files.json').write_text(json.dumps(dict(schema=1,repository='dots',resources=[dict(id='leaf',app='leaf',category='config',source='config/leaf',target='${CONFIG}/leaf',strategy='directory-link',platforms=platforms)])))
        with patch.dict(os.environ,self.env,clear=True),patch.object(theme_cli,'reload_apps'):
            themes=Themes();theme_cli.publication(themes,'nord')
            self.assertTrue((source/'themes/dots.toml').is_symlink())
            self.assertTrue((source/'themes/dots.tmTheme').is_symlink())
            self.assertTrue(base.is_symlink())
            # An unowned config-root link is refused before publication.
            doc=json.loads((catalog/'files.json').read_text());doc['resources']=[]
            (catalog/'files.json').write_text(json.dumps(doc))
            with self.assertRaisesRegex(ValueError,'unmanaged application directory link'):
                theme_cli.publication(Themes(),'catppuccin-latte')

    @unittest.skipUnless(LEAF,'set LEAF_TEST_BIN to the patched Leaf executable')
    def test_real_inline_syntax_colors_and_failures(self):
        base=self.home/'config/leaf';base.mkdir(parents=True)
        (base/'config.toml').write_text('theme = "themes/dots.toml"\n')
        sample='# Header\n\n```python\ndef greet(name):\n    # sentinel_comment\n    return "sentinel_string"\n```\n'
        for identity in ('catppuccin-mocha','catppuccin-latte'):
            self.dots('theme','set',identity)
            colors=json.loads((self.generation()/'colors.json').read_text())['colors']
            result=subprocess.run([LEAF,'--inline','ansi:80'],input=sample,env=self.env,cwd=self.home,capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(result.stderr,'')
            plain,fg=colored_text(result.stdout)
            for word,role in (('sentinel_comment','muted'),('sentinel_string','bright_green')):
                start=plain.index(word);value=colors[role];rgb=tuple(int(value[i:i+2],16) for i in (1,3,5))
                self.assertEqual(set(fg[start:start+len(word)]),{rgb},(word,identity,result.stdout))
        # Owned fixture: replace only the syntax connector, not its generated target.
        syntax=base/'themes/dots.tmTheme';syntax.unlink();syntax.write_text('bad plist')
        for args in (['--inline','ansi:80'],[]):
            result=subprocess.run([LEAF,*args],input=sample,env=self.env,cwd=self.home,capture_output=True,text=True,timeout=15)
            self.assertNotEqual(result.returncode,0);self.assertIn('Cannot load syntax theme file',result.stderr)
        syntax.unlink()
        result=subprocess.run([LEAF,'--inline','ansi:80'],input=sample,env=self.env,cwd=self.home,capture_output=True,text=True,timeout=15)
        self.assertNotEqual(result.returncode,0)
        # Explicit built-ins bypass the unusable configured custom syntax.
        for args,env in ((['--theme','ocean'],self.env),([],dict(self.env,LEAF_THEME='ocean'))):
            result=subprocess.run([LEAF,*args,'--inline','ansi:80'],input=sample,env=env,cwd=self.home,capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)

        # Embedded names use the config directory even when CLI/env names are padded.
        syntax.symlink_to(self.home/'state/dots/current/theme/bat.tmTheme')
        (base/'config.toml').write_text('theme = "ocean"\n[themes.named]\nsyntax = "themes/dots.tmTheme"\n')
        for args,env in ((['--theme',' named '],self.env),([],dict(self.env,LEAF_THEME=' named '))):
            result=subprocess.run([LEAF,*args,'--inline','ansi:80'],input=sample,env=env,cwd=self.home,capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)
            plain,fg=colored_text(result.stdout);start=plain.index('sentinel_string')
            value=colors['bright_green'];expected=tuple(int(value[i:i+2],16) for i in (1,3,5))
            self.assertEqual(set(fg[start:start+len('sentinel_string')]),{expected})

    @unittest.skipUnless(LEAF and os.name!='nt','patched Leaf and POSIX PTY required')
    def test_real_dark_light_tui(self):
        import fcntl,pty,select,signal,struct,termios
        base=self.home/'config/leaf';base.mkdir(parents=True)
        (base/'config.toml').write_text('theme = "themes/dots.toml"\nwatch = true\n')
        sample=self.home/'fixture.md'
        sample_source='# Leaf fixture\n\n```python\n# sentinel_comment\nvalue = "sentinel_string"\n```\n'
        for identity in ('catppuccin-mocha','catppuccin-latte'):
            self.dots('theme','set',identity)
            doc=tomllib.loads((self.generation()/'leaf.toml').read_text())
            for width in (40,80,120):
                with self.subTest(theme=identity,width=width):
                    sample.write_text(sample_source)
                    master,slave=pty.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',28,width,0,0))
                    process=subprocess.Popen([LEAF,str(sample)],stdin=slave,stdout=slave,stderr=slave,env=self.env,cwd=self.home,start_new_session=True)
                    os.close(slave);data=bytearray()
                    def collect(seconds):
                        end=time.monotonic()+seconds
                        while time.monotonic()<end:
                            if select.select([master],[],[],.05)[0]:
                                try:chunk=os.read(master,65536)
                                except OSError:break
                                if not chunk:break
                                data.extend(chunk)
                                # Crossterm cursor-position probe.
                                if b'\x1b[6n' in chunk:os.write(master,b'\x1b[1;1R')
                    try:
                        collect(1.5);os.write(master,b'T');collect(.25)
                        os.write(master,b'\x1b[B');collect(.25);os.write(master,b'\x1b');collect(.25)
                        fcntl.ioctl(master,termios.TIOCSWINSZ,struct.pack('HHHH',30,width,0,0))
                        os.kill(process.pid,signal.SIGWINCH);collect(.25)
                        sample.write_text(sample_source.replace('sentinel_string','reload_string'))
                        os.write(master,b'r');collect(.5)
                        # A width change forces complete cell output for color assertions.
                        fcntl.ioctl(master,termios.TIOCSWINSZ,struct.pack('HHHH',30,width+1,0,0))
                        os.kill(process.pid,signal.SIGWINCH);collect(.3)
                        os.write(master,b'q');collect(.25);process.wait(timeout=5)
                        self.assertEqual(process.returncode,0)
                        output=data.decode(errors='replace')
                        bg=doc['ui']['content_bg'];rgb=';'.join(str(int(bg[i:i+2],16)) for i in (1,3,5))
                        self.assertIn('48;2;'+rgb,output)
                        self.assertIn('sentinel_string',output)
                        plain,fg=colored_text(output);start=plain.rindex('reload_string')
                        value=json.loads((self.generation()/'colors.json').read_text())['colors']['bright_green']
                        expected=tuple(int(value[i:i+2],16) for i in (1,3,5))
                        self.assertEqual(set(fg[start:start+len('reload_string')]),{expected})
                        self.assertNotIn('Cannot load syntax',output)
                    finally:
                        if process.poll() is None:process.kill();process.wait(timeout=5)
                        os.close(master)

if __name__=='__main__':unittest.main()

#!/usr/bin/env python3
"""Directory previews, bounded highlighting and read-only consumer evidence."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_theme_files as fixture
from test_theme_files import subject, ROOT
import consumer_checks as checks
import file_preview as preview


class Terminal(io.StringIO):
    def isatty(self): return True


class Views(unittest.TestCase):
    setUp = fixture.ThemeFiles.setUp
    command = fixture.ThemeFiles.command
    doc = fixture.ThemeFiles.doc
    row = fixture.ThemeFiles.row

    def observed(self, app=None, fail=False):
        inspect = subject.Inspection()
        return checks.annotate(inspect, inspect.inventory(app), subject.bounded, fail, app)

    def evidence(self, app, artifact, connection=False):
        inspect=subject.Inspection();inspect.inventory()
        return checks.Verifier(inspect,subject.bounded).verify(app,artifact,connection)

    def test_directories_empty_links_truncation_and_raw(self):
        cache=self.generation/'bat-cache';cache.mkdir()
        self.assertIn(b'Empty directory',self.command('show','bat-cache').stdout)
        (cache/'themes.bin').write_bytes(b'\x00binary')
        (cache/'nested').mkdir()
        (cache/'outside').symlink_to(self.home/'absent')
        (cache/'line\ncontrol').write_text('do not read')
        output=self.command('show','bat-cache').stdout
        self.assertIn(b'themes.bin  file',output);self.assertIn(b'nested/  dir',output)
        self.assertIn(b'outside  symlink ->',output);self.assertIn(b'line\\ncontrol',output)
        self.assertNotIn(b'binary',output)
        self.assertIn(b'No editable source',self.command('show','bat-cache','--source').stdout)
        self.command('show','bat-cache','--raw',code=1)
        for i in range(210):(cache/str(i)).touch()
        self.assertIn(b'truncated at 200',self.command('show','bat-cache').stdout)
        shutil.rmtree(cache);cache.symlink_to(self.home,target_is_directory=True)
        self.command('show','bat-cache',code=1)

    def test_directory_browser_actions(self):
        (self.generation/'bat-cache').mkdir()
        (self.generation/'bat-cache/test.bin').write_bytes(b'\0')
        class Select:
            count=0
            def pick(inner,kind,title,choices,initial=''):
                inner.count+=1
                if inner.count==1:return next(c for c in choices if c.endswith('bat-cache'))
                self.assertNotIn('Source contents',choices)
                return 'Directory contents' if inner.count==2 else 'Exit'
        output=Terminal()
        with contextlib.redirect_stdout(output):subject.browse(selector=Select())
        self.assertIn('test.bin',output.getvalue())

    def test_highlighter_bounds_failure_and_config_isolation(self):
        ui=subject.Presentation(Terminal());ui.color=True
        cache=self.generation/'bat-cache';cache.mkdir()
        for name in ('themes.bin','syntaxes.bin'):(cache/name).write_bytes(b'fixture')
        with patch.object(preview.shutil,'which',return_value='/fixture/bat'),patch.object(preview,'run_renderer',return_value=b'\x1b[32m<xml/>\x1b[0m\n') as run:
            with patch.dict(os.environ,BAT_CONFIG_PATH='untrusted',BAT_PAGER='bad',BAT_OPTS='bad'):
                preview.text_view(ui,b'<xml/>\n','bat.tmTheme.tpl',self.generation)
            argv,data,env=run.call_args.args
            self.assertIn('--language=XML',argv);self.assertIn('--paging=never',argv)
            self.assertEqual(env['BAT_CONFIG_PATH'],os.devnull);self.assertNotIn('BAT_PAGER',env);self.assertNotIn('BAT_OPTS',env)
            self.assertEqual(env['BAT_CACHE_PATH'],str(cache));self.assertEqual(data,b'<xml/>\n')
        for output in (None,b'\x1b]52;clipboard\x07',b'\xff'):
            ui.stream.seek(0);ui.stream.truncate()
            with patch.object(preview.shutil,'which',return_value='/fixture/bat'),patch.object(preview,'run_renderer',return_value=output):
                preview.text_view(ui,b'safe\x1b[31m\n','example.sh',self.generation)
            self.assertEqual(ui.stream.getvalue(),'safe\\x1b[31m\n')
        ui.color=False
        with patch.object(preview,'run_renderer',side_effect=AssertionError('renderer called')):
            preview.text_view(ui,b'plain','example.json',self.generation)
        ui.color=True
        with patch.object(preview.shutil,'which',return_value=None):
            self.assertIsNone(preview.highlight(ui,b'text','a',self.generation))
        self.assertIsNone(preview.run_renderer([sys.executable,'-c','import time;time.sleep(2)'],b'',dict(os.environ),timeout=.05))
        self.assertIsNone(preview.run_renderer([sys.executable,'-c','import sys;sys.stdout.write("x"*100000)'],b'',dict(os.environ),limit=100))
        self.assertIsNone(preview.run_renderer([sys.executable,'-c','raise SystemExit(1)'],b'',dict(os.environ)))

    def test_bat_environment_current_different_and_previous(self):
        (self.generation/'bat-cache').mkdir()
        with patch.dict(os.environ,BAT_THEME='Dots',BAT_CACHE_PATH=str(self.active/'bat-cache')):
            self.assertEqual(self.evidence('bat','bat-cache')['status'],'matches')
            with patch.dict(os.environ,BAT_THEME='Other'):
                self.assertEqual(self.evidence('bat','bat-cache')['status'],'different')
        old=self.generation.with_name('g.old');(old/'bat-cache').mkdir(parents=True)
        (self.generation/'previous').write_text('g.old\n')
        with patch.dict(os.environ,BAT_THEME='Dots',BAT_CACHE_PATH=str(old/'bat-cache')):
            self.assertEqual(self.evidence('bat','bat.tmTheme')['status'],'stale')
        (self.generation/'previous').unlink()
        with patch.dict(os.environ,BAT_THEME='Dots',BAT_CACHE_PATH=str(old/'bat-cache')):
            self.assertEqual(self.evidence('bat','bat.tmTheme')['status'],'different')
        self.assertEqual(self.evidence('bat','bat.tmTheme')['status'],'unknown')

    def test_fzf_gum_and_ls_colors_no_evaluation_or_disclosure(self):
        (self.generation/'fzf.sh').write_text('export _FZF_COLORS_="fg:#abcdef,bg:#123456"\n')
        (self.generation/'gum_env.sh').write_text("export GUM_INPUT_PROMPT_FOREGROUND='#abcdef'\nexport FOREGROUND='#eeeeee'\n")
        (self.generation/'ls_colors').write_text('di=34:fi=32\n')
        with patch.dict(os.environ,FZF_DEFAULT_OPTS='--preview "$(touch secret)" --color=fg:#000000 --color fg:#abcdef,bg:#123456',
                        GUM_INPUT_PROMPT_FOREGROUND='#abcdef',FOREGROUND='#eeeeee',LS_COLORS='di=34:fi=32'):
            for app,name in (('fzf','fzf.sh'),('gum','gum_env.sh'),('shell','ls_colors')):
                self.assertEqual(self.evidence(app,name)['status'],'matches')
            with patch.dict(os.environ,FZF_DEFAULT_OPTS='--color=fg:#abcdef,bg:#123456 --color=fg:#ffffff'):
                self.assertEqual(self.evidence('fzf','fzf.sh')['status'],'different')
            with patch.dict(os.environ,FZF_DEFAULT_OPTS_FILE='/unknown'):
                self.assertEqual(self.evidence('fzf','fzf.sh')['status'],'unknown')
            with patch.dict(os.environ,FOREGROUND='private-secret'):
                ev=self.evidence('gum','gum_env.sh')
                self.assertEqual(ev['status'],'different');self.assertNotIn('private-secret',json.dumps(ev))
        self.assertFalse((self.home/'secret').exists())

    def write_config(self, app, text):
        base=self.config/app;base.mkdir(exist_ok=True)
        suffix={'kitty':'kitty.conf','tmux':'tmux.conf','yazi':'theme.toml','btop':'btop.conf'}.get(app,'config.toml')
        path=base/suffix;path.write_text(text)
        return path

    def test_toml_selections_and_literal_includes(self):
        specs=[('television','[ui]\ntheme="dots"\n','television.toml'),
               ('leaf','theme="themes/dots.toml"\n','leaf.toml'),
               ('yazi','[flavor]\ndark="dots"\nlight="dots"\n','yazi/flavor.toml'),
               ('btop','color_theme = "dots"\n','btop.theme'),
               ('kitty','include dots-theme.conf\n','kitty.conf'),
               ('tmux','set -g ignored "multiline\nignored"\nsource-file -q -F "#{d:current_file}/dots-theme.conf"\n','tmux.conf')]
        for app,text,name in specs:
            with self.subTest(app=app):
                p=self.write_config(app,text)
                ev=self.evidence(app,name,True)
                self.assertEqual(ev['status'],'configured',ev)
                if app in ('television','leaf','btop','yazi'):
                    p.write_text(text.replace('dots','different'))
                    self.assertEqual(self.evidence(app,name,True)['status'],'different')
                else:
                    p.write_text('include $CONFIG/theme\n' if app=='kitty' else 'source-file "$CONFIG/theme"\n')
                    self.assertEqual(self.evidence(app,name,True)['status'],'unknown')
        self.write_config('television','[ui]\ntheme="dots"\ntheme="other"\n')
        self.assertEqual(self.evidence('television','television.toml',True)['status'],'unknown')
        self.write_config('yazi','[flavor]\ndark="dots"\nlight="other"\n')
        self.assertEqual(self.evidence('yazi','yazi/flavor.toml',True)['status'],'unknown')
        self.assertEqual(self.evidence('yazi','colors.json')['status'],'unknown')

    def enable(self, name):
        p=self.config/'dots/theme-plugins.json';p.parent.mkdir(exist_ok=True)
        p.write_text(json.dumps(dict(schema=1,enabled={name:'bundled/10-'+name+'.sh'})))

    def test_plugin_content_receipts_and_disabled_automation(self):
        from plugin_apps import GTK_BLOCK,qt_registration
        for app in ('gtk','qt6ct'):
            generated=self.generation/('gtk.css' if app=='gtk' else 'qt6ct.conf');generated.write_text('fixture colors\n')
            target=self.config/('gtk-3.0/dots-theme.css' if app=='gtk' else 'qt6ct/colors/dots.conf')
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(generated.read_bytes())
            reg=self.config/('gtk-3.0/gtk.css' if app=='gtk' else 'qt6ct/qt6ct.conf')
            if app=='gtk':reg.write_text(GTK_BLOCK);registration={'block':GTK_BLOCK}
            else:
                data,registration=qt_registration(None,None,target);reg.write_bytes(data)
            receipt=self.state/'theme-plugins'/(app+'.json');receipt.parent.mkdir(exist_ok=True)
            receipt.write_text(json.dumps(dict(schema=1,plugin=app,generated=hashlib.sha256(target.read_bytes()).hexdigest(),registration=registration)))
            ev=self.evidence(app,generated.name);self.assertEqual(ev['status'],'matches');self.assertEqual(ev['automation'],'disabled')
            self.enable(app)
            ev=self.evidence(app,generated.name);self.assertEqual(ev['automation'],'enabled')
            if app == 'qt6ct':
                reg.write_text(reg.read_text().replace('custom_palette=', 'custom_palette = ').replace('color_scheme_path=', 'color_scheme_path = '))
                self.assertEqual(self.evidence(app,generated.name)['status'],'matches')
            target.write_text('changed')
            self.assertEqual(self.evidence(app,generated.name)['status'],'different')
            for invalid in ('{', '{}', '[]', 'null'):
                receipt.write_text(invalid)
                self.assertEqual(self.evidence(app,generated.name)['status'],'unknown')

    def test_starship_palette_preserves_extensions_and_links(self):
        generated='palette="dots"\n[palettes.dots]\nblue="#123456"\n'
        (self.generation/'blastoff.toml').write_text(generated)
        real=self.repo/'starship.toml';real.write_text(generated+'personal="#ffffff"\n')
        target=self.home/'.config/starship.toml';target.parent.mkdir();target.symlink_to(real)
        self.assertEqual(self.evidence('starship','blastoff.toml')['status'],'matches')
        self.assertEqual(self.evidence('starship','blastoff.toml')['automation'],'disabled')
        real.write_text(generated.replace('#123456','#111111'))
        self.assertEqual(self.evidence('starship','blastoff.toml')['status'],'different')
        real.write_text(generated.replace('palette="dots"','palette="other"'))
        self.assertEqual(self.evidence('starship','blastoff.toml')['status'],'different')

    def test_opt_in_check_flags_and_no_subprocess_or_writes(self):
        (self.generation/'ls_colors').write_text('di=34\n')
        before={str(p):p.lstat().st_mtime_ns for p in self.root.rglob('*')}
        with patch.dict(os.environ,LS_COLORS='di=31'):
            with patch.object(subprocess,'Popen',side_effect=AssertionError('verification subprocess')):
                default=self.observed('shell');explicit=self.observed('shell',True)
            self.assertTrue(default['healthy']);self.assertFalse(explicit['healthy'])
            self.command('check','--app','shell')
            self.command('check','--app','shell','--consumers',code=1)
            for frontend in ('bash','native'):
                self.command('check','--app','shell','--consumers','--json',frontend=frontend,code=1)
        self.assertEqual(before,{str(p):p.lstat().st_mtime_ns for p in self.root.rglob('*')})

    def test_evidence_read_is_bounded_and_detects_drift(self):
        path=self.write_config('television','[ui]\ntheme="dots"\n')
        inspect=subject.Inspection();inspect.inventory()
        def changed(p,limit):
            data=subject.bounded(p,limit)
            Path(p).write_text('[ui]\ntheme="other"\n')
            return data
        ev=checks.Verifier(inspect,changed).verify('television','television.toml',True)
        self.assertEqual(ev['status'],'unknown')
        path.write_text('x'*300000)
        self.assertEqual(self.evidence('television','television.toml',True)['status'],'unknown')

    def test_spaced_layout_groups_and_exact_raw(self):
        path=self.write_config('leaf','theme="themes/dots.toml"\n');(path.parent/'themes').mkdir()
        (path.parent/'themes/dots.toml').symlink_to(self.active/'leaf.toml')
        output=self.command('list','--app','leaf').stdout.decode()
        self.assertIn('\n\n  leaf.toml  available\n',output)
        self.assertNotIn('activation unverified',output);self.assertNotIn('    File ',output)
        data=b'{"code": "<tag>"}\r\n'
        (self.generation/'example.json').write_bytes(data)
        with patch.dict(os.environ,DOTS_COLOR='always'):
            self.assertEqual(self.command('show','example.json').stdout,data)
            self.assertEqual(self.command('show','example.json','--raw').stdout,data)


@unittest.skipUnless(shutil.which('bat') or shutil.which('batcat'),'bat unavailable')
class NativeHighlight(unittest.TestCase):
    def test_existing_published_cache_and_syntaxes(self):
        import test_themes as themes
        case=themes.Themes('test_routes_values_and_plain_output');case.setUp();self.addCleanup(case.doCleanups)
        case.dots('theme','set','nord')
        before={str(p):p.lstat().st_mtime_ns for p in case.home.rglob('*')}
        with patch.dict(os.environ,case.env,clear=True):
            stream=Terminal();ui=subject.Presentation(stream);ui.color=True
            for name,data in (('bat.tmTheme',b'<plist><dict><key>name</key><string>Dots</string></dict></plist>\n'),
                              ('pi.json',b'{"name":"Dots","value":42}\n'),('leaf.toml.tpl',b'name = "dots"\n'),
                              ('fzf.sh',b'export COLOR="blue"\n')):
                with self.subTest(name=name):
                    output=preview.highlight(ui,data,name,case.generation())
                    self.assertIsNotNone(output)
                    self.assertIn('\x1b[',output)
                    self.assertEqual(preview.SGR.sub('',output),data.decode())
            if os.name != 'nt':
                import pty
                # Exercise the real terminal branch through both command adapters.
                for command in ([shutil.which('bash'),str(ROOT/'bin/dots')],
                                [sys.executable,'-B',str(ROOT/'lib/dots/cli.py')]):
                    master,slave=pty.openpty()
                    try:
                        env=dict(os.environ,DOTS_COLOR='always',DOTS_ICONS='never',COLUMNS='500')
                        proc=subprocess.Popen([*command,'theme','files','show','pi.json'],env=env,
                                              stdout=slave,stderr=slave)
                        os.close(slave);slave=None
                        output=bytearray()
                        while True:
                            try:part=os.read(master,65536)
                            except OSError:break
                            if not part:break
                            output.extend(part)
                        self.assertEqual(proc.wait(timeout=10),0,output)
                        self.assertIn(b'\x1b[',output)
                        self.assertEqual(preview.SGR.sub('',output.decode()).replace('\r\n','\n'),
                                         (case.generation()/'pi.json').read_text())
                    finally:
                        os.close(master)
                        if slave is not None:os.close(slave)
            self.assertEqual(before,{str(p):p.lstat().st_mtime_ns for p in case.home.rglob('*')})
            # No inspector builds: removing the private cache falls back.
            shutil.rmtree(case.generation()/'bat-cache')
            self.assertIsNone(preview.highlight(ui,b'text','x',case.generation()))


if __name__=='__main__':unittest.main()

#!/usr/bin/env python3
"""Real native Tab insertion, with disposable shells and cached glyph data."""
import json
import os
from pathlib import Path
import select
import shutil
import signal
import time
import unittest
import test_config_alignment as fixtures

FZF_TAB=Path(os.environ.get('DOTS_TEST_FZF_TAB') or Path.home()/'.local/share/zinit/plugins/Aloxaf---fzf-tab')


class Completion(unittest.TestCase):
    setUp=fixtures.Alignment.setUp

    def capture(self,shell,text):
        import pty
        path=self.home/('buffer-'+shell)
        if path.exists():path.unlink()
        env=dict(self.env,CAPTURE=str(path),TERM='xterm-256color',PS1='START> ',fish_history='')
        commands={
            'bash':r'''source "$DOTS/lib/dots/completion/bash"; cap() { printf '%s' "$READLINE_LINE" > "$CAPTURE"; }; bind -x '"\C-g":cap'; PS1='READY> ' ''',
            'zsh':r'''autoload -Uz compinit; compinit -D; source "$DOTS/lib/dots/completion/zsh"; cap() { print -rn -- "$BUFFER" > "$CAPTURE"; }; zle -N cap; bindkey '^G' cap; PROMPT='READY> ' ''',
            'fish':r'''source "$DOTS/lib/dots/completion/fish"; function cap; commandline --current-buffer > "$CAPTURE"; end; bind \cg cap; function fish_prompt; printf 'READY> '; end''',
        }
        argv={'bash':['bash','--noprofile','--norc','-i'],'zsh':['zsh','-f'],'fish':['fish','--no-config','-i']}[shell]
        pid,fd=pty.fork()
        if pid==0:os.execve(shutil.which(shell),argv,env)
        def drain_until(predicate,seconds=15):
            output=b'';deadline=time.monotonic()+seconds
            while time.monotonic()<deadline:
                if select.select([fd],[],[],.1)[0]:
                    try:output+=os.read(fd,65536)
                    except OSError:break
                if predicate(output):return output
            self.fail('shell did not finish: '+repr(output[-1000:]))
        try:
            # Use a command to establish readiness on all three native shells.
            os.write(fd,(commands[shell]+'\n').encode())
            drain_until(lambda out:out.count(b'READY>')>=2)
            os.write(fd,text.encode());time.sleep(2)
            os.write(fd,b'\x07')
            drain_until(lambda _:path.exists())
            return path.read_text().rstrip('\n')
        finally:
            try:os.kill(pid,signal.SIGKILL)
            except ProcessLookupError:pass
            os.close(fd);os.waitpid(pid,0)

    def test_branch_and_leaf_native_tab(self):
        for shell in ('bash','zsh','fish'):
            if not shutil.which(shell):continue
            with self.subTest(shell=shell):
                branch=self.capture(shell,'dots config set formatting.apps.fonts..\t')
                self.assertEqual(branch,'dots config set formatting.apps.fonts.preview.')
                leaf=self.capture(shell,'dots config set formatting.apps.menu.popup.bor\t')
                self.assertEqual(leaf,'dots config set formatting.apps.menu.popup.border ')

    def test_cached_glyph_search_inserts_only_the_glyph(self):
        cache=Path(self.env['XDG_CACHE_HOME'])/'dots/fonts/catalog.json';cache.parent.mkdir(parents=True)
        cache.write_text(json.dumps(dict(schema=1,families={},glyph_version='fixture',glyphs={'fixture':[
            dict(name='fixture-battery',glyph='\ue000',codepoint='U+E000',collection='test')]})))
        for shell in ('bash','zsh','fish'):
            if not shutil.which(shell):continue
            with self.subTest(shell=shell):
                text=self.capture(shell,'dots config set icons.git.branch fixture-batt\t')
                self.assertEqual(text,'dots config set icons.git.branch \ue000 ')
        self.assertFalse((Path(self.env['XDG_STATE_HOME'])/'dots/fonts/collection.json').exists())

    def test_full_keys_and_allowed_values_native_tab(self):
        for shell in ('bash','zsh','fish'):
            if not shutil.which(shell):continue
            for typed,expected in (
                    ('dots config set DOTS_INIT_COMPLETION\t','dots config set DOTS_INIT_COMPLETION '),
                    ('dots config set profile..\t','dots config set profile.alias '),
                    ('dots config set DOTS_COLOR nev\t','dots config set DOTS_COLOR never '),
                    ('dots config set colors.apps.todo.field.alias.value.bold tru\t','dots config set colors.apps.todo.field.alias.value.bold true '),
                    ('dots config set apps.wttr.units met\t','dots config set apps.wttr.units metric ')):
                with self.subTest(shell=shell,typed=typed):self.assertEqual(self.capture(shell,typed),expected)

    @unittest.skipUnless(shutil.which('fish'),'Fish unavailable')
    def test_fish_branch_scope_and_value_position(self):
        for typed,expected in (
                ('dots config set profile..\t','dots config set profile.alias '),
                ('dots --color=never config set --profile windows profile..\t','dots --color=never config set --profile windows profile.alias '),
                ('dots config set icons.git.branch literal..\t','dots config set icons.git.branch literal..')):
            with self.subTest(typed=typed):self.assertEqual(self.capture('fish',typed),expected)

    @unittest.skipUnless(shutil.which('zsh') and shutil.which('fzf') and (FZF_TAB/'fzf-tab.plugin.zsh').is_file(),'Zsh fzf-tab unavailable')
    def test_real_fzf_tab_branches_values_and_glyphs_use_config_preview(self):
        import shlex,re
        from bash_dots_pty import Terminal
        plugin=self.home/'fzf-tab';shutil.copytree(FZF_TAB,plugin,ignore=shutil.ignore_patterns('.git'))
        cache=Path(self.env['XDG_CACHE_HOME'])/'dots/fonts/catalog.json';cache.parent.mkdir(parents=True)
        cache.write_text(json.dumps(dict(schema=1,families={},glyph_version='fixture',glyphs={'fixture':[
            dict(name='fixture-battery',glyph='\ue000',codepoint='U+E000',collection='test'),
            dict(name='fixture-clock',glyph='\ue001',codepoint='U+E001',collection='test')]})))
        preview=self.home/'preview';preview.write_text('#!/bin/sh\ntouch "$HOME/generic-preview-called"\n');preview.chmod(0o755)
        cases=[('dots config set ..',"'colors.",'dots config set colors.'),
               ('dots config set colors..',"'colors.icons.",'dots config set colors.icons.'),
               ('dots config set colors.icons.',"'colors.icons.git.",'dots config set colors.icons.git.'),
               ('dots --color=never config set --profile windows ..',None,'dots --color=never config set --profile windows ..'),
               ('dots config set ',"'icons.navigation.new !colors",'dots config set icons.navigation.new '),
               ('dots config set DOTS_COLOR ',"'never",'dots config set DOTS_COLOR never '),
               ('dots config set colors.apps.todo.field.alias.value.bold ',"'false",'dots config set colors.apps.todo.field.alias.value.bold false '),
               ('dots config set colors.apps.todo.field.alias.value.fg ',"'colors.daylight.day.fg",'dots config set colors.apps.todo.field.alias.value.fg colors.daylight.day.fg '),
               ('dots config set icons.git.branch ',"'fixture-battery",'dots config set icons.git.branch \ue000 ')]
        for typed,query,expected in cases:
            target=self.home/'fzf-buffer';target.unlink(missing_ok=True)
            terminal=Terminal(shutil.which('zsh'),dict(self.env,TERM='xterm-256color',_PREVIEW_=str(preview)),self.home)
            try:
                setup='autoload -Uz compinit; compinit -D; source "$DOTS/lib/dots/completion/zsh"; source '+shlex.quote(str(plugin/'fzf-tab.plugin.zsh'))
                setup+='; source '+shlex.quote(str(Path(__file__).resolve().parents[1]/'shells/zsh/completions.zsh'))
                setup+='; record_fzf() { printf "%s\\0" "$@" > "$HOME/fzf-args"; command fzf "$@"; }; zstyle ":fzf-tab:complete:__dots_preview_fallback__:" fzf-command record_fzf'
                setup+='; PROMPT="READY> "; dots() { print BAD > "$HOME/command-executed"; }; cap() { print -rn -- "$BUFFER" > "$HOME/fzf-buffer"; }; zle -N cap; bindkey "^X" cap; print INITIALIZED\r'
                terminal.send(setup);terminal.wait(b'INITIALIZED\r\n')
                terminal.send(typed+'\t');terminal.wait(b'\x1b[?1000h')
                if typed.endswith('.'):
                    arguments=(self.home/'fzf-args').read_bytes().decode().split('\0')
                    queries=[arg.split('=',1)[1] for arg in arguments if arg.startswith('--query=')]
                    if '--query' in arguments:queries.append(arguments[arguments.index('--query')+1])
                    if '-q' in arguments:queries.append(arguments[arguments.index('-q')+1])
                    self.assertEqual(queries[-1:],[""],arguments)
                if query is None:terminal.send('\x1b')
                else:
                    start=len(terminal.output);terminal.send('\x15'+query)
                    deadline=time.monotonic()+8
                    while True:
                        visible=re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]','',terminal.output[start:].decode(errors='replace'))
                        if re.search(r'\b1/\d+',visible):break
                        self.assertLess(time.monotonic(),deadline,terminal.output[-1600:])
                        if select.select([terminal.master],[],[],.05)[0]:terminal.output.extend(os.read(terminal.master,65536))
                    terminal.send('\r')
                time.sleep(.3);terminal.send('\x18')
                deadline=time.monotonic()+8
                while not target.exists():
                    self.assertLess(time.monotonic(),deadline,terminal.output[-1600:]);time.sleep(.05)
                self.assertEqual(target.read_text(),expected)
                self.assertFalse((self.home/'command-executed').exists())
                self.assertFalse((self.home/'generic-preview-called').exists())
            finally:terminal.close()


if __name__=='__main__':unittest.main()

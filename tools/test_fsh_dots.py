#!/usr/bin/env python3
"""Native FSH editor regions for Dots routes in private shell/plugin roots."""
import os
from pathlib import Path
import select
import shlex
import shutil
import subprocess
import tempfile
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
ZSH=shutil.which('zsh')
FSH=Path(os.environ.get('DOTS_TEST_FSH') or Path.home()/'.local/share/zinit/plugins/zdharma-continuum---fast-syntax-highlighting')


@unittest.skipUnless(ZSH and (FSH/'fast-syntax-highlighting.plugin.zsh').is_file(),'Zsh/public FSH unavailable')
class FshDots(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='dots-fsh-input-')
        self.addCleanup(temporary.cleanup)
        self.home=Path(temporary.name)
        self.root=self.home/'checkout space ü'
        self.plugin=self.home/'plugin'
        shutil.copytree(FSH,self.plugin,ignore=shutil.ignore_patterns('.git','*.zwc','images','tests'))
        (self.root/'lib/dots/themes').mkdir(parents=True)
        for name in ('fsh.zsh','fsh-dots.zsh'):
            shutil.copy2(ROOT/'lib/dots/themes'/name,self.root/'lib/dots/themes'/name)
        (self.root/'shells/zsh/integrations').mkdir(parents=True)
        shutil.copy2(ROOT/'shells/zsh/integrations/plugins.zsh',self.root/'shells/zsh/integrations/plugins.zsh')
        (self.root/'bin').mkdir()
        for name in ('dots','dots-git','dots-git-status','dots-debug','dots-debug-startup',
                     'dots-todo','dots-todo-list','dots-blastoff','dots-blastoff-theme',
                     'dots-blastoff-theme-list','dots-pkgs','dots-pkgs-install',
                     'dots-files','dots-files-migrate-apps','dots-menu','dots-menu-tmux-keys'):
            command=self.root/'bin'/name
            command.write_text('#!/bin/sh\nprintf EXECUTED > "$HOME/executed"\nexit 97\n')
            command.chmod(0o700)
        work=self.home/'fsh-work';work.mkdir()
        (work/'secondary_theme.zsh').write_text('# owned inert secondary theme\n')
        self.env={key:value for key,value in os.environ.items()
                  if key in ('PATH','PREFIX','LD_PRELOAD','SYSTEMROOT','SystemRoot')}
        self.env.update(HOME=str(self.home),ZDOTDIR=str(self.home),DOTS=str(self.root),
                        FAST_WORK_DIR=str(work),TERM='xterm-256color',
                        XDG_CONFIG_HOME=str(self.home/'config'),XDG_CACHE_HOME=str(self.home/'cache'),
                        XDG_DATA_HOME=str(self.home/'data'),XDG_STATE_HOME=str(self.home/'state'),
                        PATH=str(self.root/'bin')+os.pathsep+self.env['PATH'])
        self.setup='source '+shlex.quote(str(self.plugin/'fast-syntax-highlighting.plugin.zsh'))+'; '
        self.setup+='source "$DOTS/lib/dots/themes/fsh.zsh"; _dots_fsh_apply; '
        self.setup+='FAST_HIGHLIGHT_STYLES[${FAST_THEME_NAME}subcommand]=fg=magenta; '
        self.setup+='FAST_HIGHLIGHT[use_brackets]=0; '

    def run_zsh(self,code,setup=None):
        result=subprocess.run([ZSH,'-dfi','-c',(self.setup if setup is None else setup)+code],cwd=self.home,env=self.env,
                              text=True,capture_output=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stderr,'')
        self.assertFalse((self.home/'executed').exists())
        return result.stdout

    def regions(self,line,extra=''):
        code=extra+'; PREBUFFER=""; BUFFER='+shlex.quote(line)+'; reply=(); '
        code+='-fast-highlight-process "$PREBUFFER" "$BUFFER" 0; print -r -- "$BUFFER"; print -rl -- $reply'
        output=self.run_zsh(code).splitlines()
        self.assertEqual(output.pop(0),line)
        return {tuple(row.split(' ',2)) for row in output if row}

    def test_routes_follow_native_style_without_a_published_theme(self):
        for line,words in (
                ('dots git',('git',)),('dots git status',('git','status')),
                ('dots debug startup',('debug','startup')),('dots todo list',('todo','list')),
                ('dots blastoff theme list',('blastoff','theme','list')),
                ('dots pkgs install',('pkgs','install')),('dots help git status',('help','git','status')),
                ('dots files migrate apps',('files','migrate','apps')),
                ('dots files migrate-apps',('files','migrate-apps')),
                ('dots menu tmux keys',('menu','tmux','keys')),
                ('dots --color=always git status',('git','status'))):
            with self.subTest(line=line):
                regions=self.regions(line)
                for word in words:
                    start=line.index(word)
                    self.assertIn((str(start),str(start+len(word)),'fg=magenta'),regions)
        self.assertEqual(self.run_zsh('print -r -- $FAST_HIGHLIGHT[chroma-dots]'),'_dots_fsh_chroma\n')
        self.assertIn(('5','8','fg=cyan'),self.regions('dots git','FAST_HIGHLIGHT_STYLES[${FAST_THEME_NAME}subcommand]=fg=cyan'))

    def test_unknowns_operands_quotes_and_shell_syntax_keep_native_handling(self):
        for line,expected in (
                ('dots unknown git',()),('dots git README.md status',('git',)),
                ('dots "git" status',()),('dots git --directory status',('git',)),
                ('dots git-status',()),('dots files migrate',('files',)),
                ('dots menu tmux',('menu',)),('dots files migrate unknown apps',('files',)),
                ('dots git -- status',('git',)),('dots git > output status',('git','status')),
                ('dots git | dots debug',('git','debug')),
                ('dots "$(dots)" git',()),('dots git; dots todo list',('git','todo','list'))):
            with self.subTest(line=line):
                regions=self.regions(line)
                highlighted={line[int(begin):int(end)] for begin,end,style in regions if style=='fg=magenta'}
                self.assertEqual(highlighted,set(expected),regions)
        for line in ('dots "git" status','dots git --directory status','dots git -- status',
                     'dots git > output status','dots git | dots debug'):
            custom=self.regions(line)
            native=self.regions(line,'unset "FAST_HIGHLIGHT[chroma-dots]"')
            # Route spans change; native quoting/options/operators remain exact.
            excluded={(begin,end) for begin,end,style in custom if style=='fg=magenta'}
            self.assertEqual({r for r in custom if r[:2] not in excluded},
                             {r for r in native if r[:2] not in excluded},line)

    def test_nested_command_substitutions_keep_independent_route_state(self):
        for line,expected in (
                ('dots git "$(dots debug startup)" status',{'git','debug','startup'}),
                ('dots "$(dots git)" debug',{'git'}),
                ('dots git $(dots) status; dots todo list',{'git','todo','list'}),
                ('dots files migrate "$(dots menu tmux keys)" apps',{'files','menu','tmux','keys'})):
            with self.subTest(line=line):
                regions=self.regions(line,'FAST_HIGHLIGHT_STYLES[${FAST_THEME_NAME}secondary]=""')
                highlighted={line[int(begin):int(end)] for begin,end,style in regions if style=='fg=magenta'}
                self.assertEqual(highlighted,expected,regions)

    def test_control_flow_preserves_native_parser_regions(self):
        for line in ('case x in x) dots git;; esac',
                     'case x in x) dots git;; y) dots todo list;; esac',
                     'if dots git; then dots todo list; fi',
                     'for x in a; do dots git; done',
                     'while dots git; do dots todo list; done'):
            with self.subTest(line=line):
                custom=self.regions(line)
                native=self.regions(line,'unset "FAST_HIGHLIGHT[chroma-dots]"')
                route_ranges={(begin,end) for begin,end,style in custom if style=='fg=magenta'}
                self.assertTrue(route_ranges,custom)
                self.assertEqual({r for r in custom if r[:2] not in route_ranges},
                                 {r for r in native if r[:2] not in route_ranges},line)

    def test_custom_chroma_choices_and_exact_profile_paths(self):
        self.assertEqual(self.run_zsh('FAST_HIGHLIGHT[chroma-dots]=custom; _dots_fsh_apply; print -r -- $FAST_HIGHLIGHT[chroma-dots]'),'custom\n')
        self.assertEqual(self.run_zsh('FAST_HIGHLIGHT[chroma-dots]=""; _dots_fsh_apply; print -r -- ${+FAST_HIGHLIGHT[chroma-dots]}:$FAST_HIGHLIGHT[chroma-dots]'),'1:\n')
        profile=self.home/'profile bin';profile.mkdir()
        command=profile/'dots-extra';command.write_text('#!/bin/sh\nexit 97\n');command.chmod(0o700)
        extra='DOTS_PROFILE_CHECKOUT=$DOTS; DOTS_PROFILE_BIN_PATHS='+shlex.quote(str(profile))
        self.assertIn(('5','10','fg=magenta'),self.regions('dots extra',extra))
        self.assertNotIn(('5','10','fg=magenta'),self.regions('dots extra'))
        self.assertIn(('3','9','fg=magenta'),self.regions('dg status',"alias dg='dots git'"))

    def test_widget_plugin_entrypoint_without_theme_initialization(self):
        code=r'''
source "$DOTS/shells/zsh/integrations/plugins.zsh"
DOTS_INIT_THEME=0
_dots_plugin_setup() { return 0; }
_dots_suggestion_plugin() { return 0; }
_dots_load_plugin() {
  [[ $1 != zdharma-continuum/fast-syntax-highlighting ]] ||
    source "$HOME/plugin/fast-syntax-highlighting.plugin.zsh"
  return 0
}
typeset -gA _comps
_dots_widget_plugins
(( ! ${+functions[_dots_fsh_apply]} )) || exit 8
[[ $FAST_HIGHLIGHT[chroma-dots] == _dots_fsh_chroma ]] || exit 9
FAST_HIGHLIGHT_STYLES[${FAST_THEME_NAME}subcommand]=fg=magenta
PREBUFFER=''; BUFFER='dots git'; reply=()
-fast-highlight-process "$PREBUFFER" "$BUFFER" 0
print -rl -- $reply
'''
        self.assertIn('5 8 fg=magenta',self.run_zsh(code,setup=''))

    def test_highlighting_does_not_execute_commands_or_change_buffer(self):
        code=r'''
command_not_found_handler() { print -r -- "$*" > "$HOME/executed"; return 127; }
hash dots="$DOTS/bin/dots"
path=()
PREBUFFER=''; BUFFER='dots blastoff theme list'; original=$BUFFER
repeat 100 { reply=(); -fast-highlight-process "$PREBUFFER" "$BUFFER" 0; }
[[ $BUFFER == $original && ! -e "$HOME/executed" ]] || exit 9
print -rl -- $reply
'''
        self.assertIn('5 13 fg=magenta',self.run_zsh(code))

    def test_real_tab_insertion_and_editor_regions(self):
        from bash_dots_pty import Terminal
        terminal=Terminal(ZSH,self.env,self.home)
        try:
            setup='autoload -Uz compinit; compinit -D; '+self.setup
            # The executed marker must differ from terminal input echo: waiting
            # on the echoed setup line can queue Tab before FSH has loaded.
            setup+=r'''_test_dots() { compadd git; }; compdef _test_dots dots; cap() { print -rn -- "$BUFFER" > "$HOME/buffer"; print -rl -- $region_highlight > "$HOME/regions"; }; zle -N cap; bindkey '^X' cap; PROMPT='READY> '; print INIT""IALIZED'''
            terminal.send(setup+'\r');terminal.wait(b'INITIALIZED\r\n')
            self.drain(terminal,.2)
            terminal.send('dots gi');self.drain(terminal,.2)
            terminal.send('\t')
            self.drain(terminal,.6)
            terminal.send('\x18')
            deadline=time.monotonic()+8
            while not (self.home/'buffer').exists():
                self.assertLess(time.monotonic(),deadline,terminal.output[-2000:])
                self.drain(terminal,.05)
            self.assertEqual((self.home/'buffer').read_text(),'dots git ')
            self.assertIn('5 8 fg=magenta',(self.home/'regions').read_text(),terminal.output[-2500:])
            self.assertFalse((self.home/'executed').exists())
        finally:terminal.close()

    def drain(self,terminal,seconds):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            if select.select([terminal.master],[],[],.02)[0]:
                chunk=os.read(terminal.master,65536);terminal.output.extend(chunk)
                if b'\x1b[6n' in chunk: terminal.send('\x1b[1;1R')


if __name__=='__main__':
    unittest.main()

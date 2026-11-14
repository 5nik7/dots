#!/usr/bin/env python3
"""Completion display and literal insertion in test-owned profiles and PTYs."""
import json
import os
from pathlib import Path
import re
import select
import shlex
import shutil
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

import test_profile_config as fixtures

ROOT = fixtures.ROOT
FZF_TAB = Path(os.environ.get('DOTS_TEST_FZF_TAB') or Path.home()/'.local/share/zinit/plugins/Aloxaf---fzf-tab')
SGR = re.compile(rb'\x1b\[[0-9;]*m')


class CompletionColors(unittest.TestCase):
    run_config = fixtures.ProfileConfig.run_config

    def setUp(self):
        fixtures.ProfileConfig.setUp(self)
        shutil.copytree(ROOT/'default', self.root/'default')
        for name in ('dots', 'todo', 'theme', 'fonts', 'bak'):
            source = ROOT/'bin'/name
            if source.exists(): shutil.copy2(source, self.root/'bin'/name)
        for source in ROOT.glob('bin/dots-*'):
            if source.is_file(): shutil.copy2(source, self.root/'bin'/source.name)
        self.env.update(ZDOTDIR=str(self.home), TERM='xterm-256color', DOTS_COLOR='always',
                        TMPDIR=str(self.home), TMPPREFIX=str(self.home/'zsh'),
                        PATH=str(self.root/'bin')+os.pathsep+self.env['PATH'],
                        GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_TERMINAL_PROMPT='0')

    def zsh(self, code, *, plugin=False, **env):
        prefix = 'source "$DOTS/lib/dots/completion/styles.zsh"; '
        if plugin:
            prefix = 'autoload -Uz compinit; compinit -D; source '+shlex.quote(str(FZF_TAB/'fzf-tab.plugin.zsh'))+'; '+prefix
        result = subprocess.run([shutil.which('zsh'), '-dfi', '-c', prefix+code],
                                env=dict(self.env, **env), cwd=self.home, capture_output=True, timeout=25)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
        return result

    def test_config_roundtrip_and_next_prompt_activation_without_publication(self):
        for native in (False, True):
            self.assertEqual(self.run_config('get', 'apps.completion.enabled', native=native).stdout, 'true\n')
            result = json.loads(self.run_config('set', 'colors.apps.completion.command.fg', '#123456', '--json', native=native).stdout)
            self.assertNotEqual(result.get('refresh', {}).get('status'), 'failed', result)
            self.assertEqual(self.run_config('get', 'colors.apps.completion.command.fg', native=native).stdout, '#123456\n')
            self.run_config('set', 'colors.apps.completion.description.italic', 'true', native=native)
            detail = json.loads(self.run_config('explain', 'colors.apps.completion.command.fg', '--json', native=native).stdout)
            self.assertIn('next Zsh prompt', str(detail))
            self.assertFalse((Path(self.env['XDG_STATE_HOME'])/'dots/current/theme').exists())
            self.run_config('unset', 'colors.apps.completion.command.fg', native=native)
        self.assertEqual(self.run_config('get', 'colors.apps.completion.command.fg').stdout, 'blue\n')
        self.run_config('set', 'colors.apps.completion.command.fg', '$(touch bad)', code=1)
        self.run_config('set','apps.completion.enabled','false')
        target='windows' if self.platform!='windows' else 'linux'
        self.run_config('import',self.platform,'--profile',target,'--apply','--yes','--json')
        self.assertEqual(self.run_config('get','apps.completion.enabled','--profile',target).stdout,'false\n')

    def test_native_styles_literals_and_color_policy(self):
        result = self.zsh('print -r -- "$_DOTS_COMPLETION_ENABLED"; print -r -- ${_DOTS_COMPLETION_STYLES[command]}; _dots_completion_list_colors; print -rl -- $reply')
        self.assertIn(b'34\n', result.stdout)
        self.assertIn(b'(options)', result.stdout)
        for env in ({'DOTS_COLOR':'never'}, {'DOTS_COLOR':'auto','NO_COLOR':'1'}, {'DOTS_COLOR':'auto','TERM':'dumb'}):
            self.assertEqual(self.zsh('_dots_completion_list_colors; print -rn -- ${(j::)reply}', **env).stdout, b'')
        self.assertTrue(self.zsh('_dots_completion_list_colors; print -rn -- ${(j::)reply}', NO_COLOR='1').stdout)
        self.run_config('set','colors.apps.completion.command.bg','#234567')
        self.run_config('set','colors.apps.completion.command.bold','true')
        styled=self.zsh('print -r -- ${_DOTS_COMPLETION_STYLES[command]}').stdout
        self.assertIn(b'48;2;35;69;103',styled);self.assertTrue(styled.startswith(b'1;'),styled)

    def test_refresh_failure_recovery_and_no_warm_subprocess(self):
        code = r'''
print -r -- "BEFORE:${_DOTS_COMPLETION_STYLES[command]}"
# Changes are made only inside this fixture's selected profile.
print -rl -- '[apps.completion.command]' 'fg = "#123456"' > "$DOTS/profiles/PROFILE/colors.new"
command mv "$DOTS/profiles/PROFILE/colors.new" "$DOTS/profiles/PROFILE/colors.toml"
_dots_completion_refresh
print -r -- "AFTER:${_DOTS_COMPLETION_STYLES[command]}"
print -r -- '[invalid' > "$DOTS/profiles/PROFILE/colors.new"
command mv "$DOTS/profiles/PROFILE/colors.new" "$DOTS/profiles/PROFILE/colors.toml"
_dots_completion_refresh
print -r -- "INVALID:${_DOTS_COMPLETION_STYLES[command]}"
print -rl -- '[apps.completion.command]' 'fg = "green"' > "$DOTS/profiles/PROFILE/colors.new"
command mv "$DOTS/profiles/PROFILE/colors.new" "$DOTS/profiles/PROFILE/colors.toml"
_dots_completion_refresh
print -r -- "RECOVERED:${_DOTS_COMPLETION_STYLES[command]}"
# A counter catches even attempted subprocesses during unchanged refresh.
mkdir -p "$HOME/no-process"
print -rl -- '#!/bin/sh' 'echo called >> "$HOME/python-called"' 'exit 99' > "$HOME/no-process/python3"
chmod +x "$HOME/no-process/python3"
path=("$HOME/no-process")
repeat 10 { _dots_completion_refresh; }
[[ ! -e "$HOME/python-called" ]] || exit 9
print -r -- "WARM:${_DOTS_COMPLETION_STYLES[command]}"
'''.replace('PROFILE', self.platform)
        result = self.zsh(code)
        self.assertIn(b'BEFORE:34', result.stdout)
        for name in (b'AFTER', b'INVALID'):
            self.assertIn(name+b':38;2;18;52;86', result.stdout)
        self.assertIn(b'RECOVERED:32',result.stdout)
        self.assertIn(b'WARM:32',result.stdout)
        self.assertEqual(result.stderr, b'')

    def test_compiled_preferences_refresh_and_remain_python_free(self):
        import test_profiles
        fixture=test_profiles.Profiles();fixture.setUp();self.addCleanup(fixture.doCleanups)
        fixture.public();shutil.copytree(ROOT/'default',fixture.root/'default')
        code='source "$DOTS/lib/dots/shell/init.zsh"; source "$DOTS/lib/dots/completion/styles.zsh"; _dots_completion_preferences "${_DOTS_COMPLETION_SETTING_ROWS[@]}"; print -r -- "${_DOTS_COMPLETION_STYLES[command]}"'
        cold=fixture.run_shell('zsh',code)
        self.assertEqual(cold.returncode,0,cold.stderr);self.assertEqual(cold.stdout,'34\n')
        palette=Path(fixture.env['XDG_STATE_HOME'])/'dots/current/theme/palette.json'
        palette.parent.mkdir(parents=True,exist_ok=True)
        palette.write_text(json.dumps({'colors':{'blue':'#123456'}}))
        changed=fixture.run_shell('zsh',code)
        self.assertEqual(changed.returncode,0,changed.stderr)
        self.assertEqual(changed.stdout,'38;2;18;52;86\n')
        commands=fixture.home/'shims';commands.mkdir()
        shim=commands/'python3';shim.write_text('#!'+shutil.which('sh')+'\nprintf UNEXPECTED_PYTHON >&2\nexit 99\n');shim.chmod(0o700)
        warm=fixture.run_shell('zsh',code,PATH=str(commands)+os.pathsep+fixture.env['PATH'])
        self.assertEqual(warm.stdout,changed.stdout);self.assertNotIn('UNEXPECTED_PYTHON',warm.stderr)

    def test_published_palette_changes_and_missing_snapshot_fallback(self):
        code=r'''
print -r -- "MISSING:${_DOTS_COMPLETION_STYLES[command]}"
mkdir -p "$XDG_STATE_HOME/dots/current/theme"
print -r -- '{"colors":{"blue":"#123456","muted":"#334455"}}' > "$XDG_STATE_HOME/dots/current/theme/palette.new"
mv "$XDG_STATE_HOME/dots/current/theme/palette.new" "$XDG_STATE_HOME/dots/current/theme/palette.json"
_dots_completion_refresh
print -r -- "DARK:${_DOTS_COMPLETION_STYLES[command]}"
print -r -- '{"colors":{"blue":"#abcdef","muted":"#667788"}}' > "$XDG_STATE_HOME/dots/current/theme/palette.new"
mv "$XDG_STATE_HOME/dots/current/theme/palette.new" "$XDG_STATE_HOME/dots/current/theme/palette.json"
_dots_completion_refresh
print -r -- "LIGHT:${_DOTS_COMPLETION_STYLES[command]}"
rm "$XDG_STATE_HOME/dots/current/theme/palette.json"
_dots_completion_refresh
print -r -- "REMOVED:${_DOTS_COMPLETION_STYLES[command]}"
'''
        result=self.zsh(code)
        for marker in (b'MISSING:34',b'DARK:38;2;18;52;86',b'LIGHT:38;2;171;205;239',b'REMOVED:34'):
            self.assertIn(marker,result.stdout)

    def test_control_characters_in_watch_paths_remain_literal(self):
        old=self.root;self.root=self.home/'line\nback\\slash\troot';old.rename(self.root)
        self.env['DOTS']=str(self.root)
        result=self.zsh('print -r -- "STYLE:${_DOTS_COMPLETION_STYLES[command]}"; _dots_completion_fingerprint; print -r -- "WATCHED:${#reply}"')
        self.assertIn(b'STYLE:34',result.stdout)
        self.assertNotIn(b'WATCHED:0',result.stdout)
        self.assertEqual(result.stderr,b'')

    def test_private_types_preserve_existing_records(self):
        command=self.root/'bin/dots-literal'
        command.write_text('#!'+shutil.which('bash')+'\n# dots:summary=Literal fixture\n'
                           '# dots:option=--pick||choice:safe,evil$(touch marker),x]|Literal values\nexit 97\n')
        command.chmod(0o700)
        for words in (['dots',''], ['dots','--'], ['dots','literal','--pick',''], ['dots','config','set','DOTS_COLOR',''], ['theme',''], ['todo',''], ['fonts',''], ['bak','']):
            base=[str(self.root/'bin/dots'), '__complete', 'zsh', str(len(words)-1)]
            plain=subprocess.run([*base,'--',*words],env=self.env,cwd=self.home,capture_output=True,check=True).stdout
            typed=subprocess.run([*base,'--display-types','--',*words],env=self.env,cwd=self.home,capture_output=True,check=True).stdout
            restored=b'\n'.join(b'\t'.join(row.split(b'\t')[:3]) for row in typed.splitlines())+(b'\n' if typed else b'')
            self.assertEqual(restored,plain,words)
            self.assertNotIn(b'\x1b',typed)
        self.assertFalse((self.home/'marker').exists())
        self.assertIn(b'\tcommand\n', subprocess.check_output([str(self.root/'bin/dots'),'__complete','zsh','1','--display-types','--','dots',''],env=self.env))

    def test_delegated_provider_types_and_native_record_contracts(self):
        cases=[]
        for family in ('todo','fonts','bak','cleanup','clipboard','pkgs','blastoff'):
            cases.extend([(['dots',family,''],'command'),(['dots',family,'--'],'option'),
                          (['dots',family,'--color',''],'value'),(['dots',family,'--color=a'],'value')])
        cases.extend([(['todo',''],'command'),(['fonts',''],'command'),(['bak',''],'command'),
                      (['dots','clipboard','watch',''],'command'),(['dots','clipboard','init',''],'value'),
                      (['dots','blastoff','theme',''],'command'),
                      (['dots','git',''],'command'),(['dots','git','submodule','demo',''],'command'),
                      (['dots','debug',''],'command'),(['dots','debug','demo',''],'value'),
                      (['dots','debug','startup','--'],'option'),
                      (['dots','files','migrate',''],'command'),
                      (['dots','git','submodule','demo','status','--'],'option')])
        # Ambient private flags must never change an ordinary or native request.
        env=dict(self.env,_DOTS_COMPLETION_DISPLAY_TYPES='1',
                 DOTS_PROFILE_CHECKOUT=str(self.root),DOTS_PROFILE_BIN_PATHS='')
        for words,role in cases:
            with self.subTest(words=words):
                command=[str(self.root/'bin/dots'),'__complete','zsh',str(len(words)-1)]
                plain=subprocess.check_output([*command,'--',*words],env=env,cwd=self.home)
                typed=subprocess.check_output([*command,'--display-types','--',*words],env=env,cwd=self.home)
                rows=[r.split(b'\t') for r in typed.splitlines()]
                candidates=[r for r in rows if r[0]==b'candidate']
                self.assertTrue(candidates,typed)
                self.assertTrue(all(len(r)==4 and r[3]==role.encode() for r in candidates),candidates)
                self.assertEqual(b''.join(b'\t'.join(r[:3])+b'\n' for r in rows),plain)
                self.assertNotIn(b'\x1b',typed)
                if words[0]=='dots':
                    native=subprocess.check_output([sys.executable,'-B',str(self.root/'lib/dots/cli.py'),'__complete',*words[1:]],env=env,cwd=self.home)
                    self.assertTrue(all(len(r.split(b'\t'))==3 for r in native.splitlines()),native)

    @unittest.skipUnless(shutil.which('zsh') and shutil.which('fzf') and (FZF_TAB/'fzf-tab.plugin.zsh').exists(), 'Zsh/fzf-tab unavailable')
    def test_delegated_and_git_menus_with_managed_zstyles(self):
        terminal=self.terminal()
        try:
            setup='source '+shlex.quote(str(ROOT/'shells/zsh/completions.zsh'))
            setup+=r'''; _PREVIEW_=true; zstyle ':fzf-tab:complete:__dots_preview_fallback__:' fzf-command capture_fzf'''
            self.command(terminal,setup)
            for typed,query,expected,sgr in (
                    ('dots todo ',"'list",'dots todo list ',b'34'),
                    ('dots pkgs ',"'install",'dots pkgs install ',b'34'),
                    ('dots blastoff ',"'theme",'dots blastoff theme ',b'34'),
                    ('dots blastoff theme ',"'list",'dots blastoff theme list ',b'34'),
                    ('dots git ',"'status",'dots git status ',b'34'),
                    ('dots debug ',"'startup",'dots debug startup ',b'34'),
                    ('dots debug demo ',"'spinner",'dots debug demo spinner ',b'32'),
                    ('dots git submodule demo ',"'status",'dots git submodule demo status ',b'34'),
                    ('dots todo --',"'--json",'dots todo --json ',b'33'),
                    ('dots pkgs --scope ',"'user",'dots pkgs --scope user ',b'32')):
                terminal.send(typed+'\t');terminal.wait(b'\x1b[?1000h');self.drain(terminal)
                data=(self.home/'menu-data').read_bytes()
                self.assertIn(b'\x1b[0;'+sgr+b'm',data,typed)
                self.finish(terminal,query,expected)
                terminal.send('\x03');self.drain(terminal)
        finally:terminal.close()

    @unittest.skipUnless(shutil.which('zsh') and shutil.which('fzf') and (FZF_TAB/'fzf-tab.plugin.zsh').exists(), 'Zsh/fzf-tab unavailable')
    def test_hidden_group_headings_keep_types_and_preferences(self):
        self.run_config('set','colors.apps.completion.command.fg','#123456')
        terminal=self.terminal()
        try:
            for mode in ('none','brief','full'):
                self.command(terminal,"zstyle ':fzf-tab:*' show-group "+mode)
                terminal.send('dots debug \t');terminal.wait(b'\x1b[?1000h');self.drain(terminal)
                data=(self.home/'menu-data').read_bytes()
                self.assertIn(b'\x1b[0;38;2;18;52;86m',data,mode)
                self.finish(terminal,"'startup",'dots debug startup ')
                terminal.send('\x03');self.drain(terminal)
        finally:terminal.close()

    @unittest.skipUnless(shutil.which('zsh') and shutil.which('fzf') and (FZF_TAB/'fzf-tab.plugin.zsh').exists(), 'Zsh/fzf-tab unavailable')
    def test_standalone_plugin_menus_and_shared_preferences(self):
        # Only completion sources/controllers are copied; no engine or package
        # backend is needed and every config/state path remains test-owned.
        for name in ('anodize','pkgs'):
            target=self.root/'plugins'/name;target.mkdir(parents=True)
            for source in (ROOT/'plugins'/name).glob('*.py'):
                shutil.copy2(source,target/source.name)
            shutil.copy2(ROOT/'bin'/name,self.root/'bin'/name)
        shutil.copytree(ROOT/'plugins/pkgs/pkgs_lib',self.root/'plugins/pkgs/pkgs_lib',
                        ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        completions=self.home/'plugin-completions';completions.mkdir()
        shutil.copy2(ROOT/'plugins/pkgs/completions/pkgs.zsh',completions/'_pkgs')
        self.env.update(PKGS_FUZZY_TAB='0',BLASTOFF_HOME=str(self.home/'blastoff'),
                        DOTS_PROFILE_CHECKOUT=str(self.root),DOTS_PROFILE_BIN_PATHS='')
        self.run_config('set','colors.apps.completion.command.fg','#123456')
        terminal=self.terminal()
        try:
            setup='fpath=('+shlex.quote(str(completions))+' $fpath); autoload -Uz _pkgs; compdef _pkgs pkgs; '
            setup+='source '+shlex.quote(str(ROOT/'plugins/blastoff/completions/blastoff.zsh'))+'; '
            setup+='source '+shlex.quote(str(ROOT/'plugins/anodize/completion/zsh'))
            self.command(terminal,setup)
            for typed,query,expected,sgr in (
                    ('pkgs ',"'install",'pkgs install ',b'38;2;18;52;86'),
                    ('pkgs --',"'--scope",'pkgs --scope ',b'33'),
                    ('pkgs --scope ',"'user",'pkgs --scope user ',b'32'),
                    ('blastoff ',"'theme",'blastoff theme ',b'38;2;18;52;86'),
                    ('blastoff theme ',"'list",'blastoff theme list ',b'38;2;18;52;86'),
                    ('blastoff --color ',"'always",'blastoff --color always ',b'32'),
                    ('anodize ',"'create",'anodize create ',b'38;2;18;52;86'),
                    ('anodize --color=',"'--color=always",'anodize --color=always ',b'32')):
                terminal.send(typed+'\t');terminal.wait(b'\x1b[?1000h');self.drain(terminal)
                data=(self.home/'menu-data').read_bytes()
                self.assertIn(b'\x1b[0;'+sgr+b'm',data,typed)
                self.finish(terminal,query,expected)
                terminal.send('\x03');self.drain(terminal)
        finally:terminal.close()

    @unittest.skipUnless(shutil.which('zsh') and shutil.which('fzf') and (FZF_TAB/'fzf-tab.plugin.zsh').exists(), 'Zsh/fzf-tab unavailable')
    def test_adapter_installs_once_and_reconnects(self):
        result=self.zsh(r'''
print -r -- "INSTALLED:${+functions[_dots_completion_original_capture]}"
original=$functions[_dots_completion_original_capture]
_dots_completion_install_fzf; disable-fzf-tab; enable-fzf-tab; _dots_completion_install_fzf
[[ $original == $functions[_dots_completion_original_capture] ]] || exit 9
[[ $functions[compadd] == *'_dots_completion_original_capture'* ]] || exit 8
''',plugin=True)
        self.assertIn(b'INSTALLED:1',result.stdout)

    @unittest.skipUnless(shutil.which('zsh') and shutil.which('fzf') and (FZF_TAB/'fzf-tab.plugin.zsh').exists(), 'Zsh/fzf-tab unavailable')
    def test_normal_startup_completion_colors_and_exact_word_tab(self):
        from zsh_fixture import fixture
        from zsh_interactive import Session
        try: root,repo,env=fixture()
        except RuntimeError as error: self.skipTest(str(error))
        self.addCleanup(shutil.rmtree,root)
        shutil.copytree(ROOT/'default',repo/'default',dirs_exist_ok=True)
        for source in (ROOT/'bin').glob('dots-*'):
            if source.is_file(): shutil.copy2(source,repo/'bin'/source.name)
        self.home=Path(env['HOME'])
        rc=repo/'shells/zsh/zshrc'
        rc.write_text(rc.read_text()+r'''
capture_fzf() { command cat >| "$HOME/menu-data"; printf '%s\0' "$@" >| "$HOME/menu-args"; command fzf "$@" < "$HOME/menu-data"; }
zstyle ':fzf-tab:*' fzf-command capture_fzf
zstyle ':fzf-tab:complete:__dots_preview_fallback__:' fzf-command capture_fzf
_PREVIEW_=true
PROMPT='READY> '
cap() { print -rn -- "$BUFFER" >| "$HOME/buffer"; print -rl -- $region_highlight >| "$HOME/regions"; }
zle -N cap; bindkey '^X' cap
print -r -- "${+functions[_dots_completion_original_capture]}" >| "$HOME/adapter-installed"
print -r -- "$FAST_HIGHLIGHT_STYLES[${FAST_THEME_NAME}subcommand]" >| "$HOME/input-style"
autoload -Uz add-zle-hook-widget
fixture_ready() { print -r -- FULL_READY; }
add-zle-hook-widget line-init fixture_ready
''')
        terminal=Session(env,self.home)
        try:
            terminal.wait(b'FULL_READY',timeout=60)
            self.assertEqual((self.home/'adapter-installed').read_text(),'1\n')
            # A complete unique word inserts its separator; the following Tab
            # opens that command's children. Neither operation executes dots.
            self.drain(terminal,.2)
            terminal.send('dots git');self.drain(terminal,.2)
            terminal.send('\t');self.drain(terminal,.4);terminal.send('\x18')
            self.assertEqual(self.await_buffer(terminal).read_text(),'dots git ')
            style=(self.home/'input-style').read_text().strip()
            self.assertTrue(style)
            self.assertIn('5 8 '+style,(self.home/'regions').read_text())
            (self.home/'buffer').unlink()
            def menu():
                target=self.home/'menu-data'
                target.unlink(missing_ok=True)
                terminal.send('\t')
                deadline=time.monotonic()+10
                while not target.exists() or not target.stat().st_size:
                    self.assertLess(time.monotonic(),deadline,terminal.output[-2000:])
                    self.drain(terminal,.05)
                self.drain(terminal,.3)
            menu()
            self.assertIn(b'\x1b[0;34m',(self.home/'menu-data').read_bytes())
            self.finish(terminal,"'status",'dots git status ')
            self.assertIn('5 8 '+style,(self.home/'regions').read_text())
            self.assertIn('9 15 '+style,(self.home/'regions').read_text())
            terminal.send('\x03');self.drain(terminal)
            # Reload through the real entry point too: Zinit may have already
            # materialized its helpers, and compinit can reconnect widgets.
            self.command(terminal,'source "$DOTS/shells/zsh/zshrc"')
            terminal.send('dots debug ');self.drain(terminal,.2);menu()
            self.assertIn(b'\x1b[0;34m',(self.home/'menu-data').read_bytes())
            self.finish(terminal,"'startup",'dots debug startup ')
        finally:terminal.close()

    def test_incompatible_plugin_keeps_original_and_native_unknown_fallback(self):
        code=r'''
functions[-ftb-compadd]='builtin compadd "$@"'
functions[-ftb-complete]='return 0'
_dots_completion_install_fzf
print -r -- "WRAPPED:${+functions[_dots_completion_original_capture]}"
for tag in main-porcelain-commands options local-branch-names tags remote-names mysterious; do
  _dots_completion_role "$tag"; print -r -- "$tag:$REPLY"
done
'''
        result=self.zsh(code)
        self.assertIn(b'WRAPPED:0',result.stdout)
        self.assertIn(b'mysterious:candidate',result.stdout)
        self.assertIn(b'local-branch-names:branch',result.stdout)
        self.assertIn(b'remote-names:remote',result.stdout)

    @unittest.skipUnless(shutil.which('zsh'), 'Zsh unavailable')
    def test_zinit_lazy_helpers_load_without_execution_and_restore_on_mismatch(self):
        library=self.home/'plugin/lib';library.mkdir(parents=True)
        for compatible in (False,True):
            for name,body in (('-ftb-generate-complist',': _ftb_complist'),
                              ('-ftb-generate-header',':'),
                              ('-ftb-fzf',": --delimiter='\\x00'" if compatible else ': unsupported')):
                (library/name).write_text(body+'\nprint executed > "$HOME/helper-executed"\n')
            result=self.zsh(r'''
FZF_TAB_HOME="$HOME/plugin"
functions[-ftb-compadd]=': _ftb_compcap'
functions[-ftb-complete]=': _ftb_complist'
typeset -A before
for fn in -ftb-generate-complist -ftb-generate-header -ftb-fzf; do
  functions[$fn]=$'local -a fpath\n''fpath=("$FZF_TAB_HOME/lib" $fpath)'$'\n''builtin autoload -X -U -z'
  before[$fn]=$functions[$fn]
done
_dots_completion_install_fzf
print -r -- "INSTALLED:${+functions[_dots_completion_original_capture]}"
if (( ! ${+functions[_dots_completion_original_capture]} )); then
  for fn in ${(k)before}; do [[ $before[$fn] == $functions[$fn] ]] || exit 9; done
fi
[[ ! -e "$HOME/helper-executed" ]] || exit 8
''')
            self.assertIn(b'INSTALLED:'+str(int(compatible)).encode(),result.stdout)

    def terminal(self, width=80, *, native=False, **env):
        from bash_dots_pty import Terminal
        import fcntl, termios, struct
        plugin=self.home/'fzf-tab'
        if not plugin.exists():shutil.copytree(FZF_TAB,plugin,ignore=shutil.ignore_patterns('.git','*.zwc'))
        terminal=Terminal(shutil.which('zsh'),dict(self.env,**env),self.home)
        fcntl.ioctl(terminal.master,termios.TIOCSWINSZ,struct.pack('HHHH',30,width,0,0))
        setup='autoload -Uz compinit; compinit -D; '
        if not native:setup+='source '+shlex.quote(str(plugin/'fzf-tab.plugin.zsh'))+'; '
        setup+='source "$DOTS/lib/dots/completion/styles.zsh"; source "$DOTS/lib/dots/completion/zsh"; '
        setup+=r'''zstyle ':completion:*' menu no; zstyle ':fzf-tab:*' use-fzf-default-opts no; zstyle ':fzf-tab:*' switch-group '<' '>'; '''
        setup+=r'''capture_fzf() { command cat > "$HOME/menu-data"; printf '%s\0' "$@" > "$HOME/menu-args"; command fzf "$@" < "$HOME/menu-data"; }; zstyle ':fzf-tab:*' fzf-command capture_fzf; '''
        setup+=r'''PROMPT='READY> '; cap() { print -rn -- "$BUFFER" > "$HOME/buffer"; }; zle -N cap; bindkey '^X' cap; print -r -- INIT""IALIZED'''
        terminal.send(setup+'\r');terminal.wait(b'INITIALIZED\r\n')
        return terminal

    def finish(self, terminal, query, expected):
        self.drain(terminal,.3)
        if query is None:terminal.send('\x1b')
        else:
            terminal.send('\x15'+query)
            self.drain(terminal,.4)
            terminal.send('\r')
        self.drain(terminal,.3);terminal.send('\x18')
        target=self.await_buffer(terminal)
        self.assertEqual(target.read_text(),expected)
        target.unlink()

    def await_buffer(self,terminal):
        deadline=time.monotonic()+8
        target=self.home/'buffer'
        while not target.exists():
            self.assertLess(time.monotonic(),deadline,terminal.output[-2000:]);self.drain(terminal,.05)
        return target

    def drain(self, terminal, seconds=.2):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            if select.select([terminal.master],[],[],.02)[0]:
                chunk=os.read(terminal.master,65536);terminal.output.extend(chunk)
                if b'\x1b[6n' in chunk:terminal.send('\x1b[1;1R')

    def command(self, terminal, code):
        # Split the marker in the command text so terminal input echo cannot
        # be mistaken for execution completing under scheduler load.
        terminal.send(code+'; print -r -- CASE_""READY\r');terminal.wait(b'CASE_READY\r\n')
        self.drain(terminal,.1)

    @unittest.skipUnless(shutil.which('zsh') and shutil.which('fzf') and (FZF_TAB/'fzf-tab.plugin.zsh').exists(), 'Zsh/fzf-tab unavailable')
    def test_real_git_and_dots_menu_spans_and_literal_selection(self):
        for width in (40,80,120):
            terminal=self.terminal(width)
            try:
                terminal.send('git \t');terminal.wait(b'\x1b[?1000h')
                data=(self.home/'menu-data').read_bytes()
                self.assertIn(b'\x1b[0;34m',data)
                self.assertIn(b'\x1b[0;90m',data)
                self.assertIn(b'--with-nth=1,3',(self.home/'menu-args').read_bytes())
                self.finish(terminal,"'status",'git status ')
                terminal.send('\x03');time.sleep(.1)
                terminal.send('dots --\t');terminal.wait(b'\x1b[?1000h')
                data=(self.home/'menu-data').read_bytes()
                self.assertIn(b'\x1b[0;33m',data)
                self.assertIn(b'--color=',data)
                self.finish(terminal,"'--color=",'dots --color=')
            finally:terminal.close()

    @unittest.skipUnless(shutil.which('zsh') and shutil.which('fzf') and (FZF_TAB/'fzf-tab.plugin.zsh').exists(), 'Zsh/fzf-tab unavailable')
    def test_groups_files_literal_controls_plain_and_disabled(self):
        terminal=self.terminal()
        try:
            self.command(terminal,r'''_sample() { local -a names=('alpha:alpha description' 'beta:beta description') vals=('one:first value' 'two:second value'); _describe -t commands Command names; _describe -t values Value vals; }; compdef _sample sample''')
            terminal.send('sample \t');terminal.wait(b'\x1b[?1000h');self.drain(terminal)
            rows=(self.home/'menu-data').read_bytes().splitlines()
            commands=[r for r in rows if b'\0alpha' in r or b'\0beta' in r]
            values=[r for r in rows if b'\0one' in r or b'\0two' in r]
            self.assertTrue(commands and values)
            self.assertNotEqual(SGR.match(commands[0])[0],SGR.match(values[0])[0])
            self.assertIn(b'\x1b[0;34m',commands[0]);self.assertIn(b'\x1b[0;32m',values[0])
            terminal.send('>');self.drain(terminal,.3)
            self.finish(terminal,"'one",'sample one ')
            terminal.send('\x03');self.drain(terminal)
            # Two matching words are selected with the plugin's existing toggle.
            terminal.send('sample \t');terminal.wait(b'\x1b[?1000h');self.drain(terminal)
            terminal.send("\x15'alpha | 'beta");self.drain(terminal,.3)
            terminal.send('\x00\t\x00\r');self.drain(terminal,.3);terminal.send('\x18');self.drain(terminal,.3)
            target=self.await_buffer(terminal)
            self.assertIn(target.read_text(),('sample alpha beta ','sample beta alpha '));target.unlink()
            terminal.send('\x03');self.drain(terminal)
            self.command(terminal,r'''_literal() { local -a raw=($'evil\e[31mword' 'evil literal') labels=($'evil\e[31mword' 'evil literal'); compadd -d labels -a raw; }; compdef _literal literal''')
            terminal.send('literal evil\t');terminal.wait(b'\x1b[?1000h');self.drain(terminal)
            data=(self.home/'menu-data').read_bytes()
            self.assertIn(b'evil\\e[31mword',data)
            self.assertIn(b'__dots_completion_',data)
            self.finish(terminal,"'word","literal evil$'\\033'\\[31mword ")
            terminal.send('\x03');self.drain(terminal)
            # File fixtures include spaces, Unicode, leading dashes and links.
            directory=self.home/'files';directory.mkdir()
            for name in ('a space ü','-dash','script.sh'):(directory/name).write_text('')
            (directory/'folder').mkdir();(directory/'link').symlink_to('a space ü');(directory/'broken').symlink_to('missing')
            (directory/'script.sh').chmod(0o755)
            self.command(terminal,'cd '+shlex.quote(str(directory))+r'''; LS_COLORS='di=34:ln=36:or=31:ex=32:fi=35'; _sample_files() { _files; }; compdef _sample_files paths''')
            terminal.send('paths \t');terminal.wait(b'\x1b[?1000h');self.drain(terminal)
            data=(self.home/'menu-data').read_bytes()
            self.assertIn(b'a space',data);self.assertIn(b'\x1b[',data)
            self.finish(terminal,"'a space",'paths a\\ space\\ ü ')
            terminal.send('\x03');self.drain(terminal)
            self.command(terminal,"DOTS_COLOR=never")
            terminal.send('sample \t');terminal.wait(b'\x1b[?1000h');self.drain(terminal)
            data=(self.home/'menu-data').read_bytes()
            self.assertNotIn(b'\x1b[0;34m',data)
            self.assertIn(b'--color=bw',(self.home/'menu-args').read_bytes())
            self.finish(terminal,None,'sample ')
            terminal.send('\x03');self.drain(terminal)
            self.command(terminal,'DOTS_COLOR=always; _DOTS_COMPLETION_ENABLED=0')
            terminal.send('sample \t');terminal.wait(b'\x1b[?1000h');self.drain(terminal)
            self.assertNotIn(b'--with-nth=1,3',(self.home/'menu-args').read_bytes())
            self.finish(terminal,None,'sample ')
        finally:terminal.close()

    @unittest.skipUnless(shutil.which('zsh') and shutil.which('fzf') and (FZF_TAB/'fzf-tab.plugin.zsh').exists(), 'Zsh/fzf-tab unavailable')
    def test_tab_observes_external_save_without_another_prompt(self):
        terminal=self.terminal()
        try:
            self.drain(terminal,.2)
            # Save from outside the waiting editor, without executing a shell command.
            colors=self.root/'profiles'/self.platform/'colors.toml'
            colors.write_text('[apps.completion.command]\nfg = "#123456"\n')
            terminal.send('git \t');terminal.wait(b'\x1b[?1000h');self.drain(terminal)
            self.assertIn(b'\x1b[0;38;2;18;52;86m',(self.home/'menu-data').read_bytes())
            self.finish(terminal,"'status",'git status ')
        finally:terminal.close()

    @unittest.skipUnless(shutil.which('zsh'), 'Zsh unavailable')
    def test_native_zsh_list_colors_and_insertion(self):
        terminal=self.terminal(native=True)
        try:
            self.command(terminal,r'''_sample() { local -a names=('alpha:alpha description' 'beta:beta description'); _describe -t commands Command names; }; compdef _sample sample''')
            start=len(terminal.output)
            terminal.send('sample \t\t');terminal.wait(b'alpha');self.drain(terminal,.2)
            shown=terminal.output[start:]
            self.assertIn(b'alpha',shown)
            self.assertIn(b'\x1b[34m',shown)
            terminal.send('\x03');self.drain(terminal)
            terminal.send('sample al\t');self.drain(terminal,.2);terminal.send('\x18');self.drain(terminal,.2)
            self.assertEqual(self.await_buffer(terminal).read_text(),'sample alpha ')
        finally:terminal.close()

    @unittest.skipUnless(shutil.which('zsh') and shutil.which('fzf') and (FZF_TAB/'fzf-tab.plugin.zsh').exists(), 'Zsh/fzf-tab unavailable')
    def test_git_reference_roles_and_preview_identity(self):
        directory=self.home/'git-repo';directory.mkdir()
        for args in (['init','-q'],['-c','user.name=Fixture','-c','user.email=fixture@example.invalid','-c','core.hooksPath=/dev/null','commit','-qm','fixture','--allow-empty'],['branch','demo-branch'],['tag','demo-tag'],['remote','add','demo-remote','https://example.invalid/repo']):
            subprocess.run(['git',*args],cwd=directory,env=self.env,check=True,capture_output=True)
        terminal=self.terminal()
        try:
            self.command(terminal,'cd '+shlex.quote(str(directory))+r'''; zstyle ':fzf-tab:*' fzf-preview 'print -r -- "$word" > "$HOME/preview-result"' ''')
            terminal.send('git checkout \t');terminal.wait(b'\x1b[?1000h');self.drain(terminal,.5)
            data=(self.home/'menu-data').read_bytes()
            self.assertRegex(data,rb'\x1b\[0;35m[^\n]*demo-branch')
            self.assertRegex(data,rb'\x1b\[0;36m[^\n]*demo-tag')
            self.finish(terminal,"'demo-branch",'git checkout demo-branch ')
            self.assertEqual((self.home/'preview-result').read_text().strip(),'demo-branch')
            terminal.send('\x03');self.drain(terminal)
            terminal.send('git push \t');terminal.wait(b'\x1b[?1000h');self.drain(terminal)
            self.assertRegex((self.home/'menu-data').read_bytes(),rb'\x1b\[0;34m[^\n]*demo-remote')
            self.finish(terminal,"'demo-remote",'git push demo-remote ')
        finally:terminal.close()

    @unittest.skipUnless(all(shutil.which(c) for c in ('tmux','zsh','fzf')) and (FZF_TAB/'fzf-tab.plugin.zsh').exists(), 'private tmux/Zsh/fzf-tab unavailable')
    def test_selected_row_keeps_semantic_colors_with_inherited_strip(self):
        import pty,signal
        socket=self.home/'colors.sock'
        env=dict(self.env,FZF_DEFAULT_OPTS='--color=fg+:strip:yellow:bold,bg+:#222222')
        def tmux(*args):
            return subprocess.check_output(['tmux','-S',str(socket),*args],env=env,stderr=subprocess.STDOUT,timeout=10).decode()
        self.addCleanup(lambda:subprocess.run(['tmux','-S',str(socket),'kill-server'],env=env,capture_output=True))
        tmux('-f',os.devnull,'new-session','-d','-s','colors','-x','80','-y','25','zsh','-dfi')
        tmux('set-option','-g','status','off')
        pid,master=pty.fork()
        if pid==0:os.execvpe('tmux',['tmux','-S',str(socket),'attach-session','-t','colors'],env)
        def screen_until(expected,exact=False):
            end=time.monotonic()+8;screen=''
            while time.monotonic()<end:
                if select.select([master],[],[],.05)[0]:os.read(master,65536)
                screen=tmux('capture-pane','-ep','-t','colors:0.0')
                if any((SGR.sub(b'',line.encode()).decode().strip()==expected if exact else expected in line and 'alpha:alpha' not in line) for line in screen.splitlines()):return screen
            self.fail(screen)
        def pump(seconds):
            end=time.monotonic()+seconds
            while time.monotonic()<end:
                if select.select([master],[],[],.02)[0]:os.read(master,65536)
        try:
            setup='autoload -Uz compinit; compinit -D; source '+shlex.quote(str(FZF_TAB/'fzf-tab.plugin.zsh'))+'; source "$DOTS/lib/dots/completion/styles.zsh"; '
            setup+=r'''zstyle ':fzf-tab:*' use-fzf-default-opts yes; _sample() { local -a a=('alpha:alpha description' 'beta:beta description'); _describe -t commands Command a; }; compdef _sample sample; PROMPT='COLOR_READY> ' '''
            tmux('send-keys','-t','colors:0.0','-l',setup);tmux('send-keys','-t','colors:0.0','Enter');screen_until('COLOR_READY>')
            tmux('send-keys','-t','colors:0.0','-l','sample ');tmux('send-keys','-t','colors:0.0','Tab')
            screen=screen_until('alpha description')
            line=next(line for line in screen.splitlines() if 'alpha description' in line and 'alpha:alpha' not in line)
            self.assertRegex(line,r'\x1b\[[0-9;]*34[0-9;]*malpha')
            self.assertRegex(line,r'\x1b\[[0-9;]*90[0-9;]*m.*alpha description')
            for background,command,description in (('#111111','38;2;137;180;250','38;2;166;173;200'),('#eeeeee','38;2;30;80;180','38;2;80;85;100')):
                tmux('send-keys','-t','colors:0.0','Escape');pump(.4)
                tmux('send-keys','-t','colors:0.0','C-c');pump(.2)
                setup='export COLORTERM=truecolor; FZF_DEFAULT_OPTS='+shlex.quote('--color=fg+:strip:yellow:bold,bg+:'+background)+'; '
                marker='PALETTE_READY_'+background[1:]
                setup+='_DOTS_COMPLETION_STYLES[command]='+shlex.quote(command)+'; _DOTS_COMPLETION_STYLES[description]='+shlex.quote(description)+'; clear; print '+marker
                tmux('send-keys','-t','colors:0.0','-l',setup);tmux('send-keys','-t','colors:0.0','Enter')
                screen_until(marker,exact=True)
                tmux('send-keys','-t','colors:0.0','-l','sample ');tmux('send-keys','-t','colors:0.0','Tab')
                screen=screen_until('alpha description')
                line=next(line for line in screen.splitlines() if 'alpha description' in line and 'alpha:alpha' not in line)
                self.assertIn(command,line);self.assertIn(description,line)
        finally:
            os.kill(pid,signal.SIGTERM);os.waitpid(pid,0);os.close(master)


if __name__=='__main__':unittest.main()

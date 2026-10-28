#!/usr/bin/env python3
"""Less colors in owned shell environments and terminals; never reload live state."""
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

from test_menus import MenuFixture, ROOT
from less_style import apply as apply_style, published_environment, START, END, MARKER, RESET


def apply(environment, colors, **options):
    # Exercise the portable RGB contract even on native Windows hosts.
    options.setdefault('windows', False)
    apply_style(environment, colors, **options)

DARK = dict(foreground='#cdd6f4', background='#1e1e2e', lighter_background='#313244')
LIGHT = dict(foreground='#4c4f69', background='#eff1f5', lighter_background='#e6e9ef')
DARK_SGR = '\x1b[0;38;2;205;214;244;48;2;49;50;68m'
LIGHT_SGR = '\x1b[0;38;2;76;79;105;48;2;230;233;239m'


class LessStyle(MenuFixture):
    def setUp(self):
        super().setUp()
        self.env.update(DOTS=str(ROOT), DOTS_COLOR='auto', ZDOTDIR=str(self.home),
                        XONSH_DATA_DIR=str(self.home/'xonsh-data'), XONSH_CACHE_DIR=str(self.home/'xonsh-cache'),
                        XONTRIBS_AUTOLOAD_DISABLED='*')
        os.environ.update(self.env)

    def test_exact_colors_inherited_ownership_and_explicit_overrides(self):
        env = dict(self.env)
        apply(env, DARK)
        self.assertEqual([env[k] for k in (START, END, MARKER)], [DARK_SGR, RESET, DARK_SGR])
        child = dict(env)
        apply(child, LIGHT)
        self.assertEqual(child[START], LIGHT_SGR)
        self.assertEqual(env[START], DARK_SGR)
        for overrides in ({START:'custom'}, {END:''}):
            custom = {**child, **overrides}
            before = {k:v for k,v in custom.items() if k != MARKER}
            apply(custom, DARK)
            self.assertEqual({k:v for k,v in custom.items() if k != MARKER}, before)
        terminfo = dict(child, LESS_TERMINFO_smso='custom')
        apply(terminfo, DARK)
        self.assertNotIn(START, terminfo)
        self.assertNotIn(END, terminfo)
        self.assertEqual(terminfo['LESS_TERMINFO_smso'], 'custom')

    def test_disabled_invalid_and_older_palettes(self):
        env = dict(self.env)
        apply(env, DARK)
        for colors in ({}, {'foreground':'bad'}, {**DARK,'lighter_background':'#000000;evil'}):
            apply(env, colors)
            self.assertEqual(env[START], DARK_SGR)
            fresh = dict(self.env); apply(fresh, colors)
            self.assertNotIn(START, fresh)
        for controls, arguments in [({},dict(mode='never')), ({'NO_COLOR':'1'},{}),
                                   ({'TERM':'dumb'},{}), ({'TERM':''},{}), ({},dict(enabled=False)), ({},dict(windows=True))]:
            disabled = {**env, **controls}
            apply(disabled, LIGHT, **arguments)
            self.assertTrue(all(k not in disabled for k in (START,END,MARKER)))
        fallback = dict(self.env)
        apply(fallback, {k:v for k,v in DARK.items() if k != 'lighter_background'})
        self.assertEqual(fallback[START], '\x1b[0;38;2;205;214;244;48;2;30;30;46m')
        forced = dict(self.env, NO_COLOR='1', TERM='dumb')
        apply(forced, DARK, mode='always')
        self.assertEqual(forced[START], DARK_SGR)

    @unittest.skipIf(os.name == 'nt', 'native Windows less retains stock colors')
    def test_popup_refresh_and_config_policy_with_inert_snapshot(self):
        palette = self.home/'state/dots/current/theme/palette.json'
        palette.parent.mkdir(parents=True)
        palette.write_text(json.dumps({'colors':DARK}))
        original = dict(self.env, LESS='-R -Pcustom', LESSOPEN='explicit hook')
        env = published_environment(original)
        self.assertEqual(env[START], DARK_SGR)
        self.assertNotIn(START, original)
        palette.write_text(json.dumps({'colors':LIGHT}))
        self.assertEqual(published_environment(env)[START], LIGHT_SGR)
        self.assertEqual(published_environment(dict(env,LESS_TERMCAP_so='mine'))[START], 'mine')
        self.assertEqual((env['LESS'],env['LESSOPEN']),('-R -Pcustom','explicit hook'))
        config = self.home/'config/dots/config.env';config.parent.mkdir(parents=True)
        config.write_text('DOTS_COLOR=never\n')
        env.pop('DOTS_COLOR')
        self.assertNotIn(START, published_environment(env))
        config.write_text('DOTS_COLOR=always\n')
        self.assertEqual(published_environment(dict(env,NO_COLOR='1'))[START], LIGHT_SGR)
        palette.write_text('{bad json')
        self.assertEqual(published_environment(env)[START], DARK_SGR)

    def helper(self, shell, calls, extra=None):
        exe = shutil.which('pwsh' if shell == 'powershell' else shell)
        if not exe:
            self.skipTest(shell+' unavailable')
        env = dict(self.env, **(extra or {}))
        if shell in ('bash','zsh'):
            script = 'source "$DOTS/lib/dots/shell/less.bash"\n'
            script += '\n'.join('_dots_less_style '+ ' '.join(json.dumps(v) for v in args) for args in calls)
            script += '\nprintf "%s\\n" "${LESS_TERMCAP_so-}" "${LESS_TERMCAP_se-}" "${_DOTS_LESS_STYLE-}"'
            flags = ['--noprofile','--norc'] if shell == 'bash' else ['-df']
        elif shell == 'fish':
            script = 'source "$DOTS/lib/dots/shell/less.fish"\n'
            script += '\n'.join('_dots_less_style '+ ' '.join(json.dumps(v) for v in args) for args in calls)
            script += '\nprintf "%s\\n" "$LESS_TERMCAP_so" "$LESS_TERMCAP_se" "$_DOTS_LESS_STYLE"'
            flags = ['--no-config']
        elif shell == 'nu':
            script = 'use '+json.dumps(str(ROOT/'lib/dots/shell/less.nu'))+' _dots-less-style\n'
            script += '\n'.join('_dots-less-style '+ ' '.join(json.dumps(v) for v in args) for args in calls)
            script += '\nprint ($env.LESS_TERMCAP_so? | default ""); print ($env.LESS_TERMCAP_se? | default ""); print ($env._DOTS_LESS_STYLE? | default "")'
            flags = ['-n']
        else:
            script = '. "$env:DOTS/lib/dots/shell/less.ps1"\n'
            script += '\n'.join('Update-DotsLessStyle '+ ' '.join(json.dumps(v) for v in args) for args in calls)
            script += '\nWrite-Output ([string]$env:LESS_TERMCAP_so); Write-Output ([string]$env:LESS_TERMCAP_se); Write-Output ([string]$env:_DOTS_LESS_STYLE)'
            flags = ['-NoProfile','-NonInteractive']
        result = subprocess.run([exe,*flags,'-c',script],env=env,cwd=self.home,capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        return result.stdout.splitlines()

    def test_native_adapters_refresh_overrides_and_disabling(self):
        first = ('#cdd6f4','#313244','auto','1')
        second = ('#4c4f69','#e6e9ef','auto','1')
        for shell in ('bash','zsh','fish','nu','powershell'):
            with self.subTest(shell=shell):
                if os.name == 'nt' and shell == 'powershell':
                    self.assertEqual(self.helper(shell,[first]),['','',''])
                    continue
                self.assertEqual(self.helper(shell,[first,second]),[LIGHT_SGR,RESET,LIGHT_SGR])
                self.assertEqual(self.helper(shell,[second],{START:DARK_SGR,END:RESET,MARKER:DARK_SGR}),[LIGHT_SGR,RESET,LIGHT_SGR])
                self.assertEqual(self.helper(shell,[second],{START:DARK_SGR,END:RESET,MARKER:DARK_SGR,'LESS_TERMINFO_smso':'custom'}),['','',''])
                self.assertEqual(self.helper(shell,[first],{START:'explicit',END:''}),['explicit','',''])
                self.assertEqual(self.helper(shell,[first,('#000000','#ffffff','never','1')]),['','',''])
                self.assertEqual(self.helper(shell,[first,('bad','#ffffff','auto','1')]),[DARK_SGR,RESET,DARK_SGR])

    @unittest.skipIf(os.name == 'nt', 'POSIX shell rendering; Windows override refusal is checked separately')
    def test_full_initialization_and_theme_refresh_without_color_shortcuts(self):
        config = self.home/'config/dots/config.env';config.parent.mkdir(parents=True)
        config.write_text('DOTS_INIT_THEME=1\nDOTS_INIT_COMMANDS=0\nDOTS_INIT_COMPLETION=0\nDOTS_INIT_COLORS=0\n')
        state = self.home/'state/dots/themes'; state.mkdir(parents=True)
        for name,colors in [('g.first',DARK),('g.second',LIGHT)]:
            generation = state/'generations'/name;generation.mkdir(parents=True)
            rows = '@theme\tid\tfixture\n@theme\tfamily\tfixture\n@theme\tflavor\tdefault\n'
            rows += ''.join(f'@palette\t{key}\t{value}\n' for key,value in colors.items())
            rows += ''.join(f'{key}\thex\t{value}\n' for key,value in colors.items())
            rows += ''.join(f'@role\t{key}\t{value}\n' for key,value in colors.items())
            (generation/'shell.tsv').write_text(rows)
            init = "export THEME=fixture FLAVOR=default DOTS_THEME_ID=fixture\ndeclare -gA dots_palette=() dots_roles=([foreground]='"+colors['foreground']+"' [background]='"+colors['background']+"')\n"
            init += f"_DOTS_LESS_FOREGROUND_HEX='{colors['foreground']}'\n_DOTS_LESS_BACKGROUND_HEX='{colors['lighter_background']}'\n"
            init += 'if [[ ${dots_options[DOTS_INIT_COLORS]:-1} == 1 ]]; then\n'
            init += ''.join(f"declare -gA {key}=([hex]='{value}')\n" for key,value in colors.items())
            init += 'declare -ga _DOTS_THEME_COLOR_NAMES=(foreground background lighter_background)\nfi\n'
            (generation/'init.zsh').write_text(init)
        marker = state/'current'
        for shell in ('bash','zsh','fish','nu','xonsh'):
            with self.subTest(shell=shell):
                marker.write_text('g.first\n')
                exe=shutil.which(shell)
                if not exe: self.skipTest(shell+' unavailable')
                if shell in ('bash','zsh','fish'):
                    extension = 'fish' if shell == 'fish' else 'bash' if shell == 'bash' else 'zsh'
                    refresh = '_dots_fish_theme' if shell == 'fish' else 'set_theme'
                    script = f'source "$DOTS/lib/dots/shell/init.{extension}"\nprintf "%s\\n" "$LESS_TERMCAP_so"\nprintf "g.second\\n" > "$XDG_STATE_HOME/dots/themes/current"\n{refresh}\nprintf "%s\\n" "$LESS_TERMCAP_so"'
                    flags = ['--no-config'] if shell == 'fish' else ['--noprofile','--norc'] if shell == 'bash' else ['-df']
                    flags += ['-i']
                elif shell == 'nu':
                    script = 'source '+json.dumps(str(ROOT/'lib/dots/shell/init.nu'))+'\nprint $env.LESS_TERMCAP_so\n"g.second\\n" | save --force '+json.dumps(str(marker), ensure_ascii=False)+'\n_dots-refresh-theme\nprint $env.LESS_TERMCAP_so'
                    flags=['-n','-i']
                else:
                    with open(exe,'rb') as stream: shebang=stream.readline().decode().strip()
                    if shebang.startswith('#!') and not Path(shebang[2:].split()[0]).exists(): self.skipTest('Xonsh launcher interpreter unavailable')
                    script = '$XONSH_INTERACTIVE = True\nsource @('+repr(str(ROOT/'lib/dots/shell/init.xsh'))+')\nprint($LESS_TERMCAP_so)\nfrom pathlib import Path\nPath('+repr(str(marker))+').write_text("g.second\\n")\n_dots_refresh_theme()\nprint($LESS_TERMCAP_so)'
                    flags=['--no-rc']
                result=subprocess.run([exe,*flags,'-c',script],env=self.env,cwd=self.home,capture_output=True,text=True,timeout=30)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(result.stdout.splitlines(),[DARK_SGR,LIGHT_SGR],result.stderr)

    @unittest.skipIf(os.name == 'nt', 'POSIX PTY; native Windows less retains stock colors')
    def test_inherited_mouse_options_scroll_through_tmux(self):
        self.mouse_reader(initialize=True)

    @unittest.skipIf(os.name == 'nt', 'POSIX PTY; Windows less requires native acceptance')
    def test_managed_mouse_default_without_shell_initialization(self):
        if not shutil.which('less'):
            self.skipTest('less unavailable')
        version = subprocess.check_output(['less', '--version'], text=True)
        if int(re.search(r'less (\d+)', version)[1]) < 702:
            self.skipTest('less 702+ required for explicit mouse features')
        # Reproduce an older tmux environment before installing the configuration.
        self.mouse_reader(mouse=False)
        command = [str(ROOT/'bin/dots'), 'files', 'link', 'dots:less', '--yes', '--json']
        result = subprocess.run(command, env=self.env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        target = self.home/'config/lesskey'
        self.assertEqual(target.resolve(), ROOT/'config/less/lesskey')
        for colors in (DARK, LIGHT):
            with self.subTest(colors=colors):
                self.mouse_reader(colors=colors, inherited=' -R -PKEEP café #prompt')
        self.mouse_reader(inherited='')
        self.mouse_reader(inherited='--mouse -R')
        self.mouse_reader(inherited='--mouse --mouse -R')
        self.mouse_reader(inherited='--MOUSE -R', reverse=True)
        self.mouse_reader(arguments=['--emouse=-'], mouse=False)
        # Less's internal environment must not change the parent launch defaults.
        self.assertNotIn('LESS', self.env)

    def test_managed_less_catalog_destinations(self):
        from files.catalog import Catalog
        for platform in ('termux', 'linux', 'wsl', 'windows'):
            with self.subTest(platform=platform):
                record = next(row for row in Catalog(ROOT, platform).records() if row['id'] == 'dots:less')
                expected = self.home/('_lesskey' if platform == 'windows' else 'config/lesskey')
                self.assertEqual(Path(record['target']), expected)
                self.assertEqual(record['strategy'], 'link')

    def mouse_reader(self, *, initialize=False, inherited=' -R', mouse=True, arguments=(), colors=None, reverse=False):
        import fcntl
        import pty
        import select
        import shlex
        import signal
        import struct
        import termios
        import time
        if not all(shutil.which(name) for name in ('tmux', 'less', 'bash')):
            self.skipTest('tmux, less and Bash required')
        socket = self.base/f'mouse-{time.monotonic_ns()}.sock'
        sample = self.base/'-mouse ü.txt'
        sample.write_text(''.join(f'MOUSE LINE {i:03d}\n' for i in range(1,101)))
        env = dict(self.env, LESS=inherited, DOTS_INIT_THEME='0', DOTS_INIT_COMMANDS='0',
                   DOTS_TERMUX_AUTOSTART='0', LESSHISTFILE='-', LESSCHARSET='utf-8',
                   LESSKEYIN_SYSTEM=os.devnull)
        if initialize:
            env['LESSKEYIN'] = os.devnull
        if colors:
            apply(env, colors)
        def tmux(*args):
            result = subprocess.run(['tmux','-S',str(socket),*args], env=env,
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            return result.stdout
        self.addCleanup(lambda: subprocess.run(['tmux','-S',str(socket),'kill-server'],
                        env=env, capture_output=True, timeout=10))
        script = ('source "$DOTS/lib/dots/shell/init.bash"; ' if initialize else '')
        script += shlex.join(['exec', 'less', *arguments, str(sample)])
        tmux('-f',os.devnull,'new-session','-d','-s','mouse','-x','80','-y','20',
             'bash','--noprofile','--norc','-c',script)
        tmux('set-option','-g','status','off')
        tmux('set-option','-g','mouse','on')
        pane = tmux('list-panes','-t','mouse','-F','#{pane_id}').strip()
        pid,master = pty.fork()
        if pid == 0:
            fcntl.ioctl(1,termios.TIOCSWINSZ,struct.pack('HHHH',20,80,0,0))
            os.execvpe('tmux',['tmux','-S',str(socket),'attach-session','-t','mouse'],env)
        def wait_screen(check):
            deadline = time.monotonic()+5
            while time.monotonic() < deadline:
                if select.select([master],[],[],.05)[0]: os.read(master,65536)
                screen = tmux('capture-pane','-p','-t',pane)
                if check(screen): return screen
            self.fail('private tmux reader did not reach expected view: '+screen)
        try:
            wait_screen(lambda screen: screen.startswith('MOUSE LINE 001'))
            self.assertEqual(tmux('display-message','-p','-t',pane,'#{mouse_any_flag}').strip(),str(int(mouse)))
            if '-P' in inherited:
                self.assertIn(inherited.split('-P', 1)[1], tmux('capture-pane','-p','-t',pane))
            if not mouse:
                return
            os.write(master,b'\x1b[<64;10;5M' if reverse else b'\x1b[<65;10;5M')
            wait_screen(lambda screen: screen.startswith('MOUSE LINE ') and not screen.startswith('MOUSE LINE 001'))
            self.assertEqual(tmux('display-message','-p','-t',pane,'#{pane_in_mode}').strip(),'0')
            os.write(master,b'\x1b[<65;10;5M' if reverse else b'\x1b[<64;10;5M')
            wait_screen(lambda screen: screen.startswith('MOUSE LINE 001'))
        finally:
            os.kill(pid,signal.SIGTERM)
            os.waitpid(pid,0)
            os.close(master)

    @unittest.skipIf(os.name == 'nt', 'POSIX PTY; native Windows less retains stock colors')
    def test_less_terminal_prompt_search_reset_unicode_and_scrolling(self):
        import fcntl
        import pty
        import select
        import signal
        import struct
        import termios
        import time
        from menu_pager import reader
        if not shutil.which('less'): self.skipTest('less unavailable')
        sample = self.base/'-report ü.txt'
        sample.write_text('needle  current\n' + ''.join(f'line {i}\n' for i in range(100)))
        palette = self.home/'state/dots/current/theme/palette.json'
        palette.parent.mkdir(parents=True)
        for backend in ('plain','popup'):
            for width in (40,80,120):
                for colors, start in ((DARK,DARK_SGR),(LIGHT,LIGHT_SGR)):
                    with self.subTest(backend=backend,width=width,colors=colors):
                        palette.write_text(json.dumps({'colors':colors}))
                        env = dict(self.env,LESSHISTFILE='-',LESSKEYIN=os.devnull,LESSKEYIN_SYSTEM=os.devnull,
                                   LESSCHARSET='utf-8',LESSUTFCHARDEF='E000-F8FF:p')
                        if backend == 'plain': apply(env,colors)
                        pid,master=pty.fork()
                        if pid == 0:
                            fcntl.ioctl(1,termios.TIOCSWINSZ,struct.pack('HHHH',20,width,0,0))
                            if backend == 'plain':
                                os.execvpe('less',['less','-R','-P','COLOR PROMPT',str(sample)],env)
                            os._exit(0 if reader(sample,backend='less',environment=env) else 1)
                        alive=True
                        def read_until(marker):
                            data=b'';deadline=time.monotonic()+5
                            while marker not in data and time.monotonic()<deadline:
                                if select.select([master],[],[],.1)[0]: data+=os.read(master,65536)
                            self.assertIn(marker,data)
                            return data
                        try:
                            prompt=b'COLOR PROMPT' if backend=='plain' else b'Back q'
                            data=read_until(prompt)
                            self.assertIn(start.encode(),data)
                            self.assertIn(' current'.encode(),data)
                            self.assertNotIn(b'<U+',data)
                            self.assertRegex(data,re.escape(start.encode())+b'.*?\x1b\\[(?:0)?m')
                            os.write(master,b'/needle\n')
                            search=read_until(prompt)
                            self.assertIn(start.encode()+b'needle',search)
                            os.write(master,b'G')
                            self.assertIn(b'line 99',read_until(prompt))
                            os.write(master,b'q')
                            deadline=time.monotonic()+5
                            while time.monotonic()<deadline:
                                done,status=os.waitpid(pid,os.WNOHANG)
                                if done:
                                    alive=False;self.assertEqual(os.waitstatus_to_exitcode(status),0);break
                                if select.select([master],[],[],.05)[0]:
                                    try: os.read(master,65536)
                                    except OSError: pass
                            self.assertFalse(alive)
                        finally:
                            if alive: os.kill(pid,signal.SIGKILL);os.waitpid(pid,0)
                            os.close(master)


if __name__ == '__main__':
    unittest.main()

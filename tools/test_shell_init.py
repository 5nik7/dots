#!/usr/bin/env python3
"""Native hook contracts in disposable roots; never load owner startup or secrets."""
import json
import os
import pty
from pathlib import Path
import shutil
from public_fixture import copy_public_tree
import subprocess
import tempfile
import time
import unittest

REPO = Path(__file__).resolve().parents[1]
SHELLS = {'bash': ('bash', 'init.bash'), 'zsh': ('zsh', 'init.zsh'),
          'fish': ('fish', 'init.fish'), 'nu': ('nushell', 'init.nu'),
          'xonsh': ('xonsh', 'init.xsh'), 'powershell': ('powershell', 'init.ps1')}


class InitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='dots-init-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "-repo space ü ' \" $(touch injected) [a]"
        self.home = self.root / 'home'
        self.home.mkdir()
        for folder in ('shells', 'lib/dots'):
            copy_public_tree(REPO / folder, self.repo / folder, repo=REPO, fixture=self.repo)
        (self.repo / 'bin').mkdir()
        for name in ('dots', 'dots.ps1', 'lib/common.sh'):
            (self.repo / 'bin' / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO / 'bin' / name, self.repo / 'bin' / name)
        (self.repo / 'scripts').mkdir()
        (self.repo / 'local/bin').mkdir(parents=True)
        self.env = {'HOME': str(self.home), 'DOTS': str(self.repo),
                    'PATH': str(self.repo / 'bin') + os.pathsep + str(Path(shutil.which('bash')).parent),
                    'ZDOTDIR': str(self.home), 'TERM': 'dumb', 'TMPDIR': str(self.root),
                    'XDG_CONFIG_HOME': str(self.home / 'config'),
                    'XDG_CACHE_HOME': str(self.home / 'cache'),
                    'XDG_DATA_HOME': str(self.home / 'data'),
                    'XDG_STATE_HOME': str(self.home / 'state'),
                    'XONSH_DATA_DIR': str(self.home / 'xonsh-data'),
                    'XONSH_CACHE_DIR': str(self.home / 'xonsh-cache'),
                    'XONTRIBS_AUTOLOAD_DISABLED': '*'}
        for key in ('LD_PRELOAD', 'PREFIX', 'TERMUX_VERSION', 'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'PATHEXT'):
            if key in os.environ:
                self.env[key] = os.environ[key]
        self.env['USERPROFILE'] = str(self.home)
        self.env['APPDATA'] = str(self.home / 'appdata')
        self.env['LOCALAPPDATA'] = str(self.home / 'localappdata')

    def dots(self, *args, env=None):
        return subprocess.run([shutil.which('bash'), str(self.repo / 'bin/dots'), *args],
                              env=env or self.env, cwd=self.home, text=True,
                              capture_output=True, timeout=20)

    def shell(self, name, code, interactive=False):
        exe = shutil.which('pwsh' if name == 'powershell' else name)
        if not exe:
            self.skipTest(name + ' is unavailable; no native verification')
        flags = {'bash': ['--noprofile', '--norc'], 'zsh': ['-df'],
                 'fish': ['--no-config'], 'nu': ['--no-config-file'],
                 'xonsh': ['--no-rc', '--shell-type', 'readline'], 'powershell': ['-NoProfile', '-NonInteractive']}[name]
        if interactive:
            flags += ['-i']
        terminal = None
        if name == 'xonsh' and interactive:
            terminal, stdin = pty.openpty()
            self.addCleanup(os.close, terminal)
            self.addCleanup(os.close, stdin)
        else:
            stdin = subprocess.DEVNULL
        proc = subprocess.run([exe, *flags, '-c', code], env=self.env, cwd=self.home,
                              stdin=stdin, text=True, capture_output=True, timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        return proc

    def generated(self, name=''):
        p = self.dots('init', *([name] if name else []))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stderr, '')
        return p.stdout

    def test_generation_is_read_only_and_undecorated(self):
        private = self.repo / 'secrets'
        private.mkdir()
        (private / 'secrets.env').write_text('echo PRIVATE_MARKER; touch "$HOME/private-read"\n')
        for shell in ('', *SHELLS):
            with self.subTest(shell=shell):
                p = self.dots('--color=always', '--icons=always', 'init', *([shell] if shell else []))
                self.assertEqual(p.returncode, 0, p.stderr)
                self.assertNotIn('PRIVATE_MARKER', p.stdout)
                self.assertNotIn('\x1b', p.stdout)
                self.assertEqual(p.stderr, '')
        self.assertEqual(list(self.home.iterdir()), [])

    def test_invalid_and_missing_loader_have_empty_stdout(self):
        for args in [('init', 'sh'), ('init', 'zsh', 'extra'), ('init', '--shell'), ('init', '')]:
            p = self.dots(*args)
            self.assertEqual(p.returncode, 2, (args, p.stderr))
            self.assertEqual(p.stdout, '')
        (self.repo / 'shells/zsh/init.zsh').unlink()
        for args in [('init',), ('init', 'zsh')]:
            p = self.dots(*args)
            self.assertEqual(p.returncode, 1)
            self.assertEqual(p.stdout, '')

    def test_metadata_and_reserved_route(self):
        for args in [('help', 'init'), ('init', '--help')]:
            p = self.dots(*args)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn('powershell', p.stdout)
        p = self.dots('__complete', 'bash', '2', '--', 'dots', 'init', '')
        for shell in SHELLS:
            self.assertIn('candidate\t' + shell + '\t', p.stdout)
        malicious = self.repo / 'bin/dots-init'
        malicious.write_text('#!/bin/sh\ntouch "$HOME/executed"\n')
        malicious.chmod(0o700)
        self.generated()
        self.assertFalse((self.home / 'executed').exists())
        self.assertEqual(self.dots('commands', '--check').returncode, 1)

    def assert_environment(self, shell):
        self.env['DOTCONFIG'] = str(self.home / 'custom config')
        code = self.generated(shell)
        # Repeated activation must not duplicate paths or inherit another checkout.
        suffix = {
            'bash': 'printf "%s\\n" "$DOTS" "$DOTCONFIG" "$PATH"',
            'zsh': 'printf "%s\\n" "$DOTS" "$DOTCONFIG" "$PATH"',
            'fish': 'printf "%s\\n" "$DOTS" "$DOTCONFIG" (string join : $PATH)',
            'nu': 'print $env.DOTS; print $env.DOTCONFIG; print ($env.PATH | str join ":")',
            'xonsh': 'print($DOTS); print($DOTCONFIG); print(":".join($PATH))',
            'powershell': '$env:DOTS; $env:DOTCONFIG; $env:PATH',
        }[shell]
        p = self.shell(shell, code + code + suffix)
        lines = p.stdout.strip().splitlines()
        self.assertEqual(lines[0], str(self.repo))
        self.assertEqual(lines[1], str(self.repo / 'config'))
        entries = lines[2].split(os.pathsep)
        for directory in ('bin', 'scripts'):
            self.assertEqual(entries.count(str(self.repo / directory)), 1)
        self.assertNotIn(str(self.repo / 'local/bin'), entries)
        self.assertLess(entries.index(str(self.repo / 'scripts')), entries.index(str(self.repo / 'bin')))
        self.assertFalse((self.home / 'injected').exists())
        self.assertNotIn('command not found', p.stderr)

    def test_bash_environment(self): self.assert_environment('bash')
    def test_zsh_environment(self): self.assert_environment('zsh')
    def test_fish_environment(self): self.assert_environment('fish')
    def test_nu_environment(self): self.assert_environment('nu')
    def test_xonsh_environment(self): self.assert_environment('xonsh')
    def test_powershell_environment(self): self.assert_environment('powershell')

    def test_default_selects_running_shell_and_initializes_children(self):
        # Synthetic loaders isolate selection from optional interactive tools.
        for shell, (directory, filename) in list(SHELLS.items())[:2]:
            (self.repo / 'shells' / directory / filename).write_text(f'export LOADED={shell}\n')
        for current, other in [('bash', 'zsh'), ('zsh', 'bash')]:
            self.env['SHELL'] = '/bin/' + other
            p = self.shell(current, 'eval "$(dots init)"; printf "%s\\n" "$LOADED"; ' +
                           other + ' -c \'eval "$(dots init)"; printf "%s\\n" "$LOADED"\'')
            self.assertEqual(p.stdout.splitlines(), [current, other])

    def test_nushell_generated_file_and_repository_fallback(self):
        config = self.home / 'config/nushell'
        config.mkdir(parents=True)
        hook = config / 'dots-init.nu'
        hook.write_text(self.generated('nu'))
        source = json.dumps(str(self.repo / 'shells/nushell/config.nu'), ensure_ascii=False)
        self.shell('nu', f'source {source}; print $env.DOTFILES')
        hook.unlink()
        self.shell('nu', f'source {source}; print $env.DOTFILES')

    def minimal_tools(self):
        directory = self.root / 'tools'
        directory.mkdir()
        for name in ('bash', 'zsh', 'fish', 'nu', 'readlink', 'mkdir', 'rm', 'mv', 'tput', 'awk', 'tr', 'uname', 'id', 'stty', 'hostname', 'which', 'sed', 'cat', 'sort', 'cut'):
            exe = shutil.which(name)
            if exe:
                (directory / name).symlink_to(exe)
        self.env['PATH'] = str(directory)

    def test_bash_interactive_reload(self):
        self.minimal_tools()
        p = self.shell('bash', self.generated() + '''
[[ ! ${RED+x} && ! ${BLUE+x} && ! ${BOLD+x} && ! ${RST+x} && ! ${COLORS+x} ]] || exit 13
RED=red BLUE=blue BOLD=bold RST=reset COLORS=caller
a=$LS_COLORS
''' + self.generated() +
                       '''
[[ $a == "$LS_COLORS" ]] || exit 9
[[ $RED == red && $BLUE == blue && $BOLD == bold && $RST == reset && $COLORS == caller ]] || exit 14
[[ $UTIL == "$DOTS/bin/lib/common.sh" ]] || exit 10
[[ ${#FG[@]} == 256 && ${#BG[@]} == 256 && ${#COLOR[@]} == 256 ]] || exit 11
# Common remains authoritative after startup and repeated initialization.
awk() { return 99; }
[[ $(upper 'a B') == 'A B' && $(lower 'A b') == 'a b' ]] || exit 12
type mkcd; alias rl''', interactive=True)
        self.assertNotIn('command not found', p.stderr)

    def test_fish_interactive_reload_and_native_snippets(self):
        self.minimal_tools()
        source = 'source "$DOTS/shells/fish/conf.d/autopair.fish"\n'
        p = self.shell('fish', source + self.generated('fish') + self.generated('fish') +
                       '\nfunctions -q d; or exit 9; functions -q _autopair_fish_key_bindings; or exit 10; contains -- "$DOTS/shells/fish/completions" $fish_complete_path; or exit 11', interactive=True)
        self.assertNotIn('Unknown command', p.stderr)

    def test_nu_interactive_reload(self):
        p = self.shell('nu', self.generated('nu') + self.generated('nu') + '\nscope aliases | where name == d | length | print', interactive=True)
        self.assertEqual(p.stdout.strip(), '1')

    def test_xonsh_interactive_wrapper(self):
        code = 'source @(' + repr(str(self.repo / 'shells/xonsh/.xonshrc')) + ')\n'
        p = self.shell('xonsh', code + code + '\nprint("d" in aliases)', interactive=True)
        self.assertEqual(p.stdout.strip(), 'True')

    def test_literal_control_characters_in_checkout_path(self):
        original = self.repo
        self.repo = self.root / "line\nback\\slash\troot"
        original.rename(self.repo)
        self.env['DOTS'] = str(self.repo)
        self.env['EXPECTED_DOTS'] = str(self.repo)
        self.env['PATH'] = str(Path(shutil.which('bash')).parent)
        suffixes = {
            'bash': '[ "$DOTS" = "$EXPECTED_DOTS" ]',
            'zsh': '[[ $DOTS == "$EXPECTED_DOTS" ]]',
            'fish': 'test "$DOTS" = "$EXPECTED_DOTS"',
            'nu': 'if $env.DOTS != $env.EXPECTED_DOTS { error make {msg: "wrong root"} }',
            'xonsh': 'assert $DOTS == $EXPECTED_DOTS',
        }
        for shell, suffix in suffixes.items():
            with self.subTest(shell=shell):
                self.shell(shell, self.generated(shell) + suffix)

    def test_bash_gum_environment_startup_reload_and_noninteractive_boundary(self):
        self.minimal_tools()
        self.env['XDG_STATE_HOME'] = str(self.home / 'state space ü')
        gum = Path(self.env['XDG_STATE_HOME']) / 'dots/current/theme/gum_env.sh'
        gum.parent.mkdir(parents=True)
        gum.write_text("export GUM_CONFIRM_PROMPT_FOREGROUND='#123456'\n")
        hook = self.generated('bash')
        self.shell('bash', hook + '\n[[ ! ${GUM_CONFIRM_PROMPT_FOREGROUND+x} ]]')
        self.shell('bash', hook + '''
[[ $GUM_CONFIRM_PROMPT_FOREGROUND == '#123456' ]] || exit 1
[[ $(bash --noprofile --norc -c 'printf %s "$GUM_CONFIRM_PROMPT_FOREGROUND"') == '#123456' ]] || exit 2
printf "export GUM_CONFIRM_PROMPT_FOREGROUND='#654321'\\n" >| "$XDG_STATE_HOME/dots/current/theme/gum_env.sh"
''' + hook + "\n[[ $GUM_CONFIRM_PROMPT_FOREGROUND == '#654321' ]]", interactive=True)
        gum.unlink()
        self.shell('bash', hook + '\n[[ ! ${GUM_CONFIRM_PROMPT_FOREGROUND+x} ]]', interactive=True)
        # The shared adapter also honors the default state root without any tools.
        gum = self.home / '.local/state/dots/current/theme/gum_env.sh'
        gum.parent.mkdir(parents=True)
        gum.write_text("export GUM_CONFIRM_PROMPT_FOREGROUND='#abcdef'\n")
        for shell in ('bash', 'zsh'):
            self.shell(shell, '''unset XDG_STATE_HOME
PATH=''
source "$DOTS/lib/dots/themes/gum-env.bash"
[[ $GUM_CONFIRM_PROMPT_FOREGROUND == '#abcdef' ]]
''')

    def test_bash_optional_activation_runs_once(self):
        self.minimal_tools()
        tool = self.root / 'tools/mise'
        tool.write_text('#!' + shutil.which('bash') + '\n' +
                        "printf '%s\\n' 'MISE_COUNT=$(( ${MISE_COUNT:-0} + 1 ))'\n")
        tool.chmod(0o700)
        self.shell('bash', self.generated('bash') + self.generated('bash') +
                   '\n[[ $MISE_COUNT == 1 ]]', interactive=True)

    def test_zsh_full_startup_private_hook_and_reload(self):
        from zsh_fixture import fixture, run
        root, repo, env = fixture(plugins=False)
        self.addCleanup(shutil.rmtree, root)
        self.minimal_tools()
        env['PATH'] = self.env['PATH']
        env['DOTCONFIG'] = str(root / 'config override')
        env['SHELLS'] = str(repo / 'shells') + '/'
        for name in ('batpipe', 'batman'):
            (repo / 'scripts' / name).unlink()
        (Path(env['HOME']) / '.fzf.zsh').unlink()
        (repo / 'secrets/secrets.env').write_text('PRIVATE_COUNT=$(( ${PRIVATE_COUNT:-0} + 1 ))\n')
        gum = Path(env['XDG_STATE_HOME']) / 'dots/current/theme/gum_env.sh'
        gum.parent.mkdir(parents=True)
        gum.write_text("export GUM_CONFIRM_PROMPT_FOREGROUND='#123456'\n")
        code = '''
[[ $GUM_CONFIRM_PROMPT_FOREGROUND == '#123456' ]] || exit 9
printf "export GUM_CONFIRM_PROMPT_FOREGROUND='#654321'\\n" >| "$XDG_STATE_HOME/dots/current/theme/gum_env.sh"
[[ $PRIVATE_COUNT == 1 && $_DOTS_COMPINIT_READY == 1 ]] || exit 1
[[ $DOTCONFIG == "$DOTS/config" && $SHELLS == "$DOTS/shells" ]] || exit 5
[[ ! ${RED+x} && ! ${BLUE+x} && ! ${BOLD+x} && ! ${RST+x} && ! ${COLORS+x} ]] || exit 7
RED=red BLUE=blue BOLD=bold RST=reset COLORS=caller
before_path=$PATH
before_hooks="${(j.:.)precmd_functions}"
source "$DOTS/shells/zsh/zshrc"
[[ $PRIVATE_COUNT == 2 && $_DOTS_COMPINIT_READY == 1 ]] || exit 2
[[ $GUM_CONFIRM_PROMPT_FOREGROUND == '#654321' ]] || exit 10
[[ $RED == red && $BLUE == blue && $BOLD == bold && $RST == reset && $COLORS == caller ]] || exit 8
[[ ${#FG} == 256 && ${#BG} == 256 && ${#COLOR} == 256 ]] || exit 6
[[ $PATH == "$before_path" && "${(j.:.)precmd_functions}" == "$before_hooks" ]] || exit 3
[[ -n ${functions[reload-completions]} && -n ${functions[is_termux]} ]] || exit 4
'''
        p = run(env, code)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertNotIn('command not found', p.stderr)

    def test_native_powershell_adapter(self):
        exe = shutil.which('pwsh')
        if not exe:
            self.skipTest('PowerShell unavailable')
        adapter = self.repo / 'bin/dots.ps1'
        p = subprocess.run([exe, '-NoProfile', '-NonInteractive', '-File', str(adapter), 'init'],
                           env=self.env, cwd=self.home, text=True, capture_output=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout, self.generated('powershell'))


    def source_code(self, shell, file):
        import shlex
        value = str(file)
        if shell in ('bash', 'zsh'):
            return 'source ' + shlex.quote(value) + '\n'
        if shell == 'fish':
            return "source '" + value.replace('\\', '\\\\').replace("'", "\\'") + "'\n"
        if shell == 'nu':
            return 'source ' + json.dumps(value, ensure_ascii=False) + '\n'
        if shell == 'xonsh':
            return 'source -e @(' + repr(value) + ')\n'
        return ". '" + value.replace("'", "''") + "'\n"

    def portable_probe(self, shell):
        names = ('DOTS', 'SHELLS', 'DOTBIN', 'DOTSCRIPTS', 'DOTFILES', 'DOTCONFIG',
                 'DOTSHHHH', 'ZSH', 'PWSH')
        expected = [self.repo, self.repo / 'shells', self.repo / 'bin',
                    self.repo / 'scripts', self.repo / 'config', self.repo / 'config',
                    self.repo / 'secrets', self.repo / 'shells/zsh', self.repo / 'shells/powershell']
        for name in names:
            self.env[name] = str(self.root / 'wrong checkout' / name)
        self.env['EXPECTED_CWD'] = str(self.home)
        if shell in ('bash', 'zsh'):
            code = '[[ $PWD == "$EXPECTED_CWD" ]] || exit 71\nprintf "%s\\n" ' + ' '.join('"$' + n + '"' for n in names)
        elif shell == 'fish':
            code = 'test "$PWD" = "$EXPECTED_CWD"; or exit 71\nprintf "%s\\n" ' + ' '.join('"$' + n + '"' for n in names)
        elif shell == 'nu':
            code = 'if $env.PWD != $env.EXPECTED_CWD { error make {msg: "cwd changed"} }; ' + '; '.join('print $env.' + n for n in names)
        elif shell == 'xonsh':
            code = 'assert $PWD == $EXPECTED_CWD\n' + '\n'.join('print($' + n + ')' for n in names)
        else:
            code = 'if ((Get-Location).Path -ne $env:EXPECTED_CWD) { throw "cwd changed" }; ' + '; '.join('$env:' + n for n in names)
        return code, [str(p) for p in expected]

    def portable_entrypoints(self, shell):
        folder, loader = SHELLS[shell]
        rc = {'bash': '.bashrc', 'zsh': 'zshrc', 'fish': 'config.fish', 'nu': 'config.nu',
              'xonsh': '.xonshrc', 'powershell': 'Microsoft.PowerShell_profile.ps1'}[shell]
        files = [self.repo / 'shells' / folder / rc, self.repo / 'shells' / folder / loader]
        if shell == 'zsh':
            files.append(self.repo / 'shells/zsh/zshenv')
        return files

    def assert_portable_links(self, shell):
        if not shutil.which('pwsh' if shell == 'powershell' else shell):
            self.skipTest(shell + ' unavailable')
        # Neutralize optional integrations: these checks isolate startup routing.
        folder = SHELLS[shell][0]
        body = next((self.repo / 'shells' / folder).glob('interactive.*'))
        body.write_text('# test-owned interactive body\n')
        probe, expected = self.portable_probe(shell)
        # A stale generated Nu hook must never redirect a repository config.
        config = self.home / 'config/nushell'
        config.mkdir(parents=True)
        (config / 'dots-init.nu').write_text('error make {msg: "stale generated hook executed"}\n')
        for entry in self.portable_entrypoints(shell):
            with self.subTest(entry=entry.name, link='direct'):
                p = self.shell(shell, self.source_code(shell, entry) + probe)
                self.assertEqual(p.stdout.splitlines(), expected)
                self.assertEqual(p.stderr, '')
            links = self.root / ('links-' + entry.name)
            links.mkdir()
            (links / 'absolute').symlink_to(entry)
            (links / 'relative').symlink_to(os.path.relpath(entry, links))
            (links / 'chain').symlink_to('relative')
            # Parent symlink plus a relative file target containing '..'.
            (links / 'directory').symlink_to(entry.parent, target_is_directory=True)
            for target in [links / 'absolute', links / 'relative', links / 'chain', links / 'directory' / entry.name]:
                with self.subTest(entry=entry.name, link=target.name):
                    code = self.source_code(shell, target)
                    p = self.shell(shell, code + code + probe)
                    self.assertEqual(p.stdout.splitlines(), expected)
                    self.assertEqual(p.stderr, '')
        # Relocation changes all derived paths; no contents or generated hooks change.
        old = self.repo
        self.repo = self.root / 'relocated ü checkout'
        old.rename(self.repo)
        probe, expected = self.portable_probe(shell)
        link = self.home / ('moved-' + self.portable_entrypoints(shell)[0].name)
        link.symlink_to(self.portable_entrypoints(shell)[0])
        p = self.shell(shell, self.source_code(shell, link) + probe)
        self.assertEqual(p.stdout.splitlines(), expected)
        self.assertEqual(p.stderr, '')

    def test_bash_portable_links(self): self.assert_portable_links('bash')
    def test_zsh_portable_links(self): self.assert_portable_links('zsh')
    def test_fish_portable_links(self): self.assert_portable_links('fish')
    def test_nu_portable_links(self): self.assert_portable_links('nu')
    def test_xonsh_portable_links(self): self.assert_portable_links('xonsh')
    def test_powershell_portable_links(self): self.assert_portable_links('powershell')

    def test_native_linked_startup(self):
        for shell in ('bash', 'zsh', 'fish', 'nu', 'xonsh'):
            with self.subTest(shell=shell):
                exe = shutil.which(shell)
                if not exe:
                    continue
                folder = SHELLS[shell][0]
                body = next((self.repo / 'shells' / folder).glob('interactive.*'))
                body.write_text('# test-owned interactive body\n')
                rc = self.portable_entrypoints(shell)[0]
                probe, expected = self.portable_probe(shell)
                if shell == 'bash':
                    link = self.home / '.bashrc'
                    args = ['--noprofile', '--rcfile', str(link), '-ic', probe]
                elif shell == 'zsh':
                    link = self.home / '.zshrc'
                    (self.home / '.zshenv').symlink_to(self.repo / 'shells/zsh/zshenv')
                    args = ['-d', '-ic', probe]
                elif shell == 'fish':
                    link = self.home / 'config/fish/config.fish'
                    args = ['-ic', probe]
                elif shell == 'nu':
                    link = self.home / 'config/nushell/config.nu'
                    args = ['--config', str(link), '--no-history', '-c', probe]
                else:
                    link = self.home / '.xonshrc'
                    args = ['--rc', str(link), '--shell-type', 'readline', '-ic', probe]
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(rc)
                master, slave = pty.openpty()
                try:
                    p = subprocess.run([exe, *args], cwd=self.home, env=self.env, stdin=slave,
                                       text=True, capture_output=True, timeout=30)
                finally:
                    os.close(master)
                    os.close(slave)
                self.assertEqual(p.returncode, 0, p.stderr)
                self.assertEqual(p.stdout.splitlines(), expected)

    def test_missing_checkout_does_not_fall_back(self):
        (self.repo / 'bin/dots').unlink()
        for shell in ('bash', 'zsh', 'fish', 'nu', 'xonsh'):
            with self.subTest(shell=shell):
                exe = shutil.which(shell)
                if not exe:
                    continue
                rc = self.portable_entrypoints(shell)[0]
                flags = {'bash': ['--noprofile', '--norc'], 'zsh': ['-df'], 'fish': ['--no-config'],
                         'nu': ['--no-config-file'], 'xonsh': ['--no-rc']}[shell]
                p = subprocess.run([exe, *flags, '-c', self.source_code(shell, rc)],
                                   env=self.env, cwd=self.home, text=True, capture_output=True, timeout=30)
                self.assertNotEqual(p.returncode, 0)
                self.assertEqual(p.stdout, '')
                self.assertIn('checkout layout' if shell != 'zsh' else 'resolvable Dots checkout', p.stderr)


    def test_unreadable_targets_and_symlink_loops(self):
        for shell in ('bash', 'zsh', 'fish', 'nu', 'xonsh'):
            exe = shutil.which(shell)
            if not exe:
                continue
            flags = {'bash': ['--noprofile', '--norc'], 'zsh': ['-df'], 'fish': ['--no-config'],
                     'nu': ['--no-config-file'], 'xonsh': ['--no-rc']}[shell]
            for kind in ('broken', 'loop', 'missing-parent'):
                with self.subTest(shell=shell, kind=kind):
                    link = self.root / (shell + '-' + kind)
                    target = link.name if kind == 'loop' else ('missing' if kind == 'broken' else 'missing/parent/file')
                    link.symlink_to(target)
                    p = subprocess.run([exe, *flags, '-c', self.source_code(shell, link)],
                                       env=self.env, cwd=self.home, text=True, capture_output=True, timeout=10)
                    # The shell rejects an unreadable entry before its body can execute.
                    self.assertNotEqual(p.returncode, 0)
                    self.assertEqual(p.stdout, '')
                    self.assertTrue(p.stderr)

    def test_bash_resolver_hop_limit_returns_to_caller(self):
        entry = self.repo / 'shells/bash/init.bash'
        # Invoke the resolver with a fake source identity: real kernels reject a
        # cyclic entry before any rc code can run, so exercise its guard directly.
        code = entry.read_text().split('_dots_bash_directory=')[0]
        loop = self.root / 'loop'
        loop.symlink_to('loop')
        import shlex
        p = self.shell('bash', code + '\n_dots_bash_source_dir ' + shlex.quote(str(loop)) +
                       '\nresult=$?\n[[ $result -ne 0 ]] || exit 9\nprintf "caller alive\\n"')
        self.assertEqual(p.stdout, 'caller alive\n')


if __name__ == '__main__':
    unittest.main()

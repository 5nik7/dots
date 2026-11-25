"""Exercise ordered profile-local code in the normal native prompt."""
from pathlib import Path
import os
import shutil
import subprocess
import unittest

if os.name != 'nt':
    from bench_shell_readiness import interactive_fixture, ROOT, wait_for_output
    from test_shell_init import executable
    from zsh_interactive import Session


def record(shell, stage):
    if shell == 'nu':
        return f'"{stage}\\n" | save --append ($nu.home-dir | path join stages)\n'
    if shell == 'xonsh':
        return f'with open($HOME + "/stages", "a") as _stage: _stage.write("{stage}\\n")\n'
    return f'echo {stage} >> "$HOME/stages"\n'


@unittest.skipIf(os.name == 'nt', 'Native Windows hooks are exercised by test_powershell_init.py')
class ProfileHooks(unittest.TestCase):
    def test_zsh_shipped_defaults_once_on_fresh_migrated_and_personal_homes(self):
        if not executable('zsh'):
            self.skipTest('Zsh unavailable')
        for profile in ('termux', 'wsl'):
            with self.subTest(profile=profile), interactive_fixture(ROOT, 'zsh', installed=True) as prepared:
                env, home, argv, _ = prepared
                prefix = str(home/('prefix/usr' if profile == 'termux' else 'prefix'))
                env.update(PREFIX=prefix, TERMUX__PREFIX=prefix, TERMUX_VERSION='test', USER='tester')
                if profile == 'wsl':
                    env['WSL_DISTRO_NAME'] = 'fixture'
                repo = Path(env['DOTS'])
                directory = Path('profiles')/profile/'shells'
                (repo/directory/'zsh').mkdir(parents=True)
                defaults = repo/directory/'zsh/local.zsh'
                shutil.copy2(ROOT/directory/'init.zsh', repo/directory/'init.zsh')
                shutil.copy2(ROOT/directory/'zsh/local.zsh', defaults)
                with defaults.open('a') as hook:
                    hook.write('\nprint -r -- profile >> "$HOME/stages"\n')
                (repo/directory/'local.zsh').write_text('print -r -- late >> "$HOME/stages"\n')
                (home/'.fzf.zsh').write_text('print -r -- fzf >> "$HOME/stages"\n')
                zinit = Path(env['XDG_DATA_HOME'])/'zinit/zinit.git'
                zinit.mkdir(parents=True)
                for plugin in ('Aloxaf/fzf-tab', 'jeffreytse/zsh-vi-mode', 'kutsan/zsh-system-clipboard'):
                    checkout = zinit.parent/'plugins'/plugin.replace('/', '---')
                    checkout.mkdir(parents=True)
                    (checkout/(plugin.split('/')[1] + '.plugin.zsh')).touch()
                (zinit/'zinit.zsh').write_text('''zinit() {
  if [[ $1 == light ]]; then print -r -- "$2" >> "$HOME/stages"; fi
  return 0
}
''')
                commands = Path(env['PATH'].split(os.pathsep)[0])
                (commands/'perl').symlink_to(executable('sh'))
                for tool in ('vfox', 'bob'):
                    shim = commands/tool
                    command = f'print -r -- {tool} >> "$HOME/stages"'
                    shim.write_text(f"#!{executable('sh')}\nprintf '%s\\n' '{command}'\n")
                    shim.chmod(0o700)
                perl = str(home/'perl5') if profile == 'termux' else '/home/njen/perl5'
                env.update(PERL5LIB=f'{perl}/lib/perl5:other::{perl}/lib/perl5',
                           PERL_LOCAL_LIB_ROOT=f'other:{perl}:{perl}')
                local = home/'.zshrc.local'
                for setup in ('fresh', 'migrated', 'personal'):
                    stages = home/'stages'
                    stages.write_text('')
                    if setup == 'migrated':
                        local.symlink_to(defaults)
                    elif setup == 'personal':
                        local.unlink()
                        local.write_text('print -r -- private >> "$HOME/stages"\nalias edit=personal-editor\n')
                    code = '''rlp >/dev/null || exit 1
print -r -- "$PERL5LIB" "$PERL_LOCAL_LIB_ROOT" "$aliases[edit]"
[[ -o sharehistory && ${+functions[setopt_if_exists]} == 0 ]]
'''
                    run = subprocess.run([argv[0], '-dic', code], cwd=home, env=env,
                                         capture_output=True, text=True, timeout=45)
                    self.assertEqual(run.returncode, 0, run.stderr)
                    self.assertEqual(run.stdout.strip(), f'{perl}/lib/perl5:other: {perl}:other ' +
                                     ('personal-editor' if setup == 'personal' else '$EDITOR'))
                    loaded = stages.read_text().splitlines()
                    self.assertEqual(loaded.count('profile'), 2)
                    self.assertEqual(loaded.count('private'), 2 if setup == 'personal' else 0)
                    self.assertEqual(loaded.count('late'), 2)
                    self.assertEqual(loaded.count('fzf'), 1)
                    self.assertLess(loaded.index('profile'), loaded.index('fzf'))
                    if setup == 'personal':
                        self.assertLess(loaded.index('profile'), loaded.index('private'))
                        self.assertLess(loaded.index('private'), loaded.index('fzf'))
                    self.assertLess(loaded.index('fzf'), loaded.index('Aloxaf/fzf-tab'))
                    self.assertLess(loaded.index('Aloxaf/fzf-tab'), loaded.index('late'))
                    for plugin in ('jeffreytse/zsh-vi-mode', 'kutsan/zsh-system-clipboard'):
                        self.assertEqual(loaded.count(plugin), int(profile == 'termux'))
                        if profile == 'termux':
                            self.assertLess(loaded.index(plugin), loaded.index('fzf'))
                    for tool in ('vfox', 'bob'):
                        self.assertEqual(loaded.count(tool), int(profile == 'wsl'))
                    self.assertFalse((home/'1').exists())

                if profile == 'termux':
                    from bench_shell_readiness import measure
                    measure('zsh', prepared)
                    self.assertFalse((home/'1').exists())
                    self.assertFalse((home/'readiness-directory/1').exists())

    def test_first_input_observes_parent_then_active_configuration(self):
        for shell in ('bash', 'zsh', 'fish', 'nu', 'xonsh'):
            if not executable(shell):
                continue
            for installed in ((True, False) if shell == 'nu' else (True,)):
                with self.subTest(shell=shell, installed=installed):
                    self.check(shell, installed)

    def check(self, shell, installed):
        with interactive_fixture(ROOT, shell, installed=installed) as (env, home, argv, _):
            env['PREFIX'] = env['TERMUX__PREFIX'] = str(home/'prefix')
            env['WSL_DISTRO_NAME'] = 'profile-order-fixture'
            repo = Path(env['DOTS'])
            ext = 'xsh' if shell == 'xonsh' else shell
            for profile in ('linux', 'wsl'):
                directory = repo/'profiles'/profile/'shells'
                directory.mkdir(parents=True)
                for phase in ('init', 'local'):
                    (directory/f'{phase}.{ext}').write_text(record(shell, f'{phase}-{profile}'))
            family = 'nushell' if shell == 'nu' else shell
            with (repo/'shells'/family/f'interactive.{ext}').open('a') as body:
                body.write('\n' + record(shell, 'shared'))
            session = Session(env, home, argv=argv)
            try:
                if shell == 'xonsh':
                    wait_for_output(session, b'\x1b[?2004h')
                # The resulting value cannot be present in terminal input echo.
                command = {'nu': "print ('COMPLETE_' + $env.DOTS_PLATFORM)",
                           'xonsh': "print('COMPLETE_' + $DOTS_PLATFORM)"}.get(
                               shell, """printf 'COMPLETE_%s\\n' "$DOTS_PLATFORM" """)
                session.send(command + '\r')
                wait_for_output(session, b'COMPLETE_wsl')
                self.assertEqual((home/'stages').read_text().splitlines(),
                                 ['init-linux', 'init-wsl', 'shared', 'local-linux', 'local-wsl'])
            finally:
                session.send('exit\r')
                try:
                    session.process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    pass
                session.close()


if __name__ == '__main__':
    unittest.main()

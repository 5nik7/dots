"""Check native optional hooks through the first input of both public Nu entries."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

if os.name != 'nt':
    from bench_shell_readiness import interactive_fixture, wait_for_output
    from zsh_interactive import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib/dots'))
from shell.nu_tools import GENERATORS, prepare


def install_command(path, text):
    path.write_text(f'#!{sys.executable}\n' + text, encoding='utf-8')
    path.chmod(0o700)


def run_probe(env, home, argv, command, after_cd=False):
    session = Session(env, home, argv=argv)
    try:
        session.send(command + "; print ('PROBE_' + 'COMPLETE')\r")
        startup = wait_for_output(session, b'PROBE_COMPLETE', timeout=20)
        result = json.loads((home/'result.json').read_text())
        if after_cd:
            session.send("cd readiness-directory; print ('MOVED_' + 'DIR')\r")
            wait_for_output(session, b'MOVED_DIR')
            session.send("print ('DIRENV_' + $env.DIRENV_FIXTURE)\r")
            wait_for_output(session, b'DIRENV_readiness-directory')
        return result, startup
    finally:
        session.send('exit\r')
        try:
            session.process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            pass
        session.close()


@unittest.skipUnless(os.name != 'nt' and shutil.which('nu'), 'native Nu PTY unavailable')
class OptionalTools(unittest.TestCase):
    def test_emitted_integration_runs_no_optional_generator(self):
        with interactive_fixture(ROOT, 'nu', installed=False) as (env, home, argv, _):
            directory = Path(env['PATH'])
            for name in (*GENERATORS, 'direnv'):
                install_command(directory/name, 'from pathlib import Path\n'
                                f'Path({str(home/"generator-ran")!r}).touch()\n')
            entry = home/'integration.nu'
            command = Path(env['DOTS'])/'bin/dots'
            emitted = subprocess.run([command, 'init', 'nu'], env=env, cwd=home,
                                     text=True, capture_output=True, check=True)
            entry.write_text(emitted.stdout)
            argv[argv.index('--config') + 1] = str(entry)
            data, _ = run_probe(env, home, argv, '{bin: $env.DOTBIN} | save ($nu.home-dir | path join result.json)')
            self.assertEqual(data['bin'], str(Path(env['DOTS'])/'bin'))
            self.assertFalse((home/'generator-ran').exists())

    def test_default_keeps_user_jumps_without_provider_processes(self):
        with interactive_fixture(ROOT, 'nu', installed=True) as (env, home, argv, _):
            commands = Path(env['PATH'])
            for name in (*GENERATORS, 'direnv'):
                install_command(commands/name, 'from pathlib import Path\n'
                                f'Path({str(home/"generator-ran")!r}).touch()\n')
            for profile in ('linux','termux'):
                directory = Path(env['DOTS'])/'profiles'/profile/'shells'
                directory.mkdir(exist_ok=True)
                (directory/'init.nu').write_text('def z [] { "my jump" }\ndef zi [] { "my interactive jump" }\n')
            data, _ = run_probe(env, home, argv, '[ (z) (zi) ] | save ($nu.home-dir | path join result.json)')
            self.assertEqual(data, ['my jump','my interactive jump'])
            self.assertFalse((home/'generator-ran').exists())

    def test_missing_failed_and_unselected_generators(self):
        with interactive_fixture(ROOT, 'nu', installed=True) as (env, home, _, _):
            directory = Path(env['PATH'])
            for name in ('atuin', 'zoxide'):
                install_command(directory/name, 'import sys\nfrom pathlib import Path\n'
                                f'Path({str(home/name)!r}).touch()\nsys.exit(1)\n')
            self.assertEqual(prepare(['atuin','zoxide'], env), dict(loaded=[], hooks=[]))
            self.assertTrue((home/'zoxide').exists())
            self.assertFalse((home/'atuin').exists())

    def test_bindings_native_commands_prompt_path_and_direnv(self):
        for installed in (True, False):
            with self.subTest(installed=installed), interactive_fixture(ROOT, 'nu', installed=installed) as (env, home, argv, _):
                directory = Path(env['PATH'])
                commands = {
                    'zoxide': 'def z [] { "jump" }',
                    'mise': ('export-env { $env.__MISE_ORIG_PATH = ($env.PATH | str join (char esep)); '
                             '$env.PATH = ($env.PATH | prepend "/fixture-shims") }\nexport def main [] { "managed" }'),
                    'starship': 'export-env { $env.PROMPT_COMMAND = {|| "generated "}; $env.STARSHIP_SHELL = "nu" }',
                    'atuin': 'def fixture_atuin [] { "history" }',
                    'tv': ('def tv_smart_autocomplete [] { "television" }\n'
                           '$env.config.keybindings = ($env.config.keybindings | append '
                           '{name: tv_conflict, modifier: control, keycode: char_t, mode: emacs, event: {edit: complete}} '
                           '| append {name: tv_added, modifier: alt, keycode: char_q, mode: emacs, event: {edit: complete}})'),
                }
                for name, source in commands.items():
                    install_command(directory/name, 'import sys\nfrom pathlib import Path\n'
                                    f'assert sys.argv[1:] == {GENERATORS[name]!r}\n'
                                    f'with Path({str(home/"calls")!r}).open("a") as log: log.write({name!r}+"\\n")\n'
                                    f'print({source!r})')
                install_command(directory/'direnv', 'import os,json,sys\nassert sys.argv[1:] == ["export","json"]\n'
                                'print(json.dumps({"DIRENV_FIXTURE":os.path.basename(os.getcwd()), "GONE":None, "PATH":os.environ["PATH"]}))\n')
                install_command(directory/'fzf', '')
                if installed:
                    optin = home/'.atuin/bin/env'
                    optin.parent.mkdir(parents=True)
                    optin.touch()
                env['GONE'] = 'clear this'
                repo = Path(env['DOTS'])
                for profile in ('linux', 'termux'):
                    profile_dir = repo/'profiles'/profile/'shells'
                    profile_dir.mkdir(exist_ok=True)
                    (profile_dir/'init.nu').write_text("$env.dots_shell_tools = ['all']\n")
                    data = '$env.PATH = ($env.PATH | prepend "/fixture-profile")\n'
                    if installed:
                        data += '$env.PROMPT_COMMAND = {|| "retained "}\n'
                    (profile_dir/'local.nu').write_text(data)
                command = ('{z: (z), mise: (mise), tv: (tv_smart_autocomplete), '
                           'atuin: (which fixture_atuin | is-not-empty), marked: ($env.STARSHIP_SHELL? | default ""), '
                           'prompt: (do $env.PROMPT_COMMAND), bind: ($env.config.keybindings | get name), '
                           'pwd: $env.DIRENV_FIXTURE, gone: ("GONE" not-in $env), path: $env.PATH, '
                           'pending: ($env.config.hooks.pre_prompt | where {|h| ($h | describe) == string} '
                           '| where {|h| $h | str starts-with "# dots optional integration"} | length)} '
                           '| to json | save ($nu.home-dir | path join result.json)')
                result, output = run_probe(env, home, argv, command, after_cd=True)
                self.assertNotIn(b'Error:', output)
                self.assertNotIn(b'Welcome to ', output)
                self.assertEqual((result['z'], result['mise'], result['tv']), ('jump', 'managed', 'television'))
                self.assertEqual(result['atuin'], installed)
                self.assertEqual(result['prompt'], 'retained ' if installed else 'generated ')
                self.assertEqual(result['marked'], '' if installed else 'nu')
                self.assertIn('fzf_files', result['bind'])
                self.assertIn('tv_added', result['bind'])
                self.assertNotIn('tv_conflict', result['bind'])
                self.assertEqual((result['pwd'], result['gone'], result['pending']), (home.name, True, 0))
                self.assertTrue({'/fixture-shims', '/fixture-profile'} <= set(result['path']))
                skipped = 'starship' if installed else 'atuin'
                self.assertCountEqual((home/'calls').read_text().splitlines(),
                                      [tool for tool in GENERATORS if tool != skipped])

    @unittest.skipUnless(all(shutil.which(t) for t in [*GENERATORS, 'direnv', 'fzf']), 'optional programs unavailable')
    def test_installed_native_generators(self):
        with interactive_fixture(ROOT, 'nu', installed=True, with_tools=True, enable_native_tools=True) as (env, home, argv, _):
            env.update(MISE_OFFLINE='true', MISE_AUTO_INSTALL='false', ATUIN_NOBIND='true')
            for name in ('mise', 'tv', 'atuin'):
                (Path(env['PATH'])/name).symlink_to(shutil.which(name))
            optin = home/'.atuin/bin/env'
            optin.parent.mkdir(parents=True)
            optin.touch()
            data, _ = run_probe(env, home, argv,
                                '{z: (which z | get type), mise: (which mise | get type), tv: (which tv_smart_autocomplete | get type), '
                                'atuin: (which _atuin_search_cmd | get type), starship: $env.STARSHIP_SHELL?, '
                                'fzf: ($env.config.keybindings | get name | where {|n| $n == fzf_files} | length)} '
                                '| to json | save ($nu.home-dir | path join result.json)')
            for name in ('z', 'mise', 'tv', 'atuin'):
                self.assertTrue({'custom', 'alias'} & set(data[name]), (name, data))
            self.assertEqual(data['starship'], 'nu')
            self.assertEqual(data['fzf'], 1)


if __name__ == '__main__':
    unittest.main()

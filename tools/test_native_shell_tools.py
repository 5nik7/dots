"""Native shell tool activation and reload in test-owned directories."""
import collections
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
FISH = shutil.which('fish')
XONSH = shutil.which('xonsh')


class NativeTools(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='dots-native-tools-')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.bin = self.home / 'bin ü'
        self.bin.mkdir()
        self.env = dict(HOME=str(self.home), USERPROFILE=str(self.home), DOTS=str(REPO),
                        PATH=str(self.bin), TMPDIR=str(self.home), TEMP=str(self.home), TMP=str(self.home),
                        XDG_CONFIG_HOME=str(self.home / 'config'), XDG_STATE_HOME=str(self.home / 'state'),
                        XDG_DATA_HOME=str(self.home / 'data'), XDG_CACHE_HOME=str(self.home / 'cache'),
                        APPDATA=str(self.home / 'appdata'), LOCALAPPDATA=str(self.home / 'localappdata'),
                        XONTRIBS_AUTOLOAD_DISABLED='*', XONSH_HISTORY_BACKEND='dummy', XONSH_SHOW_TRACEBACK='1',
                        POWERSHELL_TELEMETRY_OPTOUT='1', POWERSHELL_UPDATECHECK='Off',
                        FZF_DEFAULT_OPTS='--height=37%', TERM='xterm-256color', NO_COLOR='1')
        for key in ('LD_PRELOAD', 'PREFIX', 'TERMUX_VERSION', 'ANDROID_ROOT', 'ANDROID_DATA',
                    'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'PATHEXT'):
            if key in os.environ:
                self.env[key] = os.environ[key]

    def run_shell(self, *argv, timeout=30):
        if argv[0] == XONSH:
            self.env['PYTHONPATH'] = str(REPO / 'lib/dots')
        result = subprocess.run(argv, cwd=self.home, env=self.env, stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, timeout=timeout)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        return result

    def write_provider(self, name, code):
        path = self.bin / name
        path.write_text(f'#!{sys.executable}\n' +
                        "from pathlib import Path\nimport json, os, sys, time\n"
                        "home = Path(os.environ['HOME'])\n"
                        "with (home / 'calls').open('a') as out:\n"
                        "    print(json.dumps([Path(sys.argv[0]).name, *sys.argv[1:]]), file=out)\n" +
                        code + '\n')
        path.chmod(0o700)

    def calls(self):
        return collections.Counter(tuple(json.loads(row)) for row in
                                   (self.home / 'calls').read_text().splitlines())

    @unittest.skipUnless(FISH and os.name == 'posix', 'Fish with POSIX provider fixtures required')
    def test_fish_failed_output_retry_once_and_preserve_controls(self):
        self.write_provider('mise', '''
if not (home / 'retry').exists():
    print('set -g PARTIAL_RAN yes')
    sys.exit(1)
print('set -g mise_active yes')
''')
        self.write_provider('zoxide', "print('set -g zoxide_active yes')")
        self.write_provider('starship', "print('function fish_prompt; echo wrong; end')")
        self.write_provider('atuin', "print('set -g atuin_active yes')")
        self.write_provider('tv', '''
print('function tv_smart_autocomplete; end')
print('bind --user ctrl-r tv_smart_autocomplete')
print('bind --user -M insert ctrl-t tv_smart_autocomplete')
''')
        result = self.run_shell(FISH, '--no-config', '-i', '-c', '''
function fish_prompt; echo original; end
bind --user ctrl-r history-search-backward
bind --user -M insert ctrl-t transpose-chars
source "$DOTS/lib/dots/shell/tools.fish" all
set -q PARTIAL_RAN; and exit 1
echo yes > "$HOME/retry"
source "$DOTS/lib/dots/shell/tools.fish" all
source "$DOTS/lib/dots/shell/tools.fish" all
test "$mise_active:$atuin_active:$zoxide_active" = yes:yes:yes; or exit 2
test (fish_prompt) = original; or exit 3
test "$FZF_DEFAULT_OPTS" = '--height=37%'; or exit 4
bind --user ctrl-r
bind --user -M insert ctrl-t
''')
        self.assertIn('history-search-backward', result.stdout)
        self.assertIn('transpose-chars', result.stdout)
        self.assertEqual(self.calls(), {('mise', 'activate', 'fish'): 2, ('zoxide', 'init', 'fish'): 1,
                                        ('atuin', 'init', 'fish', '--disable-up-arrow', '--disable-ctrl-r'): 1,
                                        ('tv', 'init', 'fish'): 1})

    @unittest.skipUnless(XONSH and os.name == 'posix', 'Xonsh with POSIX provider fixtures required')
    def test_xonsh_direnv_retry_literal_path_recovery_and_reload(self):
        self.write_provider('direnv', '''
mode = (home / 'mode').read_text()
if mode == 'timeout':
    time.sleep(20)
elif mode == 'bad-shape':
    print(json.dumps({'EARLY': 'lost', 'BAD': [1]}))
elif mode == 'typed':
    print(json.dumps({'EARLY': 'lost', 'DIRSTACK_SIZE': 'non-numeric'}))
elif mode == 'fail':
    print(json.dumps({'EARLY': 'lost'}))
    sys.exit(1)
elif mode == 'bad-json':
    print('not JSON')
else:
    print(json.dumps({'DOTS_LITERAL': "-ü ' $(bad)\\nsecond", 'EARLY': None,
                      'PATH': str(home / 'extra ü') + os.pathsep + os.environ['PATH']}))
''')
        self.write_provider('mise', '''
if (home / 'mode').read_text() == 'timeout':
    print("partial_ran = True")
    sys.exit(1)
print("mise_active = True")
''')
        self.write_provider('zoxide', "print('zoxide_active = True')")
        self.write_provider('starship', "print('$PROMPT = \"wrong\"')")
        (self.home / 'mode').write_text('timeout')
        result = self.run_shell(XONSH, '--no-rc', '-c', '''
from pathlib import Path
$PROMPT = 'original'
$EARLY = 'kept'
from shell.xonsh_tools import activate
dots_shell_tools = ['all']
activate(__xonsh__, events)
assert 'partial_ran' not in __xonsh__.ctx
hooks = len(events.on_chdir)
for mode in ('bad-json', 'bad-shape', 'typed', 'fail'):
    (Path($HOME) / 'mode').write_text(mode)
    events.on_chdir.fire(olddir=$HOME, newdir=$HOME)
    assert $EARLY == 'kept'
(Path($HOME) / 'mode').write_text('good')
from shell.xonsh_tools import activate
dots_shell_tools = ['all']
activate(__xonsh__, events)
from shell.xonsh_tools import activate
dots_shell_tools = ['all']
activate(__xonsh__, events)
assert hooks == len(events.on_chdir)
events.on_chdir.fire(olddir=$HOME, newdir=$HOME)
assert $DOTS_LITERAL == "-ü ' $(bad)\\nsecond"
assert not __xonsh__.env.is_manually_set('EARLY')
assert list($PATH) == [str(Path($HOME) / 'extra ü'), str(Path($HOME) / 'bin ü')]
assert __xonsh__.ctx['mise_active'] and __xonsh__.ctx['zoxide_active']
assert $PROMPT == 'original' and $FZF_DEFAULT_OPTS == '--height=37%'
''')
        self.assertIn('TimeoutExpired', result.stderr)
        self.assertIn('JSONDecodeError', result.stderr)
        self.assertIn('ValueError', result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        self.assertEqual(self.calls(), {('direnv', 'export', 'json'): 6, ('zoxide', 'init', 'xonsh'): 1,
                                        ('mise', 'activate', 'xonsh'): 2})

    @unittest.skipUnless(FISH and XONSH and shutil.which('zoxide') and os.name == 'posix',
                         'native Fish, Xonsh and zoxide required')
    def test_default_full_shell_defers_zoxide_until_first_jump(self):
        from test_shell_init import InitTests
        fixture = InitTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.minimal_tools()
        target = fixture.home / 'target ü'
        target.mkdir()
        for name in ('mise', 'direnv', 'starship', 'tv', 'atuin'):
            self.write_provider(name, 'sys.exit(9)')
        self.write_provider('zoxide', f"os.execv({shutil.which('zoxide')!r}, sys.argv)")
        fixture.env['PATH'] = str(self.bin) + os.pathsep + fixture.env['PATH']
        fixture.env['FZF_DEFAULT_OPTS'] = '--height=37%'
        for shell in ('fish', 'xonsh'):
            with self.subTest(shell=shell):
                calls = fixture.home / 'calls'
                calls.unlink(missing_ok=True)
                startup = ('source "$DOTS/shells/fish/init.fish"\n' if shell == 'fish' else
                           "source @($DOTS + '/shells/xonsh/init.xsh')\n")
                check = ("""
if test -e "$HOME/calls"; cat "$HOME/calls"; exit 1; end
z "$HOME/target ü"; or exit 2
test "$PWD" = "$HOME/target ü"; or exit 3
functions -q __zoxide_hook; or exit 4
test "$FZF_DEFAULT_OPTS" = '--height=37%'; or exit 5
""" if shell == 'fish' else """
from pathlib import Path
assert not (Path($HOME) / 'calls').exists()
z @($HOME + '/target ü')
assert str(Path.cwd()) == $HOME + '/target ü', $PWD
assert 'zoxide' in __xonsh__.ctx['_dots_xonsh_tools']
assert $FZF_DEFAULT_OPTS == '--height=37%'
""")
                fixture.shell(shell, startup + startup + check, interactive=True)
                rows = [json.loads(line) for line in calls.read_text().splitlines()]
                self.assertEqual([row for row in rows if row[:2] == ['zoxide', 'init']],
                                 [['zoxide', 'init', shell] + (['--no-cmd'] if shell == 'fish' else [])])
                self.assertTrue(all(row[0] == 'zoxide' for row in rows), rows)

    @unittest.skipUnless(FISH and os.name == 'posix', 'native Fish required')
    def test_real_fish_integrations(self):
        names = ('zoxide', 'direnv', 'mise', 'starship', 'atuin', 'tv')
        if not all(shutil.which(name) for name in names):
            self.skipTest('requires ' + ', '.join(names))
        self.env['PATH'] = os.pathsep.join(dict.fromkeys(str(Path(shutil.which(n)).parent) for n in names))
        result = self.run_shell(FISH, '--no-config', '-i', '-c', '''
source "$DOTS/lib/dots/shell/tools.fish" all
set -l first $PATH
source "$DOTS/lib/dots/shell/tools.fish" all
test (string join : $first) = (string join : $PATH); or exit 1
functions -q __zoxide_hook __direnv_export_eval __mise_env_eval __starship_set_job_count _atuin_preexec tv_smart_autocomplete; or exit 2
test "$STARSHIP_SHELL" = fish; or exit 3
test "$FZF_DEFAULT_OPTS" = '--height=37%'; or exit 4
''')
        self.assertNotIn('Unknown command', result.stderr)

    @unittest.skipUnless(XONSH and os.name == 'posix', 'native Xonsh required')
    def test_real_xonsh_integrations_and_directory_changes(self):
        names = ('zoxide', 'direnv', 'mise', 'starship', 'atuin', 'bash')
        if not all(shutil.which(name) for name in names):
            self.skipTest('requires ' + ', '.join(names))
        self.env['PATH'] = os.pathsep.join(dict.fromkeys(str(Path(shutil.which(n)).parent) for n in names))
        project = self.home / 'work ü'
        project.mkdir()
        (project / '.envrc').write_text("export NATIVE_DIRENV='literal ü'\n")
        self.run_shell(shutil.which('direnv'), 'allow', str(project))
        result = self.run_shell(XONSH, '--no-rc', '-c', '''
from pathlib import Path
from shell.xonsh_tools import activate
dots_shell_tools = ['all']
activate(__xonsh__, events)
import importlib.util
expected = {'zoxide','direnv','mise','starship'}
if importlib.util.find_spec('prompt_toolkit'):
    expected.add('atuin')
assert expected == __xonsh__.ctx.get('_dots_xonsh_tools'), __xonsh__.ctx.get('_dots_xonsh_tools')
assert 'z' in aliases and 'mise' in aliases and callable($PROMPT)
assert $STARSHIP_SHELL == 'xonsh' and $FZF_DEFAULT_OPTS == '--height=37%'
before = (list($PATH), len(events.on_chdir), len(events.on_pre_prompt))
from shell.xonsh_tools import activate
dots_shell_tools = ['all']
activate(__xonsh__, events)
assert before == (list($PATH), len(events.on_chdir), len(events.on_pre_prompt))
cd @(str(Path($HOME) / 'work ü'))
assert $NATIVE_DIRENV == 'literal ü'
cd @($HOME)
assert not __xonsh__.env.is_manually_set('NATIVE_DIRENV')
''')
        self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()

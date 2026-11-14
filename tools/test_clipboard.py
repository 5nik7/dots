#!/usr/bin/env python3
"""Clipboard contracts in owned roots; never call the host clipboard providers."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib/dots'))
import clipboard


class Providers(unittest.TestCase):
    def select(self, platform, available, operation='write', **environment):
        with patch('clipboard.detect', return_value={'platform': platform}), \
                patch.dict(os.environ, environment, clear=True), \
                patch('clipboard.shutil.which', side_effect=lambda name: '/fixture/' + name if name in available else None):
            return clipboard._provider(operation)

    def test_termux_ignores_other_platform_tools(self):
        tools = ['termux-clipboard-set', 'termux-clipboard-get', 'pwsh.exe', 'xclip', 'wl-copy']
        self.assertEqual(self.select('termux', tools, DISPLAY=':0'), ['/fixture/termux-clipboard-set'])
        self.assertEqual(self.select('termux', tools, 'read'), ['/fixture/termux-clipboard-get'])
        with self.assertRaisesRegex(ValueError, 'termux-api'):
            self.select('termux', ['pwsh.exe', 'xclip'], DISPLAY=':0')

    def test_linux_session_selection_and_missing_tool_fallback(self):
        available = ['wl-copy', 'wl-paste', 'xclip', 'xsel', 'termux-clipboard-set']
        self.assertEqual(self.select('linux', available, WAYLAND_DISPLAY='wayland-0', DISPLAY=':0'),
                         ['/fixture/wl-copy', '--type', 'text/plain;charset=utf-8'])
        self.assertEqual(self.select('linux', available, 'read', WAYLAND_DISPLAY='wayland-0'),
                         ['/fixture/wl-paste', '--no-newline', '--type', 'text'])
        self.assertEqual(self.select('linux', ['xclip'], WAYLAND_DISPLAY='wayland-0', DISPLAY=':0'),
                         ['/fixture/xclip', '-selection', 'clipboard', '-in'])
        self.assertEqual(self.select('linux', ['xclip'], 'read', DISPLAY=':0'),
                         ['/fixture/xclip', '-selection', 'clipboard', '-out'])
        self.assertEqual(self.select('linux', ['xsel'], DISPLAY=':0'),
                         ['/fixture/xsel', '--clipboard', '--input'])
        self.assertEqual(self.select('linux', ['xsel'], 'read', DISPLAY=':0'),
                         ['/fixture/xsel', '--clipboard', '--output'])
        with self.assertRaisesRegex(ValueError, 'Clipboard unavailable'):
            self.select('linux', available)

    def test_windows_and_wsl_use_windows_clipboard(self):
        for platform, names in [('windows', ['pwsh', 'powershell']), ('wsl', ['pwsh.exe', 'powershell.exe'])]:
            for selected in range(2):
                tools = names[selected:] + ['wl-copy', 'xclip', 'win32yank.exe']
                for operation in ('read', 'write'):
                    command = self.select(platform, tools, operation, WAYLAND_DISPLAY='wayland-0', DISPLAY=':0')
                    self.assertEqual(command[0], '/fixture/' + names[selected])
                    self.assertIn('-NoProfile', command)
                    self.assertIn('UTF8Encoding($false)', command[-1])
                    self.assertIn('Get-Clipboard -Raw' if operation == 'read' else 'Set-Clipboard', command[-1])
            self.assertEqual(self.select(platform, ['win32yank.exe']), ['/fixture/win32yank.exe', '-i'])
            self.assertEqual(self.select(platform, ['win32yank.exe'], 'read'), ['/fixture/win32yank.exe', '-o'])
            with self.assertRaisesRegex(ValueError, 'Clipboard unavailable'):
                self.select(platform, ['wl-copy', 'xclip'], DISPLAY=':0')

    def test_failures_are_bounded_and_never_retry_or_reveal_text(self):
        failures = [subprocess.TimeoutExpired('fake', 8, output=b'secret'), OSError('secret')]
        for failure in failures:
            with patch('clipboard._provider', return_value=['/fixture/provider']), \
                    patch('clipboard.subprocess.run', side_effect=failure) as run:
                with self.assertRaises(ValueError) as caught:
                    clipboard.copy('secret')
                self.assertNotIn('secret', str(caught.exception))
                self.assertEqual(run.call_count, 1)
                self.assertEqual(run.call_args.kwargs['timeout'], 8)
        with patch('clipboard._provider', return_value=['/fixture/provider']), \
                patch('clipboard.subprocess.run', return_value=subprocess.CompletedProcess([], 7, stderr=b'secret')) as run:
            with self.assertRaisesRegex(ValueError, 'exit 7') as caught:
                clipboard.paste()
            self.assertNotIn('secret', str(caught.exception))
            self.assertEqual(run.call_count, 1)

    def test_copy_api_preserves_literal_utf8(self):
        self.addCleanup(patch.stopall)
        patch('clipboard._record_copy').start()
        with patch('clipboard._provider', return_value=['/fixture/provider']), \
                patch('clipboard.subprocess.run', return_value=subprocess.CompletedProcess([], 0)) as run:
            clipboard.copy('café 雪\n$(touch nope)\r\n\n')
            self.assertEqual(run.call_args.kwargs['input'], 'café 雪\n$(touch nope)\r\n\n'.encode())

    def test_help_and_invalid_arguments_do_not_probe_or_read(self):
        with patch('clipboard._provider', side_effect=AssertionError('provider probed')):
            def no_read():
                raise AssertionError('stdin read')
            for name in ('cpy', 'pst'):
                for flag in ('-h', '--help'):
                    help_text = clipboard._execute(name, [flag], no_read).decode()
                    self.assertIn('Usage: ' + name, help_text)
                    for width in (40, 80, 120):
                        self.assertTrue(all(len(line) <= width for line in help_text.splitlines()))
                with self.assertRaises(clipboard.UsageError):
                    clipboard._execute(name, ['--bad'], no_read)
            with self.assertRaises(clipboard.UsageError):
                clipboard._execute('pst', ['unexpected'], no_read)


@unittest.skipIf(os.name == 'nt', 'POSIX executable fixtures; native Windows tests are separate')
class Commands(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='dots-clipboard-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / 'checkout 雪 with spaces'
        files = ['scripts/cpy', 'scripts/pst', 'scripts/cpy.ps1', 'scripts/pst.ps1',
                 'profiles/termux/bin/cpy', 'profiles/termux/bin/pst',
                 'lib/dots/clipboard.py', 'lib/dots/clipboard.ps1', 'lib/dots/platform_info.py',
                 'shells/powershell/helpers.ps1']
        for name in files:
            destination = self.repo / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, destination)
        # Help shares the current public presentation/preferences dependency
        # graph. Keep provider PATH isolated below, but do not freeze imports.
        from public_fixture import copy_public_tree
        shutil.rmtree(self.repo / 'lib/dots')
        copy_public_tree(ROOT / 'lib/dots', self.repo / 'lib/dots',
                         repo=ROOT, fixture=self.repo, exclude=('__pycache__',))
        self.bin = self.base / 'tools'
        self.bin.mkdir()
        self.home = self.base / 'home'
        self.home.mkdir()
        self.data = self.base / 'clipboard'
        self.calls = self.base / 'calls'
        # Only allowlisted runtimes/utilities enter PATH. A missing fake provider
        # cannot fall through to a real system clipboard tool.
        for name in ('bash', 'readlink', 'python3'):
            target = sys.executable if name == 'python3' else shutil.which(name)
            if not target:
                self.skipTest('missing ' + name)
            (self.bin / name).symlink_to(target)
        self.env = dict(HOME=str(self.home), PATH=os.pathsep.join(map(str, [self.repo/'scripts', self.repo/'profiles/termux/bin', self.bin])),
                        XDG_CONFIG_HOME=str(self.home/'config'), XDG_STATE_HOME=str(self.home/'state'),
                        XDG_CACHE_HOME=str(self.home/'cache'), XDG_DATA_HOME=str(self.home/'data'),
                        PREFIX=str(self.base/'com.termux/files/usr'), TERMUX_VERSION='fixture',
                        DOTS=str(self.base/'stale checkout'), FIXTURE_CLIPBOARD=str(self.data),
                        FIXTURE_CALLS=str(self.calls), DOTS_COLOR='always', DOTS_ICONS='always',
                        LC_ALL='C.UTF-8', PYTHONDONTWRITEBYTECODE='1')
        # Termux's exec adapter resolves /usr/bin/env shebangs on Android.
        for name in ('LD_PRELOAD', 'LD_LIBRARY_PATH', 'TERMUX_EXEC__SYSTEM_LINKER_EXEC'):
            if name in os.environ:
                self.env[name] = os.environ[name]
        fake = '''#!PYTHON
import os, pathlib, sys
with open(os.environ['FIXTURE_CALLS'], 'a') as out: out.write(pathlib.Path(sys.argv[0]).name + '\\n')
if os.environ.get('FIXTURE_FAIL'):
    print('private provider error', file=sys.stderr)
    raise SystemExit(9)
path = pathlib.Path(os.environ['FIXTURE_CLIPBOARD'])
if sys.argv[0].endswith('-set'): path.write_bytes(sys.stdin.buffer.read())
else: sys.stdout.buffer.write(path.read_bytes())
'''.replace('PYTHON', sys.executable)
        for name in ('termux-clipboard-set', 'termux-clipboard-get'):
            target = self.bin / name
            target.write_text(fake)
            target.chmod(0o700)

    def run_cmd(self, command, *args, data=b'', **kwargs):
        return subprocess.run([str(command), *args], input=data, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, env=self.env, cwd=self.base, timeout=15, **kwargs)

    def test_stream_round_trips_preserve_empty_unicode_and_newlines(self):
        for data in (b'', b'no newline', b'a\r\nb\n\n', ' \t雪 café 🐈\n'.encode(), b'$(touch nope); `x` \\n'):
            copied = self.run_cmd('cpy', data=data)
            self.assertEqual((copied.returncode, copied.stdout, copied.stderr), (0, b'', b''))
            pasted = self.run_cmd('pst')
            self.assertEqual((pasted.returncode, pasted.stdout, pasted.stderr), (0, data, b''))
        self.assertFalse((self.base/'nope').exists())

    def test_arguments_are_literal_and_override_stdin(self):
        for args, expected in [(('',), b''), (('one', 'two'), b'one two'),
                               (('--', '-h', '雪', '"', '$()'), '-h 雪 " $()'.encode())]:
            result = self.run_cmd('cpy', *args, data=b'ignored')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(self.data.read_bytes(), expected)
        result = self.run_cmd('cpy', '--', data=b'stdin')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.data.read_bytes(), b'stdin')

    def test_direct_profile_relative_and_symlinked_launchers(self):
        links = self.base / 'links'
        links.mkdir()
        for command in ('cpy', 'pst'):
            (links/command).symlink_to(os.path.relpath(self.repo/'scripts'/command, links))
            (links/(command+'-profile')).symlink_to(os.path.relpath(self.repo/'profiles/termux/bin'/command, links))
        for location in (self.repo/'scripts', links):
            self.assertEqual(self.run_cmd(location/'cpy', 'linked').returncode, 0)
            self.assertEqual(self.run_cmd(location/'pst').stdout, b'linked')
        for source in (self.repo/'profiles/termux/bin', links):
            suffix = '-profile' if source == links else ''
            # sh invocation permits these Termux-specific shebangs in Linux CI.
            copied = self.run_cmd(shutil.which('sh'), str(source/('cpy'+suffix)), 'profile')
            self.assertEqual(copied.returncode, 0, copied.stderr)
            pasted = self.run_cmd(shutil.which('sh'), str(source/('pst'+suffix)))
            self.assertEqual(pasted.stdout, b'profile', pasted.stderr)
        relative = os.path.relpath(self.repo/'scripts/cpy', self.base)
        self.assertEqual(self.run_cmd(shutil.which('bash'), relative, 'relative').returncode, 0)
        self.assertEqual(self.data.read_bytes(), b'relative')

    def test_bash_zsh_and_fish_find_shared_commands(self):
        for shell in ('bash', 'zsh', 'fish'):
            executable = shutil.which(shell)
            if not executable:
                continue
            flags = ['--no-config'] if shell == 'fish' else (['--noprofile', '--norc'] if shell == 'bash' else ['-f'])
            result = self.run_cmd(executable, *flags, '-c', 'command -v cpy; printf shell | cpy; pst')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, str(self.repo/'scripts/cpy').encode() + b'\nshell')

    def test_help_errors_and_missing_providers_do_not_access_clipboard(self):
        for command in ('cpy', 'pst'):
            for args, code in [(('--help',), 0), (('--bad',), 2)]:
                result = self.run_cmd(command, *args)
                self.assertEqual(result.returncode, code, result.stderr)
        self.assertFalse(self.calls.exists())
        for path in self.bin.glob('termux-clipboard-*'):
            path.unlink()
        result = self.run_cmd('cpy', 'private contents')
        self.assertEqual(result.returncode, 1)
        self.assertIn(b'termux-api', result.stderr)
        self.assertNotIn(b'private contents', result.stderr)
        self.assertEqual(result.stdout, b'')

    def test_provider_failure_does_not_leak_stderr(self):
        self.env['FIXTURE_FAIL'] = '1'
        result = self.run_cmd('cpy', 'secret')
        self.assertEqual(result.returncode, 1)
        self.assertIn(b'exit 9', result.stderr)
        self.assertNotIn(b'private provider error', result.stderr)
        self.assertNotIn(b'secret', result.stderr)

    def test_powershell_stdin_protocol_uses_same_semantics(self):
        controller = self.repo/'lib/dots/clipboard.py'
        for arguments, data, expected in [([], '雪\n\n', '雪\n\n'), (['--', '-h', '"'], '', '-h "'), ([''], 'ignored', '')]:
            request = json.dumps(dict(command='cpy', arguments=arguments, input=data)).encode()
            result = self.run_cmd(sys.executable, '-B', str(controller), '--powershell', data=request)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(self.data.read_bytes(), expected.encode())
            request = json.dumps(dict(command='pst', arguments=[], input='')).encode()
            result = self.run_cmd(sys.executable, '-B', str(controller), '--powershell', data=request)
            self.assertEqual(result.stdout, expected.encode(), result.stderr)
        for invalid in (b'[]', b'not-json', b'{"command":"cpy","arguments":"secret","input":""}'):
            result = self.run_cmd(sys.executable, '-B', str(controller), '--powershell', data=invalid)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn(b'secret', result.stderr)

class NativeAdapters(unittest.TestCase):
    def check_engine(self, name):
        engine = shutil.which(name)
        if not engine:
            self.skipTest(name + ' unavailable; native adapter acceptance pending')
        with tempfile.TemporaryDirectory(prefix='dots-clipboard-native-') as directory:
            base = Path(directory)
            repo = base / 'checkout with spaces'
            for name in ('scripts/cpy.ps1', 'scripts/pst.ps1', 'lib/dots/clipboard.ps1',
                         'shells/powershell/helpers.ps1'):
                target = repo / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT/name, target)
            # Exercise the real controller and native adapter with an injected
            # file provider; Windows CI must never touch its desktop clipboard.
            stub = ("import os, sys\nfrom pathlib import Path\n"
                    + 'sys.path.insert(0, ' + repr(str(ROOT/'lib/dots')) + ')\n'
                    + "import clipboard\n"
                    + "def fake(operation, data=None):\n"
                    + "    path = Path(os.environ['FIXTURE_CLIPBOARD'])\n"
                    + "    if operation == 'write': path.write_bytes(data)\n"
                    + "    else: return path.read_bytes()\n"
                    + "clipboard._run = fake\nraise SystemExit(clipboard.main())\n")
            (repo/'lib/dots/clipboard.py').write_text(stub)
            env = dict(os.environ, FIXTURE_REPO=str(repo), FIXTURE_CLIPBOARD=str(base/'clipboard'),
                       DOTS=str(base/'stale checkout'), PYTHONDONTWRITEBYTECODE='1')
            for key in ('HOME', 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA', 'XDG_CONFIG_HOME',
                        'XDG_STATE_HOME', 'XDG_CACHE_HOME', 'XDG_DATA_HOME', 'CODEX_HOME'):
                owned = base/key
                owned.mkdir()
                env[key] = str(owned)
            driver = base/'check.ps1'
            driver.write_text(NATIVE_CHECK, encoding='utf-8-sig')
            result = subprocess.run([engine, '-NoLogo', '-NoProfile', '-NonInteractive', '-File', str(driver)],
                                    env=env, cwd=base, input=b'', capture_output=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_powershell_7(self):
        self.check_engine('pwsh')

    def test_windows_powershell_5(self):
        self.check_engine('powershell')


NATIVE_CHECK = r'''
$ErrorActionPreference = 'Stop'
$copyScript = Join-Path $env:FIXTURE_REPO 'scripts/cpy.ps1'
$pasteScript = Join-Path $env:FIXTURE_REPO 'scripts/pst.ps1'
$sample = "snow 雪`n`n"
$sample | & $copyScript
if ($LASTEXITCODE -ne 0) { exit 10 }
if ((& $pasteScript) -cne $sample) { exit 11 }
. (Join-Path $env:FIXTURE_REPO 'shells/powershell/helpers.ps1')
$sample | cpy
if ($LASTEXITCODE -ne 0) { exit 12 }
$result = pst
if ($result -isnot [string] -or $result -cne $sample) { exit 13 }
@('first', 'second') | cpy
if ((pst) -cne ('first' + [Environment]::NewLine + 'second')) { exit 14 }
# PowerShell consumes an unquoted -- itself; quote the literal CLI delimiter.
cpy '--' '-h' '"'
if ((pst) -cne '-h "') { exit 15 }
cpy ''
$empty = pst
if ($empty -isnot [string] -or $empty -cne '') { exit 16 }
$help = cpy --help
if ($LASTEXITCODE -ne 0 -or $help -notmatch 'Usage: cpy') { exit 17 }
$help = pst --help
if ($LASTEXITCODE -ne 0 -or $help -notmatch 'Usage: pst') { exit 18 }
# Stdin JSON transport must not hit native argv limits or append a newline.
$large = '雪' * 20000
$large | cpy
if ((pst) -cne $large) { exit 19 }
'''


if __name__ == '__main__':
    unittest.main()

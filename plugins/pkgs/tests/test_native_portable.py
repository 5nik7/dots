"""Portable manager adapters: owned scripts and mocks, never host packages."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pkgs_lib import backends, common, detect, go_tools, native_process, scopes, streams
from pkgs_lib.common import Error

NATIVE_NODE = native_process.executable('node.exe') if os.name == 'nt' else None


class NativePortable(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='pkgs native ü ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.env = dict(PATH=str(self.root), HOME=str(self.root), USERPROFILE=str(self.root),
                        NODE_OPTIONS='', NODE_PATH='', TERMUX_VERSION='', PREFIX='',
                        APPDATA=str(self.root/'config'), LOCALAPPDATA=str(self.root/'local'),
                        XDG_CONFIG_HOME=str(self.root/'config'), XDG_STATE_HOME=str(self.root/'state'),
                        XDG_DATA_HOME=str(self.root/'data'), XDG_CACHE_HOME=str(self.root/'cache'))
        self.environment = patch.dict(os.environ, self.env)
        self.environment.start(); self.addCleanup(self.environment.stop)

    def file(self, name, text='fixture'):
        path = self.root/name; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        return path

    def test_known_npm_and_gem_layouts_preserve_literal_argv(self):
        npm = self.file('npm.cmd'); node = self.file('node.exe')
        script = self.file('node_modules/npm/bin/npm-cli.js')
        gem = self.file('gem.cmd'); ruby = self.file('ruby.exe'); gem_script = self.file('gem')
        literal = ['', 'space ü', '--leading', 'x&echo pwn', '%PATH%', '$(touch nope)', 'a"b']
        with patch.object(native_process, 'windows', return_value=True):
            self.assertEqual(native_process.argv(['npm', *literal], self.env),
                             [str(node), str(script), *literal])
            self.assertEqual(native_process.argv([str(gem), *literal], self.env),
                             [str(ruby), str(gem_script), *literal])
        self.assertEqual(npm.read_text(), 'fixture')

    def test_missing_interpreter_unknown_shims_and_current_directory_refuse(self):
        self.file('npm.cmd'); self.file('unknown.cmd')
        with patch.object(native_process, 'windows', return_value=True):
            for command in ('npm', 'unknown', 'absent'):
                with self.subTest(command=command), self.assertRaises(Error):
                    native_process.argv([command], self.env)
            cwd = Path.cwd()
            try:
                os.chdir(self.root)
                self.file('untrusted.exe')
                self.assertIsNone(native_process.executable('untrusted', {'PATH':''}))
                self.assertIsNone(native_process.executable('untrusted', {'PATH':'.'}))
            finally: os.chdir(cwd)

    def test_posix_is_unchanged_without_windows_resolution(self):
        with patch.object(native_process, 'windows', return_value=False), patch.object(
                native_process, 'executable', side_effect=AssertionError('no extra PATH lookup')):
            self.assertEqual(native_process.argv(['npm', '', 'literal;arg']), ['npm', '', 'literal;arg'])

    def test_native_query_executes_owned_script_with_no_shell(self):
        self.file('npm.cmd', 'this launcher must never execute')
        self.file('node_modules/npm/bin/npm-cli.js',
                  'import json,sys; print(json.dumps(sys.argv[1:], ensure_ascii=True))')
        resolve = native_process.executable
        def interpreter(name, env=None):
            return Path(sys.executable) if name == 'node.exe' else resolve(name, env)
        literal = ['', '雪 ü', '--leading', 'x&echo pwn', '%PATH%', '$(touch nope)', 'a"b']
        with patch.object(native_process, 'windows', return_value=True), patch.object(
                native_process, 'executable', side_effect=interpreter):
            result = common.query(['npm', *literal], env=self.env, cwd=self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), literal)
        self.assertFalse((self.root/'nope').exists())

    @unittest.skipUnless(NATIVE_NODE, 'native Windows Node runtime is unavailable')
    def test_native_node_runs_owned_npm_layout_without_reading_packages(self):
        self.file('npm.cmd', 'this launcher must never execute')
        self.file('node_modules/npm/bin/npm-cli.js',
                  'process.stdout.write(JSON.stringify(process.argv.slice(2)))')
        resolve = native_process.executable
        def interpreter(name, env=None):
            return NATIVE_NODE if name == 'node.exe' else resolve(name, env)
        literal = ['', '雪 ü', '--leading', 'x&echo pwn', '%PATH%', '$(touch nope)', 'a"b']
        with patch.object(native_process, 'executable', side_effect=interpreter):
            result = common.query(['npm', *literal], env=self.env, cwd=self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), literal)

    def test_windows_detection_only_enables_supported_native_managers(self):
        with patch.object(detect, 'os', SimpleNamespace(name='nt')), patch.object(
                detect, 'which', return_value='fixture-winget'), patch.object(
                native_process, 'available', return_value=True) as available, patch.object(detect, 'run', return_value='pip fixture'):
            for name in ('npm','uv-tool','pip','gem','go','winget'): self.assertTrue(detect.available(name))
            for name in (*detect.SYSTEM, 'cargo'): self.assertFalse(detect.available(name))
            self.assertEqual(detect.default_manager(), 'winget')
            self.assertEqual([call.args[0] for call in available.call_args_list], ['npm','uv','gem','go'])

    def test_native_plans_retain_manager_scopes_and_no_sudo(self):
        native_os = SimpleNamespace(name='nt', environ=os.environ)
        with patch.object(backends, 'os', native_os), patch.object(backends, 'termux', return_value=False):
            self.assertEqual(backends.Backend('npm', True).transaction('upgrade',['one'],True),
                             ['npm','install','--global','--','one'])
            self.assertEqual(backends.Backend('uv-tool').transaction('upgrade',[],True), ['uv','tool','upgrade','--all'])
            self.assertEqual(backends.Backend('pip').transaction('upgrade',['one'],True),
                             [sys.executable,'-m','pip','install','--upgrade','one'])
            self.assertEqual(backends.Backend('gem').transaction('upgrade',['one'],True), ['gem','update','one'])
            for name in detect.SYSTEM:
                with self.subTest(name=name), self.assertRaisesRegex(Error, 'not a native Windows'): backends.Backend(name)
        with patch.object(scopes, 'run', return_value=str(self.root/'gems')):
            gem = scopes.make('gem', 'user')
        self.assertEqual(gem.operation_env, {'GEM_HOME':str(self.root/'gems'),'GEM_PATH':str(self.root/'gems')})
        self.assertEqual(scopes.scope_id(gem), 'user')

    def test_windows_go_exe_identity_and_renamed_refusal(self):
        self.file('Tool.exe'); self.file('renamed.exe')
        metadata = 'fixture\n\tpath\texample.org/tool\n\tmod\texample.org/tool\tv1.2.3\n'
        with patch.object(go_tools, 'os', SimpleNamespace(name='nt')), patch.object(
                go_tools, 'directory', return_value=self.root), patch.object(go_tools, 'local', return_value=metadata):
            rows = go_tools.installed()
        # Both names share one identity and remain ambiguous until only one exists.
        self.assertTrue(all(p.details['disabled_reason'] for p in rows))
        (self.root/'renamed.exe').unlink()
        with patch.object(go_tools, 'os', SimpleNamespace(name='nt')), patch.object(
                go_tools, 'directory', return_value=self.root), patch.object(go_tools, 'local', return_value=metadata):
            self.assertEqual(go_tools.installed()[0].details['disabled_reason'], '')

    def test_pip_negative_system_ownership_is_not_assumed(self):
        data = dict(version='1', installed=[dict(metadata={'name':'one','version':'1'},
                    installer='pip',metadata_location=str(self.root/'metadata'),requested=True)])
        with patch.object(scopes, 'os', SimpleNamespace(name='nt')), patch.object(
                scopes, 'query', return_value=subprocess.CompletedProcess([],0,json.dumps(data),'')), patch.object(
                scopes, 'default_manager', side_effect=Error('no system provider')):
            rows = scopes.pip_rows(backends.Backend('pip'), owned=True)
        self.assertEqual(rows[0][2], 'system ownership could not be checked')

    def test_stream_runner_uses_native_argv_and_keeps_console_open(self):
        console = Mock(); console.isatty.return_value = True
        child = Mock(); child.wait.return_value = 0
        with patch.object(streams, 'os', SimpleNamespace(name='nt', environ=os.environ)), patch.object(
                streams.sys, 'stdin', console), patch.object(streams, 'styled', return_value=False), patch.object(
                native_process, 'argv', return_value=['native.exe','literal']) as resolve, patch.object(
                streams.subprocess, 'Popen', return_value=child) as spawn:
            self.assertEqual(streams.run(['npm','literal'], {}), 0)
        self.assertEqual(resolve.call_args.args[0], ['npm','literal'])
        self.assertEqual(spawn.call_args.args[0], ['native.exe','literal'])
        self.assertIs(spawn.call_args.kwargs['stdin'], console)
        self.assertFalse(spawn.call_args.kwargs.get('shell', False))
        console.close.assert_not_called()


if __name__ == '__main__': unittest.main()

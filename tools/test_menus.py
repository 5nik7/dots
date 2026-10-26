#!/usr/bin/env python3
"""Shared menu contracts and private native tmux/FZF terminals; no live config."""
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import asdict
import argparse
import io
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
from menus import Entry, Menu, choose, dimensions, add_arguments, run_action, dots_argv
from interaction import RichSelector, SelectionEnded
from menu_tmux import TmuxContext, request_file, read_request
from menu_host import main as host_main


class MenuFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='dots menus ü ')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.home = self.base / 'home'; self.home.mkdir()
        self.env = {k: v for k, v in os.environ.items() if k in
                    ('PATH', 'LD_PRELOAD', 'PREFIX', 'SystemRoot', 'WINDIR', 'COMSPEC')}
        self.env.update(HOME=str(self.home), USERPROFILE=str(self.home), DOTS=str(self.base / 'repo'),
                        XDG_CONFIG_HOME=str(self.home / 'config'), XDG_STATE_HOME=str(self.home / 'state'),
                        XDG_CACHE_HOME=str(self.home / 'cache'), XDG_DATA_HOME=str(self.home / 'data'),
                        APPDATA=str(self.home / 'Roaming'), LOCALAPPDATA=str(self.home / 'Local'),
                        TMPDIR=str(self.base), TMP=str(self.base), TEMP=str(self.base),
                        TERM='xterm-256color', DOTS_COLOR='never', DOTS_ICONS='never', DOTS_PROGRESS='never',
                        PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(ROOT / 'lib/dots'))
        self.addCleanup(patch.stopall)
        patch.dict(os.environ, self.env, clear=True).start()
        self.menu = Menu('fixture', 'Fixture menu', (
            Entry('one', 'First', 'Read existing information'),
            Entry('two', 'Second', 'Open café', icon='★'),
            Entry('missing', 'Missing', available=False, reason='Tool unavailable'),
        ))

    def command(self, code):
        path = self.base / 'child ü.py'; path.write_text(code)
        return [sys.executable, '-B', str(path)]


class Menus(MenuFixture):
    def test_schema_and_data_modes_never_probe_or_select(self):
        with patch('subprocess.run', side_effect=AssertionError('unexpected child')), \
                patch('shutil.which', side_effect=AssertionError('unexpected tool probe')):
            for mode in ('print', 'auto', 'json'):
                output = io.StringIO()
                with redirect_stdout(output), patch('menus.terminal', return_value=False):
                    self.assertIsNone(choose(self.menu, mode=mode, query='café'))
                if mode == 'json':
                    self.assertEqual(json.loads(output.getvalue()), dict(schema=1, menu='fixture', title='Fixture menu', items=[
                        dict(id='two', label='Second', description='Open café', available=True, reason='')]))
                else:
                    self.assertIn('Second', output.getvalue()); self.assertNotIn('First', output.getvalue())
        with patch.dict(os.environ, DOTS_COLOR='always', DOTS_ICONS='always'), redirect_stdout(io.StringIO()) as output:
            choose(self.menu, mode='json')
        self.assertNotIn('\x1b', output.getvalue()); self.assertNotIn('★', output.getvalue())

    def test_metadata_validation_and_argument_conflicts(self):
        with self.assertRaises(ValueError): Menu('a', 'A', (Entry('x', 'one'), Entry('x', 'two')))
        with self.assertRaises(ValueError): Entry('x', 'bad\0')
        with self.assertRaises(ValueError): Entry('x', 'Missing', available=False)
        parser = argparse.ArgumentParser(); add_arguments(parser)
        self.assertEqual(parser.parse_args(['--query', 'a b', '--json']).menu_mode, 'json')
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit): parser.parse_args(['--json', '--browse'])

    def test_geometry_uses_display_cells_title_header_and_bounds(self):
        for size in ((40, 15), (80, 24), (120, 40), (5, 4)):
            width, height = dimensions(['日本語' * 20] * 80, 'Title', 'Enter\nEsc', size=size)
            self.assertLessEqual(width, size[0] - 2); self.assertLessEqual(height, size[1] - 2)
        self.assertEqual(dimensions(['short'], header='X' * 50, size=(80, 24)), (56, 7))
        self.assertEqual(dimensions(['界' * 20], size=(80, 24))[0], 46)

    def test_plain_views_wrap_and_escape_labels(self):
        from files.catalog import Presentation
        from resources import cells
        menu = Menu('weird', 'Fixture', (Entry('literal', '界 café ' * 20 + '\x1b[31m\t\n', '$(touch sentinel)'),))
        for width in (40, 80, 120):
            output = io.StringIO(); ui = Presentation(output); ui.width = width
            choose(menu, mode='print', ui=ui)
            self.assertNotIn('\x1b', output.getvalue())
            self.assertTrue(all(cells(line) <= width for line in output.getvalue().splitlines()))
        self.assertFalse((self.home / 'sentinel').exists())

    def test_empty_and_missing_tools_never_execute(self):
        with patch('menus.terminal', return_value=True), patch('menus.shutil.which', return_value=None), \
                redirect_stdout(io.StringIO()) as output, redirect_stderr(io.StringIO()) as error:
            self.assertIsNone(choose(self.menu, mode='browse'))
            self.assertIn('First', output.getvalue()); self.assertIn('FZF unavailable', error.getvalue())
        with patch('menus.terminal', return_value=True), patch('menus.shutil.which', side_effect=AssertionError), redirect_stdout(io.StringIO()) as output:
            self.assertIsNone(choose(Menu('empty', 'Empty', ()), mode='browse'))
            self.assertIn('No matching choices', output.getvalue())
        with patch('menus.terminal', return_value=False), self.assertRaises(ValueError): choose(self.menu, mode='browse')

    def test_selection_is_inert_and_failures_do_not_retry(self):
        with patch('menus.terminal', return_value=True), patch('menus.shutil.which', return_value='fixture-tool'), \
                patch('interaction.rich_fzf_available', return_value=True), patch.object(RichSelector, 'fzf', return_value=[1]) as picker:
            self.assertEqual(choose(self.menu, mode='browse', query='second').id, 'two')
            self.assertEqual(picker.call_args.kwargs['query'], 'second')
            picker.return_value = [2]
            with self.assertRaisesRegex(ValueError, 'Tool unavailable'): choose(self.menu, mode='browse')
            for failure in (SelectionEnded(130), ValueError('fixture failure')):
                picker.reset_mock(); picker.side_effect = failure
                with self.assertRaises(type(failure)): choose(self.menu, mode='browse')
                self.assertEqual(picker.call_count, 1)

    def test_published_light_dark_palette_and_presentation_preferences(self):
        from files.catalog import Presentation
        directory = Path(self.env['XDG_STATE_HOME']) / 'dots/current/theme'
        directory.mkdir(parents=True)
        for colors in ('fg:#eeeeee,bg:#111111', 'fg:#111111,bg:#eeeeee'):
            (directory / 'fzf.sh').write_text('export _FZF_COLORS_="' + colors + '"\n')
            for mode, no_color, enabled in (('auto', '', True), ('auto', '1', False), ('always', '1', True), ('never', '', False)):
                with patch.dict(os.environ, DOTS_COLOR=mode, NO_COLOR=no_color, DOTS_ICONS='never'), \
                        patch('menus.terminal', return_value=True), patch('menus.shutil.which', return_value='fixture-tool'), \
                        patch('interaction.rich_fzf_available', return_value=True), patch.object(RichSelector, 'fzf', return_value=[1]) as picker:
                    self.assertEqual(choose(self.menu, mode='browse', ui=Presentation(terminal=True)).id, 'two')
                    self.assertEqual(picker.call_args.args[4:7], (enabled, False, colors if enabled else ''))
                    self.assertNotIn('★', ''.join(picker.call_args.args[1]))

    def test_selector_environment_cannot_restore_default_actions(self):
        picker = RichSelector(backend='fzf')
        result = subprocess.CompletedProcess([], 0, b'0\tfirst\0')
        with patch('interaction.subprocess.run', return_value=result) as run:
            preview = ('fixture-preview {1}', None, {'TMUX_PANE': '%999', 'FZF_DEFAULT_OPTS': '--bind=start:abort'})
            self.assertEqual(picker.fzf('Fixture', ['first'], False, preview, False, False, '',
                environment={'TMUX_PANE': '', 'FZF_DEFAULT_OPTS': '--bind=start:abort', 'BASH_ENV': '/bad'}), [0])
        env = run.call_args.kwargs['env']
        self.assertEqual(env['TMUX_PANE'], ''); self.assertEqual(env['FZF_DEFAULT_OPTS'], ''); self.assertEqual(env['BASH_ENV'], '')
        self.assertNotIn('TMUX_PANE', os.environ)
        for output in (b'99\0', b'-1\0', b'$(touch x)\0', b'01\0', b'0\0' + b'1\0'):
            with patch('interaction.subprocess.run', return_value=subprocess.CompletedProcess([], 0, output)), self.assertRaises(ValueError):
                picker.fzf('Fixture', ['first'], False, None, False, False, '')

    def test_private_request_permissions_cleanup_and_redaction(self):
        with request_file(dict(schema=1, private='test-only-secret')) as path:
            self.assertEqual(read_request(path)['private'], 'test-only-secret')
            if os.name != 'nt':
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                path.chmod(0o644)
                with self.assertRaises(ValueError): read_request(path)
        self.assertFalse(path.exists()); self.assertFalse(path.parent.exists())
        if os.name != 'nt':
            fifo = self.base / 'fifo'; os.mkfifo(fifo)
            with self.assertRaises(ValueError): read_request(fifo)
        invalid = self.base / 'bad.json'; invalid.write_text('test-only-secret')
        invalid.chmod(0o600)
        p = subprocess.run([sys.executable, '-B', str(ROOT / 'lib/dots/menu_host.py'), 'host', str(invalid)], env=self.env, capture_output=True, text=True)
        self.assertEqual(p.returncode, 2); self.assertNotIn('test-only-secret', p.stderr + p.stdout)

    def test_navigation_protocol_keeps_query_and_handles_empty_back(self):
        from interaction import SelectionEvent
        picker = RichSelector(backend='fzf')
        for key, action in ((b'esc', 'back'), (b'f1', 'help')):
            for status in (0, 1):
                frame = {}
                with patch('interaction.subprocess.run', return_value=subprocess.CompletedProcess([], status, b'query\0' + key + b'\0')), self.assertRaises(SelectionEvent) as event:
                    picker.fzf('Title', ['first'], False, None, False, False, '', navigation=frame)
                self.assertEqual(event.exception.action, action); self.assertEqual(frame['query'], 'query')
        frame = {}
        with patch('interaction.subprocess.run', return_value=subprocess.CompletedProcess([], 0, b'query\0\0' + b'0\tfirst\0')):
            self.assertEqual(picker.fzf('Title', ['first'], False, None, False, False, '', navigation=frame), [0])
        self.assertEqual(frame['query'], 'query')
        with patch('menus.terminal', return_value=True), patch('menus.shutil.which', return_value='fixture-tool'), patch('interaction.rich_fzf_available', return_value=True), patch.object(RichSelector, 'fzf', return_value=[1]) as fzf:
            from files.catalog import Presentation
            with patch.dict(os.environ, DOTS_ICONS='always'):
                choose(self.menu, mode='browse', compact=True, navigation={}, ui=Presentation(terminal=True))
            labels=fzf.call_args.args[1]
            self.assertIn('★', labels[1]); self.assertNotIn('Open café', labels[1])

    def test_prompt_override_is_interactive_only_and_controls_geometry(self):
        menu = Menu('fixture', 'Long printed title ' * 12, (Entry('one', 'First'),))
        with patch('menus.terminal', return_value=True), patch('menus.shutil.which', return_value='fixture-tool'), patch('interaction.rich_fzf_available', return_value=True), patch.object(RichSelector, 'fzf', return_value=[0]) as picker, patch('menus.dimensions', wraps=dimensions) as geometry:
            choose(menu, mode='browse', prompt='dots·files')
            self.assertEqual(picker.call_args.args[0], 'dots·files')
            self.assertEqual(geometry.call_args.args[1], 'dots·files')
            choose(menu, mode='browse')
            self.assertEqual(picker.call_args.args[0], menu.title)
        for mode in ('print', 'json'):
            with redirect_stdout(io.StringIO()) as output:
                choose(self.menu, mode=mode, prompt='dots·files')
            self.assertIn('Fixture menu', output.getvalue())
            self.assertNotIn('dots·files', output.getvalue())

    def test_frontends_preserve_literal_arguments(self):
        values = ['keys', '--query', 'café $(not-run)', '']
        root = self.base / 'checkout space'
        self.assertEqual(dots_argv(values, root=root, windows=False), [str(root / 'bin/dots'), *values])
        self.assertEqual(dots_argv(values, root=root, windows=True), [sys.executable, '-B', str(root / 'lib/dots/cli.py'), *values])
        with self.assertRaises(ValueError): dots_argv(values, root='relative')

    @unittest.skipIf(os.name == 'nt', 'tmux has no native Windows equivalent')
    def test_old_popup_capability_lists_without_selector_or_context_probes(self):
        context = TmuxContext('/tool/tmux', '/private/socket', '/dev/pts/7', 123, '%2', '$1', str(self.home))
        with patch('menus.shutil.which', return_value='fixture-tool'), patch('interaction.rich_fzf_available', return_value=True), \
                patch('menus.subprocess.run', return_value=subprocess.CompletedProcess([], 0, b'old fzf')), \
                patch.object(TmuxContext, 'verify', side_effect=AssertionError), patch.object(RichSelector, 'fzf', side_effect=AssertionError), \
                redirect_stdout(io.StringIO()) as output, redirect_stderr(io.StringIO()) as error:
            self.assertIsNone(choose(self.menu, mode='browse', context=context))
        self.assertIn('popup support unavailable', error.getvalue()); self.assertIn('First', output.getvalue())

    def test_direct_action_literal_arguments_and_status_without_host(self):
        values = ['', '-leading', 'café "quote"', '$(touch nope);', 'a&b|c', '\n', 'C:\\a b\\']
        target = self.base / 'result.json'
        command = self.command('import json,sys\nfrom pathlib import Path\nPath(sys.argv[1]).write_text(json.dumps(sys.argv[2:]))\nsys.exit(7)\n')
        with patch('menus.terminal', return_value=True), patch('menu_pager.reader'):
            self.assertEqual(run_action([*command, str(target), *values], kind='output'), 7)
        self.assertEqual(json.loads(target.read_text()), values)
        with patch('menus.terminal', return_value=False), self.assertRaises(ValueError): run_action(command)
        self.assertFalse(list(self.base.glob('dots-menu-*')))

    def test_host_preserves_arguments_environment_cwd_and_status(self):
        cwd = self.base / 'cwd ü $(not-run)'; cwd.mkdir()
        target = self.base / 'receipt.json'
        command = self.command('import json,os,sys\nfrom pathlib import Path\nPath(sys.argv[1]).write_text(json.dumps([os.getcwd(),os.environ["FIXTURE"],sys.argv[2:]]))\nsys.exit(7)\n')
        payload = dict(schema=1, argv=[*command, str(target), '', '$(touch nope)'], cwd=str(cwd), environment=dict(self.env, FIXTURE='literal'), hold=True)
        with request_file(payload) as path, patch('menu_pager.reader', side_effect=AssertionError('capture host opened a reader')) as reader:
            self.assertEqual(host_main(['host', str(path)]), 7)
            self.assertEqual(path.with_suffix('.status').read_text(), '7')
            self.assertIn('Exit status: 7', (path.parent/'view.txt').read_text())
            reader.assert_not_called()
        self.assertEqual(json.loads(target.read_text()), [str(cwd), 'literal', ['', '$(touch nope)']])
        self.assertFalse((cwd / 'nope').exists())

    @unittest.skipIf(os.name == 'nt', 'tmux has no native Windows equivalent')
    def test_popup_owned_action_transports_context_without_hosting(self):
        context = TmuxContext('/tool/tmux', '/private/socket', '/dev/pts/7', 123, '%2', '$1', str(self.home))
        observed = []
        def execute(command, **kwargs):
            path = Path(kwargs['environment']['DOTS_MENU_CONTEXT'])
            observed.append(path)
            self.assertEqual(read_request(path)['context'], asdict(context))
            self.assertEqual(kwargs['environment']['DOTS_KEYS_TARGET_PANE'], '%2')
            return 130
        with patch.object(TmuxContext, 'verify'), patch.object(TmuxContext, 'host', side_effect=AssertionError), patch('menu_host.execute', side_effect=execute):
            self.assertEqual(run_action(['fixture'], kind='popup', context=context), 130)
        self.assertFalse(observed[0].exists())

    def test_native_selector_shell_arguments_are_literal(self):
        from types import SimpleNamespace
        # Adapter fixture, not a claim of native Windows execution.
        fake_os = SimpleNamespace(name='nt', environ=dict(self.env))
        with patch('interaction.os', fake_os), patch('interaction.native_shell', return_value=r'C:\Program Files\PowerShell\pwsh.exe'), \
                patch('interaction.subprocess.run', return_value=subprocess.CompletedProcess([], 130, b'')) as run:
            with self.assertRaises(SelectionEnded): RichSelector(backend='fzf').fzf('Native', ['literal'], False, None, False, False, '')
        flags = run.call_args.args[0]
        self.assertTrue(any(f.startswith('--with-shell="C:\\Program Files') for f in flags))
        self.assertFalse(any('bash' in f for f in flags))

    @unittest.skipIf(os.name == 'nt', 'tmux has no native Windows equivalent')
    def test_proxy_refuses_client_override_and_host_keeps_completed_hangup_status(self):
        context = TmuxContext('/tool/tmux', '/private/socket', '/dev/pts/7', 123, '%2', '$1', str(self.home))
        with request_file(dict(schema=1, context=asdict(context))) as path:
            for args in (['kill-server'], ['display-popup', '-c', '/other/client'], ['display-popup', '-C']):
                with self.assertRaisesRegex(ValueError, 'unsupported'): host_main(['proxy', str(path), *args])
        def completed(command):
            Path(command[-1]).with_suffix('.status').write_text('129')
            return subprocess.CompletedProcess(command, 129)
        with patch.object(TmuxContext, 'verify', return_value=(80,24)), patch('menu_tmux.subprocess.run', side_effect=completed):
            self.assertEqual(context.host(['fixture']), 129)


class NativeMenuFixture(MenuFixture):
    def setUp(self):
        super().setUp()
        if os.name == 'nt' or not shutil.which('tmux') or not shutil.which('fzf'):
            self.skipTest('native POSIX tmux/FZF unavailable')
        import pty, fcntl, termios, struct
        self.pty, self.fcntl, self.termios, self.struct = pty, fcntl, termios, struct
        self.tmux = shutil.which('tmux'); self.socket = self.base / 'tmux.socket'
        self.clients = []; self.workers = []
        self.addCleanup(self.cleanup_server)
        shell = shutil.which('bash')
        self.control('new-session', '-d', '-s', 'fixture', shell, '--noprofile', '--norc')
        self.control('set-option', '-g', 'default-shell', shell)
        self.control('set-option', '-g', 'status', 'off')
        self.pane = self.control('display-message', '-p', '-t', 'fixture', '#{pane_id}').strip()
        self.first = self.attach(); self.second = self.attach(columns=120)
        os.environ.update(TMUX=str(self.socket) + ',0,0', TMUX_PANE=self.pane)

    def control(self, *args):
        result = subprocess.run([self.tmux, '-u', '-S', str(self.socket), '-f', os.devnull, *args], env=self.env, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def attach(self, columns=100):
        import time
        pid, master = self.pty.fork()
        if pid == 0:
            os.execve(self.tmux, [self.tmux, '-u', '-S', str(self.socket), 'attach-session', '-t', 'fixture'], self.env)
        self.fcntl.ioctl(master, self.termios.TIOCSWINSZ, self.struct.pack('HHHH', 30, columns, 0, 0))
        before = {c[2] for c in self.clients}
        record = [pid, master, None]; self.clients.append(record)
        for _ in range(50):
            names = set(self.control('list-clients', '-F', '#{client_name}').splitlines()) - before
            if names:
                record[2] = next(iter(names)); break
            time.sleep(.05)
        self.assertIsNotNone(record[2]); self.drain(master)
        return record

    def drain(self, master):
        import select
        data = bytearray()
        while select.select([master], [], [], .03)[0]:
            try: chunk = os.read(master, 65536)
            except OSError: break
            if not chunk: break
            data.extend(chunk)
        return bytes(data)

    def receive(self, master, needle):
        import time
        data = bytearray(); deadline = time.monotonic() + 15
        while needle not in data and time.monotonic() < deadline:
            data.extend(self.drain(master))
        self.assertIn(needle, data[-10000:])
        return data

    def worker(self, code, **extra):
        env = dict(self.env, TMUX=str(self.socket) + ',0,0', TMUX_PANE=self.pane, CLIENT=self.first[2], **extra)
        p = subprocess.Popen([sys.executable, '-B', '-c', code], env=env, cwd=self.home, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.workers.append(p); return p

    def cleanup_server(self):
        import signal, time
        # Shut the owned server first: a blocked tmux child can retain its
        # worker's pipes even after the parent Python process is terminated.
        subprocess.run([self.tmux, '-N', '-S', str(self.socket), 'kill-server'], env=self.env, capture_output=True, timeout=5)
        for p in self.workers:
            if p.poll() is None: p.kill()
            p.communicate(timeout=5)
        for pid, master, _ in self.clients:
            try: os.kill(pid, signal.SIGTERM)
            except ProcessLookupError: pass
            # A client may still be flushing redraws into its unread PTY. Close
            # the master first and bound shutdown instead of waiting forever.
            os.close(master)
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                if os.waitpid(pid, os.WNOHANG)[0]: break
                time.sleep(.02)
            else:
                try: os.kill(pid, signal.SIGKILL)
                except ProcessLookupError: pass
                os.waitpid(pid, 0)

class NativeMenus(NativeMenuFixture):
    def test_native_popup_targets_exact_client_and_returns_selection(self):
        import time
        code = '''import os
from menus import Menu,Entry,choose
from menu_tmux import TmuxContext
c=TmuxContext.capture(client=os.environ['CLIENT'])
r=choose(Menu('native','Fixture chooser',(Entry('one','First'),Entry('two','Second'))),mode='browse',context=c)
print('selected:'+r.id)
'''
        p = self.worker(code)
        self.receive(self.first[1], b'Fixture chooser')
        self.assertNotIn(b'Fixture chooser', self.drain(self.second[1]))
        os.write(self.first[1], b'Second'); time.sleep(.25); os.write(self.first[1], b'\r')
        out, err = p.communicate(timeout=15)
        self.assertEqual(p.returncode, 0, err); self.assertEqual(out.strip(), 'selected:two')
        self.assertFalse(list(self.base.glob('dots-menu-*')))

    def test_native_cancel_is_130_and_popup_is_closed(self):
        code = '''import os,sys
from menus import Menu,Entry,choose
from interaction import SelectionEnded
from menu_tmux import TmuxContext
try: choose(Menu('native','Cancel chooser',(Entry('one','First'),)),mode='browse',context=TmuxContext.capture(client=os.environ['CLIENT']))
except SelectionEnded as error: sys.exit(error.status)
'''
        for key in (b'\x1b', b'\x03'):
            p = self.worker(code); self.receive(self.first[1], b'Cancel chooser')
            os.write(self.first[1], key)
            out, err = p.communicate(timeout=15)
            self.assertEqual(p.returncode, 130, err); self.assertEqual(out, '')
        self.assertFalse(list(self.base.glob('dots-menu-*')))

    def test_native_popup_fits_40_80_120_column_clients(self):
        import time
        code = '''import os,sys
from menus import Menu,Entry,choose
from interaction import SelectionEnded
from menu_tmux import TmuxContext
try: choose(Menu('width','Width chooser',(Entry('one','First'),)),mode='browse',context=TmuxContext.capture(client=os.environ['CLIENT']))
except SelectionEnded as error: sys.exit(error.status)
'''
        for width in (40, 80, 120):
            self.fcntl.ioctl(self.first[1], self.termios.TIOCSWINSZ, self.struct.pack('HHHH', 20, width, 0, 0))
            context = TmuxContext.capture(client=self.first[2])
            for _ in range(30):
                if context.verify() == (width, 20): break
                time.sleep(.05)
            self.assertEqual(context.verify(), (width, 20))
            self.drain(self.first[1])
            p = self.worker(code); self.receive(self.first[1], b'Width chooser')
            os.write(self.first[1], b'\x1b')
            out, err = p.communicate(timeout=15)
            self.assertEqual(p.returncode, 130, err)

    def test_native_terminal_host_holds_result_and_preserves_context(self):
        import time
        target = self.base / 'host-result.json'
        child = self.command('import json,os,sys\nfrom pathlib import Path\nPath(sys.argv[1]).write_text(json.dumps([os.getcwd(),sys.argv[2:],os.environ["FIXTURE"]]))\nprint("HOST RESULT",flush=True)\nsys.exit(7)\n')
        command = [*child, str(target), '', '-leading', '$(touch sentinel); café']
        code = '''import os,sys,json
from menus import run_action
from menu_tmux import TmuxContext
sys.exit(run_action(json.loads(os.environ['COMMAND']),kind='output',context=TmuxContext.capture(client=os.environ['CLIENT'])))
'''
        p = self.worker(code, COMMAND=json.dumps(command), FIXTURE='caller environment')
        self.receive(self.first[1], b'Back q')
        self.assertNotIn(b'HOST RESULT', self.drain(self.second[1]))
        self.assertIsNone(p.poll())
        os.write(self.first[1], b'q')
        out, err = p.communicate(timeout=15)
        self.assertEqual(p.returncode, 7, err)
        self.assertEqual(json.loads(target.read_text()), [str(self.home), command[4:], 'caller environment'])
        self.assertFalse((self.home / 'sentinel').exists())
        self.assertFalse(list(self.base.glob('dots-menu-*')))

    def test_native_ambiguity_and_stale_client_refuse(self):
        with self.assertRaisesRegex(ValueError, 'ambiguous'): TmuxContext.capture()
        context = TmuxContext.capture(client=self.first[2])
        self.assertEqual(context.verify(), (100, 30))
        self.control('detach-client', '-t', self.first[2])
        with self.assertRaisesRegex(ValueError, 'changed'): context.verify()

    def test_native_host_closed_before_result_is_cancellation(self):
        command = self.command('import time\nprint("HOST RUNNING",flush=True)\ntime.sleep(30)\n')
        code = '''import os,sys,json
from menus import run_action
from menu_tmux import TmuxContext
sys.exit(run_action(json.loads(os.environ['COMMAND']),context=TmuxContext.capture(client=os.environ['CLIENT'])))
'''
        p = self.worker(code, COMMAND=json.dumps(command))
        self.receive(self.first[1], b'HOST RUNNING')
        self.control('display-popup', '-C', '-c', self.first[2])
        out, err = p.communicate(timeout=15)
        self.assertEqual(p.returncode, 130, err)
        self.assertFalse(list(self.base.glob('dots-menu-*')))


if __name__ == '__main__':
    unittest.main()

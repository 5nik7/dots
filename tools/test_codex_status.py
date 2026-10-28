#!/usr/bin/env python3
"""Codex window-state fixtures; native panes run harmless named Python sleepers."""
import importlib.util
import os
from pathlib import Path
import shlex
import signal
import sys
import time
import unittest
from unittest.mock import patch

import test_tmux_status as status

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('codex_status', ROOT / 'config/tmux/codex-status.py')
adapter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapter)


class Adapter(unittest.TestCase):
    def setUp(self):
        self.fixture = status.TmuxStatus('test_layout_and_template_ownership')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.proc = self.fixture.root / 'proc'
        self.proc.mkdir()

    def process(self, pid, name='bash', group=None, tty=100, foreground=20, state='S'):
        fields = [state, '1', str(group or pid), str(pid), str(tty), str(foreground)] + ['0'] * 14
        raw = f'{pid} ({name}) ' + ' '.join(fields)
        directory = self.proc / str(pid)
        directory.mkdir(exist_ok=True)
        (directory / 'stat').write_text(raw)
        return adapter.parse_stat(raw.encode())

    def test_foreground_wrappers_any_pane_and_stale_titles(self):
        panes = adapter.parse_inventory(b'@1 %1 10 0 0\n@1 %2 11 1 0\n@10 %3 12 0 0\n')
        records = dict((r['pid'], r) for r in (
            self.process(10), self.process(11, tty=101, foreground=21),
            self.process(12, tty=102, foreground=22), self.process(20, 'codex'),
            self.process(21, 'codex', tty=101), self.process(22, 'codex', tty=102)))
        self.assertEqual(adapter.render(panes, records), '|@1:working|@10:idle|')
        for change in ({'state': b'T'}, {'state': b'Z'}, {'name': b'other'}, {'tty': 999}):
            with self.subTest(change=change):
                changed = dict(records)
                changed[21] = dict(records[21], **change)
                self.assertEqual(adapter.render(panes, changed), '|@1:idle|@10:idle|')
        records[11]['foreground'] = 11  # Background/suspended job; stale Working title.
        self.assertEqual(adapter.render(panes, records), '|@1:idle|@10:idle|')
        del records[20]
        self.assertEqual(adapter.render(panes, records), '|@10:idle|')
        self.assertEqual(adapter.render([('@2', 999, 'working')], records), '')

    def test_inventory_validation_caps_and_duplicate_links(self):
        row = b'@1 %2 30 1 0\n'
        self.assertEqual(adapter.parse_inventory(row * 2), [('@1', 30, 'working')])
        for raw in (b'@1 %2 0 1 0\n', b'@1 %2 30 Working 0\n', b'@1 %2 30 1 0 extra\n',
                    b'@1 %2 30 0 2\n', b'@1 %2 30 2 0\n', b'@1 %2 30 1\n',
                    b'@1]#[bold] %2 30 1\n', b'\xff', row + b'\n',
                    row + b'@2 %2 30 1 0\n', b'x' * (adapter.MAX_INVENTORY + 1),
                    row * (adapter.MAX_PANES + 1)):
            with self.subTest(raw=raw[:50]), self.assertRaises(ValueError):
                adapter.parse_inventory(raw)

    def test_explicit_waiting_overrides_own_working_but_not_other_panes(self):
        records = dict((r['pid'], r) for r in (
            self.process(10), self.process(20, 'codex'),
            self.process(11, tty=101, foreground=21), self.process(21, 'codex', tty=101)))
        waiting = b'@1 %1 10 1 1\n'
        self.assertEqual(adapter.render(adapter.parse_inventory(waiting), records), '|@1:waiting|')
        for tail, expected in ((b'@1 %2 11 0 0\n', 'waiting'),
                               (b'@1 %2 11 0 1\n', 'waiting'),
                               (b'@1 %2 11 1 0\n', 'working')):
            panes = adapter.parse_inventory(waiting + tail)
            for order in (panes, list(reversed(panes))):
                self.assertEqual(adapter.render(order, records), '|@1:' + expected + '|')

    @unittest.skipUnless(hasattr(os, 'getuid'), 'procfs adapter is Unix-only')
    def test_process_record_bounds_deadline_and_disappearance(self):
        expected = self.process(10, 'name with )\n( punctuation')
        records = adapter.processes(self.proc, time.monotonic() + 1)
        self.assertEqual(records[10], expected)
        self.process(11)
        with patch.object(adapter, 'MAX_PROCESSES', 1), self.assertRaises(ValueError):
            adapter.processes(self.proc, time.monotonic() + 1)
        with self.assertRaises(TimeoutError):
            adapter.processes(self.proc, time.monotonic() - 1)
        (self.proc / '11/stat').unlink()
        self.assertEqual(set(adapter.processes(self.proc, time.monotonic() + 1)), {10})
        (self.proc / '10/stat').write_bytes(b'x' * (adapter.MAX_STAT + 1))
        with self.assertRaises(ValueError):
            adapter.processes(self.proc, time.monotonic() + 1)

    @unittest.skipUnless(hasattr(os, 'getuid'), 'procfs adapter is Unix-only')
    def test_bounded_single_query_failure_clearing_and_cleanup(self):
        self.process(10)
        self.process(20, 'codex')
        executable = self.fixture.tools / 'tmux'
        def provider(body):
            executable.write_text('#!' + sys.executable + '\n' + body + '\n')
            executable.chmod(0o700)
        with patch.dict(os.environ, self.fixture.env, clear=True):
            provider('import sys, pathlib, os\nassert sys.argv[1:4] == ["-S", "socket ü", "list-panes"]\n'
                     'with pathlib.Path(os.environ["HOME"], "queries").open("a") as stream: stream.write("one\\n")\nprint("@1 %1 10 1 0")')
            self.assertEqual(adapter.status('socket ü', self.proc), '|@1:working|')
            self.assertEqual((self.fixture.home / 'queries').read_text(), 'one\n')
            for body in ('raise SystemExit(1)', 'print("bad")',
                         'print("x" * 131073)', 'print("@1 %1 10 1 0\\nPRIVATE")'):
                provider(body)
                self.assertEqual(adapter.status('socket ü', self.proc), '')
            provider('print("@1 %1 10 1 0")')
            with patch.object(adapter, 'processes', side_effect=PermissionError):
                self.assertEqual(adapter.status('socket ü', self.proc), '')
            # A descendant holding stdout must be terminated with the provider.
            child_pid = self.fixture.home / 'child-pid'
            provider('import subprocess, sys, time\nfrom pathlib import Path\n'
                     'child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(10)"])\n'
                     f'Path({str(child_pid)!r}).write_text(str(child.pid))\ntime.sleep(10)')
            start = time.monotonic()
            with patch.object(adapter, 'TIMEOUT', .3):
                self.assertEqual(adapter.status('socket ü', self.proc), '')
            self.assertLess(time.monotonic() - start, .9)
            pid = int(child_pid.read_text())
            time.sleep(.05)
            try:
                state = adapter.parse_stat((Path('/proc') / str(pid) / 'stat').read_bytes())['state']
                self.assertIn(state, (b'Z', b'X', b'x'))
            except FileNotFoundError:
                pass
            executable.unlink()
            with patch.dict(os.environ, {'PATH': str(self.fixture.tools)}):
                self.assertEqual(adapter.status('socket ü', self.proc), '')


@unittest.skipUnless(status.TMUX and sys.platform in ('linux', 'android') and Path('/proc/self/stat').exists(),
                     'native tmux and Linux/Termux procfs required')
class Native(unittest.TestCase):
    def setUp(self):
        self.fixture = status.TmuxStatus('test_layout_and_template_ownership')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root, self.env = self.fixture.root, self.fixture.env
        self.fake = self.root / 'fake codex.py'
        self.fake.write_text('import ctypes, os, pathlib, sys, time\n'
                             'assert ctypes.CDLL(None).prctl(15, b"codex", 0, 0, 0) == 0\n'
                             'pathlib.Path(sys.argv[1]).write_text(str(os.getpid()))\n'
                             'time.sleep(120)\n')
        self.inner, self.base = self.fixture.server('codex-inner')
        self.fixture.write_theme()
        # These fixtures supply display metadata directly; workspace mutation
        # hooks are covered separately and must not race the status assertions.
        self.config = self.fixture.write_config(workspace_hooks=False)
        self.inner('source-file', str(self.config))
        self.inner('set-option', '-g', 'status-interval', '1')
        self.inner('set-option', '-g', '@dots-termux-default', '1')
        self.inner('set-option', '-gw', 'automatic-rename', 'off')
        self.inner('rename-window', 'shell')

    def command(self, name, wrapped=False):
        command = shlex.join([sys.executable, '-B', str(self.fake), str(self.root / (name + '.pid'))])
        return shlex.join([status.BASH, '-c', command + ' & wait']) if wrapped else 'exec ' + command

    def pid(self, name):
        path = self.root / (name + '.pid')
        deadline = time.monotonic() + 3
        while True:
            value = path.read_text() if path.exists() else ''
            if value:
                return int(value)
            self.assertLess(time.monotonic(), deadline)
            time.sleep(.03)

    def view(self):
        self.outer, _ = self.fixture.server('codex-view', termux=False)
        self.outer('set-option', '-g', 'status', 'off')
        self.outer('set-option', '-g', 'default-terminal', 'tmux-256color')
        command = shlex.join(['env', '-u', 'TMUX', '-u', 'TMUX_PANE', *self.base, 'attach-session', '-t', 'fixture'])
        self.outer('new-session', '-d', '-s', 'view', '-x', '120', '-y', '24', command)
        self.row = 1
        deadline = time.monotonic() + 3
        while not self.inner('list-clients', '-F', '#{client_tty}'):
            self.assertLess(time.monotonic(), deadline)
            time.sleep(.03)

    def color(self, label, expected, text=None, check=None):
        self.inner('refresh-client', '-S')
        deadline, row = time.monotonic() + 8, ''
        while time.monotonic() < deadline:
            rows = self.outer('capture-pane', '-p', '-e', '-t', 'view').splitlines()
            row = rows[self.row] if len(rows) > self.row else ''
            plain = self.fixture.plain(row)
            if (label in plain and (text is None or plain.rstrip() == text.rstrip())
                    and (check is None or check(plain))):
                if self.fixture.colors_at(row, label)['fg'] == expected:
                    return row
            time.sleep(.08)
        self.fail('Codex status did not render: ' + repr(row))

    def test_native_colors_titles_warnings_widths_and_failure(self):
        self.inner('set-option', '-g', 'renumber-windows', 'off')
        pane = self.inner('new-window', '-d', '-P', '-F', '#{pane_id}', '-n', 'agent', self.command('wrapped', True))
        self.pid('wrapped')
        self.assertNotEqual(self.inner('display-message', '-p', '-t', pane, '#{pane_current_command}'), 'codex')
        # An unrelated pane's title must not produce a Codex marker.
        self.inner('select-pane', '-t', ':0', '-T', 'Waiting | Working')
        self.view()
        accent, green, red = (171, 205, 239), (85, 255, 85), (255, 85, 85)
        foreground, inactive_foreground = (255, 238, 221), (238, 238, 238)
        dark_foreground = (119, 136, 153)
        magenta = (221, 102, 204)
        self.color('1 agent', magenta, ' 0 shell │ 1 agent ')
        cases = [('project | Working | cwd', ''), ('project | Working. | cwd', ''),
                 ('project | Working… | cwd', ''), ('project | Not Working | cwd', ''),
                 ('Working directory', ''), ('', ''), ('project | Ready | cwd', ''),
                 ('Waiting', ''), ('project | Waiting | cwd', ''),
                 ('project | Waiting... | cwd', ''), ('Waiting…', ''),
                 ('Waiting | Working', ''), ('Working | Waiting', ''),
                 ('Not Waiting', ''), ('Waiting for input', ''), ('waiting', ''),
                 ('[ ! ] Action Required | project | Working | cwd', ''),
                 ('project | [ . ] Action Required | cwd', ''), ('[ ! ] Action Required', ''),
                 ('project | [ ! ] Action Required extra | cwd', ''),
                 ('project | Not [ ! ] Action Required | cwd', ''),
                 ('Action Required', ''), ('[ ? ] Action Required', ''),
                 ('#{@bad}#(touch BAD) | Working | cwd', '')]
        for title, marker in cases:
            self.inner('select-pane', '-t', pane, '-T', title)
            label = '1 agent' + (' ' + marker if marker else '')
            row = self.color(label, magenta, ' 0 shell │ ' + label + ' ')
            self.assertTrue(self.fixture.bold_at(row, label))
            self.assertTrue(self.fixture.bold_at(row, 'agent'))
            self.assertEqual(self.fixture.colors_at(row, 'agent')['fg'], inactive_foreground)
            self.assertTrue(self.fixture.dim_at(row, 'agent'))
            self.assertFalse(self.fixture.bold_at(row, label, 1))
            if marker:
                self.assertEqual(self.fixture.colors_at(row, marker)['fg'], accent)
                self.assertEqual(self.fixture.bold_at(row, marker), marker == '')
        for width in (40, 80, 120):
            self.outer('resize-window', '-t', 'view', '-x', str(width), '-y', '24')
            for title, marker in (('project | Working | cwd', ''),
                                  ('project | Waiting | cwd', '')):
                self.inner('select-pane', '-t', pane, '-T', title)
                label = '1 agent' + (' ' + marker if marker else '')
                row = self.color(label, magenta, ' 0 shell │ ' + label + ' ')
                style = {'fg': accent, 'bg': (34, 51, 68)}
                for part in (label, marker, 'agent'):
                    self.assertEqual(self.fixture.colors_at(row, part),
                                     dict(style, fg=inactive_foreground if part == 'agent' else magenta if part == label else accent))
                    self.assertEqual(self.fixture.bold_at(row, part), True if part in (label, 'agent') else marker == '')
                    self.assertEqual(self.fixture.dim_at(row, part), part == 'agent')
                    self.assertFalse(self.fixture.underline_at(row, part))
                self.assertEqual(self.fixture.colors_at(row, label, 1)['fg'], (34, 51, 68))
                self.assertFalse(self.fixture.bold_at(row, label, 1))
                self.assertFalse(self.fixture.bold_at(row, '│ ' + label))
                self.inner('set-option', '-w', '-t', pane, '@dots-window-alert', '1')
                row = self.color('[' + label + ']', red, ' 0 shell │[' + label + ']')
                self.assertTrue(self.fixture.bold_at(row, marker))
                self.assertEqual(self.fixture.colors_at(row, marker), {'fg': red, 'bg': (1, 2, 3)})
                self.assertEqual(self.fixture.colors_at(row, 'agent'), {'fg': red, 'bg': (1, 2, 3)})
                self.assertTrue(self.fixture.bold_at(row, 'agent'))
                self.assertFalse(self.fixture.dim_at(row, 'agent'))
                self.assertEqual(self.fixture.colors_at(row, ']')['fg'], red)
                self.inner('select-window', '-t', pane)
                self.color('[' + label + ']', red)
                self.inner('set-option', '-uw', '-t', pane, '@dots-window-alert')
                row = self.color(label, green)
                self.assertTrue(self.fixture.bold_at(row, marker))
                self.assertEqual(self.fixture.colors_at(row, marker), {'fg': accent, 'bg': (85, 102, 119)})
                self.assertEqual(self.fixture.colors_at(row, 'agent'),
                                 {'fg': foreground, 'bg': (85, 102, 119)})
                self.assertTrue(self.fixture.bold_at(row, 'agent'))
                self.assertFalse(self.fixture.dim_at(row, 'agent'))
                self.assertFalse(self.fixture.dim_at(row, 'agent', len('agent')))
                self.assertEqual(self.fixture.colors_at(row, 'agent', len('agent'))['fg'], green)
                self.inner('rename-window', '-t', pane, 'fixture')
                self.color('1 ' + marker, green, ' 0 shell │ 1 ' + marker + ' ')
                self.inner('set-option', '-w', '-t', pane, '@dots-window-alert', '1')
                self.color('[1 ' + marker + ']', red, ' 0 shell │[1 ' + marker + ']')
                self.inner('set-option', '-uw', '-t', pane, '@dots-window-alert')
                self.inner('rename-window', '-t', pane, 'agent')
                self.inner('select-window', '-t', ':0')
                self.inner('select-pane', '-t', pane, '-T', 'project | Ready | cwd')
                row = self.color('1 agent', magenta, ' 0 shell │ 1 agent ')
                self.assertTrue(self.fixture.bold_at(row, 'agent'))
            self.inner('select-pane', '-t', pane, '-T', 'project | Working | cwd')
            self.inner('rename-window', '-t', pane, 'long-project-' * 12)
            row = self.color('1 long-', magenta)
            # Trailing icons follow native clipping when a long name fills the row.
            self.assertLessEqual(len(self.fixture.plain(row)), width)
            self.inner('rename-window', '-t', pane, 'fixture')
            extra_name = 'adjacent-' + str(width)
            extra = self.inner('new-window', '-d', '-P', '-F', '#{pane_id}',
                               '-n', 'fixture', self.command(extra_name))
            self.pid(extra_name)
            self.inner('select-pane', '-t', extra, '-T', 'Working')
            row = self.color('2 ', magenta, ' 0 shell │ 1  │ 2  ')
            for label in ('1 ', '2 '):
                self.assertTrue(self.fixture.bold_at(row, label, 2))
                self.assertEqual(self.fixture.colors_at(row, label, 2)['fg'], accent)
                self.assertFalse(self.fixture.dim_at(row, label, 2))
            self.assertFalse(self.fixture.bold_at(row, '│ 2 '))
            self.inner('select-pane', '-t', extra, '-T', '[ ! ] Action Required')
            row = self.color('2 ', magenta, ' 0 shell │ 1  │ 2  ')
            self.assertFalse(self.fixture.bold_at(row, ''))
            self.inner('select-window', '-t', pane)
            row = self.color('1 ', green, ' 0 shell │ 1  │ 2  ')
            self.assertTrue(self.fixture.bold_at(row, ''))
            self.inner('set-option', '-w', '-t', extra, '@dots-window-alert', '1')
            self.color('[2 ]', red, ' 0 shell │ 1  │[2 ]')
            self.inner('kill-window', '-t', extra)
            self.inner('select-window', '-t', ':0')
            self.inner('rename-window', '-t', pane, 'agent')
        self.assertFalse((self.fixture.home / 'BAD').exists())
        # Match entire IDs: @1 must not match @10 in either state.
        window = self.inner('display-message', '-p', '-t', pane, '#{window_id}')
        for state in ('working', 'waiting'):
            self.inner('set-option', '-g', '@dots-codex-snapshot', '|' + window + '0:' + state + '|')
            row = self.color('1 agent', dark_foreground)
            self.assertTrue(self.fixture.bold_at(row, 'agent'))
            self.assertEqual(self.fixture.colors_at(row, 'agent')['fg'], dark_foreground)
            self.assertTrue(self.fixture.dim_at(row, 'agent'))
        self.inner('source-file', str(self.config))
        self.inner('set-option', '-g', 'status-interval', '1')
        self.inner('select-pane', '-t', pane, '-T', '[ . ] Action Required | project | Working | cwd')
        self.color('1 agent ', magenta)
        helper = self.fixture.tmux_config / 'codex-status.py'
        saved = helper.read_bytes()
        helper.unlink()
        row = self.color('1 agent', dark_foreground)
        self.assertTrue(self.fixture.bold_at(row, '1 agent'))
        helper.write_bytes(saved)
        self.color('1 agent ', magenta)
        self.inner('set-environment', '-gu', 'TERMUX_VERSION')
        self.inner('source-file', str(self.config))
        self.row = 0
        for title, marker in (('project | Working | cwd', ''), ('Waiting', '')):
            self.inner('select-pane', '-t', pane, '-T', title)
            row = self.color('1 agent ' + marker, magenta, ' 0 shell │ 1 agent ' + marker + ' ')
            self.assertTrue(self.fixture.bold_at(row, '1 agent ' + marker))
            self.assertEqual(self.fixture.bold_at(row, marker), marker == '')
            self.assertEqual(self.fixture.colors_at(row, 'agent')['fg'], inactive_foreground)
            self.assertTrue(self.fixture.dim_at(row, 'agent'))
            self.assertFalse(self.fixture.bold_at(row, '1 agent ' + marker, 1))

    def test_native_singleton_markers_names_and_visibility(self):
        pane = self.inner('new-window', '-d', '-P', '-F', '#{pane_id}', '-n', 'agent', self.command('only'))
        self.pid('only')
        self.inner('kill-window', '-t', ':0')
        self.view()
        accent, red = (171, 205, 239), (255, 85, 85)
        for width in (40, 80, 120):
            self.outer('resize-window', '-t', 'view', '-x', str(width), '-y', '24')
            for title, marker in (('project | Working | cwd', ''), ('Waiting', '')):
                self.inner('select-pane', '-t', pane, '-T', title)
                for name, label in (('agent', 'agent ' + marker), ('fixture', marker)):
                    self.inner('rename-window', '-t', pane, name)
                    row = self.color(label, (255, 238, 221) if name == 'agent' else accent, ' ' + label + ' ')
                    self.assertEqual(self.fixture.colors_at(row, marker)['fg'], accent)
                    self.assertFalse(self.fixture.dim_at(row, marker))
                    self.assertTrue(self.fixture.bold_at(row, marker))
                    if name == 'agent':
                        self.assertEqual(self.fixture.colors_at(row, 'agent')['fg'], (255, 238, 221))
                        self.assertTrue(self.fixture.bold_at(row, 'agent'))
                        self.assertEqual(self.fixture.colors_at(row, 'agent')['bg'], (85, 102, 119))
                    self.inner('set-option', '-w', '-t', pane, '@dots-window-alert', '1')
                    self.color('[' + label + ']', red, '[' + label + ']')
                    self.inner('set-option', '-uw', '-t', pane, '@dots-window-alert')
            self.inner('select-pane', '-t', pane, '-T', 'project | Ready | cwd')
            self.fixture.await_screen(self.outer, 'view', lambda rows: rows[1].rstrip() == '')
        # Neither marker nor a separator leaks when a hidden singleton is idle.
        self.inner('rename-window', '-t', pane, 'agent')
        row = self.color('agent', (255, 238, 221), ' agent ')
        self.assertTrue(self.fixture.bold_at(row, 'agent'))
        self.assertEqual(self.fixture.colors_at(row, 'agent')['bg'], (85, 102, 119))

    def test_native_session_markers_widths_transitions_and_failure(self):
        pane = self.inner('new-window', '-d', '-P', '-F', '#{pane_id}', '-n', 'dots', self.command('session'))
        pid = self.pid('session')
        self.inner('kill-window', '-t', ':0')
        self.inner('set-option', '-t', 'fixture', '@dots-workspace-data', '{"schema":1}')
        self.inner('set-option', '-t', 'fixture', '@dots-workspace-auto', '1')
        self.inner('set-option', '-t', 'fixture', '@dots-workspace-label', 'dots')
        self.view()
        accent, cyan, red = (171, 205, 239), (85, 255, 255), (255, 85, 85)
        for termux in (True, False):
            if not termux:
                self.inner('set-environment', '-gu', 'TERMUX_VERSION')
                self.inner('source-file', str(self.config))
                self.inner('set-option', '-g', 'status-interval', '1')
                self.row = 0
            self.inner('set-option', '-g', '@dots-git-snapshot', '󰊤|')
            for width in (40, 80, 120):
                self.outer('resize-window', '-t', 'view', '-x', str(width), '-y', '24')
                for title, marker in (('Working', ''), ('Waiting | Working', '')):
                    self.inner('select-pane', '-t', pane, '-T', title)
                    row = self.color('dots', cyan, ' 󰊤 dots ' + marker + ' ')
                    self.assertEqual(self.fixture.plain(row).count(marker), 1)
                    self.assertEqual(self.fixture.colors_at(row, marker), {'fg': accent, 'bg': (85, 102, 119)})
                    self.assertTrue(self.fixture.bold_at(row, marker))
                    self.assertFalse(self.fixture.dim_at(row, marker))
                    self.assertFalse(self.fixture.underline_at(row, marker))
                    # The trailing padding restores the session's foreground.
                    self.assertEqual(self.fixture.colors_at(row, marker, 1), {'fg': cyan, 'bg': (85, 102, 119)})
                    self.inner('set-option', '-t', 'fixture', '@dots-session-number', '2')
                    long_name = 'project-界-' * 10
                    self.inner('set-option', '-t', 'fixture', '@dots-workspace-label', long_name)
                    self.inner('rename-window', '-t', pane, long_name)
                    row = self.color('2 󰊤 pr', cyan, check=lambda plain: plain.rstrip().endswith(' ' + marker))
                    label = self.fixture.plain(row).rstrip() + ' '
                    self.assertTrue(label.startswith(' 2 󰊤 '), label)
                    self.assertTrue(label.endswith(' ' + marker + ' '), label)
                    self.assertEqual(label.count(marker), 1)
                    self.assertNotIn('│', label)
                    self.inner('set-option', '-g', '@fixture-label', label)
                    cells = int(self.inner('display-message', '-p', '#{w:@fixture-label}'))
                    self.assertLessEqual(cells, min(width // 4, 30) if termux else 31)
                    self.inner('set-option', '-t', 'fixture', '@dots-session-number', '')
                    self.inner('set-option', '-t', 'fixture', '@dots-workspace-label', 'dots')
                    self.inner('rename-window', '-t', pane, 'dots')
            self.inner('rename-window', '-t', pane, 'editor')
            self.color('dots', cyan, ' 󰊤 dots │ editor  ')
            self.inner('rename-window', '-t', pane, 'dots')
            self.inner('set-option', '-w', '-t', pane, '@dots-window-alert', '1')
            self.color('[]', red, ' 󰊤 dots │[]')
            self.inner('set-option', '-uw', '-t', pane, '@dots-window-alert')
            self.color('dots', cyan, ' 󰊤 dots  ')
            self.inner('set-option', '-g', '@dots-git-snapshot', '󰊤|branch')
            self.color('dots', cyan, ' 󰊤 dots  │ branch ')
            self.inner('set-option', '-g', '@dots-git-snapshot', '󰊤|')
            self.inner('select-pane', '-t', pane, '-T', 'Ready')
            self.color('dots', cyan, ' 󰊤 dots ')
        self.inner('select-pane', '-t', pane, '-T', 'Waiting')
        other = self.inner('split-window', '-t', pane, '-P', '-F', '#{pane_id}', self.command('session-other'))
        self.pid('session-other')
        self.inner('select-pane', '-t', other, '-T', 'Working')
        self.color('dots', cyan, ' 󰊤 dots  ')
        self.inner('kill-pane', '-t', other)
        self.color('dots', cyan, ' 󰊤 dots  ')
        helper = self.fixture.tmux_config / 'codex-status.py'
        saved = helper.read_bytes()
        helper.unlink()
        self.color('dots', cyan, ' 󰊤 dots ')
        helper.write_bytes(saved)
        self.color('dots', cyan, ' 󰊤 dots  ')
        self.inner('set-option', '-w', '-t', pane, 'remain-on-exit', 'on')
        os.kill(pid, signal.SIGTERM)
        self.color('dots', cyan, ' 󰊤 dots ')

    def test_any_pane_aggregation_foreground_stop_exit_and_dead_panes(self):
        magenta, dark_foreground = (221, 102, 204), (119, 136, 153)
        # tmux resumes its direct child on SIGSTOP; suspend the wrapped child.
        first = self.inner('new-window', '-d', '-P', '-F', '#{pane_id}', '-n', 'agent', self.command('first', True))
        first_pid = self.pid('first')
        self.inner('select-pane', '-t', first, '-T', 'project | Working | cwd')
        shell = self.inner('split-window', '-t', first, '-P', '-F', '#{pane_id}', 'sleep 120')
        self.inner('select-window', '-t', ':0')
        self.view()
        self.color('1 agent ', magenta)  # Codex is in the unselected pane.
        second = self.inner('split-window', '-t', shell, '-P', '-F', '#{pane_id}', self.command('second'))
        self.pid('second')
        self.inner('select-pane', '-t', second, '-T', 'Waiting | project | Working | cwd')
        self.inner('select-window', '-t', ':0')
        self.color('1 agent ', magenta)
        self.inner('select-pane', '-t', first, '-T', 'project | Idle | cwd')
        self.color('1 agent ', magenta)
        self.inner('select-pane', '-t', second, '-T', 'project | Working | cwd')
        self.color('1 agent ', magenta)
        self.inner('kill-pane', '-t', second)
        self.inner('select-pane', '-t', first, '-T', '[ . ] Action Required | project | Working | cwd')
        self.color('1 agent ', magenta)
        try:
            os.kill(first_pid, signal.SIGSTOP)
            self.color('1 agent', dark_foreground)
        finally:
            os.kill(first_pid, signal.SIGCONT)
        self.color('1 agent ', magenta)
        self.inner('set-option', '-w', '-t', first, 'remain-on-exit', 'on')
        self.inner('select-pane', '-t', first, '-T', 'project | Working | cwd')
        os.kill(first_pid, signal.SIGTERM)
        self.color('1 agent', dark_foreground)
        self.assertEqual(self.inner('display-message', '-p', '-t', first, '#{pane_dead}'), '1')


if __name__ == '__main__':
    unittest.main()

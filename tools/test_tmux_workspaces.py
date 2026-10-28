#!/usr/bin/env python3
"""Workspace lifecycle and continuous rendering on owned tmux sockets."""
import json
import os
from pathlib import Path
import runpy
import shlex
import shutil
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

import test_tmux_status as status_fixture
REPO, TMUX, BASH = status_fixture.REPO, status_fixture.TMUX, status_fixture.BASH
sys.path.insert(0, str(REPO / 'lib/dots'))
from tmux_workspaces import Workspaces, project_root


@unittest.skipUnless(TMUX and BASH, 'native tmux/Bash unavailable')
class WorkspacesTest(unittest.TestCase):
    def setUp(self):
        self.fx = status_fixture.TmuxStatus(); self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.addCleanup(patch.stopall)
        patch.dict(os.environ, self.fx.env, clear=True).start()
        self.inner, self.base = self.fx.server('workspaces')
        self.inner('set-option', '-g', 'default-shell', BASH)
        self.inner('set-option', '-g', 'default-command', shlex.join([BASH, '--noprofile', '--norc']))
        self.w = Workspaces(socket=self.base[-1])
        self.alpha = self.repo('alpha')
        self.beta = self.repo('beta')

    def repo(self, name):
        root = self.fx.home / name; root.mkdir(parents=True)
        subprocess.run(['git', 'init', '-q', str(root)], env=self.fx.env, check=True)
        return root

    def wait(self, predicate):
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(.04)
        self.fail('workspace event did not complete')

    def pane(self, session):
        return self.inner('display-message', '-p', '-t', session + ':', '#{pane_id}')

    def cd(self, pane, directory, reconcile=True):
        self.inner('send-keys', '-t', pane, '-l', 'cd -- ' + shlex.quote(str(directory)))
        self.inner('send-keys', '-t', pane, 'Enter')
        self.wait(lambda: self.inner('display-message', '-p', '-t', pane, '#{pane_current_path}') == str(directory))
        if reconcile:
            self.w.reconcile(pane)

    def config(self):
        self.fx.write_theme()
        self.inner('source-file', str(self.fx.write_config()))
        self.inner('set-option', '-gw', 'automatic-rename', 'off')

    def viewers(self, sessions, width=80):
        outer, _ = self.fx.server('viewers', termux=False)
        outer('set-option', '-g', 'status', 'off')
        outer('set-option', '-g', 'default-terminal', 'tmux-256color')
        terminals = []
        for index, session in enumerate(sessions):
            outer('new-session', '-d', '-s', 'view' + str(index), '-x', str(width), '-y', '24',
                  shlex.join(['env', '-u', 'TMUX', '-u', 'TMUX_PANE', *self.base, 'attach-session', '-t', session]))
            terminals.append(outer('display-message', '-p', '-t', 'view' + str(index), '#{pane_tty}'))
        self.fx.snapshot(terminals)
        self.wait(lambda: len(self.inner('list-clients', '-F', '#{client_name}').splitlines()) == len(sessions))
        return outer, terminals

    def test_prefix_creation_and_popup_creation_switch_only_invoking_client(self):
        self.config()
        first = self.w.create(str(self.alpha)); second = self.w.create(str(self.beta))
        outer, terminals = self.viewers((first, second))
        def clients():
            return dict(row.split('|') for row in self.inner('list-clients', '-F', '#{client_name}|#{session_id}').splitlines())
        outer('send-keys', '-t', 'view0', 'C-Space', 'C')
        self.wait(lambda: clients()[terminals[0]] != first)
        created = clients()[terminals[0]]
        self.assertEqual(clients()[terminals[1]], second)
        self.assertTrue(self.w.name(created).startswith('alpha-'))
        self.assertNotEqual(self.w.metadata(created)['id'], self.w.metadata(first)['id'])
        from menu_sessions import Server, create_session
        from menu_tmux import TmuxContext
        pane = self.pane(created)
        with patch.dict(os.environ, TMUX=self.base[-1] + ',0,0', TMUX_PANE=pane):
            context = TmuxContext.capture(client=terminals[0])
            server, record = create_session(Server.discover(), None, str(self.beta), context=context)
            server.select(record, context)
        self.assertTrue(record.name.startswith('beta-'))
        self.assertEqual(clients()[terminals[0]], record.id)
        self.assertEqual(clients()[terminals[1]], second)
        self.assertEqual(len(clients()), 2)

    def test_sustained_two_client_rows_and_independent_numbering(self):
        self.inner('respawn-pane', '-k', '-t', '$0:', 'sleep 300')
        self.config()
        # A deterministic asynchronous provider isolates rendering from Git I/O.
        (self.fx.tmux_config / 'gitmux-status.py').write_text(
            'print("󰊤|#[fg=#{@dots-gitmux-branch}]main#[default]")\n')
        self.inner('set-option', '-g', 'status-interval', '1')
        first = self.w.create(str(self.alpha)); second = self.w.create(str(self.beta))
        self.inner('rename-window', '-t', first + ':', 'alpha')
        self.inner('rename-window', '-t', second + ':', 'beta')
        for name in ('editor', 'agent', 'tools'):
            self.inner('new-window', '-d', '-t', first, '-c', str(self.alpha), '-n', name, 'sleep 300')
        outer, terminals = self.viewers((first, second))
        def frame(index):
            # A nested terminal can be captured midway through a redraw. Wait
            # for two identical observations, independent of expected content:
            # a stable empty/missing row still fails the assertions below.
            previous = None
            deadline = time.monotonic() + 3
            while True:
                rows = self.fx.plain(outer('capture-pane', '-p', '-t', 'view' + str(index))).splitlines()
                if rows[:2] == previous:
                    return rows
                self.assertLess(time.monotonic(), deadline, 'status never settled')
                previous = rows[:2]
                time.sleep(.1)
        for width in (40, 80, 120):
            for index in range(2):
                outer('resize-window', '-t', 'view' + str(index), '-x', str(width), '-y', '24')
            for index in range(2):
                self.fx.await_screen(outer, 'view' + str(index), lambda rows:
                    len(rows) > 1 and f' {index + 1} ' in rows[0] and 'main' in rows[1])
            for sample in range(45):
                for index in range(2):
                    rows = frame(index)
                    self.assertGreater(len(rows), 1)
                    self.assertIn('80%', rows[0])
                    self.assertIn('main', rows[1])
                    self.assertTrue(rows[1].startswith(' 󰊤 ' + ('alpha', 'beta')[index] + ' '), repr(rows[1]))
                    self.assertNotIn(self.w.metadata((first, second)[index])['id'], rows[1])
                time.sleep(.04)
        # A second alpha workspace adds a group-local number only to alpha.
        duplicate = self.w.create(str(self.alpha))
        self.fx.await_screen(outer, 'view0', lambda rows: len(rows) > 1 and rows[1].startswith(' 1 󰊤 alpha '))
        # Both tabs view the same tmux workspace: top highlights differ, lower numbers agree.
        self.inner('switch-client', '-c', terminals[1], '-t', first)
        for index in range(2):
            self.fx.await_screen(outer, 'view' + str(index), lambda rows:
                len(rows) > 1 and rows[1].startswith(' 1 ') and 'main' in rows[1])
        # Slow provider refreshes retain the last successful result in each client.
        provider = self.fx.tmux_config / 'gitmux-status.py'
        observed = self.fx.home / 'slow-provider'
        provider.write_text('import time\nfrom pathlib import Path\n'
                            f'Path({str(observed)!r}).touch()\ntime.sleep(.3)\n'
                            'print("󰊤|#[fg=#{@dots-gitmux-branch}]main#[default]")\n')
        self.wait(observed.exists)
        for _ in range(30):
            for index in range(2):
                rows = frame(index)
                self.assertIn('main', rows[1])
                self.assertTrue(rows[1].startswith(' 1 '))
            time.sleep(.04)
        provider.write_text('print("|")\n')
        for index in range(2):
            self.fx.await_screen(outer, 'view' + str(index), lambda rows:
                len(rows) > 1 and rows[1].startswith(' 1 ') and 'alpha' in rows[1] and '' not in rows[1])
        self.inner('kill-session', '-t', duplicate)
        self.fx.await_screen(outer, 'view0', lambda rows: len(rows) > 1 and rows[1].startswith(' alpha '))
        outer('kill-session', '-t', 'view1')
        self.fx.snapshot([terminals[0]])
        self.fx.await_screen(outer, 'view0', lambda rows:
            len(rows) > 1 and rows[1].startswith(' alpha ') and '│' not in rows[0])
        # Failed background hooks open a tmux output pager; even a readable
        # status row must not hide that lifecycle failure.
        self.assertEqual(set(self.inner('list-panes', '-a', '-F', '#{pane_in_mode}').splitlines()), {'0'})

    def test_group_numbers_match_picker_and_preserve_failed_inventory(self):
        from menu_projects import associate, discover
        from types import SimpleNamespace
        first = self.w.create(str(self.alpha))
        second = self.w.create(str(self.alpha))
        beta = self.w.create(str(self.beta))
        same_name = self.w.create(str(self.repo('nested/alpha')))
        alias = self.fx.home / 'alias'; alias.symlink_to(self.alpha, target_is_directory=True)
        third = self.w.create(str(alias))
        def numbers():
            return [self.w.option(x, '@dots-session-number') for x in (first, second, third, beta, same_name)]
        self.assertEqual(numbers(), ['1', '2', '3', '', ''])
        groups = [associate(self.w, SimpleNamespace(id=x), discover()).root
                  for x in (first, second, third, beta, same_name)]
        self.assertEqual(groups[:3], [self.alpha] * 3)
        self.assertNotEqual(groups[0], groups[4])
        with patch.object(self.w, 'batch', wraps=self.w.batch) as batch:
            self.w.renumber()
        self.assertEqual(batch.call_args.args[0], [])
        # A detached session still counts; project moves update both groups.
        self.assertEqual(self.inner('display-message', '-p', '-t', second, '#{session_attached}'), '0')
        self.cd(self.pane(second), self.beta)
        self.assertEqual(numbers(), ['1', '1', '2', '2', ''])
        previous = numbers()
        saved = self.w.option(same_name, '@dots-workspace-data')
        self.inner('set-option', '-t', same_name + ':', '@dots-workspace-data', 'broken')
        with self.assertRaises(ValueError):
            self.w.renumber()
        self.assertEqual(numbers(), previous)
        self.inner('set-option', '-t', same_name + ':', '@dots-workspace-data', saved)
        self.inner('kill-session', '-t', third)
        self.w.renumber()
        self.assertEqual(self.w.option(first, '@dots-session-number'), '')

    def test_queued_number_worker_keeps_its_observation_budget(self):
        import fcntl
        import hashlib
        first = self.w.create(str(self.alpha)); second = self.w.create(str(self.alpha))
        key = hashlib.sha256(f'{self.w.socket}:{self.w.pid}'.encode()).hexdigest()
        lock = self.fx.root / 'run' / f'dots-tmux-workspaces-{os.getuid()}' / key
        with lock.open('r+') as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            worker = subprocess.Popen([sys.executable, '-B', str(self.fx.tmux_config / 'workspace-control.py'),
                                       'numbers', '--socket', self.w.socket], env=self.fx.env,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                # A legitimate queued event can outlast the former entire budget.
                time.sleep(3.2)
                self.assertIsNone(worker.poll())
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
                output, error = worker.communicate(timeout=15)
                self.assertEqual((worker.returncode, output, error), (0, '', ''))
            finally:
                if worker.poll() is None:
                    worker.kill(); worker.communicate()
        self.assertEqual(self.w.option(first, '@dots-session-number'), '1')
        self.assertEqual(self.w.option(second, '@dots-session-number'), '2')

    def test_default_multi_and_manual_label_groups(self):
        first = self.w.create(str(self.fx.home)); second = self.w.create(str(self.fx.home))
        def numbers():
            return [self.w.option(x, '@dots-session-number') for x in (first, second)]
        self.assertEqual(numbers(), ['1', '2'])
        for target in (first, second):
            self.cd(self.pane(target), self.alpha)
            self.inner('split-window', '-d', '-t', target, '-c', str(self.beta), 'sleep 120')
            self.w.reconcile(session=target)
        self.assertEqual(numbers(), ['1', '2'])
        self.assertEqual(self.w.option(first, '@dots-workspace-label'), 'multi')
        self.inner('rename-session', '-t', first, 'personal')
        self.w.reconcile(session=first)
        self.assertEqual(numbers(), ['', ''])
        # Manual multi matches the logical auto label, but case is literal.
        self.inner('rename-session', '-t', first, 'multi')
        self.w.reconcile(session=first)
        self.assertEqual(numbers(), ['1', '2'])
        self.inner('rename-session', '-t', first, 'Multi')
        self.w.reconcile(session=first)
        self.assertEqual(numbers(), ['', ''])

    def test_all_panes_transitions_keep_identity_and_manual_override(self):
        ident = self.w.create(str(self.fx.home))
        data = self.w.metadata(ident); suffix = data['id']
        pane = self.pane(ident)
        self.assertEqual(self.w.name(ident), 'termux-' + suffix)
        self.cd(pane, self.alpha)
        self.assertEqual(self.w.name(ident), 'alpha-' + suffix)
        other = self.inner('split-window', '-d', '-P', '-F', '#{pane_id}', '-t', pane,
                           '-c', str(self.fx.home), shlex.join([BASH, '--noprofile', '--norc']))
        self.w.reconcile(other)
        self.assertEqual(self.w.name(ident), 'alpha-' + suffix)
        self.cd(other, self.beta)
        self.assertEqual(self.w.name(ident), 'multi-' + suffix)
        self.cd(pane, self.fx.home)
        self.assertEqual(self.w.name(ident), 'beta-' + suffix)
        self.cd(other, self.fx.home)
        self.assertEqual(self.w.name(ident), 'termux-' + suffix)
        self.cd(pane, self.beta)
        self.cd(pane, self.alpha)
        self.assertEqual(self.w.name(ident), 'alpha-' + suffix)
        self.inner('rename-session', '-t', ident, 'my-manual-workspace')
        self.w.reconcile()
        self.cd(pane, self.beta)
        self.assertEqual(self.w.name(ident), 'my-manual-workspace')
        self.assertFalse(self.w.metadata(ident)['auto'])
        self.assertEqual(self.w.metadata(ident)['id'], suffix)
        self.assertEqual(self.w.metadata(ident)['projects'], [str(self.beta)])

    def test_git_worktree_configured_nested_and_same_basename_roots(self):
        configured = self.fx.home / 'configured'; configured.mkdir()
        nested = configured / 'child'; nested.mkdir()
        config = self.fx.config / 'dots/projects.json'; config.parent.mkdir()
        config.write_text(json.dumps(dict(schema=1, projects=[str(configured)])))
        self.assertEqual(project_root(nested), configured)
        duplicate = self.repo('another/alpha')
        ident = self.w.create(str(self.alpha)); pane = self.pane(ident)
        self.inner('split-window', '-d', '-t', pane, '-c', str(duplicate), 'sleep 120')
        self.w.reconcile()
        self.assertTrue(self.w.name(ident).startswith('multi-'))
        worktree = self.fx.home / 'linked-worktree'
        subprocess.run(['git', '-C', str(self.alpha), '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                        'commit', '--allow-empty', '-qm', 'fixture'], env=self.fx.env, check=True)
        subprocess.run(['git', '-C', str(self.alpha), 'worktree', 'add', '-qb', 'other', str(worktree)],
                       env=self.fx.env, check=True, capture_output=True)
        self.assertEqual(project_root(worktree), worktree)
        main_session = self.w.create(str(self.alpha))
        linked_session = self.w.create(str(worktree))
        self.assertEqual(self.w.option(main_session, '@dots-session-number'), '')
        self.assertEqual(self.w.option(linked_session, '@dots-session-number'), '')

    def test_literal_names_noop_updates_and_observation_failures(self):
        root = self.repo('-café #{@literal};')
        ident = self.w.create(str(root)); suffix = self.w.metadata(ident)['id']
        self.assertEqual(self.w.name(ident), root.name + '-' + suffix)
        self.cd(self.pane(ident), self.alpha)
        self.cd(self.pane(ident), root)
        self.assertEqual(self.w.name(ident), root.name + '-' + suffix)
        with patch.object(self.w, 'store', side_effect=AssertionError('no-op wrote metadata')):
            self.w.reconcile()
        before = self.w.metadata(ident)
        for failure in (ValueError('directory unavailable'), subprocess.TimeoutExpired('git', 1)):
            with patch('tmux_workspaces.project_root', side_effect=failure):
                with self.assertRaises((ValueError, subprocess.SubprocessError)):
                    self.w.reconcile()
            self.assertEqual(self.w.metadata(ident), before)
            self.assertEqual(self.w.name(ident), root.name + '-' + suffix)
        with self.assertRaises(ValueError):
            project_root(self.fx.home / 'missing')
        with patch('tmux_workspaces.shutil.which', return_value=None):
            with self.assertRaises(ValueError):
                project_root(root)
        alias = self.fx.home / 'alias'; alias.symlink_to(root, target_is_directory=True)
        self.assertEqual(project_root(alias), root)
        self.inner('split-window', '-d', '-t', ident, '-c', str(alias).replace('#', '##'), 'sleep 120')
        self.w.reconcile()
        self.assertEqual(self.w.metadata(ident)['projects'], [str(root)])
        self.config()
        self.inner('set-option', '-g', '@literal', 'EXPANDED')
        outer, _ = self.viewers((ident,), width=120)
        rows = self.fx.await_screen(outer, 'view0', lambda rows:
            len(rows) > 1 and '#{@literal};' in rows[1])
        self.assertNotIn('EXPANDED', rows[1])

    def test_collision_and_invalid_metadata_preserve_unrelated_sessions(self):
        ident = self.w.create(str(self.fx.home)); suffix = self.w.metadata(ident)['id']
        occupied = 'alpha-' + suffix
        self.inner('new-session', '-d', '-s', occupied, 'sleep 120')
        self.cd(self.pane(ident), self.alpha, reconcile=False)
        with self.assertRaisesRegex(ValueError, 'occupied'):
            self.w.reconcile()
        self.assertEqual(self.w.name(ident), 'termux-' + suffix)
        for bad in ({'schema': True}, dict(self.w.metadata(ident), auto='yes'),
                    dict(self.w.metadata(ident), projects=['relative'])):
            self.inner('set-option', '-t', ident + ':', '@dots-workspace-data', json.dumps(bad))
            with self.assertRaisesRegex(ValueError, 'metadata'):
                self.w.reconcile()
        self.assertEqual(self.w.name('$0'), 'fixture')

    def test_targeted_update_includes_linked_windows_and_skips_unrelated_metadata(self):
        first = self.w.create(str(self.alpha)); second = self.w.create(str(self.beta))
        unrelated = self.w.create(str(self.fx.home))
        self.inner('set-option', '-t', unrelated + ':', '@dots-workspace-data', 'malformed')
        window = self.inner('display-message', '-p', '-t', first, '#{window_id}')
        self.inner('link-window', '-d', '-s', window, '-t', second + ':2')
        self.w.reconcile(session=first)
        self.assertTrue(self.w.name(first).startswith('alpha-'))
        self.assertTrue(self.w.name(second).startswith('multi-'))
        self.cd(self.pane(first), self.fx.home, reconcile=False)
        self.w.reconcile(session=first)
        self.assertTrue(self.w.name(first).startswith('termux-'))
        self.assertTrue(self.w.name(second).startswith('beta-'))

    def test_closure_hooks_manual_rename_and_numbering(self):
        self.config()
        ident = self.w.create(str(self.alpha)); suffix = self.w.metadata(ident)['id']
        self.inner('new-window', '-d', '-t', ident, '-c', str(self.beta), '-n', 'beta', 'sleep 120')
        self.wait(lambda: self.w.name(ident) == 'multi-' + suffix)
        self.inner('kill-window', '-t', ident + ':2')
        self.wait(lambda: self.w.name(ident) == 'alpha-' + suffix)
        other = self.inner('split-window', '-d', '-P', '-F', '#{pane_id}', '-t', ident,
                           '-c', str(self.beta), shlex.join([BASH, '--noprofile', '--norc']))
        self.wait(lambda: self.w.name(ident) == 'multi-' + suffix)
        self.inner('send-keys', '-t', other, 'exit', 'Enter')
        self.wait(lambda: self.w.name(ident) == 'alpha-' + suffix)
        self.inner('rename-session', '-t', ident, 'personal')
        self.wait(lambda: not self.w.metadata(ident)['auto'])
        self.assertEqual(self.w.option(ident, '@dots-session-number'), '')
        self.inner('kill-session', '-t', '$0')
        self.wait(lambda: self.w.option(ident, '@dots-session-number') == '')
        self.assertEqual(self.w.name(ident), 'personal')

    def test_startup_adoption_and_renamed_reattachment(self):
        name = 'termux-12476-213229610'
        ident = self.inner('new-session', '-d', '-P', '-F', '#{session_id}', '-s', name, '-c', str(self.alpha))
        self.inner('set-option', '-t', ident + ':', '@dots-termux-default', '1')
        legacy = self.inner('new-session', '-d', '-P', '-F', '#{session_id}', '-s', 'termux-10-20', '-c', str(self.beta))
        self.w.reconcile(adopt=True)
        self.assertEqual(self.w.name(ident), 'alpha-12476-213229610')
        self.assertIsNone(self.w.metadata(legacy))
        launcher = runpy.run_path(str(REPO / 'profiles/termux/bin/termux-bar'))
        with patch.dict(os.environ, TMUX=self.base[-1] + ',0,0'):
            self.assertEqual(launcher['ensure_session'](TMUX, name), ident)
        self.inner('rename-session', '-t', ident, 'manual-startup')
        self.w.reconcile()
        with patch.dict(os.environ, TMUX=self.base[-1] + ',0,0'):
            self.assertEqual(launcher['ensure_session'](TMUX, name), ident)
        self.assertEqual(len(self.w.sessions()), 3)

    def test_shell_notifications_preserve_status_and_compose_hooks(self):
        for shell in ('bash', 'zsh'):
            executable = shutil.which(shell)
            if not executable:
                continue
            flags = ['--noprofile', '--norc'] if shell == 'bash' else ['-df']
            self.inner('set-option', '-g', 'default-command', shlex.join([executable, *flags]))
            ident = self.w.create(str(self.fx.home)); pane = self.pane(ident)
            code = 'source ' + shlex.quote(str(REPO / 'shells/shared/tmux-workspaces.sh'))
            # Run inside the real pane shell: its cwd is the observed directory.
            self.inner('send-keys', '-t', pane, '-l', code)
            self.inner('send-keys', '-t', pane, 'Enter')
            self.cd(pane, self.alpha, reconcile=False)
            # The fixture DOTS root owns a copy of the controller.
            self.wait(lambda: self.w.name(ident).startswith('alpha-'))
            self.assertTrue(self.w.metadata(ident)['auto'])
            env = dict(self.fx.env, TMUX=self.base[-1] + ',0,0', TMUX_PANE=pane, DOTS=str(REPO))
            args = [executable, *(['--noprofile', '--norc'] if shell == 'bash' else ['-df']), '-i', '-c']
            check = code + '; ' + code + '; false; _dots_workspace_prompt; printf "RESULT=%s\\n" "$?"'
            result = subprocess.run([*args, check], env=env, capture_output=True, text=True, timeout=5)
            self.assertIn('RESULT=1', result.stdout)


if __name__ == '__main__':
    unittest.main()

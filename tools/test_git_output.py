#!/usr/bin/env python3
"""Human Git projections over disposable repositories; both operation controllers."""
import json
import os
from pathlib import Path
import re
import shutil
import sys
import unittest

import test_git_operations as fixtures
import test_progress

PROJECT = fixtures.PROJECT


class Views(unittest.TestCase):
    setUp = fixtures.GitOperations.setUp
    run_cmd = fixtures.GitOperations.run_cmd
    git = fixtures.GitOperations.git
    repo = fixtures.GitOperations.repo
    remote_repo = fixtures.GitOperations.remote_repo
    advance = fixtures.GitOperations.advance
    owned_remote = fixtures.GitOperations.owned_remote
    sub = fixtures.GitOperations.sub
    terminal = test_progress.ProgressTests.terminal

    def command(self, native, repo, action, *args):
        prefix = [sys.executable, '-B', str(PROJECT/'lib/dots/git/cli.py')] if native else [shutil.which('bash'), str(PROJECT/'bin/dots'), 'git']
        return [*prefix, action, '-C', str(repo), '--no-wiki', *args]

    def test_status_modes_combined_states_rename_and_exact_json(self):
        repo = self.repo('status ü')
        self.git(repo, 'mv', '--', 'file', '-renamed ü')
        (repo/'-renamed ü').write_text('initial\nworktree\n')
        (repo/'new\x1b[31m file').write_text('untracked')
        for native in (False, True):
            command = self.command(native, repo, 'status')
            data = self.run_cmd([*command, '--json']).stdout
            for mode in ('default','short','verbose'):
                self.assertEqual(self.run_cmd([*command, '--view', mode, '--json']).stdout, data)
                result = self.run_cmd([*command, '--view', mode]).stdout
                self.assertIn('→ -renamed ü', result)
                self.assertEqual(result.count('→ -renamed ü'), 1)
                self.assertNotIn('\x1b', result)
                self.assertIn('RM' if mode == 'short' else 'staged renamed + unstaged modified', result)
                self.assertEqual('HEAD' in result, mode == 'verbose')
            self.assertNotEqual(self.run_cmd(command).stdout, self.run_cmd([*command, '-s']).stdout)
            self.assertEqual(self.run_cmd([*command, '--short', '--verbose'], ok=False).returncode, 2)
            self.assertEqual(self.run_cmd([*command, '--view', 'bad'], ok=False).returncode, 2)

    def test_default_groups_nonadjacent_states_with_nested_indentation(self):
        repo = self.repo('grouped')
        for name in ('a.txt', 'b.txt', 'c.txt', 'd.txt'):
            (repo/name).write_text('initial\n')
        self.git(repo, 'add', '.')
        self.git(repo, 'commit', '-m', 'grouped fixture')
        for name in ('a.txt', 'b.txt', 'c.txt', 'd.txt'):
            (repo/name).write_text('changed\n')
        self.git(repo, 'add', 'b.txt', 'd.txt')
        (repo/'d.txt').write_text('partially staged\n')
        (repo/'-literal ü [x].txt').write_text('untracked\n')
        expected = ('    unstaged modified (2)\n      a.txt\n      c.txt\n'
                    '    staged modified (1)\n      b.txt\n'
                    '    staged modified + unstaged modified (1)\n      d.txt\n'
                    '    untracked (1)\n      -literal ü [x].txt\n')
        index = (repo/'.git/index').read_bytes()
        for native in (False, True):
            command = self.command(native, repo, 'status')
            data = self.run_cmd([*command, '--json']).stdout
            for capture in (False, True):
                env = dict(self.env, DOTS_PROGRESS='none', DOTS_MENU_CAPTURE='1' if capture else '0')
                output = self.run_cmd([*command, '--view', 'default'], env=env).stdout
                self.assertIn(expected, output)
                self.assertEqual(output.splitlines().count('    unstaged modified (2)'), 1)
                self.assertEqual(self.run_cmd([*command, '--view', 'default', '--json'], env=env).stdout, data)
            short = self.run_cmd([*command, '--short'], env=dict(self.env, COLUMNS='160')).stdout
            self.assertIn('States  [ M] (2) / [M ] (1) / [MM] (1) / [??] (1)', short)
            verbose = self.run_cmd([*command, '--verbose'], env=dict(self.env, COLUMNS='160')).stdout
            self.assertIn('    [ M] unstaged modified (2)\n      a.txt\n      c.txt', verbose)
            self.assertIn('    [MM] staged modified + unstaged modified (1)', verbose)
            self.assertIn('    [??] untracked (1)', verbose)
            self.assertIn('HEAD', verbose)
        # Automatic terminal default still groups with icons and wraps safely.
        ansi = re.compile(rb'\x1b\[[0-?]*[ -/]*[@-~]')
        for native in (False, True):
            for width in (40, 80, 120):
                code, data = self.terminal(self.command(native, repo, 'status'),
                    dict(self.env, DOTS_PROGRESS='none', DOTS_COLOR='always', DOTS_ICONS='always', TERM='xterm-256color'), width)
                self.assertEqual(code, 0, data)
                lines = ansi.sub(b'', data).decode().splitlines()
                self.assertEqual(lines.count('     unstaged modified (2)'), 1)
                for name in ('a.txt', 'c.txt'):
                    line = next(line for line in lines if line.endswith(name))
                    self.assertTrue(line.startswith('      ') and not line.startswith('       '), line)
                self.assertTrue(all(len(line) <= width for line in lines), lines)
        self.assertEqual((repo/'.git/index').read_bytes(), index)

    def test_grouped_status_keeps_repositories_separate(self):
        repo = self.repo('group-root'); source = self.repo('group-source')
        child = self.sub(repo, source, 'modules/child')
        (repo/'file').write_text('parent changed\n')
        (child/'file').write_text('child changed\n')
        for native in (False, True):
            output = self.run_cmd(self.command(native, repo, 'status', '--view', 'default')).stdout
            self.assertIn('    unstaged modified (2)', output)
            self.assertIn('    unstaged modified (1)', output)
            self.assertEqual(output.splitlines().count('      file'), 2, output)

    def test_sync_reports_only_actual_changed_paths(self):
        for native in (False, True):
            source, bare, repo = self.remote_repo('sync'+str(native))
            self.git(source, 'mv', 'file', 'renamed')
            self.git(source, 'commit', '-m', 'rename')
            self.git(source, 'push', str(bare), 'main')
            command = self.command(native, repo, 'sync')
            preview = self.run_cmd([*command, '--view', 'default', '--dry-run']).stdout
            self.assertNotIn('→ renamed', preview)
            result = self.run_cmd([*command, '--view', 'default']).stdout
            self.assertEqual(result.count('file → renamed'), 1, result)
            self.assertNotIn('staged', result)
            result = self.run_cmd([*command, '--view', 'short']).stdout
            self.assertNotIn('renamed', result)

    def test_publish_reviews_each_file_once_and_preserves_blockers(self):
        for native in (False, True):
            _, bare, repo = self.remote_repo('publish'+str(native))
            self.owned_remote(repo, bare)
            self.git(repo, 'mv', 'file', 'selected ü')
            command = self.command(native, repo, 'publish', '--config', str(self.config))
            result = self.run_cmd([*command, '--view', 'default', '--yes']).stdout
            self.assertEqual(result.count('file → selected ü'), 1, result)
            self.assertIn('published', result)
            self.assertNotIn('selected changes and ahead commits pushed', result)
            (repo/'selected ü').write_text('blocked\n')
            self.git(repo, 'add', '.')
            self.git(repo, 'config', 'remote.origin.push', 'HEAD:refs/heads/main')
            for mode in ('default','short','verbose'):
                result = self.run_cmd([*command, '--view', mode, '--yes'], ok=False)
                self.assertEqual(result.returncode, 1)
                self.assertIn('blocked', result.stderr)
                self.assertIn('push', result.stderr)
                self.assertIn('resolve blockers and rerun', (result.stdout+result.stderr).lower())

    def test_publish_counts_only_selected_paths_without_changing_events_or_index(self):
        _, bare, repo = self.remote_repo('selection-counts')
        self.owned_remote(repo, bare)
        for name in ('a.txt', 'b.txt', 'c.txt'):
            (repo/name).write_text('initial\n')
        self.git(repo, 'add', '.'); self.git(repo, 'commit', '-m', 'fixture')
        self.git(repo, 'push', str(bare), 'main')
        for name in ('a.txt', 'b.txt', 'c.txt'):
            (repo/name).write_text('selected\n')
        self.git(repo, 'add', 'a.txt', 'c.txt')
        self.git(repo, 'mv', '--', 'file', '-renamed ü')
        (repo/'-renamed ü').write_text('initial\nunstaged\n')
        (repo/'new.txt').write_text('untracked\n')
        index = (repo/'.git/index').read_bytes()
        head = self.git(repo, 'rev-parse', 'HEAD')
        remote = self.git(bare, 'rev-parse', 'main')
        for native in (False, True):
            command = self.command(native, repo, 'publish', '--config', str(self.config), '--dry-run', '-m', 'Counted preview')
            for all_files in (False, True):
                args = [*command, *(['--all'] if all_files else [])]
                baseline = self.run_cmd([*args, '--json']).stdout
                selected = [row for row in json.loads(baseline)['events'] if row['status'] == 'selected']
                self.assertEqual(len(selected), 5 if all_files else 3)
                for mode in ('default', 'short', 'verbose'):
                    env = dict(self.env, COLUMNS='240', DOTS_PROGRESS='none')
                    output = self.run_cmd([*args, '--view', mode], env=env).stdout
                    self.assertIn('[M ] (2)' if mode == 'short' else 'staged modified (2)', output)
                    self.assertIn('[RM] (1)' if mode == 'short' else 'staged renamed + unstaged modified (1)', output)
                    self.assertEqual('b.txt' in output, all_files)
                    self.assertEqual('new.txt' in output, all_files)
                    self.assertEqual(output.count('file → -renamed ü'), 1)
                    if all_files:
                        self.assertIn('[ M] (1)' if mode == 'short' else 'unstaged modified (1)', output)
                        self.assertIn('[??] (1)' if mode == 'short' else 'untracked (1)', output)
                    decorated = dict(env, DOTS_COLOR='always', DOTS_ICONS='always')
                    self.assertEqual(self.run_cmd([*args, '--view', mode, '--json'], env=decorated).stdout, baseline)
        self.assertEqual((repo/'.git/index').read_bytes(), index)
        self.assertEqual(self.git(repo, 'rev-parse', 'HEAD'), head)
        self.assertEqual(self.git(bare, 'rev-parse', 'main'), remote)

    def test_sync_groups_actual_change_types_in_every_view(self):
        source, bare, first = self.remote_repo('change-counts')
        for name in ('a.txt', 'b.txt'):
            (source/name).write_text('before\n')
        self.git(source, 'add', '.'); self.git(source, 'commit', '-m', 'files')
        self.git(source, 'push', str(bare), 'main')
        before = self.git(source, 'rev-parse', 'HEAD')
        for name in ('a.txt', 'b.txt'):
            (source/name).write_text('after\n')
        self.git(source, 'mv', 'file', 'renamed')
        self.git(source, 'commit', '-am', 'change and rename')
        self.git(source, 'push', str(bare), 'main')
        for native in (False, True):
            for mode in ('default', 'short', 'verbose'):
                repo = self.base / ('sync-' + str(native) + '-' + mode)
                self.run_cmd(['git', 'clone', str(bare), str(repo)])
                self.git(repo, 'reset', '--hard', before)  # Disposable clone only.
                command = self.command(native, repo, 'sync', '--view', mode)
                output = self.run_cmd(command, env=dict(self.env, COLUMNS='160')).stdout
                self.assertIn('[M ] (2)' if mode == 'short' else 'modified (2)', output)
                self.assertIn('[R ] (1)' if mode == 'short' else 'renamed (1)', output)
                self.assertNotIn('staged', output)
                self.assertEqual(output.count('file → renamed'), 1)
                self.assertNotIn('States', self.run_cmd(command).stdout)

    def test_sync_file_report_failure_keeps_completed_update(self):
        shim=self.base/'report-shim';shim.mkdir()
        real_git=shutil.which('git')
        (shim/'git').write_text('#!'+shutil.which('bash')+'\nfor arg in "$@"; do [[ $arg != --name-status ]] || exit 1; done\nexec '+__import__('shlex').quote(real_git)+' "$@"\n')
        (shim/'git').chmod(0o700)
        for native in (False,True):
            source,bare,repo=self.remote_repo('report-failure'+str(native))
            after=self.advance(source,bare)
            env=dict(self.env,PATH=str(shim)+os.pathsep+self.env['PATH'])
            result=self.run_cmd(self.command(native,repo,'sync','--view','default'),env=env)
            self.assertIn('Change list unavailable',result.stdout)
            self.assertEqual(self.git(repo,'rev-parse','HEAD'),after)

    def test_inspection_named_routes_and_details_conflict(self):
        repo = self.repo('root'); child = self.repo('source')
        checkout = self.sub(repo, child, 'modules/child')
        (repo/'file').write_text('changed\n')
        (checkout/'file').write_text('changed\n')
        for route in (['info'], ['submodules'], ['submodules','info'], ['submodules','status'], ['submodule','child','status'], ['submodule','child','info']):
            command = [shutil.which('bash'), str(PROJECT/'bin/dots'), 'git', *route, '-C', str(repo)]
            baseline = self.run_cmd([*command, '--json']).stdout
            for mode in ('default','short','verbose'):
                output = self.run_cmd([*command, '--view', mode]).stdout
                count = 2 if route == ['info'] else 1  # Root also reports the dirty child gitlink.
                self.assertIn(('[ M]' if mode == 'short' else 'unstaged modified') + f' ({count})', output)
                self.assertEqual(self.run_cmd([*command, '--view', mode, '--json']).stdout, baseline)
        conflict = [shutil.which('bash'), str(PROJECT/'bin/dots'), 'git','submodules','-C',str(repo),'--details','--short']
        self.assertNotEqual(self.run_cmd(conflict, ok=False).returncode, 0)

    def test_owned_terminals_wrap_and_clear_progress(self):
        repo = self.repo('terminal')
        (repo/('long ü ' + 'x'*110)).write_text('new')
        env = dict(self.env, DOTS_PROGRESS='none', DOTS_COLOR='always', DOTS_ICONS='never', TERM='xterm-256color')
        ansi = re.compile(rb'\x1b\[[0-?]*[ -/]*[@-~]')
        theme=Path(env['XDG_STATE_HOME'])/'dots/current/theme';theme.mkdir(parents=True)
        for palette in ('dark','light'):
            sgr='38;2;170;200;240' if palette=='dark' else '38;2;20;50;90'
            (theme/'git-styles.tsv').write_text('dots-git-styles\t1\nbranch\t'+sgr+'\n')
            for native in (False, True):
                for width in (40,80,120):
                    for mode in ('default','short','verbose'):
                        code, data = self.terminal(self.command(native, repo, 'status', '--view', mode), env, width)
                        self.assertEqual(code, 0, data)
                        self.assertIn(sgr.encode(),data)
                        plain = ansi.sub(b'', data).decode()
                        self.assertNotIn('\r\r', plain)
                        self.assertTrue(all(len(line) <= width for line in plain.splitlines()), plain)

    def test_directory_color_is_separate_from_basename_for_both_controllers(self):
        repo = self.repo('paths')
        (repo/'old dir').mkdir(); (repo/'bin').mkdir()
        self.git(repo, 'mv', 'file', 'old dir/before.txt')
        (repo/'old dir/gone.py').write_text('gone\n')
        self.git(repo, 'add', '.'); self.git(repo, 'commit', '-m', 'nested paths')
        self.git(repo, 'mv', 'old dir/before.txt', 'bin/after.py')
        self.git(repo, 'rm', 'old dir/gone.py')
        (repo/'bin/-literal → name\\part.py').write_text('new\n')
        (repo/'bin/control\x1b[31m.py').write_text('new\n')
        theme = Path(self.env['XDG_STATE_HOME'])/'dots/current/theme'; theme.mkdir(parents=True)
        theme.joinpath('file-styles.tsv').write_text(
            'dots-file-styles\t1\ntype\tdir\t38;2;11;22;33\t-\n'
            'suffix\t.txt\t38;2;44;55;66\tfold\nsuffix\t.py\t38;2;77;88;99\tfold\n')
        directory, before, after = ('\x1b['+code+'m' for code in
                                   ('38;2;11;22;33','38;2;44;55;66','38;2;77;88;99'))
        env = dict(self.env, DOTS_COLOR='always', DOTS_ICONS='never', DOTS_PROGRESS='none',
                   DOTS_MENU_CAPTURE='1', COLUMNS='160', TERM='xterm-256color')
        for native in (False, True):
            command = self.command(native, repo, 'status')
            baseline = self.run_cmd([*command, '--json']).stdout
            for mode in ('default','short','verbose'):
                output = self.run_cmd([*command,'--view',mode], env=env).stdout
                self.assertNotIn('\x1b[31m.py', output)
                for color, text in ((directory,'old dir/'), (directory,'bin/'),
                                    (before,'before.txt'), (after,'after.py'), (after,'gone.py'),
                                    (after,'-literal → name\\part.py')):
                    self.assertIn(color+text, output, (native, mode, output))
                self.assertEqual(self.run_cmd([*command,'--view',mode,'--json'], env=env).stdout, baseline)
                plain = self.run_cmd([*command,'--view',mode], env=dict(env, DOTS_COLOR='never')).stdout
                self.assertNotIn('\x1b', plain)
                self.assertIn('old dir/before.txt → bin/after.py', plain)
            full = self.run_cmd([*command,'--short','--full-paths'],env=dict(env,COLUMNS='1000')).stdout
            self.assertIn(directory+str(repo)+'/bin/', full)

    def test_directory_spans_preserve_wrapped_paths_and_icon_style(self):
        repo = self.repo('wrapped')
        (repo/'bin').mkdir()
        name = 'long ü ' + 'x'*65 + '.py'
        (repo/'bin'/name).write_text('new\n')
        theme = Path(self.env['XDG_STATE_HOME'])/'dots/current/theme'; theme.mkdir(parents=True)
        theme.joinpath('file-styles.tsv').write_text(
            'dots-file-styles\t1\ntype\tdir\t38;2;11;22;33\t-\n'
            'suffix\t.py\t38;2;77;88;99\tfold\n')
        env = dict(self.env,DOTS_COLOR='always',DOTS_ICONS='always',DOTS_PROGRESS='none',TERM='xterm-256color')
        ansi = re.compile(rb'\x1b\[[0-?]*[ -/]*[@-~]')
        for native in (False,True):
            for width in (40,80,120):
                code,data = self.terminal(self.command(native,repo,'status','--short'),env,width)
                self.assertEqual(code,0,data)
                self.assertIn(b'\x1b[38;2;11;22;33mbin/',data)
                self.assertIn(b'\x1b[38;2;77;88;99mlong',data)
                self.assertRegex(data.decode(),r'\x1b\[38;2;77;88;99m[^\x1b]+ \x1b\[0m\x1b\[38;2;11;22;33mbin/')
                plain=ansi.sub(b'',data).decode()
                self.assertTrue(all(len(line)<=width for line in plain.splitlines()),plain)
                self.assertIn('bin/'+name,''.join(line.strip() for line in plain.splitlines()))

    def test_view_completion_records_for_all_shells(self):
        repo=self.repo('completion')
        for shell in ('bash','zsh','fish','powershell','nu','xonsh'):
            words=['git','status','--view','']
            command=([sys.executable,'-B',str(PROJECT/'lib/dots/cli.py'),'__complete',*words]
                     if shell=='powershell' else [shutil.which('bash'),str(PROJECT/'bin/dots'),'__complete',shell,str(len(words)),'--','dots',*words])
            result=self.run_cmd(command)
            for mode in ('default','short','verbose'):self.assertIn('candidate\t'+mode+'\t',result.stdout)


if __name__ == '__main__': unittest.main()

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
        self.sub(repo, child, 'modules/child')
        for route in (['info'], ['submodules'], ['submodules','info'], ['submodules','status'], ['submodule','child','status'], ['submodule','child','info']):
            command = [shutil.which('bash'), str(PROJECT/'bin/dots'), 'git', *route, '-C', str(repo)]
            baseline = self.run_cmd([*command, '--json']).stdout
            for mode in ('default','short','verbose'):
                self.run_cmd([*command, '--view', mode])
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

    def test_view_completion_records_for_all_shells(self):
        repo=self.repo('completion')
        for shell in ('bash','zsh','fish','powershell','nu','xonsh'):
            words=['git','status','--view','']
            command=([sys.executable,'-B',str(PROJECT/'lib/dots/cli.py'),'__complete',*words]
                     if shell=='powershell' else [shutil.which('bash'),str(PROJECT/'bin/dots'),'__complete',shell,str(len(words)),'--','dots',*words])
            result=self.run_cmd(command)
            for mode in ('default','short','verbose'):self.assertIn('candidate\t'+mode+'\t',result.stdout)


if __name__ == '__main__': unittest.main()

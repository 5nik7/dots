#!/usr/bin/env python3
"""Git inspection and selected publication, using disposable local repositories."""
import json
import os
from pathlib import Path
import shutil
import re
import select
import signal
import time
import subprocess
import sys
import unittest
import test_git_operations as operations

PROJECT = Path(__file__).resolve().parents[1]


class Cases:
    def setUp(self):
        operations.GitOperations.setUp(self)
        for key in list(self.env):
            if key.startswith(('DOTS_', '_DOTS_')) or key in ('DOTHEMES', 'THEMES'):
                self.env.pop(key)
        self.env.update(DOTS=str(PROJECT), DOTS_COLOR='never', DOTS_ICONS='never', DOTS_PROGRESS='never',
                        USERPROFILE=str(self.home), APPDATA=str(self.home / 'Roaming'),
                        LOCALAPPDATA=str(self.home / 'Local'), XDG_RUNTIME_DIR=str(self.home / 'runtime'))

    run_cmd = operations.GitOperations.run_cmd
    git = operations.GitOperations.git
    repo = operations.GitOperations.repo
    remote_repo = operations.GitOperations.remote_repo
    sub = operations.GitOperations.sub
    owned_remote = operations.GitOperations.owned_remote
    publish_tree = operations.GitOperations.publish_tree
    cli = operations.GitOperations.cli

    def prefix(self):
        return [sys.executable, '-B', str(PROJECT / 'lib/dots/cli.py')] if self.native else ['bash', str(PROJECT / 'bin/dots')]

    def call(self, repo, *args, ok=True, env=None):
        args = list(args)
        if args[:2] == ['submodules', 'publish']:
            # Put flags before a possible literal -- operand separator.
            args[2:2] = ['--config', str(self.config)]
        return self.run_cmd(
            [*self.prefix(), 'git', *args, *([] if '--' in args else ['-C', str(repo)])],
            ok=ok, env=env or dict(self.env, DOTS=str(PROJECT)))

    def data(self, repo, *args, ok=True):
        result = self.call(repo, *args, '--json', ok=ok)
        return json.loads(result.stdout)

    def index(self, repo):
        path = Path(self.git(repo, 'rev-parse', '--git-path', 'index'))
        return (path if path.is_absolute() else repo / path).read_bytes()

    def nested(self):
        leaf = self.repo('leaf-source')
        mid = self.repo('middle-source')
        self.sub(mid, leaf, 'leaf')
        top = self.repo('top')
        child = self.sub(top, mid, 'modules/child')
        self.git(child, 'submodule', 'update', '--init')
        return top, child, child / 'leaf'

    def test_info_remote_identity_redaction_and_unborn(self):
        repo = self.repo('identity')
        self.git(repo, 'remote', 'add', 'origin', 'https://user:password@github.com/mine/project.git?secret=value#token')
        conf = self.home / '.config/dots/git.conf'
        conf.parent.mkdir(parents=True)
        conf.write_text('[dots-git]\nowner = github.com/mine\nhostAlias = work=github.com\n')
        data = self.data(repo, 'info')
        remote = data['repositories'][0]['remote']
        self.assertEqual(remote['url'], 'https://github.com/mine/project.git')
        self.assertEqual(remote['owner'], 'mine')
        self.assertTrue(remote['owned'])
        output = self.call(repo, 'info', env=dict(self.env, DOTS=str(PROJECT), DOTS_COLOR='always', DOTS_ICONS='always')).stdout
        self.assertIn('󰊤', output)
        for secret in ('password', 'secret=value', '#token'):
            self.assertNotIn(secret, output + json.dumps(data))
        self.git(repo, 'remote', 'set-url', 'origin', 'git@work:mine/project.git')
        self.assertTrue(self.data(repo, 'info')['repositories'][0]['remote']['owned'])
        conf.write_text('[invalid')
        self.assertEqual(self.data(repo, 'info')['repositories'][0]['remote']['ownership'], 'unavailable')
        local_url = '/long remote folder with spaces/another café folder/project.git'
        self.git(repo, 'remote', 'set-url', 'origin', local_url)
        lines = self.call(repo, 'info', env=dict(self.env, COLUMNS='40')).stdout.splitlines()
        start = next(i for i, line in enumerate(lines) if line.startswith('    URL'))
        end = next(i for i, line in enumerate(lines) if line.startswith('    Owner'))
        self.assertEqual(''.join(line[15:] for line in lines[start:end]), local_url)
        unborn = self.base / 'unborn'; unborn.mkdir()
        self.git(unborn, 'init', '-b', 'main')
        row = self.data(unborn, 'info')['repositories'][0]
        self.assertIsNone(row['head'])
        self.assertIsNone(row['remote']['url'])
        self.assertEqual(row['branch'], 'main')

    def test_connected_tree_and_folder_paths(self):
        top, mid, leaf = self.nested()
        self.sub(top, self.repo('last-source'), 'z-last café with a long submodule directory name')
        rich = dict(self.env, DOTS_COLOR='never', DOTS_ICONS='always', COLUMNS='120')
        output = self.call(top, 'submodules', env=rich).stdout
        lines = output.splitlines()
        self.assertTrue(lines[1].startswith('│   Repository '), output)
        self.assertEqual(lines[2], '│')
        self.assertIn('\n├──  modules/child ', output)
        self.assertIn('\n│   │\n│   └──  modules/child/leaf ', output)
        self.assertIn('\n│\n└──  z-last ', output)
        detailed = self.call(top, 'submodules', '--details', env=rich).stdout
        section = detailed[detailed.index('├── '):detailed.index('└──  z-last')].splitlines()
        self.assertTrue(all(line.startswith('│') for line in section[1:]), detailed)
        narrow = self.call(top, 'submodules', '--details', '--full-paths', env=dict(rich, COLUMNS='40')).stdout
        self.assertTrue(all(len(line) <= 40 for line in narrow.splitlines()), narrow)
        ascii_view = self.call(top, 'submodules', env=dict(rich, DOTS_ICONS='never', DOTS_COLOR='always')).stdout
        ascii_view = re.sub(r'\x1b\[[0-9;]*m', '', ascii_view)
        self.assertIn('\n|   Repository ', ascii_view)
        self.assertIn('\n|   |\n|   `-- ', ascii_view)
        redirected = self.call(top, 'submodules').stdout
        self.assertTrue(redirected.splitlines()[1].startswith('    Repository '))
        self.assertEqual(redirected.splitlines()[2], '')
        self.assertNotIn('│', redirected)
        self.assertEqual(self.call(top, 'submodules', '--json').stdout,
                         self.call(top, 'submodules', '--json', env=rich).stdout)
        short = self.call(top, 'submodules', '--depth', '1', env=rich).stdout
        self.assertNotIn('│   │', short)
        empty = self.call(self.repo('empty-tree'), 'submodules', env=rich).stdout
        self.assertNotIn('│', empty)
        theme = Path(self.env.get('XDG_STATE_HOME', self.home / '.local/state')) / 'dots/current/theme'
        theme.mkdir(parents=True, exist_ok=True)
        theme.joinpath('file-styles.tsv').write_text('dots-file-styles\t1\ntype\tdir\t38;2;17;34;51\t-\n')
        icon = next(line.split('\t')[4] for line in (PROJECT / 'lib/dots/resources.tsv').read_text().splitlines()
                    if line.startswith('kind\tdir\t'))
        for route in (('info',), ('submodules', 'info'), ('submodule', 'child', 'info')):
            text = self.call(top, *route, env=dict(rich, DOTS_COLOR='always')).stdout
            paths = [line for line in text.splitlines() if 'Path ' in line]
            self.assertTrue(paths)
            for line in paths:
                self.assertIn('\x1b[38;2;17;34;51m' + icon + ' ', line)
                self.assertNotIn('', line)
        self.git(mid, 'submodule', 'deinit', '-f', '--', 'leaf')
        missing = self.call(top, 'submodules', '--details', env=rich, ok=False).stdout
        self.assertIn('│           Reason', missing)
        self.assertIn('not initialized', missing)

    def test_tree_depth_status_filter_and_missing(self):
        top, mid, leaf = self.nested()
        before = self.index(top)
        data = self.data(top, 'submodules')
        self.assertEqual([r['relative_path'] for r in data['repositories']], ['modules/child', 'modules/child/leaf'])
        self.assertEqual([r['depth'] for r in data['repositories']], [1, 2])
        short = self.data(top, 'submodules', '--depth', '1')
        self.assertEqual(len(short['repositories']), 1)
        self.assertTrue(short['complete'])
        self.assertTrue(short['depth_limited'])
        self.assertEqual(self.data(top, 'submodules', 'status', '--dirty')['repositories'], [])
        (leaf / 'file').write_text('dirty\n')
        rows = self.data(top, 'submodules', 'status', 'modules/child', '--dirty')['repositories']
        self.assertEqual({r['path'] for r in rows}, {str(mid), str(leaf)})
        self.assertEqual(self.index(top), before)
        self.git(mid, 'submodule', 'deinit', '-f', '--', 'leaf')
        missing = self.data(top, 'submodules', 'status', '--dirty', ok=False)
        self.assertFalse(missing['complete'])
        self.assertIn('missing', [r['status'] for r in missing['repositories']])
        self.assertEqual(self.data(top, 'submodules', '--depth', '1')['submodules']['total'], 1)

    def test_pointer_change_and_clean_ahead_filter(self):
        top, mid, leaf = self.nested()
        self.git(leaf, 'checkout', 'main')
        (leaf / 'file').write_text('new commit\n')
        self.git(leaf, 'commit', '-am', 'advance')
        rows = self.data(top, 'submodules', 'status', '--dirty')['repositories']
        self.assertTrue(next(r for r in rows if r['path'] == str(leaf))['pointer_changed'])
        self.git(mid, 'add', 'leaf')
        self.git(mid, 'commit', '-m', 'record pointer')
        self.git(top, 'add', 'modules/child')
        self.git(top, 'commit', '-m', 'record pointer')
        self.assertEqual(self.data(top, 'submodules', 'status', '--dirty')['repositories'], [])

    def test_invalid_flags_paths_and_empty_collection(self):
        repo = self.repo('empty')
        self.assertTrue(self.data(repo, 'submodules')['complete'])
        for args in [('info', '--depth', '1'), ('submodules', '--depth', '0'), ('submodules', '--dirty'),
                     ('submodules', 'publish'), ('submodules', 'publish', '.', '--dry-run'),
                     ('submodules', 'publish', '../outside', '--dry-run'),
                     ('submodules', 'publish', 'ordinary', '--all-submodules', '--dry-run')]:
            result = self.call(repo, *args, ok=False)
            self.assertEqual(result.returncode, 2, (args, result.stdout, result.stderr))
        empty = self.data(repo, 'submodules', 'publish', '--all-submodules', '--dry-run')
        self.assertEqual(empty['selection'], [])
        self.assertEqual(empty['events'], [])

    def test_unsafe_and_literal_paths_and_machine_bytes(self):
        repo = self.repo('literal')
        source = self.repo('source')
        for name in ('one/shared', 'two/shared', 'space café'):
            self.sub(repo, source, name)
        # Git submodule add's internal git-add does not protect leading dashes.
        self.git(repo, 'clone', '--', str(source), str(repo / '-dash'))
        self.git(repo, 'config', '-f', '.gitmodules', 'submodule.dash.path', '-dash')
        self.git(repo, 'config', '-f', '.gitmodules', 'submodule.dash.url', str(source))
        self.git(repo, 'add', '--', '.gitmodules', '-dash')
        self.git(repo, 'commit', '-m', 'registered leading dash')
        named = self.call(repo, 'submodule', '-C', str(repo), '--json', '--', '-dash')
        self.assertEqual(json.loads(named.stdout)['base'], str(repo / '-dash'))
        plain = self.call(repo, 'submodules', '--details', '--json').stdout
        forced = self.call(repo, 'submodules', '--details', '--json', env=dict(self.env, DOTS=str(PROJECT), DOTS_COLOR='always', DOTS_ICONS='always')).stdout
        self.assertEqual(plain, forced)
        self.assertNotIn('\x1b', forced)
        result = self.call(repo, 'submodules', 'status', '-C', str(repo), '--json', '--', '-dash')
        self.assertEqual(json.loads(result.stdout)['repositories'][0]['relative_path'], '-dash')
        self.git(repo, 'config', '-f', '.gitmodules', '--unset', 'submodule.one/shared.path')
        blocked = self.data(repo, 'submodules', ok=False)
        self.assertEqual(blocked['repositories'][0]['availability'], 'available')  # -dash sorts first
        self.assertIn('blocked', [r['availability'] for r in blocked['repositories']])

    def test_completions_read_selected_repository(self):
        repo, _, _ = self.nested()
        words = ['git', 'submodules', 'publish', '-C', str(repo), 'modules/']
        args = ['__complete', *words] if self.native else ['__complete', 'bash', str(len(words)), '--', 'dots', *words]
        output = self.run_cmd([*self.prefix(), *args], env=dict(self.env, DOTS=str(PROJECT))).stdout
        self.assertIn('candidate\tmodules/child\t', output)
        self.assertIn('candidate\tmodules/child/leaf\t', output)
        help_text = self.run_cmd([*self.prefix(), 'help', 'git', 'submodules', 'publish'], env=dict(self.env, DOTS=str(PROJECT))).stdout
        self.assertIn('--all-submodules', help_text)

    @unittest.skipUnless(shutil.which('bash'), 'fixture SSH transport requires Bash')
    def test_selected_publish_preserves_outer_index_and_remote(self):
        top, mid, leaf, top_bare, mid_bare, leaf_bare = self.publish_tree()
        (leaf / 'change').write_text('selected\n'); self.git(leaf, 'add', 'change')
        (top / 'file').write_text('outer work\n'); self.git(top, 'add', 'file')
        before_index, before_head = self.index(top), self.git(top, 'rev-parse', 'HEAD')
        before_remote = self.git(top_bare, 'rev-parse', 'main')
        preview = self.data(top, 'submodules', 'publish', 'middle', '--dry-run')
        self.assertEqual(preview['command'], 'submodules publish')
        self.assertEqual(preview['selection'], [str(mid)])
        self.assertEqual(self.index(top), before_index)
        self.assertFalse(any(e['status'] == 'planned' and e['path'] == str(top) for e in preview['events']))
        data = self.data(top, 'submodules', 'publish', 'middle', '--yes', '-m', 'selected tree')
        self.assertEqual([e['path'] for e in data['events'] if e['status'] == 'published'], [str(leaf), str(mid)])
        self.assertTrue(any(e['path'] == str(top) and e['status'] == 'pending' for e in data['events']))
        self.assertEqual(self.index(top), before_index)
        self.assertEqual(self.git(top, 'rev-parse', 'HEAD'), before_head)
        self.assertEqual(self.git(top_bare, 'rev-parse', 'main'), before_remote)
        unchanged = {repo: self.git(repo, 'rev-parse', 'HEAD') for repo in (mid, leaf)}
        output = self.call(top, 'submodules', 'publish', 'middle', '--yes',
                           env=dict(self.env, DOTS_COLOR='always', DOTS_ICONS='never')).stdout
        self.assertIn('\x1b[93m[!] pending', output)
        self.assertEqual(self.index(top), before_index)
        for repo, bare in ((mid, mid_bare), (leaf, leaf_bare)):
            self.assertEqual(self.git(repo, 'rev-parse', 'HEAD'), unchanged[repo])
            self.assertEqual(self.git(repo, 'rev-parse', 'HEAD'), self.git(bare, 'rev-parse', 'main'))
            common = Path(self.git(repo, 'rev-parse', '--git-common-dir'))
            self.assertFalse((common if common.is_absolute() else repo / common).joinpath('git-it.lock').exists())

    @unittest.skipUnless(shutil.which('bash'), 'fixture SSH transport requires Bash')
    def test_all_submodules_continues_safe_sibling(self):
        top, mid, leaf, top_bare, _, _ = self.publish_tree()
        _, bare, _ = self.remote_repo('sibling')
        sibling = self.sub(top, bare, 'sibling')
        self.owned_remote(sibling, bare)
        self.git(leaf, 'checkout', '--detach')
        for repo in (leaf, sibling):
            (repo / 'file').write_text('unstaged\n')
        before = self.index(top)
        data = self.data(top, 'submodules', 'publish', '--all-submodules', '--all', '--yes', ok=False)
        self.assertFalse(data['complete'])
        self.assertIn(str(sibling), [e['path'] for e in data['events'] if e['status'] == 'published'])
        self.assertNotIn(str(mid), [e['path'] for e in data['events'] if e['status'] == 'published'])
        self.assertEqual(self.index(top), before)
        self.assertEqual(self.git(sibling, 'rev-parse', 'HEAD'), self.git(bare, 'rev-parse', 'main'))


    def test_named_navigation_and_collection_info(self):
        top, mid, leaf = self.nested()
        for route in [('submodule', 'child:leaf'), ('submodule', 'child', 'submodule', 'leaf', 'info')]:
            data = self.data(top, *route)
            self.assertEqual(data['base'], str(leaf))
            self.assertEqual(len(data['repositories']), 1)
        status = self.data(top, 'submodule', 'child', 'status')
        self.assertEqual([r['path'] for r in status['repositories']], [str(mid), str(leaf)])
        collection = self.data(top, 'submodules', 'info')
        self.assertEqual([r['selector'] for r in collection['repositories']], ['child', 'child:leaf'])
        self.assertEqual(collection['repositories'][0]['submodules']['total'], 1)
        depth = self.data(top, 'submodules', 'info', '--depth', '1')
        self.assertTrue(depth['repositories'][0]['depth_limited'])
        self.assertEqual(depth['repositories'][0]['submodules']['total'], 0)
        nested = self.data(top, 'submodule', 'child', 'submodules', 'info')
        self.assertEqual([r['selector'] for r in nested['repositories']], ['leaf'])
        direct = self.data(mid, 'submodule', 'leaf')
        self.assertEqual(direct['base'], str(leaf))
        result = self.call(top, 'submodule', 'leaf', 'info', ok=False)
        self.assertIn('no registered direct child', result.stderr)
        self.git(mid, 'submodule', 'deinit', '-f', '--', 'leaf')
        missing = self.data(top, 'submodule', 'child:leaf', ok=False)
        self.assertFalse(missing['complete'])
        self.assertEqual(missing['repositories'][0]['status'], 'missing')
        result = self.call(top, 'submodule', 'child:leaf:unknown', ok=False)
        self.assertIn('unavailable', result.stderr)

    def test_named_ambiguity_action_names_and_literal_values(self):
        top = self.repo('names')
        source = self.repo('source')
        for name in ('one/shared', 'two/shared', 'info', '_native', '_complete', 'space café'):
            self.sub(top, source, name)
        result = self.call(top, 'submodule', 'shared', 'info', ok=False)
        self.assertIn('ambiguous', result.stderr)
        for path in ('one/shared', 'two/shared'): self.assertIn(path, result.stderr)
        for name in ('info', '_native', '_complete', 'space café'):
            self.assertEqual(self.data(top, 'submodule', name)['base'], str(top / name))
        rows = self.data(top, 'submodules', 'info')['repositories']
        self.assertEqual([r['selector'] for r in rows if r['relative_path'].endswith('/shared')], [None, None])
        for args in [('shared', 'info', '--dirty'), ('info', 'publish', '--all-submodules'),
                     ('info', 'info', '--depth', '1'), ('../info',), ('info', 'unknown')]:
            self.assertEqual(self.call(top, 'submodule', *args, ok=False).returncode, 2)

    def test_named_contextual_help_and_completion(self):
        top, mid, leaf = self.nested()
        def completion(tail):
            words = ['git', 'submodule', '-C', str(top), *tail]
            args = ['__complete', *words] if self.native else ['__complete', 'bash', str(len(words)), '--', 'dots', *words]
            return self.run_cmd([*self.prefix(), *args], env=self.env).stdout
        self.assertIn('candidate\tchild\t', completion(['']))
        self.assertIn('candidate\tchild:leaf\t', completion(['child:']))
        self.assertIn('candidate\tleaf\t', completion(['child', 'submodule', '']))
        self.assertIn('candidate\tpublish\t', completion(['child', '']))
        self.assertIn('candidate\tinfo\t', completion(['child', 'submodules', '']))
        self.assertIn('candidate\t--all\t', completion(['child', 'publish', '--']))
        self.assertNotIn('candidate\t--all-submodules\t', completion(['child', 'publish', '--']))
        self.assertIn('candidate\t--all-submodules\t', completion(['child', 'submodules', 'publish', '--']))
        self.assertIn('directory\t', completion(['child', '-C', '']))
        child_help = self.run_cmd([*self.prefix(), 'help', 'git', 'submodule', 'child', 'submodule'], env=self.env).stdout
        self.assertIn('dots git submodule child submodule NAME', child_help)
        literal_help = self.run_cmd([*self.prefix(), 'help', 'git', 'submodule', '--', '-missing', 'publish'], env=self.env).stdout
        self.assertIn('--dry-run', literal_help)
        for prefix in (['help', 'git', 'submodule'], ['git', 'submodule']):
            output = self.run_cmd([*self.prefix(), *prefix, 'does-not-exist', 'publish', '--help', '-C', str(top / 'absent')], env=self.env).stdout
            self.assertIn('--dry-run', output)
            self.assertNotIn('--all-submodules', output)

    @unittest.skipUnless(shutil.which('bash'), 'fixture SSH transport requires Bash')
    def test_named_publish_preserves_parent(self):
        top, mid, leaf, top_bare, mid_bare, leaf_bare = self.publish_tree()
        (leaf / 'change').write_text('selected\n'); self.git(leaf, 'add', 'change')
        (top / 'file').write_text('outer staged\n'); self.git(top, 'add', 'file')
        before = self.index(top), self.git(top, 'rev-parse', 'HEAD'), self.git(top_bare, 'rev-parse', 'main')
        message = 'literal $(ignored) `ignored` "quoted"'
        result = self.data(top, 'submodule', 'middle', 'publish', '--config', str(self.config), '--yes', '-m', message)
        self.assertEqual([e['path'] for e in result['events'] if e['status'] == 'published'], [str(leaf), str(mid)])
        self.assertEqual(before, (self.index(top), self.git(top, 'rev-parse', 'HEAD'), self.git(top_bare, 'rev-parse', 'main')))
        self.assertEqual(self.git(leaf, 'log', '-1', '--format=%s'), message)

    def test_identity_icons_are_human_only_and_independent(self):
        repo = self.repo('identity-icons')
        self.git(repo, 'remote', 'add', 'origin', 'https://github.com/mine/project.git')
        forced = dict(self.env, DOTS_ICONS='always', DOTS_COLOR='always')
        for action in ('info', 'status'):
            output = self.call(repo, action, env=forced).stdout
            self.assertRegex(output, r'\x1b\[[0-9;]+m󰊤 identity-icons\x1b\[0m')
            self.assertRegex(output, r'\x1b\[[0-9;]+mmain\x1b\[0m')
        plain = self.call(repo, 'info', env=dict(forced, DOTS_COLOR='auto', NO_COLOR='1')).stdout
        self.assertIn('main', plain)
        self.assertNotIn('\x1b', plain)
        for route in [('info',), ('status',), ('submodules', 'info')]:
            self.assertEqual(self.call(repo, *route, '--json').stdout, self.call(repo, *route, '--json', env=forced).stdout)
        self.git(repo, 'checkout', '--detach')
        self.assertNotIn('detached', self.call(repo, 'info', env=forced).stdout)
        self.git(repo, 'remote', 'remove', 'origin')
        self.assertIn(' identity-icons', self.call(repo, 'info', env=forced).stdout)

    @unittest.skipUnless(os.name != 'nt' and shutil.which('bash'), 'POSIX PTY fixture')
    def test_confirmation_cancel_drift_and_interrupt(self):
        import pty
        top, mid, leaf, top_bare, _, _ = self.publish_tree()
        (leaf / 'selected-file').write_text('selected\n'); self.git(leaf, 'add', 'selected-file')
        before = {repo: (self.index(repo), self.git(repo, 'rev-parse', 'HEAD')) for repo in (top, mid, leaf)}
        modules = (top / '.gitmodules').read_bytes()
        for action in ('cancel', 'drift', 'interrupt'):
            master, slave = pty.openpty()
            proc = subprocess.Popen([*self.prefix(), 'git', 'submodules', 'publish', 'middle', '-C', str(top),
                                     '--config', str(self.config), '--json'], env=dict(self.env, DOTS=str(PROJECT), DOTS_ICONS='always'),
                                    stdin=slave, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                preview = b''; deadline = time.monotonic() + 30
                while b'[y/N]' not in preview and time.monotonic() < deadline:
                    if select.select([proc.stderr], [], [], .1)[0]:
                        chunk = os.read(proc.stderr.fileno(), 65536)
                        if not chunk: break
                        preview += chunk
                self.assertIn(b'[y/N]', preview)
                self.assertIn(b'selected-file', preview)
                self.assertIn('main'.encode(), preview)
                self.assertIn(''.encode(), preview)
                if action == 'drift':
                    self.git(top, 'config', '-f', '.gitmodules', 'submodule.middle.path', 'moved')
                    os.write(master, b'y\n')
                elif action == 'interrupt':
                    proc.send_signal(signal.SIGINT if self.native else signal.SIGTERM)
                else:
                    os.write(master, b'n\n')
                stdout, stderr = proc.communicate(timeout=30)
                self.assertEqual((preview + stderr).count(b'[y/N]'), 1)
                if action == 'interrupt':
                    self.assertIn(proc.returncode, (130, -signal.SIGINT) if self.native else (143, -signal.SIGTERM))
                else:
                    data = json.loads(stdout)
                    self.assertEqual(proc.returncode, 1 if action == 'drift' else 0, preview + stderr)
                    self.assertFalse(any(e['status'] == 'published' for e in data['events']))
                for repo, (index, head) in before.items():
                    self.assertEqual(self.index(repo), index)
                    self.assertEqual(self.git(repo, 'rev-parse', 'HEAD'), head)
                    common = Path(self.git(repo, 'rev-parse', '--git-common-dir'))
                    self.assertFalse((common if common.is_absolute() else repo / common).joinpath('git-it.lock').exists())
            finally:
                if proc.poll() is None: proc.kill()
                proc.communicate(timeout=10)
                os.close(master); os.close(slave)
                (top / '.gitmodules').write_bytes(modules)

    @unittest.skipUnless(os.name != 'nt', 'POSIX PTY fixture')
    def test_views_pty_widths_styles_and_plain(self):
        import fcntl
        import pty
        import struct
        import termios
        repo, mid, leaf = self.nested()
        self.git(mid, 'remote', 'set-url', 'origin', 'https://github.com/example/project.git')
        (leaf / 'new.py').write_text('new\n')
        theme = self.home / '.local/state/dots/current/theme'; theme.mkdir(parents=True)
        for background, code in (('dark', '38;2;180;210;240'), ('light', '38;2;20;40;80')):
            roles = 'repo repo_owned branch detached modified clean missing blocked conflict staged untracked'
            theme.joinpath('git-styles.tsv').write_text('dots-git-styles\t1\n' + ''.join(r + '\t' + code + '\n' for r in roles.split()))
            for width in (40, 80, 120):
                for route in (['info'], ['submodules', '--details'], ['submodules', 'status'], ['submodules', 'info'], ['submodule', 'child', 'info']):
                    master, slave = pty.openpty()
                    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 24, width, 0, 0))
                    env = dict(self.env, DOTS=str(PROJECT), DOTS_COLOR='auto', DOTS_ICONS='auto', TERM='xterm-256color', COLUMNS=str(width), NO_COLOR='')
                    proc = subprocess.Popen([*self.prefix(), 'git', *route, '-C', str(repo)], env=env, stdout=slave, stderr=subprocess.PIPE)
                    os.close(slave)
                    output = b''
                    try:
                        deadline = time.monotonic() + 25
                        while time.monotonic() < deadline:
                            if select.select([master], [], [], .1)[0]:
                                try: chunk = os.read(master, 65536)
                                except OSError: break
                                if not chunk: break
                                output += chunk
                            elif proc.poll() is not None: break
                        _, error = proc.communicate(timeout=10)
                        self.assertEqual(proc.returncode, 0, error)
                        self.assertIn(('\x1b[' + code + 'm').encode(), output)
                        if route[:1] == ['submodules'] and '--details' in route:
                            self.assertIn('󰊤'.encode(), output)
                        plain = re.sub(rb'\x1b\[[0-9;]*m', b'', output).decode()
                        self.assertNotIn('\x1b', plain)
                        self.assertTrue(all(len(line) <= width for line in plain.splitlines()), (width, plain))
                        if width == 40 and route[:1] == ['submodules'] and '--details' in route:
                            self.assertIn('        detached ', plain)
                    finally:
                        if proc.poll() is None: proc.kill()
                        proc.communicate(timeout=10); os.close(master)
        output = self.call(repo, 'submodules', env=dict(self.env, DOTS=str(PROJECT), DOTS_COLOR='auto', DOTS_ICONS='never', NO_COLOR='1')).stdout
        self.assertNotIn('\x1b', output)
        self.assertIn('`-- ', output)


@unittest.skipUnless(os.name != 'nt' and shutil.which('bash'), 'POSIX Bash unavailable')
class Bash(Cases, unittest.TestCase):
    native = False


class Native(Cases, unittest.TestCase):
    native = True


if __name__ == '__main__':
    unittest.main()

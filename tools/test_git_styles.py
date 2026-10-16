#!/usr/bin/env python3
"""Published Git roles and native CLI rendering, in disposable roots only."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import unittest
import test_git_operations as operations

if os.name != 'nt':
    import fcntl
    import pty
    import struct
    import termios

REPO = Path(__file__).resolve().parents[1]
SGR = re.compile(r'\x1b\[[0-9;]*m')
ROLES = 'repo branch untracked modified behind detached missing staged added clean ahead deleted blocked conflict renamed copied ignored'.split()


@unittest.skipUnless(shutil.which('bash') and shutil.which('git') and os.name != 'nt', 'Native Bash/Git required')
class GitStyles(unittest.TestCase):
    run_cmd = operations.GitOperations.run_cmd
    git = operations.GitOperations.git
    cli = operations.GitOperations.cli
    repo = operations.GitOperations.repo
    remote_repo = operations.GitOperations.remote_repo
    advance = operations.GitOperations.advance
    owned_remote = operations.GitOperations.owned_remote

    def setUp(self):
        operations.GitOperations.setUp(self)
        for kind in ('STATE', 'CONFIG', 'CACHE', 'DATA'):
            self.env['XDG_' + kind + '_HOME'] = str(self.home / kind.lower())
        self.env.update(DOTS=str(REPO), DOTS_LIB_DIR=str(REPO / 'lib/dots'),
                        DOTS_COLOR='always', DOTS_ICONS='never', DOTS_PROGRESS='never', TERM='xterm-256color')
        self.env.pop('NO_COLOR', None)
        self.theme = self.home / 'state/dots/current/theme'
        self.theme.mkdir(parents=True)
        self.table = self.theme / 'git-styles.tsv'
        self.codes = {role: f'0;38;2;17;34;{i + 1}' for i, role in enumerate(ROLES)}
        self.table.write_text('dots-git-styles\t1\n' + ''.join(f'{r}\t{c}\n' for r, c in self.codes.items()))

    def esc(self, role):
        return '\x1b[' + self.codes[role] + 'm'

    def shell(self, body, *args, env=None):
        return self.run_cmd(['bash', '--noprofile', '--norc', '-c',
                             'source "$DOTS_LIB_DIR/ui.bash"; ' + body, 'test', *args], env=env)

    def test_status_and_resource_colors_are_independent(self):
        repo = self.repo('repository')
        (repo / 'file').write_text('changed\n')
        (repo / 'new.png').write_text('new\n')
        self.theme.joinpath('file-styles.tsv').write_text('dots-file-styles\t1\ntype\tfile\t38;2;201;202;203\t-\n')
        result = self.cli(repo, 'status')
        for role, text in [('repo', 'repository'), ('branch', 'main'), ('modified', 'modified'), ('untracked', 'untracked')]:
            self.assertIn(self.esc(role) + text, result.stdout)
        self.assertIn('\x1b[38;2;201;202;203mnew.png', result.stdout)
        forced = self.cli(repo, 'status', '--json').stdout
        plain = self.cli(repo, 'status', '--json', env=dict(self.env, DOTS_COLOR='never')).stdout
        self.assertEqual(forced, plain)
        self.assertNotIn('\x1b', forced)
        self.git(repo, 'add', 'file')
        self.assertIn(self.esc('staged') + 'staged', self.cli(repo, 'status').stdout)
        (repo / 'file').write_text('changed again\n')
        self.assertIn(self.esc('modified') + 'staged + modified', self.cli(repo, 'status').stdout)
        self.git(repo, 'checkout', '--detach')
        self.assertIn(self.esc('detached') + 'detached ', self.cli(repo, 'status').stdout)

    def test_added_deleted_renamed_and_conflict_rendering(self):
        repo = self.repo('changes')
        (repo / 'gone').write_text('delete me\n')
        self.git(repo, 'add', 'gone')
        self.git(repo, 'commit', '-m', 'second tracked file')
        self.git(repo, 'mv', 'file', 'renamed')
        self.git(repo, 'rm', 'gone')
        (repo / 'added').write_text('added\n')
        self.git(repo, 'add', 'added')
        output = self.cli(repo, 'status').stdout
        self.assertIn(self.esc('renamed') + 'staged renamed', output)
        self.assertIn(self.esc('deleted') + 'staged deleted', output)
        self.assertIn(self.esc('added') + 'staged', output)
        conflict = self.repo('conflict')
        self.git(conflict, 'branch', 'side')
        (conflict / 'file').write_text('main change\n')
        self.git(conflict, 'commit', '-am', 'main change')
        self.git(conflict, 'checkout', 'side')
        (conflict / 'file').write_text('side change\n')
        self.git(conflict, 'commit', '-am', 'side change')
        self.git(conflict, 'merge', 'main', ok=False)
        result = self.cli(conflict, 'status', ok=False)
        # Existing discovery refuses any unmerged index before file enumeration.
        self.assertEqual(result.returncode, 1)
        self.assertIn(self.esc('blocked') + 'blocked', result.stdout)
        self.assertIn('conflicted submodule index', result.stdout)
        output = self.shell('source "$DOTS_LIB_DIR/git/common.bash"; source "$DOTS_LIB_DIR/git/ui.bash"; '
                            'status_header repository main conflict 80; file_status_style UU; '
                            'dots::resource_row conflict "$1" file "" "" "$REPLY"', str(conflict / 'file')).stdout
        self.assertGreaterEqual(output.count(self.esc('conflict') + 'conflict'), 2)

    def test_porcelain_priority_and_fallbacks(self):
        cases = {'UU':'conflict', 'AA':'conflict', 'DD':'conflict', '??':'untracked', '!!':'ignored',
                 'MD':'deleted', 'RM':'renamed', 'C ':'copied', 'AM':'added', 'MM':'modified',
                 ' M':'modified', 'M ':'staged'}
        for xy, role in cases.items():
            value = self.shell('source "$DOTS_LIB_DIR/git/ui.bash"; file_status_style "$1"; printf %s "$REPLY"', xy).stdout
            self.assertEqual(value, self.esc(role), xy)
        for data in ['bad header\n', 'dots-git-styles\t1\nrepo\t31\nbranch\t$(touch forbidden)\n',
                     'dots-git-styles\t1\nrepo\t31\nrepo\t32\n', 'dots-git-styles\t1\n\t31\n',
                     'dots-git-styles\t1\nrepo\t31\textra\n', 'x' * (2 * 1024 * 1024 + 1)]:
            self.table.write_text(data)
            self.assertEqual(self.shell('dots::git_style repo; printf %s "$REPLY"').stdout, '\x1b[1;94m')
        self.assertFalse((self.base / 'forbidden').exists())
        self.table.write_text('dots-git-styles\t1\nrepo\t0\n')
        self.assertEqual(self.shell('dots::git_style repo; printf %s "$REPLY"').stdout, '\x1b[0m')
        self.table.unlink()
        os.mkfifo(self.table)
        self.assertEqual(self.shell('dots::git_style branch; printf %s "$REPLY"').stdout, '\x1b[95m')
        self.table.unlink()
        self.table.symlink_to(self.config)
        self.assertEqual(self.shell('dots::git_style repo; printf %s "$REPLY"').stdout, '\x1b[1;94m')

    def test_plain_does_not_load_and_table_is_cached(self):
        for env in [dict(self.env, DOTS_COLOR='never'), dict(self.env, DOTS_COLOR='auto', NO_COLOR='1'),
                    dict(self.env, DOTS_COLOR='auto', TERM='dumb')]:
            result = self.shell('dots::git_style repo; printf "%s:%s" "$REPLY" "${_DOTS_GIT_STYLES_READY:-unread}"', env=env)
            self.assertEqual(result.stdout, ':unread')
        result = self.shell('dots::git_style repo; printf %s "$REPLY"; printf broken > "$1"; dots::git_style branch; printf %s "$REPLY"', str(self.table))
        self.assertEqual(result.stdout, self.esc('repo') + self.esc('branch'))

    def test_sync_publish_and_tracking_roles(self):
        source, bare, repo = self.remote_repo('remote')
        self.advance(source, bare)
        self.git(repo, 'fetch', 'origin')
        status = self.cli(repo, 'status').stdout
        self.assertIn(self.esc('ahead') + '0 ahead', status)
        self.assertIn(self.esc('behind') + '1 behind', status)
        synced = self.cli(repo, 'sync').stdout
        self.assertIn(self.esc('clean'), synced)
        (repo / 'file').write_text('publish me\n')
        self.git(repo, 'add', 'file')
        self.owned_remote(repo, bare)
        published = self.cli(repo, 'publish', '--yes', '-m', 'fixture').stdout
        self.assertIn(self.esc('clean') + '[+] published', published)
        self.git(repo, 'checkout', '--detach')
        (repo / 'file').write_text('detached change\n')
        self.git(repo, 'add', 'file')
        failed = self.cli(repo, 'publish', '--yes', ok=False)
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn(self.esc('blocked'), failed.stderr)
        self.assertNotIn(self.esc('blocked'), failed.stdout)

    def terminal(self, body, width, env):
        master, slave = pty.openpty()
        try:
            fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 24, width, 0, 0))
            result = subprocess.run(['bash', '--noprofile', '--norc', '-c', body],
                                    env=dict(env, COLUMNS=str(width)), cwd=self.base,
                                    stdout=slave, stderr=subprocess.PIPE, timeout=20)
            os.close(slave); slave = None
            data = b''
            while True:
                try: chunk = os.read(master, 65536)
                except OSError: break
                if not chunk: break
                data += chunk
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, b'')
            return data.decode().replace('\r\n', '\n')
        finally:
            os.close(master)
            if slave is not None: os.close(slave)

    def test_native_widths_and_destination_stream(self):
        repo = self.repo('long 界 repository ' * 5)
        (repo / ('long 界 path ' * 6 + '.png')).write_text('fixture')
        self.env['TEST_REPO'] = str(repo)
        for width in (40, 80, 120):
            output = self.terminal('exec bash "$DOTS/bin/dots" git status -C "$TEST_REPO"', width,
                                   dict(self.env, DOTS_COLOR='auto'))
            self.assertIn(self.esc('repo'), output)
            plain = SGR.sub('', output)
            # Long identity and filename survive line wrapping intact.
            joined = ''.join(line.strip() for line in plain.splitlines())
            self.assertIn(repo.name.replace(' ', ''), joined.replace(' ', ''))
            self.assertIn(('long 界 path ' * 6 + '.png').replace(' ', ''), joined.replace(' ', ''))
            # Summary text predates this change; check repository/file rows only.
            rows = plain.split('\n\n')[1].splitlines()
            for line in rows:
                cells = sum(2 if ord(c) > 127 else 1 for c in line)
                self.assertLessEqual(cells, width, line)
            output = self.terminal('source "$DOTS_LIB_DIR/ui.bash"; dots::git_style blocked 2; printf %s "$REPLY" >&2', width,
                                   dict(self.env, DOTS_COLOR='auto'))
            self.assertEqual(output, '')  # stderr is a pipe, stdout is a terminal


if __name__ == '__main__':
    unittest.main()

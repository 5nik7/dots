"""Exercise Git group shortcuts and sibling Wiki scope through the public frontends."""
import json
import os
import subprocess
import sys
import unittest

import test_git_operations as fixture


class Queries(unittest.TestCase):
    def setUp(self):
        self.f = fixture.GitOperations()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.root = self.f.repo('checkout')
        self.f.git(self.root, 'remote', 'add', 'origin', 'ssh://git@example.invalid:22/org/my project.git')
        self.entries = [[sys.executable, '-B', str(fixture.PROJECT/'lib/dots/cli.py')]]
        if os.name != 'nt':
            self.entries.append([str(fixture.CLI)])

    def call(self, entry, *args, code=0):
        result = subprocess.run([*entry, 'git', '-C', str(self.root), *args], capture_output=True,
                                env=dict(self.f.env, DOTS=str(fixture.PROJECT)), cwd=self.f.home)
        self.assertEqual(result.returncode, code, result.stderr)
        return result.stdout

    def test_field_queries_paths_and_argument_order(self):
        self.f.git(self.root, 'remote', 'add', 'other', 'https://name:secret@site.invalid/org/r.git?token=1')
        for entry in self.entries:
            self.assertEqual(self.call(entry, '-R', '--https', '-n'), b'https://example.invalid/org/my%20project.git')
            self.assertEqual(self.call(entry, 'info', '--remote', 'other', '-R'), b'https://site.invalid/org/r.git\n')
            self.assertEqual(self.call(entry, '--get', 'protocol'), b'ssh\n')
            self.assertEqual(self.call(entry, 'path', '--format', '{{{parent_basename}}}'), b'{checkout}\n')
            self.assertEqual(self.call(entry, 'path', '--get', 'current'), os.fsencode(self.root) + b'\n')
            self.assertEqual(self.call(entry, '-s', '--json'), self.call(entry, 'status', '-s', '--json'))
            self.call(entry, '--host', '--https', code=2)

    @unittest.skipUnless(os.name != 'nt' and (fixture.PROJECT/'plugins/git-it/git-it').is_file(),
                         'requires the initialized POSIX plugin')
    def test_installed_plugin_and_dots_report_the_same_repository(self):
        plugin = fixture.PROJECT/'plugins/git-it/git-it'
        child = self.f.repo('child')
        self.f.git(self.root, 'submodule', 'add', str(child), 'plugins/child')
        self.f.git(self.root, 'commit', '-am', 'Add child')
        (self.root/'changed.txt').write_text('work')
        repo_args = ['-C', str(self.root)]
        for width in (40, 80, 120):
            env = dict(self.f.env, DOTS=str(fixture.PROJECT), DOTS_ICONS='always', DOTS_COLOR='never',
                       COLUMNS=str(width), TERM='xterm-256color')
            reports = []
            for command in ([str(plugin), 'status'], [str(fixture.CLI), 'git', 'status']):
                result = subprocess.run([*command, *repo_args, '--no-progress', '--view', 'default'],
                                        env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                lines = result.stdout.splitlines()
                self.assertEqual(sum('Protocol' in line for line in lines), 1)
                self.assertTrue(any('changed.txt' in line for line in lines))
                self.assertTrue(any('child' in line and '' in line for line in lines))
                # Compare the repository identity and metadata independently of
                # the different fixture path lengths and status diagnostics.
                reports.append([line.strip() for line in lines if any(
                    label in line for label in ('Host ', 'Protocol ', 'Remote ', 'Upstream ', 'Owner '))])
            self.assertEqual(*reports)

    def test_sibling_wiki(self):
        wiki = self.f.repo('checkout.wiki')
        self.f.git(wiki, 'remote', 'add', 'origin', 'https://example.invalid/org/my project.wiki.git')
        for entry in self.entries:
            rows = json.loads(self.call(entry, 'status', '--json'))['repositories']
            self.assertEqual([(r['path'], r.get('kind')) for r in rows], [(str(self.root), None), (str(wiki), 'wiki')])
            self.assertEqual(json.loads(self.call(entry, 'wiki', 'info', '--json'))['base'], str(wiki))
            self.assertEqual(len(json.loads(self.call(entry, 'status', '--no-wiki', '--json'))['repositories']), 1)
            self.assertEqual(self.call(entry, 'wiki', 'info', '--get', 'root').strip(), os.fsencode(wiki))
        self.f.git(wiki, 'remote', 'set-url', 'origin', 'https://example.invalid:8443/org/my project.wiki.git')
        self.assertEqual(len(json.loads(self.call(self.entries[0], 'status', '--json'))['repositories']), 1)


if __name__ == '__main__':
    unittest.main()

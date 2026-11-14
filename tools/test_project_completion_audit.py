#!/usr/bin/env python3
"""Source discovery is read-only, explicit about limits, and fails on gaps."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

import check_project_completions as audit


class ProjectCompletions(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='dots-project-completions-')
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.repos = self.home/'repos space ü'
        self.repos.mkdir()
        self.dots = self.home/'dots'

    def write(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data)

    def run_audit(self, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = audit.main(['--repos-root',str(self.repos),'--dots-root',str(self.dots),'--json',*args])
        return status, json.loads(output.getvalue())

    def test_known_sources_aliases_and_absorbed_plugins(self):
        self.write(self.dots/'lib/dots/completion/zsh', 'compadd -J commands -- demo\n')
        self.write(self.dots/'plugins/pkgs/completions/pkgs.zsh', '_describe -t commands command names\n')
        (self.repos/'dots').symlink_to(self.dots, target_is_directory=True)
        self.write(self.repos/'pkgs/pkgs', '#!/bin/sh\ntouch NEVER\n')
        self.write(self.repos/'battery/battery', '#!/bin/sh\n_arguments --help\n')
        self.write(self.repos/'battery/maintenance.sh', '_arguments --help\n')
        before={p:p.read_bytes() for p in self.home.rglob('*') if p.is_file()}
        status, result = self.run_audit('--check')
        self.assertEqual(status, 0, result)
        rows=result['projects']
        root=next(r for r in rows if r['name']=='dots')
        self.assertEqual(root['aliases'],[str(self.repos/'dots')])
        self.assertEqual(next(r for r in rows if r['classification']=='historical-copy')['owner'],str(self.dots/'plugins/pkgs'))
        self.assertEqual(before,{p:p.read_bytes() for p in self.home.rglob('*') if p.is_file()})
        self.assertFalse((self.repos/'pkgs/NEVER').exists())

    def test_new_cli_requires_review_without_running_its_code(self):
        self.write(self.repos/'new-tool/package.json', json.dumps({'bin':{'new-tool':'bad.js'}}))
        self.write(self.repos/'new-tool/bad.js', 'throw new Error("must never execute");\n')
        status,result=self.run_audit()
        self.assertEqual(status,0)
        self.assertEqual(result['projects'][0]['status'],'unreviewed')
        self.assertIn('package.json bin',result['projects'][0]['evidence'])
        self.assertEqual(self.run_audit('--check')[0],1)

    def test_non_cli_becoming_cli_requires_review(self):
        self.write(self.repos/'njen.io/package.json', json.dumps({'scripts':{'build':'vite build'}}))
        status,result=self.run_audit('--check')
        self.assertEqual(status,0)
        self.assertEqual(result['projects'][0]['classification'],'non-cli')
        self.write(self.repos/'njen.io/package.json', json.dumps({'bin':{'web-tool':'cli.js'}}))
        self.assertEqual(self.run_audit('--check')[0],1)

    def test_missing_and_untyped_completion_sources_fail(self):
        (self.repos/'paint').mkdir()
        status,result=self.run_audit('--check')
        self.assertEqual(status,1)
        self.assertEqual(result['projects'][0]['missing_sources'],['paint'])
        self.write(self.repos/'paint/paint', '#!/bin/bash\ncompadd -- alpha beta\n')
        status,result=self.run_audit('--check')
        self.assertEqual(status,1)
        self.assertEqual(result['projects'][0]['status'],'missing-tags')

    def test_missing_repository_directory_is_not_an_empty_success(self):
        self.repos.rmdir()
        self.assertEqual(self.run_audit('--check')[0],1)

    def test_custom_nonsemantic_tags_require_review(self):
        self.write(self.repos/'paint/paint', '_describe -V -t colors color names\n')
        status,result=self.run_audit('--check')
        self.assertEqual(status,1)
        self.assertEqual(result['projects'][0]['status'],'unmapped-tags')
        self.write(self.repos/'paint/paint', '_describe -V -t color-values color names\n')
        self.assertEqual(self.run_audit('--check')[0],0)

    def test_hidden_directories_and_large_sources_are_not_scanned(self):
        self.write(self.repos/'.private/package.json', '{"bin":"secret"}')
        self.assertEqual(self.run_audit('--check')[1]['projects'],[])
        self.write(self.repos/'paint/paint', '_arguments\n'+'x'*audit.MAX_SOURCE)
        self.assertEqual(self.run_audit('--check')[1]['projects'][0]['status'],'missing-source')


if __name__ == '__main__':
    unittest.main()

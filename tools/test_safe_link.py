#!/usr/bin/env python3
"""Safe linking, transactional replacement and native frontend parity."""
import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest import mock

import test_backup_catalog as core
import test_backup_cli as cli
sys.path.insert(0, str(core.ROOT / 'lib/dots'))
from link_cli import prepare


class Links(unittest.TestCase):
    setUp = core.Backups.setUp
    file = core.Backups.file
    plan = core.Backups.plan

    def test_replace_backup_noop_and_exact_directory(self):
        source = self.file('source', 'managed')
        target = self.file('target', 'original')
        plan = prepare(self.plan(), [source], target); plan.apply('link')
        self.assertTrue(target.is_symlink()); self.assertEqual(target.read_text(), 'managed')
        row = self.plan().records()[0]
        self.assertEqual(Path(row['path']).read_text(), 'original')
        repeat = prepare(self.plan(), [source], target)
        self.assertEqual(repeat.apply('link')['status'], 'unchanged')
        directory = self.home / 'old directory'; directory.mkdir()
        (directory / 'nested').write_text('retain')
        plan = prepare(self.plan(), [source], directory, exact=True); plan.apply('link')
        self.assertTrue(directory.is_symlink())
        saved = next(r for r in self.plan().records() if r['kind'] == 'directory')
        self.assertEqual((Path(saved['path']) / 'nested').read_text(), 'retain')

    def test_multi_source_relative_and_ancestor_guards(self):
        a,b = self.file('one'),self.file('two')
        directory = self.home / 'targets'; directory.mkdir()
        alias = self.home / 'alias'; alias.symlink_to('targets', target_is_directory=True)
        plan = prepare(self.plan(), [a,b], alias, relative=True); plan.apply('link')
        self.assertEqual(os.readlink(directory/'one'), '../one')
        self.assertEqual(os.readlink(directory/'two'), '../two')
        self.assertTrue(alias.is_symlink())

    def test_missing_overlap_and_duplicate_names_fail_before_apply(self):
        source = self.file('source')
        destination = self.home/'targets'; destination.mkdir()
        with self.assertRaisesRegex(ValueError, 'missing'):
            prepare(self.plan(), [source, self.home/'missing'], destination)
        with self.assertRaisesRegex(ValueError, 'overlap'):
            prepare(self.plan(), [source], source)
        a,b = self.file('a/same'),self.file('b/same')
        with self.assertRaisesRegex(ValueError, 'overlap'):
            prepare(self.plan(), [a,b], self.home)
        self.assertFalse(self.state.exists()); self.assertFalse(self.storage.exists())
        self.assertTrue(source.is_file())

    def test_missing_explicit_and_no_backup_discard_after_commit(self):
        source = self.home/'future'
        target = self.file('target')
        plan = prepare(self.plan(), [source], target, allow_missing=True, backup=False)
        plan.apply('link')
        self.assertTrue(target.is_symlink()); self.assertFalse(target.exists())
        self.assertEqual(self.plan().records(), [])
        self.assertFalse(self.storage.exists())
        self.assertFalse(any((self.state/'files/transactions').glob('*/*-before')))

    def test_source_symlink_identity_preserved(self):
        source = self.home / 'alias'; source.symlink_to('actual')
        self.file('actual', 'data')
        target = self.home / 'target'
        plan = prepare(self.plan(), [source], target); plan.apply('link')
        self.assertEqual(os.readlink(target), str(source))
        self.assertEqual(os.readlink(source), 'actual')

    def test_batch_failure_rolls_back_targets_and_backups(self):
        a,b = self.file('one'),self.file('two')
        directory = self.home / 'targets'; directory.mkdir()
        (directory/'one').write_text('first original'); (directory/'two').write_text('second original')
        plan = prepare(self.plan(), [a,b], directory)
        rename = os.rename
        # Fail once so rollback can subsequently restore the second object.
        failed = False
        def once(source,target):
            nonlocal failed
            if not failed and Path(target)==directory/'two' and '.dots-new-' in str(source):
                failed=True; raise OSError('injected second-link failure')
            return rename(source,target)
        with mock.patch('transactions.os.rename', side_effect=once):
            with self.assertRaisesRegex(OSError, 'injected'):
                plan.apply('link')
        self.assertEqual((directory/'one').read_text(), 'first original')
        self.assertEqual((directory/'two').read_text(), 'second original')
        self.assertFalse((directory/'one').is_symlink())
        self.assertEqual(self.plan().records(), [])


class LinkCLI(unittest.TestCase):
    source = cli.BackupCLI.source

    def setUp(self):
        cli.BackupCLI.setUp(self)
        shutil.copy2(core.ROOT/'bin/dots-link', self.root/'bin/dots-link')

    def run_link(self, *args, native=False, **env):
        if native:
            command = [sys.executable,'-B',str(self.root/'lib/dots/native.py'),'link',
                       base64.b64encode(json.dumps(list(args)).encode()).decode()]
        else:
            command = [shutil.which('bash'),str(self.root/'bin/dots'),'link',*args]
        result = subprocess.run(command, env=dict(self.env,**env),capture_output=True,text=True,timeout=30,cwd=self.home)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        return result

    def test_native_json_and_quiet_plain_rows(self):
        source = self.source('雪 "literal"')
        target = self.home/'target'
        result = self.run_link(str(source),str(target),'--json',native=True,DOTS_COLOR='always',DOTS_ICONS='always')
        row = json.loads(result.stdout)['items'][-1]
        self.assertEqual(row['source'],str(source)); self.assertEqual(row['target'],str(target))
        self.assertNotIn('\x1b',result.stdout)
        result = self.run_link(str(source),str(target),'-q')
        self.assertEqual(result.stdout,''); self.assertEqual(result.stderr,'')
        result = self.run_link(str(source),str(target),'--icons=always','--color=never')
        self.assertIn('󰡯 ~/雪 "literal" -> ~/target',result.stdout)
        self.assertNotIn(str(self.home),result.stdout)

    def test_dry_run_and_metadata(self):
        source = self.source(); target = self.home/'target'
        self.run_link(str(source),str(target),'--dry-run','--json')
        self.assertFalse(target.exists()); self.assertFalse((self.home/'state').exists())
        self.run_link('--help')

    def test_human_widths_and_data_independence(self):
        import re
        from resources import cells
        source=self.source('雪 mixed '+ 'x'*55); target=self.home/('target '+ 'y'*65)
        for columns in (40,80,120):
            for color in ('always','never'):
                p=self.run_link(str(source),str(target),'--dry-run','--color='+color,'--icons=always',COLUMNS=str(columns))
                plain=re.sub(r'\x1b\[[0-9;]*m','',p.stdout)
                self.assertNotIn(str(self.home),plain)
                for line in plain.splitlines(): self.assertLessEqual(cells(line),columns)
                data=self.run_link(str(source),str(target),'--dry-run','--json',DOTS_COLOR=color,COLUMNS=str(columns))
                self.assertEqual(json.loads(data.stdout)['items'][-1]['source'],str(source))


if __name__ == '__main__': unittest.main()

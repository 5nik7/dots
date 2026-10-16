#!/usr/bin/env python3
"""Owned catalog-only cleanup, recovery, interaction and presentation checks."""
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib/dots/files'))
import check
import transactions


class CheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='dots check ü ')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.repo = self.base / 'repo'
        self.home = self.base / 'home'
        (self.repo / '.dots').mkdir(parents=True)
        (self.repo / 'config').mkdir()
        self.home.mkdir()
        self.env = dict(os.environ, DOTS=str(self.repo), HOME=str(self.home),
                        XDG_CONFIG_HOME=str(self.home / 'config'), XDG_STATE_HOME=str(self.home / 'state'),
                        XDG_CACHE_HOME=str(self.home / 'cache'), XDG_DATA_HOME=str(self.home / 'data'),
                        DOTS_COLOR='never', DOTS_ICONS='never', DOTS_PROGRESS='never')
        self.platforms = ['termux', 'linux', 'wsl', 'windows']
        self.sources = [dict(id='dots', path='.', roots=['config'], platforms=self.platforms)]
        self.row = dict(id='missing', source='config/absent parent/-missing ü', app='example',
                        category='config', platforms=self.platforms, target='${CONFIG}/missing', strategy='link')
        self.save_sources()
        self.save([self.row])
        self.patch = patch.dict(os.environ, self.env)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def save_sources(self):
        (self.repo / '.dots/sources.json').write_text(json.dumps(dict(schema=1, sources=self.sources)))

    def save(self, rows, repo=None, owner='dots'):
        (repo or self.repo).joinpath('.dots/files.json').write_text(json.dumps(
            dict(schema=1, repository=owner, resources=rows, custom='preserved')))

    def records(self, repo=None):
        return json.loads((repo or self.repo).joinpath('.dots/files.json').read_text())['resources']

    def cli(self, *args, code=0, **env):
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'lib/dots/files/check.py'), *args],
                                env=dict(self.env, **env), capture_output=True, text=True)
        self.assertEqual(result.returncode, code, result.stderr)
        return result

    def inspected(self, *args):
        instance = check.Check(check.parser().parse_args(list(args)))
        instance.inspect()
        return instance

    def test_dry_run_json_and_targets_unchanged(self):
        target = self.home / 'config/missing'
        target.parent.mkdir()
        target.symlink_to(self.repo / self.row['source'])
        before = (self.repo / '.dots/files.json').read_bytes()
        out = self.cli('--dry-run', '--yes', '--json', DOTS_COLOR='always', DOTS_ICONS='always').stdout
        self.assertNotIn('\x1b', out)
        data = json.loads(out)
        self.assertEqual(data['items'][0]['outcome'], 'would-remove')
        self.assertEqual(data['counts']['eligible'], 1)
        self.assertEqual(before, (self.repo / '.dots/files.json').read_bytes())
        self.assertTrue(target.is_symlink())
        self.assertFalse((self.home / 'state').exists())
        self.assertFalse(list(self.repo.rglob('*.lock')))

    def test_apply_undo_idempotence_preserves_all_target_kinds(self):
        rows = []
        for i, kind in enumerate(('file', 'directory', 'broken-link', 'other-link', 'absent')):
            row = dict(self.row, id='item-' + str(i), target='${CONFIG}/' + kind)
            rows.append(row)
            path = self.home / 'config' / kind
            path.parent.mkdir(exist_ok=True)
            if kind == 'file': path.write_text('untouched')
            if kind == 'directory': path.mkdir(); (path / 'child').write_text('untouched')
            if kind == 'broken-link': path.symlink_to(self.repo / row['source'])
            if kind == 'other-link': path.symlink_to(self.home / 'config/file')
        self.save(rows)
        target_before = transactions.digest(self.home / 'config')
        result = json.loads(self.cli('--yes', '--json').stdout)
        self.assertEqual(result['counts']['removed'], 5)
        self.assertEqual(self.records(), [])
        self.assertEqual(transactions.digest(self.home / 'config'), target_before)
        self.assertEqual(json.loads(self.cli('--yes', '--json').stdout)['status'], 'unchanged')
        store = transactions.Store(self.home / 'state/dots')
        self.assertEqual(len(store.records()), 1)
        ops, guards, catalogs = store.inverse(result['transaction']['id'])
        store.apply('undo', ops, guards, catalogs=catalogs)
        self.assertEqual(self.records(), rows)
        self.assertEqual(transactions.digest(self.home / 'config'), target_before)

    def test_sources_filters_conflicts_and_broken_links(self):
        (self.repo / 'config/broken').symlink_to('absent')
        (self.repo / 'config/present').write_text('present')
        self.save([self.row, dict(self.row, id='broken', source='config/broken'),
                   dict(self.row, id='present', source='config/present'),
                   dict(self.row, id='inactive', platforms=['windows'], target=None)])
        self.sources += [dict(id='optional', path='optional', platforms=self.platforms),
                         dict(id='private', path='private', platforms=self.platforms, excluded=True)]
        self.save_sources()
        data = json.loads(self.cli('--platform', 'linux', '--dry-run', '--json').stdout)
        self.assertEqual(data['counts']['eligible'], 1)
        self.assertEqual(next(x for x in data['items'] if x['id']=='dots:missing')['status'], 'conflict')
        self.assertEqual(next(x for x in data['items'] if x['id']=='dots:broken')['source_state'], 'broken-source-link')
        self.assertEqual([x['status'] for x in data['sources']], ['available', 'unavailable', 'excluded'])
        data = json.loads(self.cli('--platform', 'linux', '--all-platforms', '--dry-run', '--json', '--sort', 'source').stdout)
        self.assertEqual(data['counts']['eligible'], 2)
        self.assertEqual(json.loads(self.cli('--app', 'other', '--dry-run', '--json').stdout)['items'], [])
        self.cli('--repo', 'unknown', '--yes', code=1)
        self.cli('--yes')
        self.assertTrue((self.repo / 'config/broken').is_symlink())

    def test_nonterminal_and_json_require_explicit_mode(self):
        self.cli(code=2)
        self.cli('--json', code=2)
        self.cli('--unknown', code=2)
        self.assertFalse((self.home / 'state').exists())
        self.save([])
        self.cli()
        self.assertFalse((self.home / 'state').exists())

    def test_individual_selection_final_cancel_and_skip(self):
        self.save([self.row, dict(self.row, id='second')])
        for answers, expected in (([False, False], 2), ([True, True, False], 2), ([True, False, True], 1)):
            with patch.object(sys.stdin, 'isatty', return_value=True), patch.object(sys.stderr, 'isatty', return_value=True):
                output = io.StringIO()
                output.isatty = lambda: True
                with redirect_stdout(output), patch.object(check, 'confirm', side_effect=answers):
                    self.assertEqual(check.main([]), 0)
            self.assertEqual(len(self.records()), expected)
            if expected == 2:
                self.assertFalse((self.home / 'state').exists())
        self.assertEqual(self.records()[0]['id'], 'second')

    def test_permission_and_non_directory_fail_closed(self):
        original = Path.lstat
        source = self.repo / self.row['source']
        def denied(path, *a, **kw):
            if path == source: raise PermissionError('denied fixture')
            return original(path, *a, **kw)
        with patch.object(Path, 'lstat', denied):
            with self.assertRaises(PermissionError): self.inspected()
            with self.assertRaises(PermissionError): transactions.digest(source)
        (self.repo / 'config/absent parent').write_text('not a directory')
        self.cli('--yes', code=1)
        self.assertEqual(len(self.records()), 1)
        self.assertFalse((self.home / 'state').exists())

    def test_source_and_catalog_drift_refused(self):
        instance = self.inspected()
        source = self.repo / self.row['source']
        source.parent.mkdir()
        source.write_text('reappeared')
        with self.assertRaisesRegex(ValueError, 'source changed'): instance.apply(['dots:missing'])
        source.unlink()
        instance = self.inspected()
        self.save([self.row, dict(self.row, id='added')])
        with self.assertRaisesRegex(ValueError, 'changed after preview'): instance.apply(['dots:missing'])
        self.assertFalse((self.home / 'state').exists())

    def test_source_reappears_inside_store_preflight(self):
        instance = self.inspected()
        operations, guards, catalogs = instance.plan(['dots:missing'])
        source = self.repo / self.row['source']
        source.parent.mkdir()
        source.symlink_to('still absent')
        with self.assertRaisesRegex(ValueError, 'changed after preview'):
            instance.manager.store.apply('check', operations, guards, catalogs=catalogs)
        self.assertEqual(len(self.records()), 1)

    def second_catalog(self):
        child = self.repo / 'child'
        (child / '.dots').mkdir(parents=True)
        self.sources.append(dict(id='child', path='child', roots=['config'], platforms=self.platforms))
        self.save_sources()
        self.save([self.row], child, 'child')
        return child

    def test_multi_catalog_rollback(self):
        child = self.second_catalog()
        instance = self.inspected()
        rename = transactions.os.rename
        calls = 0
        def fail(a, b):
            nonlocal calls
            calls += 1
            if calls == 3: raise OSError('fixture rename failure')
            return rename(a, b)
        with patch.object(transactions.os, 'rename', fail):
            with self.assertRaises(OSError): instance.apply(['dots:missing', 'child:missing'])
        self.assertEqual(self.records(), [self.row])
        self.assertEqual(self.records(child), [self.row])
        self.assertEqual(instance.manager.store.records()[0]['status'], 'rolled-back')

    def test_abrupt_interruption_recovery(self):
        child = self.second_catalog()
        code = '''import os,sys
sys.path.insert(0, sys.argv[1])
import check,transactions
c=check.Check(check.parser().parse_args(['--yes']))
c.inspect()
original=transactions.os.rename
def crash(a,b):
 original(a,b)
 os._exit(77)
transactions.os.rename=crash
c.apply(['dots:missing','child:missing'])
'''
        proc = subprocess.run([sys.executable, '-B', '-c', code, str(ROOT / 'lib/dots/files')], env=self.env)
        self.assertEqual(proc.returncode, 77)
        store = transactions.Store(self.home / 'state/dots')
        record = store.records()[0]
        self.assertEqual(record['status'], 'applying')
        store.recover(record['id'])
        self.assertEqual(self.records(), [self.row])
        self.assertEqual(self.records(child), [self.row])

    def test_confirmation_fallback_and_eof(self):
        with patch.object(check, 'gum_confirm', return_value=None), patch.object(sys, 'stdin', io.StringIO('yes\n')):
            self.assertTrue(check.confirm('Fixture?'))
        with patch.object(check, 'gum_confirm', return_value=None), patch.object(sys, 'stdin', io.StringIO('')):
            with self.assertRaises(KeyboardInterrupt): check.confirm('Fixture?')

    def test_symlinked_parent_refused(self):
        (self.repo / 'config/absent parent').symlink_to(self.home, target_is_directory=True)
        self.cli('--yes', code=1)
        self.assertEqual(len(self.records()), 1)

    def test_composition_drift_and_unavailable_catalog_appearance(self):
        self.sources.append(dict(id='optional', path='optional', platforms=self.platforms))
        self.save_sources()
        instance = self.inspected()
        child = self.repo/'optional'
        (child/'.dots').mkdir(parents=True)
        self.save([], child, 'optional')
        with self.assertRaisesRegex(ValueError, 'changed after preview'):
            instance.apply(['dots:missing'])
        instance = self.inspected()
        self.sources[0]['platforms'] = ['windows']
        self.save_sources()
        with self.assertRaisesRegex(ValueError, 'changed after preview'):
            instance.apply(['dots:missing'])
        self.assertFalse((self.home/'state').exists())

    def test_undo_refuses_catalog_drift_and_preserves_metadata(self):
        self.save([dict(self.row, replaces=['other:missing']), dict(self.row, id='keep', app='keep')])
        result = json.loads(self.cli('--yes','--app','example','--json').stdout)
        doc = json.loads((self.repo/'.dots/files.json').read_text())
        self.assertEqual(doc['custom'], 'preserved')
        self.assertEqual([r['id'] for r in doc['resources']], ['keep'])
        store = transactions.Store(self.home/'state/dots')
        self.save([self.row])
        with self.assertRaisesRegex(ValueError, 'drift blocks undo'):
            store.inverse(result['transaction']['id'])

    def test_ui_error_does_not_apply(self):
        output = io.StringIO()
        output.isatty = lambda: True
        with patch.object(sys.stdin,'isatty',return_value=True), patch.object(sys.stderr,'isatty',return_value=True):
            with redirect_stdout(output), patch.object(check,'gum_confirm',side_effect=ValueError('UI failed')):
                with self.assertRaisesRegex(ValueError,'UI failed'): check.main([])
        self.assertEqual(self.records(), [self.row])
        self.assertFalse((self.home/'state').exists())

    @unittest.skipIf(os.name == 'nt', 'POSIX owned terminal')
    def test_owned_terminal_widths_progress_and_cancellation(self):
        import fcntl
        import pty
        import re
        import struct
        import termios
        from resources import cells
        code = '''import sys,time
sys.path.insert(0,sys.argv[1])
import check
original=check.source_state
def slow(path):
 time.sleep(0.65)
 return original(path)
check.source_state=slow
check.gum_confirm=lambda *a,**kw: None
raise SystemExit(check.main(sys.argv[2:]))
'''
        for width in (40, 80, 120):
            for dry_run in (True, False):
                master, slave = pty.openpty()
                try:
                    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH',24,width,0,0))
                    proc = subprocess.Popen([sys.executable, '-B', '-c', code, str(ROOT/'lib/dots/files'),
                                             *(['--dry-run'] if dry_run else [])],
                                            stdin=slave, stdout=slave, stderr=slave,
                                            env=dict(self.env, TERM='xterm-256color', COLUMNS=str(width),
                                                     DOTS_COLOR='always' if dry_run else 'never', DOTS_PROGRESS='auto'))
                    os.close(slave)
                    slave = None
                    if not dry_run:
                        os.write(master, b'y\nn\n')
                    chunks = []
                    while True:
                        try: block = os.read(master, 65536)
                        except OSError: break
                        if not block: break
                        chunks.append(block)
                    self.assertEqual(proc.wait(timeout=5), 0)
                    text = b''.join(chunks).decode()
                    plain = re.sub(r'\x1b\[[0-9;]*m', '', text)
                    for line in plain.replace('\r\n','\n').split('\n'):
                        for frame in line.split('\r'):
                            self.assertLessEqual(cells(frame), width, repr(frame))
                    if dry_run:
                        self.assertNotIn('\r', text.replace('\r\n','\n'))
                        self.assertIn('Preview only', plain)
                        self.assertIn('\x1b[', text)
                    else:
                        self.assertIn('\r', text.replace('\r\n','\n'))
                        self.assertIn('cancelled', plain)
                        self.assertNotIn('\x1b[', text)
                    self.assertEqual(self.records(), [self.row])
                    self.assertFalse((self.home/'state').exists())
                finally:
                    os.close(master)
                    if slave is not None: os.close(slave)


if __name__ == '__main__':
    unittest.main()

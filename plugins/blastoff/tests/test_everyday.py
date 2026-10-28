"""Focused everyday-use safety and help regressions; isolated state only."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent

class Everyday(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='blastoff-everyday-')
        self.addCleanup(temp.cleanup)
        self.home = Path(temp.name)
        self.store = self.home/'store'
        self.config = self.home/'active.toml'
        self.env = dict(os.environ, HOME=str(self.home), USERPROFILE=str(self.home),
                        STARSHIP_CONFIG=str(self.config), BLASTOFF_HOME=str(self.store),
                        NO_COLOR='1')

    def cli(self, *args):
        return subprocess.run([sys.executable, '-I', str(ROOT/'lib/blastoff.py'), *args],
                              env=self.env, capture_output=True, timeout=10)

    def test_delete_refuses_regular_active_config_in_storage(self):
        for kind in ('theme', 'module'):
            with self.subTest(kind=kind):
                target = self.store/(kind+'s')/'daily.toml'
                target.parent.mkdir(parents=True, exist_ok=True)
                original = b'[directory]\nstyle="purple"\n'
                target.write_bytes(original)
                self.env['STARSHIP_CONFIG'] = str(target)
                result = self.cli(kind, 'delete', 'daily', '--force', '--json')
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn('active config', json.loads(result.stderr)['error'])
                self.assertEqual(target.read_bytes(), original)
                self.assertFalse((self.store/'backups').exists())

    def test_nonobject_backup_metadata_is_clean_error(self):
        backups = self.store/'backups'
        backups.mkdir(parents=True)
        self.config.write_bytes(b'x=1\n')
        (backups/'bad.toml').write_bytes(b'x=2\n')
        for value in ([], None, 'text', 3):
            (backups/'bad.json').write_text(json.dumps(value))
            for args in [('backup','restore','bad'), ('backup','list')]:
                with self.subTest(value=value, args=args):
                    result = self.cli(*args, '--json')
                    self.assertEqual(result.returncode, 1)
                    if args == ('backup','list'):
                        doc=json.loads(result.stdout)
                        self.assertEqual(doc['backups'],[])
                        self.assertEqual(doc['errors'][0]['id'],'bad')
                        self.assertIn('metadata',json.loads(result.stderr)['message'])
                    else:
                        self.assertEqual(result.stdout, b'')
                        self.assertIn('metadata', json.loads(result.stderr)['error'])
                    self.assertEqual(self.config.read_bytes(), b'x=1\n')
                    self.assertEqual(len(list(backups.iterdir())), 2)

    def test_help_explains_operations_and_global_options(self):
        for args, expected in [
            (('theme','apply'), ('local:', '--replace-link')),
            (('theme','delete'), ('--force', 'active config')),
            (('module','load'), ('unrelated', '--replace-link')),
            (('backup','restore'), ('config', 'checksum')),
        ]:
            with self.subTest(args=args):
                result = self.cli(*args, '--help')
                self.assertEqual(result.returncode, 0)
                for text in expected:
                    self.assertIn(text, ' '.join(result.stdout.decode().split()))
        self.assertFalse(self.store.exists())
        self.assertFalse(self.config.exists())

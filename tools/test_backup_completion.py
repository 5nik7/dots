#!/usr/bin/env python3
"""Bak completion contracts in isolated roots; no payload reads or writes."""
import json
from pathlib import Path
import subprocess
import sys
import unittest
from test_backup_cli import BackupCLI


class Completion(unittest.TestCase):
    setUp = BackupCLI.setUp
    run_bak = BackupCLI.run_bak
    source = BackupCLI.source
    # Reuse only fixture helpers, not the parent's tests.
    def complete(self, words, shell='bash', native=False):
        command = ([sys.executable, '-B', str(self.root/'lib/dots/cli.py'), '__complete', *words[1:]] if native else
                   [str(self.root/'bin/dots'), '__complete', shell, str(len(words)-1), '--', *words])
        result = subprocess.run(command, env=self.env, cwd=self.home, text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('\x1b', result.stdout)
        return result.stdout

    def test_completion_routes_and_choices(self):
        for command in (['bak'], ['dots-bak'], ['dots','bak']):
            for shell in ('bash','zsh','fish','nu','xonsh'):
                self.assertIn('candidate\trestore\t', self.complete([*command,'res'],shell))
                self.assertIn('candidate\t--quiet\t', self.complete([*command,'--q'],shell))
                self.assertIn('candidate\t--color=always\t', self.complete([*command,'--color=a'],shell))
        self.assertIn('candidate\trestore\t',self.complete(['dots','bak','res'],native=True))
        self.assertFalse((self.home/'state').exists())

    def test_ids_paths_and_literal_nonexecution(self):
        row=json.loads(self.run_bak(str(self.source('雪 space')),'--json').stdout)['items'][0]
        payload=Path(row['path']);payload.unlink() # Completion reads metadata only.
        before=(self.home/'state/dots/bak/catalog.json').read_bytes()
        self.assertIn(row['id']+'\t~/雪 space',self.complete(['bak','restore','']))
        self.assertNotIn(row['id'],self.complete(['bak','delete',row['id'],'']))
        self.assertEqual(self.complete(['bak','restore',row['id'],'--to=']), 'file\t--to=\t\n')
        self.source('literal $(bad) 雪')
        for shell in ('nu','xonsh'):
            self.assertIn('candidate\t--to=literal $(bad) 雪\t',self.complete(['bak','restore',row['id'],'--to=literal'],shell))
        self.assertEqual(before,(self.home/'state/dots/bak/catalog.json').read_bytes())
        self.assertFalse((self.home/'bad').exists())
        (self.home/'state/dots/bak/catalog.json').write_text('{invalid')
        self.assertEqual(self.complete(['bak','show','']), '')

    def test_registration(self):
        for shell in ('bash','zsh','fish','powershell'):
            text=(self.root/'lib/dots/completion'/shell).read_text()
            self.assertIn('dots-bak',text)
        for shell in ('nu','xsh'):
            self.assertIn('dots-bak',(self.root/'lib/dots/shell'/('init.'+shell)).read_text())


if __name__=='__main__':unittest.main()

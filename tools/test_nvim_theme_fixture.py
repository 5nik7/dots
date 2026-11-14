#!/usr/bin/env python3
"""Owned fake editors exercise fixture cleanup without Neovim or publication."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import nvim_theme_fixture as fixture


@unittest.skipUnless(os.name == 'posix', 'requires native POSIX process groups')
class EditorProcesses(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='dots nvim process ü ')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.home = self.root/'home'; self.home.mkdir()
        self.env = {'HOME':str(self.home), 'PATH':'', 'PYTHONDONTWRITEBYTECODE':'1'}
        if os.environ.get('LD_PRELOAD'):
            self.env['LD_PRELOAD'] = os.environ['LD_PRELOAD']
        for kind in ('CONFIG','DATA','STATE','CACHE'):
            self.env['XDG_'+kind+'_HOME'] = str(self.home/kind.lower())
        self.editor = self.root/'fake editor'
        self.editor.write_text('#!'+sys.executable+'\n'+'''import json,os,subprocess,sys,time
from pathlib import Path
child=subprocess.Popen([sys.executable,'-I','-c','import time; time.sleep(60)'])
Path('processes.json').write_text(json.dumps([os.getpid(),child.pid]))
print('owned editor output',flush=True)
print('owned editor error',file=sys.stderr,flush=True)
if os.environ.get('FIXTURE_TIMEOUT'): time.sleep(60)
print('ANODIZE_NVIM_OK',flush=True)
''', encoding='utf-8')
        self.editor.chmod(0o700)

    def assert_stopped(self):
        parent, child = json.loads((self.home/'processes.json').read_text())
        # A child can briefly remain a zombie until its OS reaper runs; it must
        # never remain executable. The fixture directly reaps its editor.
        def running(pid):
            proc = Path('/proc')/str(pid)/'stat'
            try:
                if proc.exists() and proc.read_text().rsplit(')',1)[1].split()[0] == 'Z': return False
                os.kill(pid,0)
            except ProcessLookupError: return False
            return True
        deadline = time.monotonic()+2
        while running(child) and time.monotonic()<deadline: time.sleep(0.01)
        if running(child):
            os.kill(child,signal.SIGKILL)
            self.fail('owned editor child survived process-group cleanup')
        with self.assertRaises(ChildProcessError): os.waitpid(parent,os.WNOHANG)

    def test_success_removes_background_child_and_preserves_output(self):
        result = fixture._run_posix([str(self.editor)],env=self.env,cwd=self.home,output_root=self.root)
        self.assertEqual(result.returncode,0)
        self.assertIn('ANODIZE_NVIM_OK',result.stdout)
        self.assertIn('owned editor error',result.stderr)
        self.assert_stopped()

    def test_timeout_kills_group_reaps_editor_and_preserves_output(self):
        self.env['FIXTURE_TIMEOUT']='1'
        started=time.monotonic()
        with self.assertRaises(subprocess.TimeoutExpired) as caught:
            fixture._run_posix([str(self.editor)],env=self.env,cwd=self.home,output_root=self.root,timeout=2)
        self.assertEqual(caught.exception.timeout,2)
        self.assertIn(b'owned editor output',caught.exception.output)
        self.assertIn(b'owned editor error',caught.exception.stderr)
        self.assertLess(time.monotonic()-started,5)
        self.assert_stopped()

    def test_run_keeps_marker_interface_and_owned_roots(self):
        with patch.object(fixture,'NVIM',str(self.editor)):
            fixture.run(self,'-- inert fixture Lua')
        self.assertIn('-- inert fixture Lua',(self.root/'check_editor.lua').read_text())
        self.assert_stopped()


if __name__ == '__main__': unittest.main(verbosity=2)

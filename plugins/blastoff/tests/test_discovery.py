"""Optional discovery failures must not hide locals; all state is disposable."""
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('discovery_core', ROOT/'lib/blastoff.py')
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)

class Terminal(io.StringIO):
    def isatty(self):
        return True

class Discovery(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='blastoff-discovery-')
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.store = self.home/'store'
        self.config = self.home/'active.toml'
        self.config.write_bytes(b'x=1\n')
        (self.store/'themes').mkdir(parents=True)
        (self.store/'themes/local-one.toml').write_bytes(b'x=2\n')
        self.env = dict(os.environ, HOME=str(self.home), USERPROFILE=str(self.home),
                        BLASTOFF_HOME=str(self.store), STARSHIP_CONFIG=str(self.config),
                        STARSHIP_CACHE=str(self.home/'cache'), NO_COLOR='1')
        self.environment = patch.dict(os.environ, self.env)
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def snapshot(self):
        return {str(p.relative_to(self.home)): None if p.is_dir() else p.read_bytes()
                for p in self.home.rglob('*')}

    def invoke(self, args, mode='fail', text='', tty=False):
        out = Terminal() if tty else io.StringIO()
        inp = Terminal(text) if tty else io.StringIO(text)
        err = io.StringIO()
        def process(argv, **kwargs):
            self.assertEqual(argv, ['starship', 'preset', '--list'])
            self.assertEqual(kwargs['timeout'], 10)
            if mode == 'timeout':
                raise subprocess.TimeoutExpired(argv, 10)
            if mode == 'launch':
                raise PermissionError('fixture denied')
            if mode == 'interrupt':
                raise KeyboardInterrupt()
            values = {'fail': (9,b''), 'invalid': (0,b'bad name\n'),
                      'mixed': (0,b'valid\n../bad\n'), 'reserved': (0,b'CON\n'),
                      'utf8': (0,b'\xff'), 'large': (0,b'a'*(core.MAX_FILE+1)),
                      'empty': (0,b' \n\t\n'), 'ok': (0,b'zed\nalpha\nzed\n')}
            code, data = values[mode]
            return subprocess.CompletedProcess(argv, code, data, b'UNTRUSTED STDERR\x1b[31m')
        with patch.object(core.shutil, 'which', side_effect=lambda tool: '/fixture/starship' if tool=='starship' and mode!='missing' else None), \
             patch.object(core.subprocess, 'run', side_effect=process) as run, \
             patch.object(sys, 'argv', ['blastoff', *args]), \
             patch.object(sys, 'stdout', out), patch.object(sys, 'stderr', err), \
             patch.object(sys, 'stdin', inp):
            code = core.main()
        return code, out.getvalue(), err.getvalue(), run.call_count

    failures = ('missing','fail','timeout','launch','invalid','mixed','reserved','utf8','large')

    def test_combined_listing_preserves_local_and_structured_status(self):
        before = self.snapshot()
        for mode in self.failures:
            for args in (['list'], ['theme','list'], ['-l'], ['--list']):
                with self.subTest(mode=mode, args=args):
                    code,out,err,_ = self.invoke(args+['--json'], mode)
                    self.assertEqual(code,0)
                    result = json.loads(out)
                    self.assertEqual(result['themes'], ['local-one'])
                    self.assertEqual(result['presets'], [])
                    self.assertEqual(result['starship_available'], mode!='missing')
                    self.assertEqual(result['preset_discovery']['status'], 'unavailable')
                    self.assertTrue(result['preset_discovery']['error'])
                    self.assertEqual(err,'')
                    code,out,err,_ = self.invoke(args,mode)
                    self.assertEqual(code,0)
                    self.assertIn('local:local-one',out)
                    self.assertIn('(unavailable)',out)
                    self.assertEqual(len(err.splitlines()),1)
                    self.assertIn('warning: presets unavailable:',err)
                    self.assertNotIn('UNTRUSTED',err)
                    self.assertEqual(self.snapshot(),before)

    def test_successful_empty_and_valid_lists(self):
        for mode,expected in [('empty',[]),('ok',['alpha','zed'])]:
            code,out,err,_ = self.invoke(['list','--json'],mode)
            self.assertEqual(code,0)
            result=json.loads(out)
            self.assertEqual(result['presets'],expected)
            self.assertEqual(result['preset_discovery'],{'status':'ok','error':None})
            self.assertEqual(err,'')
            code,out,err,_ = self.invoke(['preset','list','--json'],mode)
            self.assertEqual((code,json.loads(out)['presets'],err),(0,expected,''))
        code,out,err,_=self.invoke(['list'],'empty')
        self.assertIn('(none)',out)
        self.assertEqual(err,'')
        (self.store/'themes/local-one.toml').unlink()
        for mode in ('empty','fail'):
            code,out,err,_=self.invoke(['list','--json'],mode)
            self.assertEqual(code,0)
            self.assertEqual(json.loads(out)['themes'],[])

    def test_explicit_requests_remain_errors(self):
        before=self.snapshot()
        for mode in self.failures:
            for args in (['preset','list'], ['preset','apply','alpha'],
                         ['preset','save','alpha','saved'], ['theme','apply','preset:alpha'],
                         ['theme','copy','preset:alpha','saved'], ['theme','apply','alpha']):
                with self.subTest(mode=mode,args=args):
                    code,out,err,_=self.invoke(args+['--json'],mode)
                    self.assertEqual(code,3)
                    self.assertEqual(out,'')
                    self.assertEqual(json.loads(err)['code'],3)
                    self.assertNotIn('warning',err)
                    self.assertEqual(self.snapshot(),before)
        code,_,err,_=self.invoke(['preset','apply','alpha','--json'],'empty')
        self.assertEqual(code,1)
        self.assertIn('Unknown preset',json.loads(err)['error'])

    def test_picker_local_selection_cancellation_and_empty(self):
        for mode in self.failures:
            with self.subTest(mode=mode):
                before=self.snapshot()
                code,_,err,_=self.invoke(['pick'],mode,'\n',tty=True)
                self.assertEqual(code,130)
                self.assertIn('warning: presets unavailable:',err)
                self.assertEqual(self.snapshot(),before)
                code,_,err,_=self.invoke(['pick'],mode,'1\n',tty=True)
                self.assertEqual(code,0)
                self.assertEqual(self.config.read_bytes(),b'x=2\n')
        (self.store/'themes/local-one.toml').unlink()
        for mode in (*self.failures,'empty'):
            before=self.snapshot()
            code,out,err,calls=self.invoke(['pick'],mode,'1\n',tty=True)
            self.assertEqual(code,1)
            self.assertEqual(out,'')
            self.assertIn('No themes or presets available',err)
            self.assertEqual(calls,0 if mode=='missing' else 1)
            self.assertEqual(self.snapshot(),before)

    def test_interrupt_and_noninteractive_not_downgraded(self):
        before=self.snapshot()
        for args in (['list'],['pick'],['preset','list']):
            code,_,err,_=self.invoke(args,'interrupt',tty=True)
            self.assertEqual(code,130)
            self.assertEqual(err,'')
        for args,tty in [(['pick'],False),(['pick','--json'],True)]:
            code,_,_,calls=self.invoke(args,tty=tty)
            self.assertEqual((code,calls),(2,0))
        self.assertEqual(self.snapshot(),before)

    @unittest.skipUnless(os.name=='posix' and shutil.which('bash'), 'POSIX Bash/PTY required')
    def test_real_process_wrapper_and_tty(self):
        from pty_support import terminal
        bindir=self.home/'bin'; bindir.mkdir()
        fixture=bindir/'starship'
        fixture.write_text('#!'+sys.executable+'\nimport sys\nsys.stderr.write("hidden fixture error")\nsys.exit(9)\n')
        fixture.chmod(0o755)
        env=dict(self.env,PATH=str(bindir),BLASTOFF_PYTHON=sys.executable,TERM='xterm-256color')
        command=[shutil.which('bash'),str(ROOT/'bin/blastoff')]
        before=self.snapshot()
        result=subprocess.run(command+['list','--json'],env=env,capture_output=True,timeout=15)
        self.assertEqual(result.returncode,0)
        self.assertEqual(json.loads(result.stdout)['themes'],['local-one'])
        self.assertEqual(result.stderr,b'')
        code,out=terminal(command+['pick'],env,b'\x03',b'Theme number',columns=40)
        self.assertEqual(code,130,repr(out))
        self.assertEqual(self.snapshot(),before)
        code,out=terminal(command+['pick'],env,b'1\r',b'Theme number',columns=40)
        self.assertEqual(code,0,repr(out))
        self.assertIn(b'warning: presets unavailable:',out)
        self.assertEqual(self.config.read_bytes(),b'x=2\n')

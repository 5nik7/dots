"""Automated native PTY evidence, not a human visual assessment."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from pty_support import terminal

ROOT = Path(__file__).resolve().parent.parent
BASH = shutil.which('bash')
TOOLS = {name: shutil.which(name) for name in ('fzf', 'gum')}

@unittest.skipUnless(os.name == 'posix' and BASH, 'POSIX PTY and Bash required')
class Picker(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='blastoff-picker-')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.config = self.home/'active/starship.toml'
        self.store = self.home/'store'
        self.bin = self.home/'bin'; self.bin.mkdir()
        self.config.parent.mkdir()
        self.config.write_bytes(b'format="$all"\n')
        (self.store/'themes').mkdir(parents=True)
        (self.store/'themes/alpha.toml').write_bytes(b'[directory]\nstyle="purple"\n')
        (self.store/'themes/beta.toml').write_bytes(b'[directory]\nstyle="blue"\n')
        self.env = dict(os.environ, HOME=str(self.home), USERPROFILE=str(self.home),
                        XDG_CONFIG_HOME=str(self.home/'xdg'), XDG_CACHE_HOME=str(self.home/'cache'),
                        STARSHIP_CACHE=str(self.home/'starship-cache'),
                        STARSHIP_CONFIG=str(self.config), BLASTOFF_HOME=str(self.store),
                        BLASTOFF_PYTHON=sys.executable, PATH=str(self.bin), TERM='xterm-256color',
                        NO_COLOR='1', FZF_DEFAULT_OPTS='', FZF_DEFAULT_OPTS_FILE='')
        # No installed Starship is exposed: no cache writes during cancellation.
        self.command = [BASH, str(ROOT/'bin/blastoff'), 'pick']

    def enable(self, backend):
        for p in self.bin.iterdir():
            p.unlink()
        if backend != 'numbered':
            if not TOOLS[backend]:
                self.skipTest(backend+' unavailable')
            (self.bin/backend).symlink_to(TOOLS[backend])

    def snapshot(self):
        return {str(p.relative_to(root)): ('dir' if p.is_dir() else p.read_bytes())
                for root in (self.store, self.config.parent)
                for p in [root, *root.rglob('*')]}

    def pick(self, backend, keys, columns=40, extra=()):
        ready = b'Theme number' if backend == 'numbered' else b'local:alpha'
        return terminal(self.command+list(extra), self.env, keys, ready, columns=columns)

    def test_selection_each_backend_at_narrow_widths(self):
        for backend in ('numbered','fzf','gum'):
            if backend != 'numbered' and not TOOLS[backend]:
                continue
            self.enable(backend)
            for width in (40,50):
                with self.subTest(backend=backend,width=width):
                    self.config.write_bytes(b'format="$all"\n')
                    code, out = self.pick(backend, b'1\r' if backend == 'numbered' else b'\r', width)
                    self.assertEqual(code,0,repr(out[-1500:]))
                    self.assertEqual(self.config.read_bytes(), (self.store/'themes/alpha.toml').read_bytes())

    def test_long_names_keep_selection_identity(self):
        name = 'a'*96
        expected = b'[directory]\nstyle="long-name"\n'
        (self.store/'themes'/(name+'.toml')).write_bytes(expected)
        for backend in ('numbered','fzf','gum'):
            if backend != 'numbered' and not TOOLS[backend]:
                continue
            self.enable(backend)
            for width in (40,50):
                with self.subTest(backend=backend,width=width):
                    self.config.write_bytes(b'format="$all"\n')
                    code,out = self.pick(backend,b'1\r' if backend == 'numbered' else b'\r',width)
                    self.assertEqual(code,0,repr(out[-1500:]))
                    self.assertEqual(self.config.read_bytes(),expected)

    def test_cancel_each_backend_leaves_contents_unchanged(self):
        for backend in ('numbered','fzf','gum'):
            if backend != 'numbered' and not TOOLS[backend]:
                continue
            self.enable(backend)
            keys = [b'\x03', b'\x1b\r'] if backend == 'numbered' else [b'\x03', b'\x1b']
            if backend == 'numbered':
                keys.extend([b'\r', b'\x04'])
            for key in keys:
                with self.subTest(backend=backend,key=repr(key)):
                    before = self.snapshot()
                    code,out = self.pick(backend,key)
                    self.assertEqual(code,130,repr(out[-1500:]))
                    self.assertEqual(self.snapshot(),before)

    def test_numbered_invalid_input(self):
        before = self.snapshot()
        for value in (b'0\r', b'3\r', b'nope\r'):
            code,out = self.pick('numbered',value)
            self.assertEqual(code,2,repr(out[-1500:]))
            self.assertEqual(self.snapshot(),before)

    def test_empty_choices(self):
        for p in (self.store/'themes').iterdir(): p.unlink()
        before = self.snapshot()
        for backend in ('numbered','fzf','gum'):
            if backend != 'numbered' and not TOOLS[backend]:
                continue
            self.enable(backend)
            code,out = terminal(self.command,self.env)
            self.assertEqual(code,1,repr(out))
            self.assertIn(b'No themes or presets',out)
            self.assertEqual(self.snapshot(),before)

    def test_invalid_names_are_not_offered(self):
        for name in ('CON','lpt1','bad space','-option','a'*97):
            (self.store/'themes'/(name+'.toml')).write_text('x=1\n')
        (self.store/'themes/link.toml').symlink_to(self.store/'themes/alpha.toml')
        (self.store/'themes/directory.toml').mkdir()
        p = subprocess.run(self.command[:-1]+['list','--json'],env=self.env,capture_output=True,check=False)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(json.loads(p.stdout)['themes'],['alpha','beta'])

    def test_redirected_streams_and_json_refused(self):
        before = self.snapshot()
        # Each one-sided redirection leaves the other side on a real PTY.
        for suffix in (' </dev/null', ' >"$HOME/output"', ' --json'):
            command = [BASH,'--noprofile','--norc','-c', '"$BLASTOFF_PYTHON" -I "$1" pick'+suffix, 'check',str(ROOT/'lib/blastoff.py')]
            code,out = terminal(command,self.env)
            self.assertEqual(code,2,repr(out))
            self.assertEqual(self.snapshot(),before)
        p = subprocess.run(self.command,env=self.env,capture_output=True,check=False)
        self.assertEqual(p.returncode,2)
        self.assertEqual(self.snapshot(),before)

    def test_fzf_ambient_options_cannot_auto_select(self):
        self.enable('fzf')
        self.env['FZF_DEFAULT_OPTS'] = '--filter=local:alpha'
        options = self.home/'fzf-options'
        options.write_text('--filter=local:alpha\n')
        self.env['FZF_DEFAULT_OPTS_FILE'] = str(options)
        before = self.snapshot()
        code,out = self.pick('fzf',b'\x1b')
        self.assertEqual(code,130,repr(out))
        self.assertEqual(self.snapshot(),before)

    def test_fzf_takes_priority_over_gum(self):
        self.enable('fzf')
        gum = self.bin/'gum'
        gum.write_text('#!'+sys.executable+'\nraise SystemExit(99)\n')
        gum.chmod(0o755)
        code,out = self.pick('fzf',b'\r')
        self.assertEqual(code,0,repr(out))
        self.assertEqual(self.config.read_bytes(),(self.store/'themes/alpha.toml').read_bytes())

    def test_gum_ambient_timeout_cannot_auto_select(self):
        self.enable('gum')
        self.env['GUM_CHOOSE_TIMEOUT'] = '1ms'
        before = self.snapshot()
        code,out = self.pick('gum',b'\x1b')
        self.assertEqual(code,130,repr(out))
        self.assertEqual(self.snapshot(),before)

if __name__ == '__main__':
    unittest.main()

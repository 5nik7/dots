"""Native noninteractive checks. Real Starship is opt-in; all state is temporary."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest

ROOT = Path(__file__).resolve().parent.parent

class Native(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='blastoff-native-')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.store = self.home / 'store space ü'
        self.config = self.home / 'config space ü' / 'starship.toml'
        self.env = dict(os.environ, HOME=str(self.home), USERPROFILE=str(self.home),
                        BLASTOFF_HOME=str(self.store), STARSHIP_CONFIG=str(self.config),
                        XDG_CONFIG_HOME=str(self.home/'xdg'), XDG_CACHE_HOME=str(self.home/'cache'),
                        STARSHIP_CACHE=str(self.home/'starship-cache'),
                        BLASTOFF_PYTHON=sys.executable, NO_COLOR='1', PYTHONPATH='')

    def run_command(self, args, code=0):
        p = subprocess.run(args, env=self.env, capture_output=True, timeout=15)
        self.assertEqual(p.returncode, code, p.stderr.decode(errors='replace'))
        return p

    def cli(self, *args, code=0):
        return self.run_command([sys.executable, '-I', str(ROOT/'lib/blastoff.py'), *args], code)

    @unittest.skipUnless(os.name == 'posix' and shutil.which('bash'), 'Native POSIX Bash required')
    def test_bash_literal_arguments_and_environment(self):
        source = self.home / 'quotes \' " ü $name ; file.toml'
        source.write_text('[directory]\nstyle="purple"\n', encoding='utf-8')
        self.cli('theme', 'import', str(source), 'literal')
        for args in [('theme','import',str(source),'literal','--json'),
                     ('theme','save','','--json'), ('theme','apply','local:missing','--json'),
                     ('doctor','--json'), ('--theme','--json'), ('--help',), ('--version',)]:
            baseline = subprocess.run([sys.executable,'-I',str(ROOT/'lib/blastoff.py'),*args], env=self.env, capture_output=True)
            actual = subprocess.run([shutil.which('bash'),str(ROOT/'bin/blastoff'),*args], env=self.env, capture_output=True)
            self.assertEqual((actual.returncode,actual.stdout,actual.stderr),
                             (baseline.returncode,baseline.stdout,baseline.stderr))
        self.run_command([shutil.which('bash'),str(ROOT/'bin/blastoff'),'theme','apply','literal'])
        self.assertEqual(self.config.read_bytes(), source.read_bytes())
        self.assertFalse((self.home/'.config/starship.toml').exists())

    def test_empty_overrides_and_tilde_paths(self):
        self.env.update(BLASTOFF_HOME='', STARSHIP_CONFIG='')
        p = self.cli('doctor','--json')
        result = json.loads(p.stdout)
        self.assertEqual(result['config'], str(self.home/'.config/starship.toml'))
        self.assertEqual(result['blastoff_home'], str(self.home/'.config/blastoff'))
        self.env.update(BLASTOFF_HOME='~/chosen', STARSHIP_CONFIG='~/config/new.toml')
        result = json.loads(self.cli('doctor','--json').stdout)
        self.assertEqual(result['config'], str(self.home/'config/new.toml'))
        self.assertEqual(result['blastoff_home'], str(self.home/'chosen'))
        self.assertFalse((self.home/'chosen').exists())
        self.env['BLASTOFF_HOME'] = 'relative'
        self.cli('doctor','--json',code=2)

    @unittest.skipUnless(os.name == 'posix' and shutil.which('bash'), 'Native POSIX Bash required')
    def test_bash_completion_without_runtime(self):
        (self.store/'themes').mkdir(parents=True)
        (self.store/'themes/purple.toml').write_text('x=1\n')
        self.env['PATH'] = ''
        script = 'source "$1"; COMP_WORDS=(blastoff theme apply p); COMP_CWORD=3; _blastoff; printf "%s\\n" "${COMPREPLY[@]}"'
        p = self.run_command([shutil.which('bash'),'-c',script,'check',str(ROOT/'completions/blastoff.bash')])
        self.assertEqual(set(p.stdout.splitlines()), {b'purple', b'preset:'})

    @unittest.skipUnless(os.name == 'posix' and shutil.which('zsh'), 'Native POSIX Zsh required')
    def test_zsh_completion_function_without_runtime(self):
        (self.store/'themes').mkdir(parents=True)
        (self.store/'themes/purple.toml').write_text('x=1\n')
        self.env['PATH'] = ''
        # Capture compadd outside ZLE; this verifies dispatch, not interactive matching.
        script = 'compadd() { [[ $1 == -S ]] && shift 2; print -rl -- "${(@P)2}"; }; words=(blastoff theme apply p); CURRENT=4; source "$1"; _blastoff'
        p = self.run_command([shutil.which('zsh'),'-f','-c',script,'check',str(ROOT/'completions/blastoff.zsh')])
        self.assertEqual(set(p.stdout.splitlines()), {b'purple', b'preset:'})

    @unittest.skipUnless(os.name == 'posix' and shutil.which('fish'), 'Native POSIX Fish required')
    def test_fish_completion_noninteractive(self):
        (self.store/'themes').mkdir(parents=True)
        (self.store/'themes/purple.toml').write_text('x=1\n')
        p = self.run_command([shutil.which('fish'),'--no-config','-c',
                              'source $argv[1]; complete -C "blastoff theme apply p"',
                              str(ROOT/'completions/blastoff.fish')])
        self.assertIn(b'purple', p.stdout.splitlines())
        self.assertFalse(self.config.exists())

    @unittest.skipUnless(os.environ.get('BLASTOFF_TEST_STARSHIP') == '1' and shutil.which('starship'),
                         'Set BLASTOFF_TEST_STARSHIP=1 for real sandboxed presets')
    def test_real_starship_presets(self):
        names = self.run_command(['starship','preset','--list']).stdout.decode().split()
        self.assertTrue(names)
        listed = json.loads(self.cli('preset','list','--json').stdout)['presets']
        self.assertEqual(listed, sorted(names))
        self.assertFalse(self.store.exists())
        self.assertFalse(self.config.parent.exists())
        self.config.parent.mkdir(parents=True)
        original = b'format="$all"\n'
        self.config.write_bytes(original)
        for name in names:
            with self.subTest(preset=name):
                expected = self.run_command(['starship','preset',name]).stdout
                tomllib.loads(expected.decode())
                self.cli('preset','save',name,name)
                self.assertEqual((self.store/'themes'/(name+'.toml')).read_bytes(), expected)
                self.cli('preset','apply',name)
                self.assertEqual(self.config.read_bytes(), expected)
        self.assertIn(original, [p.read_bytes() for p in (self.store/'backups').glob('*.toml')])
        before = self.config.read_bytes()
        self.cli('preset','apply','blastoff-nonexistent-preset',code=1)
        self.assertEqual(self.config.read_bytes(), before)
        self.run_command(['starship','preset','blastoff-nonexistent-preset'], code=2)
        # Never render a prompt or execute a config's custom commands.

if __name__ == '__main__':
    unittest.main()

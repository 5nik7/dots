"""Opt-in POSIX rehearsal of a locally built ZIP; never touches a real prefix."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile


@unittest.skipUnless(os.name == 'posix' and os.environ.get('BLASTOFF_TEST_ARCHIVE'),
                     'Set BLASTOFF_TEST_ARCHIVE to a locally built ZIP on POSIX')
class InstalledPackage(unittest.TestCase):
    def test_installed_lifecycle(self):
        with tempfile.TemporaryDirectory(prefix='blastoff-installed-') as tmp:
            root = Path(tmp)
            home = root/'home ü'
            home.mkdir()
            prefix = root/'prefix space ü'
            config = home/'config space/starship.toml'
            store = home/'storage space'
            env = dict(os.environ, HOME=str(home), USERPROFILE=str(home),
                       STARSHIP_CONFIG=str(config), BLASTOFF_HOME=str(store),
                       XDG_CONFIG_HOME=str(home/'xdg'), XDG_CACHE_HOME=str(home/'cache'),
                       STARSHIP_CACHE=str(home/'starship-cache'), NO_COLOR='1',
                       BLASTOFF_PYTHON=sys.executable)

            def run(argv, code=0, environment=None):
                result = subprocess.run([str(a) for a in argv], env=environment or env,
                                        capture_output=True, timeout=30)
                self.assertEqual(result.returncode, code, result.stderr.decode(errors='replace'))
                return result.stdout

            with zipfile.ZipFile(os.environ['BLASTOFF_TEST_ARCHIVE']) as archive:
                for name in archive.namelist():
                    self.assertFalse(Path(name).is_absolute() or '..' in Path(name).parts)
                archive.extractall(root/'source')
            source = root/'source/blastoff-rebuild'
            run([sys.executable, source/'scripts/verify.py', source])
            installer = source/'scripts/install.py'
            run([sys.executable, installer, 'install', '--prefix', prefix, '--dry-run'])
            self.assertFalse(prefix.exists())
            version = (source/'VERSION').read_text().strip()
            # Use an actual historical source when supplied; fallback is explicitly
            # synthetic and only exercises immutable-version mechanics.
            prior = root/'prior source'
            historical = os.environ.get('BLASTOFF_TEST_PRIOR_SOURCE')
            shutil.copytree(historical or source, prior, ignore=shutil.ignore_patterns('__pycache__'))
            prior_version = (prior/'VERSION').read_text().strip() if historical else '0.0.0'
            if not historical:
                (prior/'VERSION').write_text(prior_version+'\n')
                for relative in ('lib/blastoff.py','powershell/blastoff.psd1','man/blastoff.1'):
                    p=prior/relative; p.write_text(p.read_text().replace(version,prior_version))
                run([sys.executable, prior/'scripts/package.py', '--checksums-only'])
            run([sys.executable, prior/'scripts/install.py', 'install', '--prefix', prefix, '--yes'])
            old_core = prefix/'share/blastoff/versions'/prior_version/'lib/blastoff.py'
            old_bytes = old_core.read_bytes()
            run([sys.executable, installer, 'install', '--prefix', prefix, '--yes'])
            self.assertEqual(old_core.read_bytes(), old_bytes)
            payload = prefix/'share/blastoff/versions'/version
            command = prefix/'bin/blastoff'
            self.assertTrue(os.access(command, os.X_OK))
            self.assertEqual(command.read_text().splitlines()[0], '#!'+shutil.which('bash'))
            # Installed command must not depend on the extracted source tree.
            source.rename(root/'unused source')
            self.assertIn(version.encode(), run([command, '--version']))
            default_env = dict(env)
            default_env.pop('BLASTOFF_PYTHON')
            self.assertIn(version.encode(), run([command, '--version'], environment=default_env))
            # Resolve only in this child; do not change the caller's PATH.
            lookup_env = dict(env, PATH=str(prefix/'bin')+os.pathsep+env['PATH'])
            self.assertEqual(run([shutil.which('bash'), '-c', 'command -v blastoff'],
                                 environment=lookup_env).decode().strip(), str(command))
            run([command, '--version'], code=3,
                environment=dict(env, BLASTOFF_PYTHON=str(root/'missing python')))
            doctor = json.loads(run([command, 'doctor', '--json']))
            self.assertEqual(doctor['config'], str(config))
            self.assertEqual(doctor['blastoff_home'], str(store))
            self.assertFalse(config.exists())
            self.assertFalse(store.exists())
            # Exercise the installed runtime with the dotfiles storage layout.
            real_store = home/'dots/config/blastoff'
            real_store.mkdir(parents=True)
            store.symlink_to(real_store, target_is_directory=True)
            linked_doctor = json.loads(run([command, 'doctor', '--json']))
            self.assertEqual(linked_doctor['blastoff_home'], str(real_store))
            self.assertEqual(list(real_store.iterdir()), [])
            config.parent.mkdir(parents=True)
            original = b'[directory]\nstyle="purple"\n'
            config.write_bytes(original)
            # Both fast help and fzf preview helpers resolve from installed
            # siblings after the extracted source tree has been moved away.
            help_text = run([command, '--help'])
            self.assertIn(b'Browse & choose', help_text)
            for args in ([], ['-h'], ['--color', 'never']):
                self.assertEqual(run([command, *args]), help_text)
            artwork = payload/'lib/artwork/logo'
            self.assertEqual(artwork.read_bytes(), (root/'unused source/lib/artwork/logo').read_bytes())
            from pty_support import terminal
            code, screen = terminal([str(command), '-h'], dict(env, COLUMNS='60', TERM='xterm-256color', PYTHONIOENCODING='utf-8'), columns=60, rows=30)
            self.assertEqual(code, 0)
            self.assertIn('⣴⣦⣄'.encode(), screen)
            self.assertNotIn(b'{list,current', screen)
            run([command, 'theme', 'save', 'daily'])
            run([command, 'theme', 'apply', 'daily'])
            self.assertIn(b'local:daily  [current]', run([command, 'list']))
            config.write_bytes(original+b'# edited fixture\n')
            self.assertIn(b'local:daily  [last loaded; modified]', run([command, 'list']))
            config.write_bytes(original)
            session = root/'preview session'; session.mkdir()
            (session/'choices.json').write_text(json.dumps({'choices':['local:daily'],
                'themes':str(store/'themes'), 'color':False, 'starship':None}))
            preview = run([sys.executable, '-I', payload/'lib/preview.py', session, '0'])
            self.assertIn(b'CONFIGURATION PREVIEW', preview)
            self.assertIn(b'purple', preview)
            self.assertEqual(config.read_bytes(), original)
            run([command, 'theme', 'copy', 'daily', 'spare'])
            run([command, 'module', 'save', 'directory', 'directory-style'])
            run([command, 'backup', 'create'])
            backups = sorted((store/'backups').glob('*.json'))
            self.assertTrue(backups)
            backup_id = backups[0].stem
            config.write_bytes(b'[directory]\nstyle="blue"\n')
            run([command, 'theme', 'apply', 'spare'])
            self.assertEqual(config.read_bytes(), original)
            self.assertEqual(run([command,'module','show','directory-style']), original)
            result=json.loads(run([command,'current','--json']))
            self.assertEqual(result['provenance']['origin'],'local:spare')
            snapshot={str(p):p.read_bytes() for p in real_store.rglob('*') if p.is_file()}
            run([command,'backup','delete','--all','--dry-run'])
            self.assertEqual(snapshot,{str(p):p.read_bytes() for p in real_store.rglob('*') if p.is_file()})
            run([command, 'module', 'load', 'directory-style'])
            run([command, 'backup', 'restore', backup_id])
            run([command,'backup','delete',backup_id,'--yes'])
            self.assertFalse((real_store/'backups'/(backup_id+'.json')).exists())
            self.assertEqual(config.read_bytes(), original)

            # The installed runtime discovers the default link without an override
            # and reuses history previously keyed by the repository target.
            default_link = home/'.config/starship.toml'
            default_link.parent.mkdir()
            default_link.symlink_to(config)
            default_env = dict(env); default_env.pop('STARSHIP_CONFIG')
            current = json.loads(run([command,'current','--json'], environment=default_env))
            self.assertEqual(current['config'], str(default_link))
            self.assertEqual(current['resolved_config'], str(config))
            self.assertEqual(current['provenance'], json.loads(run([command,'current','--json']))['provenance'])
            config.write_bytes(b'[directory]\nstyle="blue"\n')
            run([command,'theme','apply','daily'], environment=default_env)
            self.assertTrue(default_link.is_symlink())
            self.assertEqual(config.read_bytes(), original)

            locations = {
                'bash': 'share/bash-completion/completions/blastoff',
                'zsh': 'share/zsh/site-functions/_blastoff',
                'fish': 'share/fish/vendor_completions.d/blastoff.fish',
            }
            scripts = {
                'bash': ['-c', 'source "$1"; COMP_WORDS=(blastoff theme apply da); COMP_CWORD=3; _blastoff; printf "%s\\n" "${COMPREPLY[@]}"', 'check'],
                'zsh': ['-f', '-c', 'compadd() { [[ $1 == -S ]] && shift 2; print -rl -- "${(@P)2}"; }; words=(blastoff theme apply da); CURRENT=4; source "$1"; _blastoff', 'check'],
                'fish': ['--no-config', '--private', '-c', 'source $argv[1]; complete -C "blastoff theme apply da"'],
            }
            for shell, relative in locations.items():
                installed = prefix/relative
                self.assertEqual(installed.read_bytes(), (payload/'completions'/('blastoff.'+shell)).read_bytes())
                self.assertEqual(run([command, 'completion', shell]), installed.read_bytes())
                executable = shutil.which(shell)
                if executable:
                    self.assertIn(b'daily', run([executable, *scripts[shell], installed],
                                                environment=dict(env, PATH='')).splitlines())
                else:
                    print('PENDING installed completion runtime:', shell)
            manual = prefix/'share/man/man1/blastoff.1'
            self.assertEqual(manual.read_bytes(), (payload/'man/blastoff.1').read_bytes())
            if shutil.which('mandoc'):
                self.assertIn(b'blastoff', run([shutil.which('mandoc'), '-Tutf8', manual]).lower())
            else:
                print('PENDING installed man rendering: mandoc unavailable')
            sentinel = prefix/'unowned.txt'
            sentinel.write_bytes(b'keep me')
            manifest = prefix/'share/blastoff/install.json'
            owned = list(json.loads(manifest.read_bytes())['files'])
            def snapshot():
                return {str(p.relative_to(home)): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in home.rglob('*') if p.is_file()}
            before = snapshot()
            installed_installer = payload/'scripts/install.py'
            run([sys.executable, installed_installer, 'uninstall', '--prefix', prefix, '--dry-run'])
            self.assertTrue(command.exists())
            run([sys.executable, installed_installer, 'uninstall', '--prefix', prefix, '--yes'])
            self.assertFalse(manifest.exists())
            self.assertTrue(all(not Path(p).exists() for p in owned))
            self.assertEqual(sentinel.read_bytes(), b'keep me')
            self.assertEqual(snapshot(), before)
            self.assertTrue(store.is_symlink())
            self.assertEqual(store.resolve(), real_store)


if __name__ == '__main__':
    unittest.main()

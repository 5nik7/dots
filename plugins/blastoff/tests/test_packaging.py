"""Bound source inventories; never package ambient repository/runtime files."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('verify', ROOT/'scripts/verify.py')
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)

class Packaging(unittest.TestCase):
    def test_inventory_excludes_runtime_and_ambient_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wanted = ['VERSION','LICENSE','lib/blastoff.py','.pi/settings.json',
                      '.pi/skills/a/SKILL.md','.local/src/original','.local/logo/original.png',
                      'install.sh','uninstall.sh','install.ps1','uninstall.ps1','scripts/build.sh',
                      'scripts/install.py','scripts/integration.py','scripts/install.sh',
                      'scripts/install.ps1','powershell/blastoff.psm1','powershell/blastoff.psd1',
                      'tests/test_powershell_completion.py']
            unwanted = ['.env','.git/config','.pi/tasks/log.json','.pi/sessions/session.json',
                        'lib/__pycache__/blastoff.pyc','lib/stray.pyc','personal.txt',
                        'dist/build.zip','build/generated.py','.local/private/key',
                        '.local/notes.txt']
            for name in wanted + unwanted:
                p = root/name; p.parent.mkdir(parents=True,exist_ok=True); p.write_text('fixture')
            self.assertEqual({p.relative_to(root).as_posix() for p in verify.source_files(root)},set(wanted))

    def test_inventory_refuses_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'lib').mkdir()
            (root/'target').write_text('fixture')
            try:
                (root/'lib/link.py').symlink_to(root/'target')
            except OSError:
                self.skipTest('Symlink creation unavailable')
            with self.assertRaises(ValueError):
                verify.source_files(root)

    def make_manifest(self, root):
        values = {'version': (root/'VERSION').read_text().strip(), 'files': {
            p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in verify.source_files(root)}}
        (root/'CHECKSUMS.json').write_text(json.dumps(values))

    def test_verify_reports_all_differences_without_refresh(self):
        with tempfile.TemporaryDirectory(prefix="blastoff reviewed ' source ") as directory:
            root = Path(directory)
            for name in ('VERSION', 'README.md', 'LICENSE', 'install.sh', 'uninstall.sh'):
                (root/name).write_text('fixture')
            self.make_manifest(root)
            self.assertEqual(verify.verify(root), 5)
            before = (root/'CHECKSUMS.json').read_bytes()
            (root/'README.md').write_text('edited')
            (root/'LICENSE').write_text('edited too')
            (root/'install.sh').unlink()
            (root/'uninstall.sh').unlink()
            (root/'scripts').mkdir()
            (root/'scripts/new.py').write_text('new')
            (root/'scripts/second.py').write_text('new')
            with self.assertRaises(ValueError) as caught:
                verify.verify(root)
            message = str(caught.exception)
            for expected in ('Source file inventory differs', 'Added: "scripts/new.py"',
                             'Added: "scripts/second.py"', 'Missing: "install.sh"',
                             'Missing: "uninstall.sh"', 'Checksum mismatch: README.md',
                             'Checksum mismatch: LICENSE', 'Restore missing',
                             'review unexpected added files', 'reviewing intentional edits',
                             'cd -- ' + shlex.quote(str(root)) + ' && bash scripts/build.sh',
                             'bash install.sh --dry-run'):
                self.assertIn(expected, message)
            self.assertEqual((root/'CHECKSUMS.json').read_bytes(), before)

    def test_all_integrity_failures_offer_safe_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'VERSION').write_text('1')
            for content in (None, 'not json', '[]', '{"version":"1"}'):
                with self.subTest(content=content):
                    manifest = root/'CHECKSUMS.json'
                    if content is not None:
                        manifest.write_text(content)
                    with self.assertRaises(ValueError) as caught:
                        verify.verify(root)
                    self.assertIn('trusted source', str(caught.exception))
                    self.assertIn('bash scripts/build.sh', str(caught.exception))
            self.make_manifest(root)
            (root/'VERSION').write_text('2')
            with self.assertRaises(ValueError) as caught:
                verify.verify(root)
            self.assertIn('version differs', str(caught.exception))
            self.assertIn('Checksum mismatch: VERSION', str(caught.exception))
            self.assertIn('bash scripts/build.sh', str(caught.exception))

    def test_verify_hash_only_and_unsafe_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'VERSION').write_text('1')
            (root/'README.md').write_text('original')
            self.make_manifest(root)
            (root/'README.md').write_text('changed')
            with self.assertRaisesRegex(ValueError, 'Checksum mismatch: README.md'):
                verify.verify(root)
            values = json.loads((root/'CHECKSUMS.json').read_text())
            values['files']['../outside'] = 'unused'
            (root/'CHECKSUMS.json').write_text(json.dumps(values))
            with self.assertRaisesRegex(ValueError, 'Unsafe checksum path'):
                verify.verify(root)

    def test_archive_includes_wrappers_with_executable_modes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)/'source'
            root.mkdir()
            for name in ('scripts/package.py', 'scripts/verify.py', 'scripts/build.sh',
                         'scripts/install.sh', 'install.sh', 'uninstall.sh', 'bin/blastoff',
                         'install.ps1','uninstall.ps1','powershell/runtime.ps1',
                         'scripts/powershell_install.py','scripts/powershell_lifecycle.ps1',
                         'lib/argv_transport.py','lib/completion_names.py',
                         'lib/host_platform.py','scripts/lifecycle.sh'):
                target = root/name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT/name, target)
            (root/'VERSION').write_text('1.2.3')
            (root/'lib').mkdir(exist_ok=True)
            (root/'lib/blastoff.py').write_text("VERSION = '1.2.3'\n")
            (root/'powershell').mkdir(exist_ok=True); (root/'man').mkdir()
            (root/'powershell/blastoff.psd1').write_text("@{ModuleVersion = '1.2.3'}\n")
            (root/'man/blastoff.1').write_text('.TH BLASTOFF 1 "date" "blastoff 1.2.3"\n')
            for name in ('.env', '.pi/tasks/private.json', 'dist/private.zip',
                         'lib/__pycache__/private.pyc', '.local/private/key'):
                target = root/name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('private')
            result = subprocess.run([sys.executable, '-B', str(root/'scripts/package.py'),
                                     '--output-dir', str(Path(directory)/'out')],
                                    capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(verify.verify(root), 20)
            wanted = {p.relative_to(root).as_posix() for p in verify.source_files(root)} | {'CHECKSUMS.json'}
            executable = {'install.sh', 'uninstall.sh', 'scripts/build.sh',
                          'scripts/install.sh', 'bin/blastoff'}
            with zipfile.ZipFile(Path(directory)/'out/blastoff-rebuild-1.2.3.zip') as archive:
                self.assertEqual({n.removeprefix('blastoff-rebuild/') for n in archive.namelist()}, wanted)
                for item in archive.infolist():
                    name = item.filename.removeprefix('blastoff-rebuild/')
                    self.assertEqual((item.external_attr >> 16) & 0o777, 0o755 if name in executable else 0o644)
            with tarfile.open(Path(directory)/'out/blastoff-rebuild-1.2.3.tar.gz') as archive:
                self.assertEqual({n.removeprefix('blastoff-rebuild/') for n in archive.getnames()}, wanted)
                for item in archive.getmembers():
                    name = item.name.removeprefix('blastoff-rebuild/')
                    self.assertEqual(item.mode, 0o755 if name in executable else 0o644)

    @unittest.skipUnless(os.name == 'posix' and shutil.which('bash'), 'Requires native Bash')
    def test_wrappers_forward_isolated_argv_streams_and_status(self):
        with tempfile.TemporaryDirectory(prefix="blastoff wrapper ' ") as directory:
            root = Path(directory)
            (root/'scripts').mkdir()
            shutil.copyfile(ROOT/'scripts/lifecycle.sh', root/'scripts/lifecycle.sh')
            fixture = ("import json, sys\n"
                       "print(json.dumps([sys.flags.isolated, sys.argv[1:], sys.stdin.read()]))\n"
                       "print('fixture stderr', file=sys.stderr)\n"
                       "raise SystemExit(17)\n")
            (root/'scripts/install.py').write_text(fixture)
            (root/'scripts/package.py').write_text(fixture)
            for wrapper, leading in (('install.sh', ['install', '--public']),
                                     ('uninstall.sh', ['uninstall', '--public']),
                                     ('scripts/build.sh', [])):
                shutil.copyfile(ROOT/wrapper, root/wrapper)
                for runtime in (sys.executable, '', None):
                    env = dict(os.environ)
                    env.pop('BLASTOFF_PYTHON', None)
                    if runtime is not None:
                        env['BLASTOFF_PYTHON'] = runtime
                    args = ['', 'space name', "quote'\"", '雪', '--dry-run']
                    result = subprocess.run([shutil.which('bash'), str(root/wrapper), *args],
                                            cwd=root/'scripts', env=env, input='input bytes',
                                            capture_output=True, text=True, check=False)
                    self.assertEqual(result.returncode, 17, result.stderr)
                    forwarded = json.loads(result.stdout)
                    if wrapper != 'scripts/build.sh':
                        self.assertEqual(forwarded[1][0], '--_bash-host-v1')
                        self.assertTrue(forwarded[1][1])
                        forwarded[1] = forwarded[1][2:]
                    self.assertEqual(forwarded, [1, leading + args, 'input bytes'])
                    self.assertEqual(result.stderr, 'fixture stderr\n')
                env['BLASTOFF_PYTHON'] = str(root/'missing python')
                result = subprocess.run([shutil.which('bash'), str(root/wrapper)],
                                        env=env, capture_output=True, text=True, check=False)
                self.assertEqual(result.returncode, 3)
                self.assertEqual(result.stdout, '')
                self.assertIn('install Python 3.11+ or set BLASTOFF_PYTHON', result.stderr)

if __name__ == '__main__':
    unittest.main()

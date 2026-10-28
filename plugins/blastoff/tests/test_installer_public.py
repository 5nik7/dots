"""Public lifecycle contract: disposable sources, homes and installation prefixes.

These tests never refresh the checkout's manifest, source a real profile, invoke
Starship, or put the ambient PATH (and its installed Blastoff) in a child.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which('bash')


@unittest.skipUnless(os.name == 'posix' and BASH, 'Public Bash lifecycle requires POSIX and Bash')
class PublicInstaller(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='blastoff-public-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root/'source'
        self.home = self.root/'home'
        self.home.mkdir()
        self.prefix = self.root/'target space ü'
        self.toolbin = self.root/'tools'
        self.toolbin.mkdir()
        # Expose only deliberately selected tools, never the real blastoff,
        # starship, picker tools, or unrelated commands from the caller's PATH.
        for name in ('bash', 'sh', 'zsh', 'fish', 'man', 'mandoc', 'groff'):
            executable = shutil.which(name)
            if executable:
                (self.toolbin/name).symlink_to(executable)
        for name in ('python', 'python3'):
            (self.toolbin/name).symlink_to(sys.executable)
        self.env = dict(os.environ)
        for name in list(self.env):
            if (name in {'BASH_ENV', 'ENV', 'SHELLOPTS', 'BASHOPTS', 'CDPATH',
                         'PROMPT_COMMAND', 'PYTHONPATH', 'PYTHONHOME', 'MANPATH',
                         'PSModulePath', 'STARSHIP_THEMES'}
                    or name.startswith(('BASH_FUNC_', 'BLASTOFF_', 'FZF_', 'GUM_'))):
                self.env.pop(name)
        self.env.update(
            HOME=str(self.home), USERPROFILE=str(self.home),
            XDG_CONFIG_HOME=str(self.home/'xdg-config'),
            XDG_DATA_HOME=str(self.home/'xdg-data'),
            XDG_CACHE_HOME=str(self.home/'xdg-cache'),
            XDG_STATE_HOME=str(self.home/'xdg-state'),
            STARSHIP_CONFIG=str(self.home/'config/starship.toml'),
            STARSHIP_CACHE=str(self.home/'starship-cache'),
            BLASTOFF_HOME=str(self.home/'blastoff-data'),
            ZDOTDIR=str(self.home/'zsh'),
            BLASTOFF_PYTHON=sys.executable, PYTHONDONTWRITEBYTECODE='1',
            PATH=os.pathsep.join((str(self.toolbin), str(self.prefix/'bin'))),
            SHELL=str(self.toolbin/'bash'), NO_COLOR='1', TERM='xterm-256color',
        )
        # Execute only the inventory definition, without an import that could
        # create __pycache__ in the real checkout. This shares the release boundary
        # and intentionally cannot capture .pi/tasks or arbitrary checkout logs.
        verifier = ROOT/'scripts/verify.py'
        namespace = {'__file__': str(verifier), '__name__': 'test_source_inventory'}
        exec(compile(verifier.read_bytes(), str(verifier), 'exec'), namespace)
        for original in namespace['source_files'](ROOT):
            destination = self.source/original.relative_to(ROOT)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original, destination)
        shutil.copy2(ROOT/'CHECKSUMS.json', self.source/'CHECKSUMS.json')
        self.version = (self.source/'VERSION').read_text().strip()
        self.rebuild_checksums()

    def run_command(self, argv, *, ok=True, env=None):
        result = subprocess.run(
            [str(value) for value in argv], cwd=self.root,
            env=self.env if env is None else env, stdin=subprocess.DEVNULL,
            capture_output=True, timeout=30, check=False,
        )
        message = (f'{argv!r}\nexit={result.returncode}\n'
                   + result.stdout.decode(errors='replace')
                   + result.stderr.decode(errors='replace'))
        if ok:
            self.assertEqual(result.returncode, 0, message)
        else:
            self.assertNotEqual(result.returncode, 0, message)
            self.assertNotIn(b'Traceback', result.stderr, message)
        return result

    def rebuild_checksums(self):
        return self.run_command([
            sys.executable, '-B', self.source/'scripts/package.py', '--checksums-only',
        ])

    def public(self, action, *arguments, ok=True, env=None):
        return self.run_command(
            [BASH, self.source/(action+'.sh'), '--prefix', self.prefix, *arguments],
            ok=ok, env=env,
        )

    def snapshot(self, *roots, times=False):
        """Record only requested fixture roots; never chase symlink targets."""
        result = {}

        def visit(path):
            if path.name == '__pycache__' or path.suffix in {'.pyc', '.pyo'}:
                return
            if not os.path.lexists(path):
                result[str(path)] = ('absent',)
                return
            info = path.lstat()
            mode = stat.S_IMODE(info.st_mode)
            if stat.S_ISLNK(info.st_mode):
                value = ('link', mode, os.readlink(path))
            elif stat.S_ISDIR(info.st_mode):
                value = ('directory', mode)
                for child in sorted(path.iterdir()):
                    visit(child)
            else:
                value = ('file', mode, hashlib.sha256(path.read_bytes()).hexdigest())
            result[str(path)] = value + ((info.st_mtime_ns,) if times else ())

        for root in roots:
            visit(Path(root))
        return result

    def unchanged_failure(self, *arguments):
        before = self.snapshot(self.home, self.prefix, times=True)
        result = self.public('install', *arguments, ok=False)
        self.assertEqual(self.snapshot(self.home, self.prefix, times=True), before)
        return result

    def legacy_install(self):
        legacy = self.home/'.local'
        self.run_command([
            sys.executable, '-B', self.source/'scripts/install.py', 'install',
            '--prefix', legacy, '--yes',
        ])
        manifest = legacy/'share/blastoff/install.json'
        # Model the real pre-integration ownership format, not the new writer.
        current = json.loads(manifest.read_bytes())
        manifest.write_text(json.dumps({'format': 1, 'version': current['version'], 'files': current['files']}))
        self.assertFalse((self.home/'.bashrc').exists(), 'Legacy mode must remain manual')
        return legacy

    def test_wrapper_help_and_version_are_read_only(self):
        before = self.snapshot(self.home, self.prefix, self.source, times=True)
        for action in ('install', 'uninstall'):
            with self.subTest(action=action):
                help_result = self.public(action, '--help')
                self.assertIn(b'--prefix', help_result.stdout)
                self.assertIn(b'--dry-run', help_result.stdout)
                result = self.public(action, '--version')
                self.assertIn(self.version.encode(), result.stdout)
        self.assertEqual(self.snapshot(self.home, self.prefix, self.source, times=True), before)

    def test_dry_run_labels_color_and_no_writes(self):
        before = self.snapshot(self.home, self.prefix, self.source, times=True)
        for no_color in (False, True):
            env = dict(self.env)
            if not no_color:
                env.pop('NO_COLOR')
            for action in ('install', 'uninstall'):
                with self.subTest(action=action, no_color=no_color):
                    result = self.public(action, '--dry-run', env=env)
                    for label in ('VERSION', 'PREFIX', 'CURRENT', 'PLAN', 'DONE'):
                        self.assertRegex(result.stdout.decode(), r'\b'+label+r'\b')
                    self.assertNotIn(b'\x1b', result.stdout + result.stderr)
                    self.assertIn(str(self.prefix).encode(), result.stdout)
        self.assertEqual(self.snapshot(self.home, self.prefix, self.source, times=True), before)

    def test_payload_runs_without_source(self):
        self.public('install')
        payload = self.prefix/'share/blastoff/versions'/self.version
        for relative in ('lib/blastoff.py', 'lib/cli.py', 'lib/preview.py',
                         'lib/artwork/blastoff-compact.txt',
                         'powershell/blastoff.psd1', 'scripts/install.py'):
            with self.subTest(relative=relative):
                self.assertEqual((payload/relative).read_bytes(), (self.source/relative).read_bytes())
        self.source.rename(self.root/'source unavailable')
        command = self.prefix/'bin/blastoff'
        self.assertTrue(os.access(command, os.X_OK))
        self.assertIn(self.version.encode(), self.run_command([command, '--version']).stdout)
        self.assertIn(b'BLASTOFF', self.run_command([command, '--help']).stdout.upper())
        lookup = self.run_command([BASH, '--noprofile', '--norc', '-c', 'command -v blastoff'])
        self.assertEqual(lookup.stdout.decode().strip(), str(command))
        doctor = json.loads(self.run_command([command, 'doctor', '--json']).stdout)
        self.assertEqual(doctor['config'], self.env['STARSHIP_CONFIG'])
        self.assertEqual(doctor['blastoff_home'], self.env['BLASTOFF_HOME'])
        self.assertFalse(Path(self.env['STARSHIP_CONFIG']).exists())
        self.assertFalse(Path(self.env['BLASTOFF_HOME']).exists())

    def test_fresh_shell_command_completion_and_manual_discovery(self):
        self.public('install')
        command = str(self.prefix/'bin/blastoff').encode()
        bash = self.run_command([BASH, '--noprofile', '-ic',
                                 'command -v blastoff; blastoff --version; complete -p blastoff'])
        self.assertIn(command, bash.stdout)
        self.assertIn(self.version.encode(), bash.stdout)
        self.assertIn(b'-F _blastoff blastoff', bash.stdout)
        zsh = self.toolbin/'zsh'
        if zsh.exists():
            result = self.run_command([zsh, '-ic',
                                      'whence -p blastoff; blastoff --version; print -r -- $_comps[blastoff]'])
            self.assertIn(command, result.stdout)
            self.assertIn(self.version.encode(), result.stdout)
            self.assertIn(b'_blastoff', result.stdout)
        fish = self.toolbin/'fish'
        if fish.exists():
            result = self.run_command([fish, '--private', '-c',
                                      'type -p blastoff; blastoff --version; complete -C "blastoff theme a"'])
            self.assertIn(command, result.stdout)
            self.assertIn(self.version.encode(), result.stdout)
            self.assertIn(b'apply', result.stdout)
        if (self.toolbin/'man').exists():
            # First verify the managed search list. Then omit its trailing
            # default-path expansion for this isolated lookup: mandoc can prefer
            # an ambient indexed page over an unindexed temporary-prefix page.
            result = self.run_command([BASH, '--noprofile', '-ic',
                                      'printf "%s\\n" "$MANPATH"; MANPATH="${MANPATH%:}" man -w blastoff'])
            self.assertEqual(result.stdout.splitlines()[0],
                             (str(self.prefix/'share/man') + ':').encode())
            self.assertIn(str(self.prefix/'share/man/man1/blastoff.1').encode(), result.stdout)

    def test_repeat_is_idempotent_and_missing_support_is_recreated(self):
        self.public('install')
        before = self.snapshot(self.home, self.prefix)
        self.public('install')
        self.assertEqual(self.snapshot(self.home, self.prefix), before)
        support = self.prefix/'share/bash-completion/completions/blastoff'
        expected = support.read_bytes()
        support.unlink()
        self.public('install')
        self.assertEqual(support.read_bytes(), expected)
        self.assertEqual(self.snapshot(self.home, self.prefix), before)

    def test_uninstall_retains_user_data_and_unrelated_files(self):
        data = {
            Path(self.env['STARSHIP_CONFIG']): b'[directory]\nstyle="purple"\n',
            Path(self.env['BLASTOFF_HOME'])/'themes/keep.toml': b'# theme\n',
            Path(self.env['BLASTOFF_HOME'])/'modules/keep.toml': b'# module\n',
            Path(self.env['BLASTOFF_HOME'])/'backups/keep.toml': b'# backup\n',
            Path(self.env['BLASTOFF_HOME'])/'backups/keep.json': b'{}\n',
            self.prefix/'unrelated.txt': b'not installer owned\n',
        }
        for path, content in data.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        self.public('install')
        before = self.snapshot(self.home, self.prefix, times=True)
        self.public('uninstall', '--dry-run')
        self.assertEqual(self.snapshot(self.home, self.prefix, times=True), before)
        self.public('uninstall')
        for path, content in data.items():
            self.assertEqual(path.read_bytes(), content)
        self.assertFalse((self.prefix/'bin/blastoff').exists())
        self.assertFalse((self.prefix/'share/blastoff/install.json').exists())
        before = self.snapshot(self.home, self.prefix, times=True)
        self.public('uninstall')
        self.assertEqual(self.snapshot(self.home, self.prefix, times=True), before)

    def test_absent_uninstall_is_read_only_success(self):
        before = self.snapshot(self.home, self.prefix, times=True)
        self.public('uninstall')
        self.assertEqual(self.snapshot(self.home, self.prefix, times=True), before)

    def test_legacy_format_one_migrates_to_public_prefix(self):
        legacy = self.legacy_install()
        self.assertNotEqual(legacy, self.prefix)
        sentinel = legacy/'unrelated.txt'
        sentinel.write_bytes(b'preserve old-prefix data\n')
        self.public('install')
        self.assertFalse((legacy/'bin/blastoff').exists())
        self.assertEqual(sentinel.read_bytes(), b'preserve old-prefix data\n')
        result = self.run_command([self.prefix/'bin/blastoff', '--version'])
        self.assertIn(self.version.encode(), result.stdout)

    def test_modified_legacy_owned_file_blocks_before_writes(self):
        legacy = self.legacy_install()
        launcher = legacy/'bin/blastoff'
        launcher.write_bytes(launcher.read_bytes() + b'\n# user edit\n')
        self.unchanged_failure()

    def test_unowned_destination_blocks_before_writes(self):
        collision = self.prefix/'share/man/man1/blastoff.1'
        collision.parent.mkdir(parents=True)
        collision.write_bytes(b'unowned manual\n')
        self.unchanged_failure()

    def test_linked_profile_is_not_followed_or_replaced(self):
        target = self.home/'custom-bashrc'
        target.write_bytes(b'# custom shell integration\nexport MY_SETTING=keep\n')
        (self.home/'.bashrc').symlink_to(target)
        self.unchanged_failure()
        self.assertTrue((self.home/'.bashrc').is_symlink())
        self.assertEqual(os.readlink(self.home/'.bashrc'), str(target))

    def test_unrelated_profile_text_survives_install_and_uninstall(self):
        profile = self.home/'.bashrc'
        original = b'# unrelated setup\nexport MY_SETTING="keep me"\n'
        profile.write_bytes(original)
        self.public('install')
        self.assertIn(original, profile.read_bytes())
        self.assertNotEqual(profile.read_bytes(), original, 'Public install should integrate Bash')
        later = b'\n# added by the user after installation\n'
        profile.write_bytes(profile.read_bytes() + later)
        self.public('uninstall')
        self.assertEqual(profile.read_bytes(), original + later)

    def test_checksum_failure_names_recovery_helper(self):
        edited = self.source/'lib/cli.py'
        edited.write_bytes(edited.read_bytes() + b'\n# intentional fixture edit\n')
        result = self.unchanged_failure()
        self.assertIn(b'checksum', (result.stdout + result.stderr).lower())
        self.assertIn(b'build.sh', result.stdout + result.stderr)
        self.assertIn(b'--dry-run', result.stdout + result.stderr)
        self.rebuild_checksums()
        self.public('install')

    def test_changed_same_version_source_is_immutable(self):
        self.public('install')
        edited = self.source/'lib/cli.py'
        edited.write_bytes(edited.read_bytes() + b'\n# different same-version payload\n')
        self.rebuild_checksums()
        result = self.unchanged_failure()
        self.assertIn(b'immutable', (result.stdout + result.stderr).lower())


if __name__ == '__main__':
    unittest.main()

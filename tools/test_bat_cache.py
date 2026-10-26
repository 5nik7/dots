#!/usr/bin/env python3
"""Custom Bat assets and both publishers, always in test-owned roots."""
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import test_themes as fixture

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib/dots/themes'))
import bat_cache
from palette_native import Themes

BAT = shutil.which('bat')
SYNTAX = b'''%YAML 1.2
---
name: Fixture One
scope: source.fixture-one
file_extensions: [fixture-one]
contexts:
  main:
    - match: 'HELLO'
      scope: keyword.control.fixture-one
'''


@unittest.skipUnless(BAT, 'Bat unavailable')
class Inputs(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='dots bat inputs ü ')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.home = self.root / 'home'; self.home.mkdir()
        self.source = self.root / '- custom bat ü'
        (self.source / 'syntaxes/nested').mkdir(parents=True)
        self.syntax = self.source / 'syntaxes/nested/fixture.sublime-syntax'
        self.syntax.write_bytes(SYNTAX)
        self.env = dict(HOME=str(self.home), USERPROFILE=str(self.home), PATH=os.environ['PATH'],
                        BAT_CONFIG_DIR=str(self.source), BAT_CONFIG_PATH=str(self.home / 'elsewhere/bat.conf'),
                        BAT_CACHE_PATH=str(self.home / 'normal-cache'), BAT_THEME='missing')
        for kind in ('CONFIG', 'CACHE', 'STATE', 'DATA'):
            self.env['XDG_' + kind + '_HOME'] = str(self.home / kind.lower())
        for key in ('LD_PRELOAD', 'PREFIX'):
            if key in os.environ: self.env[key] = os.environ[key]
        env_patch = patch.dict(os.environ, self.env, clear=True)
        env_patch.start(); self.addCleanup(env_patch.stop)

    def render(self, name='generation'):
        out = self.root / name; out.mkdir()
        (out / 'bat.tmTheme').write_bytes(plistlib.dumps(dict(name='Dots', settings=[
            dict(settings=dict(foreground='#ffffff', background='#000000')),
            dict(scope='keyword', settings=dict(foreground='#ff0000'))])))
        return out

    def languages(self, out):
        env = dict(self.env, BAT_CONFIG_PATH=os.devnull, BAT_THEME='Dots', BAT_CACHE_PATH=str(out / 'bat-cache'))
        return subprocess.run([BAT, '--list-languages', '--color=never'], env=env, cwd=self.home,
                              capture_output=True, text=True, check=True).stdout

    def test_real_cache_snapshot_config_override_and_builtins(self):
        snapshot = bat_cache.inputs()
        self.assertEqual(snapshot.source, str(self.source))
        self.assertEqual(snapshot.files, (('nested/fixture.sublime-syntax', SYNTAX),))
        out = self.render()
        self.syntax.write_bytes(SYNTAX.replace(b'One', b'Two'))
        self.assertTrue(bat_cache.build(out, snapshot))
        self.assertEqual((out / 'bat-source/syntaxes/nested/fixture.sublime-syntax').read_bytes(), SYNTAX)
        languages = self.languages(out)
        self.assertIn('Fixture One:', languages)
        self.assertIn('Python:', languages)
        self.assertFalse((self.home / 'normal-cache').exists())
        self.assertFalse((out / 'bat-source/syntaxes/nested/fixture.sublime-syntax').is_symlink())

    def test_gcode_and_dots_render_together(self):
        shutil.copy2(ROOT / 'config/bat/syntaxes/gcode.sublime-syntax', self.source / 'syntaxes/gcode.sublime-syntax')
        out = self.render(); bat_cache.build(out)
        self.assertIn('gcode:', self.languages(out))
        env = dict(self.env, BAT_CONFIG_PATH=os.devnull, BAT_THEME='Dots', BAT_CACHE_PATH=str(out / 'bat-cache'))
        result = subprocess.run([BAT, '--theme=Dots', '--language=gcode', '--color=always', '--paging=never', '--style=plain'],
                                input='G1 X10 Y20 ; move\n', env=env, cwd=self.home, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('\x1b[', result.stdout)
        themes = subprocess.run([BAT, '--list-themes', '--color=never'], env=env, cwd=self.home,
                                capture_output=True, text=True, check=True).stdout
        self.assertIn('Dots', themes.splitlines())

    def test_content_add_delete_source_and_compiler_invalidate(self):
        original = bat_cache.inputs().fingerprint()
        info = self.syntax.stat()
        self.syntax.write_bytes(SYNTAX.replace(b'One', b'Two'))
        os.utime(self.syntax, ns=(info.st_atime_ns, info.st_mtime_ns))
        self.assertNotEqual(bat_cache.inputs().fingerprint(), original)
        self.syntax.write_bytes(SYNTAX)
        self.assertEqual(bat_cache.inputs().fingerprint(), original)
        extra = self.source / 'syntaxes/extra.sublime-syntax'; extra.write_bytes(SYNTAX)
        self.assertNotEqual(bat_cache.inputs().fingerprint(), original)
        extra.unlink(); self.assertEqual(bat_cache.inputs().fingerprint(), original)
        other = self.root / 'other source'; shutil.copytree(self.source, other)
        with patch.dict(os.environ, BAT_CONFIG_DIR=str(other)):
            self.assertNotEqual(bat_cache.inputs().fingerprint(), original)
        run = bat_cache.subprocess.run
        def newer(args, **kwargs):
            result = run(args, **kwargs)
            if args[-1] == '--version': result.stdout += b' changed compiler'
            return result
        with patch.object(bat_cache.subprocess, 'run', side_effect=newer):
            self.assertNotEqual(bat_cache.inputs().fingerprint(), original)

    @unittest.skipIf(os.name == 'nt', 'Native Windows link permissions require separate acceptance')
    def test_linked_sources_snapshot_and_cycles(self):
        source_link = self.root / 'linked config'; source_link.symlink_to(self.source, target_is_directory=True)
        (self.source / 'syntaxes/linked.sublime-syntax').symlink_to(self.syntax)
        package = self.root / 'package'; package.mkdir()
        (package / 'other.sublime-syntax').write_bytes(SYNTAX)
        (self.source / 'syntaxes/package').symlink_to(package, target_is_directory=True)
        with patch.dict(os.environ, BAT_CONFIG_DIR=str(source_link)):
            snapshot = bat_cache.inputs()
        self.assertEqual(len(snapshot.files), 3)
        (package / 'loop').symlink_to(self.source / 'syntaxes', target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Cycle'): bat_cache.inputs()
        (package / 'loop').unlink()
        (package / 'broken.sublime-syntax').symlink_to(package / 'absent')
        with self.assertRaises(OSError): bat_cache.inputs()

    def test_missing_syntaxes_and_optional_bat(self):
        shutil.rmtree(self.source / 'syntaxes')
        self.assertEqual(bat_cache.inputs().files, ())
        out = self.render(); self.assertTrue(bat_cache.build(out))
        self.assertIn('Python:', self.languages(out))
        with patch.object(bat_cache.shutil, 'which', return_value=None), patch.object(bat_cache.subprocess, 'run') as run:
            self.assertIsNone(bat_cache.inputs().executable)
            self.assertFalse(bat_cache.build(self.root / 'no-bat-output'))
            run.assert_not_called()
        self.assertFalse((self.root / 'no-bat-output').exists())

    @unittest.skipIf(os.name == 'nt', 'POSIX XDG default; native Windows uses Bat known folders')
    def test_default_config_directory(self):
        destination = self.home / 'config/bat'; destination.parent.mkdir()
        destination.symlink_to(self.source, target_is_directory=True)
        del os.environ['BAT_CONFIG_DIR']
        self.assertEqual(bat_cache.inputs().resolved_source, str(self.source))

    def test_invalid_source_and_prebuild_drift_refused(self):
        expected = bat_cache.inputs().fingerprint()
        self.syntax.write_bytes(b'contexts: [invalid\n')
        out = self.render()
        with self.assertRaisesRegex(ValueError, 'changed'): bat_cache.build(out, expected=expected)
        self.assertFalse((out / 'bat-source').exists())
        with self.assertRaisesRegex(ValueError, 'cache build failed'): bat_cache.build(out)

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'FIFO unavailable')
    def test_nonregular_and_oversized_syntax_refused(self):
        self.syntax.unlink(); os.mkfifo(self.syntax)
        with self.assertRaisesRegex(ValueError, 'regular file'): bat_cache.inputs()
        self.syntax.unlink(); self.syntax.write_bytes(b'x' * (bat_cache.FILE_LIMIT + 1))
        with self.assertRaisesRegex(ValueError, '2 MiB'): bat_cache.inputs()


@unittest.skipUnless(fixture.BASH and os.name != 'nt', 'POSIX publisher fixtures; native Windows requires separate acceptance')
class Publication(fixture.Themes):
    def setUp(self):
        super().setUp()
        if not BAT: self.skipTest('Bat unavailable')
        self.source = self.home / 'custom bat ü'
        (self.source / 'syntaxes').mkdir(parents=True)
        self.syntax = self.source / 'syntaxes/fixture.sublime-syntax'
        self.syntax.write_bytes(SYNTAX)
        self.env.update(BAT_CONFIG_DIR=str(self.source), BAT_CONFIG_PATH=os.devnull, DOTS_PROGRESS='never')

    def publish(self, native, *args, code=0):
        if native:
            return self.run_command([sys.executable, '-B', str(self.repo / 'lib/dots/cli.py'), 'theme', *args], code=code)
        return self.dots('theme', *args, code=code)

    def exercise(self, native):
        self.publish(native, 'set', 'nord'); first = self.generation()
        self.assertEqual((first / 'bat-source/syntaxes/fixture.sublime-syntax').read_bytes(), SYNTAX)
        self.publish(native, 'refresh'); self.assertEqual(self.generation(), first)
        info = self.syntax.stat()
        self.syntax.write_bytes(SYNTAX.replace(b'One', b'Two'))
        os.utime(self.syntax, ns=(info.st_atime_ns, info.st_mtime_ns))
        self.publish(native, 'refresh'); second = self.generation()
        self.assertNotEqual(first, second)
        self.assertEqual((first / 'bat-source/syntaxes/fixture.sublime-syntax').read_bytes(), SYNTAX)
        self.syntax.unlink()
        self.publish(native, 'refresh'); third = self.generation()
        self.assertNotEqual(second, third)
        self.assertFalse((third / 'bat-source/syntaxes/fixture.sublime-syntax').exists())
        self.syntax.write_bytes(SYNTAX)
        self.publish(native, 'refresh'); fourth = self.generation()
        self.assertNotEqual(third, fourth)
        self.syntax.write_bytes(b'contexts: [invalid\n')
        self.assertNotEqual(self.publish(native, 'refresh', code=None).returncode, 0)
        self.assertEqual(self.generation(), fourth)

    def test_bash_refresh_and_failure_keep_previous_generation(self):
        self.exercise(False)

    def test_native_refresh_and_failure_keep_previous_generation(self):
        self.exercise(True)

    def drift(self, native):
        wrapper = self.repo / 'bin/bat'
        wrapper.write_text('#!' + sys.executable + '\nimport os, subprocess, sys\n'
                           'result = subprocess.run([' + repr(BAT) + ', *sys.argv[1:]])\n'
                           'if sys.argv[1:2] == ["cache"] and os.environ.get("BAT_FIXTURE_DRIFT"):\n'
                           '    with open(os.environ["BAT_FIXTURE_DRIFT"], "ab") as out: out.write(b"\\n# concurrent edit\\n")\n'
                           'sys.exit(result.returncode)\n')
        wrapper.chmod(0o700)
        self.publish(native, 'set', 'nord'); first = self.generation()
        self.syntax.write_bytes(SYNTAX.replace(b'One', b'Two'))
        self.env['BAT_FIXTURE_DRIFT'] = str(self.syntax)
        result = self.publish(native, 'refresh', code=None)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('inputs changed', result.stderr)
        self.assertEqual(self.generation(), first)

    def test_bash_drift_during_build_retains_active_generation(self):
        self.drift(False)

    def test_native_drift_during_build_retains_active_generation(self):
        self.drift(True)

    def test_inactive_setup_includes_custom_syntaxes(self):
        for command in ([fixture.BASH, str(self.lib / 'setup.bash')],
                        [sys.executable, '-B', str(self.lib / 'setup.py')]):
            with self.subTest(command=command):
                result = self.run_command([*command, 'inspect'])
                fingerprint = result.stdout.split('\0')[1]
                prepared = self.run_command([*command, 'prepare', fingerprint])
                directory = Path(prepared.stdout.split('\0')[0])
                self.assertEqual((directory / 'bat-source/syntaxes/fixture.sublime-syntax').read_bytes(), SYNTAX)
                self.assertFalse((self.home / 'state/dots/current/theme').exists())

    def test_shell_only_fingerprints_do_not_query_bat(self):
        wrapper = self.repo / 'bin/bat'
        wrapper.write_text('#!' + fixture.BASH + '\nprintf called > "$HOME/bat-called"\nexit 91\n')
        wrapper.chmod(0o700)
        self.engine('dt_load nord; dt_cached_init zsh >/dev/null')
        self.assertFalse((self.home / 'bat-called').exists())
        with patch.dict(os.environ, self.env, clear=True), patch.object(bat_cache, 'inputs') as query:
            Themes().fingerprint('nord')
            query.assert_not_called()


for name in dir(fixture.Themes):
    if name.startswith('test_') and name not in Publication.__dict__:
        setattr(Publication, name, None)


if __name__ == '__main__': unittest.main(verbosity=2)

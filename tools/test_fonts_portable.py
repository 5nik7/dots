#!/usr/bin/env python3
"""Import a real font through both launchers with a stock Python environment."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from test_bootstrap_entry import owned_environment

ROOT = Path(__file__).resolve().parents[1]


class PortableFonts(unittest.TestCase):
    def test_import_show_and_repeat_without_fonttools(self):
        with tempfile.TemporaryDirectory(prefix='dots fonts portable ') as temporary:
            home = Path(temporary).resolve()
            env = owned_environment(home)
            repo = home / 'checkout'
            (repo / 'bin').mkdir(parents=True)
            for name in ('dots', 'fonts', 'dots.ps1', 'fonts.ps1', 'dots-fonts',
                         'dots-fonts-import', 'dots-fonts-show'):
                shutil.copy2(ROOT / 'bin' / name, repo / 'bin' / name)
            shutil.copytree(ROOT / 'lib/dots', repo / 'lib/dots',
                            ignore=shutil.ignore_patterns('__pycache__'))
            for platform in ('linux', 'wsl', 'termux', 'windows'):
                profile = repo / 'profiles' / platform
                profile.mkdir(parents=True)
                (profile / 'profile.json').write_text(json.dumps(dict(schema=1, id=platform)))
            source = home / '-face ü.ttf'
            shutil.copy2(ROOT / 'profiles/termux/config/termux/font.ttf', source)

            runtime = home / 'python'
            subprocess.run([sys.executable, '-I', '-B', '-m', 'venv', '--without-pip', runtime],
                           check=True, env=env, timeout=30)
            if os.name == 'nt':
                engine = shutil.which(os.environ.get('DOTS_TEST_POWERSHELL', 'powershell'))
                self.assertIsNotNone(engine, 'select a native engine with DOTS_TEST_POWERSHELL')
                launch = [engine, '-NoLogo', '-NoProfile', '-NonInteractive', '-File']
                scripts = runtime / 'Scripts'
                python, dots, fonts = scripts / 'python.exe', 'dots.ps1', 'fonts.ps1'
                env['OS'] = 'Windows_NT'
            else:
                launch = []
                scripts = runtime / 'bin'
                python, dots, fonts = scripts / 'python3', 'dots', 'fonts'
                for name in ('bash', 'env'):
                    (scripts / name).symlink_to(shutil.which(name))
                if env.get('TERMUX_VERSION'):
                    prefix = home / 'usr'
                    prefix.mkdir()
                    (prefix / 'bin').symlink_to(scripts, target_is_directory=True)
                    env.update(PREFIX=str(prefix), TERMUX__PREFIX=str(prefix))
            env.update(PATH=str(scripts), DOTS=str(repo), DOTS_COLOR='never', DOTS_ICONS='never')
            subprocess.run([python, '-B', '-c',
                            'import importlib.util; assert importlib.util.find_spec("fontTools") is None'],
                           env=env, check=True, timeout=10)

            def command(script, *args):
                argv = [*launch, repo / 'bin' / script]
                if script == dots:
                    argv.append('fonts')
                result = subprocess.run([*argv, *args, '--json'], stdin=subprocess.DEVNULL,
                                        env=env, cwd=home, capture_output=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
                return json.loads(result.stdout)

            imported = command(dots, 'import', source, '--yes')
            self.assertEqual(imported['status'], 'complete')
            identity = imported['items'][0]['id']
            family, = command(fonts, 'show', identity)['items']
            face, = family['versions'][family['preferred']]['fonts']
            self.assertTrue(face['family'])
            self.assertEqual(family['name'], face['family'])
            self.assertEqual(face['sha256'], hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertEqual(command(fonts, 'import', source, '--yes')['status'], 'unchanged')
            self.assertEqual(command(dots, 'show', identity)['items'], [family])


if __name__ == '__main__':
    unittest.main()

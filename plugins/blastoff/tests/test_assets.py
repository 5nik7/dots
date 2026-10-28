"""Optional reference branding is never a runtime dependency."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent

class OptionalAssets(unittest.TestCase):
    def test_runtime_without_any_branding_assets(self):
        with tempfile.TemporaryDirectory(prefix='blastoff-no-assets-') as directory:
            root = Path(directory)
            payload = root/'plugins/blastoff'
            shutil.copytree(ROOT.parents[1]/'lib/dots', root/'lib/dots',
                            ignore=shutil.ignore_patterns('__pycache__'))
            for name in ('lib','bin','completions'):
                shutil.copytree(ROOT/name,payload/name,ignore=shutil.ignore_patterns('__pycache__'))
            env = dict(os.environ, HOME=str(root/'home'), USERPROFILE=str(root/'home'),
                       BLASTOFF_HOME=str(root/'store'), STARSHIP_CONFIG=str(root/'config.toml'),
                       BLASTOFF_PYTHON=sys.executable, PATH='', NO_COLOR='1')
            env.update(XDG_CONFIG_HOME=str(root/'config'), XDG_STATE_HOME=str(root/'state'),
                       XDG_CACHE_HOME=str(root/'cache'), XDG_DATA_HOME=str(root/'data'),
                       APPDATA=str(root/'Roaming'), LOCALAPPDATA=str(root/'Local'),
                       DOTS_COLOR='auto', DOTS_ICONS='never', DOTS_MENU_CAPTURE='')
            for args in [[],['--help'],['--version'],['list'],['current'],['doctor'],
                         ['completion','bash'],['completion','zsh'],['completion','fish']]:
                p = subprocess.run([sys.executable,'-I',str(payload/'lib/blastoff.py'),*args],env=env,capture_output=True,check=False)
                self.assertEqual(p.returncode,0,p.stderr)
                self.assertNotIn(b'\x1b',p.stdout)
            p = subprocess.run([sys.executable, '-I', str(payload/'lib/blastoff.py'),
                                'current', '--color', 'always'], env=env, capture_output=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn(b'\x1b[1;96mCurrent configuration', p.stdout)
            self.assertFalse((payload/'lib/__pycache__').exists())
            self.assertFalse((root/'home').exists())
            self.assertFalse((root/'store').exists())
            self.assertFalse((root/'config.toml').exists())

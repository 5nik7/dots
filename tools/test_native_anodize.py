#!/usr/bin/env python3
"""Native authoring/publication contracts using a prebuilt Anodize engine."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_native_cli as fixtures


class NativeAnodize(unittest.TestCase):
    command = fixtures.NativeCLI.command

    def setUp(self):
        engine = Path(os.environ.get('ANODIZE_ENGINE') or fixtures.ROOT / 'anodize/.build' /
                      ('anodize-engine.exe' if os.name == 'nt' else 'anodize-engine'))
        if not engine.is_file():
            if os.environ.get('DOTS_TEST_ANODIZE'): self.fail('required native Anodize engine missing')
            self.skipTest('prebuilt native Anodize engine unavailable')
        fixtures.NativeCLI.setUp(self)
        self.env['ANODIZE_ENGINE'] = str(engine)
        shutil.copytree(fixtures.ROOT / 'default', self.repo / 'default')
        (self.repo / 'themes').mkdir()

    def create(self):
        return json.loads(self.command('anodize','create','native-fixture','--color','#725ac1','--yes','--json').stdout)

    def test_native_modes_authoring_and_raw_exports(self):
        json.loads(self.command('anodize','modes','--json').stdout)
        self.command('anodize','create','native-fixture','--color','#725ac1','--dry-run','--json')
        self.assertFalse(list(self.home.iterdir()))
        self.create()
        self.assertTrue((self.repo / 'themes/native-fixture/anodize.json').is_file())
        result = self.command('anodize','export','native-fixture','--format','colors')
        self.assertIn('background', result.stdout)
        self.assertNotIn('\x1b', result.stdout)
        self.command('anodize','create','native-fixture','--color','#123456','--yes','--json',expected=1)

    def test_native_bridge_plan_does_not_publish(self):
        self.create()
        result = subprocess.run([sys.executable,'-B',str(self.repo / 'lib/dots/themes/bridge.py'),
                                 'plan','native-fixture'],env=self.env,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'],'preview')
        self.assertFalse((self.home / 'state/dots/current/theme').exists())

    def test_authored_palette_native_publication(self):
        self.create()
        sys.path.insert(0,str(fixtures.LIB / 'themes'))
        from palette_native import Themes
        import theme_cli
        with patch.dict(os.environ,self.env,clear=True), patch.object(theme_cli,'reload_apps'):
            generation = theme_cli.publication(Themes(),'native-fixture')
        path = self.home / 'state/dots/themes/generations' / generation
        self.assertEqual(json.loads((path / 'palette.json').read_text())['id'],'native-fixture')
        self.assertTrue((path / 'commands/bin/native-fixture.ps1').is_file())


if __name__ == '__main__': unittest.main()

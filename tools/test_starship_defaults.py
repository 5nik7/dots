#!/usr/bin/env python3
"""Owned-home default-path and stale override checks; never load live profiles."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

import test_shell_init as fixtures
REPO = fixtures.REPO


class Defaults(unittest.TestCase):
    setUp = fixtures.InitTests.setUp
    shell = fixtures.InitTests.shell

    def check_shell(self, name):
        scripts = {
            'bash': 'source "$DOTS/shells/environment.sh"; source "$DOTS/shells/environment.sh"; printf "VALUE<%s>" "${STARSHIP_CONFIG-}"',
            'zsh': 'source "$DOTS/shells/environment.sh"; source "$DOTS/shells/environment.sh"; printf "VALUE<%s>" "${STARSHIP_CONFIG-}"',
            'fish': 'source "$DOTS/shells/fish/environment.fish"; source "$DOTS/shells/fish/environment.fish"; echo "VALUE<$STARSHIP_CONFIG>"',
            'powershell': '. "$env:DOTS/shells/powershell/environment.ps1"; . "$env:DOTS/shells/powershell/environment.ps1"; Write-Output "VALUE<$env:STARSHIP_CONFIG>"',
            'xonsh': 'source @($DOTS + "/shells/xonsh/environment.xsh")\nsource @($DOTS + "/shells/xonsh/environment.xsh")\nprint("VALUE<" + __xonsh__.env.get("STARSHIP_CONFIG", "") + ">")',
            'nu': 'source '+str(self.repo/'shells/nushell/environment.nu').replace("'", "''"),
        }
        if name == 'nu':
            path = json.dumps(str(self.repo/'shells/nushell/environment.nu'), ensure_ascii=False)
            scripts[name] = 'source '+path+'; source '+path+'; print ($"VALUE<($env.STARSHIP_CONFIG? | default \'\')>")'
        for value, expected in [(None, ''), (str(self.repo/'config/starship/starship.toml'), ''),
                                (str(self.home/'.dots/configs/starship/starship.toml'), ''),
                                (str(self.home/'custom override.toml'), str(self.home/'custom override.toml'))]:
            with self.subTest(shell=name, value=value):
                self.env.pop('STARSHIP_CONFIG', None)
                if value is not None: self.env['STARSHIP_CONFIG'] = value
                self.assertIn('VALUE<'+expected+'>', self.shell(name, scripts[name]).stdout)

    def test_bash(self): self.check_shell('bash')
    def test_zsh(self): self.check_shell('zsh')
    def test_fish(self): self.check_shell('fish')
    def test_nushell(self): self.check_shell('nu')
    def test_xonsh(self): self.check_shell('xonsh')
    def test_powershell(self): self.check_shell('powershell')

    def test_catalog_uses_home_not_xdg(self):
        doc = json.loads((REPO/'.dots/files.json').read_text())
        row = next(r for r in doc['resources'] if r['id'] == 'starship')
        self.assertEqual(row['target'], '${HOME}/.config/starship.toml')
        self.assertTrue(all(v == row['target'] for v in row.get('targets', {}).values()))

    def test_clink_cleanup_with_stubbed_windows_environment(self):
        if not shutil.which('lua'): self.skipTest('Lua unavailable')
        source = REPO/'windots/config/clink/starship.lua'
        script = '''local values = {STARSHIP_CONFIG=arg[2], USERPROFILE="C:/Users/njen"}
os.getenv=function(name) return values[name] end
os.setenv=function(name,value) values[name]=value end
io.popen=function() return {read=function() return "" end} end
dofile(arg[1])
print("VALUE<" .. (values.STARSHIP_CONFIG or "") .. ">")
'''
        fixture = self.root/'clink-test.lua'; fixture.write_text(script)
        for value, expected in [('C:\\Users\\njen\\dots\\configs\\starship\\starship.toml', ''),
                                ('/config/starship/starship.toml', '/config/starship/starship.toml'),
                                ('C:/custom/starship.toml', 'C:/custom/starship.toml')]:
            result = subprocess.run([shutil.which('lua'),str(fixture),str(source),value],env=self.env,
                                    capture_output=True,text=True,check=True)
            self.assertEqual(result.stdout.strip(), 'VALUE<'+expected+'>')


if __name__ == '__main__': unittest.main()

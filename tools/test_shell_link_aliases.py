"""Invoke the public .ln adapter in available, isolated native shells."""
import json
import os
from pathlib import Path
import shutil
import unittest
import test_shell_init as fixture
REPO = fixture.REPO


class LinkAliases(unittest.TestCase):
    setUp=fixture.InitTests.setUp
    shell=fixture.InitTests.shell
    dots=fixture.InitTests.dots
    generated=fixture.InitTests.generated

    def check(self, shell):
        shutil.copy2(REPO/'bin/dots-link',self.repo/'bin/dots-link')
        (self.repo/'scripts').mkdir(exist_ok=True)
        shutil.copy2(REPO/'scripts/dots-link.ps1',self.repo/'scripts/dots-link.ps1')
        source=self.home/'snow 雪';source.write_text('link me')
        target=self.home/'target'
        self.env.update(DOTS_LINK_SOURCE=str(source),DOTS_LINK_TARGET=str(target),DOTS_INIT_THEME='0')
        tail={
            'bash':'\n.ln "$DOTS_LINK_SOURCE" "$DOTS_LINK_TARGET" --json\n',
            # zsh parses the complete -c input before the sourced hook defines
            # aliases. Eval models the next interactive input line.
            'zsh':'\neval \'.ln "$DOTS_LINK_SOURCE" "$DOTS_LINK_TARGET" --json\'\n',
            'fish':'\n.ln "$DOTS_LINK_SOURCE" "$DOTS_LINK_TARGET" --json\n',
            'nu':'\n.ln $env.DOTS_LINK_SOURCE $env.DOTS_LINK_TARGET --json\n',
            'xonsh':'\n.ln $DOTS_LINK_SOURCE $DOTS_LINK_TARGET --json\n',
            'powershell':'\n.ln $env:DOTS_LINK_SOURCE $env:DOTS_LINK_TARGET --json\n'}[shell]
        result=self.shell(shell,self.generated(shell)+tail,interactive=shell in ('bash','zsh'))
        self.assertEqual(json.loads(result.stdout)['items'][-1]['target'],str(target))
        self.assertTrue(target.is_symlink());self.assertEqual(target.read_text(),'link me')
    def test_bash(self):self.check('bash')
    def test_zsh(self):self.check('zsh')
    def test_fish(self):self.check('fish')
    def test_nu(self):self.check('nu')
    def test_xonsh(self):self.check('xonsh')
    def test_powershell(self):self.check('powershell')


if __name__=='__main__':unittest.main()

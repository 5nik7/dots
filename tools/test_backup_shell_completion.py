#!/usr/bin/env python3
"""Invoke Bak completion in available installed shells, with owned startup roots."""
import shutil
import unittest
import test_shell_init as fixtures


class ShellCompletion(unittest.TestCase):
    setUp=fixtures.InitTests.setUp
    shell=fixtures.InitTests.shell
    dots=fixtures.InitTests.dots
    generated=fixtures.InitTests.generated

    def check(self,shell):
        for file in fixtures.REPO.glob('bin/dots-bak*'):shutil.copy2(file,self.repo/'bin'/file.name)
        self.env.update(DOTS_INIT_THEME='0',DOTS_INIT_COMPLETION='1',DOTS_TERMUX_AUTOSTART='0')
        suffix={
            'bash':'''\nCOMP_LINE='bak res'; COMP_POINT=${#COMP_LINE}; _dots_complete_bash; printf '%s\\n' "${COMPREPLY[@]}"\n''',
            'zsh':'''\n_dots_shell_prompt
[[ $_comps[bak] == _dots && $_comps[dots-bak] == _dots ]] || { print -r -- "binding:${_comps[bak]}:${_comps[dots-bak]}"; exit 1; }
# Run the bound function with a literal completion context; capture compadd values.
compadd() { print -rl -- "${candidates[@]}"; }
_files() { return 0; }
words=(bak res); CURRENT=2; _dots\n''',
            'fish':'''\ncomplete -C 'bak res'\n''',
            'nu':'''\ndo $env.config.completions.external.completer [bak res] | to json\n''',
            'xonsh':'''\nfrom types import SimpleNamespace
context = SimpleNamespace(arg_index=1,command='bak',args=[SimpleNamespace(value='bak')],prefix='res')
print(__xonsh__.completers['dots'](SimpleNamespace(command=context)))\n''',
            'powershell':'''\n[System.Management.Automation.CommandCompletion]::CompleteInput('bak res',7,$null).CompletionMatches.CompletionText\n'''
        }[shell]
        prefix='autoload -Uz compinit; compinit -D;\n' if shell=='zsh' else ''
        result=self.shell(shell,prefix+self.generated(shell)+suffix,interactive=shell!='powershell')
        self.assertIn('restore',result.stdout,result.stderr)
        self.assertFalse((self.home/'state/dots/bak').exists())

    def test_bash(self):self.check('bash')
    def test_zsh(self):self.check('zsh')
    def test_fish(self):self.check('fish')
    def test_nu(self):self.check('nu')
    def test_xonsh(self):self.check('xonsh')
    def test_powershell(self):self.check('powershell')


if __name__=='__main__':unittest.main()

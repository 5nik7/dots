#!/usr/bin/env python3
"""Engine-free completion/manual checks in disposable shell and repository roots."""
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unittest

import test_bash_dots as fixture
from bash_dots_pty import Terminal

REPO = fixture.REPO
sys.path.insert(0, str(REPO/'lib/dots/anodize'))
from cli import parser


class Integration(unittest.TestCase):
    shell = fixture.DotsFixture.shell
    run_dots = fixture.DotsFixture.run_dots

    def setUp(self):
        fixture.DotsFixture.setUp(self)
        for source in [REPO/'bin/anodize', *REPO.glob('bin/dots-anodize*')]:
            shutil.copy2(source, self.repo/'bin'/source.name)
        self.env['PYTHONDONTWRITEBYTECODE'] = '1'
        self.env['ANODIZE_ENGINE'] = str(self.root/'engine-must-not-run')
        Path(self.env['ANODIZE_ENGINE']).write_text('#!'+fixture.BASH+'\ntouch "$HOME/engine-ran"\nexit 99\n')
        Path(self.env['ANODIZE_ENGINE']).chmod(0o700)
        for name in ('dusk', 'bundled'):
            path = self.repo/'themes'/name
            path.mkdir(parents=True)
            (path/'colors.toml').write_text('background = "#111111"\n')
        (self.repo/'themes/dusk/anodize.json').write_text('{}')

    def cli(self, *args, code=0):
        result = subprocess.run([str(self.repo/'bin/anodize'), *args], env=self.env,
                                cwd=self.home, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, code, result.stderr)
        return result.stdout

    def candidates(self, *words):
        return self.cli('__complete', 'bash', str(len(words)), '--', 'anodize', *words)

    def test_generation_manual_and_parser_metadata(self):
        subprocess.run([sys.executable, '-B', str(REPO/'tools/generate_anodize_integration.py'), '--check'],
                       env=self.env, check=True, capture_output=True)
        man = shutil.which('mandoc')
        self.assertIsNotNone(man, 'mandoc is required to validate the manual')
        lint = subprocess.run([man, '-Tlint', str(REPO/'man/anodize.1')],
                              env=self.env, text=True, capture_output=True)
        self.assertEqual((lint.returncode, lint.stdout, lint.stderr), (0, '', ''))
        self.run_dots('commands', '--check')
        actions = next(a for a in parser()._actions if isinstance(a, argparse._SubParsersAction))
        for name, command in actions.choices.items():
            header = (REPO/'bin'/('dots-anodize-'+name)).read_text()
            for action in command._actions:
                if action.dest == 'help':
                    continue
                for option in action.option_strings:
                    self.assertIn('# dots:option='+option+'|', header)
                if action.choices:
                    self.assertIn('choice:'+','.join(action.choices), header)
        # Static suggestions stay synchronized with the pure core without running it.
        core = (REPO/'anodize/anodize.go').read_text()
        modes = re.findall(r'"([^"]+)"', re.search(r'var modes = \[\]string\{([^}]+)\}', core)[1])
        actual = [line.split('\t')[1] for line in self.candidates('extract', 'wall.png', '--mode', '').splitlines()]
        self.assertEqual(actual, modes)
        for name in ('create', 'import', 'edit'):
            actual = [line.split('\t')[1] for line in self.candidates(name, 'theme', '--mode', '').splitlines()]
            self.assertEqual(actual, modes)
        adjustment_names = re.findall(r'"([^"]+)":', re.search(r'fields := map\[string\]\*float64\{([^}]+)\}', core)[1])
        ansi_names = re.findall(r'"([^"]+)"', re.search(r'var names = \[\]string\{([^}]+)\}', core)[1])
        semantic_names = re.findall(r'"([^"]+)":', re.search(r'defaults := map\[string\]string\{([^}]+)\}', core)[1])
        for name in ('create', 'edit'):
            for flag, names in (('--adjust', adjustment_names), ('--set', ansi_names+semantic_names)):
                actual = [line.split('\t')[1] for line in self.candidates(name, 'theme', flag, '').splitlines()]
                self.assertEqual(actual, [name+'=' for name in names])
        for shell in ('bash', 'zsh', 'fish'):
            source = self.cli('completion', shell)
            self.assertEqual(source, (REPO/'lib/dots/anodize/completion'/shell).read_text())
            self.assertEqual(source, self.run_dots('anodize', 'completion', shell).stdout)
            self.assertNotIn('\x1b', source)
        self.cli('completion', 'powershell', code=2)
        self.assertFalse((self.home/'engine-ran').exists())
        Path(self.env['ANODIZE_ENGINE']).unlink()
        self.assertIn('candidate\tnormal\t', self.candidates('extract', 'image', '--mode', 'nor'))
        self.assertIn('#compdef anodize', self.cli('completion', 'zsh'))

    def test_context_prefixes_and_no_execution(self):
        self.assertIn('candidate\tcompletion\t', self.candidates(''))
        self.assertNotIn('candidate\tcommands\t', self.candidates(''))
        cases = [
            (('--color=a',), '--color=always'),
            (('--color=always', '--icons=never', 'cr'), 'create'),
            (('completion', 'z'), 'zsh'),
            (('create', 'new', '--from', 'du'), 'dusk'),
            (('show', '--json', 'du'), 'dusk'),
            (('preview', 'dusk', '--app=k'), '--app=kitty'),
            (('import', 'file', '--name', 'new', '--format', 'b'), 'base16'),
            (('export', 'dusk', '--format', 'a'), 'aether'),
            (('edit', 'dusk', '--adjust', 'b'), 'brightness='),
            (('edit', 'dusk', '--set', 'acc'), 'accent='),
            (('create', 'new', '--mode=n'), '--mode=normal'),
        ]
        for words, value in cases:
            with self.subTest(words=words):
                self.assertIn('candidate\t'+value+'\t', self.candidates(*words))
        self.assertNotIn('bundled', self.candidates('edit', ''))
        self.assertIn('bundled', self.candidates('show', ''))
        self.assertEqual(self.candidates('create', 'new', '--color', ''), '')
        self.assertEqual(self.candidates('create', 'new', '--image', ''), 'file\t\t\n')
        self.assertEqual(self.candidates('extract', '--', '-wall'), 'file\t\t\n')
        self.assertEqual(self.candidates('export', 'dusk', '--output='), 'file\t--output=\t\n')
        self.assertEqual(self.candidates('create', 'new', '--unknown', ''), '')
        self.assertNotIn('\x1b', self.candidates('--color=always', 'create', 'new', '--m'))
        self.assertFalse((self.home/'engine-ran').exists())
        self.assertFalse((self.home/'state').exists())

    def test_shell_candidates_and_registration(self):
        for executable in (fixture.BASH, fixture.ZSH, fixture.FISH):
            self.assertIsNotNone(executable, 'Bash, Zsh and Fish are required')
        (self.home/'wall ü space.png').touch()
        bash = self.shell(fixture.BASH, '''source "$DOTS/lib/dots/anodize/completion/bash"
COMP_WORDS=(anodize create dusk --mode = nor); COMP_CWORD=5
_anodize_complete_bash; printf '<%s>\\n' "${COMPREPLY[@]}"
COMP_WORDS=(anodize create dusk --image wall); COMP_CWORD=4
_anodize_complete_bash; printf '<%s>\\n' "${COMPREPLY[@]}"
''')
        self.assertEqual(bash.stdout, '<normal>\n<wall ü space.png>\n')
        fish = self.shell(fixture.FISH, '''source "$DOTS/lib/dots/anodize/completion/fish"
complete -C 'anodize create dusk --mode nor'
complete -C 'anodize extract wall'
''')
        self.assertIn('normal', fish.stdout)
        self.assertIn('wall', fish.stdout)
        zsh = self.shell(fixture.ZSH, '''autoload -Uz compinit; compinit -D
source "$DOTS/lib/dots/anodize/completion/zsh"
[[ $_comps[anodize] == _anodize ]] || exit 1
compadd() { print -rl -- "${candidates[@]}"; print -rl -- "${descriptions[@]}"; }
words=(anodize create dusk --m); CURRENT=4; _anodize
words=(anodize create dusk --mode nor); CURRENT=5; _anodize
''')
        self.assertIn('--mode -- Extraction mode', zsh.stdout)
        self.assertIn('normal', zsh.stdout)
        self.assertFalse((self.home/'engine-ran').exists())

    def test_real_tab_literal_insertion(self):
        # Only this fixture wrapper captures commands; private completion still
        # calls the real adapter. No authoring/apply operation runs in the PTY.
        (self.repo/'bin/anodize').write_text('#!'+fixture.BASH+'''
if [[ $1 == __complete ]]; then
  exec python3 -B "$DOTS/lib/dots/anodize/cli.py" "$@"
fi
printf '%s\\n' "$@" > "$HOME/args"
printf 'EXECUTED\\n'
''')
        (self.home/'wall ü space.png').touch()
        for executable, name in ((fixture.BASH, 'bash'), (fixture.ZSH, 'zsh'), (fixture.FISH, 'fish')):
            with self.subTest(shell=name):
                terminal = Terminal(executable, self.env, self.home)
                try:
                    init = 'autoload -Uz compinit; compinit -D; ' if name == 'zsh' else ''
                    terminal.send(init+'source "$DOTS/lib/dots/anodize/completion/'+name+'"; printf "\\nINITIALIZED\\n"\r')
                    terminal.wait(b'INITIALIZED\r\n')
                    for typed, marker, expected in (
                        ('anodize cr\t', b'create', 'create'),
                        ('anodize create new --mode=nor\t', b'normal', '--mode=normal'),
                        ('anodize edit dusk --adjust bright\t12', b'brightness', 'brightness=12'),
                        ('anodize extract wall\t', b'png', 'wall ü space.png'),
                        ('anodize --color=al\t', b'always', '--color=always'),
                    ):
                        terminal.send(typed)
                        terminal.wait(marker)
                        terminal.send('\r')
                        terminal.wait(b'EXECUTED\r\n')
                        self.assertEqual((self.home/'args').read_text().splitlines()[-1], expected)
                finally:
                    terminal.close()
        self.assertFalse((self.home/'engine-ran').exists())


if __name__ == '__main__':
    unittest.main()

#!/usr/bin/env python3
"""Real project Zsh menus using source-only completions and owned PTYs.

No project executable, installer, battery API or backend is invoked. Embedded
completion text is extracted from its known literal here-document source.
"""
import os
from pathlib import Path
import shlex
import shutil
import unittest

import test_completion_colors as fixtures

REPOS = Path(os.environ.get('DOTS_TEST_REPOS_ROOT', Path.home()/'repos'))


def embedded(path, marker, delimiter='EOF'):
    source = path.read_text().split(marker, 1)[1]
    return source.split("<<'"+delimiter+"'\n", 1)[1].split('\n'+delimiter, 1)[0]+'\n'


@unittest.skipUnless(shutil.which('zsh') and shutil.which('fzf') and
                    (fixtures.FZF_TAB/'fzf-tab.plugin.zsh').exists(), 'Zsh/fzf-tab unavailable')
class ProjectMenus(unittest.TestCase):
    setUp = fixtures.CompletionColors.setUp
    terminal = fixtures.CompletionColors.terminal
    command = fixtures.CompletionColors.command
    drain = fixtures.CompletionColors.drain
    finish = fixtures.CompletionColors.finish
    await_buffer = fixtures.CompletionColors.await_buffer

    def test_project_source_menus_and_literal_insertion(self):
        sources = [
            ('battery','battery','generate_zsh_completion() {','EOF'),
            ('git-it','lib/completion.bash',"        zsh) cat <<'EOF'",'EOF'),
            ('gitsub','gitsub','print_zsh_completion() {','EOF'),
            ('paint','paint','print_completion_zsh() {','ZSH'),
            ('leaf','completions/leaf.zsh',None,None),
            ('codex-termux','completions/_codex-termux',None,None),
        ]
        loaded = set()
        target = self.home/'project-completions';target.mkdir()
        for name, relative, marker, delimiter in sources:
            source = REPOS/name/relative
            if not source.is_file(): continue
            if name == 'git-it':
                # Keep the heredoc opener available to the bounded extractor.
                text = embedded(source,'        zsh)',delimiter)
            else:
                text = embedded(source,marker,delimiter) if marker else source.read_text()
            (target/('_'+name)).write_text(text)
            loaded.add(name)
        if not loaded: self.skipTest('Associated project source checkouts unavailable')
        missing = {row[0] for row in sources}-loaded
        if missing: print('\nUnavailable project sources: '+', '.join(sorted(missing)),flush=True)
        terminal = self.terminal()
        try:
            setup = 'fpath=('+shlex.quote(str(target))+' $fpath); '
            for name in sorted(loaded):
                if name in ('leaf','codex-termux'):
                    setup += 'source '+shlex.quote(str(target/('_'+name)))+'; '
                else:
                    setup += 'autoload -Uz _'+name+'; compdef _'+name+' '+name+'; '
            self.command(terminal,setup.rstrip('; '))
            cases = [
                ('battery --',"'--backend",'battery --backend=',b'33'),
                ('battery --backend ',"'wrapper",'battery --backend wrapper ',b'32'),
                ('git-it ',"'publish",'git-it publish ',b'34'),
                ('git-it --color ',"'always",'git-it --color always ',b'32'),
                ('gitsub --',"'--quiet",'gitsub --quiet ',b'33'),
                ('gitsub --completion ',"'zsh",'gitsub --completion zsh ',b'32'),
                ('leaf --',"'--watch",'leaf --watch ',b'33'),
                ('leaf --inline ',"'plain",'leaf --inline plain ',b'32'),
                ('paint --',"'--ansi",'paint --ansi ',b'33'),
                ('paint --color ',"'always",'paint --color always ',b'32'),
                ('paint bright ',"'red",'paint bright red ',b'32'),
                ('codex-termux ',"'manage",'codex-termux manage ',b'34'),
                ('codex-termux manage server ',"'status",'codex-termux manage server status ',b'34'),
                ('codex-termux --',"'--help",'codex-termux --help ',b'33'),
            ]
            for typed, query, expected, sgr in cases:
                if typed.split()[0] not in loaded: continue
                terminal.send(typed+'\t');terminal.wait(b'\x1b[?1000h');self.drain(terminal)
                data=(self.home/'menu-data').read_bytes()
                self.assertIn(b'\x1b[0;'+sgr+b'm',data,typed)
                self.finish(terminal,query,expected)
                terminal.send('\x03');self.drain(terminal)
        finally:terminal.close()
        print('\nProject menu sources: '+', '.join(sorted(loaded)),flush=True)


if __name__ == '__main__':
    unittest.main()

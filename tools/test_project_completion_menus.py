#!/usr/bin/env python3
"""Native project Zsh menus remain outside Dots styling, in owned PTYs.

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
            setup += "_DOTS_COMPLETION_STYLES[command]='38;2;1;2;3'; _DOTS_COMPLETION_STYLES[option]='38;2;1;2;3'; _DOTS_COMPLETION_STYLES[value]='38;2;1;2;3'"
            self.command(terminal,setup)
            cases = [
                ('battery --',"'--backend",'battery --backend='),
                ('battery --backend ',"'wrapper",'battery --backend wrapper '),
                ('gitsub --',"'--quiet",'gitsub --quiet '),
                ('gitsub --completion ',"'zsh",'gitsub --completion zsh '),
                ('leaf --',"'--watch",'leaf --watch '),
                ('leaf --inline ',"'plain",'leaf --inline plain '),
                ('paint --',"'--ansi",'paint --ansi '),
                ('paint --color ',"'always",'paint --color always '),
                ('paint bright ',"'red",'paint bright red '),
                ('codex-termux ',"'manage",'codex-termux manage '),
                ('codex-termux manage server ',"'status",'codex-termux manage server status '),
                ('codex-termux --',"'--help",'codex-termux --help '),
            ]
            for typed, query, expected in cases:
                if typed.split()[0] not in loaded: continue
                terminal.send(typed+'\t');terminal.wait(b'\x1b[?1000h');self.drain(terminal)
                data=(self.home/'menu-data').read_bytes()
                self.assertNotIn(b'\x1b[0;38;2;1;2;3m',data,typed)
                self.assertNotIn(b'--with-nth=1,3',(self.home/'menu-args').read_bytes(),typed)
                self.finish(terminal,query,expected)
                terminal.send('\x03');self.drain(terminal)
        finally:terminal.close()
        print('\nProject menu sources: '+', '.join(sorted(loaded)),flush=True)


if __name__ == '__main__':
    unittest.main()

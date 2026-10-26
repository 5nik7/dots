#!/usr/bin/env python3
"""Exercise personal bindings using copied public plugins in owned ZLE sessions."""
import os
from pathlib import Path
import shutil
import time
import unittest
from zsh_fixture import fixture, REPO, ZSH
from zsh_interactive import Session


class Backspace(unittest.TestCase):
    @unittest.skipUnless(ZSH,'Zsh unavailable')
    def test_modes_encodings_and_reload(self):
        installed=Path.home()/'.local/share/zinit'
        extra=('jeffreytse---zsh-vi-mode','kutsan---zsh-system-clipboard')
        if not all((installed/'plugins'/name).is_dir() for name in extra):self.skipTest('installed public vi/clipboard plugins unavailable')
        try:root,repo,env=fixture()
        except RuntimeError as error:self.skipTest(str(error))
        session=None
        try:
            for name in extra:
                shutil.copytree(installed/'plugins'/name,Path(env['HOME'])/'.local/share/zinit/plugins'/name,ignore=shutil.ignore_patterns('.git','*.zwc'))
            env.update(DOTS_INIT_THEME='0',DOTS_TERMUX_AUTOSTART='0')
            shutil.copy2(REPO/'profiles/termux/shells/zsh/local.zsh',Path(env['HOME'])/'.zshrc.local')
            rc=repo/'shells/zsh/zshrc';rc.write_text(rc.read_text()+"\nPS1='READY> '\n")
            session=Session(env,env['HOME']);session.wait(b'READY> ',timeout=30);time.sleep(.4)
            def command(text):
                session.send(text+'; printf "\\036DONE\\037"\r')
                session.wait(b'\x1eDONE\x1f',timeout=25);time.sleep(.3)
            for reload in (False,True):
                if reload:command('rl; rl')
                command('_capture_buffer() { print -r -- "$BUFFER" > "$HOME/buffer"; BUFFER=""; printf "\\036CAPTURE\\037"; zle accept-line; }; zle -N _capture_buffer; bindkey -M viins "^G" _capture_buffer; _capture_cursor() { print -r -- "$CURSOR" > "$HOME/cursor"; }; zle -N _capture_cursor; bindkey -M viins "^]" _capture_cursor')
                for mode in ('i','a'):
                    for key in ('\x7f','\x08'):
                        session.send('abcd');time.sleep(.1);session.send('\x1b');time.sleep(.15)
                        session.send('h');time.sleep(.12);session.send(mode);time.sleep(.15);session.send('\x1d');time.sleep(.12);session.send(key+'\x07')
                        session.wait(b'\x1eCAPTURE\x1f',timeout=15);time.sleep(.3)
                        cursor=int((Path(env['HOME'])/'cursor').read_text());self.assertGreater(cursor,0)
                        expected='abcd'[:cursor-1]+'abcd'[cursor:]+'\n'
                        self.assertEqual((Path(env['HOME'])/'buffer').read_text(),expected,(reload,mode,repr(key),cursor))
                command('print -r -- "${#zvm_after_init_commands}:${#zvm_after_select_vi_mode_commands}:${#zvm_after_lazy_keybindings_commands}" > "$HOME/callbacks"')
                self.assertEqual((Path(env['HOME'])/'callbacks').read_text().strip(),'1:1:1')
        finally:
            if session:session.close()
            shutil.rmtree(root)


@unittest.skipUnless(ZSH, 'Zsh unavailable')
class HistoryKeys(unittest.TestCase):
    def setUp(self):
        installed = Path.home() / '.local/share/zinit'
        extra = ('jeffreytse---zsh-vi-mode', 'kutsan---zsh-system-clipboard')
        if not all((installed / 'plugins' / name).is_dir() for name in extra):
            self.skipTest('Installed public vi/clipboard plugins unavailable')
        try:
            self.root, repo, env = fixture()
        except RuntimeError as error:
            self.skipTest(str(error))
        self.addCleanup(shutil.rmtree, self.root)
        self.home = Path(env['HOME'])
        for name in extra:
            shutil.copytree(installed / 'plugins' / name, self.home / '.local/share/zinit/plugins' / name,
                            ignore=shutil.ignore_patterns('.git', '*.zwc'))
        # Exercise the clipboard widgets without touching Android or its clipboard.
        for name, body in (
                ('termux-clipboard-get', 'printf fixture-clipboard'),
                ('termux-clipboard-set', 'cat > "$HOME/clipboard"')):
            path = self.root / 'bin' / name
            path.write_text('#!' + shutil.which('sh') + '\n' + body + '\n')
            path.chmod(0o700)
        env.update(DOTS_INIT_THEME='0', DOTS_TERMUX_AUTOSTART='0')
        shutil.copy2(REPO / 'profiles/termux/shells/zsh/local.zsh', self.home / '.zshrc.local')
        rc = repo / 'shells/zsh/zshrc'
        rc.write_text(rc.read_text() + "\nPS1='READY> '\n")
        self.session = Session(env, env['HOME'])
        self.addCleanup(self.session.close)
        self.session.wait(b'READY> ', timeout=30)
        time.sleep(.3)
        self.command('''_capture() {
  print -r -- "$BUFFER" >| "$HOME/buffer"
  print -r -- "$CURSOR" >| "$HOME/cursor"
  zvm_select_vi_mode i
  BUFFER=''; CURSOR=0
  printf '\\036CAPTURE\\037'
  zle accept-line
}; zle -N _capture
bindkey -M viins '^G' _capture; bindkey -M vicmd '^G' _capture'''.replace('\n', '; '))

    def command(self, code):
        # HIST_IGNORE_SPACE keeps fixture setup commands out of the search data.
        self.session.send(' ' + code + '; printf "\\036DONE\\037"\r')
        self.session.wait(b'\x1eDONE\x1f', timeout=25)
        time.sleep(.2)

    def seed(self):
        (self.home / 'search-history').write_text(
            'print oldest-needle\nprintf NEEDLE-middle\nprint newest-needle\n'
            'print newest-needle\nprint newer-unrelated\n')
        self.command('unsetopt HIST_IGNORE_ALL_DUPS HIST_IGNORE_DUPS HIST_FIND_NO_DUPS; fc -p "$HOME/search-history" 100 100')

    def capture(self, query, keys):
        self.session.send(query)
        for key in keys:
            self.session.send(key)
            time.sleep(.15)
        self.session.send('\x07')
        self.session.wait(b'\x1eCAPTURE\x1f', timeout=15)
        time.sleep(.2)
        return (self.home / 'buffer').read_text().removesuffix('\n')

    def test_history_arrows_modes_and_reload(self):
        up, down = '\x1b[A', '\x1b[B'
        for reload in (False, True):
            if reload:
                self.command('rl; rl')
            self.seed()
            cases = [
                ('needle', [up], 'print newest-needle'),
                ('needle', [up, up], 'printf NEEDLE-middle'),
                ('needle', [up, up, up], 'print oldest-needle'),
                ('needle', [up, up, down], 'print newest-needle'),
                ('needle', ['\x1bOA', '\x1bOA', '\x1bOB'], 'print newest-needle'),
                ('needle', ['\x1b', 'k'], 'print newest-needle'),
                ('needle', ['\x1b', 'k', 'k', 'j'], 'print newest-needle'),
                ('needle', ['\x1b', up, up], 'printf NEEDLE-middle'),
                ('', [up], 'print newer-unrelated'),
                ('no-such-result', [up], 'no-such-result'),
                ('print needle', [up], 'print needle'),
            ]
            for query, keys, expected in cases:
                with self.subTest(reload=reload, query=query, keys=keys):
                    self.assertEqual(self.capture(query, keys), expected)
            self.command('print -r -- "${#zvm_after_init_commands}:${#zvm_after_select_vi_mode_commands}:${#zvm_after_lazy_keybindings_commands}" >| "$HOME/callbacks"; { bindkey -M viins "^R"; bindkey -M viins "^I"; } >| "$HOME/bindings"')
            self.assertEqual((self.home / 'callbacks').read_text().strip(), '1:1:1')
            bindings = (self.home / 'bindings').read_text()
            self.assertIn('fzf-history-widget', bindings)
            self.assertIn('fzf-tab-complete', bindings)
        self.assertIn(b'\x1b[2 q', self.session.output)
        self.assertIn(b'\x1b[6 q', self.session.output)

    def test_multiline_clipboard_and_prompt_colors(self):
        self.command("print -sr -- $'print first-needle\\nprint second-needle'")
        expected = 'print first-needle\nprint second-needle'
        self.assertEqual(self.capture('needle', ['\x1b[A', '\x1b[D', '\x1b[A']), expected)
        self.assertLessEqual(int((self.home / 'cursor').read_text()), expected.index('\n'))
        self.assertEqual(self.capture('', ['\x16']), 'fixture-clipboard')
        self.assertEqual(self.capture('clipboard text', ['\x1b', '0', 'Y']), 'clipboard text')
        self.assertEqual((self.home / 'clipboard').read_text().strip(), 'clipboard text')
        for fg, bg, error in (('#eeeeee', '#223344', '#ff6677'), ('#112233', '#ddeeff', '#aa0011')):
            self.command(f"typeset -gA selection_foreground=(hex '{fg}') selection_background=(hex '{bg}') error=(hex '{error}')")
            self.command('print -r -- "$HISTORY_SUBSTRING_SEARCH_HIGHLIGHT_FOUND|$HISTORY_SUBSTRING_SEARCH_HIGHLIGHT_NOT_FOUND" >| "$HOME/colors"')
            self.assertEqual((self.home / 'colors').read_text().strip(), f'fg={fg},bg={bg},bold|fg={error},bold')


if __name__=='__main__':unittest.main()

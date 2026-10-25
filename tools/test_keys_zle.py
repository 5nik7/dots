#!/usr/bin/env python3
"""Exercise Backspace transitions using copied public plugins in an owned PTY."""
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
                command('print -r -- "${#zvm_after_init_commands}:${#zvm_after_select_vi_mode_commands}" > "$HOME/callbacks"')
                self.assertEqual((Path(env['HOME'])/'callbacks').read_text().strip(),'1:1')
        finally:
            if session:session.close()
            shutil.rmtree(root)


if __name__=='__main__':unittest.main()

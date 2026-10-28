"""Real readline/ZLE/Fish editing via automated PTYs, not visual certification."""
import os
import re
from pathlib import Path
import shlex
import shutil
import tempfile
import unittest

from pty_support import terminal

ROOT = Path(__file__).resolve().parent.parent

@unittest.skipUnless(os.name == 'posix', 'POSIX PTY required')
class ShellTTY(unittest.TestCase):
    def test_tab_in_real_shell_editors(self):
        for shell in ('bash','zsh','fish'):
            executable = shutil.which(shell)
            if not executable:
                continue
            with self.subTest(shell=shell), tempfile.TemporaryDirectory(prefix='blastoff-shell-') as directory:
                home = Path(directory)
                store = home/'store with spaces'
                (store/'themes').mkdir(parents=True)
                (store/'themes/alpha.toml').write_text('x=1\n')
                imported = home/'import with spaces.toml'; imported.write_text('x=1\n')
                env = dict(os.environ,HOME=str(home),USERPROFILE=str(home),
                           XDG_CONFIG_HOME=str(home/'xdg'), XDG_CACHE_HOME=str(home/'cache'),
                           BLASTOFF_HOME=str(store), STARSHIP_CONFIG=str(home/'absent.toml'),
                           TERM='xterm-256color', NO_COLOR='1', HISTFILE='/dev/null', PATH='')
                completion = shlex.quote(str(ROOT/'completions'/('blastoff.'+shell)))
                if shell == 'bash':
                    rc = home/'bashrc'
                    rc.write_text('PS1="READY> "\nblastoff() { printf "UNEXPECTED_EXECUTION\\n"; return 99; }\nsource '+completion+'\n'
                                  'dump_line() { printf "\\nBUFFER<%s>\\n" "$READLINE_LINE"; READLINE_LINE=; READLINE_POINT=0; }\n'
                                  'bind -x \'"\\C-o":dump_line\'\n')
                    command = [executable,'--noprofile','--rcfile',str(rc),'-i']
                elif shell == 'zsh':
                    functions = home/'functions'; functions.mkdir()
                    shutil.copyfile(ROOT/'completions/blastoff.zsh',functions/'_blastoff')
                    (home/'.zshrc').write_text('PS1="READY> "\nHISTFILE=/dev/null\nblastoff() { print UNEXPECTED_EXECUTION; return 99; }\n'
                        'fpath=('+shlex.quote(str(functions))+' $fpath)\n'
                        'autoload -Uz compinit; compinit -D -u\n'
                        'dump_line() { print -r -- "BUFFER<$BUFFER>"; BUFFER=""; zle reset-prompt; }\n'
                        'zle -N dump_line; bindkey "^O" dump_line\n')
                    env['ZDOTDIR'] = str(home)
                    command = [executable,'-d','-i']
                else:
                    init = ('set -g fish_greeting; function fish_prompt; printf "READY> "; end; '
                            'function blastoff; printf "UNEXPECTED_EXECUTION\\n"; return 99; end; source '+completion+'; '
                            'function dump_line; printf "\\nBUFFER<%s>\\n" (commandline); commandline -r ""; end; '
                            'bind ctrl-o dump_line')
                    command = [executable,'--private','--no-config','--init-command',init,'-i']
                keys = b'blastoff theme apply local:al\t\x0f'
                keys += ('blastoff theme import '+str(home/'imp')).encode()+b'\t\x0fexit\r'
                code,out = terminal(command,env,keys,b'READY> ',columns=50)
                self.assertEqual(code,0,repr(out[-2000:]))
                self.assertNotIn(b'UNEXPECTED_EXECUTION',out)
                self.assertIn(b'BUFFER<blastoff theme apply local:alpha',out)
                buffers = re.findall(rb'BUFFER<([^>]+)>',out)
                parsed = [shlex.split(b.decode()) for b in buffers]
                self.assertIn(['blastoff','theme','import',str(imported)],parsed,repr(out[-2000:]))
                self.assertFalse((home/'absent.toml').exists())
                self.assertEqual(sorted(p.name for p in store.iterdir()),['themes'])

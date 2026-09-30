#!/usr/bin/env python3
"""Native Bash PTY acceptance in a disposable public fixture, without downloads."""
import argparse
import json
from pathlib import Path
import shutil
from bash_fixture import fixture, REPO
from zsh_interactive import Session


def exercise(source=REPO):
    root, repo, env = fixture(source)
    home = Path(env['HOME'])
    rc = root / 'fixture.bashrc'
    rc.write_text('''function fixture_status {
  local previous=$?
  printf '%s\\n' "$previous" >| "$HOME/last-status"
  return "$previous"
}
PROMPT_COMMAND=fixture_status
source "$DOTS/shells/bash/.bashrc"
PROMPT_COMMAND+=('printf "\\n__DOTS_INPUT_READY__\\n"')
''')
    session = Session(env, str(home), [shutil.which('bash'), '--noprofile', '--rcfile', str(rc), '-i'])
    try:
        session.wait()
        print('Bash prompt ready', flush=True)
        session.send('false\r'); session.wait()
        assert (home / 'last-status').read_text().strip() == '1'
        session.send('bind -m vi-insert -X >| "$HOME/keys.before"; declare -p PROMPT_COMMAND precmd_functions preexec_functions >| "$HOME/hooks.before" 2>/dev/null; printf "%s" "$FZF_DEFAULT_OPTS" >| "$HOME/fzf.before"; rl; rl; bind -m vi-insert -X >| "$HOME/keys.after"; declare -p PROMPT_COMMAND precmd_functions preexec_functions >| "$HOME/hooks.after" 2>/dev/null; printf "%s" "$FZF_DEFAULT_OPTS" >| "$HOME/fzf.after"\r')
        session.wait()
        equal = {name: (home / (name + '.before')).read_bytes() == (home / (name + '.after')).read_bytes() for name in ('keys', 'hooks', 'fzf')}
        assert all(equal.values()), equal
        session.send('printf "history-fixture\\n"\r');session.wait()
        session.send('\x12');session.wait(marker='󰅂'.encode(), timeout=30)
        session.send('\x03');session.wait(marker=b'\x1b[?2004l', timeout=15)
        session.send('\x15:\r');session.wait()
        session.send('\x1b');session.wait(marker=b'\x1b[1 q', timeout=10)
        session.send('i');session.wait(marker=b'\x1b[5 q', timeout=10)
        session.send('type mkcd; complete -p dots anodize; bind -m vi-insert -X\r');session.wait()
        # A unique filename proves actual Readline Tab completion inserts the candidate.
        (home / 'completion-fixture.txt').write_text('owned\n')
        session.send('printf "COMPLETED<%s>\\n" completion-fi\t\r')
        completed=session.wait()
        assert b'COMPLETED<completion-fixture.txt>' in completed, completed[-1000:]
        for diagnostic in (b'command not found', b'syntax error', b'bad substitution'):
            assert diagnostic not in session.output, diagnostic
        result={'fixture':str(root), 'reload_equal':equal, 'status':True, 'history_picker':True, 'vi_cursor':True, 'tab_completion':True}
        (root / 'interactive.json').write_text(json.dumps(result, indent=2))
        print(json.dumps(result, indent=2))
    finally:
        session.close()


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=REPO)
    args=parser.parse_args()
    exercise(args.source.resolve())

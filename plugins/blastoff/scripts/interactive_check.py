#!/usr/bin/env python3
"""Disposable human visual picker check; never uses live config or installation."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend', choices=['numbered','fzf','gum'], required=True)
    parser.add_argument('--expect', choices=['select','cancel'], required=True)
    style=parser.add_mutually_exclusive_group()
    style.add_argument('--fancy', nargs='?', const='unicode', choices=['unicode','ascii'])
    style.add_argument('--fzf', action='store_true', help='basic user presentation')
    parser.add_argument('--tool-config', choices=['fixture','user'], default='fixture', help='user preserves actual HOME/XDG/BAT/FZF settings while Blastoff data stays disposable')
    parser.add_argument('--feature', choices=['theme','module','backup'], default='theme')
    args = parser.parse_args()
    if args.tool_config == 'user' and args.backend != 'fzf':
        parser.error('Real tool-configuration appearance checks require --backend fzf.')
    if args.feature != 'theme' and args.backend != 'fzf':
        parser.error('Module and backup browsers require --backend fzf.')
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        parser.error('Run from your real terminal, not a pipe.')
    bash = shutil.which('bash')
    picker = shutil.which(args.backend) if args.backend != 'numbered' else None
    if not bash or (args.backend != 'numbered' and not picker):
        parser.error('Requested Bash/picker executable is unavailable; nothing installed.')
    root = Path(__file__).resolve().parent.parent
    with tempfile.TemporaryDirectory(prefix='blastoff-visual-') as directory:
        home = Path(directory)
        store = home/'store'; themes = store/'themes'; themes.mkdir(parents=True)
        config = home/'starship.toml'; original = b'format="$all"\n'; config.write_bytes(original)
        for name, color in [('alpha','purple'),('beta','blue')]:
            (themes/(name+'.toml')).write_text('[directory]\nstyle="'+color+'"\n')
        tools = home/'bin'; tools.mkdir()
        if picker:
            (tools/args.backend).symlink_to(picker)
        if shutil.which('bat'):
            (tools/'bat').symlink_to(shutil.which('bat'))
        env = dict(os.environ,HOME=str(home),USERPROFILE=str(home),PATH=str(tools),
                   XDG_CONFIG_HOME=str(home/'xdg'),XDG_CACHE_HOME=str(home/'cache'),
                   STARSHIP_CACHE=str(home/'starship-cache'),STARSHIP_CONFIG=str(config),
                   BLASTOFF_HOME=str(store),BLASTOFF_PYTHON=sys.executable)
        if args.tool_config == 'user':
            env = dict(os.environ, STARSHIP_CACHE=str(home/'starship-cache'),
                       STARSHIP_CONFIG=str(config),BLASTOFF_HOME=str(store),BLASTOFF_PYTHON=sys.executable)
        else:
            # Deterministic fixtures must not inherit config paths into real HOME.
            for key in tuple(env):
                if key.startswith(('BAT_','FZF_')): env.pop(key)
            env.update(XDG_STATE_HOME=str(home/'state'),XDG_DATA_HOME=str(home/'data'))
        if args.feature == 'module':
            (store/'modules').mkdir()
            (store/'modules/alpha.toml').write_text('[directory]\nstyle="purple"\n')
        if args.feature == 'backup':
            for _ in range(3):
                subprocess.run([bash,str(root/'bin/blastoff'),'backup','create'],env=env,check=True)
        before = {str(p.relative_to(home)):hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in [config,*store.rglob('*')] if p.is_file()}
        print('Source runtime:',root/'lib/blastoff.py', 'version:',(root/'VERSION').read_text().strip())
        print('Tool configuration:',args.tool_config,'; NO_COLOR:', 'present' if 'NO_COLOR' in env else 'absent')
        print('fzf:',picker,'; bat:',shutil.which('bat'))
        print('Temporary sandbox:',home)
        print('Use a 40- or 50-column terminal. Select alpha/beta, or cancel as requested.')
        print('Numbered: blank line, Escape then Enter, EOF, or Ctrl-C cancels.')
        print('fzf/gum: Escape or Ctrl-C cancels. Report clipping, key behavior, and result.')
        print('fzf: Ctrl-X toggles the visible preview; resize across 100 columns. Backup: Tab/Shift-Tab select, then confirm y/N.')
        # Wait through terminal SIGINT so the child can return cancellation status.
        import signal
        old = signal.signal(signal.SIGINT, lambda *_: None)
        try:
            command = ['pick'] if args.feature=='theme' else ['module','show'] if args.feature=='module' else ['backup','delete','--pick']
            command += ['--fzf'] if args.fzf else ['--fancy',args.fancy] if args.fancy else []
            command += ['--verbose']
            code = subprocess.call([bash,str(root/'bin/blastoff'),*command],env=env)
        finally:
            signal.signal(signal.SIGINT,old)
        after = {str(p.relative_to(home)):hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in [config,*store.rglob('*')] if p.is_file()}
        if args.expect == 'cancel':
            okay = code == 130 and before == after
        else:
            okay = code == 0 and (config.read_bytes() in [p.read_bytes() for p in themes.glob('*.toml')] if args.feature=='theme' else before==after if args.feature=='module' else config.read_bytes()==original and set(after)<set(before) and all(before[key]==value for key,value in after.items()))
        print('PASS' if okay else 'FAIL', 'exit='+str(code), 'expected='+args.expect,
              'config/storage unchanged='+str(before == after))
        return 0 if okay else 1

if __name__ == '__main__':
    raise SystemExit(main())

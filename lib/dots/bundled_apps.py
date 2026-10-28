"""Bundled application boundary and inert completion; no backend discovery."""
import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
FAMILIES = ('blastoff', 'pkgs')


def run(root, family, arguments):
    if family not in FAMILIES:
        raise ValueError('unknown bundled application')
    entry = Path(root) / 'plugins' / ('blastoff/lib/blastoff.py' if family == 'blastoff' else 'pkgs/main.py')
    runtime = (os.environ.get('BLASTOFF_PYTHON') or sys.executable) if family == 'blastoff' else sys.executable
    if not shutil.which(runtime):
        print(f'{family}: Python runtime unavailable: {runtime}', file=sys.stderr)
        return 3
    if os.name == 'nt' and Path(runtime).suffix.lower() in ('.cmd', '.bat', '.ps1'):
        print(f'{family}: Python runtime must be a native executable: {runtime}', file=sys.stderr)
        return 3
    if family == 'blastoff' and os.environ.get('DOTS_POWERSHELL'):
        # Preserve Blastoff's native aliases, host check and picker-shell context.
        envelope = dict(version=1, host=os.name, shell=os.environ['DOTS_POWERSHELL'], argv=list(arguments))
        arguments = ['--_powershell-argv-v1', base64.b64encode(json.dumps(envelope).encode()).decode('ascii')]
    command = [runtime, '-B', *(['-I'] if family == 'blastoff' else []), str(entry), *arguments]
    status = subprocess.call(command)
    return status if status >= 0 else 128 - status


def complete(root, words):
    """Use generated metadata only; completion never launches an application."""
    if not words or words[0] not in FAMILIES:
        return 0
    rows = json.loads((Path(root)/'lib/dots/metadata/bundled-apps.json').read_text())
    family, *tail = words
    current = tail.pop() if tail else ''
    stem = family
    positionals = []
    expected = None
    literal = False
    for word in tail:
        if expected:
            expected = None
            continue
        if word == '--':
            literal = True
            continue
        option = next((r for r in rows[stem]['option'] if word in r[:2]), None)
        if not literal and option:
            if option[2] != 'flag': expected = option[2]
        elif not literal and word.startswith('-'):
            continue
        elif not literal and not positionals and stem+'-'+word in rows:
            stem += '-'+word
        else:
            positionals.append(word)
    suggestions = []
    def add(value, description=''):
        if value.startswith(current) and not any(c in value+description for c in '\t\r\n'):
            suggestions.append(('candidate', value, description))
    def values(kind, prefix=''):
        if kind.startswith('choice:'):
            for value in kind[7:].split(','): add(prefix+value)
        elif kind in ('file', 'directory'): suggestions.append((kind, '', ''))
    row = rows[stem]
    if expected:
        values(expected)
    elif not literal and current.startswith('-'):
        flag, sep, _ = current.partition('=')
        if sep:
            for long, short, kind, _ in row['option']:
                if flag == long: values(kind, flag+'=')
        else:
            for long, short, _, description in row['option']:
                add(long, description)
                if short: add(short, description)
    else:
        if not positionals and not literal:
            for key, child in rows.items():
                if key.startswith(stem+'-') and '-' not in key[len(stem)+1:]:
                    add(key[len(stem)+1:], child['summary'])
        for number, kind, description in row['argument']:
            if int(number) == len(positionals)+1: values(kind)
    for record in dict.fromkeys(suggestions):
        print('\t'.join(record))
    return 0


if __name__ == '__main__':
    sys.exit(complete(ROOT, sys.argv[1:]))

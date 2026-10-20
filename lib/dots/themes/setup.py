#!/usr/bin/env python3
"""Inactive native setup preparation; caller owns publication locks and journal."""
import os
from pathlib import Path
import sys
import uuid

from palette_native import Themes, regular
from theme_cli import generated_commands, shell_init, validate_pointers, generation_complete
from transactions import private_directory
from file_platform import sync_dir


def main(args):
    if sys.version_info < (3, 11): raise ValueError('theme preparation requires Python 3.11 or newer')
    themes = Themes()
    identity = themes.current()
    fingerprint = themes.fingerprint(identity)
    validate_pointers(themes)
    token = themes.state / 'themes/current'
    current = regular(token).decode().strip() if token.exists() else ''
    incomplete = ''
    if current:
        generation = themes.state / 'themes/generations' / current
        if not generation_complete(themes, generation) or regular(generation / 'fingerprint').decode().strip() != fingerprint:
            incomplete = 'theme inputs changed'
    if args == ['inspect']:
        values = [identity, fingerprint, current, incomplete]
    elif len(args) == 2 and args[0] == 'prepare':
        if args[1] != fingerprint: raise ValueError('theme inputs changed after preview')
        directory = themes.state / 'themes/generations' / ('g.' + uuid.uuid4().hex)
        private_directory(directory)
        palette = themes.render(identity, directory, build_cache=True)
        for shell, suffix in (('powershell', 'ps1'), ('zsh', 'zsh'), ('fish', 'fish')):
            (directory / ('init.' + suffix)).write_text(shell_init(palette, shell), encoding='utf-8')
        generated_commands(themes, directory)
        (directory / 'status').write_text('committed\n')
        if themes.fingerprint(identity) != fingerprint: raise ValueError('theme inputs changed during preparation')
        # Preparation never changes live pointers or invokes app reloads/plugins.
        for path in directory.rglob('*'):
            if path.is_file():
                with path.open('rb') as stream: os.fsync(stream.fileno())
        sync_dir(directory)
        values = [str(directory), str(directory / 'commands'), '']
    else: raise ValueError('invalid native setup operation')
    sys.stdout.buffer.write(('\0'.join(values) + '\0').encode('utf-8'))


if __name__ == '__main__':
    try: main(sys.argv[1:])
    except (OSError, ValueError) as error:
        print('dots setup: ' + str(error), file=sys.stderr)
        sys.exit(1)

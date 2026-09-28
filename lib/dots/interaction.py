"""Lazy optional interaction bridge shared by Python command controllers."""
import os
from pathlib import Path
import shutil
import subprocess
import sys


class SelectionEnded(Exception):
    def __init__(self, status=0):
        self.status = status


class Selector:
    def __init__(self, backend=None, stream=None):
        self.stream = stream if stream is not None else sys.stdout
        self.bridge = Path(__file__).with_name('interactive-select.bash')
        self.backend = backend if backend is not None else self.run('detect')
        if self.backend not in ('gum', 'fzf', 'plain'):
            raise ValueError('unknown interactive backend')

    def run(self, *args):
        sys.stdout.flush()
        sys.stderr.flush()
        # The bridge keeps its result pipe separate from its terminal UI.
        result = subprocess.run(['bash', str(self.bridge), *args],
                                stdout=subprocess.PIPE, stderr=self.stream, text=True)
        if result.returncode:
            raise SelectionEnded(130 if result.returncode in (-2, 130) else 1)
        return result.stdout.rstrip('\n')

    def pick(self, kind, header, choices, initial=''):
        result = self.run(self.backend, kind, header, initial, *choices)
        if result not in choices:
            raise ValueError('selector returned an unknown choice')
        return result


def gum_confirm(header, action='Apply'):
    """Return approval, or None when the caller should use its existing prompt.

    Capability checks happen only here, after caller-specific JSON/yes/dry-run
    handling. A failed or interrupted selector never falls through to a prompt.
    """
    if (os.environ.get('TERM', 'dumb') == 'dumb'
            or not all(stream.isatty() for stream in (sys.stdin, sys.stdout, sys.stderr))
            or not shutil.which('bash') or not shutil.which('gum')):
        return None
    try:
        return Selector('gum', sys.stderr).pick(
            'choose', header, ['Cancel', action], 'Cancel') == action
    except SelectionEnded as exc:
        if exc.status == 130:
            raise KeyboardInterrupt from None
        raise ValueError('confirmation selector failed; no approval received') from None

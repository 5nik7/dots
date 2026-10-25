"""Lazy optional interaction bridge shared by Python command controllers."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import re


def terminal():
    return all(stream.isatty() for stream in (sys.stdin, sys.stdout, sys.stderr))


def native_shell():
    return os.environ.get('DOTS_POWERSHELL') or shutil.which('pwsh') or shutil.which('powershell')


def rich_fzf_available():
    if not shutil.which('fzf'):
        return False
    if os.name != 'nt':
        return bool(shutil.which('bash'))
    if not native_shell():
        return False
    # Old fzf Windows versions only support cmd previews. Do not interpolate
    # paths into cmd syntax or start a UI whose previews cannot work.
    try:
        return b'--with-shell' in subprocess.run(['fzf', '--help'], capture_output=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        return False


def selection_requested(parser, args, operands, supported=True):
    """Validate explicit selection before inventory reads or any terminal UI."""
    explicit = getattr(args, 'pick', False)
    if explicit:
        if not supported:
            parser.error('--pick is not supported by this action')
        if getattr(args, 'yes', False) or getattr(args, 'json', False):
            parser.error('--pick cannot be combined with --yes or --json')
        if not terminal():
            parser.error('--pick requires terminal input and output')
        if getattr(args, 'directory_link', False):
            parser.error('--directory-link requires explicit directory paths without --pick')
        if operands and args.action != 'add':
            parser.error('--pick cannot be combined with resource IDs')
        if getattr(args, 'new', False):
            parser.error('--pick selects existing resources; use --new without --pick')
    auto = (supported and not operands and not getattr(args, 'new', False)
            and not getattr(args, 'scan', False)
            and not any(getattr(args, name, False) for name in ('yes', 'json', 'dry_run'))
            and terminal())
    if auto and getattr(args, 'directory_link', False):
        parser.error('--directory-link requires explicit directory paths')
    return explicit or auto


class SelectionEnded(Exception):
    def __init__(self, status=0):
        self.status = status


class Selector:
    def __init__(self, backend=None, stream=None):
        self.stream = stream if stream is not None else sys.stdout
        self.bridge = Path(__file__).with_name('interactive-select.bash')
        if os.name == 'nt':
            self.backend = backend or ('gum' if shutil.which('gum') else 'fzf' if shutil.which('fzf') else 'plain')
        else:
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
        result = self.native_pick(kind, header, choices, initial) if os.name == 'nt' else self.run(self.backend, kind, header, initial, *choices)
        if result not in choices:
            raise ValueError('selector returned an unknown choice')
        return result

    def native_pick(self, kind, header, choices, initial):
        if not terminal():
            raise ValueError('selection requires terminal input and output')
        if self.backend == 'plain' or (self.backend == 'fzf' and kind == 'choose'):
            print(header, file=self.stream)
            for number, choice in enumerate(choices, 1):
                print(f'  {number}) {choice}', file=self.stream)
            answer = input('Number [1]: ').strip() or '1'
            if answer == '\x1b':
                raise SelectionEnded(130)
            if not answer.isdecimal() or not 1 <= int(answer) <= len(choices):
                raise ValueError('invalid selection')
            return choices[int(answer) - 1]
        env = dict(os.environ, FZF_DEFAULT_OPTS='', FZF_DEFAULT_OPTS_FILE='')
        from resources import Resources, read_data
        mode = env.get('DOTS_COLOR', 'auto')
        colored = mode == 'always' or (mode == 'auto' and terminal() and not env.get('NO_COLOR'))
        if colored:
            env.pop('NO_COLOR', None)
            env.update(CLICOLOR='1', CLICOLOR_FORCE='1', FORCE_COLOR='1')
            for line in read_data(Resources().root / 'gum_env.sh').splitlines():
                match = re.fullmatch(r"export ((?:GUM_[A-Z_]+|FOREGROUND|BACKGROUND|BORDER_FOREGROUND|BORDER_BACKGROUND))='(#[a-fA-F0-9]{6})'", line)
                if match: env[match[1]] = match[2]
        else: env.update(NO_COLOR='1', CLICOLOR='0', CLICOLOR_FORCE='0', FORCE_COLOR='0')
        if env.get('DOTS_ICONS') == 'never':
            env.update(GUM_CHOOSE_CURSOR='>', GUM_FILTER_INDICATOR='>',
                       GUM_FILTER_SELECTED_PREFIX='* ', GUM_FILTER_UNSELECTED_PREFIX='  ')
        if self.backend == 'gum':
            flags = ['gum', 'filter' if kind == 'filter' else 'choose', '--header=' + header]
            if kind == 'choose' and initial:
                flags += ['--selected=' + initial]
        else:
            flags = ['fzf', '--no-multi', '--header=' + header, '--bind=esc:abort,ctrl-c:abort']
            if not colored: flags += ['--color=bw']
            if env.get('DOTS_ICONS') == 'never': flags += ['--no-unicode']
        result = subprocess.run(flags, input=('\n'.join(choices) + '\n').encode('utf-8'),
                                stdout=subprocess.PIPE, stderr=self.stream, env=env)
        if result.returncode:
            raise SelectionEnded(130 if result.returncode in (-2, 130) else 1)
        return result.stdout.decode('utf-8').rstrip('\r\n')


class RichSelector:
    """Scoped FZF-first, token-based selection; never approves an operation."""
    def __init__(self):
        if (os.name == 'nt' or os.environ.get('TERM', 'dumb') != 'dumb') and rich_fzf_available():
            self.backend = 'fzf'
        elif (os.name == 'nt' or os.environ.get('TERM', 'dumb') != 'dumb') and shutil.which('gum') and (os.name == 'nt' or shutil.which('bash')):
            self.backend = 'gum'
        else:
            self.backend = 'plain'

    def pick(self, title, labels, multi=False, preview=None, color=False, icons=False, colors=''):
        from progress import permanent_output
        if not terminal():
            raise ValueError('selection requires terminal input and output; supply explicit operands')
        if not labels:
            return []
        with permanent_output():
            if self.backend == 'fzf':
                return self.fzf(title, labels, multi, preview, color, icons, colors)
            return self.fallback(title, labels, multi)

    def fzf(self, title, labels, multi, preview, color, icons, colors, popup=False, query='',
            height=None, preview_size=55, header=None):
        flags = ['fzf', '--read0', '--print0', '--ansi', '--delimiter=\t',
                 '--with-nth=2..', '--layout=reverse', '--no-height',
                 '--multi' if multi else '--no-multi', '--prompt=' + title + ': ',
                 '--bind=esc:abort,ctrl-c:abort', '--header=Enter: review  Esc: cancel']
        keys = 'Enter: review  Esc: cancel'
        if popup:
            flags += ['--popup', popup if isinstance(popup, str) else 'center,90%']
        elif height is not None:
            flags += ['--height=' + str(height)]
        if query:
            flags += ['--query=' + query]
        if multi:
            flags += ['--bind=tab:toggle+down,btab:toggle+up,ctrl-a:select-all,ctrl-d:deselect-all']
            keys += '\nTab: mark  Shift-Tab: mark/up\nCtrl-A: all matches  Ctrl-D: clear'
        if preview:
            # Preview commands contain only environment references and a numeric token.
            flags += ['--preview=' + preview[0],
                      '--preview-window=' + ('down,' if shutil.get_terminal_size().columns < 100 else 'right,') + str(preview_size) + '%',
                      '--bind=alt-p:toggle-preview,alt-j:preview-down,alt-k:preview-up']
            if preview[1]:
                flags += ['--bind=alt-c:execute-silent(' + preview[1] + ')+refresh-preview']
                keys += '\nAlt-C: change preview view'
            keys += '\nAlt-P: pane  Alt-J/K: scroll'
        flags = [f for f in flags if not f.startswith('--header=')] + ['--header=' + (keys if header is None else header)]
        if not color:
            flags += ['--color=bw']
        elif colors:
            flags += ['--color=' + colors]
        if not icons:
            flags += ['--no-unicode']
        env = dict(os.environ, FZF_DEFAULT_OPTS='', FZF_DEFAULT_OPTS_FILE='',
                   FZF_DEFAULT_COMMAND='', BASH_ENV='', ENV='')
        if os.name == 'nt':
            flags += ['--with-shell=' + subprocess.list2cmdline([native_shell(), '-NoLogo', '-NoProfile', '-NonInteractive', '-Command'])]
        else:
            env['SHELL'] = shutil.which('bash')
        if color:
            env.pop('NO_COLOR', None)
            env.update(CLICOLOR='1', CLICOLOR_FORCE='1', FORCE_COLOR='1')
        else:
            env.update(NO_COLOR='1', CLICOLOR='0', CLICOLOR_FORCE='0', FORCE_COLOR='0')
        if preview:
            env.update(preview[2])
        sys.stdout.flush()
        sys.stderr.flush()
        # Display text is inert and single-line; only the first field is an identity.
        data = b'\0'.join((str(i) + '\t' + label).encode() for i, label in enumerate(labels)) + b'\0'
        result = subprocess.run(flags, input=data, stdout=subprocess.PIPE, stderr=sys.stderr, env=env)
        if result.returncode:
            if result.returncode in (-2, 130):
                raise SelectionEnded(130)
            raise ValueError('Interactive selector failed; no selection was accepted.')
        selected = []
        for line in result.stdout.split(b'\0'):
            if not line:
                continue
            token = line.partition(b'\t')[0]
            if not re.fullmatch(rb'0|[1-9][0-9]*', token) or int(token) >= len(labels):
                raise ValueError('selector returned an unknown resource')
            index = int(token)
            if index not in selected:
                selected.append(index)
        if not selected:
            raise SelectionEnded(130)
        if not multi and len(selected) != 1:
            raise ValueError('selector returned multiple resources')
        return selected

    def fallback(self, title, labels, multi):
        # Index prefixes disambiguate even identical sanitized display labels.
        labels = [re.sub(r'\x1b\[[0-9;]*m', '', label) for label in labels]
        selected = []
        while True:
            choices = ['Cancel']
            if multi and selected:
                choices.append('Review selected')
            mapping = {}
            for i, label in enumerate(labels):
                if i not in selected:
                    name = str(i + 1) + ': ' + label
                    choices.append(name)
                    mapping[name] = i
            if self.backend == 'gum':
                choice = Selector('gum').pick('filter', title, choices)
            elif os.name != 'nt' and shutil.which('bash'):
                choice = Selector('plain').pick('choose', title, choices, choices[0])
            else:
                print(title)
                for i, label in enumerate(choices, 1):
                    print(f'  {i}) {label}')
                answer = input('Number [1]: ').strip() or '1'
                if answer == '\x1b':
                    raise SelectionEnded(130)
                if not answer.isdecimal() or not 1 <= int(answer) <= len(choices):
                    raise ValueError('invalid selection')
                choice = choices[int(answer) - 1]
            if choice == 'Cancel':
                raise SelectionEnded(130)
            if choice == 'Review selected':
                return selected
            selected.append(mapping[choice])
            if not multi:
                return selected


def gum_confirm(header, action='Apply', cancel='Cancel'):
    """Return approval, or None when the caller should use its existing prompt.

    Capability checks happen only here, after caller-specific JSON/yes/dry-run
    handling. A failed or interrupted selector never falls through to a prompt.
    """
    if ((os.name != 'nt' and os.environ.get('TERM', 'dumb') == 'dumb')
            or not all(stream.isatty() for stream in (sys.stdin, sys.stdout, sys.stderr))
            or (os.name != 'nt' and not shutil.which('bash')) or not shutil.which('gum')):
        return None
    try:
        return Selector('gum', sys.stderr).pick(
            'choose', header, [cancel, action], cancel) == action
    except SelectionEnded as exc:
        if exc.status == 130:
            raise KeyboardInterrupt from None
        raise ValueError('confirmation selector failed; no approval received') from None

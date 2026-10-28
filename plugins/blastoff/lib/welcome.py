"""Shared welcome/help presentation; optional local artwork, never discovery."""
import json
import os
import sys
import stat
import textwrap

_DESCRIPTION = 'Starship theme manager'
_EXAMPLES = (
    ('blastoff list', 'Browse themes and presets'),
    ('blastoff pick', 'Choose and apply a theme'),
    ('blastoff current', 'Show the active config'),
    ('blastoff --help', 'Explore all commands'),
)


def _columns():
    try:
        columns = int(os.environ.get('COLUMNS', ''))
        if columns > 0:
            return columns
    except ValueError:
        pass
    try:
        return max(1, os.get_terminal_size(sys.stdout.fileno()).columns)
    except (AttributeError, OSError, ValueError):
        return 80


def _colored(color, json_output):
    if color not in ('auto', 'always', 'never'):
        raise ValueError('color must be auto, always, or never')
    return not json_output and 'NO_COLOR' not in os.environ and (
        color == 'always' or (color == 'auto' and sys.stdout.isatty()
                              and os.environ.get('TERM') != 'dumb'))


def _wrap(text, width, accent=None, colored=False, indent=''):
    # Wrap before adding ANSI; even tiny widths must remain valid.
    indent = indent if len(indent) < width else ''
    rows = textwrap.wrap(text, width=max(1, width-len(indent)), break_on_hyphens=False)
    return [indent + ('\x1b['+accent+'m'+row+'\x1b[0m' if colored and accent else row)
            for row in rows]


def _artwork(width, json_output):
    # Never replay .ansi or logo scripts (some contain cursor-control codes).
    # Only bounded, validated Block Elements/Braille artwork beside the core.
    if json_output or width < 1 or not sys.stdout.isatty() or os.environ.get('TERM') == 'dumb':
        return []
    encoding = getattr(sys.stdout, 'encoding', None)
    if not encoding:
        return []
    for filename in ('logo',):
        try:
            path = os.path.join(os.path.dirname(__file__), 'artwork', filename)
            if os.path.islink(path):
                continue
            fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NONBLOCK', 0) | getattr(os, 'O_NOFOLLOW', 0))
            try:
                if not stat.S_ISREG(os.fstat(fd).st_mode):
                    continue
                with os.fdopen(fd, 'rb', closefd=False) as f:
                    raw = f.read(8193)
            finally:
                os.close(fd)
            if len(raw) > 8192:
                continue
            text = raw.decode('utf-8')
            text.encode(encoding)
            # Spaces and one-cell Block Elements/Braille only, never controls,
            # escape sequences, combining marks, bidi text or executable content.
            if any(c not in ' \n' and not (0x2580 <= ord(c) <= 0x259f or
                                         0x2800 <= ord(c) <= 0x28ff) for c in text):
                continue
            rows = text.splitlines()
            if rows and len(rows) <= 16 and max(map(len, rows)) <= width:
                return rows
        except (OSError, UnicodeError, LookupError):
            pass
    return []


def header(version, color='auto', json_output=False, width=None):
    width = _columns() if width is None else width
    colored = _colored(color, json_output)
    art = _artwork(width, json_output)
    rows = []
    if art:
        span = max(map(len, art))-1 or 1
        for line in art:
            if colored:
                pieces = []
                for i, char in enumerate(line):
                    rgb = tuple(round(a+(b-a)*i/span) for a,b in zip((101,30,255),(255,67,191)))
                    pieces.append('\x1b[38;2;%d;%d;%dm%s' % (*rgb, char))
                rows.append(''.join(pieces)+'\x1b[0m')
            else:
                rows.append(line)
        rows += _wrap('BLASTOFF', width, '95', colored)
    else:
        rows += _wrap('>>> BLASTOFF' if width >= 12 else 'BLASTOFF', width, '95', colored)
    rows += _wrap('Version '+version, width, '35', colored)
    rows += _wrap(_DESCRIPTION, width)
    return rows


def render(version, color='auto', json_output=False):
    colored = _colored(color, json_output)
    if json_output:
        print(json.dumps({'name':'blastoff', 'version':version, 'description':_DESCRIPTION,
                          'examples':[{'command':c, 'description':d} for c,d in _EXAMPLES]}))
        return
    width = _columns()
    rows = header(version, color, width=width) + ['']
    for command, description in _EXAMPLES:
        rows += _wrap(command, width, '95', colored)
        if width >= 40:
            rows += _wrap(description, width, indent='  ')
    print('\n'.join(rows))


def format_help(parser, version, color='auto', json_output=False):
    """Present the actual argparse grammar, without duplicated choice braces."""
    width = _columns()
    colored = _colored(color, json_output)
    rows = header(version, color, json_output, width) + ['']

    def section(title):
        if rows and rows[-1]:
            rows.append('')
        rows.extend(_wrap(title, width, '1;35', colored))

    def entry(label, description):
        rows.extend(_wrap(label, width, '95', colored, indent='  '))
        if description and description != '==SUPPRESS==':
            rows.extend(_wrap(description, width, indent='    '))

    positionals = [a for a in parser._actions if not a.option_strings and a.help != '==SUPPRESS==']
    groups = [a for a in positionals if isinstance(a.choices, dict)]
    section('Usage')
    operands = []
    for action in positionals:
        label = (action.metavar or action.dest).upper()
        if isinstance(action.choices, dict):
            label += ' [args]'
        elif action.nargs == '?':
            label = '['+label+']'
        operands.append(label)
    rows += _wrap(parser.prog+' [options]'+(' '+' '.join(operands) if operands else ''), width, '95', colored, indent='  ')
    if parser.description:
        rows.append('')
        rows += _wrap(parser.description, width)
    for action in groups:
        descriptions = {a.dest:a.help for a in action._choices_actions}
        items = action.choices
        if parser.prog == 'blastoff':
            grouping = [('Browse & choose', ('list','current','pick')),
                        ('Themes & modules', ('theme','preset','module','migrate')),
                        ('Backup & recovery', ('backup',)),
                        ('Diagnostics & integration', ('doctor','completion'))]
            covered = {name for _, names in grouping for name in names}
            grouping.append(('Other commands', tuple(n for n in items if n not in covered)))
        else:
            grouping = [('Commands', tuple(items))]
        for title, names in grouping:
            names = [n for n in names if n in items]
            if not names:
                continue
            section(title)
            for name in names:
                entry(name, descriptions.get(name) or items[name].description)
    ordinary = [a for a in positionals if a not in groups]
    if ordinary:
        section('Arguments')
        for action in ordinary:
            description = action.help or ''
            if action.choices:
                description += ' Choices: '+' | '.join(str(v) for v in action.choices)+'.'
            entry((action.metavar or action.dest).upper(), description)
    options = [a for a in parser._actions if a.option_strings and a.help != '==SUPPRESS==']
    if options:
        section('Options')
        for action in options:
            label = ', '.join(action.option_strings)
            if action.nargs != 0:
                label += ' '+(' | '.join(map(str, action.choices)) if action.choices else (action.metavar or action.dest.upper()))
            entry(label, action.help)
    if parser.epilog:
        section('Aliases' if parser.epilog.startswith('Aliases: ') else 'Global options & notes')
        rows += _wrap(parser.epilog.removeprefix('Aliases: '), width)
    return '\n'.join(rows)+'\n'

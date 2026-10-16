#!/usr/bin/env python3
"""Bounded theme-colored human panels; data interfaces never call this renderer."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import textwrap
import unicodedata

SGR = re.compile(r'\x1b\[[0-9;:]*m')


def clean(text, keep_sgr=False):
    def printable(part):
        return ''.join(c for c in part if c in '\n\t' or ord(c) >= 32 and not 127 <= ord(c) < 160)
    parts, start = [], 0
    for match in SGR.finditer(text):
        parts.append(printable(text[start:match.start()]))
        if keep_sgr:
            parts.append(match[0])
        start = match.end()
    parts.append(printable(text[start:]))
    return ''.join(parts)


def has_color(text):
    for match in SGR.finditer(text):
        fields = match[0][2:-1].split(';')
        index = 0
        while index < len(fields):
            field = fields[index].split(':')
            code = int(field[0] or 0)
            if 30 <= code <= 37 or 40 <= code <= 47 or 90 <= code <= 97 or 100 <= code <= 107:
                return True
            if code in (38, 48, 58):
                args = field[1:] if len(field) > 1 else fields[index + 1:]
                if args and args[0] in ('2', '5'):
                    if code in (38, 48):
                        return True
                    # Underline-color payload is not a foreground/background code.
                    if len(field) == 1:
                        index += 4 if args[0] == '2' else 2
            index += 1
    return False


def print_authored_logo(logo, indent=''):
    # Keep cross-line SGR state intact, isolating the whole block from the help.
    print('\x1b[0m' + '\n'.join(indent + line for line in logo.rstrip('\n').split('\n')) + '\x1b[0m')


def width(text):
    return sum(0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in 'WF' else 1 for c in SGR.sub('', text))


def escape(color, bg=False):
    return '\x1b[%s;2;%d;%d;%dm' % ('48' if bg else '38', *(int(color[i:i+2], 16) for i in (1, 3, 5)))


def luminance(color):
    channels = [int(color[i:i+2], 16) / 255 for i in (1,3,5)]
    return sum((c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4) * w for c,w in zip(channels,(.2126,.7152,.0722)))


def readable(color, bg, fallback):
    a,b = sorted((luminance(color), luminance(bg)))
    return color if (b + .05) / (a + .05) >= 4.5 else fallback


def color_enabled():
    mode = os.environ.get('DOTS_COLOR', 'auto')
    return mode == 'always' or mode == 'auto' and sys.stdout.isatty() and os.environ.get('TERM', 'dumb') != 'dumb' and not os.environ.get('NO_COLOR')


def display(value):
    """One inert table cell; data APIs never pass through this function."""
    return clean(str(value)).replace('\n', '\\n').replace('\t', '\\t')


class ColorView:
    """Shared palette/style tables, sized in terminal cells, with plain fallbacks."""

    def __init__(self, colors=None):
        colors = colors or {}
        self.columns = max(12, min(120, shutil.get_terminal_size((80, 24)).columns))
        self.available = self.columns - 4
        self.base = self.accent = self.normal = self.reset = ''
        fg, bg = colors.get('foreground'), colors.get('background')
        if color_enabled() and all(isinstance(c, str) and re.fullmatch(r'#[0-9a-fA-F]{6}', c) for c in (fg, bg)):
            fg = readable(fg, bg, '#000000' if luminance(bg) > .179 else '#ffffff')
            self.base = escape(bg, True)
            self.normal = escape(fg)
            self.accent = escape(readable(colors.get('accent', fg), bg, fg))
            self.reset = '\x1b[0m'

    def line(self, text='', heading=False, indent=0):
        # Wrap by visible cells, including wide/combining Unicode and SGR swatches.
        prefix = self.base + (self.accent + '\x1b[1m' if heading and self.base else self.normal)
        room = max(1, self.available - indent)
        parts, part, cells = [], '', 0
        for token in re.findall(r'\x1b\[[0-9;:]*m|[^\x1b]', text):
            size = width(token)
            if cells + size > room and cells:
                parts.append(part); part, cells = '', 0
            part += token; cells += size
        parts.append(part)
        for part in parts:
            content = ' ' * indent + part
            padding = ' ' * max(0, self.available - width(content)) if self.base else ''
            print(prefix + '  ' + content + padding + ('  ' if self.base else '') + self.reset)

    def title(self, title, source=None):
        self.line(display(title), heading=True)
        if source:
            self.line('Source: ' + display(source))

    def section(self, title, count):
        self.line()
        self.line(f'{title} ({count})', heading=True)

    def color(self, value):
        if value is None:
            return 'unset'
        label = f'index {value}' if isinstance(value, int) else display(value)
        code = ''
        if self.base:
            if isinstance(value, str) and re.fullmatch(r'#[0-9a-fA-F]{6}', value):
                code = escape(value, True)
            elif isinstance(value, int) and 0 <= value <= 255:
                code = f'\x1b[48;5;{value}m'
        return code + '  ' + self.base + self.normal + ' ' + label if code else label

    def table(self, headers, rows):
        if not rows:
            self.line('No entries.')
            return
        sizes = [max(width(row[i]) for row in [headers, *rows]) for i in range(len(headers))]
        if sum(sizes) + 2 * (len(sizes) - 1) <= self.available:
            for row in [headers, *rows]:
                text = '  '.join(cell + ' ' * (size - width(cell)) for cell, size in zip(row, sizes)).rstrip()
                self.line(text, heading=row is headers)
        else:
            for row in rows:
                self.line(row[0], heading=True)
                for name, value in zip(headers[1:], row[1:]):
                    self.line(name + ': ' + value, indent=2)

    def palette(self, colors, native=False):
        terminal = {f'color{i}' for i in range(16)}
        groups = [('Native colors', sorted(colors))] if native else [
            ('Named colors', sorted(k for k, v in colors.items() if isinstance(v, str) and k not in terminal)),
            ('Terminal colors', [f'color{i}' for i in range(16) if f'color{i}' in colors])]
        for title, keys in groups:
            self.section(title, len(keys))
            self.table(['Name', 'Color'], [[display(k), self.color(colors[k])] for k in keys])

    def styles(self, title, entries, sequences=None):
        # Lists preserve parser suffix priority, including duplicate rules.
        self.section(title, len(entries))
        rows = []
        for index, (key, style) in enumerate(entries):
            attrs = ', '.join(display(k) + ('=false' if v is False else '')
                              for k, v in sorted(style.items()) if k not in ('fg', 'bg')) or 'none'
            rows.append([display(key), self.color(style.get('fg')), self.color(style.get('bg')), attrs])
            if sequences is not None:
                rows[-1].append(display(sequences[index]) or '(empty)')
        self.table(['Name', 'Foreground', 'Background', 'Attributes'] + (['Sequence'] if sequences is not None else []), rows)

    def fields(self, fields):
        for key, value in fields:
            self.line(display(key) + ': ' + display(value))


STYLE_TITLES = {'type': 'File types', 'mime': 'MIME rules', 'extension': 'Extension rules'}


def render_colors(doc, source, action=None, result=None, context=None):
    view = ColorView(doc['colors'])
    view.title(f"{doc['id']} ({doc['mode']})", source)
    if action is None:
        view.palette(doc['colors'])
        for group, title in STYLE_TITLES.items():
            view.styles(title, sorted(doc['styles'][group].items()))
    elif action in STYLE_TITLES and not context:
        view.styles(STYLE_TITLES[action], sorted(result.items()))
    else:
        if context:
            view.fields(context.items())
        if result.get('group'):
            view.fields([('Group', result['group'])])
        view.styles('Style', [(result['key'], result['style'])])
        source = result.get('source', {})
        if isinstance(source, dict):
            view.section('Rule sources', len(source))
            view.table(['Field', 'Source'], [[display(k), display(v)] for k, v in sorted(source.items())])
        elif source:
            view.fields([('Rule source', source)])


def render_parsed(result, colors=None):
    view = ColorView(colors)
    view.title('LS_COLORS')
    for title, entries in [('Filesystem rules', list(result['types'].values())), ('Suffix rules', result['suffixes'])]:
        view.styles(title, [(entry['key'], entry['style']) for entry in entries], [entry['sequence'] for entry in entries])
    view.section('Invalid entries', len(result['invalid']))
    if result['invalid']:
        for error in result['invalid']:
            view.line(display(error))
    else:
        view.line('None.')


def main():
    p = argparse.ArgumentParser(); p.add_argument('--theme', required=True); p.add_argument('--logo'); p.add_argument('--palette', action='store_true'); p.add_argument('--native-table', action='store_true')
    args = p.parse_args()
    colored = color_enabled()
    text = sys.stdin.read()
    logo = ''
    if args.logo and not Path(args.logo).is_symlink():
        try: logo = clean(Path(args.logo).read_text()[:65536], keep_sgr=True)
        except OSError: pass
    authored = has_color(logo)
    palette = None
    if colored:
        try:
            bridge = Path(__file__).with_name('colors-query.bash')
            result = subprocess.run(['bash',str(bridge),args.theme],capture_output=True,text=True,timeout=15)
            if result.returncode: raise ValueError(result.stderr.strip())
            palette = json.loads(result.stdout)['colors']
        except (ValueError,OSError,subprocess.TimeoutExpired) as e:
            print('dots theme: palette unavailable; showing plain output: ' + str(e), file=sys.stderr)
    if args.native_table:
        data = json.loads(text)
        view = ColorView(palette)
        view.title(data['title'], 'Native palette')
        view.palette(data['colors'], native=True)
        return
    if not palette:
        if logo:
            if colored and authored: print_authored_logo(logo)
            else: print(clean(logo).rstrip())
        print(clean(text).rstrip()); return
    fg, bg = palette['foreground'], palette['background']
    fg = readable(fg,bg,'#000000' if luminance(bg) > .179 else '#ffffff')
    accent = readable(palette['accent'],bg,fg)
    muted = readable(palette['muted'],bg,fg)
    try: columns = max(12,min(120,shutil.get_terminal_size((80,24)).columns))
    except ValueError: columns=80
    panel = max(10,columns-2)
    body = clean(text).splitlines()
    lines = []
    if logo and max(map(width,logo.splitlines()),default=0) <= panel-4:
        if authored: print_authored_logo(logo, indent='  ')
        else: lines.extend((line,'logo') for line in clean(logo).rstrip().splitlines())
        lines.append(('', 'body'))
    for index,line in enumerate(body):
        kind = 'heading' if index == 0 or line.endswith(':') else 'body'
        parts = textwrap.wrap(line, width=max(8,(panel-4)//(2 if any(width(c)>1 for c in line) else 1)), replace_whitespace=False, drop_whitespace=True, break_long_words=False, break_on_hyphens=False)
        for part in [part for part in parts if part.strip()] or ['']:
            lines.append((part,kind))
    base = escape(bg,True)
    for line,kind in lines:
        # Long IDs remain whole, even if they exceed the nominal panel width.
        color = accent if kind in ('heading','logo') else muted if line.startswith('  #') else fg
        prefix = base + escape(color) + ('\x1b[1m' if kind == 'heading' else '')
        match = re.search(r'#[0-9a-fA-F]{6}',line) if args.palette else None
        if match:
            prefix += escape(match[0],True) + '  ' + base + escape(color) + ' '
        padding = max(0,panel-width(line)-4-(3 if match else 0))
        print(prefix + '  ' + line + ' '*padding + '  ' + '\x1b[0m')


if __name__ == '__main__': main()

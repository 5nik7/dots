"""Lazy shared menu data, selection and action handoff."""
from dataclasses import dataclass
from contextlib import nullcontext
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from interaction import RichSelector, SelectionEnded, terminal
from resources import cells, clean


HEADER = 'Enter: open  Esc: cancel'


@dataclass(frozen=True)
class Entry:
    id: str
    label: str
    description: str = ''
    available: bool = True
    reason: str = ''
    icon: str = ''
    icon_role: str = ''

    def __post_init__(self):
        if (not all(isinstance(v, str) and '\0' not in v for v in
                    (self.id, self.label, self.description, self.reason, self.icon))
                or not self.id or not self.label or type(self.available) is not bool
                or (not self.available and not self.reason)):
            raise ValueError('invalid menu entry')

    def document(self):
        return dict(id=self.id, label=self.label, description=self.description,
                    available=self.available, reason=self.reason)


@dataclass(frozen=True)
class Menu:
    id: str
    title: str
    entries: tuple

    def __post_init__(self):
        if not all(isinstance(v, str) and v and '\0' not in v for v in (self.id, self.title)):
            raise ValueError('invalid menu identity')
        if not isinstance(self.entries, tuple) or not all(isinstance(e, Entry) for e in self.entries):
            raise ValueError('menu entries must be an immutable sequence')
        if len({e.id for e in self.entries}) != len(self.entries):
            raise ValueError('duplicate menu entry identity')

    def filtered(self, query=''):
        terms = query.casefold().split()
        return tuple(e for e in self.entries if all(term in ' '.join(
            (e.id, e.label, e.description, e.reason)).casefold() for term in terms))

    def document(self, query=''):
        return dict(schema=1, menu=self.id, title=self.title,
                    items=[entry.document() for entry in self.filtered(query)])


def dimensions(labels, title='', header=HEADER, *, size=None):
    columns, lines = size or shutil.get_terminal_size((80, 24))
    text = [*labels, title, *header.splitlines()]
    width = max(32, max((cells(clean(label)) for label in text), default=0) + 6)
    height = len(labels) + len(header.splitlines()) + 5
    return min(width, max(1, columns - 2)), min(height, max(1, lines - 2))


def add_arguments(parser):
    parser.add_argument('--query', default='', help='Initial search text or listing filter')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--browse', dest='menu_mode', action='store_const', const='browse', help='Open the picker explicitly')
    mode.add_argument('--print', dest='menu_mode', action='store_const', const='print', help='List without selecting')
    mode.add_argument('--json', dest='menu_mode', action='store_const', const='json', help='Print versioned menu data')
    parser.set_defaults(menu_mode='auto')


def label(entry, ui):
    title = (entry.icon + ' ' if entry.icon and ui.icons else '') + entry.label
    suffix = entry.description
    if not entry.available:
        suffix += (' · ' if suffix else '') + 'unavailable: ' + entry.reason
    return clean(title + (' · ' + suffix if suffix else ''))


def entry_spans(menu,entry,ui,compact=False,shortcut=False,*,preferences=None,formatting=None):
    from style_config import current
    from config_values import value
    prefs=current() if preferences is None else preferences
    formatting=value('formatting.apps.menu',{}) if formatting is None else formatting
    overrides=formatting.get('entries',{}).get(menu.id+':'+entry.id,{})
    def span(part,text):
        fields=prefs.style('menu.'+part,app='cli') if prefs else {}
        if part=='icon' and prefs and entry.icon_role:fields.update(prefs.style('icons.'+entry.icon_role,app='cli'))
        fields.update({k:v for k,v in overrides.get(part,{}).items() if v is not None})
        return clean(text),prefs.sgr_fields(fields) if prefs else '39'
    spans=[span('icon',entry.icon+' ')] if entry.icon and ui.icons else []
    from row_layout import width as column_width, pad
    width=column_width(formatting.get('label_width',0),ui.width,
                       indent=formatting.get('indent',0)+formatting.get('padding',1),
                       gap=formatting.get('label_gap',1)) if not compact and ui.human else 0
    icon_width=cells(entry.icon+' ') if entry.icon and ui.icons else 0
    spans.append(span('label',pad(entry.label,max(0,width-icon_width),formatting.get('alignment','left'))))
    if entry.description and not compact:spans.append(span('description',' '*formatting.get('label_gap',1)+'· '+entry.description))
    if not entry.available:spans.append(span('state',' [unavailable]' if compact else ' · unavailable: '+entry.reason))
    if shortcut:spans.append(span('shortcut',' ['+entry.id+']'))
    ui.formatting=formatting
    return spans


def styled_label(menu,entry,ui,compact=False,*,preferences=None,formatting=None):
    # Large browsers may pass one render-local snapshot; ordinary callers retain
    # the same live resolution. No preference survives beyond the owning view.
    spans=entry_spans(menu,entry,ui,compact,preferences=preferences,formatting=formatting)
    prefix=ui.indentation(ui.formatting.get('indent',0))+' '*ui.formatting.get('padding',1)
    return prefix+''.join(ui.paint(text,code,**({'preferences':preferences} if preferences is not None else {})) for text,code in spans)


def listing(menu, entries, ui):
    ui.heading(menu.title)
    for entry in entries:
        spans=entry_spans(menu,entry,ui,shortcut=True)
        ui.detail_spans('',spans,label_width=0,label_gap=0,indent=ui.formatting.get('indent',0)+ui.formatting.get('padding',1))
        for _ in range(ui.formatting.get('row_gap',0)):ui.emit()
    if not entries:ui.emit('  No matching choices.')


def choose(menu, *, mode='auto', query='', context=None, ui=None, preview=None,
           compact=False, navigation=None, prompt=None, header=None):
    """Return one Entry or None after listing; selection never invokes an action."""
    if mode not in ('auto', 'browse', 'print', 'json'):
        raise ValueError('invalid menu output mode')
    if mode == 'json':
        print(json.dumps(menu.document(query), ensure_ascii=True))
        return None
    from files.catalog import Presentation
    ui = ui or Presentation()
    interactive = mode == 'browse' or (mode == 'auto' and terminal() and os.environ.get('TERM') != 'dumb')
    if not interactive:
        listing(menu, menu.filtered(query), ui)
        return None
    if context is None and not terminal():
        raise ValueError('menu browsing requires a terminal or explicit tmux context')
    if not menu.entries:
        listing(menu, (), ui)
        return None
    reason = ''
    if not shutil.which('fzf'):
        reason = 'FZF unavailable'
    else:
        from interaction import rich_fzf_available
        if not rich_fzf_available():
            reason = 'FZF preview shell unavailable'
        elif context is not None:
            result = subprocess.run(['fzf', '--help'], capture_output=True, timeout=5)
            if result.returncode or b'--popup' not in result.stdout:
                reason = 'FZF popup support unavailable'
    if reason:
        print('dots menu: ' + reason + '; listing choices without selecting.', file=sys.stderr)
        listing(menu, menu.filtered(query), ui)
        return None
    from files.picker import fzf_colors
    if context is not None:
        size = context.verify()
        ui = Presentation(ui.stream, terminal=True)
        ui.width = size[0]
    else:
        size = None
    labels = [styled_label(menu,entry,ui,compact) for entry in menu.entries]
    if header is None:
        header = 'Enter: open  Esc: back\nF1: help  Ctrl-C: quit' if navigation is not None else HEADER
    if preview:
        header += '\nAlt-P: pane  Alt-J/K: scroll'
        if preview[1]:
            header += '\nAlt-C: change preview view'
    prompt = clean(menu.title if prompt is None else prompt)
    width, height = dimensions(labels, prompt, header, size=size)
    if context:
        from menu_popup import dimensions as popup_dimensions, preferences, content_size
        options=preferences()
        content=(content_size(labels,prompt,header,size,options,automatic=(width,height))
                 if not preview and 'fit' in (options.get('width'),options.get('height')) else None)
        width,height=popup_dimensions(options,(width,height),size,content)
        ui.width=max(1,width-6)
        labels=[styled_label(menu,entry,ui,compact) for entry in menu.entries]
    scope = context.selector_environment() if context else nullcontext(None)
    from progress import permanent_output
    with permanent_output(), scope as environment:
        selected = RichSelector(backend='fzf').fzf(prompt, labels, False, preview,
            ui.color, ui.icons, fzf_colors(ui), popup=f'center,{width},{height}' if context else False,
            height=height, query=query, header=header, environment=environment, popup_resolved=context is not None,
            **({'navigation': navigation} if navigation is not None else {}))
    entry = menu.entries[selected[0]]
    if not entry.available and navigation is None:
        raise ValueError('menu entry unavailable: ' + clean(entry.reason))
    return entry


def dots_argv(arguments, *, root=None, windows=None):
    """Use the active first-party frontend without evaluating a shell string."""
    from menu_host import literal_argv
    if not isinstance(arguments, (tuple, list)):
        raise ValueError('menu command arguments must be a sequence')
    root = Path(root or os.environ.get('DOTS') or Path(__file__).resolve().parents[2])
    if not root.is_absolute():
        raise ValueError('menu checkout root must be absolute')
    windows = os.name == 'nt' if windows is None else windows
    prefix = [sys.executable, '-B', str(root / 'lib/dots/cli.py')] if windows else [str(root / 'bin/dots')]
    return literal_argv([*prefix, *arguments])


def run_action(argv, *, kind='terminal', context=None, title=None):
    """Invoke trusted controller-owned argv after selection, preserving its status."""
    from menu_host import execute, literal_argv
    command = literal_argv(argv)
    if kind not in ('terminal', 'output', 'popup', 'document'):
        raise ValueError('invalid menu terminal requirement')
    if kind == 'output':
        return review_output(command, context=context, title=title).code
    if context is not None:
        context.verify()
        if kind != 'popup':
            return context.host(command, **({'title': title} if title else {}),
                                **({'document': True} if kind == 'document' else {}))
        from dataclasses import asdict
        from menu_tmux import request_file
        with request_file(dict(schema=1, context=asdict(context))) as path:
            environment = dict(os.environ, TMUX=context.socket + ',0,0', TMUX_PANE=context.pane,
                               DOTS_MENU_CONTEXT=str(path), DOTS_KEYS_TARGET_PANE=context.pane)
            return execute(command, cwd=context.cwd, environment=environment)
    if not terminal():
        raise ValueError('menu actions require terminal input and output')
    return execute(command)


def review_output(argv, *, context=None, title=None):
    """Return command status separately from normal reader dismissal."""
    if context:
        return context.output(argv, title=title or 'Dots output')
    if not terminal():
        raise ValueError('menu actions require terminal input and output')
    from menu_pager import run_report
    return run_report(argv, title=title or 'Dots output')


def show_message(text, *, context=None, title='Dots menu', code=0):
    """Display inert information in the same reader used for command output."""
    from menu_pager import page_text
    return page_text(text, title=title, code=code, context=context)

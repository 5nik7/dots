"""Source-backed page/section selection using existing interaction and reader APIs."""
import os
import shutil
import sys
from menus import Entry, Menu, choose, entry_spans
from wiki_presentation import preference, document


def pick(title, choices, ui, *, menu_id='wiki', context=None, frame=None):
    """Shared menu rows and navigation, with a dependency-free numbered fallback."""
    from interaction import SelectionEvent, rich_fzf_available
    from menu_pager import page_text
    title = ui.clean(title)
    entries = tuple(item if isinstance(item, Entry) else Entry(str(i), ui.clean(item))
                    for i, item in enumerate(choices))
    menu = Menu(menu_id, title, entries)
    frame = {} if frame is None else frame
    if rich_fzf_available():
        while True:
            try:
                selected = choose(menu, mode='browse', ui=ui, context=context, navigation=frame,
                                  query=frame.get('query', ''), focus_index=frame.get('selected'),
                                  prompt='wiki·' + title.removeprefix('Wiki ').lower(), preserve_row_styles=True,
                                  header='Enter: read  Esc: back\nF1: help  Ctrl-C: quit')
                if selected is None:
                    return None
                frame['selected'] = next(i for i, entry in enumerate(entries) if entry.id == selected.id)
                return frame['selected']
            except SelectionEvent as event:
                if event.action == 'back':
                    return None
                if event.action == 'help':
                    page_text('Up/Down: move (wrap at ends)\nType: filter choices\nEnter: read or open\n'
                              'Esc: back\nCtrl-C: quit\nClose a document to return to this menu.',
                              title='Wiki keys', context=context)
    ui.heading(title)
    for i, entry in enumerate(entries, 1):
        spans = entry_spans(menu, entry, ui)
        ui.detail_spans(str(i), spans, label_width=0,
                        indent=ui.formatting.get('indent', 0) + ui.formatting.get('padding', 1))
    try:
        value = input('Choice (blank to go back): ')
    except EOFError:
        return None
    if not value:
        return None
    if not value.isdigit() or not 1 <= int(value) <= len(choices):
        raise ValueError('invalid topic selection')
    frame['selected'] = int(value) - 1
    return frame['selected']


def choice(identity, title, description='', *, navigation=False):
    from style_config import icon
    role = 'navigation.back' if navigation else 'menu.wiki'
    return Entry(identity,title,description if preference('menu_descriptions',True) else '',
                 icon=icon(role,''),icon_role=role)


def browse(root, query, ui):
    from interaction import SelectionEnded
    from wiki_topics import snapshot, search, section_text
    from menu_pager import page_text
    from menu_tmux import TmuxContext
    from markdown_viewer import reader_ui
    context = (TmuxContext.from_environment() if os.name != 'nt' and
               (os.environ.get('TMUX') or os.environ.get('DOTS_MENU_CONTEXT')) else None)
    pages, records = snapshot(root)
    page_rows = [row for row in records if not row['anchor']]
    frames = {}

    def select(title, entries, identity):
        return pick(title, entries, ui, menu_id=identity, context=context,
                    frame=frames.setdefault(identity, {}))

    def read(row):
        data = section_text(row) if row['anchor'] else pages[row['page']]
        content = document(data.encode(), reader_ui(context), inline_notice=True)
        if not (shutil.which('less') or shutil.which('fzf')):
            sys.stdout.buffer.write(content)
            sys.stdout.flush()
        else:
            page_text(content, title=row['title'], context=context)

    try:
        if query is not None:
            matches = search(records, query)
            if not matches:
                if context:
                    page_text('No matching topics.\nQuery: ' + ui.clean(query), title='Wiki topics', context=context)
                else:
                    ui.heading('Dots wiki topics')
                    ui.detail('Query', query)
                    ui.detail('Results', 'No matching topics.')
                return 1
            entries = [choice(row['page'] + '#' + row['anchor'],
                              row['title'] + (' / ' + row['heading'] if row['heading'] else ''),
                              row['text'] if preference('search_snippets', True) else '') for row in matches]
            while True:
                chosen = select('Wiki topics', entries, 'wiki:topics')
                if chosen is None:
                    return 0
                hit = matches[chosen]
                read(next(r for r in records if r['page'] == hit['page'] and r['anchor'] == hit['anchor']))
        while True:
            chosen = select('Wiki pages', [choice(r['page'], r['title'], r['section']) for r in page_rows], 'wiki:pages')
            if chosen is None:
                return 0
            page = page_rows[chosen]
            sections = [r for r in records if r['page'] == page['page'] and r['anchor']]
            entries = [choice('whole', 'Whole page'),
                       *[choice('heading:' + r['anchor'], r['breadcrumb'] if preference('section_breadcrumbs', True)
                                else r['heading']) for r in sections], choice('back', 'Back', navigation=True)]
            while True:
                chosen = select(page['title'], entries, 'wiki:sections:' + page['page'])
                if chosen is None or chosen == len(sections) + 1:
                    break
                read(page if chosen == 0 else sections[chosen - 1])
    except SelectionEnded as ended:
        return ended.status

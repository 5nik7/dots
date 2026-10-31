"""Source-backed page/section selection using existing interaction and reader APIs."""
import os
import shutil
import sys
from menus import Entry, Menu, styled_label, entry_spans
from wiki_presentation import preference, document


def pick(title, choices, ui, *, menu_id='wiki'):
    """Return an index, keeping display labels separate from selected identities."""
    from interaction import Selector, RichSelector, rich_fzf_available
    title = ui.clean(title)
    entries = tuple(choice if isinstance(choice,Entry) else Entry(str(i),ui.clean(choice)) for i,choice in enumerate(choices))
    menu = Menu(menu_id,title,entries)
    # Use the same menu columns and field styles as the family launcher. Numeric
    # transport identities are separate from labels, including duplicate titles.
    from menu_popup import viewport
    ui.width = max(1,viewport()[0] - 6)
    if shutil.which('gum') and (os.name == 'nt' or shutil.which('bash') and os.environ.get('TERM', 'dumb') != 'dumb'):
        # Gum owns its widget colors. Keep selection values plain and exact.
        color = ui.color
        try:
            ui.color = False
            labels = [str(i + 1) + '. ' + styled_label(menu,entry,ui) for i,entry in enumerate(entries)]
        finally:
            ui.color = color
        selected = Selector('gum', sys.stderr).pick('filter', title, labels)
        if selected not in labels:
            raise ValueError('picker returned an unknown topic')
        return labels.index(selected)
    if rich_fzf_available():
        from files.picker import fzf_colors
        labels = [styled_label(menu,entry,ui) for entry in entries]
        return RichSelector(backend='fzf').fzf(title, labels, False, None,
            ui.color, ui.icons, fzf_colors(ui), wrap=True,
            header='Enter: read  Esc: back  Ctrl-C: cancel')[0]
    ui.heading(title)
    for i, entry in enumerate(entries, 1):
        spans = entry_spans(menu,entry,ui)
        ui.detail_spans(str(i),spans,label_width=0,indent=ui.formatting.get('indent',0)+ui.formatting.get('padding',1))
    try:
        value = input('Choice (blank to go back): ')
    except EOFError:
        return None
    if not value:
        return None
    if not value.isdigit() or not 1 <= int(value) <= len(choices):
        raise ValueError('invalid topic selection')
    return int(value) - 1


def choice(identity, title, description='', *, navigation=False):
    from style_config import icon
    role = 'navigation.back' if navigation else 'menu.wiki'
    return Entry(identity,title,description if preference('menu_descriptions',True) else '',
                 icon=icon(role,''),icon_role=role)


def browse(root, query, ui):
    from interaction import SelectionEnded
    from wiki_topics import snapshot, search, section_text
    from menu_pager import page_text
    pages, records = snapshot(root)
    page_rows = [row for row in records if not row['anchor']]
    try:
        if query is not None:
            matches = search(records, query)
            if not matches:
                ui.heading('Dots wiki topics')
                ui.detail('Query', query)
                ui.detail('Results', 'No matching topics.')
                return 1
            labels = [choice(row['page']+'#'+row['anchor'],row['title'] + (' / ' + row['heading'] if row['heading'] else ''),
                             row['text'] if preference('search_snippets',True) else '') for row in matches]
            chosen = pick('Wiki topics', labels, ui, menu_id='wiki:topics')
            if chosen is None:
                return 0
            hit = matches[chosen]
            row = next(r for r in records if r['page'] == hit['page'] and r['anchor'] == hit['anchor'])
            data = section_text(row) if row['anchor'] else pages[row['page']]
        else:
            while True:
                chosen = pick('Wiki pages', [choice(r['page'],r['title'],r['section']) for r in page_rows], ui, menu_id='wiki:pages')
                if chosen is None:
                    return 0
                page = page_rows[chosen]
                sections = [r for r in records if r['page'] == page['page'] and r['anchor']]
                chosen = pick(page['title'], [choice('whole','Whole page'),
                    *[choice('heading:'+r['anchor'],r['breadcrumb'] if preference('section_breadcrumbs',True) else r['heading']) for r in sections],
                    choice('back','Back',navigation=True)], ui, menu_id='wiki:sections:'+page['page'])
                if chosen is None or chosen == len(sections) + 1:
                    continue
                row = page if chosen == 0 else sections[chosen - 1]
                data = pages[page['page']] if chosen == 0 else section_text(row)
                break
    except SelectionEnded as ended:
        return ended.status
    content = document(data.encode(), ui)
    if not (shutil.which('less') or shutil.which('fzf')):
        # Keep the terminal and numbered fallback useful without a reader dependency.
        sys.stdout.buffer.write(content)
        return 0
    page_text(content, title=row['title'], defer=True)
    return 0

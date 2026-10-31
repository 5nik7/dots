"""Wiki human views on the shared renderer; data interfaces bypass this module."""
import shutil
import os

from files.catalog import Presentation
from config_values import value
from style_config import current


def preference(key, fallback=None):
    return value('apps.wiki.' + key, fallback)


class WikiPresentation(Presentation):
    def style(self, role, fallback='ui.foreground'):
        prefs = current()
        return '0;' + prefs.sgr('wiki.' + role, fallback=prefs.style(fallback, app='cli'), app='cli') if prefs else '0'

    def heading(self, title):
        if not self.human:
            return super().heading(title)
        glyph = self.icon('menu.wiki', '󰈙') if self.icons else ''
        prefs = current()
        heading_style = prefs.style('wiki.heading', fallback=prefs.style('ui.heading', app='cli'), app='cli') if prefs else {}
        icon_style = '0;' + prefs.sgr('icons.menu.wiki', fallback=heading_style, app='cli') if prefs else '0'
        spans = [(glyph + ' ', icon_style)] if glyph else []
        self.heading_spans([*spans, (title, self.style('heading', 'ui.heading'))])

    def detail_spans(self, label, spans, **kwargs):
        if self.human and kwargs.get('label_code', '94') == '94':
            kwargs['label_code'] = self.style('label', 'ui.label')
        return super().detail_spans(label, spans, **kwargs)

    def detail(self, label, text, code=None):
        if self.human and code is None:
            role = {'Page': 'page', 'Heading': 'section', 'Section': 'section',
                    'Text': 'snippet', 'URL': 'url'}.get(label)
            if label.startswith('Line '): role = 'snippet'
            if role:
                code = self.style(role, 'ui.accent' if role in ('page', 'url') else 'ui.muted' if role == 'snippet' else 'ui.heading')
            elif label in ('Status', 'Freshness', 'Healthy'):
                status = str(text).casefold()
                semantic = ('status.success' if status in ('true', 'available', 'current', 'built', 'cloned', 'unchanged') else
                            'status.warning' if status in ('false', 'missing', 'stale', 'obsolete', 'missing or stale') else 'ui.muted')
                prefs = current()
                code = prefs.sgr(semantic, app='cli') if prefs else None
            else:
                prefs = current()
                code = prefs.sgr('ui.foreground', app='cli') if prefs else None
        return super().detail(label, text, code)

    def gap(self):
        for _ in range(value('formatting.apps.wiki.row_gap', 1)):
            self.emit()


def legacy_report(ui, action, data):
    """Retain the established ordinary redirected report byte layout."""
    ui.heading('Dots wiki' + (' ' + action if action != 'overview' else ''))
    for key, item in data.items():
        if key == 'items':
            section = None
            for row in item:
                if isinstance(row, dict):
                    if row.get('section') and row['section'] != section:
                        section = row['section']; ui.emit(); ui.detail('Section', section)
                    identity, title = row.get('id', row.get('page', '')), row.get('title', '')
                    ui.detail('Page', identity + (' · ' + title if title and title != identity else ''))
                    if row.get('status'): ui.detail('Status', row['status'])
                    if row.get('text'): ui.detail('Line ' + str(row['line']), row['text'])
                    if row.get('status') or row.get('text'): ui.emit()
                else: ui.resource_detail('File', row, kind='file')
        elif key == 'path': ui.resource_detail('Path', item, kind='dir')
        else: ui.detail(key.replace('_', ' ').title(), item)


def report(ui, action, data, root):
    if not ui.human:
        return legacy_report(ui, action, data)
    ui.heading('Dots wiki' + (' ' + action if action != 'overview' else ''))
    for key, item in data.items():
        if key == 'items': continue
        label = key.replace('_', ' ').title()
        if key in ('path', 'journal'):
            ui.resource_detail(label, item, kind='dir' if key == 'path' else 'file')
        else: ui.detail(label, item)
    rows = data.get('items', [])
    if 'items' not in data: return
    ui.detail('Results' if action == 'search' else 'Pages' if action in ('overview', 'list') else 'Files', len(rows), ui.style('section', 'ui.heading'))
    section = None
    for row in rows:
        ui.gap()
        if not isinstance(row, dict):
            ui.resource_detail('File', row, kind='file'); continue
        if row.get('section') and row['section'] != section:
            section = row['section']; ui.detail('Section', section)
        identity, title = row.get('id', row.get('page', '')), row.get('title', '')
        ui.detail('Page', identity + (' · ' + title if title and title != identity else ''))
        if row.get('status'): ui.detail('Status', row['status'])
        if row.get('text') and preference('search_snippets', True):
            ui.detail('Line ' + str(row['line']), row['text'])
        if row.get('source') and preference('list_details', 'summary') == 'full':
            ui.resource_detail('Source', root / row['source'], kind='file')
        elif row.get('generated') and preference('list_details', 'summary') == 'full':
            ui.detail('Source', 'Generated from static command metadata')
    if not rows:
        ui.detail('Results', 'No matching pages.' if action == 'list' else 'No matching text.' if action == 'search' else
                  'No documentation issues.' if action == 'check' else 'No file changes.')


def topics(ui, query, matches):
    ui.heading('Dots wiki topics'); ui.detail('Query', query)
    if ui.human: ui.detail('Results', len(matches), ui.style('section', 'ui.heading'))
    for item in matches:
        ui.gap() if ui.human else ui.emit()
        ui.detail('Page', item['title'] + ' (' + item['page'] + ')')
        if item['heading']: ui.detail('Heading', item['breadcrumb'])
        if not ui.human or preference('search_snippets', True): ui.detail('Text', item['text'])
        if not ui.human or preference('search_urls', True): ui.detail('URL', item['url'])
    if not matches: ui.detail('Results', 'No matching topics.')


def document(data, ui):
    """Render only a human document; callers retain exact raw/redirected bytes."""
    from themes.file_preview import run_renderer
    bat = (shutil.which('bat') or shutil.which('batcat')) if preference('reader', 'auto') == 'auto' else None
    rendered = run_renderer([bat, '--no-config', '--paging=never', '--style=plain', '--language=markdown',
                             '--color=' + ('always' if ui.color else 'never')], data, os.environ) if bat else None
    return rendered if rendered is not None else '\n'.join(ui.clean(line) for line in data.decode().replace('\r\n', '\n').split('\n')).encode()


def diagnostic(message, stream):
    ui = WikiPresentation(stream)
    if not ui.human:
        # Existing redirected error prefix and safe display escaping.
        ui.emit('dots wiki: ' + ui.clean(message)); return
    ui.heading('Dots wiki'); ui.detail('Error', message, '91')

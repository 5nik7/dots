"""Human views of the Files catalog."""
from collections import Counter
from pathlib import PurePosixPath, PureWindowsPath

from resources import cells


def displayed_path(text, windows):
    return PureWindowsPath(text) if windows and '\\' in text else PurePosixPath(text)


def compact_path(text, budget, windows):
    """Keep the basename and as many trailing directories as will fit."""
    if cells(text) <= budget:
        return text
    path = displayed_path(text, windows)
    parts = path.parts
    if len(parts) <= 1:
        return text
    anchor = path.anchor or ('~' if parts[0] == '~' else '')
    folders = parts[1:] if anchor else parts
    for count in range(len(folders) - 1, 0, -1):
        tail = folders[-count:]
        prefixes = []
        if anchor and len(folders) > count + 1:
            prefixes.append((anchor, folders[0], '…'))
        if anchor:
            prefixes.append((anchor, '…'))
        prefixes.append(('…',))
        for prefix in prefixes:
            choice = str(type(path)(*prefix, *tail))
            if cells(choice) <= budget:
                return choice
    return path.name or text


def pair_paths(left, right, budget, windows):
    """Allocate space to both basenames, then share what's left between parents."""
    left_min = cells(displayed_path(left, windows).name or left)
    right_min = cells(displayed_path(right, windows).name or right)
    if left_min + right_min > budget:
        return None
    left_budget = max(left_min, min(budget - right_min, budget // 2))
    right_text = compact_path(right, budget - min(cells(left), left_budget), windows)
    left_text = compact_path(left, budget - cells(right_text), windows)
    return left_text, compact_path(right, budget - cells(left_text), windows)


def endpoint(ui, path, display, kind, marker, code=None):
    spans = ui.path_spans(path, display, kind=kind, icon=False) if ui.color else [(display, None)]
    if marker:
        spans.insert(0, (marker + ' ', code or spans[-1][1]))
    return spans


def emit(ui, spans):
    ui._spans(spans, prefix=' ' if ui.width > 1 else '')


def endpoint_line(ui, path, text, kind, marker, code, windows, lead):
    budget = ui.width - 1 - cells(lead[0]) - (cells(marker) + 1 if marker else 0)
    display = compact_path(text, budget, windows)
    if cells(display) > budget:
        # Keep a basename intact if it fits on its own line without the markers.
        lines = []
        if lead[0] or marker:
            lines.append([(lead[0] if marker else lead[0].rstrip(), lead[1]), (marker, code)])
        return lines + [endpoint(ui, path, display, kind, '')]
    return [[lead] + endpoint(ui, path, display, kind, marker, code)]


def status_color(status):
    if status == 'linked':
        return '92'
    if status in ('source-missing', 'source-broken-link', 'broken-link', 'linked-elsewhere', 'conflict'):
        return '91'
    if status in ('stashed', 'replaced', 'inactive-platform', 'excluded', 'unmapped'):
        return '90'
    return '93'


def short_row(ui, row, windows, arrow_color, *, narrow, separate=False):
    status = row['status']
    if status == 'stashed':
        marker = ui.icon('status.stashed', '') if ui.icons else '[stashed]'
        return [[(marker + ' ', '90'), (row['id'], '90')]]

    source = row.get('source') or row.get('source_spec')
    target = row.get('target') or row.get('target_spec')
    code = status_color(status)
    if narrow:
        marker = ''
    elif status == 'linked':
        marker = ui.icon('files.symlink', '󰌷') if ui.icons else ''
    else:
        marker = '[' + status.replace('-', ' ') + ']'
    if source is None:
        return [[(marker + ' ' if marker else '', code), (row['id'], '94')]]
    directory = row.get('strategy') == 'directory-link'
    kind = 'dir' if directory else 'file'
    glyph = ''
    if ui.icons:
        glyph = ui.icon('files.directory', '󰉋') if directory else ui.icon('files.file', '󰈔')
    left = ui.clean(ui.path(source))
    glyph_width = cells(glyph) + 1 if glyph else 0
    lead = ('', None)
    if marker and (target is None or status in ('source-missing', 'source-broken-link', 'theme-unavailable',
                                                'inactive-platform', 'replaced', 'unmapped', 'unsupported-platform')):
        lead, marker = (marker + ' ', code), ''
    if target is None:
        return endpoint_line(ui, source, left, kind, glyph, None, windows, lead)
    right = ui.clean(ui.path(target))
    arrow = (' -> ', arrow_color)
    marker_width = cells(marker) + 1 if marker else 0
    available = ui.width - 1 - cells(lead[0]) - glyph_width - cells(arrow[0]) - marker_width
    pair = None
    if not separate:
        if not narrow:
            pair = pair_paths(left, right, available, windows)
        elif status == 'linked' and directory and cells(left) + cells(right) <= available:
            pair = left, right
    target_kind = 'symlink' if status in ('linked', 'linked-elsewhere') else (
        'dir' if status == 'existing-directory' or directory else 'file')
    if pair is not None:
        return [[lead] + endpoint(ui, source, pair[0], kind, glyph) + [arrow] +
                endpoint(ui, target, pair[1], target_kind, marker, code)]
    continuation = '-> '
    if narrow:
        continuation = ' 󱞩 ' if ui.icons else ' -> '
    return (endpoint_line(ui, source, left, kind, glyph, None, windows, lead) +
            endpoint_line(ui, target, right, target_kind, marker, code, windows, (continuation, arrow_color)))


def display_key(lines):
    return tuple(''.join(text for text, _ in line) for line in lines)


def render_list(ui, rows, view, platform, repo, *, group_by_status=False):
    narrow = view == 'short' and ui.width < 50
    if group_by_status:
        first = {'linked': 0, 'stashed': 5 if narrow else 1, 'missing': 2, 'source-missing': 3}
        rows = sorted(rows, key=lambda row: (first.get(row['status'], 4), row['status']))
    if view in ('default', 'verbose'):
        ui.render('list', rows, platform, repo, details=view == 'verbose')
        return
    if view != 'short':
        raise ValueError('unsupported file list view: ' + str(view))
    if not rows:
        ui.emit('No matching resources.')
        return

    from style_config import current
    styles = current() if ui.color else None
    arrow_color = styles.sgr_color('dark_foreground') if styles and 'dark_foreground' in styles.palette else '90'
    windows = platform == 'windows'
    entries = [short_row(ui, row, windows, arrow_color, narrow=narrow) for row in rows]
    # A narrow section heading already distinguishes different statuses.
    keys = [(row['status'], display_key(entry)) for row, entry in zip(rows, entries)]
    counts = Counter(keys)
    # Give identical abbreviated pairs a full line per path. Very deep
    # common suffixes can still collide, so retain the identity in that case.
    if len(counts) < len(entries):
        for index, (row, key) in enumerate(zip(rows, keys)):
            if counts[key] > 1 and len(entries[index]) == 1:
                entries[index] = short_row(ui, row, windows, arrow_color, narrow=narrow, separate=True)
        keys = [(row['status'], display_key(entry)) for row, entry in zip(rows, entries)]
        counts = Counter(keys)

    previous = None
    for row, entry, key in zip(rows, entries, keys):
        status = row['status']
        if narrow and (status != 'stashed' or previous != 'stashed'):
            ui.emit()
            # Explicit sorting can return to linked rows after an exceptional section.
            heading = status != 'linked' or previous not in (None, 'stashed')
            if heading and status != previous and status != 'stashed':
                ui.heading_spans([('[' + status.replace('-', ' ') + ']', status_color(status))])
        for line in entry:
            emit(ui, line)
        if counts[key] > 1:
            emit(ui, [(row['id'], '94')])
        previous = status

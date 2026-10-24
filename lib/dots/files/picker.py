#!/usr/bin/env python3
"""Transient file selectors and bounded, explicitly requested content previews."""
import itertools
import codecs
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile

from catalog import Presentation
from interaction import RichSelector, selection_requested as requested
from transactions import parents_safe
from file_platform import open_nofollow

LIMIT = 65536
LINES = 200
CREDENTIAL = re.compile(rb'(?i)(BEGIN [A-Z ]*PRIVATE KEY|(?:password|api[_-]?key|access[_-]?token)\s*[=:]\s*["\']?[^\s"\']{4,})')
INTENT = {
    'add': 'Import selected files and replace their originals with managed links.',
    'link': 'Link repository sources; occupied targets require backup approval.',
    'stash': 'Disable management and remove matching links; keep repository sources.',
    'restore': 'Enable selected mappings and relink on this platform.',
    'edit': 'Edit mapping metadata; live links change only with --apply.',
    'remove': 'Stop managing; keep repository sources and usable configuration.',
    'show': 'Inspect mapping details without changes.',
    'browse': 'Inspect a resource, then choose an action and review its plan.',
}


def candidates(manager, action, values=(), repo=None, restore=False):
    if action == 'add':
        roots = [Path(os.path.abspath(os.path.expanduser(p))) for p in values]
        for root in roots:
            parents_safe(root)
            if root.is_symlink() or not root.exists():
                raise ValueError('picker input must be an existing regular file or directory: ' + str(root))
            manager.mapping(root, repo)
        rows = [dict(r, target=r['path'], candidate=r['path'])
                for r in manager.system(repo) if r['status'] in ('candidate', 'existing-source')]
        return [r for r in rows if not roots or any(Path(r['path']) == p or Path(r['path']).is_relative_to(p) for p in roots)]
    rows = manager.catalog.records()
    if action == 'link':
        rows = [r for r in rows if r['enabled'] and r['applicable']]
    elif action == 'stash':
        rows = [r for r in rows if r['enabled'] != restore]
    elif action == 'remove':
        rows = [r for r in rows if r['applicable']]
    return rows


def fzf_colors(ui):
    """Read the same published literal color grammar as the theme adapter."""
    if not ui.color:
        return ''
    from resources import read_data
    text = read_data(ui.resources.root / 'fzf.sh').replace('\\\n', '')
    atom = r'(?:#[a-fA-F0-9]{6}|-1|[0-9]{1,2}|1[0-9]{2}|2[0-4][0-9]|25[0-5]|regular|bold|dim|italic|underline|blink|reverse|strikethrough|strip|nobold|nodim|noitalic|nounderline|noblink|noreverse|nostrikethrough)'
    entry = r'[a-z][a-z+-]*:' + atom + '(?::' + atom + ')*'
    colors = ''
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        match = re.fullmatch(r'export _FZF_COLORS_="([^"]+)"', line)
        if match and not colors and re.fullmatch(entry + '(?:,' + entry + ')*', match[1]):
            colors = match[1]
        elif line != 'export FZF_DEFAULT_OPTS="${FZF_DEFAULT_OPTS} --color=$_FZF_COLORS_"':
            return ''
    return colors


def select(rows, action, multi=False, new=False, selector=None, owners=()):
    ui = Presentation()
    roots = {o['id']: o['root'] for o in owners}
    rows = [dict(r, _source_root=roots.get(r.get('repository'))) for r in rows]
    if new:
        rows.insert(0, {'id': '__new__', 'label': 'New mapping', 'status': 'new'})
    if not rows:
        ui.emit('  No matching resources to select.')
        return []
    labels = []
    for row in rows:
        if row.get('label'):
            labels.append(ui.clean(row['label']))
            continue
        identity = row.get('id') or ui.repository_label(row.get('_source_root'), row.get('repository', ''))
        paths = [ui.resource(row[k]) for k in ('source', 'target') if row.get(k)]
        labels.append(' | '.join([ui.paint(identity, '94'), ui.clean(row.get('app', '')),
                                 ui.status(row.get('status', 'available')), ' -> '.join(paths)]))
    selector = selector or RichSelector()
    # Snapshots contain metadata only, never file contents; mode is UI-local.
    with tempfile.TemporaryDirectory(prefix='dots-file-picker-') as directory:
        snapshot = Path(directory) / 'items.json'
        snapshot.write_text(json.dumps(dict(rows=rows, action=action, color=ui.color, icons=ui.icons)))
        snapshot.chmod(0o600)
        prefix = '"$DOTS_PICKER_PYTHON" -B "$DOTS_PICKER_HELPER"'
        snapshot_argument = '"$DOTS_PICKER_SNAPSHOT"'
        if os.name == 'nt':
            prefix = '& $env:DOTS_PICKER_PYTHON -B $env:DOTS_PICKER_HELPER'
            snapshot_argument = '$env:DOTS_PICKER_SNAPSHOT'
        preview = (prefix + ' preview ' + snapshot_argument + ' {1}',
                   prefix + ' cycle ' + snapshot_argument,
                   dict(DOTS_PICKER_PYTHON=sys.executable, DOTS_PICKER_HELPER=str(Path(__file__).resolve()),
                        DOTS_PICKER_SNAPSHOT=str(snapshot), DOTS_PROGRESS='never', DOTS_OPERATION_VERBOSE='0'))
        indexes = selector.pick('Files ' + action, labels, multi, preview, ui.color, ui.icons, fzf_colors(ui))
    return [rows[i] for i in indexes]


def choice(title, choices):
    ui = Presentation()
    choices = [c for c in choices if c != 'Cancel']
    if not choices:
        raise ValueError('No available choices for ' + title)
    index = RichSelector().pick(title, [ui.clean(c) for c in choices],
                                color=ui.color, icons=ui.icons, colors=fzf_colors(ui))[0]
    return choices[index]


def safe_content(ui, row, field):
    from manage import Manager
    value = row.get(field)
    if not value:
        ui.emit('  No path mapped.')
        return
    path = Path(value)
    ui.resource_detail(field.title(), path)
    try:
        # Only follow a target link when it is exactly the recorded managed link.
        parents_safe(path)
        if path.is_symlink():
            source = row.get('source')
            if field != 'target' or not source or path.resolve() != Path(source):
                raise ValueError('unsafe or unrelated link')
            path = Path(source)
            parents_safe(path)
        # The checkout itself may be named dots; evaluate source exclusions
        # relative to its owner while preserving sensitive parent/name checks.
        root = row.get('_source_root')
        relative = path.relative_to(root) if root and path.is_relative_to(root) else path
        if not Manager.allowed(relative):
            raise ValueError('excluded or credential-like path')
        info = path.lstat()
        if stat.S_ISDIR(info.st_mode):
            # Directory snapshots do not recurse or follow child links.
            with os.scandir(path) as entries:
                children = list(itertools.islice(entries, LINES + 1))
            for child in sorted(children[:LINES], key=lambda c: c.name):
                ui.emit('  ' + ui.resource(child.path, child.name))
            if len(children) > LINES:
                ui.emit('  … Directory listing truncated at 200 entries.')
            return
        if not stat.S_ISREG(info.st_mode):
            raise ValueError('only regular files and directories can be previewed')
        fd = open_nofollow(path, os.O_RDONLY | getattr(os, 'O_NONBLOCK', 0))
        with os.fdopen(fd, 'rb') as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError('file type changed')
            data = stream.read(LIMIT + 1)
        if b'\0' in data or CREDENTIAL.search(data):
            raise ValueError('binary or possible credential content')
        text = codecs.getincrementaldecoder('utf-8')('strict').decode(data[:LIMIT], final=len(data) <= LIMIT)
        lines = text.splitlines()
        for line in lines[:LINES]:
            ui.emit('  ' + ui.clean(line))
        if len(data) > LIMIT or len(lines) > LINES:
            ui.emit('  … Content truncated at 64 KiB / 200 lines.')
    except (OSError, ValueError, RuntimeError):
        ui.emit('  Content unavailable: missing, excluded, binary, credential-like or unsafe path.')


def preview(snapshot, token):
    doc = json.loads(Path(snapshot).read_text())
    if not re.fullmatch(r'0|[1-9][0-9]*', token) or int(token) >= len(doc['rows']):
        raise ValueError('unknown preview token')
    os.environ.update(DOTS_COLOR='always' if doc['color'] else 'never',
                      DOTS_ICONS='always' if doc['icons'] else 'never')
    ui = Presentation()
    ui.width = max(24, int(os.environ.get('FZF_PREVIEW_COLUMNS', ui.width)))
    mode_path = Path(snapshot).with_suffix('.mode')
    mode = int(mode_path.read_text()) if mode_path.exists() else 0
    row = doc['rows'][int(token)]
    ui.heading(('Details', 'Source content', 'Target content')[mode])
    if row.get('label'):
        ui.detail('Mapping', row['label'])
        ui.emit('  Choose a repository and enter source/target mapping fields after selection.')
        return
    if mode:
        safe_content(ui, row, 'source' if mode == 1 else 'target')
        return
    for key in ('id', 'repository', 'app', 'status', 'strategy', 'enabled', 'platforms', 'applicable'):
        if key in row:
            if key == 'repository':
                ui.repository_detail('Repository', row.get('_source_root'), row[key])
            else: ui.detail(key.title(), row[key])
    for key in ('source', 'target'):
        if row.get(key):
            ui.resource_detail(key.title(), row[key])
    ui.detail('Action', INTENT[doc['action']])
    ui.emit('  Informational preview; the complete plan follows selection.')


if __name__ == '__main__':
    try:
        if len(sys.argv) == 3 and sys.argv[1] == 'cycle':
            path = Path(sys.argv[2]).with_suffix('.mode')
            mode = int(path.read_text()) if path.exists() else 0
            path.write_text(str((mode + 1) % 3))
        elif len(sys.argv) == 4 and sys.argv[1] == 'preview':
            preview(sys.argv[2], sys.argv[3])
        else:
            raise ValueError('private picker helper')
    except (OSError, ValueError, KeyError, TypeError):
        print('Preview unavailable.')
        sys.exit(1)

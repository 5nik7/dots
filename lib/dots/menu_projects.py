"""Read-only, shallow project discovery for the interactive session browser."""
from __future__ import annotations
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re


@dataclass(frozen=True)
class Project:
    root: Path
    label: str


@dataclass(frozen=True)
class Row:
    id: str
    label: str
    project: Project | None = None
    sessions: tuple = ()


def canonical(value):
    return Path(value).expanduser().resolve()


def discover():
    """Defaults plus optional user paths; never invoke Git, clone or initialize."""
    home = Path.home()
    config = Path(os.environ.get('XDG_CONFIG_HOME') or home / '.config') / 'dots/projects.json'
    roots, explicit = [home / 'repos'], [Path(os.environ.get('DOTS') or Path(__file__).resolve().parents[2])]
    if config.exists():
        try:
            data = json.loads(config.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            raise ValueError('cannot read dots/projects.json') from None
        if (not isinstance(data, dict) or type(data.get('schema')) is not int or data['schema'] != 1
                or set(data) - {'schema', 'roots', 'projects'}):
            raise ValueError('dots/projects.json requires schema 1, roots and projects path arrays')
        for key, destination in (('roots', roots), ('projects', explicit)):
            paths = data.get(key, [])
            if (not isinstance(paths, list) or any(not isinstance(p, str) or not p or '\0' in p
                    or not Path(p).expanduser().is_absolute() for p in paths)):
                raise ValueError('dots/projects.json paths must be absolute or start with ~/')
            destination.extend(Path(p).expanduser() for p in paths)
    paths = set()
    for root in roots:
        try:
            children = tuple(root.iterdir())
        except (OSError, ValueError):
            continue
        for child in children:
            if child.is_dir() and (child / '.git').exists():
                paths.add(canonical(child))
    for path in explicit:
        if path.is_dir():
            paths.add(canonical(path))
    return tuple(Project(path, path.name or str(path)) for path in sorted(paths, key=lambda p: (p.name.casefold(), str(p))))


def matching(path, projects):
    if not path or not Path(path).is_absolute():
        return None
    try:
        path = canonical(path)
    except (OSError, ValueError):
        return None
    matches = [p for p in projects if path == p.root or p.root in path.parents]
    return max(matches, key=lambda p: len(p.root.parts)) if matches else None


def associate(server, session, projects):
    managed = server.read('show-options', '-qv', '-t', session.id + ':', '@dots-workspace-data').strip()
    if managed:
        try:
            data = json.loads(managed)
            roots = data.get('projects')
            if (type(data.get('schema')) is not int or data['schema'] != 1
                    or not isinstance(roots, list)
                    or any(not isinstance(root, str) or not Path(root).is_absolute() for root in roots)):
                raise ValueError('invalid workspace project metadata')
        except (ValueError, AttributeError):
            raise ValueError('invalid workspace project metadata') from None
        if len(roots) == 1:
            root = canonical(roots[0])
            return next((p for p in projects if p.root == root), Project(root, root.name))
        return None
    # Legacy marked sessions remain generic until explicitly adopted.
    if server.read('show-options', '-qv', '-t', session.id, '@dots-termux-default').strip() == '1':
        return None
    # A session-local tag survives renames and pane directory changes. Do not
    # inherit a global tag; it must identify this session's explicit project.
    tag = server.read('show-options', '-qv', '-t', session.id, '@dots-project-root').removesuffix('\n')
    project = next((p for p in projects if str(p.root) == tag), None)
    if project:
        return project
    start = server.read('display-message', '-p', '-t', session.id, '#{session_path}').removesuffix('\n')
    project = matching(start, projects)
    if project:
        return project
    panes = server.read('list-panes', '-s', '-t', session.id, '-F', '#{pane_id}').splitlines()
    candidates = set()
    for pane in panes:
        if not re.fullmatch(r'%[0-9]+', pane):
            raise ValueError('invalid tmux pane inventory')
        path = server.read('display-message', '-p', '-t', pane, '#{pane_current_path}').removesuffix('\n')
        project = matching(path, projects)
        if project:
            candidates.add(project)
    return next(iter(candidates)) if len(candidates) == 1 else None


def inventory(server, sessions, projects):
    groups = {project: [] for project in projects}
    generic = []
    for session in sessions:
        project = associate(server, session, projects)
        if project:
            groups.setdefault(project, []).append(session)
        else:
            generic.append(Row(session.id, session.name, sessions=(session,)))
    rows = [Row('project:' + str(p.root), p.label, p, tuple(sorted(items, key=lambda s: (s.name.casefold(), s.id))))
            for p, items in groups.items()]
    rows.sort(key=lambda row: (not bool(row.sessions), row.label.casefold(), row.id))
    generic.sort(key=lambda row: (row.label.casefold(), row.id))
    if server:
        server.verify()
    return tuple([*rows, *generic])


def number_group(server, session, projects):
    """Status numbering shares picker association, without loading any menu UI."""
    project = associate(server, session, projects)
    if project:
        return ('project', str(project.root))
    managed = server.read('show-options', '-qv', '-t', session.id + ':', '@dots-workspace-data').strip()
    if managed:
        data = json.loads(managed)
        if not isinstance(data, dict):
            raise ValueError('invalid workspace project metadata')
        if data.get('auto') is True and session.name == data.get('expected'):
            label = server.read('show-options', '-qv', '-t', session.id + ':',
                                '@dots-workspace-label').removesuffix('\n')
            return ('label', label or 'termux')
    elif server.read('show-options', '-qv', '-t', session.id + ':', '@dots-termux-default').strip() == '1':
        return ('label', 'termux')
    return ('label', session.name)

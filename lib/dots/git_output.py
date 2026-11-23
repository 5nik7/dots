"""Git human views over existing records. Never discovers or mutates a repository."""
from functools import lru_cache
from pathlib import Path
import os

from cli_preferences import VIEWS, git_view
from resources import cells, wrap


def arguments(parser):
    parser.add_argument('--view', choices=VIEWS, action='append', dest='_views', help='select the human output view')
    parser.add_argument('-s', '--short', action='append_const', const='short', dest='_views', help='use compact human output')
    parser.add_argument('-v', '--verbose', action='append_const', const='verbose', dest='_views', help='show metadata and action details without patches')


def resolve(args, ui):
    modes = set(getattr(args, '_views', None) or [])
    if getattr(args, 'details', False): modes.add('verbose')
    if len(modes) > 1: raise ValueError('conflicting Git views; select default, short or verbose')
    return git_view(next(iter(modes), None), human=ui.human or os.environ.get('DOTS_MENU_CAPTURE') == '1', data=args.json)


STATES = {'M': 'modified', 'A': 'added', 'D': 'deleted', 'R': 'renamed',
          'C': 'copied', 'T': 'type changed', 'U': 'unmerged'}
CONFLICTS = {'DD': 'both deleted', 'AU': 'added by us', 'UD': 'deleted by them',
             'UA': 'added by them', 'DU': 'deleted by us', 'AA': 'both added', 'UU': 'both modified'}
STATUS_ICONS = dict(modified='', added='', deleted='', renamed='', copied='',
                    type_changed='󰑓', untracked='', ignored='', conflict='', selected='')


def file_icon_role(xy):
    """One type icon for the complete XY group, independent of staging color."""
    if xy in CONFLICTS or 'U' in xy: return 'conflict'
    if xy == '??': return 'untracked'
    if xy == '!!': return 'ignored'
    for marker, role in (('D','deleted'),('R','renamed'),('C','copied'),('A','added'),
                         ('T','type_changed'),('M','modified')):
        if marker in xy: return role
    return 'selected'


def file_label(xy, verbose=False):
    if xy == '??': return 'untracked'
    if xy == '!!': return 'ignored'
    if xy in CONFLICTS: return 'conflict: ' + CONFLICTS[xy]
    fields = []
    for marker, where in zip(xy, ('staged', 'unstaged')):
        if marker != ' ': fields.append(where + ' ' + STATES.get(marker, marker))
    text = ' + '.join(fields) or 'selected'
    return xy + ' ' + text if verbose else text


def file_role(xy):
    if xy in CONFLICTS or 'U' in xy: return 'conflict'
    if xy == '??': return 'untracked'
    if xy == '!!': return 'ignored'
    for marker, role in (('D','deleted'),('R','renamed'),('C','copied'),('A','added')):
        if marker in xy: return role
    return 'modified' if len(xy) > 1 and xy[1] != ' ' else 'staged'


def guide_foreground(ui):
    from style_config import current
    styles = current() if ui.color else None
    return styles.git_guide_foreground() if styles else '90'


@lru_cache(maxsize=128)
def foreground_only(sgr):
    """Keep the final SGR foreground, skipping complete background RGB/index values."""
    params = sgr.split(';')
    result = '39'
    i = 0
    while i < len(params):
        param = params[i]
        if param in ('38', '48', '58') and i + 1 < len(params):
            length = {'2': 5, '5': 3}.get(params[i+1], 1)
            if param == '38' and length > 1 and i + length <= len(params):
                result = ';'.join(params[i:i+length])
            i += length
        else:
            if param == '0': result = '39'
            elif param.isdecimal() and (30 <= int(param) <= 37 or 90 <= int(param) <= 97 or param == '39'):
                result = param
            i += 1
    return result


class GitView:
    def __init__(self, ui, mode, full_paths=False, root=None):
        self.ui, self.mode, self.full_paths = ui, mode, full_paths
        self.root = Path(root) if root else None
        self.last_repo = None
        self.files = set()
        self.previews = set()
        self.renames = {}
        self.selections = {}
        self.parents = {}
        self.last_child = {}
        self.gutter = ' '
        self.header_prefix = ''
        self.vertical, self.fork, self.end = '│', '├', '└'
        self.guide = guide_foreground(ui)

    def role(self, name):
        return self.ui.resources.git_style(name)

    def forest(self, parents):
        self.parents = parents
        self.last_child = {parent: path for path, parent in parents.items() if parent}

    def position(self, path, wiki=False):
        parent = self.parents.get(path)
        if not parent:
            self.header_prefix = ''
            self.gutter = '  ' if wiki else self.vertical
            return
        ancestors = []
        ancestor = parent
        while self.parents.get(ancestor):
            grand = self.parents[ancestor]
            ancestors.append('  ' if self.last_child[grand] == ancestor else self.vertical + ' ')
            ancestor = grand
        column = ''.join(reversed(ancestors))
        limit = max(4, self.ui.width // 3)
        if len(column) > limit: column = '... ' + column[-(limit-4):] if limit > 4 else '... '
        last = self.last_child[parent] == path
        self.header_prefix = column + (self.end if last else self.fork) + ' '
        self.gutter = column + ('  ' if last else self.vertical + ' ')

    def separator(self):
        self.ui.emit(self.ui.paint_guide(self.header_prefix[:-2] + self.vertical, self.guide))

    def header(self, row, label=None):
        ui = self.ui
        path = Path(row['path'])
        label = str(path) if self.full_paths else label or path.name
        remote = row.get('remote') or {}
        kind = row.get('kind') or ('submodule' if row.get('parent') or self.parents.get(str(path)) else 'root')
        self.position(str(path), kind == 'wiki')
        icon = ''
        if ui.icons:
            if kind == 'wiki': icon = ui.icon('git.wiki', '󱔘')
            elif kind == 'submodule':
                icon = ui.icon('git.submodule_github', '') if remote.get('host') == 'github.com' else ui.icon('git.submodule', '')
            else:
                from git_identity import host_icon
                icon = host_icon(remote.get('host'))
        identity = (icon + ' ' if icon else '') + label
        state = row.get('status', '')
        branch = row.get('branch') or ('detached ' + row['head'][:8] if row.get('head') else 'unavailable' if state in ('missing','blocked') else 'unborn')
        detached = branch.startswith('detached ')
        branch = branch.removeprefix('detached ')
        spans = [(identity, self.role('repo_owned' if remote.get('owned') else 'repo')),
                 (' ' + ui.branch_label(branch), self.role('detached' if detached else 'branch'))]
        for role, fallback in (('ahead', '󱦲'), ('behind', '󱦳')):
            count = row.get(role)
            if count:
                glyph = ui.icon('git.' + role, fallback) if ui.icons else ''
                space = '' if glyph and role == 'behind' and row.get('ahead') else ' '
                spans.append((space + (glyph or role + ' ') + str(count), self.role(role)))
        if state and (self.mode == 'verbose' or state in ('missing', 'blocked', 'conflict')):
            spans.append(('  ' + state, self.role(state)))
        ui._spans(spans, prefix=[(self.header_prefix, self.guide)],
                  continuation_prefix=[(self.gutter + ' ', self.guide)])
        if row.get('pointer_changed'): ui.detail('Pointer', 'differs from parent index', self.role('modified'))
        if row.get('reason'): ui._spans([('Reason  ', '93'), (row['reason'], None)], [(self.gutter + ' ', self.guide)],
                                         continuation_prefix=[(self.gutter + ' ', self.guide)])

    def box(self, row):
        ui = self.ui
        remote = row.get('remote') or {}
        url = remote.get('url') or ''
        protocol = url.split('://', 1)[0] if '://' in url else 'ssh' if remote.get('host') else 'local' if url else ''
        fields = [('Host', remote.get('host')), ('Protocol', protocol), ('Remote', remote.get('name')),
                  ('Upstream', (row.get('upstream') or '').removeprefix('refs/remotes/')), ('Owner', remote.get('owner')),
                  ('Root', row['path'] if self.full_paths else ui.path(row['path']))]
        if self.mode == 'verbose':
            fields.extend([('HEAD', row.get('head') or 'unborn'), ('URL', url), ('Tracking', row.get('upstream'))])
            if row.get('recorded_commit'): fields.append(('Recorded', row['recorded_commit']))
            if remote.get('owned') is not None: fields.append(('Owned', 'yes' if remote['owned'] else 'no'))
        fields = [(key, ui.clean(value or 'unavailable')) for key, value in fields]
        labels = max(len(key) for key, _ in fields)
        available = ui.width - cells(self.gutter) - labels - 6
        if available < 2:
            for key, value in fields: ui._spans([(key + ' ', '94'), (value, None)], [(self.gutter, self.guide)],
                                                 continuation_prefix=[(self.gutter, self.guide)])
            return
        width = min(available, max(cells(value) for _, value in fields))
        tl, tr, bl, br, rule = '┌', '┐', '└', '┘', '─'
        edge = rule * (labels + width + 4)
        ui.emit(ui.paint_guide(self.gutter + tl + edge + tr, self.guide))
        for key, value in fields:
            path_style = ui.resources.match_style('', kind='dir')[0] if key == 'Root' else None
            for line in wrap(value, width):
                ui.emit(ui.paint_guide(self.gutter + self.vertical + ' ', self.guide) + ui.paint(key.ljust(labels), '94') +
                        '  ' + (ui.paint(line, path_style) if path_style else line) + ' ' * (width - cells(line) + 1) + ui.paint_guide(self.vertical, self.guide))
                key = ''
        ui.emit(ui.paint_guide(self.gutter + bl + edge + br, self.guide))

    def file(self, repo, row, ui=None, *, listed=False):
        target = ui or self.ui
        name = row['path']
        def resource(name):
            actual = Path(repo) / name
            return target.path_spans(actual, str(actual) if self.full_paths else name)
        from style_config import code as style_code
        xy = row.get('xy') or ''
        code = self.state_role(xy, row.get('changed', False))
        group_fg = foreground_only(style_code(code)) if target.color else None
        spans = []
        if not listed and xy: spans.append(('[' + xy + '] ', code))
        if row.get('old_path'):
            spans.extend(resource(row['old_path']))
            spans.append((' → ', None))
        spans.extend(resource(name))
        last = row.get('_last')
        outer = (self.gutter + ' ', self.guide)
        prefix = [outer, ((self.end if last else self.fork) + ' ', group_fg)]
        continued = [outer, ('  ' if last else self.vertical + ' ', group_fg)]
        target._spans(spans, prefix, continuation_prefix=continued)

    def metadata(self, row):
        ui = self.ui
        ui.resource_detail('Path', row['path'], kind='dir')
        if row.get('head') is not None: ui.detail('HEAD', row['head'] or 'unborn')
        if 'upstream' in row: ui.detail('Upstream', row['upstream'] or 'unavailable')
        remote = row.get('remote')
        if remote:
            for label, key in (('Remote','name'),('URL','url'),('Owner','owner')):
                ui.detail(label, remote.get(key) or 'unavailable')
            owned = remote.get('owned')
            unknown = remote.get('ownership') or 'unavailable'
            ui.detail('Owned', ('yes' if owned else 'no') if owned is not None else
                      'unavailable' if unknown == 'configured' else unknown)
        if row.get('recorded_commit'): ui.detail('Recorded', row['recorded_commit'])

    def status(self, row, label=None):
        self.header(row, label)
        if self.mode != 'short' and (self.mode == 'verbose' or Path(row['path']) == self.root) and row.get('status') not in ('missing', 'blocked'):
            self.box(row)
        self.file_list(row['path'], row.get('files', []))

    @staticmethod
    def groups(files):
        groups = {}
        for file in files:
            groups.setdefault((file.get('xy') or '  ', bool(file.get('changed'))), []).append(file)
        return groups

    def state_label(self, xy, changed=False):
        if self.mode == 'short': return '[' + xy + ']'
        label = STATES.get(xy.strip(), xy.strip()) if changed else file_label(xy)
        return ('[' + xy + '] ' if self.mode == 'verbose' else '') + label

    def state_role(self, xy, changed=False):
        return self.role('modified' if changed and xy[:1] in ('M', 'T') else file_role(xy))

    def summary(self, files, *, ui=None, label='States', empty=None):
        target = ui or self.ui
        spans = []
        for (xy, changed), entries in self.groups(files).items():
            if spans: spans.append((' / ', None))
            spans.append((f'{self.state_label(xy, changed)} ({len(entries)})', self.state_role(xy, changed)))
        if spans:
            if label in ('States', 'Changes'):
                target._spans([(label + '  ', '94'), *spans], prefix=[(self.gutter + ' ', self.guide)],
                              continuation_prefix=[(self.gutter + '   ', self.guide)], icon_styles=False)
            else: target.detail_spans(label, spans)
        elif empty is not None: target.detail(label, empty)

    def file_list(self, repo, files, *, ui=None):
        target = ui or self.ui
        if self.mode == 'short':
            self.summary(files, ui=target)
            for i, file in enumerate(files): self.file(repo, dict(file, _last=i == len(files)-1), ui=target)
            return
        for (xy, changed), entries in self.groups(files).items():
            role = file_icon_role(xy)
            icon = target.icon('git.status.' + role, STATUS_ICONS[role]) if target.icons else ''
            label = (icon + ' ' if icon else '') + self.state_label(xy, changed) + f' ({len(entries)})'
            # A shared glyph must not inherit another surface's icon override.
            target._spans([(label, self.state_role(xy, changed))], prefix=[(self.gutter + ' ', self.guide)],
                          continuation_prefix=[(self.gutter + ' ', self.guide)], icon_styles=False)
            for i, file in enumerate(entries): self.file(repo, dict(file, _last=i == len(entries)-1), ui=target, listed=True)

    def info(self, row, label=None):
        self.header(row, label)
        if (self.mode == 'verbose' or self.mode != 'short' and Path(row['path']) == self.root) and row.get('status') not in ('missing', 'blocked'): self.box(row)
        self.summary(row.get('files', []), label='Changes')
        if row.get('selector'): self.ui.detail('Selector', row['selector'])
        if row.get('submodules'):
            counts = row['submodules']
            self.ui.detail('Submodules', f"{counts['total']} discovered / {counts['available']} available / {counts['missing']} missing / {counts['blocked']} blocked")

    def identity(self, path, target):
        identity = str(path) if self.full_paths else Path(path).name
        if not self.full_paths and self.root and Path(path) != self.root and Path(path).is_relative_to(self.root):
            identity = Path(path).relative_to(self.root).as_posix()
        return target.repository_label(path, identity)

    def flush_selected(self, path):
        """Render one complete review batch; original operation events stay intact."""
        selected = self.selections.pop(str(path), {})
        if not selected: return
        if self.last_repo != str(path):
            role = next(iter(selected.values()))['repo_role']
            self.ui._spans([(self.identity(path, self.ui), self.role(role))], prefix='  ')
        self.file_list(path, list(selected.values()))
        for name, row in selected.items():
            self.files.add((str(path), name))
            if row.get('note'): self.ui.detail('Details', row['note'])
        self.last_repo = str(path)

    def event(self, path, state, detail, file='', xy='', *, ui=None, repo_role='repo'):
        target = self.ui if ui is None else ui
        key = (str(path), file)
        if file and state == 'selected':
            row = self.selections.setdefault(str(path), {}).setdefault(file, dict(path=file))
            row.update(xy=xy or row.get('xy', ''), old_path=self.renames.get(key, ''), repo_role=repo_role)
            if not xy: row['note'] = detail
            return
        if state != 'planned': self.flush_selected(path)
        if file and key in self.files and state not in ('blocked','failed','pending'):
            if self.mode == 'verbose': target.detail(state.capitalize(), detail)
            return
        if file: self.files.add(key)
        if state == 'unchanged' and str(path) in self.previews and self.mode != 'verbose': return
        if state in ('planned','unchanged'): self.previews.add(str(path))
        identity = self.identity(path, target)
        role = 'blocked' if state in ('blocked','failed') else 'clean' if state in ('published','updated','unchanged') else 'modified'
        if file:
            if self.last_repo != str(path):
                target._spans([(identity, self.role(repo_role))], prefix='  ')
            self.file(path, dict(path=file,xy=xy,old_path=self.renames.get(key,'')), ui=target)
            if state in ('blocked','failed','pending') or self.mode == 'verbose' and not xy: target.detail('Details', detail)
        else:
            target._spans([(identity, self.role(repo_role)), ('  ' + state, self.role(role))], prefix='  ')
            if state in ('planned','blocked','failed','pending','cancelled','skipped') or self.mode == 'verbose': target.detail('Details', detail)
        self.last_repo = str(path)

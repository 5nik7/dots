"""Git human views over existing records. Never discovers or mutates a repository."""
from pathlib import Path
import os

from cli_preferences import VIEWS, git_view


def arguments(parser):
    parser.add_argument('--view', choices=VIEWS, action='append', dest='_views', help='select the human output view')
    parser.add_argument('-s', '--short', action='append_const', const='short', dest='_views', help='use compact human output')
    parser.add_argument('-v', '--verbose', action='append_const', const='verbose', dest='_views', help='show metadata and action details without patches')


def resolve(args, ui):
    modes = set(getattr(args, '_views', None) or [])
    if getattr(args, 'details', False): modes.add('verbose')
    if len(modes) > 1: raise ValueError('conflicting Git views; select default, short or verbose')
    return git_view(next(iter(modes), None), human=ui.stream.isatty() or os.environ.get('DOTS_MENU_CAPTURE') == '1', data=args.json)


STATES = {'M': 'modified', 'A': 'added', 'D': 'deleted', 'R': 'renamed',
          'C': 'copied', 'T': 'type changed', 'U': 'unmerged'}
CONFLICTS = {'DD': 'both deleted', 'AU': 'added by us', 'UD': 'deleted by them',
             'UA': 'added by them', 'DU': 'deleted by us', 'AA': 'both added', 'UU': 'both modified'}


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


class GitView:
    def __init__(self, ui, mode, full_paths=False, root=None):
        self.ui, self.mode, self.full_paths = ui, mode, full_paths
        self.root = Path(root) if root else None
        self.last_repo = None
        self.files = set()
        self.previews = set()
        self.renames = {}

    def role(self, name):
        return self.ui.resources.git_style(name)

    def header(self, row, label=None):
        ui = self.ui
        path = Path(row['path'])
        label = str(path) if self.full_paths else label or path.name
        remote = row.get('remote') or {}
        identity = ui.repository_label(path, label, remote.get('host'))
        branch = row.get('branch') or ('detached ' + row['head'][:8] if row.get('head') else 'unborn' if row.get('status') not in ('missing','blocked') else 'unavailable')
        state = row.get('status', '')
        spans = [(identity, self.role('repo_owned' if remote.get('owned') else 'repo')),
                 ('  ' + ui.branch_label(branch), self.role('detached' if branch.startswith('detached ') else 'branch')),
                 ('  ' + state, self.role(state))]
        if row.get('ahead') is not None:
            spans += [('  ' + str(row['ahead']) + ' ahead', self.role('ahead')),
                      (' / ' + str(row['behind']) + ' behind (cached)', self.role('behind'))]
        else: spans += [('  tracking unknown (cached)', '2')]
        ui._spans(spans, prefix='  ')
        if row.get('pointer_changed'): ui.detail('Pointer', 'differs from parent index', self.role('modified'))
        if row.get('reason'): ui.detail('Reason', row['reason'], self.role('blocked'))

    def file(self, repo, row, ui=None):
        path = row['path']; old = row.get('old_path', '')
        xy = row.get('xy', '')
        label = xy if self.mode == 'short' else file_label(xy, self.mode == 'verbose')
        display = str(Path(repo) / path) if self.full_paths else path
        if old: display = (str(Path(repo) / old) if self.full_paths else old) + ' → ' + display
        if row.get('changed') and self.mode != 'short': label = STATES.get(xy.strip(), xy.strip())
        role = 'modified' if row.get('changed') and xy[:1] in ('M','T') else file_role(xy)
        (ui or self.ui).resource_detail(label, Path(repo) / path, display=display,
                                       label_code=self.role(role), label_width=2 if self.mode == 'short' else None)

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
        if self.mode == 'verbose': self.metadata(row)
        for file in row.get('files', []): self.file(row['path'], file)

    def info(self, row, label=None):
        self.header(row, label)
        files = row.get('files', [])
        staged = sum(f['xy'][0] not in (' ', '?') for f in files)
        unstaged = sum(f['xy'][1] != ' ' and f['xy'] != '??' for f in files)
        changes = f"{staged} staged / {unstaged} unstaged / {sum(f['xy']=='??' for f in files)} untracked"
        self.ui.detail('Changes', changes)
        if self.mode == 'short': return
        remote = row.get('remote') or {}
        self.ui.detail('Remote', remote.get('name') or 'unavailable')
        self.ui.detail('Upstream', row.get('upstream') or 'unavailable')
        if row.get('selector'): self.ui.detail('Selector', row['selector'])
        if row.get('submodules'):
            counts = row['submodules']
            self.ui.detail('Submodules', f"{counts['total']} discovered / {counts['available']} available / {counts['missing']} missing / {counts['blocked']} blocked")
        if self.mode == 'verbose': self.metadata(row)

    def event(self, path, state, detail, file='', xy='', *, ui=None, repo_role='repo'):
        target = self.ui if ui is None else ui
        key = (str(path), file)
        if file and key in self.files and state not in ('blocked','failed','pending'):
            if self.mode == 'verbose': target.detail(state.capitalize(), detail)
            return
        if file: self.files.add(key)
        if state == 'unchanged' and str(path) in self.previews and self.mode != 'verbose': return
        if state in ('planned','unchanged'): self.previews.add(str(path))
        identity = str(path) if self.full_paths else Path(path).name
        if not self.full_paths and self.root and Path(path) != self.root and Path(path).is_relative_to(self.root):
            identity = Path(path).relative_to(self.root).as_posix()
        identity = target.repository_label(path, identity)
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

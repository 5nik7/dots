"""Project-scoped goal documents; inert reads and guarded journaled updates."""
from copy import deepcopy
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import re
import stat
import sys
import uuid

LIB = Path(__file__).resolve().parent
sys.path.insert(0, str(LIB / 'files'))
from file_platform import state_root, config_root, open_nofollow, check_object
from transactions import Store, digest, parents_safe

STATUSES = ('open', 'doing', 'blocked', 'done')
PRIORITIES = ('high', 'normal', 'low')
FIELDS = {'id', 'title', 'notes', 'status', 'priority', 'tags', 'due', 'parent',
          'acceptance', 'created', 'updated', 'completed', 'removed'}
LIMIT = 4 * 1024 * 1024
SCHEMA = 2
ALIAS = re.compile(r'[a-z][a-z0-9._-]{0,63}\Z')


def alias_selector(alias):
    """Keep hexadecimal names distinct from UUID selectors."""
    return '@' + alias if re.fullmatch('[0-9a-f]+', alias) else alias


def now():
    return datetime.now(timezone.utc).isoformat()


def scope(*, standalone=False, project=None, global_=False, cwd=None):
    if not standalone and (project is not None or global_):
        raise ValueError('scope overrides belong to standalone todo; dots todo always selects Dots')
    root = Path(os.environ.get('DOTS') or LIB.parents[1]).resolve()
    if standalone:
        if global_:
            root = None
        elif project is not None:
            root = Path(project).expanduser().resolve(strict=True)
            if not root.is_dir():
                raise ValueError('project must be an existing directory')
        else:
            from tmux_workspaces import configured_projects, project_root
            root = project_root(cwd or Path.cwd(), configured=configured_projects(config_root() / 'dots/projects.json'))
    path = root / '.dots/todo.json' if root else state_root() / 'todo/global.json'
    return dict(kind='project' if root else 'global', root=str(root) if root else None, path=str(path))


def text(value, label, maximum=32768, empty=True):
    if not isinstance(value, str) or '\0' in value or len(value) > maximum or (not empty and not value.strip()):
        raise ValueError('invalid ' + label)


def project_tag(selected):
    if selected['kind'] != 'project':
        return None
    root = Path(selected['root'])
    return root.name or root.anchor


def validate(doc):
    if not isinstance(doc, dict) or set(doc) != {'schema', 'goals'} or type(doc['schema']) is not int or doc['schema'] not in (1, SCHEMA):
        raise ValueError('todo document requires schema 1 or 2 and goals')
    if not isinstance(doc['goals'], list) or len(doc['goals']) > 10000:
        raise ValueError('invalid goal collection')
    identities, aliases = {}, set()
    fields = FIELDS | {'alias'} if doc['schema'] == SCHEMA else FIELDS
    for goal in doc['goals']:
        if not isinstance(goal, dict) or set(goal) != fields:
            raise ValueError('invalid goal fields')
        ident = goal['id']
        if not isinstance(ident, str) or not re.fullmatch('[0-9a-f]{32}', ident) or ident in identities:
            raise ValueError('invalid or duplicate goal ID')
        identities[ident] = goal
        alias = goal.get('alias')
        if alias is not None:
            if not isinstance(alias, str) or not ALIAS.fullmatch(alias):
                raise ValueError('alias must be 1-64 lowercase letters, digits, dots, underscores or hyphens, starting with a letter')
            if alias in aliases:
                raise ValueError('alias already belongs to a goal in this scope, including removed goals')
            aliases.add(alias)
        text(goal['title'], 'title', 256, False)
        text(goal['notes'], 'notes')
        if goal['status'] not in STATUSES or goal['priority'] not in PRIORITIES:
            raise ValueError('invalid goal status or priority')
        for field in ('tags', 'acceptance'):
            values = goal[field]
            if not isinstance(values, list) or len(values) > 256:
                raise ValueError('invalid ' + field)
            for value in values:
                text(value, field, 1024, False)
            if len(set(values)) != len(values):
                raise ValueError('duplicate ' + field)
        if goal['due'] is not None:
            if not isinstance(goal['due'], str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', goal['due']):
                raise ValueError('due date must be YYYY-MM-DD')
            date.fromisoformat(goal['due'])
        if goal['parent'] is not None and not isinstance(goal['parent'], str):
            raise ValueError('invalid parent ID')
        for field in ('created', 'updated', 'completed', 'removed'):
            value = goal[field]
            if value is None and field in ('completed', 'removed'):
                continue
            if not isinstance(value, str) or datetime.fromisoformat(value).tzinfo is None:
                raise ValueError('invalid goal timestamp')
        if (goal['status'] == 'done') != (goal['completed'] is not None):
            raise ValueError('completion timestamp disagrees with status')
    for goal in doc['goals']:
        seen = {goal['id']}
        parent = goal['parent']
        while parent is not None:
            if parent not in identities or parent in seen:
                raise ValueError('missing parent or cyclic goals')
            seen.add(parent)
            parent = identities[parent]['parent']
    if len((json.dumps(doc, indent=2, ensure_ascii=False) + '\n').encode('utf-8')) > LIMIT:
        raise ValueError('todo document exceeds 4 MiB')
    return doc


class Goals:
    def __init__(self, selected):
        self.scope = selected
        self.path = Path(selected['path'])
        parents_safe(self.path)
        check_object(self.path)
        if os.path.lexists(self.path):
            info = self.path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_size > LIMIT:
                raise ValueError('todo storage must be a regular file of at most 4 MiB')
            self.guard = digest(self.path)
            fd = open_nofollow(self.path, os.O_RDONLY)
            with os.fdopen(fd, 'r', encoding='utf-8') as stream:
                raw = stream.read(LIMIT + 1)
            if len(raw) > LIMIT:
                raise ValueError('todo document exceeds 4 MiB')
            try:
                def unique(pairs):
                    result = {}
                    for key, value in pairs:
                        if key in result: raise ValueError('duplicate JSON key')
                        result[key] = value
                    return result
                self.document = validate(json.loads(raw, object_pairs_hook=unique))
            except (ValueError, TypeError, OverflowError):
                raise ValueError('invalid todo document; preserve the file and repair or restore it') from None
            if digest(self.path) != self.guard:
                raise ValueError('todo changed while reading; retry')
        else:
            self.guard = None
            self.document = dict(schema=SCHEMA, goals=[])
        # Reads expose the current contract without migrating the stored file.
        # Comparing normalized records also keeps unchanged mutations inert.
        if self.document['schema'] == 1:
            self.document = dict(schema=SCHEMA,
                                 goals=[dict(g, alias=None) for g in self.document['goals']])

    @property
    def goals(self):
        return self.document['goals']

    def find(self, identity, removed=None):
        if not isinstance(identity, str) or not identity:
            raise ValueError('invalid goal selector')
        if identity.startswith('@'):
            name = identity[1:]
            if not ALIAS.fullmatch(name): raise ValueError('invalid goal alias')
            matches = [g for g in self.goals if g['alias'] == name]
        elif re.fullmatch('[0-9a-f]+', identity):
            if len(identity) > 32:
                raise ValueError('hexadecimal goal aliases require the @ prefix')
            matches = [g for g in self.goals if g['id'].startswith(identity)]
        elif ALIAS.fullmatch(identity):
            matches = [g for g in self.goals if g['alias'] == identity]
        else:
            raise ValueError('invalid goal selector')
        if len(matches) != 1:
            raise ValueError('ambiguous goal ID' if matches else 'goal not found in selected scope')
        if removed is not None and bool(matches[0]['removed']) != removed:
            raise ValueError('goal not found in selected scope with the required removal state')
        return matches[0]

    def descendants(self, identity):
        children = {}
        for goal in self.goals:
            children.setdefault(goal['parent'], []).append(goal)
        result, pending = [], list(children.get(identity, []))
        while pending:
            goal = pending.pop(0)
            result.append(goal)
            pending.extend(children.get(goal['id'], []))
        return result

    def selected(self, args):
        result = []
        for goal in self.goals:
            if bool(goal['removed']) != bool(args.removed):
                continue
            if args.status and goal['status'] != args.status:
                continue
            if not args.status and not args.all and not args.removed and goal['status'] == 'done':
                continue
            if args.priority and goal['priority'] != args.priority:
                continue
            if args.tag and not set(args.tag).issubset(goal['tags']):
                continue
            if args.overdue and (not goal['due'] or goal['due'] >= date.today().isoformat() or goal['status'] == 'done'):
                continue
            haystack = ' '.join([goal['alias'] or '', goal['title'], goal['notes'], *goal['tags'], *goal['acceptance']]).casefold()
            if not all(term in haystack for term in (args.query or '').casefold().split()):
                continue
            result.append(goal)
        return sorted(result, key=lambda g: (PRIORITIES.index(g['priority']), g['due'] or '9999-99-99', g['created'], g['id']))

    def mutate(self, action, identity=None, *, dry_run=False, expected=None, **changes):
        if expected is not None and expected != self.guard:
            raise ValueError('goal changed since selection; reopen it')
        original = deepcopy(self.document)
        stamp = now()
        recursive = changes.pop('recursive', False)
        clear = changes.pop('clear', []) or []
        note = changes.pop('note', None)
        if action == 'add':
            parent = changes.get('parent')
            if parent:
                parent_goal = self.find(parent, False)
                if parent_goal['status'] == 'done':
                    raise ValueError('reopen the parent before adding a subgoal')
                changes['parent'] = parent_goal['id']
            goal = dict(id=uuid.uuid4().hex, alias=None, title='', notes='', status='open', priority='normal',
                        tags=[], due=None, parent=None, acceptance=[], created=stamp, updated=stamp,
                        completed=None, removed=None)
            self.goals.append(goal)
        else:
            goal = self.find(identity, True if action == 'restore' else False)
        affected = [goal]
        if action in ('remove', 'restore'):
            descendants = self.descendants(goal['id'])
            if action == 'remove' and any(not g['removed'] for g in descendants) and not recursive:
                raise ValueError('goal has subgoals; use --recursive to remove the subtree')
            affected += descendants if recursive else []
            for item in affected:
                target = stamp if action == 'remove' else None
                if bool(item['removed']) != bool(target):
                    item['removed'] = target
        else:
            changes = {key: value for key, value in changes.items() if value is not None}
            if action == 'note':
                text(note, 'note', empty=False)
                old_notes = goal['notes']
                separator = '' if not old_notes or old_notes.endswith('\n\n') else '\n' if old_notes.endswith('\n') else '\n\n'
                changes['notes'] = old_notes + separator + note
            for key in clear:
                changes[key] = [] if key in ('tags', 'acceptance') else None if key in ('due', 'alias') else ''
            if action in ('start', 'done', 'reopen'):
                changes['status'] = {'start': 'doing', 'done': 'done', 'reopen': 'open'}[action]
            if changes.get('status') == 'done' and any(not g['removed'] and g['status'] != 'done' for g in self.descendants(goal['id'])):
                raise ValueError('complete unfinished subgoals first')
            if changes.get('status', goal['status']) != 'done' and goal['parent']:
                ancestor = self.find(goal['parent'])
                if not ancestor['removed'] and ancestor['status'] == 'done':
                    raise ValueError('reopen the completed parent first')
            for key, value in changes.items():
                if key not in ('title', 'alias', 'notes', 'status', 'priority', 'tags', 'due', 'parent', 'acceptance'):
                    raise ValueError('unsupported goal field')
                goal[key] = value
            if goal['status'] == 'done' and goal['completed'] is None:
                goal['completed'] = stamp
            elif goal['status'] != 'done':
                goal['completed'] = None
        if action == 'restore':
            restored = {g['id'] for g in affected}
            for item in affected:
                if item['parent'] and self.find(item['parent'])['removed'] and item['parent'] not in restored:
                    raise ValueError('restore the parent first')
                if item['parent'] and item['status'] != 'done' and self.find(item['parent'])['status'] == 'done':
                    raise ValueError('reopen the completed parent first')
        validate(self.document)
        tag = project_tag(self.scope)
        if tag is not None:
            missing = [item for item in self.goals if tag not in item['tags']]
            full = [item['id'] for item in missing if len(item['tags']) >= 256]
            if full:
                raise ValueError('project tag would exceed 256 tags for goals: ' + ', '.join(full))
            for item in missing:
                item['tags'].append(tag)
        old_goals = {item['id']: item for item in original['goals']}
        affected_ids = {item['id'] for item in affected}
        for item in self.goals:
            if old_goals.get(item['id']) != item:
                item['updated'] = stamp
                if item['id'] not in affected_ids:
                    affected.append(item)
                    affected_ids.add(item['id'])
        validate(self.document)
        unchanged = original == self.document
        result = dict(schema=SCHEMA, scope=self.scope, action=action,
                      status='unchanged' if unchanged else 'planned' if dry_run else 'complete',
                      goals=deepcopy(affected), transaction=None)
        if not unchanged and not dry_run:
            transaction = Store(state_root()).apply('todo-' + action,
                [dict(path=str(self.path), text=json.dumps(self.document, indent=2, ensure_ascii=False) + '\n')],
                {str(self.path): self.guard}, retain=True)
            result['transaction'] = transaction['id']
        return result

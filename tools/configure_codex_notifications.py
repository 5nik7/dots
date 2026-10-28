#!/usr/bin/env python3
"""Preview or transactionally install Dots Codex attention notifications.

This maintenance helper adds no public dots route. It preserves unrelated TOML,
hook handlers and notification commands; it never starts Codex or trusts hooks.
"""
import argparse
import copy
import json
import os
from pathlib import Path
import shlex
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib/dots'))
sys.path.insert(0, str(ROOT / 'lib/dots/files'))
from transactions import Store, digest
from file_platform import state_root


def read(path):
    if path.is_symlink():
        raise ValueError('linked configuration requires source-owner maintenance')
    if not path.exists():
        return ''
    if not path.is_file() or path.stat().st_size > 1048576:
        raise ValueError('unsupported configuration object')
    return path.read_text(encoding='utf-8')


def merge_config(text, notify):
    try:
        import tomlkit
    except ImportError as error:
        raise RuntimeError('setup requires tomlkit; see tools/requirements-codex-notifications.txt') from error
    doc = tomlkit.parse(text)
    before = tomllib.loads(text)
    doc['notify'] = notify
    for table in ('features', 'tui'):
        if table not in doc:
            doc[table] = tomlkit.table()
    doc['features']['hooks'] = True
    doc['tui']['notification_condition'] = 'unfocused'
    titles = before.get('tui', {}).get('terminal_title', ['activity', 'project-name', 'run-state'])
    if titles is None:
        titles = []
    if not isinstance(titles, list) or any(not isinstance(item, str) for item in titles):
        raise ValueError('invalid terminal title configuration')
    titles = [item for item in titles if item != 'thread-id']
    for item in ('activity', 'run-state'):
        if item not in titles:
            titles.append(item)
    titles.append('thread-id')  # The bridge accepts only the final title field.
    doc['tui']['terminal_title'] = titles
    output = tomlkit.dumps(doc)
    after = tomllib.loads(output)
    # Guard the semantic boundary as well as retaining formatting/comments.
    def unrelated(value):
        value = copy.deepcopy(value)
        value.pop('notify', None)
        for table, keys in [('features', ['hooks']), ('tui', ['notification_condition', 'terminal_title'])]:
            if table in value:
                for key in keys:
                    value[table].pop(key, None)
                if not value[table]:
                    value.pop(table)
        return value
    if unrelated(before) != unrelated(after):
        raise ValueError('unrelated configuration changed')
    return output


def plan(home, repo=ROOT):
    home, repo = Path(home), Path(repo).resolve()
    if not home.is_absolute():
        raise ValueError('CODEX_HOME must be absolute')
    paths = [home / name for name in ('config.toml', 'hooks.json', 'dots-notifications.json')]
    original = [read(path) for path in paths]
    config = tomllib.loads(original[0])
    old = json.loads(original[2]) if original[2] else {}
    if old and old.get('owner') != 'dots-codex-alerts':
        raise ValueError('unowned notification record')
    bridge = repo / 'config/tmux/codex-alerts.py'
    template_path = repo / 'config/tmux/codex-hooks.json'
    template = json.loads(read(template_path))
    command = shlex.join([sys.executable, '-B', str(bridge), 'hook'])
    notify = [sys.executable, '-B', str(bridge), 'notify']
    previous_notify = config.get('notify')
    if old:
        expected = old.get('notify')
        if previous_notify != expected:
            raise ValueError('notification setting drifted; preserve or resolve it before setup')
        previous_notify = old.get('previous_notify')
    if previous_notify is not None and (not isinstance(previous_notify, list)
            or not previous_notify or any(not isinstance(item, str) for item in previous_notify)):
        raise ValueError('invalid existing notify command')
    hooks = json.loads(original[1]) if original[1] else {'hooks': {}}
    if not isinstance(hooks, dict) or not isinstance(hooks.get('hooks', {}), dict):
        raise ValueError('invalid hook configuration')
    hooks.setdefault('hooks', {})
    owned = {command, old.get('hook_command')}
    for event, groups in list(hooks['hooks'].items()):
        cleaned = []
        for group in groups:
            group = copy.deepcopy(group)
            group['hooks'] = [handler for handler in group['hooks']
                              if not (handler.get('type') == 'command' and handler.get('command') in owned)]
            if group['hooks']:
                cleaned.append(group)
        hooks['hooks'][event] = cleaned
    for event, groups in template['hooks'].items():
        for group in groups:
            for handler in group['hooks']:
                handler['command'] = command
        hooks['hooks'].setdefault(event, []).extend(groups)
    marker = dict(schema=1, owner='dots-codex-alerts', bridge=str(bridge), hook_command=command,
                  notify=notify, previous_notify=previous_notify)
    desired = [merge_config(original[0], notify), json.dumps(hooks, ensure_ascii=False, indent=2) + '\n',
               json.dumps(marker, ensure_ascii=False, indent=2) + '\n']
    operations = [{'path': str(path), 'text': text} for path, old_text, text in zip(paths, original, desired)
                  if old_text != text]
    guards = {str(path): digest(path) for path in paths}
    for source in (bridge, template_path, repo / 'config/tmux/codex-alerts.toml', repo / 'config/tmux/codex-status.py'):
        guards[str(source)] = digest(source)
        if guards[str(source)] is None:
            raise ValueError('missing notification source')
    return operations, guards


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='apply the guarded preview with retained recovery')
    parser.add_argument('--dry-run', action='store_true', help='preview only, including when --apply is present')
    parser.add_argument('--undo', metavar='TRANSACTION', help='preview/apply undo of this helper\'s setup')
    args = parser.parse_args()
    if os.name == 'nt':
        parser.exit(2, 'Codex attention setup has no native Windows tmux/Termux destination.\n')
    try:
        store = Store(state_root())
        if args.undo:
            if store.load(args.undo)['action'] != 'codex-notifications-setup':
                raise ValueError('not a notification setup transaction')
            operations, guards, catalogs = store.inverse(args.undo)
        else:
            operations, guards = plan(Path(os.environ.get('CODEX_HOME', Path.home() / '.codex')))
            catalogs = ()
        # Never print configuration bodies, existing command arguments or secrets.
        print(json.dumps({'action': 'undo' if args.undo else 'setup',
                          'changes': [op['path'] for op in operations],
                          'apply': args.apply and not args.dry_run}, ensure_ascii=False))
        if args.apply and not args.dry_run:
            previous_umask = os.umask(0o077)
            try:
                result = store.apply('codex-notifications-undo' if args.undo else 'codex-notifications-setup',
                                     operations, guards, retain=True, catalogs=catalogs)
            finally:
                os.umask(previous_umask)
            print(json.dumps({key: result[key] for key in ('id', 'status') if key in result}))
    except RuntimeError as error:
        parser.exit(2, str(error) + '\n')
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        parser.exit(2, 'Setup refused: check config syntax, ownership, notify drift, paths and transaction recovery. No configuration content was printed.\n')


if __name__ == '__main__':
    main()

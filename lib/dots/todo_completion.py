"""Trusted, on-demand todo completion. Never execute extensions or write state."""
import os
import subprocess
import sys
from todo_commands import COMMANDS, OPTIONS, SCOPE


def complete(words, standalone=False):
    current = words[-1] if words else ''
    previous = words[:-1]
    action, pending, positionals, values, literal = '', None, [], {}, False
    for word in previous:
        if pending:
            values[pending] = word
            pending = None
        elif not literal and word == '--':
            literal = True
        elif not literal and word.startswith('--'):
            name, equal, value = word[2:].partition('=')
            if name not in OPTIONS:
                return
            if OPTIONS[name][0] == 'flag':
                values[name] = True
            elif equal:
                values[name] = value
            else:
                pending = name
        elif not action and word in COMMANDS and word:
            action = word
        else:
            positionals.append(word)
    lead = ''
    if current.startswith('--') and '=' in current:
        pending, _, current = current[2:].partition('=')
        lead = '--' + pending + '='
    def emit(value, description=''):
        from resources import clean
        if value.startswith(current) and not any(c in value for c in '\t\r\n\0'):
            print('candidate\t' + lead + value + '\t' + clean(description))
    names = (*SCOPE, *COMMANDS[action][2])
    if pending:
        if pending not in names:
            return
        kind = OPTIONS[pending][0]
        if kind.startswith('choice:'):
            for value in kind[7:].split(','): emit(value)
            return
        if kind == 'directory':
            print('directory\t' + lead + '\t')
            return
        if kind not in ('todo-id', 'todo-tag'):
            return
    elif current.startswith('-') and not literal:
        for name in names:
            if standalone or name not in ('project', 'global'):
                emit('--' + name, OPTIONS[name][1])
        emit('--help', 'Show help')
        return
    elif not action:
        for name, row in COMMANDS.items():
            if name: emit(name, row[0])
        return
    elif COMMANDS[action][1] and COMMANDS[action][1][1] == 'todo-id' and not positionals:
        kind = 'todo-id'
    else:
        return
    from todo_core import Goals, scope, alias_selector
    if values.get('global') and values.get('project'):
        return
    store = Goals(scope(standalone=standalone, project=values.get('project'), global_=bool(values.get('global'))))
    if kind == 'todo-tag':
        for tag in sorted({tag for g in store.goals if not g['removed'] for tag in g['tags']}): emit(tag)
    else:
        for goal in store.goals:
            if action == 'restore' and not goal['removed']:
                continue
            if (action not in ('restore', 'show', 'brief') or pending == 'parent') and goal['removed']:
                continue
            alias = goal['alias']
            candidate = ('@' + alias if current.startswith('@') else alias_selector(alias)) if alias else None
            value = candidate if candidate and candidate.startswith(current) else goal['id']
            emit(value, goal['title'] + ' · ' + ('removed' if goal['removed'] else goal['status']))


if __name__ == '__main__':
    try:
        complete(sys.argv[2:], standalone=sys.argv[1] == 'standalone')
    except (ValueError, OSError, subprocess.SubprocessError):
        pass

"""Shared todo command boundary; presentation and interaction stay optional."""
import json
import os
from pathlib import Path
import subprocess
import sys

from todo_commands import COMMANDS, OPTIONS, SCOPE, parser
from todo_core import Goals, scope, SCHEMA
from interaction import SelectionEnded, terminal, gum_confirm
from resources import clean
from todo_brief import brief


def markdown(selected, goals):
    lines = ['# Goals: ' + clean(selected['root'] or 'global'), '']
    for goal in goals:
        lines += ['## ' + clean(goal['title']), '',
                  'ID: `' + goal['id'] + '`',
                  'Status: ' + goal['status'] + ' | Priority: ' + goal['priority'] +
                  (' | Due: ' + goal['due'] if goal['due'] else '')]
        if goal.get('alias'):
            lines.append('Alias: `' + goal['alias'] + '`')
        if goal['parent']:
            lines.append('Parent: `' + goal['parent'] + '`')
        if goal['removed']:
            lines.append('Removed: ' + goal['removed'])
        if goal['tags']:
            lines.append('Tags: ' + ', '.join(clean(t) for t in goal['tags']))
        if goal['notes']:
            lines += ['', *[clean(line) for line in goal['notes'].splitlines()]]
        if goal['acceptance']:
            lines += ['', 'Acceptance criteria:', '', *['- ' + clean(item) for item in goal['acceptance']]]
        lines.append('')
    if not goals:
        lines += ['No matching goals.', '']
    return '\n'.join(lines)


def render(selected, goals, *, detailed=False, listing=False):
    from files.catalog import Presentation
    from todo_presentation import summary, detail
    from picker_style import named_styles
    ui = Presentation(detail_indent=2)
    styles = named_styles(ui)
    ui.heading(('Goal' if detailed and len(goals) == 1 else 'Goals') + ' · ' + (Path(selected['root']).name if selected['root'] else 'global'))
    if selected['root']:
        ui.resource_detail('Project', selected['root'], label_width=0 if listing else 10)
    if not detailed or len(goals) != 1:
        ui.detail_spans('Goals', [(str(len(goals)), None)], label_width=0 if listing else 10)
    if not goals:
        ui.detail_spans('', [('No matching goals. Use add to create one.', None)], label_width=0, label_gap=0)
    for index, goal in enumerate(goals):
        if detailed:
            ui.emit()
            detail(ui, goal, goals=goals, styles=styles)
        else:
            if listing and index:
                ui.emit()
            summary(ui, goal, styles, stacked=listing)


def confirm_remove(goal, recursive=False):
    if not terminal():
        raise ValueError('removal requires --yes when not interactive')
    title = 'Remove ' + clean(goal['title']) + (' and its subtree?' if recursive else '?')
    answer = gum_confirm(title, 'Remove')
    if answer is None:
        print(title, file=sys.stderr)
        answer = input('Remove? [y/N] ').strip().casefold() in ('y', 'yes')
    if not answer:
        raise SelectionEnded(130)


def field_changes(args):
    return dict(title=args.title, alias=args.alias, notes=args.notes, priority=args.priority, tags=args.tag,
                due=args.due, acceptance=args.accept, status=args.status,
                parent=args.parent, clear=args.clear, recursive=args.recursive)


def run(argv=None, *, standalone=False, expected=None):
    command = parser(standalone)
    args = command.parse_args(argv)
    allowed = {*SCOPE, *COMMANDS[args.action or ''][2]}
    for name, (kind, _) in OPTIONS.items():
        if name == 'title' and args.action == 'add':
            continue  # The creation title is positional, not --title.
        value = getattr(args, name.replace('-', '_'))
        if value is not None and value is not False and name not in allowed:
            command.error('--' + name + ' is not supported by ' + str(args.action))
    if getattr(args, 'global') and args.project:
        command.error('--global and --project are mutually exclusive')
    if args.json and args.markdown:
        command.error('--json and --markdown are mutually exclusive')
    for name in ('color', 'icons'):
        value = getattr(args, name)
        if value:
            os.environ['DOTS_' + name.upper()] = 'never' if value == 'none' else value
    selected = scope(standalone=standalone, project=args.project, global_=getattr(args, 'global'))
    if args.action == 'path':
        print(selected['path'])
        return 0
    store = Goals(selected)
    action = args.action
    if action == 'plan':
        from todo_plan import launch
        return launch(store, store.find(args.id, False), new=args.new, dry_run=args.dry_run)
    if action in (None, 'browse') and not (args.json or args.markdown or args.print):
        if action == 'browse' or (terminal() and os.environ.get('TERM') != 'dumb'):
            from todo_menu import browse, Handoff
            result = browse(selected, args)
            return result.code if isinstance(result, Handoff) else result
    action = action or 'list'
    if action in ('list', 'browse', 'next'):
        goals = store.selected(args)
        if action == 'next':
            goals = [g for g in goals if not g['removed'] and g['status'] in ('open', 'doing')
                     and not any(not c['removed'] and c['status'] != 'done' for c in store.descendants(g['id']))][:1]
    elif action in ('show', 'brief'):
        goal = store.find(args.id)
        if action == 'brief':
            print(brief(store, goal), end='')
            return 0
        goals = [goal, *store.descendants(goal['id'])]
    else:
        changes = field_changes(args)
        if action == 'note':
            note = args.text
            if note is None:
                if args.json or args.dry_run or not terminal():
                    command.error('note requires TEXT when noninteractive or using --json/--dry-run')
                store.find(args.id, False)
                from todo_input import prompt
                note = prompt('', 'Add note', multiline=True)
            changes['note'] = note
        if action == 'add' and args.title is None:
            if args.json or args.dry_run or not terminal():
                command.error('add requires TITLE when noninteractive or using --json/--dry-run')
            from todo_input import prompt
            changes['title'] = prompt('', 'New goal title')
        if action == 'edit' and not any(value is not None for key, value in changes.items() if key not in ('recursive', 'clear')) and not args.clear:
            if args.json or args.dry_run or not terminal():
                command.error('edit requires field options when noninteractive or using --json/--dry-run')
            from todo_menu import edit_fields
            changes = edit_fields(store.find(args.id), None)
            if changes is None:
                raise SelectionEnded(130)
        if action == 'remove' and not args.yes and not args.dry_run:
            if args.json:
                command.error('--json removal requires --yes or --dry-run')
            confirm_remove(store.find(args.id, False), args.recursive)
        result = store.mutate(action, args.id, dry_run=args.dry_run, expected=expected, **changes)
        if args.json:
            print(json.dumps(result, ensure_ascii=True))
        else:
            render(selected, result['goals'])
            from files.catalog import Presentation
            ui = Presentation(detail_indent=2)
            ui.detail('Result', 'No changes made (dry run)' if result['status'] == 'planned' else result['status'])
            if result['transaction']: ui.detail('Transaction', result['transaction'])
        return 0
    if args.json:
        print(json.dumps(dict(schema=SCHEMA, scope=selected, goals=goals), ensure_ascii=True))
    elif args.markdown:
        print(markdown(selected, goals), end='')
    else:
        render(selected, goals, detailed=action == 'show', listing=action in ('list', 'browse'))
    return 0


def main(argv=None, *, standalone=False):
    try:
        return run(argv, standalone=standalone)
    except SelectionEnded as error:
        return error.status
    except (KeyboardInterrupt, EOFError):
        return 130
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print('todo: ' + clean(str(error)), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())

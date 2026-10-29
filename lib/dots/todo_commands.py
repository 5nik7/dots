"""Single static definition for todo help, parsers, adapters and completion."""
OPTIONS = {
    'global': ('flag', 'Use global goals (standalone todo only)'),
    'project': ('directory', 'Use this project directory (standalone todo only)'),
    'json': ('flag', 'Print versioned JSON without interaction'),
    'markdown': ('flag', 'Export readable Markdown'),
    'print': ('flag', 'Print goals without browsing'),
    'client': ('string', 'Exact invoking tmux client for the popup'),
    'query': ('string', 'Match words in goal text, tags and acceptance criteria'),
    'status': ('choice:open,doing,blocked,done', 'Goal status'),
    'priority': ('choice:high,normal,low', 'Goal priority'),
    'tag': ('todo-tag', 'Goal tag; repeat to filter or set tags; project tag is retained'),
    'due': ('string', 'Due date in YYYY-MM-DD format'),
    'overdue': ('flag', 'Only unfinished goals due before today'),
    'all': ('flag', 'Include completed goals'),
    'removed': ('flag', 'Select removed goals'),
    'title': ('string', 'Replacement goal title'),
    'alias': ('string', 'Explicit unique name for this goal'),
    'notes': ('string', 'Goal notes'),
    'accept': ('string', 'Acceptance criterion; repeat for several'),
    'parent': ('todo-id', 'Parent goal ID for a new subgoal'),
    'clear': ('choice:notes,due,tags,acceptance,alias', 'Clear a field; repeat for several; clearing tags retains the project tag'),
    'dry-run': ('flag', 'Preview without changing storage'),
    'yes': ('flag', 'Confirm removal without prompting'),
    'recursive': ('flag', 'Remove or restore the complete subtree'),
    'color': ('choice:auto,always,never,none', 'Color mode'),
    'icons': ('choice:auto,always,never', 'Icon mode'),
}
SCOPE = ('global', 'project', 'color', 'icons')
OUTPUT = ('json',)
FILTERS = ('query', 'status', 'priority', 'tag', 'overdue', 'all', 'removed')
EDIT = ('alias', 'notes', 'priority', 'tag', 'due', 'accept')
MUTATE = ('dry-run', 'json')
# summary, positional name/type (optional), option names
COMMANDS = {
    '': ('Browse goals for the Dots project', None, (*FILTERS, 'print', 'json', 'markdown', 'client')),
    'add': ('Create a goal or subgoal', ('title', 'string'), (*EDIT, 'parent', *MUTATE)),
    'list': ('Query and list goals', None, (*FILTERS, 'json', 'markdown')),
    'show': ('Show a goal and its subgoals', ('id', 'todo-id'), ('json', 'markdown')),
    'edit': ('Edit goal fields', ('id', 'todo-id'), ('title', *EDIT, 'status', 'clear', *MUTATE)),
    'note': ('Append details to goal notes', ('id', 'todo-id'), MUTATE),
    'start': ('Mark a goal in progress', ('id', 'todo-id'), MUTATE),
    'done': ('Complete a goal', ('id', 'todo-id'), MUTATE),
    'reopen': ('Reopen a completed or blocked goal', ('id', 'todo-id'), MUTATE),
    'remove': ('Reversibly remove a goal', ('id', 'todo-id'), ('recursive', 'yes', *MUTATE)),
    'restore': ('Restore a removed goal', ('id', 'todo-id'), ('recursive', *MUTATE)),
    'next': ('Show the highest-ranked actionable goal', None, (*FILTERS, 'json')),
    'brief': ('Prepare a read-only Markdown agent brief', ('id', 'todo-id'), ()),
    'browse': ('Browse goals in the shared popup', None, (*FILTERS, 'print', 'json', 'markdown', 'client')),
    'path': ('Print the selected goal storage path', None, ()),
}
REPEAT = ('tag', 'accept', 'clear')


def usage(action):
    if action == 'note': return 'ID [TEXT] [OPTIONS]'
    positional = COMMANDS[action][1]
    return (('[TITLE]' if action == 'add' else 'ID') + ' ' if positional else '[COMMAND] ' if not action else '') + '[OPTIONS]'


def parser(standalone=False):
    import argparse
    import sys

    class HelpAction(argparse.Action):
        def __call__(self, selected, namespace, values, option_string=None):
            import os
            for name in ('color', 'icons'):
                value = getattr(namespace, name, None)
                if value:
                    os.environ['DOTS_' + name.upper()] = 'never' if value == 'none' else value
            selected.print_help()
            selected.exit()

    class HelpParser(argparse.ArgumentParser):
        def __init__(self, *args, **kwargs):
            if sys.version_info >= (3, 14): kwargs['color'] = False
            super().__init__(*args, add_help=False, **kwargs)
            self.add_argument('-h', '--help', action=HelpAction, nargs=0, help='Show help')

        def print_help(self, file=None):
            from files.catalog import Presentation
            ui = Presentation(file, detail_indent=2)
            ui.heading(self.prog)
            ui.detail_spans('', [(self.description, None)], label_width=0, label_gap=0, indent=2)
            ui.detail('Usage', self.usage % {'prog': self.prog})
            for item in self._actions:
                if isinstance(item, argparse._SubParsersAction):
                    ui.heading('Commands')
                    for action, child in item.choices.items():
                        ui.detail(action, child.description)
                elif item.option_strings:
                    label = ', '.join(item.option_strings)
                    if item.nargs != 0:
                        label += ' VALUE'
                    ui.detail(label, item.help)

    root = HelpParser(prog='todo' if standalone else 'dots todo',
        description='Project goals with reversible updates. Bare invocation opens a popup in a terminal.')

    def populate(target, action):
        summary, positional, names = COMMANDS[action]
        target.description = 'Browse goals for the current project or global scope' if standalone and not action else summary
        target.usage = '%(prog)s ' + usage(action)
        for name in (*SCOPE, *names):
            kind, description = OPTIONS[name]
            kwargs = dict(help=description, default=argparse.SUPPRESS)
            if kind == 'flag':
                kwargs['action'] = 'store_true'
            elif name in REPEAT:
                kwargs['action'] = 'append'
            if kind.startswith('choice:'):
                kwargs['choices'] = kind[7:].split(',')
            target.add_argument('--' + name, **kwargs)
        if positional:
            kwargs = {'nargs': '?'} if action == 'add' else {}
            target.add_argument(positional[0], **kwargs)
        if action == 'note':
            target.add_argument('text', nargs='?', help='Text to append; omitted text prompts interactively')
    populate(root, '')
    children = root.add_subparsers(dest='action', metavar='COMMAND', prog=root.prog)
    for action, (summary, _, _) in COMMANDS.items():
        if action:
            populate(children.add_parser(action, help=summary), action)
    root.set_defaults(**{name.replace('-', '_'): False if kind == 'flag' else None
                         for name, (kind, _) in OPTIONS.items()})
    root.set_defaults(action=None, id=None, title=None, text=None)
    return root


def header(action):
    summary, positional, names = COMMANDS[action]
    route = 'dots todo' + (' ' + action if action else '')
    lines = ['#!/usr/bin/env bash', '# Generated by tools/generate_todo_commands.py.',
             '# dots:summary=' + summary, '# dots:usage=' + usage(action)]
    if positional:
        lines.append('# dots:argument=1|' + positional[1] + '|' + ('Goal title' if action == 'add' else 'Goal UUID, prefix or alias'))
    if action == 'note':
        lines.append('# dots:argument=2|string|Text to append')
    for name in (*SCOPE, *names):
        kind, description = OPTIONS[name]
        lines.append('# dots:option=--' + name + '||' + kind + '|' + description)
    lines.append('# dots:example=' + route + (' "A new goal"' if action == 'add' else ' add "A new goal"' if not action else ' --help'))
    lines += ['DOTS=${DOTS:-$(cd -- "${BASH_SOURCE[0]%/*}/.." && pwd -P)}',
              'exec python3 -B "$DOTS/lib/dots/todo_cli.py" ' + ('"' + action + '" ' if action else '') + '"$@"']
    return '\n'.join(lines) + '\n'

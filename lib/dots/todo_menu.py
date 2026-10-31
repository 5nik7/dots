"""Goal popup: stable identities, inert snapshots and explicit actions."""
from contextlib import nullcontext
from dataclasses import dataclass
import io
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from interaction import RichSelector, SelectionEnded, SelectionEvent, rich_fzf_available, terminal
from menu_tmux import TmuxContext, request_file, read_request
from menus import Entry, Menu, choose, show_message
from picker_style import picker_colors, named_styles
from resources import clean
from todo_core import Goals, STATUSES, PRIORITIES

HELP = ('Enter: goal actions\nAlt-N: new goal\nAlt-F: filters\nF1: this help\n'
        'Alt-C: Plan in Codex\nAlt-O: print brief and close\nAlt-Y: copy brief\n'
        'Esc: back / close\nCtrl-C: cancel\nAlt-P: preview\nAlt-J/K: scroll preview\n\n'
        'Goal changes are journaled. Remove preserves goal contents; Restore recovers them.\n'
        'Project tags are required; tag edits keep them and goal changes backfill older goals.\n'
        'Brief includes /plan and the complete subtree. Plan in Codex launches or resumes its thread.\n'
        'Planning is read-only; leave Plan Mode and request Save these goals to save the agreed tree.')


@dataclass(frozen=True)
class Handoff:
    code: int = 0


def brief_actions(store, goal, context):
    from todo_cli import brief
    from menu_pager import action_page
    from clipboard import copy
    frame, notice = {}, ''
    content = brief(store, goal)
    while True:
        action = action_page(content, title='todo·agent brief', context=context, frame=frame, notice=notice,
            actions={'alt-c': ('plan', 'Codex'), 'alt-o': ('print-brief', 'print'), 'alt-y': ('copy-brief', 'copy')})
        if action == 'actions':
            action = select('Brief', [('plan', 'Plan in Codex'), ('print-brief', 'Print brief'),
                                    ('copy-brief', 'Copy brief'), ('back', 'Back')], context)
        if action == 'copy-brief':
            try:
                copy(content)
                notice = 'Copied complete brief'
            except (ValueError, OSError, subprocess.SubprocessError) as error:
                notice = clean(str(error))
            continue
        return action


def select(title, items, context=None):
    try:
        result = choose(Menu('todo:' + title, title, tuple(Entry(key, label) for key, label in items)),
                        mode='browse', context=context, navigation={}, compact=True,
                        prompt='todo·' + title.lower(), header='Enter: choose  Esc: back  Ctrl-C: cancel')
        return result.id if result else None
    except SelectionEvent:
        return None


def edit_fields(goal, context):
    from todo_input import prompt
    field = select('Edit', [(key, key) for key in ('title', 'alias', 'notes', 'status', 'priority', 'tags', 'due', 'acceptance')], context)
    if field is None: return None
    if field in ('status', 'priority'):
        values = STATUSES if field == 'status' else PRIORITIES
        value = select(field.title(), [(item, item) for item in values], context)
        return {field: value} if value else None
    initial = goal[field]
    if isinstance(initial, list): initial = '\n'.join(initial)
    value = prompt(initial or '', 'Edit ' + field + (' (one per line)' if field in ('tags', 'acceptance') else ''),
                   context, multiline=field in ('notes', 'tags', 'acceptance'))
    if field in ('tags', 'acceptance'):
        value = list(dict.fromkeys(line.strip() for line in value.splitlines() if line.strip()))
    if field in ('due', 'alias') and not value:
        return dict(clear=[field])
    return {field: value}


def rows(store, goals, ui, width):
    from files.catalog import Presentation
    from todo_presentation import compact, detail,configure
    configure(ui)
    styles = named_styles(ui)
    labels, previews = [], []
    for goal in goals:
        depth=goal.get('_todo_depth',0)*ui.formatting.get('level_indent',2)
        labels.append(' '*min(128,depth)+compact(ui,goal,max(1,width-depth),styles,context=goal.get('_todo_context',False),child=bool(depth)))
        children = [g for g in store.descendants(goal['id']) if not g['removed']]
        progress = f"{sum(g['status'] == 'done' for g in children)}/{len(children)} complete"
        stream = io.StringIO()
        preview_ui = Presentation(stream, terminal=True, detail_indent=2)
        preview_ui.width, preview_ui.color, preview_ui.icons = max(24, width), ui.color, ui.icons
        detail(preview_ui, goal, goals=store.goals, progress=progress, styles=styles)
        previews.append(stream.getvalue())
    return labels, previews


def pick(store, goals, frame, context):
    from files.catalog import Presentation
    from files.picker import fzf_colors
    from progress import permanent_output
    from config_values import value
    from todo_tree import tree,filtered,match_indices
    from todo_presentation import compact
    tree_mode=frame.get('list_type',value('formatting.apps.todo.list_type','tree'))=='tree'
    eligible={g['id'] for g in goals}
    if tree_mode:goals=[dict(g,_todo_depth=depth,_todo_context=extra) for g,depth,extra in tree(goals,store.goals)]
    frame['_goals']=goals
    ui = Presentation(terminal=True, detail_indent=2)
    if context is None and not terminal():
        raise ValueError('goal browsing requires a terminal')
    available = rich_fzf_available()
    if available and context:
        probe = subprocess.run(['fzf', '--help'], capture_output=True, timeout=5)
        available = probe.returncode == 0 and b'--popup' in probe.stdout
    if not available:
        from todo_cli import render
        print('todo: FZF or popup support unavailable; listing goals.', file=sys.stderr)
        render(store.scope,[g for g in goals if g['id'] in eligible],listing=True,all_goals=store.goals,list_type=frame.get('list_type'))
        return None
    columns, lines = context.verify() if context else shutil.get_terminal_size((80, 24))
    width = max(1, columns - 2)
    labels, previews = rows(store, goals, ui, max(1, width - 4))
    snapshot=dict(schema=1,previews=previews)
    initial_indices=None;header_row=None
    if tree_mode:
        indent=ui.formatting.get('level_indent',2)
        snapshot.update(goals=[{k:g[k] for k in ('id','parent','priority','due','created')} for g in goals],
                        eligible=[i for i,g in enumerate(goals) if g['id'] in eligible],
                        labels=[compact(ui,g,max(1,width-4-g['_todo_depth']*indent),child=bool(g['_todo_depth'])) for g in goals],
                        context=[compact(ui,g,max(1,width-4-g['_todo_depth']*indent),context=True,child=bool(g['_todo_depth'])) for g in goals],
                        search=[clean(' '.join((g.get('alias') or '',g['title'],*g['tags']))) for g in goals],indent=indent)
        payload,matches,initial_indices=filtered(snapshot,frame.get('query',''))
        records=payload.decode().split('\0');header_row=records[0]
        for record in records[1:]:
            if record:
                token,_,text=record.partition('\t');labels[int(token)]=text
    notice_lines = int(bool(frame.get('notice')))+int(tree_mode)
    preview_lines = min(4, max(1, lines - 12 - notice_lines))
    height = max(1, lines - 2)
    from todo_layout import bindings
    layout_bindings, layout_environment = bindings(popup=context is not None, notice=notice_lines)
    label = Path(store.scope['root']).name if store.scope['root'] else 'global'
    with request_file(snapshot) as path:
        preview_command = ('& $env:DOTS_TODO_PYTHON -B $env:DOTS_TODO_MENU preview $env:DOTS_TODO_PREVIEW {1}'
                           if os.name == 'nt' else '"$DOTS_TODO_PYTHON" -B "$DOTS_TODO_MENU" preview "$DOTS_TODO_PREVIEW" {1}')
        preview = (preview_command, '',
                   dict(DOTS_TODO_PYTHON=sys.executable, DOTS_TODO_MENU=str(Path(__file__).resolve()),
                        DOTS_TODO_PREVIEW=str(path), **layout_environment))
        if tree_mode:
            command=('& $env:DOTS_TODO_PYTHON -B $env:DOTS_TODO_TREE {q}' if os.name=='nt' else '"$DOTS_TODO_PYTHON" -B "$DOTS_TODO_TREE" {q}')
            layout_bindings=[*layout_bindings,'change:reload:'+command]
            preview[2].update(DOTS_TODO_TREE=str(Path(__file__).with_name('todo_tree.py')),DOTS_TODO_TREE_DATA=str(path))
        with permanent_output(), context.selector_environment() if context else nullcontext(None) as environment:
            try:
                result = RichSelector(backend='fzf').fzf('todo·' + clean(label), labels, False, preview,
                    ui.color, ui.icons, picker_colors(fzf_colors(ui)), popup=f'center,{width},{height}' if context else False,
                    height=height, preview_position='down', preview_lines=preview_lines, preview_wrap=True,
                    query=frame.get('query', ''), header='Alt-N: new  Alt-F: filters\nAlt-C: Codex  Alt-Y: copy\nAlt-O: print  F1: help' +
                        ('\n' + frame['notice'] if frame.get('notice') else ''),
                    environment=environment, info='hidden' if tree_mode else 'inline-right', hscroll=False, navigation=frame,
                    navigation_keys={'esc': 'back', 'f1': 'help', 'alt-n': 'new', 'alt-f': 'filters',
                                     'alt-c': 'plan', 'alt-o': 'print-brief', 'alt-y': 'copy-brief'},
                    event_selection=True, bindings=layout_bindings,
                    initial_indices=initial_indices,disabled=tree_mode,header_row=header_row,
                    focus_index=next((i for i,g in enumerate(goals) if g['id']==frame.get('selected') and (initial_indices is None or i in initial_indices)),None))
            except SelectionEvent as event:
                if tree_mode:
                    matches=match_indices(snapshot,frame.get('query',''))
                    for i,g in enumerate(goals):g['_todo_context']=i not in matches
                if event.index is not None: frame['selected'] = goals[event.index]['id']
                raise
    if tree_mode:
        matches=match_indices(snapshot,frame.get('query',''))
        for i,g in enumerate(goals):g['_todo_context']=i not in matches
    frame['selected'] = goals[result[0]]['id']
    return goals[result[0]]


def apply(store, action, identity=None, **changes):
    # Re-read after time spent in dialogs; no stale snapshot can approve a write.
    current = Goals(store.scope)
    if current.guard != store.guard:
        raise ValueError('goals changed since selection; review the refreshed list')
    return current.mutate(action, identity, **changes)


def browse(selected, args, *, context=None):
    from menu_pager import page_text
    from todo_cli import brief, markdown
    from todo_input import prompt
    client = args.client
    if client and (os.name == 'nt' or not os.environ.get('TMUX')):
        raise ValueError('--client requires an originating tmux pane')
    if context is None and os.name != 'nt' and (os.environ.get('TMUX') or os.environ.get('DOTS_MENU_CONTEXT')):
        context = TmuxContext.capture(client=client) if client else TmuxContext.from_environment()
    from config_values import value
    frame = dict(query='',list_type=getattr(args,'list_type',None) or value('formatting.apps.todo.list_type','tree'))
    while True:
        store = Goals(selected)
        goals = store.selected(args)
        try:
            try:
                goal = pick(store, goals, frame, context)
                if goal is None: return 0
                choices = [('show', 'details'), ('brief', 'agent brief')]
                choices += [('print-brief', 'Print brief'), ('copy-brief', 'Copy brief')]
                if goal.get('_todo_context'):
                    choices=[('show','details (read-only ancestor)')]
                elif goal['removed']:
                    choices += [('restore', 'restore'), ('restore-tree', 'restore subtree')]
                else:
                    choices += [('plan', 'Plan in Codex'), ('edit', 'edit'), ('note', 'add note'), ('start', 'start'),
                                ('reopen', 'reopen') if goal['status'] == 'done' else ('done', 'complete'),
                                ('child', 'new subgoal'), ('remove', 'remove')]
                action = select('Actions', choices, context)
            except SelectionEvent as event:
                action = event.action
                goal = frame.get('_goals',goals)[event.index] if event.index is not None else None
            if action is None: continue
            if goal and goal.get('_todo_context') and action not in ('show','back','help','filters','new'):
                frame['notice']='Ancestor context is read-only; change the filters to select this goal'
                continue
            if action in ('plan', 'brief', 'print-brief', 'copy-brief'):
                if goal is None: continue
                if action == 'brief':
                    action = brief_actions(store, goal, context)
                if action == 'print-brief':
                    print(brief(store, goal), end='')
                    return Handoff()
                if action == 'copy-brief':
                    from clipboard import copy
                    copy(brief(store, goal))
                    frame['notice'] = 'Copied complete brief'
                elif action == 'plan':
                    from todo_plan import launch, window
                    code = window(store, goal, context) if context else launch(store, goal)
                    return Handoff(code)
                continue
            if action == 'back': return 130
            if action == 'help':
                page_text(HELP, title='Todo keys', context=context)
            elif action == 'filters':
                mode = select('Filters', [('active', 'active goals'), ('all', 'all current goals'),
                    ('done', 'completed goals'), ('removed', 'removed goals'), ('overdue', 'overdue'),
                    ('priority', 'priority'), ('tag', 'tag'), ('query', 'search goal contents'), ('reset', 'reset filters')], context)
                if mode in ('priority', 'tag', 'query'):
                    if mode == 'priority':
                        value = select('Priority', [('any', 'any'), *[(p, p) for p in PRIORITIES]], context)
                        if value: args.priority = None if value == 'any' else value
                    elif mode == 'tag':
                        value = prompt('', 'Filter tag (empty clears)', context)
                        args.tag = [value] if value else None
                    else:
                        args.query = prompt(args.query or '', 'Search goal contents (empty clears)', context)
                elif mode:
                    args.all, args.removed, args.overdue = mode == 'all', mode == 'removed', mode == 'overdue'
                    args.status = 'done' if mode == 'done' else None
                    if mode == 'reset': args.priority, args.tag, args.query = None, None, None
                frame['query'] = ''
            elif action in ('new', 'child'):
                title = prompt('', 'New goal title', context)
                result = apply(store, 'add', title=title, parent=goal['id'] if goal and action=='child' else None)
                frame['selected'] = result['goals'][0]['id']
            elif action == 'show':
                content = markdown(selected, [goal, *store.descendants(goal['id'])])
                page_text(content, title='Goal ' + goal['id'][:8], context=context)
            elif action == 'edit':
                changes = edit_fields(goal, context)
                if changes is not None: apply(store, 'edit', goal['id'], **changes)
            elif action == 'note':
                note = prompt('', 'Add note', context, multiline=True)
                apply(store, 'note', goal['id'], note=note)
            elif action == 'remove':
                children = [g for g in store.descendants(goal['id']) if not g['removed']]
                if select('Remove ' + goal['id'][:8], [('cancel', 'Cancel'),
                    ('remove', 'Remove ' + clean(goal['title']) + (f' and {len(children)} subgoals' if children else ''))], context) == 'remove':
                    apply(store, 'remove', goal['id'], recursive=bool(children))
            elif action in ('start', 'done', 'reopen', 'restore', 'restore-tree'):
                apply(store, 'restore' if action == 'restore-tree' else action, goal['id'], recursive=action == 'restore-tree')
        except SelectionEnded as error:
            if error.status == 130: raise
            show_message('Goal interaction failed; nothing was changed.', context=context, title='Todo', code=error.status)
        except (ValueError, OSError, subprocess.SubprocessError) as error:
            show_message(clean(str(error)), context=context, title='Todo', code=1)
            if context: context.verify()


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == 'preview':
        token = sys.argv[3]
        if not re.fullmatch(r'0|[1-9][0-9]*', token): sys.exit(0)
        data = read_request(sys.argv[2])['previews']
        if int(token) < len(data): print(data[int(token)], end='')
    else:
        sys.exit(2)

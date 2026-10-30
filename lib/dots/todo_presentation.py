"""Inert Todo spans shared by ordinary output and popup views."""
from picker_style import named_styles, fit
from resources import clean, cells
from todo_core import alias_selector


def identity(goal):
    return alias_selector(goal['alias']) if goal.get('alias') else goal['id'][:8]


def state(goal):
    return 'removed' if goal['removed'] else goal['status']


def status_style(goal, styles):
    return styles[{'open': 'bold_bright_green', 'doing': 'blue', 'blocked': 'yellow',
                   'done': 'green', 'removed': 'muted'}[state(goal)]]


def priority_style(goal, styles):
    return styles[{'high': 'bold_warning', 'normal': 'orange', 'low': 'bold_muted'}[goal['priority']]]


def tail(goal, styles, due=True):
    result = [(' · ', styles['muted']), (state(goal), status_style(goal, styles)),
              (' · ', styles['muted']), (goal['priority'], priority_style(goal, styles))]
    if due and goal['due']:
        result.append((' · ' + goal['due'], styles['muted']))
    return result


def summary(ui, goal, styles=None, *, stacked=False):
    styles = styles or named_styles(ui)
    label = identity(goal)
    label_code = styles['accent'] if goal.get('alias') else '94'
    spans = [(goal['title'], styles['emphasis']), *tail(goal, styles)]
    if stacked or cells(label) > min(20, max(8, ui.width // 3)):
        ui.detail_spans('', [(label, label_code)], label_width=0, label_gap=0)
        ui.detail_spans('', spans, label_width=0, label_gap=0)
    else:
        ui.detail_spans(label, spans, label_width=max(10, cells(label)),
                        label_code=label_code)


def detail(ui, goal, *, goals=(), progress=None, styles=None):
    styles = styles or named_styles(ui)
    ui.heading_spans([(goal['title'], styles['emphasis'])])
    if progress is not None: ui.detail('Subgoals', progress)
    if goal.get('alias'): ui.detail_spans('Alias', [(identity(goal), styles['accent'])])
    ui.detail_spans('Status', [(state(goal), status_style(goal, styles))])
    ui.detail_spans('Priority', [(goal['priority'], priority_style(goal, styles))])
    if goal['due']: ui.detail('Due', goal['due'])
    if goal['tags']: ui.detail('Tags', ', '.join(goal['tags']))
    if goal['parent']:
        parent = next((g for g in goals if g['id'] == goal['parent']), None)
        if parent and parent.get('alias'):
            ui.detail_spans('Parent', [(identity(parent), styles['accent'])])
        else:
            ui.detail('Parent', goal['parent'])
    if goal['notes']:
        ui.emit()
        ui.heading('Notes')
        for line in goal['notes'].split('\n'):
            if line: ui.detail_spans('', [(line, styles['foreground'])], label_width=0, label_gap=0)
            else: ui.emit()
    if goal['acceptance']:
        ui.emit()
        ui.heading('Acceptance')
        for item in goal['acceptance']:
            ui.detail_spans('-', [(item, styles['foreground'])], label_width=1)
    ui.emit()
    if ui.width < ui.detail_indent + 11 + len(goal['id']):
        ui.detail('UUID', '')
        ui.detail_spans('', [(goal['id'], None)], label_width=0, label_gap=0, indent=2)
    else:
        ui.detail('UUID', goal['id'])


def compact(ui, goal, width, styles=None):
    styles = styles or named_styles(ui)
    label = fit(identity(goal), min(16, max(4, width // 4))).rstrip()
    suffix = tail(goal, styles, due=width >= 80)
    available = max(1, width - cells(label) - 1 - sum(cells(s) for s, _ in suffix))
    title = fit(((ui.icon('status.todo', '󰄬') + ' ') if ui.icons else '') + clean(goal['title']), available).rstrip()
    spans = [(label + ' ', styles['accent'] if goal.get('alias') else styles['blue']),
             (title, styles['emphasis']), *suffix]
    result, remaining = [], width
    for text, code in spans:
        if remaining <= 0: break
        value = fit(text, remaining) if cells(text) > remaining else text
        result.append(ui.paint(value, code))
        remaining -= cells(value)
    return ''.join(result)

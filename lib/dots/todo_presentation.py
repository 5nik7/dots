"""Inert Todo spans shared by ordinary output and popup views."""
from picker_style import named_styles, fit
from resources import clean, cells
from todo_core import alias_selector


def configure(ui):
    from config_values import value
    ui.formatting=value('formatting.apps.todo',{})
    ui.detail_indent=ui.formatting.get('indent',2)
    return ui


def identity(goal):return alias_selector(goal['alias']) if goal.get('alias') else goal['id'][:8]
def state(goal):return 'removed' if goal['removed'] else goal['status']


def field(name,kind='value',fallback=None):
    from style_config import current
    prefs=current();role='todo.field.'+name+'.'+kind
    return prefs.sgr(role,app='cli') if prefs and prefs.style(role,app='cli') else fallback


def status_style(goal,styles):
    from style_config import current
    prefs=current()
    role='todo.status.'+state(goal)
    fallback=styles[{'open':'bold_bright_green','doing':'blue','blocked':'yellow','done':'green','removed':'muted'}[state(goal)]]
    return field('status',fallback=prefs.sgr(role,app='cli') if prefs and prefs.style(role,app='cli') else fallback)


def priority_style(goal,styles):
    from style_config import current
    prefs=current()
    role='todo.priority.'+goal['priority']
    fallback=styles[{'high':'bold_warning','normal':'orange','low':'bold_muted'}[goal['priority']]]
    return field('priority',fallback=prefs.sgr(role,app='cli') if prefs and prefs.style(role,app='cli') else fallback)


def tail(goal,styles,due=True):
    result=[(' · ',styles['muted']),(state(goal),status_style(goal,styles)),(' · ',styles['muted']),(goal['priority'],priority_style(goal,styles))]
    if due and goal['due']:result += [(' · ',styles['muted']),(goal['due'],field('due',fallback=styles['muted']))]
    return result


def summary(ui,goal,styles=None,*,stacked=False,context=False,child=False):
    styles=styles or named_styles(ui);label=identity(goal)
    label_code=field('alias' if goal.get('alias') else 'subgoal_id' if child else 'id',fallback=styles['accent'] if goal.get('alias') else '94')
    spans=[(goal['title'],field('subgoal_title' if child else 'title',fallback=styles['emphasis'])),*tail(goal,styles)]
    if context:
        label_code=styles['muted'];spans=[(text,styles['muted']) for text,_ in spans]+[(' [context]',styles['muted'])]
    if stacked or cells(label)>min(20,max(8,ui.width//3)):
        ui.detail_spans('',[(label,label_code)],label_width=0,label_gap=0)
        ui.detail_spans('',spans,label_width=0,label_gap=0)
    else:ui.detail_spans(label,spans,label_width=max(10,cells(label)),label_code=label_code)


def detail(ui,goal,*,goals=(),progress=None,styles=None):
    configure(ui);styles=styles or named_styles(ui)
    def row(name,label,value,fallback=None):
        ui.detail_spans(label,[(str(value),field(name,fallback=fallback or styles['foreground']))],label_code=field(name,'label','94'))
    ui.heading_spans([(goal['title'],field('title',fallback=styles['emphasis']))])
    if progress is not None:row('subgoals','Subgoals',progress)
    if goal.get('alias'):row('alias','Alias',identity(goal),styles['accent'])
    row('status','Status',state(goal),status_style(goal,styles))
    row('priority','Priority',goal['priority'],priority_style(goal,styles))
    if goal['due']:row('due','Due',goal['due'])
    if goal['tags']:row('tags','Tags',', '.join(goal['tags']))
    if goal['parent']:
        parent=next((g for g in goals if g['id']==goal['parent']),None)
        row('parent','Parent',identity(parent) if parent else goal['parent'],styles['accent'] if parent and parent.get('alias') else None)
    if goal['notes']:
        ui.emit();ui.heading_spans([('Notes',field('notes','label','96'))])
        for line in goal['notes'].split('\n'):
            if line:ui.detail_spans('',[(line,field('notes',fallback=styles['foreground']))],label_width=0,label_gap=0)
            else:ui.emit()
    if goal['acceptance']:
        ui.emit();ui.heading_spans([('Acceptance',field('acceptance','label','96'))])
        for item in goal['acceptance']:ui.detail_spans('-',[(item,field('acceptance',fallback=styles['foreground']))],label_width=1,label_code=field('acceptance','label','94'))
    ui.emit()
    if ui.width<ui.detail_indent+11+len(goal['id']):
        row('id','UUID','');ui.detail_spans('',[(goal['id'],field('id'))],label_width=0,label_gap=0)
    else:row('id','UUID',goal['id'])
    for name in ('created','updated','completed','removed'):
        if goal.get(name):row(name,name.title(),goal[name])


def compact(ui,goal,width,styles=None,*,context=False,child=False):
    styles=styles or named_styles(ui)
    label=fit(identity(goal),min(16,max(4,width//4))).rstrip()
    suffix=tail(goal,styles,due=width>=80)
    icon=(ui.icon('status.todo','󰄬')+' ') if ui.icons else ''
    available=max(1,width-cells(label)-1-cells(icon)-sum(cells(s) for s,_ in suffix))
    title=fit(clean(goal['title']),available).rstrip()
    from style_config import current
    prefs=current();icon_style=prefs.sgr('icons.status.todo',app='cli') if prefs and prefs.style('icons.status.todo',app='cli') else styles['emphasis']
    spans=[(label+' ',field('alias' if goal.get('alias') else 'subgoal_id' if child else 'id',fallback=styles['accent'] if goal.get('alias') else styles['blue'])),
           (icon,icon_style),(title,field('subgoal_title' if child else 'title',fallback=styles['emphasis'])),*suffix]
    result=[];remaining=width
    for text,code in spans:
        if remaining<=0:break
        text=fit(text,remaining) if cells(text)>remaining else text
        result.append(ui.paint(text,styles['muted'] if context else code));remaining-=cells(text)
    return ''.join(result)

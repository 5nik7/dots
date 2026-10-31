"""Profile configuration browser; selection is separate from reviewed writes."""
from contextlib import nullcontext
from dataclasses import asdict, dataclass, replace
import copy
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import textwrap

from config_cli import Plan, StylePlan, ControlPlan, Presentation, digest
from profile_config import context as profile_context, schema
from profiles import available, public_report
from style_config import Styles, APPS, ANSI, ALIASES, ATTRS, current
from interaction import RichSelector, SelectionEnded, SelectionEvent, rich_fzf_available, terminal
from menu_tmux import TmuxContext, request_file, read_request
from menus import Entry, Menu, choose, dots_argv, run_action
from menu_input import prompt
from resources import clean, cells
from picker_style import fit, picker_colors, named_styles

CATEGORIES = ('all', 'icons', 'colors', 'formatting', 'apps', 'files', 'profile', 'settings', 'environment')
HELP = ('List and Get inspect configuration; Set edits reviewed values.\n'
        'Get and Set choose a category before selecting an option.\n'
        'Enter: details / set actions   Alt-G: category   Alt-S: profile / shared defaults\n'
        'Alt-N in Set: add environment declaration   F1: help\n'
        'Esc: back / close   Ctrl-C: cancel   Alt-P: preview   Alt-J/K: scroll preview\n\n'
        'Edit reviews the saved value, proposed value and destination before Save.\n'
        'Reset removes this profile override and shows the inherited value.\n'
        'Each save retains a transaction and an undo command.\n'
        'Environment references remain literal; sensitive values are redacted.\n'
        'Shared defaults support colors, icons, formatting and apps; overrides are optional.\n'
        'File actions use the existing workflow for the active profile only.\n'
        'Visual saves refresh affected active consumers; the selected theme is preserved.\n'
        'Refresh retries activation or applies direct visual-file edits.')


def display(key, value):
    if key.startswith('environment.') and value is not None:
        name = key[len('environment.'):]
        value = public_report({'environment': {name: value}})['environment'][name]
    if value is None: return 'null'
    if value == '': return '(empty)'
    if type(value) is bool: return 'true' if value else 'false'
    return clean(json.dumps(value,ensure_ascii=False) if isinstance(value,(dict,list)) else str(value))


@dataclass(frozen=True)
class Row:
    key: str
    value: object
    source: str
    destination: str
    description: str = ''
    local: bool = False
    kind: str = 'text'
    mapping: object = None
    explanation: object = None
    constraints: object = None

    @property
    def group(self): return self.key.split('.', 1)[0]


class Inventory:
    def __init__(self, root, scope, *, no_refresh=False):
        self.root, self.scope = Path(root), scope
        self.no_refresh = no_refresh
        self.defaults = scope == 'defaults'
        selected = profile_context(self.root, None if self.defaults else scope)
        paths = [self.root/'default'/file for file in ('icons.toml', 'colors.toml', 'config.json')]
        for layer in selected['layers']:
            paths += [Path(layer['root'])/file for file in ('profile.json', 'icons.toml', 'colors.toml')]
        self.guards = {str(path): digest(path) for path in paths}
        # Resolve again inside the guard interval, including inheritance.
        self.selected = profile_context(self.root, None if self.defaults else scope)
        self.styles = Styles(self.root, self.selected, defaults=self.defaults)
        from config_values import Controls,parts,lookup,MISSING,constraints
        self.controls=Controls(self.root,self.selected,defaults=self.defaults)
        self.rows = []
        destination=str(self.root/'default/config.json' if self.defaults else Path(self.selected['layers'][-1]['root'])/'profile.json')
        for key in self.controls.keys():
            if key in ('formatting','apps'):continue
            resolved=self.controls.resolve(key)
            self.rows.append(Row(key,resolved['value'],resolved['source'] or 'Not configured',destination,
                                 'Root usage logo gradient; next invocation, no theme refresh' if key=='apps.cli.logo_gradient' else
                                 'Popup appearance; reopen the popup to apply' if key.startswith('apps.menu.popup.') else
                                 'Fonts display; next invocation or reopened popup, no font activation' if key.startswith('apps.fonts.') else
                                 'Wiki display; next invocation or reopened popup, no theme refresh' if key.startswith(('apps.wiki.','formatting.apps.wiki.')) else
                                 'Literal application or formatting preference',resolved['source']==destination,'json',
                                 constraints=constraints(self.controls.defaults,key)))
        if not self.defaults and self.selected['current']==profile_context(self.root)['current'] and (self.root/'config/wttr/config.toml').is_file() and sys.version_info>=(3,11):
            from config_wttr import Native
            native=Native(self.root,self.selected,guarded=True);self.guards.update(native.guards)
            for key in native.keys():
                result=native.resolve(key)
                self.rows.append(Row(key,result['value'],str(native.original),str(native.original),
                                     'Native wttr TOML; next invocation, no profile inheritance',True,'native'))
        if not self.defaults and self.selected['current']==profile_context(self.root)['current'] and (self.root/'plugins/pkgs').is_dir():
            from config_pkgs import Native, constraints as pkgs_constraints
            native=Native(self.root,self.selected,guarded=True);self.guards.update(native.guards)
            for key in native.keys():
                result=native.resolve(key)
                self.rows.append(Row(key,result['value'],str(native.original),str(native.original),
                                     'Native pkgs JSON; next invocation, no profile inheritance',True,'pkgs',constraints=pkgs_constraints(key)))
        if not self.defaults:
            destination = str(Path(self.selected['layers'][-1]['root'])/'profile.json')
            leaf = self.selected['layers'][-1]
            self.rows.append(Row('profile.alias', leaf.get('alias'), destination if leaf.get('alias') else 'Canonical profile name only',
                                 destination, 'Additional variable prefix and map; does not replace the canonical name', 'alias' in leaf))
            definitions = schema()
            settings = {name: default for name, (_, default, _) in definitions.items()}
            settings['files.backup'] = False
            values = dict(settings=settings, environment={}, files={})
            sources = {('settings', key): 'Built-in default' for key in settings}
            for layer in self.selected['layers']:
                for group in values:
                    values[group].update(layer.get(group, {}))
                    sources.update({(group, key): str(Path(layer['root'])/'profile.json')
                                    for key in layer.get(group, {})})
            for group in ('settings', 'environment'):
                for key, value in values[group].items():
                    kind, _, description = definitions.get(key, ('text', None, 'Literal environment declaration'))
                    if key == 'files.backup': kind, description = 'boolean', 'Back up occupied managed file destinations'
                    source = sources[group, key]
                    self.rows.append(Row(group+'.'+key, value, source, destination, description,
                                         source == destination, kind))
            for owner, mappings in values['files'].items():
                for item in mappings:
                    identity = owner+':'+item['id']
                    source = sources['files', owner]
                    self.rows.append(Row('files.'+identity, item['source'], source, destination,
                                         'Managed file mapping · '+identity, source == destination,
                                         'mapping', dict(item, owner=owner)))
        from config_refresh import explain, active, read_json
        from files.file_platform import state_root
        try:
            generation = active(state_root())
            published = read_json(generation/'preferences.json') if generation else {}
        except (OSError, ValueError): published = {}
        active_profile = profile_context(self.root)['current']
        from style_catalog import known_keys
        for group in self.styles.values:
            destination = str(self.styles.path(group))
            for key in sorted(known_keys(group,self.styles)):
                resolved=self.styles.resolve(group,key)
                value,source=resolved['value'],resolved['source'] or 'Not configured'
                kind = 'boolean' if group == 'colors' and key.rsplit('.', 1)[-1] in ATTRS else 'color' if group == 'colors' else 'text'
                self.rows.append(Row(group+'.'+key, value, source, destination,
                                     'Visual preference · '+group, source == destination, kind, explanation=explain(group+'.'+key, _style=self.styles, _published=published, _active=active_profile, defaults=self.defaults)['consumers']))
        self.rows.sort(key=lambda row: (CATEGORIES.index(row.group), row.key))
        self.check()

    def check(self):
        if any(digest(Path(path)) != before for path, before in self.guards.items()):
            raise ValueError('Configuration changed; reopen the row and review again')

    def find(self, key):
        return next((row for row in self.rows if row.key == key), None)

    def app_row(self, row, app):
        name = re.sub(r'^apps\.[^.]+\.', '', row.key.split('.', 1)[1])
        key = row.group+'.apps.'+app+'.'+name
        existing = self.find(key)
        if existing: return existing
        base = self.find(row.group+'.'+name)
        return replace(base or row, key=key, local=False)


class Draft:
    """Keep one guarded baseline across input, validation and review."""
    def __init__(self, inventory, row):
        inventory.check()
        self.inventory, self.row = inventory, row
        self.base = (StylePlan(inventory.root, inventory.selected, row.group, inventory.defaults)
                     if row.group in ('colors', 'icons') else ControlPlan(inventory.root,inventory.selected,inventory.defaults)
                     if row.group in ('formatting','apps') else Plan(inventory.root, inventory.selected))
        if row.kind=='native':
            from config_wttr import NativePlan
            self.base=NativePlan(inventory.root,inventory.selected)
        elif row.kind=='pkgs':
            from config_pkgs import NativePlan
            self.base=NativePlan(inventory.root,inventory.selected)
        inventory.check()
        self.base.guards.update(inventory.guards)

    def prepare(self, value=None, reset=False):
        plan = copy.deepcopy(self.base)
        name = self.row.key.split('.', 1)[1]
        if isinstance(plan, StylePlan):
            plan.edit(name, value, unset=reset)
            styles = Styles(self.inventory.root, self.inventory.selected, defaults=self.inventory.defaults,
                            replacements={plan.path: plan.data})
            proposed = styles.resolve(self.row.group, name, 'cli')['value']
        elif self.row.kind=='native':
            from config_values import lookup,parts
            from wttr.configuration import validate
            plan.edit(self.row.key,value,unset=reset)
            proposed=lookup(validate(copy.deepcopy(plan.data)),parts(self.row.key)[2:])
        elif self.row.kind=='pkgs':
            from config_values import lookup,parts
            plan.edit(self.row.key,value,unset=reset)
            proposed=lookup(plan.effective,parts(self.row.key)[2:])
        elif isinstance(plan,ControlPlan):
            from config_values import Controls,lookup,parts
            plan.edit(self.row.key,value,unset=reset)
            proposed=(lookup(plan.data,parts(self.row.key)) if self.inventory.defaults else
                      Controls(self.inventory.root,self.inventory.selected,replacements={plan.path:plan.data}).resolve(self.row.key)['value'])
        else:
            plan.edit(self.row.key, value, unset=reset)
            plan.finish()
            values = {}
            if self.row.group == 'settings':
                values.update({key: default for key, (_, default, _) in schema().items()})
                values['files.backup'] = False
            for layer in self.inventory.selected['layers'][:-1]: values.update(layer.get(self.row.group, {}))
            values.update(plan.data.get(self.row.group, {}))
            proposed = plan.data.get('alias') if self.row.group == 'profile' else values.get(name)
        self.plan, self.proposed, self.reset = plan, proposed, reset
        return self

    def review(self):
        from config_refresh import preview_save
        visual = isinstance(self.plan, (StylePlan,ControlPlan))
        effect = preview_save(self.inventory.root, self.plan) if visual and not self.inventory.no_refresh else None
        return page('Reset override' if self.reset else 'Save configuration', [
            ('Key', self.row.key), ('Saved', display(self.row.key, self.row.value)),
            ('After reset' if self.reset else 'Proposed', display(self.row.key, self.proposed)),
            ('Destination', str(self.plan.path)),
            ('Effect', ('Remove this profile override' if self.reset else 'Save this value') +
             ('; automatic refresh disabled' if visual and self.inventory.no_refresh else
              '; next Fonts invocation or popup' if self.row.key.startswith('apps.fonts.') else
              '; next popup' if self.row.key.startswith('apps.menu.popup.') else '; refresh: '+(', '.join(effect['consumers']) or 'no active change') if effect else '')),
            ('Recovery', 'Retained transaction; undo command shown after saving')])

    def save(self):
        self.inventory.check()
        from config_refresh import effective, after_save
        before = effective(self.inventory.root) if isinstance(self.plan, (StylePlan,ControlPlan)) and not self.inventory.no_refresh else None
        result = self.plan.apply('unset' if self.reset else 'set')
        current.cache_clear()
        from config_values import current as controls_current
        controls_current.cache_clear()
        if before is not None: result['refresh'] = after_save(self.inventory.root, before)
        return result


def page(title, details, *, width=80, ui=None):
    stream = io.StringIO()
    out = Presentation(stream, terminal=True)
    out.width = max(1, width)
    if ui: out.color, out.icons = ui.color, ui.icons
    from config_values import value
    out.formatting=value('formatting.apps.menu',{})
    out.detail_indent=out.formatting.get('indent',0)+out.formatting.get('padding',1)
    out.heading(title)
    for label, value in details:
        text = clean(str(value))
        if label in ('Source','Destination','Profile file','Edit destination') and Path(str(value)).is_absolute():
            out.resource_detail(label, value, display=text)
        else:
            out.detail(label, text)
    return stream.getvalue()


def details(row, *, width=80, ui=None):
    fields = [('Key', row.key), ('Saved', display(row.key, row.value)),
              ('Source', row.source), ('Destination', row.destination), ('Description', row.description)]
    from config_values import constraint_details
    fields += constraint_details(row.constraints or {})
    for binding in row.explanation or []:
        fields += [('Consumer', binding['app'] or 'none'), ('Effective', display(row.key, binding['value'])),
                   ('Winning source', binding['source'] or 'Not configured'), ('Refresh', binding['refresh'])]
    if row.group in ('settings','environment'):
        override = os.environ.get(row.key.split('.', 1)[1])
        if override is not None and (row.group == 'environment' or override):
            value = '[redacted]' if display(row.key,row.value) == '[redacted]' else display(row.key,override)
            fields.append(('Environment override', value+' (not saved)'))
    if row.mapping:
        fields = [('Key', row.key), ('Profile file', row.source), ('Edit destination', row.destination)]
        fields += [(key.title(), row.mapping[key]) for key in ('owner', 'source', 'target', 'targets', 'strategy', 'platforms', 'replaces')
                   if key in row.mapping]
    return page('Config · '+row.key, fields, width=width, ui=ui)


def preview_transport(path):
    command = ('& $env:DOTS_CONFIG_PYTHON -B $env:DOTS_CONFIG_MENU preview $env:DOTS_CONFIG_PREVIEW {1}'
               if os.name == 'nt' else '"$DOTS_CONFIG_PYTHON" -B "$DOTS_CONFIG_MENU" preview "$DOTS_CONFIG_PREVIEW" {1}')
    return command, '', dict(DOTS_CONFIG_PYTHON=sys.executable, DOTS_CONFIG_MENU=str(Path(__file__).resolve()),
                            DOTS_CONFIG_PREVIEW=str(path))


def select(title, items, context=None, review=None):
    with request_file(dict(schema=1, previews=[review]*len(items))) if review else nullcontext() as path:
        try:
            if review:
                from files.picker import fzf_colors
                from progress import permanent_output
                ui = Presentation(terminal=True)
                columns, lines = context.verify() if context else shutil.get_terminal_size((80,24))
                width, height = max(1, columns-2), max(1, lines-2)
                from menu_popup import dimensions, preferences
                width,height=dimensions(preferences(),(width,height),(columns,lines))
                header='Enter: choose  Esc: cancel\nAlt-P: preview  Alt-J/K: scroll'
                if height < 12: header='Enter: choose  Esc: cancel'
                if height < 9: header=''
                # Leave the complete action list above the preview, accounting
                # for the popup/preview frames, prompt and FZF separators.
                budget=height-len(header.splitlines())-len(items)-7
                with permanent_output(), context.selector_environment() if context else nullcontext(None) as environment:
                    result = RichSelector(backend='fzf').fzf('config·'+title.lower(), [label for _,label in items], False,
                        preview_transport(path), ui.color, ui.icons, picker_colors(fzf_colors(ui)),
                        popup=f'center,{width},{height}' if context else False, height=height,
                        preview_position='down', preview_lines=max(1,budget), preview_wrap=True,
                        popup_resolved=context is not None, info='inline-right',
                        bindings=('start:hide-preview',) if budget<1 else (),
                        environment=environment, navigation={}, header=header)
                return items[result[0]][0]
            selected = choose(Menu('config:'+title, title, tuple(Entry(key, label) for key, label in items)),
                              mode='browse', context=context, navigation={}, compact=not bool(review),
                              prompt='config·'+title.lower(), header='Enter: choose  Esc: back  Ctrl-C: cancel',
                              preview=preview_transport(path) if path else None)
            return selected.id if selected else None
        except SelectionEvent:
            return None


def show(text, *, title, context):
    return select(title, [('back','Back')], context, text)


def pick(inventory, category, frame, context):
    from files.picker import fzf_colors
    from progress import permanent_output
    ui = Presentation(terminal=True)
    columns, lines = context.verify() if context else shutil.get_terminal_size((80, 24))
    width, height = max(1, columns-2), max(1, lines-2)
    from config_values import value
    from row_layout import width as column_width,pad
    from menu_popup import dimensions as popup_dimensions,preferences
    width,height=popup_dimensions(preferences(),(width,height),(columns,lines))
    ui.width=max(1,width-6) if context else max(1,columns-6)
    formatting=value('formatting.apps.menu',{})
    indent=min(formatting.get('indent',0)+formatting.get('padding',1),max(0,ui.width-8))
    gap=min(formatting.get('label_gap',1),max(0,ui.width-indent-8))
    key_width=column_width(formatting.get('label_width',0),ui.width,indent=indent,gap=gap)
    rows = [row for row in inventory.rows if category == 'all' or row.group == category]
    styles = named_styles(ui)
    labels = []
    for row in rows:
        origin = 'local' if row.local else 'inherited' if row.source != 'Built-in default' else 'default'
        # Keep the complete searchable key in FZF, with bounded values and sources.
        key=pad(row.key,key_width,formatting.get('alignment','left'))
        prefix=(' '*indent+ui.paint(row.key,styles['blue'])+'\n'+' '*(indent+key_width+gap)
                if key_width and cells(row.key)>key_width else ' '*indent+ui.paint(key,styles['blue'])+' '*gap)
        labels.append(prefix+fit(display(row.key, row.value), max(8, ui.width//3))+
                      ui.paint(' · '+origin, styles['muted']))
    # Snapshot inert rows once; format only the selected preview. Rendering every
    # nullable icon/style binding here makes opening All grow with the vocabulary.
    snapshots = [asdict(replace(row, value=display(row.key, row.value)))
                 if row.group == 'environment' else asdict(row) for row in rows]
    notice = '\n'.join(textwrap.wrap(clean(frame.get('notice', '')), max(1,width-4)))
    if not rows: notice = 'No options in this category'+('\n'+notice if notice else '')
    mode = frame.get('mode', 'set')
    navigation = {'esc':'back', 'f1':'help', 'alt-g':'category', 'alt-s':'scope'}
    if mode == 'set': navigation['alt-n'] = 'new'
    with request_file(dict(schema=1, rows=snapshots, width=max(1,width-4),
                           color=ui.color, icons=ui.icons)) as path:
        with permanent_output(), context.selector_environment() if context else nullcontext(None) as environment:
            try:
                result = RichSelector(backend='fzf').fzf('config·'+mode+'·'+inventory.scope+'·'+category, labels, False,
                    preview_transport(path), ui.color, ui.icons, picker_colors(fzf_colors(ui)),
                    popup=f'center,{width},{height}' if context else False, height=height,
                    preview_position='down', preview_lines=max(3, min(8, lines//3)), preview_wrap=True,
                    query=frame.get('query', ''), environment=environment, info='inline-right', hscroll=False, wrap=True,
                    header=('Enter: actions' if mode == 'set' else 'Enter: details')+'  Alt-G: category\nAlt-S: scope  '+('Alt-N: env  ' if mode == 'set' else '')+'F1: help'+
                        ('\n'+notice if notice else ''),
                    navigation=frame, navigation_keys=navigation, event_selection=True,
                    focus_index=next((i for i, row in enumerate(rows) if row.key == frame.get('selected')), None))
            except SelectionEvent as event:
                if event.index is not None: frame['selected'] = rows[event.index].key
                raise
    frame['selected'] = rows[result[0]].key
    return rows[result[0]]


def input_value(row, initial, context):
    spec = row.constraints or {}
    offered = [*spec.get('choices', []), *spec.get('examples', [])]
    if offered:
        items = [(json.dumps(value), display(row.key,value)) for value in offered]
        if spec.get('syntax'): items.append(('__custom__', 'Custom value…'))
        value = select(row.key, items, context)
        if value != '__custom__': return value
        return prompt(initial, 'Edit '+row.key, context, back=True)
    choices = {'bool': [('1','Enabled (1)'), ('0','Disabled (0)')],
               'boolean': [('true','true'), ('false','false')],
               'style': [(value,value) for value in ('auto','always','never')],
               'suggestions': [(value,value) for value in ('deja','autosuggestions','none')]}
    if row.kind in choices:
        return select(row.key, choices[row.kind], context)
    if row.kind == 'color':
        roles = set(ANSI)|set(ALIASES)|{'default','reset'}
        prefs = current()
        palette = prefs.palette if prefs and isinstance(prefs.palette,dict) else {}
        entries = [(name,color,name) for name,color in palette.items()]
        # The published palette also retains native names such as rosewater;
        # they need not be semantic roles accepted by the style validator.
        from config_refresh import read_json
        from files.file_platform import state_root
        try: published = read_json(state_root()/'current/theme/palette.json')
        except (OSError,ValueError): published = {}
        if isinstance(published,dict):
            for section,label in (('roles','role'),('palette','native')):
                colors=published.get(section,{})
                if not isinstance(colors,dict): continue
                for name,color in colors.items():
                    if palette.get(name)==color: continue
                    title=name+' ('+label+')' if name in palette else name
                    entries.append((title,color,None))
        items, values, named = [('custom','Custom color…')], {}, set()
        for name, color, role in sorted(entries,key=lambda entry:entry[0]):
            if not isinstance(color,str) or not re.fullmatch('#[a-fA-F0-9]{6}',color): continue
            token = 'palette:'+str(len(values))
            items.append((token,clean(name)+' · '+color))
            values[token] = role if role in roles else color
            if role is not None: named.add(role)
        items.extend((name,name) for name in sorted(roles-named))
        value = select('Color', items, context)
        if value != 'custom': return values.get(value,value)
    return prompt(initial, 'Edit '+row.key, context, back=True)


def edit(inventory, row, context, *, reset=False):
    draft = Draft(inventory, row)
    # Never send a hidden legacy literal to a text editor or preview transport.
    initial = json.dumps(row.value,ensure_ascii=False) if row.kind in ('json','native','pkgs') else str(row.value) if row.value is not None else ''
    if display(row.key, row.value) == '[redacted]': initial = ''
    while True:
        try:
            if display(row.key, initial) == '[redacted]': initial = ''
            value = None if reset else input_value(row, initial, context)
            if not reset and value is None: return ''
            initial = value
            draft.prepare(value, reset)
        except SelectionEvent:
            return ''
        except ValueError as error:
            inventory.check()
            show(page('Invalid value', [('Reason', str(error)), ('Action', 'Edit again or Escape to cancel')]),
                      title='config·invalid', context=context)
            if reset: return ''
            continue
        if select('Review change', [('cancel','Cancel'), ('save','Save')], context, draft.review()) != 'save': return ''
        result = draft.save()
        notice = ('Saved · undo: dots files undo '+result['id']) if result.get('id') else 'Unchanged'
        if result.get('refresh'): notice += ' · visuals: '+result['refresh']['status']
        return notice


def file_action(root, scope, row, action, context, new_id=None):
    active = profile_context(root)
    if not active['layers'] or scope != active['layers'][-1]['id']:
        raise ValueError('File workflows are available only for the active profile')
    routes = {'mapping': ('files','edit',row.key[len('files.'):]), 'browse': ('files','browse'),
              'rename': ('files','edit',row.key[len('files.'):], '--id', new_id)}
    return run_action(dots_argv(routes[action], root=root), kind='terminal', context=context, title='Config files')


def actions(inventory, row, context):
    while True:
        items = [('details','Details')]
        if row.mapping:
            active = profile_context(inventory.root)
            if active['layers'] and inventory.scope == active['layers'][-1]['id']:
                items += [('mapping','Edit mapping with dots files'), ('rename','Rename ID'), ('browse','Browse managed files')]
        else:
            from style_catalog import supported
            if row.group not in ('icons','colors') or supported(row.group, row.key.split('.',1)[1]):
                items.insert(0, ('edit','Edit value'))
            if row.local and not inventory.defaults: items.insert(1, ('reset','Reset override'))
            if row.group in ('icons','colors'): items.append(('app','Application override'))
        action = select(row.key, items, context)
        if action is None: return ''
        if action == 'details':
            show(details(row), title='Details', context=context)
        elif action in ('mapping','browse','rename'):
            new_id = None
            if action == 'rename':
                try: new_id = prompt(row.mapping['id'], 'New file ID', context, back=True)
                except SelectionEvent: continue
                if new_id is None: continue
                inventory.check()
            code = file_action(inventory.root, inventory.scope, row, action, context, new_id)
            return 'File workflow finished'+(' · status '+str(code) if code else '')
        elif action == 'app':
            app = select('Application', [(name,name) for name in APPS if __import__('style_catalog').supported(row.group, 'apps.'+name+'.'+re.sub(r'^apps\.[^.]+\.', '', row.key.split('.',1)[1]))], context)
            if app: return actions(inventory, inventory.app_row(row, app), context)
        else:
            return edit(inventory, row, context, reset=action == 'reset')


def browser_available(context):
    if not rich_fzf_available(): return False
    if context:
        result = subprocess.run(['fzf','--help'], capture_output=True, timeout=5)
        return result.returncode == 0 and b'--popup' in result.stdout
    return True


def browse(root, selected, args):
    try:
        return _browse(root, selected, args)
    except SelectionEnded as ended:
        return ended.status
    except (KeyboardInterrupt, EOFError):
        return 130


def _browse(root, selected, args):
    # Called only after JSON/help/noninteractive dispatch has been resolved.
    context = (TmuxContext.capture(client=args.client) if args.client else
               TmuxContext.from_environment() if os.environ.get('TMUX') or os.environ.get('DOTS_MENU_CONTEXT') else None)
    if not terminal() and context is None: raise ValueError('config browsing requires a terminal')
    if not browser_available(context):
        if args.action == 'set' and getattr(args,'key',None) is not None:
            raise ValueError('interactive config editing requires FZF/popup support; supply an explicit value')
        from config_cli import main
        ui = Presentation(sys.stderr)
        ui.detail('Config', 'FZF or popup support unavailable; listing configuration')
        return main(['list', *(['--defaults'] if args.defaults else ['--profile', selected['layers'][-1]['id']])])
    scope = 'defaults' if args.defaults else selected['layers'][-1]['id']
    no_refresh = getattr(args,'no_refresh',False)
    if args.action == 'set' and getattr(args,'key',None) is not None:
        inventory = Inventory(root,scope,no_refresh=no_refresh)
        key = 'settings.'+args.key if args.key.startswith('DOTS_') else args.key
        row = inventory.find(key)
        if row is None and not inventory.defaults and re.fullmatch(r'environment\.[A-Z][A-Z0-9_]*',key):
            row = Row(key,None,'Not set',str(Path(selected['layers'][-1]['root'])/'profile.json'),'Literal environment declaration')
        if row is None: raise ValueError('unknown or noneditable configuration key: '+args.key)
        if row.mapping: return file_action(root,scope,row,'mapping',context)
        if row.group in ('icons','colors'):
            from style_catalog import supported
            if not supported(row.group,key.split('.',1)[1]): raise ValueError('unsupported visual consumer or field: '+key)
        notice = edit(inventory,row,context)
        if notice:
            ui=Presentation();ui.heading('Dots config');ui.detail('Result',notice)
        return 0
    mode = args.action if args.action in ('get','set') else None
    category, frames = None, {}
    while True:
        if mode is None:
            mode = select('Config', [('list','List'), ('get','Get'), ('set','Set'), ('refresh','Refresh active visuals')], context)
            if mode is None: return 0
            if mode == 'refresh':
                from config_refresh import refresh
                review = page('Refresh active visuals', [('Effect', 'Publish current visual preferences and notify verified consumers'), ('Theme', 'Preserve current palette and identity')])
                if select('Review refresh', [('cancel','Cancel'),('apply','Refresh')], context, review) == 'apply':
                    result = refresh(root)
                    show(page('Visual refresh', [('Result', result['status']), ('Retry', 'dots config refresh')]), title='Refresh', context=context)
                mode = None
                continue
            category = 'all' if mode == 'list' else None
        if category is None:
            categories = ('all','icons','colors','formatting','apps') if scope == 'defaults' else CATEGORIES
            category = select('Category', [(name,name.title()) for name in categories], context)
            if category is None:
                mode = None
                continue
        frame = frames.setdefault((mode, scope, category), dict(query=args.query or '', mode=mode))
        try:
            inventory = Inventory(root, scope, no_refresh=no_refresh)
            try:
                row = pick(inventory, category, frame, context)
                # Refresh before opening actions; review always uses a guarded snapshot.
                inventory = Inventory(root, scope, no_refresh=no_refresh)
                row = inventory.find(row.key)
                if row and mode == 'set': frame['notice'] = actions(inventory, row, context)
                elif row: show(details(row), title='Details', context=context)
                else: frame['notice'] = 'Option changed; list refreshed'
            except SelectionEvent as event:
                if event.action == 'back':
                    if mode == 'list': mode = None
                    category = None
                if event.action == 'help': show(HELP, title='Help', context=context)
                elif event.action == 'category':
                    categories = ('all','icons','colors','formatting','apps') if scope == 'defaults' else CATEGORIES
                    category = select('Category', [(name,name.title()) for name in categories], context) or category
                elif event.action == 'scope':
                    choices = [(item['id'],item['id']) for item in available(root)] + [('defaults','Shared defaults')]
                    scope = select('Scope', choices, context) or scope
                    if scope == 'defaults' and category not in ('all','colors','icons','formatting','apps'): category = 'all'
                elif event.action == 'new' and mode == 'set':
                    if inventory.defaults:
                        frame['notice'] = 'Select a profile to add an environment declaration'
                        continue
                    try:
                        name = prompt('', 'Environment name (UPPER_CASE)', context, back=True)
                    except SelectionEvent:
                        continue
                    if not re.fullmatch('[A-Z][A-Z0-9_]*', name): raise ValueError('Use an uppercase environment variable name')
                    row = inventory.find('environment.'+name) or Row('environment.'+name, None, 'Not set',
                        str(Path(inventory.selected['layers'][-1]['root'])/'profile.json'), 'Literal environment declaration')
                    frame['notice'] = edit(inventory, row, context)
                    frame['selected'] = row.key
        except (ValueError, OSError) as error:
            review = page('Config', [('Error', str(error)), ('Action', 'Reload and review again, or Escape to close')])
            if select('Error', [('reload','Reload')], context, review) is None: return 0
            frame['notice'] = 'Configuration reloaded; review again before saving'
        except SelectionEnded as ended:
            return ended.status
        except (KeyboardInterrupt, EOFError):
            return 130


def preview(path, token):
    data = read_request(Path(path))
    if not token.isdecimal(): raise ValueError('invalid preview selection')
    index = int(token)
    rows = data.get('rows', data.get('previews', []))
    if not 0 <= index < len(rows): raise ValueError('invalid preview selection')
    if 'rows' in data:
        ui = Presentation(terminal=True)
        ui.color, ui.icons = data['color'], data['icons']
        print(details(Row(**rows[index]), width=data['width'], ui=ui), end='')
    else:
        print(rows[index], end='')


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == 'preview': preview(sys.argv[2], sys.argv[3])
    else: raise SystemExit(2)

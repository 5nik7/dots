"""Guarded layout migration and portable appearance transfer."""
import copy
import json
from pathlib import Path
from preference_files import (PreferencePlan, GROUPS, FILES, appearance_file,
    combined, overlay, partition, encode_style, controls)
from config_values import leaves, name, parts, assign
from config_keys import canonical
from profile_config import context
from style_config import Styles, read as read_styles, encode as encode_styles, validate as validate_styles
from files.transactions import digest, parents_safe, Store
from files.file_platform import state_root


DISPLAY_KEYS = {
    'apps.cli.logo_gradient',
    'apps.fonts.list_details', 'apps.fonts.provenance', 'apps.fonts.menu_descriptions',
    'apps.fonts.preview.enabled', 'apps.fonts.preview.sample',
    'apps.wiki.list_details', 'apps.wiki.search_snippets', 'apps.wiki.search_urls',
    'apps.wiki.menu_descriptions', 'apps.wiki.section_breadcrumbs', 'apps.wiki.reader',
    'apps.tmux.clock.icon_mode', 'apps.tmux.battery.charging_style',
    'apps.tmux.session.name_source', 'apps.tmux.session.show_number', 'apps.tmux.session.show_name',
    'apps.tmux.session.repository_icon', 'apps.tmux.session.repository_color', 'apps.tmux.session.multiple',
}


def portable(key):
    """Explicit portable display fields; exclude behavior, paths and native files."""
    key = canonical(key)
    return (appearance_file(key) != 'config.json' or key.startswith('formatting.') or
            key in DISPLAY_KEYS or key.startswith('apps.tmux.indicators.') and key.endswith('.text'))


class TransferPlan:
    def __init__(self, root, selected, *, source=None, all_profiles=False, defaults=False, promote=False):
        from profiles import available
        from config_values import Controls
        from profile_config import settings
        self.root = Path(root); self.selected = selected
        self.guards = {}; self.operations = []; self.items = []; self.plans = {}; self.styles = {}
        self.path = self.root/'default' if defaults else Path(selected['layers'][-1]['root'])
        def guard_values(values):
            for path,value in values.items():
                if path in self.guards and self.guards[path]!=value:raise ValueError('configuration changed during preview: '+path)
                self.guards[path]=value
        def scope_plan(scope, shared=False):
            directory = self.root/'default' if shared else Path(scope['layers'][-1]['root'])
            if directory not in self.plans:
                plan = PreferencePlan(root, scope, shared)
                self.plans[directory] = plan
                guard_values(plan.guards)
            return self.plans[directory]
        if source is None:
            identities = [r['id'] for r in available(root)] if all_profiles else [selected['current']]
            if all_profiles: scope_plan(selected,True)
            for identity in identities: scope_plan(context(root,identity))
        else:
            target = scope_plan(selected,defaults)
            source_scope = context(root,source) if source != 'defaults' else selected
            Controls(root,source_scope,defaults=source=='defaults')  # Validate source consumers before transfer.
            Styles(root,source_scope,defaults=source=='defaults')
            directories = [(self.root/'default',None)] if source == 'defaults' else [(Path(layer['root']),layer) for layer in source_scope['layers']]
            if target.directory == directories[-1][0]: raise ValueError('import source and destination must differ')
            values = {}; appearances = {'colors':{},'icons':{}}
            for directory, legacy in directories:
                for filename in (*FILES,'profile.json'):
                    path=directory/filename;parents_safe(path);guard_values({str(path):digest(path)})
                values=overlay(values,combined(directory,legacy))
                for group in appearances:
                    appearances[group].update(read_styles(directory/(group+'.toml')))
            for path,value in leaves(values):
                if not path or value is None or value == {}: continue
                key=name(path)
                if portable(key):
                    from preference_files import put
                    put(target.data,key,value)
                    self.items.append(dict(action='import',key=canonical(key)))
            for group, values in appearances.items():
                path=target.directory/(group+'.toml')
                updated={canonical(group+'.'+k).partition('.')[2]:v for k,v in read_styles(path).items()}
                updated.update({canonical(group+'.'+k).partition('.')[2]:v for k,v in values.items()})
                validate_styles(group,updated)
                self.styles[path]=updated
                self.items += [dict(action='import',key=canonical(group+'.'+k)) for k in values]
            if promote:
                if source=='defaults':raise ValueError('cannot remove shared declarations')
                leaf=scope_plan(source_scope)
                for path,value in list(leaves(leaf.data)):
                    if path and portable(name(path)):assign(leaf.data,path,None,unset=True)
                for group in appearances:self.styles[leaf.directory/(group+'.toml')]={}
        replacements={}
        for directory,plan in self.plans.items():
            plan.finish();guard_values(plan.guards);replacements.update(plan.replacements)
            self.operations.extend(plan.operations)
            if source is None:self.items += [dict(action='separate-preferences',path=op['path']) for op in plan.operations]
        for path, values in self.styles.items():
            plan=self.plans[path.parent]
            content=encode_style(path,partition(plan.data)[path.name],encode_styles(values))
            self.operations=[op for op in self.operations if op['path']!=str(path)]
            before=path.read_text(encoding='utf-8-sig') if path.exists() else ''
            if content != before:
                self.operations.append(dict(path=str(path),text=content))
        for plan in self.plans.values():
            effective=Controls(root,plan.selected,defaults=plan.defaults,replacements=replacements)
            from config_values import validate_effective
            style=Styles(root,plan.selected,defaults=plan.defaults,replacements=self.styles)
            validate_effective(effective.values,effective.defaults,style,plan.selected['facts']['platform'])
            settings(root,plan.selected,defaults=plan.defaults,replacements=replacements)
        if source is None:
            for identity in identities:
                scope=context(root,identity)
                if Controls(root,scope).values != Controls(root,scope,replacements=replacements).values:
                    raise ValueError('layout migration changes effective preferences: '+identity)
                old={k:v['value'] for k,v in settings(root,scope).items()}
                new={k:v['value'] for k,v in settings(root,scope,replacements=replacements).items()}
                if old!=new:raise ValueError('layout migration changes shell settings: '+identity)
        for path,value in self.guards.items():
            if digest(Path(path))!=value:raise ValueError('configuration changed during preview: '+path)
        self.replacements=replacements

    def apply(self, action='import'):
        return Store(state_root()).apply('config-'+action,self.operations,self.guards,retain=True,
                                         catalogs=[Path(p) for p in self.guards])


def review(plan, context=None):
    from config_menu import page, select
    rows=[('Destination',str(plan.path)),('Effect','Merge portable appearance; imported values win')]
    rows += [('Change',item.get('key',item.get('path',''))) for item in plan.items]
    rows += [('Files',str(len(plan.operations))),('Activation','Next reads; no theme publication or application reload')]
    return select('Review appearance import',[('cancel','Cancel'),('save','Save')],context,page('Appearance import',rows))=='save'


def run(root,selected,args):
    from config_cli import render
    importing=args.action=='import'
    if importing and not args.key:raise ValueError('import requires a source profile')
    plan=TransferPlan(root,selected,source=args.key if importing else None,
                      all_profiles=args.all_profiles,defaults=not args.profile if importing else False)
    result=dict(schema=1,profile='defaults' if importing and not args.profile else selected['current'],
                path=str(plan.path),status='preview',items=plan.items)
    apply=args.apply and args.yes and not args.dry_run
    from interaction import terminal
    if importing and not (args.apply or args.json or args.dry_run) and terminal():
        from interaction import SelectionEnded
        try:apply=review(plan)
        except SelectionEnded as ended:return ended.status
    if apply:
        saved=plan.apply('import' if importing else 'migrate-layout')
        result.update(status=saved['status'],transaction=saved.get('id'))
    print(json.dumps(result)) if args.json else render(result)
    return 0

"""Inspect and edit checkout-local profile configuration."""
import argparse
import copy
import json
import os
from pathlib import Path
import re
import stat
import sys

LIB = Path(__file__).resolve().parent
sys.path.insert(0, str(LIB / 'files'))
from profile_config import checkout, context, directory, legacy_directory, read_env, schema
from profiles import definition, public_report, SENSITIVE
from catalog import Catalog, Presentation, read_json
from transactions import Store, digest, parents_safe, exists
from file_platform import state_root
from style_config import Styles, read as read_styles, encode as encode_styles, nested, flatten, validate as validate_styles


def validate(root, selected, data):
    layer = selected['layers'][-1]
    definition(root, layer['id'], data)
    from profile_environment import Model
    Model(root, selected, {layer['id']: data})
    candidate = copy.deepcopy(selected)
    candidate['layers'][-1] = dict(data, root=layer['root'])
    catalog = Catalog(root, candidate['facts']['platform'], profile=candidate)
    owners = {row['id'] for row in catalog.sources if row['status'] != 'excluded'}
    if set(data.get('files', {})) - owners:
        raise ValueError('profile files refers to an unknown or excluded repository')
    rows = catalog.records()
    if any(row['applicable'] and row['status'] == 'conflict' for row in rows):
        raise ValueError('profile file mappings contain conflicting destinations')
    return catalog


def key_parts(key):
    if key.startswith('DOTS_'): return 'settings', key
    group, dot, name = key.partition('.')
    if not dot or group not in ('settings', 'environment', 'files', 'profile') or not name:
        raise ValueError('use a Dots setting name or settings.NAME, environment.NAME, files.REPOSITORY or profile.alias')
    if group == 'profile' and name != 'alias': raise ValueError('only profile.alias is editable')
    return group, name


def secret_check(path):
    parents_safe(path)
    mode = path.lstat().st_mode
    if stat.S_ISDIR(mode):
        for child in sorted(path.iterdir()): secret_check(child)
    elif stat.S_ISREG(mode):
        if path.stat().st_size > 4 * 1024 * 1024:
            raise ValueError('configuration exceeds migration size limit: ' + str(path))
        content = path.read_bytes()
        if (SENSITIVE.search(path.name) or re.search(rb'(?i)(BEGIN [A-Z ]*PRIVATE KEY|(?:password|api[_-]?key|access[_-]?token)\s*[=:]\s*["\']?[^\s"\']{4,})', content)):
            raise ValueError('possible credential material; migration refused: ' + str(path))
    else:
        raise ValueError('migration requires regular files and directories: ' + str(path))


class Plan:
    def __init__(self, root, selected):
        if not selected['layers']: raise ValueError('no profile definition in this checkout')
        self.root, self.selected = root, selected
        self.path = Path(selected['layers'][-1]['root']) / 'profile.json'
        self.guards, self.operations, self.items = {}, [], []
        self.guard(self.path)
        self.before = read_json(self.path)
        self.data = copy.deepcopy(self.before)
        catalog = Catalog(root, selected['facts']['platform'], profile=selected)
        from profiles import available
        self.catalogs = [*[Path(row['root'])/'profile.json' for row in available(root)], *catalog.lock_paths()]
        for path in [*catalog.input_paths(), *[Path(row['root'])/'profile.json' for row in available(root)]]: self.guard(path)

    def guard(self, path):
        parents_safe(path)
        self.guards[str(path)] = digest(path)

    def edit(self, key, value=None, unset=False, json_value=False):
        group, name = key_parts(key)
        if group == 'profile':
            if unset: self.data.pop(name, None)
            else:
                self.data[name] = json.loads(value) if json_value else value
            self.items.append(dict(action='unset' if unset else 'set', key=key))
            return
        if unset:
            self.data.get(group, {}).pop(name, None)
        else:
            if json_value:
                try: value = json.loads(value)
                except ValueError: raise ValueError('value must be valid JSON') from None
            elif group == 'settings' and name == 'files.backup':
                if value not in ('true', 'false'): raise ValueError('files.backup requires true or false')
                value = value == 'true'
            if group == 'environment' and (SENSITIVE.search(name) or any(SENSITIVE.search(n) for n in re.findall(r'\$\{([^}]+)\}', str(value)))):
                if not isinstance(value, str) or not re.fullmatch(r'\$\{[A-Z][A-Z0-9_]*\}', value):
                    raise ValueError('sensitive environment settings must reference an environment variable')
            self.data.setdefault(group, {})[name] = value
        self.items.append(dict(action='unset' if unset else 'set', key=key))

    def migrate(self):
        legacy = legacy_directory()
        parents_safe(legacy)
        if not exists(legacy): return
        if legacy.is_symlink() or not legacy.is_dir(): raise ValueError('legacy config must be a regular directory')
        # Only configuration is moved. Theme authoring and runtime stores remain local.
        retained = {'themes', 'state', 'cache', 'logs', 'transactions', 'backups'}
        for source in sorted(legacy.iterdir()):
            if source.name in retained: continue
            secret_check(source)
            self.guard(source)
            if source.name in ('config.env', 'files.json'):
                if not source.is_file(): raise ValueError('settings input must be a regular file')
                if source.name == 'config.env': values = read_env(source)
                else:
                    doc = read_json(source)
                    if set(doc) != {'schema', 'backup'} or type(doc['backup']) is not bool:
                        raise ValueError('invalid legacy file preferences')
                    values = {'files.backup': doc['backup']}
                for key, value in values.items():
                    prior = self.data.setdefault('settings', {}).get(key, value)
                    if prior != value: raise ValueError('profile setting conflicts with legacy configuration: ' + key)
                    self.data['settings'][key] = value
                target = self.path
            else:
                target = self.path.parent / source.name
                if source.name in ('profile.json', 'profile.lock', '.dots', '.git'):
                    raise ValueError('reserved profile destination: ' + source.name)
                self.guard(target)
                if exists(target):
                    if digest(target) != digest(source): raise ValueError('migration destination conflicts: ' + str(target))
                else:
                    self.operations.append(dict(path=str(target), source=str(source)))
            self.operations.append(dict(path=str(source), delete=True))
            self.items.append(dict(action='migrate', source=str(source), target=str(target)))

    def finish(self):
        validate(self.root, self.selected, self.data)
        if self.data != self.before: self.operations.insert(0, dict(path=str(self.path), data=self.data))
        state = state_root()
        for i, operation in enumerate(self.operations):
            path = Path(operation['path'])
            if path.is_relative_to(state) or state.is_relative_to(path): raise ValueError('configuration overlaps state store')
            for other in self.operations[i+1:]:
                right = Path(other['path'])
                if path.is_relative_to(right) or right.is_relative_to(path): raise ValueError('overlapping configuration operations')
        for path, before in self.guards.items():
            if digest(path) != before: raise ValueError('configuration changed during preview')

    def apply(self, action):
        return Store(state_root()).apply('config-' + action, self.operations, self.guards,
                                        retain=True, catalogs=self.catalogs)


class StylePlan:
    def __init__(self, root, selected, group, defaults=False):
        self.style = Styles(root, selected, defaults=defaults)
        self.group, self.defaults = group, defaults
        self.path = self.style.path(group)
        paths = [*self.style.paths, *[Path(row['root'])/'profile.json' for row in selected['layers']]]
        self.guards = {}
        for path in paths:
            parents_safe(path); self.guards[str(path)] = digest(path)
        self.before = read_styles(self.path)
        self.data = dict(self.before)
        self.items, self.operations = [], []

    def edit(self, name, value, unset=False, json_value=False):
        if not name: raise ValueError('select an individual style option')
        if json_value and not unset:
            try: value = json.loads(value)
            except ValueError: raise ValueError('value must be valid JSON') from None
            if value is None:
                from style_catalog import supported
                if not supported(self.group,name):raise ValueError('unknown configuration key: '+self.group+'.'+name)
                unset=True
        if unset:
            if self.defaults: raise ValueError('shared defaults must remain defined; use set')
            self.data = {key: val for key,val in self.data.items() if key != name and not key.startswith(name+'.')}
        else:
            if not json_value and self.group == 'colors' and name.rsplit('.',1)[-1] not in ('fg','bg') and value in ('true','false'):
                value = value == 'true'
            updates = flatten({name:value}) if isinstance(value,dict) else {name:value}
            validate_styles(self.group, updates)
            from style_catalog import supported
            if any(not supported(self.group, key) for key in updates):
                raise ValueError("unsupported visual consumer or field; use config explain for existing entries")
            known = self.style.values[self.group]
            for key in updates:
                base = re.sub(r'^apps\.[a-z][a-z0-9_]*\.', '', key)
                role, _, field = base.rpartition('.')
                recognized = base in known or self.group == 'colors' and any(k.startswith(role+'.') for k in known)
                if key not in known and not recognized and not supported(self.group, key):
                    raise ValueError('unknown style option: '+self.group+'.'+key)
            self.data.update(updates)
        Styles(self.style.root, self.style.selected, defaults=self.defaults, replacements={self.path:self.data})
        self.items.append(dict(action='unset' if unset else 'set', key=self.group+'.'+name))
        if self.data != self.before: self.operations=[dict(path=str(self.path),text=encode_styles(self.data))]

    def apply(self, action):
        return Store(state_root()).apply('config-'+action, self.operations, self.guards, retain=True, catalogs=[self.path])


class ControlPlan:
    def __init__(self,root,selected,defaults=False):
        from config_values import Controls
        self.controls=Controls(root,selected,defaults=defaults)
        self.root,self.selected,self.defaults=root,selected,defaults
        self.path=Path(root)/'default/config.json' if defaults else Path(selected['layers'][-1]['root'])/'profile.json'
        self.guards={}
        for path in self.controls.paths:
            parents_safe(path);self.guards[str(path)]=digest(path)
        self.before=read_json(self.path) if self.path.exists() else dict(schema=1,formatting={},apps={})
        self.data=copy.deepcopy(self.before);self.items=[];self.operations=[]

    def edit(self,key,value=None,unset=False,json_value=False):
        from config_values import parts,assign,validate_value,Controls
        path=parts(key)
        if not unset:
            if json_value:
                try:value=json.loads(value)
                except ValueError:raise ValueError('value must be valid JSON') from None
            elif isinstance(value,str):
                try:value=json.loads(value)
                except ValueError:pass
        validate_value(self.controls.defaults,path,None if unset else value)
        from config_values import lookup
        if self.defaults and (unset or value is None) and lookup(self.controls.defaults,path) is not None:
            raise ValueError('shared nonnullable defaults must remain defined; reset a profile override instead')
        assign(self.data,path,value,unset)
        if self.defaults:
            # Retain the declaration when a nullable default becomes unset.
            if unset or value is None:assign(self.data,path,None);node=self.data
            if unset or value is None:
                for part in path[:-1]:node=node.setdefault(part,{})
                node[path[-1]]=None
        else:validate(self.root,self.selected,self.data)
        from config_values import lookup
        proposed=self.data if self.defaults else Controls(self.root,self.selected,replacements={self.path:self.data}).values
        from tmux_config import validate_layout
        validate_layout(lookup(proposed,('formatting','apps','tmux'),{}),self.selected['facts']['platform'])
        self.items.append(dict(action='unset' if unset or value is None else 'set',key=key))
        self.operations=[dict(path=str(self.path),data=self.data)] if self.data!=self.before else []

    def apply(self,action):
        return Store(state_root()).apply('config-'+action,self.operations,self.guards,retain=True,catalogs=[self.path])


def style_value(styles,group,key):
    from style_catalog import supported, known_keys
    candidates=known_keys(group,styles)
    if key in candidates:
        return styles.resolve(group,key)['value']
    prefix=key+'.' if key else ''
    children={k[len(prefix):]:styles.resolve(group,k)['value'] for k in candidates if k.startswith(prefix)}
    if not children:raise ValueError('unknown configuration key: '+group+'.'+key)
    return nested(children)


def print_value(result,key,value,as_json=False):
    if as_json:print(json.dumps(dict(result,key=key,value=value),ensure_ascii=True))
    elif isinstance(value,(dict,list)):render(dict(result,key=key,value=value))
    elif value is None and sys.stdout.isatty():
        ui=Presentation();print(ui.paint('null','90'))
    else:print(value if isinstance(value,str) else json.dumps(value,ensure_ascii=True))


def render_value(ui, name, value, prefix=''):
    if isinstance(value, dict):
        if not value: ui.detail(name, 'No configured values'); return
        if name: ui.heading(name)
        for key,item in value.items(): render_value(ui,key,item,prefix+name+'.' if name else prefix)
    elif isinstance(value,list):
        if value and all(not isinstance(item,(dict,list)) for item in value):
            ui.detail_spans(name, [(', '.join(str(item) for item in value),None)]); return
        if not value: ui.detail(name, 'No entries'); return
        for index,item in enumerate(value):
            ui.emit()
            if isinstance(item,dict) and 'source' in item:
                owner = name if prefix.rstrip('.') == 'files' else name.rsplit('.',1)[-1]
                ui.heading(owner+':'+str(item.get('id',index+1)))
                for key in ('source','target'):
                    if item.get(key) is not None: ui.resource_detail(key.title(),item[key],display=item[key])
                for key in ('strategy','app','category','platforms','replaces','targets'):
                    if key in item: render_value(ui,key.title(),item[key])
                ui.detail('Enabled',item.get('enabled',True))
            elif isinstance(item,(dict,list)): render_value(ui,str(index+1),item)
            else: ui.detail(name,str(item))
    else:
        text = 'yes' if value is True else 'no' if value is False else 'not set' if value is None else str(value)
        ui.detail_spans(name,[(text,None)],label_width=None if ui.human else min(28,max(10,len(name))))


def render_refresh(ui, result):
    ui.detail('Visual refresh', result['status'])
    if result.get('reason'): ui.detail('Detail', result['reason'])
    if result.get('transaction'): ui.detail('Refresh undo', 'dots files undo '+result['transaction'])
    for row in result.get('consumers', []):
        if isinstance(row, str): ui.detail('Would refresh', row)
        else: ui.detail(row['app'], row['status']+(' · '+row['target'] if row.get('target') else ''))
    if result['status'] in ('failed','pending'): ui.detail('Retry', 'dots config refresh')


def render(result):
    ui = Presentation()
    ui.heading('Dots config')
    ui.detail('Profile', result['profile'], '94')
    ui.resource_detail('File', result['path'])
    if 'status' in result: ui.detail('Result', result['status'], '92' if result['status'] == 'complete' else '93')
    for row in result.get('items', []):
        ui.detail('Action', row['action'] + (' ' + row['key'] if 'key' in row else ''))
        for key in ('source', 'target'):
            if key in row: ui.resource_detail(key.title(), row[key])
    if 'refresh' in result: render_refresh(ui, result['refresh'])
    for group, entries in result.get('config', {}).items():
        if not entries: continue
        ui.emit(); ui.heading(group.title())
        for name, value in entries.items():
            if group == 'files': ui.detail(name,str(len(value))+' resources; dots config get files.'+name)
            else: render_value(ui,name,value,group+'.')
    if 'value' in result:
        ui.emit(); render_value(ui,result['key'],result['value'])
    if result.get('transaction'):
        ui.detail('Transaction', result['transaction'])
        ui.detail('Undo', 'dots files undo ' + result['transaction'])


class ConfigParser(argparse.ArgumentParser):
    def error(self, message):
        ui = Presentation(sys.stderr)
        ui.heading('Dots config')
        ui.detail_spans('Error', [(message, '91')])
        ui.detail('Help', 'dots help config')
        raise SystemExit(2)


def main(argv=None):
    parser = ConfigParser(description=__doc__)
    parser.add_argument('action', nargs='?', choices=['browse','list','get','set','unset','path','check','migrate','explain','refresh'])
    parser.add_argument('key', nargs='?')
    parser.add_argument('value', nargs='?')
    parser.add_argument('--profile')
    parser.add_argument('--app', choices=('cli','tmux','yazi','fzf','gum','starship','gitmux'))
    parser.add_argument('--no-refresh', action='store_true')
    parser.add_argument('--query', help='Initial browser search')
    parser.add_argument('--client', help='Initiating tmux client')
    parser.add_argument('--defaults', action='store_true', help='Inspect or edit shared visual, formatting and application defaults')
    for option in ('json','json-value','dry-run','apply','yes'):
        parser.add_argument('--'+option, action='store_true')
    args = parser.parse_args(argv)
    automatic = args.action is None
    args.action = args.action or 'list'
    guided = args.value is None and (args.action == 'set' or args.action == 'get' and args.key is None)
    if guided:
        from interaction import terminal
        guided = not (args.json or args.dry_run or args.json_value or args.apply or args.yes) and terminal() and os.environ.get('TERM') != 'dumb'
    if (args.query is not None or args.client) and not (automatic or args.action == 'browse'):
        parser.error('--query and --client require browse')
    if args.dry_run and args.action == 'browse': parser.error('--dry-run requires an explicit config edit')
    if args.action in ('get','set','unset','explain') and not args.key and not guided: parser.error('a key is required')
    if (args.value is not None) != (args.action == 'set') and not guided: parser.error('set requires a value; other actions take no value')
    if args.key and args.action not in ('get','set','unset','path','explain'): parser.error('unexpected key')
    if args.apply or args.yes:
        if args.action != 'migrate' or not args.apply or not args.yes: parser.error('migration apply requires --apply --yes')
    if args.json_value and args.action != 'set': parser.error('--json-value requires set')
    if args.app and args.action != 'explain': parser.error('--app requires explain')
    if args.no_refresh and args.action not in ('set','unset'): parser.error('--no-refresh requires set or unset')
    if args.action == 'refresh' and (args.profile or args.defaults): parser.error('refresh uses the active profile')
    if args.defaults and args.profile: parser.error('--defaults and --profile are mutually exclusive')
    if args.defaults and args.action == 'migrate': parser.error('migration requires a profile')
    root = checkout()
    selected = context(root, args.profile)
    if not selected['layers'] and not args.defaults: raise ValueError('no profile definition in this checkout')
    if guided and args.key is not None:
        from config_menu import browse
        return browse(root, selected, args)
    native_app = next((app for app in ('wttr','pkgs') if args.key == 'apps.'+app or (args.key or '').startswith('apps.'+app+'.')), None)
    native_key = native_app is not None
    if native_key:
        if args.defaults:raise ValueError(native_app+' uses its active native file; --defaults does not apply')
        if native_app == 'pkgs':
            from config_pkgs import Native,NativePlan
        else:
            from config_wttr import Native,NativePlan
        native=Native(root,selected)
        result=dict(schema=1,profile=selected['current'],path=str(native.original))
        if args.action in ('get','explain'):
            resolved=native.resolve(args.key) if args.key!='apps.'+native_app else dict(value=native.values,source=str(native.original))
            if args.action == 'explain' and native_app == 'pkgs':
                from config_pkgs import constraints
                result.update(constraints=constraints(args.key), activation='next invocation')
            print_value(dict(result,source=resolved['source']),args.key,resolved['value'],args.json)
            if args.action == 'explain' and native_app == 'pkgs' and not args.json:
                from config_values import constraint_details
                ui=Presentation()
                for label,value in constraint_details(result['constraints']): ui.detail(label,value)
                ui.detail('Source',str(native.original));ui.detail('Activation','next invocation')
        elif args.action=='path':print(json.dumps(result) if args.json else native.original)
        elif args.action in ('set','unset'):
            plan=NativePlan(root,selected);plan.edit(args.key,args.value,args.action=='unset',args.json_value)
            result.update(status='preview',items=plan.items)
            if not args.dry_run:
                applied=plan.apply(args.action);result.update(status=applied['status'],transaction=applied.get('id'))
                result['refresh']=dict(status='complete',reason=native_app+' reads this native file on its next invocation',consumers=[])
            if args.json:print(json.dumps(result))
            else:render(result)
        else:raise ValueError('unsupported native application configuration action')
        return 0
    if not args.json and not args.dry_run and (automatic or args.action == 'browse' or guided):
        from interaction import terminal
        if args.action == 'browse' or guided or terminal() and os.environ.get('TERM') != 'dumb':
            from config_menu import browse
            return browse(root, selected, args)
    if args.action == 'explain' and args.key.split('.',1)[0] in ('formatting','apps'):
        from config_values import Controls, constraints, constraint_details
        controls=Controls(root,selected,defaults=args.defaults)
        resolved=controls.resolve(args.key)
        result=dict(schema=1,key=args.key,profile='defaults' if args.defaults else selected['current'],
                    constraints=constraints(controls.defaults,args.key),**resolved)
        if args.key == 'apps.menu' or args.key.startswith('apps.menu.'):
            result['activation'] = 'next popup'
        if args.key == 'apps.fonts' or args.key.startswith('apps.fonts.'):
            result['activation'] = 'next Fonts invocation or popup'
        if args.key == 'apps.wiki' or args.key.startswith('apps.wiki.') or args.key.startswith('formatting.apps.wiki.'):
            result['activation'] = 'next Wiki invocation or popup'
        if args.key == 'apps.setup' or args.key.startswith('apps.setup.'):
            result['activation'] = 'next setup invocation'
        if args.key == 'apps.cli' or args.key.startswith('apps.cli.'):
            result['activation'] = 'next invocation'
        if args.key.startswith('formatting.apps.cli.'):
            result['activation'] = 'next invocation'
        if args.key.startswith('formatting.apps.menu.'):
            result['activation'] = 'next popup'
        if args.key.startswith('apps.fzf'):
            from fzf_config import picker_options
            _,ignored=picker_options(Controls(root,selected,defaults=args.defaults).values['apps'].get('fzf',{}))
            result['picker_ignored']=ignored
        if args.json:print(json.dumps(result,ensure_ascii=True))
        else:
            ui=Presentation();ui.heading('Effective configuration');render_value(ui,args.key,resolved['value'])
            ui.detail('Source',resolved['source'] or 'Not configured')
            for label, value in constraint_details(result['constraints']): ui.detail(label, value)
            if result.get('activation'):ui.detail('Activation',result['activation'])
            for ignored in result.get('picker_ignored',[]):ui.detail('Picker-owned',ignored)
        return 0
    if args.action == 'explain':
        from config_refresh import explain
        result = explain(args.key, root, selected, args.defaults, args.app)
        if args.json: print(json.dumps(result, ensure_ascii=True))
        else:
            ui = Presentation(); ui.heading('Effective configuration'); ui.detail('Key', args.key)
            for row in result['consumers']:
                ui.emit(); ui.detail('Consumer', row['app'] or 'none')
                render_value(ui, 'Effective', row['value']); ui.detail('Source', row['source'] or 'Not configured')
                ui.detail('Refresh', row['refresh'])
                for declaration in row['declarations']:
                    ui.detail('Declared', declaration['key']+' · '+declaration['source'])
        return 0
    if args.action == 'refresh':
        from config_refresh import refresh
        result = refresh(root, dry=args.dry_run)
        if args.json: print(json.dumps(result, ensure_ascii=True))
        else: render_refresh(Presentation(), result)
        return int(result['status']=='failed' or any(isinstance(row,dict) and row.get('status')=='failed' for row in result.get('consumers',[])))
    layer = selected['layers'][-1] if selected['layers'] else None
    path = root/'default' if args.defaults else Path(layer['root'])/'profile.json'
    result = dict(schema=1, profile='defaults' if args.defaults else layer['id'], path=str(path))
    group, _, style_key = (args.key or '').partition('.')
    is_style = group in ('icons','colors')
    is_control = group in ('formatting','apps')
    if args.defaults and args.action in ('get','set','unset') and not (is_style or is_control):
        parser.error('--defaults supports colors, icons, formatting and apps')
    if args.action == 'path':
        if args.key and args.key.split('.',1)[0] in ('formatting','apps'):
            path=root/'default/config.json' if args.defaults else path
        elif args.key:
            name = Path(args.key+'.toml' if args.key in ('icons','colors') else args.key)
            if not name.parts or name.is_absolute() or '..' in name.parts or any(ord(c)<32 for c in str(name)): raise ValueError('invalid configuration name')
            path = (root/'default' if args.defaults else legacy_directory() if name.parts[0] == 'themes' else path.parent) / name
        print(json.dumps(dict(result, path=str(path)))) if args.json else print(path)
        return 0
    if args.action in ('set','unset','migrate'):
        before = None
        if (is_style or is_control) and not args.no_refresh and not args.dry_run:
            from config_refresh import effective
            before = effective(root)
        if is_style:
            plan = StylePlan(root, selected, group, args.defaults)
            plan.edit(style_key, args.value, args.action == 'unset', args.json_value)
            result['path'] = str(plan.path)
        elif is_control:
            plan=ControlPlan(root,selected,args.defaults)
            plan.edit(args.key,args.value,args.action=='unset',args.json_value)
            result['path']=str(plan.path)
        else:
            plan = Plan(root, selected)
            if args.action == 'migrate': plan.migrate()
            else: plan.edit(args.key, args.value, args.action == 'unset', args.json_value)
            plan.finish()
        preview = args.dry_run or (args.action == 'migrate' and not args.apply)
        result.update(status='preview' if preview else 'unchanged', items=plan.items)
        if preview and (is_style or is_control) and not args.no_refresh:
            from config_refresh import preview_save
            result['refresh'] = preview_save(root, plan)
        if not preview:
            applied = plan.apply(args.action)
            result.update(status=applied['status'], transaction=applied.get('id'))
            if before is not None:
                from style_config import current
                from config_refresh import after_save
                current.cache_clear()
                from config_values import current as controls_current
                controls_current.cache_clear()
                result['refresh'] = after_save(root, before)
    else:
        styles = Styles(root, selected, defaults=args.defaults)
        from config_values import Controls
        controls=Controls(root,selected,defaults=args.defaults)
        if args.action == 'check':
            if not args.defaults: validate(root, selected, read_json(path))
            result['status'] = 'valid'
        else:
            merged = dict(settings={key:default for key,(_,default,_) in schema().items()},environment={},files={})
            merged['settings']['files.backup']=False
            for item in selected['layers'] if not args.defaults else []:
                for key in merged: merged[key].update(item.get(key, {}))
            if not args.defaults: merged['profile'] = dict(alias=layer.get('alias'))
            merged = public_report(merged)
            merged.update({key:nested(values) for key,values in styles.values.items()})
            merged.update(controls.values)
            if not args.defaults and selected['current']==context(root)['current'] and (root/'config/wttr/config.toml').is_file() and sys.version_info>=(3,11):
                from config_wttr import Native
                merged.setdefault('apps',{})['wttr']=Native(root,selected).values
            if not args.defaults and selected['current']==context(root)['current'] and (root/'plugins/pkgs').is_dir():
                from config_pkgs import Native
                merged.setdefault('apps',{})['pkgs']=Native(root,selected).values
            if args.action == 'get':
                if is_style:
                    value = style_value(styles,group,style_key)
                    result['path'] = str(styles.path(group))
                elif is_control:
                    value=controls.resolve(args.key)['value']
                else:
                    group, key = key_parts(args.key)
                    if key not in merged[group]: raise ValueError('key is not configured in this profile or its parents')
                    value = merged[group][key]
                print_value(result,args.key,value,args.json)
                return 0
            result['config'] = merged
    print(json.dumps(result, ensure_ascii=True)) if args.json else render(result)
    return int(result.get('refresh',{}).get('status') == 'failed' or any(isinstance(row,dict) and row.get('status')=='failed' for row in result.get('refresh',{}).get('consumers',[])))


if __name__ == '__main__':
    try: sys.exit(main())
    except (ValueError, OSError, KeyError, TypeError) as error:
        ui = Presentation(sys.stderr)
        ui.emit(ui.paint('dots config: ' + str(error), '91')); sys.exit(1)
    except KeyboardInterrupt: sys.exit(130)

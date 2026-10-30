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
        if unset:
            if self.defaults: raise ValueError('shared defaults must remain defined; use set')
            self.data = {key: val for key,val in self.data.items() if key != name and not key.startswith(name+'.')}
        else:
            if json_value:
                try: value = json.loads(value)
                except ValueError: raise ValueError('value must be valid JSON') from None
            elif self.group == 'colors' and name.rsplit('.',1)[-1] not in ('fg','bg') and value in ('true','false'):
                value = value == 'true'
            updates = flatten({name:value}) if isinstance(value,dict) else {name:value}
            validate_styles(self.group, updates)
            known = self.style.values[self.group]
            for key in updates:
                base = re.sub(r'^apps\.[a-z][a-z0-9_]*\.', '', key)
                role, _, field = base.rpartition('.')
                recognized = base in known or self.group == 'colors' and any(k.startswith(role+'.') for k in known)
                if key not in known and not recognized:
                    raise ValueError('unknown style option: '+self.group+'.'+key)
            self.data.update(updates)
        Styles(self.style.root, self.style.selected, defaults=self.defaults, replacements={self.path:self.data})
        self.items.append(dict(action='unset' if unset else 'set', key=self.group+'.'+name))
        if self.data != self.before: self.operations=[dict(path=str(self.path),text=encode_styles(self.data))]

    def apply(self, action):
        return Store(state_root()).apply('config-'+action, self.operations, self.guards, retain=True, catalogs=[self.path])


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
        ui.detail_spans(name,[(text,None)],label_width=min(28,max(10,len(name))))


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
    parser.add_argument('action', nargs='?', choices=['browse','list','get','set','unset','path','check','migrate'])
    parser.add_argument('key', nargs='?')
    parser.add_argument('value', nargs='?')
    parser.add_argument('--profile')
    parser.add_argument('--query', help='Initial browser search')
    parser.add_argument('--client', help='Initiating tmux client')
    parser.add_argument('--defaults', action='store_true', help='Inspect or edit shared colors and icons')
    for option in ('json','json-value','dry-run','apply','yes'):
        parser.add_argument('--'+option, action='store_true')
    args = parser.parse_args(argv)
    automatic = args.action is None
    args.action = args.action or 'list'
    if (args.query is not None or args.client) and not (automatic or args.action == 'browse'):
        parser.error('--query and --client require browse')
    if args.dry_run and args.action == 'browse': parser.error('--dry-run requires an explicit config edit')
    if args.action in ('get','set','unset') and not args.key: parser.error('a key is required')
    if (args.value is not None) != (args.action == 'set'): parser.error('set requires a value; other actions take no value')
    if args.key and args.action not in ('get','set','unset','path'): parser.error('unexpected key')
    if args.apply or args.yes:
        if args.action != 'migrate' or not args.apply or not args.yes: parser.error('migration apply requires --apply --yes')
    if args.json_value and args.action != 'set': parser.error('--json-value requires set')
    if args.defaults and args.profile: parser.error('--defaults and --profile are mutually exclusive')
    if args.defaults and args.action == 'migrate': parser.error('migration requires a profile')
    root = checkout()
    selected = context(root, args.profile)
    if not selected['layers'] and not args.defaults: raise ValueError('no profile definition in this checkout')
    if not args.json and not args.dry_run and (automatic or args.action == 'browse'):
        from interaction import terminal
        if args.action == 'browse' or terminal() and os.environ.get('TERM') != 'dumb':
            from config_menu import browse
            return browse(root, selected, args)
    layer = selected['layers'][-1] if selected['layers'] else None
    path = root/'default' if args.defaults else Path(layer['root'])/'profile.json'
    result = dict(schema=1, profile='defaults' if args.defaults else layer['id'], path=str(path))
    group, _, style_key = (args.key or '').partition('.')
    is_style = group in ('icons','colors')
    if args.defaults and args.action in ('get','set','unset') and not is_style:
        parser.error('--defaults supports colors and icons')
    if args.action == 'path':
        if args.key:
            name = Path(args.key+'.toml' if args.key in ('icons','colors') else args.key)
            if not name.parts or name.is_absolute() or '..' in name.parts or any(ord(c)<32 for c in str(name)): raise ValueError('invalid configuration name')
            path = (root/'default' if args.defaults else legacy_directory() if name.parts[0] == 'themes' else path.parent) / name
        print(json.dumps(dict(result, path=str(path)))) if args.json else print(path)
        return 0
    if args.action in ('set','unset','migrate'):
        if is_style:
            plan = StylePlan(root, selected, group, args.defaults)
            plan.edit(style_key, args.value, args.action == 'unset', args.json_value)
            result['path'] = str(plan.path)
        else:
            plan = Plan(root, selected)
            if args.action == 'migrate': plan.migrate()
            else: plan.edit(args.key, args.value, args.action == 'unset', args.json_value)
            plan.finish()
        preview = args.dry_run or (args.action == 'migrate' and not args.apply)
        result.update(status='preview' if preview else 'unchanged', items=plan.items)
        if not preview:
            applied = plan.apply(args.action)
            result.update(status=applied['status'], transaction=applied.get('id'))
    else:
        styles = Styles(root, selected, defaults=args.defaults)
        if args.action == 'check':
            if not args.defaults: validate(root, selected, read_json(path))
            result['status'] = 'valid'
        else:
            merged = {key: {} for key in ('settings', 'environment', 'files')}
            for item in selected['layers'] if not args.defaults else []:
                for key in merged: merged[key].update(item.get(key, {}))
            if not args.defaults: merged['profile'] = dict(alias=layer.get('alias'))
            merged = public_report(merged)
            merged.update({key:nested(values) for key,values in styles.values.items()})
            if args.action == 'get':
                if is_style:
                    value = merged[group]
                    for part in style_key.split('.') if style_key else []:
                        if not isinstance(value,dict) or part not in value: raise ValueError('style option is not configured')
                        value = value[part]
                    result['path'] = str(styles.path(group))
                else:
                    group, key = key_parts(args.key)
                    if key not in merged[group]: raise ValueError('key is not configured in this profile or its parents')
                    value = merged[group][key]
                if args.json: print(json.dumps(dict(result, key=args.key, value=value), ensure_ascii=True))
                elif isinstance(value,(dict,list)): render(dict(result,key=args.key,value=value))
                else: print(value if isinstance(value, str) else json.dumps(value, ensure_ascii=True))
                return 0
            result['config'] = merged
    print(json.dumps(result, ensure_ascii=True)) if args.json else render(result)
    return 0


if __name__ == '__main__':
    try: sys.exit(main())
    except (ValueError, OSError, KeyError, TypeError) as error:
        ui = Presentation(sys.stderr)
        ui.emit(ui.paint('dots config: ' + str(error), '91')); sys.exit(1)
    except KeyboardInterrupt: sys.exit(130)

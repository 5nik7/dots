"""Explicit, journaled key migration; compatible readers never invoke this."""
import json
import re
from pathlib import Path

from config_keys import canonical, document, public_styles
from style_config import read, encode
from files.transactions import Store, digest, parents_safe
from files.file_platform import state_root


def apply_operations(action, operations, guards, catalogs):
    from preference_files import clear_current
    result = Store(state_root()).apply('config-' + action, operations, guards, retain=True, catalogs=catalogs)
    if operations:
        clear_current()
    return result


def style_text(path, group):
    before=read(path)
    after=public_styles(group,before,strict=True)
    if before==after:return path.read_text()
    # Keep comments and per-field spelling while combining renamed tables.
    tables={};section='';preamble=[];seen=set()
    from preference_files import style_sections,controls,encode_controls
    for line in style_sections(path.read_text())[0].splitlines():
        match=re.fullmatch(r'\s*\[([a-z][a-z0-9_.]*)\]\s*(#.*)?',line)
        if match:
            section=match[1]
            target=canonical(group+'.'+section+'.__field__').partition('.')[2].rsplit('.',1)[0]
            tables.setdefault(target,[])
            if match[2]:tables[target].append(match[2])
            continue
        assignment=re.match(r'\s*([a-z][a-z0-9_]*)\s*=',line)
        target=canonical(group+'.'+section+'.__field__').partition('.')[2].rsplit('.',1)[0] if section else ''
        if assignment:
            full=canonical(group+'.'+(section+'.' if section else '')+assignment[1]).partition('.')[2]
            table,_,field=full.rpartition('.')
            if full not in seen:
                tables.setdefault(table,[]).append(re.sub(r'^(\s*)[a-z][a-z0-9_]*(\s*=)',lambda m:m[1]+field+m[2],line));seen.add(full)
            elif '#' in line:
                # Duplicate declarations are equal (checked above). Retain their comment.
                quoted=False;escape=False
                for i,char in enumerate(line):
                    if char=='"' and not escape:quoted=not quoted
                    if char=='#' and not quoted:tables.setdefault(table,[]).append(line[i:]);break
                    escape=char=='\\' and not escape
        elif section:tables.setdefault(target,[]).append(line)
        else:preamble.append(line)
    text='\n'.join(preamble)+'\n'+ '\n'.join(('['+table+']\n' if table else '')+'\n'.join(lines)+'\n' for table,lines in tables.items())
    # Every resulting value must match the conflict-checked translation.
    import tomllib
    from style_config import flatten
    if flatten(tomllib.loads(text))!=after:raise ValueError('key migration would change style values: '+str(path))
    return text+encode_controls(controls(path))


class KeyPlan:
    def __init__(self,root,selected,*,all_profiles=False):
        from profiles import available,definition,directory
        self.root=Path(root);self.guards={};self.operations=[];self.items=[]
        identities=[r['id'] for r in available(root)] if all_profiles else [selected['current']]
        paths=[self.root/'default/config.json',self.root/'default/colors.toml',self.root/'default/icons.toml'] if all_profiles else []
        for identity in identities:
            layer=definition(root,identity)
            profile_root=directory(self.root,identity)
            paths.extend(profile_root/name for name in ('profile.json','config.json','colors.toml','icons.toml'))
        # Shared inputs and inherited profiles are guarded even for a one-profile migration.
        paths=list(dict.fromkeys(paths))
        guard_paths=paths+[self.root/'default'/name for name in ('config.json','colors.toml','icons.toml')]
        guard_paths += [Path(layer['root'])/name for layer in selected['layers'] for name in ('profile.json','config.json','colors.toml','icons.toml')]
        for path in guard_paths:
            parents_safe(path);self.guards[str(path)]=digest(path)
        for path in paths:
            if not path.exists():continue
            if path.is_symlink() or not path.is_file() or path.stat().st_size>4*1024*1024:
                raise ValueError('key migration requires a bounded regular file: '+str(path))
            before=path.read_text()
            if path.suffix=='.json':
                data=json.loads(before)
                if path.name == 'config.json' and data.get('schema') == 2:
                    from preference_files import unified_values
                    unified_values(data)
                    continue
                changed=document(data,strict=True)
                if changed==data:continue
                after=json.dumps(changed,ensure_ascii=False,indent=2)+'\n'
            else:after=style_text(path,path.stem)
            if after!=before:
                self.operations.append(dict(path=str(path),text=after))
                self.items.append(dict(action='rename-keys',path=str(path)))
        self.catalogs=paths
        # Compare consumer projections across the complete affected inheritance
        # chains before offering a migration. Source names may change; values may not.
        from profile_config import context
        from config_values import Controls
        from style_config import Styles,flatten
        from theme_styles import snapshot
        import tomllib
        from preference_files import style_sections
        replacements={Path(op['path']):(json.loads(op['text']) if op['path'].endswith('.json') else flatten(tomllib.loads(style_sections(op['text'])[0]))) for op in self.operations}
        control_replacements={path:data for path,data in replacements.items() if path.suffix=='.json'}
        for identity in identities:
            scope=context(self.root,identity)
            before=Styles(self.root,scope)
            palette=dict(colors=before.palette,palette=before.native_palette)
            after=Styles(self.root,scope,replacements=replacements,palette=palette)
            old=Controls(self.root,scope).values
            new=Controls(self.root,scope,replacements=control_replacements).values
            if old!=new or snapshot(palette,styles=before,controls=old)['apps']!=snapshot(palette,styles=after,controls=new)['apps']:
                raise ValueError('key migration would change effective configuration for '+identity)

    def apply(self):
        return apply_operations('migrate-keys', self.operations, self.guards, self.catalogs)


def unified_layer(directory, manifest):
    """Combine explicit declarations, requiring agreement at a shared address."""
    from preference_files import GROUPS, controls, put, unified_document, unified_values
    from config_values import name
    from style_config import read as read_styles

    merged = {}
    def merge(target, incoming, path=()):
        for field, value in incoming.items():
            key = (*path, field)
            if field not in target:
                target[field] = value
            elif isinstance(value, dict) and isinstance(target[field], dict):
                merge(target[field], value, key)
            elif type(value) is not type(target[field]) or value != target[field]:
                raise ValueError('conflicting configuration declarations in ' + str(directory) + ': ' + name(key))

    empty_styles = {'colors': {}, 'icons': {}}
    def add_typed(data):
        # Test aliases before document() can replace one of their spellings.
        merge(merged, unified_document(document(data, strict=True), empty_styles))

    from preference_files import json_document
    from copy import deepcopy
    config = json_document(directory/'config.json')
    if config.get('schema') == 2:
        typed, styles = unified_values(config)
        merge(merged, unified_document(typed, styles))
    else:
        add_typed(config)
    if manifest is not None:
        add_typed({group: manifest[group] for group in GROUPS if group in manifest})
    # Inline declarations still participate below schema 2. Sibling legacy TOML
    # does not, so an unmerged entry there must be reviewed before removal.
    active = deepcopy(merged) if config['schema'] == 2 else None
    for group in empty_styles:
        path = directory/(group+'.toml')
        typed = {}
        for key, value in controls(path).items():
            put(typed, key, value)
        merge(merged, unified_document(document(typed, strict=True), {**empty_styles, group: read_styles(path)}))
    if active is not None and active != merged:
        raise ValueError('legacy preferences beside unified configuration require explicit reconciliation: ' + str(directory))
    return merged


class LayoutReviewError(ValueError):
    def __init__(self, problems):
        self.problems = problems
        super().__init__('\n'.join(item['path'] + ': ' + item['reason'] for item in problems))


class UnifiedLayoutPlan:
    """Publish each selected scope atomically with its obsolete source removals."""
    def __init__(self, root, selected, *, all_profiles=False, defaults=False):
        from profiles import available
        from profile_config import context, settings
        from preference_files import FILES, GROUPS, text
        from config_values import Controls, validate_effective
        from style_config import Styles

        root = Path(root)
        shared = root/'default'
        self.path = shared if defaults or all_profiles else Path(selected['layers'][-1]['root'])
        self.operations = []
        self.items = []
        self.guards = {}
        replacements = {}
        problems = []
        scopes = [context(root, item['id']) for item in available(root)] if all_profiles or defaults else [selected]
        targets = {shared} if all_profiles or defaults else set()
        if not defaults:
            targets.update(Path(scope['layers'][-1]['root']) for scope in scopes)
        directories = {shared, *(Path(layer['root']) for scope in scopes for layer in scope['layers'])}
        for directory in sorted(directories):
            for filename in (*FILES, *(('profile.json',) if directory != shared else ())):
                path = directory/filename
                parents_safe(path)
                text(path)  # Reject symlinks, nonregular and oversized artifacts.
                self.guards[str(path)] = digest(path)
        for directory in sorted(targets):
            path = directory/'config.json'
            manifest_path = directory/'profile.json'
            manifest = json.loads(text(manifest_path)) if directory != shared else None
            sources = [directory/filename for filename in FILES if self.guards[str(directory/filename)] is not None]
            if not sources and not any(field in (manifest or {}) for field in GROUPS):
                continue
            try:
                unified = unified_layer(directory, manifest)
            except ValueError as error:
                problems.append(dict(path=str(directory), reason=str(error)))
                continue
            replacements[path] = unified
            if path not in sources or json.loads(text(path)) != unified:
                self.write_json(path, unified)
            for source in sources:
                if source != path:
                    self.operations.append(dict(path=str(source), delete=True))
                    self.items.append(dict(action='remove-merged-preferences', path=str(source)))
            if manifest is not None:
                structural = {key: value for key, value in manifest.items() if key not in GROUPS}
                if structural != manifest:
                    replacements[manifest_path] = structural
                    self.write_json(manifest_path, structural)
        if problems:
            raise LayoutReviewError(problems)
        checks = [(scope, False) for scope in scopes]
        if shared in targets:
            checks.append((selected, True))
        for scope, checking_defaults in checks:
            before = Controls(root, scope, defaults=checking_defaults)
            after = Controls(root, scope, defaults=checking_defaults, replacements=replacements)
            old_styles = Styles(root, scope, defaults=checking_defaults)
            new_styles = Styles(root, scope, defaults=checking_defaults, replacements=replacements)
            validate_effective(after.values, after.defaults, new_styles, scope['facts']['platform'])
            def setting_values(replacements=None):
                return {key: record['value'] for key, record in settings(root, scope, defaults=checking_defaults,
                                                                         replacements=replacements).items()}
            if before.values != after.values or setting_values() != setting_values(replacements):
                raise ValueError('unified migration changes effective preferences: ' + scope['current'])
            for group in ('colors', 'icons'):
                for key in old_styles.values[group].keys() | new_styles.values[group].keys():
                    if old_styles.resolve(group, key)['value'] != new_styles.resolve(group, key)['value']:
                        raise ValueError('unified migration changes ' + group + '.' + key + ' for ' + scope['current'])
        if any(digest(Path(path)) != expected for path, expected in self.guards.items()):
            raise ValueError('configuration changed during preview')

    def write_json(self, path, value):
        from preference_files import unified_operation
        # Store retains the original byte payload for text and deletion operations.
        self.operations.append(unified_operation(path, value))
        self.items.append(dict(action='unify-preferences', path=str(path)))

    def apply(self, action='migrate-layout'):
        return apply_operations(action, self.operations, self.guards, [Path(path) for path in self.guards])

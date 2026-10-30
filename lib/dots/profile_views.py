"""Read-only profile inspection, with selected-context resolution."""
import argparse
import json
import os
from pathlib import Path
import sys
from profiles import PLATFORMS, DIRECTORIES, definition, directory, resolve, available, public_report
from platform_info import detect


def selected(root, identity=None):
    facts = detect()
    if identity is None:
        return resolve(root, facts)
    if definition(root, identity) is None:
        raise ValueError('unknown profile: ' + identity)
    platform, _, distro = identity.partition('/')
    context = dict(facts, platform=platform, distro=distro or platform, family=[], runtime='not evaluated', architecture='not evaluated', version='', name=identity, evidence=['explicit-profile'], wsl_distribution='')
    result = resolve(root, context)
    result['inspection_only'] = True
    result['detected'] = facts
    return result


def file_catalog(root, context):
    from files.catalog import Catalog, read_json, ID
    if (root / '.dots/sources.json').is_file():
        reader = Catalog(root, context['facts']['platform'], profile=context)
        active_roots = {str(root), *[r['root'] for r in context['layers']]}
        overrides = {key for row in context['layers'] for key in row.get('files', {})}
        reader.sources = [s for s in reader.sources if s['status'] == 'available' and (s['root'] in active_roots or s['id'] in overrides)]
        for source in reader.sources:
            source['profile'] = next((r['id'] for r in reversed(context['layers']) if source['id'] in r.get('files',{}) or r['root'] == source['root']), 'universal')
    else:
        # Minimal definitions can still be inspected without source composition.
        reader = Catalog.__new__(Catalog)
        reader.root, reader.platform, reader.manifests, reader.sources = root, context['facts']['platform'], {}, []
        reader.profile = context
        reader.registry = None
        reader.registry_path = root/'.dots/files.json'
        seen = set()
        for owner, path in [('universal', root), *[(r['id'], Path(r['root'])) for r in context['layers']]]:
            file = path / '.dots/files.json'
            if not file.is_file(): continue
            if not file.resolve().is_relative_to(root): raise ValueError('catalog escapes checkout')
            doc = read_json(file)
            from files.identities import canonical
            identity = canonical(doc.get('repository'))
            if not isinstance(identity, str) or not ID.fullmatch(identity) or identity in seen: raise ValueError('duplicate or invalid catalog repository')
            seen.add(identity)
            reader.sources.append(dict(id=identity, root=str(path), status='available', platforms=[reader.platform], profile=owner))
    reader.observe = lambda row: 'unobserved'
    return reader


def manifests(root, context):
    reader = file_catalog(root,context)
    rows=[]
    for source in reader.sources:
        path=Path(source['root']);owner=source['profile']
        for item in reader.manifest(source)['resources']:
            origin=path/item['source']
            if not origin.resolve().is_relative_to(path.resolve()): raise ValueError('resource source escapes profile: '+item['id'])
            target=item.get('targets',{}).get(reader.platform,item.get('target'))
            if reader.platform=='wsl' and owner.startswith('linux'):
                target=item.get('targets',{}).get('wsl',item.get('targets',{}).get('linux',item.get('target')))
            rows.append(dict(item,id=source['id']+':'+item['id'],layer=owner,source=str(origin),target=target))
    return rows


def command_rows(root, context):
    from command_metadata import catalog, read, ROUTE
    directories = [Path(r['root'])/'bin' for r in reversed(context['layers'])] + [root/'bin', root/'local/bin']
    # Shared catalog validates collisions, reserved routes and replacements.
    winners = catalog([p for p in directories if p.is_dir()])
    result = []
    for layer in reversed(context['layers']):
        for path in sorted((Path(layer['root'])/'bin').glob('dots-*')):
            stem = path.name[5:]
            if path.suffix in ('.ps1','.exe'): stem = stem[:-len(path.suffix)]
            if not ROUTE.fullmatch(stem): continue
            result.append(dict(route=stem.replace('-', ' '), source=str(path), layer=layer['id'],
                               selected=str(winners[stem]['path']) == str(path), replaces=stem in layer.get('replaces_commands', [])))
    return result


def validate(root, identities):
    checks = []
    for identity in identities:
        try:
            context = selected(root, identity)
            from profile_environment import Model
            Model(root, context)
            rows = manifests(root, context)
            conflicts=[r['id'] for r in file_catalog(root,context).records() if r['status']=='conflict']
            if conflicts: raise ValueError('conflicting resource mappings: '+', '.join(conflicts))
            command_rows(root, context)
            checks.append(dict(profile=identity, status='passed', detail='Definition, inheritance, catalogs and commands are valid'))
        except (ValueError, OSError, KeyError, TypeError) as error:
            checks.append(dict(profile=identity, status='failed', detail=str(error)))
    return checks


def identities(root):
    result = []
    for platform in PLATFORMS:
        if (root/'profiles'/platform/'profile.json').exists(): result.append(platform)
        base = root/'profiles'/platform/'distros'
        if base.is_dir():
            result.extend(platform+'/'+p.name for p in sorted(base.iterdir()) if (p/'profile.json').exists())
    return result


def report(root, args):
    if args.family == 'profiles':
        if args.operation == 'check':
            return dict(version=1, checks=validate(root, identities(root)))
        context = resolve(root)
        active = {r['id'] for r in context['layers']}
        context['profiles'] = [dict(r, active=r['id'] in active) for r in available(root)
                               if (not args.platform or r['id'].split('/')[0] == args.platform) and (not args.active or r['id'] in active)]
        return context
    context = selected(root, args.identity)
    operation = args.operation
    if operation == 'show': return context
    if operation == 'check': return dict(version=1, checks=validate(root, [args.identity or context['current']]))
    rows = []
    if operation == 'layers':
        rows = [dict(id='universal', root=str(root), reason='Universal defaults')]
        parents = {p for r in context['layers'] for p in r.get('extends', [])}
        for layer in context['layers']:
            reason = 'Explicit parent' if layer['id'] in parents else 'Platform base' if '/' not in layer['id'] else 'Distro or family match'
            if context['facts']['platform'] == 'wsl' and layer['id'].startswith('linux'): reason += '; Linux inherited by WSL'
            rows.append(dict(id=layer['id'], root=layer['root'], reason=reason))
    elif operation == 'paths':
        for layer in context['layers']:
            for kind in DIRECTORIES:
                p = Path(layer['root'])/kind
                if args.kind and args.kind!='path' and kind != args.kind or args.existing and not p.is_dir(): continue
                rows.append(dict(layer=layer['id'], kind=kind, path=str(p), exists=p.is_dir()))
        ordered = [str(Path(r['root'])/part) for r in reversed(context['layers']) for part in r.get('path',['bin','scripts']) if (Path(r['root'])/part).is_dir()]
        if not args.kind or args.kind=='path':
            for layer in context['layers']:
                for relative in layer.get('path',['bin','scripts']):
                    if relative in DIRECTORIES: continue
                    path=Path(layer['root'])/relative
                    if args.existing and not path.is_dir(): continue
                    rows.append(dict(layer=layer['id'],kind='path',path=str(path),exists=path.is_dir()))
        for row in rows: row['path_order'] = ordered.index(row['path'])+1 if row['path'] in ordered else None
        if args.kind=='path': rows=sorted((r for r in rows if r['path_order'] is not None),key=lambda r:r['path_order'])
    elif operation == 'env':
        from profile_environment import Model
        generated = Model(root,context)
        rows += [dict(name=key,template=value,layer=generated.origins[key][8:],selected=True,generated=True) for key,value in generated.scalars.items()]
        for layer in context['layers']:
            for key, value in public_report(layer).get('environment', {}).items():
                rows.append(dict(name=key, template=value, layer=layer['id'], selected=True))
        seen = set()
        for row in reversed(rows): row['selected'] = row['name'] not in seen; seen.add(row['name'])
        if not args.all: rows = [r for r in rows if r['selected']]
    elif operation == 'files': rows = [r for r in manifests(root, context) if r['layer'] != 'universal']
    elif operation == 'commands': rows = command_rows(root, context)
    return dict(version=1, current=context['current'], inspection_only=bool(args.identity), rows=rows)


def render(result, operation, verbose=False):
    from files.catalog import Presentation
    ui = Presentation()
    ui.heading({'show':'Dots profile','list':'Dots profiles'}.get(operation,'Profile '+operation))
    if 'checks' in result:
        for row in result['checks']:
            ui.emit(); ui.detail('Profile', row['profile']); ui.detail('Status', row['status'], '32' if row['status']=='passed' else '31'); ui.detail('Detail', row['detail'])
        ui.emit(); ui.detail('Result', f"{sum(r['status']=='passed' for r in result['checks'])}/{len(result['checks'])} passed")
        return
    if 'profiles' in result:
        rows = result['profiles']
    elif 'rows' in result: rows = result['rows']
    else:
        facts = result['facts']
        for key in ('platform','distro','runtime','architecture'):
            ui.detail('Arch' if key=='architecture' else key.capitalize(), facts[key])
        if result.get('inspection_only'): ui.detail('Context', 'Inspection only; detected platform is '+result['detected']['platform'])
        ui.detail('Profile', result['current']); ui.detail('Layers', ['universal']+[r['id'] for r in result['layers']])
        if verbose: ui.detail('Evidence', facts.get('evidence',[]))
        rows = result['layers']
    for row in rows:
        ui.emit()
        if operation=='paths':
            ui.resource_detail(row['kind'].capitalize(),row['path'],kind='dir')
            ui.detail('State',('available' if row['exists'] else 'missing')+' · '+row['layer']+((' · PATH '+str(row['path_order'])) if row['path_order'] is not None else ''))
            continue
        for key, value in row.items():
            if key in ('files','settings'):
                if key == 'files': ui.detail('Mappings', sum(len(items) for items in value.values()))
                else: ui.detail('Saved settings', len(value))
                continue
            if key == 'generated': continue
            if key == 'template' and row.get('generated'):
                ui.resource_detail('Path', value, kind='dir'); continue
            if key=='schema' and not verbose: continue
            if key in ('schema','environment','extends','replaces_commands','path') and isinstance(value,(list,dict)) and not verbose: continue
            if key in ('platforms','targets','app','category','strategy','enabled') and not verbose: continue
            if key in ('root','source','path'):
                ui.resource_detail('Directory' if key=='root' else key.capitalize(), value, kind='dir' if key=='root' or row.get('kind') else None)
            else:
                label = {'id':'Resource' if operation=='files' else 'Profile','description':'Summary','inspection_only':'Preview','path_order':'PATH order'}.get(key,key.replace('_',' ').capitalize())
                ui.detail(label, value)
    if not rows: ui.detail('Result','No matching entries')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('family', choices=('profile','profiles'))
    parser.add_argument('operation', nargs='?')
    parser.add_argument('identity', nargs='?')
    parser.add_argument('--json', action='store_true'); parser.add_argument('--verbose','-v',action='store_true')
    parser.add_argument('--kind',choices=(*DIRECTORIES,'path')); parser.add_argument('--existing',action='store_true'); parser.add_argument('--raw',action='store_true')
    parser.add_argument('--all',action='store_true'); parser.add_argument('--active',action='store_true'); parser.add_argument('--platform',choices=PLATFORMS)
    args=parser.parse_args(argv)
    args.operation = args.operation or ('show' if args.family=='profile' else 'list')
    allowed = ('show','layers','paths','env','files','commands','check') if args.family=='profile' else ('list','check')
    if args.operation not in allowed: parser.error('unknown operation: '+args.operation)
    if args.family=='profiles' and args.identity: parser.error('profiles does not accept an ID')
    if (args.kind or args.existing or args.raw) and args.operation!='paths': parser.error('path options require profile paths')
    if args.raw and (not args.kind or args.json): parser.error('--raw requires --kind and excludes --json')
    if args.all and args.operation!='env': parser.error('--all requires profile env')
    if (args.active or args.platform) and not (args.family=='profiles' and args.operation=='list'): parser.error('collection filters require profiles list')
    root=Path(os.environ.get('DOTS') or Path(__file__).resolve().parents[2]).resolve()
    result=public_report(report(root,args))
    if args.json: print(json.dumps(result,ensure_ascii=True))
    elif args.raw:
        for row in result['rows']: print(row['path'])
    else: render(result,args.operation,args.verbose)
    return int(any(r['status']=='failed' for r in result.get('checks',[])))

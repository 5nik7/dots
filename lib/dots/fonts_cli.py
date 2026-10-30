#!/usr/bin/env python3
"""Shared native fonts controller. Frontends never duplicate font lifecycle logic."""
from contextlib import ExitStack
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

LIB = Path(__file__).resolve().parent
sys.path.insert(0, str(LIB))
sys.path.insert(0, str(LIB / 'files'))
from fonts.commands import COMMANDS, OPTIONS, COMMON, parser
from fonts.model import Library, Plan, metadata, digest, exists
from fonts import operations as ops
from fonts.config import TARGETS, configure, destination
from interaction import SelectionEnded, terminal, gum_confirm
from resources import clean


def render(data, stream=None):
    from files.catalog import Presentation
    ui = Presentation(stream)
    ui.heading('Fonts')
    if data.get('status'): ui.detail('Result', data['status'])
    if data.get('transaction'): ui.detail('Transaction', data['transaction'])
    if data.get('directory'): ui.resource_detail('Directory', data['directory'])
    if data.get('path'): ui.resource_detail('Preferences', data['path'])
    rows = data.get('items', [])
    if not rows and 'items' in data: ui.emit('  No matching fonts.')
    for row in rows:
        for key in ('id','name','target','action'):
            if row.get(key):ui.detail(key.upper() if key=='id' else key.title(),row[key])
        for key in ('version','latest','variant','status','ownership','reason','face','source','provider','codepoint','glyph','pinned','selection'):
            if row.get(key) is not None: ui.detail(key.title(), row[key])
        if row.get('installed'): ui.detail('Installed', row['installed']['version'] + ' / ' + row['installed']['variant'])
        if row.get('pin'): ui.detail('Pinned', row['pin'])
        if row.get('path'): ui.resource_detail('Path', row['path'])
        if row.get('aliases'): ui.detail('Aliases', ', '.join(row['aliases']))
        if 'stored_versions' in row: ui.detail('Stored', ', '.join(row['stored_versions']) or 'none; history retained')
        for active in row.get('active',[]): ui.detail('Active',active['version']+' / '+active['selection'])
        versions = row.get('versions', {})
        for version, record in versions.items():
            ui.detail('Version', version)
            if record.get('available') is False: ui.detail('Status','uninstalled; history retained')
            for font in record.get('fonts', []): ui.detail('Face', font['file'] + ' · ' + font['family'] + ' · ' + font['variant'])
            if record.get('provenance'): ui.detail('Provenance', json.dumps(record['provenance'], ensure_ascii=False))
    for operation in data.get('operations', []): ui.resource_detail(operation['kind'].title(), operation['path'])
    for notice in data.get('notices', []): ui.detail('Notice', notice)


def emit(data, args):
    if getattr(args,'_directory',None):data=dict(data,directory=args._directory)
    if args.json: print(json.dumps(data, ensure_ascii=True))
    else: render(data)


def approve(plan, args, *, context=None):
    if not plan.operations: return
    if args.yes: return
    if args.json or (context is None and not terminal()): raise ValueError('mutation requires --yes when noninteractive')
    if context:
        import io
        from menus import show_message, choose, Menu, Entry
        from menu_pager import page_text
        output = io.StringIO(); render(plan.report(), output)
        result = page_text(output.getvalue(), title='fonts·review', context=context)
        if not result: raise SelectionEnded(130)
        selected = choose(Menu('fonts:confirm','Apply font changes', (Entry('cancel','Cancel'), Entry('apply','Apply'))),
                          mode='browse',context=context,compact=True)
        if selected is None or selected.id != 'apply': raise SelectionEnded(130)
    else:
        render(plan.report(), sys.stderr)
        answer = gum_confirm('Apply these font changes?', 'Apply')
        if answer is None: answer = input('Apply? [y/N] ').strip().casefold() in ('y','yes')
        if not answer: raise SelectionEnded(130)


def targets(library):
    rows = []
    for target in TARGETS:
        try:
            result = destination(library, target)
            rows.append(dict(target=target, status='available', path=result['path'], source=result['source']))
        except (ValueError, OSError) as error:
            rows.append(dict(target=target, status='unavailable', reason=clean(str(error))))
    return rows


def system_fonts(library):
    if library.platform == 'windows':
        import winreg
        import font_registry
        rows = []
        for hive, label in ((winreg.HKEY_CURRENT_USER,'user'), (winreg.HKEY_LOCAL_MACHINE,'system')):
            try:
                with winreg.OpenKey(hive, font_registry.KEY) as key:
                    for index in range(min(winreg.QueryInfoKey(key)[1], 20000)):
                        name, path, kind = winreg.EnumValue(key,index)
                        if kind == winreg.REG_SZ: rows.append(dict(name=name,path=path,source=label,provider='external'))
            except FileNotFoundError: pass
        return rows
    if not shutil.which('fc-list'): raise ValueError('system inventory requires optional fontconfig (fc-list)')
    result = subprocess.run(['fc-list','--format=%{file}\t%{family}\t%{style}\n'],capture_output=True,text=True,timeout=15)
    if result.returncode or len(result.stdout) > 8*1024*1024: raise ValueError('system font inventory failed or exceeded its limit')
    rows = []
    for line in result.stdout.splitlines():
        fields = line.split('\t')
        if len(fields) == 3: rows.append(dict(path=fields[0], name=fields[1], face=fields[2], provider='external', source='fontconfig'))
    return rows


def downloaded(plan, identity, version, temporary, *, keep_archive=False):
    from fonts.providers import download
    available = plan.library.catalog['families'].get(identity)
    if not available: raise ValueError('font is absent from saved catalogs; run fonts update')
    version = version or available['latest']
    if version in plan.document['families'].get(identity, {}).get('versions', {}) and not plan.document['families'][identity]['versions'][version].get('partial'):
        for font in plan.document['families'][identity]['versions'][version]['fonts']: plan.file(identity,version,font)
        return version
    if version not in available['versions']: raise ValueError('version is not cataloged; refresh that Nerd Fonts version explicitly')
    payload = Path(temporary) / ('payload-' + str(len(plan.payloads)))
    record = download(identity, available['versions'][version], payload, keep_archive=keep_archive)
    ops.stage(plan, identity, version, payload, record, available['name'],temporary=temporary)
    return version


def plan_action(library, args, temporary):
    action = args.action
    if action=='set' or action=='use' and args.target:
        from fonts.defaults import set_font
        return set_font(library,args,temporary)
    if action=='restore':
        from fonts.defaults import restore
        return restore(library,args,temporary)
    if action in ('install','copy','migrate'):
        from fonts.actions import transfer
        return transfer(library,args,temporary)
    if library.directory and action not in ('export','undo'):
        from fonts.directories import action as directory_action
        return directory_action(library,args,temporary)
    if action=='use': raise ValueError('use requires --directory; use install for the personal library')
    if action=='update': raise ValueError('update FONT requires --directory; use upgrade for active fonts')
    if action=='uninstall' and args.version: raise ValueError('--version on uninstall requires --directory; use remove for a retained personal version')
    plan = Plan(library)
    plan.guard(library.catalog_path)
    identity = library.resolve(args.operand, available=action=='download') if args.operand and action not in ('import','undo') else None
    if action == 'download':
        if args.dry_run:
            row = library.catalog['families'][identity]
            version = args.version or row['latest']
            if version not in row['versions']: raise ValueError('version is not cataloged')
            plan.items.append(dict(id=identity,version=version,action='download and validate before saving'))
        else: downloaded(plan,identity,args.version,temporary,keep_archive=args.keep_archive)
    elif action == 'import':
        ops.import_files(plan,args.operand,temporary)
    elif action == 'export':
        if not args.output: raise ValueError('export requires --output DIRECTORY')
        version, record = library.version(identity,args.version)
        for font in record['fonts']: plan.file(identity,version,font)
        output = Path(args.output).expanduser().absolute()
        if exists(output): raise ValueError('export destination already exists; choose a new directory')
        source = library.folder(identity,version)
        if output == source or output.is_relative_to(source) or source.is_relative_to(output): raise ValueError('export source and destination overlap')
        plan.put(output,source=source)
        plan.items.append(dict(id=identity,version=version,action='export',path=str(output)))
    elif action in ('install','rollback'):
        if action=='rollback' and not args.version: raise ValueError('rollback requires --version')
        if action=='rollback' and not plan.document['families'][identity].get('installed'):
            ops.replace_active(plan,identity,args.version)
        else:ops.install(plan,identity,args.version,args.variant)
    elif action == 'uninstall': ops.uninstall(plan,identity)
    elif action in ('pin','unpin'):
        row = plan.document['families'][identity]
        value = ops.version_for(plan,identity,args.version)[0] if action=='pin' else None
        row['pin'] = value
        plan.items.append(dict(id=identity,action=action,version=value))
    elif action == 'remove':
        if not args.version: raise ValueError('remove requires an exact --version')
        ops.remove(plan,identity,args.version)
    elif action == 'upgrade':
        active={ref['id']:ref for ref in library.document['targets'].values()}
        identities = [identity] if identity else [key for key,row in library.families.items() if row.get('installed') or key in active]
        for key in identities:
            row = plan.document['families'][key]
            if not row.get('installed') and key not in active: raise ValueError('upgrade requires an installed or active family')
            if row.get('pin'):
                plan.items.append(dict(id=key, action='skip pinned',version=row['pin'])); continue
            catalog = library.catalog['families'].get(key)
            if not catalog:
                plan.items.append(dict(id=key,action='skip unknown upstream version')); continue
            current=(row.get('installed') or active[key])['version']
            old = row['versions'][current]
            candidate = catalog['versions'][catalog['latest']]
            if catalog['latest'] == current or (old.get('fingerprint') and old['fingerprint']==candidate.get('fingerprint')):
                plan.items.append(dict(id=key,action='up to date',version=current)); continue
            if args.dry_run and catalog['latest'] not in row['versions']:
                plan.items.append(dict(id=key,version=catalog['latest'],action='download, validate active faces, then upgrade',
                    targets=[r['target'] for r in library.document['targets'].values() if r['id']==key])); continue
            version = downloaded(plan,key,catalog['latest'],temporary)
            if row.get('installed'):ops.install(plan,key,version)
            else:ops.replace_active(plan,key,version)
    elif action == 'undo':
        from transactions import Store
        store=Store(library.state); record=store.load(args.operand)
        prefix=library.transaction_action('')
        if not record['action'].startswith(prefix) or (not library.directory and record['action'].startswith('fonts-directory-')):
            raise ValueError('transaction belongs to another font scope; select its --directory or use dots files undo')
        if library.directory: plan=Plan(Library(platform=library.platform))
        plan.operations,plan.guards,_=store.inverse(args.operand)
        from fonts.inventory import user_roots
        if any('font_registry' in op or any(Path(op['path']).is_relative_to(root) for root in user_roots(plan.library)) for op in plan.operations): plan.refresh.add('fonts')
        if any(op['path']==str(library.home/'.termux/font.ttf') for op in plan.operations): plan.refresh.add('termux')
        plan.items.append(dict(id=args.operand,action='undo'))
    if action in ('upgrade','rollback'):
        from fonts.defaults import synchronize
        from fonts.workspace import Workspace
        workspace=Workspace(library,temporary,plan=plan)
        synchronize(workspace)
        return workspace.finish()
    return plan.finish()


def mutate(library,args,*,context=None):
    with tempfile.TemporaryDirectory(prefix='dots-fonts-') as temporary:
        plan=plan_action(library,args,temporary)
        if args.dry_run:
            data=plan.report()
            if library.directory:data['directory']=str(library.directory)
            return data
        approve(plan,args,context=context)
        from files.events import OperationOutput
        from transactions import Store
        result=Store(library.state,observer=OperationOutput.for_args(args)).apply(library.transaction_action(args.action),plan.operations,plan.guards,retain=True)
        data=dict(schema=1,status=result['status'],transaction=result.get('id'),items=plan.items)
        if library.directory:data['directory']=str(library.directory)
        if result['status']=='complete':
            if args.action=='undo': plan.document=Library(platform=library.platform).document
            data['notices']=ops.refresh(plan,no_reload=args.no_reload)
        return data


def run(argv=None):
    command=parser();args=command.parse_args(argv)
    for name in ('color','icons'):
        if getattr(args,name): os.environ['DOTS_'+name.upper()]='never' if getattr(args,name)=='none' else getattr(args,name)
    if sys.version_info < (3,11): raise ValueError('fonts requires Python 3.11 or newer')
    from progress import configure as progress_configure
    progress_configure(not (args.json or args.dry_run or args.action == 'path'))
    action=args.action
    library=Library(directory=args.directory)
    args._directory=str(library.directory) if library.directory else None
    interactive=not args.json and not args.print and (terminal() or bool(os.environ.get('DOTS_MENU_CONTEXT')))
    if action in (None,'browse','installed') and not args.json and not args.print and (interactive or action=='browse'):
        from fonts.browser import browse
        from fonts.menus import home,installed,downloaded
        if action=='installed':return installed(args)
        if args.downloaded:return downloaded(args)
        if action is None and not args.query:return home(args)
        return browse(args)
    if action=='set' and not args.operand and not args.file and interactive:
        from fonts.menus import set_menu
        return set_menu(args)
    args.action=action=action or 'list'
    if action=='icons':
        from fonts.browser import icons
        return icons(library,args)
    if action=='installed':
        from fonts.inventory import snapshot
        rows,notices=snapshot(library)
        terms=(args.query or '').casefold().split()
        emit(dict(schema=1,items=[r for r in rows if all(t in json.dumps(r).casefold() for t in terms)],notices=notices),args)
    elif action=='defaults':
        from fonts.defaults import rows
        emit(rows(library),args)
    elif action=='browse' and args.downloaded:
        from fonts.menus import downloaded_rows
        emit(dict(schema=1,items=downloaded_rows(library)),args)
    elif action in ('list','search','browse'):
        rows=system_fonts(library) if args.system else library.rows(available=action in ('search','browse'))
        terms=(args.query or args.operand or '').casefold().split()
        rows=[row for row in rows if all(term.replace(' ','') in json.dumps(row,ensure_ascii=False).casefold().replace(' ','') for term in terms)
              and (not args.source or args.source=='all' or row.get('provider')==args.source)
              and (not args.installed or (row.get('stored_versions') if library.directory else row.get('installed')))
              and (not args.downloaded or not library.directory or row.get('stored_versions'))
              and (not args.monospace or any(font['monospace'] for v in row.get('versions',{}).values() for font in v.get('fonts',[])))]
        emit(dict(schema=1,items=rows),args)
    elif action in ('show','versions','path'):
        identity=library.resolve(args.operand,available=True)
        if action=='versions':
            available=library.catalog['families'].get(identity,{}).get('versions',{})
            saved=library.families.get(identity,{}).get('versions',{})
            emit(dict(schema=1,items=[dict(id=identity,version=v,status=('uninstalled' if saved[v].get('available') is False else 'stored' if library.directory else 'downloaded') if v in saved else 'cataloged') for v in dict(available,**saved)]),args)
        elif action=='path':
            version,record=library.version(identity,args.version);font=ops.face_for(record,args.face,args.variant)
            path=str(library.file(identity,version,font))
            if args.json:emit(dict(schema=1,items=[dict(id=identity,version=version,path=path)]),args)
            else:print(path)
        else:
            upstream=library.catalog['families'].get(identity,{})
            saved=library.families.get(identity,{})
            row=dict(upstream,**saved)
            row['versions']=dict(upstream.get('versions',{}),**saved.get('versions',{}))
            if args.version:
                if args.version not in row['versions']: raise ValueError('unknown version')
                row=dict(row,versions={args.version:row['versions'][args.version]})
            emit(dict(schema=1,items=[dict(id=identity,**row)]),args)
    elif action=='current': emit(dict(schema=1,items=library.active() if library.directory else [dict(selection=key,**row) for key,row in library.document['targets'].items()]),args)
    elif action=='targets': emit(dict(schema=1,items=targets(library)),args)
    elif action=='directories':
        from fonts.destinations import Destinations
        emit(dict(schema=1,items=Destinations().rows()),args)
    elif action=='update' and not args.operand:
        if args.source=='local': raise ValueError('local imports have no upstream catalog')
        plan=Plan(library);plan.guard(library.catalog_path)
        plan.items.append(dict(action='refresh catalog',source=args.source or 'all',version=args.version))
        if args.dry_run: emit(plan.report(),args)
        else:
            from fonts.providers import refresh
            data=refresh(library.catalog,args.source or 'all',args.version)
            plan.put(library.catalog_path,data=data)
            emit(plan.apply('update'),args)
    else: emit(mutate(library,args),args)
    return 0


def main(argv=None):
    try:
        if argv is None: argv=sys.argv[1:]
        if argv[:1]==['__legacy']:
            from fonts.legacy import run as legacy
            return legacy(argv[1:])
        return run(argv)
    except SelectionEnded as error: return error.status
    except (KeyboardInterrupt,EOFError): return 130
    except (KeyError,TypeError):
        print('fonts: invalid font metadata; preserve and review the library or refresh its catalog',file=sys.stderr);return 1
    except (ValueError,OSError,subprocess.SubprocessError) as error:
        print('fonts: '+clean(str(error)),file=sys.stderr);return 1


if __name__=='__main__': sys.exit(main())

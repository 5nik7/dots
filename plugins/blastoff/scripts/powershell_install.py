#!/usr/bin/env python3
"""CurrentUser module layout using the shared lifecycle transaction engine.

The private JSON plan protocol is consumed by PowerShell's ShouldProcess adapter.
It is never the default human CLI output. No profile is executed here.
"""
import base64
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('blastoff_lifecycle', ROOT/'scripts/install.py')
engine = importlib.util.module_from_spec(spec); spec.loader.exec_module(engine)
core, integration = engine.core, engine.integration


def control(package):
    return package/'.blastoff'


def read_manifest(package):
    path = control(package)/'install.json'
    integration.inspect(core,path)
    if not core.exists(path):
        return {'format':3,'layout':'powershell','home':str(Path.home()),'version':None,
                'files':{},'integration':None,'backups':{}}
    doc = json.loads(core.read(path))
    if (not isinstance(doc,dict) or doc.get('format') != 3 or doc.get('layout') != 'powershell'
            or doc.get('home') != str(Path.home()) or not isinstance(doc.get('files'),dict)
            or not isinstance(doc.get('backups'),dict)):
        raise core.Failure('Invalid CurrentUser module ownership; preserve and review '+str(path))
    engine.version_tuple(doc.get('version'))
    for value, checksum in doc['files'].items():
        target = integration.absolute(core,value)
        if not target.is_relative_to(package) or len(target.relative_to(package).parts)<2:
            raise core.Failure('Unsafe module ownership path: '+value)
        engine.version_tuple(target.relative_to(package).parts[0])
        if not isinstance(checksum,str) or not re.fullmatch('[0-9a-f]{64}',checksum):
            raise core.Failure('Invalid owned checksum')
    for value,checksum in doc['backups'].items():
        target=integration.absolute(core,value)
        if not target.is_relative_to(control(package)/'profile-backups') or not re.fullmatch('[0-9a-f]{64}',checksum):
            raise core.Failure('Unsafe profile backup ownership')
    record=doc.get('integration')
    if record:
        if not isinstance(record,dict) or set(record) != {'profiles','files'} or record['files']:
            raise core.Failure('Invalid PowerShell profile ownership')
        if set(record['profiles']) != {'powershell'}:
            raise core.Failure('Invalid PowerShell profile ownership')
        item=record['profiles']['powershell']; integration.absolute(core,item['path'])
        if not isinstance(item.get('blocks'),list) or len(item['blocks']) != 1:
            raise core.Failure('Invalid profile integration block')
        block=item['blocks'][0]
        raw=base64.b64decode(block['bytes'],validate=True)
        texts=[]
        for codec in ('utf-8','utf-16-le','utf-16-be'):
            try: texts.append(raw.decode(codec))
            except UnicodeError: pass
        text=next((v for v in texts if '# >>> blastoff powershell-currentuser ' in v),'')
        if block.get('position') != 'append' or '# >>> blastoff powershell-currentuser ' not in text or '# <<< blastoff powershell-currentuser ' not in text:
            raise core.Failure('Unrecognized profile integration block')
    return doc


def payload(package):
    version_root=package/core.VERSION
    pending={}
    for directory in ('lib','powershell','scripts','completions','man','assets','docs'):
        for source in sorted((ROOT/directory).rglob('*')):
            if '__pycache__' in source.parts or source.suffix in ('.pyc','.pyo') or not source.is_file(): continue
            pending[version_root/source.relative_to(ROOT)] = (core.read(source),0o644)
    for name in ('install.ps1','uninstall.ps1','VERSION','README.md','LICENSE','CHANGELOG.md'):
        pending[version_root/name]=(core.read(ROOT/name),0o644)
    manifest=core.read(ROOT/'powershell/blastoff.psd1').replace(b"RootModule = 'blastoff.psm1'",b"RootModule = 'powershell/blastoff.psm1'")
    pending[version_root/'blastoff.psd1']=(manifest,0o644)
    return pending,version_root


def profile_conflicts(plan, paths, previous, imports=()):
    for path in dict.fromkeys(paths):
        target=integration.absolute(core,path)
        if plan.observe(target) is None: continue
        data=core.read(target)
        if previous and previous['path']==str(target):
            data=integration.remove_blocks(core,data,previous)
        codec,bom=integration.encoding(data); text=data[len(bom):].decode(codec)
        # Conservative read-only supplement to the host AST check. Never execute
        # a profile to discover dynamic imports. Other ownership is not adopted.
        observed=any(item.get('path')==str(target) and item.get('text') and item['text'] in text for item in imports)
        if observed or '# >>> blastoff ' in text or re.search(r'(?im)^[^#\r\n]*\b(?:Import-Module|ipmo)\b[^\r\n]*blastoff',text):
            raise core.Failure('Conflicting Blastoff profile integration: '+str(target)+'; preserve it and use -NoProfile or resolve its owner explicitly')


def make_plan(action, context, *, verify=True):
    if not isinstance(context,dict): raise core.Failure('Invalid lifecycle context',2)
    if context.get('host') != os.name:
        raise core.Failure('PowerShell and Python platform mismatch; do not mix Windows and WSL',3)
    try:
        platforms = core.ui_module('host_platform')
        platform = platforms.validate(platforms.detect('powershell'))
    except ValueError as error:
        raise core.Failure(str(error),3) from error
    module_root=integration.absolute(core,context['module_root'])
    if module_root == Path(module_root.anchor): raise core.Failure('Refusing filesystem root as ModuleRoot',2)
    package=module_root/'blastoff'; private=control(package)
    doc=read_manifest(package)
    plan=engine.Plan(action,package,doc,manifest=private/'install.json',lock=private/'.install.lock',backup_root=private/'profile-backups')
    plan.platform = platform
    previous=(doc.get('integration') or {}).get('profiles',{}).get('powershell')
    if action=='uninstall':
        if doc['version'] is None:
            plan.notes.append('Not installed; nothing to remove.'); return plan
        for value,checksum in doc['files'].items():
            target=Path(value)
            if plan.observe(target) is not None:
                if engine.digest(core.read(target)) == checksum:
                    plan.remove(target,'remove owned file')
                else: plan.notes.append('Retain modified file: '+value)
        if previous:
            target=Path(previous['path'])
            if plan.observe(target) is not None:
                data=core.read(target)
                try: clean=integration.remove_blocks(core,data,previous)
                except core.Failure:
                    plan.notes.append('Retain modified profile integration: '+str(target))
                else: engine.profile_edits(plan,{target:None if previous.get('created') and not clean else clean})
        plan.notes.append('Retain themes, modules, backups, provenance, Starship config and profile recovery backups.')
        engine.preflight(plan)
        return plan
    if verify: engine.module('blastoff_verify',ROOT/'scripts/verify.py').verify(ROOT)
    engine.verify_owned(plan,doc)
    if doc['version'] and engine.version_tuple(doc['version'])>engine.version_tuple(core.VERSION):
        raise core.Failure('Newer managed module is installed; refusing downgrade')
    pending,version_root=payload(package)
    ownership=dict(doc['files'])
    for target,(data,mode) in pending.items():
        present=plan.observe(target) is not None
        if present and str(target) not in ownership:
            raise core.Failure('Unowned module destination: '+str(target))
        if present and core.read(target)!=data:
            raise core.Failure('Immutable module version has different payload: '+str(target)+'; use a new release version')
        plan.write(target,data,mode,'refresh owned file' if present else 'install')
        ownership[str(target)]=engine.digest(data)
    record=doc.get('integration')
    profile=context.get('profile_path')
    edits={}
    if profile:
        target=integration.absolute(core,profile)
        if previous and previous['path']!=str(target):
            raise core.Failure('A different profile is already owned; uninstall its integration before changing -ProfilePath')
        profile_conflicts(plan,[profile,*context.get('known_profiles',[])],previous,context.get('imports',[]))
        manifest=version_root/'blastoff.psd1'
        quoted=str(manifest).replace("'","''")
        body="Import-Module '"+quoted+"'"
        data,item=integration.profile(core,target,'powershell',[('append',body)],previous,'powershell-currentuser')
        edits[target]=data;record={'profiles':{'powershell':item},'files':{}}
    elif previous:
        plan.notes.append('-NoProfile leaves the previously owned integration unchanged; it continues importing its recorded version.')
    plan.new_doc={'format':3,'layout':'powershell','home':str(Path.home()),'version':core.VERSION,
                  'files':ownership,'integration':record,'backups':dict(doc['backups'])}
    engine.profile_edits(plan,edits)
    plan.notes += ['New sessions use the managed profile import.' if profile else 'No profile changes requested.',
                   "Activate in this session: Import-Module '"+str(version_root/'blastoff.psd1').replace("'","''")+"' -Force",
                   'Module payload is independent of the shell-prefix frontend; user data paths are unchanged.']
    engine.preflight(plan)
    return plan


def description(plan):
    # Include the complete observed set and planned bytes in the approval digest,
    # but return only actions and profile diffs to the human adapter.
    digest=engine.digest(engine.document_bytes({'expected':{str(k):(list(v[:4])+[v[4].hex(),v[5]] if v is not None else None) for k,v in plan.expected.items()},
        'writes':{str(k):[engine.digest(v[0]),v[1]] for k,v in plan.writes.items()},
        'removes':sorted(str(p) for p in plan.removes),'record':plan.new_doc}))
    profiles=[]
    import difflib
    for path in plan.profiles:
        before=core.read(path) if core.exists(path) else b''
        after=plan.writes[path][0] if path in plan.writes else b'' if path in plan.removes else before
        codec,bom=integration.encoding(before or after)
        profiles.append({'path':str(path),'diff':''.join(difflib.unified_diff(before.decode(codec).splitlines(True),after.decode(codec).splitlines(True),fromfile=str(path),tofile=str(path)))})
    actions=[[reason,str(path)] for reason,path in plan.rows]
    if plan.action=='install' and plan.new_doc!=plan.doc: actions.append(['record ownership',str(plan.manifest)])
    elif plan.action=='uninstall' and plan.doc['version']: actions.append(['remove ownership record',str(plan.manifest)])
    return {'protocol':1,'action':plan.action,'version':core.VERSION,'destination':str(plan.prefix),
            'current':plan.current,'actions':actions,'platform':plan.platform,
            'profiles':profiles,'notes':plan.notes,'token':digest}


def run(argv):
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['install','uninstall'])
    parser.add_argument('--context',required=True)
    parser.add_argument('--plan-json',action='store_true')
    parser.add_argument('--apply-token')
    args=parser.parse_args(argv)
    if len(args.context)>131072: raise ValueError('Context too large')
    context=json.loads(base64.b64decode(args.context,validate=True).decode('utf-8'))
    plan=make_plan(args.action,context)
    doc=description(plan)
    if args.plan_json:
        print(json.dumps(doc,ensure_ascii=True));return 0
    if not args.apply_token or args.apply_token!=doc['token']:
        raise core.Failure('Installation plan changed or approval token missing; review again')
    engine.apply(plan)
    print('Blastoff '+args.action+' complete; user data preserved.')
    return 0

if __name__=='__main__':
    try: raise SystemExit(run(sys.argv[1:]))
    except (core.Failure,OSError,ValueError,KeyError,TypeError) as error:
        print('blastoff lifecycle: '+str(error),file=sys.stderr)
        raise SystemExit(error.code if isinstance(error,core.Failure) else 1)

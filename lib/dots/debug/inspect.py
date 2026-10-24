"""Diagnostics read data and metadata; they never source a cache or run a route."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
from command_metadata import roots, resolve, candidates, BUILTINS, catalog
from profiles import resolve as profile
from profile_views import validate, identities


def path_report(root, command=None):
    active=profile(root)
    owners={str(Path(r['root'])/part):'profile:'+r['id'] for r in active['layers'] for part in r.get('path',['bin','scripts'])}
    owners.update({str(root/p):'checkout' for p in ('bin','scripts')})
    seen=set();rows=[];winner=None
    for index,text in enumerate(os.environ.get('PATH','').split(os.pathsep),1):
        path=Path(text or '.')
        candidate=None
        if command:
            candidate=shutil.which(command,path=str(path))
            if candidate and winner is None: winner=candidate
        key=os.path.normcase(os.path.abspath(path))
        rows.append(dict(order=index,path=str(path.absolute()),source=owners.get(text,'inherited'),exists=path.is_dir(),duplicate=key in seen,
                         command=candidate,selected=bool(candidate and candidate==winner and not any(r['selected'] for r in rows))))
        seen.add(key)
    return dict(version=1,command=command,selected=winner,rows=rows)


def command_report(root, words):
    if not words: raise ValueError('provide a Dots route after --')
    if words[0] in BUILTINS:
        return dict(version=1,route=words[0],selected='builtin',forwarded_count=len(words)-1,candidates=[])
    directories=roots(root)
    stem,path,count=resolve(directories,words)
    return dict(version=1,route=stem.replace('-',' '),selected=str(path) if path else None,forwarded_count=len(words)-count,
                candidates=[str(p) for d in directories for p in candidates(d,stem)] if stem else [], roots=list(map(str,directories)))


def cache_report(root, shell=None):
    base=Path(os.environ.get('XDG_CACHE_HOME') or (Path(os.environ['LOCALAPPDATA'])/'cache' if os.name=='nt' and os.environ.get('LOCALAPPDATA') else Path.home()/'.cache'))/'dots/startup'
    rows=[]
    if base.is_dir():
        for pointer in sorted(base.glob('*/current')):
            if shell and not pointer.parent.name.startswith(shell+'-'): continue
            row=dict(path=str(pointer.parent),status='invalid',reasons=[])
            try:
                if pointer.is_symlink() or pointer.stat().st_size>128: raise ValueError('unsafe generation pointer')
                generation=pointer.read_text().strip()
                if not re.fullmatch('[a-f0-9]{24}',generation): raise ValueError('invalid generation identifier')
                manifest=pointer.parent/generation/'manifest.json'
                if not manifest.resolve().is_relative_to(base.resolve()): raise ValueError('generation escapes cache')
                if manifest.is_symlink() or manifest.stat().st_size>2**20: raise ValueError('unsafe manifest')
                data=json.loads(manifest.read_text());row.update(generation=generation,shell=data['shell'],inputs=len(data['inputs']))
                if data['root']!=str(root): row['reasons'].append('checkout identity changed')
                if not data.get('metadata'): row['reasons'].append('older generation lacks comparable input metadata')
                for item in data.get('metadata',[]):
                    try: stat=Path(item['path']).stat()
                    except OSError: row['reasons'].append('missing input: '+item['path']);continue
                    if any(getattr(stat,'st_'+key)!=item[key] for key in ('size','mtime_ns','ctime_ns')): row['reasons'].append('changed input: '+item['path'])
                for name in ('guard','bundle'):
                    if not (manifest.parent/name).is_file(): row['reasons'].append('missing '+name)
                row['status']='stale' if row['reasons'] else 'valid'
                row['scope']='input metadata; native shell version is checked by its loader'
            except (OSError,ValueError,KeyError,TypeError) as error: row['reasons'].append(str(error))
            rows.append(row)
        for native in ('fish','ps1'):
            if shell and shell != ('powershell' if native=='ps1' else native): continue
            file=base/('environment.'+native)
            if file.is_file():
                row=dict(path=str(file),status='unverified',reasons=['native adapter has no input manifest'])
                meta=file.with_suffix(file.suffix+'.json')
                try:
                    if meta.is_symlink() or file.is_symlink(): raise ValueError('native cache must not be a symlink')
                    if meta.is_file() and meta.stat().st_size<=2**20:
                        data=json.loads(meta.read_text()); reasons=[]
                        if data['root']!=str(root): reasons.append('checkout identity changed')
                        if file.stat().st_size>2**20 or hashlib.sha256(file.read_bytes()).hexdigest()!=data['digest']: reasons.append('adapter content changed')
                        for item in data['inputs']:
                            try: st=Path(item['path']).stat()
                            except OSError: reasons.append('missing input: '+item['path']);continue
                            if st.st_mtime_ns!=item['mtime_ns'] or st.st_size!=item['size']: reasons.append('changed input: '+item['path'])
                        row.update(status='stale' if reasons else 'valid',reasons=reasons)
                except (OSError,ValueError,KeyError,TypeError) as error: row.update(status='invalid',reasons=[str(error)])
                rows.append(row)
    return dict(version=1,path=str(base),rows=rows)


def health(root, only=None):
    checks=[]
    def run(name, action):
        if only and name!=only: return
        try:
            detail=action();checks.append(dict(name=name,status='passed',detail=detail))
        except (ValueError,OSError,KeyError,TypeError) as error: checks.append(dict(name=name,status='failed',detail=str(error)))
    run('platform',lambda: profile(root)['facts']['platform'])
    def profiles():
        rows=validate(root,identities(root)); failures=[r['profile']+': '+r['detail'] for r in rows if r['status']=='failed']
        if failures: raise ValueError('; '.join(failures))
        return str(len(rows))+' definitions valid'
    run('profiles',profiles)
    run('commands',lambda: str(len(catalog(roots(root))))+' routes valid')
    def startup():
        missing=[p for p in ('lib/dots/shell/startup.bash','shells/zsh/zshrc','shells/bash/.bashrc','shells/powershell/profile.ps1') if not (root/p).is_file()]
        if missing: raise ValueError('missing entrypoints: '+', '.join(missing))
        if os.name!='nt' and not shutil.which('stat'): raise ValueError('native startup requires stat')
        rows=cache_report(root)['rows']
        if any(r['status']=='invalid' for r in rows): raise ValueError('invalid startup cache; inspect dots debug cache')
        bad=[r for r in rows if r['status'] in ('invalid','stale')]
        return 'Entrypoints available; '+str(len(bad))+' caches need normal startup preparation; '+str(len(rows))+' observed'
    run('startup',startup)
    def environment():
        from environment import inspect
        rows=inspect(root)['values']
        return str(len(rows))+' registered values; '+str(sum(r['inherited']=='different' for r in rows.values()))+' inherited differences (values omitted)'
    run('environment',environment)
    return dict(version=1,checks=checks)

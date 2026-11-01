"""Explicit, journaled key migration; compatible readers never invoke this."""
import json
import re
from pathlib import Path

from config_keys import canonical, document, public_styles
from style_config import read, encode
from files.transactions import Store, digest, parents_safe
from files.file_platform import state_root


def style_text(path, group):
    before=read(path)
    after=public_styles(group,before,strict=True)
    if before==after:return path.read_text()
    # Keep comments and per-field spelling while combining renamed tables.
    tables={};section='';preamble=[];seen=set()
    for line in path.read_text().splitlines():
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
    return text


class KeyPlan:
    def __init__(self,root,selected,*,all_profiles=False):
        from profiles import available,definition,directory
        self.root=Path(root);self.guards={};self.operations=[];self.items=[]
        identities=[r['id'] for r in available(root)] if all_profiles else [selected['current']]
        paths=[self.root/'default/config.json',self.root/'default/colors.toml',self.root/'default/icons.toml'] if all_profiles else []
        for identity in identities:
            layer=definition(root,identity)
            profile_root=directory(self.root,identity)
            paths.extend(profile_root/name for name in ('profile.json','colors.toml','icons.toml'))
        # Shared inputs and inherited profiles are guarded even for a one-profile migration.
        paths=list(dict.fromkeys(paths))
        guard_paths=paths+[self.root/'default'/name for name in ('config.json','colors.toml','icons.toml')]
        guard_paths += [Path(layer['root'])/name for layer in selected['layers'] for name in ('profile.json','colors.toml','icons.toml')]
        for path in guard_paths:
            parents_safe(path);self.guards[str(path)]=digest(path)
        for path in paths:
            if not path.exists():continue
            if path.is_symlink() or not path.is_file() or path.stat().st_size>4*1024*1024:
                raise ValueError('key migration requires a bounded regular file: '+str(path))
            before=path.read_text()
            if path.suffix=='.json':
                data=json.loads(before);changed=document(data,strict=True)
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
        replacements={Path(op['path']):(json.loads(op['text']) if op['path'].endswith('.json') else flatten(tomllib.loads(op['text']))) for op in self.operations}
        for identity in identities:
            scope=context(self.root,identity)
            before=Styles(self.root,scope)
            palette=dict(colors=before.palette,palette=before.native_palette)
            after=Styles(self.root,scope,replacements=replacements,palette=palette)
            old=Controls(self.root,scope).values
            new=Controls(self.root,scope,replacements=replacements).values
            if old!=new or snapshot(palette,styles=before,controls=old)['apps']!=snapshot(palette,styles=after,controls=new)['apps']:
                raise ValueError('key migration would change effective configuration for '+identity)

    def apply(self):
        return Store(state_root()).apply('config-migrate-keys',self.operations,self.guards,retain=True,catalogs=self.catalogs)

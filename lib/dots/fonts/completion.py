"""Trusted on-demand font completion; no network, subprocesses or state writes."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fonts.commands import COMMANDS,OPTIONS,COMMON


def complete(words):
    current=words[-1] if words else '';previous=words[:-1]
    action='';pending=None;values={};positionals=[];literal=False
    for word in previous:
        if pending:values[pending]=word;pending=None
        elif not literal and word=='--':literal=True
        elif not literal and word.startswith('--'):
            name,equal,value=word[2:].partition('=')
            if name not in OPTIONS:return
            if OPTIONS[name][0]=='flag':values[name]=True
            elif equal:values[name]=value
            else:pending=name
        elif not action and word in COMMANDS and word:action=word
        else:positionals.append(word)
    lead=''
    if current.startswith('--') and '=' in current:
        pending,_,current=current[2:].partition('=');lead='--'+pending+'='
    def emit(value,description=''):
        from resources import clean
        if value.startswith(current) and not any(c in value for c in '\t\r\n\0'):
            print('candidate\t'+lead+value+'\t'+clean(description))
    names=(*COMMON,*COMMANDS[action][2])
    if pending:
        if pending not in names:return
        kind=OPTIONS[pending][0]
        if pending in ('directory','from'):
            from fonts.destinations import Destinations
            if pending=='from':emit('personal','Personal library')
            for name,path in Destinations().names.items():emit(name,path)
            return
        if kind.startswith('choice:'):
            for value in kind[7:].split(','):emit(value)
            return
        if kind in ('file','directory'):print(kind+'\t'+lead+'\t');return
        if pending not in ('version','face'):return
    elif current.startswith('-') and not literal:
        for name in names:emit('--'+name,OPTIONS[name][1])
        emit('--help','Show help');return
    elif not action:
        for name,row in COMMANDS.items():
            if name:emit(name,row[0])
        return
    elif COMMANDS[action][1]=='path':print('file\t\t');return
    elif action=='restore':
        from fonts.defaults import rows
        from fonts.model import Library
        for row in rows(Library())['items']:emit(row['selection'])
        return
    elif action in ('copy','migrate'):return # Installed IDs require explicit inventory, never fc-list during completion.
    elif (positionals and COMMANDS[action][1]!='fonts') or COMMANDS[action][1] not in ('font','optional-font','fonts'):return
    from fonts.model import Library
    source=values.get('from') if action=='install' else values.get('directory')
    library=Library(directory=None if source=='personal' else source)
    workspace=None
    if action in ('install','set') and not source:
        from fonts.workspace import Workspace
        workspace=Workspace(library,None)
    if pending:
        if not positionals:return
        if workspace:identity=workspace.resolve(positionals[0],catalog=True)
        elif library.directory:
            from fonts.directories import resolve
            identity=resolve(library,positionals[0])
        else:identity=library.resolve(positionals[0],available=True)
        if pending=='version':
            saved=library.families.get(identity,{}).get('versions',{})
            if workspace:
                saved={v:r for plan in workspace.all_stores() for v,r in plan.document['families'].get(identity,{}).get('versions',{}).items()}
            available=library.catalog['families'].get(identity,{}).get('versions',{})
            if library.directory and action=='install':saved=dict(library.collection['families'].get(identity,{}).get('versions',{}),**saved)
            for version in dict(available,**saved):emit(version,('uninstalled' if saved[version].get('available') is False else 'stored' if library.directory else 'downloaded') if version in saved else 'cataloged')
        else:
            if workspace:
                plan,version=workspace.obtain(identity,values.get('version'),dry_run=True)
                if plan is None:return
                record=plan.document['families'][identity]['versions'][version]
            else:_,record=library.version(identity,values.get('version'))
            for font in record['fonts']:emit(font['file'],font['family']+' · '+font['style'])
    else:
        rows={r['id']:r for r in library.rows(available=action in ('download','show','versions','set','install') or bool(library.directory and action=='update'))}
        if workspace:
            from fonts.menus import downloaded_rows
            rows.update({r['id']:r for r in downloaded_rows(library)})
        if library.directory and action in ('install','download'):rows=dict(library.collection['families'],**rows)
        for identity,row in sorted(rows.items()):emit(identity,row.get('name',''))


if __name__=='__main__':
    try:complete(sys.argv[1:])
    except (ValueError,OSError,KeyError):pass

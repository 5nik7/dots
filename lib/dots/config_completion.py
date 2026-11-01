"""Shared, read-only Config branches and typed value candidates."""
import json
from pathlib import Path
import re
import sys


def prefixes(key):
    from config_values import parts,name
    if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*(?:\.[a-z][a-z0-9_]*)*',key):
        path=key.split('.')
        return ['.'.join(path[:i]) for i in range(1,len(path)+1)]
    try:
        path=parts(key)
        return [name(path[:i]) for i in range(1,len(path)+1)]
    except ValueError:
        # Qualified file identities and environment names are literal leaves.
        group,sep,rest=key.partition('.')
        return [group,key] if sep else [key]


def branches(keys, current=''):
    """Return immediate continuations without splitting bracket-quoted keys."""
    result={}
    chains={key:prefixes(key) for key in keys if key.startswith(current)}
    parents={prefix for chain in chains.values() for prefix in chain[:-1]}
    for key,chain in chains.items():
        if not key.startswith(current):continue
        for index,prefix in enumerate(chain):
            if len(prefix)<len(current):continue
            branch=prefix in parents
            suffix=('[' if key[len(prefix):].startswith('[') else '.') if branch else ''
            value=prefix+suffix
            if value.startswith(current):result[value]=branch
            break
    return sorted(result.items())


def key_candidates(root,current='',profile=None):
    from profile_config import keys
    from config_keys import canonical,description,MOVES
    # A consumed suffix requests the next branch. Selected branches retain a
    # trailing dot/bracket, so another Tab continues drilling down.
    branch_mode=current.endswith(('..','.','['))
    if current.endswith('..'):
        current=current[:-2]
        if current and not current.endswith(('.','[')):current+='.'
    if not branch_mode:
        query=canonical(current).casefold()
        available=set(keys(root,profile))
        parents={prefix for key in available for prefix in prefixes(key)[:-1]}
        return [(key,description(key)) for key in sorted(available-parents)
                if all(word in key.casefold() for word in query.split())
                and not (key.startswith('settings.DOTS_') and key[9:] in available)]
    current=canonical(current)
    result=[(key,'Branch' if branch else description(key)) for key,branch in branches(keys(root,profile),current)]
    if not result and current:
        result=sorted({(new,description(new)) for old,new in MOVES if old.startswith(current)})
    return result


def glyph_candidates(query=''):
    from fonts.model import Library
    from fonts.browser import icon_version
    library=Library()
    version=icon_version(library,None)
    rows=library.catalog.get('glyphs',{}).get(version,[])
    for row in rows:
        label=' '.join(str(row.get(k,'')) for k in ('name','codepoint','collection'))
        glyph=row.get('glyph','')
        if glyph and all(word in (glyph+' '+label).casefold() for word in query.casefold().split()):
            yield glyph,label


def color_candidates(root,profile=None):
    from style_config import Styles,ANSI,ALIASES
    from style_catalog import known_keys,supported
    from config_keys import canonical
    from profile_config import context
    style=Styles(root,context(root,profile))
    result={name:style.color(name) for name in (*ANSI,*ALIASES,'default','reset')}
    for name,color in style.native_palette.items():
        if isinstance(color,str) and color.startswith('#'):result['palette.'+name]=color
    for key in known_keys('colors',style):
        if canonical('colors.'+key).startswith('colors.apps.') or not key.endswith(('.fg','.bg')) or not supported('colors',key):continue
        value=style.resolve('colors',key)['value']
        if isinstance(value,str):result[canonical('colors.'+key)]=style.color(value)
    return sorted((name,str(value)) for name,value in result.items())


def value_spec(root,key):
    """The same finite choices used by details, editors and completion."""
    from config_keys import internal
    from config_values import constraints,read_defaults
    from profile_config import schema
    key=internal(key)
    setting=key.removeprefix('settings.')
    if setting in schema():
        kind=schema()[setting][0]
        choices={'bool':['0','1'],'style':['auto','always','never'],
                 'suggestions':['deja','autosuggestions','none']}.get(kind,[])
        return dict(type='string',choices=choices)
    if key=='settings.files.backup':return dict(type='boolean',choices=[True,False])
    if key.startswith(('colors.','icons.')):
        from style_catalog import constraints as visual_constraints
        return visual_constraints(*key.split('.',1))
    if key.startswith('apps.pkgs.'):
        from config_pkgs import constraints as native_constraints
        return native_constraints(key)
    if key.startswith('apps.codex.'):
        if key.startswith('apps.codex.vibrate.'):
            from codex_vibration import constraints as native_constraints
        else:
            from codex_toast import constraints as native_constraints
        return native_constraints(key)
    if key.startswith('apps.wttr.'):
        # Import only the data validator; never the native editor/transaction path.
        from wttr.configuration import constraints as weather_constraints
        return weather_constraints(key)
    return constraints(read_defaults(root),key)


def value_candidates(root,key,current='',profile=None):
    from config_keys import internal
    key=internal(key)
    try:spec=value_spec(root,key)
    except (OSError,ValueError):spec={}
    color=spec.get('type')=='color'
    icon=key.startswith('icons.') or key.startswith('apps.nvim.icons.') or key.startswith(('apps.wttr.icons[','apps.wttr.icons.','apps.wttr.night_icons['))
    if color:
        rows=color_candidates(root,profile)
        if key.startswith('apps.codex.toast.'):
            from codex_toast import validate
            accepted=[]
            for value,label in rows:
                try:validate(key.rsplit('.',1)[1],value)
                except ValueError:continue
                accepted.append((value,label))
            rows=accepted
        if key.startswith('apps.wttr.'):
            from wttr.styling import color as validate_color
            accepted=[]
            for value,label in rows:
                try:validate_color(value)
                except ValueError:continue
                accepted.append((value,label))
            rows=accepted
    elif icon:
        try:rows=list(glyph_candidates(current))
        except (OSError,ValueError,KeyError):rows=[]
        return rows
    else:rows=[(value if isinstance(value,str) else json.dumps(value),'')
               for value in [*spec.get('choices',[]),*spec.get('examples',[])]]
    return [(v,d) for v,d in rows if v.startswith(current)]


def preview(root, word, words=()):
    """Safe fzf-tab preview: cached data only, without file-command fallbacks."""
    from config_keys import description
    from resources import clean
    value=word.rstrip('.')
    keys=key_candidates(root,word)
    if keys:
        print(clean(description(value)))
        for key,label in keys[:40]:print(clean(key+' · '+label))
        return
    colors=dict(color_candidates(root))
    if value in colors:
        print(clean(value+' · '+colors[value]))
        return
    for glyph,label in glyph_candidates():
        if glyph==value:
            print(clean(glyph+'  '+label))
            return
    print(clean(value))


if __name__=='__main__':
    from profile_config import checkout
    try:
        if sys.argv[1:2]==['preview']:
            preview(checkout(),sys.argv[2],sys.argv[3:])
        else:
            kind,key,current,profile=(sys.argv[1:]+['']*4)[:4]
            rows=key_candidates(checkout(),current,profile or None) if kind=='key' else value_candidates(checkout(),key,current,profile or None)
            from resources import clean
            for value,description in rows:
                if not any(c in value for c in '\t\r\n\0'):print('candidate\t'+value+'\t'+clean(description))
    except (OSError,ValueError,KeyError):pass

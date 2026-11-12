"""Typed literal application/formatting preferences; no publication on reads."""
import copy
from functools import lru_cache
import json
import os
from pathlib import Path
import re

IDENTIFIER = re.compile(r'[A-Za-z_][A-Za-z0-9_-]*')
MISSING = object()
GROUPS = ('formatting', 'apps')
ENUMS = {'list_type': ('tree', 'regular'), 'indent_style': ('spaces', 'tabs'),
         'alignment': ('left', 'right', 'center'), 'position': ('top', 'bottom'),
         'signcolumn': ('auto', 'yes', 'no', 'number')}
DYNAMIC = {('apps','fzf','bindings'): 'string', ('apps','nvim','highlights'): 'highlights',
           ('apps','nvim','icons'): 'icons', ('apps','nvim','icon_styles'): 'highlights',
           ('formatting','apps','menu','entries'): 'entries'}
STYLE_FIELDS = {'fg','bg','sp','bold','italic','underline','undercurl','strikethrough','reverse','blend','link'}
MENU_FIELDS={'fg','bg','bold','dim','italic','underline','strikethrough','reverse'}
NULL_TYPES = {'number':False,'relativenumber':False,'expandtab':False,'list':False,
              'padding_left':0,'padding_right':0,'main_row':0,'termux_row':0,
              'shiftwidth':0,'tabstop':0,'softtabstop':0,'scrolloff':0,'sidescrolloff':0,
              'mouse':'','signcolumn':'','listchars':'','virtual_text':False,'signs':False,
              'underline':False,'update_in_insert':False,'severity_sort':False}


def parts(key):
    """Dot identifiers and JSON-quoted bracket keys; never evaluate input."""
    if not isinstance(key, str) or not key: raise ValueError('empty configuration key')
    out=[]; pos=0
    while pos < len(key):
        if key[pos] == '[' and out:
            try: value, end = json.JSONDecoder().raw_decode(key[pos+1:])
            except ValueError: raise ValueError('invalid quoted configuration key') from None
            pos += end+1
            if not isinstance(value,str) or not value or pos >= len(key) or key[pos] != ']': raise ValueError('invalid quoted configuration key')
            pos += 1
        else:
            match=IDENTIFIER.match(key,pos)
            if not match: raise ValueError('invalid configuration key')
            value=match.group();pos=match.end()
        if any(ord(c)<32 or ord(c)==127 for c in value): raise ValueError('invalid configuration key')
        out.append(value)
        if pos == len(key): break
        if key[pos] == '.':
            pos += 1
            if pos == len(key) or key[pos] == '[': raise ValueError('invalid configuration key')
        elif key[pos] != '[': raise ValueError('invalid configuration key')
    return tuple(out)


def name(path):
    result=''
    for part in path:
        result += ('.' if result else '')+part if IDENTIFIER.fullmatch(part) else '['+json.dumps(part,ensure_ascii=False)+']'
    return result


def lookup(doc, path, default=None):
    for part in path:
        if not isinstance(doc,dict) or part not in doc:return default
        doc=doc[part]
    return doc


def merge(base, overlay):
    result=copy.deepcopy(base)
    for key,value in overlay.items():
        if value is None:continue
        result[key]=merge(result.get(key,{}) if isinstance(result.get(key),dict) else {},value) if isinstance(value,dict) else copy.deepcopy(value)
    return result


def assign(doc,path,value,unset=False):
    node=doc
    for part in path[:-1]:
        if part not in node:node[part]={}
        if not isinstance(node[part],dict):raise ValueError('configuration path overlaps a scalar')
        node=node[part]
    if unset or value is None:node.pop(path[-1],None)
    else:node[path[-1]]=value


def read_defaults(root):
    from preference_files import combined
    data=combined(Path(root)/'default')
    return {g:data.get(g,{}) for g in GROUPS}


def dynamic(path):
    return next(((prefix,kind) for prefix,kind in DYNAMIC.items() if path[:len(prefix)]==prefix), ((),None))


def recognized(defaults,path):
    if path[:3]==('apps','nvim','icon_styles') and len(path)>3 and path[3] not in ('diagnostics.Error','diagnostics.Warn','diagnostics.Info','diagnostics.Hint'):return False
    if lookup(defaults,path,MISSING) is not MISSING:return True
    prefix,kind=dynamic(path)
    if not kind or len(path)<=len(prefix):return False
    rest=path[len(prefix):]
    if kind=='string':return len(rest)==1
    if kind=='icons':return len(rest)<=6
    if kind=='highlights':return len(rest)==1 or len(rest)==2 and rest[1] in STYLE_FIELDS
    if kind=='entries':return len(rest)==1 or len(rest)==2 and rest[1] in ('icon','label','description','shortcut','state') or len(rest)==3 and rest[1] in ('icon','label','description','shortcut','state') and rest[2] in MENU_FIELDS
    return False


def style(value):
    if not isinstance(value,dict) or set(value)-STYLE_FIELDS:raise ValueError('invalid native style fields')
    for field,v in value.items():
        if v is None:continue
        if field in ('fg','bg','sp'):
            from style_config import validate
            if v != 'NONE':validate('colors',{'ui.foreground.'+('bg' if field=='bg' else 'fg'):v})
        elif field=='link':
            if not isinstance(v,str) or not re.fullmatch(r'[@A-Za-z_][\w.@:-]*',v):raise ValueError('invalid highlight link')
        elif field=='blend':
            if type(v) is not int or not 0<=v<=100:raise ValueError('blend must be 0..100')
        elif type(v) is not bool:raise ValueError('style attributes require booleans')


def validate_value(defaults,path,value):
    if not recognized(defaults,path):raise ValueError('unknown configuration key: '+name(path))
    if value is None:return
    if path[:2]==('apps','clipboard'):
        bounds={'max_entries':(1,10000),'max_age_days':(1,3650),'max_entry_bytes':(1,1048576),
                'poll_seconds':(1,10),'preview_lines':(1,40),'list_limit':(1,10000)}
        if len(path)==3 and path[-1] in bounds:
            low,high=bounds[path[-1]]
            if type(value) is not int or not low<=value<=high:raise ValueError('clipboard '+path[-1]+' requires integer '+str(low)+'..'+str(high))
            return
        if path[-1]=='exclude_patterns':
            if not isinstance(value,list) or len(value)>100 or any(not isinstance(v,str) or len(v)>512 or '\0' in v for v in value):raise ValueError('clipboard exclusions require up to 100 bounded glob patterns')
            return
    if path[:2]==('apps','tmux'):
        bounds={'location_refresh_seconds':(3600,86400),'sun_times_max_stale_seconds':(86400,604800)}
        if path[2:3]==('clock',) and path[-1] in bounds:
            low,high=bounds[path[-1]]
            if type(value) is not int or not low<=value<=high:raise ValueError('clock '+path[-1]+' requires integer '+str(low)+'..'+str(high))
            return
        choices={('clock','icon_mode'):('none','fixed','daylight'),('session','name_source'):('workspace','session','repository')}
        if path[2:] in choices:
            if value not in choices[path[2:]]:raise ValueError('invalid tmux choice: '+name(path))
            return
        if path[2:3]==('battery',) and path[-1] in ('critical','low'):
            if type(value) is not int or not 0<=value<=100:raise ValueError('battery threshold requires integer 0..100')
            return
    if path in (('apps','wiki','list_details'), ('apps','wiki','reader')):
        allowed = ('summary','full') if path[-1]=='list_details' else ('auto','plain')
        if not isinstance(value,str) or value not in allowed:raise ValueError('invalid wiki '+path[-1]+'; allowed: '+', '.join(allowed))
        return
    if path == ('formatting','apps','wiki','row_gap'):
        if type(value) is not int or not 0<=value<=4:raise ValueError('wiki row_gap requires an integer 0..4')
        return
    if path in (('apps','fonts','list_details'),('apps','fonts','preview','position')):
        allowed=('summary','full') if path[-1]=='list_details' else ('down','right')
        if not isinstance(value,str) or value not in allowed:raise ValueError('invalid font '+path[-1]+'; allowed: '+', '.join(allowed))
        return
    if path==('apps','fonts','preview','size'):
        if type(value) is not int or not 10<=value<=80:raise ValueError('font preview size requires an integer percentage 10..80')
        return
    if path == ('apps','cli','logo_gradient'):
        if value not in ('classic','installer'):raise ValueError('logo_gradient requires classic or installer')
        return
    if path in (('apps','bak','mode'), ('apps','bak','location')):
        allowed = ('move','copy') if path[-1] == 'mode' else ('store','adjacent')
        if value not in allowed: raise ValueError('backup '+path[-1]+' requires '+', '.join(allowed))
        return
    if path == ('apps','bak','store'):
        from pathlib import PureWindowsPath
        if (not isinstance(value,str) or not value or any(ord(c)<32 or ord(c)==127 for c in value)
                or not (value.startswith(('~/','~\\')) or Path(value).is_absolute() or PureWindowsPath(value).is_absolute())):
            raise ValueError('backup store requires an absolute or home-relative path')
        return
    if path == ('apps','setup','components'):
        from files.setup_components import COMPONENTS
        if not isinstance(value,list) or any(not isinstance(v,str) or v not in COMPONENTS for v in value) or len(set(value))!=len(value):
            raise ValueError('setup components require unique supported names')
    if path == ('apps','setup','resources'):
        if not isinstance(value,list) or any(not isinstance(v,str) or not re.fullmatch(r'[a-zA-Z0-9_-]+:[a-zA-Z0-9_.:-]+',v) for v in value) or len(set(value))!=len(value):
            raise ValueError('setup resources require unique qualified catalog IDs; [] means all applicable resources')
    if path[:2]==('formatting','apps') and len(path)==4 and path[2] in ('cli','menu') and path[-1]=='label_width':
        from row_layout import valid_width
        if not valid_width(value):raise ValueError('label_width requires integer 0..4096 or 1%..100%; zero uses spacing only')
        return
    if path[:3]==('apps','menu','popup') and len(path)==4 and path[-1] in ('width','height'):
        from menu_popup import valid_size
        if not valid_size(value):raise ValueError('popup size requires auto, fit, fill, 1%..100%, or an integer 1..10000')
        return
    if path[:3]==('apps','menu','popup') and len(path)==4 and path[-1] in ('position','border'):
        from menu_popup import POSITIONS,BORDERS
        allowed = POSITIONS if path[-1]=='position' else BORDERS
        if not isinstance(value,str) or value not in allowed:
            raise ValueError('invalid popup '+path[-1]+'; allowed: '+', '.join(allowed))
        return
    if path[:4]==('apps','menu','popup','colors') and len(path)==5:
        from fzf_config import validate_color,ATTRS
        if not isinstance(value,str) or ':' in value or value in ATTRS:raise ValueError('popup colors require one color')
        validate_color(value);return
    if path[:4]==('formatting','apps','nvim','lualine') and len(path)==6 and path[4]=='sections':
        if not isinstance(value,list) or any(v not in ('mode','root','diagnostics','filetype','path','symbols','profiler','debug','diff','progress','location') for v in value) or len(set(value))!=len(value):raise ValueError('lualine sections require unique named components')
    if path[:3]==('formatting','apps','tmux') and len(path)==4:
        if path[-1] in ('main_row','termux_row') and (type(value) is not int or value not in (0,1)):raise ValueError('tmux rows must be 0 or 1')
        if path[-1]=='rows' and (type(value) is not int or value not in (0,1,2)):raise ValueError('tmux rows must be auto (0), 1 or 2')
        if path[-1] in ('main_left','main_right','termux_left','termux_right'):
            if not isinstance(value,list) or any(v not in ('session','windows','git','indicators','clock','tabs','battery') for v in value) or len(set(value))!=len(value):raise ValueError('tmux sections require unique named components')
    if path[:3]==('apps','fzf','colors') and len(path)==4:
        from fzf_config import validate_color
        if path[-1]=='nth':
            from fzf_config import ATTRS
            if not isinstance(value,str) or any(token not in ATTRS for token in value.split(':')):raise ValueError('FZF nth accepts attributes only')
        validate_color(value);return
    prefix,kind=dynamic(path)
    if isinstance(value,dict):
        if not isinstance(lookup(defaults,path,{}),dict) and kind not in ('highlights','entries','icons'):
            raise ValueError('invalid object for '+name(path))
        if kind=='highlights' and len(path)==len(prefix)+1:
            if not re.fullmatch(r'[@A-Za-z_][\w.@:-]*',path[-1]):raise ValueError('invalid native highlight key')
            style(value);return
        if kind=='entries' and len(path)==len(prefix)+2:
            if set(value)-{'fg','bg','bold','dim','italic','underline','strikethrough','reverse'}:raise ValueError('unsupported popup style field')
            for field,v in value.items():
                if v is not None:
                    from style_config import validate
                    validate('colors',{'ui.foreground.'+field:v})
            return
        for key,v in value.items():
            if not isinstance(key,str) or not key or any(ord(c)<32 or ord(c)==127 for c in key):raise ValueError('invalid configuration map key')
            validate_value(defaults,(*path,key),v)
        return
    if kind=='highlights' and len(path)==len(prefix)+2:style({path[-1]:value});return
    if kind=='entries' and len(path)==len(prefix)+3:
        from style_config import validate
        validate('colors',{'ui.foreground.'+path[-1]:value});return
    default=lookup(defaults,path,MISSING)
    if default is MISSING and kind in ('icons','string'):default=''
    if default is None:default=NULL_TYPES.get(path[-1],'')
    if type(value) is not type(default):raise ValueError('invalid type for '+name(path))
    if isinstance(value,str) and (any(ord(c)<32 or ord(c)==127 for c in value) or len(value)>32768):raise ValueError('invalid literal configuration value')
    if path[-1] in ENUMS and value not in ENUMS[path[-1]]:raise ValueError('invalid '+path[-1]+'; allowed: '+', '.join(ENUMS[path[-1]]))
    if type(value) is int and not 0<=value<=4096:raise ValueError('formatting integer must be 0..4096')
    if isinstance(value,list) and (len(value)>256 or any(not isinstance(v,str) or any(ord(c)<32 or ord(c)==127 for c in v) or len(v)>32768 for v in value)):raise ValueError('option lists require bounded literal strings')
    if kind=='icons' and (not isinstance(value,str) or len(value)>64 or any(ord(c)<32 for c in value)):raise ValueError('icons require short printable strings')


def validate_groups(root,data,defaults=None):
    from config_keys import document
    data=document(data,public=False)
    if data.get('colors'):raise ValueError('profile colors support only popup and menu entries; use colors.toml for visual styles')
    defaults=read_defaults(root) if defaults is None else defaults
    for group in GROUPS:
        values=data.get(group,{})
        if not isinstance(values,dict):raise ValueError(group+' must be an object')
        validate_value(defaults,(group,),values)


def constraints(defaults, key):
    from config_keys import internal
    key=internal(key)
    choices={'apps.tmux.clock.icon_mode':['none','fixed','daylight'],'apps.tmux.session.name_source':['workspace','session','repository']}
    if key in choices:return dict(type='string',choices=choices[key])
    if key in ('apps.tmux.clock.location_refresh_seconds','apps.tmux.clock.sun_times_max_stale_seconds'):
        bounds=(3600,86400) if key.endswith('location_refresh_seconds') else (86400,604800)
        return dict(type='integer',syntax='Seconds '+str(bounds[0])+'..'+str(bounds[1]))
    if key in ('apps.tmux.battery.critical','apps.tmux.battery.low'):return dict(type='integer',syntax='Integer 0..100; null retains provider threshold')
    """Describe validated typed controls for explain, editing and completion."""
    path = parts(key)
    if not recognized(defaults, path): return {}
    default = lookup(defaults, path)
    if path in (('apps','wiki','list_details'), ('apps','wiki','reader')):
        return dict(type='string',choices=['summary','full'] if path[-1]=='list_details' else ['auto','plain'])
    if path == ('formatting','apps','wiki','row_gap'):
        return dict(type='integer',examples=[0,1,2],syntax='Integer 0..4 blank lines between Wiki records')
    if path[:2]==('apps','clipboard'):
        bounds={'max_entries':(1,10000),'max_age_days':(1,3650),'max_entry_bytes':(1,1048576),
                'poll_seconds':(1,10),'preview_lines':(1,40),'list_limit':(1,10000)}
        if path[-1] in bounds:
            low,high=bounds[path[-1]]
            return dict(type='integer',syntax='Integer '+str(low)+'..'+str(high),examples=[lookup(defaults,path)])
        if path[-1]=='exclude_patterns':return dict(type='array',syntax='Up to 100 case-sensitive text glob patterns',examples=[[],['*password*']])
    if path in (('apps','fonts','list_details'),('apps','fonts','preview','position')):
        return dict(type='string',choices=['summary','full'] if path[-1]=='list_details' else ['down','right'])
    if path==('apps','fonts','preview','size'):
        return dict(type='integer',examples=[25,33,50],syntax='Integer 10..80 percent of the picker height or width')
    if path == ('apps','cli','logo_gradient'):
        return dict(type='string', choices=['classic','installer'], syntax='Classic vertical blue/cyan or installer horizontal hint/info/accent')
    if path in (('apps','bak','mode'), ('apps','bak','location')):
        return dict(type='string', choices=['move','copy'] if path[-1]=='mode' else ['store','adjacent'])
    if path == ('apps','bak','store'):
        return dict(type='string', syntax='Absolute or home-relative backup directory; applied on the next invocation')
    if path == ('apps','setup','components'):
        from files.setup_components import COMPONENTS
        return dict(type='array', examples=[list(COMPONENTS[:6]), ['core']], syntax='Unique component names: '+', '.join(COMPONENTS))
    if path == ('apps','setup','resources'):
        return dict(type='array', examples=[[], ['dots:git']], syntax='Qualified catalog IDs; [] selects all applicable enabled files')
    if path[:2]==('formatting','apps') and len(path)==4 and path[2] in ('cli','menu') and path[-1]=='label_width':
        return dict(type='column-width', examples=['25%','40%','50%',16,24,0],
                    syntax='Integer 0..4096 cells or 1%..100% of the terminal/popup width; 0 uses label_gap only')
    prefix, kind = dynamic(path)
    if kind in ('highlights', 'entries'):
        field_depth = len(prefix) + (2 if kind=='highlights' else 3)
        if len(path) < field_depth: return dict(type='object')
        if path[-1] in ('fg', 'bg', 'sp'):
            return dict(type='color', examples=['accent', '#89b4fa', 'palette.blue', 'colors.daylight.day.fg'], syntax='Semantic role, palette.NAME, global colors.ROLE.fg/bg reference or #RRGGBB'+('; NONE is also accepted' if kind=='highlights' else ''))
        if path[-1] == 'link': return dict(type='string')
        if path[-1] == 'blend': return dict(type='integer', syntax='Integer 0..100')
        return dict(type='boolean', choices=[True,False])
    if kind in ('icons', 'string'): return dict(type='string')
    if path[:3] == ('apps', 'menu', 'popup') and len(path) == 4:
        from menu_popup import POSITIONS, BORDERS, SIZES, SIZE_PRESETS
        if path[-1] in ('position', 'border'):
            return dict(type='string', choices=list(POSITIONS if path[-1]=='position' else BORDERS))
        if path[-1] in ('width', 'height'):
            return dict(type='size', choices=list(SIZES), examples=[*SIZE_PRESETS, 80 if path[-1]=='width' else 24],
                        syntax='auto: controller layout; fit: known content (90% cap); fill: full client; 1%..100%; integer 1..10000 '+('columns' if path[-1]=='width' else 'rows'))
    if path[:4] == ('apps', 'menu', 'popup', 'colors') and len(path) == 5:
        return dict(type='color', examples=['accent', '#89b4fa', 'default', 'palette.blue', 'colors.daylight.day.fg'], syntax='Semantic role, palette.NAME, global colors.ROLE.fg/bg reference, #RRGGBB, or quoted terminal color index 0..255')
    if path[:3] == ('formatting', 'apps', 'tmux') and path[-1] in ('main_row', 'termux_row', 'rows'):
        return dict(type='integer', choices=[0, 1, 2] if path[-1]=='rows' else [0, 1])
    if path[-1] in ENUMS and lookup(defaults,path,MISSING) is not MISSING:
        return dict(type='string', choices=list(ENUMS[path[-1]]))
    if default is None: default = NULL_TYPES.get(path[-1], '')
    if type(default) is bool: return dict(type='boolean', choices=[True, False])
    if type(default) is int: return dict(type='integer', syntax='Integer 0..4096')
    return dict(type={str:'string', list:'array', dict:'object'}.get(type(default), 'value'))


def constraint_details(spec):
    def literal(value): return value if isinstance(value,str) else json.dumps(value)
    rows = [('Type', spec['type'])] if spec else []
    if spec.get('choices'): rows.append(('Allowed', ', '.join(literal(v) for v in spec['choices'])))
    if spec.get('syntax'): rows.append(('Format', spec['syntax']))
    if spec.get('examples'): rows.append(('Examples', ', '.join(literal(v) for v in spec['examples'])))
    return rows


def activation(key):
    from config_keys import internal
    path=parts(internal(key))
    app=path[1] if path[0]=='apps' else path[2] if path[:2]==('formatting','apps') else ''
    return (app, {'tmux':'visual publication; verified tmux servers receive owned controls',
                  'nvim':'visual publication; Neovim refreshes on focus',
                  'fzf':'visual publication; existing shells follow on the next prompt',
                  'menu':'next popup', 'fonts':'next Fonts invocation or popup',
                  'wiki':'next Wiki invocation or popup', 'clipboard':'next invocation or watcher poll'}.get(app,'next invocation'))


def candidates(root, key):
    if key.startswith('apps.codex.'):
        if key.startswith('apps.codex.vibrate.'):
            from codex_vibration import constraints as native_constraints
        else:
            from codex_toast import constraints as native_constraints
        spec=native_constraints(key)
        return [str(v) if isinstance(v,str) else json.dumps(v) for v in [*spec.get('choices', []), *spec.get('examples', [])]]
    if key.startswith('apps.pkgs.'):
        from config_pkgs import constraints as native_constraints
        spec = native_constraints(key)
        return [str(v) if isinstance(v,str) else json.dumps(v) for v in [*spec.get('choices', []), *spec.get('examples', [])]]
    try: spec = constraints(read_defaults(root), key)
    except (OSError, ValueError): return []
    return [str(v) if isinstance(v,str) else json.dumps(v) for v in [*spec.get('choices', []), *spec.get('examples', [])]]


def validate_effective(values, defaults, styles, platform):
    """Cross-field and color-reference checks shared by edits and imports."""
    for path,value in leaves(values):
        if path[:1] not in (('apps',),('formatting',)):continue
        if isinstance(value,str) and (path[:3]==('apps','fzf','colors') or constraints(defaults,name(path)).get('type')=='color'):
            for token in value.split(':'):
                if token.startswith('colors.'):styles.color(token)
    from tmux_config import validate_layout
    validate_layout(lookup(values,('formatting','apps','tmux'),{}),platform)
    battery=lookup(values,('apps','tmux','battery'),{})
    if battery.get('critical') is not None and battery.get('low') is not None and battery['critical']>=battery['low']:
        raise ValueError('critical battery threshold must be below low')


def leaves(doc,path=()):
    if isinstance(doc,dict) and doc:
        for key,value in doc.items():yield from leaves(value,(*path,key))
    else:yield path,doc


class Controls:
    def __init__(self,root=None,selected=None,*,defaults=False,replacements=None):
        from profile_config import checkout,context
        from preference_files import layers, combined
        self.root=checkout(root)
        default_document=combined(self.root/'default', replacements=replacements)
        self.defaults={g:default_document.get(g,{}) for g in GROUPS}
        self.selected=selected if selected is not None else context(self.root)
        self.paths=[];self.layers=[];self.values=copy.deepcopy(self.defaults)
        inputs=layers(self.root/'default', replacements=replacements)
        for layer in [] if defaults else self.selected['layers']:
            inputs.extend(layers(Path(layer['root']), layer, replacements))
        for path,data in inputs:
            self.paths.append(path)
            if path.parent != self.root/'default': validate_groups(self.root,data,self.defaults)
            values={g:data.get(g,{}) for g in GROUPS}
            self.layers.append((path,values));self.values=merge(self.values,values)

    def resolve(self,key):
        from config_keys import internal
        key=internal(key)
        path=parts(key)
        if not recognized(self.defaults,path):raise ValueError('unknown configuration key: '+key)
        declarations=[]
        for source,doc in self.layers:
            value=lookup(doc,path,MISSING)
            if value is not MISSING and value is not None:declarations.append(dict(value=value,source=str(source)))
        return dict(value=lookup(self.values,path),source=declarations[-1]['source'] if declarations else None,declarations=declarations)

    def keys(self):return sorted({name(path) for path,_ in leaves(self.values)}|set(GROUPS))


@lru_cache(maxsize=1)
def _current(root,profile):
    from profile_config import context
    return Controls(root,context(root,profile or None))


def current():
    from profile_config import checkout
    return _current(str(checkout()),os.environ.get('DOTS_PROFILE',''))


current.cache_clear=_current.cache_clear


def value(key,default=None):
    try:result=current().resolve(key)['value']
    except (OSError,ValueError):return default
    return default if result is None else result


if __name__ == '__main__':
    import sys
    from profile_config import checkout
    if len(sys.argv) == 3 and sys.argv[1] == '__values':
        try:
            for candidate in candidates(checkout(),sys.argv[2]): print(candidate)
        except (OSError, ValueError): sys.exit(1)
    else: sys.exit(2)

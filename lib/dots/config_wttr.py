"""Guarded edits of wttr's active native TOML; no profile inheritance."""
import copy
import json
from pathlib import Path
import re

from config_values import parts,name,lookup,MISSING,leaves
from files.file_platform import state_root,config_root
from profile_config import context

STYLE_FIELDS=('fg','bg','bold','dim','italic','underline','reverse')
KEYS={'default_location','units','language','days','timeout','ttl','max_stale','location_max_age','widget',
      'label_gap','show_location_attribution','widget_color','widget_color_format','temperature_scale',
      'icons','night_icons','icon_colors','night_icon_colors'}


def style_fields(value):
    from wttr.styling import parse_style
    style=parse_style(value)
    return dict(fg=style.foreground,bg=style.background,**{k:True for k in style.attributes})


class Native:
    def __init__(self,root,selected=None,*,guarded=False):
        from wttr.configuration import config,read
        self.root=Path(root)
        if selected and selected['current']!=context(root)['current']:
            raise ValueError('wttr uses the active native configuration; inactive-profile access is unavailable')
        self.original,self.values=config(root=root)
        self.path=self.original.resolve()
        self.text=read(self.path)
        self.declared=__import__('tomllib').loads(self.text)
        self.defaults=config(self.root/'config/wttr/config.toml',root)[1]
        self.guards={}
        if guarded:
            from files.transactions import digest
            self.guards={str(p):digest(p) for p in {self.original,self.path,config_root()/'wttr/config.toml'}}

    def recognized(self,path):
        if not path or path[0] not in KEYS:return False
        if len(path)==3 and path[0] in ('icon_colors','night_icon_colors'):
            return path[2] in STYLE_FIELDS and self.recognized(path[:2])
        if lookup(self.defaults,path,MISSING) is not MISSING:return True
        if len(path)>=2 and path[0] in ('icons','night_icons','icon_colors','night_icon_colors'):
            return (bool(re.fullmatch(r'\d{3}|unknown',path[1])) or path[0] in ('icons','icon_colors') and path[1] in ('location','sunrise','sunset','humidity','precip','wind')) and len(path)==2
        return False

    def resolve(self,key):
        path=parts(key)
        if path[:2]!=('apps','wttr') or not self.recognized(path[2:]):raise ValueError('unknown weather configuration key: '+key)
        value=lookup(self.values,path[2:])
        if len(path)==5 and path[2] in ('icon_colors','night_icon_colors'):
            value=style_fields(lookup(self.values,path[2:4])).get(path[4])
        return dict(value=value,source=str(self.original),declarations=[])

    def keys(self):
        paths={path for path,_ in leaves(self.defaults) if self.recognized(path)}|{path for path,_ in leaves(self.values) if self.recognized(path)}
        for group in ('icons','night_icons'):
            paths.update((group.replace('icons','icon_colors'),k) for k in self.values.get(group,{}))
        paths.update((*path,field) for path in list(paths) if len(path)==2 and path[0] in ('icon_colors','night_icon_colors') for field in STYLE_FIELDS)
        return sorted(name(('apps','wttr',*path)) for path in paths)


class NativePlan:
    def __init__(self,root,selected):
        from files.transactions import parents_safe
        self.native=Native(root,selected,guarded=True);self.path=self.native.path
        self.guards=self.native.guards.copy();self.items=[];self.operations=[]
        parents_safe(self.path)

    def edit(self,key,value=None,unset=False,json_value=False):
        from wttr.configuration import validate
        try:import tomlkit
        except ImportError:raise ValueError('native TOML editing requires tomlkit; see tools/requirements-config.txt') from None
        path=parts(key)[2:]
        self.native.resolve(key)
        if not unset:
            if json_value:
                try:value=json.loads(value)
                except ValueError:raise ValueError('value must be valid JSON') from None
            elif isinstance(value,str):
                try:value=json.loads(value)
                except ValueError:pass
        document=tomlkit.parse(self.native.text)
        if len(path)==3 and path[0] in ('icon_colors','night_icon_colors'):
            node=document.setdefault(path[0],tomlkit.table())
            old=node.get(path[1])
            if not isinstance(old,dict):node[path[1]]={k:v for k,v in style_fields(old).items() if v is not None}
        node=document
        for part in path[:-1]:
            if part not in node:node[part]=tomlkit.table()
            node=node[part]
        if unset or value is None:node.pop(path[-1],None)
        else:node[path[-1]]=value
        text=tomlkit.dumps(document)
        candidate=__import__('tomllib').loads(text)
        validate(copy.deepcopy(candidate))
        self.data=candidate
        self.items=[dict(action='unset' if unset or value is None else 'set',key=key)]
        self.operations=[dict(path=str(self.path),text=text)] if text!=self.native.text else []

    def apply(self,action):
        from files.transactions import Store
        return Store(state_root()).apply('config-'+action,self.operations,self.guards,retain=True,catalogs=[self.path])

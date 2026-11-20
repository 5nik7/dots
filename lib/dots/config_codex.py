"""Guarded Config bindings for Codex toast and vibration native TOML fields."""
import json
from pathlib import Path
import stat
import tomllib

from codex_toast import ACTIVATION
from config_values import parts, lookup
from profile_config import context
from codex_notifications import GROUPS, KEYS, LEGACY_KEYS, TYPES, canonical, split, values, constraints


class Native:
    def __init__(self, root, selected=None, *, guarded=False):
        self.root=Path(root)
        if selected and selected['current']!=context(root)['current']:
            raise ValueError('Codex alerts use the checkout native file; inactive-profile access is unavailable')
        self.original=self.path=self.root/'config/tmux/codex-alerts.toml'
        self.guards={}
        if guarded:
            from files.transactions import digest
            self.guards={str(self.path):digest(self.path)}
        info=self.path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_size>65536:
            raise ValueError('Codex preferences require a bounded regular file')
        self.text=self.path.read_text(encoding='utf-8')
        self.declared=tomllib.loads(self.text)
        if self.declared.get('schema')!=1 or not isinstance(self.declared.get('termux'),dict):
            raise ValueError('invalid Codex preferences')
        self.values=values(self.declared['termux'])
        if guarded and digest(self.path)!=self.guards[str(self.path)]:
            raise ValueError('Codex preferences changed while reading')

    def keys(self): return list(KEYS)

    def resolve(self, key):
        branches=('apps.codex','apps.codex.alerts',*('apps.codex.'+group for group in GROUPS),
                  *('apps.codex.alerts.'+kind for kind in TYPES),
                  *('apps.codex.alerts.'+kind+'.'+group for kind in TYPES for group in GROUPS))
        if key not in (*KEYS,*LEGACY_KEYS,*branches):
            raise ValueError('unknown Codex alert configuration key: '+key)
        source=self.path
        if key in (*KEYS,*LEGACY_KEYS):
            kind,group,field=split(key);schema=GROUPS[group]
            table=self.declared['termux'] if kind=='regular' else self.declared['termux'].get('finished',{})
            if schema.FIELDS[field] not in table:
                source=self.root/'lib/dots'/(schema.__name__+'.py')
                if kind=='finished' and group=='toast' and field=='fg':source=self.root/'lib/dots/codex_notifications.py'
        return dict(value=lookup(self.values,parts(key)[2:]), source=str(source),
                    declarations=[], activation=ACTIVATION,canonical_key=canonical(key))


class NativePlan:
    def __init__(self, root, selected):
        from files.transactions import parents_safe
        self.native=Native(root,selected,guarded=True)
        self.path=self.native.path
        parents_safe(self.path)
        self.guards=self.native.guards.copy()
        self.items=[];self.operations=[]

    def edit(self, key, value=None, unset=False, json_value=False):
        if key not in (*KEYS,*LEGACY_KEYS): raise ValueError('edit an individual Codex alert field')
        try: import tomlkit
        except ImportError: raise ValueError('native TOML editing requires tomlkit; see tools/requirements-config.txt') from None
        if not unset and isinstance(value,str):
            try: value=json.loads(value)
            except ValueError:
                if json_value: raise ValueError('value must be valid JSON') from None
        kind,group,field=split(key);schema=GROUPS[group]
        reset=unset or value is None
        if not reset:
            schema.validate(field,value)
            if group=='toast' and field in ('fg','bg') and value.startswith('colors.'):
                from style_config import Styles
                Styles(self.native.root).color(value)  # Reject unresolved global references.
        document=tomlkit.parse(self.native.text)
        table=document['termux']
        if kind=='finished':
            if 'finished' not in table and not reset:table['finished']=tomlkit.table()
            table=table.get('finished',{})
        if reset: table.pop(schema.FIELDS[field],None)
        else: table[schema.FIELDS[field]]=value
        text=tomlkit.dumps(document)
        self.data=tomllib.loads(text)
        self.effective=values(self.data['termux'])
        self.items=[dict(action='unset' if reset else 'set',key=key)]
        self.operations=[dict(path=str(self.path),text=text)] if text!=self.native.text else []

    def apply(self, action):
        from files.file_platform import state_root
        from files.transactions import Store
        if not self.operations: return dict(status='unchanged')
        return Store(state_root()).apply('config-'+action,self.operations,self.guards,retain=True,catalogs=[self.path])

"""Guarded Config bindings for Codex toast and vibration native TOML fields."""
import json
from pathlib import Path
import stat
import tomllib

import codex_toast
import codex_vibration
from codex_toast import ACTIVATION
from config_values import parts, lookup
from profile_config import context

GROUPS={'toast':codex_toast,'vibrate':codex_vibration}
KEYS=tuple(key for schema in GROUPS.values() for key in schema.KEYS)


def constraints(key):
    path=parts(key)
    return GROUPS[path[2]].constraints(key) if len(path)>2 and path[2] in GROUPS else {}


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
        self.values={group:schema.values(self.declared['termux']) for group,schema in GROUPS.items()}
        if guarded and digest(self.path)!=self.guards[str(self.path)]:
            raise ValueError('Codex preferences changed while reading')

    def keys(self): return list(KEYS)

    def resolve(self, key):
        if key not in (*KEYS,'apps.codex',*('apps.codex.'+group for group in GROUPS)):
            raise ValueError('unknown Codex alert configuration key: '+key)
        source=self.path
        if key in KEYS:
            _,_,group,field=parts(key);schema=GROUPS[group]
            if schema.FIELDS[field] not in self.declared['termux']:
                source=self.root/'lib/dots'/(schema.__name__+'.py')
        return dict(value=lookup(self.values,parts(key)[2:]), source=str(source),
                    declarations=[], activation=ACTIVATION)


class NativePlan:
    def __init__(self, root, selected):
        from files.transactions import parents_safe
        self.native=Native(root,selected,guarded=True)
        self.path=self.native.path
        parents_safe(self.path)
        self.guards=self.native.guards.copy()
        self.items=[];self.operations=[]

    def edit(self, key, value=None, unset=False, json_value=False):
        if key not in KEYS: raise ValueError('edit an individual Codex alert field')
        try: import tomlkit
        except ImportError: raise ValueError('native TOML editing requires tomlkit; see tools/requirements-config.txt') from None
        if not unset and isinstance(value,str):
            try: value=json.loads(value)
            except ValueError:
                if json_value: raise ValueError('value must be valid JSON') from None
        _,_,group,field=parts(key);schema=GROUPS[group]
        reset=unset or value is None
        if not reset:
            schema.validate(field,value)
            if group=='toast' and field in ('fg','bg') and value.startswith('colors.'):
                from style_config import Styles
                Styles(self.native.root).color(value)  # Reject unresolved global references.
        document=tomlkit.parse(self.native.text)
        if reset: document['termux'].pop(schema.FIELDS[field],None)
        else: document['termux'][schema.FIELDS[field]]=value
        text=tomlkit.dumps(document)
        self.data=tomllib.loads(text)
        self.effective={group:schema.values(self.data['termux']) for group,schema in GROUPS.items()}
        self.items=[dict(action='unset' if reset else 'set',key=key)]
        self.operations=[dict(path=str(self.path),text=text)] if text!=self.native.text else []

    def apply(self, action):
        from files.file_platform import state_root
        from files.transactions import Store
        if not self.operations: return dict(status='unchanged')
        return Store(state_root()).apply('config-'+action,self.operations,self.guards,retain=True,catalogs=[self.path])

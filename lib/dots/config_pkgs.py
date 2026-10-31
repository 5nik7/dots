"""Guarded edits of pkgs' authoritative native JSON, without profile inheritance."""
import copy
import json
from pathlib import Path
import sys

from config_values import parts, name, lookup, MISSING
from files.file_platform import state_root
from profile_config import context


def core(root):
    path = str(Path(root) / 'plugins/pkgs')
    if path not in sys.path: sys.path.insert(0, path)
    file_lib = str(Path(root)/'lib/dots/files')
    if file_lib not in sys.path: sys.path.insert(0, file_lib)
    from pkgs_lib import common, policies
    return common, policies


class Native:
    def __init__(self, root, selected=None, *, guarded=False):
        common, policies = core(root)
        if selected and selected['current'] != context(root)['current']:
            raise ValueError('pkgs uses active native configuration; inactive-profile access is unavailable')
        self.original = common.config_path()
        self.path = self.original.resolve()
        from files.transactions import digest
        self.guards = {str(p): digest(p) for p in {self.original, self.path}}
        self.text = self.path.read_text() if self.path.exists() else '{}\n'
        self.declared = json.loads(self.text)
        self.defaults = copy.deepcopy(policies.DEFAULTS)
        try: self.values = common.config()
        except common.Error as e: raise ValueError(str(e)) from e
        if any(digest(Path(p)) != before for p, before in self.guards.items()):
            raise ValueError('pkgs configuration changed while reading')

    def recognized(self, path):
        if path in ((), ('upgrade',), ('upgrade','managers'), ('output',), ('policies',)):
            return True
        # Arbitrary package names belong in JSON objects, not dot-split keys.
        return len(path) == 2 and path[0] == 'policies' and path[1] in core(Path(__file__).parents[2])[1].MANAGERS

    def resolve(self, key):
        path = parts(key)
        if path[:2] != ('apps','pkgs') or not self.recognized(path[2:]):
            raise ValueError('unknown pkgs configuration key: ' + key)
        return dict(value=lookup(self.values, path[2:]) if path[2:] else self.values,
                    source=str(self.original), declarations=[], activation='next invocation')

    def keys(self):
        from pkgs_lib.grammar import MANAGERS
        return ['apps.pkgs.'+k for k in ('upgrade.managers','output','policies')] + [
            name(('apps','pkgs','policies',m)) for m in MANAGERS]


class NativePlan:
    def __init__(self, root, selected):
        from files.transactions import parents_safe
        self.root = root
        self.native = Native(root, selected, guarded=True)
        self.path = self.native.path
        parents_safe(self.path)
        self.guards = self.native.guards.copy()
        self.items, self.operations = [], []

    def edit(self, key, value=None, unset=False, json_value=False):
        common, policies = core(self.root)
        path = parts(key)[2:]
        if not path or not self.native.recognized(path):
            raise ValueError('edit a declared pkgs control, not the whole native document')
        data = copy.deepcopy(self.native.declared)
        if not unset and isinstance(value, str):
            try: value = json.loads(value)
            except ValueError:
                if json_value: raise ValueError('value must be valid JSON') from None
        node = data
        for part in path[:-1]:
            node = node.setdefault(part, {})
            if not isinstance(node, dict): raise ValueError('invalid configuration parent')
        if unset or value is None: node.pop(path[-1], None)
        else: node[path[-1]] = value
        # Missing nested defaults are restored fieldwise without serializing them.
        effective = copy.deepcopy(data)
        effective.setdefault('upgrade', {}).setdefault('managers', 'auto')
        try: policies.validate(effective)
        except common.Error as e: raise ValueError(str(e)) from e
        self.data, self.effective = data, effective
        text = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
        self.items = [dict(action='unset' if unset or value is None else 'set', key=key)]
        self.operations = [dict(path=str(self.path), text=text)] if data != self.native.declared else []

    def apply(self, action):
        from files.transactions import Store
        if not self.operations: return dict(status='unchanged')
        return Store(state_root()).apply('config-'+action, self.operations, self.guards, retain=True,
                                         catalogs=[self.path] if self.path.parent.is_dir() else [])


def constraints(key):
    if key == 'apps.pkgs.output': return dict(type='string', choices=['auto','styled','raw'], default='auto')
    if key == 'apps.pkgs.upgrade.managers':
        return dict(type='manager-list', examples=['auto',['apt','npm','uv-tool','go']], default='auto',
                    syntax='auto or an ordered JSON array of supported manager IDs')
    return dict(type='object', default={}, syntax='JSON manager policy: skip, install/upgrade recipes, and packages overrides')

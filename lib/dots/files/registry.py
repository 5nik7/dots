"""Core resource identities and eligibility, independent of profile mappings."""
import copy
import re

from identities import canonical

QUALIFIED = re.compile(r'[a-z][a-z0-9_-]*:[a-z][a-z0-9_-]*\Z')
PLATFORMS = {'termux', 'linux', 'wsl', 'windows'}


class Registry:
    def __init__(self, document, sources):
        self.schema = document.get('schema') if isinstance(document, dict) else None
        fields = {'schema', 'resources'} | ({'renames'} if self.schema == 3 else set())
        if self.schema not in (2, 3) or set(document) != fields:
            raise ValueError('core files registry requires schema 2 or 3 and resources')
        if not isinstance(document['resources'], list): raise ValueError('registry resources must be a list')
        self.sources = {canonical(row['id']) for row in sources if not row.get('excluded')}
        self.entries = {}
        for row in document['resources']:
            if not isinstance(row, dict) or set(row) != {'id','platforms'}:
                raise ValueError('registry entries contain only qualified id and platforms')
            identity = row['id']
            if not isinstance(identity,str) or not QUALIFIED.fullmatch(identity) or identity in self.entries:
                raise ValueError('duplicate or invalid registry resource ID')
            if identity.split(':')[0] not in self.sources: raise ValueError('registry refers to an unknown or excluded source: '+identity)
            self.validate_platforms(row['platforms'])
            self.entries[identity] = list(row['platforms'])
        self.renames = copy.deepcopy(document.get('renames', {}))
        if not isinstance(self.renames, dict): raise ValueError('registry renames must be an object')
        for old, new in self.renames.items():
            if (not isinstance(old, str) or not QUALIFIED.fullmatch(old)
                    or not isinstance(new, str) or not QUALIFIED.fullmatch(new)
                    or old in self.entries or new not in self.entries
                    or old.split(':')[0] != new.split(':')[0]):
                raise ValueError('registry renames require reserved old IDs and current IDs within one owner')

    def resolve(self, identity):
        identity = canonical(identity)
        return self.renames.get(identity, identity)

    def require_current(self, identity):
        current = self.resolve(identity)
        if current != identity:
            raise ValueError(identity + ' was renamed; use ' + current)

    def renamed(self, old, new):
        self.require_current(old)
        if old not in self.entries: raise ValueError('resource ID not found: ' + old)
        if not QUALIFIED.fullmatch(new) or old.split(':')[0] != new.split(':')[0]:
            raise ValueError('new resource ID must be a local ID within the same owner')
        if old == new: return self.update({})
        if new in self.entries or new in self.renames:
            raise ValueError('resource ID exists or is reserved for recovery: ' + new)
        entries = {new if key == old else key: value for key, value in self.entries.items()}
        renames = {key: new if value == old else value for key, value in self.renames.items()}
        renames[old] = new
        return dict(schema=3, resources=[dict(id=key, platforms=entries[key]) for key in sorted(entries)],
                    renames=dict(sorted(renames.items())))

    @staticmethod
    def validate_platforms(value):
        if not isinstance(value,list) or not value or any(not isinstance(v,str) for v in value) or not set(value) <= PLATFORMS or len(set(value)) != len(value):
            raise ValueError('registry platforms must be a nonempty unique platform list')

    def join(self, owner, rows, *, candidate=False):
        result = []
        for raw in rows:
            if not isinstance(raw,dict): raise ValueError('profile mapping must be an object')
            row = copy.deepcopy(raw)
            identity = owner+':'+str(row.get('id',''))
            self.require_current(identity)
            for replacement in row.get('replaces', []): self.require_current(replacement)
            if identity not in self.entries and not candidate:
                raise ValueError('profile mapping is absent from the core registry: '+identity)
            platforms = row.get('platforms') if candidate and 'platforms' in row else self.entries.get(identity)
            self.validate_platforms(platforms)
            row['platforms'] = list(platforms)
            result.append(row)
        return result

    def update(self, documents):
        entries = dict(self.entries)
        for owner, doc in documents.items():
            for row in doc['resources']:
                self.require_current(owner+':'+row['id'])
                self.validate_platforms(row['platforms'])
                entries[owner+':'+row['id']] = row['platforms']
        result = dict(schema=self.schema, resources=[dict(id=key,platforms=entries[key]) for key in sorted(entries)])
        if self.schema == 3: result['renames'] = dict(self.renames)
        return result


def implementation(row, platform):
    result = copy.deepcopy(row)
    result['target'] = result.get('targets', {}).get(platform, result.get('target'))
    result.pop('platforms', None)
    result.pop('targets', None)
    return result

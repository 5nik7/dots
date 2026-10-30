"""Core resource identities and eligibility, independent of profile mappings."""
import copy
import re

from identities import canonical

QUALIFIED = re.compile(r'[a-z][a-z0-9_-]*:[a-z][a-z0-9_-]*\Z')
PLATFORMS = {'termux', 'linux', 'wsl', 'windows'}


class Registry:
    def __init__(self, document, sources):
        if not isinstance(document, dict) or document.get('schema') != 2 or set(document) != {'schema','resources'}:
            raise ValueError('core files registry requires schema 2 and resources')
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
                self.validate_platforms(row['platforms'])
                entries[owner+':'+row['id']] = row['platforms']
        return dict(schema=2, resources=[dict(id=key,platforms=entries[key]) for key in sorted(entries)])


def implementation(row, platform):
    result = copy.deepcopy(row)
    result['target'] = result.get('targets', {}).get(platform, result.get('target'))
    result.pop('platforms', None)
    result.pop('targets', None)
    return result

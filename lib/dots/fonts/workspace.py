"""One guarded collection plan spanning the personal and profile font stores."""
from copy import deepcopy

from fonts.model import Library,Plan


class Workspace:
    def __init__(self, library, temporary, *, plan=None):
        self.temporary=temporary
        native=library if not library.directory else Library(platform=library.platform)
        if native.guard!=library.guard:raise ValueError('font collection changed while planning')
        self.user=plan or Plan(native)
        self.stores={}
        if library.directory:self.attach(library)

    def attach(self, library):
        if library.guard!=self.user.library.guard:raise ValueError('font collection changed while planning')
        if library.directory_key in self.stores:return self.stores[library.directory_key]
        plan=Plan(library)
        if library.directory_key in self.user.document.get('directories',{}):
            plan.document=deepcopy(self.user.document['directories'][library.directory_key])
        for path,expected in plan.guards.items():
            if path in self.user.guards and self.user.guards[path]!=expected:raise ValueError('font inputs changed while planning')
        self.user.guards.update(plan.guards)
        plan.guards=self.user.guards;plan.operations=self.user.operations;plan.refresh=self.user.refresh
        self.stores[library.directory_key]=plan
        return plan

    def store(self, directory=None):
        if not directory or directory=='personal':return self.user
        return self.attach(Library(platform=self.user.library.platform,directory=directory))

    def all_stores(self):
        from fonts.destinations import Destinations,key
        for row in Destinations().rows():
            if key(row['path']) in self.user.document.get('directories',{}):self.store(row['path'])
        return [self.user,*self.stores.values()]

    def resolve(self, query, source=None, *, catalog=False):
        plans=[self.store(source)] if source else self.all_stores()
        rows={}
        if catalog:rows.update(self.user.library.catalog['families'])
        for plan in plans:rows.update(plan.document['families'])
        if query in rows:return query
        needle=query.casefold().replace(' ','')
        found=[k for k,v in rows.items() if needle in (k+' '+v.get('name','')).casefold().replace(' ','')]
        if len(found)!=1:raise ValueError('font selection is ambiguous' if found else 'font not found in the selected source')
        return found[0]

    def obtain(self, identity, version=None, source=None, *, dry_run=False, required_variant=None, download_target=None):
        plans=[self.store(source)] if source else self.all_stores()
        for plan in plans:
            row=plan.document['families'].get(identity,{})
            selected=version or row.get('pin') or (row.get('installed') or {}).get('version') or row.get('preferred')
            record=row.get('versions',{}).get(selected)
            if not record or record.get('available') is False:continue
            if required_variant and record.get('partial'):
                needed={f['file'] for f in record.get('known_fonts',[]) if f['variant']==required_variant}
                if not needed<={f['file'] for f in record['fonts']}:continue
            return plan,selected
        if source:raise ValueError('font version is not available in the selected source')
        spec=self.user.library.catalog['families'].get(identity)
        if not spec:raise ValueError('local font is unavailable; import its original files')
        version=version or spec['latest']
        if version not in spec['versions']:raise ValueError('exact version is not cataloged; refresh that release first')
        if dry_run:
            self.user.items.append(dict(id=identity,version=version,action='download and validate selected version before applying'))
            return None,version
        from fonts.providers import download
        from fonts.operations import stage
        from pathlib import Path
        import tempfile
        payload=Path(tempfile.mkdtemp(prefix='fetch-',dir=self.temporary))/'payload'
        record=download(identity,spec['versions'][version],payload)
        target=download_target or self.user
        stage(target,identity,version,payload,record,spec['name'],temporary=self.temporary)
        return target,version

    def finish(self):
        for key,plan in self.stores.items():
            if plan.document!=plan.library.document:self.user.document.setdefault('directories',{})[key]=deepcopy(plan.document)
            self.user.items.extend(plan.items)
        return self.user.finish()

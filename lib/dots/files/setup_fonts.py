"""Compose font-owner plans with checkout publication and selective removal."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

from transactions import digest


class Fonts:
    def __init__(self, installation, args):
        self.args = args
        self.installation = installation
        self.plan = None

    def preview(self):
        from fonts.model import Library
        from fonts.config import destination, TARGETS
        library = Library(platform=self.installation.platform)
        library.setup_installation = self.installation
        self.installation.merge_plan([],{str(library.path):library.guard,
                                        str(library.catalog_path):library.catalog_guard},label='font inputs')
        document = self.args.font_document or dict(schema=1,applications={})
        if document.get('schema') != 1 or not isinstance(document.get('applications'),dict):
            raise ValueError('invalid setup font preferences')
        keys = self.args.font_target if self.args.font_target is not None else list(document['applications'])
        rows = []
        for key in keys:
            saved = document['applications'].get(key)
            if not saved or saved.get('target') not in TARGETS or not all(saved.get(f) for f in ('id','version','face','variant','files')):
                raise ValueError('saved font choice is missing exact identity/files: '+key)
            import re
            from fonts.model import relative
            if not isinstance(saved['files'],dict) or any(not isinstance(v,str) or not re.fullmatch('[a-f0-9]{64}',v) for v in saved['files'].values()):
                raise ValueError('saved font files require exact SHA-256 values: '+key)
            for name in saved['files']: relative(name)
            rows.append(saved)
        rows += self.args.font_choices
        for row in rows:
            found = destination(library,row['target'],row.get('config'))
            self.installation.merge_plan([],found.get('guards',{}),label='font destinations')
            self.installation.guard(found['path'])
            if found.get('catalog'):
                for path in found['catalog'].input_paths(): self.installation.guard(path)
                self.installation.guard(found['destination'])
        return [dict(target=r['target'], id=r['id'], version=r['version'], face=r['face']) for r in rows]

    def prepare(self, temporary, *, dry_run=False):
        from fonts.model import Library
        from fonts.workspace import Workspace
        from fonts.defaults import choose, synchronize
        from fonts.config import TARGETS
        library = Library(platform=self.installation.platform)
        library.setup_installation = self.installation
        workspace = Workspace(library, temporary)
        document = self.args.font_document or dict(schema=1,applications={})
        if document.get('schema') != 1 or not isinstance(document.get('applications'), dict):
            raise ValueError('invalid setup font preferences')
        selections = self.args.font_target if self.args.font_target is not None else list(document['applications'])
        for key in selections:
            saved = document['applications'].get(key)
            if not saved: raise ValueError('no saved default font for '+key)
            if saved.get('target') not in TARGETS or key != saved['target']+(':'+saved['app_profile'] if saved.get('app_profile') else ''):
                raise ValueError('invalid saved application font target')
            identity, version = saved['id'], saved['version']
            if saved.get('upstream'):
                catalog = library.catalog['families']
                entry = catalog.setdefault(identity,dict(name=saved['name'],provider=identity.split(':')[0],latest=version,versions={}))
                entry['versions'].setdefault(version,deepcopy(saved['upstream']))
            selected = SimpleNamespace(target=[saved['target']], config=saved.get('config'),
                app_profile=saved.get('app_profile'), variant=saved['variant'], face=saved['face'], dry_run=dry_run)
            choose(workspace,identity,version,None,selected,saved=saved)
        for choice in self.args.font_choices:
            selected = SimpleNamespace(target=[choice['target']], config=None, app_profile=None,
                variant=choice['variant'],face=choice['face'],dry_run=dry_run)
            choose(workspace,choice['id'],choice['version'],None,selected)
        if not dry_run: synchronize(workspace,save_preferences=self.args.save_choices)
        self.plan = workspace.finish()
        return self.plan.report()

    def publish(self, installation):
        plan = self.plan
        targets = {key:ref for key,ref in plan.document['targets'].items()
                   if any(i.get('target') == key and i.get('action') == 'set' for i in plan.items)}
        originals = installation.receipt.setdefault('font_targets', {})
        for key in targets:
            if key not in originals:
                originals[key] = deepcopy(plan.library.document['targets'].get(key))
                installation.receipt_changed = True
            after = installation.receipt.setdefault('font_after',{})
            if after.get(key) != targets[key]:
                after[key] = deepcopy(targets[key])
                installation.receipt_changed = True
        paths = {ref['path'] for ref in targets.values()}
        for op in plan.operations:
            if op['path'] == str(installation.receipt_path):
                # Fonts normally updates installed copies' after-images. This
                # coordinator computes those images with its one final receipt.
                continue
            if op['path'] not in paths: continue
            key = next(key for key,ref in targets.items() if ref['path'] == op['path'])
            installation.add('setup:font:'+key,op['path'], **{k:op[k] for k in ('source','text') if k in op})
        # A managed copy has two edits: its canonical source and active copy.
        # Save the source's pre-font baseline independently of the copy's
        # original checkout-install baseline, so either component can be removed.
        copies = {}
        for op in plan.operations:
            if op['path'] in paths or op['path'] == str(installation.receipt_path): continue
            owned = installation.entries.get(op['path'])
            if not owned or 'text' not in op: continue
            source_op = next((s for s in plan.operations if s['path'] in paths and s.get('text') == op['text']),None)
            if source_op is None: continue
            original = installation.entries.get(source_op['path'])
            if original is None: continue
            installation.receipt.setdefault('font_copies',{}).setdefault(op['path'],
                dict(source=source_op['path'], **{k:original[k] for k in ('before','backup','index')}))
            previous = next((p for p in installation.operations if p['path'] == op['path']),None)
            if previous:
                if 'source' not in previous: raise ValueError('font copy conflicts with a setup operation: '+op['path'])
                previous.clear();previous.update(op)
                owned['desired'] = {k:v for k,v in op.items() if k != 'path'}
            else:
                installation.add(owned['id'],op['path'],text=op['text'])
            copies[op['path']] = True
        remainder = [op for op in plan.operations if op['path'] not in paths|set(copies)|{str(installation.receipt_path)}]
        installation.merge_plan(remainder,plan.guards,label='font libraries, registrations and preferences')


def uninstall(installation):
    """Called after ordinary removal planning; preserve drift and registrations."""
    if installation.components is not None and 'fonts' not in installation.components: return
    if not installation.receipt.get('font_targets') and not installation.receipt.get('font_copies'): return
    from fonts.model import Library, Plan
    library = Library(platform=installation.platform)
    plan = Plan(library)
    changed = False
    preserved = set()
    for key, original in list(installation.receipt.get('font_targets',{}).items()):
        current = plan.document['targets'].get(key)
        expected = installation.receipt.get('font_after',{}).get(key)
        if expected is not None and current != expected:
            # Ordinary removal has only planned writes so far. Restore its
            # receipt entry and remove that planned source restoration on drift.
            path = expected['path']
            previous = installation.receipt['entries'].get(path)
            if previous and path not in installation.entries:
                installation.entries[path] = deepcopy(previous)
                installation.operations[:] = [op for op in installation.operations if op['path'] != path]
                installation.items[:] = [item for item in installation.items if item.get('target') != path]
            installation.item('setup:font:'+key,'preserved',path,reason='font selection metadata changed')
            preserved.add(path)
            continue
        if current and current['path'] in installation.entries:
            # A preserved source means its app selection must remain too.
            preserved.add(current['path'])
            continue
        if original is None: plan.document['targets'].pop(key,None)
        else: plan.document['targets'][key] = deepcopy(original)
        del installation.receipt['font_targets'][key]
        installation.receipt.get('font_after',{}).pop(key,None)
        changed = True
    for path, baseline in list(installation.receipt.get('font_copies',{}).items()):
        owned = installation.entries.get(path)
        if owned:
            if baseline.get('source') in preserved or preserved and 'source' not in baseline:
                installation.item('setup:font:copy','preserved',path,reason='source font selection was preserved')
                continue
            installation.guard(path)
            if installation.guards[path] != owned['after']:
                installation.item('setup:font:copy','preserved',path,reason='font configuration copy changed')
                continue
            op = dict(path=path)
            if baseline['before'] is None: op['delete'] = True
            else:
                source = installation.store.root/baseline['backup']/(str(baseline['index'])+'-before')
                installation.guard(source)
                if installation.guards[str(source)] != baseline['before']: raise ValueError('font baseline backup changed')
                op['source'] = str(source)
            installation.operations.append(op)
            owned['after'] = baseline['before']
            installation.item('setup:font:copy','restore',path)
        del installation.receipt['font_copies'][path]
        changed = True
    if changed:
        plan.finish()
        installation.merge_plan(plan.operations,plan.guards,label='restore previous font selections')
        installation.receipt_changed = True

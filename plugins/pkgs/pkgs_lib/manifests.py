"""Editable package data and desired-state restore; never source a manifest."""
import copy
from contextlib import nullcontext
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from .common import Error, ROOT, budget, phase, validate_names, config_path, clean
from .detect import MANAGERS, SYSTEM, available, termux
from . import policies, scopes, workflows

PINNED = {'apt','dnf','npm','pip','uv-tool','gem','go'}
PLATFORMS = {'termux','linux','wsl','windows'}


def dotslib():
    path = str(ROOT.parent.parent / 'lib/dots')
    if path not in sys.path: sys.path.insert(0, path)
    if path+'/files' not in sys.path: sys.path.insert(0, path+'/files')


def platform():
    dotslib()
    from platform_info import detect
    return detect()['platform']


def default_path(root=None):
    """The active leaf profile owns its package manifest, independent of cwd."""
    dotslib()
    from profile_config import context
    selected = context(root or os.environ.get('DOTS') or ROOT.parent.parent)
    if not selected['layers']:
        raise ValueError('No active Dots profile; specify an export --output FILE')
    return Path(selected['layers'][-1]['root'])/'packages.json'


def validate(document):
    if not isinstance(document, dict) or document.get('schema') != 1 or not isinstance(document.get('groups'), list):
        raise Error('expected a schema-1 package manifest with groups')
    if set(document) - {'schema','groups','notices'}: raise Error('unknown manifest fields; manifests contain data, not recipes')
    result, seen = copy.deepcopy(document), set()
    for group in result['groups']:
        if not isinstance(group, dict) or set(group) - {'manager','scope','platforms','packages'}:
            raise Error('invalid manifest group')
        manager = group.get('manager')
        if manager not in MANAGERS: raise Error('unknown manifest manager')
        allowed = ('system',) if manager in SYSTEM else ('global','project') if manager == 'npm' else (
            ('base','venv') if manager == 'pip' else ('user','active') if manager == 'gem' else ('tools',))
        if group.get('scope') not in allowed: raise Error('invalid scope for '+manager)
        group.setdefault('platforms', ['termux','linux','wsl'])
        if not isinstance(group['platforms'], list) or not group['platforms'] or any(p not in PLATFORMS for p in group['platforms']):
            raise Error('invalid manifest platforms')
        key = ('pacman' if manager in ('pacman','paru','yay') else manager, group['scope'])
        if key in seen: raise Error('duplicate manifest database/scope')
        seen.add(key)
        if not isinstance(group.get('packages'), list): raise Error('packages must be a list')
        names = set()
        for package in group['packages']:
            if not isinstance(package, dict) or set(package) - {'name','observed_version','pin','selection','enabled','reason'}:
                raise Error('invalid package record')
            name = package.get('name')
            if not isinstance(name, str): raise Error('package name must be a string')
            if package.get('enabled', True): validate_names([name], manager)
            elif not policies.literal(name) or len(name) > 4096: raise Error('invalid disabled package identity')
            if manager == 'go' and '@' in name: raise Error('Go version belongs in pin, not name')
            normal = policies.identity(name, manager)
            if normal in names: raise Error('duplicate package: '+name)
            names.add(normal)
            package.setdefault('enabled', True); package.setdefault('pin', None)
            package.setdefault('selection', 'manual'); package.setdefault('observed_version', '')
            if type(package['enabled']) is not bool or package['selection'] not in ('explicit','inferred','all','manual'):
                raise Error('invalid enabled state or selection evidence')
            if not isinstance(package['observed_version'], str) or not isinstance(package.get('reason',''), str):
                raise Error('invalid package metadata')
            pin = package['pin']
            if pin is not None:
                if manager not in PINNED: raise Error('exact pins are unsupported for '+manager)
                if not isinstance(pin, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._+~:-]*', pin):
                    raise Error('pin must be one exact version: '+name)
    return result


def load(path):
    path = Path(path).expanduser().absolute()
    if path.stat().st_size > 8*1024*1024: raise Error('manifest exceeds 8 MiB')
    return validate(json.loads(path.read_text(encoding='utf-8')))


def guards(path=None, extra=()):
    dotslib()
    from files.transactions import digest
    paths = [config_path(), *map(Path, extra)] + ([Path(path).expanduser().absolute()] if path else [])
    expected = {str(p): digest(p) for original in paths for p in (original, original.resolve())}
    def check():
        if any(digest(Path(p)) != before for p, before in expected.items()):
            raise Error('manifest or package configuration changed after preview; review again')
    check.expected = expected
    return check


def merge(previous, current):
    """Refresh observations, preserving every existing desired-state decision."""
    result, current = validate(previous), validate(current)
    key = lambda g: ('pacman' if g['manager'] in ('pacman','paru','yay') else g['manager'], g['scope'])
    groups = {key(g): g for g in result['groups']}
    for fresh in current['groups']:
        group = groups.get(key(fresh))
        if group is None:
            result['groups'].append(fresh); continue
        if platform() not in group['platforms']: continue
        packages = {policies.identity(p['name'], group['manager']): p for p in group['packages']}
        for observed in fresh['packages']:
            package = packages.get(policies.identity(observed['name'], group['manager']))
            if package is None: group['packages'].append(observed)
            else: package['observed_version'] = observed['observed_version']
    if current.get('notices'):
        if not isinstance(result.get('notices', []), list): raise Error('manifest notices must be a list to update')
        for notice in current['notices']:
            if notice not in result.setdefault('notices', []): result['notices'].append(notice)
    return validate(result)


class Update:
    """A read-only export snapshot followed by a guarded, journaled file write."""
    def __init__(self, path, args, cfg, *, root=None, profile_default=False):
        self.path = Path(path).expanduser().absolute()
        self.root, self.profile_default = root, profile_default
        self.check = guards(self.path, [self.path.parent/'profile.json'] if profile_default else [])
        if self.path.is_symlink() or self.path.exists() and not self.path.is_file():
            raise Error('export destination must be a regular file')
        self.previous = load(self.path) if self.path.exists() else None
        self.document, failed = export(args, cfg)
        if failed: raise Error('manifest update is incomplete: '+json.dumps(self.document['notices'], ensure_ascii=False))
        if self.previous is not None: self.document = merge(self.previous, self.document)
        self.verify()

    def verify(self):
        self.check()
        if self.profile_default and default_path(self.root).absolute() != self.path:
            raise Error('active profile changed after preview; review again')

    def save(self, args, *, emit=True):
        self.verify()
        return write_export(self.path, self.document, args, expected=self.check.expected, emit=emit)


def export(args, cfg):
    document = dict(schema=1, groups=[], notices=[])
    failed = False
    progress = phase if not (args.dry_run or args.json or cfg.get('output') == 'raw' or
                            os.environ.get('DOTS_PROGRESS', 'auto') != 'auto') else lambda label: nullcontext()
    with budget(45), progress('Detecting export managers'):
        selection = [(args.manager, 'global' if args.global_scope else None)] if args.manager not in (None,'auto') else scopes.bulk(dict(cfg, upgrade={'managers':'auto'}))
    for index, (manager, scope) in enumerate(selection, 1):
        try:
            with budget(45), progress(f'Exporting {manager} ({index}/{len(selection)})'):
                if not available(manager): raise Error('manager unavailable')
                backend = scopes.make(manager, scope)
                rows = scopes.inventory(backend, roots=not args.include_dependencies,
                                        owned=manager == 'pip' and args.manager in (None,'auto'), portable=True)
            packages = []
            grouped = {}
            for row in rows: grouped.setdefault(policies.identity(row[0].name, manager), []).append(row)
            for identity, values in sorted(grouped.items()):
                p, evidence, reason = values[0]
                version = p.installed_version or p.version
                if len(values) > 1:
                    reason = 'multiple installed records; choose the desired identity/version manually'
                    version = ', '.join(sorted({v[0].installed_version or v[0].version for v in values}))
                record = dict(name=p.name, observed_version=version,
                              pin=version if args.pin_versions and manager in PINNED and not reason and version else None,
                              selection=evidence, enabled=not bool(reason))
                if reason: record['reason'] = reason
                packages.append(record)
            if args.pin_versions and manager not in PINNED:
                document['notices'].append(dict(manager=manager, warning='exact pins unsupported; observed versions retained without pins'))
            document['groups'].append(dict(manager=manager, scope=scopes.scope_id(backend),
                platforms=[platform()] if manager in SYSTEM else ['termux','linux','wsl'], packages=packages))
        except (Error, OSError, ValueError) as error:
            failed = True
            document['notices'].append(dict(manager=manager, error=str(error)))
    return validate(document), failed


def prepare_group(group, cfg, *, ignore=False):
    manager = group['manager']
    if platform() not in group['platforms']: return dict(group=group, status='skipped', reason='different platform', plan=None)
    targets = [p['name'] for p in group['packages'] if p['enabled']]
    targets, blocked = policies.selected(cfg, manager, targets, override=ignore, explicit=False)
    if not targets: return dict(group=group, status='skipped', reason='no enabled targets after manifest/policy exclusions', plan=None)
    if not available(manager): return dict(group=group, status='deferred', reason='manager prerequisite unavailable', plan=None)
    backend = scopes.make(manager, group['scope'])
    if scopes.scope_id(backend) != group['scope']: raise Error('current '+manager+' scope does not match manifest '+group['scope'])
    rows = backend.installed()
    if manager == 'gem': rows = scopes.gem_versions(rows)
    installed = {policies.identity(p.name, manager): p for p in rows}
    names, skipped, backend.pins = [], [], {}
    for package in group['packages']:
        name = package['name']
        if not package['enabled']:
            skipped.append(dict(package=name, reason=package.get('reason','disabled in manifest'))); continue
        allowed, blocked = policies.selected(cfg, manager, [name], override=ignore, explicit=False)
        if blocked:
            skipped.append(dict(package=name, reason='skipped by policy')); continue
        p = installed.get(policies.identity(name, manager))
        pin = package['pin']
        if p and (pin is None or p.installed_version == pin or manager == 'gem' and pin in p.details.get('versions', [])): continue
        names.append(name)
        if pin: backend.pins[name] = pin
    item = workflows.plan(backend, 'install', names, cfg, yes=True, override=ignore) if names else workflows.Plan(backend, 'install')
    item.skipped += skipped
    return dict(group=group, status='planned', reason='', plan=item)


def prepare(document, cfg, *, ignore=False):
    cfg = dict(cfg, _quiet_progress=True)
    document = validate(document)
    result = []
    for group in sorted(document['groups'], key=lambda g: 0 if g['manager'] in SYSTEM else 1):
        try:
            with budget(45): result.append(prepare_group(group, cfg, ignore=ignore))
        except (Error, OSError, ValueError) as error:
            result.append(dict(group=group, status='failed', reason=str(error), plan=None))
    return result


def serialized(entries):
    return [dict(manager=e['group']['manager'], scope=e['group']['scope'], status=e['status'], reason=e['reason'],
                 plan=e['plan'].document() if e['plan'] else None) for e in entries]


def preview(entries, cfg, *, stream=None):
    stream = stream or sys.stdout
    for entry in entries:
        if entry['plan']: workflows.display(entry['plan'], cfg, stream=stream)
        else: print(entry['group']['manager']+': '+entry['status']+' · '+entry['reason'], file=stream)


def apply(document, cfg, *, ignore=False, data=False, check=None):
    result, failed = [], False
    # Re-query after the system stage; declared packages may supply prerequisites.
    for group in sorted(validate(document)['groups'], key=lambda g: 0 if g['manager'] in SYSTEM else 1):
        if check: check()
        try:
            with budget(45): entry = prepare_group(group, cfg, ignore=ignore)
            item = entry['plan']
            if item is None:
                if entry['status'] == 'deferred': entry['status'] = 'failed'; failed = True
            else:
                workflows.display(item, cfg, stream=sys.stderr if data else sys.stdout)
                rc = workflows.apply(item, cfg, data=data)
                entry['status'] = 'failed' if rc else 'complete' if item.commands else 'unchanged'
                if not rc and item.commands:
                    with budget(45): after = prepare_group(group, cfg, ignore=ignore)
                    if after['plan'] and after['plan'].commands:
                        entry['status'], entry['reason'] = 'failed', 'manager returned success but requested packages/pins are not satisfied'
                failed |= entry['status'] == 'failed'
            result.extend(serialized([entry]))
        except (Error, OSError, ValueError) as error:
            result.append(dict(manager=group['manager'], scope=group['scope'], status='failed', reason=str(error), plan=None))
            failed = True
    return dict(schema=1, status='incomplete' if failed else 'complete', groups=result)


def write_export(path, document, args, *, expected=None, emit=True):
    dotslib()
    from files.transactions import Store, digest, parents_safe, exists
    from files.file_platform import state_root
    path = Path(path).expanduser().absolute()
    parents_safe(path)
    if path.is_symlink() or exists(path) and not path.is_file(): raise Error('export destination must be a regular file')
    before = digest(path)
    text = json.dumps(document, indent=2, ensure_ascii=False)+'\n'
    if path.exists() and path.read_text() == text: return
    if args.dry_run:
        print('Would write package manifest: '+str(path), file=sys.stderr); return
    if path.exists() and not workflows.confirm(args.yes): return
    Store(state_root()).apply('pkgs-export', [dict(path=str(path), text=text)], expected if expected is not None else {str(path): before}, retain=True,
                              catalogs=[path] if path.parent.is_dir() else [])
    if emit: print('Wrote package manifest: '+str(path), file=sys.stderr)


def cli(args, cfg):
    if args.query or args.installed: raise Error('manifest workflows do not accept --query or --installed')
    if args.command != 'export' and (args.manager is not None or args.global_scope):
        raise Error('manifest groups specify their managers and scopes')
    if args.command == 'export':
        if args.names: raise Error('export takes --output FILE, not positional operands')
        if args.global_scope and args.manager != 'npm': raise Error('--global requires --manager npm')
        if args.update:
            update = Update(args.output or default_path(), args, cfg, profile_default=not args.output)
            if args.dry_run:
                print(json.dumps(update.document, indent=2, ensure_ascii=False))
                print('Would update package manifest: '+str(update.path), file=sys.stderr)
            else: update.save(args)
            return 0
        check = guards(args.output)
        document, failed = export(args, cfg)
        check()
        if args.output:
            if failed: raise Error('export is incomplete; retry without --output to inspect partial JSON')
            write_export(args.output, document, args, expected=check.expected)
        else: print(json.dumps(document, indent=2, ensure_ascii=False))
        return int(failed)
    if len(args.names) != 1: raise Error(args.command+' requires one manifest file')
    check = guards(args.names[0])
    document = load(args.names[0])
    if args.command == 'manifest':
        if args.json: print(json.dumps(document, indent=2, ensure_ascii=False))
        else:
            from .reports import report
            ui = report(explicit=cfg.get('_explicit_color'), fallback=cfg.get('color','auto'))
            if ui: ui.heading('Package manifest', len(document['groups']))
            else: print('Package manifest')
            for group in document['groups']:
                title = group['manager']+' · '+group['scope']
                if ui: ui.heading(title, len(group['packages']))
                else: print('  '+title)
                for p in group['packages']:
                    text = p['name']+' · '+('pin '+p['pin'] if p['pin'] else 'installed or latest')+' · '+p['selection']
                    if not p['enabled']: text += ' · disabled: '+p.get('reason','manual')
                    if ui: ui.text(text, 'identity' if p['enabled'] else 'warning')
                    else: print('    '+clean(text))
        return 0
    entries = prepare(document, cfg, ignore=args.ignore_skip)
    check()
    if args.dry_run:
        if args.json: print(json.dumps(dict(schema=1, status='preview', groups=serialized(entries))))
        else: preview(entries, cfg)
        return 0
    preview(entries, cfg, stream=sys.stderr if args.json else sys.stdout)
    if not workflows.confirm(args.yes):
        if args.json: print(json.dumps(dict(schema=1,status='cancelled',groups=[])))
        return 0
    result = apply(document, cfg, ignore=args.ignore_skip, data=args.json, check=check)
    if args.json: print(json.dumps(result, ensure_ascii=False))
    else:
        print('Restore '+result['status'])
        for group in result['groups']: print('  '+group['manager']+': '+group['status']+(' · '+group['reason'] if group['reason'] else ''))
    return int(result['status'] != 'complete')

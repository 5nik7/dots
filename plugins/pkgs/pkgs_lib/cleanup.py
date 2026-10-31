"""Explicitly reviewed removal of manifest-disabled pip source installations."""
import hashlib
import json
from pathlib import Path
import sys

from .common import Error, Package, budget, clean, query, validate_names
from .detect import default_manager
from .backends import Backend
from . import manifests, policies, scopes, workflows

REASON = 'source or editable install; retain original source'


def provenance():
    result = query([sys.executable, '-m', 'pip', 'inspect', '--local'])
    if result.returncode: raise Error('cleanup requires current pip inspect ownership evidence')
    data = json.loads(result.stdout)
    if data.get('version') != '1': raise Error('unsupported pip inspect schema')
    system = Backend(default_manager())
    targets, files = set(), {}
    for item in data['installed']:
        location = item.get('metadata_location')
        if not location or not Path(location).is_absolute(): continue
        root = Path(location)
        paths = [root] if root.is_file() else [root/n for n in ('METADATA','PKG-INFO','INSTALLER','direct_url.json','RECORD') if (root/n).is_file()]
        files[location] = paths
        for path in paths: targets.update((str(path), str(path.resolve())))
    owners = system.owners(targets)
    records = {}
    manifests.dotslib()
    from files.transactions import digest
    for item in data['installed']:
        name, version = item['metadata']['name'], item['metadata']['version']
        location = item.get('metadata_location')
        paths = files.get(location, [])
        reason = ''
        if item.get('installer') != 'pip': reason = 'not proven pip-owned'
        elif not item.get('direct_url'): reason = 'no longer a source or editable install'
        elif not paths: reason = 'ownership metadata unavailable'
        else:
            evidence = [owners.get(value) for p in paths for value in (str(p), str(p.resolve()))]
            if any(e is None for e in evidence): reason = 'system ownership could not be checked'
            elif any(evidence): reason = 'owned by the system package manager'
        # Snapshot relevant provenance and file identities; never display URLs
        # (which can contain credentials) or trust the manifest's historical flag.
        evidence = dict(name=name, version=version, installer=item.get('installer'),
                        source=item.get('direct_url'), location=location,
                        files={str(p): digest(p) for p in paths})
        proof = hashlib.sha256(json.dumps(evidence, sort_keys=True).encode()).hexdigest()
        records[policies.identity(name, 'pip')] = dict(name=name, version=version, reason=reason, proof=proof)
    return records


def inspect(document):
    backend = scopes.make('pip')
    platform, scope = manifests.platform(), scopes.scope_id(backend)
    flagged = [(g,p) for g in document['groups'] for p in g['packages']
               if not p['enabled'] and p.get('reason') == REASON]
    needs_evidence = any(g['manager'] == 'pip' and platform in g['platforms'] and g['scope'] == scope for g,p in flagged)
    live, error = {}, ''
    if needs_evidence:
        try:
            with budget(45): live = provenance()
        except (Error, OSError, ValueError, KeyError, TypeError) as exc: error = str(exc)
    rows, proofs = [], {}
    for group, package in flagged:
        name = package['name']
        reason = ''
        if group['manager'] != 'pip': reason = 'source cleanup supports pip ownership only'
        elif platform not in group['platforms']: reason = 'different platform'
        elif group['scope'] != scope: reason = 'different Python scope'
        elif error: reason = error
        else:
            item = live.get(policies.identity(name,'pip'))
            reason = 'not currently installed' if item is None else item['reason']
            if not reason:
                try: validate_names([name], 'pip')
                except Error as exc: reason = str(exc)
            if not reason: proofs[name] = item['proof']
        rows.append(dict(name=name, manager=group['manager'], scope=group['scope'], eligible=not reason,
                         reason=reason, version=live.get(policies.identity(name,'pip'),{}).get('version','')))
    return backend, rows, proofs


def display(path, rows, cfg):
    from .reports import report
    ui = report(explicit=cfg.get('_explicit_color'), fallback=cfg.get('color','auto'))
    if ui:
        ui.heading('Review source installs'); ui.resource('Manifest', path)
    else: print('Review source installs\n  Manifest: '+str(path))
    for row in rows:
        status = 'can select for removal' if row['eligible'] else row['reason']
        text = row['name']+' · '+row['scope']+' · '+status
        if ui: ui.text(text, 'identity' if row['eligible'] else 'muted')
        else: print('  '+clean(text))
    if not rows:
        if ui: ui.text('No disabled source installs in this manifest.', 'muted')
        else: print('  No disabled source installs in this manifest.')


def terminal():
    try:
        with open('/dev/tty', 'r'), open('/dev/tty', 'w'): pass
    except OSError:
        raise Error('cleanup needs a terminal for selection and confirmation; use --dry-run to inspect') from None


def cli(args, cfg):
    if len(args.names) > 1: raise Error('Usage: pkgs cleanup [FILE] [--dry-run | --json]')
    if args.yes: raise Error('cleanup requires selection and confirmation; --yes cannot bypass review')
    if args.manager or args.global_scope or args.query or args.ignore_skip:
        raise Error('cleanup takes its package scope from the manifest and current Python environment')
    default = not args.names
    path = (manifests.default_path() if default else Path(args.names[0]).expanduser()).absolute()
    guard = manifests.guards(path, [path.parent/'profile.json'] if default else [])
    def check():
        guard()
        if default and manifests.default_path().absolute() != path:
            raise Error('active profile changed after preview; review again')
    document = manifests.load(path)
    with workflows.progress('Checking source install ownership', cfg):
        backend, rows, proofs = inspect(document)
    check()
    if args.json:
        print(json.dumps(dict(schema=1, manifest=str(path), packages=rows), indent=2, ensure_ascii=False))
        return 0
    display(path, rows, cfg)
    if args.dry_run: return 0
    candidates = [Package(r['name'], r['version'], REASON, True, r['version']) for r in rows if r['eligible']]
    if not candidates: return 0
    terminal()
    from .ui import pick
    selected = pick(candidates, backend, dict(cfg, external_detection=False))
    if not selected:
        print('Cancelled; no packages changed.'); return 0
    names = list(dict.fromkeys(p.name for p in selected))
    if any(n not in proofs for n in names): raise Error('selection is not in the reviewed cleanup candidates')
    # Native uninstall only. Install/update recipes do not authorize removal.
    item = workflows.plan(backend, 'uninstall', names, cfg, yes=True)
    workflows.display(item, cfg)
    if not workflows.confirm():
        print('Cancelled; no packages changed.'); return 0
    check()
    with budget(45), workflows.progress('Rechecking source install ownership', cfg): fresh = provenance()
    for name in names:
        record = fresh.get(policies.identity(name,'pip'))
        if not record or record['reason'] or record['proof'] != proofs[name]:
            raise Error(name+': installed provenance changed after preview; review again')
    check()
    rc = workflows.apply(item, cfg)
    if rc: return rc
    with budget(45): remaining = {policies.identity(p.name,'pip') for p in backend.installed()}
    if any(policies.identity(n,'pip') in remaining for n in names):
        raise Error('some selected packages remain installed; inspect the native uninstall result')
    print('Removed '+str(len(names))+' package(s). Manifest entries retained.')
    return 0

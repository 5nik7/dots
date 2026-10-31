"""Shared package plans and sequential execution, separate from file rollback."""
from dataclasses import dataclass, field
from contextlib import nullcontext
import os
import shlex
import sys
from .common import Error, Cache, budget, validate_names
from .catalog import invalidate_evidence
from .detect import SYSTEM, available
from . import policies, scopes, streams


@dataclass
class Plan:
    backend: object
    action: str
    names: list = field(default_factory=list)
    commands: list = field(default_factory=list)
    skipped: list = field(default_factory=list)
    error: str = ''

    def document(self):
        return dict(manager=self.backend.name, scope=self.backend.scope, action=self.action,
                    packages=self.names, commands=self.commands, skipped=self.skipped, error=self.error)


def progress(label, cfg):
    if cfg.get('_quiet_progress') or cfg.get('output') == 'raw': return nullcontext()
    try:
        from . import reports  # establishes the shared renderer import path
        from progress import Progress, configure
        configure(True)
        return Progress(label)
    except (ImportError, OSError): return nullcontext()


def plan(backend, action, names, cfg, *, yes=False, override=False, bulk=False):
    names = validate_names(names, backend.name)
    explicit = bool(names)
    skipped = []
    policy = cfg.get('policies', {}).get(backend.name, {})
    with budget(45), progress('Preparing '+action+' · '+backend.name, cfg):
        if action == 'uninstall':
            installed = {policies.identity(p.name, backend.name) for p in backend.installed()}
            missing = [n for n in names if policies.identity(n, backend.name) not in installed and not
                       (backend.name == 'apt' and any(i.partition(':')[0] == n for i in installed))]
            if missing: raise Error('Not installed in selected scope: '+', '.join(missing))
        elif action == 'upgrade' and (not names or backend.name == 'go'):
            expand = backend.name not in SYSTEM or bool(policy.get('skip') or policy.get('packages'))
            if expand:
                rows = scopes.inventory(backend, owned=backend.name == 'pip' and bulk)
                if backend.name == 'go' and names:
                    by_name = {alias: p.name for p, _, _ in rows for alias in (p.name, p.details['binary'])}
                    names = [by_name.get(n, n) for n in names]
                else:
                    names = [p.name for p, _, reason in rows if not reason]
                    skipped += [dict(package=p.name, reason=reason) for p, _, reason in rows if reason]
                if not names: return Plan(backend, action, skipped=skipped)
        if action in ('install','upgrade'):
            names, blocked = policies.selected(cfg, backend.name, names, override=override, explicit=explicit)
            skipped += [dict(package=n, reason='skipped by policy') for n in blocked]
            if blocked and not names: return Plan(backend, action, skipped=skipped)
        backend.bulk_system = action == 'upgrade' and not explicit and backend.name in SYSTEM
        backend.skipped_targets = [row['package'] for row in skipped]
        commands = policies.commands(backend, action, names, cfg, yes or action in ('upgrade', 'refresh'))
    return Plan(backend, action, names, commands, skipped)


def display(plan, cfg, *, stream=None):
    stream = stream or sys.stdout
    from .reports import report
    ui = report(explicit=cfg.get('_explicit_color'), fallback=cfg.get('color','auto'), stream=stream)
    title = plan.action.upper()+' · '+plan.backend.name+' · '+plan.backend.scope
    if ui:
        ui.heading(plan.action.capitalize()+' packages' if plan.action != 'refresh' else 'Refresh repositories')
        ui.field('Manager', plan.backend.name, 'identity')
        ui.field('Scope', plan.backend.scope)
    else: print(title, file=stream)
    for command in plan.commands:
        if ui:
            if ui.ui.width < 80:
                ui.text('Command', 'label')
                ui.text(shlex.join(command), 'identity')
            else: ui.field('Command', shlex.join(command), 'identity')
        else: print('  '+shlex.join(command), file=stream)
    for item in plan.skipped:
        text = item['package']+': '+item['reason']
        if ui: ui.field('Skipped', text, 'warning')
        else: print('  Skipped '+text, file=stream)
    if plan.error:
        if ui: ui.field('Failed', plan.error, 'error')
        else: print('  Failed: '+plan.error, file=stream)
    elif not plan.commands:
        if ui: ui.text('No package changes needed.', 'muted')
        else: print('  No package changes needed.', file=stream)
    stream.flush()


def confirm(yes=False):
    if yes: return True
    try:
        with open('/dev/tty', 'r+') as tty:
            tty.write('Proceed? [y/N] '); tty.flush()
            return tty.readline().strip().lower() in ('y','yes')
    except OSError:
        raise Error('No controlling terminal. Use --yes for an intentional noninteractive transaction.') from None


def apply(plan, cfg, *, data=False):
    if plan.error: return 1
    if not plan.commands: return 0
    try:
        for command in plan.commands:
            rc = streams.run(command, dict(cfg, _manager=plan.backend.name), unattended=plan.action in ('upgrade', 'refresh'),
                             env=getattr(plan.backend, 'operation_env', None), data=data)
            if rc: return rc if rc > 0 else 128-rc
        return 0
    finally:
        try:
            Cache(plan.backend.cache_key).clear()
            invalidate_evidence(plan.backend)
        except OSError: pass


def execute(backend, action, names, args, cfg):
    cfg = dict(cfg, _quiet_progress=args.dry_run or getattr(args,'json',False))
    item = plan(backend, action, names, cfg, yes=args.yes,
                override=getattr(args,'ignore_skip',False))
    display(item, cfg)
    if args.dry_run:
        print('Dry run: no packages changed.')
        return 0
    if not item.commands: return 0
    if action not in ('upgrade', 'refresh') and not confirm(args.yes):
        print('Cancelled; no packages changed.'); return 0
    return apply(item, cfg)


def upgrade(args, cfg):
    cfg = dict(cfg, _quiet_progress=args.dry_run)
    entries, failed = [], False
    with budget(45): selection = scopes.bulk(cfg)
    for manager, scope in selection:
        try:
            if not available(manager): raise Error('configured manager is unavailable')
            with budget(45):
                backend = scopes.make(manager, scope)
                item = plan(backend, 'upgrade', [], cfg, override=args.ignore_skip, bulk=True)
            display(item, cfg)
            rc = 0 if args.dry_run else apply(item, cfg)
            entries.append((manager, 'failed' if rc else 'planned' if args.dry_run else 'complete' if item.commands else 'unchanged'))
            failed |= bool(rc)
        except (Error, OSError, ValueError) as error:
            print('pkgs: '+manager+': '+str(error), file=sys.stderr)
            entries.append((manager, 'failed')); failed = True
    from .reports import report
    ui = report(explicit=cfg.get('_explicit_color'), fallback=cfg.get('color','auto'))
    if ui:
        ui.heading('Upgrade summary', len(entries))
        for manager, status in entries: ui.field(manager, status, 'error' if status == 'failed' else 'success')
    else:
        print('Upgrade summary')
        for manager, status in entries: print('  '+manager+': '+status)
    if not entries: print('No supported user-wide managers found.')
    return int(failed)

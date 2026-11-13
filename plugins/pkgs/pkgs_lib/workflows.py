"""Shared package plans and sequential execution, separate from file rollback."""
from .common import human_message
from dataclasses import dataclass, field
from contextlib import contextmanager, nullcontext
import os
import shlex
import sys
from .common import Error, Cache, budget, validate_names
from .catalog import invalidate_evidence
from .detect import SYSTEM, available
from . import policies, scopes, streams


# Invoking these commands (or accepting an install selection) authorizes execution.
UNATTENDED_ACTIONS = frozenset(('install', 'upgrade', 'refresh'))


@dataclass
class Plan:
    backend: object
    action: str
    names: list = field(default_factory=list)
    commands: list = field(default_factory=list)
    skipped: list = field(default_factory=list)
    error: str = ''
    steps: list = field(default_factory=list)
    failed: list = field(default_factory=list)
    completed: list = field(default_factory=list)

    def document(self):
        return dict(manager=self.backend.name, scope=self.backend.scope, action=self.action,
                    packages=self.names, commands=self.commands, skipped=self.skipped, error=self.error)


def _progress(label, cfg):
    if cfg.get('_quiet_progress') or cfg.get('output') == 'raw': return nullcontext()
    try:
        from . import reports  # establishes the shared renderer import path
        from progress import Progress, configure
        from .presentation import styles
        configure(True)
        colors=styles()
        return Progress(label,marker_style=colors['spinner'],label_style=colors['progress'])
    except (ImportError, OSError): return nullcontext()


@contextmanager
def progress(label, cfg):
    with _progress(label, cfg) as meter:
        if meter is not None:
            completed, total = cfg.get('_progress_batch', (0, 0))
            meter.update(label + (' · managers' if total else ''), completed, total)
        yield meter


def plan(backend, action, names, cfg, *, yes=False, override=False, bulk=False):
    names = validate_names(names, backend.name)
    explicit = bool(names)
    skipped = []
    policy = cfg.get('policies', {}).get(backend.name, {})
    backend.automatic_upgrade = action == 'upgrade' and not explicit
    backend.update_system = (backend.name == 'gem' and backend.automatic_upgrade and
                             cfg.get('upgrade', {}).get('gem_system', True) and
                             'replace' not in policy.get('upgrade', {}))
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
                if backend.name == 'go': backend.go_rows = [p for p, _, _ in rows]
                if backend.name == 'go' and names:
                    by_name = {alias: p.name for p, _, _ in rows for alias in (p.name, p.details['binary'])}
                    names = [by_name.get(n, n) for n in names]
                else:
                    names = [p.name for p, _, reason in rows if not reason]
                    skipped += [dict(package=p.name, reason=reason) for p, _, reason in rows if reason]
                if not names and not backend.update_system: return Plan(backend, action, skipped=skipped)
        if action in ('install','upgrade'):
            names, blocked = policies.selected(cfg, backend.name, names, override=override, explicit=explicit)
            skipped += [dict(package=n, reason='skipped by policy') for n in blocked]
            if blocked and not names and not backend.update_system: return Plan(backend, action, skipped=skipped)
        if backend.name == 'go' and action == 'upgrade' and 'replace' not in policy.get(action, {}):
            # Reuse the read-only version comparison from upgrade --list.
            # Replacement recipes own their update/rebuild semantics.
            from . import go_tools, outdated
            replacements = {policies.identity(n, 'go') for n, rules in policy.get('packages', {}).items()
                            if 'replace' in rules.get(action, {})}
            native = go_tools.select([n for n in names if n not in replacements], backend.go_rows)
            with progress('Checking updates · go', cfg):
                newer = {p['name'] for p in outdated.candidates(backend, native)} if native else set()
            names = [n for n in names if n in replacements or n in newer]
            if not names: return Plan(backend, action, skipped=skipped)
        backend.bulk_system = action == 'upgrade' and not explicit and backend.name in SYSTEM
        backend.skipped_targets = [row['package'] for row in skipped]
        steps = policies.pip_upgrade_steps(backend, names, cfg, True) if backend.name == 'pip' and action == 'upgrade' else []
        commands = ([command for _, group in steps for command in group] if steps else
                    policies.commands(backend, action, names, cfg, yes or action in UNATTENDED_ACTIONS))
    return Plan(backend, action, names, commands, skipped, steps=steps)


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
    if os.name == 'nt':
        if not sys.stdin.isatty(): raise Error('Use --yes for an intentional noninteractive transaction.')
        return input('Proceed? [y/N] ').strip().lower() in ('y', 'yes')
    try:
        with open('/dev/tty', 'r') as source, open('/dev/tty', 'w') as target:
            target.write('Proceed? [y/N] '); target.flush()
            return source.readline().strip().lower() in ('y','yes')
    except OSError:
        raise Error('No controlling terminal. Use --yes for an intentional noninteractive transaction.') from None


def apply(plan, cfg, *, data=False):
    if plan.error: return 1
    if not plan.commands: return 0
    output = cfg.get('_upgrade_output')
    if output: output.commands_progress(0, len(plan.commands))
    try:
        if plan.steps: return apply_steps(plan, cfg, data=data)
        for index, command in enumerate(plan.commands, 1):
            if hasattr(plan.backend,'revalidate'): plan.backend.revalidate()
            rc = streams.run(command, dict(cfg, _manager=plan.backend.name), unattended=plan.action in UNATTENDED_ACTIONS,
                             env=getattr(plan.backend, 'operation_env', None), data=data)
            if output: output.commands_progress(index, len(plan.commands))
            if rc: return rc if rc > 0 else 128-rc
        return 0
    finally:
        try:
            Cache(plan.backend.cache_key).clear()
            invalidate_evidence(plan.backend)
        except OSError: pass


def apply_steps(plan, cfg, *, data=False):
    """Continue independent pip targets; never replay a failed recipe or hook."""
    failed = 0
    plan.failed.clear(); plan.completed.clear()
    output = cfg.get('_upgrade_output')
    processed = 0
    for names, commands in plan.steps:
        if not names and failed: break  # Manager after-hooks require full success.
        rc = 0
        if output: output.target = names[0] if names else ''
        for command in commands:
            if output: output.begin_command()
            try:
                if hasattr(plan.backend, 'revalidate'): plan.backend.revalidate()
                rc = streams.run(command, dict(cfg, _manager=plan.backend.name),
                                 unattended=True, env=getattr(plan.backend, 'operation_env', None), data=data)
            except (Error, OSError, ValueError) as error:
                if not names: raise
                rc = 1
                if output: output.line('error: '+str(error), '\n', sys.stderr)
                else: print('pkgs: '+names[0]+': '+str(error), file=sys.stderr)
            rc = rc if rc >= 0 else 128-rc
            if output: output.end_command(rc)
            processed += 1
            if output: output.commands_progress(processed, len(plan.commands))
            if rc in (130, 143): raise KeyboardInterrupt
            if rc: break
        if rc:
            if not names: return rc
            plan.failed.append((names[0], rc))
            if not output: print('pkgs: '+names[0]+' failed (exit '+str(rc)+'); continuing.', file=sys.stderr)
            failed = failed or rc
        else: plan.completed.extend(names)
    return failed


def execute(backend, action, names, args, cfg):
    cfg = dict(cfg, _quiet_progress=args.dry_run or getattr(args,'json',False))
    item = plan(backend, action, names, cfg, yes=args.yes,
                override=getattr(args,'ignore_skip',False))
    if action in ('install', 'upgrade', 'uninstall'):
        from . import upgrade_output
        if upgrade_output.enabled(args, cfg):
            upgrade_output.heading(cfg, backend, action=action)
            if action == 'uninstall' and item.commands and not args.yes:
                upgrade_output.packages(cfg, 'Manager', [backend.name])
                upgrade_output.packages(cfg, 'Remove', item.names)
                if not confirm(args.yes):
                    human_message('Cancelled; no packages changed.','muted'); return 0
            return apply_compact(item, cfg)
    display(item, cfg)
    if args.dry_run:
        human_message('Dry run: no packages changed.','muted')
        return 0
    if not item.commands: return 0
    if action not in UNATTENDED_ACTIONS and not confirm(args.yes):
        human_message('Cancelled; no packages changed.','muted'); return 0
    return apply(item, cfg)


def installed_versions(backend):
    """Bound local summary queries without changing transaction eligibility/status."""
    try:
        with budget(15):
            rows = backend.installed()
            if getattr(backend, 'update_system', False):
                from .common import Package, run
                rows = [*rows, Package('RubyGems', run(['gem', '--version'], env=getattr(backend,'operation_env',None)).strip())]
        versions = {}
        for package in rows:
            if package.details.get('disabled_reason'): continue
            identity = policies.identity(package.name, backend.name)
            version = package.installed_version or package.version
            if not isinstance(version, str) or not version or identity in versions:
                return None
            versions[identity] = (package.name, version)
        return versions
    except (Error, OSError, ValueError, KeyError, TypeError, AttributeError):
        return None


def changed_packages(item, before, after):
    if before is None or after is None: return None
    manager = item.backend.name
    selected = {policies.identity(name, manager) for name in item.names}
    if selected and getattr(item.backend,'update_system',False): selected.add('RubyGems')
    skipped = {policies.identity(row['package'], manager) for row in item.skipped}
    def aliases(name):
        return {name, name.partition(':')[0]} if manager == 'apt' else {name}
    return sorted((display for name, (display, version) in after.items()
                   if name in before and version != before[name][1]
                   and (not selected or aliases(name) & selected)
                   and not aliases(name) & skipped), key=str.casefold)


def apply_compact(item, cfg):
    from .upgrade_output import Output, STAGES
    stage = STAGES[item.action]
    before = None
    if item.action == 'upgrade' and item.commands and not item.error:
        with progress(item.backend.name+' · Reading installed versions', cfg):
            before = installed_versions(item.backend)
    with progress(item.backend.name+' · '+stage, cfg) as meter:
        output = Output(item.backend.name, cfg, meter, action=item.action)
        if item.error: output.errors.append(item.error)
        try:
            try: rc = apply(item, dict(cfg, _upgrade_output=output))
            except (Error, OSError, ValueError) as error:
                output.errors.insert(0,str(error)); rc = 1
                output.extra += max(0,len(output.errors)-2)
                del output.errors[2:]
        finally:
            output.close()
    if item.backend.name == 'npm' and output.pending:
        rc = output.pending.review(item, cfg, output, rc)
    if item.action == 'upgrade' and item.commands and (not rc or item.completed):
        after = None
        if before is not None:
            with progress(item.backend.name+' · Checking updated packages', cfg):
                after = installed_versions(item.backend)
        output.updated = changed_packages(item, before, after)
        if rc and output.updated is not None:
            completed = {policies.identity(name, item.backend.name) for name in item.completed}
            output.updated = [name for name in output.updated if policies.identity(name, item.backend.name) in completed]
    output.failed = item.failed
    output.partial_result = bool(rc and item.completed)
    output.result(rc, skipped=len(item.skipped), unchanged=not item.commands, names=item.names)
    return rc


def upgrade(args, cfg):
    cfg = dict(cfg, _quiet_progress=args.dry_run or getattr(args, 'json', False))
    from . import upgrade_output
    compact = upgrade_output.enabled(args, cfg)
    if compact: upgrade_output.heading(cfg)
    entries, failed = [], False
    with budget(45), progress('Finding upgrade managers', cfg): selection = scopes.bulk(cfg)
    for index, (manager, scope) in enumerate(selection):
        manager_cfg = dict(cfg, _progress_batch=(index, len(selection)))
        try:
            if not available(manager): raise Error('configured manager is unavailable')
            with budget(45):
                backend = scopes.make(manager, scope)
                item = plan(backend, 'upgrade', [], manager_cfg, override=args.ignore_skip, bulk=True)
            if compact: rc = apply_compact(item, manager_cfg)
            else:
                display(item, cfg)
                rc = 0 if args.dry_run else apply(item, cfg)
            entries.append((manager, 'failed' if rc else 'planned' if args.dry_run else 'complete' if item.commands else 'unchanged'))
            failed |= bool(rc)
        except (Error, OSError, ValueError) as error:
            if compact:
                output = upgrade_output.Output(manager, cfg)
                output.errors.append(str(error)); output.result(1)
            else: print('pkgs: '+manager+': '+str(error), file=sys.stderr)
            entries.append((manager, 'failed')); failed = True
    if compact:
        if not entries: human_message('No supported user-wide managers found.','muted')
        return int(failed)
    from .reports import report
    ui = report(explicit=cfg.get('_explicit_color'), fallback=cfg.get('color','auto'))
    if ui:
        ui.heading('Upgrade summary', len(entries))
        for manager, status in entries: ui.field(manager, status, 'error' if status == 'failed' else 'success')
    else:
        print('Upgrade summary')
        for manager, status in entries: print('  '+manager+': '+status)
    if not entries: human_message('No supported user-wide managers found.','muted')
    return int(failed)

"""Mutation preparation, interactive save and read-only module display."""
import os
import shutil
import sys


def interactive(core, app):
    if app.args.json or not sys.stdin.isatty() or not sys.stdout.isatty():
        raise core.Failure('This operation requires a human terminal; specify explicit targets instead', 2)


def answer(prompt, ui=None):
    if ui:
        ui.prompt(prompt)
    else:
        print(prompt, end=' ', file=sys.stderr, flush=True)
    return sys.stdin.readline().strip().lower()


def confirm(core, prompt, ui=None):
    while True:
        value = answer(prompt, ui)
        if value in ('y','yes'):
            return
        if value in ('','n','no') or '\x1b' in value:
            raise core.Failure('Cancelled; no files changed', 130)
        message = 'Enter y/yes to confirm, or n/no/Enter to cancel.'
        if ui:
            ui.text(message, 'warning')
        else:
            print(message, file=sys.stderr)


def report(app, operation, targets=(), actions=(), unresolved=()):
    if app._active is not None and app.config != app.configured_config:
        access = 'write' if app.args.command in {'apply','pick','restore','module-load','edit'} else 'read'
        actions = [*actions, 'preserve active link '+str(app.configured_config)+'; '+access+' target '+str(app.config)]
    result = {'dry_run':True, 'operation':operation, 'targets':[str(p) for p in targets],
              'actions':list(actions), 'unresolved':list(unresolved)}
    ui = app.report()
    if ui:
        ui.heading('Dry run: ' + operation)
        for target in targets:
            ui.resource('Target', target)
        for action in actions:
            ui.field('Action', action)
        for missing in unresolved:
            ui.field('Unresolved', missing, 'warning')
        ui.text('No changes made.', 'muted')
        return 0
    lines = ['Dry run: '+operation]+['  '+str(p) for p in targets]+['  '+x for x in actions]+['  Unresolved: '+x for x in unresolved]
    app.emit(result, '\n'.join(lines))
    return 0


def inspect_destination(core, app, target, *, active=False, deleting=False):
    if active:
        app.check_active()
    core.inspect_parents(target.parent)
    if core.exists(target):
        if target.is_symlink() and active and app.args.replace_link:
            core.regular(target, links=True)
        else:
            core.regular(target)
        if not active:
            try:
                if app.config.samefile(target):
                    raise core.Failure('This stored file is the active config or its symlink target; use a separate active path')
            except FileNotFoundError:
                pass
        if not active and not deleting and not app.args.force:
            raise core.Failure('Destination exists; use --force to back it up and replace it: '+str(target))
    elif deleting:
        raise core.Failure('File not found: '+str(target))
    core.inspect_parents(app.backups)
    return core.fingerprint(target)


def check_locks(core, app):
    paths = [app.root/'.operation.lock']
    if app.args.command in ('apply','pick','restore','module-load','edit','active-save'):
        paths.append(app.config.parent/('.'+app.config.name+'.blastoff.lock'))
    for p in paths:
        core.inspect_parents(p.parent)
        if core.exists(p):
            raise core.Failure('Another operation or a stale lock exists: '+str(p)+'; inspect before removing it.')


def save_choice(core, app, provenance, previous):
    candidate = provenance.target(core, app, previous)
    if app.args.dry_run:
        return candidate
    interactive(core, app)
    ui = app.report(sys.stderr)
    if ui:
        ui.heading('Save active theme')
    if candidate:
        while True:
            value = answer('Save edits to "'+candidate.stem+'"? [y/as/N]', ui)
            if value in ('y','yes'):
                app.args.force = True
                app.confirmed_expected = core.fingerprint(candidate)
                return candidate
            if value in ('a','as'):
                break
            if value in ('','n','no') or '\x1b' in value:
                raise core.Failure('Save cancelled.', 130)
            if ui:
                ui.text('Use y/yes, a/as, or n/no/Enter.', 'warning')
            else:
                print('Use y/yes, a/as, or n/no/Enter.', file=sys.stderr)
    else:
        message = 'No unchanged local destination is known; save a local copy or cancel.'
        if ui:
            ui.text(message, 'warning')
        else:
            print(message, file=sys.stderr)
    while True:
        if ui:
            ui.prompt('Save as theme name (empty cancels):')
        else:
            print('Save as theme name (empty cancels): ', end='', file=sys.stderr, flush=True)
        value = sys.stdin.readline().strip()
        if not value or '\x1b' in value:
            raise core.Failure('Save cancelled.', 130)
        try:
            target = app.themes/(core.name(value)+'.toml')
        except core.Failure as e:
            if ui:
                ui.text(str(e), 'error')
            else:
                print(str(e), file=sys.stderr)
            continue
        core.inspect_parents(target.parent)
        before = core.fingerprint(target)
        if before is not None:
            core.regular(target)
            confirm(core, 'Replace existing theme "'+value+'"? [y/N]', ui)
            if core.fingerprint(target) != before:
                raise core.Failure('Destination changed during confirmation; refusing overwrite')
            app.args.force = True
        app.confirmed_expected = before
        return target


def show_module(core, app):
    n = app.args.name
    if n is None:
        if app.args.dry_run:
            return report(app, 'module show', unresolved=['choose a module or supply NAME'])
        interactive(core, app)
        core.inspect_parents(app.modules)
        values = ['module:'+p.stem for p in app.files(app.modules)]
        if not values:
            raise core.Failure('No saved modules available')
        if not shutil.which('fzf'):
            raise core.Failure('fzf is required to browse modules; use module show NAME', 3)
        selected = core.ui_module('picker_ui').choose_fzf(values, app.modules, app.color, os.environ,
                    kind='module', fancy=app.args.fancy, diagnostic=app.diagnostic)
        if selected is None:
            raise core.Failure('Selection cancelled', 130)
        n = selected.split(':',1)[1]
    p = app.modules/(core.name(n)+'.toml')
    core.inspect_parents(p.parent)
    data = core.read(p)
    text = data.decode('utf-8-sig')
    if app.args.json:
        app.emit({'name':n, 'path':str(p), 'toml':text})
    elif not sys.stdout.isatty():
        sys.stdout.buffer.write(data)
    else:
        app.emit({}, 'Module: '+n)
        preview = core.ui_module('preview')
        print(preview.highlight(preview.clean(text), app.color, shutil.which('bat')), end='')
    return 0


def run(core, app):
    args = app.args
    cmd, action = args.command, getattr(args,'action',None)
    operation = cmd+(' '+action if action else '')
    if cmd == 'backup' and action == 'delete':
        return core.ui_module('backups').delete(core, app)
    if cmd == 'theme' and action == 'edit':
        return core.ui_module('editor').edit(core, app)
    if cmd == 'pick' and args.dry_run:
        return report(app, operation, [app.config], ['apply selected theme; back up changed config'], ['theme selection'])
    provenance = core.ui_module('provenance')
    previous, _ = provenance.read_record(core, app)
    observed_provenance = previous
    target = data = origin = None
    read_config = False
    active_before = core.fingerprint(app.config) if (cmd == 'theme' and action == 'save') else None
    if cmd in ('theme','preset'):
        if action in ('apply','copy') or (cmd == 'preset' and action == 'save'):
            value = ('preset:'+args.name if action == 'apply' else 'preset:'+args.source) if cmd == 'preset' else (args.name if action == 'apply' else args.source)
            local = app.themes/(value.removeprefix('local:')+'.toml')
            preset = value.startswith('preset:') or (not value.startswith('local:') and not core.exists(local))
            if args.dry_run and preset:
                core.name(value.removeprefix('preset:'))
                target = app.config if action == 'apply' else app.themes/(core.name(args.name)+'.toml')
                if action == 'apply': args.command = 'apply'
                inspect_destination(core,app,target,active=action=='apply')
                check_locks(core,app)
                return report(app, operation,[target],['validate generated TOML and back up replaced content'],['preset generation/availability deferred (no subprocesses)'])
            data = app.source(value)
            if action == 'apply':
                args.command = 'apply'; origin = app.loaded_source
            else:
                target = app.themes/(core.name(args.name)+'.toml')
        elif action == 'save':
            if args.name is not None: core.name(args.name)
            if args.name is None and not args.dry_run: interactive(core,app)
            data = core.read(app.config, links=True); core.parsed(data); read_config = True
            if args.name is None:
                # Capture the known destination before prompting, not afterward.
                known = provenance.target(core, app, previous)
                known_before = core.fingerprint(known) if known else None
                target = save_choice(core,app,provenance,previous)
                if args.dry_run:
                    args.command = 'active-save'
                    check_locks(core, app)
                    state = provenance.location(app)
                    core.inspect_parents(state.parent)
                    for member in (state, state.with_suffix('.pending')):
                        if core.exists(member): core.regular(member)
                    if target:
                        args.force = True
                        inspect_destination(core,app,target)
                    return report(app, operation, [target] if target else [], ['back up and save active edits'] if target else [], ['confirmation'] if target else ['local destination name'])
                if target == known and core.fingerprint(target) != known_before:
                    raise core.Failure('Stored theme changed since loading/confirmation; use save-as')
            else:
                target = app.themes/(core.name(args.name)+'.toml')
                if previous and previous.get('save_target',{}):
                    if previous['save_target']['name'] == args.name and not provenance.target(core,app,previous):
                        app.diagnostic('Stored destination changed since loading; explicit destination/--force rules apply', 'warning')
            args.command = 'active-save'
        elif action == 'import':
            target = app.themes/(core.name(args.name)+'.toml'); data = core.read(core.path(args.path))
        elif action == 'delete':
            target = app.themes/(core.name(args.name)+'.toml')
    elif cmd == 'module':
        if action == 'save':
            active_before = core.fingerprint(app.config); read_config = True
            route = core.module_path(args.module)
            target = app.modules/(core.name(args.name or args.module.replace('.','-'))+'.toml')
            data = core.extract_module(core.read(app.config,links=True),route)
            if core.snippet_route(data) != route:
                raise core.Failure('Module must start with its own explicit table declaration; no files changed.')
        elif action == 'load':
            snippet = core.read(app.modules/(core.name(args.name)+'.toml')); core.snippet_route(snippet)
            args.command = 'module-load'
            active_before = core.fingerprint(app.config)
            active = core.read(app.config,links=True) if active_before else b''
            data = core.merge_module(active,snippet); read_config = True
        elif action == 'delete':
            target = app.modules/(core.name(args.name)+'.toml')
    elif cmd == 'backup' and action == 'restore':
        ident = core.name(args.id)
        meta = core.backup_metadata(app.backups/(ident+'.json'))
        if meta.get('kind') != 'config':
            raise core.Failure('Only config backups can be restored; use theme import for stored-theme backups, or inspect and copy stored-module backups')
        data = core.read(app.backups/(ident+'.toml'))
        if provenance.digest(data) != meta.get('sha256'):
            raise core.Failure('Backup checksum mismatch')
        restored = meta.get('provenance')
        try:
            previous = restored if provenance.valid(core, app, restored) else None
        except (core.Failure,TypeError,AttributeError):
            previous = None
        if previous is None: origin = {'kind':'unknown'}
        args.command = 'restore'
    elif cmd == 'pick':
        data = app.source(app.pick()); origin = app.loaded_source
    elif cmd == 'backup':
        core.read(app.config,links=True)
    elif cmd == 'migrate':
        source = core.path(args.path)
        if not source.is_dir():
            raise core.Failure('Legacy theme directory not found: '+str(source))
        pending = [(app.themes/p.name, core.read(p)) for p in app.files(source)]
        for dest, content in pending:
            core.parsed(content)
            if core.exists(dest):
                raise core.Failure('Migration destination exists: '+str(dest)+'; resolve collisions first. No themes copied.')
            inspect_destination(core,app,dest)
    if data is not None: core.parsed(data)
    deleting = action == 'delete'
    if deleting and not args.force:
        raise core.Failure('Delete requires --force; a recoverable backup is created first.', 2)
    active_write = args.command in ('apply','pick','restore','module-load')
    if target is not None:
        expected = inspect_destination(core,app,target,deleting=deleting)
        if hasattr(app,'confirmed_expected') and expected != app.confirmed_expected:
            raise core.Failure('Destination changed after confirmation; refusing overwrite')
    elif active_write:
        expected = inspect_destination(core,app,app.config,active=True)
        if read_config and expected != active_before:
            raise core.Failure('Active config changed during operation; refusing overwrite')
    else:
        core.inspect_parents(app.backups)
    check_locks(core,app)
    if active_write or args.command == 'active-save':
        state = provenance.location(app)
        core.inspect_parents(state.parent)
        for p in (state, state.with_suffix('.pending')):
            if core.exists(p): core.regular(p)
    if read_config and core.fingerprint(app.config) != active_before:
        raise core.Failure('Active config changed during operation; refusing overwrite')
    if args.dry_run:
        targets = [target] if target else [app.config] if active_write else [p for p,_ in pending] if cmd=='migrate' else [app.backups]
        return report(app,operation,targets,['validate and '+('back up then delete' if deleting else 'back up replaced content and write atomically')])
    with app.mutate():
        if (active_write or args.command == 'active-save') and provenance.read_record(core, app)[0] != observed_provenance:
            raise core.Failure('Tracking changed during operation; review current origin and retry')
        if read_config and core.fingerprint(app.config) != active_before:
            raise core.Failure('Active config changed during operation; refusing overwrite')
        if active_write:
            with provenance.transaction(core,app) as commit:
                backup = app.active_write(data,expected=expected)
                commit(provenance.updated(core,app,previous,origin=origin))
            app.emit({'config':str(app.configured_config),'backup':backup},'Active config updated'+('; backup '+backup if backup else ''))
        elif target is not None:
            if core.fingerprint(target) != expected:
                raise core.Failure('Destination changed during operation; refusing overwrite')
            if deleting:
                inspect_destination(core,app,target,deleting=True)
                backup = app.backup(target,'stored')
                if core.fingerprint(target) != expected:
                    raise core.Failure('File changed during operation; refusing delete')
                core.inspect_parents(target.parent); target.unlink()
            elif args.command == 'active-save':
                with provenance.transaction(core,app) as commit:
                    backup = app.stored_write(target,data,expected=expected)
                    if core.fingerprint(app.config) != active_before:
                        raise core.Failure('Theme saved but active config changed; provenance not updated')
                    commit(provenance.updated(core,app,previous,save_target=target))
            else:
                backup = app.stored_write(target,data,expected=expected)
            ui = app.report()
            if ui:
                ui.heading('Save active theme')
                ui.field('Status', 'Saved', 'success')
                ui.resource('Theme', target)
                if backup:
                    ui.field('Backup', backup, 'identity')
            else:
                app.emit({'path':str(target),'backup':backup},str(target)+('; backup '+backup if backup else ''))
        elif cmd == 'backup':
            backup = app.backup(app.config,'config'); app.emit({'backup':backup},backup)
        elif cmd == 'migrate':
            for dest, content in pending:
                app.stored_write(dest,content,expected=None)
            app.emit({'copied':[str(p) for p,_ in pending], 'source_preserved':True},'Copied '+str(len(pending))+' themes; source preserved')
    return 0

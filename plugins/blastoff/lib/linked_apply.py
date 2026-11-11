"""Select a saved theme with a journaled link; never overwrite the old theme."""
import hashlib
import json
import os
from pathlib import Path
import uuid


def run(core, app, value):
    provenance = core.ui_module('provenance')
    configured = app.configured_config
    if any(configured.is_relative_to(directory) for directory in (app.themes, app.modules)):
        raise core.Failure('Active configuration must be outside the saved library; select a separate active link')
    core.inspect_parents(configured.parent)
    core.inspect_parents(app.themes)
    old_target = app.config if core.exists(configured) else None
    if old_target is not None:
        core.inspect_parents(old_target.parent)
    requested = value.removeprefix('local:').removeprefix('preset:')
    core.name(requested)
    preset = value.startswith('preset:') or (not value.startswith('local:') and not core.exists(app.themes/(requested+'.toml')))
    if app.args.dry_run and preset:
        return core.ui_module('operations').report(app, 'theme apply', [configured],
            ['materialize preset without replacing a local theme; back up and link active config'],
            ['preset generation/availability deferred (no subprocesses)'])
    data = app.source(value)
    origin = app.loaded_source
    source = app.themes/(origin['name']+'.toml')
    if preset:
        # Stable content-qualified names neither overwrite user themes nor make
        # a second apply create another saved copy.
        source = app.themes/('preset-'+origin['name']+'-'+hashlib.sha256(data).hexdigest()[:16]+'.toml')
    backups = core.ui_module('shared_backups')
    plan = backups.plan()
    plan.guard(configured)
    plan.guard(source)
    if core.exists(source):
        core.regular(source)
        if core.read(source) != data:
            raise core.Failure('Saved theme changed or preset storage name is occupied: '+str(source))
    else:
        plan.operations.append(dict(path=str(source), text=data.decode('utf-8-sig')))
    same = configured.is_symlink() and Path(os.path.abspath(configured.parent/os.readlink(configured))) == source
    record = dict(version=1, config=os.path.normcase(os.path.abspath(source)),
                  last_loaded=origin, save_target=origin if origin['kind']=='local' else None,
                  active_sha256=hashlib.sha256(data).hexdigest())
    destination = app.root/'state/provenance'/(provenance.digest(os.path.normcase(os.path.abspath(source)).encode())+'.json')
    previous, status = provenance.read_record(core, app)
    if same and not plan.operations and previous == record and destination.is_file() and status == 'tracked':
        if app.args.dry_run:
            return core.ui_module('operations').report(app, 'theme apply', [configured, source], ['active theme unchanged'])
        app.emit({'config':str(configured), 'backup':None}, 'Active theme unchanged')
        return 0
    backup = None
    if core.exists(configured) and not same:
        if configured.is_dir(): raise core.Failure('Active config is a directory: '+str(configured))
        if configured.is_symlink():
            # Keep the exact link object for bak restore; the app's backup
            # restore route intentionally restores the previous content.
            backup = plan.snapshot(configured, origin='blastoff-link')['id']
        if configured.exists():
            plan.guard(old_target)
            backup = backups.snapshot(core, app, old_target, 'config', plan)
    if not same:
        plan.operations.append(dict(path=str(configured), link=str(source)))
    core.inspect_parents(destination.parent)
    plan.guard(destination)
    plan.operations.append(dict(path=str(destination), text=json.dumps(record, sort_keys=True)+'\n'))
    # Keep one canonical record. Archive legacy configured-path records in the
    # same journal so conflicting aliases cannot authorize later overwrites.
    alias = app.root/'state/provenance'/(provenance.digest(os.path.normcase(os.path.abspath(configured)).encode())+'.json')
    if alias != destination:
        plan.guard(alias)
        if core.exists(alias):
            core.regular(alias)
            archived = alias.with_name(alias.stem+'.legacy-'+uuid.uuid4().hex+'.json')
            plan.guard(archived)
            plan.operations.extend([dict(path=str(archived), source=str(alias)), dict(path=str(alias), delete=True)])
    for tracked in dict.fromkeys((destination, alias)):
        pending = tracked.with_suffix('.pending')
        plan.guard(pending)
        if core.exists(pending):
            core.regular(pending)
            plan.operations.append(dict(path=str(pending), delete=True))
    plan.finish()
    if app.args.dry_run:
        return core.ui_module('operations').report(app, 'theme apply', [configured, source],
            ['back up active destination; link directly to saved theme; record origin'])
    lock_paths = list(dict.fromkeys((app.root/'.operation.lock',
        configured.parent/('.'+configured.name+'.blastoff.lock'),
        source.parent/('.'+source.name+'.blastoff.lock'))))
    if app._active is not None:
        lock_paths = list(dict.fromkeys([*lock_paths, app.config.parent/('.'+app.config.name+'.blastoff.lock')]))
    with core.locks(lock_paths):
        if app._active is not None: app._active.check()
        plan.apply('blastoff-theme-link')
    app.emit({'config':str(configured), 'backup':backup}, 'Active theme linked to '+str(source)+('; backup '+backup if backup else ''))
    return 0

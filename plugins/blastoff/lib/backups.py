"""Backup inventory and permanently deleting an explicitly authorized snapshot."""
import hashlib
import os
import shutil
import sys


def ids(core, app):
    core.inspect_parents(app.backups)
    if not app.backups.exists():
        return []
    values = set()
    for p in app.backups.iterdir():
        if p.suffix in ('.json','.toml'):
            try: values.add(core.name(p.stem))
            except core.Failure: pass
    return sorted(values)


def inspect(core, app, ident, *, verify=True):
    core.name(ident); core.inspect_parents(app.backups)
    meta_path = app.backups/(ident+'.json'); payload = app.backups/(ident+'.toml')
    size_bytes = None
    # Never trust source or link paths as deletion destinations.
    for p in (meta_path,payload):
        if core.exists(p):
            member_stat = core.regular(p)
            if p == payload:
                size_bytes = member_stat.st_size
            try:
                if app.config.samefile(p):
                    raise core.Failure('Backup member is the active config or its target: '+str(p))
            except FileNotFoundError: pass
    before_meta = core.fingerprint(meta_path)
    meta = core.backup_metadata(meta_path)
    if meta.get('id') != ident or meta.get('kind') not in ('config','stored') or not isinstance(meta.get('sha256'),str) or not core.re.fullmatch('[a-f0-9]{64}',meta['sha256']):
        raise core.Failure('Malformed backup metadata: '+ident)
    before_payload = core.fingerprint(payload) if verify else (True if core.exists(payload) else None)
    if verify and before_payload is not None and hashlib.sha256(core.read(payload)).hexdigest() != meta['sha256']:
        raise core.Failure('Backup checksum mismatch: '+ident)
    if core.fingerprint(meta_path) != before_meta or (verify and core.fingerprint(payload) != before_payload):
        raise core.Failure('Backup changed during inspection: '+ident)
    return {'id':ident, 'metadata':meta, 'missing_payload':before_payload is None,
            'expected':(before_payload,before_meta), 'size_bytes':size_bytes if before_payload is not None else None}


def listing(core, app):
    entries, failures, sizes = [], [], []
    for ident in ids(core,app):
        try:
            item = inspect(core,app,ident,verify=False)
            entries.append(dict(item['metadata'],missing_payload=item['missing_payload']))
            sizes.append(item['size_bytes'])
        except (core.Failure,OSError,ValueError) as e:
            failures.append({'id':ident,'error':str(e)})
    for failure in failures:
        app.diagnostic(failure['id']+': '+failure['error'], 'error')
    result = {'backups':entries,'errors':failures}
    status = 1 if failures else 0
    if app.args.json:
        app.emit(result)
        return status
    ui = app.report()
    if ui:
        core.ui_module('reports').backups(ui, entries, failures, sizes)
        return status
    lines = []
    import datetime
    import textwrap
    width = max(1, min(100, shutil.get_terminal_size((80,24)).columns))
    def field(label, value):
        return [(label+':', 'label'), (' ', None), (value, 'value')]
    for entry, size_bytes in zip(entries, sizes):
        ident = entry['id']
        try:
            # The writer uses gmtime and a literal Z, not local wall time.
            created_at = datetime.datetime.strptime(ident.split('-')[0], '%Y%m%dT%H%M%SZ').replace(tzinfo=datetime.timezone.utc)
            created = created_at.isoformat(sep=' ', timespec='seconds').removesuffix('+00:00')+' UTC'
        except ValueError:
            created = 'unknown'
        size = str(size_bytes)+' B' if size_bytes is not None else 'unavailable'
        if lines:
            lines.append([])
        lines += [[(ident, 'id')], [('  ', None), *field('Created', created)]]
        kind_row = [('  ', None), *field('Kind', entry['kind'])]
        size_fields = field('Size', size)
        combined = [*kind_row, (' ', None), ('|', 'separator'), (' ', None), *size_fields]
        if sum(len(text) for text, _ in combined) <= width:
            lines.append(combined)
        else:
            lines += [kind_row, [('  ', None), *size_fields]]
        for label in ('source','reason'):
            if label in entry:
                safe = ''.join(c if c.isprintable() else '?' for c in str(entry[label]))
                # Wrap plain text first; only the label gets the label accent.
                label_text = label.title()+':'
                rows = textwrap.wrap(label_text+' '+safe, width=max(len(label_text)+2, width),
                                     initial_indent='  ', subsequent_indent='    ')
                for index, row in enumerate(rows):
                    if index == 0:
                        lines.append([('  ', None), (label_text, 'label'), (row[2+len(label_text):], 'value')])
                    else:
                        lines.append([('    ', None), (row[4:], 'value')])
        if entry['missing_payload']: lines.append([('  Payload missing; metadata remains', None)])
    for failure in failures:
        if lines: lines.append([])
        lines.append([('Invalid backup '+failure['id']+': see stderr', None)])
    if entries:
        lines += [[], [(str(len(entries))+' backup(s)'+('; '+str(len(failures))+' invalid' if failures else ''), None)]]
    app.emit(result, styled_lines=lines or [[('No backups found', None)]])
    return status


def delete(core, app):
    args = app.args
    op = core.ui_module('operations')
    if (args.all or args.pick) and args.ids:
        raise core.Failure('Explicit IDs, --pick and --all are mutually exclusive',2)
    if not (args.all or args.pick or args.ids):
        raise core.Failure('Specify backup IDs, --pick or --all; use --dry-run to preview',2)
    if args.pick and args.dry_run:
        return op.report(app,'backup delete',unresolved=['backup picker selection'])
    if args.pick:
        op.interactive(core,app)
        if not shutil.which('fzf'):
            raise core.Failure('fzf is required for --pick; use explicit IDs or backup delete --all --dry-run',3)
    elif not args.dry_run and (args.json or not sys.stdin.isatty() or not sys.stdout.isatty()) and not args.yes:
        raise core.Failure('Noninteractive backup deletion requires explicit targets and --yes',2)
    selected = ids(core,app) if args.all or args.pick else list(dict.fromkeys(args.ids))
    entries = [inspect(core,app,ident,verify=not args.pick) for ident in selected]
    if args.pick:
        if not entries: raise core.Failure('No backups available')
        values = ['backup:'+item['id'] for item in entries]
        clean = core.ui_module('preview').clean
        labels = [clean(item['id']+' | '+item['metadata']['kind']+' | '+str(item['metadata'].get('source',''))+(' | payload missing' if item['missing_payload'] else '')).replace('\n',' ').replace('\t',' ') for item in entries]
        chosen = core.ui_module('picker_ui').choose_fzf(values,app.backups,app.color,os.environ,
                      kind='backup',multi=True,labels=labels,fancy=args.fancy,diagnostic=app.diagnostic)
        if not chosen: raise core.Failure('Selection cancelled',130)
        wanted = set(chosen)
        entries = [inspect(core,app,item['id']) for item in entries if 'backup:'+item['id'] in wanted]
    for item in entries:
        if item['missing_payload']:
            app.diagnostic(item['id']+': payload already missing; metadata only','warning')
    if args.dry_run:
        return op.report(app,'backup delete',[app.backups/(item['id']+suffix) for item in entries for suffix in ('.toml','.json')],['permanently remove '+str(len(entries))+' selected backup(s)'])
    if not args.json:
        app.emit({},'Selected backups ('+str(len(entries))+'):')
        for item in entries:
            app.emit({},'  '+item['id']+'  '+item['metadata']['kind'])
    if not entries:
        app.emit({'deleted':[],'count':0},'No backups to delete'); return 0
    if not args.yes:
        op.confirm(core,'Delete '+str(len(entries))+' selected backups permanently? [y/N]')
    deleted, failures = [], []
    with app.mutate():
        # Revalidate the WHOLE frozen set before the first irreversible unlink.
        for item in entries:
            if inspect(core,app,item['id'])['expected'] != item['expected']:
                raise core.Failure('Backup changed after selection; no backups deleted: '+item['id'])
        try:
            for item in entries:
                ident = item['id']
                try:
                    if inspect(core,app,ident)['expected'] != item['expected']:
                        raise core.Failure('Backup changed before deletion')
                    for suffix, expected in zip(('.toml','.json'),item['expected']):
                        p = app.backups/(ident+suffix)
                        core.inspect_parents(p.parent)
                        if core.fingerprint(p) != expected:
                            raise core.Failure('Backup member changed before deletion: '+str(p))
                        if expected is not None: p.unlink()
                    deleted.append(ident)
                except (core.Failure,OSError,ValueError) as e:
                    failures.append({'id':ident,'error':str(e)})
        except KeyboardInterrupt:
            app.diagnostic('Deletion interrupted; completed: '+', '.join(deleted)+'; inspect remaining pairs','warning')
            raise
    if failures:
        raise core.Failure('Partial backup deletion; deleted '+str(deleted)+'; failures '+str(failures))
    app.emit({'deleted':deleted,'count':len(deleted)},'Deleted '+str(len(deleted))+' backup(s)')
    return 0

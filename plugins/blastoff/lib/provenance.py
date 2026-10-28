"""Small path-associated provenance records; never discover the theme library."""
import contextlib
import hashlib
import json
import os
import uuid


def digest(data):
    return hashlib.sha256(data).hexdigest()


def serial(fp):
    if fp is None:
        return None
    return [x.hex() if isinstance(x, bytes) else x for x in fp]


def location(app, configured=False):
    identity = os.path.normcase(os.path.abspath(app.configured_config if configured else app.config))
    return app.root/'state/provenance'/(digest(identity.encode('utf-8'))+'.json')


def valid(core, app, doc):
    if not isinstance(doc, dict) or doc.get('version') != 1 or doc.get('config') not in {os.path.normcase(os.path.abspath(app.config)), os.path.normcase(os.path.abspath(app.configured_config))}:
        return False
    origin = doc.get('last_loaded')
    if not isinstance(origin, dict) or origin.get('kind') not in ('local','preset','unknown'):
        return False
    destination = doc.get('save_target')
    if destination is not None and (not isinstance(destination, dict) or destination.get('kind') != 'local'):
        return False
    for item in (origin, destination):
        if item is None or (isinstance(item,dict) and item.get('kind') == 'unknown'):
            continue
        if not isinstance(item, dict):
            return False
        core.name(item.get('name',''))
        if item.get('kind') == 'local':
            if item.get('path') != str(app.themes/(item['name']+'.toml')):
                return False
            if not isinstance(item.get('fingerprint'), list) or len(item['fingerprint']) != 6:
                return False
        if not isinstance(item.get('sha256'), str) or not core.re.fullmatch('[a-f0-9]{64}', item['sha256']):
            return False
    return isinstance(doc.get('active_sha256'), str) and bool(core.re.fullmatch('[a-f0-9]{64}', doc['active_sha256']))


def record_paths(app):
    return list(dict.fromkeys((location(app), location(app, configured=True))))


def read_record(core, app):
    try:
        documents = []
        for p in record_paths(app):
            core.inspect_parents(p.parent)
            if core.exists(p.with_suffix('.pending')):
                return None, 'incomplete operation; explicit apply/save/restore required'
            if not core.exists(p):
                continue
            if core.regular(p).st_size > 16384:
                return None, 'invalid tracking record'
            doc = json.loads(core.read(p))
            if not valid(core, app, doc):
                return None, 'invalid or unsupported tracking record'
            documents.append(doc)
        if not documents:
            return None, 'unknown (no tracking record)'
        fields = ('last_loaded', 'save_target', 'active_sha256')
        if any(any(d.get(k) != documents[0].get(k) for k in fields) for d in documents[1:]):
            return None, 'conflicting alias tracking; explicit apply/save/restore required'
        return documents[0], 'tracked'
    except (core.Failure, OSError, ValueError, TypeError, AttributeError):
        return None, 'invalid or unsafe tracking record'


def status(core, app, data):
    doc, state = read_record(core, app)
    result = {'status':state, 'origin':'unknown', 'last_loaded':None, 'save_target':None,
              'changed_since_load':None, 'external_change':None, 'matches_source':None}
    if doc:
        origin = doc['last_loaded']
        result.update(last_loaded=origin, save_target=doc.get('save_target'),
                      origin=origin['kind']+(':'+origin['name'] if 'name' in origin else ''))
        current = digest(data) if data is not None else None
        result['changed_since_load'] = current != origin.get('sha256') if origin['kind'] != 'unknown' else None
        result['external_change'] = current != doc['active_sha256']
        if data is None:
            result['status'] = 'active configuration missing'
        elif result['external_change']:
            result['status'] = 'active content changed outside Blastoff'
        elif result['changed_since_load']:
            result['status'] = 'edited; origin retained'
        if origin['kind'] == 'local':
            try:
                core.inspect_parents(app.themes)
                result['matches_source'] = digest(core.read(app.themes/(origin['name']+'.toml'))) == current
            except (core.Failure, OSError):
                result['status'] += '; source missing or unsafe'
    return result


def list_identity(core, app):
    """Read-only human-list annotation; never search for an untracked match.

    Stat snapshots detect ordinary concurrent replacements/edits without the
    repeated content reads in mutation fingerprints. This is an observation,
    not authorization for a later write.
    """
    observed = []

    def stamp(p, links=False):
        if not core.exists(p):
            return None
        def fields(s):
            return (s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        return (fields(p.lstat()), fields(p.stat()) if links else None)

    def observe(p, links=False):
        value = stamp(p, links)
        observed.append((p, links, value))
        return value

    unknown = {'identity':None, 'marker':None,
               'note':'Current theme: unknown. Use blastoff current for local matches.'}
    try:
        record = location(app)
        for record in record_paths(app):
            observe(record)
            observe(record.with_suffix('.pending'))
        doc, state = read_record(core, app)
        if not doc or doc['last_loaded']['kind'] == 'unknown':
            if doc:
                state = 'unknown origin'
            if not core.exists(app.config):
                unknown['note'] = 'Current theme: unavailable (active configuration missing).'
            else:
                unknown['note'] = 'Current theme: unknown ('+state+'). Use blastoff current for local matches.'
            return unknown
        origin = doc['last_loaded']
        result = {'identity':(origin['kind'], origin['name']), 'marker':None, 'note':None}
        reasons = []
        if observe(app.config, links=True) is None:
            reasons.append('active configuration missing')
        else:
            current = digest(core.read(app.config, links=True))
            if current != origin['sha256']:
                reasons.append('modified')
            if origin['kind'] == 'local':
                try:
                    source = app.themes/(origin['name']+'.toml')
                    core.inspect_parents(source.parent)
                    observe(source)
                    if digest(core.read(source)) != origin['sha256']:
                        reasons.append('source changed')
                except (core.Failure, OSError) as error:
                    app.diagnostic('Cannot inspect tracked theme: '+str(error))
                    reasons.append('source unavailable')
        if app._active is not None:
            app._active.check()
        if any(stamp(p, links) != before for p, links, before in observed):
            unknown['note'] = 'Current theme: unknown (files changed during inspection; retry list).'
            return unknown
        result['marker'] = 'last loaded; '+'; '.join(reasons) if reasons else 'current'
        return result
    except (core.Failure, OSError) as error:
        app.diagnostic('Cannot identify current theme: '+str(error))
        unknown['note'] = 'Current theme: unavailable (configuration or tracking could not be read).'
        return unknown


def target(core, app, doc):
    item = doc.get('save_target') if doc else None
    if not isinstance(item, dict):
        return None
    try:
        p = app.themes/(core.name(item['name'])+'.toml')
        core.inspect_parents(p.parent)
        core.regular(p)
        if serial(core.fingerprint(p)) == item['fingerprint']:
            return p
    except (core.Failure, OSError, KeyError):
        pass
    return None


def updated(core, app, previous, *, origin=None, save_target=None):
    doc = dict(previous or {})
    doc.update(version=1, config=os.path.normcase(os.path.abspath(app.config)),
               active_sha256=digest(core.read(app.config, links=True)),
               active_fingerprint=serial(core.fingerprint(app.config)))
    if origin is not None:
        doc['last_loaded'] = origin
        doc['save_target'] = origin if origin.get('kind') == 'local' else None
    else:
        doc.setdefault('last_loaded', {'kind':'unknown'})
    if save_target is not None:
        doc['save_target'] = {'kind':'local', 'name':save_target.stem, 'path':str(save_target),
                              'sha256':digest(core.read(save_target)), 'fingerprint':serial(core.fingerprint(save_target))}
    return doc


@contextlib.contextmanager
def transaction(core, app):
    """An incomplete marker prevents stale state authorizing a later overwrite."""
    p = location(app); marker = p.with_suffix('.pending')
    core.inspect_parents(p.parent)
    for candidate in (p, marker):
        if core.exists(candidate):
            core.regular(candidate)
    app._backup_origin = read_record(core,app)[0]
    expected = core.fingerprint(p)
    aliases = []
    for candidate in record_paths(app):
        if candidate == p:
            continue
        pending = candidate.with_suffix('.pending')
        for item in (candidate, pending):
            if core.exists(item): core.regular(item)
        aliases.append((candidate, core.fingerprint(candidate), core.fingerprint(pending)))
    core.atomic(marker, b'{"version":1}\n', core.fingerprint(marker))
    completed = False
    def commit(doc):
        nonlocal completed
        app._active.check()
        for alias, before, pending_before in aliases:
            if core.fingerprint(alias) != before or core.fingerprint(alias.with_suffix('.pending')) != pending_before:
                raise core.Failure('Alias tracking changed during operation')
        core.atomic(p, (json.dumps(doc, sort_keys=True)+'\n').encode(), expected)
        for alias, before, pending_before in aliases:
            if before is not None:
                os.replace(alias, alias.with_name(alias.stem+'.legacy-'+uuid.uuid4().hex+'.json'))
            pending = alias.with_suffix('.pending')
            if core.exists(pending):
                core.regular(pending)
                os.replace(pending, pending.with_name(pending.name+'.legacy-'+uuid.uuid4().hex))
        marker.unlink()
        completed = True
    try:
        yield commit
    except BaseException:
        app.diagnostic('Operation did not complete; tracking is untrusted. Inspect content and use explicit apply/save/restore to reestablish origin.', 'warning')
        raise
    finally:
        del app._backup_origin
        if not completed:
            app.diagnostic('Pending tracking marker: '+str(marker), 'warning')

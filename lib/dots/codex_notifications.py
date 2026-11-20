"""Data-only alert types, native settings and backwards-compatible key names."""
import codex_toast
import codex_vibration

TYPES = ('regular', 'finished')
GROUPS = {'toast': codex_toast, 'vibrate': codex_vibration}
LEGACY_KEYS = tuple(key for schema in GROUPS.values() for key in schema.KEYS)
KEYS = tuple('apps.codex.alerts.' + kind + '.' + group + '.' + field
             for kind in TYPES for group, schema in GROUPS.items() for field in schema.FIELDS)


def canonical(key):
    for group in GROUPS:
        prefix='apps.codex.'+group
        if key==prefix or key.startswith(prefix+'.'):
            return key.replace('apps.codex.', 'apps.codex.alerts.regular.', 1)
    return key


def split(key):
    key = canonical(key)
    if key not in KEYS:
        raise ValueError('unknown Codex alert configuration key: ' + key)
    return tuple(key.split('.')[3:])


def options(termux, kind='regular'):
    if kind not in TYPES:
        raise ValueError('unknown Codex alert type')
    source = termux if kind == 'regular' else termux.get('finished', {})
    if not isinstance(source, dict):
        raise ValueError('invalid finished notification settings')
    source = dict(source)
    if kind == 'finished':
        source.setdefault('toast_foreground', 'bright_green')
    result = dict(termux)
    for schema in GROUPS.values():
        result.update({schema.FIELDS[key]: value for key, value in schema.values(source).items()})
    return result


def values(termux):
    alerts = {kind: {group: schema.values(options(termux, kind))
                     for group, schema in GROUPS.items()} for kind in TYPES}
    # Existing JSON paths retain their values; there is only one native store.
    return dict(alerts['regular'], alerts=alerts)


def constraints(key):
    try:
        kind, group, field = split(key)
    except ValueError:
        return {}
    result = GROUPS[group].constraints('apps.codex.' + group + '.' + field)
    if kind == 'finished' and group == 'toast' and field == 'fg':
        result = dict(result, default='bright_green')
    return result

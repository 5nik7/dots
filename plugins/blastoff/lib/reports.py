"""Blastoff human reports; data collection and mutation stay in their owners."""
from pathlib import Path
import sys

# Fixed checkout-relative import also works with Blastoff's Python -I adapter.
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'lib/dots'))
from plugin_presentation import report


def current(ui, result):
    ui.heading('Current configuration')
    matches = result['matching_themes']
    ui.field('Matches', ', '.join(matches) if matches else
             '(no local match)' if result['exists'] else '(no active config)',
             'success' if matches else 'muted')
    ui.resource('Config', result['config'])
    ui.resource('Target', result['resolved_config'])
    ui.field('File', 'symlink' if result['symlink'] else
             'regular file' if result['exists'] else 'not found',
             'success' if result['exists'] else 'warning')
    ui.gap()
    ui.heading('Origin')
    ui.field('Last loaded', result['provenance']['origin'])
    tracking = result['provenance']['status']
    ui.field('Tracking', tracking, 'warning' if tracking != 'tracked' else 'success')


def themes(ui, result, identity):
    identified = False
    for index, (title, key, kind) in enumerate((('Themes', 'themes', 'local'), ('Presets', 'presets', 'preset'))):
        if index:
            ui.gap()
        ui.heading(title, len(result[key]))
        for name in result[key]:
            selected = identity['identity'] == (kind, name)
            spans = [(kind + ':', 'muted'), (name, 'identity')]
            if selected:
                marker = identity['marker']
                spans.append(('  [' + marker + ']', 'success' if marker == 'current' else 'warning'))
                identified = True
            ui.row(spans)
        if not result[key]:
            unavailable = key == 'presets' and result['preset_discovery']['status'] == 'unavailable'
            ui.text('Presets unavailable.' if unavailable else 'No ' + title.lower() + ' found.',
                    'warning' if unavailable else 'muted')
    if identity['identity'] and not identified:
        kind, name = identity['identity']
        ui.gap()
        ui.field('Origin', kind + ':' + name + ' [' + identity['marker'] + '; not listed]', 'warning')
    if identity['note']:
        ui.text(identity['note'], 'muted')


def doctor(ui, result):
    ui.heading('Blastoff doctor')
    ui.field('Version', result['version'])
    ui.field('Python', result['python'])
    ui.gap()
    ui.heading('Configuration')
    for label, key in (('Config', 'config'), ('Target', 'resolved_config'),
                       ('Storage', 'blastoff_home'), ('Themes', 'themes'), ('Modules', 'modules')):
        if result[key]:
            ui.resource(label, result[key], kind='dir' if key in ('blastoff_home', 'themes', 'modules') else None)
        else:
            ui.field(label, 'unavailable', 'warning')
    state = 'present' if result['config_exists'] else 'not found'
    ui.field('Status', state + (' (symlink)' if result['config_symlink'] else ''),
             'success' if result['config_exists'] else 'warning')
    ui.gap()
    ui.heading('Dependencies')
    for key in ('starship', 'fzf', 'gum'):
        if result[key]:
            ui.resource(key.upper(), result[key], kind='executable')
        else:
            ui.field(key.upper(), 'not found (needed for presets)' if key == 'starship' else 'not found (optional)', 'warning')


def backups(ui, entries, failures, sizes):
    import datetime
    ui.heading('Backups', len(entries))
    if not entries and not failures:
        ui.text('No backups found.', 'muted')
    for entry, size in zip(entries, sizes):
        ui.gap()
        ui.text(entry['id'], 'identity')
        try:
            created = datetime.datetime.strptime(entry['id'].split('-')[0], '%Y%m%dT%H%M%SZ')
            created = created.strftime('%Y-%m-%d %H:%M:%S UTC')
        except ValueError:
            created = 'unknown'
        ui.field('Created', created)
        ui.field('Kind', entry['kind'])
        ui.field('Size', str(size) + ' B' if size is not None else 'unavailable')
        if entry.get('source'):
            ui.resource('Source', entry['source'])
        if entry.get('reason'):
            ui.field('Reason', entry['reason'])
        if entry['missing_payload']:
            ui.text('Payload missing; metadata remains', 'warning')
    for failure in failures:
        ui.text('Invalid backup ' + failure['id'] + ': see stderr', 'error')
    if failures:
        ui.field('Invalid', len(failures), 'error')

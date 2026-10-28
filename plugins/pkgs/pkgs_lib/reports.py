"""Dots layouts for package inventories and diagnostics; no backend discovery."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'lib/dots'))
from plugin_presentation import report, color_mode
from resources import cells
from .grammar import MANAGERS


def label(key):
    return dict(default_manager='Default', configured_manager='Configured',
                pkgs_on_path='On PATH', virtual_env='Virtual env', installed_version='Installed',
                legacy_startup='Startup', in_supplied_fpath='In FPATH').get(key, key.replace('_', ' ').capitalize())


def managers(ui, rows):
    ui.heading('Package managers', len(rows))
    if not rows:
        ui.text('No supported package managers found.', 'muted')
    for item in rows:
        ui.gap()
        ui.text(item['manager'], 'identity')
        for key in ('scope', 'catalog', 'actions'):
            ui.field(key.title(), item[key])


def packages(ui, rows, backend, *, installed=False):
    ui.heading('Installed packages' if installed else 'Packages', len(rows))
    ui.field('Manager', backend.name, 'identity')
    ui.field('Scope', backend.scope)
    if not rows:
        ui.text('No packages match the selected manager and filters.', 'muted')
        return
    ui.text('[i] installed | [e] external commands', 'muted')
    ui.gap()
    name_width = min(30, max(12, max(cells(ui.ui.clean(p.name)) for p in rows)))
    for item in rows:
        name, version = ui.ui.clean(item.name), ui.ui.clean(item.version)
        state = ('[i]' if item.installed else 'not installed') + (' [e]' if item.external else '')
        if ui.ui.width >= 80 and cells(name) <= name_width and cells(version) <= 18:
            ui.row([(name + ' ' * (name_width - cells(name) + 2), 'identity'),
                    (version + ' ' * (20 - cells(version)), 'value'),
                    (state, 'success' if item.installed else 'muted')])
        else:
            ui.text(name, 'identity')
            ui.field('Version', version or 'unavailable')
            ui.field('Status', state, 'success' if item.installed else 'muted')
        if item.description:
            ui.row([(item.description, 'muted')], indent=4)


def doctor(ui, data):
    ui.heading('pkgs doctor')
    for key in ('version', 'environment', 'default_manager', 'configured_manager'):
        role = 'warning' if key == 'default_manager' and data[key] not in MANAGERS else 'value'
        ui.field(label(key), data[key], role)
    ui.gap()
    ui.heading('Runtime and paths')
    for key in ('python', 'launcher', 'pkgs_on_path', 'cwd', 'virtual_env'):
        value = data[key]
        if value not in ('missing', 'none', ''):
            ui.resource(label(key), value, kind='dir' if key in ('cwd', 'virtual_env') else 'executable')
        else:
            ui.field(label(key), value, 'warning' if value == 'missing' else 'muted')
    ui.field('Shadowed', data['command_shadowed'], 'warning' if data['command_shadowed'] else 'success')
    ui.gap()
    ui.heading('FZF')
    for key, value in data['fzf'].items():
        if key == 'path' and value:
            ui.resource('Path', value, kind='executable')
        else:
            role = ('success' if value else 'warning') if key in ('supported', 'with_shell') else 'value'
            ui.field(label(key), (value or 'missing') if key == 'path' else value, role)
    ui.gap()
    ui.heading('Completions', len(data['completions']))
    for item in data['completions']:
        ui.gap()
        ui.text(item['shell'], 'identity')
        for key, value in item.items():
            if key == 'shell':
                continue
            if key == 'file' or key == 'loader' and value not in ('not found', 'shell-owned setup', ''):
                ui.resource(label(key), value)
            else:
                role = 'value'
                if key == 'status':
                    role = 'success' if value == 'current' else 'warning'
                elif key in ('notice', 'activation'):
                    role = 'warning' if str(value).startswith('unavailable') or key == 'notice' else 'muted'
                ui.field(label(key), value, role)

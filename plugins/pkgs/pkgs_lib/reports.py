"""Dots layouts for package inventories and diagnostics; no backend discovery."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'lib/dots'))
from plugin_presentation import color_mode
from .presentation import report
from resources import cells
from .grammar import COMMANDS, DESCRIPTION, MANAGERS


def help_report(parser, argv, stream=None):
    """Use the parser's option records without querying managers or optional UIs."""
    explicit = None
    for index, arg in enumerate(argv):
        if arg == '--': break
        if arg.startswith('--color='): explicit = arg.partition('=')[2]
        elif arg == '--color' and index + 1 < len(argv): explicit = argv[index + 1]
    from .common import config, Error
    try: fallback = config()['color']
    except (Error, OSError, ValueError): fallback = 'auto'
    # Ordinary redirected help keeps argparse's text and avoids rendering.
    stream = sys.stdout if stream is None else stream
    ui = report(explicit, fallback=fallback, stream=stream)
    if ui is None: return False
    from help_adapters import HelpView
    help_ui = HelpView(stream, prog='pkgs', commands=tuple(COMMANDS))
    help_ui.color, help_ui.human = ui.ui.color, ui.ui.human
    help_ui.heading('pkgs')
    help_ui.text(DESCRIPTION.splitlines()[0], indent=2)
    help_ui.emit(); help_ui.heading('Usage')
    help_ui.text('pkgs COMMAND [ARG ...] [OPTIONS]', 'syntax', indent=2)
    help_ui.emit(); help_ui.heading('Commands')
    for name, description in COMMANDS.items():
        help_ui.help_row(name, description, kind='command', prog='pkgs',
                         commands=tuple(COMMANDS), label_width=12)
    help_ui.emit(); help_ui.heading('Options')
    for action in parser._actions:
        if not action.option_strings: continue
        label = ', '.join(action.option_strings)
        if action.nargs != 0:
            label += ' '+(action.metavar or {'manager':'NAME', 'color':'MODE'}.get(action.dest, action.dest.upper()))
        description = action.help or ''
        if help_ui.width >= 80:
            help_ui.help_row(label, description, kind='option', label_width=27)
        else:
            help_ui.text(label, 'option', indent=2)
            help_ui.text(description, indent=4)
    help_ui.emit(); help_ui.heading('Managers')
    spans=[]
    for manager in MANAGERS:
        if spans: spans.append((', ', 'value'))
        spans.append((manager, 'manager'))
    ui.row(spans)
    help_ui.emit(); help_ui.heading('Examples')
    examples = DESCRIPTION.split('Examples:\n', 1)[1].split('\n\n', 1)[0]
    for example in examples.splitlines(): help_ui.text(example.strip(), 'syntax', indent=2)
    help_ui.emit()
    help_ui.text('Install, upgrade and refresh run without an extra confirmation flag.', indent=2)
    help_ui.text('Install, uninstall and upgrade show brief results; --raw shows full manager output.', indent=2)
    help_ui.text('Pip upgrades continue after package failures; global npm scripts need separate approval.', indent=2)
    help_ui.text('Picker: Tab select, Ctrl-X preview, Alt-I installed, Alt-O homepage.', indent=2)
    return True


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
        ui.text(item['manager'], 'manager')
        for key in ('scope', 'catalog', 'actions'):
            ui.field(key.title(), item[key])


def manager_heading(ui, manager, scope, count):
    ui.ui.heading_spans([(manager, ui.styles['manager']), (' · '+scope, ui.styles['heading']),
                         (' (', ui.styles['muted']), (str(count), ui.styles['count']),
                         (')', ui.styles['muted'])])


def packages(ui, rows, backend, *, installed=False):
    ui.heading('Installed packages' if installed else 'Packages', len(rows))
    ui.field('Manager', backend.name, 'manager')
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
            ui.row([(name + ' ' * (name_width - cells(name) + 2), 'package'),
                    (version + ' ' * (20 - cells(version)), 'version'),
                    (state, 'success' if item.installed else 'muted')])
        else:
            ui.text(name, 'package')
            ui.field('Version', version or 'unavailable', 'version')
            ui.field('Status', state, 'success' if item.installed else 'muted')
        if item.description:
            ui.row([(item.description, 'muted')], indent=4)


def doctor(ui, data):
    ui.heading('pkgs doctor')
    for key in ('version', 'environment', 'default_manager', 'configured_manager'):
        role = ('manager' if key in ('default_manager', 'configured_manager') and data[key] in MANAGERS else
                'warning' if key == 'default_manager' and data[key] not in MANAGERS else 'value')
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

"""Read-only setup drafts. Only the lifecycle coordinator can apply a draft."""
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import sys

from catalog import Catalog, Presentation
from transactions import digest, parents_safe
from setup_components import COMPONENTS, DEFAULTS, component, validate
from interaction import Selector, SelectionEnded, terminal
from progress import clip


def arguments(parser):
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--interactive', action='store_true', help='open the setup wizard')
    mode.add_argument('--non-interactive', action='store_true', help='skip the wizard; writes require --yes')
    parser.add_argument('--component', action='append', choices=COMPONENTS, help='select components instead of defaults; repeat')
    parser.add_argument('--resource', action='append', help='select enabled catalog IDs within Files; repeat')
    parser.add_argument('--with-dependencies', action='store_true', default=None, help='offer mapped missing prerequisites before preparation')
    parser.add_argument('--save-choices', action='store_true', help='save successful choices in the active profile')
    parser.add_argument('--no-clear', action='store_true', help='retain the visible screen on wizard entry')
    parser.add_argument('--no-logo', action='store_true', help='omit the wizard logo')
    parser.add_argument('--fonts', metavar='FILE', help='restore exact choices from a font-preference document')
    parser.add_argument('--font-target', action='append', help='select saved font targets; repeat')


def read_document(path, guards, default):
    path = Path(path).expanduser().absolute()
    parents_safe(path)
    before = digest(path)
    if before is None:
        document = deepcopy(default)
    else:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 8*1024*1024:
            raise ValueError('setup input must be a bounded regular JSON file: ' + str(path))
        document = json.loads(path.read_text(encoding='utf-8'))
    if digest(path) != before:
        raise ValueError('setup input changed while reading: ' + str(path))
    guards.setdefault(str(path), before)
    return document


def defaults(root, installation, args):
    from config_values import Controls
    controls = Controls(root)
    for path in controls.paths:
        installation.guard(path)
    values = controls.values.get('apps', {}).get('setup', {})
    args.profile_directory = (Path(controls.selected['layers'][-1]['root'])
                              if controls.selected['layers'] else None)
    args.setup_controls = controls
    args.package_document = None
    args.font_document = None
    args.font_choices = []
    component_defaults = args.component is None
    if component_defaults:
        args.component = (values.get('components', list(DEFAULTS)) if args.action == 'install'
                          else sorted({entry.get('component', component(entry['id']))
                                       for entry in installation.entries.values()}))
    args.component = validate(args.component)
    if args.action == 'uninstall' and installation.receipt.get('font_targets') and 'fonts' not in args.component:
        # Receipt metadata can own a selection even when the app bytes matched.
        if component_defaults:
            args.component.append('fonts')
    if args.resource is None and args.action == 'install':
        args.resource = values.get('resources') or None
    if args.resource is not None and 'files' not in args.component:
        args.component.append('files')
    for enabled, name in ((args.packages, 'packages'), (args.fonts or args.font_target, 'fonts')):
        if enabled and name not in args.component:
            args.component.append(name)
    if args.with_dependencies is None:
        args.with_dependencies = values.get('dependencies', False) if args.action == 'install' else False
    args.setup_values = values


def selected_inputs(installation, args):
    if 'packages' in args.component and args.action == 'install' and args.package_document is None:
        path = args.packages or (args.profile_directory/'packages.json' if args.profile_directory else None)
        if args.packages and not Path(args.packages).expanduser().exists():
            raise ValueError('package manifest is missing: ' + args.packages)
        args.package_document = read_document(path, installation.guards, dict(schema=1, groups=[])) if path else dict(schema=1, groups=[])
    if 'fonts' in args.component and args.action == 'install' and args.font_document is None:
        path = args.fonts or (args.profile_directory/'fonts.json' if args.profile_directory else None)
        if args.fonts and not Path(args.fonts).expanduser().exists():
            raise ValueError('font preferences are missing: ' + args.fonts)
        args.font_document = read_document(path, installation.guards, dict(schema=1, applications={})) if path else dict(schema=1, applications={})


def pick_many(selector, title, records, selected):
    """Searchable stable rows; arbitrary labels never become command arguments."""
    selected = set(selected)
    original = set(selected)
    ids = {key for key, _ in records}
    width = max(12, shutil.get_terminal_size((80,24)).columns-18)
    while True:
        labels = {f'{i+1}. [{"x" if key in selected else " "}] {clip(Presentation.clean(label),width)[0]}': key
                  for i, (key, label) in enumerate(records)}
        choice = selector.pick('filter', title, ['Continue', 'Select all', 'Clear all', 'Back', *labels])
        if choice == 'Continue': return [key for key, _ in records if key in selected]
        if choice == 'Back': return [key for key, _ in records if key in original]
        if choice == 'Select all': selected = set(ids)
        elif choice == 'Clear all': selected.clear()
        elif labels[choice] in selected: selected.remove(labels[choice])
        else: selected.add(labels[choice])


def banner(root, args, ui):
    if not args.no_clear and args.setup_values.get('clear_screen', True) and os.environ.get('TERM') != 'dumb':
        ui.stream.write('\x1b[2J\x1b[H')
    path = root/'logo.txt'
    if not args.no_logo and args.setup_values.get('logo', True) and path.is_file():
        lines = [ui.clean(line) for line in path.read_text().splitlines()]
        if max(map(len, lines), default=0) <= ui.width:
            if ui.color:
                from style_config import Styles
                from text_gradient import gradient
                lines = gradient(lines, Styles(root).palette, horizontal=True)
            for line in lines: ui.emit(line)
    ui.heading('Dots ' + args.action)
    layers = args.setup_controls.selected['layers']
    profile = ([(layers[-1]['id'], '1;93'), (' (' + ui.path(args.profile_directory) + ')', '2;39')]
               if layers else [('checkout defaults', '2;39')])
    ui.detail_spans('Profile', profile)
    ui.emit(ui.paint('Select components, prepare optional work, then review managed changes.','92'))


def package_choices(selector, args):
    sys.path.insert(0, str(Path(args.setup_controls.root)/'plugins/pkgs'))
    from pkgs_lib.manifests import validate as validate_manifest
    document = validate_manifest(args.package_document)
    if not document['groups']:
        Presentation().emit('No saved packages. Supply --packages FILE or create a profile package manifest.')
        return
    while True:
        labels = {f"{i+1}. {g['manager']} / {g['scope']} ({sum(p['enabled'] for p in g['packages'])}/{len(g['packages'])})": g
                  for i, g in enumerate(document['groups'])}
        choice = selector.pick('choose', 'Package groups', ['Back', *labels])
        if choice == 'Back': break
        group = labels[choice]
        selected = pick_many(selector, 'Packages: '+group['manager'], [(p['name'], p['name']) for p in group['packages']],
                             [p['name'] for p in group['packages'] if p['enabled']])
        for package in group['packages']: package['enabled'] = package['name'] in selected
    args.package_document = document


def font_choices(selector, args):
    from fonts.config import TARGETS
    from fonts.model import Library
    from fonts.workspace import Workspace
    apps = args.font_document.get('applications', {})
    choice = selector.pick('choose', 'Fonts', ['Back', 'Select saved targets', 'Choose retained font'])
    if choice == 'Select saved targets':
        args.font_target = pick_many(selector, 'Saved font targets', [(k, k+' — '+v['id']) for k,v in apps.items()],
                                     args.font_target if args.font_target is not None else list(apps))
    elif choice == 'Choose retained font':
        library = Library()
        targets = [k for k in TARGETS if not (k == 'termux' and library.platform != 'termux'
                   or k == 'windows-terminal' and library.platform != 'windows'
                   or k == 'kitty' and library.platform == 'windows')]
        target = selector.pick('choose', 'Application target', ['Back', *targets])
        if target == 'Back': return
        choices = {}
        for plan in Workspace(library, None).all_stores():
            for identity, family in plan.document['families'].items():
                for version, record in family['versions'].items():
                    if record.get('available') is False: continue
                    for face in record['fonts']:
                        if target == 'termux' and not face['file'].lower().endswith('.ttf'): continue
                        label = Presentation.clean(f"{identity} / {version} / {face['file']}")
                        choices[label] = dict(id=identity, version=version, target=target, face=face['file'],
                                              variant=face['variant'])
        if not choices:
            Presentation().emit('No retained faces. Download/import fonts with dots fonts first, or supply exact saved preferences.')
            return
        choice = selector.pick('filter', 'Retained font face', ['Back', *sorted(choices)])
        if choice != 'Back':
            args.font_choices = [r for r in args.font_choices if r['target'] != target] + [choices[choice]]
            if args.font_target is None: args.font_target = list(apps)
            args.font_target = [t for t in args.font_target if t != target]


def run(root, installation, args):
    ui = Presentation()
    banner(root, args, ui)
    backend = 'gum' if shutil.which('gum') and (os.name == 'nt' or shutil.which('bash')) else 'plain'
    selector = Selector(backend)
    while True:
        choices = ['Review', 'Components: '+str(len(args.component))+' selected', 'Files: '+('all applicable' if args.resource is None else str(len(args.resource))) ]
        if args.action == 'install':
            choices += ['Packages', 'Fonts', 'Dependencies: '+('include' if args.with_dependencies else 'report only'),
                        'Save choices: '+('yes' if args.save_choices else 'no')]
        choice = selector.pick('choose', ui.paint('Setup preferences','96'), [*choices, 'Cancel'])
        if choice == 'Cancel': raise SelectionEnded(0)
        if choice == 'Review': break
        if choice.startswith('Components:'):
            allowed = list(COMPONENTS) if args.action == 'install' else sorted({e.get('component', component(e['id'])) for e in installation.entries.values()})
            if args.action == 'uninstall' and installation.receipt.get('font_targets') and 'fonts' not in allowed:
                allowed.append('fonts')
            args.component = pick_many(selector, 'Components', [(c,c) for c in allowed], args.component)
        elif choice.startswith('Files:'):
            if args.action == 'uninstall':
                ids = sorted({e['id'] for e in installation.entries.values() if component(e['id']) == 'files'})
                rows = [(key,key) for key in ids]
            else:
                catalog = Catalog(root, installation.platform)
                for path in catalog.input_paths(): installation.guard(path)
                rows = [(r['id'],r['id']+' — '+str(r.get('target') or r['status'])) for r in catalog.records()
                        if r['enabled'] and r['applicable'] and r['status'] not in ('replaced','conflict','unmapped','source-missing','source-broken-link')]
            args.resource = pick_many(selector, 'Catalog files', rows, [r[0] for r in rows] if args.resource is None else args.resource)
            if args.resource and 'files' not in args.component: args.component.append('files')
            if not args.resource and 'files' in args.component: args.component.remove('files')
        elif choice in ('Packages', 'Fonts'):
            name = choice.lower()
            if name not in args.component: args.component.append(name)
            selected_inputs(installation, args)
            (package_choices if name == 'packages' else font_choices)(selector, args)
        elif choice.startswith('Dependencies:'): args.with_dependencies = not args.with_dependencies
        elif choice.startswith('Save choices:'): args.save_choices = not args.save_choices
    selected_inputs(installation, args)


def save_plan(root, installation, args):
    if not args.save_choices: return
    if args.profile_directory is None:
        raise ValueError('saving setup choices requires an active profile')
    from config_cli import ControlPlan
    plan = ControlPlan(root, args.setup_controls.selected)
    for key, value in (('components', args.component), ('resources', args.resource or []), ('dependencies', args.with_dependencies)):
        plan.edit('apps.setup.'+key, value)
    installation.merge_plan(plan.operations, plan.guards, label='saved setup choices')
    if args.package_document is not None and 'packages' in args.component:
        path = args.profile_directory/'packages.json'
        installation.merge_plan([dict(path=str(path), data=args.package_document)],
                                {str(path): digest(path)}, label='saved package choices')

"""Inert output fixtures rendered by the real shared human-view helpers.

This module owns no provider discovery, commands, hooks or state. File kinds and
Git identities are declared by fixtures, so rendering never inspects sample paths.
"""
from fractions import Fraction
import json
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace


DESCRIPTIONS = {
    'progress': 'Overall sequence, nested steps and independent download progress',
    'spinner': 'Unknown work with the current spinner and label styles',
    'pkgs': 'Package managers, versions, successes, skips and mock failures',
    'git': 'Clean and changed repositories in default, short and verbose views',
    'files': 'Directory prefixes, file types, Unicode and wrapped paths',
    'messages': 'Information, success, warning, error and muted text',
    'help': 'Executable, command, subcommand, option and argument colors',
}
KINDS = (*DESCRIPTIONS, 'all')
ANIMATED = ('progress', 'spinner')


def arguments(parser):
    parser.add_argument('kind', nargs='?', choices=KINDS, help='mock output kind; omit to list demos')
    parser.add_argument('--static', action='store_true', help='show immediate snapshots without animation')
    parser.add_argument('--duration', type=int, help='animation seconds, 1–60 (default: 4)')
    parser.add_argument('--loop', action='store_true', help='repeat progress or spinner until Ctrl-C')


def samples(kind):
    """Fresh versionable records; all identities and results are fictional."""
    if kind == 'progress':
        return [dict(overall=0, completed=0, total=100, step=1, steps=2,
                     label='npm · Downloading · example-tool'),
                dict(overall=27, completed=63, total=100, step=1, steps=2,
                     label='npm · Downloading · example-tool'),
                dict(overall=100, completed=100, total=100, step=2, steps=2,
                     label='uv · Updated · example-lint')]
    if kind == 'spinner':
        return [dict(label='Inspecting mock metadata', completed=0, total=0)]
    if kind == 'pkgs':
        return [dict(manager='npm', package='example-tool', version='2.4.0', status='complete', skipped=1),
                dict(manager='pip', package='example-lint', version='1.8.2', status='complete', skipped=0),
                dict(manager='apt', package='example-library', version='3.2.1', status='unchanged', skipped=2),
                dict(manager='uv', package='example-check', version='0.6.0', status='failed (exit 1)', skipped=0)]
    if kind == 'git':
        return [dict(path='demo-workspace/dotfiles', branch='main', status='dirty', ahead=1, behind=0,
                     head='0123456789abcdef0123456789abcdef01234567', upstream='origin/main',
                     remote=dict(host='github.com', name='origin', url='https://example.invalid/demo/dotfiles.git',
                                 owner='demo', owned=True),
                     files=[dict(path='bin/dots-git-info', xy=' M'),
                            dict(path='config/界 café/new name.toml', old_path='config/old name.toml', xy='R '),
                            dict(path='docs/conflict.md', xy='UU'),
                            dict(path='notes/new idea.txt', xy='??')]),
                dict(path='demo-workspace/clean-repo', branch='main', status='clean', ahead=0, behind=0, files=[])]
    if kind == 'files':
        return [dict(path='bin/dots-git-info', kind='executable'),
                dict(path='config/editor/settings.toml', kind='file'),
                dict(path='docs/界 café/long directory name/complete guide with spaces.md', kind='file'),
                dict(path='assets/sample.png', kind='file'),
                dict(path='config/linked directory', kind='symlink'),
                dict(path='config/missing target', kind='broken_symlink'),
                dict(path='-leading-name.txt', kind='file')]
    if kind == 'messages':
        return [dict(role=role, text=text) for role, text in (
            ('info', 'Mock information: inspecting sample data'),
            ('success', 'Mock success: three items completed'),
            ('warning', 'Mock warning: one item skipped'),
            ('error', 'Mock error: sample failure; no operation was attempted'),
            ('muted', 'Mock context: no changes were made'))]
    if kind == 'help':
        return [dict(text='dots [OPTIONS] COMMAND [ARGS...]', kind='syntax'),
                dict(text='dots debug demo progress --duration SECONDS', kind='syntax'),
                dict(text='--static', kind='option'),
                dict(text='--duration SECONDS', kind='option'),
                dict(text='progress|spinner|pkgs|git|files|messages|help|all', kind='argument')]
    raise ValueError('unknown demo kind')


def document(kind):
    selected = tuple(DESCRIPTIONS) if kind in (None, 'all') else (kind,)
    return dict(version=1, mock=True, kind=kind or 'list', demos=[
        dict(kind=name, description=DESCRIPTIONS[name], samples=samples(name)) for name in selected])


def presentation():
    from files.catalog import Presentation
    from progress import terminal_columns
    ui = Presentation()
    ui.width = max(24, terminal_columns(sys.stdout))
    return ui


def list_demos(ui):
    ui.heading('Output demos')
    ui.detail('Samples', 'Fictional data using current appearance; no operations are run.')
    for name, description in DESCRIPTIONS.items():
        ui.detail(name, description)
    ui.detail('all', 'Run the complete finite gallery')
    ui.emit()
    ui.detail('Example', 'dots debug demo progress --duration 4')
    ui.detail('Example', 'dots debug demo all --static')
    ui.detail('Example', 'dots debug demo spinner --loop')


def progress_snapshot(ui, kind, rows, meter=None):
    from progress import Progress, terminal_columns
    meter = meter or Progress('', mode_override='spinner' if kind == 'spinner' else 'both')
    meter.mode = meter.mode_override
    meter.resolve_styles()
    for index, row in enumerate(rows):
        meter.overall = (Fraction(row.get('overall', 0), 100), 'manager', 1, 2)
        meter.step_hint = ('step', row['step'], row['steps']) if 'step' in row else None
        meter.update(row['label'], row['completed'], row['total'])
        width = max(1, min(ui.width, terminal_columns(ui.stream)) - 1)
        for text, cells in meter.lines(index, width, ui.color, ui.icons):
            if cells: ui.emit(text)


def animate(ui, kind, duration, loop):
    from progress import Progress, sequence, terminal_columns
    mode = 'spinner' if kind == 'spinner' else 'both'
    # Resolve before the first frame and retain the same appearance across loops.
    meter = Progress('Mock output', mode_override=mode)
    meter.resolve_styles()
    with meter:
        while True:
            meter.overall = (Fraction(0), 'manager', 1, 2)
            if kind == 'spinner':
                meter.update(samples('spinner')[0]['label'])
                time.sleep(duration)
            else:
                with sequence('Mock package update', 2, 'manager') as managers:
                    for manager in ('npm', 'uv'):
                        with managers.step(manager):
                            with sequence(manager, 2) as steps:
                                with steps.step(manager + ' · Downloading · example-tool'):
                                    for count in range(10):
                                        # A download is local activity, independent of overall work.
                                        meter.update(manager + ' · Downloading · example-tool', count * 10, 100)
                                        time.sleep(duration / 40)
                                with steps.step(manager + ' · Updating · example-tool') as work:
                                    for count in range(10):
                                        work.update(manager + ' · Updating · example-tool', count + 1, 10)
                                        time.sleep(duration / 40)
            if not loop: break
    ui.width = max(24, terminal_columns(ui.stream))
    progress_snapshot(ui, kind, samples(kind)[-1:], meter)
    ui.detail('Result', 'Mock demo complete')


def render_pkgs(ui, rows, root):
    # Import only the package presentation/report modules, never a manager adapter.
    sys.path.insert(0, str(root / 'plugins/pkgs'))
    from pkgs_lib.presentation import PackagePresentation, styles
    from pkgs_lib.reports import packages
    from plugin_presentation import Report, color_mode
    report = Report(ui.stream, color_mode(), False, presentation=PackagePresentation, styles=styles())
    report.ui.width = ui.width
    for row in rows:
        package = SimpleNamespace(name=row['package'], version=row['version'], installed=True,
                                  external=[], description='Fictional package for output preview')
        packages(report, [package], SimpleNamespace(name=row['manager'], scope='mock user scope'), installed=True)
        role = 'error' if row['status'].startswith('failed') else 'muted' if row['status'] == 'unchanged' else 'success'
        spans = [(row['status'], report.styles[role])]
        if row['skipped']: spans.append((' · '+str(row['skipped'])+' skipped', report.styles['skipped']))
        report.ui.detail_spans(row['manager'], spans, label_width=11,
                               label_code=report.styles.get('manager', report.styles['identity']))
        report.gap()


def render_git(ui, rows):
    from git_output import GitView
    from resources import Resources

    class FixtureResources(Resources):
        def describe(self, path, kind=None, mime=None, styled=True):
            # GitView passes paths for file styling; declare their mock kinds so
            # a coincidental real path can never influence the output.
            return super().describe(path, kind or ('executable' if str(path).endswith('dots-git-info') else 'file'), mime, styled)

    ui.resources = FixtureResources()
    for mode in ('default', 'short', 'verbose'):
        ui.heading('Git ' + mode)
        view = GitView(ui, mode)
        for row in rows: view.status(row)
        ui.emit()


def render_static(ui, kind, rows, root):
    if kind in ANIMATED: progress_snapshot(ui, kind, rows)
    elif kind == 'pkgs': render_pkgs(ui, rows, root)
    elif kind == 'git': render_git(ui, rows)
    elif kind == 'files':
        for row in rows:
            ui.resource_detail(row['kind'], row['path'], kind=row['kind'], display=row['path'], path_components=True)
    elif kind == 'messages':
        codes = dict(info='94', success='92', warning='93', error='91', muted='2')
        for row in rows: ui.detail(row['role'].capitalize(), row['text'], codes[row['role']])
    elif kind == 'help':
        from help_presentation import HelpPresentation
        view = HelpPresentation(ui.stream)
        view.width = ui.width
        view.heading('Usage')
        for row in rows:
            view.help_text(row['text'], kind=row['kind'], commands=(('debug', 'demo'),), indent=2)


def run(args, parser, root):
    from progress import configure, eligible
    if args.duration is not None and (not 1 <= args.duration <= 60 or args.kind not in (*ANIMATED, 'all')):
        parser.error('--duration requires progress, spinner or all and an integer from 1 to 60')
    if args.loop and (args.kind not in ANIMATED or args.json or args.static):
        parser.error('--loop requires progress or spinner without --json or --static')
    if args.json:
        print(json.dumps(document(args.kind), ensure_ascii=True))
        return 0
    configure(human=True)
    animated = not args.static and eligible('both')
    if args.loop and not animated:
        parser.error('--loop requires usable stdout and stderr terminals')
    ui = presentation()
    if args.kind is None:
        list_demos(ui)
        return 0
    selected = tuple(DESCRIPTIONS) if args.kind == 'all' else (args.kind,)
    duration = (args.duration or 4) / (2 if args.kind == 'all' else 1)
    for index, kind in enumerate(selected):
        if index: ui.emit()
        ui.heading('Mock ' + kind)
        if kind in ANIMATED and animated: animate(ui, kind, duration, args.loop)
        else: render_static(ui, kind, samples(kind), root)
    return 0

"""Curated Dots family menus with explicit navigation and terminal ownership."""
import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
import sys

from command_metadata import read
from interaction import SelectionEnded, SelectionEvent, terminal
from menus import Entry, Menu, add_arguments, choose, dots_argv, run_action, review_output, show_message
from menu_tmux import TmuxContext
from resources import clean


@dataclass(frozen=True)
class Action:
    id: str
    label: str
    route: tuple
    options: tuple = ()
    kind: str = 'output'
    icon: str = '󰈔'
    tool: str = ''
    submenu: str = ''


def group(name, icon, *, route=None, tool=''):
    return Action(name, name, route or (name,), kind='submenu', icon=icon, tool=tool, submenu=name)


def help_action(family=''):
    if family == 'anodize':
        return Action('help', 'help', ('anodize',),
                      ('--logo=text', '--logo-layout=horizontal', '--help'), icon='󰋖')
    route = ('menu', 'tmux') if family == 'tmux' else tuple(family.split('/')) if family else ()
    return Action('help', 'help', ('help', *route), icon='󰋖')


def leaves(family, names):
    return tuple(Action(name, name, (*family.split('/'), name)) for name in names.split())


ACTIONS = (
    Action('keys', 'keys', ('keys',), ('--browse',), 'popup', '󰌆'),
    group('tmux', '', route=('menu', 'tmux'), tool='tmux'),
    group('files', '󰉋'), group('git', '', tool='git'), group('theme', '󰏘'), group('themes', '󰏘'),
    group('anodize', '󰏘'), group('blastoff', '󱓞'), group('pkgs', '󰏖'),
    group('debug', '󰃤'), group('profile', '󰀵'),
    group('profiles', '󰀵'), group('wiki', '󰈙'),
    Action('env', 'env', ('env',), icon='󰒓'),
)
FAMILIES = {
    'blastoff': (
        Action('pick', 'choose theme', ('blastoff', 'pick'), kind='terminal'),
        Action('current', 'current theme', ('blastoff', 'current')),
        Action('list', 'themes', ('blastoff', 'theme', 'list')),
        Action('edit', 'edit active configuration', ('blastoff', 'theme', 'edit'), kind='terminal'),
        Action('save', 'save active theme', ('blastoff', 'theme', 'save'), kind='terminal'),
        Action('modules', 'browse modules', ('blastoff', 'module', 'show'), kind='terminal'),
        Action('backups', 'backups', ('blastoff', 'backup', 'list')),
        Action('doctor', 'doctor', ('blastoff', 'doctor')),
    ),
    'pkgs': (
        *tuple(Action(name, name, ('pkgs', name), kind='terminal')
               for name in ('search', 'install', 'uninstall')),
        Action('list', 'installed packages', ('pkgs', 'list'), ('--installed',)),
        *tuple(Action(name, name, ('pkgs', name), kind='terminal') for name in ('upgrade', 'refresh')),
        *leaves('pkgs', 'managers doctor'),
    ),
    'tmux': (
        Action('sessions', 'sessions', ('menu', 'tmux', 'sessions'), kind='session', icon='', tool='tmux'),
        Action('keys', 'keys', ('menu', 'tmux', 'keys'), ('--browse',), 'popup', '󰌆', 'tmux'),
    ),
    'files': (Action('browse', 'browse', ('files', 'browse'), kind='terminal', icon='󰉋'),
              *leaves('files', 'list history sources')),
    'git': (*leaves('git', 'status info'),
            Action('submodules', 'submodules', ('git', 'submodules'), kind='submenu', submenu='git/submodules', icon=''),
            Action('wiki', 'wiki', ('git', 'wiki'), kind='submenu', submenu='git/wiki', icon='󰈙'),
            Action('publish', 'publish', ('git', 'publish'), ('--all',), kind='terminal', icon=''),
            Action('sync', 'sync', ('git', 'sync'), kind='sync', icon='')),
    'git/submodules': (Action('list', 'list', ('git', 'submodules')),
                       *leaves('git/submodules', 'info status')),
    'git/wiki': (*leaves('git/wiki', 'status info'),
                 Action('publish', 'publish', ('git', 'wiki', 'publish'), ('--all',), kind='terminal', icon=''),
                 Action('sync', 'sync', ('git', 'wiki', 'sync'), kind='sync', icon='')),
    'theme': (Action('show', 'show', ('theme', 'show')),
              Action('switcher', 'switcher', ('theme', 'switcher'), kind='terminal', icon='󰏘'),
              Action('files', 'files', ('theme', 'files', 'browse'), kind='terminal', icon='󰈔'),
              Action('backgrounds', 'backgrounds', ('theme', 'bg', 'switcher'), kind='terminal', icon='󰸉')),
    'themes': (Action('list', 'list', ('themes', 'list')),
               Action('switcher', 'switcher', ('themes', 'switcher'), kind='terminal', icon='󰏘'),
               Action('plugins', 'plugins', ('themes', 'plugins'), kind='submenu', submenu='themes/plugins')),
    'themes/plugins': leaves('themes/plugins', 'list doctor'),
    'anodize': (*tuple(Action(name, name, ('anodize', name),
                       ('--interactive', '--logo=text', '--logo-layout=base') if name in ('preview', 'extract') else ('--interactive',),
                       'document' if name in ('preview', 'extract') else 'terminal', '󰏘')
                       for name in ('create', 'extract', 'edit', 'preview', 'apply')),
                Action('list', 'list', ('anodize', 'list'))),
    'debug': leaves('debug', 'check startup path cache'),
    'profile': leaves('profile', 'show paths layers files commands env check'),
    'profiles': leaves('profiles', 'list check'),
    'wiki': (Action('browse', 'browse', ('wiki', 'browse'), kind='document', icon='󰈙'),
             *leaves('wiki', 'list check')),
}


def actions(family=''):
    return (*FAMILIES[family], help_action(family)) if family else ACTIONS


def entry(root, action, *, windows=None):
    windows = os.name == 'nt' if windows is None else windows
    reason = ''
    path = (root / 'lib/dots/metadata/help.meta' if action.route[0] == 'help'
            else root / 'bin' / ('dots-' + '-'.join(action.route)))
    description = 'Browse ' + action.label + ' workflows' if action.submenu else action.label
    if path.is_file():
        description = read(path)['summary'] or description
    elif not action.submenu:
        reason = 'Command is missing from this checkout'
    tool = action.tool or ('git' if action.route[0] == 'git' else '')
    if windows and tool == 'tmux':
        reason = 'Tmux menus are unavailable on native Windows'
    elif windows and action.route[0] == 'pkgs' and not action.submenu:
        reason = 'Package operations require a separate Termux, Linux or WSL installation'
    elif tool and not shutil.which(tool):
        reason = tool + ' is unavailable'
    if action.route[0] in ('theme', 'themes', 'anodize') and sys.version_info < (3, 11):
        reason = 'Theme commands require Python 3.11 or newer'
    return Entry(action.id, action.label, description, not reason, reason, action.icon)


def launcher(root, *, family='', windows=None):
    return Menu('dots' + (':' + family if family else ''),
                'dots / ' + family.replace('/', ' / ') if family else 'Dots menu',
                tuple(entry(root, a, windows=windows) for a in actions(family)))


def invoke(root, action, context):
    """Return True only for completed session navigation; all other actions return."""
    current = entry(root, action)
    if not current.available:
        show_message(current.reason, context=context, title=action.label, code=2)
        return False
    if action.kind == 'session':
        from menu_sessions import browse
        outcome = browse(context)
        if outcome.message:
            show_message(outcome.message, context=context, title='Tmux sessions', code=outcome.code)
        if outcome.selected and outcome.code == 0:
            return True
        if outcome.code not in (0, 130):
            show_message('Session attachment failed.', context=context, title='Tmux sessions', code=outcome.code)
        return False
    kind = action.kind
    if kind == 'sync':
        result = review_output(dots_argv([*action.route, '--dry-run'], root=root),
                               context=context, title='Preview: dots ' + ' '.join(action.route))
        if result.code or not result.reviewed:
            return False
        confirmation = Menu('git-sync-confirm', 'Sync repositories?', (
            Entry('cancel', 'Cancel'), Entry('sync', 'Sync')))
        selected = choose(confirmation, mode='browse', context=context, compact=True,
                          prompt='dots·' + '·'.join(action.route))
        if selected is None or selected.id == 'cancel':
            return False
        if selected.id != 'sync':
            raise ValueError('invalid sync confirmation')
        kind = 'terminal'
    code = run_action(dots_argv([*action.route, *action.options], root=root), kind=kind,
                      context=context, title='dots ' + ' '.join(action.route))
    # Output readers and hosted terminal failures already display their status.
    if code not in (0, 130) and (kind == 'popup' or context is None and kind in ('terminal', 'document')):
        show_message('The workflow failed.', context=context, title=action.label, code=code)
    return False


def run(args):
    root = Path(os.environ.get('DOTS') or Path(__file__).resolve().parents[2])
    if not root.is_absolute():
        raise ValueError('menu checkout root must be absolute')
    interactive = args.menu_mode == 'browse' or (args.menu_mode == 'auto' and terminal() and os.environ.get('TERM') != 'dumb')
    if not interactive:
        choose(launcher(root, family=getattr(args, 'family', '')), mode=args.menu_mode, query=args.query)
        return 0
    context = None
    if os.name != 'nt' and os.environ.get('DOTS_MENU_CONTEXT'):
        context = TmuxContext.from_environment()
        if args.client and args.client != context.client:
            raise ValueError('requested tmux client differs from the inherited menu context')
    elif os.name != 'nt' and os.environ.get('TMUX'):
        context = TmuxContext.capture(client=args.client)
    elif args.client:
        raise ValueError('--client requires an inherited tmux server and pane')
    stack = [dict(family=getattr(args, 'family', ''), query=args.query)]
    while stack:
        frame = stack[-1]
        family = frame['family']
        try:
            selected = choose(launcher(root, family=family), mode='browse', query=frame['query'],
                              context=context, compact=True, navigation=frame,
                              prompt='dots' + ('·' + family.replace('/', '·') if family else ''))
        except SelectionEvent as event:
            if event.action == 'back':
                stack.pop()
                if not stack:
                    return 130
                continue
            action = help_action(family)
        else:
            if selected is None:  # Missing-tool fallback printed a useful listing.
                return 0
            action = next(a for a in actions(family) if a.id == selected.id)
            if action.submenu and selected.available:
                stack.append(dict(family=action.submenu, query=''))
                continue
        try:
            if invoke(root, action, context):
                return 0
        except SelectionEnded:
            continue  # A delegated browser was canceled, not the launcher.
        except (ValueError, OSError, subprocess.SubprocessError) as error:
            # Stale contexts also fail message hosting, leaving main to report
            # the failure rather than choosing a different client implicitly.
            show_message(clean(str(error)), context=context, title=action.label, code=2)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog='dots menu', description='Browse Dots command families')
    add_arguments(parser)
    parser.add_argument('family', nargs='?', choices=('blastoff', 'pkgs'), default='',
                        help='Open an application family directly')
    parser.add_argument('--client', help='Exact invoking tmux client (requires an inherited server and pane)')
    args = parser.parse_args(argv)
    try:
        return run(args)
    except SelectionEnded as error:
        return error.status
    except KeyboardInterrupt:
        return 130
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print('dots menu: ' + clean(str(error)), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())

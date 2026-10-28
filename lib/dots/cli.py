#!/usr/bin/env python3
"""Native front end for shared Dots controllers and static command metadata."""
import json
import base64
import os
from pathlib import Path
import runpy
import subprocess
import sys

LIB = Path(__file__).resolve().parent
sys.path.insert(0, str(LIB))
sys.path.insert(0, str(LIB.parents[1] / 'plugins'))
from command_metadata import BUILTINS, RESERVED, catalog, read, resolve, roots


def controller(relative, args):
    path = LIB / relative
    sys.path.insert(0, str(path.parent))
    sys.argv = [str(path), *args]
    runpy.run_path(str(path), run_name='__main__')
    return 0


def anodize_options(values):
    from anodize.logo import configure_options, render
    try:
        return configure_options(values)
    except ValueError as error:
        from files.catalog import Presentation
        render(Presentation(sys.stderr))
        print('dots: ' + str(error), file=sys.stderr)
        raise SystemExit(2) from None


def help_view(directories, words):
    if words[:1] == ['anodize']:
        words = ['anodize', *anodize_options(words[1:])]
    if words[:2] == ['git', 'submodule']:
        stem, path, _ = resolve(directories, words)
        if stem == 'git-submodule' and path.parent.resolve() == (LIB.parents[1] / 'bin').resolve():
            return controller('git/submodule.py', ['--help-context', *words[2:]])
    sys.path.insert(0, str(LIB / 'files'))
    from catalog import Presentation
    ui = Presentation()
    stem = '-'.join(words)
    rows = catalog(directories)
    metadata = read(LIB / 'metadata' / (stem + '.meta')) if stem in BUILTINS else rows.get(stem)
    if words[:1] == ['anodize']:
        from anodize.logo import render
        render(ui, full=True)
    ui.heading('Dots' if not stem else 'dots ' + ' '.join(words))
    if metadata:
        ui.emit('  ' + metadata['summary'])
        ui.detail('Usage', 'dots ' + ' '.join(words) + ' ' + metadata['usage'])
        for long, short, _, description in metadata['option']:
            ui.detail(', '.join(x for x in (long, short) if x), description)
        for example in metadata['example']:
            ui.emit('  ' + example)
    children = [(name, row) for name, row in sorted(rows.items())
                if not row['hidden'] and (not stem or name.startswith(stem + '-'))]
    if not words:
        for name in BUILTINS:
            ui.detail(name, read(LIB / 'metadata' / (name + '.meta'))['summary'])
    for name, row in children:
        ui.detail(name.replace('-', ' '), row['summary'])
    if stem and not metadata and not children and words[:1] == ['theme'] and len(words) == 2:
        return controller('themes/theme_cli.py', [words[1], '--help'])
    if stem and not metadata and not children:
        raise ValueError('unknown command: ' + ' '.join(words))
    return 0


def complete(root, directories, words):
    """Private completion records: candidate, file, directory. No shell evaluation."""
    current = words[-1] if words else ''
    previous = words[:-1]
    # Prefix presentation switches do not change the route being completed.
    while previous:
        if previous[0].startswith(('--color=', '--icons=')) or previous[0] in ('--raw', '-r'):
            previous = previous[1:]
        elif len(previous) > 1 and previous[0] == '--command-dir':
            extra = Path(previous[1])
            if extra.is_absolute() and extra.is_dir(): directories = [*directories, extra]
            previous = previous[2:]
        else: break
    if previous[:1] in (['blastoff'], ['pkgs']):
        from bundled_apps import complete as bundled_complete
        return bundled_complete(root, [*previous, current])
    if previous[:1] == ['anodize']:
        index = 1
        while index < len(previous):
            flag = previous[index].split('=')[0]
            if flag == '--interactive':
                index += 1
                continue
            if flag not in ('--logo', '--logo-layout'): break
            count = 1 if '=' in previous[index] else 2
            if index + count > len(previous): break
            index += count
        previous = [previous[0], *previous[index:]]
    if previous == ['--command-dir']:
        print('directory\t\t'); return 0
    help_context = previous[:1] == ['help']
    if help_context: previous = previous[1:]
    if previous[:2] == ['git', 'submodule']:
        stem, path, _ = resolve(directories, previous)
        if stem == 'git-submodule' and path.parent.resolve() == (LIB.parents[1] / 'bin').resolve():
            return controller('git/submodule.py', ['--complete', *previous[2:], current])
    rows = catalog(directories)
    stem, path, consumed = resolve(directories, previous)
    metadata = read(path.with_suffix('.meta') if path.suffix == '.exe' else path) if path else None
    if previous and previous[0] in BUILTINS:
        metadata = read(LIB / 'metadata' / (previous[0] + '.meta'))
        consumed = 1
    suggestions = []
    positionals, option_values = [], {}
    def add(value, desc=''):
        if value.startswith(current) and not any(c in value + desc for c in '\t\r\n'):
            suggestions.append(('candidate', value, desc))
    def values(kind):
        if kind.startswith('choice:'):
            for value in kind[7:].split(','): add(value)
        elif kind in ('file', 'directory'):
            suggestions.append((kind, '', ''))
        elif kind in ('wiki-page','wiki-section'):
            from wiki import Reader, manifest
            pages=manifest(Reader(root))['pages']
            for value in dict.fromkeys(row['id' if kind=='wiki-page' else 'section'] for row in pages): add(value)
        elif kind in ('file-resource', 'file-repository'):
            sys.path.insert(0, str(LIB / 'files'))
            from catalog import Catalog, platform
            source = Catalog(root, platform())
            for row in source.sources if kind == 'file-repository' else source.records(): add(row['id'])
        elif kind == 'git-submodule':
            base = option_values.get('--directory') or option_values.get('-C') or root
            result = subprocess.run([sys.executable, '-B', str(LIB / 'git/inspection.py'), '_complete', '-C', str(base)],
                                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            if result.returncode == 0:
                for value in result.stdout.splitlines(): add(value)
        elif kind == 'profile-id':
            from profiles import available
            for row in available(root): add(row['id'])
        elif kind == 'dots-setting':
            from environment import inspect
            for key in inspect(root)['values']: add(key)
        elif kind in ('anodize-theme', 'anodize-user-theme'):
            from file_platform import config_root
            base = Path(os.environ.get('DOTHEMES') or os.environ.get('THEMES') or root / 'themes')
            if kind == 'anodize-user-theme': base = config_root() / 'dots/themes'
            for item in sorted(set([*base.glob('*/anodize.json'), *(config_root() / 'dots/themes').glob('*/anodize.json')])):
                if not item.is_symlink(): add(item.parent.name)
        elif kind in ('theme-file', 'theme-app'):
            sys.path.insert(0, str(LIB / 'themes'))
            import inspection
            if kind == 'theme-file':
                names = [r['id'] for r in inspection.Inspection().inventory(connections=False)['artifacts']]
            else:
                names = {r[0] for r in inspection.registry()} | {'codex', 'pi', 'termux', 'managed'}
                names.update(a for values in inspection.CONSUMERS.values() for a, _, _ in values)
            for name in sorted(names):
                if not any(ord(c) < 32 or ord(c) == 127 for c in name): add(name)
        elif kind == 'theme-plugin':
            sys.path.insert(0, str(LIB / 'themes'))
            import plugins
            _, config, _ = plugins.roots()
            _, selected = plugins.selection(config)
            for row in plugins.discover(config, selected['enabled']): add(row['name'])
        elif kind in ('theme', 'theme-id', 'flavor', 'palette-color', 'color-format', 'theme-color', 'file-color-key'):
            sys.path.insert(0, str(LIB / 'themes'))
            from palette_native import Themes, FORMATS, styles
            themes = Themes()
            if kind == 'theme':
                for value in themes.families(): add(value)
            elif kind == 'theme-id':
                for value in themes.ids(): add(value)
            elif kind == 'color-format':
                for value in FORMATS: add(value)
            elif kind == 'flavor':
                for value in themes.families().get(positionals[0] if positionals else '', {}): add(value)
            elif kind == 'palette-color':
                family = positionals[0] if positionals else themes.current()
                flavor = option_values.get('--flavor') or (positionals[1] if len(positionals) > 1 else None)
                for value in themes.load(themes.pick(family, flavor))['palette']: add(value)
            elif kind == 'theme-color':
                palette = themes.load(option_values.get('--theme') or themes.current())
                for value in palette['palette']: add(value)
                if '--native' not in option_values:
                    for value in (*palette['colors'], 'mode'): add(value)
            else:
                # The existing read-only completer owns rule-group semantics.
                import contextlib, io
                output = io.StringIO()
                with contextlib.redirect_stdout(output): styles().main(['_complete', *positionals])
                for value in output.getvalue().splitlines(): add(value)
    if not previous and current.startswith(('--color=', '--icons=')):
        flag = current.split('=')[0]
        for mode in ('auto', 'always', 'never', *(['none'] if flag == '--color' else [])): add(flag + '=' + mode)
    if not previous:
        for name in BUILTINS: add(name)
        for name, row in rows.items():
            if not row['hidden']: add(name.split('-')[0], row['summary'])
        for flag in ('--help', '--dir', '--raw', '--color=', '--icons=', '--command-dir'): add(flag)
    prefix = '-'.join(previous)
    for name, row in rows.items():
        if prefix and name.startswith(prefix + '-') and not row['hidden']:
            add(name[len(prefix) + 1:].split('-')[0], row['summary'])
    if previous and previous[0] == 'theme' and stem == 'theme':
        sys.path.insert(0, str(LIB / 'themes'))
        from palette_native import Themes, FORMATS
        themes = Themes()
        families = themes.families()
        if len(previous) == 1:
            for name in families: add(name, 'Theme palette')
        elif previous[1] in families or previous[1] in themes.ids():
            name = previous[1]
            palette = themes.load(themes.pick(name))
            family_name, flavor = palette['theme'], palette['flavor']
            prior, color, action = '', None, None
            for token in previous[2:]:
                if prior in ('--flavor', '-f'): flavor, prior = token, ''; continue
                if prior in ('--color', '-c'): color, prior = token, ''; continue
                if prior: prior = ''; continue
                if token in ('--flavor','-f','--color','-c','--format','-F','--completion','completion'): prior = token
                elif token in ('set','init','--init'): action = token
                elif token in families.get(family_name, {}): flavor = token
                elif token not in ('show','color','--raw','-r','--array','-a','--all') and not token.startswith('-'): color = token
            if prior in ('--completion', 'completion'):
                for value in ('bash','zsh','fish','powershell'): add(value)
            elif prior in ('--format','-F') or color:
                for value in FORMATS: add(value)
            elif action == 'set':
                for value in ('--dry-run','--background','--verbose','-v','--help'): add(value)
            elif not action:
                if prior not in ('--color', '-c'):
                    for value in families.get(family_name, {}): add(value)
                if not prior:
                    for value in ('show','set','color','init','--color=auto','--color=always','--color=never','--raw','--array','--all','--flavor','--color','--format','--completion'): add(value)
                if prior not in ('--flavor', '-f'):
                    for value in themes.load(themes.pick(family_name, flavor))['palette']: add(value)
            for row in dict.fromkeys(suggestions): print('\t'.join(row))
            return 0
    if metadata and not help_context:
        options = {flag: (kind, desc) for long, short, kind, desc in metadata['option'] for flag in (long, short) if flag}
        args = previous[consumed:]
        waiting = None
        waiting_option = None
        position = 1
        literal = False
        for arg in args:
            if waiting:
                option_values[waiting_option] = arg
                waiting = None
            elif not literal and arg == '--':
                literal = True
            elif not literal and arg.split('=')[0] in options:
                kind = options[arg.split('=')[0]][0]
                option_values[arg.split('=')[0]] = arg.split('=', 1)[1] if '=' in arg else True
                if '=' not in arg and kind != 'flag': waiting, waiting_option = kind, arg
            elif literal or not arg.startswith('-'):
                position += 1
                positionals.append(arg)
        if waiting:
            values(waiting)
        elif '=' in current and current.split('=')[0] in options:
            flag, value = current.split('=', 1)
            current = value
            values(options[flag][0])
            suggestions = [(kind, flag + '=' + value, desc) for kind, value, desc in suggestions]
        elif current.startswith('-') and not literal:
            for flag, (_, desc) in options.items(): add(flag, desc)
            add('--help', 'Show help')
        else:
            for pos, kind, _ in metadata['argument']:
                if pos in (str(position), '*'): values(kind)
    for row in dict.fromkeys(suggestions):
        print('\t'.join(row))
    return 0


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    root = Path(os.environ.get('DOTS') or LIB.parents[1]).resolve()
    extras = []
    raw = False
    while args:
        value = args[0]
        if value in ('--raw', '-r'):
            raw = True
        elif value in ('--dir', '-d'):
            home = str(Path.home())
            print(str(root) if raw else str(root).replace(home, '~', 1) if root.is_relative_to(home) else str(root))
            return 0
        elif value.startswith(('--color=', '--icons=')):
            key, mode = value[2:].split('=', 1)
            if key == 'color' and mode == 'none': mode = 'never'
            if mode not in ('auto', 'always', 'never'): raise ValueError('invalid ' + key + ' mode')
            os.environ['DOTS_' + key.upper()] = mode
        elif value == '--command-dir':
            if len(args) < 2 or not Path(args[1]).is_absolute() or not Path(args[1]).is_dir():
                raise ValueError('--command-dir requires an existing absolute directory')
            extras.append(args.pop(1))
        else:
            break
        args.pop(0)
    directories = roots(root, extras)
    if args[:2] == ['files', 'migrate-apps']:
        args = ['files', 'migrate', 'apps', *args[2:]]
    if not args or args[0] in ('help', '--help', '-h'):
        return help_view(directories, args[1:])
    from environment import settings
    preferences = settings(root)
    for key in ('DOTS_COLOR', 'DOTS_ICONS', 'DOTS_PROGRESS'):
        if args[0] != 'env' and key in preferences and not os.environ.get(key): os.environ[key] = preferences[key]['value']
    if args[0] == '__complete':
        return complete(root, directories, args[1:])
    if args[0] in BUILTINS and args[1:] in (['--help'], ['-h']):
        return help_view(directories, args[:1])
    if args[0] == 'commands':
        if args[1:] not in ([], ['--check']): raise ValueError('Usage: dots commands [--check]')
        rows = catalog(directories)
        if args[1:]: print('Validated ' + str(len(rows)) + ' external commands')
        else:
            for name, row in sorted(rows.items()):
                if not row['hidden']: print(name.replace('-', ' ') + '\t' + row['summary'])
        return 0
    if args[0] == 'completion':
        if len(args) != 2 or args[1] not in ('bash', 'zsh', 'fish', 'powershell'):
            raise ValueError('Usage: dots completion bash|zsh|fish|powershell')
        print((LIB / 'completion' / args[1]).read_text(), end='')
        return 0
    if args[:2] == ['init', '--bootstrap']:
        if len(args) != 3: raise ValueError('Usage: dots init --bootstrap bash|zsh|powershell')
        from bootstrap_snippet import snippet
        print(snippet(args[2]), end='')
        return 0
    if args[:2] == ['init', '--setup']:
        return controller('files/install.py', ['install', *args[2:]])
    if args[0] == 'init':
        if len(args) != 2 or args[1] not in ('bash', 'zsh', 'fish', 'powershell', 'nu', 'xonsh'):
            raise ValueError('Usage: dots init SHELL | --setup [OPTIONS]')
        shell = args[1]
        loader = root / 'lib/dots/shell' / ('init.' + {'powershell':'ps1', 'xonsh':'xsh'}.get(shell, shell))
        if not loader.is_file(): raise ValueError('shell adapter unavailable')
        import shlex
        if shell in ('bash', 'zsh'): print('export DOTS=' + shlex.quote(str(root)) + '\nsource ' + shlex.quote(str(loader)))
        elif shell == 'powershell': print("$env:DOTS = '" + str(root).replace("'", "''") + "'\n. (Join-Path $env:DOTS 'lib/dots/shell/init.ps1')")
        elif shell == 'fish': print('set -gx DOTS ' + shlex.quote(str(root)) + '\nsource ' + shlex.quote(str(loader)))
        elif shell == 'nu': print('$env.DOTS = ' + json.dumps(str(root)) + '\nsource ' + json.dumps(str(loader)))
        else: print('$DOTS = ' + repr(str(root)) + '\nexecx(open(' + repr(str(loader)) + ').read())')
        return 0
    if args[:1] == ['anodize']:
        args = ['anodize', *anodize_options(args[1:])]
    stem, path, count = resolve(directories, args)
    if not path:
        return help_view(directories, args)
    if stem.split('-')[0] in ('blastoff', 'pkgs') and path.parent.resolve() == (root / 'bin').resolve():
        from bundled_apps import run
        return run(root, args[0], args[1:])
    if any(a in ('--help', '-h') for a in args[:args.index('--') if '--' in args else len(args)]):
        if stem == 'git-submodule' and path.parent.resolve() == (root / 'bin').resolve():
            return controller('git/submodule.py', args[count:])
        if stem == 'theme' and len(args) > count and not args[count].startswith('-'):
            return controller('themes/theme_cli.py', args[count:])
        return help_view(directories, stem.split('-'))
    rest = args[count:]
    if path.parent.resolve() != (root / 'bin').resolve():
        if stem.split('-')[0] in RESERVED: raise ValueError('reserved command route')
        if path.suffix == '.exe': command = [str(path)]
        elif path.suffix == '.ps1':
            shell = os.environ.get('DOTS_POWERSHELL')
            if not shell: raise ValueError('PowerShell extension requires a native PowerShell adapter')
            # PowerShell 5.1 native -File argv cannot reliably preserve every
            # empty/quoted argument. Transfer inert JSON, then splat natively.
            script = "[Console]::OutputEncoding = New-Object Text.UTF8Encoding($false); "
            script += "$forward = @(ConvertFrom-Json ([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($env:DOTS_EXTENSION_ARGUMENTS)))); "
            script += "$global:LASTEXITCODE = 0; & $env:DOTS_EXTENSION_PATH @forward; if (-not $?) { if ($LASTEXITCODE) { exit $LASTEXITCODE }; exit 1 }; exit $LASTEXITCODE"
            encoded = base64.b64encode(script.encode('utf-16-le')).decode('ascii')
            env = dict(os.environ, DOTS_EXTENSION_PATH=str(path),
                       DOTS_EXTENSION_ARGUMENTS=base64.b64encode(json.dumps(rest).encode()).decode())
            return subprocess.call([shell, '-NoLogo', '-NoProfile', '-EncodedCommand', encoded], env=env)
        elif os.name != 'nt': command = [str(path)]
        else: raise ValueError('extension has no native Windows entry point: ' + stem)
        return subprocess.call([*command, *rest])
    parts = stem.split('-')
    if parts in (['git'], ['themes'], ['theme', 'plugins'], ['themes', 'plugins']):
        return help_view(directories, parts)
    if parts[0] == 'files':
        if stem == 'files-migrate-apps':
            return controller('files/install.py', ['migrate-apps', *rest])
        action = '-'.join(parts[1:])
        if not action or action == 'backups': return help_view(directories, parts)
        if action in ('install', 'uninstall'): target = 'install'
        elif action in ('stash', 'edit'): target = 'mappings'
        elif action in ('browse', 'check', 'repair'): return controller('files/' + action.replace('browse', 'browser') + '.py', rest)
        elif action in ('list', 'sources', 'source', 'target', 'show', 'track', 'locate', 'discover'): target = 'catalog'
        else: target = 'manage'
        if action == 'rm': action = 'remove'
        if action == 'discover' and '--system' in rest:
            target, action = 'manage', 'system'
            rest = [a for a in rest if a != '--system']
        return controller('files/' + target + '.py', [action, *rest])
    if parts[0] in ('anodize', 'theme', 'themes') and sys.version_info < (3, 11):
        raise ValueError('theme and Anodize commands require Python 3.11 or newer')
    if parts[0] == 'anodize': return controller('../../plugins/anodize/cli.py', [*parts[1:], *rest])
    if parts[0] in ('profile', 'profiles'): return controller('profiles.py', [*parts, *rest])
    if parts[0] == 'wiki': return controller('wiki.py', [*parts[1:], *rest])
    if parts[:2] == ['git','wiki']: return controller('wiki_git.py', [*parts[2:], *rest])
    if parts[0] == 'keys': return controller('keys_cli.py', [*parts[1:], *rest])
    if parts[0] == 'debug': return controller('debug_cli.py', [*parts[1:], *rest])
    if parts[0] == 'env': return controller('environment.py', rest)
    if parts[0] == 'git':
        if parts[1:] == ['submodule']:
            return controller('git/submodule.py', ['--frontend=native', *rest])
        if parts[1:] in (['info'], ['submodules'], ['submodules', 'status'], ['submodules', 'info']):
            action = 'status' if parts[1:] == ['submodules', 'status'] else 'submodules-info' if parts[1:] == ['submodules', 'info'] else parts[1]
            return controller('git/inspection.py', [action, *rest])
        if parts[1:] == ['submodules', 'publish']:
            return controller('git/cli.py', ['submodules-publish', *rest])
        return controller('git/cli.py', [*parts[1:], *rest])
    if parts[0] in ('theme', 'themes'):
        if parts[1:2] == ['files']: return controller('themes/inspection.py', [*parts[2:], *rest])
        if parts[1:2] == ['colors']: return controller('themes/file-colors.py', [*parts[2:], *rest])
        if parts[1:2] == ['plugins'] and len(parts) > 2: return controller('themes/plugins.py', [*parts[2:], *rest])
        return controller('themes/theme_cli.py', [*parts[1:], *rest])
    if stem in ('menu', 'menu-blastoff', 'menu-pkgs'):
        return controller('menu_cli.py', [*parts[1:], *rest])
    if stem == 'menu-tmux-keys': return controller('keys_cli.py', ['tmux', *rest])
    if stem == 'menu-tmux-sessions': return controller('menu_sessions.py', rest)
    raise ValueError('command requires a POSIX/tmux session: ' + stem.replace('-', ' '))


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError) as error:
        print('dots: ' + str(error), file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)

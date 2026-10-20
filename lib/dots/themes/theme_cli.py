#!/usr/bin/env python3
"""Native theme command adapter over the shared palette and transaction engines."""
import argparse
import contextlib
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import uuid

from palette_native import Themes, LIB, FORMATS, ID, metric, regular, styles
from catalog import Presentation, atomic_json
from events import OperationOutput
from file_platform import lock, open_nofollow, sync_dir
from transactions import Store, digest, exists, parents_safe, private_directory
from interaction import RichSelector, Selector, SelectionEnded
from progress import Progress, configure


def preview(themes, identity, native=False):
    palette = themes.load(identity)
    if native:
        # Native panel rendering is exposed by the existing presentation CLI.
        result = subprocess.run([sys.executable, '-B', str(LIB / 'presentation.py'), '--theme', identity, '--native-table'],
                                input=json.dumps(dict(title=palette['theme'] + ' — ' + palette['flavor'], colors=palette['palette'])).encode())
        if result.returncode: raise ValueError('palette preview failed')
    elif sys.stdout.isatty():
        from presentation import render_colors
        render_colors(styles().resolve(palette, themes.directory(identity)), 'Configured sources')
    else:
        print(identity + ' (' + palette['mode'] + ')')
        for key, value in sorted({**palette['colors'], 'mode': palette['mode']}.items()): print(key + '\t' + value)


def shell_init(palette, shell):
    if shell == 'powershell':
        lines = ["$env:DOTS_THEME_ID = '" + palette['id'] + "'", "$env:THEME = '" + palette['theme'] + "'", "$env:FLAVOR = '" + palette['flavor'] + "'"]
        for key, data in (('dots_palette', palette['palette']), ('dots_roles', palette['roles'])):
            lines.append('$global:' + key + ' = @{')
            lines += ["  '" + k + "' = '" + v + "'" for k, v in data.items()]
            lines.append('}')
        lines.append('$global:dots_colors = @{')
        for name, value in {**palette['palette'], **palette['roles']}.items():
            lines.append("  '" + name + "' = @{")
            for format in FORMATS:
                result = metric(name, value, format)
                expression = "'" + result.replace("'", "''") + "'"
                if result.startswith('\x1b'):
                    expression = "([string][char]27 + '" + result[1:] + "')"
                lines.append("    '" + format + "' = " + expression)
            lines.append('  }')
        lines.append('}')
        return '\n'.join(lines) + '\n'
    if shell == 'fish':
        lines = ['set -gx DOTS_THEME_ID ' + palette['id'], 'set -gx THEME ' + palette['theme'], 'set -gx FLAVOR ' + palette['flavor']]
        for key, value in palette['palette'].items(): lines.append("set -g dots_color_" + key + " '" + value + "'")
        for key, value in palette['roles'].items(): lines.append("set -g dots_role_" + key + " '" + value + "'")
        return '\n'.join(lines) + '\n'
    if shell not in ('bash', 'zsh'): raise ValueError('unknown initialization shell')
    import shlex
    lines = ['export DOTS_THEME_ID=' + palette['id'], 'export THEME=' + palette['theme'] + ' FLAVOR=' + palette['flavor']]
    for name, values in (('dots_palette', palette['palette']), ('dots_roles', palette['roles'])):
        lines.append('declare -gA ' + name + '=(' + ' '.join('[' + key + ']=' + shlex.quote(value) for key, value in values.items()) + ')')
    for name, value in {**palette['palette'], **palette['roles']}.items():
        lines.append('declare -gA ' + name + '=(' + ' '.join('[' + fmt + ']=' + shlex.quote(metric(name, value, fmt)) for fmt in FORMATS) + ')')
    return '\n'.join(lines) + '\n'


def connectors(themes):
    home = Path(os.environ.get('HOME') or Path.home())
    config = Path(os.environ.get('XDG_CONFIG_HOME') or home / '.config')
    result = []
    themes.connector_guards = {}
    for line in (LIB / 'connectors.tsv').read_text().splitlines():
        app, suffix, artifact = line.split('\t')
        if os.name == 'nt':
            if app not in ('yazi', 'git', 'vivid'): continue
            from app_paths import config_directory
            base = config_directory('yazi') if app == 'yazi' else config / app
        else: base = config / app
        target = base / suffix
        if target.parent.is_dir():
            if base.is_symlink():
                from catalog import Catalog, platform
                owners = Catalog(themes.checkout, platform()).records()
                owner = next((r for r in owners if r['app'] == app and r['enabled'] and r['applicable']
                              and r['strategy'] == 'directory-link' and r['target'] == str(base)
                              and base.resolve() == Path(r['source'])), None)
                if not owner: raise ValueError('unmanaged application directory link: ' + str(base))
                themes.connector_guards[str(base)] = digest(base)
                target = Path(owner['source']) / suffix
            result.append((target, artifact))
    if os.name != 'nt' and os.environ.get('TERMUX_VERSION') and (home / '.termux').is_dir():
        result.append((home / '.termux/colors.properties', 'termux.properties'))
    for base, suffix, artifact in ((Path(os.environ.get('CODEX_HOME') or home / '.codex'), 'themes/dots.tmTheme', 'bat.tmTheme'),
                                  (Path(os.environ.get('PI_CODING_AGENT_DIR') or home / '.pi/agent').expanduser(), 'themes/dots.json', 'pi.json')):
        if not base.is_absolute(): raise ValueError('application home must be absolute')
        if (base / suffix).parent.is_dir(): result.append((base / suffix, artifact))
    return result


def generated_commands(themes, out):
    directory = out / 'commands'
    (directory / 'bin').mkdir(parents=True)
    reserved = set('themes env theme dots anodize current_theme help list current dir show color colors init set refresh switcher install update remove bg plugin plugins summary'.split())
    names = sorted((set(themes.families()) | set(themes.ids())) - reserved)
    for name in names:
        if not ID.fullmatch(name): raise ValueError('unsafe generated command name')
        ps = "& (Join-Path $env:DOTS 'bin/dots.ps1') theme '" + name + "' @args\nexit $LASTEXITCODE\n"
        (directory / 'bin' / (name + '.ps1')).write_text(ps, encoding='utf-8')
        bash = '#!/usr/bin/env bash\nexec "${DOTS:?}/bin/dots" theme ' + name + ' "$@"\n'
        path = directory / 'bin' / name
        path.write_text(bash); path.chmod(0o755)
    (directory / 'names').write_text('\n'.join(names) + '\n')
    fingerprint = hashlib.sha256(json.dumps(themes.families(), sort_keys=True).encode())
    for path in sorted((directory / 'bin').iterdir()): fingerprint.update(path.read_bytes())
    (directory / 'fingerprint').write_text(fingerprint.hexdigest() + '\n')
    files = {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.rglob('*') if p.is_file()}
    (directory / 'manifest.json').write_text(json.dumps(files))


def generation_complete(themes, directory):
    required = {'id','selection','fingerprint','palette.json','shell.tsv','init.ps1','init.zsh','init.fish',
                'colors.json','colors.lua','ls_colors','file-styles.tsv','git-styles.tsv',
                'yazi/flavor.toml','yazi/tmtheme.xml'}
    for base in (themes.config / 'themed', themes.templates):
        required.update(path.stem for path in base.glob('*.tpl'))
    return all((directory / name).is_file() and not (directory / name).is_symlink() for name in required)


def validate_pointers(themes):
    """Refuse unrelated state and modified generated commands before publication."""
    token = themes.state / 'themes/current'
    active = themes.state / 'current/theme'
    commands = themes.state / 'themes/commands/current'
    for path in (token, active, commands): parents_safe(path)
    if exists(token):
        value = regular(token).decode().strip()
        if not re.fullmatch(r'g\.[a-zA-Z0-9]+', value): raise ValueError('invalid theme generation')
    if exists(active):
        if not active.is_symlink(): raise ValueError('unmanaged active theme pointer')
        target = active.resolve()
        if target.parent != themes.state / 'themes/generations' or not target.name.startswith('g.'):
            raise ValueError('unmanaged active theme pointer')
        if target.is_symlink() or not target.is_dir() or not (target / 'status').is_file():
            raise ValueError('unrecognized active theme generation')
    if exists(commands):
        if not commands.is_symlink(): raise ValueError('unmanaged command pointer')
        target = commands.resolve()
        separate = target.parent == themes.state / 'themes/commands/generations' and re.fullmatch(r'g\.[a-zA-Z0-9]+', target.name)
        bundled = target.name == 'commands' and target.parent.parent == themes.state / 'themes/generations' and re.fullmatch(r'g\.[a-zA-Z0-9]+', target.parent.name)
        if not (separate or bundled): raise ValueError('unmanaged command pointer')
        manifest = json.loads(regular(target / 'manifest.json'))
        actual = {str(p.relative_to(target)): hashlib.sha256(regular(p)).hexdigest()
                  for p in target.rglob('*') if p.is_file() and p != target / 'manifest.json'}
        if actual != manifest: raise ValueError('generated command drift; preserve and review')


def commands_refresh(themes, verbose=False):
    validate_pointers(themes)
    pointer = themes.state / 'themes/commands/current'
    parents_safe(pointer)
    before = digest(pointer)
    with tempfile.TemporaryDirectory(prefix='dots-theme-commands-') as tmp:
        out = Path(tmp)
        generated_commands(themes, out)
        stage = out / 'commands'
        if pointer.is_symlink():
            old = pointer.resolve()
            if not old.is_relative_to(themes.state / 'themes'):
                raise ValueError('unmanaged command pointer')
            manifest_path = old / 'manifest.json'
            if manifest_path.is_file():
                manifest = json.loads(regular(manifest_path))
                actual = {str(p.relative_to(old)): hashlib.sha256(regular(p)).hexdigest() for p in old.rglob('*') if p.is_file() and p != manifest_path}
                if actual != manifest: raise ValueError('generated command drift; preserve and review')
                if regular(old / 'fingerprint') == regular(stage / 'fingerprint'):
                    OperationOutput(verbose)('Unchanged', pointer, reason='generated commands match'); return
            else: raise ValueError('command generation lacks a native ownership manifest')
        elif exists(pointer): raise ValueError('unmanaged command pointer')
        generation = themes.state / 'themes/commands/generations' / ('g.' + uuid.uuid4().hex)
        Store(themes.state, OperationOutput(verbose)).apply('theme-commands',
            [dict(path=str(generation), source=str(stage)), dict(path=str(pointer), link=str(generation), directory=True)],
            {str(pointer):before, str(generation):None}, retain=True)
    Presentation().emit('  Theme commands refreshed')


def publication(themes, identity, dry=False, verbose=False, refresh=False):
    if os.environ.get('DOTS_THEME_PLUGIN_RUNNING'): raise ValueError('recursive theme publication from a plugin is refused')
    ui, events = Presentation(), OperationOutput(verbose)
    validate_pointers(themes)
    active, token = themes.state / 'current/theme', themes.state / 'themes/current'
    parents_safe(active); parents_safe(token)
    for path in (themes.state / 'themes/generations').glob('*/status'):
        if regular(path).decode().strip() == 'prepared': raise ValueError('legacy interrupted theme publication requires recovery before native publication')
    links = connectors(themes)
    # Capture every live input before rendering or any writes to managed state.
    targets = [active, token, themes.state / 'themes/commands/current', *(p for p, _ in links)]
    guards = dict(getattr(themes, 'connector_guards', {}))
    for path in targets:
        parents_safe(path)
        if path.is_dir() and not path.is_symlink(): raise ValueError('cannot replace a real theme connector directory: ' + str(path))
        guards[str(path)] = digest(path)
    fingerprint = themes.fingerprint(identity)
    if token.is_file() and not token.is_symlink():
        current = token.read_text().strip()
        if not re.fullmatch(r'g\.[a-zA-Z0-9]+', current): raise ValueError('invalid theme generation')
        prior = themes.state / 'themes/generations' / current
        if (prior / 'fingerprint').is_file() and (prior / 'id').is_file() and regular(prior / 'fingerprint').decode().strip() == fingerprint and regular(prior / 'id').decode().strip() == identity:
            if generation_complete(themes, prior) and active.is_symlink() and active.resolve() == prior and all(p.is_symlink() and p.resolve() == prior / artifact for p, artifact in links):
                events('Unchanged', prior, reason='theme and connectors match')
                ui.emit('  Theme unchanged: ' + identity)
                if refresh and not dry: reload_apps(themes, events)
                return current
    if dry:
        themes.load(identity)
        ui.heading('Theme preview')
        ui.detail('Select', identity)
        events('Would publish', target=active)
        for target, artifact in links:
            ui.resource_detail('Connect', target)
            events('Would link', active / artifact, target)
        ui.emit('  Preview only; no changes made')
        return None
    name = 'g.' + uuid.uuid4().hex
    destination = themes.state / 'themes/generations' / name
    guards[str(destination)] = None
    with tempfile.TemporaryDirectory(prefix='dots-theme-') as tmp:
        out = Path(tmp)
        with Progress('Rendering application themes'):
            palette = themes.render(identity, out, build_cache=True)
            for shell in ('powershell', 'zsh', 'fish'):
                (out / ('init.' + ('ps1' if shell == 'powershell' else shell))).write_text(shell_init(palette, shell), encoding='utf-8')
            generated_commands(themes, out)
            (out / 'status').write_text('committed\n')
            if themes.fingerprint(identity) != fingerprint: raise ValueError('theme inputs changed during preparation')
        operations = [dict(path=str(destination), source=str(out))]
        for target, artifact in links:
            if not (out / artifact).exists(): raise ValueError('missing connector artifact: ' + artifact)
            if target.is_symlink() and os.readlink(target) == str(active / artifact) and artifact != 'pi.json': continue
            operations.append(dict(path=str(target), link=str(active / artifact), directory=(out / artifact).is_dir()))
        operations += [dict(path=str(themes.state / 'themes/commands/current'), link=str(destination / 'commands'), directory=True),
                       dict(path=str(token), text=name + '\n'), dict(path=str(active), link=str(destination), directory=True)]
        store = Store(themes.state, events)
        with Progress('Publishing theme'):
            result = store.apply('theme-set', operations, guards, retain=True)
        ui.heading('Theme selected: ' + identity)
        ui.detail('Transaction', result['id'])
    reload_apps(themes, events)
    return name


def reload_apps(themes, events):
    active = themes.state / 'current/theme'
    commands = []
    if os.name != 'nt':
        if os.environ.get('TERMUX_VERSION') and (Path(os.environ.get('HOME') or Path.home()) / '.termux').is_dir() and shutil.which('termux-reload-settings'): commands.append(['termux-reload-settings'])
        if os.environ.get('TMUX') and shutil.which('tmux'): commands.append(['tmux', 'source-file', str(active / 'tmux.conf')])
        if os.environ.get('KITTY_LISTEN_ON') and shutil.which('kitty'): commands.append(['kitty', '@', '--to', os.environ['KITTY_LISTEN_ON'], 'set-colors', '--all', '--configured', str(active / 'kitty.conf')])
    if shutil.which('ya'): commands.append(['ya', 'pub-to', '0', 'dots-theme-changed', '--str', str(themes.state)])
    failed = False
    for command in commands:
        try:
            with Progress('Reloading ' + command[0]): result = subprocess.run(command, capture_output=True, timeout=15)
            if result.returncode: raise ValueError('reload failed')
            events('Reloaded', reason=command[0])
        except (OSError, ValueError, subprocess.TimeoutExpired):
            if command[0] == 'ya':
                events('Skipped', reason='Yazi notification unavailable')
            else:
                failed = True; events('Failed', reason=command[0] + ' reload; theme remains published')
    if failed: raise ValueError('application reload failed; theme remains published; retry dots theme refresh')
    import plugins
    _, selected = plugins.selection(themes.config.parent)
    if selected['enabled'] and plugins.main(['run'], reason='set'):
        raise ValueError('theme plugin failed; theme remains published; retry dots theme plugins run')


def backgrounds(themes, action, args, preflight=False, identity=None):
    identity = identity or themes.current()
    files = sorted(set(p for base in (themes.directory(identity) / 'backgrounds', themes.config / 'backgrounds' / identity)
                       for p in base.glob('*') if p.is_file() and not p.is_symlink() and p.suffix.lower() in ('.png','.jpg','.jpeg','.webp','.bmp')))
    record, current = themes.state / 'backgrounds' / identity, themes.state / 'background-current'
    if action in ('list', 'current'):
        if args: raise ValueError('unexpected background argument')
        if action == 'list':
            for p in files: print(p)
        elif current.is_file(): print(regular(current).decode().strip())
        return
    locked = False
    if action == 'set':
        if len(args) not in (1, 2) or (len(args) == 2 and args[1] != '--lock-screen'): raise ValueError('Usage: bg set FILE [--lock-screen]')
        path = Path(args[0]).expanduser().resolve(); locked = len(args) == 2
    else:
        if args or not files: raise ValueError('no theme backgrounds or unexpected arguments')
        previous = regular(record).decode().strip() if record.is_file() else ''
        index = next((i for i, p in enumerate(files) if str(p) == previous), 0)
        if action == 'next': index = (index + 1) % len(files) if previous else 0
        elif action == 'switcher':
            from picker_native import choose
            index = choose(themes, files=files)
        elif action != 'select': raise ValueError('unknown background action')
        path = files[index]
    if not path.is_file() or path.suffix.lower() not in ('.png','.jpg','.jpeg','.webp','.bmp'): raise ValueError('background must be an existing image')
    if os.name == 'nt':
        if locked: raise ValueError('lock-screen wallpaper is Android-only')
        command = [sys.executable, '-B', str(LIB / 'wallpaper.py'), str(path)]
    elif os.environ.get('TERMUX_VERSION'):
        command = ['termux-wallpaper', '-f', str(path)] + (['-l'] if locked else [])
    elif os.environ.get('WSL_DISTRO_NAME') or os.environ.get('WSL_INTEROP'): raise ValueError('WSL wallpaper changes are unavailable')
    elif os.environ.get('WAYLAND_DISPLAY'): command = ['swww', 'img', str(path)]
    elif os.environ.get('DISPLAY'): command = ['feh', '--no-fehbg', '--bg-fill', str(path)]
    else: raise ValueError('no supported wallpaper session')
    if not shutil.which(command[0]): raise ValueError('wallpaper adapter unavailable')
    if preflight: return str(path)
    parents_safe(record)
    private_directory(record.parent)
    with os.fdopen(open_nofollow(record.parent / 'lock', os.O_RDWR | os.O_CREAT), 'a') as handle:
        lock(handle)
        guards = {str(p): digest(p) for p in (record, current)}
        journal = record.parent / ('action.' + uuid.uuid4().hex + '.json')
        doc = dict(schema=1, status='prepared', path=str(path), lock_screen=locked)
        atomic_json(journal, doc)
        try:
            with Progress('Applying wallpaper'): result = subprocess.run(command, capture_output=True, timeout=15)
            if result.returncode: raise ValueError('wallpaper failed; app theme remains published')
            if not locked:
                Store(themes.state).apply('theme-background', [dict(path=str(p), text=str(path) + '\n') for p in (record,current)], guards, retain=True)
            doc['status'] = 'committed'; atomic_json(journal, doc)
        except BaseException:
            doc['status'] = 'failed'; atomic_json(journal, doc); raise
    Presentation().resource_detail('Background applied', path)


def family(themes, name, args):
    families = themes.families()
    if name not in families:
        palette = themes.load(name); name, flavor = palette['theme'], palette['flavor']
    else: flavor = None
    if not args or any(arg in ('help','-h','--help') for arg in args):
        ui = Presentation()
        ui.heading('Theme palette: ' + name)
        ui.detail('Usage', 'dots theme ' + name + ' [FLAVOR] [show|set|init|COLOR [FORMAT]]')
        ui.detail('Flavors', list(families.get(name, {})))
        ui.detail('Formats', FORMATS)
        ui.detail('Options', '--flavor, --color NAME, --format, --raw, --array, --all, --completion')
        ui.detail('Activate', 'set [--dry-run] [--background] [--verbose]')
        return
    action, color, format, raw, array, all_flavors = 'show', None, 'hex', False, False, False
    flags = []
    args = [part for arg in args for part in (arg.split('=', 1) if arg.startswith(('--flavor=', '--format=', '--completion=')) else [arg])]
    while args:
        token = args.pop(0)
        if token.startswith(('--color=', '--icons=')):
            key, mode = token[2:].split('=', 1)
            if key == 'color' and mode == 'none': mode = 'never'
            if mode not in ('always', 'never', 'auto'): raise ValueError('invalid decoration mode')
            os.environ['DOTS_' + key.upper()] = mode
        elif token in ('-r','--raw'): raw = True
        elif token in ('-a','--array'): raw = array = True
        elif token == '--all': all_flavors = True
        elif token in ('--dry-run','--background','-v','--verbose'): flags.append(token)
        elif token == 'color': pass
        elif token in ('show','set','init','--init'): action = token.lstrip('-')
        elif token in ('--completion','completion'):
            if len(args) != 1 or args[0] not in ('bash', 'zsh', 'fish', 'powershell'): raise ValueError('expected a completion shell')
            print((LIB.parent / 'completion' / args[0]).read_text(), end=''); return
        elif token in ('-f','--flavor','-c','--color','-F','--format'):
            if not args:
                values = families.get(name, {}) if token in ('-f','--flavor') else FORMATS if token in ('-F','--format') else themes.load(themes.pick(name, flavor))['palette']
                print('\n'.join(values)); return
            value = args.pop(0)
            if token in ('-f','--flavor'): flavor = value
            elif token in ('-F','--format'): format = value
            else: color = value
        elif token == '-e': format = 'esc'
        elif token in ('help','-h','--help'):
            print('Usage: dots theme ' + name + ' [FLAVOR] [show|set|init|COLOR [FORMAT]]'); return
        elif token in families.get(name, {}): flavor = token
        elif token in FORMATS: format = token
        elif token.startswith('-') or color: raise ValueError('invalid palette argument: ' + token)
        else: color = token
    identities = list(families[name].values()) if all_flavors else [themes.pick(name, flavor)]
    if action != 'show':
        if all_flavors or raw or color: raise ValueError('invalid activation/export options')
        if action == 'set': main(['set', identities[0], *flags])
        else: print(shell_init(themes.load(identities[0]), 'powershell' if os.name == 'nt' else 'bash'), end='')
        return
    if flags: raise ValueError('operation flags require set')
    for identity in identities:
        palette = themes.load(identity)
        if not color and not raw and format == 'hex': preview(themes, identity, native=True); continue
        colors = {color: palette['palette'][color]} if color in palette['palette'] else palette['palette'] if color is None else None
        if colors is None: raise ValueError('unknown palette color')
        for key, value in colors.items():
            result = metric(key, value, format)
            if array and os.name == 'nt': print('$' + key + " = '" + result.replace("'", "''") + "'")
            elif array:
                import shlex
                print(key + '=' + shlex.quote(result))
            else: print(result if raw or color else key.ljust(20) + ' ' + result)


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    themes = Themes()
    action = args.pop(0) if args else 'summary'
    verbose = any(a in ('-v','--verbose') for a in args)
    if action in ('set','refresh','switcher'):
        args = [a for a in args if a not in ('-v','--verbose')]
    if action in ('summary','show'):
        native = '--native' in args; args = [a for a in args if a != '--native']
        if len(args) > 1: raise ValueError('show accepts at most one theme ID')
        preview(themes, args[0] if args else themes.current(), native or action == 'summary')
    elif action == 'list':
        if not args: values = themes.ids()
        elif args == ['--families']: values = sorted(k for k,v in themes.families().items() if list(v) != ['default'])
        elif len(args) == 2 and args[0] == '--flavors': values = sorted(themes.families().get(args[1], {}))
        elif len(args) == 1 and args[0].startswith('--flavors='): values = sorted(themes.families().get(args[0].split('=',1)[1], {}))
        else: raise ValueError('invalid list options')
        print('\n'.join(values))
    elif action == 'current':
        if args: raise ValueError('current takes no arguments')
        print(themes.current())
    elif action == 'dir':
        if len(args)>1: raise ValueError('dir accepts at most one ID')
        print(themes.directory(args[0] if args else themes.current()))
    elif action == 'color':
        parser = argparse.ArgumentParser()
        parser.add_argument('name'); parser.add_argument('format', nargs='?', default='hex', choices=FORMATS)
        parser.add_argument('--theme'); parser.add_argument('--native', action='store_true')
        options = parser.parse_args(args); palette = themes.load(options.theme or themes.current())
        colors = palette['palette'] if options.native else {**palette['palette'], **palette['colors'], 'mode':palette['mode']}
        if options.name not in colors: raise ValueError('unknown color')
        print(colors[options.name] if options.name == 'mode' else metric(options.name, colors[options.name], options.format))
    elif action == 'init':
        parser = argparse.ArgumentParser(); parser.add_argument('--shell', default='powershell' if os.name == 'nt' else 'zsh', choices=['powershell','bash','zsh','fish'])
        options = parser.parse_args(args); print(shell_init(themes.load(themes.current()), options.shell), end='')
    elif action in ('set','refresh'):
        parser = argparse.ArgumentParser()
        if action == 'set': parser.add_argument('identity')
        else: parser.add_argument('--commands-only', action='store_true')
        parser.add_argument('--dry-run', action='store_true'); parser.add_argument('--background', action='store_true')
        options = parser.parse_args(args)
        if action == 'refresh' and options.commands_only:
            if options.dry_run or options.background: raise ValueError('--commands-only does not accept publication options')
            commands_refresh(themes, verbose)
            return 0
        identity = options.identity if action == 'set' else themes.current()
        configure(not options.dry_run)
        wallpaper = backgrounds(themes, 'select', [], preflight=True, identity=identity) if options.background else None
        publication(themes, identity, options.dry_run, verbose, refresh=action == 'refresh')
        if wallpaper and not options.dry_run: backgrounds(themes, 'set', [wallpaper], identity=identity)
    elif action == 'switcher':
        if args: raise ValueError('unexpected switcher options')
        from picker_native import choose
        ids = themes.ids()
        while True:
            identity = ids[choose(themes, identities=ids)]
            preview(themes, identity)
            answer = Selector().pick('choose', 'Apply selected theme?', ['Cancel','Back','Apply'], 'Cancel')
            if answer == 'Back': continue
            if answer == 'Apply': publication(themes, identity, verbose=verbose)
            break
    elif action == 'bg':
        if not args: raise ValueError('choose bg list|current|set|next|select|switcher')
        backgrounds(themes, args[0], args[1:])
    elif action in ('install','update','remove'):
        from theme_source import source_operation
        source_operation(themes, action, args)
    else: family(themes, action, args)
    return 0


if __name__ == '__main__':
    try: sys.exit(main())
    except SelectionEnded as ended: sys.exit(ended.status)
    except (OSError, ValueError) as error:
        print('dots theme: ' + str(error), file=sys.stderr); sys.exit(1)
    except KeyboardInterrupt: sys.exit(130)

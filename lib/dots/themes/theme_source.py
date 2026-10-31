"""Explicit Git theme imports using retained, guarded file transactions."""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import uuid

from palette_native import ID, literal
from catalog import Presentation
from transactions import Store, digest, parents_safe, exists
from progress import Progress


def git(*args):
    env = dict(os.environ, GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
               GIT_TERMINAL_PROMPT='0', GIT_OPTIONAL_LOCKS='0')
    # A caller's injected Git config must not override the import protocol policy.
    for key in list(env):
        if key.startswith(('GIT_CONFIG_KEY_', 'GIT_CONFIG_VALUE_')) or key in ('GIT_CONFIG_COUNT', 'GIT_CONFIG_PARAMETERS', 'GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR'): env.pop(key)
    result = subprocess.run(['git', '-c', 'core.hooksPath=' + os.devnull, '-c', 'protocol.allow=never',
                             '-c', 'protocol.https.allow=always', '-c', 'protocol.ssh.allow=always',
                             '-c', 'protocol.file.allow=' + os.environ.get('DOTS_TEST_LOCAL_GIT', 'never'), *map(str,args)],
                            capture_output=True, env=env)
    if result.returncode: raise ValueError('Git theme operation failed; check transport, credentials and history')
    return result.stdout.decode('utf-8').strip()


def source_operation(themes, action, args):
    from theme_cli import generated_commands, validate_pointers
    validate_pointers(themes)
    if action == 'update' and args == ['--all']:
        failures = []
        for path in sorted(themes.user.glob('*/.git/dots-managed')):
            try: source_operation(themes, action, [path.parent.parent.name])
            except (ValueError, OSError): failures.append(path.parent.parent.name)
        if failures: raise ValueError('theme updates failed: ' + ', '.join(failures))
        return
    url = branch = old = None
    if action == 'install':
        if len(args) not in (1, 3) or (len(args) == 3 and args[1] != '--name'): raise ValueError('Usage: theme install URL [--name ID]')
        url = args[0]
        if not (re.fullmatch(r'(?:https://|ssh://)\S+', url) or re.fullmatch(r'[a-zA-Z0-9_.-]+@[a-zA-Z0-9_.-]+:\S+', url) or (os.environ.get('DOTS_TEST_LOCAL_GIT') == 'always' and Path(url).is_absolute())):
            raise ValueError('expected an HTTPS or SSH Git URL')
        name = args[2] if len(args) == 3 else re.sub(r'^(?:omarchy-|dots-)|-theme$', '', re.sub(r'\.git$', '', url.rsplit('/',1)[-1].rsplit(':',1)[-1])).lower()
    else:
        if len(args) != 1: raise ValueError('expected one theme ID')
        name = args[0]
    if not ID.fullmatch(name): raise ValueError('invalid theme identifier')
    if (themes.root / name).exists(): raise ValueError('bundled theme identifiers cannot be replaced')
    target = themes.user / name
    parents_safe(target)
    before = digest(target)
    if action == 'install':
        if exists(target): raise ValueError('theme identifier already exists')
    else:
        if target.is_symlink() or not (target / '.git/dots-managed').is_file() or (target / '.git').is_symlink(): raise ValueError('not a Dots-managed Git theme')
        if git('-C', target, 'status', '--porcelain', '--untracked-files=all'): raise ValueError('installed theme has local changes')
        if action == 'remove' and themes.current() == name: raise ValueError('cannot remove the active theme')
        if action == 'update':
            url = git('-C', target, 'remote', 'get-url', 'origin')
            branch = git('-C', target, 'symbolic-ref', '--short', 'HEAD')
            old = git('-C', target, 'rev-parse', 'HEAD')
    pointer = themes.state / 'themes/commands/current'
    guards = {str(target):before, str(pointer):digest(pointer),
              str(themes.state / 'themes/current'):digest(themes.state / 'themes/current')}
    with tempfile.TemporaryDirectory(prefix='dots-theme-import-') as directory:
        stage = Path(directory) / 'source'
        if action != 'remove':
            with Progress('Downloading theme: ' + name):
                git('clone', '--quiet', '--no-recurse-submodules', '--template=', *(['--branch', branch] if branch else []), '--', url, stage)
            for path in stage.rglob('*'):
                if path.is_symlink() or not (path.is_file() or path.is_dir()): raise ValueError('installed theme contains unsafe objects')
            if not any((stage / f).is_file() for f in ('colors.toml','palette.toml')): raise ValueError('installed themes require colors.toml or palette.toml')
            for file, kind in (('theme.toml','metadata'),('palette.toml','palette'),('colors.toml','colors')):
                if (stage / file).exists(): literal(stage / file, kind)
            if old: git('-C', stage, 'merge-base', '--is-ancestor', old, 'HEAD')
            (stage / '.git/dots-managed').write_text('schema=1\n')
        class Pending(type(themes)):
            def ids(self): return sorted((set(super().ids()) - {name}) | ({name} if action != 'remove' else set()))
            def directory(self, identity): return stage if identity == name and action != 'remove' else super().directory(identity)
        command_stage = Path(directory) / 'generated'
        command_stage.mkdir()
        generated_commands(Pending(), command_stage)
        generation = themes.state / 'themes/commands/generations' / ('g.' + uuid.uuid4().hex)
        guards[str(generation)] = None
        operations = [dict(path=str(target), **({'source':str(stage)} if action != 'remove' else {'delete':True})),
                      dict(path=str(generation), source=str(command_stage / 'commands')),
                      dict(path=str(pointer), link=str(generation), directory=True)]
        result = Store(themes.state).apply('theme-' + action, operations, guards, retain=True)
        ui = Presentation(); ui.heading(action + ': ' + name + ' (selection unchanged)'); ui.detail('Recovery transaction', result['id'])

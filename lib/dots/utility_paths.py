"""Native path inspection for the existing standalone shell utilities."""
import json
import os
from pathlib import Path
import re
import shlex


MODES = {'--full': 'l', '-d': 'd', '--dirname': 'd', '-b': 'b', '--basename': 'b',
         '-p': 'p', '--prefix': 'p', '-s': 's', '--source': 's', '-D': 'D',
         '--source-dirname': 'D', '-B': 'B', '--source-basename': 'B', '-C': 'c',
         '--shared-prefix': 'c', '-e': 'e', '--link-branch-dir': 'e', '-E': 'E',
         '--source-branch-dir': 'E', '-m': 'm', '--shared-basename': 'm'}


def cwd():
    candidate = os.environ.get('DOTS_UTILITY_PWD') or os.environ.get('PWD')
    if candidate and os.path.isabs(candidate):
        try:
            if os.path.samefile(candidate, os.getcwd()):
                return os.path.normpath(candidate)
        except OSError:
            pass
    return os.getcwd()


def display(value, raw=False):
    home = os.path.normpath(str(Path.home()))
    if raw:
        return value
    if os.path.normcase(value) == os.path.normcase(home):
        return '~'
    if os.path.normcase(value).startswith(os.path.normcase(home + os.sep)):
        return '~' + value[len(home):]
    return value


def parts(path):
    return list(Path(path).parts) if path else []


def link_components(path):
    current = Path(Path(path).anchor)
    found = []
    for index, piece in enumerate(Path(path).parts):
        if index == 0 and piece == current.anchor:
            continue
        current /= piece
        if current.is_symlink() or getattr(current, 'is_junction', lambda: False)():
            found.append((index, str(current)))
    return found


def array_shell(value='auto'):
    if value == 'auto':
        value = os.environ.get('LINKED_ARRAY_SHELL') or os.path.basename(os.environ.get('SHELL', 'bash'))
        value = 'zsh' if os.path.basename(value) == 'zsh' else 'bash'
    if value not in ('bash', 'zsh'):
        raise ValueError('array shell must be auto, bash or zsh; use --json in PowerShell')
    return value


def linked_data(operand=None, raw=False):
    current = cwd()
    supplied = operand is not None
    value = current if operand is None else operand
    if not value:
        raise FileNotFoundError('path does not exist: empty path')
    target = os.path.normpath(os.path.join(current, value))
    if not os.path.lexists(target):
        raise FileNotFoundError('path does not exist: ' + value)
    links = link_components(target)
    if not links:
        raise FileNotFoundError('no symlink or junction component found in path: ' + target)
    index, link = links[-1]
    readlink = os.readlink(link)
    source = readlink
    if os.name == 'nt' and source.startswith('\\\\?\\UNC\\'):
        source = '\\\\' + source[8:]
    elif os.name == 'nt' and source.startswith('\\\\?\\'):
        source = source[4:]
    source = os.path.normpath(os.path.join(os.path.dirname(link), source))
    source = os.path.join(os.path.realpath(os.path.dirname(source)), os.path.basename(source))
    prefix = os.path.relpath(target, link)
    prefix = '' if prefix == '.' else prefix
    combined = os.path.join(source, prefix) if prefix else source
    try:
        common = os.path.commonpath((link, source))
    except ValueError:
        common = ''  # Distinct native volumes have no common directory.
    def branch(path):
        relative = os.path.relpath(path, common) if common else path
        return '' if relative == '.' else relative
    link_branch, source_branch = branch(os.path.dirname(link)), branch(os.path.dirname(source))
    link_base, source_base = os.path.basename(link), os.path.basename(source)
    shared = link_base if link_base == source_base else ''
    def path_row(path):
        physical = os.path.realpath(path) if os.path.isdir(path) else os.path.join(
            os.path.realpath(os.path.dirname(path)), os.path.basename(path))
        return dict(logical=path, physical=physical, display=display(path), parts=parts(path))
    placeholders = dict(l=display(link, raw), d=display(os.path.dirname(link), raw), b=link_base,
        p=prefix, s=display(source, raw), D=display(os.path.dirname(source), raw), B=source_base,
        P=display(combined, raw), c=display(common, raw), e=link_branch, E=source_branch, m=shared)
    return dict(tool='linked', raw_output=raw, array_shell_default=array_shell(),
        input=dict(provided=supplied, path=value), current_pwd=path_row(current),
        target=path_row(target), pwd=path_row(target),
        symlink=dict(path=link, display_path=display(link), dirname=os.path.dirname(link),
            display_dirname=display(os.path.dirname(link)), basename=link_base, index=index,
            readlink=readlink, branch_dir=link_branch, branch_parts=parts(link_branch), parts=parts(link)),
        source=dict(path=source, display_path=display(source), dirname=os.path.dirname(source),
            display_dirname=display(os.path.dirname(source)), basename=source_base, branch_dir=source_branch,
            branch_parts=parts(source_branch), with_prefix=combined, display_with_prefix=display(combined),
            parts=parts(source), with_prefix_parts=parts(combined)),
        prefix=dict(path=prefix, parts=parts(prefix), part_count=len(parts(prefix))),
        shared_prefix=dict(path=common, display_path=display(common), parts=parts(common), part_count=len(parts(common))),
        branch_dirs=dict(link=link_branch, source=source_branch, link_parts=parts(link_branch), source_parts=parts(source_branch)),
        basename=dict(link=link_base, source=source_base, match=bool(shared), shared=shared),
        placeholders={'%' + key: value for key, value in placeholders.items()})


def arrays(data, shell):
    shell = array_shell(shell)
    flat = dict(tool='linked', array_shell=shell, input_provided=int(data['input']['provided']),
        input_path=data['input']['path'], pwd=data['target']['logical'], target_path=data['target']['logical'],
        target_physical=data['target']['physical'], current_pwd=data['current_pwd']['logical'],
        current_pwd_physical=data['current_pwd']['physical'], symlink_path=data['symlink']['path'],
        symlink_dirname=data['symlink']['dirname'], symlink_basename=data['symlink']['basename'],
        symlink_index=data['symlink']['index'], symlink_readlink=data['symlink']['readlink'],
        link_branch_dir=data['branch_dirs']['link'], source_path=data['source']['path'],
        source_dirname=data['source']['dirname'], source_basename=data['source']['basename'],
        source_branch_dir=data['branch_dirs']['source'], source_with_prefix=data['source']['with_prefix'],
        prefix=data['prefix']['path'], shared_prefix=data['shared_prefix']['path'],
        bases_match=int(data['basename']['match']), shared_basename=data['basename']['shared'])
    shown = {key: display(str(value), data['raw_output']) for key, value in flat.items()}
    shown.update(data['placeholders'], raw_output=str(int(data['raw_output'])))
    def emit(name, values):
        if shell == 'bash':
            return 'declare -gA ' + name + '=(' + ' '.join('[' + shlex.quote(str(k)) + ']=' + shlex.quote(str(v)) for k, v in values.items()) + ')'
        return 'typeset -gA ' + name + '=(' + ' '.join(shlex.quote(str(k)) + ' ' + shlex.quote(str(v)) for k, v in values.items()) + ')'
    lines = [emit('linked', shown), emit('linked_raw', flat)]
    for name, values in dict(target=data['target']['parts'], pwd=data['target']['parts'],
        current_pwd=data['current_pwd']['parts'], symlink=data['symlink']['parts'], source=data['source']['parts'],
        source_with_prefix=data['source']['with_prefix_parts'], prefix=data['prefix']['parts'],
        shared_prefix=data['shared_prefix']['parts'], link_branch=data['branch_dirs']['link_parts'],
        source_branch=data['branch_dirs']['source_parts']).items():
        start = 1 if shell == 'zsh' else 0
        mapping = {str(index + start): value for index, value in enumerate(values)}
        mapping['__length'] = str(len(values))
        lines.append(emit('linked_' + name + '_parts', mapping))
    return '\n'.join(lines)


def linked(arguments):
    operand = None; mode = 'l'; raw = False; template = ''; shell = 'auto'
    arguments = list(arguments)
    while arguments:
        argument = arguments.pop(0)
        if argument in ('--help', '-h'):
            from utility_cli import help_text
            print(help_text('linked'), end='')
            return 0
        if argument == '--completion' or argument.startswith('--completion='):
            shell = argument.partition('=')[2] if '=' in argument else (arguments.pop(0) if arguments else '')
            from utility_cli import main
            return main(['linked', '--completion', shell])
        if argument == '--':
            if len(arguments) > 1 or (arguments and operand is not None):
                raise ValueError('expected one path')
            if arguments: operand = arguments[0]
            break
        if argument in MODES: mode = MODES[argument]
        elif argument in ('-r', '--raw'): raw = True
        elif argument in ('-j', '--json'): mode = 'json'
        elif argument in ('-f', '--format'):
            if not arguments: raise ValueError('missing format string')
            mode = 'format'; template = arguments.pop(0)
        elif argument.startswith('--format='): mode = 'format'; template = argument.partition('=')[2]
        elif argument in ('-A', '--arrays', '--array'):
            mode = 'arrays'
            if arguments and arguments[0] in ('auto', 'bash', 'zsh'): shell = arguments.pop(0)
        elif argument.startswith(('--arrays=', '--array=')): mode = 'arrays'; shell = argument.partition('=')[2]
        elif argument.startswith('-'): raise ValueError('unknown option: ' + argument)
        elif operand is not None: raise ValueError('expected one path')
        else: operand = argument
    array_shell(shell)
    data = linked_data(operand, raw)
    if mode == 'json': print(json.dumps(data, ensure_ascii=True, indent=2))
    elif mode == 'arrays': print(arrays(data, shell))
    elif mode == 'format': print(re.sub(r'%[%ldbpsDBPceEm]', lambda m: '%' if m[0] == '%%' else data['placeholders'][m[0]], template))
    else: print(data['placeholders']['%' + mode])
    return 0


def path_command(name, arguments):
    if name in ('isdir', 'isfile'):
        if arguments[:1] == ['--']: arguments = arguments[1:]
        target = arguments[0] if arguments else ''
        return 0 if target and (os.path.isdir(target) if name == 'isdir' else os.path.isfile(target)) else 1
    if name == 'lnkd':
        links = link_components(cwd())
        for _, path in links: print(path)
        return 0 if links else 1
    if name == 'linked': return linked(arguments)
    raw = styled = join = False; arguments = list(arguments)
    while arguments:
        option = arguments[0]
        if option in ('-r', '--raw'): raw = True
        elif name == 'dirout' and option in ('-c', '--color'): styled = True
        elif name == 'dirout' and option in ('-j', '--join'): join = True
        elif option == '--': arguments.pop(0); break
        else: break
        arguments.pop(0)
    if name == 'dirout' and not arguments: arguments = [cwd()]
    painter = None
    if styled:
        from files.catalog import Presentation
        painter = Presentation()
    for argument in arguments:
        value = (os.path.dirname(argument.rstrip('/\\')) or '.') if name == 'dirout' else argument
        # A native root's dirname is itself, as with POSIX dirname /.
        if name == 'dirout' and Path(argument).anchor == argument: value = argument
        value = display(value, raw) + (os.sep if join else '')
        print(painter.paint(value, '34') if painter else value)
    return 0

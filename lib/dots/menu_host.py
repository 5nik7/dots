#!/usr/bin/env python3
"""Private menu transport entry; not a public dots command or extension API."""
import os
from pathlib import Path
import subprocess
import sys

from menu_tmux import TmuxContext, read_request, status


def literal_argv(argv):
    if not isinstance(argv, (list, tuple)) or not argv or not argv[0] or not all(isinstance(a, str) and '\0' not in a for a in argv):
        raise ValueError('invalid menu action arguments')
    return list(argv)


def execute(argv, *, cwd=None, environment=None):
    try:
        return status(subprocess.call(literal_argv(argv), cwd=cwd, env=environment))
    except KeyboardInterrupt:
        return 130
    except OSError:
        print('dots menu: selected command could not be started', file=sys.stderr)
        return 2


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) < 2 or args[0] not in ('host', 'proxy'):
        raise ValueError('invalid private menu invocation')
    kind, path, *forward = args
    data = read_request(path)
    if kind == 'proxy':
        # This is a private FZF adapter, not a general replacement for tmux.
        if (not forward or forward[0] != 'display-popup'
                or any(arg.startswith('-c') or arg == '-C' for arg in forward[1:])):
            raise ValueError('unsupported FZF tmux request')
        context = TmuxContext(**data['context'])
        context.verify()
        return status(subprocess.call(context.command('display-popup', '-c', context.client, *forward[1:])))
    if forward:
        raise ValueError('invalid private menu invocation')
    command = literal_argv(data.get('argv'))
    cwd, environment, hold = data.get('cwd'), data.get('environment'), data.get('hold')
    if (not isinstance(cwd, str) or not os.path.isabs(cwd) or '\0' in cwd
            or type(hold) is not bool or not isinstance(environment, dict)
            or not all(isinstance(k, str) and isinstance(v, str) and k and '=' not in k
                       and '\0' not in k + v for k, v in environment.items())):
        raise ValueError('invalid private menu request')
    receipt = Path(path).with_suffix('.status')
    environment = dict(environment, DOTS_MENU_SPOOL_DIR=str(receipt.parent))
    environment.pop('DOTS_MENU_READER_HANDOFF', None)
    if data.get('defer_reader') is True:
        environment['DOTS_MENU_READER_HANDOFF'] = str(path)
    def completed(code):
        with receipt.open('x', encoding='ascii') as stream:
            if os.name != 'nt':
                os.fchmod(stream.fileno(), 0o600)
            stream.write(str(code))
    if hold:
        from menu_pager import capture, prepare
        from resources import clean
        title = data.get('title', 'Dots output')
        size = data.get('render_size')
        if (not isinstance(title, str) or size is not None and
                (not isinstance(size, list) or len(size) != 2 or
                 not all(type(n) is int and n > 0 for n in size))):
            raise ValueError('invalid private menu request')
        print('Loading ' + clean(title) + '…', flush=True)
        code, source = capture(command, receipt.parent, cwd=cwd, environment=environment,
                               render_size=size)
        prepare(source, receipt.parent, title=title, code=code)
        completed(code)
        return code
    code = execute(command, cwd=cwd, environment=environment)
    completed(code)
    if code not in (0, 130):
        try:
            input('\nPress Enter to close. ')
        except (EOFError, KeyboardInterrupt):
            pass
    return code


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except (ValueError, OSError, KeyError, TypeError, subprocess.TimeoutExpired):
        # Requests can contain caller arguments/environment; never dump them.
        print('dots menu: terminal handoff failed', file=sys.stderr)
        sys.exit(2)

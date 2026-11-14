"""Native HTTP, browser and cheat-sheet adapters. Tests inject all providers."""
import os
from pathlib import Path
import re
import secrets
import sys
from urllib.parse import quote, urlencode, urlsplit, urlunsplit
import webbrowser

from utility_runtime import ToolExit, capture, execute, require, words
from utility_options import publish_text


def http_get(arguments):
    for program, prefix in (('curl', ['-A', 'curl', '-s']), ('wget', ['-qO-']),
                            ('http', ['-b', 'GET']), ('fetch', ['-q'])):
        try: require(program)
        except ToolExit: continue
        return execute([program, *prefix, *arguments])
    raise ToolExit(1, 'requires a native curl, wget, HTTPie or fetch executable')


def remote_url(remote):
    remote = remote.strip().removesuffix('.git').rstrip('/')
    match = re.fullmatch(r'[^/@:]+@([^/:]+):(.+)', remote)
    if match: return 'https://' + match[1] + '/' + match[2]
    parsed = urlsplit(remote)
    if parsed.scheme in ('http', 'https', 'ssh', 'git') and parsed.hostname:
        host = '[' + parsed.hostname + ']' if ':' in parsed.hostname else parsed.hostname
        # HTTP(S) remotes name their browser port. SSH/Git ports belong to
        # their transport and must not be reused for the HTTPS destination.
        if parsed.scheme in ('http', 'https') and parsed.port is not None:
            host += ':' + str(parsed.port)
        return urlunsplit(('https', host, parsed.path, '', ''))
    raise ValueError('Git remote has no supported web address')


def browser_url(arguments):
    arguments = list(arguments)
    if arguments and arguments[0] in (':', '-q', '--query', '-s', '--search', '-g', '--google'):
        return 'https://www.google.com/search?' + urlencode({'q': ' '.join(arguments[1:])}) if len(arguments) > 1 else 'https://google.com'
    if arguments:
        value = ' '.join(arguments)
    else:
        value = ''
        try:
            if capture('git', ['rev-parse', '--is-inside-work-tree']).strip() == b'true':
                value = remote_url(capture('git', ['remote', 'get-url', 'origin']).decode('utf-8'))
        except (ToolExit, ValueError):
            pass
        value = value or os.environ.get('WWW') or 'https://google.com'
    if value.lower().startswith('http://'): raise ValueError('www requires HTTPS')
    if '://' not in value: value = 'https://' + value
    parsed = urlsplit(value)
    if parsed.scheme.lower() != 'https' or not parsed.hostname or any(ord(char) < 32 for char in value):
        raise ValueError('expected an HTTPS web address')
    return value


class Cheat:
    def __init__(self):
        self.home = Path(os.environ.get('CHTSH') or Path.home()/'.cht.sh').expanduser().absolute()
        configuration = Path(os.environ.get('CHTSH_CONF') or self.home/'cht.sh.conf')
        self.settings = {key: os.environ[key] for key in ('CHTSH_URL', 'CHTSH_QUERY_OPTIONS', 'CHTSH_CURL_OPTIONS') if key in os.environ}
        if configuration.is_file():
            # Read only literal assignments belonging to this client. Never
            # source the POSIX configuration or evaluate shell substitutions.
            import shlex
            for line in configuration.read_text(encoding='utf-8').splitlines():
                match = re.match(r'^\s*(?:export\s+)?(CHTSH_URL|CHTSH_QUERY_OPTIONS|CHTSH_CURL_OPTIONS)=(.*)$', line)
                if not match or match[1] in self.settings: continue
                value = match[2]
                if '$' in value or '`' in value:
                    raise ValueError('shell expressions in ' + match[1] + ' require an explicit native environment override')
                parsed = shlex.split(value, comments=True)
                if len(parsed) > 1: raise ValueError('expected a literal setting for ' + match[1])
                self.settings[match[1]] = parsed[0] if parsed else ''
        self.url = self.settings.get('CHTSH_URL') or 'https://cht.sh'
        if urlsplit(self.url).scheme not in ('http', 'https') or not urlsplit(self.url).hostname:
            raise ValueError('CHTSH_URL must be an HTTP or HTTPS service URL')
        mode = self.home/'mode'
        self.mode = mode.read_text(encoding='utf-8').strip() if mode.is_file() else 'auto'
        if self.mode != 'lite': self.mode = 'auto'

    def query(self, query):
        extra = self.settings.get('CHTSH_QUERY_OPTIONS', '')
        if extra: query += ('&' if '?' in query else '?') + extra
        local = self.home/'standalone'
        if self.mode == 'auto' and local.is_file():
            location = Path(local.read_text(encoding='utf-8').strip())
            interpreter = location/'ve'/('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
            controller = location/'lib/standalone.py'
            if location.is_absolute() and interpreter.is_file() and controller.is_file():
                return capture(str(interpreter), ['-B', str(controller), query])
        arguments = []
        extra_options = self.settings.get('CHTSH_CURL_OPTIONS', '')
        if extra_options: arguments += words(extra_options)
        if (self.home/'id').is_file(): arguments += ['-b', str(self.home/'id')]
        url = self.url.rstrip('/') + '/' + quote(query.lstrip('/'), safe='/+?:&=,%')
        return capture('curl', [*arguments, '-s', '--', url])

    def set_mode(self, value=None):
        if value is None:
            print('current mode: ' + self.mode)
            return 0
        if value not in ('auto', 'lite'): raise ValueError('mode must be auto or lite')
        identity = publish_text(self.home/'mode', value+'\n', 'cht-mode')
        self.mode = value
        print('Configured mode: ' + value)
        if identity: print('Recovery transaction ' + identity)
        return 0

    def identity(self, value=''):
        path = self.home/'id'
        previous = path.read_text(encoding='utf-8') if path.is_file() else '# Netscape HTTP Cookie File\n'
        lines = previous.splitlines()
        current = next((line.split('\t')[-1] for line in reversed(lines) if len(line.split('\t')) == 7 and line.split('\t')[5] == 'id'), '')
        if not value and current:
            print(current); return
        if value == 'remove':
            updated = [line for line in lines if not (len(line.split('\t')) == 7 and line.split('\t')[5] == 'id')]
            if updated != lines: publish_text(path, '\n'.join(updated)+'\n', 'cht-id-remove')
            print('id removed'); return
        value = secrets.token_urlsafe(18) if value in ('', 'reset') else value
        if len(value) < 16 or not re.fullmatch(r'[A-Za-z0-9_.~+-]+', value):
            raise ValueError('id must contain at least 16 cookie-safe characters')
        lines = [line for line in lines if not (len(line.split('\t')) == 7 and line.split('\t')[5] == 'id')]
        lines.append('.'+urlsplit(self.url).hostname+'\tTRUE\t/\tTRUE\t0\tid\t'+value)
        publish_text(path, '\n'.join(lines)+'\n', 'cht-id')
        print(value)  # This explicit identity command is the reveal boundary.


def prepare_query(section, value):
    value = value.strip()
    if section and not value.startswith('/'):
        return section + '/' + value.replace(' ', '+')
    first, separator, rest = value.lstrip('/').partition(' ')
    return first + ('/' + rest.replace(' ', '+') if separator else '')


SHELL_HELP = ('help  cd LANG  copy/yank/y/c  ccopy/cc/Y/C  id [ID|reset|remove]\n'
              'hush  version  exit/quit  QUERY\n'
              'stealth: native selection-monitor adapter is not implemented.\n'
              'update: use the reviewed Dots checkout update workflow.\n')


def cheat_shell(client, section='', *, read=None):
    read = input if read is None else read
    query = ''; status = 0
    if not (client.home/'.hushlogin').exists(): print('Use help for native cheat-shell commands.')
    while True:
        try: line = read('cht.sh' + ('/'+section if section else '') + '> ').strip()
        except EOFError: return status
        if not line: continue
        command, _, argument = line.partition(' ')
        try:
            if command in ('exit', 'quit'): return status
            if command in ('?', 'h', 'help'): print(SHELL_HELP, end='')
            elif command == 'version': print('cht native adapter; service ' + (urlsplit(client.url).hostname or 'configured'))
            elif command == 'cd': section = '' if argument in ('', '..', '/') else argument.strip('/')
            elif command in ('copy', 'yank', 'c', 'y', 'ccopy', 'cc', 'C', 'Y'):
                if not query: raise ValueError('make a query before copying')
                from clipboard import copy
                option = 'TQ' if command in ('ccopy', 'cc', 'C', 'Y') else 'T'
                response = client.query(query + ('&' if '?' in query else '?') + option)
                copy(response.decode('utf-8')); print('Copied answer to clipboard.')
            elif command == 'hush':
                publish_text(client.home/'.hushlogin', '', 'cht-hush')
                print('Initial help message disabled.')
            elif command == 'id': client.identity(argument)
            elif command == 'stealth': raise ToolExit(3, 'native selection monitoring is not implemented; use an explicit query')
            elif command == 'update': raise ToolExit(3, 'vendored client updates belong to the reviewed Dots checkout update workflow')
            else:
                query = prepare_query(section, line)
                response = client.query(query)
                sys.stdout.buffer.write(response); sys.stdout.buffer.flush()
            status = 0
        except (ValueError, ToolExit) as error:
            print('cht: '+str(error), file=sys.stderr)
            status = error.code if isinstance(error, ToolExit) else 2


def cheat(arguments):
    arguments = list(arguments)
    if not arguments:
        from utility_cli import help_text
        print(help_text('cht'), end=''); return 0
    if arguments[0] == '--read':
        print(sys.stdin.readline().rstrip('\r\n') or 'exit'); return 0
    if arguments[0] == '--standalone-install':
        message = ('The legacy shell/virtualenv installer has no native installer adapter. '
                   'Use reviewed package/environment installation; an existing native standalone checkout is supported by auto mode.')
        if arguments[1:] == ['help']: print(message); return 0
        raise ToolExit(3, message)
    client = Cheat()
    if arguments[0] == '--mode':
        if len(arguments) > 2: raise ValueError('--mode accepts auto or lite')
        return client.set_mode(arguments[1] if len(arguments) == 2 else None)
    if arguments[0] == '--shell':
        section = arguments[1].strip('/') if len(arguments) > 1 else ''
        if len(arguments) > 2:
            output = client.query(prepare_query(section, ' '.join(arguments[2:])))
            sys.stdout.buffer.write(output); sys.stdout.buffer.flush()
        return cheat_shell(client, section)
    # Legacy one-shot options are service query options; text words form the
    # section/query path. Do not execute or interpolate either into shell code.
    query = prepare_query('', ' '.join(value for value in arguments if not value.startswith('-')))
    output = client.query(query)
    sys.stdout.buffer.write(output); sys.stdout.buffer.flush()
    return 0


def main(name, arguments):
    if name == 'httpGet': return http_get(arguments)
    if name == 'www':
        if not webbrowser.open(browser_url(arguments)):
            raise ToolExit(1, 'the native browser could not be opened')
        return 0
    return cheat(arguments)

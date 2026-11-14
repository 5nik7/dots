"""Inert grammar for the existing standalone utility adapters."""
import os
NAMES = ('linked', 'lnkd', 'cpwd', 'pathout', 'dirout', 'isdir', 'isfile',
         'fzcmd', 'fzenv', 'fzfd', 'fzfig', 'fzg', 'fzopt', 'fzpyfig', 'fzrg', 'fzrg3',
         'cht', 'httpGet', 'www')

FZF_OPTIONS = tuple(('color bind style height min-height layout margin padding border border-label border-label-pos '
    'gutter gutter-raw pointer marker scrollbar list-border list-label list-label-pos prompt info info-command '
    'input-border input-label input-label-pos header header-lines header-first header-border header-label '
    'header-label-pos header-lines-border footer footer-border footer-label footer-label-pos preview '
    'preview-border preview-label preview-label-pos preview-window').split())
FZF_COLORS = tuple(('fg list-fg selected-fg preview-fg bg list-bg selected-bg preview-bg input-bg header-bg footer-bg '
    'hl fg+ bg+ gutter hl+ query info border scrollbar separator preview-border preview-scrollbar input-border '
    'header-border footer-border label list-label preview-label input-label header-label footer-label prompt '
    'pointer marker spinner header footer').split())
OPTIONS = {
    'linked': ('--full', '-d', '--dirname', '-b', '--basename', '-p', '--prefix', '-s', '--source',
        '-D', '--source-dirname', '-B', '--source-basename', '-C', '--shared-prefix', '-e', '--link-branch-dir',
        '-E', '--source-branch-dir', '-m', '--shared-basename', '-f', '--format', '-j', '--json', '-A', '--arrays',
        '--array', '-r', '--raw', '--completion', '-h', '--help'),
    'pathout': ('-r', '--raw', '--'), 'dirout': ('-r', '--raw', '-j', '--join', '-c', '--color', '--'),
    'fzfig': ('-p', '--pipe', '--'), 'fzopt': (*FZF_OPTIONS, 'uncolor', 'unbind', 'dump', 'write-rc', 'help'),
    'cht': ('--help', '--read', '--shell', '--mode', '--standalone-install'),
    'www': (':', '-q', '--query', '-s', '--search', '-g', '--google'),
}
USAGE = {
    'linked': 'linked [PATH] [--full|--source|--json|--format FORMAT|--arrays [auto|bash|zsh]] [-r|--raw]',
    'lnkd': 'lnkd', 'cpwd': 'cpwd', 'pathout': 'pathout [-r|--raw] [--] PATH...',
    'dirout': 'dirout [-r|--raw] [-j|--join] [-c|--color] [--] [PATH...]',
    'isdir': 'isdir PATH', 'isfile': 'isfile PATH', 'fzcmd': 'fzcmd', 'fzenv': 'fzenv [QUERY]',
    'fzfd': 'fzfd', 'fzfig': 'fzfig [-p|--pipe "EXECUTABLE ARG..."] [TEXT...]',
    'fzpyfig': 'fzpyfig [TEXT]', 'fzg': 'fzg [QUERY...]', 'fzrg': 'fzrg [QUERY...]', 'fzrg3': 'fzrg3 [QUERY...]',
    'fzopt': 'fzopt KEY VALUE... | color KEY VALUE... | bind KEY ACTION... | uncolor KEY... | unbind KEY... | dump | write-rc',
    'cht': 'cht QUERY... | --shell [LANG] | --read | --mode [auto|lite] | --standalone-install [DIR|help]',
    'httpGet': 'httpGet [NATIVE_CLIENT_OPTIONS...] URL', 'www': 'www [URL | -q|--query|-s|--search|-g|--google QUERY...]',
}


def canonical(name, windows=None):
    windows = os.name == 'nt' if windows is None else windows
    if (name.casefold() if windows else name).endswith('.ps1'): name = name[:-4]
    return next((item for item in NAMES if (item.casefold() == name.casefold() if windows else item == name)), '')


def complete(name, words, *, windows=None):
    """Return legacy three-field records; the last word is the partial token."""
    windows = os.name == 'nt' if windows is None else windows
    name = canonical(name, windows)
    if not name: return []
    current = words[-1] if words else ''
    previous = words[-2] if len(words) > 1 else ''
    before = list(words[:-1]); literal = False; index = 0
    while index < len(before):
        token = before[index]
        if token == '--': literal = True; break
        if name == 'linked' and token in ('-f', '--format', '--completion'): index += 1
        index += 1
    if literal:
        return [('directory' if name == 'isdir' else 'file', '', '')] if name in ('linked', 'isdir', 'isfile', 'pathout', 'dirout') else []
    values = OPTIONS.get(name, ('--help', '-h') if windows else ())
    if windows: values = tuple(dict.fromkeys((*values, '--help', '-h')))
    if not windows:
        if name == 'pathout': values = ('-r',)
        elif name == 'dirout': values = tuple(value for value in values if value != '--')
        elif name == 'fzfig': values = ('-p', '--pipe')
    if name == 'linked' and previous in ('-A', '--arrays', '--array'): values = ('auto', 'bash', 'zsh')
    elif name == 'linked' and previous == '--completion': values = ('bash', 'zsh')
    elif name == 'linked' and previous in ('-f', '--format'): return []
    elif name == 'linked' and current.startswith(('--array=', '--arrays=', '--completion=')):
        prefix = current.partition('=')[0] + '='
        values = tuple(prefix + value for value in (('bash', 'zsh') if prefix == '--completion=' else ('auto', 'bash', 'zsh')))
    elif name == 'cht' and previous == '--mode': values = ('auto', 'lite')
    elif name == 'fzfig' and previous in ('-p', '--pipe'): return []
    elif name == 'fzopt':
        index = 0
        while index < len(before):
            token = before[index]
            remaining = len(before) - index - 1
            if token in ('color', 'bind'):
                if remaining == 0: values = FZF_COLORS if token == 'color' else (); break
                if remaining == 1: return []
                index += 3
            elif token in ('uncolor', 'unbind'):
                index += 1
                while index < len(before) and before[index] not in ('color', 'bind', 'uncolor', 'unbind'): index += 1
                if index == len(before): values = FZF_COLORS if token == 'uncolor' else (); break
            else:
                if remaining == 0: return []
                index += 2
    records = [('candidate', value, '') for value in values if value.startswith(current)]
    if name in ('linked', 'isdir', 'isfile', 'pathout', 'dirout') and not current.startswith('-') and previous not in ('-A', '--arrays', '--array', '--completion'):
        records.append(('directory' if name == 'isdir' else 'file', '', ''))
    return records

"""Private PowerShell argv boundary, data only; no shell quoting or evaluation."""
import base64
import json
import os

FLAG = '--_powershell-argv-v1'

def decode(arguments, *, aliases=True):
    if len(arguments) != 2 or arguments[0] != FLAG or len(arguments[1]) > 131072:
        raise ValueError('Invalid PowerShell argument envelope')
    try:
        data = base64.b64decode(arguments[1], validate=True)
        doc = json.loads(data.decode('utf-8'))
    except (ValueError, UnicodeError) as error:
        raise ValueError('Invalid PowerShell argument envelope') from error
    if (len(data) > 98304 or not isinstance(doc, dict) or doc.get('version') != 1
            or doc.get('host') not in ('nt','posix') or not isinstance(doc.get('argv'),list)
            or any(not isinstance(v,str) or '\x00' in v for v in doc['argv'])):
        raise ValueError('Invalid PowerShell argument envelope')
    if doc['host'] != os.name:
        raise ValueError('PowerShell and Python must use the same native platform; do not mix Windows and WSL tools')
    args = doc['argv'][:]
    # Compatibility aliases are command selectors, never arbitrary operands.
    index = 0
    while aliases and index < len(args):
        word = args[index]
        if word == '--': break
        if word == '--color': index += 2; continue
        if word in ('--json','-v','--verbose','--dry-run','--force','--replace-link') or word.startswith('--color='):
            index += 1; continue
        if word in ('-help','-list','-theme'):
            args[index] = {'-help':'--help','-list':'--list','-theme':'--theme'}[word]
        break
    shell = doc.get('shell')
    if shell is not None and (not isinstance(shell,str) or not os.path.isabs(shell) or any(c in shell for c in '\x00\r\n')):
        raise ValueError('Invalid native PowerShell executable path')
    return args, shell

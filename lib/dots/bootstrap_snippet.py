"""Emit a standalone rc using the same native sources as the installer."""
import base64
from pathlib import Path
import shlex
import sys

ROOT = Path(__file__).resolve().parents[2]
ENTRIES = {'bash': 'rc.sh', 'zsh': 'rc.sh', 'fish': 'config.fish',
           'powershell': 'profile.ps1', 'nu': 'config.nu', 'xonsh': 'rc.xsh'}


def inline(entry, reference, replacement):
    if entry.count(reference) != 1:
        raise ValueError('bootstrap entry no longer has its expected helper reference')
    return entry.replace(reference, replacement)


def nu_literal(value):
    fence = '#'
    while "'" + fence in value:
        fence += '#'
    return 'r' + fence + "'" + value + "'" + fence


def installed_nu_entry(root):
    template = (root / 'lib/dots/shell/bootstrap/entry.nu').read_text(encoding='utf-8')
    # Nu parses source paths before reading the runtime environment. Embed only
    # the installed checkout path; the existence check also works after removal.
    return inline(template, "($nu.home-dir | path join '.local/share/dots/bootstrap/init.nu')",
                  nu_literal(str(root / 'shells/nushell/init.nu')))


def encoded_command(source, arguments):
    script = '& {\n' + source + '\n} ' + arguments
    return base64.b64encode(script.encode('utf-16le')).decode('ascii')


def snippet(shell):
    if shell not in ENTRIES:
        raise ValueError('bootstrap supports bash, zsh, fish, powershell, nu and xonsh')
    sources = ROOT / 'shells/bootstrap'
    helpers = ROOT / 'lib/dots/shell/bootstrap'
    entry_file = helpers/'entry.nu' if shell == 'nu' else sources/ENTRIES[shell]
    entry = entry_file.read_text(encoding='utf-8')
    # Inline the cold path for a manually distributed snippet. Installed
    # copies call the two independent helpers, leaving their rc files small.
    if shell == 'powershell':
        native = (helpers / 'locate.ps1').read_text(encoding='utf-8')
        return inline(entry, "(Join-Path $HOME '.local/share/dots/bootstrap/locate.ps1')", '{\n' + native + '\n}')
    posix = (helpers / 'locate.sh').read_text(encoding='utf-8')
    if shell in ('bash', 'zsh', 'fish'):
        quoted = shlex.quote(posix) if shell != 'fish' else "'" + posix.replace('\\', '\\\\').replace("'", "\\'") + "'"
        return inline(entry, 'sh "$HOME/.local/share/dots/bootstrap/locate.sh"', 'sh -c ' + quoted + ' dots-bootstrap')
    native = (helpers / 'locate.ps1').read_text(encoding='utf-8')
    if shell == 'xonsh':
        # Windows PowerShell's -EncodedCommand uses UTF-16LE.
        encoded = encoded_command(native, '$env:DOTS_RC_MODE -Utf8 -Shell xonsh')
        entry = inline(entry, "'-File', str(data / 'locate.ps1'), mode, '-Utf8', '-Shell', 'xonsh'", "'-EncodedCommand'," + repr(encoded))
        entry = inline(entry, "['sh', str(data / 'locate.sh'),", "['sh','-c'," + repr(posix) + ",'dots-bootstrap',")
        return inline(entry, 'text=True, env=env', 'text=True, env=dict(env, DOTS_RC_MODE=mode)')
    encoded = encoded_command(native, 'interactive -Utf8 -Shell nu')
    entry = inline(entry, "^sh ($nu.home-dir | path join '.local/share/dots/bootstrap/locate.sh')",
                   '^sh -c ' + nu_literal(posix) + ' dots-bootstrap')
    return inline(entry, "-File ($nu.home-dir | path join '.local/share/dots/bootstrap/locate.ps1') interactive -Utf8 -Shell nu",
                  "-EncodedCommand '" + encoded + "'")


if __name__ == '__main__':
    print(snippet(sys.argv[1]), end='')

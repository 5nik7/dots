"""Pure command grammar; no platform probes or package-manager imports."""
import argparse
from . import VERSION
MANAGERS = ('apt', 'pacman', 'paru', 'yay', 'dnf', 'xbps', 'npm', 'uv-tool', 'pip', 'gem')

COMMANDS = {'install': 'Install exact names or open a picker', 'uninstall': 'Remove installed packages',
            'remove': 'Alias for uninstall', 'search': 'Read-only search picker', 'list': 'Print package inventory',
            'info': 'Readable package details', 'upgrade': 'Upgrade packages', 'refresh': 'Refresh repository metadata',
            'managers': 'Detected managers and capabilities', 'doctor': 'Detection and completion diagnostics',
            'completion': 'Generate or install shell completions', 'cache': 'Clear cached catalogs', 'help': 'Show usage'}

DESCRIPTION = '''Fuzzy package management for Termux and Linux.

Commands:
  install [NAME ...]       Install exact names; no names opens picker
  uninstall [NAME ...]     Remove installed packages; no names opens picker
  search [QUERY]           Read-only search picker (Enter shows details)
  list                    Print package inventory
  info NAME ...           Colorized, wrapped package information
  upgrade [NAME ...]       Upgrade using the selected manager
  refresh                 Refresh repository metadata where supported
  managers                Show detected managers and capabilities
  doctor                  Explain environment, dependencies, completions
  completion SHELL [install|update|status|uninstall]
                          Print or manage Bash/Zsh/Fish completion
  cache clear             Clear pkgs inventory caches
  help                    Show this usage

Examples:
  pkgs install --query editor
  pkgs uninstall
  pkgs install --manager npm --global typescript
  pkgs install --manager uv-tool ruff
  pkgs completion ZSH install

Picker: Tab select, Ctrl-X preview, Alt-I installed, Alt-O homepage.
Bare invocation shows help. Completion inserts names and never installs.
'''

def parser():
    p = argparse.ArgumentParser(prog='pkgs', description=DESCRIPTION, add_help=False,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('command', nargs='?', choices=list(COMMANDS))
    p.add_argument('names', nargs='*', metavar='ARG')
    p.add_argument('-h', '-H', '--help', action='help')
    p.add_argument('-V', '--version', action='version', version='pkgs ' + VERSION)
    p.add_argument('--manager', choices=('auto',) + MANAGERS, default=None)
    p.add_argument('--query', default='')
    p.add_argument('--global', dest='global_scope', action='store_true', help='npm global scope')
    p.add_argument('--installed', action='store_true')
    p.add_argument('--json', action='store_true', help='machine-readable reporting output')
    p.add_argument('--color', choices=('auto', 'always', 'never'),
                   help='report color; overrides DOTS_COLOR and configured color')
    p.add_argument('-p', '--preview', help='fzf preview-window layout')
    p.add_argument('--directory', help='completion destination directory (file-only for Bash/Zsh)')
    p.add_argument('--debug', action='store_true', help='phase timing diagnostics on stderr')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('-y', '--yes', action='store_true')
    return p

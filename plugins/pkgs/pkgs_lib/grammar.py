"""Pure command grammar; no platform probes or package-manager imports."""
import argparse
import sys
from . import VERSION
MANAGERS = ('apt', 'pacman', 'paru', 'yay', 'dnf', 'xbps', 'npm', 'uv-tool', 'pip', 'gem', 'go')

COMMANDS = {'install': 'Install exact names or open a picker', 'uninstall': 'Remove installed packages',
            'remove': 'Alias for uninstall', 'search': 'Read-only search picker', 'list': 'Print package inventory',
            'info': 'Readable package details', 'upgrade': 'Upgrade user-wide packages or a selected manager', 'refresh': 'Refresh repository metadata',
            'managers': 'Detected managers and capabilities', 'doctor': 'Detection and completion diagnostics',
            'completion': 'Generate or install shell completions', 'cache': 'Clear cached catalogs',
            'format': 'Format package-manager output from stdin', 'export': 'Export editable installed-package JSON',
            'manifest': 'Validate and inspect a package manifest', 'restore': 'Restore packages from a manifest', 'help': 'Show usage'}

DESCRIPTION = '''Fuzzy package management for Termux and Linux.

Commands:
  install [NAME ...]       Install exact names; no names opens picker
  uninstall [NAME ...]     Remove installed packages; no names opens picker
  search [QUERY]           Read-only search picker (Enter shows details)
  list                    Print package inventory
  info NAME ...           Colorized, wrapped package information
  upgrade [NAME ...]       Unattended user-wide upgrades; --manager selects one
  format                  Format stdin; use pipefail for producer failures
  export                  Export installed roots as editable JSON
  manifest FILE           Validate and inspect a package manifest
  restore FILE            Preview and restore a package manifest
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

class Parser(argparse.ArgumentParser):
    def print_help(self, file=None):
        # Keep metadata generation pure; presentation is loaded only for help.
        from .reports import help_report
        if not help_report(self, self.help_argv, file): super().print_help(file)


def parser(argv=None):
    p = Parser(prog='pkgs', description=DESCRIPTION, add_help=False,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.help_argv = sys.argv[1:] if argv is None else argv
    p.add_argument('command', nargs='?', choices=list(COMMANDS))
    p.add_argument('names', nargs='*', metavar='ARG')
    p.add_argument('-h', '-H', '--help', action='help', help='show this help and exit')
    p.add_argument('-V', '--version', action='version', version='pkgs ' + VERSION)
    p.add_argument('--manager', choices=('auto',) + MANAGERS, default=None, help='select a package manager (default: auto)')
    p.add_argument('--query', default='', help='initial picker search text')
    p.add_argument('--global', dest='global_scope', action='store_true', help='npm global scope')
    p.add_argument('--installed', action='store_true', help='show installed packages only')
    p.add_argument('--json', action='store_true', help='machine-readable reporting output')
    p.add_argument('--color', choices=('auto', 'always', 'never'),
                   help='auto, always or never; overrides DOTS_COLOR and configured color')
    p.add_argument('-p', '--preview', help='fzf preview-window layout')
    p.add_argument('--directory', help='completion destination directory (file-only for Bash/Zsh)')
    p.add_argument('--debug', action='store_true', help='phase timing diagnostics on stderr')
    p.add_argument('--dry-run', action='store_true', help='preview changes without running transactions')
    p.add_argument('--raw', action='store_true', help='forward manager streams unchanged')
    p.add_argument('--ignore-skip', action='store_true', help='explicitly override direct-target skip rules')
    p.add_argument('--output', metavar='FILE', help='export destination; stdout by default')
    p.add_argument('--update', action='store_true', help='merge export into a manifest; defaults to the current profile')
    p.add_argument('--include-dependencies', action='store_true', help='export full installed inventory')
    p.add_argument('--pin-versions', action='store_true', help='export exact installed version pins')
    p.add_argument('-y', '--yes', action='store_true', help='approve install, removal, restore or file replacement')
    return p

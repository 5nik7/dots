"""Lightweight shared CLI grammar and presentation; no application discovery."""
import argparse
import importlib.util
from pathlib import Path

class Failure(Exception):
    def __init__(self, message, code=1):
        super().__init__(message)
        self.code = code

_UI = None
def presentation():
    global _UI
    if _UI is None:
        spec = importlib.util.spec_from_file_location('blastoff_presentation', Path(__file__).with_name('welcome.py'))
        _UI = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_UI)
    return _UI

def picker_options(parser):
    styles = parser.add_mutually_exclusive_group()
    styles.add_argument('--fancy', nargs='?', const='unicode', choices=['unicode','ascii'],
                        help='Blastoff styling (default: Unicode, automatic ASCII fallback)')
    styles.add_argument('--fzf', action='store_true', help='basic fzf with compatible user settings; requires fzf')

def parser(version, color="auto", json_output=False):
    VERSION = version
    class Parser(argparse.ArgumentParser):
        def format_help(self):
            return presentation().format_help(self, VERSION, color, json_output)
        def error(self, message):
            raise Failure(message, 2)
    p = Parser(prog='blastoff', description='Starship themes and stored modules. Themes: ~/.config/blastoff/themes; active config: $STARSHIP_CONFIG or ~/.config/starship.toml.', epilog='Aliases: -l/--list = list; -t/--theme NAME = theme apply NAME; bare -t/--theme = current. Use a subcommand with --help for details.', allow_abbrev=False)
    p.add_argument('--version', action='version', version='blastoff ' + VERSION)
    p.add_argument('-v', '--verbose', action='store_true', help='diagnostics on stderr; JSON records with --json')
    p.add_argument('--dry-run', action='store_true', help='report intended actions without writes, prompts, pickers or editors')
    p.add_argument('--json', action='store_true', help='machine-readable output (no decoration)')
    p.add_argument('--color', choices=['auto','always','never'], default='auto', help='report color policy; overrides DOTS_COLOR; always forces report color')
    p.add_argument('--force', action='store_true', help='back up and replace an existing stored file; required for theme/module deletion')
    p.add_argument('--replace-link', action='store_true', help='back up and replace an active symlink; leave its target unchanged')
    subs = p.add_subparsers(dest='command')
    list_description = 'List local themes and presets with current/modified origin markers. Dim source prefixes keep names prominent. Unknown origins require explicit blastoff current matching; --json retains the name-list schema.'
    for cmd, desc in [('list','list local themes and Starship presets with current/modified origin markers'),('current','show active config, origin and exact matches'),('doctor','read-only paths and dependency diagnostics')]:
        subs.add_parser(cmd, help=desc, description=list_description if cmd == 'list' else None)
    pick = subs.add_parser('pick', help='choose and apply a theme', description='Fancy Unicode fzf by default, then gum/numbered fallback. --fzf uses compatible user styling and requires fzf. Compatible FZF_DEFAULT_OPTS_FILE and FZF_DEFAULT_OPTS apply. Enter applies; Escape/Ctrl-C cancels (130). Ctrl-X toggles the visible, responsive source preview. No theme commands run. Requires human terminal input/output. Dry-run does not open a picker.')
    picker_options(pick)
    pick.add_argument('style', nargs='?', choices=['fancy','fzf'], help='presentation alias')
    t = subs.add_parser('theme', help='manage full themes').add_subparsers(dest='action', required=True)
    t.add_parser('list', description=list_description)
    t.add_parser('apply', description='Apply NAME (local first), local:NAME or preset:NAME to the active config. Changed content is backed up; identical content is unchanged. Active symlinks are preserved while their guarded targets are updated. Use --replace-link only to convert a link to a regular file, leaving its target untouched.').add_argument('name')
    t.add_parser('save', description='Save active edits. NAME creates a local theme; --force backs up and replaces a collision. Without NAME, a terminal asks Save edits to known theme? [y/as/N]; y authorizes replacement, as asks a name, Enter cancels. Changed/missing origins require save-as. Noninteractive use requires NAME. Dry-run reports unresolved choices.').add_argument('name', nargs='?')
    t.add_parser('edit', description='Edit a private working copy of the active config, then validate and atomically publish. Editor: nonempty EDITOR, nvim, vim, vi, code, nano. Quote paths with spaces; arguments are supported without eval. Known GUI editors wait. Back up before editing; --replace-link preserves the old link target. Failed/invalid edits remain at a reported recovery path. Requires a human terminal except --dry-run.')
    cp = t.add_parser('copy', description='Copy NAME, local:NAME or preset:NAME to a local theme without applying it. Use --force for a backed-up replacement.'); cp.add_argument('source'); cp.add_argument('name')
    im = t.add_parser('import', description='Import valid UTF-8 TOML from an absolute file path without applying it. Quote paths containing spaces. Use --force for a backed-up replacement.'); im.add_argument('path'); im.add_argument('name')
    t.add_parser('delete', description='Delete a stored theme with --force after backing it up. Refuse the active config or its symlink target. Recover stored-theme backups with theme import.').add_argument('name')
    pr = subs.add_parser('preset', help='Starship built-in presets').add_subparsers(dest='action', required=True)
    pr.add_parser('list')
    pr.add_parser('apply', description='Generate a Starship preset and apply it, backing up changed active content. Requires Starship; --replace-link permits active symlink replacement.').add_argument('name')
    ps = pr.add_parser('save', description='Generate a Starship preset into a local theme without applying it. Requires Starship; --force backs up and replaces an existing destination.'); ps.add_argument('source'); ps.add_argument('name')
    mo = subs.add_parser('module', help='save, load or show TOML module tables').add_subparsers(dest='action', required=True)
    mo.add_parser('list')
    show = mo.add_parser('show', description='Show a saved module without loading it. NAME prints TOML (raw bytes when redirected); --json returns name/path/toml. Without NAME, browse with fzf and Ctrl-X previews; Enter shows, Escape/Ctrl-C cancels. Requires a terminal and fzf for browsing; fancy by default, --fzf uses user styling.'); show.add_argument('name', nargs='?'); picker_options(show)
    ms = mo.add_parser('save', description='Store an explicit TOML table and descendants, e.g. directory or custom.clock. NAME defaults to the module route with dots replaced by hyphens. Unsupported inline/dotted layouts are refused. --force backs up an existing destination.'); ms.add_argument('module'); ms.add_argument('name', nargs='?')
    mo.add_parser('load', description='Replace the saved module table and descendants in the active config, preserving unrelated settings. Back up changed active content. --replace-link permits active symlink replacement. Referenced palettes/formats must already exist.').add_argument('name')
    mo.add_parser('delete', description='Delete a stored snippet with --force after backing it up. Refuse the active config or its symlink target. Recover by inspecting/validating backup bytes and copying to a new module file.').add_argument('name')
    b = subs.add_parser('backup', help='create, list, restore or delete backups').add_subparsers(dest='action', required=True)
    b.add_parser('create', description='Snapshot active config bytes, including invalid TOML for recovery.'); b.add_parser('list', description='Readable backup ID/time/kind/source/size by default. --json explicitly requests the stable structured result.'); b.add_parser('restore', description='Restore a config backup ID after checksum and TOML validation; back up current content first. Stored-theme/module backups cannot be restored here. --replace-link permits active symlink replacement.').add_argument('id')
    bd = b.add_parser('delete', description='Permanently delete config/stored backups. IDs, --pick and --all are exclusive. Show selection/count, then Delete N selected backups permanently? [y/N]. --yes bypasses confirmation; noninteractive use requires explicit targets and --yes. Bare all selects all; trailing y/yes authorize. After -- all words are literal IDs. Snapshot all before confirmation; new backups are excluded. Dry-run never prompts or opens fzf.')
    picker_options(bd)
    bd.add_argument('ids', nargs='*', metavar='ID')
    selection = bd.add_mutually_exclusive_group()
    selection.add_argument('--pick', action='store_true', help='fzf multi-selection with Tab/Shift-Tab')
    selection.add_argument('--all', action='store_true', help='freeze all eligible backups before confirmation')
    bd.add_argument('-y', '--yes', action='store_true', help='affirm deletion of the explicit selection')
    mi = subs.add_parser('migrate', help='copy themes from an explicit legacy directory'); mi.add_argument('path')
    co = subs.add_parser('completion', help='print a static shell completion script', description='Print offline positional shell completion. Completes commands, options, local source names/prefixes, stored modules, paired backup filenames and import/migration paths. Never starts Blastoff or Starship. Preset names, destination names and module-save routes remain free text; backup candidates are unverified.'); co.add_argument('shell', choices=['bash','zsh','fish'])
    # Shared options are normalized at every command position, not redeclared.
    def help_options(parent):
        for action in parent._actions:
            if isinstance(action, argparse._SubParsersAction):
                for child in action.choices.values():
                    child.epilog = 'Global options before or after commands: -v/--verbose, --dry-run, --json, --color auto|always|never, --force, --replace-link. Mutating flags apply only where described. See blastoff --help.'
                    help_options(child)
    help_options(p)
    return p

def normalize(argv):
    # Global options can appear before or after subcommands. Normalize only known
    # flags; values after -- remain untouched. Legacy -t/-l use this same parser.
    opts, words = [], []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == '--':
            words.extend(argv[i:]); break
        if a in ('--json','--force','--replace-link','-v','--verbose','--dry-run'):
            opts.append(a)
        elif a == '--color':
            if i+1 >= len(argv):
                raise Failure('--color requires a value', 2)
            opts.extend(argv[i:i+2]); i += 1
        elif a.startswith('--color='):
            opts.append(a)
        else:
            words.append(a)
        i += 1
    if words and words[0] in ('-l','--list'):
        words[0] = 'list'
    elif words and words[0] in ('-t','--theme'):
        words = ['theme','apply', *words[1:]] if len(words)>1 else ['current']
    if words[:2] == ['backup', 'delete']:
        tail = words[2:]
        cut = tail.index('--') if '--' in tail else len(tail)
        front, literal = tail[:cut], tail[cut:]
        flags, operands = [], []
        index = 0
        while index < len(front):
            word = front[index]; index += 1
            if word in ('--yes','-y','--all','--pick','--fzf') or word.startswith('--fancy='):
                flags.append(word)
            elif word == '--fancy':
                flags.append(word)
                if index < len(front) and front[index] in ('unicode','ascii'):
                    flags.append(front[index]); index += 1
            else:
                operands.append(word)
        if operands and operands[-1].lower() in ('y','yes'):
            if len(operands) == 1 and not any(x in flags for x in ('--all','--pick')):
                raise Failure('Affirmative alias requires targets; use -- for a literal ID', 2)
            flags.append('--yes'); operands.pop()
        if any(x.lower() in ('y','yes') for x in operands):
            raise Failure('y/yes aliases must trail targets; use -- for literal IDs', 2)
        if any(x.lower() == 'all' for x in operands):
            if len(operands) != 1 or literal:
                raise Failure('all cannot be combined with IDs; use -- for a literal ID', 2)
            flags.append('--all'); operands = []
        words = ['backup','delete', *flags, *operands, *literal]
    return opts + words

def parse(argv, version):
    words = normalize(argv)
    color, json_output, report_color = 'auto', False, None
    i = 0
    while i < len(words) and words[i] != '--':
        word = words[i]
        if word == '--color' and i+1 < len(words):
            i += 1
            color = words[i]
            report_color = color
        elif word.startswith('--color='):
            color = word.split('=', 1)[1]
            report_color = color
        elif word == '--json':
            json_output = True
        i += 1
    root = parser(version, color, json_output)
    args = root.parse_args(words)
    args.report_color = report_color
    if args.command is None and not args.json:
        root.print_help()
        root.exit()
    if hasattr(args, 'fancy'):
        alias = getattr(args, 'style', None)
        if (alias == 'fancy' and args.fzf) or (alias == 'fzf' and args.fancy):
            raise Failure('Fancy and fzf presentations are mutually exclusive', 2)
        explicit = args.fancy is not None or args.fzf
        if explicit and args.command == 'module' and args.name is not None:
            raise Failure('Presentation options require module show without NAME', 2)
        if explicit and args.command == 'backup' and not args.pick:
            raise Failure('Presentation options require backup delete --pick', 2)
        args.fzf = args.fzf or alias == 'fzf'
        args.fancy = None if args.fzf else args.fancy or 'unicode'
    return args

"""Single static font CLI definition for parsing, help, adapters and completion."""
import argparse

OPTIONS = {
    'json': ('flag', 'Print schema-1 JSON without interaction'),
    'print': ('flag', 'Print without opening a browser'),
    'color': ('choice:auto,always,never,none', 'Human output color'),
    'icons': ('choice:auto,always,never', 'Human output icons'),
    'verbose': ('flag', 'Show transaction operation details'),
    'source': ('choice:all,nerd,google,local', 'Font provider'),
    'directory': ('string', 'Backend *FONTS name or path; store versions without activating them'),
    'from': ('string', 'Source store: personal or a backend *FONTS name/path'),
    'query': ('string', 'Initial search text'),
    'version': ('string', 'Exact release tag or saved revision'),
    'variant': ('choice:nerd,mono,propo,original', 'Install all styles of this variant'),
    'face': ('string', 'Exact font filename or full face name'),
    'target': ('choice:termux,kitty,wezterm,windows-terminal,vscode-editor,vscode-terminal', 'Application target; repeat to select several'),
    'config': ('file', 'Explicit unmanaged app configuration'),
    'app-profile': ('string', 'Exact Windows Terminal profile GUID'),
    'output': ('directory', 'Export destination directory'),
    'file': ('file', 'Import this local font file before setting it'),
    'installed': ('flag', 'Show installed families'),
    'downloaded': ('flag', 'Show downloaded families'),
    'system': ('flag', 'Inspect external system font inventory'),
    'monospace': ('flag', 'Filter known monospaced fonts'),
    'keep-archive': ('flag', 'Keep a newly downloaded Nerd Fonts archive'),
    'no-reload': ('flag', 'Do not reload Termux after committing'),
    'dry-run': ('flag', 'Preview without persistent writes or network requests'),
    'yes': ('flag', 'Approve the reviewed mutation without prompting'),
    'client': ('string', 'Exact originating tmux client'),
    'format': ('choice:glyph,name,codepoint', 'Exact single-icon output representation'),
    'copy': ('flag', 'Copy one exact icon result to the native clipboard'),
    'insert': ('flag', 'Insert one icon literally into the originating tmux pane'),
}
COMMON = ('json', 'color', 'icons', 'verbose', 'directory')
MUTATE = ('dry-run', 'yes')
# Summary, positional mode (none/query/font/path/transaction), option names.
COMMANDS = {
    '': ('Browse and manage personal fonts', None, ('query','print','client')),
    'browse': ('Browse fonts and reviewed actions', None, ('query','source','downloaded','client','print')),
    'installed': ('Browse installed fonts and copy, migrate or set them', None, ('query','client','print')),
    'defaults': ('Show saved application font defaults', None, ()),
    'restore': ('Restore exact saved application font defaults', 'targets', ('no-reload',*MUTATE)),
    'copy': ('Copy installed fonts into a Dots font directory', 'fonts', MUTATE),
    'migrate': ('Adopt user-owned fonts into Dots with backups', 'fonts', ('no-reload',*MUTATE)),
    'search': ('Search the saved upstream catalogs', 'query', ('source','monospace')),
    'list': ('List downloaded or installed fonts', None, ('source','installed','downloaded','system','query','monospace')),
    'show': ('Show font versions, faces and provenance', 'font', ('version',)),
    'versions': ('List saved and cataloged versions', 'font', ()),
    'current': ('Show tracked application font selections', None, ()),
    'targets': ('Inspect application font destinations', None, ()),
    'directories': ('List backend font storage directories', None, ()),
    'path': ('Print an exact downloaded font path', 'font', ('version','face','variant')),
    'update': ('Refresh catalogs, or store a newer FONT with --directory', 'optional-font', ('source','version',*MUTATE)),
    'download': ('Save an upstream family and its license', 'font', ('version','keep-archive',*MUTATE)),
    'import': ('Copy selected existing fonts into the library', 'path', MUTATE),
    'export': ('Export a saved family and its licenses', 'font', ('version','output',*MUTATE)),
    'install': ('Install for this user, or store versions with --directory', 'fonts', ('from','version','variant','no-reload',*MUTATE)),
    'uninstall': ('Unregister a family, or remove one directory version', 'font', ('version','no-reload',*MUTATE)),
    'upgrade': ('Upgrade active fonts, or store newer directory versions', 'optional-font', ('no-reload',*MUTATE)),
    'rollback': ('Switch to an exact retained version', 'font', ('version','no-reload',*MUTATE)),
    'pin': ('Pin an exact downloaded version', 'font', ('version',*MUTATE)),
    'unpin': ('Allow a family to be upgraded', 'font', MUTATE),
    'set': ('Set and retain fonts for selected applications', 'optional-font', ('file','version','variant','face','target','config','app-profile','no-reload','client',*MUTATE)),
    'use': ('Activate a stored --directory version for this user', 'font', ('version','variant','face','target','config','app-profile','no-reload',*MUTATE)),
    'remove': ('Remove an unused retained version', 'font', ('version',*MUTATE)),
    'undo': ('Undo a fonts transaction with drift checks', 'transaction', ('no-reload',*MUTATE)),
    'icons': ('Search, copy or insert Nerd Fonts glyphs', 'query', ('query','version','client','print','format','copy','insert')),
}


class HelpParser(argparse.ArgumentParser):
    def print_help(self, file=None):
        from files.catalog import Presentation
        ui=Presentation(file)
        ui.heading(self.prog)
        ui.emit('  '+self.description)
        ui.detail('Usage',self.format_usage().removeprefix('usage: ').strip())
        for action in self._actions:
            if isinstance(action,argparse._SubParsersAction):
                for name,command in action.choices.items():ui.detail(name,command.description)
            elif action.option_strings:
                ui.detail(', '.join(action.option_strings)+(' VALUE' if action.nargs!=0 else ''),action.help or '')


def parser():
    root = HelpParser(prog='fonts', description='Personal font management through Dots')
    def populate(parser, action):
        summary, positional, names = COMMANDS[action]
        parser.description = summary
        for name in (*COMMON, *names):
            kind, help_ = OPTIONS[name]
            args = dict(help=help_, default=argparse.SUPPRESS)
            if name=='from':args['dest']='from_'
            if kind == 'flag': args['action'] = 'store_true'
            elif name == 'target': args['action'] = 'append'
            if kind.startswith('choice:'): args['choices'] = kind[7:].split(',')
            parser.add_argument('--' + name, **args)
        if positional: parser.add_argument('operand', nargs='+' if positional=='fonts' else '*' if positional=='targets' else '?' if positional in ('query','optional-font') else None)
    populate(root, '')
    subs = root.add_subparsers(dest='action')
    for action in COMMANDS:
        if action: populate(subs.add_parser(action, help=COMMANDS[action][0]), action)
    root.set_defaults(**{name.replace('-', '_'): False if kind == 'flag' else None for name,(kind,_) in OPTIONS.items()}, operand=None)
    root.set_defaults(from_=None)
    return root


def header(action):
    summary, positional, names = COMMANDS[action]
    usage = ('[COMMAND] ' if not action else ('[QUERY] ' if positional == 'query' else '[FONT] ' if positional == 'optional-font' else positional.upper()+' ' if positional else '')) + '[OPTIONS]'
    lines = ['#!/usr/bin/env bash', '# Generated by tools/generate_fonts_commands.py.', '# dots:summary='+summary, '# dots:usage='+usage]
    if positional: lines.append('# dots:argument=1|' + ('file' if positional=='path' else 'string') + '|'+positional)
    for name in (*COMMON,*names):
        kind, description = OPTIONS[name]
        lines.append('# dots:option=--'+name+'||'+kind+'|'+description)
    lines += ['DOTS=${DOTS:-$(cd -- "${BASH_SOURCE[0]%/*}/.." && pwd -P)}',
              'exec python3 -B "$DOTS/lib/dots/fonts_cli.py" '+('"'+action+'" ' if action else '')+'"$@"']
    return '\n'.join(lines)+'\n'

"""Compatibility selectors; mutations always return through the fonts CLI."""
import os
from pathlib import Path

from fonts.model import Library
from fonts.commands import HelpParser
from interaction import terminal


def chnf(argv):
    parser=HelpParser(prog='chnf',description='Compatibility wrapper for fonts set --target termux')
    parser.add_argument('query',nargs='?')
    parser.add_argument('-i','--font','--apply',dest='font',help='Select a legacy/library font query')
    parser.add_argument('-l','--list',action='store_true',help='List available TTF faces')
    parser.add_argument('-r','--reload',action='store_true',help='Reload after applying (the default)')
    parser.add_argument('--no-reload',action='store_true',help='Skip the Termux reload')
    parser.add_argument('--yes',action='store_true',help='Approve without prompting')
    parser.add_argument('--dry-run',action='store_true',help='Preview without persistent writes')
    args=parser.parse_args(argv)
    if args.font and args.query:parser.error('only one font query is allowed')
    library=Library()
    if library.platform!='termux':raise ValueError('chnf is available only on Termux')
    root=Path(os.environ.get('TERMUX_NF_FONT_DIR') or Path(os.environ.get('PREFIX',''))/'share/termux-nf/fonts')
    entries=[]
    if root.is_dir():
        for path in sorted(root.rglob('*.ttf')):
            if path.is_file() and not path.is_symlink():entries.append((str(path.relative_to(root)),['set','--file',str(path)]))
    for identity,row in library.families.items():
        version=row.get('preferred')
        if not version:continue
        for font in row['versions'][version]['fonts']:
            if font['file'].lower().endswith('.ttf'):
                entries.append((identity+'/'+font['file'],['set',identity,'--version',version,'--face',font['file']]))
    if args.list:
        from fonts.presentation import FontPresentation
        if FontPresentation().human:
            from fonts_cli import render
            render(dict(items=[dict(face=label) for label,_ in entries]),action='list')
        else:
            for label,_ in entries:print(label)
        return 0
    query=args.font or args.query
    if query:
        exact=[entry for entry in entries if query in (entry[0],Path(entry[0]).name)]
        entries=exact or [entry for entry in entries if query.casefold() in entry[0].casefold()]
    if not entries:raise ValueError('no matching fonts; download or import a font first')
    if len(entries)==1:chosen=entries[0][1]
    else:
        if not terminal():raise ValueError('ambiguous font query; select an exact face')
        from fonts.browser import select,context_for
        from fonts.commands import parser as fonts_parser
        context=context_for(fonts_parser().parse_args([]))
        key=select('Termux font',[(str(i),label) for i,(label,_) in enumerate(entries)],context)
        if key is None:return 130
        chosen=entries[int(key)][1]
    from fonts_cli import main
    return main([*chosen,'--target','termux',*(['--no-reload'] if args.no_reload else []),
                 *(['--yes'] if args.yes else []),*(['--dry-run'] if args.dry_run else [])])


def getnf(argv):
    parser=HelpParser(prog='getnf',description='Compatibility wrapper for Nerd Fonts download/install')
    parser.add_argument('-i',dest='families',help='Comma-separated Nerd Fonts family names')
    parser.add_argument('-f',action='store_true',help='Refresh the catalog and include already installed families')
    parser.add_argument('-k',action='store_true',help='Keep newly downloaded archives')
    parser.add_argument('--yes',action='store_true',help='Approve without prompting')
    parser.add_argument('--dry-run',action='store_true',help='Preview without persistent writes or network')
    args=parser.parse_args(argv)
    from fonts_cli import main
    if not args.families:return main(['browse','--source','nerd'])
    library=Library()
    if args.f or not any(k.startswith('nerd:') for k in library.catalog['families']):
        code=main(['update','--source','nerd',*(['--dry-run'] if args.dry_run else [])])
        if code:return code
        if args.dry_run:return 0
    flags=[*(['--yes'] if args.yes else []),*(['--dry-run'] if args.dry_run else [])]
    for name in args.families.split(','):
        identity='nerd:'+name.strip()
        code=main(['download',identity,*(['--keep-archive'] if args.k else []),*flags])
        if code:return code
        if args.dry_run:continue
        code=main(['install',identity,*flags])
        if code:return code
    if not args.dry_run and terminal() and Library().platform=='termux':
        from fonts.browser import select
        if select('Termux',[('cancel','Keep current font'),('set','Choose a Termux font')])=='set':return chnf([])
    return 0


def run(argv):
    if not argv or argv[0] not in ('getnf','chnf'):raise ValueError('unknown font compatibility wrapper')
    return (getnf if argv[0]=='getnf' else chnf)(argv[1:])

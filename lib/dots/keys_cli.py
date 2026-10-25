#!/usr/bin/env python3
"""Browse binding metadata without running binding actions or app startup."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from keys.model import APPS
from keys.providers import collect, snapshot, read_file
from keys.presentation import binding_label, menu_rows, menu_dimensions, styles, picker_colors, MENU_HEADER


def details(ui,row):
    ui.heading(row['app']+' keybinding')
    ui.detail('Keys',row['display'])
    for label,key in (('Mode','mode'),('Action','description'),('Identifier','action'),('Evidence','evidence'),('Status','status'),('Scope','scope')):
        if row.get(key):ui.detail(label,str(row[key]))
    ui.detail('Notation',json.dumps(row['key'],ensure_ascii=False))
    if row.get('source'):
        display=ui.path(row['source'])+(':'+str(row['line']) if row.get('line') else '')
        if os.path.isabs(row['source']):ui.resource_detail('Source',row['source'],display)
        else:ui.detail('Source',display)
    ui.detail('Description',row['description_source'])


def listing(ui,data,apps=False):
    ui.heading('Dots keybindings')
    if apps:
        for item in data['coverage']:
            ui.detail(item['app'],str(item['count'])+' bindings · '+('live' if item['live'] else 'configured / unavailable'))
            for note in item['notes']:ui.detail('Coverage',note)
        return
    previous=None
    for row in data['rows']:
        group=(row['app'],row['mode'])
        if group!=previous:
            ui.emit();ui.heading(' · '.join(group));previous=group
        label=row['display'];value=row['description']+' ['+row['evidence']+(' · shadowed' if row['status']=='shadowed' else '')+']'
        if len(label)>min(16,ui.width//3):
            ui.detail('Keys',label);ui.detail('Action',value)
        else:ui.detail(label,value)
    if not data['rows']:ui.emit('  No matching keybindings.')
    ui.emit();ui.detail('Result',str(len(data['rows']))+' bindings')
    for item in data['coverage']:
        for note in item['notes']:ui.detail(item['app'],note)


def picker_ui(ui):
    from interaction import rich_fzf_available
    if os.name=='nt' and not rich_fzf_available():raise ValueError('FZF needs native PowerShell preview support; use --print')
    if os.environ.get('TMUX'):
        from files.catalog import Presentation
        ui=Presentation(terminal=True)
        result=subprocess.run(['fzf','--help'],capture_output=True,timeout=5)
        if result.returncode or b'--popup' not in result.stdout:raise ValueError('installed FZF does not support --popup; use --print or update FZF')
    elif not sys.stdout.isatty():raise ValueError('--browse requires a terminal outside tmux')
    return ui


def choose_category(ui,coverage=None):
    from interaction import RichSelector
    from files.picker import fzf_colors
    rows=menu_rows(ui,coverage)
    labels=[label for _,label in rows]
    width,height=menu_dimensions(labels)
    popup=f'center,{width},{height}' if os.environ.get('TMUX') else False
    selected=RichSelector().fzf('Keybinding apps' if coverage is not None else 'Keybinding categories',
        labels,False,None,ui.color,ui.icons,fzf_colors(ui),popup=popup,height=height,header=MENU_HEADER)
    return rows[selected[0]][0]


def browse(ui,data,query):
    from interaction import RichSelector
    from files.picker import fzf_colors
    codes=styles(ui)
    labels=[binding_label(ui,r,codes) for r in data['rows']]
    if not labels:listing(ui,data);return
    with tempfile.TemporaryDirectory(prefix='dots-keys-') as directory:
        path=Path(directory)/'bindings.json';path.write_text(json.dumps(data['rows']));path.chmod(0o600)
        command='"$DOTS_KEYS_PYTHON" -B "$DOTS_KEYS_HELPER" --preview "$DOTS_KEYS_DATA" {1}'
        if os.name=='nt':command='& $env:DOTS_KEYS_PYTHON -B $env:DOTS_KEYS_HELPER --preview $env:DOTS_KEYS_DATA {1}'
        preview=(command,None,dict(DOTS_KEYS_PYTHON=sys.executable,DOTS_KEYS_HELPER=str(Path(__file__).resolve()),DOTS_KEYS_DATA=str(path),DOTS_PROGRESS='never',DOTS_KEYS_CAPTURE='',DOTS_COLOR='always' if ui.color else 'never',DOTS_ICONS='always' if ui.icons else 'never'))
        selected=RichSelector().fzf('Keybindings',labels,False,preview,ui.color,ui.icons,
            picker_colors(fzf_colors(ui)),popup='center,99%' if os.environ.get('TMUX') else False,
            query=query,preview_size=45)
        details(ui,data['rows'][selected[0]])


def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv)
    from files.catalog import Presentation
    ui=Presentation()
    if argv[:1]==['--preview']:
        if len(argv)!=3 or not argv[2].isdigit():raise ValueError('invalid preview request')
        rows=json.loads(read_file(Path(argv[1])));index=int(argv[2])
        if not isinstance(rows,list) or index>=len(rows):raise ValueError('unknown preview binding')
        details(ui,rows[index]);return 0
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('app',nargs='?',choices=(*APPS,'all','apps'))
    p.add_argument('--query',default='');p.add_argument('--mode')
    p.add_argument('--source',choices=('live','configured','all'),default='all')
    p.add_argument('--no-defaults',action='store_true')
    output=p.add_mutually_exclusive_group();output.add_argument('--print',action='store_true',dest='print_only');output.add_argument('--json',action='store_true');output.add_argument('--browse',action='store_true')
    # Private bridge transport is a file of inert JSON, never executable code.
    p.add_argument('--snapshot',help=argparse.SUPPRESS)
    args=p.parse_args(argv);root=Path(os.environ.get('DOTS') or Path(__file__).resolve().parents[2])
    live=[];apps=set()
    if args.snapshot:live,apps=snapshot(read_file(Path(args.snapshot)).encode(),'json')
    elif os.environ.get('DOTS_KEYS_CAPTURE') in ('shell','json'):
        live,apps=snapshot(sys.stdin.buffer.read(16*1024*1024+1),os.environ['DOTS_KEYS_CAPTURE'])
    interactive=args.browse or (not args.json and not args.print_only and sys.stdout.isatty() and os.environ.get('TERM')!='dumb')
    if interactive and not shutil.which('fzf'):
        ui.detail('Picker','FZF unavailable; printing bindings.')
        interactive=False
    if interactive:
        ui=picker_ui(ui)
        if args.app is None:args.app=choose_category(ui)
    data=collect(root,None if args.app in ('all','apps') else args.app,live,apps,not args.no_defaults)
    data['rows']=[r for r in data['rows'] if (args.source=='all' or r['evidence']==args.source)
                  and (not args.mode or r['mode']==args.mode) and (not args.no_defaults or not r['default'])]
    if interactive and args.app=='apps':
        coverage=[dict(item,count=sum(r['app']==item['app'] for r in data['rows']),
                       live=any(r['app']==item['app'] and r['evidence']=='live' for r in data['rows']))
                  for item in data['coverage']]
        args.app=choose_category(ui,coverage)
        data['rows']=[r for r in data['rows'] if r['app']==args.app]
        data['coverage']=[item for item in data['coverage'] if item['app']==args.app]
    if args.query and not interactive:
        terms=args.query.casefold().split()
        data['rows']=[r for r in data['rows'] if all(term in ' '.join(str(r[k]) for k in ('app','mode','display','action','description')).casefold() for term in terms)]
    if args.json:print(json.dumps(data,ensure_ascii=True))
    elif args.app=='apps':listing(ui,data,True)
    elif interactive:browse(ui,data,args.query)
    else:listing(ui,data)
    return 0


if __name__=='__main__':
    from interaction import SelectionEnded
    try:sys.exit(main())
    except SelectionEnded as error:sys.exit(error.status)
    except KeyboardInterrupt:sys.exit(130)
    except (ValueError,OSError,KeyError,TypeError,subprocess.TimeoutExpired) as error:
        print('dots keys: '+str(error),file=sys.stderr);sys.exit(2)

#!/usr/bin/env python3
"""Browse binding metadata without running binding actions or app startup."""
import argparse
from contextlib import nullcontext
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from keys.model import APPS
from keys.providers import collect, snapshot, read_file
from keys.presentation import binding_prompt, menu_rows, menu_dimensions, styles, picker_colors, terminal_dimensions, MENU_HEADER


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


def preview_details(ui, row):
    muted, key, orange = styles(ui)
    fields = [('Keys', row['display'], key), ('Action', row['description'], None),
              ('Mode', row['mode'], orange)]
    fields.extend((label, str(row[name]), muted) for label, name in (
        ('Identifier', 'action'), ('Evidence', 'evidence'), ('Status', 'status'), ('Scope', 'scope')) if row.get(name))
    fields.append(('Notation', json.dumps(row['key'], ensure_ascii=False), muted))
    if row.get('source'):
        path = row['source']
        display = ui.path(path) + (':' + str(row['line']) if row.get('line') else '')
        style = muted
        if os.path.isabs(path) and (ui.color or ui.icons):
            _, icon, style = ui.resources.describe(path)
            if ui.icons:
                display = icon + ' ' + display
        fields.append(('Source', display, style))
    fields.append(('Description', row['description_source'], muted))
    for label, value, code in fields:
        if ui.width <= 13:
            ui.heading_spans([(label, '94')])
            ui.heading_spans([(value, code)])
        else:
            ui.detail_spans(label, [(value, code)], label_width=11, indent=0)


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
        label=row['display'];value=row['description']+' ['+row['evidence']+(' · '+row['status'] if row['status'] in ('shadowed','disabled') else '')+']'
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
    if os.environ.get('DOTS_MENU_CONTEXT'):
        from menu_tmux import TmuxContext
        ui.menu_context=TmuxContext.from_environment()
        ui.width=ui.menu_context.verify()[0]
    return ui


def choose_category(ui,coverage,*,include_all=True):
    from interaction import RichSelector
    from files.picker import fzf_colors
    rows=menu_rows(ui,coverage,include_all=include_all)
    if not rows:return None
    labels=[label for _,label in rows]
    context=getattr(ui,'menu_context',None)
    width,height=menu_dimensions(labels,size=context.verify()) if context else menu_dimensions(labels)
    popup=f'center,{width},{height}' if os.environ.get('TMUX') else False
    with context.selector_environment() if context else nullcontext(None) as environment:
        selected=RichSelector().fzf(binding_prompt(ui),
            labels,False,None,ui.color,ui.icons,picker_colors(fzf_colors(ui)),popup=popup,height=height,header=MENU_HEADER,info='inline-right',environment=environment)
    return rows[selected[0]][0]


def browse(ui,data,query,source='all',app=None,mode=None):
    from interaction import RichSelector, SelectionEvent
    from files.picker import fzf_colors
    from keys.browser import view, choose_mode
    if not data['rows']:listing(ui,data);return
    with tempfile.TemporaryDirectory(prefix='dots-keys-') as directory:
        path=Path(directory)/'bindings.json';path.write_text(json.dumps(data['rows']));path.chmod(0o600)
        command='"$DOTS_KEYS_PYTHON" -B "$DOTS_KEYS_HELPER" --preview "$DOTS_KEYS_DATA" {1}'
        if os.name=='nt':command='& $env:DOTS_KEYS_PYTHON -B $env:DOTS_KEYS_HELPER --preview $env:DOTS_KEYS_DATA {1}'
        preview=(command,None,dict(DOTS_KEYS_PYTHON=sys.executable,DOTS_KEYS_HELPER=str(Path(__file__).resolve()),DOTS_KEYS_DATA=str(path),DOTS_PROGRESS='never',DOTS_KEYS_CAPTURE='',DOTS_COLOR='always' if ui.color else 'never',DOTS_ICONS='always' if ui.icons else 'never'))
        context=getattr(ui,'menu_context',None)
        navigation={'query':query}
        while True:
            columns=(context.verify() if context else terminal_dimensions())[0]
            labels,indices,position=view(ui,data['rows'],app,mode,columns)
            try:
                with context.selector_environment() if context else nullcontext(None) as adapter:
                    selected=RichSelector().fzf(binding_prompt(ui,app,mode),labels,False,preview,ui.color,ui.icons,
                        picker_colors(fzf_colors(ui)),popup='center,99%' if os.environ.get('TMUX') else False,
                        query=navigation['query'],preview_size=45,header=binding_header(),info='inline-right',
                        initial_indices=indices,environment=adapter,navigation=navigation,
                        navigation_keys={'alt-m':'mode'},hscroll=False,preview_position=position)
            except SelectionEvent as event:
                if event.action!='mode':raise
                mode=choose_mode(ui,data['rows'],mode)
                continue
            details(ui,data['rows'][selected[0]])
            return


def binding_header():
    return 'Enter: review  Esc: cancel\nAlt-P: pane  Alt-J/K: scroll\nAlt-M: mode'


def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv)
    from files.catalog import Presentation
    ui=Presentation()
    if argv[:1]==['--preview']:
        if len(argv)!=3 or not argv[2].isdigit():raise ValueError('invalid preview request')
        rows=json.loads(read_file(Path(argv[1])));index=int(argv[2])
        if not isinstance(rows,list) or index>=len(rows):raise ValueError('unknown preview binding')
        try:ui.width=max(1,int(os.environ.get('FZF_PREVIEW_COLUMNS',ui.width)))
        except ValueError:pass
        preview_details(ui,rows[index]);return 0
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('app',nargs='?',choices=(*APPS,'all','apps'))
    p.add_argument('--query',default='');p.add_argument('--mode',help='Starting mode in the picker; exact mode filter in print/JSON output')
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
    bridge_note=None
    if args.app in (None,'zsh','all','apps') and 'zsh' not in apps and args.source!='configured' and os.environ.get('DOTS_KEYS_TARGET_PANE'):
        from keys.zsh_bridge import capture
        found,bridge_note=capture(os.environ['DOTS_KEYS_TARGET_PANE'])
        if found is not None:
            live.extend(found);apps.add('zsh')
    data=collect(root,None if args.app in ('all','apps') else args.app,live,apps,not args.no_defaults)
    if bridge_note:
        for item in data['coverage']:
            if item['app']=='zsh':
                item['notes']=([bridge_note] if 'zsh' in apps else [bridge_note,*item['notes']])
    data['rows']=[r for r in data['rows'] if (args.source=='all' or r['evidence']==args.source)
                  and (interactive or not args.mode or r['mode']==args.mode) and (not args.no_defaults or not r['default'])]
    if interactive and args.app in (None,'apps'):
        if not data['rows']:
            listing(ui,data);return 0
        coverage=[dict(item,count=sum(r['app']==item['app'] for r in data['rows']),
                       live=any(r['app']==item['app'] and r['evidence']=='live' for r in data['rows']))
                  for item in data['coverage']]
        args.app=choose_category(ui,coverage,include_all=args.app is None)
        if args.app is None:
            raise ValueError('No available keybinding categories')
        if args.app!='all':
            data['rows']=[r for r in data['rows'] if r['app']==args.app]
            data['coverage']=[item for item in data['coverage'] if item['app']==args.app]
    if args.query and not interactive:
        terms=args.query.casefold().split()
        data['rows']=[r for r in data['rows'] if all(term in ' '.join(str(r[k]) for k in ('app','mode','display','action','description')).casefold() for term in terms)]
    if args.json:print(json.dumps(data,ensure_ascii=True))
    elif args.app=='apps':listing(ui,data,True)
    elif interactive:browse(ui,data,args.query,args.source,app=args.app if args.app in APPS else None,mode=args.mode or None)
    else:listing(ui,data)
    return 0


if __name__=='__main__':
    from interaction import SelectionEnded
    try:sys.exit(main())
    except SelectionEnded as error:sys.exit(error.status)
    except KeyboardInterrupt:sys.exit(130)
    except (ValueError,OSError,KeyError,TypeError,subprocess.TimeoutExpired) as error:
        print('dots keys: '+str(error),file=sys.stderr);sys.exit(2)

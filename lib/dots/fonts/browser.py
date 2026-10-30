"""Font and glyph browsers using pinned menu context and inert preview snapshots."""
from contextlib import nullcontext
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from fonts.model import Library, sha
from interaction import RichSelector, SelectionEnded, SelectionEvent, rich_fzf_available, terminal
from menu_tmux import TmuxContext, request_file, read_request
from menus import Menu, Entry, choose, dots_argv, run_action, show_message
from files.catalog import Presentation
from files.picker import fzf_colors
from resources import clean


def context_for(args):
    if args.client and (os.name == 'nt' or not os.environ.get('TMUX')): raise ValueError('--client requires tmux')
    if os.name != 'nt' and (os.environ.get('TMUX') or os.environ.get('DOTS_MENU_CONTEXT')):
        return TmuxContext.capture(client=args.client) if args.client else TmuxContext.from_environment()
    return None


def select(title, pairs, context=None, *, frame=None):
    frame={} if frame is None else frame
    try:
        entry=choose(Menu('fonts:'+title,title,tuple(Entry(key,label) for key,label in pairs)),
                     mode='browse',context=context,compact=True,navigation=frame,query=frame.get('query',''),prompt='fonts·'+title.lower())
        return entry.id if entry else None
    except SelectionEvent: return None


def picker(rows, previews, frame, context, *, icons=False):
    if not rich_fzf_available(): return None
    if context:
        probe=subprocess.run(['fzf','--help'],capture_output=True,timeout=5)
        if probe.returncode or b'--popup' not in probe.stdout: return None
    ui=Presentation(terminal=True)
    columns,lines=context.verify() if context else shutil.get_terminal_size((80,24))
    width,height=max(1,columns-2),max(1,lines-2)
    labels=[clean((r['glyph']+'  '+r['name']+'  '+r['codepoint']) if icons else
                  r['id']+' · '+r.get('name','')+(' · installed '+r['installed']['version'] if r.get('installed') else '')) for r in rows]
    keys={'esc':'back','f1':'help'}
    keys.update({'alt-y':'copy','alt-i':'insert','alt-p':'print'} if icons else
                {'alt-u':'update','alt-n':'import','alt-t':'targets','alt-g':'icons','alt-l':'local','alt-s':'catalog','alt-d':'directory'})
    header=('Enter/Alt-Y: copy  Alt-I: insert  Alt-P: print' if icons else
            'Enter: actions  Alt-U: catalogs  Alt-N: import\nAlt-D: directory  Alt-L: local  Alt-S: catalog\nAlt-T: targets  Alt-G: icons')
    header+='\nEsc: back  F1: help  Ctrl-C: cancel'
    if frame.get('notice'): header+='\n'+frame['notice']
    with request_file(dict(schema=1,previews=previews,color=ui.color)) as path:
        command=('& $env:DOTS_FONTS_PYTHON -B $env:DOTS_FONTS_PREVIEW $env:DOTS_FONTS_REQUEST {1}' if os.name=='nt'
                 else '"$DOTS_FONTS_PYTHON" -B "$DOTS_FONTS_PREVIEW" "$DOTS_FONTS_REQUEST" {1}')
        preview=(command,'',dict(DOTS_FONTS_PYTHON=sys.executable,
            DOTS_FONTS_PREVIEW=str(Path(__file__).with_name('preview.py')),DOTS_FONTS_REQUEST=str(path)))
        from progress import permanent_output
        with permanent_output(), context.selector_environment() if context else nullcontext(None) as environment:
            try:
                result=RichSelector(backend='fzf').fzf('fonts·icons' if icons else 'fonts',labels,False,preview,
                    ui.color,ui.icons,fzf_colors(ui),popup=f'center,{width},{height}' if context else False,
                    height=height,preview_position='down',preview_lines=max(1,min(12,height//3)),preview_wrap=True,
                    query=frame.get('query',''),header=header,navigation=frame,navigation_keys=keys,event_selection=True,
                    environment=environment,focus_index=next((i for i,r in enumerate(rows) if (r.get('id') or r.get('name'))==frame.get('selected')),None))
            except SelectionEvent as event:
                if event.index is not None: frame['selected']=rows[event.index].get('id') or rows[event.index].get('name')
                raise
    frame['selected']=rows[result[0]].get('id') or rows[result[0]].get('name')
    return rows[result[0]]


def previews(library,rows):
    from fonts_cli import render
    result=[]
    for row in rows:
        stream=io.StringIO();render(dict(items=[row]),stream)
        entry=dict(text=stream.getvalue())
        saved=library.families.get(row['id'])
        if saved and any(r.get('available',True) for r in saved['versions'].values()):
            version,record=library.version(row['id'])
            fonts=record['fonts'];font=next((f for f in fonts if f['style'].casefold()=='regular'),fonts[0])
            path=library.folder(row['id'],version)/font['file']
            entry.update(font=str(path),sha256=font['sha256'])
        result.append(entry)
    return result


def invoke(arguments,context,library=None):
    report=arguments[0] in ('show','targets','current','versions','directories','defaults') or arguments==['update']
    if library is not None:
        fresh=Library(directory=str(library.directory) if library.directory else None)
        if fresh.guard!=library.guard or fresh.input_guards!=library.input_guards:raise ValueError('font collection or directory definitions changed; reopen the selection')
        if library.directory:arguments=[*arguments,'--directory',str(library.directory)]
    return run_action(dots_argv(['fonts',*arguments]),kind='output' if report else 'terminal',
                      context=context,title='fonts·'+arguments[0])


def family_actions(library,row,context):
    identity=row['id'];saved=library.families.get(identity)
    actions=[('show','Details'),('install','Store version') if library.directory else ('download','Download version')]
    if saved:
        actions += [('use','Use stored version') if library.directory else ('install','Install variant'),('set','Set application font'),('upgrade','Store updates' if library.directory else 'Upgrade'),('rollback','Roll back'),
                    ('unpin','Unpin') if saved.get('pin') else ('pin','Pin version'),('export','Export'),('uninstall','Uninstall'),('remove','Remove retained version')]
    else:actions.append(('set','Set application font'))
    action=select('Actions',actions,context)
    if not action:return
    if action=='set' and not saved:
        from fonts.menus import set_menu
        from fonts.commands import parser
        return set_menu(parser().parse_args(['set']),context=context,selected=row)
    if action=='show' and library.directory and not saved and identity not in library.catalog['families']:
        from fonts_cli import render
        stream=io.StringIO();render(dict(status='Personal library copy available to store',items=[row]),stream)
        show_message(stream.getvalue(),context=context,title='Font details');return
    argv=[action,identity]
    if action in ('download','install','use','set','rollback','pin','export','remove') or library.directory and action=='uninstall':
        candidates=(library.catalog['families'].get(identity,{}) if action=='download' else saved or {}).get('versions',{})
        if library.directory:
            if action=='install':
                candidates=dict(library.catalog['families'].get(identity,{}).get('versions',{}),
                                **library.collection['families'].get(identity,{}).get('versions',{}))
                candidates.update((saved or {}).get('versions',{}))
            else:candidates={v:r for v,r in candidates.items() if r.get('available',True)}
        if not candidates: raise ValueError('No versions available; update catalogs first')
        version=select('Version',[(v,v) for v in reversed(candidates)],context)
        if version is None:return
        argv += ['--version',version]
        if action in ('use','set') or action=='install' and not library.directory:
            record=saved['versions'][version]
            variants=sorted({f['variant'] for f in record['fonts']})
            variant=select('Variant',[(v,v) for v in variants],context)
            if variant is None:return
            argv+=['--variant',variant]
            if action=='set':
                face=select('Face',[(f['file'],f['file']) for f in record['fonts'] if f['variant']==variant],context)
                if face is None:return
                from fonts_cli import targets
                targets_=targets(library)
                target=select('Target',[(r['target'],r['target']) for r in targets_ if r['status']=='available'],context)
                if target is None:return
                argv+=['--face',face,'--target',target]
        if action=='export':
            from menu_input import prompt
            output=prompt('','Export to a new directory',context)
            if not output:return
            argv+=['--output',output]
    invoke(argv,context,library)


def browse(args):
    context=context_for(args);frame=dict(query=args.query or '');available=True
    directory=args.directory
    while True:
        library=Library(directory=directory)
        args._directory=str(library.directory) if library.directory else None
        frame['notice']='Directory: '+library.directory_names[0]+' · '+clean(str(library.directory)) if library.directory else 'Personal library'
        rows=library.rows(available=available)
        if library.directory and available:
            rows=list({**{k:dict(id=k,**v) for k,v in library.collection['families'].items()},**{r['id']:r for r in rows}}.values())
        if args.source and args.source!='all':rows=[r for r in rows if r['provider']==args.source]
        try:
            if not rows:
                action=select('Fonts',[('directory','Select directory'),('update','Update catalogs'),('import','Import existing fonts'),('icons','Icon search'),('targets','Application targets')],context)
                if action is None:return 0
            else:
                try:
                    row=picker(rows,previews(library,rows),frame,context)
                    if row is None:
                        from fonts_cli import emit
                        print('fonts: FZF unavailable; printing the collection',file=sys.stderr)
                        emit(dict(schema=1,items=rows),args);return 0
                    family_actions(library,row,context);continue
                except SelectionEvent as event: action=event.action
            if action=='back':return 0
            if action=='local':available=False;continue
            if action=='catalog':available=True;continue
            if action=='directory':
                from fonts.destinations import Destinations
                choice=select('Directory',[('personal','Personal library')]+[(r['path'],r['name']+' · '+r['path']) for r in Destinations().rows()],context)
                if choice is not None:directory=None if choice=='personal' else choice
                continue
            if action=='help':
                show_message('Alt-U refreshes catalogs. Alt-D selects a storage directory.\nIn a directory, Install stores all variants; Use/Set activates explicitly.\nIn the personal library, Download saves and Install registers fonts.\nSet changes an explicit app target after review. Esc goes back; Ctrl-C cancels.\nFont previews use optional ImageMagick and Chafa; otherwise metadata is shown.',context=context,title='Fonts help')
            elif action in ('update','targets'):invoke([action],context,library)
            elif action=='import':
                from menu_input import prompt
                source=prompt('','Import a font file or family directory (originals are kept)',context)
                if source:invoke(['import',source],context,library)
            elif action=='icons':
                from fonts.commands import parser
                icon_args=parser().parse_args(['icons']);icons(library,icon_args,context=context)
        except SelectionEnded as error:
            if error.status==130:return 130
            raise
        except (ValueError,OSError,subprocess.SubprocessError) as error:
            show_message(clean(str(error)),context=context,title='Fonts',code=1)


def insert(glyph,context):
    if context is None:raise ValueError('icon insertion requires tmux; use copy or print here')
    if len(glyph)!=1 or ord(glyph)<32 or ord(glyph)==127:raise ValueError('expected one printable glyph')
    context.verify()
    result=subprocess.run(context.command('send-keys','-t',context.pane,'-l','--',glyph),capture_output=True,timeout=5)
    if result.returncode:raise ValueError('icon insertion failed; the originating pane was not replaced with another target')


def copy(glyph):
    from clipboard import copy as native_copy
    try:native_copy(glyph)
    except ValueError:raise ValueError('Clipboard unavailable or copy failed; use Print to export the icon') from None


def icon_version(library,requested):
    if requested:return requested
    installed={r['installed']['version'] for r in library.families.values() if r['provider']=='nerd' and r.get('installed')}
    return next(iter(installed)) if len(installed)==1 else library.catalog.get('glyph_version')


def icons(library,args,*,context=None):
    from fonts_cli import emit
    version=icon_version(library,args.version)
    if version not in library.catalog['glyphs']:raise ValueError('glyph index is not cached; run fonts update --source nerd with the desired --version')
    rows=library.catalog['glyphs'][version]
    query=args.query or args.operand or ''
    filtered=[r for r in rows if all(word in (r['name']+' '+r['codepoint']+' '+r['collection']).casefold() for word in query.casefold().split())]
    if args.copy and args.insert:raise ValueError('--copy and --insert are mutually exclusive')
    if args.copy or args.insert:
        if len(filtered)!=1:raise ValueError('copy/insert requires one exact search result')
        if args.copy:copy(filtered[0]['glyph'])
        else:insert(filtered[0]['glyph'],context or context_for(args))
        if args.json:emit(dict(schema=1,status='copied' if args.copy else 'inserted',version=version,items=filtered),args)
        return 0
    if args.format:
        if len(filtered)!=1:raise ValueError('--format requires one exact icon result')
        print(filtered[0][args.format],end='');return 0
    if args.json or args.print or (context is None and not terminal() and not os.environ.get('DOTS_MENU_CONTEXT')):
        emit(dict(schema=1,version=version,items=filtered),args);return 0
    context=context or context_for(args)
    frame=dict(query=query,notice='Nerd Fonts '+str(version)+' · glyphs use the current terminal font')
    preview=[dict(kind='glyph',text=r['glyph']+'\n'+r['name']+'\n'+r['codepoint']+'\nCollection: '+r['collection']+'\nVersion: '+str(version)) for r in rows]
    while True:
        try:
            try:
                selected=picker(rows,preview,frame,context,icons=True);action='copy'
                if selected is None:emit(dict(schema=1,version=version,items=filtered),args);return 0
            except SelectionEvent as event:
                action=event.action
                if action=='back':return 0
                if action=='help':
                    show_message('Enter / Alt-Y: copy glyph and close\nAlt-I: insert in the originating tmux pane, without Enter\nAlt-P: print glyph and close\nOutside tmux use clipboard or stdout.',context=context,title='Icon search');continue
                if event.index is None:continue
                selected=rows[event.index]
            if action=='copy':copy(selected['glyph'])
            elif action=='insert':insert(selected['glyph'],context)
            elif action=='print':print(selected['glyph'],end='')
            return 0
        except (ValueError,OSError,subprocess.SubprocessError) as error:frame['notice']=clean(str(error))

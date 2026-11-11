"""Clipboard selection with inert previews and explicit terminal handoffs."""
from contextlib import nullcontext
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid

from clipboard_history import History
from interaction import RichSelector, SelectionEnded, SelectionEvent, rich_fzf_available
from menu_tmux import TmuxContext, request_file, read_request
from menus import Menu, Entry, styled_labels, dots_argv, run_action, show_message
from files.catalog import Presentation
from files.picker import fzf_colors
from resources import clean


def context_for(args):
    client = getattr(args, 'client', None)
    if client:
        return TmuxContext.capture(client=client)
    if os.environ.get('TMUX') or os.environ.get('DOTS_MENU_CONTEXT'):
        return TmuxContext.from_environment()
    return None


def insertion_text(text):
    # Escape sequences can terminate bracketed paste; other C0 controls can
    # trigger editor commands. Reject them rather than transform stored text.
    if any((ord(c) < 32 and c not in '\n\t') or 127 <= ord(c) < 160 for c in text):
        raise ValueError('terminal insertion refuses control characters; use copy or print')
    return text


def insert(text, context):
    insertion_text(text)
    if context is None:
        raise ValueError('insertion requires a clipboard shell widget or a verified tmux shell prompt; use copy or print')
    context.verify()
    def ready():
        state = context.observe('display-message','-p','-t',context.pane,
                                '#{pane_current_command}|#{bracket_paste_flag}|#{pane_in_mode}|#{pane_dead}').strip().split('|')
        if len(state)!=4 or state[0] not in ('bash','zsh','fish') or state[1:] != ['1','0','0']:
            raise ValueError('origin is not an idle shell with bracketed paste; use the clipboard shell widget')
    ready()
    name = 'dots-clipboard-' + uuid.uuid4().hex
    loaded = False
    try:
        result = subprocess.run(context.command('load-buffer','-b',name,'-'),input=text.encode(),capture_output=True,timeout=5)
        if result.returncode: raise ValueError('clipboard insertion buffer could not be prepared')
        loaded = True
        context.verify(); ready()
        result = subprocess.run(context.command('paste-buffer','-d','-p','-r','-b',name,'-t',context.pane),capture_output=True,timeout=5)
        if result.returncode: raise ValueError('clipboard insertion failed')
    finally:
        if loaded:
            subprocess.run(context.command('delete-buffer','-b',name),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5)


def picker(rows, settings, frame, context, selecting=False):
    from clipboard_cli import ClipboardPresentation
    from menu_popup import dimensions, preferences
    ui = ClipboardPresentation(terminal=True)
    columns, lines = context.verify() if context else shutil.get_terminal_size((80,24))
    width, height = dimensions(preferences(),(max(1,columns-2),max(1,lines-2)),(columns,lines))
    ui.width = max(1,width-4)
    entries = tuple(Entry(r['id'], clean(r['text']) or '(empty text)',
                          r['id'][:8] + ' · ' + ('pinned · ' if r['pinned'] else '') + r['source'] + ' · ' + str(r['bytes']) + ' B · ' + r['updated'][:19],
                          icon_role='menu.clipboard') for r in rows)
    labels = styled_labels(Menu('clipboard:entries','Clipboard history',entries),ui)
    keys = {'esc':'back','f1':'help','alt-h':'help','alt-y':'copy','alt-i':'insert',
            'alt-p':'print','alt-s':'pin','alt-d':'remove','alt-o':'config'}
    header = ('Enter/Alt-I: insert' if selecting else 'Enter/Alt-Y: copy') + '  Alt-H: keys'
    if frame.get('notice'): header += '\n' + frame['notice']
    # Bound the private preview request even with a large configured list.
    budget = max(64, min(12000, 3000000 // max(1, len(rows))))
    previews = [('ID: ' + r['id'] + '\nSource: ' + r['source'] + '  Bytes: ' + str(r['bytes']) + '\nUpdated: ' + r['updated'] + '\nPinned: ' + str(r['pinned']) + '\n\n' + ('\n'.join(clean(line[:240]) for line in r['text'].splitlines()[:settings['preview_lines']]) or '(empty text)'))[:budget] for r in rows]
    with request_file(dict(schema=1,previews=previews)) as path:
        command = ('& $env:DOTS_CLIP_PREVIEW_PYTHON -B $env:DOTS_CLIP_PREVIEW_SCRIPT $env:DOTS_CLIP_PREVIEW_REQUEST {1}' if os.name=='nt' else
                   '"$DOTS_CLIP_PREVIEW_PYTHON" -B "$DOTS_CLIP_PREVIEW_SCRIPT" "$DOTS_CLIP_PREVIEW_REQUEST" {1}')
        preview = (command,'',dict(DOTS_CLIP_PREVIEW_PYTHON=sys.executable,DOTS_CLIP_PREVIEW_SCRIPT=str(Path(__file__).resolve()),DOTS_CLIP_PREVIEW_REQUEST=str(path)))
        if not settings['preview'] or height < 12: preview = None
        with context.selector_environment() if context else nullcontext(None) as environment:
            try:
                result = RichSelector(backend='fzf').fzf('clipboard·history',labels,False,preview,
                    ui.color,ui.icons,fzf_colors(ui),popup=f'center,{width},{height}' if context else False,
                    height=height,hscroll=False,preview_position='down',preview_size=35,preview_wrap=True,
                    popup_resolved=context is not None,header=header,query=frame.get('query',''),navigation=frame,
                    navigation_keys=keys,event_selection=True,environment=environment,
                    bindings=('alt-p:accept',),
                    focus_index=next((i for i,r in enumerate(rows) if r['id']==frame.get('selected')),None))
            except SelectionEvent as event:
                row = rows[event.index] if event.index is not None else None
                if row: frame['selected'] = row['id']
                return event.action, row
    if not result: raise SelectionEnded(130)
    row = rows[result[0]]; frame['selected'] = row['id']
    return ('insert' if selecting else 'copy'), row


def browse(history, args, selecting=False):
    from clipboard_cli import selected, render
    if not rich_fzf_available() or not sys.stderr.isatty():
        if selecting: raise ValueError('interactive clipboard selection requires FZF and a terminal')
        render(dict(schema=1,status='observed',items=selected(history,args,listing=True)),args)
        return 0
    context = context_for(args)
    frame = dict(query=getattr(args,'query',''))
    while True:
        history = History()
        # FZF handles query filtering so actions retain it after refresh.
        from copy import copy
        listing_args = copy(args); listing_args.query = ''
        rows = selected(history,listing_args)
        action,row = picker(rows,history.settings,frame,context,selecting)
        if action=='back': return 130 if selecting else 0
        if action=='help':
            show_message('Enter: '+('insert' if selecting else 'copy')+'\nAlt-Y: copy\nAlt-I: insert without executing\nAlt-P: print and close\nAlt-S: pin/unpin\nAlt-D: remove with review\nAlt-O: configuration\nAlt-H/F1: help\nEsc: back   Ctrl-C: cancel',context=context,title='Clipboard keys')
            continue
        if action=='config':
            run_action(dots_argv(['config','browse','--query','clipboard']),kind='popup',context=context,title='Clipboard configuration')
            continue
        if row is None: continue
        try:
            fresh = history.get(row['id'])
            if fresh['updated'] != row['updated']: raise ValueError('entry changed; review it again')
            text = fresh['text']
            if action=='copy':
                from clipboard import _run
                _run('write',text.encode('utf-8')); history.set_control('last_digest',fresh['digest'])
                if not selecting: return 0
                frame['notice']='Copied'; continue
            if action=='insert':
                insertion_text(text)
                if selecting:
                    if getattr(args,'json',False): print(json.dumps(dict(schema=1,id=fresh['id'],text=text),ensure_ascii=True))
                    else: sys.stdout.buffer.write(text.encode('utf-8'))
                    return 0
                insert(text,context); return 0
            if action=='print':
                if selecting and getattr(args,'json',False):
                    print(json.dumps(dict(schema=1,id=fresh['id'],text=insertion_text(text)),ensure_ascii=True))
                else: sys.stdout.buffer.write(text.encode('utf-8'))
                return 0
            if action=='pin': history.change([fresh],pinned=not fresh['pinned'])
            elif action=='remove':
                # Shared popup confirmation remains attached to the same client.
                from menus import choose
                choice=choose(Menu('clipboard:remove','Remove this entry permanently?',(Entry('cancel','Cancel'),Entry('remove','Remove'))),mode='browse',context=context,compact=True)
                if choice and choice.id=='remove': history.change([fresh],delete=True)
        except ValueError as error:
            frame['notice']=clean(str(error))


if __name__ == '__main__':
    # Preview receives only an index into a private, sanitized snapshot.
    if len(sys.argv)!=3 or not re.fullmatch(r'0|[1-9][0-9]*',sys.argv[2]): raise SystemExit(2)
    data=read_request(sys.argv[1]); index=int(sys.argv[2])
    if not 0<=index<len(data['previews']): raise SystemExit(2)
    print(data['previews'][index])

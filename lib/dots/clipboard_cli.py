#!/usr/bin/env python3
"""Dots clipboard history: explicit operations, inert reads, shared human views."""
import argparse
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
import sqlite3
import sys

from clipboard_commands import COMMANDS, OPTIONS
from clipboard_history import History, metadata
from files.catalog import Presentation
from interaction import SelectionEnded, terminal, gum_confirm


class ClipboardPresentation(Presentation):
    def code(self, role, fallback='ui.foreground'):
        from style_config import current
        prefs = current()
        return (prefs.sgr('clipboard.' + role, app='cli') if prefs and prefs.style('clipboard.' + role, app='cli')
                else prefs.sgr(fallback, app='cli') if prefs else None)

    def heading(self, title):
        self.heading_spans([(self.icon('menu.clipboard', '󰅌') + ' ' if self.icons else '', self.code('heading','ui.heading')),
                            (title, self.code('heading','ui.heading'))])

    def detail(self, label, text, code=None):
        role = {'ID':'identity','Text':'text','Preview':'text','Source':'source','Updated':'timestamp','Pinned':'pinned'}.get(label)
        self.detail_spans(label, [(str(text), code or self.code(role or 'label'))], label_code=self.code('label','ui.label'))


class Parser(argparse.ArgumentParser):
    def print_help(self, file=None):
        ui = ClipboardPresentation(file)
        ui.heading(self.prog)
        for line in self.format_help().splitlines():
            ui.emit(ui.paint(line, ui.code('label','ui.foreground')))


def parser():
    root = Parser(prog='dots clipboard', description=COMMANDS[''][0])
    def options(p, action):
        for long, short, kind, help_text in OPTIONS[action]:
            flags = [long] + ([short] if short else [])
            kwargs = dict(help=help_text, default=argparse.SUPPRESS)
            if kind == 'flag': kwargs['action'] = 'store_true'
            elif kind.startswith('choice:'): kwargs['choices'] = kind[7:].split(',')
            p.add_argument(*flags, **kwargs)
    options(root, '')
    commands = root.add_subparsers(dest='action')
    for action, (description, _) in COMMANDS.items():
        if not action or ' ' in action: continue
        p = commands.add_parser(action, description=description, help=description)
        options(p, action)
        if action == 'watch':
            watch = p.add_subparsers(dest='watch_action')
            for child in ('start','stop','pause','resume','status'):
                w = watch.add_parser(child, description=COMMANDS['watch ' + child][0])
                options(w, 'watch ' + child)
        elif action in ('show','copy','print','insert'):
            p.add_argument('id')
        elif action in ('pin','unpin','remove'):
            p.add_argument('ids', nargs='+')
        elif action == 'init':
            p.add_argument('shell', choices=('bash','zsh','fish','powershell'))
        elif action == 'add':
            p.add_argument('text', nargs='*')
        elif action == 'search':
            p.add_argument('text', nargs='+')
    return root


def date(value, upper=False):
    if value is None: return None
    try:
        parsed = datetime.fromisoformat(value.replace('Z','+00:00'))
        if len(value) == 10 and upper: parsed += timedelta(days=1, microseconds=-1)
        if parsed.tzinfo is None: parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat(timespec='microseconds')
    except ValueError:
        raise ValueError('expected an ISO date or date/time') from None


def selected(history, args, *, listing=False):
    limit = getattr(args, 'limit', history.settings['list_limit'] if listing else 0)
    try: limit = int(limit)
    except ValueError: raise ValueError('--limit requires a nonnegative integer') from None
    if limit < 0: raise ValueError('--limit requires a nonnegative integer')
    query = ' '.join(args.text) if args.action == 'search' else getattr(args,'query','')
    return history.rows(query=query, pinned=getattr(args,'pinned',False), source=getattr(args,'source',None),
                        since=date(getattr(args,'since',None)), until=date(getattr(args,'until',None),True), limit=limit or None)


def render(data, args, stream=None):
    if getattr(args,'json',False) and stream is None:
        print(json.dumps(data, ensure_ascii=True)); return
    ui = ClipboardPresentation(stream)
    ui.heading('Clipboard history')
    if data.get('status'): ui.detail('Status', data['status'])
    for key in ('record_copies','paused','read_provider','write_provider','watch_status','watch_error','limit','max_entries','max_age_days','max_entry_bytes','notice','count'):
        if key in data: ui.detail(key.replace('_',' ').capitalize(), data[key])
    if 'path' in data: ui.resource_detail('Store', data['path'])
    for row in data.get('items', []):
        ui.emit()
        for label, key in (('ID','id'),('Updated','updated'),('Source','source'),('Pinned','pinned'),('Bytes','bytes')):
            if key in row: ui.detail(label, row[key])
        if 'text' in row:
            text = row['text']
            ui.detail('Text' if data.get('view')=='show' else 'Preview', text if data.get('view')=='show' else text[:160])
    if 'items' in data and not data['items']: ui.emit('  No matching entries.')


def report_status(history):
    from clipboard import _provider
    from clipboard_watch import status
    from platform_info import detect
    state = status(history)
    report = dict(schema=1, status='observed', path=str(history.path), record_copies=history.settings['record_copies'],
                  paused=history.control('paused',False), count=len(history.rows()), watch_status=state['status'],
                  max_entries=history.settings['max_entries'], max_age_days=history.settings['max_age_days'],
                  max_entry_bytes=history.settings['max_entry_bytes'])
    for operation in ('read','write'):
        try: report[operation+'_provider'] = Path(_provider(operation)[0]).name
        except ValueError: report[operation+'_provider'] = 'unavailable'
    if state.get('error'): report['watch_error'] = state['error']
    if detect()['platform']=='termux':
        report['notice'] = 'Android may restrict clipboard reads while Termux is not focused; Dots copies can still be recorded.'
    return report


def approve(rows, args):
    if not rows or getattr(args,'yes',False): return
    if getattr(args,'json',False) or not terminal():
        raise ValueError('removal requires --yes outside an interactive review; inspect --dry-run first')
    render(dict(schema=1,status='remove permanently',items=[metadata(r) for r in rows]),args,sys.stderr)
    answer = gum_confirm('Permanently remove these clipboard entries?', 'Remove')
    if answer is None:
        print('Permanently remove these clipboard entries? [y/N] ',end='',file=sys.stderr,flush=True)
        answer = sys.stdin.readline().strip().lower() in ('y','yes')
    if not answer: raise SelectionEnded(130)


def read_text(limit):
    data = sys.stdin.buffer.read(limit+1)
    if len(data)>limit: raise ValueError('input exceeds the configured size limit')
    try: return data.decode('utf-8')
    except UnicodeError: raise ValueError('input must be UTF-8 text') from None


def main(argv=None):
    args = parser().parse_args(argv)
    for name in ('color','icons'):
        if getattr(args,name,None): os.environ['DOTS_'+name.upper()] = getattr(args,name)
    action = args.action or ('browse' if terminal() and not getattr(args,'json',False) else 'list')
    args.action = action
    dry = getattr(args,'dry_run',False)
    if getattr(args,'raw',False) and getattr(args,'json',False): raise ValueError('--raw and --json cannot be combined')
    if action=='init':
        from clipboard_widgets import code
        print(code(args.shell),end=''); return 0
    history = History()
    if action == 'pick':
        from clipboard_menu import browse
        return browse(history,args,selecting=True)
    if action == 'browse':
        if getattr(args,'json',False) or not terminal(): action = 'list'
        else:
            from clipboard_menu import browse
            return browse(history,args)
    data = dict(schema=1,status='planned' if dry else 'complete',items=[])
    if action in ('list','search'):
        data.update(status='observed',items=selected(history,args,listing=True))
    elif action == 'status': data = report_status(history)
    elif action in ('pause','resume'):
        if not dry: history.set_control('paused', action=='pause')
        data.update(paused=action=='pause')
    elif action == 'watch':
        from clipboard_watch import start, stop, status
        sub = args.watch_action or 'status'
        if sub=='status': data.update(status='observed',watch=status(history))
        elif not dry:
            if sub=='start': start(history,getattr(args,'foreground',False))
            elif sub=='stop': stop(history)
            else: history.set_control('paused',sub=='pause')
        state=status(history)
        data.update(watch_status=state['status'],paused=history.control('paused',False))
        if state.get('error'): data['watch_error']=state['error']
    elif action in ('show','print','copy','insert'):
        row = history.get(args.id)
        if action=='print' or (action=='show' and getattr(args,'raw',False)):
            sys.stdout.buffer.write(row['text'].encode('utf-8')); return 0
        if not dry and action=='copy':
            from clipboard import _run
            _run('write',row['text'].encode('utf-8'))
            history.set_control('last_digest',row['digest'])
        elif not dry and action=='insert':
            from clipboard_menu import insert, context_for
            insert(row['text'],context_for(args))
        data.update(status='observed' if action=='show' else data['status'],view='show' if action=='show' else action,
                    items=[row if action=='show' else metadata(row)])
    elif action in ('add','capture'):
        if action=='capture' and dry: pass
        else:
            if action=='capture':
                from clipboard import paste
                try: text = paste().decode('utf-8')
                except UnicodeError: raise ValueError('clipboard does not contain UTF-8 text') from None
            else: text = ' '.join(args.text) if args.text else read_text(history.settings['max_entry_bytes'])
            history.validate_text(text)
            if not dry:
                row = history.add(text,source='capture' if action=='capture' else 'manual')
                data.update(items=[metadata(row)] if row else [],status='complete' if row else 'excluded')
    elif action in ('pin','unpin','remove','clear','prune'):
        if action in ('pin','unpin','remove'):
            rows = [history.get(i) for i in dict.fromkeys(args.ids)]
        elif action=='prune': rows = history.prune_candidates()
        else: rows = [r for r in selected(history,args) if getattr(args,'include_pinned',False) or not r['pinned']]
        data['items'] = [metadata(r) for r in rows]
        if not dry and rows:
            if action in ('remove','clear','prune'): approve(rows,args)
            history.change(rows,delete=action in ('remove','clear','prune'),pinned=action=='pin')
            if action in ('pin','unpin'): data['items']=[metadata(history.get(r['id'])) for r in rows]
    elif action=='export':
        print(json.dumps(dict(schema=1,entries=[{k:r[k] for k in ('text','pinned')} for r in selected(history,args)]),ensure_ascii=True)); return 0
    elif action=='import':
        try: document = json.loads(read_text(min(64*1024*1024,history.settings['max_entries']*(history.settings['max_entry_bytes']*6+100))))
        except json.JSONDecodeError: raise ValueError('invalid clipboard export JSON') from None
        data['count'] = history.import_entries(document,dry)
    render(data,args)
    return 0


if __name__ == '__main__':
    try: raise SystemExit(main())
    except SelectionEnded as error: raise SystemExit(error.status)
    except (ValueError, OSError, sqlite3.Error) as error:
        message = str(error) if isinstance(error,ValueError) else 'history storage or clipboard operation failed'
        ui=ClipboardPresentation(sys.stderr); ui.heading('Clipboard history'); ui.detail('Error',message,ui.code('error','status.error'))
        raise SystemExit(1)
    except KeyboardInterrupt: raise SystemExit(130)

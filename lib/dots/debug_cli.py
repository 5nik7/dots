#!/usr/bin/env python3
"""Dots diagnostics: read-only inspection and explicit startup execution."""
import argparse
import json
import os
from pathlib import Path
import sys
from debug.inspect import health,path_report,command_report,cache_report
from debug.startup import run,shell_choice


def render(data, action, view='sequence'):
    from files.catalog import Presentation
    ui=Presentation();ui.heading('Dots debug '+action)
    if action=='startup':
        ui.detail('Mode',data['mode']);ui.detail('Shell',data['shell'])
        if data['mode']=='plan':
            ui.detail('Note',data['note'])
            for index,row in enumerate(data['steps'],1):
                if row['kind']=='phase': ui.detail(str(index),row['name']+' (phase)')
                else: ui.resource_detail(str(index),row['name'],display=row['name'])
            ui.emit();ui.detail('Execute','Add --live for normal startup or --isolated for public fixtures')
            return
        for index,sample in enumerate(data['runs'],1):
            ui.emit();ui.detail('Run',index);ui.detail('Status',sample['status'],'32' if sample['status']=='completed' else '33')
            if sample.get('coverage'): ui.detail('Coverage',sample['coverage'])
            ui.detail('Startup',format_time(sample.get('startup_ms')));ui.detail('Process',format_time(sample.get('process_ms')))
            events=sample['events']
            if view=='slowest': events=sorted((e for e in events if e['duration_ms'] is not None),key=lambda e:e['duration_ms'],reverse=True)
            if view!='summary':
                for number,row in enumerate(events,1):
                    depth=min(row['depth'],6) if view=='sequence' else 0
                    display=row['name']
                    if sample.get('checkout') and display.startswith(sample['checkout']+os.sep): display=display[len(sample['checkout'])+1:]
                    name=('  '*depth+('└─ ' if depth else '')+ui.path(display))
                    _,icon,style=ui.resources.describe(row['name'],None,None)
                    if ui.icons and row['kind'] in ('source','source-entry','module','inlined'): name=icon+' '+name
                    timing=format_time(row['duration_ms']) if row['duration_ms'] is not None else 'entry only' if row['kind']=='source-entry' else '—'
                    label=f"{number:02d}"
                    start='?' if row['offset_ms'] is None else f"+{row['offset_ms']:.2f}"
                    state=('returned '+str(row.get('exit_status'))) if row['status']=='returned-nonzero' else row['status']
                    tail=' ['+row['kind']+']'+(' '+state if row['status'] not in ('completed','observed') else '')
                    if ui.width<70:
                        ui.emit()
                        ui.detail_spans(label,[(name,style)],label_width=2)
                        ui.detail_spans('',[(timing+' · '+start+' ms','90')],label_width=2)
                        ui.detail_spans('',[(tail.strip(),'33' if row['status'] in ('failed','incomplete','returned-nonzero') else '90')],label_width=2)
                    else:
                        ui.detail_spans(label,[(f"{start} ms  {timing}  ",'90'),(name,style),(tail,'33' if row['status'] in ('failed','incomplete','returned-nonzero') else '90')],label_width=4)
            if sample.get('note'): ui.detail('Note',sample['note'])
            if sample.get('truncated'): ui.detail('Coverage','Event limit reached; partial trace','33')
        ui.emit();ui.detail('Median',format_time(data['summary']['median_ms']));ui.detail('Range',format_time(data['summary']['min_ms'])+' – '+format_time(data['summary']['max_ms']))
        return
    rows=data.get('checks',data.get('rows'))
    for key,value in data.items():
        if key in ('version','rows','checks','exit_code') or value is None: continue
        if key in ('candidates','roots'):
            for path in value: ui.resource_detail('Candidate' if key=='candidates' else 'Root',path,kind='dir' if key=='roots' else None)
        elif key in ('path','selected') and value and (os.path.isabs(str(value))): ui.resource_detail(key.capitalize(),value)
        else: ui.detail({'forwarded_count':'Arguments','candidates':'Candidates'}.get(key,key.capitalize()),value)
    if rows is not None:
        for row in rows:
            ui.emit()
            if action=='path':
                ui.resource_detail(str(row['order']),row['path'],kind='dir')
                ui.detail('Origin',row['source']+(' · missing' if not row['exists'] else '')+(' · duplicate' if row['duplicate'] else ''))
                if row['command']:
                    ui.resource_detail('Selected' if row['selected'] else 'Shadowed',row['command'])
                continue
            for key,value in row.items():
                if value is None: continue
                if key=='elapsed_ms': ui.detail('Elapsed',format_time(value))
                elif key=='reasons':
                    for reason in value: ui.detail('Reason',reason)
                elif key in ('path','command'): ui.resource_detail(key.capitalize(),value)
                else: ui.detail(key.capitalize(),value,'31' if key=='status' and value=='failed' else '32' if key=='status' and value=='passed' else None)
        ui.emit()
        if 'checks' in data:
            ui.detail('Result',', '.join(str(sum(r.get('status')==status for r in rows))+' '+status for status in ('passed','failed','skipped')))
        else: ui.detail('Result',str(len(rows))+' entries' if rows else 'No entries')


def format_time(value):
    return 'not measured' if value is None else f'{value:.3f} ms'


def parser():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='action')
    for name in ('check','startup','path','command','cache','test'):
        s=sub.add_parser(name);s.add_argument('--json',action='store_true')
        if name=='check': s.add_argument('--only',choices=('platform','profiles','commands','startup','environment'))
        if name=='path': s.add_argument('command',nargs='?')
        if name=='command': s.add_argument('words',nargs=argparse.REMAINDER)
        if name in ('startup','cache'): s.add_argument('--shell',choices=('bash','zsh','powershell','fish') if name=='cache' else ('bash','zsh','powershell'))
        if name=='startup':
            mode=s.add_mutually_exclusive_group();mode.add_argument('--live',action='store_true');mode.add_argument('--isolated',action='store_true')
            s.add_argument('--login',action='store_true');s.add_argument('--view',choices=('sequence','slowest','summary'),default='sequence')
            s.add_argument('--runs',type=int,default=1);s.add_argument('--timeout',type=float,default=30)
        if name=='test':
            s.add_argument('suite',nargs='?',choices=('profiles','environment','dispatch','startup'));s.add_argument('--list',action='store_true')
    return p


def main(argv=None):
    p=parser();args=p.parse_args(argv)
    root=Path(os.environ.get('DOTS') or Path(__file__).resolve().parents[2]).resolve()
    if not args.action:
        from files.catalog import Presentation
        from command_metadata import catalog, roots, read
        ui=Presentation();ui.heading('Dots debug')
        for name,row in sorted(catalog(roots(root)).items()):
            if name.startswith('debug-') and not row['hidden']: ui.detail(name[6:].replace('-',' '),row['summary'])
        ui.emit()
        for example in read(root/'bin/dots-debug')['example']: ui.detail('Example',example)
        return 0
    if args.action=='startup':
        if not 1<=args.runs<=20 or not 1<=args.timeout<=300: p.error('--runs must be 1–20 and --timeout 1–300')
        if args.login and shell_choice(args.shell)=='powershell': p.error('--login has no PowerShell equivalent')
        if not (args.live or args.isolated) and (args.runs!=1 or args.timeout!=30): p.error('execution options require --live or --isolated')
        data=run(root,args)
    elif args.action=='check': data=health(root,args.only)
    elif args.action=='path':
        if args.command and (os.sep in args.command or os.altsep and os.altsep in args.command): p.error('path lookup requires a command name, not a path')
        data=path_report(root,args.command)
    elif args.action=='command': data=command_report(root,args.words[1:] if args.words[:1]==['--'] else args.words)
    elif args.action=='cache': data=cache_report(root,args.shell)
    else:
        from debug.selftest import run_tests
        data=run_tests(root,args.suite,args.list)
    if args.json: print(json.dumps(data,ensure_ascii=True))
    else: render(data,args.action,getattr(args,'view','sequence'))
    return data.get('exit_code',int(any(row.get('status')=='failed' for row in data.get('checks',[]))))


if __name__=='__main__':
    try: sys.exit(main())
    except (ValueError,OSError,KeyError,TypeError) as error:
        print('dots debug: '+str(error),file=sys.stderr);sys.exit(2)

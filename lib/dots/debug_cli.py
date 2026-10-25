#!/usr/bin/env python3
"""Dots diagnostics: read-only inspection and explicit startup execution."""
import argparse
import json
import os
from pathlib import Path
import sys
from debug.inspect import health,path_report,command_report,cache_report
from debug.startup import run,shell_choice


def render(data, action, view='tree', args=None):
    from debug.presentation import render as show
    show(data, action, view, args)


def format_time(value):
    return 'not measured' if value is None else f'{value:.3f} ms'


def parser():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='action')
    for name in ('check','startup','path','command','cache','test','record'):
        s=sub.add_parser(name);s.add_argument('--json',action='store_true')
        if name=='check':s.add_argument('--only',choices=('platform','profiles','commands','startup','environment'))
        if name=='path':
            s.add_argument('command',nargs='?');s.add_argument('--history',action='store_true');s.add_argument('--entry')
            s.set_defaults(detail='files',changes='path',file=[],name=[],show_values=[],view='tree',min_ms=0)
        if name=='record':s.add_argument('operation',choices=('start','stop','status'),nargs='?',default='status')
        if name=='command':s.add_argument('words',nargs=argparse.REMAINDER)
        if name in ('startup','path','cache','record'):
            s.add_argument('--shell',choices=('bash','zsh','powershell','fish') if name=='cache' else ('bash','zsh','powershell'))
        if name in ('startup','path'):
            mode=s.add_mutually_exclusive_group();mode.add_argument('--live',action='store_true');mode.add_argument('--isolated',action='store_true')
            s.add_argument('--login',action='store_true');s.add_argument('--runs',type=int,default=1);s.add_argument('--timeout',type=float,default=30)
            s.add_argument('--depth',type=int);s.add_argument('--limit',type=int,default=10000)
        if name=='startup':
            s.add_argument('--view',choices=('tree','sequence','slowest','summary'),default='tree')
            s.add_argument('--detail',choices=('files','changes','deep'),default='files')
            s.add_argument('--changes',default='path,variables,functions,aliases,options')
            s.add_argument('--file',action='append',default=[]);s.add_argument('--name',action='append',default=[])
            s.add_argument('--show-values',action='append',default=[]);s.add_argument('--min-ms',type=float,default=0)
        if name=='test':
            s.add_argument('suite',nargs='?',choices=('profiles','environment','dispatch','startup'));s.add_argument('--list',action='store_true')
    return p


def main(argv=None):
    p=parser();args=p.parse_args(argv)
    root=Path(os.environ.get('DOTS') or Path(__file__).resolve().parents[2]).resolve()
    if not args.action:
        from files.catalog import Presentation
        from command_metadata import catalog, roots, read
        from debug.presentation import Tree
        ui=Presentation();ui.heading('Dots debug')
        tree=Tree(ui)
        for name,row in sorted(catalog(roots(root)).items()):
            if name.startswith('debug-') and not row['hidden']: tree.row(name[6:].replace('-',' ')+' · '+row['summary'],name[6:].count('-'))
        ui.emit()
        for example in read(root/'bin/dots-debug')['example']: ui.detail('Example',example)
        return 0
    if args.action in ('startup','path'):
        from debug.changes import CATEGORIES
        import re, math
        if not set(args.changes.split(','))<=set(CATEGORIES):p.error('--changes contains an unknown category')
        if args.limit<1 or args.limit>10000 or args.depth is not None and args.depth<0 or args.min_ms<0 or not math.isfinite(args.min_ms):p.error('invalid display bounds')
        if any(not re.fullmatch('[A-Za-z_][A-Za-z_0-9]*',name) for name in args.show_values):p.error('--show-values requires a variable name')
        if not (args.live or args.isolated) and (args.detail!='files' or args.show_values):p.error('state capture requires --live or --isolated')
        if not 1<=args.runs<=20 or not 1<=args.timeout<=300: p.error('--runs must be 1–20 and --timeout 1–300')
        if args.login and shell_choice(args.shell)=='powershell': p.error('--login has no PowerShell equivalent')
        if not (args.live or args.isolated) and (args.runs!=1 or args.timeout!=30): p.error('execution options require --live or --isolated')
    if args.action=='startup':
        data=run(root,args)
    elif args.action=='record':
        from debug.record import snippet,history
        if args.operation in ('start','stop'):
            if args.json:p.error('start/stop emit shell code; --json is available for status')
            print(snippet(root,args.operation,shell_choice(args.shell)),end='');return 0
        data=history()
    elif args.action=='check': data=health(root,args.only)
    elif args.action=='path':
        if args.command and (os.sep in args.command or os.altsep and os.altsep in args.command): p.error('path lookup requires a command name, not a path')
        from debug.record import history
        if args.live or args.isolated:
            args.detail='deep';args.changes='path';args.show_values=[]
            trace=run(root,args);sample=trace['runs'][-1]
            evidence=dict(status=sample['status'],history=sample.get('changes',[]),note=sample.get('coverage',''),final_path=sample.get('final_path'),truncated=sample.get('truncated',False))
            data=path_report(root,args.command,sample.get('final_path')) if sample.get('final_path') is not None else dict(version=1,command=args.command,selected=None,rows=[])
            data.update(mode=trace['mode'],shell=trace['shell'],exit_code=trace['exit_code'])
            if sample.get('final_path') is None:data['exit_code']=1
        else:
            evidence=history();data=path_report(root,args.command);data['mode']='current-session'
        data.update(recording=evidence['status'],history=evidence['history'],note=evidence['note'],truncated=evidence.get('truncated',False))
        for row in data['rows']:
            row['history']=[e for e in evidence['history'] if e['name']==row.get('raw_path',row['path']) or e['action']=='reordered']
            row['provenance']='recorded' if row['history'] else 'inherited; origin unknown'
        if args.entry:
            data['rows']=[r for r in data['rows'] if r['path']==str(Path(args.entry).absolute())]
            data['history']=[r for r in data['history'] if r['name']==args.entry or r['action']=='reordered']
        if not (args.live or args.isolated) and evidence.get('final_path') is not None and evidence['final_path']!=os.environ.get('PATH',''):
            data['note']+=' Current PATH differs from the last observation; later changes are unrecorded.'
    elif args.action=='command': data=command_report(root,args.words[1:] if args.words[:1]==['--'] else args.words)
    elif args.action=='cache': data=cache_report(root,args.shell)
    else:
        from debug.selftest import run_tests
        data=run_tests(root,args.suite,args.list)
    if args.json: print(json.dumps(data,ensure_ascii=True))
    else: render(data,args.action,getattr(args,'view','tree'),args)
    return data.get('exit_code',int(any(row.get('status')=='failed' for row in data.get('checks',[]))))


if __name__=='__main__':
    try: sys.exit(main())
    except (ValueError,OSError,KeyError,TypeError) as error:
        print('dots debug: '+str(error),file=sys.stderr);sys.exit(2)

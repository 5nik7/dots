#!/usr/bin/env python3
"""Display-only bounded session list; never switches or modifies a session."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"lib/dots"))
import codex_attention
from status_styles import preferences,style,span,glyph,format_for,cells


def render(rows,current,width,prefs=None,attention=None):
    prefs=preferences() if prefs is None else prefs
    cfg=prefs.get('options',{}).get('session',{});fmt=format_for('session',prefs)
    attention=attention or {}
    def alert_style(kind):
        base=style('window.attention','#[fg=brightred,bold,nodim]',prefs)
        if kind=='finished':base+='#[fg=brightgreen]'
        return style('session.'+('finished' if kind=='finished' else 'alert'),base,prefs)
    def overflow(rows, text):
        kind=codex_attention.alert_type(row[3] for row in rows)
        return alert_style(kind)+text+'#[default]' if kind else text
    entries=[]
    for row in rows:
        identity,name,label,number,alerts,data=row
        if not re.fullmatch(r'\$[0-9]+',identity):continue
        kind='regular' if alerts else attention.get(identity)
        state=('finished' if kind=='finished' else 'alert') if kind else 'active' if identity==current else 'inactive'
        selected_fmt=dict(fmt,**fmt.get('alert',{})) if kind else fmt
        if kind:selected_fmt=dict(selected_fmt,before='[',after=']')
        base=style('session','#[default]',prefs)
        if kind:base=style('window.attention',base+'#[fg=brightred,bold,nodim]',prefs)
        if kind=='finished':base+='#[fg=brightgreen]'
        base=style('session.'+state,base,prefs)
        try:metadata=json.loads(data)
        except (ValueError,TypeError):metadata={}
        projects=metadata.get('projects',[]) if isinstance(metadata,dict) else []
        multiple=isinstance(projects,list) and len(projects)>1 and metadata.get('auto') is True
        if multiple:
            if identity==current:return ''
            continue
        repository=metadata.get('repository',{}) if isinstance(metadata,dict) else {}
        if not isinstance(repository,dict):repository={}
        if not isinstance(projects,list) or len(projects)!=1:repository={}
        host=repository.get('host','')
        repository_base=style('hosts.'+host,style('session.repository',base,prefs),prefs) if cfg.get('repository_color') and repository and not kind else base
        if cfg.get('name_source','workspace')=='workspace':name=label or name
        elif cfg.get('name_source')=='repository':
            try:
                roots=metadata.get('projects',[])
                if len(roots)==1:name=Path(roots[0]).name or name
            except (ValueError,AttributeError,TypeError):pass
        pieces=[]
        icon=glyph('session.default','',prefs)
        for part,text,visible in (('number',number,cfg.get('show_number',True)),('icon',icon,True),('name',name,cfg.get('show_name',True))):
            if not visible or not text:continue
            settings=fmt.get(part,{})
            pieces.append(span('session.'+state+'.'+part,settings.get('before','')+text+settings.get('after',''),style('session.'+part,repository_base if part in ('icon','name') else base,prefs),prefs))
        body=span('session.'+state+'.spacer',fmt.get('spacer',' '),style('session.spacer',base,prefs),prefs).join(pieces)
        text=span('session.'+state+'.surround',selected_fmt.get('before',' '),style('session.surround',base,prefs),prefs)+body+span('session.'+state+'.surround',selected_fmt.get('after',' '),style('session.surround',base,prefs),prefs)+'#[default]'
        entries.append((identity,text,cells(text),kind))
    if not entries or width<=0:return ''
    selected=next((i for i,row in enumerate(entries) if row[0]==current),0)
    separator=span('session.spacer',fmt.get('separator','│'),prefs=prefs);gap=cells(separator)
    left,right=selected,selected+1
    if entries[selected][2]>width:
        # Preserve unread attention even when the current name cannot fit.
        if any(row[3] for row in entries):return overflow(entries,'[!]' if width>=3 else '!')
        return span('session.active',current[:width],prefs=prefs)
    while True:
        candidates=[(a,b) for a,b in ((left-1,right),(left,right+1)) if a>=0 and b<=len(entries) and sum(r[2] for r in entries[a:b])+gap*(b-a-1)+2*(a>0)+2*(b<len(entries))<=width]
        if not candidates:break
        left,right=min(candidates,key=lambda p:abs(selected-p[0]-(p[1]-selected-1)))
    result=[r[1] for r in entries[left:right]]
    spare=width-sum(r[2] for r in entries[left:right])-gap*(right-left-1)
    if left and spare>=gap+1:result.insert(0,overflow(entries[:left],'<'));spare-=gap+1
    if right<len(entries) and spare>=gap+1:result.append(overflow(entries[right:],'>'))
    return separator.join(result)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--socket',required=True);parser.add_argument('--current',required=True);parser.add_argument('--width',type=int,default=31)
    args=parser.parse_args()
    fmt='\t'.join('#{'+field+'}' for field in ('session_id','session_name','@dots-workspace-label','@dots-session-number','session_alerts','@dots-workspace-data','session_created'))
    result=subprocess.run(['tmux','-S',args.socket,'list-sessions','-F',fmt],capture_output=True,text=True,timeout=1)
    if result.returncode or len(result.stdout)>65536:return ''
    rows=[line.split('\t') for line in result.stdout.splitlines()]
    rows=[r for r in rows if len(r)==7 and r[-1].isdigit()]
    key=codex_attention.socket_key(args.socket)
    created={r[0]:int(r[-1]) for r in rows}
    alerts={r['id']:r['alert_type'] for r in codex_attention.sessions(codex_attention.load())
            if r['key']==key and created.get(r['id'])==r['created'] and r['attention']}
    return render([r[:6] for r in rows],args.current,min(4096,max(0,args.width)),attention=alerts)


if __name__=='__main__':
    try:print(main())
    except (OSError,ValueError,subprocess.SubprocessError):print('')

#!/usr/bin/env python3
"""Bounded battery adapter: the existing battery tool still owns acquisition."""
import os
from pathlib import Path
import re
import subprocess
import sys
from status_styles import preferences,style,span,glyph,format_for
from widget_cache import Cache, age, command


def render(output,colors,slot=False,prefs=None,stale=False):
    prefs=preferences() if prefs is None else prefs
    match=re.fullmatch(r'\x1b\[(31|32|33)m([^\s\x00-\x1f#]+) ([0-9]{1,3})%\x1b\[0m(?: ([A-Z_]+))?\s*',output)
    if (not match or int(match[3])>100 or len(match[2])>4) and not slot:return ''
    state='unknown';icon='󰂑';percent='?%'
    if match and int(match[3])<=100 and len(match[2])<=4:
        state={'31':'critical','33':'low','32':'normal'}[match[1]];icon=match[2];percent=str(int(match[3]))+'%'
        if match[4] in ('CHARGING','FULL') and prefs.get('options',{}).get('battery',{}).get('charging_style'):state='charging'
    color=colors[{'critical':0,'low':1,'normal':2,'charging':2,'unknown':3}[state]]
    base=style('battery.'+state,'#[fg='+color+']',prefs)
    fmt=format_for('battery',prefs)
    icon=glyph('battery.'+state,icon,prefs)
    width=fmt.get('width',4) if slot else 0
    percent=percent.ljust(width)+('~' if stale else ' ') if slot else percent
    custom=any(k.startswith('battery.') and k.split('.')[-1] in ('icon','text','surround','spacer') for k in prefs.get('colors',{}))
    if not custom and all(fmt.get(k,v)==v for k,v in {'before':'','after':'','spacer':' ','width':4}.items()):
        from status_styles import literal
        return base+literal(icon)+' '+percent.ljust(width)+'#[default]'
    body=span('battery.'+state+'.icon',icon,style('battery.icon',base,prefs),prefs)
    if icon:body+=span('battery.spacer',fmt.get('spacer',' '),base,prefs)
    body+=span('battery.'+state+'.text',percent.ljust(width),style('battery.text',base,prefs),prefs)
    return span('battery.surround',fmt.get('before',''),base,prefs)+body+span('battery.surround',fmt.get('after',''),base,prefs)+'#[default]'


def acquire(options):
    tool=Path.home()/'repos/battery/battery'
    fmt='{color}{icon} {percent}{reset}'+(' {status}' if options.get('charging_style') else '')
    argv=['bash',str(tool),'--format',fmt,'--color','always','--color-by','percentage','--no-newline']
    for key in ('critical','low'):
        value=options.get(key)
        if type(value) is int and 0<=value<=100:argv+=['--'+key,str(value)]
    output=command(argv,5,511)
    if not render(output,['red','yellow','green','brightblack'],prefs={}):
        raise ValueError('invalid battery reading')
    return output


def main(argv):
    token=None
    if argv[:1]==['--_worker']:
        token=argv[1];argv=argv[2:]
    slot=bool(argv and argv[0]=='--slot')
    colors=argv[1:] if slot else ['red','yellow','green','brightblack']
    from status_styles import COLOR
    if len(colors)!=4 or any(not COLOR.fullmatch(c) for c in colors):return ''
    prefs=preferences();options=prefs.get('options',{}).get('battery',{})
    output=''
    if not slot:
        try:
            output=acquire(options)
        except (OSError,ValueError,subprocess.SubprocessError):pass
        return render(output,colors,False,prefs) if output else ''
    cache=Cache('battery',[str(Path.home()),options])
    if token:
        cache.work(token,lambda previous:({'output':acquire(options)},30),30,retry=10)
        return ''
    row=cache.read();elapsed=age(row.get('updated'))
    if elapsed<=300 and isinstance(row.get('value',{}).get('output'),str):
        output=row['value']['output']
    cache.schedule(__file__,argv,timeout=5)
    return render(output,colors,True,prefs,stale=bool(output) and (row.get('failed',False) or elapsed>35))


if __name__=='__main__':
    try:print(main(sys.argv[1:]))
    except (OSError,ValueError,IndexError,subprocess.SubprocessError):
        print(render('', ['red','yellow','green','brightblack'],slot=True))

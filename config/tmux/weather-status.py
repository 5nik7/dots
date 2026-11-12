#!/usr/bin/env python3
"""Cached solar schedule for tmux; acquisition belongs to a quiet worker."""
from datetime import datetime, date
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import time
import tomllib

from status_styles import preferences
from widget_cache import Cache, age, command, read

ROOT=Path(__file__).resolve().parents[2]


def settings():
    path=Path(os.environ.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))/'wttr/config.toml'
    if not path.exists():path=ROOT/'config/wttr/config.toml'
    cfg=tomllib.loads(read(path.resolve()).decode('utf-8'))
    options=preferences().get('options',{}).get('clock',{})
    return path,cfg,options


def seconds(options,key,default,low,high):
    value=options.get(key,default)
    return value if type(value) is int and low<=value<=high else default


def timezone():
    return [os.environ.get('TZ',''),list(time.tzname),time.timezone]


def location_id(location):
    return hashlib.sha256(location.encode('utf-8')).hexdigest()


def next_location(value,interval):
    if not value.get('geo_failures') and age(value.get('geo_updated'))!=float('inf'):
        return value['geo_updated']+interval
    deadline=value.get('geo_next',0)
    return deadline if type(deadline) in (int,float) and 0<=deadline<=time.time()+86400 else 0


def solar_days(data):
    result={}
    for day in data.get('weather',[]):
        try:
            key=day['date'];date.fromisoformat(key)
            solar=day['astronomy'][0]
            rise,setting=[datetime.strptime(solar[field],'%I:%M %p').strftime('%H:%M') for field in ('sunrise','sunset')]
            if rise<setting:result[key]=[rise,setting]
        except (ValueError,TypeError,KeyError,IndexError):continue
    return result


def daylight(value,max_stale,now=None):
    now=now or datetime.now()
    if value.get('timezone')!=timezone() or age(value.get('solar_updated'),now.timestamp())>max_stale:
        return 'unknown'
    days=value.get('days',{})
    if not isinstance(days,dict):return 'unknown'
    today=now.date().isoformat()
    candidates=[key for key in days if isinstance(key,str) and key<=today]
    if not candidates:return 'unknown'
    key=max(candidates)
    try:
        if (now.date()-date.fromisoformat(key)).days*86400>max_stale:return 'unknown'
        rise,setting=[datetime.strptime(v,'%H:%M').time() for v in days[key]]
        if rise>=setting:return 'unknown'
        return 'day' if rise<=now.time()<setting else 'night'
    except (ValueError,TypeError):return 'unknown'


def refresh(previous,path,options,attached):
    sys.path[:0]=[str(ROOT/'lib/dots'),str(ROOT/'lib/dots/wttr')]
    from wttr import core
    _,cfg=core.config(path)
    value=dict(previous);now=time.time();resolved=None
    if value.get('timezone') and value['timezone']!=timezone():
        value.pop('days',None);value.pop('solar_updated',None)
        value['weather_after']=now
    value['timezone']=timezone()
    interval=seconds(options,'location_refresh_seconds',21600,3600,86400)
    auto=options.get('auto_location') is True and attached and not cfg['default_location']
    geo_next=next_location(value,interval)
    if auto and now>=geo_next:
        helper=core.geo_helper()
        if helper:
            value['geo_attempted']=now
            try:
                data=core.load_json(command([helper,'--json','--timeout','20'],20,65536))
                if not isinstance(data,dict) or type(data.get('version')) is not int or data['version']!=1:
                    raise ValueError('invalid location')
                city=core.validate_location(data.get('city'))
                attribution=data.get('attribution','')
                if not isinstance(attribution,str):attribution=''
                resolved=(city,'cached city',core.clean(attribution))
                value.update(geo_updated=time.time(),geo_next=time.time()+interval,geo_failures=0)
            except (OSError,ValueError,subprocess.SubprocessError):
                count=value.get('geo_failures',0)
                count=min(count+1,3) if type(count) is int and count>=0 else 1
                # The helper independently enforces longer service cooldowns.
                value.update(geo_failures=count,geo_next=time.time()+(300,900,3600)[count-1])
        else:
            value.update(geo_next=now+3600,geo_failures=3)
    if resolved is None:
        try:resolved=core.resolve_location(None,cfg,True,cfg['timeout'])
        except (OSError,ValueError):pass
    cache=core.Cache(cfg)
    row=cache.read()
    if resolved:
        identity=location_id(resolved[0])
        if value.get('location')!=identity:
            value.pop('days',None);value.pop('solar_updated',None)
        value['location']=identity
        try:row=cache.refresh(background=True,resolved=resolved)
        except (OSError,ValueError):row=cache.read()
    elif not cfg['default_location'] and row.get('location') and not value.get('location'):
        value['location']=location_id(row['location'])
    if row.get('location') and location_id(row['location'])==value.get('location'):
        days=solar_days(row.get('data',{}))
        if days and row.get('updated',0)>=value.get('weather_after',0) and age(row.get('updated'))<age(value.get('solar_updated')):
            value.update(days=days,solar_updated=row['updated'],timezone=timezone())
    delay=cfg['ttl']
    if auto:delay=min(delay,max(5,next_location(value,interval)-time.time()))
    if not value.get('days'):delay=min(delay,300)
    return value,delay


def main(argv):
    token=None
    if argv[:1]==['--_worker']:
        token=argv[1];argv=argv[2:]
    attached=argv==['--attached','1']
    path,cfg,options=settings()
    cache=Cache('solar',[str(path.resolve()),cfg.get('default_location',''),cfg.get('language','en')])
    if token:
        cache.work(token,lambda previous:refresh(previous,path,options,attached),900,retry=300)
        return 'unknown'
    row=cache.read();value=row.get('value',{})
    geo_next=next_location(value,seconds(options,'location_refresh_seconds',21600,3600,86400))
    due=(not row.get('failed') and options.get('auto_location') is True and attached
         and not cfg.get('default_location') and type(geo_next) in (int,float) and time.time()>=geo_next)
    cache.schedule(__file__,['--attached','1' if attached else '0'],timeout=85,due=due)
    return daylight(value,seconds(options,'sun_times_max_stale_seconds',604800,86400,604800))


if __name__=='__main__':
    try:print(main(sys.argv[1:]))
    except (OSError,ValueError,TypeError,KeyError,IndexError,subprocess.SubprocessError):print('unknown')

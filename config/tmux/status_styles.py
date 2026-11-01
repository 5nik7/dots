"""Literal component rendering from the published snapshot, with no refresh."""
from functools import lru_cache
import json
import os
from pathlib import Path
import re
import stat
import unicodedata

ATTRS={'bold':'bold','dim':'dim','italic':'italics','underline':'underscore','reverse':'reverse','strikethrough':'strikethrough'}
COLOR=re.compile(r'(?:#[0-9a-fA-F]{6}|default|(?:bright_?)?(?:black|red|green|yellow|blue|magenta|cyan|white)|foreground|background|muted)\Z')


@lru_cache(maxsize=1)
def preferences():
    path=Path(os.environ.get('XDG_STATE_HOME',str(Path.home()/'.local/state')))/'dots/current/theme/preferences.json'
    try:
        if not stat.S_ISREG(path.lstat().st_mode) or path.stat().st_size>4*1024*1024:return {}
        data=json.loads(path.read_text())
        return data.get('apps',{}).get('tmux',{}) if data.get('schema')==1 else {}
    except (OSError,ValueError,AttributeError):return {}


def literal(value):
    text=''.join(c for c in str(value) if ord(c)>=32 and not 127<=ord(c)<160)
    return text.replace('#','##')


def cells(value):
    value=re.sub(r'##|#\[[^]]*\]',lambda match:'#' if match[0]=='##' else '',value)
    return sum(0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in ('W','F') else 1 for c in value)


def style(role,base='',prefs=None):
    prefs=preferences() if prefs is None else prefs
    fields=prefs.get('colors',{}).get(role,{})
    values=[]
    for field,value in fields.items():
        if field in ('fg','bg') and isinstance(value,str) and COLOR.fullmatch(value):
            value={'foreground':'default','background':'default','muted':'brightblack'}.get(value,value.replace('bright_','bright'))
            values.append(field+'='+value)
        elif field in ATTRS and type(value) is bool:values.append(('' if value else 'no')+ATTRS[field])
    return base+('#['+','.join(values)+']' if values else '')


def span(role,text,base='',prefs=None):
    return '#[default]'+style(role,base,prefs)+literal(text)+'#[default]'+base


def format_for(component,prefs=None):
    return (preferences() if prefs is None else prefs).get('formatting',{}).get(component,{})


def glyph(role,fallback,prefs=None):
    return (preferences() if prefs is None else prefs).get('icons',{}).get(role,fallback)

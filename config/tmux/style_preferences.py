"""Read published preferences only; tmux polling never resolves or publishes themes."""
from functools import lru_cache
import json
import os
from pathlib import Path
import stat

@lru_cache(maxsize=1)
def preferences():
    path = Path(os.environ.get('XDG_STATE_HOME', str(Path.home()/'.local/state')))/'dots/current/theme/preferences.json'
    try:
        if not stat.S_ISREG(path.lstat().st_mode) or path.stat().st_size > 2*1024*1024: return {}
        doc = json.loads(path.read_text())
        return doc.get('apps',{}).get('tmux',{}).get('icons',{}) if doc.get('schema') == 1 else {}
    except (OSError,ValueError,AttributeError): return {}


def glyph(role, fallback):
    value = preferences().get(role, fallback)
    if not isinstance(value,str) or len(value)>64 or any(ord(c)<32 or 127<=ord(c)<160 for c in value): value=fallback
    return value.replace('#','##').replace('|','')

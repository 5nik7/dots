"""Native weather configuration shared with the Dots configuration editor."""
import re
import unicodedata
from pathlib import Path
import tomllib
from files.file_platform import config_root, open_nofollow
import os
import stat

ROOT=Path(__file__).resolve().parents[3]


def clean(value):
    return ''.join(c for c in str(value) if not unicodedata.category(c).startswith('C') or unicodedata.category(c)=='Co')[:1024]


def validate_location(value,empty=False):
    if not isinstance(value,str) or len(value)>200 or clean(value)!=value or (not empty and not value.strip()):
        raise ValueError('location must be nonempty text of at most 200 characters')
    return value.strip()


def validate_language(value):
    if not isinstance(value,str) or not re.fullmatch(r'[a-z]{2,3}(?:-[A-Za-z]{2,4})?',value):
        raise ValueError('language must be a language code such as en or pt-br')


def selected_path(root=ROOT):
    user=config_root()/'wttr/config.toml'
    return user if user.exists() or user.is_symlink() else Path(root)/'config/wttr/config.toml'


def read(path):
    fd=open_nofollow(path,os.O_RDONLY|getattr(os,'O_NONBLOCK',0))
    with os.fdopen(fd,'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):raise ValueError('expected a regular weather config')
        raw=stream.read(128*1024+1)
    if len(raw)>128*1024:raise ValueError('weather config exceeds size limit')
    return raw.decode('utf-8')


def config(path=None,root=ROOT):
    selected=Path(path).absolute() if path else selected_path(root)
    return selected,validate(tomllib.loads(read(selected.resolve())))


def validate(data):
    for key, default in [('default_location', ''), ('units', 'us'), ('language', 'en'),
                         ('days', 3), ('timeout', 20), ('ttl', 900), ('max_stale', 21600),
                         ('location_max_age', 86400), ('widget', '{icon} {temperature}{unit}{stale_marker}')]:
        data.setdefault(key, default)
    if data['units'] not in ('us', 'metric'):
        raise ValueError('config units must be us or metric')
    for key, low, high in [('days', 1, 3), ('timeout', 1, 60), ('ttl', 60, 86400),
                           ('max_stale', 60, 86400), ('location_max_age', 0, 86400)]:
        if type(data[key]) is not int or not low <= data[key] <= high:
            raise ValueError('invalid config ' + key)
    if data['max_stale'] < data['ttl']:
        raise ValueError('max_stale must be at least ttl')
    data['default_location'] = validate_location(data['default_location'], empty=True)
    validate_language(data['language'])
    if not isinstance(data['widget'], str):
        raise ValueError('widget must be a string')
    for group in ('icons', 'night_icons'):
        icons = data.setdefault(group, {})
        if not isinstance(icons, dict) or any(not isinstance(v, str) or len(v) > 16 or clean(v) != v for v in icons.values()):
            raise ValueError('invalid ' + group)
    from .styling import validate_config
    validate_config(data)
    return data


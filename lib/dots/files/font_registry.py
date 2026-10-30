"""Bounded Windows current-user font values for the shared transaction engine."""
import os
from pathlib import PureWindowsPath

KEY = r'Software\Microsoft\Windows NT\CurrentVersion\Fonts'


def validate(spec):
    if not isinstance(spec, dict) or set(spec) != {'name', 'before', 'after'}:
        raise ValueError('invalid font registration operation')
    name = spec['name']
    if not isinstance(name, str) or not name or len(name) > 255 or any(ord(c) < 32 for c in name):
        raise ValueError('invalid font registration name')
    base = PureWindowsPath(os.environ.get('LOCALAPPDATA', '')) / 'Microsoft/Windows/Fonts'
    for value in (spec['before'], spec['after']):
        if value is None: continue
        if (not isinstance(value, str) or not base.is_absolute()
                or PureWindowsPath(value).parent != base
                or PureWindowsPath(value).suffix.lower() not in ('.ttf', '.otf')
                or '..' in PureWindowsPath(value).parts or any(ord(c) < 32 for c in value)):
            raise ValueError('font registration must reference the current-user font directory')


def read(name):
    if os.name != 'nt': raise ValueError('Windows font registration requires native Windows')
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY) as key:
            value, kind = winreg.QueryValueEx(key, name)
    except FileNotFoundError:
        return None
    if kind != winreg.REG_SZ: raise ValueError('conflicting Windows font registration type')
    return value


def write(name, value):
    if os.name != 'nt': raise ValueError('Windows font registration requires native Windows')
    import winreg
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, KEY, 0, winreg.KEY_SET_VALUE) as key:
        if value is None:
            try: winreg.DeleteValue(key, name)
            except FileNotFoundError: pass
        else: winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
        winreg.FlushKey(key)


def verify(spec):
    validate(spec)
    if read(spec['name']) != spec['before']:
        raise ValueError('font registration changed after preview')


def apply(spec):
    verify(spec)
    write(spec['name'], spec['after'])
    if read(spec['name']) != spec['after']:
        raise ValueError('font registration verification failed')


def rollback(spec):
    validate(spec)
    value = read(spec['name'])
    if value == spec['before']: return
    if value != spec['after']: raise ValueError('font registration drift blocks recovery')
    write(spec['name'], spec['before'])

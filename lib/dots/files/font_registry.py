"""Bounded Windows font registrations for personal and machine transactions."""
import os
import re
from pathlib import Path
from pathlib import PureWindowsPath

KEY = r'Software\Microsoft\Windows NT\CurrentVersion\Fonts'

def windows_root():
    """Use the OS directory, independently of account/environment overrides."""
    if os.name != 'nt':
        raise ValueError('system font installation requires native Windows')
    import ctypes
    buffer = ctypes.create_unicode_buffer(32768)
    size = ctypes.windll.kernel32.GetSystemWindowsDirectoryW(buffer, len(buffer))
    if not 0 < size < len(buffer):
        raise ctypes.WinError()
    return Path(buffer.value)


def machine_state():
    return windows_root() / 'DotsFontState' / 'dots'


def elevated():
    import ctypes
    return os.name == 'nt' and bool(ctypes.windll.shell32.IsUserAnAdmin())


def validate(spec):
    if not isinstance(spec, dict) or set(spec) - {'scope'} != {'name', 'before', 'after'} or spec.get('scope', 'user') not in ('user', 'system'):
        raise ValueError('invalid font registration operation')
    name = spec['name']
    if not isinstance(name, str) or not name or len(name) > 255 or any(ord(c) < 32 for c in name):
        raise ValueError('invalid font registration name')
    base = PureWindowsPath(os.environ.get('LOCALAPPDATA', '')) / 'Microsoft/Windows/Fonts'
    for value in (spec['before'], spec['after']):
        if value is None: continue
        if spec.get('scope') == 'system':
            if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{24}-[0-9a-f]{24}\.(ttf|otf)', value):
                raise ValueError('machine registration requires a Dots-owned font filename')
            continue
        if (not isinstance(value, str) or not base.is_absolute()
                or PureWindowsPath(value).parent != base
                or PureWindowsPath(value).suffix.lower() not in ('.ttf', '.otf')
                or '..' in PureWindowsPath(value).parts or any(ord(c) < 32 for c in value)):
            raise ValueError('font registration must reference the current-user font directory')


def read(name, *, system=False):
    if os.name != 'nt': raise ValueError('Windows font registration requires native Windows')
    import winreg
    try:
        hive = winreg.HKEY_LOCAL_MACHINE if system else winreg.HKEY_CURRENT_USER
        with winreg.OpenKey(hive, KEY, 0, winreg.KEY_READ | (winreg.KEY_WOW64_64KEY if system else 0)) as key:
            value, kind = winreg.QueryValueEx(key, name)
    except FileNotFoundError:
        return None
    if kind != winreg.REG_SZ: raise ValueError('conflicting Windows font registration type')
    return value


def write(name, value, *, system=False):
    if os.name != 'nt': raise ValueError('Windows font registration requires native Windows')
    import winreg
    hive = winreg.HKEY_LOCAL_MACHINE if system else winreg.HKEY_CURRENT_USER
    with winreg.CreateKeyEx(hive, KEY, 0, winreg.KEY_SET_VALUE | (winreg.KEY_WOW64_64KEY if system else 0)) as key:
        if value is None:
            try: winreg.DeleteValue(key, name)
            except FileNotFoundError: pass
        else: winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
        winreg.FlushKey(key)


def machine_values():
    import winreg
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, KEY, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
    except FileNotFoundError:
        return
    with key:
        for index in range(winreg.QueryInfoKey(key)[1]):
            name, path, kind = winreg.EnumValue(key, index)
            if kind in (winreg.REG_SZ, winreg.REG_EXPAND_SZ):
                yield name, os.path.expandvars(path)


def check_machine_conflicts(spec):
    """A different registry value can reference the same face or font file."""
    directory = PureWindowsPath(windows_root()) / 'Fonts'
    paths = {directory / value for value in (spec['before'], spec['after']) if value}
    def face(name):
        return re.sub(r' \((?:TrueType|OpenType)\)$', '', name, flags=re.I).casefold()
    for name, value in machine_values():
        if name.casefold() != spec['name'].casefold() and (face(name) == face(spec['name']) or directory / value in paths):
            raise ValueError('another machine font registration uses this face or file: ' + name)


def verify(spec):
    validate(spec)
    if spec.get('scope') == 'system':
        check_machine_conflicts(spec)
    if read(spec['name'], **scope_args(spec)) != spec['before']:
        raise ValueError('font registration changed after preview')


def scope_args(spec):
    return {'system': True} if spec.get('scope') == 'system' else {}


def apply(spec):
    verify(spec)
    write(spec['name'], spec['after'], **scope_args(spec))
    if read(spec['name'], **scope_args(spec)) != spec['after']:
        raise ValueError('font registration verification failed')


def rollback(spec):
    validate(spec)
    if spec.get('scope') == 'system':
        check_machine_conflicts(spec)
    value = read(spec['name'], **scope_args(spec))
    if value == spec['before']: return
    if value != spec['after']: raise ValueError('font registration drift blocks recovery')
    write(spec['name'], spec['before'], **scope_args(spec))

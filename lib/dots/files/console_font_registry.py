"""Journal only the FaceName string in existing current-user console keys."""
import os


def key_path(name):
    if (not isinstance(name, str) or len(name) > 255 or '\\' in name
            or name.startswith('%%') or any(ord(c) < 32 for c in name)):
        raise ValueError('invalid console profile')
    return 'Console' + ('\\' + name if name else '')


def read(name):
    if os.name != 'nt':
        raise ValueError('classic Console requires native Windows')
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path(name)) as key:
        try:
            value, kind = winreg.QueryValueEx(key, 'FaceName')
        except FileNotFoundError:
            return None
    if kind != winreg.REG_SZ:
        raise ValueError('unexpected Console FaceName registry type')
    return value


def profiles():
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Console') as key:
        names = [winreg.EnumKey(key, i) for i in range(winreg.QueryInfoKey(key)[0])]
    return [''] + sorted(n for n in names if not n.startswith('%%') and read(n) is not None)


def write(name, value):
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path(name), 0, winreg.KEY_SET_VALUE) as key:
        if value is None:
            winreg.DeleteValue(key, 'FaceName')
        else:
            winreg.SetValueEx(key, 'FaceName', 0, winreg.REG_SZ, value)
        winreg.FlushKey(key)


def validate(spec):
    if not isinstance(spec, dict) or set(spec) != {'name', 'before', 'after'}:
        raise ValueError('invalid Console FaceName operation')
    key_path(spec['name'])
    for face in (spec['before'], spec['after']):
        if face is not None and (not isinstance(face, str) or len(face) > 255 or any(ord(c) < 32 for c in face)):
            raise ValueError('invalid Console FaceName')


def verify(spec):
    validate(spec)
    if read(spec['name']) != spec['before']:
        raise ValueError('Console font changed after preview')


def apply(spec):
    verify(spec)
    write(spec['name'], spec['after'])
    if read(spec['name']) != spec['after']:
        raise ValueError('Console font verification failed')


def rollback(spec):
    validate(spec)
    if read(spec['name']) != spec['before']:
        apply(dict(name=spec['name'], before=spec['after'], after=spec['before']))

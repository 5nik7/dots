"""App configuration locations; no app execution or writes."""
import os
from pathlib import Path


def eza_config_directory(*, windows=None):
    """Shared eza destination for the Bash and native publishers."""
    windows = os.name == 'nt' if windows is None else windows
    home = os.environ.get('HOME') or str(Path.home())
    root = (os.environ.get('APPDATA') or str(Path(home) / 'AppData/Roaming')) if windows else (
        os.environ.get('XDG_CONFIG_HOME') or str(Path(home) / '.config'))
    value = os.environ.get('DOTS_APP_EZA_CONFIG') or os.environ.get('EZA_CONFIG_DIR') or root + '/eza'
    components = value.replace('\\', '/').split('/') if windows else value.split('/')
    path = Path(value)
    if (not path.is_absolute() or any(ord(c) < 32 or ord(c) == 127 for c in value)
            or any(c in ('.', '..') for c in components)):
        raise ValueError('eza configuration must be an absolute directory without control characters or dot components')
    if os.name == 'nt':
        from file_platform import validate_windows_path
        validate_windows_path(path)
    return path


def television_config_directory(*, windows=None):
    """Match Television's config search, with an explicit Dots override."""
    windows = os.name == 'nt' if windows is None else windows
    home = Path(os.environ.get('HOME') or Path.home())
    xdg = os.environ.get('XDG_CONFIG_HOME')
    if xdg and Path(xdg).is_absolute():
        default = Path(xdg) / 'television'
    elif windows:
        default = Path(os.environ.get('LOCALAPPDATA') or home / 'AppData/Local') / 'television/config'
    else:
        default = home / '.config/television'
    value = os.environ.get('DOTS_APP_TELEVISION_CONFIG') or os.environ.get('TELEVISION_CONFIG') or str(default)
    components = value.replace('\\', '/').split('/') if windows else value.split('/')
    path = Path(value)
    if (not path.is_absolute() or any(ord(c) < 32 or ord(c) == 127 for c in value)
            or any(c in ('.', '..') for c in components)):
        raise ValueError('television configuration must be an absolute directory without control characters or dot components')
    if os.name == 'nt':
        from file_platform import validate_windows_path
        validate_windows_path(path)
    return path


def leaf_config_directory(*, windows=None):
    """Leaf uses XDG/HOME on Unix and APPDATA on native Windows."""
    windows = os.name == 'nt' if windows is None else windows
    root = os.environ.get('APPDATA') if windows else (
        os.environ.get('XDG_CONFIG_HOME') or str(Path(os.environ.get('HOME') or Path.home()) / '.config'))
    value = os.environ.get('DOTS_APP_LEAF_CONFIG') or (root + '/leaf' if root else None)
    if value is None:
        return None
    components = value.replace('\\', '/').split('/') if windows else value.split('/')
    path = Path(value)
    if (not path.is_absolute() or any(ord(c) < 32 or ord(c) == 127 for c in value)
            or any(c in ('.', '..') for c in components)):
        raise ValueError('leaf configuration must be an absolute directory without control characters or dot components')
    if os.name == 'nt':
        from file_platform import validate_windows_path
        validate_windows_path(path)
    return path


def config_directory(app):
    if app == 'leaf':
        return leaf_config_directory(windows=True)
    if app == 'television':
        return television_config_directory(windows=True)
    if app == 'eza':
        return eza_config_directory(windows=True)
    home = Path(os.environ.get('HOME') or Path.home())
    roaming = Path(os.environ.get('APPDATA') or home / 'AppData/Roaming')
    local = Path(os.environ.get('LOCALAPPDATA') or home / 'AppData/Local')
    xdg = Path(os.environ.get('XDG_CONFIG_HOME') or home / '.config')
    defaults = {
        'lsd': (home / '.config/lsd', None),
        'bat': (roaming / 'bat', 'BAT_CONFIG_DIR'),
        'wttr': (xdg / 'wttr' if os.environ.get('XDG_CONFIG_HOME') else roaming / 'wttr', None),
        'alacritty': (roaming / 'alacritty', None),
        'clink': (local / 'clink', 'CLINK_PROFILE'),
        'fastfetch': (xdg / 'fastfetch', None),
        'glaze-wm': (home / '.glzr/glazewm', None),
        'komorebi': (home, 'KOMOREBI_CONFIG_HOME'),
        'tacky-borders': (home / '.config/tacky-borders', None),
        'wezterm': (xdg / 'wezterm', None),
        'whkd': (home / '.config', 'WHKD_CONFIG_HOME'),
        'yasb': (home / '.config/yasb', 'YASB_CONFIG_HOME'),
        'yazi': (roaming / 'yazi/config', 'YAZI_CONFIG_HOME'),
        'nushell': ((xdg / 'nushell') if os.environ.get('XDG_CONFIG_HOME') else roaming / 'nushell', None),
        'mpv': (roaming / 'mpv', 'MPV_HOME'),
        'vscode': (roaming / 'Code/User', None),
        'filepilot': (None, None),
        'wt': (None, None), 'winget': (None, None),
    }
    if app not in defaults:
        raise ValueError('unknown Windows application location: ' + app)
    default, variable = defaults[app]
    override = os.environ.get('DOTS_APP_' + app.upper().replace('-', '_') + '_CONFIG')
    value = override or (os.environ.get(variable) if variable else None)
    if value:
        path = Path(value)
        if not path.is_absolute() or any(ord(c) < 32 for c in value):
            raise ValueError('app configuration override must be an absolute directory: ' + app)
        return path
    variants = {
        'wt': [local / 'Packages/Microsoft.WindowsTerminal_8wekyb3d8bbwe/LocalState',
               local / 'Packages/Microsoft.WindowsTerminalPreview_8wekyb3d8bbwe/LocalState',
               local / 'Microsoft/Windows Terminal'],
        'winget': [local / 'Packages/Microsoft.DesktopAppInstaller_8wekyb3d8bbwe/LocalState',
                   local / 'Microsoft/WinGet/Settings'],
    }
    if app in variants:
        present = [p for p in variants[app] if p.is_dir()]
        # Never guess which installation the user wants to manage.
        return present[0] if len(present) == 1 else None
    return default


if __name__ == '__main__':
    import sys
    try:
        resolvers = {'eza': eza_config_directory, 'television': television_config_directory,
                     'leaf': leaf_config_directory}
        if len(sys.argv) != 2 or sys.argv[1] not in resolvers:
            raise ValueError('expected application: eza, television or leaf')
        result = resolvers[sys.argv[1]]()
        print(result if result is not None else '')
    except ValueError as exc:
        print('dots theme: ' + str(exc), file=sys.stderr)
        sys.exit(1)

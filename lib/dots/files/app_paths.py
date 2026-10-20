"""App-specific native Windows config locations; no app execution or writes."""
import os
from pathlib import Path


def config_directory(app):
    home = Path(os.environ.get('HOME') or Path.home())
    roaming = Path(os.environ.get('APPDATA') or home / 'AppData/Roaming')
    local = Path(os.environ.get('LOCALAPPDATA') or home / 'AppData/Local')
    xdg = Path(os.environ.get('XDG_CONFIG_HOME') or home / '.config')
    defaults = {
        'lsd': (home / '.config/lsd', None),
        'bat': (roaming / 'bat', 'BAT_CONFIG_DIR'),
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

"""Publish the rendered Dots color scheme into existing Windows Terminal settings."""
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / 'files'))
from app_paths import WT_EDITIONS
from file_platform import open_nofollow, state_root
from transactions import Store, digest, parents_safe
from themes.wt_scheme import rendered_scheme, upsert_scheme, upsert_terminal_theme

SCHEME_ARTIFACT = 'windows-terminal.json'
THEME_ARTIFACT = 'windows-terminal-theme.json'


def terminal_inputs(scheme_text, theme_text):
    """Decode the fragment and its separate Windows Terminal appearance template."""
    scheme = rendered_scheme(scheme_text)
    fragment = json.loads(theme_text)
    if not isinstance(fragment, dict) or fragment.get('theme') != 'dots':
        raise ValueError(THEME_ARTIFACT + ' must select the dots theme')
    themes = fragment.get('themes')
    if isinstance(themes, list):
        matches = [theme for theme in themes if isinstance(theme, dict) and theme.get('name') == 'dots']
        if len(matches) == 1:
            return scheme, matches[0]
    raise ValueError(THEME_ARTIFACT + ' must contain one theme named dots')


def discover_settings(*, env=None):
    env = os.environ if env is None else env
    home = Path(env.get('USERPROFILE') or env.get('HOME') or Path.home())
    local = Path(env.get('LOCALAPPDATA') or home / 'AppData/Local')
    scoop = Path(env.get('SCOOP') or home / 'scoop')
    directories = [local / suffix for suffix in WT_EDITIONS.values()]
    directories.append(local / 'Packages/Microsoft.WindowsTerminalCanary_8wekyb3d8bbwe/LocalState')
    directories.extend(scoop / 'persist' / app / 'settings'
                       for app in ('windows-terminal', 'windows-terminal-preview'))
    for key in ('WT_SETTINGS_DIR', 'DOTS_APP_WT_CONFIG'):
        if env.get(key):
            directories.append(Path(env[key]))
    paths = []
    for directory in dict.fromkeys(directories):
        path = directory / 'settings.json'
        # Surface malformed settings locations as per-target errors during sync.
        if path.is_absolute() and '..' not in path.parts:
            try:
                path.lstat()
            except FileNotFoundError:
                continue
            except (OSError, ValueError):
                pass  # Recheck and report the error for this target during sync.
        paths.append(path)
    return paths


def plan_settings_file(path, scheme, theme=None):
    """Return the input digest and optional text replacement for a transaction."""
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts or path.name != 'settings.json':
        raise ValueError('expected an absolute path to Terminal settings.json')
    parents_safe(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('expected a regular settings file')
    before = digest(path)
    flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0)
    with os.fdopen(open_nofollow(path, flags), 'rb') as stream:
        text = stream.read().decode('utf-8')
    updated = upsert_scheme(text, scheme)
    if theme is not None:
        updated = upsert_terminal_theme(updated, theme)
    if digest(path) != before:
        raise ValueError('settings changed while reading')
    op = None if updated == text else {'path': str(path), 'text': updated}
    return before, op


def sync_settings(scheme, *, theme=None, dry_run=False, env=None, state=None, guards=None, paths=None):
    """Return one outcome per target; changed files have an undoable transaction."""
    store = Store(state if state is not None else state_root(env))
    results = []
    targets = discover_settings(env=env) if paths is None else paths
    for path in targets:
        result = {'path': str(path)}
        try:
            before, op = plan_settings_file(path, scheme, theme)
            if op is None:
                result['status'] = 'unchanged'
            elif dry_run:
                result['status'] = 'would-update'
            else:
                expected = dict(guards or {})
                expected[str(path)] = before
                transaction = store.apply('theme-wt-settings', [op], expected, retain=True)
                result.update(status='updated', transaction=transaction['id'])
        except (OSError, ValueError) as exc:
            result.update(status='error', error=str(exc))
        results.append(result)
    return results

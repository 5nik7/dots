"""Lazy human CLI preferences; no writes, publication or shell evaluation."""
import os

VIEWS = ('default', 'short', 'verbose')
PROGRESS_MODES = ('none', 'spinner', 'bar', 'both')


def values(controls=None):
    if controls is None:
        from config_values import current
        from profile_config import checkout
        if not (checkout() / 'default/config.json').is_file(): return {}
        controls = current()
    return controls.values.get('apps', {})


def progress_mode():
    mode = os.environ.get('DOTS_PROGRESS', 'auto')
    if mode == 'never':
        return 'none'
    if mode == 'auto':
        try:
            mode = values().get('cli', {}).get('progress', 'both')
        except (OSError, ValueError, ImportError):
            return 'none'
    return mode if mode in PROGRESS_MODES else 'none'


def git_view(explicit=None, *, human=False, data=False):
    if data or not human and explicit is None:
        return None
    if explicit is not None:
        return explicit
    try: mode = values().get('git', {}).get('view', 'default')
    except (OSError, ValueError, ImportError): mode = 'default'
    return mode if mode in VIEWS else 'default'


def rows(controls):
    apps = values(controls)
    yield '__cli.progress', apps.get('cli', {}).get('progress', 'both'), 'literal'
    yield '__git.view', apps.get('git', {}).get('view', 'default'), 'literal'

"""Declarative built-in plugin installation assets; no plugin code is loaded."""
import json
from pathlib import Path, PurePosixPath
import re


def relative(value):
    if (not isinstance(value, str) or not value or '\\' in value or ':' in value
            or any(ord(char) < 32 for char in value)):
        raise ValueError('invalid plugin asset path')
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ('', '.', '..') for part in value.split('/')):
        raise ValueError('plugin assets must stay within their plugin')
    return value


def definitions(root):
    manifest = Path(root) / 'plugins/manifest.json'
    data = json.loads(manifest.read_text(encoding='utf-8'))
    if data.get('schema') != 1 or not isinstance(data.get('plugins'), dict):
        raise ValueError('unsupported plugin manifest')
    for name, row in data['plugins'].items():
        if not re.fullmatch('[a-z][a-z0-9-]*', name) or not isinstance(row, dict):
            raise ValueError('invalid plugin definition')
        for key in ('runtime', 'manual'):
            relative(row[key])
        if set(row['completions']) != {'bash', 'zsh', 'fish'}:
            raise ValueError('plugin completion assets are incomplete')
        for value in row['completions'].values():
            relative(value)
    return data['plugins']

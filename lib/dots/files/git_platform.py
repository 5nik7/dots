"""Bounded companion for the consolidated dots:git directory mapping."""
import os
from pathlib import Path
import re

from transactions import exists, parents_safe

PLATFORMS = ('termux', 'linux', 'wsl', 'windows')
IDENTITY = 'dots:git-platform'


def selector(root, row, platform, guard, entry_text=None):
    """Return (selector, overlay, unchanged), or None for other resource layouts.

    This is not a general permission to write inside directory-linked sources.
    Only the fixed Git source and its explicit gitplatform include opt in.
    """
    source = Path(root) / 'config/git'
    if (row['id'] != 'dots:git' or Path(row['source']) != source
            or row['strategy'] != 'directory-link' or not row['enabled'] or not row['applicable']):
        return None
    entry = source / 'config'
    parents_safe(entry)
    guard(entry)
    if not exists(entry):
        return None  # Older common-only layouts have no companion.
    if entry.is_symlink() or not entry.is_file() or entry.stat().st_size > 65536:
        raise ValueError('Git entry point must be a bounded regular file')
    if not re.search(r'(?m)^\s*path\s*=\s*gitplatform\s*$', entry.read_text() if entry_text is None else entry_text):
        return None
    if platform not in PLATFORMS:
        raise ValueError('unsupported Git platform')
    overlay = source / platform
    target = source / 'gitplatform'
    guard(overlay)
    guard(target)
    if overlay.is_symlink() or not overlay.is_file():
        raise ValueError('Git platform source must be a regular file: ' + str(overlay))
    if exists(target):
        if not target.is_symlink():
            raise ValueError('Git platform selector is occupied; preserve and review it')
        linked = Path(os.path.abspath(target.parent / os.readlink(target)))
        if linked not in [source / name for name in PLATFORMS]:
            raise ValueError('unrelated Git platform link is protected')
        return target, overlay, linked == overlay
    return target, overlay, False


def plan(installation, row, entry_text=None):
    selected = selector(installation.root, row, installation.platform, installation.guard, entry_text)
    if selected is None:
        return False
    target, overlay, same = selected
    owned = installation.entries.get(str(target))
    if owned and installation.guards[str(target)] != owned['after']:
        raise ValueError('installer-owned Git platform selector changed; preserve and review it')
    if same:
        installation.item(IDENTITY, 'unchanged', target, overlay)
    else:
        # The selector parser has bounded replacement to recognized platform links.
        installation.add(IDENTITY, target, link=overlay.name, managed=True)
        installation.items[-1]['source'] = str(overlay)
    installation.items[-1]['reason'] = 'Select the ' + installation.platform + ' Git overlay'
    return True

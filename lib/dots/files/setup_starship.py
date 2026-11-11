"""Prepare the saved Starship theme and its active link in the setup journal."""
import os
from pathlib import Path
import sys
from contextlib import contextmanager


@contextmanager
def coordinated_lock():
    """Serialize setup palette publication with Blastoff edits and switches."""
    from file_platform import state_root, lock, open_nofollow
    from transactions import private_directory
    directory = state_root()/'blastoff'
    private_directory(directory)
    descriptor = open_nofollow(directory/'operation.lock', os.O_RDWR | os.O_CREAT, 0o600)
    with os.fdopen(descriptor, 'a+b') as handle:
        try:
            lock(handle)
        except BlockingIOError as error:
            raise ValueError('another Blastoff or setup operation holds the palette lock; retry after it finishes') from error
        yield


def plan(installation):
    if 'blastoff' not in installation.components:
        return
    root = installation.root
    default = root/'config/blastoff/themes/dots.toml'
    if not default.is_file(): return  # Minimal catalog fixtures have no bundle.
    sys.path.insert(0, str(root/'lib/dots/themes'))
    from backup_catalog import physical as resolve_parent
    from starship import update_palette
    import tomllib
    home = Path(os.environ.get('HOME') or Path.home())
    active = resolve_parent(os.environ.get('STARSHIP_CONFIG') or home/'.config/starship.toml', installation.guards)
    logical_store = Path(os.environ.get('BLASTOFF_HOME') or home/'.config/blastoff').expanduser()
    # Account for a selected catalog link that has not been published yet.
    mapping = next((op for op in installation.operations if op['path'] == str(logical_store) and 'link' in op), None)
    storage = Path(mapping['link']) if mapping else resolve_parent(logical_store/'themes/dots.toml', installation.guards).parent.parent
    saved = storage/'themes/dots.toml'
    if active.is_relative_to(storage/'themes') or active.is_relative_to(storage/'modules'):
        raise ValueError('Starship active destination must be outside the saved library')
    if active.is_symlink():
        target = active.resolve()
        if target.parent == storage/'themes' and target.is_file() and not target.is_symlink():
            saved = target
    installation.guard(saved)
    original = saved.read_bytes() if saved.is_file() else default.read_bytes()
    installation.guard(default)
    # Reuse the prepared generation, or render privately when only Blastoff is
    # selected. No app hooks, prompt execution or current-pointer change.
    generation = getattr(installation, 'theme_payload', None)
    if generation is None and installation.theme:
        generation = installation.state/'themes/generations'/installation.theme['generation']
    if generation is not None and (generation/'blastoff.toml').is_file():
        installation.guard(generation/'blastoff.toml')
        rendered = (generation/'blastoff.toml').read_bytes()
    else:
        from palette_native import Themes
        # A full native render has no publication or application effects.
        import tempfile
        with tempfile.TemporaryDirectory(prefix='dots-setup-palette-') as temp:
            themes = Themes()
            themes.render(themes.current(), Path(temp), build_cache=False)
            rendered = (Path(temp)/'blastoff.toml').read_bytes()
    palette = tomllib.loads(rendered.decode('utf-8'))['palettes']['dots']
    updated = update_palette(original, palette)
    if saved.exists() and not saved.is_file(): raise ValueError('saved Starship theme must be a regular file')
    if updated != original or not saved.exists():
        installation.add('dots:blastoff:palette', saved, text=updated.decode('utf-8-sig'))
    installation.add('dots:blastoff:active', active, link=saved)

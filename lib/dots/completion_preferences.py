"""Read-only completion appearance projected as validated shell literals."""
from pathlib import Path
import sys

ROLES = ('candidate', 'command', 'option', 'value', 'branch', 'tag', 'remote',
         'description', 'heading', 'separator')
DEFAULTS = dict(candidate='foreground', command='blue', option='yellow', value='green',
                branch='magenta', tag='cyan', remote='blue', description='muted',
                heading='cyan', separator='muted')


def rows(root=None, selected=None, *, styles=None, controls=None):
    from style_config import Styles
    from config_values import Controls
    from files.file_platform import state_root
    styles = styles or Styles(root, selected)
    controls = controls or Controls(styles.root, styles.selected)
    yield '__completion.enabled', '1' if controls.values.get('apps', {}).get('completion', {}).get('enabled', True) else '0', 'literal'
    for role in ROLES:
        yield '__completion.color.'+role, styles.sgr(role, dict(fg=DEFAULTS[role]), app='completion'), 'style'
    # Watch exact inputs and parent directories: creating an absent override
    # must invalidate the in-memory projection too. No directory enumeration.
    paths = {*styles.paths, *controls.paths, Path(__file__)}
    paths.update(Path(layer['root'])/'profile.json' for layer in styles.selected['layers'])
    paths.add(state_root()/'current/theme/palette.json')
    paths.update(path.parent for path in tuple(paths))
    for path in sorted(paths):
        if any(ord(c) < 32 or ord(c) == 127 for c in str(path)):
            yield '__completion.watch.hex', str(path).encode().hex(), 'path'
        else:
            yield '__completion.watch', str(path), 'path'


if __name__ == '__main__':
    try:
        # Construct completely before writing: invalid inputs cannot yield a
        # partial replacement for a running shell's last-good preferences.
        result = list(rows())
        print('\n'.join('\t'.join(row) for row in result))
    except (OSError, ValueError, KeyError, TypeError):
        sys.exit(1)

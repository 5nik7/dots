"""Names exposed from a published generation to profile mappings and inspection."""
from pathlib import PurePosixPath

# These are publication internals, never browsable content or completion operands.
INTERNAL = {'id', 'selection', 'fingerprint', 'previous', 'previous-active', 'status',
            'connectors', 'commands', 'commands-old', 'commands-new', 'active.new'}


def identifier(value):
    p = PurePosixPath(value)
    if (not value or any(ord(c) < 32 or ord(c) == 127 for c in value)
            or ':' in value or '\\' in value or p.is_absolute()
            or any(x in ('', '.', '..') for x in value.split('/'))
            or p.parts[0] in INTERNAL or p.parts[0].startswith('.') or len(p.parts) > 2):
        raise ValueError('expected a listed generation-relative file identifier')
    return value

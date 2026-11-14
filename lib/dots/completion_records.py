"""Private semantic metadata for trusted completion providers; never ANSI."""
import os


def requested():
    # Set locally by the dispatcher for its private Zsh request. Native Python
    # callers keep their default three-field API without consulting this flag.
    return os.environ.get('_DOTS_COMPLETION_DISPLAY_TYPES') == '1'


def candidate_record(value, description='', role='value', *, display_types=False):
    record = ('candidate', value, description)
    return record + (role,) if display_types else record

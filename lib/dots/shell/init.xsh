# Keep the native source bridge small. The existing interpreter loads ordinary Python.
import os as _dots_os
import sys as _dots_sys
_dots_lib = _dots_os.path.join($DOTS, 'lib', 'dots')
if not _dots_sys.path or _dots_sys.path[0] != _dots_lib:
    _dots_sys.path.insert(0, _dots_lib)
from shell.xonsh_integration import initialize as _dots_initialize
_dots_profile_shells = _dots_initialize(__xonsh__, events)
del _dots_lib, _dots_initialize

# __file__ is supplied both by native rc startup and by source.
import os as _dots_os
_dots_file = _dots_os.path.realpath(__file__, strict=True)
_dots_directory = _dots_os.path.dirname(_dots_file)
if not _dots_os.path.isfile(_dots_os.path.join(_dots_directory, '../../bin/dots')):
    raise RuntimeError('dots: Xonsh startup requires the Dots checkout layout')
$DOTS = _dots_os.path.dirname(_dots_os.path.dirname(_dots_directory))
source @($DOTS + '/lib/dots/shell/init.xsh')
if $XONSH_INTERACTIVE:
    for _dots_hook_dir in _dots_profile_shells:
        _dots_hook = _dots_os.path.join(_dots_hook_dir, 'init.xsh')
        if _dots_os.path.isfile(_dots_hook):
            source @(_dots_hook)
    from shell.xonsh_tools import activate as _dots_load_xonsh_tools
    _dots_load_xonsh_tools(__xonsh__, events)
    del _dots_load_xonsh_tools
    source @($DOTS + '/shells/xonsh/interactive.xsh')
    for _dots_hook_dir in _dots_profile_shells:
        _dots_hook = _dots_os.path.join(_dots_hook_dir, 'local.xsh')
        if _dots_os.path.isfile(_dots_hook):
            source @(_dots_hook)

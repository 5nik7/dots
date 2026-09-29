# __file__ is supplied both by native rc startup and by source.
import os as _dots_os
_dots_file = _dots_os.path.realpath(__file__, strict=True)
_dots_directory = _dots_os.path.dirname(_dots_file)
if not _dots_os.path.isfile(_dots_os.path.join(_dots_directory, '../../bin/dots')):
    raise RuntimeError('dots: Xonsh startup requires the Dots checkout layout')
source @(_dots_os.path.join(_dots_directory, 'environment.xsh'))
if $XONSH_INTERACTIVE:
    source @($DOTS + '/shells/xonsh/interactive.xsh')

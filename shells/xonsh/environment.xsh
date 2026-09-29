# __file__ is supplied both by native rc startup and by source.
import os as _dots_os
_dots_file = _dots_os.path.realpath(__file__, strict=True)
_dots_directory = _dots_os.path.dirname(_dots_file)
if not _dots_os.path.isfile(_dots_os.path.join(_dots_directory, '../../bin/dots')):
    raise RuntimeError('dots: Xonsh startup requires the Dots checkout layout')
$DOTS = _dots_os.path.dirname(_dots_os.path.dirname(_dots_directory))
$DOTBIN = _dots_os.path.join($DOTS, 'bin')
$DOTSCRIPTS = _dots_os.path.join($DOTS, 'scripts')
$DOTFILES = _dots_os.path.join($DOTS, 'config')
$DOTCONFIG = $DOTFILES
$DOTSHHHH = _dots_os.path.join($DOTS, 'secrets')
$SHELLS = _dots_os.path.join($DOTS, 'shells')
$ZSH = _dots_os.path.join($DOTS, 'shells/zsh')
$PWSH = _dots_os.path.join($DOTS, 'shells/powershell')
for _dots_directory in ($DOTBIN, $DOTSCRIPTS):
    if _dots_os.path.isdir(_dots_directory) and _dots_directory not in $PATH:
        $PATH.insert(0, _dots_directory)

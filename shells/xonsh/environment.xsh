# __file__ is supplied both by native rc startup and by source.
import os as _dots_os
_dots_file = _dots_os.path.realpath(__file__, strict=True)
_dots_directory = _dots_os.path.dirname(_dots_file)
if not _dots_os.path.isfile(_dots_os.path.join(_dots_directory, '../../bin/dots')):
    raise RuntimeError('dots: Xonsh startup requires the Dots checkout layout')
$DOTS = _dots_os.path.dirname(_dots_os.path.dirname(_dots_directory))
source @($DOTS + '/lib/dots/shell/init.xsh')

# Only paths formerly exported by Dots are retired.
for _dots_starship_root in [__xonsh__.env.get('DOTFILES', ''), __xonsh__.env.get('DOTCONFIG', ''), *[_dots_os.path.join(base, directory) for base in [$DOTS, _dots_os.path.join($HOME, 'dots'), _dots_os.path.join($HOME, '.dots')] for directory in ['config', 'configs']]]:
    if _dots_starship_root and __xonsh__.env.get('STARSHIP_CONFIG') == _dots_os.path.join(_dots_starship_root, 'starship', 'starship.toml'):
        __xonsh__.env.pop('STARSHIP_CONFIG', None)
        break

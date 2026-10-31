__xonsh__.env.pop('DOTRUBY', None)
__xonsh__.env.pop('RUBYCOMP', None)
# Dots integration only; Xonsh's own rc retains personal configuration.
from pathlib import Path as _DotsPath
import importlib.util as _dots_import
_dots_spec = _dots_import.spec_from_file_location('_dots_runtime', str(_DotsPath($DOTS) / 'lib/dots/shell/runtime.py'))
_dots_runtime = _dots_import.module_from_spec(_dots_spec)
exec(compile((_DotsPath($DOTS) / 'lib/dots/shell/runtime.py').read_text(), _dots_spec.origin, 'exec'), _dots_runtime.__dict__)
# Use Xonsh's Python runtime; no subprocess or shell-code evaluation.
import sys as _dots_sys
_dots_sys.path.insert(0, str(_DotsPath($DOTS) / 'lib/dots'))
from native_environment import document as _dots_document
from less_style import apply as _dots_less_style
_dots_profile_document = _dots_document(_DotsPath($DOTS), __xonsh__.env.detype())
_dots_profile_environment = _dots_profile_document['exports']
for _dots_key in _dots_profile_document['unset']:
    __xonsh__.env.pop(_dots_key, None)
for _dots_key in __xonsh__.ctx.get('_dots_profile_map_names', []):
    __xonsh__.ctx.pop(_dots_key, None)
__xonsh__.ctx.update(_dots_profile_document['maps'])
__xonsh__.ctx['_dots_profile_map_names'] = list(_dots_profile_document['maps'])
__xonsh__.env['PATH'] = _dots_profile_environment['PATH'].split(__import__('os').pathsep)
for _dots_key, _dots_value in _dots_profile_environment.items():
    if _dots_key != 'PATH' and (_dots_key in _dots_profile_document['generated'] or _dots_key.startswith('DOTS_') or not __xonsh__.env.get(_dots_key)):
        __xonsh__.env[_dots_key] = _dots_value

dots_options, dots_option_sources, _dots_config = _dots_runtime.settings($DOTS, __xonsh__.env)
dot = {}
for _dots_line in (_DotsPath($DOTS) / 'lib/dots/shell/paths.tsv').read_text().splitlines():
    _dots_variable, _dots_key, _dots_relative = _dots_line.split('\t')
    _dots_value = str(_DotsPath($DOTS) / _dots_relative)
    if _dots_variable != '-':
        __xonsh__.env[_dots_variable] = _dots_value
    if _dots_key != '-':
        dot[_dots_key] = _dots_value
dot['config'] = _dots_config
dot['state'] = str(_DotsPath(__xonsh__.env.get('XDG_STATE_HOME') or _DotsPath($HOME) / '.local/state') / 'dots')
$THEMESCMD = str(_DotsPath(dot['bin']) / 'theme')
$THEMESBIN = str(_DotsPath(dot['state']) / 'themes/commands/current/bin')
$PATH = [p for p in $PATH if p not in (str(_DotsPath($DOTS) / 'themes/bin'), $THEMESBIN)]
for _dots_directory in ($DOTBIN, $DOTSCRIPTS):
    if _DotsPath(_dots_directory).is_dir() and _dots_directory not in $PATH:
        $PATH.insert(0, _dots_directory)
if dots_options['DOTS_INIT_COMMANDS'] == '1':
    $PATH.append($THEMESBIN)
if $XONSH_INTERACTIVE:
    esc = ESC = '\x1b'
    rst = RST = '\x1b[0m'
    if dots_options['DOTS_INIT_COLORS'] == '0':
        for _dots_name in __xonsh__.ctx.get('_dots_color_names', []):
            __xonsh__.ctx.pop(_dots_name, None)
        __xonsh__.ctx['_dots_color_names'] = []
    _dots_generation = None
    def _dots_refresh_theme(**kwargs):
        global _dots_generation
        if dots_options['DOTS_INIT_THEME'] != '1':
            _dots_less_style(__xonsh__.env, {}, enabled=False)
            return
        try:
            marker = _DotsPath(dot['state']) / 'themes/current'
            if not marker.exists() or marker.read_text().strip() == _dots_generation:
                return
            result = _dots_runtime.palette(dot['state'])
            if result is None:
                return
            generation, data = result
        except (OSError, ValueError):
            return
        ctx = __xonsh__.ctx
        _dots_less_style(__xonsh__.env, {name: value['hex'] for name, value in data.items() if 'hex' in value}, mode=dots_options['DOTS_COLOR'])
        for name in ctx.get('_dots_color_names', []):
            ctx.pop(name, None)
        names = []
        if dots_options['DOTS_INIT_COLORS'] == '1':
            for name, value in data.items():
                if not name.startswith('@'):
                    ctx[name] = value
                    names.append(name)
        ctx['_dots_color_names'] = names
        ctx['dots_palette'], ctx['dots_roles'] = data['@palette'], data['@role']
        $THEME, $FLAVOR, $DOTS_THEME_ID = data['@theme']['family'], data['@theme']['flavor'], data['@theme']['id']
        dot['theme'] = $DOTS_THEME_ID
        ls_file = _DotsPath(dot['state']) / 'themes/generations' / generation / 'ls_colors'
        if ls_file.is_file():
            $LS_COLORS = ls_file.read_text().rstrip('\r\n')
        visual_file = _DotsPath(dot['state']) / 'themes/generations' / generation / 'visual.tsv'
        if visual_file.is_file():
            visual = {}
            for line in visual_file.read_text().splitlines():
                kind, key, value = line.split('\t', 2)
                if kind == 'env':
                    if not __import__('re').fullmatch('[A-Z][A-Z0-9_]*', key):
                        return
                    visual[key] = value
            __xonsh__.env.update(visual)
            if 'DOTS_THEME_FZF_COLORS' in visual:
                if '_dots_visual_fzf_base' not in ctx:
                    ctx['_dots_visual_fzf_base'] = __xonsh__.env.get('FZF_DEFAULT_OPTS', '')
                __xonsh__.env['FZF_DEFAULT_OPTS'] = visual.get('DOTS_THEME_FZF_OPTS', ctx['_dots_visual_fzf_base']) + ' --color=' + visual['DOTS_THEME_FZF_COLORS']
        _dots_generation = generation
    _dots_refresh_theme()
    if '_dots_prompt_handler' in __xonsh__.ctx:
        events.on_pre_prompt.discard(__xonsh__.ctx['_dots_prompt_handler'])
    def _dots_prompt_handler(**kwargs):
        if dots_options['DOTS_THEME_AUTO_UPDATE'] == '1':
            _dots_refresh_theme()
    events.on_pre_prompt(_dots_prompt_handler)
    from xonsh.completers.tools import contextual_command_completer as _dots_contextual
    from xonsh.completers.completer import add_one_completer as _dots_add_completer
    import subprocess as _dots_subprocess
    @_dots_contextual
    def _dots_complete(context):
        if dots_options['DOTS_INIT_COMPLETION'] != '1' or context.arg_index < 1:
            return None
        names = _DotsPath(dot['state']) / 'themes/commands/current/names'
        families = names.read_text().splitlines() if names.is_file() else []
        if context.command not in ['dots', 'theme', *families]:
            return None
        words = [arg.value for arg in context.args[:context.arg_index]] + [context.prefix]
        result = _dots_subprocess.run([str(_DotsPath($DOTS) / 'bin/dots'), '__complete', 'bash',
                                      str(context.arg_index), '--', *words],
                                     capture_output=True, text=True, env=__xonsh__.env.detype(), timeout=5)
        return {line.split('\t')[1] for line in result.stdout.splitlines() if line.startswith('candidate\t')}
    __xonsh__.completers.pop('dots', None)
    _dots_add_completer('dots', _dots_complete, 'start')


_dots_profile_paths = [p for p in _dots_profile_environment['DOTS_PROFILE_PATHS'].split(__import__('os').pathsep) if p]
__xonsh__.env['PATH'] = list(dict.fromkeys(_dots_profile_paths + list(__xonsh__.env['PATH'])))

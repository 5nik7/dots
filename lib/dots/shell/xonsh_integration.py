"""Native Xonsh state and hooks, using the shell's Python interpreter."""
import json
import os
from pathlib import Path
import sys

from native_completion import environment


def initialize(session, events):
    env, ctx = session.env, session.ctx
    root = Path(env['DOTS'])
    env.pop('DOTRUBY', None)
    env.pop('RUBYCOMP', None)
    document = environment(root, env.detype())
    exports = document['exports']
    for name in document['unset']:
        env.pop(name, None)
    for name in ctx.get('_dots_profile_map_names', ()):
        ctx.pop(name, None)
    ctx.update(document['maps'])
    ctx['_dots_profile_map_names'] = list(document['maps'])
    for key, value in exports.items():
        if key == 'PATH':
            continue
        if (key in document['generated'] or key.startswith('DOTS_') or not env.get(key)
                or (key == 'MANPATH' and exports['DOTS_PLATFORM'] != 'windows')):
            env[key] = value

    settings = document['settings']
    ctx['dots_options'] = settings['values']
    ctx['dots_option_sources'] = settings['origins']
    dot = ctx['dot'] = {}
    for line in (root/'lib/dots/shell/paths.tsv').read_text(encoding='utf-8').splitlines():
        variable, key, relative = line.split('\t')
        path = str(root/relative)
        if variable != '-':
            env[variable] = path
        if key != '-':
            dot[key] = path
    dot.update(config=settings['path'], state=document['shell_paths']['state'])
    state = Path(dot['state'])
    env['THEME'] = str(state/'current/theme')
    env['THEMESCMD'] = document['shell_paths']['theme_command']
    env['THEMESBIN'] = str(state/'themes/commands/current/bin')
    link = [sys.executable, '-B', str(root/'lib/dots/link_cli.py')]
    owned = [path for path in (env['DOTBIN'], env['DOTSCRIPTS']) if Path(path).is_dir()]
    if ctx['dots_options']['DOTS_INIT_COMMANDS'] == '1':
        owned.append(env['THEMESBIN'])
        session.aliases['.ln'] = link
    elif session.aliases.get('.ln') == link:
        del session.aliases['.ln']
    profile = [path for path in exports['DOTS_PROFILE_PATHS'].split(os.pathsep) if path]
    retired = {str(root/'themes/bin'), env['THEMESBIN']}
    inherited = [path for path in exports['PATH'].split(os.pathsep) if path not in retired]
    env['PATH'] = list(dict.fromkeys([*owned, *profile, *inherited]))
    if env.get('XONSH_INTERACTIVE'):
        register_interactive(session, events, root, state, document['completion_commands'])
    return document['shell_paths']['profile_shells']


def register_interactive(session, events, root, state, commands):
    from less_style import apply
    from shell.runtime import palette
    from xonsh.completers.tools import contextual_command_completer
    from xonsh.completers.completer import add_one_completer

    env, ctx = session.env, session.ctx
    if 'FZF_DEFAULT_OPTS' not in env and 'FZF_DEFAULT_OPTS_FILE' not in env:
        env['FZF_DEFAULT_OPTS'] = "--bind=ctrl-x:toggle-preview --preview-window=right:hidden:50% --preview='_dots-fzf-preview --selection {f}'"
        ctx['_dots_visual_fzf_base'] = env['FZF_DEFAULT_OPTS']
    ctx.update(esc='\x1b', ESC='\x1b', rst='\x1b[0m', RST='\x1b[0m')
    if ctx['dots_options']['DOTS_INIT_COLORS'] == '0':
        for name in ctx.pop('_dots_color_names', ()):
            ctx.pop(name, None)

    loaded = None

    def refresh_theme(**kwargs):
        nonlocal loaded
        options = ctx['dots_options']
        if options['DOTS_INIT_THEME'] != '1':
            apply(env, {}, enabled=False)
            return
        try:
            marker = state/'themes/current'
            if not marker.is_file() or marker.read_text(encoding='utf-8').strip() == loaded:
                return
            result = palette(state)
            if result is None:
                return
            generation, data = result
        except (OSError, ValueError):
            return
        apply(env, {name: value['hex'] for name, value in data.items() if 'hex' in value},
              mode=options['DOTS_COLOR'])
        for name in ctx.get('_dots_color_names', ()):
            ctx.pop(name, None)
        colors = {name: value for name, value in data.items() if not name.startswith('@')
                  and options['DOTS_INIT_COLORS'] == '1'}
        ctx.update(colors)
        ctx['_dots_color_names'] = list(colors)
        ctx.update(dots_palette=data['@palette'], dots_roles=data['@role'])
        identity = data['@theme']
        env.update(DOTS_THEME_FAMILY=identity['family'], FLAVOR=identity['flavor'], DOTS_THEME_ID=identity['id'])
        ctx['dot']['theme'] = identity['id']
        directory = state/'themes/generations'/generation
        ls_file = directory/'ls_colors'
        if ls_file.is_file():
            env['LS_COLORS'] = ls_file.read_text(encoding='utf-8').rstrip('\r\n')
        visual_file = directory/'visual.tsv'
        if visual_file.is_file():
            import re
            visual = {}
            for line in visual_file.read_text(encoding='utf-8').splitlines():
                kind, key, value = line.split('\t', 2)
                if kind == 'env':
                    if not re.fullmatch('[A-Z][A-Z0-9_]*', key):
                        return
                    visual[key] = value
            env.update(visual)
            if 'DOTS_THEME_FZF_COLORS' in visual and '_dots_visual_fzf_base' in ctx and 'FZF_DEFAULT_OPTS_FILE' not in env:
                base = visual.get('DOTS_THEME_FZF_OPTS', ctx['_dots_visual_fzf_base'])
                if visual.get('DOTS_THEME_FZF_PREVIEW') == '0':
                    base += " --preview='_dots-fzf-preview --selection {f}'"
                env['FZF_DEFAULT_OPTS'] = base + ' --color=' + visual['DOTS_THEME_FZF_COLORS']
        loaded = generation

    def prompt(**kwargs):
        if ctx['dots_options']['DOTS_THEME_AUTO_UPDATE'] == '1':
            refresh_theme()

    @contextual_command_completer
    def complete(context):
        if ctx['dots_options']['DOTS_INIT_COMPLETION'] != '1' or context.arg_index < 1:
            return None
        names = state/'themes/commands/current/names'
        families = names.read_text(encoding='utf-8').splitlines() if names.is_file() else ()
        command = Path(context.command).name
        if os.name == 'nt':
            command = command.casefold()
        command = command.removesuffix('.ps1')
        if command not in commands and command not in families:
            return None
        import subprocess
        words = [arg.value for arg in context.args[:context.arg_index]] + [context.prefix]
        result = subprocess.run([sys.executable, '-B', str(root/'lib/dots/native_completion.py'),
                                 '--complete', 'xonsh', *words],
                                capture_output=True, encoding='utf-8', env=env.detype(), timeout=5)
        return {row['value'] for row in (json.loads(result.stdout) or [])} if result.returncode == 0 else set()

    refresh_theme()
    if '_dots_prompt_handler' in ctx:
        events.on_pre_prompt.discard(ctx['_dots_prompt_handler'])
    ctx.update(_dots_refresh_theme=refresh_theme, _dots_prompt_handler=prompt)
    events.on_pre_prompt(prompt)
    session.completers.pop('dots', None)
    add_one_completer('dots', complete, 'start')

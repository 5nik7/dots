"""Data-only schema shared by the Codex worker and toast Config bindings."""
import re

FIELDS = dict(fg='toast_foreground', bg='toast_background',
              position='toast_gravity', short='toast_short', bg_opacity='toast_background_opacity')
DEFAULTS = dict(fg='warning', bg='dark_background', position='middle', short=False, bg_opacity=100)
ACTIVATION = 'next cycle of an updated Codex alert worker (within five seconds); Termux delivery only'
KEYS = tuple('apps.codex.toast.'+key for key in FIELDS)


def validate(field, value):
    if field not in FIELDS: raise ValueError('unknown Codex toast field')
    if field == 'short':
        if type(value) is not bool: raise ValueError('toast short requires true or false')
    elif field == 'position':
        if value not in ('top', 'middle', 'bottom'): raise ValueError('toast position requires top, middle or bottom')
    elif field == 'bg_opacity':
        if type(value) is not int or not 0<=value<=100: raise ValueError('toast bg_opacity requires an integer 0..100 percent')
    elif not isinstance(value, str) or len(value)>128 or not re.fullmatch(
            r'#[0-9a-fA-F]{6}|(?!default$|reset$)[a-z_]+|palette\.[A-Za-z0-9_-]+|colors\.(?!apps\.)[a-z][a-z0-9_.]*\.(?:fg|bg)', value):
        raise ValueError('toast color requires a palette role, palette.NAME, global colors.ROLE.fg/bg or #RRGGBB')


def values(options):
    result = {key: options.get(native, DEFAULTS[key]) for key, native in FIELDS.items()}
    for key, value in result.items(): validate(key, value)
    return result


def constraints(key):
    field=key.removeprefix('apps.codex.toast.')
    if field not in FIELDS: return {}
    result=dict(default=DEFAULTS[field])
    if field=='short': result.update(type='boolean', choices=[True, False])
    elif field=='position': result.update(type='string', choices=['top','middle','bottom'])
    elif field=='bg_opacity': result.update(type='integer', examples=[0,25,50,75,100], syntax='Integer 0..100 percent; 0 is transparent, 100 is opaque')
    else: result.update(type='color', examples=['warning','dark_background','#89b4fa'],
                        syntax='Published palette role, palette.NAME, global colors.ROLE.fg/bg or #RRGGBB')
    return result


def background(rgb, opacity):
    """Android's alpha comes before RGB; retain the existing opaque argument."""
    validate('bg_opacity',opacity)
    return rgb if opacity==100 else '#'+format((255*opacity+50)//100,'02x')+rgb[1:]


def color(value, palette, root, fallback):
    if re.fullmatch('#[0-9a-fA-F]{6}', value): return value
    if value.startswith(('colors.', 'palette.')):
        try:
            from style_config import Styles
            value=Styles(root, palette=palette).color(value)
        except (OSError, ValueError, KeyError, TypeError): return fallback
    else:
        colors=palette.get('colors', {}) if isinstance(palette,dict) else {}
        value=colors.get(value) if isinstance(colors,dict) else None
    return value if isinstance(value,str) and re.fullmatch('#[0-9a-fA-F]{6}', value) else fallback

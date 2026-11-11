"""Supported visual bindings, shared by editing, discovery and publication."""
from functools import lru_cache
from pathlib import Path

APPS = ('cli', 'tmux', 'yazi', 'fzf', 'gum', 'starship', 'gitmux', 'nvim', 'wttr')
ATTRIBUTES = ('bold', 'dim', 'italic', 'underline', 'reverse', 'strikethrough')
ALIASES = {'navigation.codex': 'applications.codex'}
TODO = ('status.open', 'status.doing', 'status.blocked', 'status.done', 'status.removed',
        'priority.high', 'priority.normal', 'priority.low')
TODO_FIELDS=('id','alias','title','notes','tags','status','priority','due','parent','acceptance','subgoal_id','subgoal_title','subgoals','created','updated','completed','removed')
FONTS = ('heading','label','identity','version','source','face','glyph')
CLIPBOARD = ('heading','label','identity','text','source','timestamp','pinned','error')
WIKI = ('heading','label','page','section','snippet','url')
PKGS = ('heading','label','identity','package','version','value','count','muted','skipped',
        'success','warning','error','progress','spinner','preview.heading','preview.label',
        'preview.success','preview.warning','preview.version')
TMUX = ('window.active', 'window.inactive', 'window.attention', 'pane.active_border', 'pane.inactive_border')


def canonical(name):
    return ALIASES.get(name, name)


@lru_cache(maxsize=1)
def icon_roles():
    # The shipped defaults declare the public icon vocabulary; profile-only
    # unknown entries remain readable without becoming advertised controls.
    from style_config import read
    return {canonical(name) for name in read(Path(__file__).resolve().parents[2]/'default/icons.toml')
            if not name.startswith('apps.')}


def split(name):
    if name.startswith('apps.'):
        _, app, name = name.split('.', 2)
        return app, name
    return None, name


@lru_cache(maxsize=8192)
def fields(role, app):
    """Only fields actually consumed by each native adapter are editable."""
    if app == 'cli':
        if role in ('pkgs.'+name for name in PKGS): return ('fg','bg',*ATTRIBUTES)
        if role in ('clipboard.'+name for name in CLIPBOARD): return ('fg','bg',*ATTRIBUTES)
        if role in ('wiki.'+name for name in WIKI): return ('fg','bg',*ATTRIBUTES)
        if role in ('fonts.'+name for name in FONTS): return ('fg','bg',*ATTRIBUTES)
        if role.startswith('icons.') and role[6:] in icon_roles():return ('fg','bg',*ATTRIBUTES)
        if role in ('menu.icon','menu.label','menu.description','menu.shortcut','menu.state') or role in ('todo.field.'+name+'.'+kind for name in TODO_FIELDS for kind in ('label','value')):
            return ('fg','bg',*ATTRIBUTES)
        if role in ('ui.border', 'ui.cursor', 'ui.match', 'ui.separator'): return ()
        if role in ('ui.foreground','ui.muted','ui.accent','ui.heading','ui.label','status.error','status.success','status.warning') or role in ['todo.'+x for x in TODO]:
            return ('fg', 'bg', *ATTRIBUTES)
    if app == 'wttr':
        return ('fg',) if role in ('daylight.sunrise','daylight.sunset') else ()
    if app == 'tmux':
        from tmux_controls import ROLES
        if role=='git':return ('bg',)
        if role in ROLES or role=='session':return ('fg','bg',*ATTRIBUTES)
        if role in ('daylight.day','daylight.night','battery.critical','battery.low','battery.normal','battery.charging','battery.unknown'):return ('fg',)
        if role in ('status.working','status.waiting') or role.startswith(('icons.status.working','icons.status.waiting')):return ('fg','bg',*ATTRIBUTES)
        if role in TMUX:
            return ('fg',) if role.startswith('pane.') else ('fg', 'bg')
        return {'ui.foreground': ('fg',), 'ui.muted': ('fg',), 'ui.accent': ('fg',),
                'ui.selection': ('bg',), 'ui.heading': ('fg',), 'ui.border': ('fg',),
                'ui.separator': ('fg',), 'status.warning': ('fg',)}.get(role, ())
    if app == 'yazi': return ('fg',) if role == 'ui.accent' else ()
    if app == 'fzf':
        return {'ui.selection': ('bg',), 'ui.accent': ('fg',), 'ui.muted': ('fg',),
                'ui.heading': ('fg',), 'status.warning': ('fg',), 'status.info': ('fg',),
                'ui.border': ('fg',), 'ui.cursor': ('fg',), 'ui.match': ('fg',),
                'ui.separator': ('fg',)}.get(role, ())
    if app == 'gum':
        return {'ui.foreground': ('fg',), 'ui.accent': ('fg',), 'ui.selection': ('bg',),
                'ui.muted': ('fg',), 'ui.border': ('fg',), 'ui.cursor': ('fg',),
                'ui.match': ('fg',)}.get(role, ())
    return ()


@lru_cache(maxsize=8192)
def consumers(group, name):
    from config_keys import internal
    name=internal(group+'.'+name).partition('.')[2]
    app, base = split(name)
    base = canonical(base)
    if group == 'icons':
        from tmux_controls import ICONS
        if app=='tmux' and base in ICONS:return ['tmux']
        if base not in icon_roles(): return []
        apps = [] if base in ('menu.profiles','menu.themes') else ['cli']
        if base.startswith('files.'): apps += ['yazi']
        if base.startswith('git.'): apps += ['yazi', 'gitmux', 'starship']
        if base.startswith('hosts.') or base in ('git.repository','applications.codex', 'status.working', 'status.waiting', 'status.todo', 'navigation.separator'):
            apps += ['tmux']
    else:
        role, _, field = base.rpartition('.')
        apps = [consumer for consumer in APPS if field in fields(role, consumer)]
    return [a for a in APPS if a in apps and (not app or a == app)]


def supported(group, name):
    return bool(consumers(group, name))


def constraints(group,name):
    if group=='icons':return dict(type='string',syntax='Up to 64 printable characters; empty hides the icon; reset inherits')
    if name.rsplit('.',1)[-1] in ATTRIBUTES:return dict(type='boolean',choices=[True,False],syntax='Reset a profile override to inherit')
    return dict(type='color',syntax='Semantic role, #RRGGBB, palette.NAME or global colors.ROLE.fg/bg reference; reset inherits')


def known_keys(group,styles):
    result=set(styles.values[group])
    from tmux_controls import ROLES,ICONS
    if group=='icons':result.update('apps.tmux.'+key for key in ICONS)
    else:
        result.update('apps.tmux.'+role+'.'+field for role in ROLES for field in ('fg','bg',*ATTRIBUTES))
        result.add('apps.tmux.git.bg')
    if group=='icons':bases=icon_roles()
    else:
        roles=({split(key)[1].rsplit('.',1)[0] for key in result}|{'icons.'+key for key in icon_roles()}|
               {'todo.field.'+name+'.'+kind for name in TODO_FIELDS for kind in ('label','value')}|
               {'fonts.'+name for name in FONTS}|
               {'clipboard.'+name for name in CLIPBOARD}|
               {'wiki.'+name for name in WIKI}|
               {'pkgs.'+name for name in PKGS}|
               {'menu.'+name for name in ('icon','label','description','shortcut','state')})
        shared={key.rsplit('.',1)[0] for key in styles.values['colors'] if not key.startswith('apps.')}
        roles={role for role in roles if role not in ROLES or role in shared or role in TMUX}
        bases={role+'.'+field for role in roles for app in APPS for field in fields(role,app)}
    result.update(bases)
    for key in bases:
        result.update('apps.'+app+'.'+key for app in consumers(group,key))
    return result

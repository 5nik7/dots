"""Canonical public configuration paths and bounded legacy translations.

Native adapters keep their own vocabulary. These translations are data only;
they are also used by migration, discovery and the existing consumer readers.
"""
import copy

FEATURES = ('todo', 'fonts', 'wiki', 'menu')
MOVES = (
    ('apps.menu.popup.colors.preview-border', 'colors.apps.menu.popup.preview.border.fg'),
    ('apps.menu.popup.colors.preview-label', 'colors.apps.menu.popup.preview.label.fg'),
    ('apps.menu.popup.colors.preview-fg', 'colors.apps.menu.popup.preview.fg'),
    ('apps.menu.popup.colors.preview-bg', 'colors.apps.menu.popup.preview.bg'),
    ('apps.menu.popup.colors.border', 'colors.apps.menu.popup.border.fg'),
    ('apps.menu.popup.colors.label', 'colors.apps.menu.popup.label.fg'),
    ('apps.menu.popup.colors.fg', 'colors.apps.menu.popup.body.fg'),
    ('apps.menu.popup.colors.bg', 'colors.apps.menu.popup.body.bg'),
    ('formatting.apps.menu.entries', 'colors.apps.menu.entries'),
    *((f'apps.menu.popup.{field}', f'formatting.apps.menu.popup.{field}')
      for field in ('position', 'width', 'height', 'border')),
    *((f'apps.fonts.preview.{field}', f'formatting.apps.fonts.preview.{field}')
      for field in ('position', 'size', 'wrap')),
)


def under(key, prefix):
    return key == prefix or key.startswith(prefix+'.') or key.startswith(prefix+'[')


def canonical(key):
    for old, new in MOVES:
        if under(key, old): return new+key[len(old):]
    for feature in FEATURES:
        for old in ('colors.apps.cli.'+feature, 'colors.'+feature):
            if under(key, old): return 'colors.apps.'+feature+key[len(old):]
    for old,new in (('colors.apps.tmux.window.attention','colors.apps.tmux.windows.alert'),
                    ('colors.apps.tmux.window','colors.apps.tmux.windows')):
        if under(key,old):return new+key[len(old):]
    return key


def internal(key):
    """Resolve a public path to the existing owning controller's vocabulary."""
    for old, new in MOVES:
        if under(key,new):return old+key[len(new):]
    for feature in FEATURES:
        prefix='colors.apps.'+feature
        if under(key,prefix):return 'colors.'+feature+key[len(prefix):]
    for new,old in (('colors.apps.tmux.windows.alert','colors.apps.tmux.window.attention'),
                    ('colors.apps.tmux.windows','colors.apps.tmux.window')):
        if under(key,new):return old+key[len(new):]
    return key


def style_names(group, key):
    """Low-to-high specificity spellings of one visual field."""
    public=canonical(group+'.'+key)
    old=internal(public).partition('.')[2]
    if group=='colors' and old.split('.')[0] in FEATURES:
        return list(dict.fromkeys((old, 'apps.cli.'+old, public.partition('.')[2])))
    return list(dict.fromkeys((old, public.partition('.')[2])))


def document(data, *, public=True, strict=False):
    """Translate typed fields, retaining unrelated data and literal map keys."""
    from config_values import parts, name
    result=copy.deepcopy(data)
    def remove(path):
        nodes=[result]
        for part in path[:-1]:
            if not isinstance(nodes[-1],dict) or part not in nodes[-1]:return
            nodes.append(nodes[-1][part])
        nodes[-1].pop(path[-1],None)
        for index in range(len(path)-2,-1,-1):
            if nodes[index+1]:break
            nodes[index].pop(path[index],None)
    def place(path,value):
        node=result
        for part in path[:-1]:node=node.setdefault(part,{})
        if strict and path[-1] in node and node[path[-1]]!=value:
            raise ValueError('conflicting configuration aliases: '+name(path))
        node[path[-1]]=copy.deepcopy(value)
    def lookup(path):
        node=result
        for part in path:
            if not isinstance(node,dict) or part not in node:return False,None
            node=node[part]
        return True,node
    for old,new in MOVES:
        source,target=(old,new) if public else (new,old)
        found,value=lookup(parts(source))
        if found:
            # Canonical input wins when both spellings occur on a read.
            if public and not strict and lookup(parts(target))[0]:remove(parts(source));continue
            remove(parts(source));place(parts(target),value)
    return result


def public_styles(group, values, *, strict=False):
    result={}
    # General legacy declarations precede explicit legacy app overrides, then
    # canonical declarations. Conflicting migrations still require resolution.
    ordered=sorted(values, key=lambda k:(canonical(group+'.'+k)==group+'.'+k, k.startswith('apps.')))
    for key in ordered:
        target=canonical(group+'.'+key).partition('.')[2]
        if strict and target in result and result[target]!=values[key]:
            raise ValueError('conflicting configuration aliases: '+group+'.'+target)
        result[target]=values[key]
    return result


def description(key):
    key=canonical(key)
    if key.startswith(('colors.apps.', 'icons.apps.', 'formatting.apps.')):
        _,_,app,*tail=key.split('.')
    elif key.startswith('apps.'):
        _,app,*tail=key.split('.')
    else:
        app='shared';tail=key.split('.')
    field=tail[-1] if tail else ''
    meanings={'fg':'foreground color','bg':'background color','before':'literal text before the component',
              'after':'literal text after the component','spacer':'space or separator between components',
              'bold':'bold text','dim':'dim text','underline':'underlined text','italic':'italic text',
              'reverse':'reverse foreground/background','strikethrough':'struck-through text'}
    return app+' · '+'.'.join(tail[:-1])+' · '+meanings.get(field,field.replace('_',' '))

"""Bounded, inert projections of visual preferences for managed consumers."""
import json
from pathlib import Path
import re

from style_config import Styles, ATTRS


APPS = ('cli', 'tmux', 'yazi', 'fzf', 'gum', 'starship', 'gitmux', 'nvim')


def snapshot(palette, root=None, *, styles=None,controls=None):
    styles = styles or Styles(root, palette=palette)
    from config_values import Controls
    controls=controls if controls is not None else Controls(styles.root,styles.selected,defaults=styles.defaults).values
    result = dict(schema=1, icons=styles.values['icons'], colors={}, apps={})
    from style_catalog import split, consumers, fields
    roles = sorted({split(key)[1].rsplit('.', 1)[0] for key in styles.values['colors']})
    for app in (None, *APPS):
        target = result if app is None else result['apps'].setdefault(app, dict(icons={}, colors={}))
        for key in styles.values['icons']:
            if not key.startswith('apps.') and (app is None or app in consumers('icons', key)):
                target['icons'][key] = styles.icon(key, app=app)
        for role in roles:
            doc = styles.style(role, app=app)
            resolved = {k: styles.color(v) if k in ('fg', 'bg') else v for k,v in doc.items()
                        if app is None or k in fields(role, app)}
            if resolved: target['colors'][role] = resolved
        if app:
            target['options']=controls.get('apps',{}).get(app,{})
            target['formatting']=controls.get('formatting',{}).get('apps',{}).get(app,{})
    result['config']=controls
    native=result['apps']['nvim']['options']
    for group in ('highlights','icon_styles'):
        for fields in native.get(group,{}).values():
            for field in ('fg','bg','sp'):
                if fields.get(field) in ('default','reset'):fields[field]='NONE'
                elif fields.get(field) not in (None,'NONE'):fields[field]=styles.color(fields[field])
    result['apps']['cli']['formatting']=controls.get('formatting',{}).get('apps',{})
    return result


def tmux_literal(value):
    # First protect tmux's format interpreter, then its configuration parser.
    value = value.replace('#', '##').replace('\\', '\\\\').replace('"', '\\"').replace('$', '\\$')
    return '"' + value + '"'


def tokens(palette, root=None):
    doc = snapshot(palette, root)
    result = {}
    for app in APPS:
        for role, fields in doc['apps'][app]['colors'].items():
            for field, value in fields.items():
                if field in ATTRS: continue
                # Application templates consume concrete colors only.
                if value in ('default', 'reset'):
                    if app == 'tmux':
                        result[app+'_'+role.replace('.', '_')+'_'+field] = 'default'
                        continue
                    value = palette.get('foreground', '#ffffff')
                if not re.fullmatch('#[a-fA-F0-9]{6}', value): value = palette.get(value, palette.get('foreground', '#ffffff'))
                result[app+'_'+role.replace('.', '_')+'_'+field] = value
    tmux_styles = Styles(root, palette=palette)
    for name in (k for k in tmux_styles.values['icons'] if not k.startswith('apps.')):
        value = tmux_styles.icon(name, app='tmux')
        result['tmux_icon_'+name.replace('.', '_')] = tmux_literal(value)
    # Native Yazi icon rules; file colors remain owned by file-colors.toml.
    from resources import read_data
    rows = read_data(Path(__file__).with_name('resources.tsv')).splitlines()
    groups = dict(kind=[], name=[], suffix=[], mime=[])
    kinds = dict(file='file', dir='dir', symlink='link', executable='exec', fifo='fifo', socket='sock', block_device='block', character_device='char', broken_symlink='orphan')
    for row in rows:
        parts = row.split('\t')
        if len(parts) != 5 or parts[0] not in groups: continue
        group, key, token, mime, fallback = parts
        glyph = doc['apps']['yazi']['icons'].get(token, fallback)
        selector = 'if = '+json.dumps(kinds[key]) if group == 'kind' and key in kinds else 'name = '+json.dumps(key) if group == 'name' else 'name = '+json.dumps(key.lstrip('.')) if group == 'suffix' else None
        if selector: groups[group].append('{ '+selector+', text = '+json.dumps(glyph,ensure_ascii=False)+' }')
    # Specific conditions precede the regular-file fallback.
    groups['kind'] = [row for row in groups['kind'] if '"file"' not in row] + [row.replace('"file"','"!dir"') for row in groups['kind'] if '"file"' in row]
    result['file_icons_yazi'] = '[icon]\n' + '\n'.join(name+' = [\n'+',\n'.join(groups[group])+'\n]' for group,name in [('kind','conds'),('name','files'),('suffix','exts')])
    return result


def write(out, palette, root=None):
    styles = Styles(root, palette=palette)
    doc = snapshot(palette, styles.root)
    (out/'preferences.json').write_text(json.dumps(doc,ensure_ascii=True)+'\n')
    if (out/'tmux.conf').is_file():
        from tmux_config import layout
        text=(out/'tmux.conf').read_text().split('# Dots configuration placement\n')[0]
        (out/'tmux.conf').write_text(text+'# Dots configuration placement\n'+layout(styles.root,styles.selected))
    # Gitmux receives a generated copy; its editable layout stays at its source.
    path = styles.root/'config/gitmux/gitmux.conf'
    if path.is_file():
        text = path.read_text()
        names = dict(branch='branch', ahead='ahead', behind='behind', staged='staged', conflict='conflict', modified='modified', untracked='untracked', stashed='stashed', insertions='added', deletions='deleted', clean='clean')
        before, marker, after = text.partition('    styles:')
        for name, token in names.items():
            value = styles.icon('git.'+token, app='gitmux').replace('#','##')
            if name in ('ahead','behind'): value = '#[fg=#{s/^reset$/default/:@dots-gitmux-'+name+'},nobold,nounderscore,noreverse]'+value
            before = re.sub(r'(?m)^        '+name+r':.*$', lambda _: '        '+name+': '+json.dumps(value,ensure_ascii=False), before)
        (out/'gitmux.conf').write_text(before+marker+after)
    write_shell(out, styles, doc)
    return doc


def write_shell(out, styles, doc):
    """Data for native adapters; no generated text is evaluated as code."""
    from style_config import ROLES
    rows = [('icon', k, v) for k, v in doc['apps']['cli']['icons'].items()]
    rows += [('color', k, styles.code(k)) for k in ROLES]
    gum = (out/'gum_env.sh').read_text() if (out/'gum_env.sh').is_file() else ''
    rows += [('env', m[1], m[2]) for m in re.finditer(r"(?m)^export ([A-Z][A-Z0-9_]*)='(#[0-9a-fA-F]{6})'$", gum)]
    fzf = (out/'fzf.sh').read_text().replace('\\\n', '') if (out/'fzf.sh').is_file() else ''
    match = re.search(r'^export _FZF_COLORS_="([^"\n]+)"', fzf, re.M)
    if match: rows.append(('env', 'DOTS_THEME_FZF_COLORS', match[1]))
    from fzf_config import shell_options,colors
    options=doc.get('config',{}).get('apps',{}).get('fzf',{})
    overrides=colors(options,styles)
    if overrides:
        rows=[(kind,key,value+','+overrides if key=='DOTS_THEME_FZF_COLORS' and value else overrides if key=='DOTS_THEME_FZF_COLORS' else value) for kind,key,value in rows]
        if not match:rows.append(('env','DOTS_THEME_FZF_COLORS',overrides))
    if options:
        rows.append(('env','DOTS_THEME_FZF_OPTS',shell_options(options)))
        rows.append(('env','DOTS_THEME_FZF_PREVIEW','1' if options.get('preview') is not None else '0'))
    (out/'visual.tsv').write_text(''.join('\t'.join(row)+'\n' for row in rows))

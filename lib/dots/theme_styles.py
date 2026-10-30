"""Bounded, inert projections of visual preferences for managed consumers."""
import json
from pathlib import Path
import re

from style_config import Styles, ATTRS


APPS = ('tmux', 'yazi', 'fzf', 'gum', 'starship', 'gitmux')


def snapshot(palette, root=None):
    styles = Styles(root, palette=palette)
    result = dict(schema=1, icons=styles.values['icons'], colors={}, apps={})
    roles = sorted({key.rsplit('.', 1)[0] for key in styles.values['colors'] if not key.startswith('apps.')})
    for app in (None, *APPS):
        target = result if app is None else result['apps'].setdefault(app, dict(icons={}, colors={}))
        for key in styles.values['icons']:
            if not key.startswith('apps.'): target['icons'][key] = styles.icon(key, app=app)
        for role in roles:
            doc = styles.style(role, app=app)
            target['colors'][role] = {k: styles.color(v) if k in ('fg', 'bg') else v for k,v in doc.items()}
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
                if value in ('default', 'reset'): value = palette.get('foreground', '#ffffff')
                if not re.fullmatch('#[a-fA-F0-9]{6}', value): value = palette.get(value, palette.get('foreground', '#ffffff'))
                result[app+'_'+role.replace('.', '_')+'_'+field] = value
    for name, value in doc['apps']['tmux']['icons'].items():
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
    return doc

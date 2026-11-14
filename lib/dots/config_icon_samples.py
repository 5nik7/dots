"""Read-only evidence for Config glyph samples outside colors/icons.toml."""
import json
from pathlib import Path
import re

from resources import Resources, read_data


# Representative menu entries, from menu_cli, keys.presentation, wttr.browser
# and menu_sessions. The last flag records whether that entry has icon_role.
MENU_ENTRIES = {
    'files.configuration': ('dots:config', True),
    'files.directory': ('dots:files', True),
    'git.repository': ('dots:git', True),
    'status.todo': ('dots:todo', True),
    'navigation.keys': ('dots:keys', True),
    'navigation.session': ('dots:tmux', True),
    'navigation.help': ('dots:help', True),
    'navigation.back': ('wttr:main:back', True),
    'navigation.refresh': ('wttr:main:refresh', True),
    'navigation.new': ('session-actions:new', False),
    'navigation.edit': ('session-actions:rename', False),
    'navigation.delete': ('session-actions:delete', False),
    'weather.title': ('dots:wttr', True),
    **{'weather.'+role: ('wttr:main:'+entry, True) for role, entry in
       (('daily','daily'), ('hourly','hourly'), ('location','location'), ('units','units'))},
}


def menu_entry(role):
    if role == 'navigation.codex': role = 'applications.codex'
    if role.startswith('applications.'):
        return 'keys:categories:'+role.split('.')[1], True
    return MENU_ENTRIES.get(role)


class PublishedSamples:
    """Use the consumer's bounded snapshot, never publish or resolve a theme.

    The table owns filename matching. colors.json supplies actual rule fields;
    Vivid-only suffixes must not be guessed from a coincidentally equal color.
    """
    def __init__(self, styles, root=None):
        self.styles = styles
        self.resources = Resources(root)
        try:
            doc = json.loads(read_data(self.resources.root/'colors.json'))
            self.doc = doc if isinstance(doc,dict) and doc.get('schema') == 1 else {}
        except ValueError:
            self.doc = {}
        # A stale/malformed optional snapshot must not hide core Config rows.
        for section in ('rules','styles'):
            groups=self.doc.get(section,{})
            if not isinstance(groups,dict) or any(not isinstance(entries,dict) or
                    any(not isinstance(rule,dict) for rule in entries.values()) for entries in groups.values()):
                self.doc={};break
        self.files = {}
        for line in read_data(Path(__file__).with_name('resources.tsv')).splitlines():
            fields = line.split('\t')
            if len(fields) != 5: continue
            group, key, role, mime, _ = fields
            if role in self.files or key in ('missing','broken_symlink'): continue
            if group == 'kind': self.files[role] = (key, key, None)
            elif group in ('name','suffix'):
                self.files[role] = (key, 'file', mime if mime != '-' else None)

    def annotation(self, group, key, fields=('fg','bg')):
        if not fields:return ''
        if group == 'suffix': return 'Vivid suffix '+json.dumps(key)
        if group == 'default_mime': group = 'mime'
        rules = self.doc.get('rules',{})
        rule = rules.get(group,{}).get(key)
        if not isinstance(rule,dict): return ''
        sources = []
        for field in fields:
            owner, name, current, seen = group, key, rule, set()
            while field not in current and isinstance(current.get('use'),str) and current['use'] not in seen:
                owner, name = 'type', current['use']; seen.add(name)
                current = rules.get(owner,{}).get(name,{})
            if field in current:
                source = owner+'.'+name if owner in ('type','git') else owner+'['+json.dumps(name)+']'
                sources.append(source+'.'+field)
        return 'file-colors.toml: '+', '.join(sources) if sources else ''

    def sample(self, role, fields=('fg','bg')):
        if role.startswith('git.status.'):
            key = role.rsplit('.',1)[-1]
            key = {'type_changed':'modified', 'selected':'staged'}.get(key,key)
            annotation = self.annotation('git',key,fields)
            source = annotation+' (published)' if annotation else 'Git '+key+' fallback'
            return self.resources.git_style(key), source+'; default status heading, unstaged when applicable'
        if role in self.files:
            name, kind, mime = self.files[role]
            code, source = self.resources.match_style(name, kind, mime)
            if source:
                if self.annotation(*source):
                    annotation = self.annotation(*source,fields)
                    return code, annotation+' (published; '+name+')' if annotation else ''
        # Branch and host glyphs share their identity's complete Git style.
        # Other Git glyphs are consumed by Gitmux, which uses only its fg.
        if role.startswith('hosts.') or role == 'git.branch':
            key = 'branch' if role == 'git.branch' else 'repo'
            if self.annotation('git',key):
                annotation = self.annotation('git',key,fields)
                return self.resources.git_style(key), annotation+' (published; '+('branch' if key=='branch' else 'repository, not owned')+')' if annotation else ''
        if role in ('git.added','git.ahead','git.behind','git.clean','git.conflict',
                    'git.deleted','git.modified','git.staged','git.untracked'):
            key = role.split('.')[1]
            style = self.doc.get('styles',{}).get('git',{}).get(key,{})
            annotation = self.annotation('git',key,('fg',))
            if isinstance(style.get('fg'),str) and re.fullmatch(r'#[0-9a-fA-F]{6}|reset',style['fg']) and annotation:
                # Same generated git_<role> token and fixed Gitmux attributes.
                code = self.styles.sgr_fields(dict(fg=style['fg'],bold=key in ('modified','untracked')))
                return code, annotation+' (published; Gitmux)'
        return None

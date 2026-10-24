"""Native theme data reader and renderer. All theme inputs are inert data."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys

LIB = Path(__file__).resolve().parent
sys.path.insert(0, str(LIB.parent))
sys.path.insert(0, str(LIB.parent / 'files'))
from environment import settings
from file_platform import config_root, state_root
from transactions import parents_safe

ID = re.compile(r'[a-z][a-z0-9_]*(?:-[a-z0-9_]+)*\Z')
KEY = re.compile(r'[a-zA-Z_][a-zA-Z0-9_]*\Z')
HEX = re.compile(r'#[a-fA-F0-9]{6}\Z')
FORMATS = 'name hex rgb r g b rgb-r rgb-g rgb-b luminance brightness cmyk ansi-8bit ansi-8bit-value ansi-8bit-escapecode ansi-24bit ansi-24bit-escapecode esc'.split()
ROLES = 'background foreground muted accent selection error warning info hint'.split()
ANSI = 'background red green yellow blue magenta cyan foreground muted bright_red bright_green bright_yellow bright_blue bright_magenta bright_cyan bright_foreground'.split()


def regular(path):
    if path.is_symlink() or not path.is_file(): raise ValueError('expected a regular theme data file: ' + str(path))
    with path.open('rb') as stream: data = stream.read(2 * 1024 * 1024 + 1)
    if len(data) > 2 * 1024 * 1024: raise ValueError('theme input exceeds size limit')
    return data


def literal(path, kind):
    # Preserve the existing restricted TOML grammar instead of accepting code,
    # dates, arrays, dotted assignments, escaped strings or arbitrary tables.
    text = regular(path).decode('utf-8')
    section = ''
    values, sections = {}, set()
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith('#'): continue
        match = re.fullmatch(r'\s*\[([a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)?)\]\s*(?:#.*)?', line)
        if match:
            section = match[1]
            if kind != 'metadata' or section in sections or not (section == 'integrations' or section == 'roles' or section.startswith('roles.')):
                raise ValueError('unsupported or duplicate theme table')
            sections.add(section); continue
        match = re.fullmatch(r'''\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(?:"([^"\\]*)"|'([^']*)')\s*(?:#.*)?''', line)
        if not match: raise ValueError('unsupported theme syntax: ' + str(path))
        key, value = match[1], match[2] if match[2] is not None else match[3]
        full = (section + '.' if section else '') + key
        if full in values or any(ord(c) < 32 for c in value): raise ValueError('duplicate key or control character in theme')
        if kind == 'palette' and not HEX.fullmatch(value): raise ValueError('expected #RRGGBB palette color')
        if kind == 'metadata':
            if section.startswith('roles'):
                if not KEY.fullmatch(value): raise ValueError('invalid role reference')
            elif full not in ('name', 'source', 'default_flavor', 'integrations.nvim', 'integrations.vivid', 'family', 'flavor'):
                raise ValueError('unsupported metadata key: ' + full)
        if kind == 'colors':
            if key == 'mode':
                if value not in ('dark', 'light'): raise ValueError('invalid palette mode')
            elif not HEX.fullmatch(value):
                if key.startswith('hyprland_') or key in ('active_border_color', 'inactive_border_color'): continue
                raise ValueError('expected #RRGGBB semantic color')
        values[full] = value
    if not values: raise ValueError('empty theme data')
    return values


def metric(name, color, format='hex'):
    r, g, b = (int(color[i:i+2], 16) for i in (1, 3, 5))
    ansi = (16 if r < 8 else 231 if r > 248 else 232 + (r - 8) * 24 // 247) if r == g == b else 16 + 36 * ((r*5+127)//255) + 6*((g*5+127)//255) + (b*5+127)//255
    rgb = f'{r} {g} {b}'
    value = dict(name=name, hex=color, rgb=rgb, r=str(r), g=str(g), b=str(b), **{'rgb-r':str(r), 'rgb-g':str(g), 'rgb-b':str(b), 'ansi-8bit':str(ansi), 'ansi-8bit-value':str(ansi), 'ansi-8bit-escapecode':f'\x1b[38;5;{ansi}m', 'ansi-24bit':f'38;2;{r};{g};{b}', 'ansi-24bit-escapecode':f'\x1b[38;2;{r};{g};{b}m', 'esc':f'\x1b[38;2;{r};{g};{b}m'})
    lin = lambda c: c / 255 / 12.92 if c/255 <= .04045 else ((c/255+.055)/1.055)**2.4
    value['luminance'] = f'{.2126*lin(r)+.7152*lin(g)+.0722*lin(b):.6f}'
    value['brightness'] = str(int(.299*r+.587*g+.114*b+.5))
    c, m, y = 1-r/255, 1-g/255, 1-b/255
    k = min(c, m, y)
    value['cmyk'] = '0 0 0 100' if k >= .999999 else ' '.join(str(int(v*100+.5)) for v in ((c-k)/(1-k), (m-k)/(1-k), (y-k)/(1-k), k))
    if format not in value: raise ValueError('unsupported color format: ' + format)
    return value[format]


def styles():
    spec = importlib.util.spec_from_file_location('dots_file_colors', LIB / 'file-colors.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


class Themes:
    def __init__(self):
        self.checkout = Path(os.environ.get('DOTS') or LIB.parents[2]).resolve()
        self.root = Path(os.environ.get('DOTHEMES') or os.environ.get('THEMES') or self.checkout / 'themes')
        self.config, self.state = config_root() / 'dots', state_root()
        self.user = self.config / 'themes'
        self.templates = Path(os.environ.get('DOTS_THEME_TEMPLATES') or self.checkout / 'default/themed')
        for path in (self.root, self.config, self.state):
            if not path.is_absolute(): raise ValueError('theme roots must be absolute')

    def directory(self, identity):
        if not ID.fullmatch(identity): raise ValueError('invalid theme identifier')
        if any((self.root / identity / name).is_file() for name in ('colors.toml', 'palette.toml')) and (self.user / identity).is_dir():
            raise ValueError('duplicate bundled and user theme: ' + identity)
        for base in (self.root, self.user):
            path = base / identity
            if path.is_dir() and not path.is_symlink() and any((path / name).is_file() for name in ('colors.toml', 'palette.toml')):
                return path
        if identity == 'pywal16-current' and (self.root / identity).is_dir(): return self.root / identity
        raise ValueError('unknown selectable theme ID: ' + identity)

    def ids(self):
        return sorted({path.parent.name for base in (self.root, self.user) for name in ('colors.toml', 'palette.toml')
                       for path in base.glob('*/' + name) if not path.is_symlink() and ID.fullmatch(path.parent.name)} |
                      ({'pywal16-current'} if (self.root / 'pywal16-current').is_dir() else set()))

    def families(self):
        result = {}
        for identity in self.ids():
            directory = self.directory(identity)
            meta = literal(directory / 'theme.toml', 'metadata') if (directory / 'theme.toml').exists() else {}
            family, flavor = meta.get('family', identity), meta.get('flavor', 'default')
            if not ID.fullmatch(family) or not re.fullmatch('[a-z][a-z0-9_]*', flavor): raise ValueError('invalid family or flavor')
            if flavor in result.setdefault(family, {}): raise ValueError('duplicate family flavor')
            result[family][flavor] = identity
        return result

    def pick(self, name, flavor=None):
        families = self.families()
        if name not in families: self.directory(name); return name
        if not flavor:
            current = self.current()
            if current in families[name].values(): return current
            path = self.root / name / 'theme.toml'
            meta = literal(path, 'metadata') if path.exists() else {}
            flavor = meta.get('default_flavor') or ('default' if 'default' in families[name] else sorted(families[name])[0])
        if flavor not in families[name]: raise ValueError('unknown family flavor')
        return families[name][flavor]

    def current(self):
        return settings(self.checkout)['DOTS_THEME_ID']['value']

    def load(self, identity):
        directory = self.directory(identity)
        meta = literal(directory / 'theme.toml', 'metadata') if (directory / 'theme.toml').exists() else {}
        family, flavor = meta.get('family', identity), meta.get('flavor', 'default')
        family_meta = self.root / family / 'theme.toml'
        if family_meta.exists(): meta = {**literal(family_meta, 'metadata'), **meta}
        for key, value in list(meta.items()):
            if key.startswith('roles.' + flavor + '.'): meta['roles.' + key.rsplit('.', 1)[1]] = value
        # Pywal's bundled file is a placeholder; its palette comes from the export.
        palette = literal(directory / 'palette.toml', 'palette') if family != 'pywal16' and (directory / 'palette.toml').exists() else {}
        if family != 'pywal16' and not palette and (self.root / family / 'flavors' / (flavor + '.toml')).is_file():
            palette = literal(self.root / family / 'flavors' / (flavor + '.toml'), 'palette')
        if family == 'pywal16':
            cache = Path(os.environ.get('XDG_CACHE_HOME') or Path.home() / '.cache') / 'wal/colors.json'
            doc = json.loads(regular(cache))
            colors = {**doc['colors'], **doc['special']}
            if not all(HEX.fullmatch(v) for v in colors.values()): raise ValueError('invalid pywal palette')
            palette = dict(colors)
        elif (directory / 'colors.toml').exists(): colors = literal(directory / 'colors.toml', 'colors')
        else:
            colors = dict(palette)
            for role in ROLES:
                name = meta.get('roles.' + role, role)
                if name not in palette: raise ValueError('missing role color: ' + role)
                colors[role] = palette[name]
        for i, name in enumerate(ANSI):
            if name not in colors and 'color' + str(i) in colors: colors[name] = colors['color' + str(i)]
        if not all(name in colors for name in ('background', 'foreground')): raise ValueError('missing background or foreground')
        colors.setdefault('accent', colors.get('blue', colors['foreground']))
        for name in ('red', 'green', 'yellow', 'blue', 'magenta', 'cyan'):
            colors.setdefault(name, colors['accent']); colors.setdefault('bright_' + name, colors[name])
        colors.setdefault('muted', colors['foreground'])
        colors.setdefault('selection', colors.get('selection_background', colors['muted']))
        for name in ('dark_background', 'darker_background', 'lighter_background'): colors.setdefault(name, colors['background'])
        for name in ('bright_foreground', 'dark_foreground', 'light_foreground', 'cursor', 'selection_foreground'): colors.setdefault(name, colors['foreground'])
        for name, default in dict(selection_background='selection', orange='yellow', brown='muted', error='red', warning='yellow', info='blue', hint='cyan').items(): colors.setdefault(name, colors[default])
        for i, name in enumerate(ANSI): colors['color' + str(i)] = colors[name]
        mode = colors.pop('mode', 'light' if int(metric('', colors['background'], 'brightness')) >= 128 else 'dark')
        if not palette: palette = dict(colors)
        return dict(schema=1, id=identity, adapter='native' if (self.root / family / 'flavors').is_dir() else 'generic',
                    mode=mode, theme=family, flavor=flavor, palette=palette,
                    roles={name: colors[name] for name in ROLES}, colors=colors)

    def fingerprint(self, identity):
        digest = hashlib.sha256()
        digest.update(regular(LIB.parent / "files/app_paths.py"))
        digest.update(str(shutil.which('bat')).encode())
        family = self.load(identity)['theme']
        if family == 'pywal16':
            digest.update(regular(Path(os.environ.get('XDG_CACHE_HOME') or Path.home() / '.cache') / 'wal/colors.json'))
        for base in (LIB, LIB.parent / 'shell', self.checkout / 'default', self.directory(identity), self.root / family, self.config / 'themed', self.templates):
            if not base.exists(): continue
            for path in sorted(base.rglob('*')):
                if path.is_file() and not path.is_symlink() and '__pycache__' not in path.parts:
                    digest.update(str(path).encode())
                    with path.open('rb') as stream:
                        for chunk in iter(lambda: stream.read(65536), b''): digest.update(chunk)
        for path in styles().input_paths(identity, self.directory(identity)):
            digest.update(str(path).encode())
            if path.exists(): digest.update(regular(path))
        return digest.hexdigest()

    def render(self, identity, out, build_cache=False):
        palette = self.load(identity)
        directory = self.directory(identity)
        color = styles()
        doc = color.resolve(palette, directory)
        tokens = dict(palette['colors'])
        tokens.update({'git_' + key: value for key, value in doc['colors']['git'].items()})
        for key, value in list(tokens.items()):
            tokens[key + '_delta'] = 'normal' if value == 'reset' else value
            if key.startswith('git_'):
                tokens[key + '_eza'] = 'default' if value == 'reset' else value
            value = palette['colors']['background'] if value == 'reset' else value
            for percent in (10, 25):
                bg = palette['colors']['background']
                tokens[key + '_blend_' + str(percent)] = '#' + ''.join(f'{(int(value[i:i+2],16)*percent + int(bg[i:i+2],16)*(100-percent)+50)//100:02x}' for i in (1,3,5))
            tokens[key + '_strip'] = value.lstrip('#')
            tokens[key + '_rgb'] = metric(key, value, 'rgb').replace(' ', ',')
        tokens.update(color.leaf_template_tokens(palette))
        tokens['mode'] = palette['mode']
        tokens['file_styles_vivid'] = json.dumps(color.vivid_theme(doc, color.vivid_runtime()[2]), indent=2)
        tokens['git_colors_starship'] = '\n'.join('git_' + key + ' = ' + json.dumps(value) for key, value in doc['colors']['git'].items())
        rendered = set()
        trusted = directory.is_relative_to(self.root)
        overrides = 'kitty.conf tmux.conf btop.theme termux.properties bat.tmTheme yazi.toml fzf.sh gum_env.sh pi.json vivid.yml fsh.ini eza.yml television.toml leaf.toml'.split()
        for name in overrides if trusted else ():
            if (directory / name).is_file() and not (directory / name).is_symlink():
                (out / name).write_bytes(regular(directory / name)); rendered.add(name)
        reserved = {'id','selection','fingerprint','palette.json','shell.tsv','colors.json','colors.lua','git-styles.tsv','file-styles.tsv','ls_colors','previous','status','connectors','bat-cache','bat-source','delta-cache','commands','yazi'}
        for base in (self.config / 'themed', self.templates):
            for path in sorted(base.glob('*.tpl')):
                name = path.stem
                if name in rendered: continue
                if not re.fullmatch('[a-zA-Z0-9][a-zA-Z0-9._-]*', name) or name in reserved or name.startswith('init.'): raise ValueError('reserved template output')
                text = regular(path).decode('utf-8')
                def substitute(match):
                    key = match[1]
                    if key not in tokens: raise ValueError('unknown template color: ' + key)
                    return tokens[key]
                text = re.sub(r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}', substitute, text)
                if '{{' in text or '}}' in text: raise ValueError('unresolved template expression')
                (out / name).write_text(text, encoding='utf-8', newline='\n'); rendered.add(name)
        color.write_snapshot(color.generate(doc, out / 'vivid.yml'), out)
        if build_cache and shutil.which('bat') and (out / 'bat.tmTheme').is_file():
            source, cache = out / 'bat-source', out / 'bat-cache'
            (source / 'themes').mkdir(parents=True)
            cache.mkdir()
            (source / 'themes/Dots.tmTheme').write_bytes(regular(out / 'bat.tmTheme'))
            env = dict(os.environ, BAT_CONFIG_PATH=os.devnull, BAT_THEME='ansi',
                       BAT_CONFIG_DIR=str(source), BAT_CACHE_PATH=str(cache))
            result = subprocess.run(['bat', 'cache', '--build', '--source', str(source), '--target', str(cache)],
                                    env=env, cwd=source, capture_output=True, timeout=120)
            if result.returncode: raise ValueError('bat theme cache build failed')
            (out / 'delta-cache').mkdir()
            (out / 'delta-cache/bat').symlink_to('../bat-cache', target_is_directory=True)
        (out / 'yazi').mkdir()
        for src, dest in (('yazi.toml', 'flavor.toml'), ('bat.tmTheme', 'tmtheme.xml')):
            (out / 'yazi' / dest).write_bytes(regular(out / src))
        (out / 'palette.json').write_text(json.dumps(palette) + '\n', encoding='utf-8')
        (out / 'id').write_text(identity + '\n')
        (out / 'selection').write_text(palette['theme'] + '-' + palette['flavor'] + '\n')
        (out / 'fingerprint').write_text(self.fingerprint(identity) + '\n')
        rows = [('@theme', 'id', identity), ('@theme', 'family', palette['theme']), ('@theme', 'flavor', palette['flavor'])]
        for name, value in palette['palette'].items():
            rows.append(('@palette', name, value))
        for name, value in {**palette['palette'], **palette['roles']}.items():
            for format in FORMATS: rows.append((name, format, metric(name, value, format)))
        rows += [('@role', name, value) for name, value in palette['roles'].items()]
        (out / 'shell.tsv').write_text(''.join('\t'.join(row) + '\n' for row in rows), encoding='utf-8')
        return palette

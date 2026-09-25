"""Data-only imports and journaled Anodize source storage."""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
import tomllib

from catalog import read_json
from transactions import Store, digest, exists, parents_safe

ID = re.compile(r'^[a-z][a-z0-9_]*(-[a-z0-9_]+)*$')
HEX = re.compile(r'^#[0-9a-fA-F]{6}$')
NAMES = ['background', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'foreground', 'muted',
         'bright_red', 'bright_green', 'bright_yellow', 'bright_blue', 'bright_magenta', 'bright_cyan', 'bright_foreground']
ALIASES = {'bg': 'background', 'fg': 'foreground', 'purple': 'magenta', 'bright_purple': 'bright_magenta',
           'dark_bg': 'dark_background', 'darker_bg': 'darker_background', 'lighter_bg': 'lighter_background',
           'dark_fg': 'dark_foreground', 'light_fg': 'light_foreground', 'bright_fg': 'bright_foreground'}
LIMIT = 1 << 20


def regular_bytes(path, limit=LIMIT):
    path = Path(path)
    # lstat before open prevents blocking on a FIFO supplied as input.
    if not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError('input must be a regular file: ' + str(path))
    with path.open('rb') as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError('input exceeds size limit: ' + str(path))
    return data


def encode(doc):
    return (json.dumps(doc, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False) + '\n').encode()


def color_data(colors, light=False):
    if not isinstance(colors, dict):
        raise ValueError('colors must be a mapping')
    result = {}
    for key, value in colors.items():
        if key == 'mode':
            if value not in ('light', 'dark'):
                raise ValueError('invalid theme mode')
            continue
        key = ALIASES.get(key, key)
        if not isinstance(value, str) or not HEX.fullmatch(value):
            raise ValueError('colors must use #RRGGBB')
        if not re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_]{0,63}', key):
            raise ValueError('invalid color name')
        if key in result and result[key] != value.lower():
            raise ValueError('conflicting color aliases: ' + key)
        result[key] = value.lower()
    for i, key in enumerate(NAMES):
        if key not in result and f'color{i}' in result:
            result[key] = result[f'color{i}']
    for key in ('background', 'foreground'):
        if key not in result:
            raise ValueError('missing color: ' + key)
    result.setdefault('accent', result.get('blue', result['foreground']))
    for key in NAMES:
        result.setdefault(key, result.get(key.removeprefix('bright_'), result['accent']))
    # ANSI aliases are generated after adjustments, so cannot diverge from names.
    return {k: v for k, v in result.items() if not re.fullmatch(r'color\d+', k)}


def new_document(identity, colors, light=False, mode='normal'):
    if not ID.fullmatch(identity):
        raise ValueError('invalid theme ID; use lowercase words separated by hyphens')
    return dict(schema=1, id=identity, baseline=color_data(colors), adjustments={}, overrides={},
                options=dict(mode=mode, light=light))


def toml_colors(colors, light):
    lines = ['mode = "' + ('light' if light else 'dark') + '"']
    lines += [f'{k} = "{v}"' for k, v in sorted(colors.items())]
    return ('\n'.join(lines) + '\n').encode()


class Author:
    def __init__(self):
        self.code = Path(__file__).resolve().parents[3]
        self.root = Path(os.environ.get('DOTS') or self.code).resolve()
        self.themes = self.root / 'themes'
        self.engine = Path(os.environ.get('ANODIZE_ENGINE') or self.code / 'anodize/.build/anodize-engine')
        self.bridge = self.code / 'lib/dots/anodize/themes.bash'

    def call(self, action, **kwargs):
        if not self.engine.is_file():
            raise ValueError('Anodize engine is not built; run python3 -B tools/verify_anodize.py build in Dots')
        proc = subprocess.run([str(self.engine)], input=encode(dict(schema=1, action=action, **kwargs)),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        if proc.returncode:
            raise ValueError(proc.stderr.decode(errors='replace').strip())
        result = json.loads(proc.stdout)
        if result.get('schema') != 1:
            raise ValueError('unsupported engine response')
        return result

    def theme_bridge(self, action, identity, *args):
        if not ID.fullmatch(identity):
            raise ValueError('invalid theme ID')
        env = dict(os.environ, DOTHEMES=str(self.themes), THEMES=str(self.themes))
        proc = subprocess.run(['bash', str(self.bridge), action, identity, *map(str, args)], env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        if proc.returncode:
            raise ValueError(proc.stderr.decode(errors='replace').strip() or 'theme operation failed')
        # Successful adapter diagnostics are returned separately, never parsed.
        return proc.stdout, proc.stderr

    def render(self, doc):
        if not isinstance(doc, dict) or not isinstance(doc.get('id'), str) or not ID.fullmatch(doc['id']):
            raise ValueError('invalid Anodize document ID')
        if not isinstance(doc.get('options'), dict) or not isinstance(doc['options'].get('light'), bool):
            raise ValueError('document options require a boolean light value')
        for field in ('baseline', 'adjustments', 'overrides'):
            if not isinstance(doc.get(field), dict):
                raise ValueError('document requires a ' + field + ' mapping')
        if 'wallpaper' in doc and (not isinstance(doc['wallpaper'], str) or any(ord(c) < 32 for c in doc['wallpaper'])):
            raise ValueError('invalid wallpaper reference')
        return self.call('render', document={k: v for k, v in doc.items() if k != 'generated'})

    def generate(self, image=None, seed=None, options=None):
        kwargs = dict(options=options or dict(mode='normal', light=False))
        if image:
            kwargs['image'] = base64.b64encode(regular_bytes(image, 32 << 20)).decode()
        else:
            kwargs['color'] = seed
        return self.call('generate', **kwargs)['colors']

    def target(self, identity):
        if not ID.fullmatch(identity):
            raise ValueError('invalid theme ID')
        path = self.themes / identity
        parents_safe(path)
        if path.is_symlink():
            raise ValueError('theme directory must not be a symlink')
        return path

    def load(self, identity, owned=False):
        path = self.target(identity)
        if exists(path / 'anodize.json'):
            doc = read_json(path / 'anodize.json')
            if doc.get('id') != identity:
                raise ValueError('theme recipe ID does not match directory')
            self.render(doc)
            return doc
        if owned:
            raise ValueError('edit requires an Anodize-owned theme; use create --from')
        raw, _ = self.theme_bridge('resolve', identity)
        data = json.loads(raw)
        colors = data.get('colors') or data['palette']
        colors.update(data['roles'])
        return new_document(identity, colors, data['mode'] == 'light')

    def verify_generated(self, path, doc):
        generated = doc.get('generated')
        if not isinstance(generated, dict) or not {'colors.toml', 'theme.toml'} <= generated.keys():
            raise ValueError('missing generated-file receipt; derive a new theme with create --from')
        for name, expected in generated.items():
            if name not in ('colors.toml', 'theme.toml') and not re.fullmatch(r'backgrounds/wallpaper\.(png|jpg|jpeg|gif)', name):
                raise ValueError('invalid generated-file receipt')
            if hashlib.sha256(regular_bytes(path / name, 32 << 20)).hexdigest() != expected:
                raise ValueError('generated file changed; refusing to overwrite: ' + name)

    def imported(self, path, identity, fmt):
        data = regular_bytes(path)
        notes = []
        if fmt == 'anodize':
            doc = json.loads(data)
            if not isinstance(doc, dict):
                raise ValueError('invalid blueprint')
            doc.pop('generated', None)
            doc['id'] = identity
            # Local references are resolved against the blueprint, never cwd.
            if doc.get('wallpaper') and not Path(doc['wallpaper']).is_absolute():
                doc['wallpaper'] = str((Path(path).absolute().parent / doc['wallpaper']).resolve())
            self.render(doc)
            return doc, notes
        if fmt == 'aether':
            raw = json.loads(data)
            p = raw['palette']
            values = p['colors']
            if not isinstance(values, list) or len(values) != 16:
                raise ValueError('Aether palette requires 16 colors')
            colors = dict(zip(NAMES, values))
            colors.update(p.get('extendedColors') or {})
            doc = new_document(identity, colors, p.get('mode') == 'light' or (p.get('mode') != 'dark' and bool(p.get('lightMode'))))
            if raw.get('adjustments'):
                doc['provenance'] = {'aether_adjustments': raw['adjustments']}
                notes.append('Imported colors are already adjusted; active adjustments start at zero.')
            if p.get('wallpaper'):
                wall = Path(p['wallpaper']).expanduser()
                doc['wallpaper'] = str(wall if wall.is_absolute() else (Path(path).absolute().parent / wall).resolve())
            if any(raw.get(k) for k in ('settings', 'appOverrides', 'iconTheme')) or any(p.get(k) for k in ('wallpaperBlur', 'additionalImages', 'lockedColors', 'nativeColors', 'wallpaperUrl')):
                notes.append('App settings, overrides, native colors, locks, extra images and wallpaper effects are not imported.')
            return doc, notes
        if fmt == 'colors':
            colors = tomllib.loads(data.decode())
            return new_document(identity, colors, colors.get('mode') == 'light'), notes
        if fmt == 'base16':
            # Deliberate data subset: flat base00..base0F YAML or JSON values.
            text = data.decode()
            if text.lstrip().startswith('{'):
                values = json.loads(text)
            else:
                values = {}
                for line in text.splitlines():
                    match = re.fullmatch(r'''\s*(base[0-9a-fA-F]{2}):\s*["']?([#]?[0-9a-fA-F]{6})["']?\s*(?:#.*)?''', line)
                    if match:
                        key, value = match.groups()
                        if key.lower() in values:
                            raise ValueError('duplicate Base16 color')
                        values[key.lower()] = value
            values = {k.lower(): '#' + str(v).lstrip('#') for k, v in values.items() if k.lower().startswith('base')}
            if not all('base' + format(i, '02x') in values for i in range(16)):
                raise ValueError('Base16 requires base00 through base0F')
            order = ['00','08','0b','0a','0d','0e','0c','05','03','08','0b','0a','0d','0e','0c','07']
            colors = {name: values['base' + n] for name, n in zip(NAMES, order)}
            colors.update(lighter_background=values['base01'], selection=values['base02'],
                          dark_foreground=values['base04'], light_foreground=values['base06'],
                          orange=values['base09'], brown=values['base0f'])
            # Base16 does not carry an explicit mode; use background luminance.
            bg = colors['background'].lstrip('#')
            light = sum(int(bg[i:i+2],16)*w for i,w in zip((0,2,4),(299,587,114))) >= 128000
            return new_document(identity, colors, light), notes
        raise ValueError('unsupported import format')

    def store(self):
        if os.name != 'posix':
            raise ValueError('journaled theme authoring currently requires POSIX')
        state = Path(os.environ.get('XDG_STATE_HOME') or Path.home() / '.local/state')
        if not state.is_absolute():
            raise ValueError('state root must be absolute')
        return Store(state / 'dots')

    def prepare(self, doc, edit=False, reference=False, wallpaper=None):
        path = self.target(doc['id'])
        if exists(path) and not edit:
            raise ValueError('theme ID already exists')
        user_themes = Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config') / 'dots/themes'
        if exists(user_themes / doc['id']):
            raise ValueError('theme ID conflicts with an installed user theme')
        old = self.load(doc['id'], owned=True) if edit else None
        if old:
            self.verify_generated(path, old)
        before = digest(path)
        colors = self.render(doc)['colors']
        files = {'colors.toml': toml_colors(colors, doc['options']['light']),
                 'theme.toml': f'name = "{doc["id"]}"\n'.encode()}
        # Existing copied wallpaper survives edits; new/imported references are copied unless opted out.
        wall = wallpaper or doc.get('wallpaper')
        external_guard = None
        if wall:
            source = Path(wall)
            if not source.is_absolute():
                if not edit or not re.fullmatch(r'backgrounds/wallpaper\.(png|jpg|jpeg|gif)', wall):
                    raise ValueError('invalid relative wallpaper reference')
                source = path / wall
            content = regular_bytes(source, 32 << 20)
            external_guard = (str(source), digest(source))
            if reference or (edit and not wallpaper and Path(wall).is_absolute()):
                doc['wallpaper'] = str(source.absolute())
            elif edit and not wallpaper and not Path(wall).is_absolute():
                doc['wallpaper'] = wall
                files[wall] = content
            else:
                suffix = source.suffix.lower()
                if suffix not in ('.png', '.jpg', '.jpeg', '.gif'):
                    raise ValueError('wallpaper must be PNG, JPEG, or GIF')
                # Decode before copying imported image data too.
                self.generate(source, options=doc['options'])
                dest = 'backgrounds/wallpaper' + suffix
                doc['wallpaper'] = dest
                files[dest] = content
        doc['generated'] = {k: hashlib.sha256(v).hexdigest() for k, v in files.items()}
        files['anodize.json'] = encode(doc)
        guards = {str(path): before}
        if external_guard:
            # A copied wallpaper inside the replaced directory is guarded by the tree digest.
            if not Path(external_guard[0]).is_relative_to(path):
                guards[external_guard[0]] = external_guard[1]
        unchanged = old is not None and all(exists(path / name) and regular_bytes(path / name, 32 << 20) == value for name, value in files.items())
        return dict(schema=1, status='unchanged' if unchanged else 'preview', action='edit' if edit else 'create',
                    target=str(path), files=files, guards=guards, document=doc)

    def save(self, plan):
        if plan['status'] == 'unchanged':
            return {'schema': 1, 'status': 'unchanged', 'target': plan['target']}
        path = Path(plan['target'])
        with tempfile.TemporaryDirectory(prefix='anodize-stage-') as tmp:
            stage = Path(tmp) / 'theme'
            if exists(path):
                shutil.copytree(path, stage, symlinks=True)
            else:
                stage.mkdir()
            # Refuse links/special objects before touching the staged copy.
            for node in stage.rglob('*'):
                if node.is_symlink() or not (node.is_dir() or node.is_file()):
                    raise ValueError('theme contains a symlink or special object')
            for name, content in plan['files'].items():
                dest = stage / name
                dest.parent.mkdir(exist_ok=True, parents=True)
                dest.write_bytes(content)
            return self.store().apply('anodize-' + plan['action'], [{'path': str(path), 'source': str(stage)}], plan['guards'], retain=True)

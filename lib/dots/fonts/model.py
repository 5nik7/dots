"""Read-only font inventory and guarded plans; all durable writes use Store."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import sys

LIB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LIB / 'files'))
from transactions import Store, digest, exists, parents_safe
from file_platform import state_root
from platform_info import detect


def token(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()[:24]


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read_text(path):
    with Path(path).open(encoding='utf-8', newline='') as stream:
        return stream.read()


def read(path, default):
    path = Path(path)
    parents_safe(path)
    if not exists(path): return deepcopy(default)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 32 * 1024 * 1024:
        raise ValueError('invalid font metadata file: ' + str(path))
    try: data = json.loads(path.read_text(encoding='utf-8'))
    except (ValueError, UnicodeError): raise ValueError('invalid font metadata: ' + str(path)) from None
    if not isinstance(data, dict) or data.get('schema') != 1:
        raise ValueError('unsupported font metadata schema')
    return data


def relative(value):
    if (not isinstance(value, str) or not value or '\\' in value
            or any(ord(c) < 32 for c in value) or Path(value).is_absolute()
            or any(p in ('', '.', '..') for p in value.split('/'))):
        raise ValueError('unsafe font library path')
    return value


def license_file(name):
    lower = name.lower()
    return 'license' in lower or 'licence' in lower or name.upper() in ('OFL.TXT','COPYING','COPYRIGHT','NOTICE')


class Library:
    def __init__(self, *, platform=None, directory=None):
        self.platform = platform or detect()['platform']
        self.home = Path(os.environ.get('HOME') or Path.home())
        self.state = state_root()
        self.data = Path(os.environ.get('XDG_DATA_HOME') or
            (os.environ.get('LOCALAPPDATA', self.home / 'AppData/Local') if self.platform == 'windows'
             else self.home / '.local/share')) / 'dots/fonts'
        self.cache = Path(os.environ.get('XDG_CACHE_HOME') or
            (os.environ.get('LOCALAPPDATA', self.home / 'AppData/Local') if self.platform == 'windows'
             else self.home / '.cache')) / 'dots/fonts'
        if not all(p.is_absolute() for p in (self.home, self.state, self.data, self.cache)):
            raise ValueError('font roots must be absolute')
        self.path = self.state / 'fonts/collection.json'
        self.directory=None
        self.directory_key=None
        self.input_guards={}
        if directory:
            from fonts.destinations import Destinations, key
            destinations=Destinations()
            self.directory,self.directory_names=destinations.resolve(str(directory))
            self.directory_key=key(self.directory)
            self.input_guards=destinations.guards
            self.data=self.directory/'.dots-fonts'
        self.catalog_path = self.cache / 'catalog.json'
        self.guard = digest(self.path)
        self.catalog_guard = digest(self.catalog_path)
        self.collection = read(self.path, dict(schema=1, families={}, targets={}))
        if any(not isinstance(self.collection.get(k),dict) for k in ('families','targets')):
            raise ValueError('invalid font collection')
        if any(not isinstance(row,dict) for key in ('families','targets') for row in self.collection[key].values()):
            raise ValueError('invalid font collection entry')
        directories=self.collection.get('directories',{})
        if not isinstance(directories,dict):raise ValueError('invalid font directory inventories')
        self.document=(deepcopy(directories.get(self.directory_key,dict(schema=1,families={},targets={})))
                       if self.directory else self.collection)
        self.catalog = read(self.catalog_path, dict(schema=1, families={}, glyphs={}))
        if digest(self.path) != self.guard: raise ValueError('font collection changed while reading')
        if digest(self.catalog_path) != self.catalog_guard: raise ValueError('font catalog changed while reading')
        for doc, fields in ((self.document, ('families', 'targets')), (self.catalog, ('families', 'glyphs'))):
            if not isinstance(doc,dict) or doc.get('schema')!=1 or any(not isinstance(doc.get(f), dict) for f in fields): raise ValueError('invalid font inventory')
        self.families = self.document['families']
        self.verified_payloads = set()
        for identity, row in self.families.items():
            if not re.fullmatch(r'(nerd|google|local):[^\x00-\x1f]+', identity): raise ValueError('invalid font identity')
            if not isinstance(row, dict) or not isinstance(row.get('versions'), dict): raise ValueError('invalid font family')
            for version, item in row['versions'].items():
                if not isinstance(version, str) or not isinstance(item, dict) or not isinstance(item.get('fonts'), list) or not item['fonts']:
                    raise ValueError('invalid font version')
                if 'partial' in item and not isinstance(item['partial'],bool):raise ValueError('invalid partial font coverage')
                known=item.get('known_fonts',[])
                if not isinstance(known,list):raise ValueError('invalid known font coverage')
                for font in item['fonts']+known:
                    if not isinstance(font, dict) or any(not isinstance(font.get(k), str) for k in ('file','family','style','full_name','variant','sha256')):
                        raise ValueError('invalid font face')
                    relative(font['file'])
                    if not re.fullmatch('[a-f0-9]{64}', font['sha256']): raise ValueError('invalid font digest')
                if not isinstance(item.get('payload_digest'), str): raise ValueError('invalid font payload digest')
                if 'available' in item and (not self.directory or not isinstance(item['available'],bool)):
                    raise ValueError('invalid directory font availability')
            installed = row.get('installed')
            if installed and (not isinstance(installed,dict) or installed.get('version') not in row['versions'] or not isinstance(installed.get('files'),list)):
                raise ValueError('invalid font installation')
        for ref in self.document['targets'].values():
            if not isinstance(ref,dict) or any(not isinstance(ref.get(k),str) for k in ('id','version','face','path','after','target')):
                raise ValueError('invalid application font selection')
            if ref['id'] not in self.families or ref['version'] not in self.families[ref['id']]['versions']:
                raise ValueError('application font selection has no saved version')
        adoptions=self.document.get('adoptions',{})
        if not isinstance(adoptions,dict):raise ValueError('invalid installed font adoptions')
        for key,ref in adoptions.items():
            if not isinstance(ref,dict) or any(not isinstance(ref.get(k),str) for k in ('id','version','face','path','after')):
                raise ValueError('invalid installed font adoption')
            if key!='installed:'+token(os.path.normcase(os.path.abspath(ref['path']))):raise ValueError('invalid installed font identity')
            row=self.families.get(ref['id'],{}).get('versions',{}).get(ref['version'],{})
            if not any(f['file']==ref['face'] for f in row.get('fonts',[])):raise ValueError('adopted font has no saved face')
        for row in self.catalog['families'].values():
            if not isinstance(row,dict) or not isinstance(row.get('versions'),dict) or row.get('latest') not in row['versions']:
                raise ValueError('invalid font catalog family')

    def folder(self, identity, version):
        return self.data / 'library' / token(identity) / token(version)

    def resolve(self, query, *, available=False):
        rows = dict(self.catalog['families']) if available else {}
        rows.update(self.families)
        if query in rows: return query
        needle = query.casefold().replace(' ', '')
        found = [key for key, row in rows.items() if needle in (key + ' ' + row.get('name', '')).casefold().replace(' ', '')]
        if len(found) != 1: raise ValueError('font selection is ambiguous' if found else 'font not found; use fonts search or update')
        return found[0]

    def version(self, identity, version=None):
        if identity not in self.families: raise ValueError('font is not downloaded')
        row = self.families[identity]
        version = version or (row.get('installed') or {}).get('version') or row.get('preferred')
        if version not in row['versions']: raise ValueError('font version is not downloaded')
        if row['versions'][version].get('available') is False:raise ValueError('font version was uninstalled from this directory; install it again')
        return version, row['versions'][version]

    def file(self, identity, version, font):
        if self.families[identity]['versions'][version].get('available') is False:
            raise ValueError('font version was uninstalled from this directory; install it again')
        folder = self.folder(identity, version)
        if (identity, version) not in self.verified_payloads:
            record = self.families[identity]['versions'][version]
            if folder.is_symlink() or digest(folder) != record.get('payload_digest'):
                raise ValueError('font payload directory changed; preserve and review it')
            self.verified_payloads.add((identity, version))
        path = folder / relative(font['file'])
        parents_safe(path)
        if path.is_symlink() or not path.is_file() or sha(path) != font['sha256']:
            raise ValueError('font payload is missing or changed; import or download again')
        return path

    def active(self):
        if not self.directory:return []
        rows=[dict(selection=target,**ref) for target,ref in self.collection['targets'].items()
              if ref.get('directory')==self.directory_key]
        for identity,row in self.collection['families'].items():
            installed=row.get('installed') or {}
            if installed.get('directory')==self.directory_key:
                rows.append(dict(id=identity,version=installed['version'],variant=installed['variant'],selection='user-fonts',directory=self.directory_key))
        return rows

    def transaction_action(self, action):
        return 'fonts-'+('directory-'+token(self.directory_key)+'-' if self.directory else '')+action

    def rows(self, *, available=False):
        rows = dict(self.catalog['families']) if available else {}
        active=self.active() if self.directory else []
        for identity, row in self.families.items():
            upstream = rows.get(identity, {})
            rows[identity] = dict(upstream, **row)
            rows[identity]['versions'] = dict(upstream.get('versions',{}), **row['versions'])
            if self.directory:
                rows[identity]['stored_versions']=[v for v,r in row['versions'].items() if r.get('available',True)]
                rows[identity]['active']=[r for r in active if r['id']==identity]
        return [dict(id=identity, **row) for identity, row in sorted(rows.items())]


class Plan:
    def __init__(self, library):
        self.library = library
        self.document = deepcopy(library.document)
        self.operations = []
        self.guards = {str(library.path): library.guard, str(library.catalog_path): library.catalog_guard, **library.input_guards}
        self.items = []
        self.refresh = set()
        self.payloads = {}

    def file(self, identity, version, font):
        folder = self.payloads.get((identity, version))
        path = folder / relative(font['file']) if folder else self.library.file(identity, version, font)
        if not folder:
            self.guards[str(self.library.folder(identity,version))] = self.library.families[identity]['versions'][version]['payload_digest']
        self.guard(path)
        return path

    def guard(self, path):
        path = str(path)
        parents_safe(path)
        self.guards.setdefault(path, digest(path))
        return self.guards[path]

    def put(self, path, **operation):
        path = Path(path)
        if 'data' in operation:
            if len(json.dumps(operation['data'],ensure_ascii=True).encode()) > 32*1024*1024:
                raise ValueError('font metadata exceeds its 32 MiB limit; existing state is unchanged')
        before = self.guard(path)
        if 'source' in operation:
            source = Path(operation['source'])
            after = self.guard(source)
            operation['source'] = str(source)
            if before == after and 'font_registry' not in operation: return
        elif 'text' in operation and path.is_file() and not path.is_symlink():
            if read_text(path) == operation['text']: return
        elif 'data' in operation and path.is_file() and not path.is_symlink():
            if json.loads(path.read_text()) == operation['data'] and 'font_registry' not in operation: return
        elif operation.get('delete') and before is None and 'font_registry' not in operation: return
        elif 'link' in operation and path.is_symlink() and os.readlink(path) == operation['link']: return
        row = dict(path=str(path), **operation)
        existing = next((i for i, op in enumerate(self.operations) if op['path'] == str(path)), None)
        if existing is None: self.operations.append(row)
        else: self.operations[existing] = row

    def finish(self):
        if self.document != self.library.document:
            if self.library.directory:
                collection=deepcopy(self.library.collection)
                collection.setdefault('directories',{})[self.library.directory_key]=self.document
            else:collection=self.document
            self.put(self.library.path, data=collection)
        return self

    def report(self):
        return dict(schema=1, status='preview', items=self.items,
                    operations=[dict(path=op['path'], kind='registration' if 'font_registry' in op else
                        'delete' if op.get('delete') else 'link' if 'link' in op else 'write') for op in self.operations])

    def apply(self, action):
        result = Store(self.library.state).apply(self.library.transaction_action(action), self.operations, self.guards, retain=True)
        return dict(schema=1, status=result['status'], transaction=result.get('id'), items=self.items)


def metadata(path):
    try: from fontTools.ttLib import TTFont
    except ImportError:
        raise ValueError('font parsing requires fontTools; install tools/requirements-fonts.txt in your Python environment') from None
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.suffix.lower() not in ('.ttf', '.otf') or path.stat().st_size > 64 * 1024 * 1024:
        raise ValueError('expected a regular TTF/OTF font of at most 64 MiB')
    try:
        with TTFont(path, lazy=False) as font:
            names = font['name']
            family = names.getBestFamilyName()
            style = names.getBestSubFamilyName() or 'Regular'
            full = names.getDebugName(4) or (family + ' ' + style)
            if not family or any(ord(c) < 32 for c in family + style + full): raise ValueError('invalid font names')
            mono = bool(getattr(font.get('post'), 'isFixedPitch', 0))
            variant = 'mono' if re.search(r'(Nerd Font Mono|NFM)\b', family) else 'propo' if re.search(r'(Nerd Font Propo|NFP)\b', family) else 'nerd' if re.search(r'(Nerd Font|NF)\b', family) else 'original'
            axes = [dict(tag=a.axisTag, minimum=a.minValue, default=a.defaultValue, maximum=a.maxValue)
                    for a in font['fvar'].axes] if 'fvar' in font else []
            return dict(file=path.name, family=family, style=style, full_name=full, variant=variant,
                        monospace=mono, variable=bool(axes), axes=axes, sha256=sha(path))
    except (OSError, ValueError): raise
    except Exception as error: raise ValueError('invalid font file: ' + path.name) from error

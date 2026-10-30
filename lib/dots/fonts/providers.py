"""Bounded downloads from official upstreams; no network on inventory reads."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import time
from urllib.parse import quote, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import URLError
import zipfile

from fonts.model import metadata, relative, license_file
from progress import tracked

HOSTS = {'api.github.com', 'github.com', 'raw.githubusercontent.com', 'objects.githubusercontent.com',
         'release-assets.githubusercontent.com'}
API = 'https://api.github.com/repos/'


def url(value):
    parsed = urlsplit(value)
    if parsed.scheme != 'https' or parsed.hostname not in HOSTS or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError('font download URL is not an approved upstream')
    return value


class Redirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return super().redirect_request(req, fp, code, msg, headers, url(newurl))


@tracked('Reading upstream font data')
def fetch(address, *, output=None, limit=32 * 1024 * 1024):
    started = time.monotonic()
    request = Request(url(address), headers={'User-Agent': 'dots-fonts', 'Accept': 'application/vnd.github+json'})
    try:
        with build_opener(Redirect()).open(request, timeout=30) as response:
            url(response.url)
            chunks, size = [], 0
            stream = Path(output).open('xb') if output else None
            try:
                while True:
                    block = response.read(256 * 1024)
                    if not block: break
                    size += len(block)
                    if size > limit or time.monotonic() - started > 180: raise ValueError('font download exceeds its size or time limit')
                    if stream: stream.write(block)
                    else: chunks.append(block)
            finally:
                if stream: stream.close()
        return Path(output) if output else b''.join(chunks)
    except (URLError, TimeoutError, OSError):
        raise ValueError('upstream request failed or was rate limited; saved catalogs and fonts remain available') from None


def get(address):
    try:
        data = json.loads(fetch(address))
        if not isinstance(data,dict): raise ValueError('invalid upstream JSON object')
        return data
    except (UnicodeError, json.JSONDecodeError): raise ValueError('invalid upstream JSON') from None


def tree(repo, revision):
    data = get(API + repo + '/git/trees/' + quote(revision, safe=''))
    if data.get('truncated') or not isinstance(data.get('tree'), list): raise ValueError('incomplete upstream font tree')
    return data['tree']


def nerd(version=None):
    endpoint = 'tags/' + quote(version, safe='') if version else 'latest'
    release = get(API + 'ryanoasis/nerd-fonts/releases/' + endpoint)
    revision = release.get('tag_name')
    if not isinstance(revision, str) or not re.fullmatch(r'v?\d+\.\d+\.\d+(?:[-.][A-Za-z0-9]+)*', revision):
        raise ValueError('invalid Nerd Fonts release')
    families = {}
    for asset in release.get('assets', []):
        name = asset.get('name', '')
        if not name.endswith('.zip') or name in ('FontPatcher.zip',): continue
        family = name[:-4]
        if not re.fullmatch('[A-Za-z0-9_.-]+', family): continue
        item = dict(version=revision, url=url(asset['browser_download_url']), fingerprint=asset.get('digest') or '',
                    size=asset.get('size'), provider='nerd')
        families['nerd:' + family] = dict(name=family, provider='nerd', latest=revision, versions={revision: item})
    if not families: raise ValueError('upstream release contains no font archives')
    glyphs = get('https://raw.githubusercontent.com/ryanoasis/nerd-fonts/' + quote(revision, safe='') + '/glyphnames.json')
    return families, {revision: validate_glyphs(glyphs)}


def validate_glyphs(data):
    if not isinstance(data, dict) or len(data) > 100000: raise ValueError('invalid Nerd Fonts glyph index')
    out = []
    for name, item in data.items():
        if name == 'METADATA': continue
        if not isinstance(item, dict) or not re.fullmatch(r'[a-zA-Z0-9_-]+', name): raise ValueError('invalid glyph record')
        try: point = int(item['code'], 16)
        except (KeyError, TypeError, ValueError): raise ValueError('invalid glyph codepoint') from None
        if not (0xE000 <= point <= 0xF8FF or 0xF0000 <= point <= 0xFFFFD or 0x100000 <= point <= 0x10FFFD
                or 0x20 <= point <= 0xD7FF or 0xF900 <= point <= 0xFFFD):
            raise ValueError('invalid glyph codepoint')
        glyph = chr(point)
        if item.get('char', glyph) != glyph: raise ValueError('glyph/codepoint mismatch')
        out.append(dict(name=name, collection=name.split('-', 1)[0], codepoint=f'U+{point:04X}', glyph=glyph))
    if not out: raise ValueError('empty glyph index')
    return out


def google():
    commit = get(API + 'google/fonts/commits/main').get('sha', '')
    if not re.fullmatch('[a-f0-9]{40}', commit): raise ValueError('invalid Google Fonts revision')
    families = {}
    for group in tree('google/fonts', commit):
        if group['path'] not in ('ofl', 'apache', 'ufl') or group['type'] != 'tree': continue
        for family in tree('google/fonts', group['sha']):
            if family['type'] != 'tree': continue
            path = relative(group['path'] + '/' + family['path'])
            families['google:' + path] = dict(name=family['path'], provider='google', latest=commit,
                versions={commit: dict(version=commit, tree=family['sha'], path=path, fingerprint=family['sha'], provider='google')})
    if not families: raise ValueError('upstream Google Fonts catalog is empty')
    return families, {}


def refresh(catalog, source='all', version=None):
    if version and source != 'nerd': raise ValueError('--version refresh requires --source nerd')
    from copy import deepcopy
    result = deepcopy(catalog)
    for provider in ('nerd', 'google') if source == 'all' else (source,):
        families, glyphs = nerd(version) if provider == 'nerd' else google()
        for identity, row in families.items():
            old = result['families'].get(identity, {})
            row['versions'] = dict(old.get('versions', {}), **row['versions'])
            if version and old.get('latest'): row['latest'] = old['latest']
            result['families'][identity] = row
        result['glyphs'].update(glyphs)
        if glyphs: result['glyph_version'] = next(iter(glyphs))
    result['updated'] = datetime.now(timezone.utc).isoformat()
    return result


def extract(archive, destination):
    try: _extract(archive, destination)
    except (zipfile.BadZipFile, RuntimeError): raise ValueError('invalid or encrypted font archive') from None


def _extract(archive, destination):
    total, seen = 0, set()
    with zipfile.ZipFile(archive) as zipped:
        if len(zipped.infolist()) > 5000: raise ValueError('font archive has too many entries')
        for entry in zipped.infolist():
            name = entry.filename.rstrip('/')
            relative(name)
            mode = entry.external_attr >> 16
            if stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR)):
                raise ValueError('font archive contains an unsafe object')
            total += entry.file_size
            if total > 1024 * 1024 * 1024: raise ValueError('expanded font archive is too large')
            if entry.is_dir(): continue
            leaf = PurePosixPath(name).name
            if not (leaf.lower().endswith(('.ttf', '.otf')) or license_file(leaf)): continue
            if leaf.casefold() in seen: raise ValueError('font archive contains colliding filenames')
            seen.add(leaf.casefold())
            with zipped.open(entry) as source, (destination / leaf).open('xb') as target:
                shutil.copyfileobj(source, target, 256 * 1024)


def download(identity, spec, destination, *, keep_archive=False):
    destination.mkdir()
    if spec['provider'] == 'nerd':
        archive = destination.with_name(destination.name + '.zip')
        fetch(spec['url'], output=archive, limit=256 * 1024 * 1024)
        expected = spec.get('fingerprint', '')
        if expected.startswith('sha256:'):
            from fonts.model import sha
            if sha(archive) != expected[7:]: raise ValueError('upstream archive digest mismatch')
        extract(archive, destination)
        if keep_archive: shutil.copyfile(archive, destination / 'upstream.zip')
    else:
        entries=tree('google/fonts', spec['tree'])
        if len(entries)>5000:raise ValueError('Google Fonts family contains too many entries')
        total=0
        for item in entries:
            name = item['path']
            relative(name)
            if item['type'] != 'blob' or '/' in name: continue
            if not (name.lower().endswith(('.ttf', '.otf')) or license_file(name)): continue
            address = 'https://raw.githubusercontent.com/google/fonts/' + spec['version'] + '/' + quote(spec['path'] + '/' + name)
            fetch(address, output=destination / name, limit=64 * 1024 * 1024)
            total+=(destination/name).stat().st_size
            if total>1024*1024*1024:raise ValueError('Google Fonts family exceeds 1 GiB')
    fonts = [metadata(p) for p in sorted(destination.iterdir()) if p.suffix.lower() in ('.ttf', '.otf')]
    if not fonts: raise ValueError('download contains no usable fonts')
    licenses = [p.name for p in destination.iterdir() if p.suffix.lower() not in ('.ttf', '.otf', '.zip')]
    if not licenses: raise ValueError('download has no license; retained library was not changed')
    return dict(fonts=fonts, licenses=licenses, provider=spec['provider'], fingerprint=spec.get('fingerprint', ''),
                provenance=dict(source=identity, revision=spec['version'], url=spec.get('url', 'https://github.com/google/fonts')))

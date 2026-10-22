"""Weather data, bounded providers and a private, on-demand cache. No daemon."""
from contextlib import contextmanager
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import tomllib
import urllib

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'lib/dots/files'))
from file_platform import config_root, open_nofollow, lock as lock_file
from transactions import private_directory

LIMIT = 4 * 1024 * 1024
VERSION = '1.2.0'
FIELDS = ('location', 'attribution', 'condition', 'code', 'icon', 'temperature', 'unit', 'feels_like',
          'humidity', 'wind', 'wind_unit', 'wind_direction', 'precipitation', 'precipitation_unit',
          'sunrise', 'sunset', 'daylight', 'age', 'stale', 'stale_marker')


class Unavailable(ValueError):
    def __init__(self, message, retry=60):
        super().__init__(message)
        self.retry = max(60, min(86400, retry))


def load_json(raw):
    def invalid_constant(_):
        raise ValueError('non-finite JSON number')
    return json.loads(raw, parse_constant=invalid_constant)


def read_regular(path, limit=LIMIT):
    fd = open_nofollow(path, os.O_RDONLY | getattr(os, 'O_NONBLOCK', 0))
    with os.fdopen(fd, 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError('expected a regular file')
        data = stream.read(limit + 1)
        if len(data) > limit:
            raise ValueError('file exceeds size limit')
        return data


def config(path=None):
    user = config_root() / 'wttr/config.toml'
    selected = Path(path).absolute() if path else user if user.exists() else ROOT / 'config/wttr/config.toml'
    # Managed directory links are supported; the final config must be regular.
    data = tomllib.loads(read_regular(selected.resolve(), 128 * 1024).decode('utf-8'))
    for key, default in [('default_location', ''), ('units', 'us'), ('language', 'en'),
                         ('days', 3), ('timeout', 20), ('ttl', 900), ('max_stale', 21600),
                         ('location_max_age', 86400), ('widget', '{icon} {temperature}{unit}{stale_marker}')]:
        data.setdefault(key, default)
    if data['units'] not in ('us', 'metric'):
        raise ValueError('config units must be us or metric')
    for key, low, high in [('days', 1, 3), ('timeout', 1, 60), ('ttl', 60, 86400),
                           ('max_stale', 60, 86400), ('location_max_age', 0, 86400)]:
        if type(data[key]) is not int or not low <= data[key] <= high:
            raise ValueError('invalid config ' + key)
    if data['max_stale'] < data['ttl']:
        raise ValueError('max_stale must be at least ttl')
    data['default_location'] = validate_location(data['default_location'], empty=True)
    validate_language(data['language'])
    if not isinstance(data['widget'], str):
        raise ValueError('widget must be a string')
    for group in ('icons', 'night_icons'):
        icons = data.setdefault(group, {})
        if not isinstance(icons, dict) or any(not isinstance(v, str) or len(v) > 16 or clean(v) != v for v in icons.values()):
            raise ValueError('invalid ' + group)
    from styling import validate_config
    validate_config(data)
    return selected, data


def clean(value):
    # Keep Nerd Font PUA while disallowing terminal controls, bidi and line breaks.
    import unicodedata
    return ''.join(c for c in str(value) if not unicodedata.category(c).startswith('C') or unicodedata.category(c) == 'Co')[:1024]


def validate_location(value, empty=False):
    if not isinstance(value, str) or len(value) > 200 or clean(value) != value or (not empty and not value.strip()):
        raise ValueError('location must be nonempty text of at most 200 characters')
    return value.strip()


def validate_language(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-z]{2,3}(?:-[A-Za-z]{2,4})?', value):
        raise ValueError('language must be a language code such as en or pt-br')
    return value


def validate_weather(data):
    if not isinstance(data, dict):
        raise Unavailable('invalid weather response')
    current, days = data.get('current_condition'), data.get('weather')
    if not isinstance(current, list) or not current or not isinstance(current[0], dict) or not isinstance(days, list) or not days or not all(isinstance(d, dict) for d in days):
        raise Unavailable('invalid weather response')
    if not re.fullmatch(r'\d{3}', str(current[0].get('weatherCode', ''))):
        raise Unavailable('invalid weather condition')
    return data


def bounded_command(command, timeout, limit=LIMIT):
    """Bound elapsed time and retained output, including child stderr suppression."""
    with tempfile.TemporaryFile() as output:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=output,
                                   stderr=subprocess.DEVNULL, start_new_session=os.name != 'nt')
        deadline = time.monotonic() + timeout
        try:
            while process.poll() is None:
                if time.monotonic() >= deadline:
                    raise Unavailable('provider timed out')
                if os.fstat(output.fileno()).st_size > limit:
                    raise Unavailable('provider output exceeds size limit')
                time.sleep(.02)
            output.seek(0)
            result = output.read(limit + 1)
            if len(result) > limit:
                raise Unavailable('provider output exceeds size limit')
            if process.returncode:
                raise Unavailable('provider unavailable')
            return result
        finally:
            # A helper may leave descendants even after its direct process exits.
            if os.name != 'nt':
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            elif process.poll() is None:
                process.kill()
            process.wait()


def geo_helper():
    if not (os.environ.get('TERMUX_VERSION') or 'com.termux' in os.environ.get('PREFIX', '')):
        return None
    found = shutil.which('termux-geo')
    adjacent = ROOT / 'androidots/bin/termux-geo'
    return found or (str(adjacent) if adjacent.is_file() else None)


def resolve_location(explicit, cfg, background, timeout):
    if explicit:
        return explicit, 'manual', ''
    if cfg['default_location']:
        return cfg['default_location'], 'default', ''
    helper = geo_helper()
    if helper:
        geo_timeout = min(timeout, 1) if background else timeout / 2
        args = [helper, '--json']
        args += ['--max-age', str(cfg['location_max_age']), '--cached'] if background else ['--timeout', str(max(1, int(geo_timeout)))]
        try:
            data = load_json(bounded_command(args, geo_timeout, 64 * 1024))
            if isinstance(data, dict) and type(data.get('version')) is int and data['version'] == 1:
                city = validate_location(data.get('city'))
                attribution = data.get('attribution')
                if attribution is not None and not isinstance(attribution, str):
                    raise ValueError('invalid location attribution')
                return city, 'cached city' if background else 'city', clean(attribution or '')
        except (OSError, ValueError, UnicodeError, RecursionError):
            pass
    raise Unavailable('city unavailable; run termux-geo --json, set default_location or pass --location')


def fetch(location, language, timeout):
    # A separate bounded process covers DNS stalls and slow streaming bodies too.
    result = bounded_command([sys.executable, '-B', str(Path(__file__).with_name('cli.py')),
                              '--_fetch', location, language, str(timeout)], timeout)
    try:
        envelope = load_json(result)
        if 'error' in envelope:
            raise Unavailable(envelope['error'], envelope.get('retry', 60))
        return validate_weather(envelope['data'])
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise Unavailable('invalid weather response') from error


def http_fetch(location, language, timeout):
    # Cached/bar reads do not need TLS, HTTP, email or proxy setup imports.
    import urllib.error
    import urllib.parse
    import urllib.request
    url = 'https://wttr.in/' + urllib.parse.quote(location, safe='') + '?' + urllib.parse.urlencode({'format': 'j1', 'lang': language})
    request = urllib.request.Request(url, headers={'User-Agent': 'dots-wttr/' + VERSION, 'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(LIMIT + 1)
        if len(raw) > LIMIT:
            raise Unavailable('weather response exceeds size limit')
        return {'data': validate_weather(load_json(raw))}
    except urllib.error.HTTPError as error:
        retry = error.headers.get('Retry-After', '60')
        try:
            seconds = int(retry)
        except ValueError:
            from email.utils import parsedate_to_datetime
            try:
                seconds = int(parsedate_to_datetime(retry).timestamp() - time.time())
            except (TypeError, ValueError, OverflowError):
                seconds = 60
        error.close()
        return {'error': 'weather service returned HTTP ' + str(error.code), 'retry': max(60, min(seconds, 86400))}
    except (OSError, ValueError, UnicodeError, RecursionError):
        return {'error': 'weather request failed', 'retry': 60}


def cache_root():
    home = Path.home()
    base = Path(os.environ.get('XDG_CACHE_HOME') or
                (Path(os.environ.get('LOCALAPPDATA', home / 'AppData/Local')) / 'cache' if os.name == 'nt' else home / '.cache'))
    if not base.is_absolute():
        raise ValueError('cache root must be absolute')
    return base / 'wttr'


def atomic(path, data):
    private_directory(path.parent)
    payload = json.dumps(data, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
    if len(payload.encode('utf-8')) > LIMIT:
        raise ValueError('cache record exceeds size limit')
    fd, name = tempfile.mkstemp(prefix='.wttr-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise ValueError('unsafe cache target')
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


class Cache:
    def __init__(self, cfg, explicit=None):
        self.cfg, self.explicit = cfg, explicit
        identity = ['city-v2', explicit or 'auto', bool(explicit), cfg['default_location'], cfg['language']]
        self.path = cache_root() / (hashlib.sha256(json.dumps(identity).encode()).hexdigest() + '.json')

    def read(self):
        try:
            row = load_json(read_regular(self.path))
            if not isinstance(row, dict) or row.get('schema') != 2:
                return {}
            for field in ('updated', 'retry_at', 'lease'):
                if type(row.get(field, 0)) not in (int, float) or not math.isfinite(row.get(field, 0)):
                    return {}
            if row.get('data'):
                validate_weather(row['data'])
            return row
        except (OSError, ValueError, TypeError, RecursionError):
            return {}

    def age(self, row):
        updated = row.get('updated', 0)
        age = time.time() - updated
        return age if updated > 0 and age >= 0 else float('inf')

    def usable(self, row, stale=False):
        return bool(row.get('data')) and self.age(row) <= self.cfg['max_stale' if stale else 'ttl']

    @contextmanager
    def locked(self):
        private_directory(self.path.parent)
        fd = open_nofollow(self.path.with_suffix('.lock'), os.O_CREAT | os.O_RDWR)
        with os.fdopen(fd, 'r+b') as handle:
            lock_file(handle)
            yield

    def refresh(self, background=False, force=False):
        # Nonblocking lock: competing callers can use retained data or retry.
        with self.locked():
            row = self.read()
            now = time.time()
            if not force and (self.usable(row) or now < row.get('retry_at', 0)):
                return row
            try:
                started = time.monotonic()
                location, source, attribution = resolve_location(self.explicit, self.cfg, background, self.cfg['timeout'])
                remaining = self.cfg['timeout'] - (time.monotonic() - started)
                if remaining <= 0:
                    raise Unavailable('location timed out')
                data = fetch(location, self.cfg['language'], remaining)
                fresh = dict(schema=2, updated=time.time(), data=data, source=source, location=location, attribution=attribution,
                             lease=0, retry_at=0)
                if len(json.dumps(fresh, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')) > LIMIT:
                    raise Unavailable('weather record exceeds size limit')
                row = fresh
            except (OSError, ValueError) as error:
                row.update(schema=2, lease=0, retry_at=now + getattr(error, 'retry', 60),
                           error=str(error) if isinstance(error, Unavailable) else 'weather refresh failed')
                atomic(self.path, row)
                raise Unavailable(row['error']) from error
            atomic(self.path, row)
            return row

    def schedule(self, config_path):
        try:
            with self.locked():
                row = self.read()
                now = time.time()
                if self.usable(row) or now < max(row.get('retry_at', 0), row.get('lease', 0)):
                    return
                row.update(schema=2, lease=now + self.cfg['timeout'] + 10)
                atomic(self.path, row)
                payload = json.dumps({'config': str(config_path), 'location': self.explicit,
                                      'language': self.cfg['language'], 'timeout': self.cfg['timeout']})
                options = {'start_new_session': True} if os.name != 'nt' else {'creationflags': subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP}
                subprocess.Popen([sys.executable, '-B', str(Path(__file__).with_name('cli.py')), '--_worker', payload],
                                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **options)
        except (OSError, ValueError):
            pass


def astronomy(data, now=None):
    now = now or datetime.now()
    days = [day for day in data.get('weather', []) if day.get('date') == now.date().isoformat()]
    try:
        solar = days[0]['astronomy'][0]
        rise, setting = solar['sunrise'], solar['sunset']
        start, end = (datetime.strptime(v, '%I:%M %p').time() for v in (rise, setting))
        if start >= end:
            return '', '', 'unknown'
        return rise, setting, 'day' if start <= now.time() < end else 'night'
    except (ValueError, KeyError, IndexError, TypeError):
        return '', '', 'unknown'


def first_value(values):
    return clean(values[0].get('value', '')) if isinstance(values, list) and values and isinstance(values[0], dict) else ''


def fields(row, cfg, age=0, icons=True, now=None):
    data = row.get('data') or {}
    current = (data.get('current_condition') or [{}])[0]
    us = cfg['units'] == 'us'
    sunrise, sunset, daylight = astronomy(data, now)
    if age > cfg['ttl']:
        daylight = 'unknown'
    code = clean(current.get('weatherCode', ''))
    from styling import condition
    icon = condition(code, cfg, daylight == 'night')[0]
    stale = age > cfg['ttl']
    return dict(location=clean(row.get('location', '')), attribution=clean(row.get('attribution', '')),
                condition=first_value(current.get('weatherDesc')),
                code=code, icon=icon if icons else '', temperature=clean(current.get('temp_F' if us else 'temp_C', '?')),
                unit='°F' if us else '°C', feels_like=clean(current.get('FeelsLikeF' if us else 'FeelsLikeC', '?')),
                humidity=clean(current.get('humidity', '?')), wind=clean(current.get('windspeedMiles' if us else 'windspeedKmph', '?')),
                wind_unit='mph' if us else 'km/h', wind_direction=clean(current.get('winddir16Point', '')),
                precipitation=clean(current.get('precipInches' if us else 'precipMM', '?')), precipitation_unit='in' if us else 'mm',
                sunrise=sunrise, sunset=sunset, daylight=daylight, age=str(int(age)) if math.isfinite(age) else '',
                stale=str(stale).lower(), stale_marker='~' if stale else '')


def format_widget(template, values):
    import string
    if len(template) > 1024 or clean(template) != template:
        raise ValueError('template must be one line of at most 1024 characters')
    for _, field, spec, conversion in string.Formatter().parse(template):
        if field is not None and (field not in FIELDS or spec or conversion):
            raise ValueError('template accepts only literal {field} placeholders; see --fields')
    return template.format_map(values)

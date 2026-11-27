"""On-demand native Windows location and city cache for Dots."""
import argparse
from contextlib import contextmanager
from email.utils import parsedate_to_datetime
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import time
import unicodedata
from urllib.parse import urlencode, urlsplit

from files.file_platform import check_object, lock, open_nofollow


FIX_TTL = 60
ADDRESS_TTL = 86400
DEFAULT_ENDPOINT = 'https://nominatim.openstreetmap.org/reverse'
ATTRIBUTION = '© OpenStreetMap contributors, ODbL 1.0 — https://www.openstreetmap.org/copyright'


class LocationUnavailable(RuntimeError):
    """Safe, coordinate-free diagnostic for a caller."""


def cache_path():
    base = os.environ.get('XDG_CACHE_HOME')
    root = Path(base) if base else Path(os.environ.get('LOCALAPPDATA') or Path.home() / 'AppData/Local') / 'cache'
    if not root.is_absolute():
        raise LocationUnavailable('location cache root must be absolute')
    return root / 'dots/location/windows.json'


def _endpoint():
    value = os.environ.get('DOTS_LOCATION_ENDPOINT') or DEFAULT_ENDPOINT
    try:
        parts = urlsplit(value)
        if (parts.scheme == 'https' and parts.hostname and parts.path.startswith('/')
                and not parts.username and not parts.password and '@' not in parts.netloc
                and not any(c in value for c in ('?', '#', '\\'))
                and all(c.isprintable() and not c.isspace() for c in value)):
            return value
    except ValueError:
        pass
    raise LocationUnavailable('DOTS_LOCATION_ENDPOINT must be an HTTPS URL without credentials, query or fragment')


def _safe_text(value, length):
    return (isinstance(value, str) and bool(value.strip()) and len(value) <= length
            and not any(unicodedata.category(c).startswith('C') for c in value))


def _age(timestamp):
    now = time.time()
    if type(timestamp) not in (float, int) or not 0 < timestamp <= now:
        return math.inf
    return now - timestamp


def _read(path):
    try:
        with os.fdopen(open_nofollow(path, os.O_RDONLY | getattr(os, 'O_NONBLOCK', 0)), 'rb') as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise LocationUnavailable('unsafe location cache')
            raw = stream.read(65537)
        row = json.loads(raw) if len(raw) <= 65536 else None
        return row if isinstance(row, dict) and row.get('version') == 1 else {}
    except (FileNotFoundError, json.JSONDecodeError, UnicodeError, RecursionError):
        return {}


def _save(path, row):
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.location-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(row, stream, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


@contextmanager
def _locked(path):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with os.fdopen(open_nofollow(path.with_suffix('.lock'), os.O_CREAT | os.O_RDWR), 'r+b') as handle:
        try:
            lock(handle)
        except OSError as error:
            raise LocationUnavailable('another location refresh is running') from error
        yield


def _remaining(deadline):
    seconds = deadline - time.monotonic()
    if seconds <= 0:
        raise LocationUnavailable('location lookup timed out')
    return seconds


def _device_fix(timeout):
    shell = _system32() / 'WindowsPowerShell/v1.0/powershell.exe'
    command = [str(shell), '-NoLogo', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
               '-File', str(Path(__file__).with_suffix('.ps1')), str(max(1, int(timeout * 1000)))]
    try:
        result = subprocess.run(command, capture_output=True, stdin=subprocess.DEVNULL,
                                timeout=timeout, creationflags=subprocess.CREATE_NO_WINDOW)
    except subprocess.TimeoutExpired as error:
        raise LocationUnavailable('Windows Location Services timed out') from error
    if result.returncode == 3:
        raise LocationUnavailable('Windows location access is disabled or denied; check Settings > Privacy & security > Location')
    if result.returncode == 4:
        raise LocationUnavailable('Windows Location Services timed out')
    if result.returncode:
        raise LocationUnavailable('Windows Location Services could not obtain a current fix')
    try:
        fix = json.loads(result.stdout)
        lat, lon, timestamp = fix['latitude'], fix['longitude'], fix['timestamp']
        if (type(lat) in (float, int) and type(lon) in (float, int) and -90 <= lat <= 90
                and -180 <= lon <= 180 and _age(timestamp) <= FIX_TTL):
            return lat, lon, timestamp
    except (KeyError, TypeError, ValueError, UnicodeError):
        pass
    raise LocationUnavailable('Windows Location Services returned an invalid or expired fix')


class GeocodingError(LocationUnavailable):
    def __init__(self, reason, retry_after=0):
        super().__init__(reason)
        self.retry_after = retry_after


def _system32():
    system = os.environ.get('SystemRoot')
    if not system or not Path(system).is_absolute():
        raise LocationUnavailable('Windows system directory is unavailable')
    return Path(system) / 'System32'


def _retry_delay(value):
    try:
        seconds = int(value[:10]) if value.isdigit() else parsedate_to_datetime(value).timestamp() - time.time()
        return max(0, seconds)
    except (TypeError, ValueError, OverflowError):
        return 0


def _geocode(endpoint, latitude, longitude, timeout):
    # Native curl enforces a total deadline, including DNS and streaming bodies.
    curl = _system32() / 'curl.exe'
    query = urlencode(dict(lat=latitude, lon=longitude, format='jsonv2', addressdetails=1,
                           **{'accept-language': 'en'}))
    with tempfile.TemporaryDirectory(prefix='dots-location-') as directory:
        headers = Path(directory) / 'headers'
        command = [str(curl), '-q', '--silent', '--proto', '=https', '--max-time', str(timeout),
                   '--max-filesize', '131072', '--dump-header', str(headers), '--write-out', '\n%{http_code}',
                   '--user-agent', 'Dots-Windows-Location/1.0 (https://github.com/5nik7/dots)',
                   '--url', endpoint + '?' + query]
        try:
            result = subprocess.run(command, capture_output=True, stdin=subprocess.DEVNULL,
                                    timeout=timeout, creationflags=subprocess.CREATE_NO_WINDOW)
        except subprocess.TimeoutExpired as error:
            raise LocationUnavailable('city lookup timed out') from error
        if result.returncode == 28:
            raise LocationUnavailable('city lookup timed out')
        if result.returncode:
            raise LocationUnavailable('city lookup failed; check connectivity')
        raw, _, status = result.stdout.rpartition(b'\n')
        if status != b'200':
            retry = 0
            with headers.open('rb') as stream:
                for line in stream.read(65536).splitlines():
                    name, _, value = line.partition(b':')
                    if name.lower() == b'retry-after':
                        retry = max(retry, _retry_delay(value.decode('ascii', 'ignore').strip()))
            raise GeocodingError('city lookup service returned HTTP ' + str(int(status)), retry)
    try:
        response = json.loads(raw) if len(raw) <= 131072 else {}
        address = response.get('address')
        for field in ('city', 'town', 'village', 'municipality', 'hamlet'):
            if isinstance(address, dict) and _safe_text(address.get(field), 200):
                licence = response.get('licence')
                return address[field].strip(), licence if _safe_text(licence, 1024) else ATTRIBUTION
    except (ValueError, AttributeError, UnicodeError, RecursionError):
        pass
    raise LocationUnavailable('city lookup returned no usable city')


def _snapshot(row):
    if (_age(row.get('timestamp')) == math.inf or not _safe_text(row.get('city'), 200)
            or not _safe_text(row.get('attribution'), 1024)):
        return None
    result = {key: row[key] for key in ('city', 'timestamp', 'attribution')}
    result['stale'] = _age(row['timestamp']) > FIX_TTL
    return result


def _refresh(path, row, endpoint, deadline):
    lat, lon, timestamp = _device_fix(_remaining(deadline))
    # Neighbouring fixes in the same ~100 m cell can reuse their city lookup.
    key = hashlib.sha256(f'{endpoint}|{lat:.3f},{lon:.3f}'.encode()).hexdigest()
    if key == row.get('address_key') and _age(row.get('address_timestamp')) < ADDRESS_TTL and _snapshot(row):
        city, attribution = row['city'], row['attribution']
    else:
        now = time.time()
        retry_at = row.get('retry_at')
        if type(retry_at) in (int, float) and now < retry_at:
            raise LocationUnavailable('city lookup is cooling down; retry later')
        row['retry_at'] = now + 15
        row['version'] = 1
        _save(path, row)
        try:
            city, attribution = _geocode(endpoint, round(lat, 3), round(lon, 3), _remaining(deadline))
        except GeocodingError as error:
            row['retry_at'] = max(row['retry_at'], time.time() + error.retry_after)
            _save(path, row)
            raise
        row.update(address_key=key, address_timestamp=time.time())
    row.update(city=city, attribution=attribution, timestamp=timestamp)
    _save(path, row)
    return _snapshot(row)


def resolve_city(*, cached=False, refresh=False, max_age=None, timeout=10):
    if sys.platform != 'win32':
        raise LocationUnavailable('dots location requires native Windows')
    path = cache_path()
    deadline = time.monotonic() + timeout
    previous = None
    try:
        for parent in path.parents:
            check_object(parent)
            if parent.is_symlink():
                raise LocationUnavailable('unsafe location cache directory')
        row = _read(path)
        previous = _snapshot(row)
        if cached:
            if previous and (max_age is None or _age(previous['timestamp']) <= max_age):
                return previous
            raise LocationUnavailable('no eligible cached Windows city; run dots location --refresh')
        if previous and not refresh and not previous['stale']:
            return previous
        endpoint = _endpoint()
        with _locked(path):
            row = _read(path)
            previous = _snapshot(row)
            if previous and not refresh and not previous['stale']:
                return previous
            return _refresh(path, row, endpoint, deadline)
    except (OSError, ValueError, LocationUnavailable) as error:
        reason = str(error) if isinstance(error, LocationUnavailable) else 'Windows location provider or cache unavailable'
        if previous and not cached:
            return dict(previous, stale=True, warning=reason)
        raise LocationUnavailable(reason) from error


def main(argv=None):
    parser = argparse.ArgumentParser(prog='dots location', description='Find the current city using Windows Location Services.',
                                     epilog='City lookup sends approximate coordinates to Nominatim. '
                                            'Map data © OpenStreetMap contributors (openstreetmap.org/copyright).')
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--cached', action='store_true', help='read the last saved city')
    modes.add_argument('--refresh', action='store_true', help='request a fresh device fix')
    parser.add_argument('--json', action='store_true', help='print the city, fix time, freshness and attribution')
    args = parser.parse_args(argv)
    try:
        result = resolve_city(cached=args.cached, refresh=args.refresh)
    except LocationUnavailable as error:
        print(f'dots location: {error}', file=sys.stderr)
        if sys.platform == 'win32' and not args.cached:
            print('For weather, pass a city with wttr --location "City Name".', file=sys.stderr)
        return 1
    if result['stale']:
        reason = result.get('warning', 'cached fix has expired')
        print(f'dots location: using last known city ({reason})', file=sys.stderr)
    print(json.dumps(result, ensure_ascii=False) if args.json else result['city'])
    if not args.json and sys.stdout.isatty() and sys.stderr.isatty():
        print(result['attribution'], file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

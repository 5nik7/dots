"""Exercise the Windows city cache with test-owned storage and fake providers."""
from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib/dots'))
import windows_location as geo


class WindowsLocationTests(unittest.TestCase):
    def setUp(self):
        self.temp = self.enterContext(tempfile.TemporaryDirectory())
        self.enterContext(patch.dict(os.environ, {'XDG_CACHE_HOME': self.temp, 'SystemRoot': self.temp,
                                                  'DOTS_LOCATION_ENDPOINT': geo.DEFAULT_ENDPOINT}))
        self.enterContext(patch.object(sys, 'platform', 'win32'))
        self.enterContext(patch.object(subprocess, 'CREATE_NO_WINDOW', 0, create=True))
        self.now = time.time()
        self.enterContext(patch.object(time, 'time', side_effect=lambda: self.now))
        self.fix = self.enterContext(patch.object(geo, '_device_fix', side_effect=lambda _: (22.12346, -45.67654, self.now)))
        self.lookup = self.enterContext(patch.object(geo, '_geocode', return_value=('München', geo.ATTRIBUTION)))

    def test_fresh_and_forced_lookup_and_cache_only_age(self):
        first = geo.resolve_city()
        self.assertEqual(first, dict(city='München', timestamp=self.now, stale=False, attribution=geo.ATTRIBUTION))
        self.assertEqual(geo.resolve_city(), first)
        self.now += 25
        self.assertGreater(geo.resolve_city(refresh=True)['timestamp'], first['timestamp'])
        self.assertEqual(self.fix.call_count, 2)
        self.assertEqual(self.lookup.call_count, 1)
        self.assertEqual(self.lookup.call_args.args[1:3], (22.123, -45.677))
        self.assertNotIn('22.123', geo.cache_path().read_text(encoding='utf-8'))
        self.now += 61
        self.assertTrue(geo.resolve_city(cached=True)['stale'])
        with self.assertRaisesRegex(geo.LocationUnavailable, 'no eligible cached'):
            geo.resolve_city(cached=True, max_age=60)
        self.assertEqual(self.fix.call_count, 2)
        self.now += geo.ADDRESS_TTL
        self.assertFalse(geo.resolve_city()['stale'])
        self.assertEqual(self.lookup.call_count, 2)

    def test_changed_city_and_endpoint(self):
        geo.resolve_city()
        self.now += 65
        self.fix.side_effect = lambda _: (50.5, 118.4, self.now)
        self.lookup.return_value = ('Second City', geo.ATTRIBUTION)
        self.assertEqual(geo.resolve_city()['city'], 'Second City')
        self.now += 20
        with patch.dict(os.environ, {'DOTS_LOCATION_ENDPOINT': 'https://example.org/geocoding'}):
            geo.resolve_city(refresh=True)
        self.assertEqual(self.lookup.call_args.args[0], 'https://example.org/geocoding')

    def test_refresh_failure_returns_original_timestamp_and_warns(self):
        first = geo.resolve_city()
        self.now += 5
        self.fix.side_effect = geo.LocationUnavailable('device denied access')
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            self.assertEqual(geo.main(['--refresh', '--json']), 0)
        row = json.loads(stdout.getvalue())
        self.assertTrue(row['stale'])
        self.assertEqual(row['timestamp'], first['timestamp'])
        self.assertIn('device denied access', stderr.getvalue())

    def test_cache_miss_and_network_backoff(self):
        with self.assertRaisesRegex(geo.LocationUnavailable, 'no eligible cached'):
            geo.resolve_city(cached=True)
        self.fix.assert_not_called()
        self.assertFalse(geo.cache_path().parent.exists())
        self.lookup.side_effect = geo.GeocodingError('HTTP 429', retry_after=120)
        with self.assertRaisesRegex(geo.LocationUnavailable, 'HTTP 429'):
            geo.resolve_city()
        self.now += 65
        with self.assertRaisesRegex(geo.LocationUnavailable, 'cooling down'):
            geo.resolve_city()
        self.assertEqual(self.lookup.call_count, 1)
        self.now += 60
        self.lookup.side_effect = None
        self.assertEqual(geo.resolve_city()['city'], 'München')

    def test_first_device_timeout_gives_hint_then_next_lookup_recovers(self):
        with patch.object(geo, '_device_fix', REAL_FIX):
            payload = json.dumps(dict(latitude=22, longitude=-45, timestamp=self.now)).encode()
            outcomes = [subprocess.TimeoutExpired('powershell', 1), subprocess.CompletedProcess([], 0, payload)]
            stdout, stderr = io.StringIO(), io.StringIO()
            with patch.object(subprocess, 'run', side_effect=outcomes):
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    self.assertEqual(geo.main([]), 1)
                self.assertEqual(stdout.getvalue(), '')
                self.assertIn('Windows Location Services timed out', stderr.getvalue())
                self.assertIn('wttr --location', stderr.getvalue())
                self.assertFalse(geo.cache_path().exists())
                self.assertFalse(geo.resolve_city()['stale'])
                self.assertEqual(geo.resolve_city(cached=True)['city'], 'München')

    def test_native_timeouts_retain_previous_city(self):
        first = geo.resolve_city()
        self.now += geo.ADDRESS_TTL + 1
        for name, func, code, warning in (
                ('_device_fix', REAL_FIX, 4, 'Windows Location Services timed out'),
                ('_geocode', REAL_GEOCODE, 28, 'city lookup timed out')):
            for timeout in (subprocess.TimeoutExpired('provider', 1), subprocess.CompletedProcess([], code)):
                self.now += 20
                with self.subTest(name=name, timeout=type(timeout).__name__), patch.object(geo, name, func):
                    with patch.object(subprocess, 'run', side_effect=[timeout]):
                        result = geo.resolve_city()
                    self.assertEqual((result['city'], result['timestamp']), (first['city'], first['timestamp']))
                    self.assertTrue(result['stale'])
                    self.assertEqual(result['warning'], warning)

    def test_plain_interactive_output_prints_attribution_on_stderr(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr), patch.object(stdout, 'isatty', return_value=True), \
                patch.object(stderr, 'isatty', return_value=True):
            self.assertEqual(geo.main([]), 0)
        self.assertEqual(stdout.getvalue(), 'München\n')
        self.assertEqual(stderr.getvalue(), geo.ATTRIBUTION + '\n')

    def test_concurrent_refresh_uses_last_city_and_skips_provider(self):
        original = geo.resolve_city()
        self.now += 70
        with geo._locked(geo.cache_path()):
            result = geo.resolve_city()
            self.assertEqual(result['city'], original['city'])
            self.assertTrue(result['stale'])
            self.assertIn('another location refresh', result['warning'])
            self.assertEqual(self.fix.call_count, 1)

    def test_invalid_endpoint_before_network_and_non_windows_guard(self):
        for invalid in ('http://example.org/', 'https://user@example.org/', 'https://example.org/r?k=1'):
            with self.subTest(invalid=invalid), patch.dict(os.environ, {'DOTS_LOCATION_ENDPOINT': invalid}):
                with self.assertRaisesRegex(geo.LocationUnavailable, 'HTTPS URL'):
                    geo.resolve_city()
        with patch.object(sys, 'platform', 'linux'), self.assertRaisesRegex(geo.LocationUnavailable, 'native Windows'):
            geo.resolve_city()
        self.fix.assert_not_called()

    def test_malformed_and_future_cache_is_ineligible(self):
        path = geo.cache_path()
        path.parent.mkdir(parents=True)
        for value in ('no JSON', '[]', json.dumps(dict(version=1, timestamp=self.now + 60,
                                                       city='Example', attribution='source'))):
            path.write_text(value, encoding='utf-8')
            with self.assertRaisesRegex(geo.LocationUnavailable, 'no eligible cached'):
                geo.resolve_city(cached=True)
        self.lookup.assert_not_called()

    def test_command_geocoder_normalization_and_http_backoff(self):
        with patch.object(geo, '_geocode', REAL_GEOCODE):
            def respond(command, **kwargs):
                self.assertIn('Dots-Windows-Location', command[command.index('--user-agent') + 1])
                self.assertIn('lat=22.123', command[-1])
                return subprocess.CompletedProcess(command, 0, b'{"address":{"town":"Example"}}\n200')
            with patch.object(subprocess, 'run', side_effect=respond):
                self.assertEqual(geo.resolve_city()['city'], 'Example')
            self.now += geo.ADDRESS_TTL + 5
            def limited(command, **kwargs):
                Path(command[command.index('--dump-header') + 1]).write_bytes(b'Retry-After: 90\r\n')
                return subprocess.CompletedProcess(command, 0, b'err\n429')
            with patch.object(subprocess, 'run', side_effect=limited):
                self.assertTrue(geo.resolve_city()['stale'])
            self.assertGreaterEqual(json.loads(geo.cache_path().read_bytes())['retry_at'], self.now + 90)

    def test_device_rejects_expired_or_invalid_position(self):
        for latitude, timestamp in ((200, self.now), (40, self.now - 70), (True, self.now)):
            payload = json.dumps(dict(latitude=latitude, longitude=12, timestamp=timestamp)).encode()
            with patch.object(subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, payload)):
                with self.assertRaisesRegex(geo.LocationUnavailable, 'invalid or expired'):
                    REAL_FIX(2)
        with patch.object(subprocess, 'run', return_value=subprocess.CompletedProcess([], 3)):
            with self.assertRaisesRegex(geo.LocationUnavailable, 'denied'):
                REAL_FIX(2)


REAL_FIX = geo._device_fix
REAL_GEOCODE = geo._geocode

if __name__ == '__main__':
    unittest.main()

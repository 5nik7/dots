#!/usr/bin/env python3
"""Android/tmux boundary tests with owned scripts, caches and mocked providers."""
import json
import os
from pathlib import Path
import runpy
import re
import shutil
import subprocess
import sys
import time
import unittest

import test_tmux_status as status


class AndroidStatus(unittest.TestCase):
    def setUp(self):
        self.fx = status.TmuxStatus()
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.render = runpy.run_path(str(self.fx.android_adapter))['render']
        self.unknown = '?  \n'

    def run_adapter(self):
        result = subprocess.run([sys.executable, '-B', str(self.fx.android_adapter)],
                                cwd=self.fx.home, env=self.fx.env, capture_output=True,
                                text=True, timeout=4)
        self.assertEqual((result.returncode, result.stderr), (0, ''))
        self.assertNotIn('PRIVATE', result.stdout)
        plain = re.sub(r'#\[fg=(?:[a-z]+|#[0-9a-fA-F]{6})\]|#\[default\]', '', result.stdout)
        self.assertNotIn('#', plain)
        self.assertNotIn('\x1b', result.stdout)
        return plain

    def test_only_network_helpers_are_read_and_wifi_wins(self):
        self.assertEqual(self.run_adapter(), self.fx.android_text() + ' \n')
        for module in ('wifi', 'cell'):
            self.assertEqual((self.fx.home / (module + '-calls')).read_text(), 'call\n')
        for module in ('notification', 'volume', 'location'):
            self.assertFalse((self.fx.home / (module + '-calls')).exists())
        self.fx.android_scripts['cell'].unlink()
        self.assertEqual(self.run_adapter(), self.fx.android_text() + ' \n')
        self.fx.android_scripts['wifi'].unlink()
        self.assertEqual(self.run_adapter(), self.unknown)

    def test_network_visibility_matrix(self):
        for connected in (True, False, None, 'false', 0):
            for enabled in (True, False, None, 'true', 1):
                for state in ('connected', 'connecting', 'disconnected', 'suspended', None, 'unknown'):
                    wifi = dict(module='wifi', icon='\U000f0928', stale=False,
                                state='connected', data={'connected': connected, 'level': 4})
                    cell = dict(module='cell', icon='\U000f08f8', stale=False,
                                state='registered', data={'data_enabled': enabled, 'data_state': state, 'device_stale': False, 'level': 3})
                    select = runpy.run_path(str(self.fx.android_adapter))['select_network']
                    result = re.sub(r'#\[[^]]*\]', '', select([wifi, cell]))
                    if connected is True:
                        expected = '\U000f0928 '
                    elif connected is not False:
                        expected = '? '
                    elif enabled is False or state in ('connecting', 'disconnected', 'suspended'):
                        expected = ''
                    elif enabled is True and state == 'connected':
                        expected = '\U000f08fa '
                    else:
                        expected = '? '
                        self.assertIn('#[fg=brightblack]', select([wifi, cell]))
                    self.assertEqual(result, expected, (connected, enabled, state))
        self.fx.android_snapshot('wifi', connected=False, stale=True)
        self.assertEqual(self.run_adapter(), self.fx.android_text(stale=True, network='cell') + ' \n')
        self.fx.android_snapshot('wifi', connected=None)
        self.assertEqual(self.run_adapter(), self.unknown)

    def test_unknown_cell_when_wifi_is_disconnected(self):
        self.fx.android_snapshot('wifi', connected=False)
        for state in ('unknown', 'missing', 'invalid', 'timeout'):
            if state == 'unknown':
                self.fx.android_snapshot('cell', data_enabled=None, data_state=None)
            elif state == 'missing':
                self.fx.android_scripts['cell'].rename(self.fx.android_scripts['cell'].with_suffix('.saved'))
            elif state == 'invalid':
                self.fx.android_scripts['cell'].with_suffix('.saved').rename(self.fx.android_scripts['cell'])
                (self.fx.home / 'cell.json').write_text('broken')
            else:
                (self.fx.home / 'cell-delay').touch()
            self.assertEqual(self.run_adapter(), self.unknown, state)
        self.fx.android_snapshot('wifi', connected=None)
        self.assertEqual(self.run_adapter(), self.unknown)

    def test_signal_states_counts_and_stale_markers(self):
        for module in ('wifi', 'cell'):
            for level, color in enumerate(('red', 'red', 'yellow', 'green', 'green')):
                for stale in (False, True):
                    snapshot = dict(module=module, icon='\U000f0928' + ('~' if stale else ''),
                                    stale=stale, state='connected', data={'level': level})
                    result = self.render(module, snapshot)
                    self.assertIn('#[fg=' + ('brightblack' if stale else color) + ']', result)
                    self.assertEqual(len(re.sub(r'#\[[^]]*\]', '', result)), 2)
                    if module == 'cell':
                        self.assertIn('\U000f08fa', result)
        result = self.render('cell', dict(module='cell', icon='\U000f08fe?', stale=False,
                                          state='registered', data={'level': None}))
        self.assertEqual(result, '#[fg=brightblack]\U000f08fa?#[default]')
        # Only renderer-owned styles may be emitted.
        with self.assertRaises(ValueError):
            self.render('wifi', dict(module='wifi', icon='\U000f0928', stale=False, data={}),
                        ['default', 'white', 'cyan', 'red]#(bad)', 'yellow', 'green'])

    def test_stale_negative_and_independent_device_freshness(self):
        self.fx.android_snapshot('wifi', connected=False)
        # Old signal does not invalidate fresh evidence that data is disabled.
        self.fx.android_snapshot('cell', stale=True, data_enabled=False, device_stale=False)
        self.assertEqual(self.run_adapter(), '\n')
        self.fx.android_snapshot('cell', stale=True, data_enabled=False, device_stale=True)
        self.assertEqual(self.run_adapter(), '?~ \n')
        self.fx.android_snapshot('wifi', connected=False, stale=True)
        self.fx.android_snapshot('cell', data_enabled=False)
        self.assertEqual(self.run_adapter(), '?~ \n')
        self.fx.android_snapshot('wifi', connected=None)
        self.fx.android_snapshot('cell', stale=True)
        self.assertEqual(self.run_adapter(), '?~ \n')
        # Missing/invalid freshness cannot establish a fresh negative decision.
        self.fx.android_snapshot('wifi', connected=False)
        for value in (None, 0, 'false'):
            path = self.fx.home / 'cell.json'
            self.fx.android_snapshot('cell', data_enabled=False)
            result = json.loads(path.read_text())
            result['data']['device_stale'] = value
            path.write_text(json.dumps(result))
            self.assertEqual(self.run_adapter(), self.unknown)

    def test_unavailable_wifi_with_each_cell_activity(self):
        script = self.fx.android_scripts['wifi']
        original = script.read_text()
        for failure in ('missing', 'invalid', 'failed', 'timeout'):
            for enabled in (True, False, None):
                with self.subTest(failure=failure, enabled=enabled):
                    self.fx.android_snapshot('cell', data_enabled=enabled,
                                             data_state='connected' if enabled is not None else None)
                    if failure == 'missing':
                        script.unlink(missing_ok=True)
                    elif failure == 'invalid':
                        script.write_text('print("broken")\n')
                    else:
                        script.write_text(original)
                        (self.fx.home / ('wifi-' + ('fail' if failure == 'failed' else 'delay'))).touch()
                    self.assertEqual(self.run_adapter(), self.unknown)
                    for flag in ('fail', 'delay'):
                        (self.fx.home / ('wifi-' + flag)).unlink(missing_ok=True)
        script.write_text(original)
        self.fx.android_snapshot('wifi')
        self.assertEqual(self.run_adapter(), self.fx.android_text() + ' \n')

    def test_invalid_fields_and_unsafe_text_are_not_forwarded(self):
        for icon in ['', 'wifi', '#(touch BAD)', '#[fg=red]', '\x1b[31m\U000f0928',
                     '\U000f0928\n', '\U000f0928\t', '\U000f0928\x00', '\U000f0928\u200b']:
            with self.subTest(icon=repr(icon)), self.assertRaises(ValueError):
                self.render('wifi', dict(module='wifi', icon=icon, stale=False))
        for snapshot in [None, [], {}, {'module': 'cell', 'icon': '\U000f0928', 'stale': False},
                         {'module': 'wifi', 'icon': '\U000f0928~', 'stale': False},
                         {'module': 'wifi', 'icon': '\U000f0928', 'stale': 0}]:
            with self.assertRaises(ValueError):
                self.render('wifi', snapshot)
        (self.fx.home / 'wifi.json').write_text('invalid')
        (self.fx.home / 'cell-fail').touch()
        self.assertEqual(self.run_adapter(), self.unknown)

    def test_parallel_deadlines_oversized_and_invalid_encoding(self):
        for module in status.ANDROID_ICONS:
            (self.fx.home / (module + '-delay')).touch()
        started = time.monotonic()
        self.assertEqual(self.run_adapter(), self.unknown)
        self.assertLess(time.monotonic() - started, 2.5, 'two deadlines must run concurrently')
        for module in status.ANDROID_ICONS:
            (self.fx.home / (module + '-delay')).unlink()
        self.fx.android_scripts['wifi'].write_text('import sys\nsys.stdout.write("x" * (3 * 1024 * 1024))\n')
        self.fx.android_scripts['cell'].write_text('import sys\nsys.stdout.buffer.write(b"\\xff")\n')
        self.assertEqual(self.run_adapter(), self.unknown)

    def test_timeout_reaps_helper_descendants(self):
        script = self.fx.android_scripts['wifi']
        script.write_text('import subprocess, sys, os, time\nfrom pathlib import Path\n' +
                          'p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])\n' +
                          'Path(os.environ["HOME"], "child-pid").write_text(str(p.pid))\n' +
                          'time.sleep(30)\n')
        self.assertEqual(self.run_adapter(), self.unknown)
        pid = int((self.fx.home / 'child-pid').read_text())
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            try:
                state = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[0]
            except FileNotFoundError:
                break
            if state == 'Z':
                break
            time.sleep(.02)
        else:
            self.fail('fixture helper descendant survived timeout')

    def install_real_scripts_with_fake_providers(self):
        root = self.fx.repo / 'androidots'
        shutil.copytree(status.REPO / 'androidots/lib/termux_status', root / 'lib/termux_status',
                        ignore=shutil.ignore_patterns('__pycache__'))
        for module, script in self.fx.android_scripts.items():
            shutil.copyfile(status.REPO / 'androidots/bin' / script.name, script)
        provider = self.fx.home / 'provider.py'
        provider.write_text('''import os, pathlib, sys
home = pathlib.Path(os.environ['HOME'])
name = sys.argv[1]
with (home / (name + '-api-calls')).open('a') as stream: stream.write('call\\n')
if (home / (name + '-api-fail')).exists(): sys.exit(1)
print((home / (name + '-response')).read_text())
''')
        # Override ONLY the copied provider command boundary. In particular, the
        # production location command is absolute and cannot be mocked via PATH.
        source = root / 'lib/termux_status/providers.py'
        source.write_text(source.read_text() + '\n\ndef command(provider):\n' +
                          f'    return [{sys.executable!r}, {str(provider)!r}, provider]\n')
        responses = dict(wifi={'supplicant_state': 'COMPLETED', 'rssi': -50, 'ssid': 'PRIVATE'},
                         cells=[{'registered': True, 'level': 2}],
                         device={'data_enabled': True, 'data_state': 'connected'},
                         volume=[{'stream': 'music', 'volume': 5, 'max_volume': 10}],
                         notifications=[{'packageName': 'com.termux'}, {'packageName': 'a.app'},
                                        {'packageName': 'a.app'}], location='3')
        for name, data in responses.items():
            (self.fx.home / (name + '-response')).write_text(data if name == 'location' else json.dumps(data))
        self.cache = Path(self.fx.env['XDG_CACHE_HOME']) / 'termux-status'

    def wait_cache(self, module, predicate):
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            path = self.cache / (module + '.json')
            if path.exists() and predicate(json.loads(path.read_text())['providers']):
                return
            time.sleep(.02)
        self.fail('fixture worker did not finish for ' + module)

    def refresh(self, module, code=0):
        result = subprocess.run([sys.executable, '-B', str(self.fx.android_scripts[module]), '--refresh', '--json'],
                                cwd=self.fx.home, env=self.fx.env, capture_output=True, text=True, timeout=6)
        self.assertEqual(result.returncode, code, result.stderr)

    def test_real_cache_refresh_permission_gates_and_recovery(self):
        self.install_real_scripts_with_fake_providers()
        self.run_adapter()
        for provider in ['cells', 'device', 'notifications', 'location', 'volume']:
            self.assertFalse((self.fx.home / (provider + '-api-calls')).exists())
        self.wait_cache('wifi', lambda p: p.get('wifi', {}).get('enabled') is True)
        self.refresh('cell')
        self.assertEqual(self.run_adapter(), '\U000f0928  \n')
        calls = {p: p.read_text() for p in self.fx.home.glob('*-api-calls')}
        self.run_adapter()
        self.assertEqual({p: p.read_text() for p in self.fx.home.glob('*-api-calls')}, calls)
        (self.fx.home / 'wifi-response').write_text('{"supplicant_state":"DISCONNECTED"}')
        self.refresh('wifi')
        self.assertEqual(self.run_adapter(), '\U000f08fa  \n')
        # Provider failure keeps bounded stale data; expiration marks activity unknown.
        (self.fx.home / 'device-api-fail').touch()
        path = self.cache / 'cell.json'
        document = json.loads(path.read_text())
        document['providers']['device']['success']['mono'] -= 20
        path.write_text(json.dumps(document))
        self.assertEqual(self.run_adapter(), '\U000f08fa~ \n')
        self.wait_cache('cell', lambda p: p['device'].get('error') ==
                        'request failed; check Android permissions and retry --refresh')
        failed_calls = (self.fx.home / 'device-api-calls').read_text()
        self.assertEqual(self.run_adapter(), '\U000f08fa~ \n')
        self.assertEqual((self.fx.home / 'device-api-calls').read_text(), failed_calls)
        document = json.loads(path.read_text())
        document['providers']['device']['success']['mono'] -= 301
        path.write_text(json.dumps(document))
        self.assertEqual(self.run_adapter(), self.unknown)
        self.assertEqual((self.fx.home / 'device-api-calls').read_text(), failed_calls)
        (self.fx.home / 'device-api-fail').unlink()
        self.refresh('cell')
        self.assertEqual(self.run_adapter(), '\U000f08fa  \n')
        (self.fx.home / 'device-response').write_text('{"data_enabled":false,"data_state":"connected"}')
        self.refresh('cell')
        self.assertEqual(self.run_adapter(), '\n')
        for module in ('notification', 'volume', 'location'):
            self.assertFalse((self.cache / (module + '.json')).exists())

    def test_real_wifi_failure_expiration_and_explicit_recovery(self):
        self.install_real_scripts_with_fake_providers()
        self.refresh('wifi')
        self.refresh('cell')
        (self.fx.home / 'wifi-api-fail').touch()
        self.refresh('wifi', code=1)
        self.assertEqual(self.run_adapter(), '\U000f0928~ \n')
        path = self.cache / 'wifi.json'
        document = json.loads(path.read_text())
        document['providers']['wifi']['success']['mono'] -= 301
        path.write_text(json.dumps(document))
        calls = (self.fx.home / 'wifi-api-calls').read_text()
        for enabled in (True, False, None):
            (self.fx.home / 'device-response').write_text(json.dumps(
                {'data_enabled': enabled, 'data_state': 'connected' if enabled is not None else None}))
            self.refresh('cell')
            self.assertEqual(self.run_adapter(), self.unknown)
        self.assertEqual((self.fx.home / 'wifi-api-calls').read_text(), calls)
        # Recovery is explicit; an ordinary read cannot re-enable this provider.
        (self.fx.home / 'wifi-api-fail').unlink()
        self.assertEqual(self.run_adapter(), self.unknown)
        self.assertEqual((self.fx.home / 'wifi-api-calls').read_text(), calls)
        self.refresh('wifi')
        self.assertEqual(self.run_adapter(), '\U000f0928  \n')
        # A failed negative observation remains uncertain rather than disappearing.
        (self.fx.home / 'wifi-response').write_text('{"supplicant_state":"DISCONNECTED"}')
        (self.fx.home / 'device-response').write_text('{"data_enabled":false,"data_state":"disconnected"}')
        self.refresh('wifi')
        self.refresh('cell')
        self.assertEqual(self.run_adapter(), '\n')
        (self.fx.home / 'wifi-api-fail').touch()
        self.refresh('wifi', code=1)
        self.assertEqual(self.run_adapter(), '?~ \n')


if __name__ == '__main__':
    unittest.main()

"""Termux upgrade argv and compact mirror phases, with owned fake managers."""
import io
import json
import os
import re
import sys
import unittest
from unittest.mock import Mock, patch

import test_workflows as fixtures
from pkgs_lib import scopes, streams, upgrade_output, workflows
from pkgs_lib.backends import Backend
from pkgs_lib.common import Error, Package


class TermuxUpgrades(unittest.TestCase):
    setUp = fixtures.Workflows.setUp
    invoke = fixtures.Workflows.invoke

    def backend(self, name='apt'):
        backend = Backend(name)
        backend.termux = True
        return backend

    def test_bulk_pkg_flags_and_unchanged_explicit_actions(self):
        backend = self.backend()
        with patch('pkgs_lib.backends.which', return_value='/fixture/pkg'), \
             patch('pkgs_lib.backends.default_manager', return_value='apt'):
            for _ in range(2):
                item = workflows.plan(backend, 'upgrade', [], self.cfg)
                self.assertEqual(item.commands, [['pkg', '--check-mirror', 'upgrade', '--fix-missing', '-y']])
            explicit = workflows.plan(backend, 'upgrade', ['hello'], self.cfg)
            self.assertEqual(explicit.commands, [['pkg', 'install', '--only-upgrade', '-y', 'hello']])
            for action, verb in (('install', 'install'), ('refresh', 'update')):
                names = ['hello'] if action == 'install' else []
                self.assertEqual(workflows.plan(backend, action, names, self.cfg).commands,
                                 [['pkg', verb, '-y', *names]])
            self.assertEqual(backend.transaction('uninstall', ['hello'], True),
                             ['pkg', 'uninstall', '-y', 'hello'])

    def test_pacman_mismatch_and_direct_backend_fallbacks(self):
        with patch('pkgs_lib.backends.which', return_value='/fixture/pkg'), \
             patch('pkgs_lib.backends.default_manager', return_value='pacman'):
            self.assertEqual(workflows.plan(self.backend('pacman'), 'upgrade', [], self.cfg).commands,
                             [['pkg', 'upgrade', '--noconfirm']])
            with self.assertRaisesRegex(Error, 'pkg uses pacman'):
                workflows.plan(self.backend(), 'upgrade', [], self.cfg)
        for executable in ('apt', 'apt-get'):
            backend = self.backend(); backend.bin = executable
            with patch('pkgs_lib.backends.which', return_value=None):
                self.assertEqual(workflows.plan(backend, 'upgrade', [], self.cfg).commands,
                                 [[executable, 'upgrade', '--fix-missing', '-y', '--']])
            backend.termux = False
            with patch('pkgs_lib.backends.os.geteuid', return_value=0):
                self.assertEqual(workflows.plan(backend, 'upgrade', [], self.cfg).commands,
                                 [[executable, 'upgrade', '-y', '--']])

    def test_policy_groups_force_once_and_replacements_own_their_commands(self):
        backend = self.backend()
        rows = [(Package(name, '1'), 'explicit', '') for name in ('plain', 'custom', 'replaced', 'skip')]
        cfg = dict(self.cfg, policies={'apt': {
            'skip': ['skip'], 'upgrade': {'before': [['before']], 'after': [['after']]},
            'packages': {'custom': {'upgrade': {'flags': ['--no-fix-missing']}},
                         'replaced': {'upgrade': {'replace': [['custom-upgrade', '{package}']]}}}}})
        with patch('pkgs_lib.backends.which', return_value='/fixture/pkg'), \
             patch('pkgs_lib.backends.default_manager', return_value='apt'), \
             patch.object(scopes, 'inventory', return_value=rows):
            item = workflows.plan(backend, 'upgrade', [], cfg)
            self.assertEqual(item.commands, [
                ['before'], ['pkg', '--check-mirror', 'install', '--only-upgrade', '--fix-missing', '-y', 'plain'],
                ['pkg', 'install', '--only-upgrade', '--fix-missing', '-y', 'custom', '--no-fix-missing'],
                ['custom-upgrade', 'replaced'], ['after']])
            self.assertEqual(item.skipped, [{'package': 'skip', 'reason': 'skipped by policy'}])
            cfg = dict(self.cfg, policies={'apt': {'upgrade': {'replace': [['custom-upgrade']]}}})
            with patch('pkgs_lib.backends.default_manager', side_effect=AssertionError('replacement probe')):
                self.assertEqual(workflows.plan(backend, 'upgrade', [], cfg).commands, [['custom-upgrade']])

    def fake_apt(self):
        os.environ.update(TERMUX_VERSION='fixture', TERMUX_APP_PACKAGE_MANAGER='apt',
                          TEST_APT_DB=str(self.home/'apt.json'))
        (self.home/'apt.json').write_text('{"changed":"1","kept":"1"}')
        script = '#!'+sys.executable+'\n'+'''import json,os,sys,time
from pathlib import Path
name=Path(sys.argv[0]).name; args=sys.argv[1:]
db=Path(os.environ['TEST_APT_DB']); versions=json.loads(db.read_text())
if name=='dpkg-query':
    for package,version in versions.items(): print(package+'\\t'+version+'\\tinstalled\\tfixture')
elif name=='pkg':
    with open(os.environ['TEST_CALLS'],'a') as f: f.write(json.dumps(args)+'\\n')
    assert args==['--check-mirror','upgrade','--fix-missing','-y'], args
    if not os.environ.get('TERMUX_PKG_NO_MIRROR_SELECT'):
        print('Testing the available mirrors:')
        print('[*] (1) https://mirror.invalid/termux-main: ok')
        print('Picking mirror: (0) /fixture/mirror')
        sys.stdout.flush(); time.sleep(float(os.environ.get('TEST_STAGE_DELAY','0')))
    if os.environ.get('TEST_APT_FAIL'):
        print('Error: None of the mirrors are accessible',file=sys.stderr)
        sys.exit(int(os.environ['TEST_APT_FAIL']))
    print('Hit:1 https://mirror.invalid/termux-main stable InRelease')
    print('Reading package lists... Done')
    sys.stdout.flush(); time.sleep(float(os.environ.get('TEST_STAGE_DELAY','0')))
    print('2 packages can be upgraded. Run apt list --upgradable to see them.')
    print('Calculating upgrade... Done')
    sys.stdout.flush(); time.sleep(float(os.environ.get('TEST_STAGE_DELAY','0')))
    for line in ('1 upgraded, 0 newly installed, 0 to remove and 1 not upgraded.',
                 'Get:1 https://mirror.invalid changed 2 [30 kB]',
                 'Fetched 30 kB in 1s', 'Unpacking changed (2) over (1) ...', 'Setting up changed (2) ...'):
        print(line, flush=True)
        time.sleep(float(os.environ.get('TEST_PACKAGE_DELAY','0')))
    print('W: Unavailable download held back: kept',file=sys.stderr)
    versions['changed']='2'; db.write_text(json.dumps(versions))
else: raise SystemExit('unexpected native invocation: '+name)
'''
        for name in ('pkg', 'apt', 'apt-cache', 'dpkg-query'):
            path = self.bin/name; path.write_text(script); path.chmod(0o755)

    def test_fake_upgrade_summary_raw_dry_run_failure_and_mirror_opt_out(self):
        self.fake_apt()
        path = self.home/'config/pkgs/config.json'; path.parent.mkdir(parents=True)
        path.write_text(json.dumps({'output': 'styled'}))
        preview = self.invoke('up', '--manager', 'apt', '--dry-run')
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertIn('pkg --check-mirror upgrade --fix-missing -y', preview.stdout)
        self.assertFalse((self.home/'calls.jsonl').exists())
        for opt_out in ('', '1'):
            (self.home/'apt.json').write_text('{"changed":"1","kept":"1"}')
            with patch.dict(os.environ, TERMUX_PKG_NO_MIRROR_SELECT=opt_out):
                result = self.invoke('up', '--manager', 'apt')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertRegex(result.stdout, r'Updated:?\s+changed')
            self.assertNotRegex(result.stdout, r'Updated[^\n]*kept')
            self.assertIn('held back: kept', result.stderr)
            self.assertNotIn('mirror.invalid', result.stdout+result.stderr)
        raw = self.invoke('up', '--manager', 'apt', '--raw')
        self.assertEqual(raw.returncode, 0, raw.stderr)
        self.assertIn('[*] (1) https://mirror.invalid/termux-main: ok', raw.stdout)
        for code in ('100', '130'):
            with patch.dict(os.environ, TEST_APT_FAIL=code):
                failed = self.invoke('up', '--manager', 'apt')
            self.assertEqual(failed.returncode, int(code), failed.stderr)
            self.assertIn('failed (exit '+code+')', failed.stdout)
            self.assertIn('None of the mirrors are accessible', failed.stderr)
            self.assertNotIn('Updated', failed.stdout)
        path.write_text(json.dumps({'output': 'styled', 'upgrade': {'managers': ['apt', 'npm']}}))
        (self.home/'db.json').write_text('{"hello":"1"}')
        with patch.dict(os.environ, TEST_APT_FAIL='100'):
            result = self.invoke('up')
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertRegex(result.stdout, r'npm:?\s+complete')

    def test_fragmented_mirror_phases_prompts_and_repository_transition(self):
        meter = Mock(); out = io.StringIO()
        summary = upgrade_output.Output('apt', self.cfg, meter)
        summary.begin(['pkg', '--check-mirror', 'upgrade', '--fix-missing', '-y'])
        formatter = streams.Formatter(out, dict(self.cfg, _manager='apt'), summary)
        for chunk in (b'Testing the available ', b'mirrors:\n[*] (1) https://private.invalid: ', b'bad\n',
                      b'Picking mirror: (1) /fixture/mirror\n'):
            formatter.feed(chunk); formatter.flush_partial()
        self.assertEqual(summary.stage, 'Checking mirrors')
        formatter.feed(b'Hit:1 https://private.invalid stable InRelease\nReading package lists... Done\n')
        self.assertEqual(summary.stage, 'Updating repositories')
        formatter.feed(b'2 packages can be upgraded.\nCalculating upgrade... Done\n')
        self.assertEqual(summary.stage, 'Upgrading')
        formatter.feed(b'Get:1 https://private.invalid package 2 [100 kB]\n')
        self.assertEqual(summary.stage, 'Downloading')
        formatter.feed(b'Unpacking changed (2) over (1) ...\n')
        self.assertEqual(summary.stage, 'Installing')
        self.assertEqual(out.getvalue(), '')
        self.assertNotIn('private.invalid', repr(meter.update_spans.call_args_list))
        self.assertIsNone(summary.pause)
        formatter.feed(b'Continue? [Y/n] '); formatter.flush_partial()
        self.assertIn('Continue?', out.getvalue())
        summary.close()
        formatter.feed(b'Testing the available mirrors:\n[*] Continue? [Y/n] ')
        formatter.flush_partial()
        self.assertIn('[*] Continue?', out.getvalue())
        summary.close()
        summary.begin(['pkg', 'upgrade', '--fix-missing', '-y'])
        formatter.feed(b'Hit:1 https://private.invalid stable InRelease\n')
        self.assertEqual(summary.stage, 'Updating repositories')
        summary.begin(['apt', 'upgrade', '--fix-missing', '-y'])
        self.assertFalse(summary.apt_stage('Testing the available mirrors:'))

    @unittest.skipIf(os.name == 'nt', 'Termux progress uses a private POSIX terminal')
    def test_native_mirror_progress_at_terminal_widths(self):
        import fcntl
        import pty
        import select
        import signal
        import struct
        import termios
        import time
        self.fake_apt()
        config = self.home/'config/pkgs/config.json'
        config.parent.mkdir(parents=True)
        config.write_text(json.dumps({'upgrade': {'managers': ['apt', 'npm']}}))
        for width in (40, 80, 120):
            for color in ('always', 'never'):
                with self.subTest(width=width, color=color):
                    pid, fd = pty.fork()
                    if pid == 0:
                        try:
                            fcntl.ioctl(1, termios.TIOCSWINSZ, struct.pack('HHHH', 24, width, 0, 0))
                            env = dict(os.environ, COLUMNS=str(width), TERM='xterm-256color',
                                       DOTS_COLOR=color, DOTS_ICONS='never', DOTS_PROGRESS='auto',
                                       TEST_STAGE_DELAY='.8', TEST_PACKAGE_DELAY='.35', TERMUX_PKG_NO_MIRROR_SELECT='')
                            if color == 'never': env['NO_COLOR'] = '1'
                            else: env.pop('NO_COLOR', None)
                            args = ['up'] if color == 'always' else ['up', '--manager', 'apt']
                            os.execve(sys.executable, [sys.executable, '-B', str(fixtures.APP/'main.py'), *args], env)
                        except BaseException: os._exit(99)
                    data = b''; status = None; start = time.monotonic()
                    try:
                        while time.monotonic()-start < 10:
                            if select.select([fd], [], [], .05)[0]:
                                try: chunk = os.read(fd, 65536)
                                except OSError: break
                                if not chunk: break
                                data += chunk
                            if status is None:
                                ended, state = os.waitpid(pid, os.WNOHANG)
                                if ended: status = state
                        if status is None:
                            ended, state = os.waitpid(pid, os.WNOHANG)
                            if not ended:
                                os.kill(pid, signal.SIGKILL); state = os.waitpid(pid, 0)[1]
                            status = state
                    finally: os.close(fd)
                    self.assertEqual(os.waitstatus_to_exitcode(status), 0, data.decode(errors='replace'))
                    plain = streams.ESCAPES.sub('', data.decode())
                    for stage in ('Checking mirrors', 'Updating repositories', 'Upgrading'):
                        self.assertIn(stage, plain)
                    percentages = re.findall(r'\]\s+(\d+(?:\.\d+)?%)', plain)
                    expected = (['19.4%', '22.2%', '25.0%', '27.7%', '30.5%'] if color == 'always' else
                                ['38.8%', '44.4%', '50.0%', '55.5%', '61.1%'])
                    self.assertEqual(list(dict.fromkeys(p for p in percentages if p in expected)), expected, plain)
                    self.assertNotIn('mirror.invalid', plain)
                    self.assertNotIn('Picking mirror', plain)
                    self.assertIn('complete', plain)
                    self.assertTrue(all(len(line) <= width for line in plain.splitlines()), plain)
                    self.assertEqual(bool(re.search(rb'\x1b\[[0-9;]*m', data)), color == 'always')


if __name__ == '__main__': unittest.main()

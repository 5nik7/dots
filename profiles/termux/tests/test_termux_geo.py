#!/usr/bin/env python3
"""Native shells and mock-only location/HTTP; every mutable path is test-owned."""
import errno
import fcntl
import json
import os
from pathlib import Path
import pty
import re
import resource
import select
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import time
import unittest

REPO = Path(__file__).resolve().parents[1]
PARENT = REPO.parent
FIX = {"latitude": 40.7484, "longitude": -73.9857, "accuracy": 12.5,
       "elapsedMs": 500, "provider": "network"}
ADDRESS = {"lat": "99", "lon": "99", "display_name": "Example address",
           "licence": "© OpenStreetMap contributors",
           "address": {"city": "Example City", "state": "New York", "postcode": "00123",
                       "country": "United States", "country_code": "us", "ISO3166-2-lvl4": "US-NY"}}
MOCK = '''#!@PYTHON@
import json, os, pathlib, resource, sys, time
name=pathlib.Path(sys.argv[0]).name
root=pathlib.Path(os.environ['MOCK_ROOT'])
with (root/'calls').open('a') as f: f.write(json.dumps([name]+sys.argv[1:])+'\\n')
delay=float(os.environ.get('MOCK_DELAY_'+('FIX' if name=='termux-location' else 'HTTP'),'0'))
if delay:
    (root/(name+'.pid')).write_text(str(os.getpid()))
    time.sleep(delay)
if name=='termux-location':
    (root/'fix-limit').write_text(json.dumps(resource.getrlimit(resource.RLIMIT_FSIZE)))
    print((root/'fix').read_text())
    sys.exit(int(os.environ.get('MOCK_FIX_EXIT','0')))
args=sys.argv[1:]
pathlib.Path(args[args.index('--output')+1]).write_bytes((root/'address').read_bytes())
pathlib.Path(args[args.index('--dump-header')+1]).write_text(os.environ.get('MOCK_HEADERS','HTTP/1.1 200 OK\\r\\n'))
print(os.environ.get('MOCK_HTTP_CODE','200'),end='')
sys.exit(int(os.environ.get('MOCK_HTTP_EXIT','0')))
'''


class GeoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='geo tests ü -')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'dots' / 'androidots'
        (self.repo / 'bin').mkdir(parents=True)
        shutil.copy2(REPO / 'bin/termux-geo', self.repo / 'bin/termux-geo')
        shutil.copytree(REPO / 'lib/termux_geo', self.repo / 'lib/termux_geo')
        # Copy public renderer dependencies only, never personal settings.
        self.dots = self.repo.parent
        for name in ('ui.bash', 'progress.bash', 'resources.bash', 'resources.tsv',
                     'shell/config.bash', 'shell/settings.tsv'):
            dest = self.dots / 'lib/dots' / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(PARENT / 'lib/dots' / name, dest)
        self.bin = self.root / 'mock-bin'
        self.bin.mkdir()
        for name in ('termux-location', 'curl'):
            path = self.bin / name
            path.write_text(MOCK.replace('@PYTHON@', sys.executable))
            path.chmod(0o700)
        self.env = {key: value for key, value in os.environ.items()
                    if key in ('PATH', 'PREFIX', 'LD_PRELOAD', 'LANG')}
        self.env.update(HOME=str(self.root / 'home'), TMPDIR=str(self.root),
                        XDG_CONFIG_HOME=str(self.root / 'config'), XDG_CACHE_HOME=str(self.root / 'cache'),
                        XDG_DATA_HOME=str(self.root / 'data'), XDG_STATE_HOME=str(self.root / 'state'),
                        DOTS=str(self.dots), PATH=str(self.bin) + ':' + str(self.repo/'bin') + ':' + self.env['PATH'],
                        MOCK_ROOT=str(self.root), TERM='dumb', DOTS_TERMUX_AUTOSTART='0')
        self.fix = self.root / 'fix'; self.fix.write_text(json.dumps(FIX))
        self.address = self.root / 'address'; self.address.write_text(json.dumps(ADDRESS))
        self.command = str(self.repo / 'bin/termux-geo')

    def run_geo(self, *args, status=0, input=None, extra=None):
        p = subprocess.run([self.command, *args], input=input, text=True, capture_output=True,
                           env=self.env | (extra or {}), timeout=8)
        self.assertEqual(p.returncode, status, (args, p.stdout, p.stderr))
        return p

    def calls(self):
        path = self.root / 'calls'
        return [json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []

    def state(self):
        return Path(self.env['XDG_CACHE_HOME']) / 'termux-geo/state.json'

    def change_state(self, fn):
        state = json.loads(self.state().read_text()); fn(state)
        self.state().write_text(json.dumps(state))

    def test_normalized_json_and_warm_cache(self):
        first = json.loads(self.run_geo().stdout)
        self.assertEqual(first['latitude'], FIX['latitude'])
        self.assertEqual(first['longitude'], FIX['longitude'])
        self.assertEqual(first['postcode'], '00123')
        self.assertEqual(first['country_code'], 'US')
        self.assertFalse(first['cached'])
        second = json.loads(self.run_geo('--color=always', '--icons=always', '-v').stdout)
        self.assertTrue(second['cached']); self.assertTrue(second['address_cached'])
        self.assertEqual([x[0] for x in self.calls()], ['termux-location', 'curl'])
        self.assertEqual(self.state().stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.state().parent.stat().st_mode & 0o777, 0o700)

    def test_coordinates_get_and_templates_skip_http(self):
        self.assertEqual(self.run_geo('--coords').stdout, '40.7484,-73.9857\n')
        self.assertEqual(self.run_geo('get', 'lat').stdout, '40.7484\n')
        self.assertEqual(self.run_geo('format', '{{{lat}}}:{lon}').stdout, '{40.7484}:-73.9857\n')
        self.assertEqual(len(self.calls()), 1)

    def test_explicit_zero_and_stdin_no_device(self):
        self.assertEqual(self.run_geo('--lat', '0', '--lon=-0', '--coords').stdout, '0,-0\n')
        p = self.run_geo('--stdin', 'get', 'longitude', input=json.dumps(FIX))
        self.assertEqual(p.stdout, '-73.9857\n')
        self.assertFalse(self.calls()); self.assertFalse(self.state().exists())
        self.run_geo('--stdin', '--coords', input='{}\n{}', status=1)
        self.run_geo('--stdin', '--coords', input='x'*65537, status=1)

    def test_explicit_lookup_does_not_replace_device(self):
        self.run_geo('--coords')
        self.run_geo('--lat', '10', '--lon', '20')
        state = json.loads(self.state().read_text())
        self.assertEqual(state['devices']['network']['data']['latitude'], FIX['latitude'])
        self.assertEqual([x[0] for x in self.calls()], ['termux-location', 'curl'])

    def test_bad_usage_never_acquires(self):
        for args in [('--lat','bad','--lon','0'), ('--lat','91','--lon','0'),
                     ('--lat','0'), ('--json','--coords'), ('get','missing'),
                     ('format','{city.foo}'), ('format','{city'), ('format','city}'),
                     ('--cached','--refresh'), ('--allow-stale',), ('--timeout','0'),
                     ('--provider','bad'), ('--stdin','--provider','gps'),
                     ('--install',), ('completion','bash','--all','--install'),
                     ('completion','bash','--dir','x'), ('--language','a?b')]:
            with self.subTest(args=args):
                p=self.run_geo(*args, status=2); self.assertEqual(p.stdout,'')
        self.assertFalse(self.calls())

    def test_cache_only_never_writes_or_acquires(self):
        self.run_geo('--cached', status=1)
        self.assertFalse(self.state().parent.exists())
        self.run_geo('--coords')
        self.change_state(lambda s: s['devices']['network'].update(at=0))
        before=self.state().read_bytes()
        self.run_geo('--cached','--coords', status=1)
        p=self.run_geo('--cached','--allow-stale','get','stale')
        self.assertEqual(p.stdout,'true\n'); self.assertEqual(self.state().read_bytes(),before)
        self.assertEqual(len(self.calls()),1)

    def test_boot_unknown_and_provider_separation(self):
        self.run_geo('--coords')
        self.change_state(lambda s: s['devices']['network'].update(boot='old-boot'))
        self.run_geo('--cached','--coords',status=1)
        self.assertEqual(self.run_geo('--cached','--allow-stale','get','stale').stdout,'true\n')
        self.run_geo('--provider','gps','--coords')
        self.assertEqual(self.calls()[-1][1:], ['-p','gps','-r','once'])

    def test_refresh_reuses_address_cache(self):
        self.run_geo(); self.run_geo('--refresh')
        self.assertEqual([x[0] for x in self.calls()], ['termux-location','curl','termux-location'])

    def test_missing_field_and_safe_template(self):
        self.run_geo()
        p=self.run_geo('get','street',status=1); self.assertEqual(p.stdout,'')
        p=self.run_geo('format','{city}: {street}',status=1); self.assertEqual(p.stdout,'')
        p=self.run_geo('format','$(touch injected) {city} {{x}}')
        self.assertEqual(p.stdout,'$(touch injected) Example City {x}\n')
        self.assertFalse((self.root/'injected').exists())

    def test_permission_error_and_old_fix(self):
        self.fix.write_text('{"API_ERROR":"secret remote stack trace"}')
        p=self.run_geo(status=1)
        self.assertEqual(p.stdout,''); self.assertNotIn('secret',p.stderr)
        self.fix.write_text(json.dumps(FIX | {'elapsedMs':999999}))
        self.run_geo('--coords',status=1)
        self.assertFalse(any(x[0]=='curl' for x in self.calls()))

    def test_address_failure_strict_and_human_partial(self):
        self.address.write_text('{"error":"not found"}')
        p=self.run_geo(status=1); self.assertEqual(p.stdout,'')
        self.change_state(lambda s: s.update(rate={}))
        p=self.run_geo('--human',status=1)
        self.assertIn('Latitude',p.stdout); self.assertIn('unavailable',p.stderr)

    def test_rate_limit_and_retry_after(self):
        self.run_geo('--lat','1','--lon','2')
        p=self.run_geo('--lat','2','--lon','3',status=1)
        self.assertEqual(p.stdout,''); self.assertIn('cooldown',p.stderr)
        self.assertEqual(len(self.calls()),1)
        self.change_state(lambda s:s.update(rate={}))
        self.run_geo('--lat','2','--lon','3',status=1,
                     extra={'MOCK_HTTP_CODE':'429','MOCK_HEADERS':'HTTP/1.1 429\r\nRetry-After: 120\r\n'})
        p=self.run_geo('--lat','2','--lon','3',status=1)
        self.assertRegex(p.stderr,r'retry after 1[12][0-9] seconds')

    def test_deadline_cleans_children(self):
        start=time.monotonic()
        p=self.run_geo('--coords','--timeout','2','--color=always','--icons=always',
                       status=124,extra={'MOCK_DELAY_FIX':'5'})
        self.assertLess(time.monotonic()-start,4)
        self.assertEqual(p.stdout,''); self.assertIn('device location deadline exceeded',p.stderr)
        self.assertNotIn('\x1b',p.stderr)
        pid=int((self.root/'termux-location.pid').read_text())
        with self.assertRaises(ProcessLookupError): os.kill(pid,0)
        self.assertFalse(list(self.root.glob('termux-geo.*')))
        # A timed-out pipeline must not leave a child holding the cache lock.
        self.run_geo('--coords')

    def test_device_preserves_file_size_resource_limit(self):
        self.run_geo('--coords')
        self.assertEqual(json.loads((self.root/'fix-limit').read_text()),
                         list(resource.getrlimit(resource.RLIMIT_FSIZE)))

    def test_device_response_size_boundary(self):
        fix=json.dumps(FIX)
        # The mock adds one newline; a complete 64 KiB response is accepted.
        self.fix.write_text(fix+' '*(65535-len(fix)))
        self.run_geo('--coords')
        for suffix in ('\n', '\u00fc'*40000, 'x'*200000):
            with self.subTest(suffix_bytes=len(suffix.encode())):
                self.fix.write_text(fix+' '*(65535-len(fix))+suffix)
                p=self.run_geo('--coords','--refresh',status=1)
                self.assertEqual(p.stdout,'')
                self.assertIn('device location response exceeds 64 KiB',p.stderr)
                self.assertFalse(list(self.root.glob('termux-geo.*')))
        self.assertFalse(any(x[0]=='curl' for x in self.calls()))

    def test_address_timeout_names_phase_and_cleans_children(self):
        p=self.run_geo('--lat','1','--lon','2','--timeout','2',status=124,
                       extra={'MOCK_DELAY_HTTP':'5'})
        self.assertEqual(p.stdout,'')
        self.assertIn('address lookup deadline exceeded',p.stderr)
        pid=int((self.root/'curl.pid').read_text())
        with self.assertRaises(ProcessLookupError): os.kill(pid,0)
        self.assertFalse(list(self.root.glob('termux-geo.*')))

    def test_curl_timeout_preserves_timeout_status(self):
        p=self.run_geo('--lat','1','--lon','2',status=124,extra={'MOCK_HTTP_EXIT':'28'})
        self.assertEqual(p.stdout,''); self.assertIn('address lookup timed out',p.stderr)

    def test_stalled_stdin_names_phase(self):
        with subprocess.Popen([self.command,'--stdin','--coords','--timeout','1'],
                              env=self.env,stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE,stderr=subprocess.PIPE) as p:
            try:
                self.assertEqual(p.wait(timeout=4),124)
                out,err=p.communicate(timeout=1)
            finally:
                if p.poll() is None:
                    p.kill(); p.communicate()
        self.assertEqual(out,b''); self.assertIn(b'stdin reading deadline exceeded',err)
        self.assertFalse(list(self.root.glob('termux-geo.*')))
        self.assertEqual(self.calls(),[])

    def test_concurrent_misses_share_fix(self):
        env=self.env | {'MOCK_DELAY_FIX':'0.2'}
        procs=[subprocess.Popen([self.command,'--coords'],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE) for _ in range(2)]
        results=[(proc, *proc.communicate(timeout=5)) for proc in procs]
        for proc,out,err in results:
            self.assertEqual(proc.returncode,0,err); self.assertEqual(out,b'40.7484,-73.9857\n')
        self.assertEqual(len(self.calls()),1)

    def test_malformed_and_symlink_cache(self):
        self.run_geo('--coords')
        self.state().write_text('bad')
        self.run_geo('--cached','--coords',status=1)
        self.state().unlink(); self.state().symlink_to(self.fix)
        self.run_geo('--coords',status=1)
        self.assertEqual(json.loads(self.fix.read_text()),FIX)

    def test_cache_rejects_invalid_coordinates_and_address_override(self):
        self.run_geo()
        self.change_state(lambda s:s['addresses'][0]['data'].update(latitude=99))
        self.run_geo('--cached',status=1)
        self.state().unlink()
        self.run_geo('--coords')
        self.change_state(lambda s:s['devices']['network']['data'].update(latitude=999))
        self.run_geo('--cached','--coords',status=1)

    def test_sleep_and_backwards_wall_time_expire_fix(self):
        self.run_geo('--coords')
        self.change_state(lambda s:s['devices']['network'].update(wall=int(time.time())-120))
        self.run_geo('--cached','--coords',status=1)
        self.change_state(lambda s:s['devices']['network'].update(wall=int(time.time())+120))
        self.run_geo('--cached','--coords',status=1)

    def test_api_multiobject_and_invalid_response_are_refused(self):
        self.fix.write_text(json.dumps(FIX)+'\n'+json.dumps(FIX))
        self.run_geo('--coords',status=1)
        self.fix.write_text(json.dumps(FIX))
        self.address.write_text('not json')
        p=self.run_geo(status=1); self.assertEqual(p.stdout,'')

    def test_sigint_cleans_worker_and_releases_lock(self):
        env=self.env | {'MOCK_DELAY_FIX':'5'}
        p=subprocess.Popen([self.command,'--coords'],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            end=time.monotonic()+4
            while time.monotonic()<end and not (self.root/'termux-location.pid').exists(): time.sleep(0.02)
            self.assertTrue((self.root/'termux-location.pid').exists())
            p.send_signal(signal.SIGINT)
            out,err=p.communicate(timeout=3)
            self.assertEqual(p.returncode,130,err); self.assertEqual(out,b'')
            pid=int((self.root/'termux-location.pid').read_text())
            with self.assertRaises(ProcessLookupError): os.kill(pid,0)
            self.run_geo('--coords')
        finally:
            if p.poll() is None: p.kill(); p.communicate()

    def test_terminal_controls_sanitized_but_json_preserved(self):
        dirty=ADDRESS | {'display_name':'line\x1b[31m\tname'}
        self.address.write_text(json.dumps(dirty))
        data=json.loads(self.run_geo('--json').stdout)
        self.assertEqual(data['address'],dirty['display_name'])
        p=self.run_geo('--human','--color=never','--icons=never')
        self.assertNotIn('\x1b',p.stdout); self.assertNotIn('\t',p.stdout)

    def test_standalone_plain_human_fallback(self):
        shutil.rmtree(self.dots/'lib/dots')
        p=self.run_geo('--human','--lat','40','--lon','-73')
        self.assertIn('City: Example City',p.stdout)
        self.assertNotIn('\x1b',p.stdout)
        p=self.run_geo('--bad\x1b[31m',status=2)
        self.assertNotIn('\x1b',p.stderr)

    def test_help_fields_completion_no_lookup(self):
        plain=self.run_geo('--help').stdout
        self.assertNotIn('\x1b',plain)
        self.assertEqual(self.run_geo('-h').stdout,plain)
        strip_color=lambda text: re.sub(r'\x1b\[[0-9;]*m','',text)
        for args,extra in [(['--help','--color=always'],{}),
                           (['--help'],{'DOTS_COLOR':'always'}),
                           (['completion','bash','--help','--color=always'],{'NO_COLOR':'1'})]:
            colored=self.run_geo(*args,extra=extra).stdout
            self.assertEqual(strip_color(colored),plain)
            self.assertIn('\x1b[1m\x1b[96mOutput:\x1b[0m',colored)
            self.assertIn('\x1b[94m--coords\x1b[0m',colored)
            self.assertIn('\x1b[94m  termux-geo get city\x1b[0m',colored)
            self.assertRegex(colored,r'\x1b\[94m--coords\x1b\[0m +latitude,longitude; no address lookup\n')
        self.assertEqual(self.run_geo('--help','--color=never',extra={'DOTS_COLOR':'always'}).stdout,plain)
        self.assertEqual(self.run_geo('--help',extra={'NO_COLOR':'1'}).stdout,plain)
        for width in (40,80,120):
            out=self.pty_geo(width,['--help']).decode().replace('\r\n','\n')
            self.assertIn('\x1b[94m--coords\x1b[0m',out)
            self.assertEqual(strip_color(out),plain)
        for extra in ({'NO_COLOR':'1'},{'TERM':'dumb'},{'DOTS_COLOR':'never'}):
            out=self.pty_geo(80,['--help'],extra).decode().replace('\r\n','\n')
            self.assertEqual(out,plain)
        self.assertNotIn('\x1b',self.run_geo('--fields','--color=always').stdout)
        for shell in ('bash','zsh','fish'):
            p=self.run_geo('completion',shell, '--color=always')
            self.assertNotIn('\x1b',p.stdout)
            target=self.root/f'completion.{shell}'; target.write_text(p.stdout)
            result=subprocess.run([shell,'-n',str(target)],env=self.env,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
        shutil.rmtree(self.dots/'lib/dots')
        fallback=self.run_geo('--help','--color=always').stdout
        self.assertEqual(fallback,plain.partition('\n')[2])
        self.assertFalse(self.calls()); self.assertFalse(self.state().parent.exists())

    def test_install_defaults_idempotence_and_backup(self):
        self.run_geo('completion','--all','--install')
        files={'bash':'termux-geo.bash','zsh':'_termux-geo','fish':'termux-geo.fish'}
        for shell,name in files.items():
            target=self.repo/'shells'/shell/'completions'/name
            self.assertEqual(target.read_text(),self.run_geo('completion',shell).stdout)
        p=self.run_geo('completion','--all','--install')
        self.assertEqual(p.stdout,''); self.assertEqual(p.stderr.count('Unchanged'),3)
        target=self.repo/'shells/bash/completions/termux-geo.bash'
        target.write_bytes(b'old\x00bytes\n'); target.chmod(0o640)
        self.run_geo('completion','bash','--install')
        backups=list(target.parent.glob('*.bak.*'))
        self.assertEqual(len(backups),1); self.assertEqual(backups[0].read_bytes(),b'old\x00bytes\n')
        self.assertEqual(target.stat().st_mode & 0o777,0o640)
        self.assertFalse(self.calls())

    def test_install_custom_and_preflight_refusal(self):
        dest=self.root/'-custom space ü'; dest.mkdir()
        (dest/'termux-geo.fish').symlink_to(self.fix)
        self.run_geo('completion','--all','--install','--dir',str(dest),status=1)
        self.assertFalse((dest/'termux-geo.bash').exists())
        (dest/'termux-geo.fish').unlink()
        self.run_geo('completion','--all','--install','--dir',str(dest))
        self.assertEqual(len(list(dest.iterdir())),3)

    def test_install_partial_failure_retains_completed_files(self):
        dest=self.root/'export'
        real=shutil.which('mv')
        stub=self.bin/'mv'
        stub.write_text(f'#!{sys.executable}\nimport os,sys\nif sys.argv[-1].endswith("/_termux-geo"): sys.exit(1)\nos.execv({real!r},[{real!r}]+sys.argv[1:])\n')
        stub.chmod(0o700)
        p=self.run_geo('completion','--all','--install','--dir',str(dest),status=1)
        self.assertIn('retained',p.stderr)
        self.assertTrue((dest/'termux-geo.bash').is_file())
        self.assertFalse((dest/'_termux-geo').exists())
        self.assertFalse((dest/'termux-geo.fish').exists())
        self.assertFalse(list(dest.glob('.termux-geo.*')))

    def test_install_detects_preflight_drift(self):
        dest=self.root/'export'; dest.mkdir()
        first=dest/'termux-geo.bash'; first.write_text('original')
        (dest/'_termux-geo').write_text('old zsh')
        real=shutil.which('cp')
        stub=self.bin/'cp'
        stub.write_text(f'#!{sys.executable}\nimport pathlib,subprocess,sys\np=subprocess.run([{real!r}]+sys.argv[1:])\nif sys.argv[-1].endswith("old.1"): pathlib.Path({str(first)!r}).write_text("concurrent edit")\nsys.exit(p.returncode)\n')
        stub.chmod(0o700)
        self.run_geo('completion','--all','--install','--dir',str(dest),status=1)
        self.assertEqual(first.read_text(),'concurrent edit')
        self.assertEqual((dest/'_termux-geo').read_text(),'old zsh')
        self.assertFalse(list(dest.glob('*.bak.*')))

    def test_bash_and_fish_completion_candidates(self):
        self.run_geo('completion','--all','--install')
        bash=self.repo/'shells/bash/completions/termux-geo.bash'
        code='source "$1"; COMP_WORDS=(termux-geo get po); COMP_CWORD=2; _termux_geo; printf "%s\\n" "${COMPREPLY[@]}"'
        p=subprocess.run(['bash','-c',code,'_',str(bash)],capture_output=True,text=True,env=self.env)
        self.assertEqual(p.stdout,'postcode\n')
        fish=self.repo/'shells/fish/completions'
        p=subprocess.run(['fish','--no-config','-c','set -p fish_complete_path "$argv[1]"; complete -C "termux-geo --provider "',str(fish)],capture_output=True,text=True,env=self.env)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn('network',p.stdout); self.assertIn('gps',p.stdout)
        self.assertFalse(self.calls())

    def pty_geo(self, width, args, extra=None, status=0):
        master,slave=pty.openpty()
        fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',40,width,0,0))
        env=self.env | {'TERM':'xterm-256color','COLUMNS':str(width)} | (extra or {})
        p=subprocess.Popen([self.command,*args],stdin=subprocess.DEVNULL,stdout=slave,stderr=slave,env=env)
        os.close(slave); data=bytearray(); deadline=time.monotonic()+8
        try:
            while time.monotonic()<deadline:
                ready,_,_=select.select([master],[],[],0.2)
                if ready:
                    try: chunk=os.read(master,65536)
                    except OSError as e:
                        if e.errno==errno.EIO: break
                        raise
                    if not chunk: break
                    data.extend(chunk)
                elif p.poll() is not None: break
            self.assertEqual(p.wait(timeout=2),status,data.decode(errors='replace'))
        finally:
            os.close(master)
            if p.poll() is None: p.kill(); p.wait()
        return bytes(data)

    def test_native_pty_device_timeout(self):
        for width in (40,80,120):
            out=self.pty_geo(width,['--human','--timeout','2','--color=never','--icons=never'],
                             {'MOCK_DELAY_FIX':'5'},status=124)
            self.assertIn(b'device location deadline exceeded',out)
            self.assertNotIn(b'Latitude',out)
            self.assertFalse(list(self.root.glob('termux-geo.*')))

    def test_native_pty_widths_and_progress(self):
        for width in (40,80,120):
            out=self.pty_geo(width,['--human'],{'MOCK_DELAY_FIX':'0.7'})
            self.assertIn(b'Location',out); self.assertIn(b'Example City',out)
            self.assertIn(b'\x1b[',out)
        self.assertIn(b'Getting location',self.pty_geo(80,['--human','--refresh'],{'MOCK_DELAY_FIX':'0.7'}))
        out=self.pty_geo(80,['--human'],{'NO_COLOR':'1','DOTS_PROGRESS':'never'})
        self.assertNotIn(b'\x1b[',out)
        out=self.pty_geo(80,['--json','--color=always','--icons=always','-v'])
        self.assertNotIn(b'\x1b[',out); json.loads(out)
        out=self.pty_geo(80,['--human'],{'TERM':'dumb'})
        self.assertNotIn(b'\x1b[',out)


if __name__ == '__main__':
    unittest.main()

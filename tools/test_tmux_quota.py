#!/usr/bin/env python3
"""Quota providers, configuration and private tmux consumers; never live accounts."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'config/tmux'),str(ROOT/'lib/dots')]
spec=importlib.util.spec_from_file_location('quota',ROOT/'config/tmux/codex-usage.py')
quota=importlib.util.module_from_spec(spec);spec.loader.exec_module(quota)
import codex_quota
from status_styles import preferences
from widget_cache import Cache


def report(value=72.9):
    return {'providers':{'codex':{'accounts':[
        {'active':False,'limits':{'seven_day':{'remaining_percent':99}}},
        {'active':True,'email':'private@example.test','limits':{
            'seven_day':{'remaining_percent':value},'five_hour':{'remaining_percent':1},
            'code_review_seven_day':{'remaining_percent':2}}}]}}}


class Quota(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='quota-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.home=self.root/'home space ü';self.home.mkdir()
        self.bin=self.root/'bin';self.bin.mkdir()
        env={k:os.environ[k] for k in ('PATH','PREFIX','LD_PRELOAD','LD_LIBRARY_PATH') if k in os.environ}
        env.update(HOME=str(self.home),CODEX_HOME=str(self.home/'.codex'),
            XDG_CONFIG_HOME=str(self.root/'config'),XDG_STATE_HOME=str(self.root/'state'),
            XDG_CACHE_HOME=str(self.root/'cache'),XDG_DATA_HOME=str(self.root/'data'),
            TMPDIR=str(self.root),PATH=str(self.bin)+os.pathsep+env.get('PATH',''))
        self.env=env;self.environment=patch.dict(os.environ,env,clear=True);self.environment.start();self.addCleanup(self.environment.stop)
        preferences.cache_clear();self.addCleanup(preferences.cache_clear)
        self.tool=self.bin/'aistat'
        self.response=self.home/'response';self.response.write_text(json.dumps(report()))
        self.provider('print((home/"response").read_text())')

    def provider(self,body):
        self.tool.write_text('#!'+sys.executable+'\nfrom pathlib import Path\nimport sys,time\nhome=Path.home()\nwith (home/"calls").open("a") as f:f.write(" ".join(sys.argv[1:])+"\\n")\n'+body+'\n')
        self.tool.chmod(0o700)

    def publish(self,options=None):
        p=self.root/'state/dots/current/theme/preferences.json';p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps({'schema':1,'apps':{'tmux':{'options':{'codex_usage':options or {}}}}}))
        preferences.cache_clear()

    def seed(self,value=72,elapsed=0,failed=False):
        cache=Cache('codex-usage',quota.identity(str(self.tool)))
        with cache.locked():cache.write(dict(value={'remaining_percent':value},updated=time.time()-elapsed,next_at=time.time()+600,failed=failed))
        return cache

    def wait_value(self,text):
        deadline=time.monotonic()+6
        while True:
            value=quota.main([])
            if text in value:return value
            self.assertLess(time.monotonic(),deadline,value);time.sleep(.05)

    def test_active_weekly_only_and_invalid_data(self):
        self.assertEqual(codex_quota.parse(json.dumps(report())),{'remaining_percent':72.9})
        for value in (True,-1,101,float('nan'),'72',None):
            with self.subTest(value=value),self.assertRaises(ValueError):codex_quota.parse(json.dumps(report(value)))
        for change in ('none','two','error','missing'):
            data=report();rows=data['providers']['codex']['accounts']
            if change=='none':rows[1]['active']=False
            if change=='two':rows[0]['active']=True
            if change=='error':rows[1]['error']='private diagnostics'
            if change=='missing':del rows[1]['limits']['seven_day']
            with self.assertRaises((ValueError,KeyError)):codex_quota.parse(json.dumps(data))

    def test_colors_zero_rounding_and_literal_styles(self):
        for value,color in ((0,'red'),(9.9,'red'),(10,'colour208'),(24.9,'colour208'),(25,'yellow'),(49.9,'yellow'),(50,'green'),(100,'green'),(None,'brightblack')):
            output=quota.render(value,{})
            self.assertIn('fg='+color,output);self.assertIn('bold',output)
        self.assertIn('72%',quota.render(72.9,{}));self.assertIn('0%',quota.render(0,{}))
        prefs={'icons':{'codex_usage':'#(BAD)'},'colors':{'codex_usage.icon':{'bold':False,'bg':'#112233'},'codex_usage.good':{'fg':'#abcdef'}},'formatting':{'codex_usage':{'before':'[','after':']','spacer':':','width':5,'alignment':'left'}}}
        out=quota.render(72,prefs,True)
        self.assertIn('##(BAD)',out);self.assertIn('72%  ~',out);self.assertIn('nobold',out);self.assertIn('fg=#abcdef',out)

    def test_disabled_or_missing_provider_has_no_cache_or_worker(self):
        self.publish({'enabled':False})
        with patch.object(Cache,'schedule') as schedule:
            self.assertEqual(quota.main([]),'');schedule.assert_not_called()
        self.publish()
        with patch.object(codex_quota.shutil,'which',return_value=None),patch.object(Cache,'schedule') as schedule:
            self.assertEqual(quota.main([]),'');schedule.assert_not_called()
        self.assertFalse((self.root/'cache').exists())

    def test_retention_only_failure_expiry_and_identity(self):
        for elapsed,failed,expected in ((100,False,'72%'),(100,True,'72%~'),(301,True,'?%')):
            self.seed(elapsed=elapsed,failed=failed)
            with patch.object(Cache,'schedule'):
                out=quota.main([]);self.assertIn(expected,out)
                if not failed:self.assertNotIn('~',out)
        self.seed();auth=self.home/'.codex/auth.json';auth.parent.mkdir();auth.write_text('fixture identity')
        with patch.object(Cache,'schedule'):self.assertNotIn('72%',quota.main([]))

    def test_real_worker_coalescing_and_warm_latency(self):
        argv=[sys.executable,'-B',str(ROOT/'config/tmux/codex-usage.py')]
        children=[subprocess.Popen(argv,env=self.env,stdout=subprocess.PIPE,stderr=subprocess.PIPE) for _ in range(8)]
        for child in children:
            out,err=child.communicate(timeout=5);self.assertEqual(child.returncode,0);self.assertEqual(err,b'')
        self.wait_value('72%');times=[]
        for _ in range(10):
            start=time.monotonic();self.assertIn('72%',quota.main([]));times.append(time.monotonic()-start)
        self.assertLess(max(times),.25)
        self.assertEqual((self.home/'calls').read_text(),'usage codex\n')
        self.assertNotIn('private@',next((self.root/'cache/dots/tmux-widgets').glob('*.json')).read_text())
        print('quota warm render max: %.2f ms'%(max(times)*1000))

    def test_provider_timeout_and_obsolete_result(self):
        self.provider('time.sleep(10)');self.publish({'timeout_seconds':1})
        initial=quota.identity(str(self.tool));cache=Cache('codex-usage',initial)
        with cache.locked():cache.write(dict(token='test',lease=0))
        start=time.monotonic();quota.main(['--_worker','test'])
        self.assertLess(time.monotonic()-start,2);self.assertTrue(cache.read()['failed'])
        self.provider('(home/".codex").mkdir(exist_ok=True)\n(home/".codex/auth.json").write_text("new fixture identity")\nprint((home/"response").read_text())')
        cache=Cache('codex-usage',quota.identity(str(self.tool)))
        with cache.locked():cache.write(dict(token='test',lease=0))
        quota.main(['--_worker','test']);self.assertTrue(cache.read()['failed']);self.assertNotIn('remaining_percent',cache.read().get('value',{}))

    def cli(self, *args, **overrides):
        return subprocess.run([str(ROOT/'scripts/codex-usage'), *args], env={**self.env, **overrides},
                              cwd=self.home, capture_output=True, text=True, timeout=6)

    def test_terminal_and_tmux_join_one_refresh(self):
        self.provider('time.sleep(.3)\nprint((home/"response").read_text())')
        self.assertIn('?%', quota.main([]))
        clients = [subprocess.Popen([str(ROOT/'scripts/codex-usage')], env=self.env,
                                    cwd=self.home, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                   for _ in range(5)]
        for client in clients:
            self.assertEqual(client.communicate(timeout=5), ('  72%\n'.encode(), b''))
            self.assertEqual(client.returncode, 0)
        self.assertIn('72%', quota.main([]))
        self.assertEqual(self.cli().stdout, '  72%\n')
        self.assertEqual((self.home/'calls').read_text(), 'usage codex\n')

    def test_explicit_request_disabled_widget_and_go_install(self):
        self.publish({'enabled': False})
        self.response.write_text(json.dumps(report(0)))
        go_bin = self.home/'go/bin'
        go_bin.mkdir(parents=True)
        self.tool.rename(go_bin/'aistat')
        # Restrict PATH to the launcher's own tools, never a real provider.
        for name in ('bash', 'dirname', 'python3', 'readlink'):
            (self.bin/name).symlink_to(shutil.which(name))
        self.assertEqual(quota.main([]), '')
        result = self.cli(PATH=str(self.bin))
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, '  0%\n', ''))
        (go_bin/'aistat').unlink()
        result = self.cli(PATH=str(self.bin))
        self.assertEqual((result.returncode, result.stdout), (1, '  ?%\n'))
        self.assertIn('aistat is unavailable', result.stderr)

    def test_cli_unknown_stale_expiry_and_timeout(self):
        self.provider('print("private provider failure", file=sys.stderr)\nsys.exit(1)')
        self.seed(value=19, elapsed=100)
        result = self.cli()
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, '  19%~\n', ''))
        self.seed(value=19, elapsed=301, failed=True)
        result = self.cli()
        self.assertEqual((result.returncode, result.stdout), (1, '  ?%\n'))
        self.assertNotIn('private', result.stderr)
        self.publish({'timeout_seconds': 1})
        self.provider('time.sleep(8)')
        start = time.monotonic()
        result = self.cli()
        self.assertLess(time.monotonic() - start, 2.5)
        self.assertEqual((result.returncode, result.stdout), (1, '  ?%\n'))
        cache = Cache('codex-usage', quota.identity(str(self.tool)))
        deadline = time.monotonic() + 2
        while cache.read().get('lease'):
            self.assertLess(time.monotonic(), deadline)
            time.sleep(.05)
        self.assertTrue(cache.read()['failed'])

    def test_cli_widget_styles_plain_and_tty(self):
        import pty
        self.seed()
        self.publish()
        snapshot = self.root/'state/dots/current/theme/preferences.json'
        data = json.loads(snapshot.read_text())
        prefs = data['apps']['tmux']
        prefs.update(icons={'codex_usage': '#[雪]'}, formatting={'codex_usage': {
            'before': '[', 'after': ']', 'width': 5, 'alignment': 'left', 'spacer': ':'}},
            colors={'codex_usage.good': {'fg': '#abcdef'}, 'codex_usage.icon': {
                    'bold': False, 'bg': '#112233'}})
        snapshot.write_text(json.dumps(data))
        expected = '[#[雪]:72%  ]'
        self.assertEqual(self.cli().stdout, expected + '\n')
        self.assertEqual(self.cli(DOTS_ICONS='never').stdout, '[72%  ]\n')
        for no_color in ('', '1'):
            read_fd, write_fd = pty.openpty()
            try:
                result = subprocess.run([str(ROOT/'scripts/codex-usage')], stdout=write_fd,
                    stderr=subprocess.PIPE, env={**self.env, 'TERM': 'xterm-256color', 'NO_COLOR': no_color},
                    timeout=4)
                raw = os.read(read_fd, 2048).decode().rstrip('\r\n')
            finally:
                os.close(write_fd)
                os.close(read_fd)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(re.sub(r'\x1b\[[0-9;]*m', '', raw), expected)
            if no_color:
                self.assertEqual(raw, expected)
            else:
                self.assertIn('\x1b[0;38;2;171;205;239;48;2;17;34;51m#[雪]', raw)
                self.assertIn('\x1b[0;1;38;2;171;205;239m72%', raw)
                self.assertTrue(raw.endswith('\x1b[0m'))

    def test_cli_help_completion_and_bad_arguments_do_not_fetch(self):
        for args in [('--help',), ('-h',)]:
            result = self.cli(*args)
            self.assertEqual(result.returncode, 0)
            self.assertIn('weekly quota', result.stdout)
        self.assertEqual(self.cli('--_worker', 'token').returncode, 2)
        from native_completion import complete
        for shell in ('nu', 'xonsh', 'powershell'):
            self.assertEqual([row['value'] for row in complete(ROOT, shell, ['codex-usage', '--h'])], ['--help'])
        for shell in ('bash', 'fish', 'zsh'):
            argv = [str(ROOT/'bin/dots'), '__complete', shell, '1']
            if shell == 'zsh':
                argv.append('--display-types')
            result = subprocess.run([*argv, '--', 'codex-usage', '--h'], env=self.env,
                                    capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            fields = result.stdout.rstrip('\n').split('\t')
            self.assertEqual(fields[:2], ['candidate', '--help'])
            if shell == 'zsh':
                self.assertEqual(fields[-1], 'option')
        self.assertFalse((self.home/'calls').exists())
        self.assertFalse((self.root/'cache').exists())

    def test_config_validation_and_catalog(self):
        from config_values import read_defaults,validate_value,validate_effective,constraints
        from style_catalog import supported
        defaults=read_defaults(ROOT)
        for key,bad in (('refresh_seconds',0),('timeout_seconds',61),('green_at',101),('enabled',1)):
            with self.assertRaises(ValueError):validate_value(defaults,('apps','tmux','codex_usage',key),bad)
        values=copy.deepcopy(defaults);values['apps']['tmux']['codex_usage']['orange_at']=50
        with self.assertRaises(ValueError):validate_effective(values,defaults,None,'termux')
        for role in ('good','critical','icon','text','surround','spacer','git_separator'):
            for field in ('fg','bg','bold'):self.assertTrue(supported('colors','apps.tmux.codex_usage.'+role+'.'+field))
        self.assertTrue(supported('icons','apps.tmux.codex_usage'))
        self.assertEqual(constraints(defaults,'apps.tmux.codex_usage.refresh_seconds')['type'],'integer')

    def test_shared_battery_padding_preserves_marker_slot(self):
        spec=importlib.util.spec_from_file_location('battery',ROOT/'config/tmux/battery-status.py')
        battery=importlib.util.module_from_spec(spec);spec.loader.exec_module(battery)
        fmt=json.loads((ROOT/'default/config.json').read_text())['formatting']['apps']['tmux']['battery']
        prefs={'formatting':{'battery':fmt},'icons':{'battery.normal':'B','battery.unknown':'B'}}
        from status_styles import cells
        for percent,tail in ((1,'1%  '),(80,'80% '),(100,'100% '),(None,'?%  ')):
            raw='' if percent is None else '\x1b[32mB '+str(percent)+'%\x1b[0m'
            fresh=battery.render(raw,['red','yellow','green','brightblack'],True,prefs)
            stale=battery.render(raw,['red','yellow','green','brightblack'],True,prefs,True)
            self.assertEqual(re.sub(r'#\[[^]]*\]','',fresh),' B '+tail)
            self.assertEqual(cells(fresh),cells(stale))


from test_config_layout import GeneratedStatus

class NativeQuota(GeneratedStatus):
    def setUp(self):
        super().setUp()
        # General status fixtures omit this optional adapter. Only these cases
        # install it, alongside a fake provider before any client is attached.
        for name in ('codex-usage.py', 'codex_quota.py'):
            shutil.copy2(ROOT/'config/tmux'/name, self.tmux_config/name)

    def test_quota_cells_visibility_modes_and_right_placement(self):
        profile=self.repo/'profiles/termux'
        (profile/'icons.toml').write_text('[apps.tmux]\ncodex_usage="Q"\n')
        self.write_theme()
        provider=self.tools/'aistat'
        provider.write_text('#!'+sys.executable+'\nimport json\nfrom pathlib import Path\np=Path.home()\nwith (p/"quota-calls").open("a") as f:f.write("call\\n")\nprint((p/"quota-response").read_text())\n');provider.chmod(0o700)
        (self.home/'quota-response').write_text(json.dumps(report(72)))
        inner,base=self.server('quota-inner')
        config=self.write_config(workspace_hooks=False);inner('source-file',str(config))
        inner('set-option','-g','status-interval','1')
        inner('set-option','-g','@dots-window-codex','#{==:#{window_name},codex-fixture}')
        inner('set-option','-g','@dots-gitmux','#[fg=magenta]BRANCH#[default]')
        outer,_=self.server('quota-view',termux=False);outer('set-option','-g','status','off');outer('set-option','-g','default-terminal','tmux-256color')
        attach=shlex.join(['env','-u','TMUX','-u','TMUX_PANE',*base,'attach-session','-t','fixture'])
        outer('new-session','-d','-s','view','-x','80','-y','24',attach)
        self.await_screen(outer,'view',lambda rows:len(rows)>1 and 'BRANCH' in rows[1])
        self.assertFalse((self.home/'quota-calls').exists())
        inner('rename-window','-t','fixture:0','codex-fixture')
        for width in (40,80,120):
            outer('resize-window','-t','view','-x',str(width),'-y','24')
            rows=self.await_screen(outer,'view',lambda rows:len(rows)>1 and 'Q 72%' in self.plain(rows[1]) and 'BRANCH' in rows[1] and self.plain(rows[1]).index('BRANCH')>=width-10 and len(self.plain(rows[1]))<=width)
            line=self.plain(rows[1]);self.assertLess(line.index('Q 72%'),line.index('BRANCH'))
            self.assertIn('Q 72% · BRANCH',line)
            self.assertEqual(self.colors_at(rows[1],'·')['fg'],(136,136,136))
            self.assertEqual(self.colors_at(rows[1],'·')['bg'],self.colors_at(rows[1],'BRANCH')['bg'])
            self.assertFalse(self.bold_at(rows[1],'·'))
            self.assertGreaterEqual(line.index('BRANCH'),width-10)
            self.assertTrue(self.bold_at(rows[1],'Q'));self.assertTrue(self.bold_at(rows[1],'72%'))
            self.assertEqual(self.colors_at(rows[1],'Q')['fg'],(0,255,0))
            self.assertEqual(self.colors_at(rows[1],'BRANCH',-1)['bg'],self.colors_at(rows[1],'BRANCH')['bg'])
        cache=next(Path(self.env['XDG_CACHE_HOME']).glob('dots/tmux-widgets/codex-usage-*.json'))
        for value,failed,elapsed,label,color in ((25,False,0,'25%',(255,255,0)),(10,False,0,'10%',(255,136,0)),(0,False,0,'0%',(255,0,0)),(72,True,20,'72%~',(0,255,0)),(72,True,301,'?%',(136,136,136)),(72,False,0,'72%',(0,255,0))):
            row=json.loads(cache.read_text());row.update(value={'remaining_percent':value},failed=failed,updated=time.time()-elapsed,next_at=time.time()+600)
            cache.write_text(json.dumps(row))
            rows=self.await_screen(outer,'view',lambda rows:len(rows)>1 and 'Q '+label in self.plain(rows[1]) and (label.endswith('~') or '~' not in self.plain(rows[1])))
            self.assertEqual(self.colors_at(rows[1],'Q')['fg'],color)
            self.assertEqual(self.colors_at(rows[1],label)['fg'],color)
            self.assertTrue(self.bold_at(rows[1],label))
        inner('source-file',str(self.write_theme(background='#eeeeee',dark_background='#dddddd')))
        self.await_screen(outer,'view',lambda rows:len(rows)>1 and 'Q 72%' in self.plain(rows[1]) and self.colors_at(rows[1],'72%')['bg']==(238,238,238),styled=True)
        inner('new-session','-d','-s','ordinary',shutil.which('sleep')+' 60')
        attach_other=shlex.join(['env','-u','TMUX','-u','TMUX_PANE',*base,'attach-session','-t','ordinary'])
        outer('new-window','-d','-t','view:1','-n','other',attach_other)
        self.await_screen(outer,'view:1',lambda rows:len(rows)>1 and 'BRANCH' in rows[1] and 'Q 72%' not in self.plain(rows[1]))
        inner('set-option','-g','status-right','#[bold] MODE #[default]')
        rows=self.await_screen(outer,'view',lambda rows:len(rows)>1 and 'MODE' in rows[1] and 'Q 72%' in self.plain(rows[1]))
        line=self.plain(rows[1]);self.assertLess(line.index('BRANCH'),line.index('MODE'))
        inner('set-option','-g','@dots-gitmux','')
        rows=self.await_screen(outer,'view',lambda rows:len(rows)>1 and 'Q 72%' in self.plain(rows[1]) and 'BRANCH' not in rows[1])
        self.assertNotIn('·',self.plain(rows[1]))
        inner('rename-window','-t','fixture:0','shell')
        self.await_screen(outer,'view',lambda rows:len(rows)>1 and 'Q 72%' not in self.plain(rows[1]))
        self.assertEqual((self.home/'quota-calls').read_text(),'call\n')

    def test_profile_quota_publication_inheritance_and_icon_sample(self):
        profile=self.repo/'profiles/termux'
        data=json.loads((profile/'profile.json').read_text())
        data['apps']={'tmux':{'codex_usage':{'green_at':80}}}
        data['formatting']={'apps':{'tmux':{'codex_usage':{'before':'[','after':']','width':5,'alignment':'left'}}}}
        (profile/'profile.json').write_text(json.dumps(data))
        (profile/'icons.toml').write_text('[apps.tmux]\ncodex_usage=""\n')
        (profile/'colors.toml').write_text('[apps.tmux.codex_usage.medium]\nfg="#112244"\n[apps.tmux.codex_usage.text]\nbold=false\nbg="#ffeeaa"\n')
        self.write_theme(background='#eeeeee',dark_background='#dddddd')
        p=Path(self.env['XDG_STATE_HOME'])/'dots/current/theme/preferences.json'
        prefs=json.loads(p.read_text())['apps']['tmux']
        self.assertEqual(prefs['options']['codex_usage']['refresh_seconds'],90)
        self.assertEqual(prefs['options']['codex_usage']['green_at'],80)
        text=quota.render(72,prefs)
        self.assertEqual(re.sub(r'#\[[^]]*\]','',text),'[72%  ]')
        self.assertIn('fg=#112244',text);self.assertIn('bg=#ffeeaa',text);self.assertIn('nobold',text)


def load_tests(loader,tests,pattern):
    return unittest.TestSuite([loader.loadTestsFromTestCase(Quota),NativeQuota('test_quota_cells_visibility_modes_and_right_placement'),NativeQuota('test_profile_quota_publication_inheritance_and_icon_sample')])


if __name__=='__main__':unittest.main()

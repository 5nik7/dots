#!/usr/bin/env python3
"""Retained widget state and bounded workers; all providers/roots are owned."""
from datetime import datetime,timedelta,timezone as dt_timezone
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'config/tmux'),str(ROOT/'lib/dots'),str(ROOT/'lib/dots/wttr')]
from widget_cache import Cache,age,command
from status_styles import preferences
from wttr import core

def module(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'config/tmux'/f'{name}-status.py')
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result

battery=module('battery');git=module('gitmux');solar=module('weather')

class Widgets(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='widget-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.home=self.root/'home space ü';self.home.mkdir()
        self.bin=self.root/'bin';self.bin.mkdir()
        env={key:os.environ[key] for key in ('PATH','PREFIX','LD_PRELOAD','LD_LIBRARY_PATH') if key in os.environ}
        env.update(HOME=str(self.home),XDG_CONFIG_HOME=str(self.root/'config'),XDG_CACHE_HOME=str(self.root/'cache'),XDG_STATE_HOME=str(self.root/'state'),XDG_DATA_HOME=str(self.root/'data'),TMPDIR=str(self.root),TZ='UTC',TERMUX_VERSION='fixture',PATH=str(self.bin)+os.pathsep+env.get('PATH',''))
        self.env=env;self.environment=patch.dict(os.environ,env,clear=True);self.environment.start();self.addCleanup(self.environment.stop)
        preferences.cache_clear();self.addCleanup(preferences.cache_clear)
        self.cfg_path=self.root/'weather.toml';self.cfg_path.write_text('default_location="Fixture Town"\n')
        _,self.cfg=core.config(self.cfg_path)
        self.now=datetime.now().replace(microsecond=0)
        self.data={'current_condition':[{'weatherCode':'113'}],'weather':[{'date':self.now.date().isoformat(),'astronomy':[{'sunrise':'06:00 AM','sunset':'06:00 PM'}]}]}

    def provider(self,name,body):
        path=self.bin/name;path.write_text('#!'+sys.executable+'\n'+body+'\n');path.chmod(0o700);return path

    def seed(self,cache,value,updated=None,**extra):
        with cache.locked():cache.write(dict(value=value,updated=updated or time.time(),next_at=time.time()+600,**extra))

    def worker(self,cache,producer):
        with cache.locked():
            row=cache.read();row.update(token='fixture',lease=time.time()+10);cache.write(row)
        cache.work('fixture',producer,30)
        return cache.read()

    def test_read_only_missing_and_private_atomic_storage(self):
        cache=Cache('test','one');self.assertEqual(cache.read(),{});self.assertFalse(cache.root.exists())
        self.seed(cache,{'text':'value'})
        self.assertEqual(cache.path.stat().st_mode&0o777,0o600)
        self.assertEqual(cache.root.stat().st_mode&0o777,0o700)
        for payload in ('[]','{"schema":1,"written":NaN}','['*2000):
            cache.path.write_text(payload);self.assertEqual(cache.read(),{})
        cache.path.unlink();target=self.root/'target';target.write_text('untouched');cache.path.symlink_to(target)
        self.assertEqual(cache.read(),{})
        with self.assertRaises(ValueError):self.seed(cache,{})
        self.assertEqual(target.read_text(),'untouched')

    def test_clock_reversal_special_files_and_stale_token(self):
        cache=Cache('test','two');self.seed(cache,{'ok':True})
        with patch('widget_cache.time.time',return_value=time.time()-60):self.assertEqual(cache.read(),{})
        before=cache.path.read_bytes();cache.work('wrong',lambda x:({},1),1);self.assertEqual(cache.path.read_bytes(),before)
        cache.path.unlink();os.mkfifo(cache.path);self.assertEqual(cache.read(),{})
        cache.path.unlink();cache.path.with_suffix('.lock').unlink();os.mkfifo(cache.path.with_suffix('.lock'))
        with self.assertRaises(ValueError):
            with cache.locked():pass

    def test_schedule_coalesces_and_recovers_expired_lease(self):
        cache=Cache('test','schedule')
        with patch('widget_cache.subprocess.Popen') as spawn:
            for _ in range(8):cache.schedule('script',timeout=1)
            self.assertEqual(spawn.call_count,1)
            row=cache.read();row['lease']=time.time()-1
            with cache.locked():cache.write(row)
            cache.schedule('script');self.assertEqual(spawn.call_count,2)
        row=self.worker(cache,lambda previous:({'ok':True},30));updated=row['updated']
        def fail(previous):raise ValueError('PRIVATE diagnostics')
        row=self.worker(cache,fail)
        self.assertEqual(row['value'],{'ok':True});self.assertEqual(row['updated'],updated);self.assertTrue(row['failed'])
        self.assertNotIn('PRIVATE',cache.path.read_text())

    def test_provider_deadline_caps_and_descendant_cleanup(self):
        for body,error in [('print("x"*10000)',ValueError),('import time;time.sleep(10)',TimeoutError),('import subprocess;subprocess.Popen(["sleep","10"])',TimeoutError)]:
            tool=self.provider('provider',body);started=time.monotonic()
            with self.assertRaises(error):command([str(tool)],.2,512)
            self.assertLess(time.monotonic()-started,1)
        self.assertEqual(command([str(self.provider('provider','print("ok")'))],1,512),'ok\n')

    def test_battery_retention_expiry_and_marker_width(self):
        raw='\x1b[32m󰁹 80%\x1b[0m';cache=Cache('battery',[str(self.home),{}])
        self.seed(cache,{'output':raw},updated=time.time()-40,failed=True)
        args=['--slot','red','yellow','green','brightblack']
        with patch.object(Cache,'schedule'):
            result=battery.main(args)
            self.assertIn('80% ~',result)
            self.seed(cache,{'output':raw},updated=time.time()-301,failed=True)
            self.assertIn('?%',battery.main(args))
            self.seed(cache,{'output':raw})
            self.assertNotIn('~',battery.main(args))
        from status_styles import cells
        for pct in (1,80,100):
            value=f'\x1b[32m󰁹 {pct}%\x1b[0m'
            self.assertEqual(cells(battery.render(value,args[1:],True,{},False)),cells(battery.render(value,args[1:],True,{},True)))

    def test_real_battery_worker_and_fast_warm_reads(self):
        tool=self.home/'repos/battery/battery';tool.parent.mkdir(parents=True)
        tool.write_text('printf "call\\n" >> "$HOME/calls"\nprintf "\\033[32m󰁹 80%%\\033[0m"\n')
        args=['--slot','red','yellow','green','brightblack']
        self.assertIn('?%',battery.main(args))
        deadline=time.monotonic()+5
        while '80%' not in battery.main(args):
            self.assertLess(time.monotonic(),deadline);time.sleep(.05)
        starts=[]
        for _ in range(10):
            start=time.monotonic();battery.main(args);starts.append(time.monotonic()-start)
        self.assertEqual((self.home/'calls').read_text(),'call\n')
        self.assertLess(max(starts),.25)

    def test_concurrent_battery_renderers_share_one_worker(self):
        tool=self.home/'repos/battery/battery';tool.parent.mkdir(parents=True)
        tool.write_text('printf "call\\n" >> "$HOME/calls"\nsleep .2\nprintf "\\033[32m󰁹 80%%\\033[0m"\n')
        argv=[sys.executable,'-B',str(ROOT/'config/tmux/battery-status.py'),'--slot','red','yellow','green','brightblack']
        processes=[subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE) for _ in range(8)]
        for process in processes:
            out,err=process.communicate(timeout=5);self.assertEqual(process.returncode,0);self.assertEqual(err,b'')
        deadline=time.monotonic()+5
        while '80%' not in battery.main(argv[3:]):
            self.assertLess(time.monotonic(),deadline);time.sleep(.05)
        self.assertEqual((self.home/'calls').read_text(),'call\n')

    def repo(self):
        path=self.home/'repo space ü';path.mkdir();(path/'.git').mkdir();(path/'.git/HEAD').write_text('ref: refs/heads/main\n')
        return path

    def test_git_identity_and_nonrepository(self):
        repo=self.repo();first=git.repository(repo)
        (repo/'child').mkdir();self.assertNotEqual(first,git.repository(repo/'child'))
        (repo/'.git/HEAD').write_text('ref: refs/heads/other\n');self.assertNotEqual(first,git.repository(repo))
        self.assertEqual(git.cached_status(self.home),'|')
        work=self.home/'work';work.mkdir();(work/'.git').write_text('gitdir: ../repo space ü/.git\n')
        self.assertEqual(git.repository(work)[3],first[3])

    def test_git_retention_independent_fields_and_expiry(self):
        repo=self.repo()
        with patch.object(Cache,'schedule'),patch.object(Cache,'read',return_value={'value':{'gitmux':{'value':'branch#{unsafe}','updated':time.time()-10,'failed':True},'icon':{'value':'󰊤','updated':time.time()}}}):
            output=git.cached_status(repo);self.assertIn('󰊤|',output);self.assertIn('~',output);self.assertIn('branch##{unsafe}',output)
        with patch.object(Cache,'schedule'),patch.object(Cache,'read',return_value={'value':{'gitmux':{'value':'old','updated':time.time()-31}}}):
            output=git.cached_status(repo);self.assertIn(' ?',output);self.assertNotIn('old',output)
        with patch.object(Cache,'schedule'),patch.object(Cache,'read',return_value={'value':{'gitmux':{'value':'unsafe\x1b','updated':time.time()}}}):self.assertNotIn('unsafe',git.cached_status(repo))

    def test_git_unavailable_head_keeps_unknown_slot(self):
        repo=self.repo();(repo/'.git/HEAD').unlink()
        result=subprocess.run([sys.executable,'-B',str(ROOT/'config/tmux/gitmux-status.py'),'--snapshot',str(repo)],capture_output=True,text=True,timeout=2)
        self.assertEqual(result.returncode,0);self.assertEqual(result.stderr,'')
        self.assertIn('|#[fg=',result.stdout);self.assertIn(' ?',result.stdout)

    def test_real_git_worker_failure_and_branch_invalidation(self):
        repo=self.repo();self.provider('gitmux','print("main")');self.provider('git-it','print(\'{"remote":"origin","icon":"󰊤"}\')')
        self.assertIn('?',git.cached_status(repo));deadline=time.monotonic()+5
        while 'main' not in git.cached_status(repo):
            self.assertLess(time.monotonic(),deadline);time.sleep(.05)
        self.provider('gitmux','raise SystemExit(1)')
        for path in (self.root/'cache/dots/tmux-widgets').glob('git-*.json'):
            row=json.loads(path.read_text());row['next_at']=0;path.write_text(json.dumps(row))
        git.cached_status(repo)
        deadline=time.monotonic()+5
        while '~' not in git.cached_status(repo):
            self.assertLess(time.monotonic(),deadline);time.sleep(.05)
        self.assertIn('main',git.cached_status(repo))
        (repo/'.git/HEAD').write_text('ref: refs/heads/new\n')
        with patch.object(Cache,'schedule'):self.assertNotIn('main',git.cached_status(repo))

    def test_solar_boundaries_rollover_expiry_timezone(self):
        now=self.now.replace(hour=12,minute=0,second=0)
        value={'days':{now.date().isoformat():['06:00','18:00']},'solar_updated':(now-timedelta(hours=10)).timestamp(),'timezone':solar.timezone()}
        for hour,expected in [(5,'night'),(6,'day'),(17,'day'),(18,'night')]:
            self.assertEqual(solar.daylight(value,604800,now.replace(hour=hour)),expected)
        self.assertEqual(solar.daylight(value,604800,now+timedelta(days=6)),'day')
        self.assertEqual(solar.daylight(value,604800,now+timedelta(days=7)),'unknown')
        value['timezone']=['changed'];self.assertEqual(solar.daylight(value,604800,now),'unknown')

    def seed_weather(self,location='Fixture Town',age_seconds=0):
        cache=core.Cache(self.cfg)
        core.atomic(cache.path,dict(schema=2,updated=time.time()-age_seconds,data=self.data,location=location,source='cached city',lease=0,retry_at=0))
        return cache

    def test_solar_uses_old_weather_without_changing_raw_weather_contract(self):
        cache=self.seed_weather(age_seconds=40000)
        with patch.object(core.Cache,'refresh',side_effect=core.Unavailable('offline')):
            value,delay=solar.refresh({},self.cfg_path,{},False)
        self.assertEqual(value['days'],solar.solar_days(self.data))
        self.assertEqual(value['solar_updated'],cache.read()['updated'])
        self.assertEqual(core.fields(cache.read(),self.cfg,40000)['daylight'],'unknown')

    def test_location_change_drops_old_sun_times_even_on_weather_failure(self):
        self.seed_weather(location='Old Town')
        old={'location':solar.location_id('Old Town'),'days':{'2000-01-01':['06:00','18:00']},'solar_updated':time.time()}
        with patch.object(core.Cache,'refresh',side_effect=core.Unavailable('offline')):
            value,_=solar.refresh(old,self.cfg_path,{},False)
        self.assertNotIn('days',value)

    def test_geo_interval_backoff_and_opt_out(self):
        self.cfg_path.write_text('default_location=""\n');_,self.cfg=core.config(self.cfg_path)
        self.seed_weather();options={'auto_location':True}
        with patch.object(core,'geo_helper',return_value='owned-geo'),patch.object(solar,'command',return_value='{"version":1,"city":"Fixture Town","latitude":1,"longitude":2}') as provider,patch.object(core,'resolve_location',return_value=('Fixture Town','cached city','')):
            value,_=solar.refresh({},self.cfg_path,options,True)
            self.assertEqual(provider.call_count,1)
            self.assertAlmostEqual(value['geo_next']-value['geo_updated'],21600,delta=.1)
            self.assertNotIn('latitude',json.dumps(value))
            solar.refresh(value,self.cfg_path,options,True);self.assertEqual(provider.call_count,1)
            solar.refresh({},self.cfg_path,{},True);solar.refresh({},self.cfg_path,options,False);self.assertEqual(provider.call_count,1)
        value={}
        with patch.object(core,'geo_helper',return_value='owned-geo'),patch.object(solar,'command',side_effect=TimeoutError),patch.object(core,'resolve_location',return_value=('Fixture Town','cached city','')):
            for delay in (300,900,3600):
                value['geo_next']=0
                started=time.time();value,_=solar.refresh(value,self.cfg_path,options,True)
                self.assertAlmostEqual(value['geo_next']-started,delay,delta=1)

    def test_geo_missing_helper_and_changed_interval(self):
        self.cfg_path.write_text('default_location=""\n');_,self.cfg=core.config(self.cfg_path)
        self.seed_weather()
        previous={'geo_updated':time.time()-7200,'geo_next':time.time()+14400,'geo_failures':0}
        self.assertLess(solar.next_location(previous,3600),time.time())
        self.assertGreater(solar.next_location(previous,21600),time.time())
        with patch.object(core,'geo_helper',return_value=None),patch.object(core,'resolve_location',return_value=('Fixture Town','cached city','')):
            value,_=solar.refresh(previous,self.cfg_path,{'auto_location':True,'location_refresh_seconds':3600},True)
        self.assertGreater(solar.next_location(value,3600),time.time()+3500)

    def test_real_solar_worker_acquires_once_and_reuses_weather(self):
        fixture=self.root/'fixture';scripts=fixture/'config/tmux';scripts.mkdir(parents=True)
        for name in ('weather-status.py','status_styles.py','widget_cache.py'):
            shutil.copy2(ROOT/'config/tmux'/name,scripts/name)
        (fixture/'lib').mkdir();(fixture/'lib/dots').symlink_to(ROOT/'lib/dots',target_is_directory=True)
        path=fixture/'config/wttr/config.toml';path.parent.mkdir();path.write_text('default_location=""\n')
        _,self.cfg=core.config(path);self.seed_weather()
        projection=Path(self.env['XDG_STATE_HOME'])/'dots/current/theme/preferences.json';projection.parent.mkdir(parents=True)
        projection.write_text(json.dumps({'schema':1,'apps':{'tmux':{'options':{'clock':{'auto_location':True}}}}}))
        self.provider('termux-geo','import pathlib,os,sys\np=pathlib.Path(os.environ["HOME"])/"geo-calls"\np.open("a").write(" ".join(sys.argv[1:])+"\\n")\nprint(\'{"version":1,"city":"Fixture Town","latitude":1,"longitude":2}\')')
        argv=[sys.executable,'-B',str(scripts/'weather-status.py'),'--attached','1']
        deadline=time.monotonic()+5
        while True:
            result=subprocess.run(argv,capture_output=True,timeout=2)
            self.assertEqual(result.stderr,b'')
            if result.stdout in (b'day\n',b'night\n'):break
            self.assertLess(time.monotonic(),deadline);time.sleep(.05)
        self.assertEqual((self.home/'geo-calls').read_text(),'--json --timeout 20\n')
        values=list((self.root/'cache/dots/tmux-widgets').glob('solar-*.json'))
        self.assertEqual(len(values),1);self.assertNotIn('latitude',values[0].read_text())

    def test_resolved_location_refreshes_changed_city_and_honors_cooldown(self):
        cache=self.seed_weather(location='Old Town')
        with patch.object(core,'fetch',return_value=self.data) as fetch:
            row=cache.refresh(background=True,resolved=('New Town','cached city',''))
            self.assertEqual(row['location'],'New Town');self.assertEqual(fetch.call_count,1)
            row['retry_at']=time.time()+600;core.atomic(cache.path,row)
            self.assertEqual(cache.refresh(background=True,resolved=('Other Town','cached city',''))['location'],'New Town')
            self.assertEqual(fetch.call_count,1)

    def test_clock_config_types_constraints_and_projection(self):
        from config_values import read_defaults,validate_value,constraints
        from theme_styles import snapshot
        defaults=read_defaults(ROOT)
        for key,good,bad in [('auto_location',True,'yes'),('location_refresh_seconds',21600,True),('sun_times_max_stale_seconds',604800,604801)]:
            path=('apps','tmux','clock',key);validate_value(defaults,path,good)
            with self.assertRaises(ValueError):validate_value(defaults,path,bad)
            self.assertTrue(constraints(defaults,'.'.join(path)))
        # Existing publication projects typed controls without a second store.
        class Styles:
            root=ROOT;selected={};defaults={};values={'icons':{},'colors':{}}
            def resolve(self,*args):return {'source':None}
        controls={'apps':{'tmux':{'clock':{'auto_location':True}},'nvim':{}}}
        self.assertTrue(snapshot({},styles=Styles(),controls=controls)['apps']['tmux']['options']['clock']['auto_location'])

import test_tmux_status as fixtures

@unittest.skipUnless(fixtures.TMUX,'native tmux unavailable')
class NativeWidgets(fixtures.TmuxStatus):
    def test_native_solar_retention_expiry_and_recovery(self):
        import shlex
        source=self.repo/'config/tmux/weather-status.py'
        shutil.copy2(ROOT/'config/tmux/weather-status.py',source)
        cfg=self.repo/'config/wttr/config.toml';cfg.parent.mkdir(parents=True);cfg.write_text('default_location="Fixture Town"\n')
        self.write_theme()
        with patch.dict(os.environ,self.env,clear=True):
            cache=Cache('solar',[str(cfg.resolve()),'Fixture Town','en'])
        now=datetime.now(dt_timezone.utc).replace(tzinfo=None)
        value={'days':{now.date().isoformat():['06:00','18:00']},'solar_updated':time.time()-3600,
               'timezone':['UTC',['UTC','UTC'],0]}
        def seed(expired=False):
            value['solar_updated']=time.time()-(604801 if expired else 3600)
            with cache.locked():cache.write(dict(value=value,updated=time.time(),next_at=time.time()+3600,failed=True))
        seed()
        inner,base=self.server('solar-retained');inner('source-file',str(self.write_config(workspace_hooks=False)))
        inner('set-option','-g','status-interval','1')
        outer,_=self.server('solar-view',termux=False);outer('set-option','-g','status','off')
        outer('set-option','-g','default-terminal','tmux-256color')
        attach=shlex.join(['env','-u','TMUX','-u','TMUX_PANE',*base,'attach-session','-t','fixture'])
        outer('new-session','-d','-s','view','-x','80','-y','24',attach)
        color=(255,255,0) if 6<=now.hour<18 else (0,0,255)
        for width in (40,48,80,120):
            outer('resize-window','-t','view','-x',str(width),'-y','24')
            for expired,wanted in ((False,color),(True,(238,238,238)),(False,color)):
                seed(expired)
                direct=subprocess.run([sys.executable,'-B',str(source),'--attached','1'],env=self.env,capture_output=True,text=True,timeout=2)
                self.assertEqual(direct.stdout,'unknown\n' if expired else ('day\n' if color==(255,255,0) else 'night\n'),(expired,cache.path,cache.read(),direct.stderr))
                lines=self.await_screen(outer,'view',lambda rows:rows and '80%' in rows[0] and self.colors_at(rows[0],':').get('fg')==wanted,styled=True)
                self.assertLessEqual(len(self.plain(lines[0])),width)
                self.assertEqual(self.colors_at(lines[0],':')['bg'],(34,51,68))
        self.assertFalse((self.home/'weather-calls').exists())


def load_tests(loader,tests,pattern):
    return unittest.TestSuite([loader.loadTestsFromTestCase(Widgets),NativeWidgets('test_native_solar_retention_expiry_and_recovery')])

if __name__=='__main__':unittest.main()

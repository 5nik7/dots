#!/usr/bin/env python3
"""Vibration controls, finite helpers and explicit Debug alerts in owned roots."""
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import patch

import test_codex_toast_config as toast_fixture
import test_profile_config as fixtures
from test_codex_alerts import alerts
from codex_vibration import DEFAULTS,KEYS,run,validate
from config_codex import Native,NativePlan,KEYS as ALL_KEYS
from config_menu import Inventory,Draft
from profile_config import context,keys
from files.file_platform import state_root
from files.transactions import Store
from files.catalog import Presentation
from resources import cells
from debug.presentation import render


class Vibration(unittest.TestCase):
    cli=toast_fixture.ToastConfig.cli

    def setUp(self):
        toast_fixture.ToastConfig.setUp(self)
        shutil.copytree(fixtures.ROOT/'config/tmux',self.toast.parent,dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('__pycache__','*.pyc','codex-alerts.toml'))
        for script in (fixtures.ROOT/'bin').glob('dots-debug*'):shutil.copy2(script,self.root/'bin'/script.name)
        self.log=self.home/'device-calls.jsonl'
        fake=self.home/'device-bin';fake.mkdir()
        for name in ('termux-toast','termux-vibrate'):
            path=fake/name
            path.write_text('#!'+sys.executable+'\nimport json,os,sys,time\nfrom pathlib import Path\n'
                'kind=Path(sys.argv[0]).name\n'
                'with open(os.environ["DEVICE_LOG"],"a") as out: out.write(json.dumps([kind,sys.argv[1:],time.monotonic()])+"\\n")\n'
                'if os.environ.get("DEVICE_SLOW")==kind: time.sleep(6)\n'
                'if os.environ.get("DEVICE_FAIL")==kind: sys.exit(1)\n')
            path.chmod(0o700)
        self.env.update(PATH=str(fake)+os.pathsep+self.env['PATH'],DEVICE_LOG=str(self.log))
        os.environ.update(self.env)
        self.addCleanup(self.cleanup_helpers)

    def cleanup_helpers(self):
        for process in alerts.VIBRATIONS:
            if process.poll() is None:process.terminate()
            process.wait(timeout=10)
        alerts.VIBRATIONS.clear()

    def calls(self):return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def debug(self,*args,native=False,code=0,**env):
        command=([sys.executable,'-B',str(self.root/'lib/dots/cli.py'),'debug'] if native else [str(self.root/'bin/dots'),'debug'])
        p=subprocess.run([*command,*args],env=dict(self.env,**env),capture_output=True,text=True,timeout=25)
        self.assertEqual(p.returncode,code,p.stdout+p.stderr)
        return p

    def test_config_cli_popup_completion_and_reset(self):
        profile=self.path.read_bytes();original=self.toast.read_bytes()
        self.assertEqual(Native(self.root).values['vibrate'],DEFAULTS)
        self.assertEqual(set(k for k in keys(self.root) if k.startswith('apps.codex.')),set(ALL_KEYS))
        for native in (False,True):
            for field,value in (('duration','17'),('force','false'),('count','3')):
                self.cli('set','apps.codex.vibrate.'+field,value,'--json',native=native)
            data=json.loads(self.cli('get','apps.codex.vibrate','--json',native=native).stdout)
            self.assertEqual(data['value'],dict(duration=17,force=False,count=3))
            spec=json.loads(self.cli('explain',KEYS[2],'--json',native=native).stdout)
            self.assertEqual(spec['constraints']['choices'],list(range(11)))
        self.assertEqual(profile,self.path.read_bytes());self.assertFalse(self.log.exists())
        inventory=Inventory(self.root,self.platform)
        for key in KEYS:self.assertEqual(inventory.find(key).kind,'codex')
        draft=Draft(inventory,inventory.find(KEYS[2])).prepare('0')
        self.assertEqual(draft.proposed,0);self.assertIn('alert setting default',Draft(inventory,inventory.find(KEYS[2])).prepare(reset=True).review())
        draft.save();self.assertEqual(Native(self.root).values['vibrate']['count'],0)
        for field in ('duration','force','count'):
            self.cli('unset','apps.codex.vibrate.'+field,'--json')
        with patch.object(alerts,'HERE',self.toast.parent):
            prefs=alerts.preferences();self.assertEqual((prefs['termux']['vibration_ms'],prefs['termux']['force_vibration'],prefs['termux']['vibration_count']),(300,True,1))
        self.assertTrue(Native(self.root).resolve(KEYS[2])['source'].endswith('codex_vibration.py'))
        self.assertIn('toast_foreground = "warning"',self.toast.read_text())
        for shell in ('bash','zsh','fish','native'):
            for key,expected in ((KEYS[1],{'true','false'}),(KEYS[2],{str(n) for n in range(11)}),(KEYS[0],{'100','300','500','1000'})):
                words=['config','set',key,'']
                command=([sys.executable,'-B',str(self.root/'lib/dots/cli.py'),'__complete',*words] if shell=='native' else
                         [str(self.root/'bin/dots'),'__complete',shell,str(len(words)),'--','dots',*words])
                result=subprocess.run(command,env=self.env,text=True,capture_output=True,timeout=25)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual({row.split('\t')[1] for row in result.stdout.splitlines()},expected)

    def test_bounds_dryrun_stale_and_undo(self):
        original=self.toast.read_bytes()
        for field,values in (('duration',[0,10001,True,1.5,'bad']),('force',[0,'yes']),('count',[-1,11,False,1.5,'$(touch NEVER)'])):
            for value in values:
                with self.assertRaises(ValueError):NativePlan(self.root,self.selected).edit('apps.codex.vibrate.'+field,value)
        self.assertEqual(original,self.toast.read_bytes())
        self.cli('set',KEYS[2],'2','--dry-run','--json');self.assertEqual(original,self.toast.read_bytes())
        plan=NativePlan(self.root,self.selected);plan.edit(KEYS[2],2);saved=plan.apply('set')
        again=NativePlan(self.root,self.selected);again.edit(KEYS[2],2);self.assertEqual(again.apply('set')['status'],'unchanged')
        store=Store(state_root());operations,guards,catalogs=store.inverse(saved['id'])
        store.apply('undo',operations,guards,retain=True,catalogs=catalogs);self.assertEqual(original,self.toast.read_bytes())
        stale=NativePlan(self.root,self.selected);stale.edit(KEYS[2],2)
        self.toast.write_text(self.toast.read_text()+'# concurrent edit\n')
        with self.assertRaises(ValueError):stale.apply('set')

    def test_pattern_order_gaps_failure_timeout_and_cancel(self):
        events=[]
        settings=dict(duration=300,force=True,count=3)
        result=run(settings,lambda argv,timeout:events.append((argv,timeout)),sleep=lambda seconds:events.append(seconds))
        self.assertEqual(result['sent'],3)
        self.assertEqual(events[::2],[(['termux-vibrate','-d','300','-f'],5)]*3)
        self.assertEqual(len(events[1::2]),2)
        for delay in events[1::2]:self.assertAlmostEqual(delay,.45)
        for error in (ValueError('failed'),TimeoutError('timed out')):
            seen=[]
            def request(argv,timeout):
                seen.append(argv)
                if len(seen)==2:raise error
            result=run(settings,request,sleep=lambda seconds:None)
            self.assertEqual((result['status'],result['attempted'],result['sent']),('failed',2,1))
        result=run(dict(duration=10,force=False,count=0),lambda *a,**k:self.fail('disabled request'))
        self.assertEqual(result['status'],'skipped')
        cancelled=threading.Event()
        result=run(settings,lambda *a,**k:cancelled.set(),cancel=cancelled)
        self.assertEqual((result['status'],result['sent']),('cancelled',1))

    @unittest.skipIf(os.name=='nt','Termux device adapter uses POSIX helpers')
    def test_repeat_helper_returns_promptly_and_is_reaped(self):
        with patch.dict(os.environ,TERMUX_VERSION='fixture'),patch.object(alerts,'HERE',self.toast.parent):
            prefs=alerts.preferences();prefs['termux'].update(vibration_ms=300,vibration_count=3)
            started=time.monotonic();result=alerts.notify_device('test',prefs)
            self.assertEqual(result['vibrate']['status'],'started')
            self.assertLess(time.monotonic()-started,.8)
            self.assertEqual(len(alerts.VIBRATIONS),1)
            process=alerts.VIBRATIONS[0];process.wait(timeout=10);alerts.reap_vibrations()
            self.assertEqual(alerts.VIBRATIONS,[])
        pulses=[row for row in self.calls() if row[0]=='termux-vibrate']
        self.assertEqual(len(pulses),3)
        self.assertTrue(all(b[2]-a[2]>=.44 for a,b in zip(pulses,pulses[1:])))
        self.assertEqual(sum(row[0]=='termux-toast' for row in self.calls()),1)
        self.assertFalse((state_root()/'codex-alerts').exists())

    @unittest.skipIf(os.name=='nt','Termux device adapter uses POSIX helpers')
    def test_debug_frontends_send_configured_pattern_and_single_toast(self):
        for field,value in (('duration','10'),('force','false'),('count','3')):self.cli('set','apps.codex.vibrate.'+field,value,'--json')
        self.cli('set','apps.codex.toast.bg','#123456','--json')
        self.cli('set','apps.codex.toast.bg_opacity','50','--json')
        before=self.toast.read_bytes();state=list(state_root().rglob('*'))
        reports=[]
        for native in (False,True):
            data=json.loads(self.debug('alert','--json',native=native,TERMUX_VERSION='fixture',DOTS_COLOR='always',DOTS_ICONS='always').stdout)
            reports.append(data)
            self.assertEqual(data['version'],1)
            self.assertEqual(data['results']['vibrate']['sent'],3)
            self.assertEqual(data['results']['toast']['status'],'sent')
            self.assertIn('test',data['message'])
            self.assertNotIn('\x1b',json.dumps(data))
        pulses=[row for row in self.calls() if row[0]=='termux-vibrate'];toasts=[row for row in self.calls() if row[0]=='termux-toast']
        self.assertEqual(len(pulses),6);self.assertEqual(len(toasts),2)
        self.assertTrue(all(row[1]==['-d','10'] for row in pulses))
        self.assertTrue(all(row[1][-1]==data['message'] for row in toasts))
        self.assertTrue(all(row[1][row[1].index('-b')+1]=='#80123456' for row in toasts))
        self.assertEqual(reports[0],reports[1])
        self.assertEqual(before,self.toast.read_bytes());self.assertEqual(state,list(state_root().rglob('*')))
        for width in (40,80,120):
            for colored in (False,True):
                ui=Presentation(io.StringIO(),terminal=True);ui.width=width;ui.color=colored
                with patch('files.catalog.Presentation',return_value=ui):render(data,'alert')
                plain=re.sub(r'\x1b\[[0-9;]*m','',ui.stream.getvalue())
                self.assertIn('3/3 requests',plain)
                self.assertTrue(all(cells(row)<=width for row in plain.splitlines()),plain)

    @unittest.skipIf(os.name=='nt','Termux device adapter uses POSIX helpers')
    def test_debug_report_and_delivery_use_one_configuration_snapshot(self):
        from debug.alert import run as test_alert
        def capture(*args,**kwargs):
            native=Native(*args,**kwargs)
            self.toast.write_text(self.toast.read_text().replace('vibration_ms = 300','vibration_ms = 1'))
            return native
        with patch('config_codex.Native',side_effect=capture),patch.dict(os.environ,TERMUX_VERSION='fixture'):
            result=test_alert(self.root)
        self.assertEqual(result['settings']['vibrate']['duration'],300)
        self.assertIn(['-d','300','-f'],[row[1] for row in self.calls() if row[0]=='termux-vibrate'])
        self.assertEqual(Native(self.root).values['vibrate']['duration'],1)

    @unittest.skipIf(os.name=='nt','Termux device adapter uses POSIX helpers')
    def test_debug_zero_disabled_failure_and_unavailable(self):
        self.cli('set',KEYS[2],'3','--json')
        result=json.loads(self.debug('alert','--json',code=1,TERMUX_VERSION='fixture',DEVICE_FAIL='termux-vibrate').stdout)
        self.assertEqual(result['results']['vibrate']['attempted'],1)
        self.assertEqual(result['results']['toast']['status'],'sent')
        started=time.monotonic()
        result=json.loads(self.debug('alert','--json',native=True,code=1,TERMUX_VERSION='fixture',DEVICE_SLOW='termux-vibrate').stdout)
        self.assertEqual(result['results']['vibrate']['attempted'],1)
        self.assertEqual(result['results']['vibrate']['status'],'failed')
        self.assertEqual(result['results']['toast']['status'],'sent')
        self.assertLess(time.monotonic()-started,9)
        result=json.loads(self.debug('alert','--json',native=True,code=1,TERMUX_VERSION='fixture',PATH='').stdout)
        self.assertTrue(all(row['status']=='unavailable' for row in result['results'].values()))
        self.cli('set',KEYS[2],'0','--json')
        result=json.loads(self.debug('alert','--json',TERMUX_VERSION='fixture').stdout)
        self.assertEqual(result['results']['vibrate']['status'],'skipped')
        count=len(self.calls())
        result=json.loads(self.debug('alert','--json',code=1,TERMUX_VERSION='').stdout)
        self.assertEqual(result['results']['toast']['status'],'unavailable');self.assertEqual(len(self.calls()),count)
        self.toast.write_text(self.toast.read_text().replace('[termux]\nenabled = true','[termux]\nenabled = false'))
        result=json.loads(self.debug('alert','--json',TERMUX_VERSION='fixture').stdout)
        self.assertEqual(result['results']['toast']['status'],'skipped');self.assertEqual(len(self.calls()),count)

    def test_help_completion_and_curated_tests_never_send(self):
        for native in (False,True):
            self.debug('--help',native=native)
            self.debug('alert','--help',native=native)
            listed=json.loads(self.debug('test','--list','--json',native=native).stdout)
            self.assertNotIn('alert',{row['name'] for row in listed['rows']})
        for shell in ('bash','zsh','fish','native'):
            words=['debug','']
            cmd=([sys.executable,'-B',str(self.root/'lib/dots/cli.py'),'__complete',*words] if shell=='native' else
                 [str(self.root/'bin/dots'),'__complete',shell,str(len(words)),'--','dots',*words])
            p=subprocess.run(cmd,env=self.env,capture_output=True,text=True,timeout=20)
            self.assertEqual(p.returncode,0,p.stderr);self.assertIn('\talert\t',p.stdout)
        self.assertFalse(self.log.exists())


if __name__=='__main__':unittest.main()

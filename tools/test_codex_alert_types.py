#!/usr/bin/env python3
"""Question lifecycle and typed alert regressions in owned stores and providers."""
import copy
import io
import json
import os
import time
import unittest
from unittest.mock import patch

import test_codex_alerts as queue
import test_codex_attention as topology
import test_codex_toast_config as native
from codex_notifications import KEYS, LEGACY_KEYS
from config_codex import Native, NativePlan
from config_menu import Inventory
from config_completion import key_candidates, value_candidates
from config_view import listing
from files.catalog import Presentation
from files.file_platform import state_root
from files.transactions import Store

alerts=queue.alerts


class Questions(unittest.TestCase):
    setUp=queue.Queue.setUp
    panes=queue.Queue.panes
    phases=queue.Queue.phases
    run_events=queue.Queue.run_events

    def snapshot(self):
        return json.loads((alerts.status.alert_root()/'socket-a.json').read_text())

    def test_acknowledgement_retains_question_until_answer_or_state_change(self):
        self.panes();alerts.record(queue.event(),self.prefs);self.run_events()
        self.assertEqual(self.snapshot()['questions'],['@2'])
        with alerts.database() as db:alerts.acknowledge(db,'thread=?',(queue.THREAD,))
        self.run_events(False)
        self.assertEqual(self.snapshot()['windows'],[])
        self.assertEqual(self.snapshot()['questions'],['@2'])
        self.panes(state='working');self.run_events()
        self.assertEqual(self.snapshot()['questions'],[])
        self.panes();self.run_events()
        self.assertEqual(self.snapshot()['questions'],[])  # no resurrection
        alerts.record(queue.event(request='request-2'),self.prefs);self.run_events()
        self.assertEqual(self.snapshot()['questions'],['@2'])
        alerts.record(queue.event('PostToolUse',request='request-2'),self.prefs);self.run_events()
        self.assertEqual(self.snapshot()['questions'],[])

    def test_completion_is_typed_and_question_wins_across_panes(self):
        self.panes();alerts.record(queue.event(),self.prefs);self.run_events()
        with alerts.database() as db:alerts.acknowledge(db,'thread=?',(queue.THREAD,))
        self.panes(thread=queue.OTHER,state='idle',pane='%3')
        alerts.record(queue.complete(thread=queue.OTHER),self.prefs)
        with alerts.database() as db:
            delivered,_=alerts.reconcile(db,self.prefs,time.time(),typed=True)
        self.assertEqual(delivered[0]['kind'],'finished')
        self.assertEqual(self.snapshot()['alert_types'],{'@2':'regular'})
        self.assertEqual(self.snapshot()['questions'],['@2'])
        alerts.record(queue.event('PostToolUse'),self.prefs);self.run_events()
        self.assertEqual(self.snapshot()['alert_types'],{'@2':'finished'})
        self.assertEqual(self.snapshot()['questions'],[])

    def test_completion_resolves_own_question_and_never_infers_from_idle(self):
        self.panes();alerts.record(queue.event(),self.prefs);self.run_events()
        alerts.record(queue.complete(),self.prefs);self.run_events()
        self.assertEqual(self.snapshot()['questions'],[])
        self.assertEqual(self.snapshot()['alert_types'],{'@2':'finished'})
        self.assertEqual(len([r for r in self.phases() if r['phase']=='alert']),1)
        alerts.record(queue.event(request='late-question'),self.prefs);self.run_events()
        self.assertEqual(self.snapshot()['questions'],[])
        self.panes(state='idle',thread=queue.OTHER,pane='%3',window='@3');self.run_events()
        self.assertNotIn('@3',self.snapshot()['windows'])
        alerts.record(queue.event('Interrupt'),self.prefs);self.run_events()
        alerts.record(queue.complete(),self.prefs);self.run_events()
        self.assertEqual(self.snapshot()['windows'],[])

    def test_expired_unconfirmed_and_automatic_approval_never_become_question(self):
        self.panes(state='working')
        alerts.record(queue.event(),self.prefs);self.run_events()
        self.assertEqual(self.snapshot()['questions'],[])
        with alerts.database() as db:db.execute('UPDATE events SET created=?',(time.time()-700,))
        self.panes();self.run_events()
        self.assertEqual(self.snapshot()['questions'],[])
        for hook in ('PermissionRequest','PostToolUse'):
            alerts.record(queue.event(hook)|dict(tool_name='Bash',tool_input={'command':'true'}),self.prefs)
        self.run_events()
        self.assertEqual(self.snapshot()['questions'],[])


class TypedViews(unittest.TestCase):
    setUp=topology.Attention.setUp
    process=topology.Attention.process
    publish=topology.Attention.publish

    def test_legacy_and_typed_session_tab_badge_and_question_priority(self):
        panes=self.server['panes']
        panes[1].update(alert_type='finished',state='idle')
        state,badge=topology.attention.tab_states([self.server],self.proc,typed=True)
        self.assertEqual(state[(20,200,'pts/2')]['alert_type'],'finished')
        panes.append(dict(panes[1],pane='%3',thread=queue.OTHER,state='waiting',question=True,attention=False,alert_type=None))
        state,badge=topology.attention.tab_states([self.server],self.proc,typed=True)
        self.assertEqual(state[(20,200,'pts/2')]['alert_type'],'regular')
        self.assertEqual(topology.attention.display_state(state[(20,200,'pts/2')]),'question')
        self.server['clients']=[]
        _,badge=topology.attention.tab_states([self.server],self.proc,typed=True)
        self.assertEqual(badge,dict(count=1,alert_type='regular'))
        panes.pop();_,badge=topology.attention.tab_states([self.server],self.proc,typed=True)
        self.assertEqual(badge,dict(count=1,alert_type='finished'))
        panes[1].pop('alert_type');self.publish()
        self.assertEqual(topology.attention.sessions(topology.attention.load())[1]['alert_type'],'regular')
        panes[1]['alert_type']='unexpected';self.publish();self.assertEqual(topology.attention.load(),[])

    def test_finished_number_only_question_and_overflow_styles(self):
        snapshot=dict(count=10,sessions=[dict(pid=i*10,tty=f'pts/{i}') for i in range(1,11)])
        states={(20,200,'pts/2'):dict(state='idle',attention=True,alert_type='finished'),
                (100,1000,'pts/10'):dict(state='idle',attention=True,alert_type='finished')}
        prefs=dict(colors={'tabs.finished':{'fg':'#00ff00'},'indicators.question':{'fg':'#ff0000','bold':True}})
        colors=['#111111','#aaaaaa','#222222','#ff8800']
        for width in (22,40,80,120):
            result=topology.tabs.render_attention_tabs(snapshot,'pts/1',colors,width,'#555555','#111111',states,dict(count=1,alert_type='finished'),'#ff0000','#101010',prefs)
            plain=topology.re.sub(r'#\[[^]]*\]','',result)
            self.assertLessEqual(len(plain),width);self.assertIn('[2]',plain);self.assertNotIn('',plain)
            self.assertIn('fg=#00ff00',result)
        states[(20,200,'pts/2')].update(question=True,state='waiting')
        result=topology.tabs.render_attention_tabs(snapshot,'pts/1',colors,80,'#555555','#111111',states,0,'#ff0000','#101010',prefs)
        self.assertIn('[2 ]',topology.re.sub(r'#\[[^]]*\]','',result));self.assertNotIn('',result)

    def test_optional_session_alert_styles_and_clipped_priority(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('typed_sessions',queue.ROOT/'config/tmux/session-status.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        prefs=dict(colors={'session.finished':{'fg':'#00ff00'},'session.alert':{'fg':'#ff0000'}})
        rows=[['$1','current','current','1','','{}'],['$2','finished','finished','2','','{}'],['$3','question','question','3','','{}']]
        result=module.render(rows,'$1',80,prefs,{'$2':'finished','$3':'regular'})
        self.assertIn('[2 finished]',topology.re.sub(r'#\[[^]]*\]','',result))
        self.assertIn('fg=#00ff00',result);self.assertIn('fg=#ff0000',result)
        for width in (1,3,13):
            result=module.render(rows,'$1',width,prefs,{'$2':'finished'})
            self.assertIn('fg=#00ff00',result)
            self.assertLessEqual(len(topology.re.sub(r'#\[[^]]*\]','',result)),width)
        result=module.render(rows,'$1',3,prefs,{'$2':'finished','$3':'regular'})
        self.assertIn('fg=#ff0000',result);self.assertNotIn('fg=#00ff00',result)


class Configuration(unittest.TestCase):
    setUp=native.ToastConfig.setUp
    cli=native.ToastConfig.cli

    def test_independent_settings_aliases_reset_undo_discovery_and_no_delivery(self):
        old=self.toast.read_bytes();profile=self.path.read_bytes()
        finished='apps.codex.alerts.finished.'
        regular='apps.codex.alerts.regular.'
        for frontend in (False,True):
            self.cli('set',finished+'toast.fg','#123456','--json',native=frontend)
            self.cli('set',finished+'vibrate.duration','17','--json',native=frontend)
            self.assertEqual(Native(self.root).values['toast']['fg'],'#abcdef' if frontend else 'warning')
            self.cli('set','apps.codex.toast.fg','#abcdef','--json',native=frontend)
            self.assertEqual(Native(self.root).resolve(regular+'toast.fg')['value'],'#abcdef')
            self.assertEqual(Native(self.root).resolve(finished+'toast.fg')['value'],'#123456')
        inventory=Inventory(self.root,self.platform)
        for key in KEYS:self.assertIsNotNone(inventory.find(key))
        for key in LEGACY_KEYS:self.assertIsNotNone(inventory.find(key))
        self.assertFalse(any(r.key in LEGACY_KEYS for r in inventory.rows))
        self.assertEqual({v for v,_ in value_candidates(self.root,finished+'toast.short')},{'true','false'})
        self.assertEqual({v for v,_ in value_candidates(self.root,finished+'vibrate.force')},{'true','false'})
        self.assertIn(finished+'toast.',{v for v,_ in key_candidates(self.root,finished)})
        self.assertIn(regular+'toast.fg',{v for v,_ in key_candidates(self.root,'apps.codex.toast.')})
        plan=NativePlan(self.root,self.selected);plan.edit(finished+'toast.fg',unset=True)
        tx=plan.apply('unset');self.assertEqual(Native(self.root).resolve(finished+'toast.fg')['value'],'bright_green')
        self.assertEqual(Native(self.root).resolve(regular+'toast.fg')['value'],'#abcdef')
        store=Store(state_root());operations,guards,catalogs=store.inverse(tx['id'])
        store.apply('undo',operations,guards,retain=True,catalogs=catalogs)
        self.assertEqual(Native(self.root).resolve(finished+'toast.fg')['value'],'#123456')
        self.assertEqual(profile,self.path.read_bytes());self.assertFalse((state_root()/'codex-alerts').exists())
        raw=json.loads(self.cli('list','apps','--json').stdout)
        self.assertEqual(raw['config']['apps']['codex']['toast'],raw['config']['apps']['codex']['alerts']['regular']['toast'])
        for width in (40,80,120):
            ui=Presentation(io.StringIO(),terminal=True);ui.width=width;listing(ui,raw)
            self.assertIn('finished',ui.stream.getvalue())

    def test_typed_delivery_exact_arguments_and_debug_type(self):
        from debug.alert import run
        import shutil
        shutil.copytree(native.profile_fixtures.ROOT/'config/tmux',self.toast.parent,dirs_exist_ok=True,ignore=shutil.ignore_patterns('codex-alerts.toml','__pycache__','*.pyc'))
        for kind,fg,duration in (('regular','#ff0000',10),('finished','#00ff00',20)):
            for key,value in {'toast.fg':fg,'toast.bg':'#010203','toast.short':True,'vibrate.duration':duration,'vibrate.count':1}.items():
                plan=NativePlan(self.root,self.selected);plan.edit('apps.codex.alerts.'+kind+'.'+key,value);plan.apply('set')
        calls=[]
        with patch.object(alerts,'HERE',self.toast.parent),patch.object(alerts.shutil,'which',side_effect=lambda name:name),patch.object(alerts,'bounded',side_effect=lambda cmd,timeout:calls.append(cmd)):
            prefs=alerts.preferences()
            for kind,fg,duration in (('regular','#ff0000',10),('finished','#00ff00',20)):
                alerts.notify_device('literal $(never)',prefs,kind=kind,wait=True)
                self.assertIn(['termux-toast','-b','#010203','-c',fg,'-g','middle','-s','--','literal $(never)'],calls)
                self.assertIn(['termux-vibrate','-d',str(duration),'-f'],calls)
        with patch.dict(os.environ,TERMUX_VERSION=''):
            result=run(self.root,'finished')
        self.assertEqual(result['alert_type'],'finished');self.assertEqual(result['settings']['toast']['fg'],'#00ff00')
        self.assertFalse((state_root()/'codex-alerts').exists())


if __name__=='__main__':unittest.main()

#!/usr/bin/env python3
"""Native toast Config bindings and exact notification argv in owned roots."""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_config_alignment as fixtures
import test_profile_config as profile_fixtures
from test_codex_alerts import alerts
from codex_toast import DEFAULTS, FIELDS, KEYS
from config_codex import Native, NativePlan
from config_menu import Inventory, Draft
from config_view import listing
from profile_config import context
from files.catalog import Presentation
from files.transactions import Store
from files.file_platform import state_root
from resources import cells


class ToastConfig(unittest.TestCase):
    def setUp(self):
        fixtures.Alignment.setUp(self)
        self.toast=self.root/'config/tmux/codex-alerts.toml'
        self.toast.parent.mkdir(parents=True)
        shutil.copy2(profile_fixtures.ROOT/'config/tmux/codex-alerts.toml',self.toast)
        import tomlkit
        import codex_vibration
        doc=tomlkit.parse(self.toast.read_text())
        doc['termux'].update({FIELDS[key]:value for key,value in DEFAULTS.items()})
        doc['termux'].update({codex_vibration.FIELDS[key]:value for key,value in codex_vibration.DEFAULTS.items()})
        self.toast.write_text(tomlkit.dumps(doc))
        self.selected=context(self.root)

    def cli(self,*args,**kwargs):
        return profile_fixtures.ProfileConfig.run_config(self,*args,**kwargs)

    def test_cli_both_frontends_and_exact_worker_argv(self):
        profile=self.path.read_bytes()
        for native in (False,True):
            for field,value in dict(fg='#123456',bg='#abcdef',position='top',short='true').items():
                result=json.loads(self.cli('set','apps.codex.toast.'+field,value,'--json',native=native).stdout)
                self.assertEqual(result['path'],str(self.toast))
                self.assertIn('five seconds',result['refresh']['reason'])
            self.assertEqual(self.cli('get','apps.codex.toast.short',native=native).stdout,'true\n')
            explanation=json.loads(self.cli('explain','apps.codex.toast.position','--json',native=native).stdout)
            self.assertEqual(explanation['constraints']['choices'],['top','middle','bottom'])
            self.assertEqual(explanation['source'],str(self.toast))
        self.assertEqual(profile,self.path.read_bytes())
        calls=[]
        with patch.object(alerts,'HERE',self.toast.parent),patch.dict(os.environ,TERMUX_VERSION='fixture'), \
                patch.object(alerts.shutil,'which',side_effect=lambda name:name), \
                patch.object(alerts,'bounded',side_effect=lambda cmd,timeout:calls.append(cmd)):
            prefs=alerts.preferences()
            alerts.notify_device('Literal $(never) -- message',prefs)
            self.assertIn(['termux-toast','-b','#abcdef','-c','#123456','-g','top','-s','--','Literal $(never) -- message'],calls)
            for position in ('middle','bottom'):
                prefs['termux'].update(toast_gravity=position,toast_short=False)
                alerts.notify_device('long',prefs)
                self.assertIn(['termux-toast','-b','#abcdef','-c','#123456','-g',position,'--','long'],calls)
            before=len(calls)
            with patch.dict(os.environ,TERMUX_VERSION=''): alerts.notify_device('disabled',prefs)
            self.assertEqual(before,len(calls))

    def test_guarded_toml_reset_noop_invalid_and_undo(self):
        original=self.toast.read_bytes()
        plan=NativePlan(self.root,self.selected)
        plan.edit(KEYS[0],'#abcdef')
        self.assertEqual(original,self.toast.read_bytes())
        result=plan.apply('set')
        self.assertIn('# User preferences:',self.toast.read_text())
        self.assertIn('focus_policy = "conservative"',self.toast.read_text())
        again=NativePlan(self.root,self.selected);again.edit(KEYS[0],'#abcdef')
        self.assertEqual(again.apply('set')['status'],'unchanged')
        store=Store(state_root());operations,guards,catalogs=store.inverse(result['id'])
        store.apply('undo',operations,guards,retain=True,catalogs=catalogs)
        self.assertEqual(original,self.toast.read_bytes())
        for key,value in ((KEYS[0],'$(touch NEVER)'),(KEYS[0],'colors.does_not_exist.fg'),(KEYS[2],'center'),(KEYS[3],'yes'),(KEYS[3],1)):
            with self.assertRaises(ValueError): NativePlan(self.root,self.selected).edit(key,value)
        self.assertEqual(original,self.toast.read_bytes())
        stale=NativePlan(self.root,self.selected);stale.edit(KEYS[3],True)
        self.toast.write_text(self.toast.read_text()+'# concurrent edit\n')
        with self.assertRaises((ValueError,OSError)): stale.apply('set')
        reset=NativePlan(self.root,self.selected);reset.edit(KEYS[3],unset=True);reset.apply('unset')
        with patch.object(alerts,'HERE',self.toast.parent):
            self.assertFalse(alerts.preferences()['termux']['toast_short'])
        self.assertEqual(Native(self.root).resolve(KEYS[3])['source'],str(self.root/'lib/dots/codex_toast.py'))
        self.assertIn('# concurrent edit',self.toast.read_text())

    def test_popup_toast_keys_colors_scope_and_widths(self):
        inventory=Inventory(self.root,self.platform)
        rows={row.key:row for row in inventory.rows if row.key.startswith('apps.codex.toast.')}
        self.assertEqual(set(rows),set(KEYS))
        draft=Draft(inventory,rows[KEYS[3]]).prepare('true')
        self.assertTrue(draft.proposed);self.assertIn('five seconds',draft.review())
        self.assertEqual(Native(self.root).values['toast'],DEFAULTS)
        self.assertFalse(any(r.key.startswith('apps.codex.') for r in Inventory(self.root,'defaults').rows))
        other='windows' if self.platform!='windows' else 'linux'
        with self.assertRaises(ValueError): Native(self.root,context(self.root,other))
        raw=json.loads(self.cli('list','apps','--json').stdout)
        self.assertEqual(raw['config']['apps']['codex']['toast'],DEFAULTS)
        self.assertNotIn('codex',json.loads(self.cli('list','apps','--defaults','--json').stdout)['config']['apps'])
        palette=self.home/'state/dots/current/theme/palette.json'
        palette.parent.mkdir(parents=True)
        palette.write_text(json.dumps({'colors':{'warning':'#123456','dark_background':'#abcdef','blue':'#345678'},'palette':{'custom':'#567890'}}))
        with patch.object(alerts,'HERE',self.toast.parent):
            prefs=alerts.preferences();self.assertEqual(alerts.colors(prefs),('#abcdef','#123456'))
            prefs['termux']['toast_foreground']='palette.custom'
            self.assertEqual(alerts.colors(prefs)[1],'#567890')
            prefs['termux']['toast_foreground']='colors.ui.label.fg'
            self.assertEqual(alerts.colors(prefs)[1], '#345678')
            prefs['termux']['toast_foreground']='colors.missing.fg'
            self.assertEqual(alerts.colors(prefs)[1], '#ffff00')
        for width in (40,80,120):
            for colored in (False,True):
                ui=Presentation(io.StringIO(),terminal=True);ui.width=width;ui.color=colored
                listing(ui,raw)
                text=re.sub(r'\x1b\[[0-9;]*m','',ui.stream.getvalue())
                self.assertIn('codex-alerts.toml',text)
                self.assertTrue(all(cells(line)<=width for line in text.splitlines()))
        with patch('config_refresh.effective',side_effect=AssertionError('native save does not activate consumers')):
            draft.save()
        self.assertTrue(Native(self.root).values['toast']['short'])

    def test_completion_choices_and_native_literal_colors(self):
        for key,expected in ((KEYS[2],{'top','middle','bottom'}),(KEYS[3],{'true','false'}),(KEYS[0],{'warning','dark_background','colors.ui.label.fg'})):
            for shell in ('bash','zsh','fish','native'):
                words=['config','set',key,'']
                cmd=([sys.executable,'-B',str(self.root/'lib/dots/cli.py'),'__complete',*words] if shell=='native' else
                     [str(self.root/'bin/dots'),'__complete',shell,str(len(words)),'--','dots',*words])
                p=subprocess.run(cmd,env=self.env,text=True,capture_output=True,timeout=30)
                self.assertEqual(p.returncode,0,p.stderr)
                values={line.split('\t')[1] for line in p.stdout.splitlines()}
                self.assertTrue(expected<=values,(key,values))
                self.assertNotIn('default',values)
        self.cli('set',KEYS[2],'middle','--dry-run','--json')
        self.cli('get','apps.codex.toast.unknown','--json',code=1)
        self.cli('get',KEYS[0],'--defaults','--json',code=1)

    def test_background_opacity_flags_bounds_reset_and_completion(self):
        from codex_toast import background
        key='apps.codex.toast.bg_opacity'
        for value in (-1,101,True,50.5,'50%'):
            with self.assertRaises(ValueError):NativePlan(self.root,self.selected).edit(key,value)
        self.assertEqual(background('#123456',0),'#00123456')
        self.assertEqual(background('#123456',50),'#80123456')
        self.assertEqual(background('#123456',100),'#123456')
        for native in (False,True):
            self.cli('set','apps.codex.toast.bg','#123456','--json',native=native)
            self.cli('set',key,'50','--json',native=native)
            self.assertEqual(self.cli('get',key,native=native).stdout,'50\n')
            calls=[]
            with patch.object(alerts,'HERE',self.toast.parent),patch.dict(os.environ,TERMUX_VERSION='fixture'), \
                    patch.object(alerts.shutil,'which',side_effect=lambda name:name), \
                    patch.object(alerts,'bounded',side_effect=lambda command,timeout:calls.append(command)):
                alerts.notify_device('Opacity test',alerts.preferences())
            toast=next(command for command in calls if command[0]=='termux-toast')
            self.assertEqual(toast[toast.index('-b')+1],'#80123456')
        from config_completion import value_candidates
        self.assertEqual({value for value,label in value_candidates(self.root,key)}, {'0','25','50','75','100'})
        self.cli('unset',key,'--json')
        with patch.object(alerts,'HERE',self.toast.parent):
            self.assertEqual(alerts.colors(alerts.preferences())[0],'#123456')


if __name__=='__main__':unittest.main()

#!/usr/bin/env python3
"""Canonical keys, migration and interactive data in disposable roots."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch
import test_profile_config as fixtures
from profile_config import context
from config_cli import ControlPlan,StylePlan
from config_values import Controls
from config_keys import canonical,document
from config_migration import KeyPlan
from config_completion import branches,key_candidates,value_candidates
from style_config import Styles
from files.transactions import Store


class Discovery(unittest.TestCase):
    setUpFixture=fixtures.ProfileConfig.setUp
    run_config=fixtures.ProfileConfig.run_config

    def setUp(self):
        self.setUpFixture()
        shutil.copytree(fixtures.ROOT/'default',self.root/'default')
        shutil.copytree(fixtures.ROOT/'config/tmux',self.root/'config/tmux')
        self.environment=patch.dict(os.environ,self.env,clear=True)
        self.environment.start();self.addCleanup(self.environment.stop)
        from config_values import current as controls
        from style_config import current as styles
        controls.cache_clear();styles.cache_clear()
        self.addCleanup(controls.cache_clear);self.addCleanup(styles.cache_clear)

    def test_canonical_control_and_style_roundtrip(self):
        selected=context(self.root)
        plan=ControlPlan(self.root,selected)
        plan.edit('formatting.apps.menu.popup.width','75%');plan.apply('set')
        saved=json.loads(self.path.read_text())
        self.assertEqual(saved['formatting']['apps']['menu']['popup']['width'],'75%')
        self.assertEqual(Controls(self.root).resolve('apps.menu.popup.width')['value'],'75%')
        plan=StylePlan(self.root,context(self.root),'colors')
        plan.edit('apps.cli.todo.field.alias.value.fg','#112233');plan.apply('set')
        raw=(self.path.parent/'colors.toml').read_text()
        self.assertIn('[apps.todo.field.alias.value]',raw)
        self.assertEqual(Styles(self.root).style('todo.field.alias.value',app='cli')['fg'],'#112233')

    def test_migration_comments_values_idempotence_and_undo(self):
        path=self.path.parent/'colors.toml'
        original='# retained comment\n[todo.status.done] # state\nfg = "green" # field\nbold = false\n'
        path.write_text(original)
        data=json.loads(self.path.read_text());data['apps']={'menu':{'popup':{'width':'75%','colors':{'border':'accent'}}}}
        self.path.write_text(json.dumps(data));before=self.path.read_bytes()
        expected=Styles(self.root).style('todo.status.done',app='cli')
        plan=KeyPlan(self.root,context(self.root));result=plan.apply()
        self.assertEqual(Styles(self.root).style('todo.status.done',app='cli'),expected)
        self.assertEqual(Controls(self.root).resolve('apps.menu.popup.width')['value'],'75%')
        for comment in ('retained comment','# state','# field'):self.assertIn(comment,path.read_text())
        self.assertEqual(KeyPlan(self.root,context(self.root)).operations,[])
        store=Store(Path(self.env['XDG_STATE_HOME'])/'dots')
        operations,guards,catalogs=store.inverse(result['id']);store.apply('undo',operations,guards,retain=True,catalogs=catalogs)
        self.assertEqual(path.read_text(),original);self.assertEqual(self.path.read_bytes(),before)

    def test_migration_conflicts_and_stale_input(self):
        path=self.path.parent/'colors.toml'
        path.write_text('[todo.status.done]\nfg="green"\n[apps.todo.status.done]\nfg="red"\n')
        with self.assertRaisesRegex(ValueError,'conflicting'):KeyPlan(self.root,context(self.root))
        path.write_text('[todo.status.done]\nfg="green"\n')
        plan=KeyPlan(self.root,context(self.root));path.write_text('[todo.status.done]\nfg="blue"\n')
        with self.assertRaises(Exception):plan.apply()
        self.assertIn('blue',path.read_text())

    def test_interrupted_key_migration_rolls_back_completed_replacements(self):
        import files.transactions as transactions
        path=self.path.parent/'colors.toml';path.write_text('[todo.status.done]\nfg="green"\n')
        data=json.loads(self.path.read_text());data['apps']={'menu':{'popup':{'width':'75%'}}};self.path.write_text(json.dumps(data))
        before={p:p.read_bytes() for p in (self.path,path)}
        plan=KeyPlan(self.root,context(self.root));rename=transactions.os.rename;interrupted=False
        def interrupt_once(left,right):
            nonlocal interrupted
            if Path(left)==path and not interrupted:
                interrupted=True;raise KeyboardInterrupt('fixture interruption')
            return rename(left,right)
        with patch.object(transactions.os,'rename',side_effect=interrupt_once),self.assertRaises(KeyboardInterrupt):plan.apply()
        self.assertTrue(interrupted)
        self.assertEqual({p:p.read_bytes() for p in before},before)
        self.assertEqual(len(KeyPlan(self.root,context(self.root)).operations),2)

    def test_references_fallback_cycles_and_layer_precedence(self):
        path=self.path.parent/'colors.toml'
        path.write_text('[ui.heading]\nfg="palette.rosewater"\n[apps.todo.field.alias.value]\nfg="colors.daylight.day.fg"\n')
        style=Styles(self.root,palette={'rosewater':'#ffeedd','yellow':'#ffee00'})
        self.assertEqual(style.color('palette.rosewater'),'#ffeedd')
        self.assertEqual(style.color(style.style('todo.field.alias.value',app='cli')['fg']),'#ffee00')
        missing=Styles(self.root,palette={'cyan':'#00ffff'})
        self.assertNotEqual(missing.style('ui.heading',app='cli')['fg'],'palette.rosewater')
        path.write_text('[daylight.day]\nfg="colors.daylight.night.fg"\n[daylight.night]\nfg="colors.daylight.day.fg"\n')
        with self.assertRaisesRegex(ValueError,'cycle'):Styles(self.root)
        path.write_text('[ui.heading]\nfg="colors.missing.fg"\n')
        with self.assertRaisesRegex(ValueError,'unknown global'):Styles(self.root)

    def test_branches_literals_and_typed_values(self):
        keys=['apps.nvim.highlights["@variable.member"].fg','apps.nvim.highlights["@variable.member"].bold','colors.ui.heading.fg']
        self.assertEqual(branches(keys,''),[('apps.',True),('colors.',True)])
        self.assertEqual(branches(keys,'apps.nvim.highlights['),[('apps.nvim.highlights["@variable.member"].',True)])
        root={v for v,_ in key_candidates(self.root,'..')}
        self.assertTrue({'apps.','colors.','icons.','formatting.'}<=root)
        self.assertFalse(any(v.startswith('colors.apps.') for v in root))
        self.assertIn(('true',''),value_candidates(self.root,'apps.tmux.session.multiple'))
        self.assertTrue(any(k=='colors.daylight.day.fg' for k,_ in value_candidates(self.root,'colors.apps.todo.field.alias.value.fg')))

    def test_browser_branch_and_canonical_editor(self):
        from config_menu import Inventory,Draft,tree_rows
        inventory=Inventory(self.root,self.platform,no_refresh=True)
        rows=tree_rows(inventory,'colors.apps.todo.field.alias.value')
        self.assertTrue(any(r.key.endswith('.fg') and r.kind=='color' for r in rows))
        row=inventory.find('colors.apps.menu.popup.border.fg')
        self.assertIsNotNone(row)
        draft=Draft(inventory,row).prepare('accent')
        self.assertIsInstance(draft.plan,ControlPlan)
        self.assertEqual(draft.proposed,'accent')

    def test_tmux_compiler_literal_controls(self):
        from tmux_controls import compile_options
        data=json.loads(self.path.read_text());data['apps']={'tmux':{'indicators':{'prefix':{'text':'#(touch /tmp/escape)'}}}}
        self.path.write_text(json.dumps(data))
        source=(self.root/'config/tmux/tmux.conf').read_text()
        options=compile_options(self.root,context(self.root),source)
        self.assertIn('##(touch /tmp/escape)',options.values())
        self.assertNotIn('session-status.py',options['status-left'])
        self.assertIn('@dots-config-clock',options)
        self.assertIn('@dots-marker-working',options)

    @unittest.skipUnless(shutil.which('tmux'),'tmux unavailable')
    def test_generated_tmux_literals_styles_and_clock(self):
        from tmux_controls import fragment
        socket=str(self.home/'component.sock')
        def tmux(*args):
            result=subprocess.run(['tmux','-S',socket,*args],env=self.env,capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr)
            return result.stdout.strip()
        tmux('-f','/dev/null','new-session','-d','-s','fixture','sleep 60')
        self.addCleanup(lambda:subprocess.run(['tmux','-S',socket,'kill-server'],env=self.env,capture_output=True))
        value='P,}#(touch '+str(self.home/'escaped')+')#{session_name}'
        data=json.loads(self.path.read_text())
        data['apps']={'tmux':{'indicators':{'zoom':{'text':value}},'clock':{'icon_mode':'fixed'}}}
        data['formatting']={'apps':{'tmux':{'clock':{'format':'%H:%M'},'indicators':{'zoom':{'before':'<','after':'>','spacer':'!'}}}}}
        self.path.write_text(json.dumps(data))
        (self.path.parent/'colors.toml').write_text('[apps.tmux.indicators.zoom]\nfg="#112233"\n[apps.tmux.indicators.zoom.surround]\nfg="#445566"\n[apps.tmux.git]\nbg="#123456"\n')
        source=(self.root/'config/tmux/tmux.conf').read_text()
        generated=self.home/'components.conf';generated.write_text(fragment(self.root,context(self.root),source))
        tmux('source-file',str(generated))
        tmux('split-window','-d','sleep 60');tmux('resize-pane','-Z')
        text=tmux('display-message','-p','#{E:status-right}')
        self.assertIn('#[fg=#112233]',text)
        self.assertIn('#[fg=#445566]',text)
        self.assertIn('P,}##(touch',text)
        self.assertIn('##{session_name}',text)
        self.assertFalse((self.home/'escaped').exists())
        clock=tmux('display-message','-p','#{E:@dots-config-clock}')
        self.assertRegex(clock,r'\d{2}:\d{2}')
        tmux('set-option','-g','@dots-gitmux','BRANCH')
        tmux('set-option','-g','@dots-gitmux-width','48')
        git=tmux('display-message','-p','#{E:@dots-gitmux-segment}')
        self.assertIn('#[bg=#123456]#[push-default]',git)
        self.assertIn('BRANCH',git)

    def test_multisession_widths_and_battery_spans(self):
        import importlib.util
        sys.path.insert(0,str(self.root/'config/tmux'));self.addCleanup(sys.path.remove,str(self.root/'config/tmux'))
        def module(name):
            spec=importlib.util.spec_from_file_location(name,self.root/'config/tmux'/(name+'.py'))
            mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
        sessions=module('session-status');battery=module('battery-status');tabs=module('termux-status')
        from status_styles import cells,literal
        self.assertEqual(cells(literal('#[bold]')),7)
        rows=[('$'+str(i),'session-'+str(i),'project-'+str(i),str(i),'',json.dumps({'projects':[],'repository':{}})) for i in range(1,12)]
        for width in (1,6,40,80,120):
            out=sessions.render(rows,'$7',width,{'options':{'session':{}}})
            self.assertLessEqual(cells(out),width)
            self.assertIn('7' if width>1 else '$',out)
        prefs={'colors':{'battery.low':{'fg':'#112233'},'battery.low.icon':{'fg':'#445566'},'battery.low.text':{'fg':'#778899'}},'icons':{'battery.low':'L'}}
        text=battery.render('\x1b[33mX 20%\x1b[0m',('red','yellow','green','brightblack'),True,prefs)
        self.assertIn('#[fg=#445566]L',text);self.assertIn('#[fg=#778899]20%',text)
        snapshot=dict(count=12,sessions=[dict(pid=i,tty='pts/'+str(i)) for i in range(1,13)])
        prefs={'formatting':{'tabs':{'separator':' | ','before':'#[','after':']'}}}
        for width in (6,12,40,80,120):
            for orphan in (0,1):
                text=tabs.render_attention_tabs(snapshot,'pts/7',('black','white','blue','white'),width,'white','black',{},orphan,'red','black',prefs)
                self.assertLessEqual(cells(text),width)
        tool=self.home/'repos/battery/battery';tool.parent.mkdir(parents=True);tool.write_text('fixture')
        prefs={'options':{'battery':{'critical':10,'low':25,'charging_style':True}},'icons':{'battery.charging':'C'}}
        with patch.object(battery,'preferences',return_value=prefs),patch.object(battery.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'\x1b[32mX 80%\x1b[0m CHARGING','')) as run:
            text=battery.main(['--slot','red','yellow','green','brightblack'])
            self.assertIn('C 80%',text)
            self.assertEqual(run.call_args.args[0][-4:],['--critical','10','--low','25'])
        self.assertIn('?%',battery.render('',('red','yellow','green','brightblack'),True,{}))

    def test_weather_shared_colors_preserve_explicit_native_overrides(self):
        from wttr.styling import detail_color
        (self.path.parent/'colors.toml').write_text('[daylight.sunrise]\nfg="#123456"\n')
        prefs=Styles(self.root)
        with patch('style_config.current',return_value=prefs):
            self.assertEqual(detail_color('sunrise',{'icon_colors':{}}),'#123456')
            self.assertEqual(detail_color('sunrise',{'icon_colors':{'sunrise':'yellow'}}),'yellow')


if __name__=='__main__':unittest.main()

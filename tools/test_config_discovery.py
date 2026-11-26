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

    def test_custom_map_roots_and_empty_icon_aliases(self):
        from config_values import DYNAMIC, constraints, name, read_defaults
        from config_menu import Inventory
        defaults = read_defaults(self.root)
        for path in DYNAMIC:
            self.assertEqual(constraints(defaults, name(path))['type'], 'object', path)

        aliases = ('apps.nvim.icons', 'nvim.icons', 'icons.nvim', 'icons.apps.nvim')
        inventory = Inventory(self.root, self.platform)
        for key in aliases:
            self.assertEqual(inventory.find(key).value, {}, key)
            info = json.loads(self.run_config('explain', key, '--json').stdout)
            self.assertEqual(info['value'], {}, key)
            self.assertEqual(info['constraints']['type'], 'object', key)
        self.assertIn('nvim.icons', dict(key_candidates(self.root, 'nvim.ico', self.platform)))
        self.assertEqual(json.loads(self.run_config('get', 'icons.nvim', '--json', native=True).stdout)['value'], {})
        bindings = json.loads(self.run_config('explain', 'fzf.settings.bindings', '--json', native=True).stdout)
        self.assertEqual(bindings['constraints']['type'], 'object')
        self.assertEqual(bindings['value']['ctrl-x'], 'toggle-preview')
        self.assertEqual(constraints(defaults, 'apps.fzf.bindings.ctrl-x')['type'], 'string')
        child = 'nvim.icons["diagnostics.Error"]'
        self.run_config('set', child, '!', '--no-refresh', native=True)
        self.assertEqual(json.loads(self.run_config('get', 'icons.nvim', '--json').stdout)['value'],
                         {'diagnostics.Error': '!'})
        self.run_config('unset', child, '--no-refresh')
        self.assertEqual(json.loads(self.run_config('get', 'icons.nvim', '--json').stdout)['value'], {})
        self.assertEqual(constraints(defaults, 'apps.' + child)['type'], 'string')
        self.run_config('get', 'nvim.unrecognized', code=1)

    def test_scalar_get_loads_only_its_owners(self):
        import io
        from contextlib import ExitStack, redirect_stdout
        from config_cli import main
        with ExitStack() as stack:
            for item in ('profile_config.keys', 'profile_config.file_rows', 'style_catalog.known_keys',
                         'config_wttr.Native', 'config_pkgs.Native', 'config_codex.Native'):
                stack.enter_context(patch(item, side_effect=AssertionError('unrelated owner ' + item)))
            for key in ('colors.fzf.ui.cursor.fg', 'icons.git.branch', 'settings.fzf.preview_window',
                        'formatting.cli.label_gap', 'DOTS_COLOR', 'profile.alias'):
                with self.subTest(key=key), redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(main(['get', key, '--profile', self.platform, '--json']), 0)
                    self.assertIn('value', json.loads(output.getvalue()))

    def test_application_and_type_views_keep_one_owner(self):
        for native in (False, True):
            def read(key):
                return json.loads(self.run_config('get', key, '--json', native=native).stdout)['value']
            self.assertEqual(read('fzf'), read('apps.fzf'))
            values = [read(key) for key in ('apps.fzf.colors', 'fzf.colors', 'colors.fzf')]
            self.assertEqual(values[0], values[1])
            self.assertEqual(values[1], values[2])
            human = self.run_config('get','fzf.colors',native=native).stdout
            self.assertIn('cursor', human)
            self.assertIn('fg+', values[0])
            self.assertIn('fg', values[0]['ui']['cursor'])
            for spelling in ('fzf.colors["fg+"]', 'colors.fzf["fg+"]', 'colors.apps.fzf["fg+"]'):
                self.run_config('set', spelling, 'red:bold', '--no-refresh', native=native)
                self.assertEqual(read('apps.fzf.colors["fg+"]'), 'red:bold')
                self.run_config('unset', spelling, '--no-refresh', native=native)
            for spelling in ('fzf.settings.preview_window', 'settings.fzf.preview_window'):
                self.assertEqual(read(spelling), read('apps.fzf.preview_window'))
            self.assertEqual(read('files'), {})
            self.assertEqual(read('apps.files.list_view'), 'short')

    def test_group_edits_use_one_owner_and_reject_cross_owner_writes(self):
        colors = self.path.with_name('config.json')
        for key in ('apps.fzf.colors', 'fzf.colors', 'colors.fzf'):
            change = self.run_config('set', key, '{"border":"red","fg+":"bold:white"}',
                                     '--json-value','--no-refresh','--json')
            self.assertEqual(json.loads(change.stdout)['path'], str(colors))
            original = colors.read_bytes()
            bad = self.run_config('set', key, '{"border":"blue","ui":{"cursor":{"fg":"blue"}}}',
                                  '--json-value','--no-refresh',code=1)
            self.assertIn('edit each field individually', bad.stderr)
            self.assertEqual(colors.read_bytes(), original)
            self.run_config('unset', key, '--no-refresh')
        result = self.run_config('set','settings.fzf.preview_window','down:30%','--dry-run','--json')
        self.assertEqual(json.loads(result.stdout)['items'][0]['key'],'apps.fzf.preview_window')
        result = self.run_config('explain','fzf.colors["fg+"]','--json')
        self.assertEqual(json.loads(result.stdout)['key'],'apps.fzf.colors["fg+"]')

    def test_application_env_file_and_browser_views(self):
        data=json.loads(self.path.read_text())
        data['environment']={'FZF_OPTION':'fixture','FZF_API_KEY':'${SECRET_KEY}','TEAM_PRIVATE_TOKEN':'${SECRET_KEY}'}
        data['files']={'dots':[dict(self.resource)]}
        self.path.write_text(json.dumps(data))
        def read(key):
            return json.loads(self.run_config('get',key,'--json').stdout)['value']
        self.assertEqual(read('apps.fzf.env'),read('env.fzf'))
        self.assertEqual(read('fzf.env.FZF_API_KEY'),'[redacted]')
        self.assertEqual(read('env.TEAM_PRIVATE_TOKEN'),'[redacted]')
        self.run_config('get','apps.team.env','--json',code=1)
        hidden = self.run_config('get','fzf.env.FZF_DEFAULT_OPTS','--json',
                                 FZF_DEFAULT_OPTS='private sentinel',DOTS_ENV_HOOKS='FZF_DEFAULT_OPTS:local:1:set')
        self.assertEqual(json.loads(hidden.stdout)['value'],'[redacted]')
        self.assertNotIn('private sentinel',hidden.stdout + hidden.stderr)
        self.run_config('set','env.fzf.FZF_OPTION','saved')
        self.assertEqual(read('environment.FZF_OPTION'),'saved')
        self.assertEqual(read('app.files'),[self.resource])
        self.assertEqual(read('files.app'),read('apps.app.files'))
        self.assertEqual(read('app.files["dots:app"]'), self.resource)
        self.run_config('unset','apps.app.files',code=1)
        inventory=__import__('config_menu').Inventory(self.root,self.platform)
        self.assertEqual(inventory.find('fzf.settings.preview_window').key, 'apps.fzf.preview_window')
        app_rows=__import__('config_menu').tree_rows(inventory,'apps.fzf.colors')
        self.assertTrue(any(row.key=='apps.fzf.colors.ui.cursor' for row in app_rows))
        self.assertTrue(any(key.startswith('colors.fzf.') for key,_ in key_candidates(self.root,'colors.fzf.')))
        self.assertIn('fzf.settings.preview_window',dict(key_candidates(self.root,'fzf.settings.preview_w')))
        self.assertEqual(list(dict(key_candidates(self.root,'fzf.colors.bord'))), ['fzf.colors.border'])
        self.assertEqual(list(dict(key_candidates(self.root,'colors.fzf.bord'))), ['colors.fzf.border'])

    def test_canonical_control_and_style_roundtrip(self):
        selected=context(self.root)
        plan=ControlPlan(self.root,selected)
        plan.edit('formatting.apps.menu.popup.width','75%');plan.apply('set')
        saved=json.loads(self.path.with_name('config.json').read_text())
        self.assertEqual(saved['apps']['menu']['formatting']['popup']['width'],'75%')
        self.assertEqual(Controls(self.root).resolve('apps.menu.popup.width')['value'],'75%')
        plan=StylePlan(self.root,context(self.root),'colors')
        plan.edit('apps.cli.todo.field.alias.value.fg','#112233');plan.apply('set')
        raw=json.loads(self.path.with_name('config.json').read_bytes())
        self.assertEqual(raw['apps']['todo']['colors']['field']['alias']['value']['fg'],'#112233')
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

    def test_open_indicator_browser_and_completion_controls(self):
        from config_menu import Inventory,Draft
        inventory=Inventory(self.root,self.platform,no_refresh=True)
        for key in ('icons.apps.tmux.status.open','icons.apps.tmux.status.working',
                    'icons.apps.tmux.status.waiting','colors.apps.tmux.indicators.open.fg',
                    'colors.apps.tmux.indicators.open.bg','colors.apps.tmux.indicators.open.bold',
                    'apps.tmux.indicators.open.text','formatting.apps.tmux.indicators.open.before',
                    'formatting.apps.tmux.indicators.open.after','formatting.apps.tmux.indicators.open.spacer'):
            with self.subTest(key=key):
                self.assertIsNotNone(inventory.find(key))
                self.assertIn(key,{k for k,_ in key_candidates(self.root,key.rsplit('.',1)[0]+'.')})
        draft=Draft(inventory,inventory.find('colors.apps.tmux.indicators.open.fg')).prepare('accent')
        self.assertEqual(draft.proposed,'accent')
        self.assertEqual(Controls(self.root).resolve('apps.tmux.indicators.open.text')['value'],None)

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
        data['apps']={'tmux':{'indicators':{'zoom':{'text':value}},'clock':{'icon_mode':'fixed'},
                              'session':{'repository_icon':False}}}
        data['formatting']={'apps':{'tmux':{'clock':{'format':'%H:%M'},'indicators':{'zoom':{'before':'<','after':'>','spacer':'!'}}}}}
        self.path.write_text(json.dumps(data))
        (self.path.parent/'colors.toml').write_text('[apps.tmux.indicators.zoom]\nfg="#112233"\n[apps.tmux.indicators.zoom.surround]\nfg="#445566"\n[apps.tmux.git]\nbg="#123456"\n')
        (self.path.parent/'icons.toml').write_text('[apps.tmux.session]\ndefault="BADGE"\n')
        source=(self.root/'config/tmux/tmux.conf').read_text()
        generated=self.home/'components.conf';generated.write_text(fragment(self.root,context(self.root),source))
        tmux('source-file',str(generated))
        self.assertEqual(tmux('display-message','-p','#{E:@dots-session-icon}'),'BADGE')
        self.assertEqual(tmux('show-option','-gqv','@dots-remote-icon'),'')
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
        metadata={'auto':True,'projects':['/a','/b'],'repository':{'host':'github'}}
        multi=('$0','multi-123','multi','7','',json.dumps(metadata))
        single=('$1','multi-456','multi','','',json.dumps(dict(metadata,projects=['/multi'])))
        prefs={'options':{'session':{}},'icons':{'hosts.github':'HOST'}}
        self.assertEqual(sessions.render([multi,single],'$0',120,prefs),'')
        self.assertNotIn('HOST',sessions.render([multi,single],'$1',120,prefs))
        prefs['icons']['session.default']='BADGE'
        self.assertIn('BADGE',sessions.render([multi,single],'$1',120,prefs))
        self.assertNotIn('multi-123',sessions.render([multi,single],'$1',120,prefs))
        unknown=('$2','manual','manual','','',json.dumps({'repository':{'host':'github'}}))
        self.assertNotIn('HOST',sessions.render([unknown],'$2',120,prefs))
        self.assertIn('manual',sessions.render([unknown],'$2',120,prefs))
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
        with patch.object(battery,'command',return_value='\x1b[32mX 80%\x1b[0m CHARGING') as run:
            output=battery.acquire(prefs['options']['battery'])
            text=battery.render(output,('red','yellow','green','brightblack'),True,prefs)
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

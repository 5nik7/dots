#!/usr/bin/env python3
"""Fonts display/configuration contracts in test-owned homes and checkouts."""
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_profile_config as fixtures
from config_values import current as controls, constraints, read_defaults, validate_value, parts
from style_config import current as styles
from fonts_cli import render, emit
from fonts.commands import COMMANDS, parser
from resources import cells

ANSI=re.compile(r'\x1b\[[0-9;]*m')
ROW=dict(id='local:fixture',name='Fixture ü',provider='local',versions={
    'v1':dict(fonts=[dict(file='-Fixture.ttf',family='Fixture ü',variant='mono')],provenance={'origin':'local fixture'})})


class FontsPresentation(unittest.TestCase):
    def setUp(self):
        fixtures.ProfileConfig.setUp(self)
        shutil.copytree(fixtures.ROOT/'default',self.root/'default')
        for adapter in fixtures.ROOT.glob('bin/dots-fonts*'):shutil.copy2(adapter,self.root/'bin'/adapter.name)
        self.env.update(TERM='xterm-256color',COLUMNS='80')
        self.environment=patch.dict(os.environ,self.env,clear=True)
        self.environment.start();self.addCleanup(self.environment.stop)
        self.clear();self.addCleanup(self.clear)

    def clear(self):controls.cache_clear();styles.cache_clear()

    def configure(self, **groups):
        doc=json.loads(self.path.read_text());doc.update(groups)
        self.path.write_text(json.dumps(doc));self.clear()

    def cli(self,*args,**kwargs):return fixtures.ProfileConfig.run_config(self,*args,**kwargs)

    def report(self,data=None,**kwargs):
        out=io.StringIO();render(data or dict(items=[ROW]),out,**kwargs);return out.getvalue()

    def test_human_summary_full_provenance_and_width(self):
        self.configure(formatting=dict(apps=dict(cli=dict(indent=2,label_width='25%',label_gap=2,alignment='right'))))
        for width in (40,80,120):
            text=self.report(human=True,width=width,action='list')
            self.assertIn('Matches',text);self.assertIn('Faces',text)
            self.assertNotIn('-Fixture.ttf',text)
            self.assertTrue(all(cells(line)<=width for line in text.splitlines()),text)
            self.assertIn('-Fixture.ttf',self.report(human=True,width=width,action='show'))
        self.configure(apps=dict(fonts=dict(list_details='full',provenance=False)))
        text=self.report(human=True,action='list')
        self.assertIn('-Fixture.ttf',text);self.assertNotIn('Provenance',text)

    def test_redirected_and_json_are_exact_despite_preferences(self):
        self.configure(apps=dict(fonts=dict(list_details='summary',provenance=False)),
                       formatting=dict(apps=dict(cli=dict(indent=15,label_width='50%'))))
        doc=dict(schema=1,items=[dict(id='local:test',version='v1',status='stored')])
        self.assertEqual(self.report(doc),'Fonts\n    ID         local:test\n    Version    v1\n    Status     stored\n')
        self.assertIn('Provenance',self.report())
        with patch.dict(os.environ,DOTS_MENU_CAPTURE='1'):
            capture=self.report(action='list')
            self.assertIn('Faces',capture);self.assertNotIn('Provenance',capture)
        out=io.StringIO()
        with patch.dict(os.environ,DOTS_COLOR='always',DOTS_ICONS='always'),redirect_stdout(out):
            emit(doc,parser().parse_args(['list','--json']))
        self.assertEqual(out.getvalue(),json.dumps(doc,ensure_ascii=True)+'\n')

    def test_font_styles_icons_sanitization_and_independent_color_modes(self):
        (self.path.parent/'colors.toml').write_text('[fonts.identity]\nfg="#123456"\nbg="#654321"\nbold=true\n[fonts.label]\nunderline=true\n')
        (self.path.parent/'icons.toml').write_text('[menu]\nfonts="F"\n')
        self.clear()
        with patch.dict(os.environ,DOTS_COLOR='always',DOTS_ICONS='never'):
            text=self.report(dict(items=[dict(id='$(touch NO)\x1b[2J')]),human=True)
            self.assertIn('38;2;18;52;86',text);self.assertIn('48;2;101;67;33',text)
            self.assertNotIn('\x1b[2J',text);self.assertFalse(ANSI.sub('',text).startswith('F Fonts'))
        with patch.dict(os.environ,DOTS_COLOR='never',DOTS_ICONS='always'):
            text=self.report(human=True);self.assertTrue(text.startswith('F Fonts'));self.assertNotIn('\x1b',text)
        with patch.dict(os.environ,DOTS_COLOR='auto',DOTS_ICONS='never',NO_COLOR='1'):
            self.assertNotIn('\x1b',self.report(human=True))
        from style_catalog import supported,known_keys
        self.assertTrue(supported('colors','apps.cli.fonts.identity.bg'))
        self.assertIn('fonts.identity.italic',known_keys('colors',styles()))

    def test_config_discovery_validation_reset_and_runtime_activation(self):
        from config_menu import Inventory,Draft
        from config_refresh import effective,after_save,preview_save
        key='apps.fonts.preview.position'
        row=Inventory(self.root,self.platform).find(key)
        self.assertEqual(row.constraints['choices'],['down','right'])
        before=effective(self.root)
        draft=Draft(Inventory(self.root,self.platform),row).prepare('right')
        self.assertIn('fonts',preview_save(self.root,draft.plan)['consumers'])
        draft.plan.apply('set')
        with patch('config_refresh.refresh',side_effect=AssertionError('display setting must not publish a theme')):
            self.assertEqual(after_save(self.root,before)['consumers'],[dict(app='fonts',status='next invocation or popup')])
        self.assertEqual(self.cli('get',key,native=True).stdout,'right\n')
        self.assertIn('next Fonts',json.loads(self.cli('explain',key,'--json').stdout)['activation'])
        self.cli('set',key,'null','--json-value','--no-refresh')
        self.assertEqual(self.cli('get',key).stdout,'down\n')
        defaults=read_defaults(self.root)
        for key,bad in [('apps.fonts.list_details','all'),('apps.fonts.preview.position','left'),
                        ('apps.fonts.preview.size',9),('apps.fonts.preview.size',81),('apps.fonts.preview.size',True),
                        ('apps.fonts.preview.sample','yes')]:
            with self.assertRaises(ValueError):validate_value(defaults,parts(key),bad)

    def test_fresh_completion_on_all_frontends_is_static_and_consistent(self):
        for key,expected in [('apps.fonts.list_details',{'summary','full'}),('apps.fonts.preview.position',{'down','right'})]:
            results=[]
            for shell in ('bash','zsh','fish','native'):
                cmd=([sys.executable,'-B',str(self.root/'lib/dots/cli.py'),'__complete','config','set',key,''] if shell=='native' else
                     [str(self.root/'bin/dots'),'__complete',shell,'4','--','dots','config','set',key,''])
                result=subprocess.run(cmd,env=self.env,capture_output=True,text=True,timeout=20)
                self.assertEqual(result.returncode,0,result.stderr);self.assertNotIn('\x1b',result.stdout)
                values={line.split('\t')[1] for line in result.stdout.splitlines()}
                self.assertTrue(expected<=values,result.stdout);results.append(values)
            self.assertTrue(all(v==results[0] for v in results))

    def test_font_style_save_and_reset_apply_without_theme_publication(self):
        from config_menu import Inventory,Draft
        from config_refresh import effective,after_save
        for key,value in [('colors.fonts.identity.fg','#123456'),('icons.menu.fonts','F'),('colors.icons.menu.fonts.bg','#654321')]:
            before=effective(self.root)
            inventory=Inventory(self.root,self.platform)
            draft=Draft(inventory,inventory.find(key)).prepare(value)
            draft.plan.apply('set')
            with patch('config_refresh.refresh',side_effect=AssertionError('font style must not publish a theme')):
                self.assertEqual(after_save(self.root,before)['consumers'],[dict(app='fonts',status='next invocation or popup')])
            self.cli('unset',key,'--no-refresh')

    def test_all_route_help_uses_shared_preferences_without_library_or_provider_reads(self):
        from fonts_cli import main
        self.configure(formatting=dict(apps=dict(cli=dict(indent=2,label_width='25%',alignment='right'))))
        with patch('fonts_cli.Library',side_effect=AssertionError('help opened library')),patch('subprocess.run',side_effect=AssertionError('help spawned child')):
            for command in COMMANDS:
                out=io.StringIO()
                with patch.dict(os.environ,DOTS_COLOR='always'),redirect_stdout(out),self.assertRaises(SystemExit) as exit:
                    main([*([command] if command else []),'--help'])
                self.assertEqual(exit.exception.code,0)
                self.assertIn('Usage',out.getvalue());self.assertIn('\x1b',out.getvalue())

    def test_catalog_and_nested_rows_keep_literal_ids_and_menu_preferences(self):
        from fonts.browser import picker,select
        self.configure(formatting=dict(apps=dict(menu=dict(indent=2,padding=1,label_width='25%',label_gap=2))),
                       apps=dict(fonts=dict(preview=dict(enabled=False),menu_descriptions=False)))
        rows=[dict(id='local:$(literal)',name='Hidden name')]
        with patch('fonts.browser.rich_fzf_available',return_value=True),patch('fonts.browser.RichSelector.fzf',return_value=[0]) as choose:
            self.assertIs(picker(rows,[],{},None),rows[0])
            args=choose.call_args
            self.assertTrue(args.args[1][0].startswith('   local:$(literal)'))
            self.assertNotIn('Hidden name',args.args[1][0]);self.assertIsNone(args.args[3])
        with patch('fonts.browser.choose',side_effect=lambda menu,**kw:menu.entries[0]) as choose:
            self.assertEqual(select('Face',[('-font ü.ttf','Family','Regular')]),'-font ü.ttf')
            self.assertEqual(choose.call_args.args[0].entries[0].description,'')
            self.assertNotIn('compact',choose.call_args.kwargs)

    def test_preview_renders_at_actual_width_and_can_skip_optional_tools(self):
        from fonts.preview import main
        from menu_tmux import request_file
        self.configure(formatting=dict(apps=dict(cli=dict(label_width='25%'))))
        snapshot=dict(schema=1,previews=[dict(report=dict(items=[ROW]),font='/never/read.ttf',sha256='0'*64)],sample=False,color=False,icons=False)
        with request_file(snapshot) as path:
            for width in (40,80,120):
                out=io.StringIO()
                with patch.object(sys,'argv',['preview',str(path),'0']),patch.dict(os.environ,FZF_PREVIEW_COLUMNS=str(width)),redirect_stdout(out),patch('fonts.preview.sha',side_effect=AssertionError('sample disabled')),patch('subprocess.run',side_effect=AssertionError('sample disabled')):
                    main()
                self.assertIn('-Fixture.ttf',out.getvalue())
                self.assertTrue(all(cells(line)<=width for line in out.getvalue().splitlines()),out.getvalue())
        snapshot['wrap']=False
        with request_file(snapshot) as path:
            out=io.StringIO()
            with patch.object(sys,'argv',['preview',str(path),'0']),patch.dict(os.environ,FZF_PREVIEW_COLUMNS='40'),redirect_stdout(out):main()
            self.assertTrue(any(cells(line)>40 for line in out.getvalue().splitlines()))

    def test_configuration_handoff_is_literal_popup_without_approval_flags(self):
        from fonts.menus import configuration
        from menus import dots_argv
        for windows in (False,True):
            expected=dots_argv(['config','browse','--query','apps.fonts'],root=self.root,windows=windows)
            with patch('fonts.menus.select',return_value='apps.fonts'),patch('menus.dots_argv',return_value=expected),patch('menus.run_action') as run:
                configuration(None)
                self.assertEqual(run.call_args.args[0],expected);self.assertEqual(run.call_args.kwargs['kind'],'popup')
                self.assertNotIn('--yes',expected)


if __name__=='__main__':unittest.main()

#!/usr/bin/env python3
"""Typed config and exact reads in disposable profile/state roots."""
import json
import os
import shutil
import subprocess
import unittest
from unittest.mock import patch
import test_profile_config as fixtures
from config_values import Controls, parts, name, current
from config_cli import ControlPlan
from profile_config import context, keys
from transactions import Store

class Values(fixtures.ProfileConfig):
    def setUp(self):
        super().setUp()
        shutil.copytree(fixtures.ROOT/'default',self.root/'default')
        self.environ=patch.dict(os.environ,self.env,clear=True);self.environ.start();self.addCleanup(self.environ.stop)
        current.cache_clear();self.addCleanup(current.cache_clear)

    def test_git_view_and_progress_choices_reset_and_activation(self):
        from config_menu import Inventory,Draft
        from config_refresh import effective,after_save
        for key,default,choices,consumer in (
                ('apps.cli.progress','both',['none','spinner','bar','both'],'cli'),
                ('apps.git.view','default',['default','short','verbose'],'git')):
            self.assertEqual(self.run_config('get',key).stdout,default+'\n')
            self.run_config('set',key,'invalid','--no-refresh',code=1)
            row=Inventory(self.root,self.platform).find(key)
            self.assertEqual(row.constraints['choices'],choices)
            before=effective(self.root)
            Draft(Inventory(self.root,self.platform),row).prepare(choices[1]).plan.apply('set')
            with patch('config_refresh.refresh',side_effect=AssertionError('view preferences must not publish')):
                self.assertEqual(after_save(self.root,before)['consumers'],[dict(app=consumer,status='next invocation')])
            self.assertEqual(self.run_config('get',key,native=True).stdout,choices[1]+'\n')
            current.cache_clear()
            from cli_preferences import git_view,progress_mode
            if consumer=='git':
                self.assertEqual(git_view(human=True),'short')
                self.assertIsNone(git_view(human=False))
                self.assertEqual(git_view('verbose',human=True),'verbose')
                self.assertIsNone(git_view('verbose',human=True,data=True))
            else:
                with patch.dict(os.environ,{'DOTS_PROGRESS':'auto'}): self.assertEqual(progress_mode(),'spinner')
                with patch.dict(os.environ,{'DOTS_PROGRESS':'bar'}): self.assertEqual(progress_mode(),'bar')
                with patch.dict(os.environ,{'DOTS_PROGRESS':'never'}): self.assertEqual(progress_mode(),'none')
            self.assertEqual(json.loads(self.run_config('explain',key,'--json').stdout)['activation'],'next invocation')
            self.run_config('set',key,'null','--json-value','--no-refresh')
            self.assertEqual(self.run_config('get',key).stdout,default+'\n')

    def test_cleanup_preference_validation_reset_and_consumer(self):
        import io
        from contextlib import redirect_stdout
        import cleanup_cli
        key='apps.cleanup.checkpoint_min_age_days'
        self.run_config('set',key,'45','--defaults','--no-refresh')
        self.assertEqual(self.run_config('get',key).stdout,'45\n')
        self.run_config('set',key,'60','--no-refresh')
        for bad in ('-1','36501','true','abc'):
            self.run_config('set',key,bad,'--no-refresh',code=1)
        self.assertEqual(Controls(self.root).resolve(key)['value'],60)
        explanation=json.loads(self.run_config('explain',key,'--json').stdout)
        self.assertEqual(explanation['activation'],'next invocation')
        for flag,expected in [([],60),(['--older-than','7'],7)]:
            current.cache_clear()
            with patch('cleanup_cli.Termux') as adapter,patch('cleanup_cli.detect',return_value={'platform':'termux'}),patch('cleanup_cli.available',return_value=0),redirect_stdout(io.StringIO()):
                adapter.return_value.candidates.return_value=([],[])
                self.assertEqual(cleanup_cli.main(['scan','--group','project-checkpoints','--json',*flag]),0)
                self.assertEqual(adapter.return_value.candidates.call_args.args[1],expected)
        self.run_config('unset',key,'--no-refresh')
        self.assertEqual(self.run_config('get',key).stdout,'45\n')

    def test_backup_controls_preserve_explicit_choices_and_validate(self):
        self.assertEqual(Controls(self.root).resolve('apps.bak.mode')['value'],'move')
        for key,value in [('apps.bak.mode','copy'),('apps.bak.location','adjacent'),('apps.bak.store','~/my backups')]:
            self.run_config('set',key,value,'--no-refresh')
            self.assertEqual(Controls(self.root).resolve(key)['value'],value)
        for key,value in [('apps.bak.mode','delete'),('apps.bak.location','anywhere'),('apps.bak.store','relative')]:
            before=self.path.read_bytes()
            self.run_config('set',key,value,'--no-refresh',code=1)
            self.assertEqual(self.path.read_bytes(),before)

    def test_literals_types_null_and_data(self):
        key='apps.nvim.highlights["@variable.member"].fg'
        self.assertEqual(name(parts(key)),key)
        self.assertIn('formatting.apps.todo.list_type',keys(self.root))
        self.assertIn('colors.apps.todo.field.status.value.fg',keys(self.root))
        self.assertEqual(self.run_config('get','colors.todo.field.status.value.fg').stdout,'null\n')
        self.assertEqual(self.run_config('get',key).stdout,'null\n')
        self.assertIsNone(json.loads(self.run_config('get',key,'--json').stdout)['value'])
        self.run_config('get','apps.nvim.typo',code=1)
        self.run_config('set',key,'#123456','--no-refresh')
        self.assertEqual(self.run_config('get',key,native=True).stdout,'#123456\n')
        self.run_config('set','apps.nvim.options.wrap','false','--no-refresh')
        self.assertEqual(self.run_config('get','apps.nvim.options.wrap').stdout,'false\n')
        self.run_config('set','formatting.apps.todo.indent','0','--no-refresh')
        self.assertEqual(self.run_config('get','formatting.apps.todo.indent').stdout,'0\n')
        self.run_config('set','formatting.apps.todo.list_type','invalid','--no-refresh',code=1)
        self.run_config('set','apps.nvim.options.wrap','null','--json-value','--no-refresh')
        self.assertEqual(self.run_config('get','apps.nvim.options.wrap').stdout,'true\n')
        self.assertEqual(self.run_config('get','colors.apps.tmux.status.warning.fg').stdout,'warning\n')
        self.assertEqual(self.run_config('get','colors.apps.cli.ui.heading.bg').stdout,'null\n')
        self.run_config('get','colors.not_a_role.fg',code=1)
        for malformed in ('apps.nvim.highlights["x"]junk','apps.nvim.highlights[1]','apps..nvim'):
            self.run_config('get',malformed,code=1)

    def test_guards_undo_and_popup(self):
        from config_menu import Inventory,Draft
        original=self.path.read_bytes()
        row=Inventory(self.root,self.platform).find('formatting.apps.todo.list_type')
        draft=Draft(Inventory(self.root,self.platform),row).prepare('regular')
        self.assertEqual(draft.proposed,'regular')
        result=draft.plan.apply('set')
        self.assertEqual(Controls(self.root).resolve(row.key)['value'],'regular')
        store=Store(self.home/'state/dots');ops,guards,catalogs=store.inverse(result['id'])
        store.apply('undo',ops,guards,retain=True,catalogs=catalogs)
        self.assertEqual(json.loads(self.path.read_bytes()),json.loads(original))
        plan=ControlPlan(self.root,context(self.root));plan.edit('formatting.apps.todo.indent','3')
        self.path.write_text(self.path.read_text()+'\n')
        with self.assertRaises(ValueError):plan.apply('set')

    def test_usage_logo_choices_reset_popup_and_next_invocation(self):
        from config_menu import Inventory,Draft
        from config_refresh import effective,after_save
        key='apps.cli.logo_gradient'
        # Isolate reset semantics from the user's shared default preference.
        self.run_config('set',key,'classic','--defaults','--no-refresh')
        self.assertEqual(self.run_config('get',key).stdout,'classic\n')
        self.run_config('set',key,'invalid','--no-refresh',code=1)
        row=Inventory(self.root,self.platform).find(key)
        self.assertEqual(row.constraints['choices'],['classic','installer'])
        before=effective(self.root)
        draft=Draft(Inventory(self.root,self.platform),row).prepare('installer')
        draft.plan.apply('set')
        with patch('config_refresh.refresh',side_effect=AssertionError('logo choice must not publish a theme')):
            self.assertEqual(after_save(self.root,before)['consumers'],[dict(app='cli',status='next invocation')])
        self.assertEqual(self.run_config('get',key,native=True).stdout,'installer\n')
        explanation=json.loads(self.run_config('explain',key,'--json').stdout)
        self.assertEqual(explanation['activation'],'next invocation')
        self.run_config('set',key,'null','--json-value','--no-refresh')
        self.assertEqual(self.run_config('get',key).stdout,'classic\n')

    def test_help_tagline_validation_popup_inheritance_and_literal_shell_value(self):
        from config_menu import Inventory,Draft
        from config_refresh import effective,after_save
        from help_presentation import HelpStyles
        from config_values import validate_value
        key='apps.cli.tagline'
        self.assertEqual(self.run_config('get',key).stdout,'Manage your dotfiles and more...\n')
        defaults=Controls(self.root).defaults
        for invalid in ('line\nline','tab\there','\x1b[31m','\x85','\u2028',42):
            with self.assertRaises(ValueError):validate_value(defaults,parts(key),invalid)
        literal='  ü dots $(touch MUST_NOT_EXIST); "quoted" \\ text  '
        row=Inventory(self.root,self.platform).find(key)
        self.assertIn('empty hides',row.constraints['syntax'])
        before=effective(self.root)
        Draft(Inventory(self.root,self.platform),row).prepare(literal).plan.apply('set')
        with patch('config_refresh.refresh',side_effect=AssertionError('help preferences must not publish')):
            self.assertEqual(after_save(self.root,before)['consumers'],[dict(app='cli',status='next invocation')])
        self.assertEqual(HelpStyles(self.root).tagline,literal)
        self.assertEqual(self.run_config('get',key,native=True,DOTS_COLOR='always').stdout,literal+'\n')
        explanation=json.loads(self.run_config('explain',key,'--json').stdout)
        self.assertEqual(explanation['activation'],'next invocation')
        script='source "$DOTS/lib/dots/shell/config.bash"; _dots_config_load || exit; printf "%s" "$_DOTS_HELP_TAGLINE"'
        for shell in ('bash','zsh'):
            executable=shutil.which(shell)
            if not executable:continue
            result=subprocess.run([executable,'-c',script],env=self.env,cwd=self.home,capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(result.stdout,literal)
        self.assertFalse((self.home/'MUST_NOT_EXIST').exists())
        self.run_config('set',key,'','--no-refresh')
        self.assertEqual(HelpStyles(self.root).tagline,'')
        self.run_config('set',key,'null','--json-value','--no-refresh')
        self.assertEqual(HelpStyles(self.root).tagline,'Manage your dotfiles and more...')

    def test_help_styles_discovery_consumer_and_next_invocation(self):
        from config_menu import Inventory,Draft
        from config_refresh import effective,after_save
        from help_presentation import HelpStyles
        from style_catalog import HELP,ATTRIBUTES
        from style_config import Styles
        from config_completion import key_candidates,value_candidates
        catalog=set(keys(self.root))
        for role in HELP:
            for field in ('fg','bg',*ATTRIBUTES):
                self.assertIn('colors.apps.cli.help.'+role+'.'+field,catalog)
        self.assertNotIn('colors.help.argument.fg',catalog)
        self.assertEqual([key for key,_ in key_candidates(self.root,'apps.cli.tagline')],['apps.cli.tagline'])
        self.assertIn(('colors.apps.cli.help.argument.fg','cli · help.argument · foreground color'),key_candidates(self.root,'colors.apps.cli.help.argument.fg'))
        self.assertEqual({value for value,_ in value_candidates(self.root,'colors.apps.cli.help.heading.bold')},{'true','false'})
        self.assertIn('cyan',{value for value,_ in value_candidates(self.root,'colors.apps.cli.help.executable.fg')})
        key='colors.apps.cli.help.argument.fg'
        row=Inventory(self.root,self.platform).find(key)
        before=effective(self.root)
        Draft(Inventory(self.root,self.platform),row).prepare('#123456').plan.apply('set')
        with patch('config_refresh.refresh',side_effect=AssertionError('help colors must not publish')):
            self.assertEqual(after_save(self.root,before)['consumers'],[dict(app='cli',status='next invocation')])
        self.assertIn('38;2;18;52;86',HelpStyles(self.root).code('argument'))
        self.assertEqual(self.run_config('get',key,DOTS_COLOR='always',DOTS_ICONS='always').stdout,'#123456\n')
        self.assertEqual(self.run_config('get',key,'--json',native=True,DOTS_COLOR='always').stdout.count('\x1b'),0)
        script='source "$DOTS/lib/dots/shell/config.bash"; _dots_config_load || exit; printf "%s" "${_DOTS_HELP_STYLES[argument]}"'
        result=subprocess.run([shutil.which('bash'),'-c',script],env=self.env,capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout,HelpStyles(self.root).code('argument'))
        self.run_config('set','colors.apps.cli.help.heading.bold','false','--no-refresh')
        self.assertFalse(Styles(self.root).style('help.heading',app='cli')['bold'])
        self.run_config('unset',key,'--no-refresh')
        self.assertEqual(self.run_config('get',key).stdout,'green\n')
        from config_refresh import explain
        from config_view import compact_styles
        styles=Styles(self.root,palette={})
        explanation=explain('colors.apps.cli.help.tagline.fg',self.root,_style=styles)['consumers'][0]
        self.assertEqual(explanation['value'],'accent')
        self.assertEqual(explanation['resolved_color'],'foreground')
        self.assertIn('Theme accent unavailable',explanation['fallback'])
        sample=compact_styles({'apps':{'cli':{'help':{'tagline':{'fg':'accent'}}}}},styles)['apps']['cli']['help']['tagline']
        self.assertEqual(sample.text,'fg:accent')
        self.assertEqual(sample.code,HelpStyles(styles=styles).code('tagline'))

if __name__=='__main__':unittest.main()

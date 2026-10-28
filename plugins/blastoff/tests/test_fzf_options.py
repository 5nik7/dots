import os
from unittest.mock import patch
from release_support import ReleaseHarness,core

ui=core.ui_module('picker_ui')

class FzfOptions(ReleaseHarness):
    def test_file_environment_precedence_and_blocked_execution(self):
        file=self.write(self.home/'fzf opts','--layout=reverse --color=light --bind ctrl-j:down\n')
        values=ui.inherited_options({'FZF_DEFAULT_OPTS_FILE':str(file),'FZF_DEFAULT_OPTS':'--color=dark --filter=x --bind=start:execute(touch bad) --history=/tmp/history --preview=evil --listen=9000'})
        self.assertLess(values.index('--color=light'),values.index('--color=dark'))
        self.assertIn('--bind=ctrl-j:down',values)
        for bad in ('filter','execute','history','preview','listen'):self.assertNotIn(bad,' '.join(values))
    def test_bindings_and_malformed_settings(self):
        for value in ('start:accept','ctrl-x:abort','ctrl-a:select-all+accept','ctrl-j:execute(evil)','ctrl-c:ignore'):
            self.assertFalse(ui.safe_binding(value))
        self.assertEqual(ui.inherited_options({'FZF_DEFAULT_OPTS':'"bad'}),[])
    def test_basic_fancy_and_multiselect(self):
        args=ui.fzf_args(120,30,True,'sh -c','fixed {1}')
        self.assertFalse(any(x.startswith('--color=') for x in args));self.assertFalse(any(x.startswith('--border=') for x in args))
        self.assertIn('--bind=ctrl-x:toggle-preview',args)
        self.assertTrue(any('<60(down' in x for x in args))
        args=ui.fzf_args(40,12,False,'sh -c','fixed {1}',fancy='ascii',multi=True)
        self.assertIn('--no-unicode',args);self.assertIn('--multi',args);self.assertIn('--bind=tab:toggle+down,shift-tab:toggle+up',args)
    def test_selection_uses_original_ids_not_display_commands(self):
        import subprocess
        def fake(argv,**kw):
            self.assertNotIn('FZF_DEFAULT_COMMAND',kw['env']);self.assertNotIn('BASH_ENV',kw['env'])
            return subprocess.CompletedProcess(argv,0,'1\tb\n0\ta\n')
        with patch.object(ui.subprocess,'run',fake):
            selected=ui.choose_fzf(['backup:one','backup:two'],self.home,False,{'FZF_DEFAULT_COMMAND':'evil','BASH_ENV':'evil'},multi=True,labels=['a','b'])
        self.assertEqual(selected,['backup:two','backup:one'])

    def test_hex_colors_comments_negative_values_and_individual_bindings(self):
        values=ui.inherited_options({'FZF_DEFAULT_OPTS': '--color=fg:#abcdef,bg:#123456 --height -3 # comment\n--layout=reverse --bind=ctrl-j:down,ctrl-x:abort,ctrl-k:up'})
        self.assertIn('--color=fg:#abcdef,bg:#123456',values)
        self.assertIn('--height=-3',values); self.assertIn('--layout=reverse',values)
        self.assertIn('--bind=ctrl-j:down,ctrl-k:up',values)
        self.assertEqual(ui.option_words('--color="fg:#123456" --border-label="a # b"'),['--color=fg:#123456','--border-label=a # b'])

    def test_shared_style_grammar_and_no_write_dry_run(self):
        parse=lambda args:core.cli_module().parse(args,core.VERSION)
        for command in (['pick'],['module','show'],['backup','delete','--pick']):
            self.assertEqual(parse(command).fancy,'unicode')
            self.assertEqual(parse(command+['--fancy','ascii']).fancy,'ascii')
            self.assertIsNone(parse(command+['--fzf']).fancy)
            with self.assertRaises(core.Failure):parse(command+['--fzf','--fancy'])
            before=self.tree(); result=self.invoke(*command,'--fzf','--dry-run')
            self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(before,self.tree())
        self.assertTrue(parse(['pick','fzf']).fzf)
        for args in (['pick','fancy','--fzf'],['pick','fzf','--fancy'],['module','show','foo','--fzf'],['backup','delete','--all','--fzf']):
            with self.assertRaises(core.Failure):parse(args)
        self.assertTrue(parse(['backup','delete','--pick','--fancy','ascii','yes']).yes)
        self.assertEqual(parse(['backup','delete','--','fzf','all','yes']).ids,['fzf','all','yes'])

    def test_explicit_basic_missing_dependency_is_clear_before_discovery(self):
        before=self.tree()
        with patch.object(core.shutil,'which',return_value=None),patch.object(core.App,'optional_presets',side_effect=AssertionError('unnecessary discovery')):
            status,out,err=self.run_tty(['pick','--fzf'])
        self.assertEqual(status,3);self.assertIn('fzf is required',err)
        self.assertEqual(before,self.tree())

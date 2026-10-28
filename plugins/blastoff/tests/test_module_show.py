import json
from release_support import ReleaseHarness

class ModuleShow(ReleaseHarness):
    def test_named_raw_and_json_no_mutation(self):
        content='# comment\n[directory]\nstyle="purple"\n'
        self.write(self.store/'modules/dir.toml',content);before=self.tree()
        self.assertEqual(self.invoke('module','show','dir').stdout,content)
        self.assertEqual(json.loads(self.invoke('module','show','dir','--json').stdout)['toml'],content)
        self.assertEqual(self.tree(),before);self.assertFalse(self.config.exists())
    def test_missing_noninteractive_and_optional_tool(self):
        self.invoke('module','show','missing',code=1);self.invoke('module','show',code=2)
        self.write(self.store/'modules/dir.toml','[directory]\nx=1\n')
        code,_,err=self.run_tty(['module','show']);self.assertEqual(code,3);self.assertIn('fzf',err)
    def test_symlink_refused(self):
        p=self.write(self.store/'modules/dir.toml','x=1\n');p.unlink();p.symlink_to(self.home/'other')
        self.invoke('module','show','dir',code=1)
    def test_browser_selection_and_cancellation_never_load(self):
        from unittest.mock import patch
        from release_support import core
        self.write(self.store/'modules/dir.toml','[directory]\nx=1\n');before=self.tree()
        ui=core.ui_module('picker_ui');op=core.ui_module('operations')
        loader=core.ui_module
        with patch.object(core,'ui_module',side_effect=lambda name:ui if name=='picker_ui' else loader(name)), patch.object(op.shutil,'which',side_effect=lambda name:'/fixture/fzf' if name=='fzf' else None):
            with patch.object(ui,'choose_fzf',return_value=None):
                code,_,_=self.run_tty(['module','show']);self.assertEqual(code,130)
            with patch.object(ui,'choose_fzf',return_value='module:dir'):
                code,out,_=self.run_tty(['module','show']);self.assertEqual(code,0)
                self.assertIn('Module: dir',out);self.assertIn('[directory]',out)
        self.assertEqual(self.tree(),before);self.assertFalse(self.config.exists())

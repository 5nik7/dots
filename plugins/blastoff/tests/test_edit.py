import json
import sys
import os
import shutil
import unittest
from unittest.mock import patch
from release_support import ReleaseHarness,core

class Edit(ReleaseHarness):
    def editor(self, body):
        executable=self.home/'editor space'
        executable.write_text('#!'+sys.executable+'\nfrom pathlib import Path\nimport sys,os\np=Path(sys.argv[-1])\n'+body+'\n');executable.chmod(0o755)
        self.env['EDITOR']='"'+str(executable)+'" --argument "with spaces"'
    def test_edit_staged_atomic_save_and_provenance(self):
        self.theme();self.invoke('theme','apply','purple')
        self.editor('q=p.with_suffix(".new");q.write_text("x=7\\n");os.replace(q,p)')
        code,_,err=self.run_tty(['theme','edit']);self.assertEqual(code,0,err)
        self.assertEqual(self.config.read_text(),'x=7\n');self.assertIn('purple',(self.store/'themes/purple.toml').read_text())
        self.assertEqual(json.loads(self.invoke('current','--json').stdout)['provenance']['origin'],'local:purple')
    def test_invalid_failure_and_concurrent_edits_retained(self):
        for body in ('p.write_text("invalid = [")','p.write_text("x=2\\n");sys.exit(4)',
                     'p.write_text("x=2\\n");Path(os.environ["STARSHIP_CONFIG"]).write_text("external=1\\n")'):
            self.write(self.config,'x=1\n');self.editor(body)
            code,_,err=self.run_tty(['theme','edit']);self.assertIn(code,(1,3));self.assertIn('recovery',err)
            self.assertTrue(list(self.config.parent.glob('.blastoff-edit-*/starship.toml')))
            self.assertIn(self.config.read_text(),('x=1\n','external=1\n'))
    def test_symlink_conversion_preserves_target(self):
        original=self.write(self.home/'source.toml','x=1\n');self.config.parent.mkdir();self.config.symlink_to(original)
        self.editor('p.write_text("x=2\\n")')
        code,_,_=self.run_tty(['theme','edit','--replace-link']);self.assertEqual(code,0)
        self.assertFalse(self.config.is_symlink());self.assertEqual(original.read_text(),'x=1\n')
    def test_symlink_edit_preserves_link_and_target_history(self):
        original=self.write(self.home/'source.toml','x=1\n')
        self.config.parent.mkdir();self.config.symlink_to(original)
        self.editor('p.write_text("x=2\\n")')
        code,_,err=self.run_tty(['theme','edit']);self.assertEqual(code,0,err)
        self.assertTrue(self.config.is_symlink());self.assertEqual(original.read_text(),'x=2\n')
        self.assertEqual(self.snapshots()[0].read_text(),'x=1\n')

    def test_dry_run_no_launch_and_explicit_editor_failure(self):
        self.editor('raise RuntimeError("must not launch")');before=self.tree()
        self.invoke('theme','edit','--dry-run');self.assertEqual(self.tree(),before)
        self.env['EDITOR']='missing-editor';self.invoke('theme','edit','--dry-run',code=3)
    def test_editor_order_and_wait_arguments(self):
        editor=core.ui_module('editor')
        with patch.dict('os.environ',{'EDITOR':''},clear=True),patch.object(editor.shutil,'which',side_effect=lambda x:'/bin/code' if x=='code' else None):
            self.assertEqual(editor.resolve(core),['/bin/code','--wait'])
        self.assertEqual(editor.windows_words('"C:\\Program Files\\editor.exe" --arg "two words"'),['C:\\Program Files\\editor.exe','--arg','two words'])

    @unittest.skipUnless(os.name=='posix' and shutil.which('nvim'), 'native nvim/PTTY unavailable')
    def test_native_editor_in_isolated_pty(self):
        from pty_support import terminal
        self.write(self.config,'x=1\n')
        import shlex
        self.env['PATH']=os.environ.get('PATH','')
        self.env['EDITOR']=shlex.join([shutil.which('nvim'),'--clean','--headless','-i','NONE','-n','-c','call setline(1, "x=8")','-c','wq'])
        code,output=terminal([sys.executable,'-I',str(core.Path(core.__file__)),'theme','edit'],self.env,columns=60,rows=24)
        self.assertEqual(code,0,output)
        self.assertEqual(self.config.read_text(),'x=8\n')
    def test_interruption_preserves_work_and_original(self):
        self.write(self.config,'x=1\n');self.editor('p.write_text("x=2\\n")')
        editor=core.ui_module('editor')
        with patch.object(editor.subprocess,'run',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):self.run_tty(['theme','edit'])
        self.assertEqual(self.config.read_text(),'x=1\n')
        self.assertTrue(list(self.config.parent.glob('.blastoff-edit-*/starship.toml')))
        self.assertFalse((self.store/'.operation.lock').exists())

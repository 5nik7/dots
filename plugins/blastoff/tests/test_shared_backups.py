"""New snapshots share Bak storage; old pairs remain a compatibility reader."""
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
from release_support import ReleaseHarness, core


class SharedBackups(ReleaseHarness):
    def test_profile_storage_preferences_and_adjacent_cleanup(self):
        import shutil
        root = self.home/'checkout'; root.mkdir()
        shutil.copytree(Path(core.__file__).resolve().parents[3]/'default',root/'default')
        self.env['DOTS'] = str(root)
        for platform in ('termux','linux','wsl','windows'):
            self.write(root/'profiles'/platform/'profile.json',json.dumps(dict(schema=1,id=platform,
                apps=dict(bak=dict(store='~/custom backups',location='store',mode='move')))))
        self.write(self.config,'x=1\n')
        ident=json.loads(self.invoke('backup','create','--json').stdout)['backup']
        self.assertEqual(self.backup_payload(ident).parent.parent,self.home/'custom backups')
        self.assertTrue(self.config.exists()) # automatic snapshots explicitly copy
        for path in (root/'profiles').glob('*/profile.json'):
            doc=json.loads(path.read_text());doc['apps']['bak']['location']='adjacent';path.write_text(json.dumps(doc))
        ident=json.loads(self.invoke('backup','create','--json').stdout)['backup']
        self.assertEqual(self.backup_payload(ident).parent,self.config.parent)
        self.invoke('backup','delete',ident,'--yes')
        self.assertTrue(self.config.parent.exists());self.assertTrue(self.config.exists())

    def test_create_list_restore_and_delete_share_one_payload(self):
        self.write(self.config, 'x=1\n')
        ident = json.loads(self.invoke('backup','create','--json').stdout)['backup']
        payload = self.backup_payload(ident)
        self.assertEqual(self.config.read_text(), 'x=1\n')
        self.assertEqual(payload.read_text(), 'x=1\n')
        self.assertFalse((self.store/'backups').exists())
        listed = json.loads(self.invoke('backup','list','--json').stdout)['backups']
        self.assertEqual([r['id'] for r in listed], [ident])
        self.assertIn('created', listed[0])
        before = self.tree()
        preview = json.loads(self.invoke('backup','delete',ident,'--dry-run','--json').stdout)
        self.assertIn(str(payload.parent), preview['targets'])
        self.assertEqual(before, self.tree())
        self.write(self.config, 'x=2\n')
        self.invoke('backup','restore',ident)
        self.assertEqual(self.config.read_text(),'x=1\n')
        self.assertTrue(payload.exists())
        self.invoke('backup','delete',ident,'--yes')
        self.assertFalse(payload.parent.exists())
        self.assertNotIn(ident, self.backup_entries())

    def test_bak_delete_is_immediately_visible_to_blastoff(self):
        self.write(self.config, 'x=1\n')
        ident = json.loads(self.invoke('backup','create','--json').stdout)['backup']
        payload = self.backup_payload(ident)
        script = Path(core.__file__).resolve().parents[3]/'lib/dots/bak_cli.py'
        result = subprocess.run([sys.executable,'-B',str(script),'delete',ident,'--yes','--json'],
            env=self.env,capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertFalse(payload.parent.exists())
        self.assertEqual(json.loads(self.invoke('backup','list','--json').stdout)['backups'],[])

    def test_missing_payload_cleanup_extra_files_and_legacy_inventory(self):
        self.write(self.config,'x=1\n')
        legacy = self.legacy_backup()
        ident = json.loads(self.invoke('backup','create','--json').stdout)['backup']
        payload = self.backup_payload(ident)
        self.assertEqual(len(json.loads(self.invoke('backup','list','--json').stdout)['backups']),2)
        payload.unlink()
        self.invoke('backup','delete',ident,'--yes')
        self.assertFalse(payload.parent.exists())
        self.invoke('backup','restore',legacy)
        ident = json.loads(self.invoke('backup','create','--json').stdout)['backup']
        payload = self.backup_payload(ident)
        extra = payload.parent/'keep'; extra.write_text('mine')
        self.invoke('backup','delete',ident,'--yes')
        self.assertEqual(extra.read_text(),'mine')

    def test_preview_and_completion_use_catalog_without_payload_discovery(self):
        self.write(self.config,'x=1\n')
        ident = json.loads(self.invoke('backup','create','--json').stdout)['backup']
        with patch.dict(os.environ,self.env,clear=True):
            helper = core.ui_module('completion_names')
            before = self.tree()
            self.assertEqual(helper.names(str(self.store),'backups'),[ident])
            self.assertEqual(before,self.tree())
            preview = core.ui_module('preview')
            directory = self.home/'preview'; directory.mkdir()
            (directory/'choices.json').write_text(json.dumps(dict(choices=['backup:'+ident],
                themes=str(self.store/'backups'), color=False, starship=None, bat=None)))
            # Preview runs its normal bounded reader and renders backup content.
            output = subprocess.run([sys.executable,'-I',str(Path(preview.__file__)),str(directory),'0'],
                env=self.env,capture_output=True,text=True,timeout=10)
            self.assertEqual(output.returncode,0,output.stderr)
            self.assertIn('x=1',output.stdout)

    def test_shared_catalog_race_does_not_delete_a_changed_selection(self):
        self.write(self.config,'x=1\n')
        ident = json.loads(self.invoke('backup','create','--json').stdout)['backup']
        payload = self.backup_payload(ident)
        def change(): payload.write_text('x=9\n')
        code,_,_ = self.run_tty(['backup','delete',ident], 'yes\n', change)
        self.assertEqual(code,1)
        self.assertIn(ident,self.backup_entries()); self.assertEqual(payload.read_text(),'x=9\n')

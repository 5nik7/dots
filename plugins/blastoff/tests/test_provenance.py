import json
from unittest.mock import patch
from release_support import ReleaseHarness, core

class Provenance(ReleaseHarness):
    def current(self): return json.loads(self.invoke('current','--json').stdout)['provenance']
    def test_origin_survives_external_edits_and_save_as(self):
        self.theme();self.invoke('theme','apply','purple')
        self.assertEqual(self.current()['origin'],'local:purple')
        self.config.write_text('x=2\n')
        self.assertTrue(self.current()['external_change'])
        self.invoke('theme','save','work')
        doc=self.current();self.assertEqual(doc['origin'],'local:purple')
        self.assertEqual(doc['save_target']['name'],'work');self.assertFalse(doc['external_change'])
    def test_backup_restore_restores_origin_old_backup_unknown(self):
        self.theme();self.invoke('theme','apply','purple')
        ident=json.loads(self.invoke('backup','create','--json').stdout)['backup']
        self.config.write_text('x=4\n');self.invoke('backup','restore',ident)
        self.assertEqual(self.current()['origin'],'local:purple')
        p=self.store/'backups'/(ident+'.json');doc=json.loads(p.read_text());doc.pop('provenance');p.write_text(json.dumps(doc))
        self.invoke('backup','restore',ident);self.assertEqual(self.current()['origin'],'unknown')
    def test_module_load_retains_origin(self):
        self.theme();self.invoke('theme','apply','purple');self.invoke('module','save','directory','dir')
        (self.store/'modules/dir.toml').write_text('[directory]\nstyle="other"\n')
        self.invoke('module','load','dir');self.assertEqual(self.current()['origin'],'local:purple')
        self.assertTrue(self.current()['changed_since_load'])
    def test_corrupt_future_and_pending_state_are_read_only(self):
        self.theme();self.invoke('theme','apply','purple')
        p=next((self.store/'state/provenance').glob('*.json'))
        malformed=json.loads(p.read_text());malformed['save_target']={'kind':'preset','name':'purple','sha256':'a'*64}
        for text in ('{','[]','{"version":99}', json.dumps(malformed)):
            p.write_text(text);before=self.tree();self.assertEqual(self.current()['origin'],'unknown');self.assertEqual(self.tree(),before)
        p.with_suffix('.pending').write_text('{}')
        self.assertIn('incomplete',self.current()['status'])
    def test_failed_state_commit_disables_save_authority(self):
        self.theme();self.invoke('theme','apply','purple');self.theme('other','x=3\n')
        original=core.atomic
        def fail(p,*args,**kw):
            if p.parent.name=='provenance' and p.suffix=='.json': raise OSError('injected tracking failure')
            return original(p,*args,**kw)
        with patch.object(core,'atomic',side_effect=fail):
            with self.assertRaises(OSError):self.run_tty(['theme','apply','other'])
        self.assertEqual(self.config.read_text(),'x=3\n');self.assertIn('incomplete',self.current()['status'])
    def test_no_library_scan_for_save(self):
        self.theme();self.invoke('theme','apply','purple')
        with patch.object(core.App,'files',side_effect=AssertionError('library scan')):
            code,_,_=self.run_tty(['theme','save'],'y\n')
        self.assertEqual(code,0)
    def test_preset_origin_offers_local_copy_and_failed_apply_preserves_state(self):
        with patch.object(core.App,'presets',return_value=['builtin']), patch.object(core.App,'starship',return_value='x=9\n'):
            code,_,_=self.run_tty(['preset','apply','builtin']);self.assertEqual(code,0)
        self.assertEqual(self.current()['origin'],'preset:builtin')
        code,_,err=self.run_tty(['theme','save'],'local-copy\n');self.assertEqual(code,0)
        self.assertIn('save a local copy',err)
        self.assertEqual(self.current()['origin'],'preset:builtin')
        self.assertEqual(self.current()['save_target']['name'],'local-copy')
        before=self.tree();self.theme('invalid','x=[')
        before=self.tree();self.invoke('theme','apply','invalid',code=1);self.assertEqual(self.tree(),before)
    def test_renamed_origin_does_not_guess_matching_copy(self):
        self.theme();self.invoke('theme','apply','purple')
        (self.store/'themes/purple.toml').rename(self.store/'themes/renamed.toml')
        before=self.tree();code,_,err=self.run_tty(['theme','save'],'\n')
        self.assertEqual(code,130);self.assertIn('No unchanged',err);self.assertEqual(self.tree(),before)

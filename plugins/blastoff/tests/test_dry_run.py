import json
from release_support import ReleaseHarness

class DryRun(ReleaseHarness):
    def test_all_mutations_leave_tree_unchanged(self):
        self.write(self.config,'[directory]\nstyle="old"\n'); self.theme()
        self.invoke('module','save','directory','dir')
        ident=json.loads(self.invoke('backup','create','--json').stdout)['backup']
        legacy=self.home/'legacy'; self.write(legacy/'new.toml','x=1\n')
        cases=[['theme','apply','purple'],['theme','save','copy'],['theme','save'],
            ['theme','copy','purple','copy'],['theme','import',str(self.config),'imported'],
            ['theme','delete','purple','--force'],['preset','apply','plain'],['preset','save','plain','plain'],
            ['pick'],['module','save','directory','other'],['module','load','dir'],
            ['module','delete','dir','--force'],['backup','create'],['backup','restore',ident],
            ['backup','delete','--all'],['backup','delete','--pick'],['migrate',str(legacy)]]
        for case in cases:
            with self.subTest(case=case):
                before=self.tree(); result=self.invoke(*case,'--dry-run','--json')
                self.assertTrue(json.loads(result.stdout)['dry_run']);self.assertEqual(self.tree(),before)
    def test_no_missing_directories_or_editor_launch(self):
        self.theme();before=self.tree()
        self.invoke('theme','apply','purple','--dry-run')
        self.assertEqual(self.tree(),before)
    def test_verbose_preserves_json_stdout(self):
        result=self.invoke('module','list','-v','--json')
        self.assertEqual(json.loads(result.stdout),{'modules':[]})
        self.assertEqual(json.loads(result.stderr)['level'],'debug')
    def test_dry_run_rejects_unsafe_destination_and_collision(self):
        self.write(self.config,'x=1\n');self.theme()
        self.invoke('theme','save','purple','--dry-run',code=1)
        self.config.unlink();self.config.symlink_to(self.store/'themes/purple.toml')
        before=self.tree();self.invoke('theme','apply','purple','--dry-run',code=1)
        self.assertEqual(self.tree(),before)
    def test_known_save_dry_run_refuses_lock_and_linked_state(self):
        self.theme();self.invoke('theme','apply','purple')
        lock=self.store/'.operation.lock';lock.write_text('busy')
        before=self.tree();self.invoke('theme','save','--dry-run',code=1);self.assertEqual(self.tree(),before)
        lock.unlink()
        p=next((self.store/'state/provenance').glob('*.json'));p.unlink();p.symlink_to(self.config)
        before=self.tree();self.invoke('theme','save','--dry-run',code=1);self.assertEqual(self.tree(),before)

from release_support import ReleaseHarness

class ThemeSave(ReleaseHarness):
    def prepare(self):
        self.theme();self.invoke('theme','apply','purple');self.config.write_text('x=2\n')
    def test_yes_needs_no_force(self):
        for answer in ('y','Y','yes','Yes','YES'):
            self.prepare();code,_,_=self.run_tty(['theme','save'],answer+'\n')
            self.assertEqual(code,0);self.assertEqual((self.store/'themes/purple.toml').read_text(),'x=2\n')
    def test_negative_and_unknown_input(self):
        self.prepare()
        for answer in ('','n','NO'):
            before=self.tree();code,_,err=self.run_tty(['theme','save'],answer+'\n')
            self.assertEqual(code,130);self.assertIn('cancelled',err);self.assertEqual(self.tree(),before)
        code,_,err=self.run_tty(['theme','save'],'bad\nYES\n');self.assertEqual(code,0);self.assertIn('Use y/yes',err)
    def test_save_as_and_collision(self):
        self.prepare();self.theme('work','old=1\n')
        code,_,_=self.run_tty(['theme','save'],'AS\n../bad\nwork\ny\n')
        self.assertEqual(code,0);self.assertEqual((self.store/'themes/work.toml').read_text(),'x=2\n')
    def test_changed_destination_never_guessed(self):
        self.prepare();self.theme('purple','external=1\n')
        before=self.tree();code,_,err=self.run_tty(['theme','save'],'\n')
        self.assertEqual(code,130);self.assertIn('No unchanged',err);self.assertEqual(self.tree(),before)
    def test_concurrent_active_and_destination_changes(self):
        for destination in (False,True):
            self.prepare()
            def change():
                p=self.store/'themes/purple.toml' if destination else self.config
                p.write_text('external=9\n')
            code,_,_=self.run_tty(['theme','save'],'y\n',change)
            self.assertEqual(code,1)
            self.assertEqual((self.store/'themes/purple.toml' if destination else self.config).read_text(),'external=9\n')
    def test_noninteractive_requires_name(self):
        self.invoke('theme','save',code=2)
    def test_tracking_changed_during_confirmation_is_not_overwritten(self):
        import json
        self.prepare();p=next((self.store/'state/provenance').glob('*.json'))
        def change():
            doc=json.loads(p.read_text());doc['last_loaded']={'kind':'unknown'};p.write_text(json.dumps(doc))
        stored=(self.store/'themes/purple.toml').read_bytes()
        code,_,err=self.run_tty(['theme','save'],'y\n',change)
        self.assertEqual(code,1);self.assertIn('Tracking changed',err)
        self.assertEqual((self.store/'themes/purple.toml').read_bytes(),stored)
        self.assertEqual(json.loads(p.read_text())['last_loaded']['kind'],'unknown')

import json
from unittest.mock import patch
from release_support import ReleaseHarness,core

class BackupDelete(ReleaseHarness):
    def backup(self):
        self.write(self.config,'x=1\n')
        return json.loads(self.invoke('backup','create','--json').stdout)['backup']
    def test_explicit_multiple_and_noninteractive_authorization(self):
        a,b=self.backup(),self.backup();before=self.tree()
        self.invoke('backup','delete',a,b,code=2);self.assertEqual(self.tree(),before)
        result=self.invoke('backup','delete',a,b,'YES','--json')
        self.assertEqual(json.loads(result.stdout)['count'],2);self.assertEqual(self.config.read_text(),'x=1\n')
    def test_alias_escaping_and_modes(self):
        ident=self.backup()
        for literal in ('all','y','yes'):
            p=self.store/'backups';meta=json.loads((p/(ident+'.json')).read_text());meta['id']=literal
            (p/(literal+'.json')).write_text(json.dumps(meta));(p/(literal+'.toml')).write_text('x=1\n')
        self.invoke('backup','delete','--yes','--','all','y','yes')
        self.assertTrue((self.store/'backups'/(ident+'.toml')).exists())
        for args in ([],['yes'],['all',ident],[ident,'--all'],['--pick','--all']):
            self.invoke('backup','delete',*args,code=2)
    def test_all_freezes_selection_before_confirmation(self):
        ident=self.backup();created=[]
        def new_backup():
            if not created:created.append(self.backup())
        code,_,_=self.run_tty(['backup','delete','all'],'y\n',new_backup)
        self.assertEqual(code,0);self.assertFalse((self.store/'backups'/(ident+'.json')).exists())
        self.assertTrue((self.store/'backups'/(created[0]+'.json')).exists())
    def test_negative_empty_and_malformed_preserve_files(self):
        ident=self.backup()
        for answer in ('','NO','\x1b'):
            before=self.tree();code,_,_=self.run_tty(['backup','delete',ident],answer+'\n')
            self.assertEqual(code,130);self.assertEqual(self.tree(),before)
        p=self.store/'backups'/(ident+'.json');p.write_text('[]');before=self.tree()
        self.invoke('backup','delete','--all','--yes',code=1);self.assertEqual(self.tree(),before)
    def test_link_and_active_alias_refused(self):
        ident=self.backup();p=self.store/'backups'/(ident+'.toml');p.unlink();p.symlink_to(self.config)
        before=self.tree();self.invoke('backup','delete',ident,'--yes',code=1);self.assertEqual(self.tree(),before)
    def test_partial_failure_preserves_failed_metadata(self):
        a,b=self.backup(),self.backup();original=core.Path.unlink
        def fail(p,*args,**kwargs):
            if p.name==b+'.toml':raise OSError('injected unlink failure')
            return original(p,*args,**kwargs)
        with patch.object(core.Path,'unlink',fail):code,_,err=self.run_tty(['backup','delete',a,b,'--yes'])
        self.assertEqual(code,1);self.assertIn('Partial',err)
        self.assertFalse((self.store/'backups'/(a+'.json')).exists());self.assertTrue((self.store/'backups'/(b+'.json')).exists())
    def test_missing_payload_cleanup_and_missing_metadata_refusal(self):
        ident=self.backup();(self.store/'backups'/(ident+'.toml')).unlink()
        self.invoke('backup','delete',ident,'--yes')
        ident=self.backup();(self.store/'backups'/(ident+'.json')).unlink()
        self.invoke('backup','delete',ident,'--yes',code=1)
    def test_picker_multi_cancel_and_missing_tool(self):
        a,b=self.backup(),self.backup();before=self.tree()
        code,_,err=self.run_tty(['backup','delete','--pick'])
        self.assertEqual(code,3);self.assertIn('fzf',err);self.assertEqual(self.tree(),before)
        ui=core.ui_module('picker_ui');backups=core.ui_module('backups')
        loader=core.ui_module
        with patch.object(core,'ui_module',side_effect=lambda name:ui if name=='picker_ui' else loader(name)), patch.object(backups.shutil,'which',return_value='/fixture/fzf'):
            with patch.object(ui,'choose_fzf',return_value=[]) as choose:
                code,_,_=self.run_tty(['backup','delete','--pick'])
                self.assertEqual(code,130);self.assertEqual(self.tree(),before)
                self.assertTrue(choose.call_args.kwargs['multi'])
            with patch.object(ui,'choose_fzf',return_value=['backup:'+a,'backup:'+b]):
                code,_,_=self.run_tty(['backup','delete','--pick'],'YES\n')
                self.assertEqual(code,0)
        self.assertFalse(list((self.store/'backups').glob('*.json')))
    def test_changed_backup_during_confirmation_aborts_whole_set(self):
        a,b=self.backup(),self.backup()
        def change(): (self.store/'backups'/(b+'.toml')).write_text('x=9\n')
        code,_,_=self.run_tty(['backup','delete',a,b],'yes\n',change)
        self.assertEqual(code,1)
        for ident in (a,b):self.assertTrue((self.store/'backups'/(ident+'.json')).exists())
    def test_active_file_identity_alias_is_never_deleted(self):
        # Termux Python lacks os.link: simulate only the identity comparison.
        ident=self.backup();before=self.tree()
        original=core.Path.samefile
        def samefile(p,other):
            return True if str(other).endswith(ident+'.toml') else original(p,other)
        with patch.object(core.Path,'samefile',samefile):
            code,_,_=self.run_tty(['backup','delete',ident,'--yes'])
        self.assertEqual(code,1);self.assertEqual(self.tree(),before)

#!/usr/bin/env python3
"""Stash/edit acceptance in isolated catalogs, homes and installation state."""
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_installation as fixtures

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'lib/dots/files'))
import mappings
from catalog import Catalog, platform
from install import Installation
from transactions import Store, digest


class Mappings(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.InstallationTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.repo, self.home, self.source, self.target = self.f.repo, self.f.home, self.f.source, self.f.target
        self.env = self.f.env
        self.env['DOTS_PROGRESS'] = 'never'
        self.patch = patch.dict(os.environ, self.env)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def cli(self, *args, code=0, **env):
        proc = subprocess.run([sys.executable,'-B',str(ROOT/'lib/dots/files/mappings.py'),*map(str,args)],
                              env=dict(self.env, **env), capture_output=True, text=True)
        self.assertEqual(proc.returncode,code,proc.stderr+'\n'+proc.stdout)
        return proc

    def doc(self):
        return json.loads((self.repo/'.dots/files.json').read_text())

    def save(self, doc):
        (self.repo/'.dots/files.json').write_text(json.dumps(doc))

    def link(self):
        self.target.parent.mkdir(parents=True,exist_ok=True)
        self.target.symlink_to(self.source)

    def test_stash_restore_and_idempotence(self):
        self.link()
        first=json.loads(self.cli('stash','dots:example','--yes','--json').stdout)
        self.assertFalse(self.target.is_symlink())
        self.assertTrue(self.source.exists())
        self.assertFalse(self.doc()['resources'][0]['enabled'])
        self.assertEqual(Catalog(self.repo,platform()).records()[0]['status'],'stashed')
        self.assertEqual(json.loads(self.cli('stash','dots:example','--yes','--json').stdout)['status'],'unchanged')
        self.cli('stash','dots:example','--restore','--yes')
        self.assertTrue(self.target.is_symlink())
        self.assertTrue(self.doc()['resources'][0]['enabled'])
        self.assertTrue(first['transaction'])

    def test_installation_skips_disabled_and_baseline_survives(self):
        self.target.parent.mkdir(parents=True)
        self.target.write_text('original installation baseline')
        self.f.cli('install','--yes')
        original=self.f.receipt()['entries'][str(self.target)].copy()
        self.cli('stash','dots:example','--yes')
        suspended=self.f.receipt()['entries'][str(self.target)]
        self.assertIsNone(suspended['after'])
        for field in ('before','backup','index'):
            self.assertEqual(suspended[field],original[field])
        self.f.cli('install','--yes')
        self.assertFalse(self.target.exists())
        self.cli('stash','dots:example','--restore','--yes')
        self.f.cli('uninstall','--yes')
        self.assertEqual(self.target.read_text(),'original installation baseline')

    def test_restore_unmanaged_occupied_target_needs_backup(self):
        self.cli('stash','dots:example','--yes')
        self.target.parent.mkdir(parents=True)
        self.target.write_text('keep local')
        self.cli('stash','dots:example','--restore','--yes',code=1)
        self.assertFalse(self.doc()['resources'][0]['enabled'])
        self.cli('stash','dots:example','--restore','--backup','--yes')
        self.assertTrue(self.target.is_symlink())

    def test_unrelated_and_broken_links(self):
        self.link(); self.source.unlink()
        self.cli('stash','dots:example','--yes')
        self.assertFalse(self.target.is_symlink())
        self.cli('stash','dots:example','--restore','--yes',code=1)
        self.source.write_text('source restored')
        self.target.symlink_to('unrelated missing')
        self.cli('stash','dots:example','--yes')
        self.assertEqual(os.readlink(self.target),'unrelated missing')
        self.cli('stash','dots:example','--restore','--backup','--yes',code=1)

    def test_metadata_edit_preserves_live_link_and_extra_fields(self):
        self.link()
        doc=self.doc();doc['resources'][0].update(custom='keep',targets={'windows':'${APPDATA}/example'})
        self.save(doc)
        self.cli('edit','dots:example','--target',str(self.home/'.config/new place'),'--yes')
        row=self.doc()['resources'][0]
        self.assertEqual(row['target'],'${CONFIG}/new place')
        self.assertEqual(row['targets'],doc['resources'][0]['targets'])
        self.assertEqual(row['custom'],'keep')
        self.assertTrue(self.target.is_symlink())
        self.assertFalse((self.home/'.config/new place').exists())
        self.assertFalse((self.home/'.state/dots/installation.json').exists())

    def test_edit_apply_moves_target_and_undo(self):
        self.link()
        out=json.loads(self.cli('edit','dots:example','--target','${CONFIG}/new place','--apply','--yes','--json').stdout)
        new=self.home/'.config/new place'
        self.assertTrue(new.is_symlink())
        self.assertFalse(self.target.is_symlink())
        store=Store(self.home/'.state/dots')
        ops,guards,catalogs=store.inverse(out['transaction'])
        store.apply('undo',ops,guards,catalogs=catalogs)
        self.assertTrue(self.target.is_symlink())
        self.assertFalse(new.is_symlink())
        self.assertEqual(self.doc()['resources'][0]['target'],'${CONFIG}/example/settings')

    def test_retarget_owned_preserves_old_and_new_baselines(self):
        self.target.parent.mkdir(parents=True)
        self.target.write_text('old location baseline')
        self.f.cli('install','--yes')
        new=self.home/'.config/new';new.write_text('new location baseline')
        self.cli('edit','dots:example','--target','${CONFIG}/new','--apply','--backup','--yes')
        self.assertFalse(self.target.exists())
        self.f.cli('install','--yes')
        self.f.cli('uninstall','--yes')
        self.assertEqual(self.target.read_text(),'old location baseline')
        self.assertEqual(new.read_text(),'new location baseline')

    def test_stash_retires_owned_link_after_metadata_only_edit(self):
        self.target.parent.mkdir(parents=True)
        self.target.write_text('original')
        self.f.cli('install','--yes')
        self.cli('edit','dots:example','--target','${CONFIG}/later','--yes')
        self.assertTrue(self.target.is_symlink())
        self.cli('stash','dots:example','--yes')
        self.assertFalse(self.target.exists())
        self.f.cli('uninstall','--yes')
        self.assertEqual(self.target.read_text(),'original')

    def test_historical_link_reassigned_to_other_resource_is_protected(self):
        self.f.cli('install','--yes')
        old=self.doc()['resources'][0].copy()
        self.cli('edit','dots:example','--target','${CONFIG}/later','--yes')
        doc=self.doc();doc['resources'].append(dict(old,id='other'));self.save(doc)
        self.cli('stash','dots:example','--yes',code=1)
        self.cli('edit','dots:example','--apply','--yes',code=1)
        self.assertTrue(self.target.is_symlink())

    def test_same_target_new_source_and_disabled_edit(self):
        self.link()
        other=self.source.with_name('other');other.write_text('other')
        self.cli('edit','dots:example','--source','config/example/other','--apply','--yes')
        self.assertEqual(self.target.resolve(),other)
        self.cli('stash','dots:example','--yes')
        self.cli('edit','dots:example','--target','${CONFIG}/another','--yes')
        self.assertFalse(self.doc()['resources'][0]['enabled'])
        self.cli('edit','dots:example','--apply','--yes',code=1)

    def test_new_directory_mapping(self):
        args=['edit','--new','--repo','dots','--id','directory','--app','example','--category','config',
              '--source','config/example','--target','${CONFIG}/directory','--strategy','directory-link']
        self.cli(*args,'--dry-run')
        self.assertEqual(len(self.doc()['resources']),1)
        self.cli(*args,'--apply','--yes')
        self.assertEqual((self.home/'.config/directory').resolve(),self.source.parent)
        self.cli(*args,'--yes',code=1)

    def test_conflicts_exclude_disabled_and_track_retains_enabled(self):
        doc=self.doc();doc['resources'].append(dict(doc['resources'][0],id='other',enabled=False))
        self.save(doc)
        self.assertNotIn('conflict',[r['status'] for r in Catalog(self.repo,platform()).records()])
        self.cli('stash','dots:other','--restore','--yes',code=1)
        proc=subprocess.run([sys.executable,'-B',str(ROOT/'lib/dots/files/catalog.py'),'track',
                             'config/example/settings','--repo','dots','--id','other','--app','example',
                             '--category','config','--target','${CONFIG}/example/settings','--update'],
                            env=self.env,capture_output=True,text=True)
        self.assertEqual(proc.returncode,0,proc.stderr)
        self.assertFalse(next(r for r in self.doc()['resources'] if r['id']=='other')['enabled'])
        proc=subprocess.run([sys.executable,'-B',str(ROOT/'lib/dots/files/manage.py'),'link','dots:other','--yes'],
                            env=self.env,capture_output=True,text=True)
        self.assertNotEqual(proc.returncode,0)
        self.assertIn('stashed',proc.stderr)

    def test_disabled_replacement_does_not_hide_active(self):
        doc=self.doc();doc['resources'].append(dict(doc['resources'][0],id='other',enabled=False,replaces=['dots:example']))
        self.save(doc)
        self.assertNotEqual(Catalog(self.repo,platform()).records()[0]['status'],'replaced')
        doc['resources'][0]['enabled']='false';self.save(doc)
        self.cli('stash','dots:example','--yes',code=1)

    def test_restore_validates_other_platform_claims(self):
        doc=self.doc();doc['resources'][0]['enabled']=False
        doc['resources'].append(dict(doc['resources'][0],id='windows',enabled=True,platforms=['windows']))
        self.save(doc)
        self.cli('stash','dots:example','--restore','--yes',code=1)
        self.assertFalse(self.doc()['resources'][0]['enabled'])

    def test_filters_platform_and_inactive_live_apply(self):
        self.cli('edit','dots:example','--platform','windows','--target','${APPDATA}/specific','--yes')
        self.assertEqual(self.doc()['resources'][0]['targets']['windows'],'${APPDATA}/specific')
        if platform() != 'windows':
            self.cli('edit','dots:example','--platform','windows','--target','${APPDATA}/specific','--apply','--yes',code=1)

    def test_dry_run_json_noninteractive_and_idempotence(self):
        before=self.doc()
        out=self.cli('stash','dots:example','--dry-run','--yes','--json',DOTS_COLOR='always',DOTS_ICONS='always').stdout
        self.assertNotIn('\x1b',out);json.loads(out)
        self.assertEqual(self.doc(),before)
        self.assertFalse((self.home/'.state').exists())
        self.cli('stash','dots:example',code=2)
        self.cli('stash','--yes',code=2)
        self.cli('edit','--json',code=2)
        self.assertEqual(json.loads(self.cli('edit','dots:example','--target',before['resources'][0]['target'],'--yes','--json').stdout)['status'],'unchanged')

    def test_source_catalog_and_receipt_drift(self):
        self.link()
        plan=mappings.MappingPlan();plan.stash(['dots:example']);plan.finish()
        self.source.write_text('changed')
        with self.assertRaisesRegex(ValueError,'changed after preview'):plan.apply('stash')
        plan=mappings.MappingPlan();plan.stash(['dots:example']);plan.finish()
        doc=self.doc();doc['custom']='drift';self.save(doc)
        with self.assertRaisesRegex(ValueError,'changed after preview'):plan.apply('stash')
        self.f.cli('install','--yes')
        # A pre-existing matching link isn't owned; explicitly own a fresh one.
        self.target.unlink();self.f.cli('install','--yes')
        self.target.unlink();self.target.write_text('drift')
        self.cli('stash','dots:example','--yes',code=1)
        self.assertTrue(self.doc()['resources'][0].get('enabled',True))

    def test_rollback_after_link_removal(self):
        self.link()
        plan=mappings.MappingPlan();plan.stash(['dots:example']);plan.finish()
        import transactions
        rename=transactions.os.rename
        calls=0
        def fail(a,b):
            nonlocal calls
            calls+=1
            if calls==2:raise OSError('fixture failure')
            return rename(a,b)
        with patch.object(transactions.os,'rename',fail):
            with self.assertRaises(OSError):plan.apply('stash')
        self.assertTrue(self.target.is_symlink())
        self.assertTrue(self.doc()['resources'][0].get('enabled',True))
        self.assertEqual(plan.install.store.records()[0]['status'],'rolled-back')

    def test_abrupt_exit_recovery(self):
        self.link()
        script='''import sys,os
sys.path.insert(0,sys.argv[1])
import mappings,transactions
p=mappings.MappingPlan();p.stash(['dots:example']);p.finish()
original=transactions.os.rename
def crash(a,b):
 original(a,b)
 os._exit(77)
transactions.os.rename=crash
p.apply('stash')
'''
        proc=subprocess.run([sys.executable,'-B','-c',script,str(ROOT/'lib/dots/files')],env=self.env)
        self.assertEqual(proc.returncode,77)
        store=Store(self.home/'.state/dots');record=store.records()[0]
        store.recover(record['id'])
        self.assertTrue(self.target.is_symlink())
        self.assertTrue(self.doc()['resources'][0].get('enabled',True))

    def test_interactive_cancel_and_plain_picker_without_bash(self):
        self.link()
        with patch.object(mappings,'terminal',return_value=True),patch.object(mappings,'gum_confirm',return_value=False):
            with redirect_stdout(io.StringIO()):mappings.main(['stash','dots:example'])
        self.assertTrue(self.target.is_symlink())
        self.assertFalse((self.home/'.state').exists())
        with patch.object(mappings,'terminal',return_value=True),patch('interaction.terminal',return_value=True),patch('interaction.shutil.which',return_value=None),patch('builtins.input',return_value='2'):
            with redirect_stdout(io.StringIO()):self.assertEqual(mappings.pick('Test',['Cancel','choice']),'choice')

    def test_source_ownership_and_symlink_parent_refused(self):
        alias=self.repo/'alias';alias.symlink_to(self.source.parent,target_is_directory=True)
        self.cli('edit','dots:example','--source','alias/settings','--yes',code=1)
        self.cli('edit','dots:example','--source','../escape','--yes',code=1)
        self.cli('edit','dots:example','--target','/outside-supported-roots/example','--yes',code=1)

    def test_stash_never_unlinks_source_or_another_claim(self):
        self.link()
        doc=self.doc();doc['resources'].append(dict(doc['resources'][0],id='other'))
        self.save(doc)
        self.cli('stash','dots:example','--yes',code=1)
        self.assertTrue(self.target.is_symlink())
        # A catalog that points its target at its own source must fail closed.
        doc['resources']=doc['resources'][:1]
        doc['resources'][0]['target']='${HOME}/../checkout/config/example/settings'
        self.save(doc)
        self.cli('stash','dots:example','--yes',code=1)
        self.assertTrue(self.source.is_file())

    @unittest.skipIf(os.name=='nt','POSIX owned terminal')
    def test_owned_terminal_presentation_and_cancel(self):
        import fcntl
        import pty
        import re
        import struct
        import termios
        from resources import cells
        script='''import sys,time
sys.path.insert(0,sys.argv[1])
import mappings
original=mappings.MappingPlan.stash
def slow(self,*a,**kw):
 time.sleep(.65)
 return original(self,*a,**kw)
mappings.MappingPlan.stash=slow
mappings.gum_confirm=lambda *a,**kw:None
raise SystemExit(mappings.main(sys.argv[2:]))
'''
        for width in (40,80,120):
            for dry in (True,False):
                master,slave=pty.openpty()
                try:
                    fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',24,width,0,0))
                    proc=subprocess.Popen([sys.executable,'-B','-c',script,str(ROOT/'lib/dots/files'),'stash','dots:example',*(['--dry-run'] if dry else [])],
                                          stdin=slave,stdout=slave,stderr=slave,
                                          env=dict(self.env,COLUMNS=str(width),TERM='xterm-256color',DOTS_COLOR='always' if dry else 'never',DOTS_ICONS='never',DOTS_PROGRESS='auto'))
                    os.close(slave);slave=None
                    if not dry:os.write(master,b'n\n')
                    chunks=[]
                    while True:
                        try:block=os.read(master,65536)
                        except OSError:break
                        if not block:break
                        chunks.append(block)
                    self.assertEqual(proc.wait(timeout=5),0)
                    text=b''.join(chunks).decode()
                    plain=re.sub(r'\x1b\[[0-9;]*m','',text)
                    for frame in plain.replace('\r\n','\n').replace('\r','\n').splitlines():
                        self.assertLessEqual(cells(frame),width,repr(frame))
                    if dry:
                        self.assertNotIn('\r',text.replace('\r\n','\n'))
                    else:
                        self.assertIn('cancelled',plain)
                        self.assertIn('\r',text.replace('\r\n','\n'))
                        self.assertNotIn('\x1b[',text)
                    self.assertFalse((self.home/'.state').exists())
                finally:
                    os.close(master)
                    if slave is not None:os.close(slave)


@unittest.skipIf(os.name=='nt','Termux migration')
class GitMigration(unittest.TestCase):
    def setUp(self):
        Mappings.setUp(self)
        env=patch.dict(os.environ,TERMUX_VERSION='fixture',PREFIX='/fixture/usr')
        env.start();self.addCleanup(env.stop)
        self.common=self.repo/'config/git'
        self.common.mkdir()
        (self.common/'gitconfig').write_text('[fixture]\n common = yes\n[include]\n path = aliases\n')
        (self.common/'aliases').write_text('[fixture]\n aliases = yes\n')
        (self.common/'config').write_text('[include]\n  path = gitconfig\n  path = ~/.config/git-termux/config\n')
        (self.common/'termux').write_text('[fixture]\n android = yes\n[credential]\n helper = !false\n')
        self.android=self.repo/'androidots'
        (self.android/'.dots').mkdir(parents=True)
        (self.android/'config/git').mkdir(parents=True)
        self.android_source=self.android/'config/git/gitconfig'
        self.old='[include]\n  path = ~/repos/dots/config/git/gitconfig\n[fixture]\n android = yes\n[credential]\n helper = !false\n'
        self.android_source.write_text(self.old)
        self.android_source.chmod(0o600)
        sources=json.loads((self.repo/'.dots/sources.json').read_text())
        sources['sources'].append(dict(id='androidots',path='androidots',roots=['config'],platforms=['termux']))
        self.f.write('.dots/sources.json',sources)
        row=dict(id='git',source='config/git',target='${CONFIG}/git',strategy='directory-link',app='git',category='config',platforms=['termux','linux','wsl'])
        self.f.write('.dots/files.json',dict(schema=1,repository='dots',resources=[row]))
        (self.android/'.dots/files.json').write_text(json.dumps(dict(schema=1,repository='androidots',resources=[dict(row,source='config/git/gitconfig',target='${HOME}/.gitconfig',strategy='link',platforms=['termux'])])))
        (self.android/'.dots/file-locations.json').write_text(json.dumps(dict(schema=1,repository='androidots',locations=[dict(id='git',kind='file',source='config/git/gitconfig',target='${HOME}/.gitconfig',platforms=['termux'])])))
        (self.home/'.gitconfig').symlink_to(self.android_source)

    def test_migration_loading_idempotence_and_undo(self):
        import migrate_git_config as migration
        plan=migration.migration_plan()
        self.assertFalse((self.home/'.state').exists())
        self.assertEqual(self.android_source.read_text(),self.old)
        result=plan.apply('git-config-migration')
        self.assertFalse((self.home/'.gitconfig').is_symlink())
        self.assertEqual((self.home/'.config/git').resolve(),self.common)
        self.assertFalse((self.home/'.config/git-termux/config').is_symlink())
        self.assertEqual((self.common/'gitplatform').readlink(),Path('termux'))
        self.assertFalse(any(r['id']=='git' for r in json.loads((self.android/'.dots/files.json').read_text())['resources']))
        self.assertEqual(json.loads((self.android/'.dots/file-locations.json').read_text())['locations'],[])
        env=dict(self.env)
        for key in list(env):
            if key.startswith('GIT_CONFIG'):del env[key]
        env['GIT_CONFIG_NOSYSTEM']='1'
        for key in ('common','aliases','android'):
            proc=subprocess.run(['git','config','--global','--includes','--get','fixture.'+key],env=env,cwd=self.home,capture_output=True,text=True)
            self.assertEqual(proc.returncode,0,proc.stderr)
            self.assertEqual(proc.stdout.strip(),'yes')
        self.assertEqual(self.android_source.read_text(),self.old)
        self.assertEqual(self.android_source.stat().st_mode & 0o777,0o600)
        expected=migration.settings('--file',str(self.common/'gitconfig'),'--includes')
        expected+=migration.settings('--file',str(self.common/'termux'),'--no-includes')
        self.assertEqual(migration.settings('--global','--includes'),expected)
        self.assertEqual(migration.migration_plan().apply('git-config-migration')['status'],'unchanged')
        store=Store(self.home/'.state/dots');ops,guards,catalogs=store.inverse(result['id'])
        store.apply('undo',ops,guards,catalogs=catalogs)
        self.assertTrue((self.home/'.gitconfig').is_symlink())
        self.assertEqual(self.android_source.read_text(),self.old)
        self.assertEqual((self.common/'config').read_text(),migration.OLD_ENTRY)
        self.assertEqual(json.loads((self.android/'.dots/file-locations.json').read_text())['locations'][0]['id'],'git')

    def test_unrelated_old_link_refuses_complete_plan(self):
        import migrate_git_config as migration
        (self.home/'.gitconfig').unlink()
        (self.home/'.gitconfig').symlink_to('other-config')
        with self.assertRaisesRegex(ValueError,'old target'):
            migration.migration_plan()
        self.assertEqual(self.android_source.read_text(),self.old)
        self.assertEqual((self.common/'config').read_text(),migration.OLD_ENTRY)

    def test_consolidated_layout_retires_owned_dangling_overlay(self):
        import migrate_git_config as migration
        (self.home/'.gitconfig').unlink()
        legacy=self.home/'.config/git-termux/config';legacy.parent.mkdir(parents=True)
        legacy.symlink_to(self.android_source)
        self.android_source.unlink()
        (self.common/'config').write_text(migration.ENTRY)
        (self.common/'gitplatform').symlink_to('termux')
        state=self.home/'.state/dots';state.mkdir(parents=True)
        receipt=dict(schema=1,root=str(self.repo),platform='termux',transactions=[],entries={str(legacy):dict(id='androidots:git',before=None,after=digest(legacy),backup='unused',index=0)})
        (state/'installation.json').write_text(json.dumps(receipt))
        plan=migration.migration_plan();result=plan.apply('git-config-migration')
        self.assertFalse(legacy.is_symlink())
        current=json.loads((state/'installation.json').read_text())
        self.assertIsNone(current['entries'][str(legacy)]['after'])
        self.assertTrue((self.common/'gitplatform').is_symlink())
        self.assertEqual(migration.migration_plan().apply('git-config-migration')['status'],'unchanged')
        ops,guards,catalogs=plan.install.store.inverse(result['id'])
        plan.install.store.apply('undo',ops,guards,retain=True,catalogs=catalogs)
        self.assertTrue(legacy.is_symlink())
        self.assertFalse(self.android_source.exists())

    def test_retired_catalog_does_not_reappear(self):
        import migrate_git_config as migration
        plan=migration.migration_plan();plan.apply('git-config-migration')
        self.assertFalse(any(r['id']=='androidots:git' for r in Catalog(self.repo,'termux').records()))
        install=Installation(self.repo);install.plan_install()
        self.assertFalse(any('git-termux' in op['path'] or op['path']==str(self.home/'.gitconfig') for op in install.operations))

    def test_failed_global_verification_undoes_migration(self):
        import migrate_git_config as migration
        with patch.object(sys,'argv',['migrate_git_config.py','--apply','--yes']):
            with patch.object(migration,'settings',side_effect=[[],[],[b'fixture.bad\nyes']]):
                with redirect_stdout(io.StringIO()):
                    with self.assertRaisesRegex(ValueError,'was undone'):migration.main()
        self.assertTrue((self.home/'.gitconfig').is_symlink())
        self.assertEqual(self.android_source.read_text(),self.old)
        self.assertEqual((self.common/'config').read_text(),migration.OLD_ENTRY)


if __name__ == '__main__':
    unittest.main()

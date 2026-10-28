#!/usr/bin/env python3
"""Application migration uses only synthetic legacy installations and homes."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_bundled_apps as fixtures
from test_installation import Installation
from app_migration import Migration
from transactions import digest, Store


@unittest.skipIf(os.name == 'nt', 'POSIX legacy receipt layouts; native plugin setup tested separately')
class MigrationTests(unittest.TestCase):
    setUp = fixtures.BundledApps.setUp
    write = fixtures.BundledApps.write
    cli = fixtures.BundledApps.cli
    receipt = fixtures.BundledApps.receipt
    call = fixtures.BundledApps.call

    def put(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def legacy(self):
        prefix = self.home/'.local'
        root = prefix/'lib/pkgs'
        files = {'pkgs': 'legacy launcher\n', 'VERSION': '0.1.1\n', 'docs/pkgs.1': 'legacy manual\n'}
        sums = ''
        for name, text in files.items():
            self.put(root/name, text)
            sums += hashlib.sha256(text.encode()).hexdigest()+'  '+name+'\n'
        self.put(root/'SHA256SUMS', sums)
        self.put(self.repo/'plugins/pkgs/SHA256SUMS', sums)
        self.put(root/'install.json', json.dumps(dict(marker='pkgs-user-install-v1', version='0.1.1', shells=[])))
        for link, target in ((prefix/'bin/pkgs', root/'pkgs'), (prefix/'share/man/man1/pkgs.1', root/'docs/pkgs.1')):
            link.parent.mkdir(parents=True, exist_ok=True);link.symlink_to(target)
        broot = prefix/'share/blastoff'
        targets = {prefix/'bin/blastoff': 'legacy Blastoff\n', broot/'versions/0.1.12/lib/core.py': 'legacy core\n'}
        for path, text in targets.items(): self.put(path, text)
        self.put(broot/'install.json', json.dumps(dict(format=2, version='0.1.12', backups={},
                 files={str(p): hashlib.sha256(t.encode()).hexdigest() for p,t in targets.items()})))
        return root, broot

    def plan(self):
        installation = Installation(self.repo)
        migration = Migration(installation)
        # The fixture never inspects the machine's prefix or /usr/local.
        migration.prefixes = [self.home/'.local']
        migration.plan()
        return installation

    def test_preview_apply_repeat_and_restore_exact_baseline(self):
        root, broot = self.legacy()
        data = self.put(self.home/'.config/blastoff/themes/personal.toml', 'personal data\n')
        before = {p: digest(p) for p in (root, broot, self.home/'.local/bin/pkgs', self.home/'.local/bin/blastoff', data)}
        with patch.dict(os.environ, self.env, clear=True):
            installation = self.plan()
            self.assertFalse(installation.blocked, installation.items)
            self.assertEqual(before, {p: digest(p) for p in before})
            installation.apply('migrate-apps')
            self.assertFalse(root.exists());self.assertFalse(broot.exists())
            self.assertFalse(self.target.exists())
            for app in ('anodize','blastoff','pkgs'):
                self.assertEqual((self.home/'.local/bin'/app).resolve(), self.repo/'bin'/app)
            self.assertEqual(self.plan().apply('migrate-apps')['status'], 'unchanged')
            uninstall=Installation(self.repo);uninstall.plan_uninstall();uninstall.apply('uninstall')
            self.assertEqual(before, {p: digest(p) for p in before})

    def test_changed_and_forged_receipts_block_without_writes(self):
        root,broot=self.legacy()
        receipt=broot/'install.json'; original=receipt.read_text()
        outside=self.put(self.home/'unrelated', 'private data')
        forged=json.loads(original);forged['files'][str(outside)]=hashlib.sha256(outside.read_bytes()).hexdigest()
        receipt.write_text(json.dumps(forged))
        with patch.dict(os.environ,self.env,clear=True):
            p=self.plan();self.assertTrue(p.blocked)
            with self.assertRaisesRegex(ValueError,'conflicts'):p.apply('migrate-apps')
        self.assertEqual(outside.read_text(),'private data')
        receipt.write_text(original);(root/'pkgs').write_text('edited launcher')
        with patch.dict(os.environ,self.env,clear=True):
            self.assertTrue(self.plan().blocked)
        self.assertTrue((self.home/'.local/bin/pkgs').is_symlink())

    def test_unknown_payload_and_recovery_files_are_retained(self):
        root,broot=self.legacy()
        unknown=self.put(root/'notes.txt','keep me')
        recovery=self.put(self.home/'.config/.blastoff-edit-fixture/active.toml','unsaved edits')
        with patch.dict(os.environ,self.env,clear=True):
            p=self.plan();self.assertFalse(p.blocked,p.items);p.apply('migrate-apps')
        self.assertEqual(unknown.read_text(),'keep me');self.assertEqual(recovery.read_text(),'unsaved edits')

    def test_changed_after_preview_and_uninstall_drift(self):
        root,broot=self.legacy()
        with patch.dict(os.environ,self.env,clear=True):
            p=self.plan();(root/'VERSION').write_text('edited')
            with self.assertRaisesRegex(ValueError,'changed after preview'):p.apply('migrate-apps')
            (root/'VERSION').write_text('0.1.1\n');self.plan().apply('migrate-apps')
            launcher=self.home/'.local/bin/pkgs';launcher.unlink();launcher.write_text('new user launcher')
            p=Installation(self.repo);p.plan_uninstall();p.apply('uninstall')
        self.assertEqual(launcher.read_text(),'new user launcher')

    def test_failure_after_retirement_rolls_back(self):
        root,broot=self.legacy();before=digest(self.home/'.local')
        with patch.dict(os.environ,self.env,clear=True):
            p=self.plan();save=p.store.save; failed=False
            def fault(record):
                nonlocal failed
                save(record)
                if not failed and record['status']=='applying' and any(
                        item['path']==str(broot) and item['phase']=='done' for item in record['operations']):
                    failed=True;raise OSError('retirement fault')
            with patch.object(p.store,'save',side_effect=fault):
                with self.assertRaisesRegex(OSError,'retirement fault'):p.apply('migrate-apps')
        self.assertTrue(failed);self.assertEqual(digest(self.home/'.local'),before)

    def test_completion_overlap_retires_only_obsolete_claim(self):
        self.legacy()
        fish=self.home/'.config/fish/completions/pkgs.fish';fish.parent.mkdir(parents=True)
        fish.symlink_to(self.repo/'plugins/pkgs/completions/pkgs.fish')
        bash=self.put(self.home/'.data/bash-completion/completions/pkgs',
                      (self.repo/'plugins/pkgs/completions/pkgs.bash').read_text())
        state=self.put(self.home/'.state/pkgs/completions.json',json.dumps(dict(format=1,shells={
            'fish':dict(file=str(fish),hash='stale'),
            'bash':dict(file=str(bash),hash=hashlib.sha256(bash.read_bytes()).hexdigest())})))
        with patch.dict(os.environ,self.env,clear=True):
            p=self.plan();self.assertFalse(p.blocked,p.items);p.apply('migrate-apps')
        self.assertTrue(fish.is_symlink());self.assertTrue(bash.is_symlink());self.assertFalse(state.exists())

    def test_process_death_after_retirement_recovers_before_retry(self):
        root,broot=self.legacy();before=digest(self.home/'.local')
        program = '''import os,sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from install import Installation
from app_migration import Migration
p=Installation(Path(sys.argv[2]));m=Migration(p);m.prefixes=[Path.home()/'.local'];m.plan()
save=p.store.save
def crash(doc):
    save(doc)
    if doc['status']=='applying' and any(x['path']==sys.argv[3] and x['phase']=='done' for x in doc['operations']): os._exit(42)
p.store.save=crash
p.apply('migrate-apps')
'''
        result=subprocess.run([sys.executable,'-B','-c',program,str(fixtures.ROOT/'lib/dots/files'),str(self.repo),str(broot)],env=self.env,capture_output=True)
        self.assertEqual(result.returncode,42,result.stderr)
        with patch.dict(os.environ,self.env,clear=True):
            with self.assertRaisesRegex(ValueError,'unfinished transaction'):self.plan()
            store=Store(self.home/'.state/dots');record=store.records()[0];store.recover(record['id'])
            self.assertEqual(digest(self.home/'.local'),before)
            self.assertFalse(self.plan().blocked)

    def test_plugin_manifest_rejects_escape_and_native_drive_paths(self):
        manifest=self.repo/'plugins/manifest.json';doc=json.loads(manifest.read_text())
        with patch.dict(os.environ,self.env,clear=True):
            for invalid in ('../outside','/absolute','C:/outside','sub\\outside'):
                doc['plugins']['blastoff']['runtime']=invalid;manifest.write_text(json.dumps(doc))
                with self.assertRaises(ValueError):self.plan()

    def test_custom_legacy_startup_reference_blocks_retirement(self):
        root,_=self.legacy();self.put(self.home/'.bashrc', 'source '+str(root/'integration.sh'))
        with patch.dict(os.environ,self.env,clear=True):
            p=self.plan();self.assertTrue(p.blocked)
            with self.assertRaisesRegex(ValueError,'conflicts'):p.apply('migrate-apps')
        self.assertTrue(root.exists())

    def test_cli_preview_alias_and_dry_run_never_mutate(self):
        before=digest(self.home)
        # Use WSL detection to avoid the actual Termux PREFIX during subprocess tests.
        self.env.update(PREFIX=str(self.base/'isolated-prefix'))
        for route in (['files','migrate-apps'],['files','migrate','apps']):
            for frontend in ([self.repo/'bin/dots'],[sys.executable,'-B',self.repo/'lib/dots/cli.py']):
                for flags in (['--json'],['--yes','--dry-run','--json']):
                    data=json.loads(self.call([*frontend,*route,*flags])[0])
                    self.assertEqual(data['status'],'preview')
        self.assertEqual(before,digest(self.home))


if __name__=='__main__':unittest.main()

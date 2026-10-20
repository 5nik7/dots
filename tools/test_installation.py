#!/usr/bin/env python3
"""Disposable native setup, updater and restore acceptance tests."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from vivid_fixture import install_vivid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'lib/dots/files'))
from install import Installation
from transactions import Store, digest


class InstallationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='dots setup ü ')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.home = self.base/'home'
        self.repo = self.base/'checkout'
        self.home.mkdir()
        for name in ('.dots', 'bin', 'config/example'):
            (self.repo/name).mkdir(parents=True)
        (self.repo/'bin/dots').write_text('#!/bin/sh\nexit 0\n')
        (self.repo/'bin/dots.ps1').write_text('exit 0\n')
        self.source = self.repo/'config/example/settings'
        self.source.write_text('repository settings\n')
        self.target = self.home/'.config/example/settings'
        self.env = dict(os.environ, HOME=str(self.home), USERPROFILE=str(self.home),
                        DOTS=str(self.repo), XDG_CONFIG_HOME=str(self.home/'.config'),
                        XDG_STATE_HOME=str(self.home/'.state'), LOCALAPPDATA=str(self.home/'Local'),
                        APPDATA=str(self.home/'Roaming'), DOTS_COLOR='never', DOTS_ICONS='never',
                        TERM='dumb', PYTHONDONTWRITEBYTECODE='1', GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_CONFIG_NOSYSTEM='1', GIT_TERMINAL_PROMPT='0')
        self.env.update(CODEX_HOME=str(self.home/'.codex'), PI_CODING_AGENT_DIR=str(self.home/'.pi/agent'),
                        XDG_CACHE_HOME=str(self.home/'.cache'), XDG_DATA_HOME=str(self.home/'.data'))
        self.write('.dots/sources.json', {'schema':1,'sources':[dict(id='dots',path='.',roots=['config','bin'],platforms=['termux','linux','wsl','windows'])]})
        self.write('.dots/files.json', {'schema':1,'repository':'dots','resources':[dict(id='example',source='config/example/settings',target='${CONFIG}/example/settings',strategy='link',app='example',category='config',platforms=['termux','linux','wsl','windows'])]})
        # Native Windows positive cases require explicit link capability.
        if os.name == 'nt':
            probe = self.base/'probe'
            try:
                probe.symlink_to(self.source)
                probe.unlink()
            except OSError:
                self.skipTest('native Windows symbolic links unavailable; refusal tested separately')

    def write(self, name, data):
        (self.repo/name).write_text(json.dumps(data))

    def cli(self, *args, ok=True):
        result = subprocess.run([sys.executable,'-B',str(ROOT/'lib/dots/files/install.py'),*args],env=self.env,capture_output=True,text=True)
        if ok:
            self.assertEqual(result.returncode,0,result.stderr+'\n'+result.stdout)
        else:
            self.assertNotEqual(result.returncode,0,result.stdout)
        return result

    def receipt(self):
        return json.loads((self.home/'.state/dots/installation.json').read_text())

    def test_dry_run_and_idempotent_install_restore(self):
        before = list(self.home.rglob('*'))
        plan = json.loads(self.cli('install','--dry-run','--json').stdout)
        self.assertEqual(plan['status'],'preview')
        self.assertEqual(list(self.home.rglob('*')),before)
        self.cli('install','--yes')
        self.assertTrue(self.target.is_symlink())
        first = self.receipt()
        self.assertEqual(json.loads(self.cli('install','--yes','--json').stdout)['status'],'unchanged')
        self.assertEqual(first,self.receipt())
        self.cli('uninstall','--yes')
        self.assertFalse(self.target.exists())
        self.assertFalse((self.home/'.config').exists())
        self.assertTrue(self.source.exists())
        self.assertFalse(self.receipt()['entries'])

    def test_backup_survives_reconciliation(self):
        self.target.parent.mkdir(parents=True)
        self.target.write_text('before installation')
        self.cli('install','--yes')
        first = self.receipt()['entries'][str(self.target)]
        self.source.write_text('updated repository')
        self.cli('install','--yes')
        self.assertEqual(first,self.receipt()['entries'][str(self.target)])
        self.cli('uninstall','--yes')
        self.assertEqual(self.target.read_text(),'before installation')
        self.assertEqual(self.source.read_text(),'updated repository')

    def test_preserves_preexisting_matching_link_and_user_drift(self):
        self.target.parent.mkdir(parents=True)
        self.target.symlink_to(self.source)
        self.cli('install','--yes')
        self.assertNotIn(str(self.target),self.receipt()['entries'])
        self.cli('uninstall','--yes')
        self.assertTrue(self.target.is_symlink())
        self.target.unlink()
        self.cli('install','--yes')
        self.target.unlink()
        self.target.write_text('user replacement')
        result=json.loads(self.cli('uninstall','--yes','--json',ok=False).stdout)
        self.assertEqual(result['status'],'incomplete')
        self.assertEqual(self.target.read_text(),'user replacement')
        self.assertIn(str(self.target),self.receipt()['entries'])

    def test_conflict_blocks_complete_batch(self):
        self.target.parent.mkdir(parents=True)
        self.target.symlink_to(self.home/'missing')
        self.cli('install','--yes',ok=False)
        self.assertFalse((self.home/'.local').exists())
        self.assertFalse((self.home/'.state').exists())

    def test_catalog_drift_after_preview(self):
        with mock.patch.dict(os.environ,self.env,clear=True):
            install=Installation(self.repo)
            install.plan_install()
            self.write('.dots/files.json',dict(schema=1,repository='dots',resources=[]))
            with self.assertRaisesRegex(ValueError,'changed after preview'):
                install.apply('install')
        self.assertFalse(self.target.exists())

    def test_failure_rolls_back_links_and_receipt(self):
        self.target.parent.mkdir(parents=True)
        self.target.write_text('original')
        with mock.patch.dict(os.environ,self.env,clear=True):
            install=Installation(self.repo)
            install.plan_install()
            save=install.store.save
            failed=False
            def fail(doc):
                nonlocal failed
                save(doc)
                if not failed and doc['status']=='applying' and any(e['phase']=='done' for e in doc['operations']):
                    failed=True
                    raise OSError('injected failure')
            with mock.patch.object(install.store,'save',side_effect=fail):
                with self.assertRaisesRegex(OSError,'injected failure'):
                    install.apply('install')
        self.assertEqual(self.target.read_text(),'original')
        self.assertFalse((self.home/'.state/dots/installation.json').exists())

    def test_undo_install_restores_receipt(self):
        result=json.loads(self.cli('install','--yes','--json').stdout)
        store=Store(self.home/'.state/dots')
        ops,guards,catalogs=store.inverse(result['transaction'])
        store.apply('undo',ops,guards,retain=True,catalogs=catalogs)
        self.assertFalse(self.target.exists())
        self.assertFalse((self.home/'.state/dots/installation.json').exists())

    def test_declined_noninteractive_and_bad_options(self):
        self.cli('install',ok=False)
        self.cli('uninstall','--update',ok=False)
        self.assertFalse((self.home/'.state').exists())

    def git(self, root, *args):
        result=subprocess.run(['git','-C',str(root),*args],env=self.env,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        return result.stdout.strip()

    def git_fixture(self):
        shutil.copytree(ROOT/'lib/dots/files',self.repo/'lib/dots/files')
        for name in ('progress.py','interaction.py','resources.py','resources.tsv'):
            shutil.copy2(ROOT/'lib/dots'/name,self.repo/'lib/dots'/name)
        self.git(self.repo,'init','--initial-branch=main')
        self.git(self.repo,'config','user.email','fixture@example.invalid')
        self.git(self.repo,'config','user.name','Fixture')
        self.git(self.repo,'add','.')
        self.git(self.repo,'commit','-m','Initial fixture')
        remote=self.base/'remote.git'
        self.git(self.base,'clone','--bare',str(self.repo),str(remote))
        self.git(self.repo,'remote','add','origin',str(remote))
        self.git(self.repo,'fetch','origin')
        self.git(self.repo,'branch','--set-upstream-to=origin/main')
        author=self.base/'author'
        self.git(self.base,'clone',str(remote),str(author))
        self.git(author,'config','user.email','fixture@example.invalid')
        self.git(author,'config','user.name','Fixture')
        return author

    def test_update_fast_forward_and_original_backup(self):
        author=self.git_fixture()
        self.target.parent.mkdir(parents=True)
        self.target.write_text('pre-install')
        self.cli('install','--yes')
        (author/'config/example/settings').write_text('remote update')
        self.git(author,'add','.')
        self.git(author,'commit','-m','Update fixture')
        self.git(author,'push','origin','HEAD:refs/heads/main')
        oldhead=self.git(self.repo,'rev-parse','HEAD')
        oldfetch=(self.repo/'.git/FETCH_HEAD').read_bytes()
        self.cli('install','--update','--dry-run')
        self.assertEqual(oldfetch,(self.repo/'.git/FETCH_HEAD').read_bytes())
        self.assertEqual(oldhead,self.git(self.repo,'rev-parse','HEAD'))
        result=self.cli('install','--update','--yes','--verbose')
        self.assertIn('Unchanged',result.stderr)  # Survives the updated Python process.
        self.assertEqual(self.target.read_text(),'remote update')
        self.cli('uninstall','--yes')
        self.assertEqual(self.target.read_text(),'pre-install')

    def test_update_dirty_and_diverged_refused(self):
        author=self.git_fixture()
        self.source.write_text('dirty')
        self.cli('install','--update','--yes',ok=False)
        self.assertEqual(self.source.read_text(),'dirty')
        self.git(self.repo,'add','.')
        self.git(self.repo,'commit','-m','Local branch')
        (author/'remote-only').write_text('remote')
        self.git(author,'add','.')
        self.git(author,'commit','-m','Diverge')
        self.git(author,'push','origin','HEAD:refs/heads/main')
        head=self.git(self.repo,'rev-parse','HEAD')
        self.cli('install','--update','--yes',ok=False)
        self.assertEqual(head,self.git(self.repo,'rev-parse','HEAD'))
        self.assertFalse(self.target.exists())

    def test_update_preserves_ignored_content(self):
        (self.repo/'.gitignore').write_text('private-file\n')
        author=self.git_fixture()
        (self.repo/'private-file').write_text('local content')
        (author/'private-file').write_text('remote content')
        self.git(author,'add','--force','private-file')
        self.git(author,'commit','-m','Add formerly ignored path')
        self.git(author,'push','origin','HEAD:refs/heads/main')
        head=self.git(self.repo,'rev-parse','HEAD')
        self.cli('install','--update','--yes',ok=False)
        self.assertEqual((self.repo/'private-file').read_text(),'local content')
        self.assertEqual(head,self.git(self.repo,'rev-parse','HEAD'))

    def test_source_drift_after_preview(self):
        with mock.patch.dict(os.environ,self.env,clear=True):
            install=Installation(self.repo)
            install.plan_install()
            self.source.write_text('changed')
            with self.assertRaisesRegex(ValueError,'changed after preview'):
                install.apply('install')
        self.assertFalse(self.target.exists())

    def test_interrupted_transaction_recovers_before_retry(self):
        code = '''
import os,sys
sys.path.insert(0,sys.argv[1])
from install import Installation
p=Installation(os.environ['DOTS']);p.plan_install()
save=p.store.save
def crash(doc):
    save(doc)
    if doc['status']=='applying' and any(e['phase']=='done' for e in doc['operations']):
        os._exit(17)
p.store.save=crash
p.apply('install')
'''
        result=subprocess.run([sys.executable,'-B','-c',code,str(ROOT/'lib/dots/files')],env=self.env,capture_output=True,text=True)
        self.assertEqual(result.returncode,17,result.stderr)
        self.cli('install','--yes',ok=False)
        store=Store(self.home/'.state/dots')
        doc=store.records()[0]
        store.recover(doc['id'])
        self.assertFalse(self.target.exists())
        self.cli('install','--yes')
        self.assertTrue(self.target.is_symlink())

    def test_link_capability_refusal_preserves_existing_config(self):
        self.target.parent.mkdir(parents=True)
        self.target.write_text('before')
        with mock.patch.dict(os.environ,self.env,clear=True):
            install=Installation(self.repo)
            install.plan_install()
            with mock.patch.object(Path,'symlink_to',side_effect=OSError('link privilege unavailable')):
                with self.assertRaisesRegex(ValueError,'symbolic links unavailable'):
                    install.apply('install')
        self.assertEqual(self.target.read_text(),'before')
        self.assertFalse((self.home/'.state/dots/installation.json').exists())

    def test_optional_source_download_is_explicit_and_nonrecursive(self):
        if not shutil.which('git'):
            self.skipTest('Git unavailable')
        author=self.git_fixture()
        child=self.base/'child'
        child.mkdir()
        self.git(child,'init','--initial-branch=main')
        self.git(child,'config','user.email','fixture@example.invalid')
        self.git(child,'config','user.name','Fixture')
        (child/'.dots').mkdir()
        (child/'settings').write_text('optional config')
        (child/'.dots/files.json').write_text(json.dumps(dict(schema=1,repository='nvim',resources=[dict(id='optional',app='nvim',category='config',source='settings',target='${CONFIG}/optional',strategy='link',platforms=['termux','linux','wsl','windows'])])))
        self.git(child,'add','.')
        self.git(child,'commit','-m','Optional fixture')
        self.git(self.repo,'-c','protocol.file.allow=always','submodule','add',str(child),'optional')
        sources=json.loads((self.repo/'.dots/sources.json').read_text())
        sources['sources'].append(dict(id='nvim',path='optional',platforms=['termux','linux','wsl','windows'],roots=['.']))
        self.write('.dots/sources.json',sources)
        self.git(self.repo,'add','.')
        self.git(self.repo,'commit','-m','Record optional source')
        self.git(self.repo,'submodule','deinit','-f','--','optional')
        self.cli('install','--yes')
        self.assertFalse((self.repo/'optional/.git').exists())
        self.cli('install','--with-source','nvim','--dry-run')
        self.assertFalse((self.repo/'optional/.git').exists())
        # Local fixture transport is enabled for this test only.
        self.env['GIT_ALLOW_PROTOCOL']='file'
        self.cli('install','--with-source','nvim','--yes')
        self.assertEqual((self.home/'.config/optional').read_text(),'optional config')

    def theme_fixture(self):
        for name in ('lib', 'themes', 'default'):
            shutil.copytree(ROOT/name, self.repo/name, symlinks=True)
        (self.repo/'config/fsh').mkdir()
        shutil.copy2(ROOT/'config/fsh/README.md', self.repo/'config/fsh/README.md')
        doc=json.loads((self.repo/'.dots/files.json').read_text())
        doc['resources'].append(dict(id='fsh',source='config/fsh',target='${CONFIG}/fsh',strategy='directory-link',app='fsh',category='config',platforms=['termux','linux','wsl']))
        self.write('.dots/files.json',doc)

    @unittest.skipIf(os.name == 'nt', 'POSIX theme publication')
    def test_legacy_vivid_setup_notice_json_and_repeat(self):
        self.theme_fixture()
        install_vivid(self.repo/'bin')
        self.env['PATH'] = str(self.repo/'bin') + os.pathsep + self.env['PATH']
        self.env['DOTS_COLOR'] = self.env['DOTS_ICONS'] = 'always'
        preview = self.cli('install', '--dry-run', '--json')
        self.assertEqual(json.loads(preview.stdout)['status'], 'preview')
        self.assertNotIn('compatibility mode', preview.stderr)
        self.assertFalse((self.home/'.state').exists())
        result = self.cli('install', '--yes', '--json')
        self.assertEqual(json.loads(result.stdout)['status'], 'complete')
        self.assertEqual(result.stderr.count('Vivid compatibility mode'), 1)
        self.assertNotIn('\x1b', result.stderr + result.stdout)
        active = self.home/'.state/dots/current/theme'
        self.assertEqual((self.home/'.config/fsh/dots.ini').resolve(), active.resolve()/'fsh.ini')
        self.assertTrue((active/'fsh.ini').is_file())
        doc = json.loads((active/'colors.json').read_text())
        for kind in ('tw', 'ow'):
            style = doc['ls_rules']['types'][kind]['style']
            self.assertTrue(style['bold'] and style['underline'])
        receipt = self.receipt()
        repeated = self.cli('install', '--yes', '--json')
        self.assertEqual(json.loads(repeated.stdout)['status'], 'unchanged')
        self.assertNotIn('compatibility mode', repeated.stderr)
        self.assertEqual(self.receipt(), receipt)

    @unittest.skipIf(os.name == 'nt', 'POSIX theme publication')
    def test_legacy_vivid_setup_human_notice_and_custom_failure(self):
        self.theme_fixture()
        install_vivid(self.repo/'bin')
        self.env['PATH'] = str(self.repo/'bin') + os.pathsep + self.env['PATH']
        self.env['DOTS_COLOR'] = 'always'
        result = self.cli('install', '--yes')
        self.assertEqual(result.stderr.count('Vivid compatibility mode'), 1)
        self.assertIn('\x1b[93m', result.stderr)
        active = self.home/'.state/dots/current/theme'
        previous = active.resolve(); receipt = self.receipt()
        template = self.home/'.config/dots/themed/vivid.yml.tpl'
        template.parent.mkdir(parents=True)
        theme = json.loads((active/'vivid.yml').read_text())
        theme['archives']['font-style'] = ['bold', 'underline']
        template.write_text(json.dumps(theme, indent=2))
        result = self.cli('install', '--yes', ok=False)
        self.assertIn(str(template), result.stderr)
        self.assertIn('Vivid 0.9.0', result.stderr)
        self.assertEqual(active.resolve(), previous)
        self.assertEqual(self.receipt(), receipt)

    @unittest.skipIf(os.name == 'nt', 'POSIX fresh-checkout publication')
    @unittest.skipUnless(shutil.which('git'), 'Git required to enumerate tracked sources')
    def test_fresh_checkout_wsl_setup_connectors_check_and_restore(self):
        # Copy only versioned public inputs, never ignored connectors or local
        # submodule contents. Include this change's new source files before commit.
        names=set(subprocess.check_output(['git','-C',str(ROOT),'ls-files','-z','--',
            '.dots','bin','lib','default','themes','config','shells','ruby',
            'install.sh','uninstall.sh']).decode().rstrip('\0').split('\0'))
        names.update(('config/fsh/README.md','lib/dots/themes/generation.bash',
                      'lib/dots/files/events.py', 'lib/dots/verbose.bash'))
        shutil.rmtree(self.repo)
        self.repo.mkdir()
        for name in sorted(names):
            source=ROOT/name
            if source.is_dir() and not source.is_symlink():
                continue  # An uninitialized optional submodule is not a source.
            if not source.exists() and not source.is_symlink():
                continue
            target=self.repo/name
            target.parent.mkdir(parents=True,exist_ok=True)
            if source.is_symlink():
                link=os.readlink(source)
                self.assertFalse(os.path.isabs(link),name)
                self.assertTrue(Path(os.path.abspath(target.parent/link)).is_relative_to(self.repo),name)
                target.symlink_to(link)
            else:
                shutil.copy2(source,target)
        self.env={k:v for k,v in self.env.items() if k in (
            'PATH','PREFIX','LD_PRELOAD','LD_LIBRARY_PATH','TMPDIR','HOME','USERPROFILE',
            'DOTS','XDG_CONFIG_HOME','XDG_STATE_HOME','XDG_DATA_HOME','XDG_CACHE_HOME',
            'CODEX_HOME','PI_CODING_AGENT_DIR','GIT_CONFIG_GLOBAL','GIT_CONFIG_NOSYSTEM',
            'GIT_TERMINAL_PROMPT','DOTS_COLOR','DOTS_ICONS','TERM','PYTHONDONTWRITEBYTECODE')}
        self.env['WSL_DISTRO_NAME']='Fixture'
        self.env['DOTS_PROGRESS']='never'
        legacy_bin = self.base/'legacy-bin'
        legacy_bin.mkdir()
        install_vivid(legacy_bin)
        self.env['PATH'] = str(legacy_bin) + os.pathsep + self.env['PATH']
        self.assertEqual(list((self.repo/'config/fsh').iterdir()),[self.repo/'config/fsh/README.md'])
        def run(script,*args):
            result=subprocess.run(['sh',str(self.repo/script),*args,'--json'],env=self.env,
                                  capture_output=True,text=True,timeout=120)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertNotIn('\x1b',result.stdout)
            return json.loads(result.stdout)
        preview=run('install.sh','--dry-run')
        self.assertEqual(preview['platform'],'wsl')
        self.assertEqual(list(self.home.iterdir()),[])
        fsh=next(row for row in preview['items'] if row['id']=='dots:fsh')
        self.assertEqual(fsh['status'],'create')
        result=run('install.sh','--yes')
        active=self.home/'.state/dots/current/theme'
        self.assertTrue((self.home/'.config/fsh').is_symlink())
        self.assertTrue((self.home/'.config/fsh/dots.ini').is_file())
        for line in (self.repo/'lib/dots/themes/connectors.tsv').read_text().splitlines():
            app,suffix,artifact=line.split('\t')
            row=next((r for r in result['items'] if r['id']=='theme:'+app),None)
            if row:
                self.assertTrue(Path(row['target']).is_symlink(),app)
                self.assertTrue(Path(row['target']).exists(),app)
                self.assertTrue((active/artifact).exists(),app)
        for template in (self.repo/'default/themed').glob('*.tpl'):
            self.assertTrue((active/template.name[:-4]).is_file(),template.name)
        self.assertFalse((self.repo/'config/btop/themes/dots.theme').exists())  # Stashed.
        self.assertFalse((self.repo/'config/nvim/.git').exists())
        check=subprocess.run([sys.executable,'-B',str(self.repo/'lib/dots/files/check.py'),
                              '--dry-run','--json','--app','fsh'],env=self.env,capture_output=True,text=True)
        self.assertEqual(check.returncode,0,check.stderr)
        self.assertNotIn('"eligible": true',check.stdout)
        self.assertIn('dots:fsh',check.stdout)
        self.assertEqual(run('install.sh','--yes')['status'],'unchanged')
        run('uninstall.sh','--yes')
        self.assertFalse((self.home/'.config/fsh').is_symlink())
        self.assertFalse((self.repo/'config/fsh/dots.ini').is_symlink())
        self.assertTrue((self.repo/'config/fsh/README.md').is_file())

    @unittest.skipIf(os.name == 'nt', 'POSIX theme publication')
    def test_theme_output_and_pointer_repair_retains_baseline(self):
        self.theme_fixture()
        self.cli('install','--yes')
        active=self.home/'.state/dots/current/theme'
        initial=active.resolve()
        baseline=self.receipt()['entries'][str(active)]['before']
        for relative in ('fsh.ini', 'colors.json', 'yazi/tmtheme.xml'):
            with self.subTest(artifact=relative):
                old=active.resolve()
                (old/relative).unlink()
                preview=json.loads(self.cli('install','--dry-run','--json').stdout)
                row=next(r for r in preview['items'] if r['id']=='theme:catppuccin-mocha')
                self.assertEqual(row['status'],'prepare')
                self.assertIn(relative,row['target'])
                self.assertEqual(active.resolve(),old)
                self.assertFalse((old/relative).exists())
                self.cli('install','--yes')
                self.assertNotEqual(active.resolve(),old)
                self.assertTrue((active/relative).is_file())
        active.unlink()
        self.cli('install','--yes')
        self.assertTrue(active.is_symlink())
        self.assertEqual(self.receipt()['entries'][str(active)]['before'],baseline)
        self.assertEqual(json.loads(self.cli('install','--yes','--json').stdout)['status'],'unchanged')
        self.cli('uninstall','--yes')
        self.assertFalse(active.exists())
        self.assertTrue(initial.is_dir())
        self.assertFalse((self.home/'.config/fsh').is_symlink())
        self.assertFalse((self.repo/'config/fsh/dots.ini').is_symlink())
        self.assertTrue((self.repo/'config/fsh/README.md').is_file())

    @unittest.skipIf(os.name == 'nt', 'POSIX theme publication')
    def test_failed_theme_repair_does_not_publish_or_change_receipt(self):
        self.theme_fixture()
        self.cli('install','--yes')
        active=self.home/'.state/dots/current/theme'
        old=active.resolve(); receipt=self.receipt()
        (old/'fsh.ini').unlink()
        (self.repo/'default/themed/fsh.ini.tpl').write_text('{{ unknown_fsh_color }}')
        result=self.cli('install','--yes',ok=False)
        self.assertIn('unknown template color',result.stderr)
        self.assertEqual(active.resolve(),old)
        self.assertEqual(self.receipt(),receipt)
        self.assertFalse((old/'fsh.ini').exists())

    @unittest.skipIf(os.name == 'nt', 'POSIX theme publication')
    def test_theme_repair_publication_failure_rolls_back(self):
        self.theme_fixture()
        self.cli('install','--yes')
        active=self.home/'.state/dots/current/theme'
        old=active.resolve(); receipt=self.receipt()
        (old/'fsh.ini').unlink()
        with mock.patch.dict(os.environ,self.env,clear=True):
            install=Installation(self.repo)
            install.plan_install()
            save=install.store.save
            failed=False
            def fail(doc):
                nonlocal failed
                save(doc)
                if not failed and doc['status']=='applying' and any(
                        row['path']==str(active) and row['phase']=='done' for row in doc['operations']):
                    failed=True
                    raise OSError('injected theme publication failure')
            with mock.patch.object(install.store,'save',side_effect=fail):
                with self.assertRaisesRegex(OSError,'injected theme publication failure'):
                    install.apply('install')
        self.assertTrue(failed)
        self.assertEqual(active.resolve(),old)
        self.assertEqual(self.receipt(),receipt)
        self.assertFalse((old/'fsh.ini').exists())
        self.cli('install','--yes')
        self.assertTrue((active/'fsh.ini').is_file())

    @unittest.skipIf(os.name == 'nt', 'POSIX theme publication')
    def test_incomplete_preparation_and_foreign_pointer_are_refused(self):
        self.theme_fixture()
        render=self.repo/'lib/dots/themes/render.bash'
        with render.open('a') as stream:
            stream.write("\neval \"$(declare -f dt_render | sed '1s/dt_render/dt_original_render/')\"\n"
                         'dt_render() { dt_original_render "$1" && rm "$1/fsh.ini"; }\n')
        result=self.cli('install','--yes',ok=False)
        self.assertIn('incomplete prepared theme',result.stderr)
        self.assertFalse(self.target.exists())
        self.assertFalse((self.home/'.state/dots/installation.json').exists())
        shutil.copy2(ROOT/'lib/dots/themes/render.bash',render)
        self.cli('install','--yes')
        active=self.home/'.state/dots/current/theme'
        active.unlink(); active.symlink_to(self.home)
        result=self.cli('install','--yes',ok=False)
        self.assertIn('invalid active theme',result.stderr)
        self.assertEqual(active.readlink(),self.home)

    @unittest.skipIf(os.name == 'nt', 'POSIX theme publication')
    def test_real_theme_install_repeat_and_restore(self):
        shutil.copytree(ROOT/'lib',self.repo/'lib',symlinks=True)
        shutil.copytree(ROOT/'themes',self.repo/'themes',symlinks=True)
        shutil.copytree(ROOT/'default',self.repo/'default',symlinks=True)
        (self.repo/'config/kitty').mkdir()
        (self.repo/'config/kitty/kitty.conf').write_text('include dots-theme.conf\n')
        doc=json.loads((self.repo/'.dots/files.json').read_text())
        doc['resources'].append(dict(id='kitty',source='config/kitty',target='${CONFIG}/kitty',strategy='directory-link',app='kitty',category='config',platforms=['termux','linux','wsl']))
        self.write('.dots/files.json',doc)
        self.cli('install','--dry-run')
        self.assertFalse((self.home/'.state').exists())
        self.cli('install','--yes')
        active=self.home/'.state/dots/current/theme'
        connector=self.repo/'config/kitty/dots-theme.conf'
        self.assertTrue(active.is_symlink())
        self.assertTrue(connector.is_file())
        self.assertIn('background',connector.read_text())
        receipt=self.receipt()
        self.assertEqual(json.loads(self.cli('install','--yes','--json').stdout)['status'],'unchanged')
        self.assertEqual(receipt,self.receipt())
        # Normal publication remains compatible with setup-owned generations.
        # Suppress external app effects explicitly, including on Termux hosts.
        script='''DT_LIB="$DOTS/lib/dots/themes"
source "$DT_LIB/core.bash"
source "$DT_LIB/views.bash"
source "$DT_LIB/state.bash"
dt_apps_reload() { :; }
dt_plugins_after_publish() { :; }
dt_set rose-pine-dawn
'''
        switched=subprocess.run(['bash','-c',script],env=self.env,capture_output=True,text=True)
        self.assertEqual(switched.returncode,0,switched.stderr)
        template=self.repo/'lib/dots/themes/setup.bash'
        template.write_text(template.read_text()+'\n# Updated checkout fixture\n')
        self.cli('install','--yes')
        self.assertEqual((active/'id').read_text().strip(),'rose-pine-dawn')
        self.assertEqual(self.receipt()['entries'][str(active)]['before'],receipt['entries'][str(active)]['before'])
        self.cli('uninstall','--yes')
        self.assertFalse(active.is_symlink())
        self.assertFalse(connector.is_symlink())
        self.assertTrue((self.repo/'config/kitty/kitty.conf').exists())


if __name__=='__main__':
    unittest.main(verbosity=2)

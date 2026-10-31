#!/usr/bin/env python3
"""Manifest publication uses fake inventories and disposable local Git remotes."""
import io
import json
import os
from pathlib import Path
import shutil
import sys
from contextlib import redirect_stdout
import unittest
from unittest.mock import patch

import test_git_operations as fixture
ROOT = fixture.PROJECT
sys.path.insert(0, str(ROOT/'lib/dots'))
sys.path.insert(0, str(ROOT/'plugins/pkgs'))


@unittest.skipIf(os.name == 'nt', 'POSIX inventory and local SSH fixtures; native Windows refuses this option')
class PublishPackages(unittest.TestCase):
    setUp = fixture.GitOperations.setUp
    run_cmd = fixture.GitOperations.run_cmd
    git = fixture.GitOperations.git
    repo = fixture.GitOperations.repo
    remote_repo = fixture.GitOperations.remote_repo
    owned_remote = fixture.GitOperations.owned_remote

    def prepare(self, name):
        _, remote, repo = self.remote_repo(name)
        self.owned_remote(repo, remote)
        profile = repo/'profiles/termux';profile.mkdir(parents=True)
        (profile/'profile.json').write_text(json.dumps({'schema':1,'id':'termux'}))
        path = profile/'packages.json'
        path.write_text(json.dumps({'schema':1,'groups':[{'manager':'npm','scope':'global',
            'packages':[{'name':'hello','pin':'1','observed_version':'1','selection':'manual'},
                        {'name':'keep','enabled':False,'reason':'my choice'}, {'name':'absent'}]}]}))
        self.git(repo,'add','profiles');self.git(repo,'commit','-m','profile fixture')
        self.git(repo,'push','origin','HEAD:refs/heads/main')
        binaries=self.base/(name+'-bin');binaries.mkdir()
        # No host package-manager executables are exposed to the command.
        for command in ('bash','git','python3','uname','readlink','dirname','tr','cat','sed','sort','mkdir','rmdir','rm','sha256sum','date','find','wc','stat','pwd'):
            executable=shutil.which(command)
            if executable:(binaries/command).symlink_to(executable)
        git_exec=Path(self.git(repo,'--exec-path'))
        for command in ('git-upload-pack','git-receive-pack'):(binaries/command).symlink_to(git_exec/command)
        modules=self.base/(name+'-modules');modules.mkdir();(modules/'pip.py').write_text('raise SystemExit(1)\n')
        npm=binaries/'npm'
        npm.write_text('#!'+sys.executable+'\n'+'''import json,os,sys
from pathlib import Path
a=sys.argv[1:]
with open(os.environ['FIXTURE_QUERIES'],'a') as f:f.write(json.dumps(a)+'\\n')
if a!=['ls','--depth=0','--json','--global']:raise SystemExit(91)
if os.environ.get('FIXTURE_FAIL'):
 print(json.dumps({'error':'fixture inventory failure'}));raise SystemExit(1)
print(json.dumps({'dependencies':{'hello':{'version':'2'},'new':{'version':'3'}}}))
''');npm.chmod(0o755)
        env=dict(self.env,DOTS=str(repo),PREFIX=str(self.base/'usr'),TERMUX_VERSION='fixture',
                 TERMUX__PREFIX='',TERMUX_APP_PACKAGE_MANAGER='',PATH=str(binaries),PYTHONPATH=str(modules),
                 VIRTUAL_ENV='',BUNDLE_GEMFILE='',FIXTURE_QUERIES=str(self.base/(name+'-queries')))
        return repo,remote,path,env

    def publish(self, repo, env, *args, frontend='native', ok=True):
        command=([sys.executable,'-B',str(ROOT/'lib/dots/git/cli.py'),'publish'] if frontend=='native' else
                 [shutil.which('bash'),str(ROOT/'bin/dots-git-publish')])
        return self.run_cmd([*command,'-C',str(repo),'--config',str(self.config),'--no-wiki','--update-packages',*args],env=env,ok=ok)

    def test_preview_pure_then_publish_preserves_edits_and_unrelated_files_both_frontends(self):
        for frontend in ('native','bash'):
            repo,remote,path,env=self.prepare(frontend)
            env.update(DOTS_COLOR='always',DOTS_ICONS='always')
            (repo/'staged').write_text('include');self.git(repo,'add','staged')
            (repo/'unrelated').write_text('leave unstaged')
            before=path.read_bytes();index=(repo/'.git/index').read_bytes();refs=self.git(repo,'show-ref')
            preview=json.loads(self.publish(repo,env,'--dry-run','--json',frontend=frontend).stdout)
            self.assertTrue(preview['complete']);self.assertTrue(preview['dry_run'])
            self.assertEqual(path.read_bytes(),before);self.assertEqual((repo/'.git/index').read_bytes(),index)
            self.assertEqual(self.git(repo,'show-ref'),refs);self.assertFalse((repo/'.git/git-it.lock').exists())
            result=json.loads(self.publish(repo,env,'--yes','--json',frontend=frontend).stdout)
            self.assertTrue(result['complete'])
            stored=json.loads(self.git(remote,'show','main:profiles/termux/packages.json'))
            packages={p['name']:p for p in stored['groups'][0]['packages']}
            self.assertEqual(packages['hello']['observed_version'],'2');self.assertEqual(packages['hello']['pin'],'1')
            self.assertEqual(packages['hello']['selection'],'manual');self.assertFalse(packages['keep']['enabled'])
            self.assertEqual(packages['keep']['reason'],'my choice');self.assertIn('absent',packages);self.assertIn('new',packages)
            committed=self.git(remote,'ls-tree','--name-only','main').splitlines()
            self.assertIn('staged',committed);self.assertNotIn('unrelated',committed)
            self.assertEqual((repo/'unrelated').read_text(),'leave unstaged')
            self.assertEqual(self.git(repo,'rev-parse','HEAD'),self.git(remote,'rev-parse','main'))
            before=self.git(repo,'rev-parse','HEAD');stamp=path.stat().st_mtime_ns
            self.publish(repo,env,'--yes','--json',frontend=frontend)
            self.assertEqual(self.git(repo,'rev-parse','HEAD'),before);self.assertEqual(path.stat().st_mtime_ns,stamp)

    def test_failed_export_and_partial_staging_stop_before_publication(self):
        repo,remote,path,env=self.prepare('failure')
        head=self.git(repo,'rev-parse','HEAD');before=path.read_bytes();index=(repo/'.git/index').read_bytes()
        failed=json.loads(self.publish(repo,dict(env,FIXTURE_FAIL='1'),'--yes','--json',ok=False).stdout)
        self.assertFalse(failed['complete']);self.assertIn('inventory failure',str(failed['events']))
        self.assertEqual(path.read_bytes(),before);self.assertEqual((repo/'.git/index').read_bytes(),index)
        self.assertEqual(self.git(remote,'rev-parse','main'),head)
        data=json.loads(path.read_text());data['groups'][0]['packages'][0]['pin']='4';path.write_text(json.dumps(data))
        self.git(repo,'add','profiles/termux/packages.json')
        data['groups'][0]['packages'][0]['pin']='5';path.write_text(json.dumps(data));before=path.read_bytes()
        index=(repo/'.git/index').read_bytes()
        failed=json.loads(self.publish(repo,env,'--yes','--json',ok=False).stdout)
        self.assertFalse(failed['complete']);self.assertIn('partially staged',str(failed['events']))
        self.assertEqual(path.read_bytes(),before);self.assertEqual((repo/'.git/index').read_bytes(),index)
        self.assertEqual(self.git(repo,'rev-parse','HEAD'),head)

    def test_missing_manifest_is_created_and_ignored_manifest_is_refused(self):
        repo,remote,path,env=self.prepare('new-manifest')
        self.git(repo,'rm','profiles/termux/packages.json');self.git(repo,'commit','-m','remove fixture manifest')
        self.git(repo,'push','origin','HEAD:refs/heads/main')
        (repo/'.gitignore').write_text('profiles/termux/packages.json\n')
        head=self.git(repo,'rev-parse','HEAD')
        failed=json.loads(self.publish(repo,env,'--yes','--json',ok=False).stdout)
        self.assertFalse(failed['complete']);self.assertIn('ignored',str(failed['events']));self.assertFalse(path.exists())
        (repo/'.gitignore').unlink()
        self.publish(repo,env,'--yes','--json')
        self.assertTrue(path.is_file());self.assertNotEqual(self.git(repo,'rev-parse','HEAD'),head)

    def test_cancel_and_manifest_drift_preserve_source_and_index(self):
        from wiki_git import core
        module=core()
        for change in (False,True):
            repo,remote,path,env=self.prepare('drift' if change else 'cancel')
            head=self.git(repo,'rev-parse','HEAD');index=(repo/'.git/index').read_bytes();before=path.read_bytes()
            def confirm(*args):
                if change:path.write_text(json.dumps({'schema':1,'groups':[]}))
                return change
            with patch.dict(os.environ,env,clear=True),patch.object(sys,'argv',['git','publish','-C',str(repo),'--config',str(self.config),'--no-wiki','--update-packages']), \
                 patch.object(module.sys.stdin,'isatty',return_value=True),patch.object(module,'gum_confirm',side_effect=confirm),redirect_stdout(io.StringIO()):
                self.assertEqual(module.main(),int(change))
            self.assertEqual(self.git(repo,'rev-parse','HEAD'),head);self.assertEqual((repo/'.git/index').read_bytes(),index)
            self.assertEqual(path.read_bytes(),json.dumps({'schema':1,'groups':[]}).encode() if change else before)
            self.assertFalse((repo/'.git/git-it.lock').exists())

    def test_windows_refusal_and_invalid_scopes_do_not_query_packages(self):
        from package_publish import Stage
        from pkgs_lib import manifests
        with patch.object(manifests,'platform',return_value='windows'),patch.object(manifests,'export',side_effect=AssertionError('inventory forbidden')):
            with self.assertRaisesRegex(ValueError,'native Windows'):Stage(self.base)
        for command in ('sync','submodules-publish'):
            result=self.run_cmd([sys.executable,'-B',str(ROOT/'lib/dots/git/cli.py'),command,'--update-packages'],ok=False)
            self.assertEqual(result.returncode,2);self.assertIn('requires root git publish',result.stderr)


if __name__=='__main__':unittest.main()

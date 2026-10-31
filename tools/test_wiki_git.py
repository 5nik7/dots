#!/usr/bin/env python3
"""Associated wiki workflows against disposable repositories and local transports."""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch
from test_wiki import WikiFixture,ROOT


@unittest.skipIf(os.name=='nt','local SSH shim requires Bash; portable/native controller tests run separately')
class WikiGitTests(WikiFixture):
    def setUp(self):
        super().setUp()
        self.env.update(GIT_CONFIG_COUNT='2',GIT_CONFIG_KEY_0='commit.gpgSign',GIT_CONFIG_VALUE_0='false',GIT_CONFIG_KEY_1='core.hooksPath',GIT_CONFIG_VALUE_1=os.devnull)
        self.git(self.root,'init','-b','main');self.git(self.root,'add','.');self.git(self.root,'commit','-m','source')
        self.source_remote=self.base/'source.git';self.wiki_remote=self.base/'wiki.git'
        for repo,bare,branch in ((self.root,self.source_remote,'main'),(self.target,self.wiki_remote,'master')):
            self.git(self.base,'clone','--bare',str(repo),str(bare))
            self.git(repo,'remote','add','origin',str(bare));self.git(repo,'fetch','origin');self.git(repo,'branch','--set-upstream-to=origin/'+branch)
        ssh=self.base/'ssh-test';ssh.write_text('#!'+shutil.which('bash')+'\n[[ $1 != -G ]] || exit 1\nexec bash -c "${!#}"\n');ssh.chmod(0o700)
        self.env.update(GIT_SSH_COMMAND=shlex.quote(str(ssh)),GIT_SSH_VARIANT='ssh')
        self.config=self.home/'config/dots/git.conf';self.config.parent.mkdir(parents=True)
        self.config.write_text('[dots-git]\nowner = example.invalid/'+str(self.base).lstrip('/')+'\n')
        for repo,bare in ((self.root,self.source_remote),(self.target,self.wiki_remote)):
            self.git(repo,'remote','set-url','origin','ssh://git@example.invalid'+str(bare))
        self.extra=patch.dict(os.environ,self.env,clear=True);self.extra.start();self.addCleanup(self.extra.stop)

    def run_git(self,action,*args,only=False,bash=False,code=0):
        if bash:
            command=['bash',str(ROOT/'bin/dots'),'git',*(['wiki'] if only else []),action]
        else:
            command=[sys.executable,'-B',str(ROOT/'lib/dots'/('wiki_git.py' if only else 'git/cli.py')),action]
        # Bash resolves its implementation checkout's profile configuration.
        # Publication must always use this fixture's owner rules, never live ones.
        if action=='publish':command+=['--config',str(self.config)]
        result=subprocess.run([*command,'-C',str(self.root),*args],env=dict(self.env,DOTS=str(ROOT)) if bash else self.env,cwd=self.base,text=True,capture_output=True,timeout=40)
        self.assertEqual(result.returncode,code,result.stderr+'\n'+result.stdout)
        return json.loads(result.stdout) if '--json' in args and result.stdout else result.stdout

    def stage_build(self):self.build();self.git(self.target,'add','.')

    def test_status_scope_and_submodule_boundary_both_frontends(self):
        for bash in (False,True):
            data=self.run_git('status','--json',bash=bash)
            self.assertEqual({r['path'] for r in data['repositories']},{str(self.root),str(self.target)})
            wiki=next(r for r in data['repositories'] if r['path']==str(self.target));self.assertEqual(wiki['kind'],'wiki')
            data=self.run_git('status','--json','--no-wiki',bash=bash)
            self.assertEqual([r['path'] for r in data['repositories']],[str(self.root)])
            data=self.run_git('status','--json',only=True,bash=bash)
            self.assertEqual([r['path'] for r in data['repositories']],[str(self.target)])
            self.assertEqual(data['repositories'][0]['kind'],'wiki')
        self.assertEqual(self.git(self.root,'ls-files','--stage').count('160000'),0)

    def test_info_and_missing_companion(self):
        command=[sys.executable,'-B',str(ROOT/'lib/dots/git/inspection.py'),'info','-C',str(self.root),'--json']
        result=subprocess.run(command,env=self.env,text=True,capture_output=True);self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['companions'][0]['kind'],'wiki')
        shutil.rmtree(self.target)
        data=self.run_git('status','--json');self.assertTrue(data['complete'])
        self.assertEqual(data['repositories'][-1]['status'],'missing')
        self.run_git('status','--json',only=True,code=1)
        self.assertFalse(self.target.exists())

    def test_combined_publish_source_first_and_no_gitlink(self):
        (self.root/'docs/guide.md').write_text('# Guide\n## Hello world\nUpdated\n')
        self.git(self.root,'add','docs/guide.md');self.stage_build()
        data=self.run_git('publish','--yes','--json','-m','Update docs')
        published=[r['path'] for r in data['events'] if r['status']=='published']
        self.assertEqual(published,[str(self.root),str(self.target)])
        self.assertEqual(self.git(self.root,'rev-parse','HEAD'),self.git(self.source_remote,'rev-parse','main'))
        self.assertEqual(self.git(self.target,'rev-parse','HEAD'),self.git(self.wiki_remote,'rev-parse','master'))
        self.assertEqual(self.git(self.root,'status','--porcelain'),'')
        self.cli('check','--json')

    def test_package_manifest_refresh_precedes_source_and_wiki_publication(self):
        import io
        from contextlib import redirect_stdout
        from wiki_git import core
        sys.path.insert(0,str(ROOT/'plugins/pkgs'))
        from pkgs_lib import manifests
        for identity in ('termux','linux','wsl','windows'):
            profile=self.root/'profiles'/identity;profile.mkdir(parents=True)
            (profile/'profile.json').write_text(json.dumps({'schema':1,'id':identity}))
        self.git(self.root,'add','profiles');self.stage_build()
        snapshot={'schema':1,'groups':[{'manager':'npm','scope':'global','packages':[{'name':'fixture','observed_version':'2'}]}]}
        output=io.StringIO()
        with patch.object(manifests,'export',return_value=(snapshot,False)), \
             patch.object(sys,'argv',['git','publish','-C',str(self.root),'--config',str(self.config),'--update-packages','--yes','--json']), \
             redirect_stdout(output):
            self.assertEqual(core().main(),0)
        events=json.loads(output.getvalue())['events']
        self.assertEqual([r['path'] for r in events if r['status']=='published'],[str(self.root),str(self.target)])
        updated=next(i for i,r in enumerate(events) if r['status']=='updated' and r['file'].endswith('packages.json'))
        published=next(i for i,r in enumerate(events) if r['status']=='published')
        self.assertLess(updated,published)
        path=manifests.default_path(self.root).relative_to(self.root).as_posix()
        self.assertEqual(json.loads(self.git(self.source_remote,'show','main:'+path))['groups'][0]['packages'][0]['name'],'fixture')
        self.cli('check','--json')

    def test_stale_index_is_blocked_even_with_current_worktree(self):
        self.stage_build()
        (self.root/'docs/guide.md').write_text('# Guide\n## Hello world\nNew docs\n')
        self.git(self.root,'add','docs/guide.md');self.build() # deliberately leave wiki index stale
        before=self.git(self.target,'rev-parse','HEAD')
        data=self.run_git('publish','--yes','--json',code=1)
        self.assertTrue(any(r['status']=='blocked' and 'stale' in r['detail'] for r in data['events']))
        self.assertEqual(self.git(self.target,'rev-parse','HEAD'),before)
        self.assertEqual(self.git(self.root,'rev-parse','HEAD'),self.git(self.source_remote,'rev-parse','main'))

    def test_wiki_only_requires_published_source_and_preserves_parent(self):
        self.stage_build();before=self.git(self.root,'rev-parse','HEAD')
        self.run_git('publish','--yes','--json',only=True)
        self.assertEqual(self.git(self.root,'rev-parse','HEAD'),before)
        (self.root/'docs/guide.md').write_text('# Guide\n## Hello world\nUnpublished\n')
        self.git(self.root,'add','.');self.git(self.root,'commit','-m','not pushed');self.stage_build()
        self.run_git('publish','--yes','--json',only=True,code=1)
        self.assertNotEqual(self.git(self.root,'rev-parse','HEAD'),self.git(self.source_remote,'rev-parse','main'))

    def test_all_mode_and_dry_run_are_explicit(self):
        (self.root/'docs/guide.md').write_text('# Guide\n## Hello world\nAll mode\n');self.build()
        before=(self.git(self.root,'status','--porcelain'),self.git(self.target,'status','--porcelain'))
        data=self.run_git('publish','--all','--dry-run','--json')
        self.assertTrue(data['complete'])
        self.assertEqual(before,(self.git(self.root,'status','--porcelain'),self.git(self.target,'status','--porcelain')))
        self.run_git('publish','--all','--yes','--json',bash=True)
        self.assertEqual(self.git(self.target,'status','--porcelain'),'')

    def test_source_failure_blocks_wiki_but_exclusion_works(self):
        self.stage_build();(self.root/'docs/guide.md').write_text('# Guide\n## Hello world\nChanged\n')
        self.git(self.root,'add','.');self.stage_build()
        self.git(self.root,'remote','set-url','--push','origin','https://unowned.invalid/test/source.git')
        before=self.git(self.target,'rev-parse','HEAD')
        data=self.run_git('publish','--yes','--json',code=1)
        self.assertTrue(any('source publication failed' in r['detail'].lower() for r in data['events']))
        self.assertEqual(self.git(self.target,'rev-parse','HEAD'),before)
        self.git(self.root,'config','--unset-all','remote.origin.pushurl')
        (self.target/'Home.md').write_text('unreviewed')
        self.run_git('publish','--no-wiki','--yes','--json')
        self.assertEqual((self.target/'Home.md').read_text(),'unreviewed')

    def test_sync_own_upstream_and_dirty_refusal(self):
        clone=self.base/'other-wiki';self.git(self.base,'clone',str(self.wiki_remote),str(clone))
        (clone/'New.md').write_text('remote page');self.git(clone,'add','.');self.git(clone,'commit','-m','remote wiki');self.git(clone,'push','origin','master')
        self.run_git('sync','--json','--dry-run');self.assertFalse((self.target/'New.md').exists())
        self.run_git('sync','--json');self.assertTrue((self.target/'New.md').exists())
        (self.target/'Home.md').write_text('dirty')
        self.run_git('sync','--json',code=1)
        self.assertEqual((self.target/'Home.md').read_text(),'dirty')

    def test_publish_refuses_different_source_branch(self):
        self.git(self.root,'push','origin','HEAD:refs/heads/feature')
        self.git(self.root,'branch','--set-upstream-to=origin/feature')
        self.stage_build()
        before=self.git(self.target,'rev-parse','HEAD')
        data=self.run_git('publish','--yes','--json',code=1)
        self.assertTrue(any('configured source branch' in r['detail'] for r in data['events']))
        self.assertEqual(self.git(self.target,'rev-parse','HEAD'),before)

    def test_sync_rechecks_changed_association(self):
        clone=self.base/'other-source';self.git(self.base,'clone',str(self.source_remote),str(clone))
        self.git(clone,'rm','.dots/wiki.json');self.git(clone,'commit','-m','remove association');self.git(clone,'push','origin','main')
        before=self.git(self.target,'rev-parse','HEAD')
        data=self.run_git('sync','--json',code=1)
        self.assertTrue(any('association changed' in r['detail'] for r in data['events']))
        self.assertEqual(self.git(self.target,'rev-parse','HEAD'),before)
        self.assertFalse((self.root/'.dots/wiki.json').exists())


if __name__=='__main__':unittest.main()

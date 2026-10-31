"""Aliases and read-only native update queries with owned roots and fixtures."""
import contextlib
import io
import json
import os
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_workflows as fixtures
from pkgs_lib import cli, completion, outdated, policies, workflows, scopes
from pkgs_lib.backends import Backend
from pkgs_lib.common import Error, Package

CODEX = ['npm','install','-g','--force','@openai/codex@latest',
         '@openai/codex-linux-arm64@npm:@openai/codex@linux-arm64']


class UpdateCommands(unittest.TestCase):
    setUp = fixtures.Workflows.setUp
    args = fixtures.Workflows.args
    invoke = fixtures.Workflows.invoke

    def test_aliases_and_literal_ls(self):
        for words, command, listing, update in (
            (['in','hello'],'install',False,False), (['un','hello'],'uninstall',False,False),
            (['up'],'upgrade',False,False), (['xup'],'export',False,True),
            (['upls'],'upgrade',True,False), (['up','ls'],'upgrade',True,False),
            (['upgrade','--list'],'upgrade',True,False), (['upgrade','--','ls'],'upgrade',False,False)):
            with self.subTest(words=words):
                args = self.args(*words)
                self.assertEqual((args.command,args.list_upgrades,args.update),(command,listing,update))
        result = self.invoke('in','--manager','npm','hello')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads((self.home/'db.json').read_text()),{'hello':'2.0'})

    def test_alias_dispatch_and_options(self):
        with patch('pkgs_lib.manifests.cli',return_value=0) as export:
            self.assertEqual(cli.main(['xup','--dry-run']),0)
            self.assertTrue(export.call_args.args[0].update)
            self.assertEqual(export.call_args.args[0].command,'export')
        bad = self.invoke('in','--list','hello')
        self.assertEqual(bad.returncode,1); self.assertIn('--list requires upgrade',bad.stderr)
        with patch.object(completion,'default_manager',side_effect=AssertionError('probe')):
            self.assertIn(('upls','Alias for upgrade --list'),completion.complete(['u'],self.cfg))
            self.assertEqual(completion.complete(['upls',''],self.cfg),[])
        self.assertEqual(completion.context(['in','x'],self.cfg)[3],'install')
        self.assertEqual(completion.context(['un','x'],self.cfg)[3],'uninstall')
        self.assertIn(('--list','List available upgrades without installing'),completion.complete(['up','--l'],self.cfg))
        self.assertIn(('--dry-run','Print transaction without executing'),completion.complete(['cleanup','--d'],self.cfg))

    def test_every_native_query_parses_versions_without_transactions(self):
        fixtures = {
            'apt': 'Listing...\nhello/stable 2.0 aarch64 [upgradable from: 1.0]\n',
            'pacman': 'hello 1.0 -> 2.0\n', 'paru': 'hello 1.0 -> 2.0\n', 'yay':'hello 1.0 -> 2.0\n',
            'dnf': 'hello\t2.0\n', 'xbps': 'hello-2.0 update aarch64 repo 200 100\n',
            'npm': '{"hello":{"current":"1.0","wanted":"2.0","latest":"3.0"}}',
            'pip': '[{"name":"hello","version":"1.0","latest_version":"2.0"}]',
            'uv-tool': 'hello v1.0 [latest: 2.0]\n- hello\n', 'gem': 'hello (1.0 < 2.0)\n',
        }
        for manager,text in fixtures.items():
            with self.subTest(manager=manager), patch.object(outdated,'query',return_value=subprocess.CompletedProcess([],1 if manager=='npm' else 0,text,'')) as run:
                rows = outdated.candidates(Backend(manager,manager=='npm'),[Package('hello','1.0',installed=True)])
                self.assertEqual(rows,[dict(name='hello',current='1.0',candidate='2.0')])
                argv = run.call_args.args[0]
                if manager == 'xbps': self.assertEqual(argv,['xbps-install','-un'])
                else: self.assertFalse({'install','update','upgrade','refresh'} & set(argv),argv)
                if manager == 'npm': self.assertEqual(argv,['npm','outdated','--json','--global','--','hello'])
                if manager == 'dnf': self.assertIn('--cacheonly',argv)

    def test_malformed_native_results_and_failed_queries_are_not_empty_success(self):
        for manager,code,text,err in [('npm',1,'{"error":{"code":"E404"}}',''),('apt',0,'bad output',''),
                ('uv-tool',2,'','unknown flag: --outdated'),('pacman',1,'','database unavailable'),
                ('pip',0,'not json','')]:
            with self.subTest(manager=manager), patch.object(outdated,'query',return_value=subprocess.CompletedProcess([],code,text,err)):
                with self.assertRaises((Error,ValueError)):
                    outdated.candidates(Backend(manager),[Package('hello','1')])

    def test_go_query_uses_build_module_and_isolated_directory(self):
        package = Package('example.org/mod/cmd/hello','v1.0.0',details={'module':'example.org/mod'})
        with patch.object(outdated,'query',return_value=subprocess.CompletedProcess([],0,'{"Version":"v1.1.0"}','')) as run:
            rows = outdated.candidates(Backend('go'),[package])
        self.assertEqual(rows[0]['candidate'],'v1.1.0')
        self.assertEqual(run.call_args.args[0],['go','list','-m','-json','example.org/mod@latest'])
        self.assertIn('pkgs-go-query-',run.call_args.kwargs['cwd'])
        self.assertEqual(run.call_args.kwargs['env']['GOTOOLCHAIN'],'local')
        for older,newer in [('v1.0.0-rc.2','v1.0.0-rc.10'),('v1.0.0-rc.10','v1.0.0'),('v1.9.0','v1.10.0')]:
            self.assertLess(outdated.semver(older),outdated.semver(newer))

    def test_scope_skips_ownership_and_source_exclusions(self):
        cfg = dict(self.cfg,policies={'pip':{'skip':['held']}})
        packages = [(Package(n,'1.0'),'explicit',reason) for n,reason in
                    [('hello',''),('held',''),('source','source install'),('system','system owned')]]
        with patch.object(scopes,'inventory',return_value=packages) as inventory, patch.object(outdated,'candidates',return_value=[
            dict(name='hello',current='1.0',candidate='2.0'),dict(name='system',current='1',candidate='2')]) as query:
            group = outdated.inspect(Backend('pip'),self.args('upls'),cfg,bulk=True)
        self.assertTrue(inventory.call_args.kwargs['owned'])
        self.assertEqual([p.name for p in query.call_args.args[1]],['hello'])
        self.assertEqual(len(group['skipped']),3); self.assertEqual(len(group['packages']),1)
        with patch.object(scopes,'inventory',return_value=packages):
            with self.assertRaisesRegex(Error,'Not installed'):
                outdated.inspect(Backend('pip'),self.args('upgrade','--list','missing'),cfg)

    def test_bulk_json_continues_failure_and_never_executes(self):
        cfg = dict(self.cfg,upgrade={'managers':['npm','uv-tool']})
        out = io.StringIO()
        with contextlib.redirect_stdout(out), patch.object(outdated,'available',return_value=True), \
             patch.object(scopes,'inventory',return_value=[(Package('hello','1.0'),'explicit','')]), \
             patch.object(outdated,'candidates',side_effect=[Error('registry failed'),[dict(name='hello',current='1',candidate='2')]]), \
             patch.object(workflows,'apply',side_effect=AssertionError('mutation')):
            rc = outdated.cli(self.args('upls','--json'),cfg)
        self.assertEqual(rc,1)
        data = json.loads(out.getvalue()); self.assertEqual(data['schema'],1)
        self.assertEqual([g['status'] for g in data['groups']],['error','ok'])
        self.assertEqual(data['groups'][0]['scope'],'global')

    def test_real_cli_readonly_npm_exit_one_is_updates(self):
        fake = self.bin/'npm'
        fake.write_text('#!'+sys.executable+'\n'+'''import sys,json,os
args=sys.argv[1:]
with open(os.environ['TEST_CALLS'],'a') as f:f.write(json.dumps(args)+'\\n')
if args[0]=='ls': print('{"dependencies":{"hello":{"version":"1.0"}}}')
elif args[0]=='outdated': print('{"hello":{"current":"1.0","wanted":"2.0"}}');sys.exit(1)
else: sys.exit(99)
''')
        for spelling in (['upls'],['upgrade','ls'],['upgrade','--list']):
            result = self.invoke(*spelling,'--manager','npm','--global','--json')
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout)['groups'][0]['packages'][0]['name'],'hello')
        calls = [json.loads(line) for line in (self.home/'calls.jsonl').read_text().splitlines()]
        self.assertTrue(all(c[0] in ('ls','outdated') for c in calls),calls)
        self.assertEqual((self.home/'db.json').read_text(),'{}')

    def test_codex_literal_recipe_and_companion_exclusion(self):
        self.assertEqual(Backend('npm').transaction('upgrade',['hello']),['npm','update','--','hello'])
        cfg = dict(self.cfg,policies={'npm':{'skip':['@openai/codex-linux-arm64'],
                   'packages':{'@openai/codex':{a:{'replace':[CODEX]} for a in ('install','upgrade')}}}})
        policies.validate(cfg)
        for action in ('install','upgrade'):
            item = workflows.plan(Backend('npm',True),action,['@openai/codex'],cfg)
            self.assertEqual(item.commands,[CODEX])
        with patch.object(scopes,'inventory',return_value=[(Package(n),'explicit','') for n in
                ('@openai/codex','@openai/codex-linux-arm64','hello')]):
            item = workflows.plan(Backend('npm',True),'upgrade',[],cfg,bulk=True)
        self.assertEqual(item.commands,[['npm','install','--global','--','hello'],CODEX])
        self.assertEqual(item.skipped,[dict(package='@openai/codex-linux-arm64',reason='skipped by policy')])

    def test_list_presentation_widths_color_and_plain(self):
        from pkgs_lib import reports  # Establish the shared presentation import path.
        from resources import cells
        from pkgs_lib.streams import ESCAPES
        class Terminal(io.StringIO):
            def isatty(self): return True
        group=dict(manager='npm',scope='global',packages=[dict(name='@scope/a-long-package-name',current='1.0',candidate='2.0')],
                   skipped=[],error='',status='ok')
        for width in (40,80,120):
            for color in ('always','never'):
                out=Terminal()
                with contextlib.redirect_stdout(out),patch.dict(os.environ,COLUMNS=str(width),TERM='xterm-256color'):
                    outdated.display(group,dict(self.cfg,_explicit_color=color))
                text=out.getvalue()
                self.assertEqual('\x1b[' in text,color=='always')
                self.assertTrue(all(cells(line)<=width for line in ESCAPES.sub('',text).splitlines()),text)
                self.assertIn('1.0→2.0',''.join(ESCAPES.sub('',text).split()))


if __name__ == '__main__': unittest.main()

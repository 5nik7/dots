import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pkgs_lib import detect, manifests, policies, scopes, outdated
from pkgs_lib.common import Error, Package
from pkgs_lib.grammar import parser
from pkgs_lib.winget import WinGetBackend, bridge_command, NO_APPLICATIONS


def row(name='Vendor.App', **values):
    return dict(id=name, name='Friendly name', source='winget', version='2.0',
                installed_version='1.0', versions=['2.0', '1.0'], update_available=True, **values)


class WinGetTests(unittest.TestCase):
    def backend(self, scope='user'):
        with patch('pkgs_lib.winget.which', return_value=None): return WinGetBackend(scope)

    def test_structured_identity_scope_and_ambiguous_inventory(self):
        data = [row(), dict(row('Other.App'), source=''), row('Both.App'), row('Machine.App')]
        b = self.backend()
        with patch('pkgs_lib.winget.bridge', return_value={'packages': data}), patch.object(
                b, 'probe_scope', side_effect=lambda name, scope: name == 'Both.App' or scope == ('machine' if name == 'Machine.App' else 'user')):
            rows = b.installed()
        self.assertEqual([p.name for p in rows], ['Vendor.App','Other.App','Both.App'])
        self.assertEqual(rows[0].details['scope'], 'user')
        self.assertTrue(all(p.details['disabled_reason'] for p in rows[1:]))
        self.assertEqual(outdated.candidates(b, rows[:1]), [dict(name='Vendor.App', current='1.0', candidate='2.0')])
        with self.assertRaisesRegex(Error, 'not uniquely'): b.transaction('uninstall', ['Both.App'], True)

    def test_literal_transactions_pins_and_multiple_ids(self):
        b = self.backend('machine')
        b.pins = {'Vendor.App': '1.0'}
        with patch('pkgs_lib.winget.bridge', side_effect=lambda action, **kw: {'packages':[row(kw['id'])]}):
            commands = policies.commands(b, 'install', ['Vendor.App','Second.App'], {}, yes=True)
        self.assertEqual(len(commands), 2)
        for command in commands:
            self.assertEqual(command[:2], ['winget.exe','install'])
            self.assertEqual(command[command.index('--scope')+1], 'machine')
            self.assertEqual(command[command.index('--source')+1], 'winget')
            self.assertIn('--exact', command)
            self.assertNotIn('--accept-source-agreements', command)
        self.assertEqual(commands[0][-3:], ['--version','1.0','--accept-package-agreements'])
        b.pins = {'Vendor.App': '9.0'}
        with patch('pkgs_lib.winget.bridge', return_value={'packages':[row()]}), self.assertRaisesRegex(Error, 'version is unavailable'):
            b.transaction('install', ['Vendor.App'], True)

    def test_manifest_scope_and_casefold(self):
        document = dict(schema=1, groups=[dict(manager='winget',scope='user',packages=[dict(name='Vendor.App', pin='1.0')])])
        self.assertEqual(manifests.validate(document)['groups'][0]['platforms'], ['windows'])
        document['groups'][0]['packages'].append(dict(name='vendor.app'))
        with self.assertRaisesRegex(Error, 'duplicate'): manifests.validate(document)
        self.assertEqual(scopes.scope_id(self.backend()), 'user')
        self.assertEqual(parser([]).parse_intermixed_args(['install','--manager','winget','--scope','machine','Vendor.App']).scope, 'machine')

    def test_query_failure_is_not_absence_or_display_parsing(self):
        b = self.backend()
        from types import SimpleNamespace
        with patch('pkgs_lib.winget.query', return_value=SimpleNamespace(returncode=NO_APPLICATIONS-2**32)):
            self.assertFalse(b.probe_scope('Vendor.App','user'))
        with patch('pkgs_lib.winget.query', return_value=SimpleNamespace(returncode=1,stderr='source failure',stdout='')), self.assertRaisesRegex(Error, 'scope query failed'):
            b.probe_scope('Vendor.App','user')

    def test_no_shell_interpolation_and_native_detection(self):
        import base64
        with patch('pkgs_lib.winget.powershell', return_value='powershell.exe'):
            command = bridge_command('search', query="a'; $(bad) \u00fc")
        self.assertIn('-File', command)
        self.assertEqual(json.loads(base64.b64decode(command[-1])), {'action':'search','query':"a'; $(bad) \u00fc"})
        with patch('pkgs_lib.detect.os.name', 'nt'), patch('pkgs_lib.detect.which', return_value='winget.exe'):
            self.assertTrue(detect.available('winget'))
            self.assertFalse(detect.available('apt'))
            self.assertEqual(detect.default_manager(), 'winget')

    def test_native_picker_details_and_unsupported_selection_use_no_shell(self):
        import io
        from contextlib import redirect_stdout, redirect_stderr
        from pkgs_lib import ui
        sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'lib/dots'))
        from interaction import Selector
        valid=Package('Vendor.App',description='Display name')
        unsupported=Package('Unknown',details=dict(disabled_reason='unproven scope'))
        choices=['Details','1. [ ] Vendor.App','2. [ ] Unknown — unproven scope',
                 '1. [ ] Vendor.App','Accept selection']
        out,err=io.StringIO(),io.StringIO()
        with patch.object(Selector,'pick',side_effect=choices),patch.object(ui,'which',return_value=None), \
             patch.object(ui,'enrich',return_value=(valid,'fixture notice')), \
             patch.object(ui.subprocess,'run',side_effect=AssertionError('native picker invoked a shell')), \
             redirect_stdout(out),redirect_stderr(err):
            selected=ui.native_pick([valid,unsupported],self.backend(),dict(color='never'))
        self.assertEqual(selected,[valid]);self.assertIn('fixture notice',out.getvalue())
        self.assertIn('unproven scope',err.getvalue())

    def test_shared_export_restore_and_upgrade_preserve_scope_and_pins(self):
        import io, os, tempfile
        from contextlib import redirect_stdout
        from types import SimpleNamespace
        from pkgs_lib import workflows
        installed={'Vendor.App':'1.0'};commands=[]
        def structured(action,**values):
            if action=='capabilities':return dict(schema=1,module='fixture')
            if action=='installed':return dict(packages=[dict(row(name),installed_version=version) for name,version in installed.items()]+[dict(row('Unknown'),source='')])
            return dict(packages=[row(values.get('id','Vendor.App'))])
        def mutate(argv,*args,**kwargs):
            commands.append(argv)
            if argv[1]=='install':installed[argv[argv.index('--id')+1]]=argv[argv.index('--version')+1]
            return 0
        cfg=dict(output='raw',color='never',policies={},_quiet_progress=True)
        args=SimpleNamespace(manager='winget',scope='user',global_scope=False,dry_run=True,json=True,
                             include_dependencies=False,pin_versions=True)
        with tempfile.TemporaryDirectory(prefix='winget-workflows-') as temporary, \
             patch.dict(os.environ,dict(HOME=temporary,XDG_CACHE_HOME=temporary)), \
             patch('pkgs_lib.winget.bridge',side_effect=structured), \
             patch.object(WinGetBackend,'probe_scope',side_effect=lambda name,scope:scope=='user'), \
             patch('pkgs_lib.manifests.available',return_value=True),patch('pkgs_lib.manifests.platform',return_value='windows'), \
             patch('pkgs_lib.workflows.streams.run',side_effect=mutate),redirect_stdout(io.StringIO()):
            document,failed=manifests.export(args,cfg)
            self.assertFalse(failed)
            packages=document['groups'][0]['packages']
            self.assertFalse(next(p for p in packages if p['name']=='Unknown')['enabled'])
            self.assertEqual(next(p for p in packages if p['name']=='Vendor.App')['pin'],'1.0')
            packages.append(dict(name='New.App',pin='1.0'))
            self.assertEqual(manifests.apply(document,cfg)['status'],'complete')
            self.assertEqual(len(commands),1)
            self.assertEqual(commands[0][commands[0].index('--scope')+1],'user')
            self.assertEqual(manifests.apply(document,cfg)['groups'][0]['status'],'unchanged')
            b=self.backend()
            upgrade=workflows.plan(b,'upgrade',[],cfg,yes=True)
            self.assertEqual(set(upgrade.names),{'Vendor.App','New.App'})
            self.assertEqual(workflows.apply(upgrade,cfg),0)
            self.assertEqual(len(commands),3)
            refresh=workflows.plan(b,'refresh',[],cfg)
            self.assertEqual(workflows.apply(refresh,cfg),0)
            self.assertEqual(commands[-1][1:4],['source','update','--name'])


if __name__ == '__main__': unittest.main()

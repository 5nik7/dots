"""Native Go upgrade selection without touching installed host tools."""
import copy
import json
import subprocess
import unittest
from unittest.mock import patch

import test_workflows as fixtures
from pkgs_lib import go_tools, outdated, workflows
from pkgs_lib.backends import Backend
from pkgs_lib.common import Error, Package


def tool(name, version='v1.0.0', module=None, reason=''):
    return Package(name, version, installed=True, installed_version=version,
                   details=dict(binary=name.rsplit('/',1)[-1],module=module or name,disabled_reason=reason))


class GoUpdates(unittest.TestCase):
    setUp=fixtures.Workflows.setUp

    def test_only_newer_native_targets_share_module_query_and_keep_flags(self):
        rows=[tool('example.org/shared/cmd/first',module='example.org/shared'),
              tool('example.org/shared/cmd/second',module='example.org/shared'),
              tool('example.org/current'),tool('example.org/newer','v1.2.0-rc.1'),
              tool('example.org/metadata','v1.0.0+incompatible')]
        versions={'example.org/shared':'v1.1.0','example.org/current':'v1.0.0',
                  'example.org/newer':'v1.1.0','example.org/metadata':'v1.0.0'}
        def query(argv,**kwargs):
            return subprocess.CompletedProcess(argv,0,json.dumps({'Version':versions[argv[-1][:-7]]}), '')
        cfg=copy.deepcopy(self.cfg);cfg['policies']={'go':{'upgrade':{'flags':['-trimpath']}}}
        backend=Backend('go')
        with patch.object(backend,'installed',return_value=rows),patch.object(outdated,'query',side_effect=query) as run:
            plan=workflows.plan(backend,'upgrade',[],cfg)
        self.assertEqual(plan.commands,[['go','install','-trimpath',p.name+'@latest'] for p in rows[:2]])
        self.assertEqual(plan.names,[p.name for p in rows[:2]])
        self.assertEqual(run.call_count,4)
        for call in run.call_args_list:
            self.assertIn('pkgs-go-query-',call.kwargs['cwd'])
            self.assertEqual(call.kwargs['env'],dict(GOTOOLCHAIN='local',GOWORK='off',GO111MODULE='on',GOFLAGS=''))

    def test_current_tools_do_nothing_and_query_failures_refuse_preparation(self):
        backend=Backend('go');rows=[tool('example.org/tool')]
        with patch.object(backend,'installed',return_value=rows):
            with patch.object(outdated,'query',return_value=subprocess.CompletedProcess([],0,'{"Version":"v1.0.0"}','')):
                plan=workflows.plan(backend,'upgrade',['tool'],self.cfg)
                self.assertEqual(plan.commands,[])
                self.assertEqual(plan.names,[])
            for result in (subprocess.CompletedProcess([],7,'','registry unavailable'),
                           subprocess.CompletedProcess([],0,'{}',''),
                           subprocess.CompletedProcess([],0,'{"Version":null}',''),
                           subprocess.CompletedProcess([],0,'{"Version":"garbage"}','')):
                with self.subTest(result=result),patch.object(outdated,'query',return_value=result):
                    with self.assertRaises(Error):workflows.plan(backend,'upgrade',[],self.cfg)

    def test_source_skips_and_custom_replacements_retain_their_semantics(self):
        rows=[tool('example.org/native'),tool('example.org/custom'),tool('example.org/held'),
              tool('example.org/source',reason='local development build or replaced module')]
        backend=Backend('go');cfg=copy.deepcopy(self.cfg)
        replacement=['go-global-update','-f','custom']
        cfg['policies']={'go':{'skip':['example.org/held'],
                             'packages':{'example.org/custom':{'upgrade':{'replace':[replacement]}}}}}
        with patch.object(backend,'installed',return_value=rows),patch.object(outdated,'query',
                return_value=subprocess.CompletedProcess([],0,'{"Version":"v1.0.0"}','')) as run:
            plan=workflows.plan(backend,'upgrade',[],cfg)
            self.assertEqual(plan.commands,[replacement])
            self.assertEqual(run.call_count,1)
            self.assertEqual(run.call_args.args[0][-1],'example.org/native@latest')
            self.assertEqual({p['package'] for p in plan.skipped},{'example.org/held','example.org/source'})
            with self.assertRaisesRegex(Error,'local development'):
                workflows.plan(backend,'upgrade',['source'],cfg)
            with self.assertRaisesRegex(Error,'Unknown or ambiguous'):
                workflows.plan(backend,'upgrade',['missing'],cfg)
        cfg['policies']={'go':{'upgrade':{'replace':[['custom-updater','{packages}']]}}}
        with patch.object(backend,'installed',return_value=rows),patch.object(outdated,'query',side_effect=AssertionError):
            plan=workflows.plan(backend,'upgrade',['native'],cfg)
        self.assertEqual(plan.commands,[['custom-updater','example.org/native']])
        with patch.object(go_tools,'installed',side_effect=AssertionError),patch.object(outdated,'query',side_effect=AssertionError):
            plan=workflows.plan(backend,'install',['example.org/native'],self.cfg)
        self.assertEqual(plan.commands,[['go','install','example.org/native@latest']])


if __name__=='__main__':unittest.main()

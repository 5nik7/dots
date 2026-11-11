"""Independent pip upgrades preserve hooks, statuses and truthful summaries."""
import contextlib
import io
import json
import os
import sys
import unittest
from unittest.mock import patch

import test_workflows as fixtures
from pkgs_lib import workflows, streams, upgrade_output
from pkgs_lib.backends import Backend


class PipPartial(unittest.TestCase):
    setUp = fixtures.Workflows.setUp

    def test_conflicts_do_not_mask_failures_or_inflate_diagnostic_counts(self):
        summary=upgrade_output.Output('pip',self.cfg)
        for name, rc, lines in (
                ('marshmallow',0,['ERROR: '+upgrade_output.PIP_CONFLICT,
                 'dataclasses-json 0.6.7 requires marshmallow<4,>=3.18, but you have marshmallow 4.4.0 which is incompatible.']),
                ('pyppeteer',0,['ERROR: '+upgrade_output.PIP_CONFLICT,
                 'scipy 1.18.1 requires numpy, which is not installed.']),
                ('w3lib',1,['error: subprocess-exited-with-error','error: build backend failed']),
                ('last',0,['Successfully installed last'])):
            summary.target=name; summary.begin_command(); summary.begin()
            formatter=streams.Formatter(io.StringIO(),dict(self.cfg,_manager='pip'),summary)
            for line in lines:
                formatter.feed(line[:20].encode()); formatter.feed((line[20:]+'\n').encode())
            summary.end_command(rc)
        out,err=io.StringIO(),io.StringIO()
        with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err): summary.result(1)
        self.assertIn('w3lib: subprocess-exited-with-error',err.getvalue())
        self.assertIn('w3lib: build backend failed',err.getvalue())
        self.assertEqual(err.getvalue().count('dependency conflicts;'),1)
        self.assertNotIn('does not currently',err.getvalue())
        self.assertNotIn('more diagnostic',err.getvalue())
        self.assertEqual(summary.extra,0)

    def test_unknown_failure_has_hint_without_success_tail_and_headers_are_scoped(self):
        summary=upgrade_output.Output('pip',self.cfg)
        summary.begin_command()
        summary.line('ERROR: successful command diagnostic','\n',sys.stderr);summary.end_command(0)
        summary.begin_command();summary.end_command(3)
        out,err=io.StringIO(),io.StringIO()
        with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err): summary.result(3)
        self.assertIn('--raw shows full failure output',err.getvalue())
        self.assertNotIn('successful command diagnostic',err.getvalue())
        summary.begin_command()
        summary.line('ERROR: '+upgrade_output.PIP_CONFLICT,'\n',sys.stderr)
        summary.line('ERROR: actual error immediately after conflict','\n',sys.stderr)
        summary.end_command(7)
        self.assertIn('actual error immediately after conflict',summary.errors)

    def test_failure_continues_and_summary_only_names_verified_successes(self):
        item = workflows.plan(Backend('pip'), 'upgrade', ['first','broken','last'], self.cfg)
        self.assertEqual(item.commands, [[sys.executable,'-m','pip','install','--upgrade',name]
                                       for name in ('first','broken','last')])
        calls = []
        def run(command, cfg, **kwargs):
            calls.append(command[-1])
            output = cfg['_upgrade_output']; output.begin(command)
            if command[-1] == 'broken':
                output.line('error: subprocess-exited-with-error','\n',sys.stderr)
                return 1
            return 0
        before = {n:(n,'1') for n in item.names}
        after = {n:(n,'2') for n in item.names}  # A failed target is never claimed successful.
        out, err = io.StringIO(), io.StringIO()
        with patch.object(streams,'run',side_effect=run), \
             patch.object(workflows,'installed_versions',side_effect=[before,after]), \
             contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(workflows.apply_compact(item,self.cfg),1)
        self.assertEqual(calls, ['first','broken','last'])
        self.assertEqual(item.failed,[('broken',1)])
        self.assertRegex(out.getvalue(),r'Updated:\s+first, last')
        self.assertIn('Failed: broken (exit 1)',out.getvalue())
        self.assertIn('broken: subprocess-exited-with-error',err.getvalue())

    def test_recipe_boundaries_and_flags_are_preserved(self):
        cfg = dict(self.cfg, policies={'pip': {'upgrade': {
            'before':[['manager-before','{packages}']], 'after':[['manager-after']], 'flags':['--pre']},
            'packages': {'broken': {'upgrade': {'before':[['package-before']],
                         'replace':[['package-replace']], 'after':[['package-after']]}}}}})
        item = workflows.plan(Backend('pip'),'upgrade',['broken','good'],cfg)
        calls = []
        def run(command,*args,**kwargs):
            calls.append(command)
            return 7 if command == ['package-replace'] else 0
        with patch.object(streams,'run',side_effect=run), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(workflows.apply(item,cfg),7)
        self.assertEqual(calls,[['manager-before','broken','good'],['package-before'],['package-replace'],
                                [sys.executable,'-m','pip','install','--upgrade','good','--pre']])
        self.assertEqual(item.completed,['good'])
        for fail in ('manager-before','manager-after'):
            calls.clear()
            with patch.object(streams,'run',side_effect=lambda cmd,*a,**k: calls.append(cmd) or (9 if cmd[0]==fail else 0)):
                self.assertEqual(workflows.apply(item,cfg),9)
            if fail == 'manager-before': self.assertEqual(len(calls),1)
            else: self.assertEqual(calls[-1],['manager-after'])

    def test_manager_replacement_remains_atomic(self):
        cfg=dict(self.cfg,policies={'pip': {'upgrade':{'replace':[['custom','{packages}']], 'after':[['after']]}}})
        item=workflows.plan(Backend('pip'),'upgrade',['first','last'],cfg)
        self.assertEqual(item.steps,[])
        with patch.object(streams,'run',return_value=6) as run:
            self.assertEqual(workflows.apply(item,cfg),6)
        self.assertEqual(run.call_count,1)
        self.assertEqual(run.call_args.args[0],['custom','first','last'])

    def test_interrupt_stops_remaining_targets(self):
        for code in (-2,130,143):
            item=workflows.plan(Backend('pip'),'upgrade',['first','last'],self.cfg)
            with patch.object(streams,'run',return_value=code) as run, self.assertRaises(KeyboardInterrupt):
                workflows.apply(item,self.cfg)
            self.assertEqual(run.call_count,1)

    @unittest.skipIf(os.name=='nt','POSIX fake interpreter executable')
    def test_raw_native_processes_continue_without_replaying_failed_batch(self):
        fake=self.bin/'python-fixture'
        fake.write_text('#!'+sys.executable+'\n'+'''import sys,json,os
with open(os.environ['TEST_CALLS'],'a') as f:f.write(json.dumps(sys.argv[1:])+'\\n')
print('error: fixture build failure' if sys.argv[-1]=='broken' else 'Successfully installed '+sys.argv[-1])
raise SystemExit(3 if sys.argv[-1]=='broken' else 0)
'''); fake.chmod(0o755)
        item=workflows.plan(Backend('pip'),'upgrade',['broken','good'],self.cfg)
        for command in item.commands: command[0]=str(fake)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(workflows.apply(item,dict(self.cfg,output='styled')),3)
        calls=[json.loads(line) for line in (self.home/'calls.jsonl').read_text().splitlines()]
        self.assertEqual([call[-1] for call in calls],['broken','good'])


if __name__ == '__main__': unittest.main()

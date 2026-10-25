#!/usr/bin/env python3
"""Detailed traces and session histories in disposable, public shell fixtures."""
from contextlib import ExitStack
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'lib/dots'))
from debug.fixtures import fixture
from debug.startup import one_run
from debug.changes import Snapshots,path_changes,source_location
from debug.record import snippet


class Tracing(unittest.TestCase):
    def setUp(self):
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.root,self.env,self.base=self.stack.enter_context(fixture(ROOT))
        self.stack.enter_context(patch.dict(os.environ,self.env,clear=True))
        self.home=Path(self.env['HOME'])
        for name in ('.zshenv','.zshrc','.bashrc'):
            (self.home/name).unlink();(self.home/name).write_text('')

    def setup_shell(self,shell):
        sample=self.home/'source ü.sh'
        sample.write_text('''export TRACE_DEMO=one
TRACE_DEMO=two
TRACE_SECRET=never-print-this-value
trace_function() { printf 'never-print-this-body'; }
:
trace_function() { :; }
:
alias trace_alias='never-print-this-alias'
alias trace_alias='true'
unalias trace_alias
PATH="$HOME/added:$PATH"
:
unset TRACE_DEMO
'''+('shopt -s nullglob\nshopt -u nullglob\n' if shell=='bash' else 'setopt globdots\nunsetopt globdots\n'))
        rc=self.home/('.bashrc' if shell=='bash' else '.zshrc')
        rc.write_text('source "$DOTS/lib/dots/shell/debug.bash"\n_dots_debug_event begin "$HOME/source ü.sh" source\nsource "$HOME/source ü.sh"\n_dots_debug_event end "$HOME/source ü.sh" source 0\n')
        return sample

    def test_native_deep_categories_and_no_unselected_values(self):
        for shell in ('bash','zsh'):
            if not shutil.which(shell):continue
            with self.subTest(shell=shell):
                self.setup_shell(shell)
                result=one_run(self.root,self.env,shell,False,30,True,self.base,'deep')
                self.assertEqual(result['exit_code'],0,result)
                changes=result['changes']
                self.assertTrue({'path','variables','functions','aliases','options'} <= {r['category'] for r in changes},changes)
                variable=[r for r in changes if r['name']=='TRACE_DEMO']
                self.assertTrue({'set','changed','unset'} <= {r['action'] for r in variable},variable)
                self.assertTrue(any(r['name']=='trace_function' and r['action']=='created' for r in changes))
                self.assertTrue(any(r['category']=='path' and r['operation']=='prepend' for r in changes))
                self.assertNotIn('never-print',json.dumps(result))
                self.assertTrue(all(r['precision']=='observation-interval' for r in changes))

    def test_selected_values_and_sensitive_names(self):
        self.setup_shell('bash')
        result=one_run(self.root,self.env,'bash',False,30,True,self.base,'deep','variables',('TRACE_DEMO','TRACE_SECRET'))
        self.assertEqual(result['exit_code'],0)
        self.assertIn('one',json.dumps([r for r in result['changes'] if r['name']=='TRACE_DEMO']))
        self.assertNotIn('never-print',json.dumps(result))
        self.assertTrue(any(r.get('redacted') for r in result['changes']))

    def test_boundary_changes_and_debug_conflict(self):
        self.setup_shell('bash')
        result=one_run(self.root,self.env,'bash',False,20,True,self.base,'changes')
        self.assertEqual(result['exit_code'],0)
        self.assertTrue(result['changes'])
        rc=self.home/'.bashrc';rc.write_text("trap ':' DEBUG\n"+rc.read_text())
        result=one_run(self.root,self.env,'bash',False,20,True,self.base,'deep')
        self.assertEqual(result['status'],'incomplete')
        self.assertTrue(any('existing DEBUG' in row['name'] for row in result['events']))

    def test_session_recording_stop_subshell_and_exit_cleanup(self):
        for shell in ('bash','zsh'):
            if not shutil.which(shell):continue
            with self.subTest(shell=shell):
                code=snippet(self.root,'start',shell)+'''
PATH="$HOME/recorded:$PATH"
false
TRACE_EXIT_STATUS=$?
python3 -B "$DOTS/lib/dots/debug_cli.py" path --json
( PATH="$HOME/child:$PATH"; : )
'''+snippet(self.root,'stop',shell)+'''
PATH="$HOME/unrecorded:$PATH"
python3 -B "$DOTS/lib/dots/debug_cli.py" path --json
printf '%s\\n' "$TRACE_EXIT_STATUS" "$DOTS_DEBUG_SESSION"
'''
                flags=['--noprofile','--norc','-c'] if shell=='bash' else ['-d','-f','-c']
                result=subprocess.run([shutil.which(shell),*flags,code],env=self.env,capture_output=True,text=True,timeout=20)
                self.assertEqual(result.returncode,0,result.stderr)
                lines=result.stdout.splitlines();first,second=map(json.loads,lines[:2])
                self.assertEqual(first['recording'],'active');self.assertEqual(second['recording'],'stopped')
                self.assertTrue(any(r['name'].endswith('/recorded') for r in first['history']))
                self.assertFalse(any(r['name'].endswith('/child') for r in second['history']))
                self.assertIn('unrecorded',second['note']);self.assertEqual(lines[2],'1')
                self.assertFalse(Path(lines[3]).exists())

    def test_path_diff_preserves_occurrences_and_reordering(self):
        rows=path_changes('/a::/a','/a:')
        self.assertEqual(rows[0]['operation'],'deduplicate');self.assertEqual(rows[0]['index'],2)
        self.assertEqual(path_changes('/a:/b','/b:/a')[0]['action'],'reordered')
        self.assertEqual([r['action'] for r in path_changes('/a:/b','/new:/b:/a')],['added','reordered'])

    def test_session_restart_and_repeated_stop(self):
        for shell in ('bash','zsh'):
            if not shutil.which(shell):continue
            with self.subTest(shell=shell):
                code=snippet(self.root,'start',shell)+snippet(self.root,'stop',shell)*2+snippet(self.root,'start',shell)+'''
PATH="$HOME/restarted:$PATH"
python3 -B "$DOTS/lib/dots/debug_cli.py" record status --json
'''+snippet(self.root,'stop',shell)
                flags=['--noprofile','--norc','-c'] if shell=='bash' else ['-d','-f','-c']
                result=subprocess.run([shutil.which(shell),*flags,code],env=self.env,capture_output=True,text=True,timeout=20)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(result.stderr,'')
                data=json.loads(result.stdout)
                self.assertEqual(data['status'],'active')
                self.assertTrue(any(r['name'].endswith('/restarted') for r in data['history']))

    def test_record_limit_survives_stop(self):
        from debug.record import history
        path=self.base/'events';pid=str(os.getpid())
        rows=[('baseline','1','inherited','0','/a',pid),('limit','2','','','',pid),('stop','3','','','',pid)]
        path.write_text(''.join('\0'.join(row)+'\0' for row in rows));path.chmod(0o600)
        with patch.dict(os.environ,{'DOTS_DEBUG_SESSION':str(path)}):
            data=history()
        self.assertEqual(data['status'],'stopped');self.assertTrue(data['truncated'])

    def test_snapshot_limits_and_no_definition_retention(self):
        collector=Snapshots(limit=1)
        for index,value in enumerate(('one','two','three')):
            collector.accept(('state-begin',str(index),'source','1','top','1'))
            collector.accept(('state-functions',str(index),'demo','function',value+'-secret','1'))
            collector.accept(('state-end',str(index),'','','','1'))
        self.assertEqual(len(collector.changes),1);self.assertTrue(collector.truncated)
        self.assertNotIn('secret',repr(collector.previous));self.assertNotIn('secret',repr(collector.changes))

    def test_compiler_maps_authored_lines(self):
        from startup import Compiler
        compiler=Compiler(self.root,'bash');body,_=compiler.build();mapping=compiler.source_map(body)
        self.assertTrue(mapping)
        for row in mapping:
            self.assertEqual(body.splitlines()[row['generated_start']-1],Path(row['file']).read_text().splitlines()[row['line']-1])
        directory=self.base/'generation';directory.mkdir();(directory/'manifest.json').write_text(json.dumps({'source_map':mapping}))
        first=mapping[0]
        self.assertEqual(source_location(str(directory/'bundle'),first['generated_start'],{}),(first['file'],first['line']))

    def test_record_code_and_read_only_status(self):
        command=[sys.executable,'-B',str(self.root/'lib/dots/debug_cli.py')]
        before=set(self.base.rglob('*'))
        for shell in ('bash','zsh','powershell'):
            result=subprocess.run([*command,'record','start','--shell',shell],env=dict(self.env,DOTS_COLOR='always'),capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr);self.assertNotIn('\x1b',result.stdout)
        result=subprocess.run([*command,'record','status','--json'],env=self.env,capture_output=True,text=True)
        self.assertEqual(json.loads(result.stdout)['status'],'unrecorded')
        self.assertEqual(set(self.base.rglob('*')),before)

    def test_invalid_source_maps_are_ignored(self):
        directory=self.base/'map';directory.mkdir();bundle=str(directory/'bundle')
        manifest=directory/'manifest.json'
        for value in ([],{'source_map':None},{'source_map':[{}, {'line':'bad'}]}):
            manifest.write_text(json.dumps(value))
            self.assertEqual(source_location(bundle,10,{}),(bundle,10))
        if hasattr(os,'mkfifo'):
            manifest.unlink();os.mkfifo(manifest)
            self.assertEqual(source_location(bundle,10,{}),(bundle,10))

    def test_private_scope_values_are_redacted(self):
        self.setup_shell('bash')
        rc=self.home/'.bashrc'
        rc.write_text('source "$DOTS/lib/dots/shell/debug.bash"\nprivate=1\nTRACE_PRIVATE=private-sentinel\n:\n')
        result=one_run(self.root,self.env,'bash',False,20,True,self.base,'deep','variables',('TRACE_PRIVATE',))
        self.assertEqual(result['exit_code'],0)
        self.assertNotIn('private-sentinel',json.dumps(result))

    def test_replaced_observer_and_session_conflict(self):
        self.setup_shell('bash')
        rc=self.home/'.bashrc';rc.write_text(rc.read_text()+"trap ':' DEBUG\n")
        result=one_run(self.root,self.env,'bash',False,20,True,self.base,'deep','path')
        self.assertEqual(result['status'],'incomplete')
        code="trap ':' DEBUG\n"+snippet(self.root,'start','bash')+'\ntrap -p DEBUG\n'
        result=subprocess.run([shutil.which('bash'),'--noprofile','--norc','-c',code],env=self.env,capture_output=True,text=True)
        self.assertIn('prevents recording',result.stderr)
        self.assertNotIn('_dots_record_tick',result.stdout)

    def test_nested_native_source_intervals(self):
        self.setup_shell('zsh')
        outer=self.home/'source ü.sh';inner=self.home/'inner.sh';inner.write_text('TRACE_INNER=yes\n:\n')
        outer.write_text('source "$HOME/inner.sh"\n:\n')
        result=one_run(self.root,self.env,'zsh',False,20,True,self.base,'deep','variables')
        self.assertEqual(result['exit_code'],0)
        events={e['id']:e for e in result['events']}
        inner_event=next(e for e in events.values() if e['kind']=='observed-source' and e['name']==str(inner))
        self.assertEqual(events[inner_event['parent_id']]['name'],str(outer))
        self.assertEqual(inner_event['precision'],'observed-interval')
        self.assertGreaterEqual(inner_event['duration_ms'],0)

    @unittest.skipUnless(shutil.which('pwsh') or shutil.which('powershell'),'PowerShell engine unavailable')
    def test_native_powershell_boundary_snapshot(self):
        profile=self.root/'shells/powershell/profile.ps1'
        profile.write_text('''$env:DOTS_DEBUG_DETAIL='changes'
. (Join-Path $env:DOTS 'lib/dots/shell/debug.ps1')
Write-DotsDebugEvent begin fixture source
$global:TRACE_DEMO='value-sentinel'
Set-Alias traceAlias Get-Date
function global:TraceFunction { 'body-sentinel' }
$env:PATH='extra'+[IO.Path]::PathSeparator+$env:PATH
Write-DotsDebugEvent end fixture source
''')
        result=one_run(self.root,self.env,'powershell',False,30,True,self.base,'changes')
        self.assertEqual(result['exit_code'],0)
        self.assertTrue(result['changes']);self.assertNotIn('sentinel',json.dumps(result))


if __name__=='__main__':unittest.main()

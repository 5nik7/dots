#!/usr/bin/env python3
"""Sequence arithmetic and terminal ownership; no real operations or settings."""
from fractions import Fraction
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'lib/dots'))
import progress
import test_progress as terminal_fixtures


class Model(unittest.TestCase):
    def setUp(self):
        quiet=patch.object(progress,'eligible',return_value=False)
        quiet.start(); self.addCleanup(quiet.stop)

    def test_equal_groups_with_unequal_nested_command_counts(self):
        with progress.sequence('Upgrade',3,unit='manager') as run:
            meter=run.meter
            with run.step('npm'):
                with progress.sequence('Commands',2) as commands:
                    with commands.step('first'):
                        self.assertEqual(meter.overall[0],0)
                    self.assertEqual(meter.overall[0],Fraction(1,6))
                    with commands.step('second'):pass
            self.assertEqual(meter.overall[0],Fraction(1,3))
            with run.step('pip'):
                with progress.sequence('Commands',4) as commands:
                    with commands.step('first'):pass
                    self.assertEqual(meter.overall[0],Fraction(5,12))
            self.assertEqual(meter.overall[0],Fraction(2,3))
            with run.step('go'):pass
        self.assertEqual(meter.overall[0],1)
        self.assertIsNone(progress._active_step)

    def test_artifact_activity_cannot_complete_opaque_command(self):
        with progress.sequence('Upgrade',2) as run:
            with run.step('Native command'):
                run.meter.update('First download',100,100)
                self.assertEqual(run.meter.overall[0],0)
                run.meter.update_spans([('Second download',None)],1,200)
                self.assertEqual(run.meter.overall[0],0)
            self.assertEqual(run.meter.overall[0],Fraction(1,2))
            with run.step('Verify'):
                self.assertLess(run.meter.overall[0],1)

    def test_measurements_and_lazy_discovery_stay_within_reserved_share(self):
        with progress.sequence('Run',2) as run:
            with run.step('Discover') as work:
                work.update('Scanning',1,2)
                self.assertEqual(run.meter.overall[0],Fraction(1,4))
                work.update('Scanning',0,2)
                self.assertEqual(run.meter.overall[0],Fraction(1,4))
            with run.step('Apply'):
                with progress.sequence('Discovered files',8,unit='file') as files:
                    self.assertEqual(run.meter.overall[0],Fraction(1,2))
                    with files.step('First') as work:
                        work.update('First file',1,2)
                        self.assertEqual(run.meter.overall[0],Fraction(17,32))
                        work.update('Invalid',1,'unknown')
                        self.assertEqual(run.meter.overall[0],Fraction(17,32))

    def test_cancellation_returned_as_data_freezes_parent_and_children(self):
        with progress.sequence('Run',2) as run:
            with run.step('Prepare'):pass
            with run.step('Apply'):
                with progress.sequence('Files',4) as files:
                    with files.step('First'):pass
                    files.cancel()
                    stopped=run.meter.overall[0]
            self.assertEqual(run.meter.overall[0],stopped)
        self.assertEqual(run.meter.overall[0],stopped)
        self.assertLess(stopped,1)

    def test_failure_and_recovery_do_not_finish_original_work(self):
        with self.assertRaisesRegex(ValueError,'failure'):
            with progress.sequence('Apply',3) as run:
                with run.step('Prepared'):pass
                try:
                    with run.step('Replacing'):raise ValueError('failure')
                except ValueError:
                    reached=run.meter.overall[0]
                    # Recovery can be nested under an active step or adopted by
                    # an existing renderer. It never credits the original work.
                    with run.step('Recovery',index=1):
                        with progress.sequence('Undo',2,recovery=True) as undo:
                            with undo.step('Restore') as item:item.update('Restore',1,1)
                            self.assertEqual(run.meter.overall[0],reached)
                            with undo.step('Verify'):pass
                        raise
        self.assertEqual(run.meter.overall[0],reached)
        self.assertIsNone(progress._active_step)

    def test_handled_failure_empty_and_skipped_sequences_resolve(self):
        with progress.sequence('Managers',2,unit='manager') as run:
            try:
                with run.step('failed'):raise ValueError('failed')
            except ValueError:pass
            with run.step('unchanged'):
                with progress.sequence('No commands',0):pass
        self.assertEqual(run.meter.overall[0],1)


@unittest.skipUnless(terminal_fixtures.BASH,'Bash unavailable')
class BashModel(unittest.TestCase):
    def check_model(self, body):
        script=('set -e\nsource '+shlex.quote(str(terminal_fixtures.LIB/'progress.bash'))+
                '\nDOTS_PROGRESS=none\n'+body)
        result=subprocess.run([terminal_fixtures.BASH,'--noprofile','--norc','-c',script],
                              stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=5)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout,'')
        self.assertEqual(result.stderr,'')

    def test_equal_groups_with_unequal_nested_command_counts(self):
        self.check_model('''
dots::progress_sequence_start Upgrade 3 manager
dots::progress_step_start npm
dots::progress_sequence_start Commands 2
dots::progress_step_start First
dots::progress_step_end
[[ $DOTS_PROGRESS_OVERALL == 166666 ]]
dots::progress_step_start Second
dots::progress_step_end
dots::progress_sequence_end
dots::progress_step_end
[[ $DOTS_PROGRESS_OVERALL == 333333 ]]
dots::progress_step_start pip
dots::progress_sequence_start Commands 4
dots::progress_step_start First
dots::progress_step_end
[[ $DOTS_PROGRESS_OVERALL == 416666 ]]
dots::progress_sequence_end
dots::progress_step_end
[[ $DOTS_PROGRESS_OVERALL == 666666 ]]
dots::progress_step_start go
dots::progress_step_end
dots::progress_sequence_end
[[ $DOTS_PROGRESS_OVERALL == 1000000 && $DOTS_PROGRESS_DEPTH == 0 ]]
''')

    def test_activity_measurements_and_reserved_lazy_work(self):
        self.check_model('''
dots::progress_sequence_start Run 2
dots::progress_step_start Discover
dots::progress_update Download 100 100
[[ $DOTS_PROGRESS_OVERALL == 0 ]]
dots::progress_measure Scan 1 2
[[ $DOTS_PROGRESS_OVERALL == 250000 ]]
dots::progress_measure Scan 0 2
[[ $DOTS_PROGRESS_OVERALL == 250000 ]]
dots::progress_step_end
dots::progress_step_start Apply
dots::progress_sequence_start Files 8 file
[[ $DOTS_PROGRESS_OVERALL == 500000 ]]
dots::progress_step_start First
dots::progress_measure File 1 2
[[ $DOTS_PROGRESS_OVERALL == 531250 ]]
dots::progress_update Download 100 100
[[ $DOTS_PROGRESS_OVERALL == 531250 ]]
dots::progress_step_end
[[ $DOTS_PROGRESS_OVERALL == 562500 ]]
dots::progress_sequence_end 1
dots::progress_step_end 1
dots::progress_sequence_end 1
[[ $DOTS_PROGRESS_OVERALL == 562500 && $DOTS_PROGRESS_DEPTH == 0 ]]
''')

    def test_failure_recovery_and_returned_cancellation_freeze(self):
        self.check_model('''
dots::progress_sequence_start Apply 3
dots::progress_step_start Prepared
dots::progress_step_end
dots::progress_step_start Replacing
dots::progress_step_end 1
[[ $DOTS_PROGRESS_OVERALL == 333333 ]]
recover() {
  dots::progress_step_start Restore
  dots::progress_measure Restore 1 1
  dots::progress_step_end
  dots::progress_step_start Verify
  dots::progress_step_end
}
dots::progress_recovery_run Undo 2 step recover
[[ $DOTS_PROGRESS_OVERALL == 333333 ]]
dots::progress_sequence_end 1
[[ $DOTS_PROGRESS_OVERALL == 333333 && $DOTS_PROGRESS_DEPTH == 0 ]]
dots::progress_sequence_start Run 2
dots::progress_step_start Prepare
dots::progress_step_end
dots::progress_step_start Apply
dots::progress_cancel
dots::progress_measure File 1 1
dots::progress_step_end
dots::progress_sequence_end
[[ $DOTS_PROGRESS_OVERALL == 500000 && $DOTS_PROGRESS_DEPTH == 0 ]]
''')


class Terminal(unittest.TestCase):
    setUp=terminal_fixtures.ProgressTests.setUp
    python=terminal_fixtures.ProgressTests.python
    bash=terminal_fixtures.ProgressTests.bash
    terminal=terminal_fixtures.ProgressTests.terminal

    def test_bash_slow_discovery_releases_terminal_before_status_heading(self):
        body=('source '+shlex.quote(str(terminal_fixtures.LIB/'git/status.bash'))+'''
JSON=0 GIT_VIEW=default ROOT=/fixture DOTS_UI_RESET=''
collect_status() { sleep .7; STATUS_DIRS=(); }
dots::heading() {
  if [[ -n ${DOTS_PROGRESS_FD:-} ]]; then
    printf 'heading raced active renderer\\n' >&2; exit 79
  fi
  printf '%s\\n' "$*"
}
status_main
''')
        code,data=self.terminal(self.bash(body),dict(self.env,DOTS_COLOR='never'))
        self.assertEqual(code,0,data)
        self.assertIn(b'Discovering repositories',data)
        self.assertIn(b'Git status\r\n',data)
        self.assertIn(b'0 repositories',data)

    def test_overall_and_current_rows_and_nested_prompt_suspension(self):
        body="""with progress.sequence('Upgrade',2,unit='manager') as run:
 with run.step('npm'):
  with progress.sequence('Commands',2) as commands:
   with commands.step('First'): pass
   with commands.step('Second'):
    progress.report('npm - Downloading ws',28,100)
    time.sleep(.65)
    with progress.permanent_output():
     with progress.permanent_output(): print('Prompt:')
     time.sleep(.2)
    time.sleep(.2)
 with run.step('pip'): pass
print('done')
"""
        code,data=self.terminal(self.python(body),dict(self.env,DOTS_COLOR='never'))
        self.assertEqual(code,0,data)
        plain=terminal_fixtures.ANSI.sub(b'',data)
        self.assertNotIn(b'Overall',plain);self.assertIn(b'25%',plain)
        self.assertNotIn(b'manager 1/2',plain);self.assertNotIn(b'step 2/2',plain)
        self.assertIn(b'2/2',plain)
        self.assertIn(b'28%',plain);self.assertIn(b'npm - Downloading ws',plain)
        self.assertNotRegex(data,terminal_fixtures.SGR)
        self.assertIn(b'\x1b[1A',data)
        self.assertTrue(data.endswith(b'done\r\n'))

    @unittest.skipUnless(shutil.which('tmux'),'private tmux terminal unavailable')
    def test_resize_erases_both_rows_without_erasing_previous_output(self):
        for kind in ('python','bash','common'):
            for bottom in (False,True):
                with self.subTest(kind=kind,bottom=bottom):self.resize_case(kind,bottom)

    def resize_case(self,kind,bottom=False):
        suffix=kind+('-bottom' if bottom else '')
        socket=self.root/('terminal-'+suffix+'.sock')
        env=dict(self.env,TMUX_TMPDIR=str(self.root),SHELL=terminal_fixtures.BASH,
                 DOTS_COLOR='never',DOTS_PROGRESS='both')
        def tmux(*args):
            result=subprocess.run(['tmux','-S',str(socket),'-f',os.devnull,*args],
                                  env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=5)
            return result
        self.addCleanup(lambda:tmux('kill-server'))
        program=self.root/('display-'+suffix+'.py');finish=self.root/('finish-'+suffix)
        program.write_text("""import progress,time,sys
from pathlib import Path
progress.configure()
print('KEEP',flush=True)
with progress.sequence('Run',2) as run:
 with run.step('Inspect'):
  progress.report('Long '+('x'*120))
  while not Path(sys.argv[1]).exists():time.sleep(.03)
 with run.step('Finalize'):pass
print('FINAL',flush=True)
time.sleep(5)
""")
        if bottom:
            program.write_text(program.read_text().replace("print('KEEP',flush=True)",
                               "print('before\\n'*10,end='');print('KEEP',flush=True)"))
        command=[sys.executable,'-B',str(program),str(finish)]
        if kind!='python':
            common=terminal_fixtures.PROJECT/'bin/lib/common.sh'
            if kind=='bash':
                body=('source '+shlex.quote(str(terminal_fixtures.LIB/'ui.bash'))+'\nsource '+
                      shlex.quote(str(terminal_fixtures.LIB/'progress.bash'))+"\nDOTS_PROGRESS_HUMAN=1\nprintf 'KEEP\\n'\n"+
                      "dots::progress_sequence_start Run 2\ndots::progress_step_start Inspect\n"+
                      'dots::progress_update '+shlex.quote('Long '+'x'*120)+'\n'+
                      'while [[ ! -e "$1" ]]; do sleep .03; done\n'+
                      "dots::progress_step_end\ndots::progress_step_start Finalize\ndots::progress_step_end\ndots::progress_sequence_end\n")
            else:
                body=('source '+shlex.quote(str(common))+"\nprintf 'KEEP\\n'\n"+
                      'while [[ ! -e "$1" ]]; do sleep .03; done &\nchild=$!\n'+
                      'spinner "$child" 1 '+shlex.quote('Long '+'x'*120)+'\nwait "$child"\n')
            body+="printf 'FINAL\\n'\nsleep 5\n"
            if bottom:body=body.replace("printf 'KEEP\\n'", "printf 'before\\n%.0s' {1..10}; printf 'KEEP\\n'")
            command=[terminal_fixtures.BASH,'--noprofile','--norc','-c',body,'progress-fixture',str(finish)]
        result=tmux('new-session','-d','-s','progress','-x','80','-y','12',
                    *command)
        self.assertEqual(result.returncode,0,result.stderr)
        def screen_until(check):
            deadline=time.monotonic()+6; text=''
            while time.monotonic()<deadline:
                text=tmux('capture-pane','-p','-S','-','-t','progress:0.0').stdout
                if check(text):return text
                time.sleep(.05)
            self.fail(text)
        overall = re.compile(r'^\[[-#]+\] 0%$', re.M)
        screen_until(lambda text:overall.search(text) and 'Long' in text)
        for width in (40,120):
            self.assertEqual(tmux('resize-window','-t','progress:0','-x',str(width),'-y','12').returncode,0)
            time.sleep(.2)
            text=screen_until(lambda text:overall.search(text) and 'Long' in text)
            rows=overall.findall(text)
            self.assertEqual(len(rows),1,text)
            self.assertEqual(len(rows[0]),width-1,text)
            self.assertEqual(text.count('Long'),1,text)
            self.assertIn('KEEP',text)
        finish.touch()
        text=screen_until(lambda text:'FINAL' in text)
        self.assertIn('KEEP',text)
        self.assertIsNone(overall.search(text))
        self.assertNotIn('Long',text)
        self.assertNotIn('xxxx',text)
        tmux('kill-server')


if __name__=='__main__':unittest.main()

"""Concise upgrade acceptance with fake managers and private terminals."""
import contextlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import test_workflows as fixtures
from pkgs_lib import cli, streams, upgrade_output, workflows
from pkgs_lib.backends import Backend


class Terminal(io.StringIO):
    def isatty(self): return True


class UpgradeOutput(unittest.TestCase):
    setUp = fixtures.Workflows.setUp
    args = fixtures.Workflows.args
    invoke = fixtures.Workflows.invoke

    def test_go_target_is_visible_before_output_and_through_quiet_builds(self):
        from unittest.mock import Mock
        meter=Mock();summary=upgrade_output.Output('go',self.cfg,meter)
        formatter=streams.Formatter(io.StringIO(),dict(self.cfg,_manager='go'),summary)
        with patch.object(upgrade_output.time,'monotonic',return_value=0):
            summary.begin(['go','install','-trimpath','example.org/first/v2@latest'])
            self.assertIn('Installing · first',meter.update.call_args.args[0])
            formatter.feed(b'go: downloading example.org/dependency v1.2.3\n')
            self.assertIn('Installing · first',meter.update.call_args.args[0])
        with patch.object(upgrade_output.time,'monotonic',return_value=65):
            summary.tick()
            self.assertIn('quiet 1:05 · Installing · first',meter.update.call_args.args[0])
            summary.begin(['go','install','example.org/cmd/second@latest'])
            self.assertIn('Installing · second',meter.update.call_args.args[0])
            self.assertNotIn('quiet',meter.update.call_args.args[0])
            self.assertNotIn('first',meter.update.call_args.args[0])
        self.assertNotIn('dependency',repr(meter.update.call_args_list))

    def test_npm_fetch_script_and_quiet_activity_without_log_noise(self):
        from unittest.mock import Mock
        meter=Mock();out=io.StringIO()
        summary=upgrade_output.Output('npm',self.cfg,meter)
        formatter=streams.Formatter(out,dict(self.cfg,_manager='npm'),summary)
        with patch.object(upgrade_output.time,'monotonic',return_value=0):
            summary.begin()
            formatter.feed(b'npm http fetch GET 200 https://user:secret@registry.invalid/@scope%2ftool?token=private 12ms\n')
            self.assertIn('Metadata · @scope/tool',meter.update.call_args.args[0])
            formatter.feed(b'npm http fetch GET 200 https://registry.invalid/@scope/tool/-/tool-2.0.tgz 45000ms\n')
            self.assertIn('Fetched · @scope/tool',meter.update.call_args.args[0])
            formatter.feed(b'npm info run @scope/tool@2.0.0 postinstall node_modules/@scope/tool node private-script.js\n')
            self.assertIn('Script postinstall · @scope/tool',meter.update.call_args.args[0])
            formatter.feed(b'npm notice run node private-script.js\n')
            self.assertIn('Script postinstall · @scope/tool',meter.update.call_args.args[0])
        with patch.object(upgrade_output.time,'monotonic',return_value=65):
            summary.tick()
            self.assertIn('quiet 1:05 · Script postinstall',meter.update.call_args.args[0])
            formatter.feed(b'npm info run @scope/tool@2.0.0 postinstall { code: 0, signal: null }\n')
            self.assertIn('Script finished · @scope/tool',meter.update.call_args.args[0])
            self.assertNotIn('quiet',meter.update.call_args.args[0])
        labels=repr(meter.update.call_args_list)
        for hidden in ('secret','private','https://','node_modules'):self.assertNotIn(hidden,labels)
        self.assertEqual(out.getvalue(),'')
        for line,stage in (
            ('npm http cache https://registry.invalid/hello 0ms (cache hit)','Cached'),
            ('npm http fetch GET https://registry.invalid/hello attempt 1 failed with ETIMEDOUT','Retrying'),
            ('npm http fetch GET 404 https://registry.invalid/hello/-/hello-2.0.tgz 20ms','Fetch failed'),
            ('npm http fetch POST 200 https://registry.invalid/-/npm/v1/security/audits/bulk 5ms','Auditing'),
        ):
            formatter.feed((line+'\n').encode());self.assertIn(stage,meter.update.call_args.args[0])
        self.assertNotIn('%',repr(meter.update.call_args_list))

    def test_npm_logging_environment_is_native_and_respects_overrides(self):
        for executable in ('npm','/tools/npm','npm.cmd'):
            env={};streams.npm_progress_environment([executable,'install','-g','--force','hello'],env)
            self.assertEqual(env,{'npm_config_loglevel':'info'})
        for key in ('npm_config_loglevel','NPM_CONFIG_LOGLEVEL'):
            env={key:'silent'};streams.npm_progress_environment(['npm','install','hello'],env)
            self.assertEqual(env,{key:'silent'})
        env={};streams.npm_progress_environment(['custom-script','npm'],env)
        self.assertEqual(env,{})
        fake=self.bin/'npm'
        fake.write_text('#!'+sys.executable+'\nimport os\nassert os.environ["npm_config_loglevel"]=="info"\nprint("npm http fetch GET 200 https://registry.invalid/hello 5ms",flush=True)\n')
        from unittest.mock import Mock
        meter=Mock();summary=upgrade_output.Output('npm',self.cfg,meter)
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            rc=streams.run(['npm','install','--global','hello'],dict(self.cfg,output='styled',_upgrade_output=summary))
        self.assertEqual(rc,0)
        self.assertIn('Metadata · hello',meter.update.call_args.args[0])

    def test_pip_bytes_package_partial_build_and_quiet_time(self):
        from unittest.mock import Mock
        meter=Mock();out=io.StringIO()
        summary=upgrade_output.Output('pip',self.cfg,meter)
        formatter=streams.Formatter(out,dict(self.cfg,_manager='pip'),summary)
        with patch.object(upgrade_output.time,'monotonic',return_value=0):
            summary.begin()
            formatter.feed(b'Collecting numpy\nDownloading https://user:secret@example.invalid/numpy-2.0.whl?token=private (8 MB)\n')
            formatter.feed(b'Progress 2097152 of 8388608\n')
            self.assertIn('25% 2.0MiB/8.0MiB',meter.update.call_args.args[0])
            self.assertIn('numpy',meter.update.call_args.args[0])
            self.assertNotIn('secret',repr(meter.update.call_args_list))
            self.assertNotIn('private',repr(meter.update.call_args_list))
            formatter.feed(b'Installing build dependencies ... ')
            formatter.flush_partial()
            self.assertIn('Build dependencies',meter.update.call_args.args[0])
            self.assertNotIn('25%',meter.update.call_args.args[0])
        with patch.object(upgrade_output.time,'monotonic',return_value=65):
            formatter.flush_partial();summary.tick()
            self.assertIn('quiet 1:05',meter.update.call_args.args[0])
            self.assertEqual(summary.last_activity,0)
            formatter.feed(b'done\nBuilding wheel for numpy (pyproject.toml) ... ')
            formatter.flush_partial()
            self.assertIn('Building · numpy',meter.update.call_args.args[0])
            self.assertNotIn('quiet',meter.update.call_args.args[0])
        self.assertEqual(out.getvalue(),'')

    def test_pip_unknown_total_and_native_environment_capabilities(self):
        from unittest.mock import Mock
        meter=Mock();summary=upgrade_output.Output('pip',self.cfg,meter)
        summary.line('Progress 1048576 of 0','\n',io.StringIO())
        self.assertIn('Downloaded 1.0MiB',meter.update.call_args.args[0])
        self.assertNotIn('%',meter.update.call_args.args[0])
        self.assertFalse(summary.pip_stage('Progress '+'9'*5000+' of 0'))
        command=[sys.executable,'-m','pip','install','--upgrade','hello']
        for version,expected in (('25.1','raw'),('26.2.2','raw'),('24.3',None)):
            env={}
            with patch('importlib.metadata.version',return_value=version):streams.pip_progress_environment(command,env)
            self.assertEqual(env.get('PIP_PROGRESS_BAR'),expected)
            self.assertEqual(env['PYTHONUNBUFFERED'],'1')
        env={'PIP_PROGRESS_BAR':'off'}
        streams.pip_progress_environment(command,env)
        self.assertEqual(env['PIP_PROGRESS_BAR'],'off')
        env={};streams.pip_progress_environment(['custom-recipe'],env)
        self.assertEqual(env,{})

    def test_runner_reports_silence_without_ending_process_or_changing_status(self):
        from unittest.mock import Mock
        fake=self.home/'quiet.py'
        fake.write_text("import sys,time\nprint('Collecting hello',flush=True)\ntime.sleep(.3)\nsys.exit(42)\n")
        meter=Mock();summary=upgrade_output.Output('pip',self.cfg,meter)
        with patch.object(summary,'tick',wraps=summary.tick) as tick, \
             contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            rc=streams.run([sys.executable,str(fake)],dict(self.cfg,output='styled',_upgrade_output=summary))
        self.assertEqual(rc,42)
        self.assertGreaterEqual(tick.call_count,3)

    def test_raw_and_ordinary_redirects_do_not_request_pip_progress(self):
        fake=self.home/'output.py';fake.write_text("print('fixture output')")
        with patch.object(streams,'pip_progress_environment',side_effect=AssertionError('changed native environment')), \
             patch.object(streams,'npm_progress_environment',side_effect=AssertionError('changed native environment')):
            with tempfile.TemporaryFile(mode='w+') as out, tempfile.TemporaryFile(mode='w+') as err, \
                 contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
                for mode in ('auto','raw'):
                    self.assertEqual(streams.run([sys.executable,str(fake)],dict(self.cfg,output=mode)),0)

    def test_apt_mirror_fragments_cannot_join_summary_and_keep_failure(self):
        out,err=io.StringIO(),io.StringIO()
        with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
            summary=upgrade_output.Output('apt',self.cfg)
            formatter=streams.Formatter(err,dict(self.cfg,_manager='apt'),summary)
            for chunk in (b'main:', b'\nE: Failed to fetch https://fixture/Packages.gz ',
                          b'File has unexpected size (10 != 11). Mirror sync in progress?\n'):
                formatter.feed(chunk);formatter.flush_partial()
                self.assertEqual(err.getvalue(),'')
            formatter.feed(b'',final=True);summary.result(100)
        self.assertIn('failed (exit 100)',out.getvalue())
        self.assertNotIn('main:',out.getvalue()+err.getvalue())
        self.assertIn('mirror sync',err.getvalue())
        self.assertIn('pkgs refresh',err.getvalue())

    def test_long_bulk_output_has_one_result_per_manager_and_continues_failure(self):
        fake = self.home/'manager.py'
        fake.write_text('''import sys
manager=sys.argv[1]
if manager=='apt':
    for i in range(400): print('(Reading database ... '+str(i%101)+'%',end='\\r')
    print('Setting up fixture...')
elif manager=='npm':
    print('npm error code E404',file=sys.stderr)
    print('npm error 404 Not Found - @openai/codex-linux-arm64',file=sys.stderr)
    print('npm error 404',file=sys.stderr)
    sys.exit(42)
elif manager=='uv-tool':
    for i in range(8): print('Nothing to upgrade')
elif manager=='pip':
    for i in range(500): print('Requirement already satisfied: package'+str(i))
''')
        backends = [Backend(name) for name in ('apt','npm','uv-tool','pip')]
        plans = [workflows.Plan(b,'upgrade',names=['package'+str(i) for i in range(80)],
                 commands=[[sys.executable,str(fake),b.name]],
                 skipped=[dict(package='held'+str(i),reason='not proven pip-owned') for i in range(15)] if b.name=='pip' else [])
                 for b in backends]
        for width in (40,80,120):
            out,err = Terminal(),Terminal()
            with patch.dict(os.environ,COLUMNS=str(width),DOTS_PROGRESS='never'), \
                 contextlib.redirect_stdout(out),contextlib.redirect_stderr(err), \
                 patch.object(workflows.scopes,'bulk',return_value=[(b.name,None) for b in backends]), \
                 patch.object(workflows,'available',return_value=True), \
                 patch.object(workflows.scopes,'make',side_effect=backends), \
                 patch.object(workflows,'plan',side_effect=plans):
                rc = workflows.upgrade(self.args('upgrade'),dict(self.cfg,output='auto'))
            self.assertEqual(rc,1)
            text = out.getvalue()+err.getvalue()
            self.assertEqual(text.count('Upgrade packages'),1)
            self.assertEqual(text.count('complete'),3)
            self.assertEqual(text.count('failed (exit 42)'),1)
            self.assertIn('15 skipped',text)
            self.assertIn('@openai/codex-linux-arm64',''.join(text.split()))
            for noise in ('Reading database','Requirement already','Nothing to upgrade','Command','held0','package0'):
                self.assertNotIn(noise,text)
            self.assertLess(len(text.splitlines()),14,text)

    def test_unknown_failure_warning_and_prompt_survive_chunk_boundaries(self):
        out,err = Terminal(),Terminal()
        with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err),patch.dict(os.environ,DOTS_PROGRESS='never'):
            summary = upgrade_output.Output('npm',self.cfg)
            formatter = streams.Formatter(err,dict(self.cfg,_manager='npm'),summary)
            for chunk in (b'warn',b'ing: fixture advisory\r',b'\nPassword: '):
                formatter.feed(chunk)
            formatter.flush_partial()
            self.assertIn('Password:',err.getvalue())
            formatter.feed(b'\nRegistry refused the requested package',final=True)
            summary.result(43)
        self.assertIn('fixture advisory',err.getvalue())
        self.assertIn('Registry refused the requested package',err.getvalue())
        self.assertIn('failed (exit 43)',out.getvalue())

    def test_diagnostics_are_bounded_and_never_define_success(self):
        out,err = io.StringIO(),io.StringIO()
        with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
            summary = upgrade_output.Output('npm',self.cfg)
            formatter = streams.Formatter(err,dict(self.cfg,_manager='npm'),summary)
            formatter.feed(b'complete\n'+b''.join(('error: detail '+str(i)+'\n').encode() for i in range(200)))
            summary.result(44)
        self.assertNotIn('complete',out.getvalue())
        self.assertIn('failed (exit 44)',out.getvalue())
        self.assertIn('198 more diagnostic lines',err.getvalue())
        self.assertLess(len(err.getvalue().splitlines()),5)
        self.assertEqual(len(summary.errors),2)
        self.assertEqual(len(summary.tail),3)

    def test_redirect_raw_and_preview_keep_commands_and_full_output(self):
        for options in ([],['--raw']):
            result = self.invoke('upgrade','--manager','npm','--global','hello',*options)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('npm install --global -- hello',result.stdout)
            self.assertIn('Installed packages',result.stdout)
            self.assertIn('warning: fixture detail',result.stderr)
        path = self.home/'config/pkgs/config.json';path.parent.mkdir(parents=True)
        path.write_text(json.dumps({'output':'styled'}))
        (self.home/'calls.jsonl').unlink()
        preview = self.invoke('upgrade','--manager','npm','--global','hello','--dry-run')
        self.assertEqual(preview.returncode,0,preview.stderr)
        self.assertIn('npm install --global -- hello',preview.stdout)
        self.assertIn('Dry run',preview.stdout)
        self.assertFalse((self.home/'calls.jsonl').exists())
        brief = self.invoke('upgrade','--manager','npm','--global','hello')
        self.assertEqual(brief.returncode,0,brief.stderr)
        self.assertIn('complete',brief.stdout)
        self.assertNotIn('npm install',brief.stdout)
        self.assertNotIn('Installed packages',brief.stdout)
        self.assertIn('fixture detail',brief.stderr)
        raw = self.invoke('upgrade','--manager','npm','--global','hello','--raw')
        self.assertIn('Installed packages',raw.stdout)

    def test_empty_plans_and_launch_errors_have_accurate_results(self):
        out,err=Terminal(),Terminal()
        with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err),patch.dict(os.environ,DOTS_PROGRESS='never'):
            empty=workflows.Plan(Backend('npm'),'upgrade',skipped=[dict(package='held',reason='policy')])
            self.assertEqual(workflows.apply_upgrade(empty,dict(self.cfg,output='auto')),0)
            broken=workflows.Plan(Backend('npm'),'upgrade',commands=[[str(self.home/'missing-executable')]])
            self.assertEqual(workflows.apply_upgrade(broken,dict(self.cfg,output='auto')),1)
        self.assertIn('unchanged · 1 skipped',out.getvalue())
        self.assertIn('failed (exit 1)',out.getvalue())
        self.assertIn('missing-executable',''.join(err.getvalue().split()))
        self.assertNotIn('complete',out.getvalue())
        self.assertFalse((self.home/'calls.jsonl').exists())

    @unittest.skipUnless(os.name=='posix','private PTYs require POSIX')
    def test_real_pty_widths_progress_and_child_terminal_restore(self):
        import fcntl
        import pty
        import select
        import signal
        import struct
        import termios
        from resources import cells
        fake = self.bin/'npm'
        fake.write_text('#!'+sys.executable+'\n'+'''import sys,time,termios,os
state=termios.tcgetattr(0)
state[1] &= ~termios.ONLCR
termios.tcsetattr(0,termios.TCSANOW,state)
is_go=os.path.basename(sys.argv[0])=='go'
print('go: downloading example.org/dependency v1.2.3' if is_go else 'npm http fetch GET 200 https://registry.invalid/hello/-/hello-2.0.tgz 1200ms',flush=True)
for i in range(21):
    print('(Reading database ... '+str(i*5)+'%',end='\\r',flush=True)
    time.sleep(.03)
if not is_go:print('npm info run hello@2.0.0 postinstall node_modules/hello private-script',flush=True)
time.sleep(.25)
print('Installed packages')
sys.exit(int(__import__('os').environ.get('TEST_EXIT','0')))
''')
        go=self.bin/'go';go.write_text(fake.read_text());go.chmod(0o755)
        scenarios = [(width,mode,0,manager) for width in (40,80,120) for mode in ('always','never') for manager in ('npm','go')]
        scenarios += [(80,'never',code,manager) for code in (17,130) for manager in ('npm','go')]
        for width,mode,expected,manager in scenarios:
            with self.subTest(width=width,mode=mode,expected=expected,manager=manager):
                pid,fd=pty.fork()
                if pid==0:
                    try:
                        fcntl.ioctl(1,termios.TIOCSWINSZ,struct.pack('HHHH',24,width,0,0))
                        os.environ.update(COLUMNS=str(width),TERM='xterm-256color',DOTS_COLOR=mode,
                                          NO_COLOR='1',DOTS_ICONS='never',DOTS_PROGRESS='auto')
                        os.environ['TEST_EXIT']=str(expected if expected!=130 else 0)
                        before=termios.tcgetattr(0)
                        if expected==130:
                            import threading
                            threading.Timer(.3,lambda:os.kill(os.getpid(),signal.SIGINT)).start()
                        if manager=='go':
                            plan=workflows.Plan(Backend('go'),'upgrade',names=['example.org/hello'],
                                                commands=[['go','install','example.org/hello@latest']])
                            with patch.object(workflows,'plan',return_value=plan):
                                rc=cli.main(['upgrade','--manager','go','hello'])
                        else:rc=cli.main(['upgrade','--manager','npm','--global','hello'])
                        assert termios.tcgetattr(0)==before, 'terminal settings drifted'
                        print('RESTORED',flush=True)
                        os._exit(rc)
                    except BaseException as error:
                        print(repr(error),flush=True);os._exit(99)
                data=b'';status=None;start=time.monotonic()
                try:
                    while time.monotonic()-start<8:
                        if select.select([fd],[],[],.05)[0]:
                            try: chunk=os.read(fd,65536)
                            except OSError: break
                            if not chunk: break
                            data+=chunk
                        if status is None:
                            ended,state=os.waitpid(pid,os.WNOHANG)
                            if ended: status=state
                    if status is None:
                        ended,state=os.waitpid(pid,os.WNOHANG)
                        if not ended:
                            os.kill(pid,signal.SIGKILL);state=os.waitpid(pid,0)[1]
                        status=state
                finally: os.close(fd)
                self.assertEqual(os.waitstatus_to_exitcode(status),expected,data.decode(errors='replace'))
                text=data.decode()
                self.assertIn('RESTORED\r\n',text)
                if expected==0:
                    self.assertNotIn('Reading database',text)
                    self.assertNotIn('registry.invalid',text)
                    self.assertNotIn('private-script',text)
                    if manager=='npm':
                        self.assertIn('Fetched',text)
                        self.assertIn('Script postinstall',text)
                    else:
                        self.assertIn('Installing',text)
                        self.assertIn('hello',text)
                        self.assertNotIn('dependency',text)
                    self.assertIn('complete',text)
                else:
                    self.assertNotIn('complete',text)
                self.assertEqual('\x1b[' in text,mode=='always')
                plain=re.sub(r'\x1b\[[0-9;]*m','',text)
                self.assertTrue(all(cells(line)<=width for line in plain.splitlines()),plain)


if __name__=='__main__': unittest.main()

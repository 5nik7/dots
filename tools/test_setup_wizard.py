#!/usr/bin/env python3
"""Real terminal cancellation and the setup data/approval boundaries."""
import errno
import json
import os
from pathlib import Path
import select
import shutil
import signal
import sys
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import test_installation as fixtures


class SetupWizard(unittest.TestCase):
    setUp = fixtures.InstallationTests.setUp
    write = fixtures.InstallationTests.write
    cli = fixtures.InstallationTests.cli

    @unittest.skipIf(os.name=='nt','POSIX PTY acceptance; native PowerShell is separately pending')
    def terminal(self, width, answers, color='never'):
        import fcntl,pty,struct,termios
        tools = self.base/'terminal tools';tools.mkdir(exist_ok=True)
        for name in ('bash','python3','cat','stty','tput'):
            path = shutil.which(name)
            if path and not (tools/name).exists(): (tools/name).symlink_to(path)
        env = dict(self.env,TERM='xterm-256color',COLUMNS=str(width),PATH=str(tools),DOTS_COLOR=color)
        (self.repo/'logo.txt').write_text('DOTS\n')
        pid,fd = pty.fork()
        if pid == 0:
            os.execve(sys.executable,[sys.executable,'-B',str(fixtures.ROOT/'lib/dots/files/install.py'),'install'],env)
        fcntl.ioctl(fd,termios.TIOCSWINSZ,struct.pack('HHHH',30,width,0,0))
        output=b'';stage=0;deadline=time.monotonic()+20
        try:
            while time.monotonic()<deadline:
                if select.select([fd],[],[],0.1)[0]:
                    try: part=os.read(fd,65536)
                    except OSError as error:
                        if error.errno==errno.EIO:break
                        raise
                    if not part:break
                    output+=part
                    if stage<len(answers) and answers[stage][0] in output:
                        os.write(fd,answers[stage][1]);stage+=1
            else: self.fail('wizard did not finish: '+output.decode(errors='replace'))
            _,status=os.waitpid(pid,0)
            self.assertEqual(os.waitstatus_to_exitcode(status),0,output.decode(errors='replace'))
            self.assertEqual(stage,len(answers),output.decode(errors='replace'))
            return output.decode(errors='replace')
        finally:
            os.close(fd)
            try:os.kill(pid,signal.SIGKILL)
            except ProcessLookupError:pass

    def test_terminal_default_cancel_at_three_widths(self):
        for width in (40,80,120):
            text=self.terminal(width,[(b'Number',b'8\n')])
            self.assertEqual(text.count('\x1b[2J'),1)
            self.assertIn('DOTS',text);self.assertIn('Save choices: no',text)
            self.assertIn('cancelled',text)
            self.assertFalse((self.home/'.state').exists())
            self.assertFalse(self.target.exists())

    def test_two_reviews_and_final_decline(self):
        text=self.terminal(80,[(b'Number',b'1\n'),(b'Prepare these components',b'y\n'),
                               (b'Apply these managed changes?',b'n\n')])
        self.assertIn('Final managed changes',text)
        self.assertIn('cancelled',text)
        self.assertFalse(self.target.exists())

    def test_profile_abbreviation_and_requested_terminal_colors(self):
        self.repo.rename(self.home/'dots');self.repo=self.home/'dots';self.env['DOTS']=str(self.repo)
        for name in ('termux','linux','wsl','windows'):
            directory=self.repo/'profiles'/name;directory.mkdir(parents=True)
            (directory/'profile.json').write_text(json.dumps(dict(schema=1,id=name)))
        for width in (40,80,120):
            output=self.terminal(width,[(b'Number',b'8\n')],color='always')
            self.assertIn('~/dots/profiles/',output)
            self.assertNotIn(str(self.home),output)
            self.assertIn('\x1b[92mSelect components, prepare optional work, then review managed changes.\x1b[0m',output)
            self.assertIn('\x1b[96mSetup preferences\x1b[0m',output)
        output=self.terminal(80,[(b'Number',b'8\n')])
        self.assertNotIn('\x1b[92m',output);self.assertNotIn('\x1b[96m',output)

    def test_data_and_invalid_interaction_are_inert(self):
        result=self.cli('install','--dry-run','--json','--component','core')
        self.assertEqual(json.loads(result.stdout)['components'],['core'])
        self.assertNotIn('\x1b',result.stdout)
        self.cli('install','--interactive','--json',ok=False)
        self.cli('install','--non-interactive',ok=False)
        self.assertFalse((self.home/'.state').exists())

    def test_saved_choices_are_opt_in_and_keep_other_profile_fields(self):
        from install import Installation
        from setup_wizard import defaults, save_plan
        from config_values import Controls
        from config_refresh import effective, after_save
        shutil.copytree(fixtures.ROOT/'default',self.repo/'default')
        for name in ('termux','linux','wsl','windows'):
            directory=self.repo/'profiles'/name;directory.mkdir(parents=True)
            (directory/'profile.json').write_text(json.dumps(dict(schema=1,id=name,settings={},files={})))
        with patch.dict(os.environ,self.env,clear=True):
            installation=Installation(self.repo)
            args=SimpleNamespace(action='install',component=['core'],resource=None,packages=None,fonts=None,
                font_target=None,with_dependencies=None,save_choices=False)
            defaults(self.repo,installation,args)
            installation.plan_install(args.component,args.resource)
            before=list(installation.operations)
            save_plan(self.repo,installation,args)
            self.assertEqual(before,installation.operations)
            args.save_choices=True
            previous=effective(self.repo)
            save_plan(self.repo,installation,args)
            profile=args.profile_directory/'profile.json'
            self.assertNotIn('setup',json.loads(profile.read_text()).get('apps',{}))
            installation.apply('install')
            values=Controls(self.repo).values['apps']['setup']
            self.assertEqual(values['components'],['core'])
            self.assertEqual(json.loads(profile.read_text())['settings'],{})
            with patch('config_refresh.refresh',side_effect=AssertionError('setup preferences refreshed live consumers')):
                result=after_save(self.repo,previous)
            self.assertEqual(result['consumers'],[dict(app='setup',status='next invocation')])

    def test_files_menu_handoff_never_adds_approval(self):
        import menu_cli
        for name in ('install','uninstall'):
            shutil.copy2(fixtures.ROOT/'bin'/('dots-files-'+name),self.repo/'bin'/('dots-files-'+name))
            action=next(a for a in menu_cli.FAMILIES['files'] if a.id==name)
            with patch.dict(os.environ,self.env,clear=True),patch.object(menu_cli,'run_action',return_value=0) as run:
                menu_cli.invoke(self.repo,action,None)
            self.assertEqual(run.call_args.kwargs['kind'],'terminal')
            self.assertNotIn('--yes',run.call_args.args[0])
            self.assertNotIn('--non-interactive',run.call_args.args[0])

    def test_horizontal_gradient_preserves_rows_and_plain_fallback(self):
        from text_gradient import gradient
        lines=['DOTS','DOTS']
        self.assertEqual(gradient(lines,{},horizontal=True),lines)
        colored=gradient(lines,dict(hint='#112233',info='#445566',accent='#778899'),horizontal=True)
        self.assertEqual(colored[0],colored[1])
        self.assertIn('\x1b[38;2;17;34;51m',colored[0])
        self.assertIn('\x1b[38;2;119;136;153m',colored[0])


if __name__=='__main__':unittest.main(verbosity=2)

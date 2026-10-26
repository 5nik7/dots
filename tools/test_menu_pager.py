#!/usr/bin/env python3
"""Read-only output, private capture and native terminal reader acceptance."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

from test_menus import MenuFixture, NativeMenuFixture
import menu_pager


class Pager(MenuFixture):
    def test_fitted_height_counts_content_wrapping_and_reader_controls(self):
        source=self.base/'rows.txt'
        for body,expected in [('title\n\none\n',6),('title\nExit status: 7\n\none\n',7),('title\n\n'+'x'*35,7),('title\n\n\x1b[32m'+'x'*34+'\x1b[0m\n',6),('title\n\n'+'界'*17+'e\u0301',7),('title\n\n'+'x'*33+'\t',7),('title\n\n'+'x'*33+'\x01',7),('title\n\n'+'line\n'*200,21)]:
            source.write_text(body)
            self.assertEqual(menu_pager.report_size(source,(40,24)),(36,expected),repr(body[:50]))
        source.write_text('title\n\none\n')
        self.assertEqual(menu_pager.report_size(source,(80,24),'fzf-wrap'),(72,9))
        self.assertEqual(menu_pager.report_size(source,(10,5)),(9,4))

    def test_review_status_is_separate_from_command_result(self):
        for closed,reviewed in ((True,True),(False,False),(KeyboardInterrupt(),False)):
            with patch('menu_pager.reader',side_effect=closed if isinstance(closed,Exception) or isinstance(closed,KeyboardInterrupt) else None,return_value=closed):
                result=menu_pager.run_report(self.command('raise SystemExit(7)'))
            self.assertEqual(result,menu_pager.OutputResult(7,reviewed))

    @unittest.skipIf(os.name == 'nt', 'native POSIX terminal')
    def test_short_report_stays_open_outside_tmux_without_private_path(self):
        import pty, select, signal, time
        if not shutil.which('less'): self.skipTest('less unavailable')
        report = 'SHORT REPORT\n\uf00c current\n\U000f0001 icon\n\U00100000 icon\ncontrol: \x01'
        child = 'print(' + repr(report) + ');raise SystemExit(7)'
        code = "import sys;from menu_pager import run_output;sys.exit(run_output([sys.executable,'-c'," + repr(child) + "]))"
        pid, master = pty.fork()
        if pid == 0:
            os.execve(sys.executable, [sys.executable,'-B','-c',code], dict(self.env, LESSCHARSET='ascii', LESSUTFCHARDEF='E000-F8FF:b'))
        alive = True
        try:
            data = b''; deadline = time.monotonic()+10
            while b'Back q' not in data and time.monotonic()<deadline:
                if select.select([master],[],[],.1)[0]: data += os.read(master,65536)
            self.assertIn(b'SHORT REPORT',data);self.assertIn(b'Exit status: 7',data)
            for glyph in ('\uf00c','\U000f0001','\U00100000'): self.assertIn(glyph.encode(),data)
            self.assertNotIn(b'<U+',data);self.assertIn(b'^A',data)
            self.assertIn(b'Back q',data);self.assertEqual(os.waitpid(pid,os.WNOHANG),(0,0))
            os.write(master,b'=');time.sleep(.1)
            while select.select([master],[],[],.05)[0]: data += os.read(master,65536)
            self.assertNotIn(b'dots-output-',data)
            os.write(master,b'q');deadline=time.monotonic()+10
            while time.monotonic()<deadline:
                done,status=os.waitpid(pid,os.WNOHANG)
                if done:
                    alive=False;self.assertEqual(os.waitstatus_to_exitcode(status),7);break
                time.sleep(.05)
            self.assertFalse(alive);self.assertFalse(list(self.base.glob('dots-output-*')))
        finally:
            if alive: os.kill(pid,signal.SIGKILL);os.waitpid(pid,0)
            os.close(master)

    def test_capture_once_complete_streams_literal_arguments_and_cleanup(self):
        marker=self.base/'runs'; cwd=self.base/'cwd ü';cwd.mkdir()
        argv=self.command('import os,sys\nfrom pathlib import Path\np=Path(sys.argv[1]);p.write_text(p.read_text()+"x" if p.exists() else "x")\nprint(os.getcwd(),flush=True)\nprint(sys.argv[2:],flush=True)\nprint(os.environ["VALUE"],flush=True)\nprint("tail"*10000,file=sys.stderr)\nsys.exit(7)\n')
        paths=[];completed=[]
        def read(path):
            paths.append(path)
            data=path.read_text();self.assertIn('Exit status: 7',data);self.assertIn(str(cwd),data)
            self.assertIn('$(touch sentinel)',data);self.assertIn('literal env',data)
            self.assertIn('tail'*10000,data);self.assertEqual(completed,[7])
            if os.name!='nt': self.assertEqual(path.stat().st_mode & 0o777,0o600)
            raise KeyboardInterrupt
        with patch('menu_pager.reader',side_effect=read):
            self.assertEqual(menu_pager.run_output([*argv,str(marker),'','$(touch sentinel)'],title='Fixture',cwd=cwd,environment=dict(self.env,VALUE='literal env'),completed=completed.append),7)
        self.assertEqual(marker.read_text(),'x');self.assertFalse(paths[0].exists());self.assertFalse(paths[0].parent.exists())
        self.assertFalse((cwd/'sentinel').exists())

    def test_empty_and_missing_command_status(self):
        contents=[]
        with patch('menu_pager.reader',side_effect=lambda p:contents.append(p.read_text())):
            self.assertEqual(menu_pager.run_output(self.command('pass')),0)
            self.assertEqual(menu_pager.run_output([str(self.base/'missing')]),2)
        self.assertIn('(No output.)',contents[0]);self.assertIn('Exit status: 2',contents[1])

    def test_reader_clears_hooks_history_and_uses_fzf_without_actions(self):
        path=self.base/'literal ü $(touch x)';path.write_bytes(b'first\nlast\0literal\n')
        with patch.dict(os.environ,LESS='-F',LESSOPEN='bad',LESSHISTFILE='/bad',FZF_DEFAULT_OPTS='--bind=start:execute(bad)'), patch('menu_pager.shutil.which',side_effect=lambda name, **kwargs:'/tools/'+name), patch('menu_pager.subprocess.call',return_value=1) as less, patch('menu_pager.subprocess.run',return_value=subprocess.CompletedProcess([],130)) as fzf:
            menu_pager.reader(path)
        self.assertNotIn(str(path),less.call_args.args[0])
        self.assertEqual(less.call_args.kwargs['stdin'].name,str(path))
        self.assertNotIn('-F',less.call_args.args[0]);self.assertEqual(less.call_args.kwargs['env']['LESSHISTFILE'],'-')
        self.assertEqual(less.call_args.kwargs['env']['LESSOPEN'],'');self.assertEqual(less.call_args.kwargs['env']['LESSSECURE'],'1')
        self.assertEqual(fzf.call_args.kwargs['env']['FZF_DEFAULT_OPTS'],'')
        self.assertEqual(fzf.call_args.kwargs['input'],b'first\0last\\0literal\0')
        self.assertFalse(any('execute' in arg or 'preview' in arg for arg in fzf.call_args.args[0]))
        self.assertEqual(fzf.call_args.kwargs['stdout'],subprocess.DEVNULL)
        with patch('menu_pager.shutil.which',return_value=None),self.assertRaisesRegex(ValueError,'install less or FZF'):
            menu_pager.reader(path)

    def test_passed_presentation_environment_survives_capture(self):
        command=self.command('import os,json;print(json.dumps([os.environ[k] for k in ("DOTS_COLOR","DOTS_ICONS","DOTS_PROGRESS")]))')
        contents=[]
        with patch('menu_pager.reader',side_effect=lambda p:contents.append(p.read_text())):
            self.assertEqual(menu_pager.run_output(command,environment=dict(self.env,DOTS_COLOR='always',DOTS_ICONS='always')),0)
        self.assertIn('["always", "always", "never"]',contents[0])


class NativePager(NativeMenuFixture):
    def reader_probe(self, name='less'):
        executable=shutil.which(name)
        if not executable:self.skipTest(name+' unavailable')
        directory=self.base/('probe-'+name);directory.mkdir()
        record=self.base/(name+'-geometry.json')
        script=directory/name
        script.write_text('#!'+sys.executable+'\nimport json,os,sys\nfrom pathlib import Path\nPath('+repr(str(record))+').write_text(json.dumps(list(os.get_terminal_size(2))))\nos.execv('+repr(executable)+', ['+repr(executable)+', *sys.argv[1:]])\n')
        script.chmod(0o700)
        return str(directory)+os.pathsep+self.env['PATH'],record

    def test_actual_reader_height_tracks_short_wrapped_and_long_output(self):
        import time
        from menu_tmux import TmuxContext
        path,record=self.reader_probe()
        marker=self.base/'runs'
        for width in (40,80,120):
            self.fcntl.ioctl(self.first[1],self.termios.TIOCSWINSZ,self.struct.pack('HHHH',24,width,0,0))
            context=TmuxContext.capture(client=self.first[2]);deadline=time.monotonic()+3
            while context.verify()!=(width,24) and time.monotonic()<deadline:time.sleep(.05)
            for report,expected in (('SHORT\n',6),('x'*(width*9//10-1)+'\n',7),('FIRST\n'+'middle\n'*60+'LAST\n',21)):
                child=self.command('from pathlib import Path\nimport sys\np=Path('+repr(str(marker))+');p.write_text(p.read_text()+"x" if p.exists() else "x")\nsys.stdout.write('+repr(report)+')')
                self.drain(self.first[1]);self.drain(self.second[1])
                p=self.worker("import os,json,sys;from menus import run_action;from menu_tmux import TmuxContext;sys.exit(run_action(json.loads(os.environ['COMMAND']),kind='output',context=TmuxContext.capture(client=os.environ['CLIENT'])))",COMMAND=json.dumps(child),PATH=path)
                self.receive(self.first[1],b'Back q')
                self.assertEqual(json.loads(record.read_text()),[width*9//10-2,expected-2])
                self.assertNotIn(b'Back q',self.drain(self.second[1]))
                if expected==21:os.write(self.first[1],b'G');self.receive(self.first[1],b'LAST')
                os.write(self.first[1],b'q');_,err=p.communicate(timeout=15)
                self.assertEqual(p.returncode,0,err)
        self.assertEqual(marker.read_text(),'xxxxxxxxx')
        self.assertFalse(list(self.base.glob('dots-menu-*')))

    def test_fitted_fzf_reader_cancel_is_not_successful_review(self):
        path,record=self.reader_probe('fzf')
        for report,height in (('SHORT\n',7),('x'*88+'WRAPPEDEND\n',8)):
            self.drain(self.first[1])
            p=self.worker("import os;from unittest.mock import patch;from menu_tmux import TmuxContext;from menu_pager import page_text;\nwith patch('menu_pager.backends',return_value=iter(['fzf-wrap'])): print(page_text(os.environ['REPORT'],context=TmuxContext.capture(client=os.environ['CLIENT'])))",PATH=path,REPORT=report)
            data=self.receive(self.first[1],b'Search output:')
            self.assertEqual(json.loads(record.read_text()),[88,height])
            if height==8:
                data+=self.receive(self.first[1],b'WRAPPEDEND') if b'WRAPPEDEND' not in data else b''
                self.assertIn(b'WRAPPEDEND',data)
            os.write(self.first[1],b'\x1b');out,err=p.communicate(timeout=15)
            self.assertEqual(p.returncode,0,err);self.assertEqual(out.strip(),'False')

    def test_document_selection_host_closes_before_fitted_reader(self):
        path,record=self.reader_probe()
        child=self.command('from menu_pager import page_text\ninput("SELECT DOCUMENT: ")\npage_text("DOCUMENT BODY\\n",title="Page",defer=True)\n')
        p=self.worker("import os,json,sys;from menus import run_action;from menu_tmux import TmuxContext;sys.exit(run_action(json.loads(os.environ['COMMAND']),kind='document',context=TmuxContext.capture(client=os.environ['CLIENT'])))",COMMAND=json.dumps(child),PATH=path)
        self.receive(self.first[1],b'SELECT DOCUMENT:');self.assertFalse(record.exists())
        os.write(self.first[1],b'\r');data=self.receive(self.first[1],b'Back q')
        self.assertIn(b'DOCUMENT BODY',data);self.assertEqual(json.loads(record.read_text()),[88,4])
        os.write(self.first[1],b'q');_,err=p.communicate(timeout=15);self.assertEqual(p.returncode,0,err)
        self.assertFalse(list(self.base.glob('dots-menu-*')))

    def test_failed_less_refits_fzf_without_running_command_again(self):
        path,record=self.reader_probe('fzf')
        less=Path(path.split(os.pathsep)[0])/'less'
        less.write_text('#!'+sys.executable+'\nraise SystemExit(2)\n');less.chmod(0o700)
        marker=self.base/'runs'
        child=self.command('from pathlib import Path\np=Path('+repr(str(marker))+');p.write_text(p.read_text()+"x" if p.exists() else "x")\nprint("ONE RUN")')
        # The FZF probe needs a terminal; only backend discovery is stubbed.
        p=self.worker("import os,json;from unittest.mock import patch;from menu_tmux import TmuxContext;from menus import review_output;\nwith patch('menu_pager.backends',return_value=iter(['less','fzf-wrap'])): print(review_output(json.loads(os.environ['COMMAND']),context=TmuxContext.capture(client=os.environ['CLIENT'])))",COMMAND=json.dumps(child),PATH=path)
        self.receive(self.first[1],b'Search output:')
        self.assertEqual(json.loads(record.read_text()),[88,7])
        os.write(self.first[1],b'\r');out,err=p.communicate(timeout=15)
        self.assertEqual(p.returncode,0,err);self.assertIn('code=0, reviewed=True',out)
        self.assertEqual(marker.read_text(),'x');self.assertFalse(list(self.base.glob('dots-menu-*')))

    def test_loading_window_cancellation_never_opens_reader(self):
        path,record=self.reader_probe()
        child=self.command('import time\ntime.sleep(30)\nprint("NOT READY")')
        p=self.worker("import os,json;from menus import review_output;from menu_tmux import TmuxContext;print(review_output(json.loads(os.environ['COMMAND']),context=TmuxContext.capture(client=os.environ['CLIENT'])))",COMMAND=json.dumps(child),PATH=path)
        self.receive(self.first[1],b'Loading Dots output')
        self.control('display-popup','-C','-c',self.first[2])
        out,err=p.communicate(timeout=15);self.assertEqual(p.returncode,0,err)
        self.assertIn('code=130, reviewed=False',out);self.assertFalse(record.exists())
        self.assertFalse(list(self.base.glob('dots-menu-*')))

    def test_popup_reader_renders_private_use_glyphs_and_escapes_controls(self):
        report = '\x1b[32m\uf00c current\x1b[0m\n\U000f0001 icon\n\U00100000 icon\ncontrol: \x01'
        child=self.command('print(' + repr(report) + ')')
        p=self.worker("import os,json,sys;from menus import run_action;from menu_tmux import TmuxContext;sys.exit(run_action(json.loads(os.environ['COMMAND']),kind='output',context=TmuxContext.capture(client=os.environ['CLIENT'])))",COMMAND=json.dumps(child))
        data=self.receive(self.first[1],b'Back q')
        for glyph in ('\uf00c','\U000f0001','\U00100000'): self.assertIn(glyph.encode(),data)
        self.assertNotIn(b'<U+',data);self.assertIn(b'^A',data)
        self.assertNotIn('current'.encode(),self.drain(self.second[1]))
        os.write(self.first[1],b'q');_,err=p.communicate(timeout=15)
        self.assertEqual(p.returncode,0,err)

    def test_popup_close_after_output_preserves_child_failure(self):
        child=self.command('print("REPORT COMPLETE",flush=True)\nraise SystemExit(7)')
        p=self.worker("import os,json,sys;from menus import run_action;from menu_tmux import TmuxContext;sys.exit(run_action(json.loads(os.environ['COMMAND']),kind='output',context=TmuxContext.capture(client=os.environ['CLIENT'])))",COMMAND=json.dumps(child))
        self.receive(self.first[1],b'Back q');self.control('display-popup','-C','-c',self.first[2])
        _,err=p.communicate(timeout=15);self.assertEqual(p.returncode,7,err)
        self.assertFalse(list(self.base.glob('dots-menu-*')))
        # Closing a host sends a hangup; reader capture lives inside that host.
        self.assertFalse(list(self.base.glob('dots-output-*')))

    def test_fzf_reader_scroll_search_and_return_without_less(self):
        # Patch only this worker's reader probe; the tmux process uses installed FZF.
        p=self.worker("import os,sys;from menu_tmux import TmuxContext;from menus import run_action;code=\"import shutil;from unittest.mock import patch;from menu_pager import page_text;real=shutil.which;\\nwith patch('menu_pager.shutil.which',side_effect=lambda n, **kw:None if n=='less' else real(n, **kw)): page_text('FIRST MARKER\\\\n'+'middle\\\\n'*100+'LAST MARKER\\\\n')\";sys.exit(run_action([sys.executable,'-B','-c',code],context=TmuxContext.capture(client=os.environ['CLIENT'])))")
        self.receive(self.first[1],b'Search output:');os.write(self.first[1],b'LAST MARKER')
        self.receive(self.first[1],b'LAST MARKER');os.write(self.first[1],b'\x1b')
        _,err=p.communicate(timeout=15);self.assertEqual(p.returncode,0,err)
        self.assertFalse(list(self.base.glob('dots-output-*')))


if __name__=='__main__': unittest.main()

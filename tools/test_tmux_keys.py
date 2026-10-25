#!/usr/bin/env python3
"""Shared tmux key browser: private servers, native FZF, and owned terminals."""
import fcntl
import json
import os
from pathlib import Path
import pty
import re
import select
import shlex
import shutil
import signal
import struct
import subprocess
import termios
import time
import unittest
from unittest.mock import patch
import test_keys

ROOT=test_keys.ROOT
TMUX=shutil.which('tmux');FZF=shutil.which('fzf');BASH=shutil.which('bash')


class TmuxKeys(unittest.TestCase):
    setUp=test_keys.Keys.setUp
    cli=test_keys.Keys.cli

    def tool(self,name,body):
        path=self.base/'commands'/name
        if path.is_symlink():path.unlink()
        path.write_text('#!'+BASH+'\n'+body);path.chmod(0o700);return path

    def native(self,socket,*args):
        p=subprocess.run([TMUX,'-S',str(socket),*args],env=self.env,cwd=self.home,capture_output=True,text=True,timeout=10)
        self.assertEqual(p.returncode,0,p.stderr);return p.stdout

    def test_routes_completion_and_no_execution_for_help(self):
        for native in (False,True):
            prefix=[test_keys.sys.executable,'-B',str(self.root/'lib/dots/cli.py')] if native else [str(self.root/'bin/dots')]
            for route in (['keys'],['menu','tmux','keys']):
                p=subprocess.run([*prefix,*route,'--help'],env=self.env,capture_output=True,text=True)
                self.assertEqual(p.returncode,0,p.stderr);self.assertIn('--print',p.stdout)
            completion=[*prefix,'__complete',*(['keys',''] if native else ['bash','2','--','dots','keys',''])]
            p=subprocess.run(completion,env=self.env,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr);self.assertIn('nvim',p.stdout);self.assertIn('zsh',p.stdout)

    @unittest.skipUnless(TMUX,'tmux unavailable')
    def test_native_notes_and_prefixes_without_starting_server(self):
        socket=self.base/'private.socket'
        try:
            self.native(socket,'-f',os.devnull,'new-session','-d','-s','fixture',BASH+' --noprofile --norc')
            self.native(socket,'set-option','-t','fixture','prefix','C-a')
            self.native(socket,'bind-key','-T','prefix','-N','Find café $(touch sentinel)','x','display-message','unused')
            self.native(socket,'bind-key','-T','custom table','-N','Line\nTab\tEscape\x1b[31m','y','display-message','unused')
            self.tool('tmux','exec '+shlex.quote(TMUX)+' -S '+shlex.quote(str(socket))+' "$@"\n')
            pane=self.native(socket,'display-message','-p','-t','fixture','#{pane_id}').strip()
            self.env['TMUX_PANE']=pane
            with patch.dict(os.environ,self.env,clear=True):
                data=json.loads(self.cli('tmux','--json').stdout)
            row=next(r for r in data['rows'] if r['mode']=='prefix' and r['key']=='x')
            self.assertEqual(row['display'],'Ctrl+A → x');self.assertIn('café',row['description'])
            self.assertFalse((self.home/'sentinel').exists())
        finally:subprocess.run([TMUX,'-S',str(socket),'kill-server'],env=self.env,capture_output=True,timeout=10)
        data=json.loads(self.cli('tmux','--json').stdout)
        self.assertEqual(data['rows'],[]);self.assertTrue(data['coverage'][0]['notes'])
        p=subprocess.run([TMUX,'-N','-S',str(socket),'list-sessions'],env=self.env,capture_output=True,timeout=5)
        self.assertNotEqual(p.returncode,0)

    def test_missing_fzf_and_unsupported_popup(self):
        directory=self.root/'config/yazi';directory.mkdir(parents=True)
        (directory/'keymap.toml').write_text('[[mgr.prepend_keymap]]\non="<C-g>"\nrun="help"\ndesc="Open help"\n')
        self.assertIn('FZF unavailable',self.cli('yazi','--browse').stdout)
        self.tool('fzf','printf old-fzf\n');self.env['TMUX']='owned,1,0'
        self.assertIn('does not support --popup',self.cli('yazi','--browse',code=2).stderr)

    def test_print_is_safe_at_terminal_widths(self):
        directory=self.root/'config/yazi';directory.mkdir(parents=True)
        (directory/'keymap.toml').write_text('[[mgr.prepend_keymap]]\non="<C-g>"\nrun="help"\ndesc="Long description café with spaces that must wrap on narrow screens"\n')
        for width in (40,80,120):
            for color in ('never','always'):
                master,slave=pty.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',30,width,0,0))
                p=subprocess.Popen([test_keys.sys.executable,'-B',str(self.root/'lib/dots/keys_cli.py'),'yazi','--print'],env=dict(self.env,DOTS_COLOR=color,DOTS_ICONS='never'),stdin=slave,stdout=slave,stderr=slave)
                os.close(slave);output=bytearray()
                try:
                    deadline=time.monotonic()+15
                    while time.monotonic()<deadline:
                        if select.select([master],[],[],.1)[0]:
                            try:chunk=os.read(master,65536)
                            except OSError:break
                            if not chunk:break
                            output.extend(chunk)
                        elif p.poll() is not None:break
                    self.assertEqual(p.wait(timeout=2),0)
                    text=output.decode();plain=re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]','',text)
                    self.assertIn('Ctrl+G',plain);self.assertIn('café',plain)
                    for line in plain.splitlines():self.assertLessEqual(len(line),width,line)
                    if color=='never':self.assertNotIn('\x1b',text)
                finally:
                    if p.poll() is None:p.kill();p.wait()
                    os.close(master)

    @unittest.skipUnless(TMUX and FZF,'tmux/FZF unavailable')
    def test_repository_binding_opens_one_native_popup(self):
        binding=next(l for l in (ROOT/'config/tmux/tmux.conf').read_text().splitlines() if 'Browse keybinding categories' in l)
        self.assertIn('run-shell -b',binding);self.assertNotIn('display-popup',binding)
        for name,source in (('tmux',TMUX),('fzf',FZF)):
            p=self.base/'commands'/name
            if p.exists():p.unlink()
            p.symlink_to(source)
        # The tmux server and all spawned processes receive only fixture paths.
        cfg=self.base/'tmux.conf';cfg.write_text('set -g default-shell '+shlex.quote(BASH)+'\n'+binding+'\nbind D display-message -d 1500 DOTS_PICKER_CLOSED\n')
        socket=self.base/'popup.socket';self.native(socket,'-f',str(cfg),'new-session','-d','-s','fixture',BASH+' --noprofile --norc')
        pid,master=pty.fork()
        if pid==0:os.execve(TMUX,[TMUX,'-S',str(socket),'attach','-t','fixture'],self.env)
        output=bytearray();reaped=False
        def receive(needle):
            deadline=time.monotonic()+20
            while needle not in output and time.monotonic()<deadline:
                if select.select([master],[],[],.1)[0]:
                    try:output.extend(os.read(master,65536))
                    except OSError:break
            self.assertIn(needle,output[-12000:])
        try:
            fcntl.ioctl(master,termios.TIOCSWINSZ,struct.pack('HHHH',30,100,0,0))
            receive(b'fixture')
            for cancel in (b'\x1b',b'\x03'):
                for stage in ('categories','apps','bindings'):
                    with self.subTest(cancel=cancel,stage=stage):
                        output.clear();os.write(master,b'\x02?');receive(b'Keybinding categories')
                        if stage!='categories':
                            os.write(master,b'Apps');time.sleep(.4);os.write(master,b'\r');receive(b'Keybinding apps')
                        if stage=='bindings':
                            os.write(master,b'tmux');time.sleep(.4);os.write(master,b'\r');receive(b'Keybindings')
                        output.clear();os.write(master,cancel)
                        deadline=time.monotonic()+1
                        while time.monotonic()<deadline:
                            if select.select([master],[],[],.1)[0]:output.extend(os.read(master,65536))
                        self.assertNotIn(b'returned 130',output)
                        self.assertNotIn('returned 130',self.native(socket,'show-messages'))
                        os.write(master,b'\x02D');receive(b'DOTS_PICKER_CLOSED')
            output.clear();os.write(master,b'\x02?');receive(b'Keybinding categories')
            os.write(master,b'All');time.sleep(.4);os.write(master,b'\r');output.clear();receive(b'Keybindings')
            os.write(master,b'\x03');time.sleep(.3);output.clear();os.write(master,b'\x02D');receive(b'DOTS_PICKER_CLOSED')
            self.native(socket,'detach-client','-s','fixture')
            os.waitpid(pid,0);reaped=True
        finally:
            if not reaped:
                os.kill(pid,signal.SIGKILL);os.waitpid(pid,0)
            os.close(master)
            subprocess.run([TMUX,'-S',str(socket),'kill-server'],env=self.env,capture_output=True,timeout=10)

    def test_launcher_normalizes_only_cancellation(self):
        binding=next(l for l in (ROOT/'config/tmux/tmux.conf').read_text().splitlines() if 'Browse keybinding categories' in l)
        launcher=shlex.split(binding)[-1]
        for shell in (BASH,shutil.which('zsh')):
            if not shell:continue
            for status in (0,2,7,127,130):
                self.tool('dots',f'printf fixture-diagnostic >&2\nexit {status}\n')
                env=dict(self.env,PATH=str(self.base/'commands')+os.pathsep+self.env['PATH'])
                result=subprocess.run([shell,'-c',launcher],env=env,cwd=self.home,capture_output=True,text=True,timeout=10)
                self.assertEqual(result.returncode,0 if status==130 else status)
                self.assertEqual(result.stderr,'fixture-diagnostic')

    def test_direct_cli_keeps_cancellation_status(self):
        directory=self.root/'config/yazi';directory.mkdir(parents=True)
        (directory/'keymap.toml').write_text('[[mgr.prepend_keymap]]\non="q"\nrun="quit"\n')
        self.tool('fzf','if [[ $1 == --help ]]; then printf -- "--popup\\n"; else exit 130; fi\n')
        self.env['TMUX']='owned,1,0'
        self.cli('yazi','--browse',code=130)


if __name__=='__main__':unittest.main()

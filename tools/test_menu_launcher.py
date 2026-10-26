#!/usr/bin/env python3
"""Curated launcher and shortcuts in owned repositories, servers and terminals."""
from contextlib import redirect_stdout, redirect_stderr
import io
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

from test_menus import MenuFixture, NativeMenuFixture, ROOT
import menu_cli
from interaction import SelectionEnded, SelectionEvent
from menus import Entry, Menu


def checkout(base):
    root = base / 'repo'; root.mkdir(exist_ok=True)
    shutil.copytree(ROOT / 'bin', root / 'bin', symlinks=True)
    shutil.copytree(ROOT / 'lib/dots', root / 'lib/dots', ignore=shutil.ignore_patterns('__pycache__'))
    return root


class LauncherContracts(MenuFixture):
    def setUp(self):
        super().setUp(); self.root = checkout(self.base)

    def invoke(self, *args):
        output, error = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(error):
            code = menu_cli.main(list(args))
        return code, output.getvalue(), error.getvalue()

    def test_data_is_fixed_static_and_never_executes_providers_or_fzf(self):
        with patch('subprocess.run', side_effect=AssertionError('provider executed')), patch('menu_cli.terminal', return_value=False):
            for mode in ([], ['--print'], ['--json']):
                code, out, err = self.invoke(*mode)
                self.assertEqual((code, err), (0, '')); self.assertIn('keys', out)
            doc = json.loads(self.invoke('--json')[1])
            self.assertEqual((doc['schema'], doc['menu'], doc['title']), (1, 'dots', 'Dots menu'))
            self.assertEqual([r['id'] for r in doc['items']], 'keys tmux files git theme themes anodize debug profile profiles wiki env'.split())
            for item in doc['items']:
                self.assertEqual(set(item), {'id','label','description','available','reason'})
            self.assertEqual([r['id'] for r in json.loads(self.invoke('--json','--query','anodize')[1])['items']], ['anodize'])

    def test_action_map_uses_existing_safe_routes(self):
        expected = {
            'tmux': [('sessions','menu tmux sessions','','session'),('keys','menu tmux keys','--browse','popup')],
            'files': [('browse','files browse','','terminal'), *[(n,'files '+n,'','output') for n in ('list','history','sources')]],
            'git': [('status','git status','','output'),('info','git info','','output'),('submodules','git submodules','','submenu'),('wiki','git wiki','','submenu'),('publish','git publish','--all','terminal'),('sync','git sync','','sync')],
            'git/submodules': [('list','git submodules','','output'),('info','git submodules info','','output'),('status','git submodules status','','output')],
            'git/wiki': [('status','git wiki status','','output'),('info','git wiki info','','output'),('publish','git wiki publish','--all','terminal'),('sync','git wiki sync','','sync')],
            'theme': [('show','theme show','','output'),('switcher','theme switcher','','terminal'),('files','theme files browse','','terminal'),('backgrounds','theme bg switcher','','terminal')],
            'themes': [('list','themes list','','output'),('switcher','themes switcher','','terminal'),('plugins','themes plugins','','submenu')],
            'themes/plugins': [(n,'themes plugins '+n,'','output') for n in ('list','doctor')],
            'anodize': [(n,'anodize '+n,'--interactive','terminal') for n in ('create','edit','preview','apply')]+[('list','anodize list','','output')],
            'debug': [(n,'debug '+n,'','output') for n in ('check','startup','path','cache')],
            'profile': [(n,'profile '+n,'','output') for n in ('show','paths','layers','files','commands','env','check')],
            'profiles': [(n,'profiles '+n,'','output') for n in ('list','check')],
            'wiki': [('browse','wiki browse','','document'),('list','wiki list','','output'),('check','wiki check','','output')],
        }
        for family, rows in expected.items():
            self.assertEqual([(a.id,' '.join(a.route),' '.join(a.options),a.kind) for a in menu_cli.actions(family)[:-1]], rows)
            self.assertEqual(menu_cli.actions(family)[-1].id, 'help')
            for action in menu_cli.actions(family):
                if action.kind in ('submenu','session','sync'): continue
                with patch('menu_cli.run_action', return_value=0) as run:
                    self.assertFalse(menu_cli.invoke(self.root,action,None))
                self.assertEqual(run.call_args.args[0][-len(action.route+action.options):],list(action.route+action.options))
                self.assertEqual(run.call_args.kwargs['kind'],action.kind)
                self.assertNotIn('--yes',run.call_args.args[0])

    def test_navigation_preserves_queries_context_help_and_workflow_return(self):
        visits=[]
        def select(menu, **kwargs):
            visits.append((menu.id, kwargs['query']))
            self.assertTrue(kwargs['compact'])
            self.assertEqual(kwargs['prompt'], 'dots·files' if menu.id=='dots:files' else 'dots')
            step=len(visits)
            if step==1:
                kwargs['navigation']['query']='fil'; return Entry('files','inert $(touch sentinel)')
            if step==2:
                kwargs['navigation']['query']='li'; return Entry('list','inert')
            if step==3: raise SelectionEvent('help')
            if step==4: raise SelectionEvent('back')
            raise SelectionEvent('back')
        with patch('menu_cli.choose',side_effect=select), patch('menu_cli.run_action',return_value=7) as run:
            self.assertEqual(self.invoke('--browse','--query','initial')[0],130)
        self.assertEqual(visits,[('dots','initial'),('dots:files',''),('dots:files','li'),('dots:files','li'),('dots','fil')])
        self.assertEqual([c.args[0][-2:] for c in run.call_args_list],[['files','list'],['help','files']])
        self.assertFalse((self.home/'sentinel').exists())

    def test_sync_requires_successful_review_and_explicit_confirmation(self):
        from menu_pager import OutputResult
        for family in ('git', 'git/wiki'):
            action = next(a for a in menu_cli.actions(family) if a.id == 'sync')
            for result in (OutputResult(7,True), OutputResult(0,False), OutputResult(130,False)):
                with patch('menu_cli.review_output',return_value=result), patch('menu_cli.choose') as confirm, patch('menu_cli.run_action') as run:
                    self.assertFalse(menu_cli.invoke(self.root,action,None))
                    confirm.assert_not_called();run.assert_not_called()
            for selection in (None, Entry('cancel','Cancel'), Entry('sync','inert $(touch sentinel)')):
                with patch('menu_cli.review_output',return_value=OutputResult(0,True)) as preview, patch('menu_cli.choose',return_value=selection) as confirm, patch('menu_cli.run_action',return_value=0) as run:
                    self.assertFalse(menu_cli.invoke(self.root,action,None))
                self.assertEqual(preview.call_args.args[0][-len(action.route)-1:],[*action.route,'--dry-run'])
                self.assertEqual(confirm.call_args.args[0].entries[0].id,'cancel')
                if selection and selection.id=='sync':
                    self.assertEqual(run.call_args.args[0][-len(action.route):],list(action.route))
                    self.assertEqual(run.call_args.kwargs['kind'],'terminal')
                    self.assertFalse(set(run.call_args.args[0]) & {'--yes','--all','--remote','--init'})
                else: run.assert_not_called()
            with patch('menu_cli.review_output',return_value=OutputResult(0,True)), patch('menu_cli.choose',side_effect=SelectionEnded(130)), patch('menu_cli.run_action') as run:
                with self.assertRaises(SelectionEnded):menu_cli.invoke(self.root,action,None)
                run.assert_not_called()

    def test_git_unavailable_without_executing_any_provider(self):
        real_which = shutil.which
        with patch('menu_cli.shutil.which',side_effect=lambda n:None if n=='git' else real_which(n)), patch('subprocess.run',side_effect=AssertionError('Git executed')):
            self.assertFalse(next(e for e in menu_cli.launcher(self.root).entries if e.id=='git').available)
            self.assertFalse(menu_cli.entry(self.root,menu_cli.actions('git')[0]).available)

    def test_session_success_exits_other_outcomes_return_and_ctrl_c_exits(self):
        from menu_sessions import SessionOutcome
        for outcome in (SessionOutcome(True,0),SessionOutcome(message='No tmux sessions available.'),SessionOutcome(True,7),SelectionEnded(130),ValueError('server failed')):
            sequence=[Entry('tmux','tmux'),Entry('sessions','sessions'),SelectionEnded(130)]
            with patch('menu_cli.choose',side_effect=sequence), patch('menu_sessions.browse', side_effect=outcome if isinstance(outcome,Exception) else None, return_value=outcome), patch('menu_cli.show_message') as message:
                code=self.invoke('--browse')[0]
            self.assertEqual(code,0 if outcome==SessionOutcome(True,0) else 130)
            if isinstance(outcome,ValueError) or getattr(outcome,'message','') or getattr(outcome,'code',0): self.assertTrue(message.called)
        with patch('menu_cli.choose',side_effect=[Entry('files','files'),SelectionEnded(130)]), patch('menu_cli.run_action') as run:
            self.assertEqual(self.invoke('--browse')[0],130);run.assert_not_called()

    def test_windows_keeps_tmux_visible_and_both_action_frontends(self):
        from menus import dots_argv
        entries = {e.id:e for e in menu_cli.launcher(self.root, windows=True).entries}
        self.assertFalse(entries['tmux'].available); self.assertIn('native Windows', entries['tmux'].reason)
        for family in ('', *menu_cli.FAMILIES):
            for action in menu_cli.actions(family):
                for windows in (False, True):
                    with self.subTest(family=family, action=action.id, windows=windows):
                        argv = dots_argv([*action.route,*action.options],root=self.root,windows=windows)
                        prefix = [sys.executable,'-B',str(self.root/'lib/dots/cli.py')] if windows else [str(self.root/'bin/dots')]
                        self.assertEqual(argv, [*prefix, *action.route, *action.options])

    def test_unavailable_and_failed_workflows_show_reason_then_return(self):
        (self.root/'bin/dots-theme-switcher').unlink()
        with patch('menu_cli.choose',side_effect=[Entry('theme','theme'),Entry('switcher','switcher'),SelectionEvent('back'),SelectionEvent('back')]), patch('menu_cli.show_message') as message, patch('menu_cli.run_action') as run:
            self.assertEqual(self.invoke('--browse')[0],130)
            run.assert_not_called(); self.assertIn('missing',message.call_args.args[0])
        with patch('menu_cli.choose',side_effect=[Entry('keys','keys'),SelectionEvent('back')]), patch('menu_cli.run_action',return_value=7), patch('menu_cli.show_message') as message:
            self.assertEqual(self.invoke('--browse')[0],130); self.assertEqual(message.call_args.kwargs['code'],7)

    def test_metadata_longest_prefix_and_both_frontends(self):
        from command_metadata import resolve
        for route in (['menu'],['menu','tmux','keys'],['menu','tmux','sessions']):
            stem,path,count=resolve([self.root/'bin'],[*route,'--json'])
            self.assertEqual((stem,count),('-'.join(route),len(route)))
        env=dict(self.env,DOTS=str(self.root))
        fronts=[[sys.executable,'-B',str(self.root/'lib/dots/cli.py')]]
        if os.name!='nt':fronts.insert(0,[str(self.root/'bin/dots')])
        for front in fronts:
            def call(*args):
                p=subprocess.run([*front,*args],env=env,capture_output=True,text=True,timeout=20)
                self.assertEqual(p.returncode,0,p.stderr);return p.stdout
            self.assertIn('--client',call('menu','--help'))
            self.assertEqual(len(json.loads(call('menu','--json'))['items']),12)
            complete=['__complete','bash','2','--','dots'] if len(front)==1 else ['__complete']
            self.assertIn('--query',call(*complete,'menu','--q'))
            self.assertIn('menu tmux sessions',call('help','menu'))

    def test_missing_fzf_falls_back_and_key_data_ignores_private_context(self):
        real_which=shutil.which
        with patch('menu_cli.terminal',return_value=True),patch('menus.terminal',return_value=True), \
                patch('shutil.which',side_effect=lambda name: None if name=='fzf' else real_which(name)), \
                patch('menu_cli.run_action',side_effect=AssertionError('action')):
            code,out,err=self.invoke('--browse')
            self.assertEqual(code,0);self.assertIn('keys',out);self.assertIn('FZF unavailable',err)
        import keys_cli
        with patch.dict(os.environ,DOTS_MENU_CONTEXT='/absent/private/request'), \
                patch('keys_cli.collect',return_value=dict(rows=[],coverage=[])),redirect_stdout(io.StringIO()):
            self.assertEqual(keys_cli.main(['tmux','--json']),0)
            self.assertEqual(keys_cli.main(['tmux','--print']),0)


class NativeLauncher(NativeMenuFixture):
    def setUp(self):
        super().setUp(); self.root=checkout(self.base)
        self.env['DOTS']=str(self.root)
        self.env['PATH']=str(self.root/'bin')+os.pathsep+self.env['PATH']
        os.environ.update(DOTS=str(self.root),PATH=self.env['PATH'])
        self.control('set-environment','-g','DOTS',str(self.root))
        self.control('set-environment','-g','PATH',self.env['PATH'])
        self.cwd=self.home / "work ü ' $(touch sentinel);";self.cwd.mkdir()
        # Change the owned pane's cwd so the real shortcut must carry it safely.
        self.control('send-keys','-t',self.pane,'cd -- '+shlex.quote(str(self.cwd)),'Enter')
        self.drain(self.first[1]);self.drain(self.second[1])
        config=ROOT/'config/tmux/tmux.conf'
        bindings=[line for line in config.read_text().splitlines() if line.startswith(('bind -N "Open Dots menu"','bind -N "Choose tmux session"'))]
        self.assertEqual(len(bindings),2)
        path=self.base/'shortcuts.conf';path.write_text('\n'.join(bindings)+'\n')
        self.control('source-file',str(path))

    def picker(self, query=''):
        return self.worker("import os,sys;from menu_cli import main;sys.exit(main(['--browse','--client',os.environ['CLIENT'],'--query',os.environ['QUERY']]))",QUERY=query)

    def choose(self, text):
        os.write(self.first[1],text.encode());time.sleep(.3);os.write(self.first[1],b'\r')

    def test_real_shortcuts_open_exact_client_cancel_quietly_and_preserve_cwd(self):
        for key,prompt in ((b'm',b'dots:'),(b's','dots·tmux·sessions'.encode())):
            for cancel in (b'\x1b',b'\x03'):
                self.drain(self.first[1]);self.drain(self.second[1])
                os.write(self.first[1],b'\x02'+key)
                self.receive(self.first[1],prompt)
                self.assertNotIn(prompt,self.drain(self.second[1]))
                os.write(self.first[1],cancel);time.sleep(.2)
                self.assertNotIn(b'returned 130',self.drain(self.first[1]))
                self.assertEqual(self.control('display-message','-p','-t',self.pane,'#{pane_in_mode}').strip(),'0')
        self.assertEqual(self.control('display-message','-p','-t',self.pane,'#{pane_current_path}').strip(),str(self.cwd))
        self.assertFalse((self.home/'sentinel').exists())

    def test_shortcut_session_selection_only_switches_originating_client(self):
        ident=self.control('new-session','-d','-P','-F','#{session_id}','-s','destination',shutil.which('bash'),'--noprofile','--norc').strip()
        os.write(self.first[1],b'\x02s');self.receive(self.first[1],'dots·tmux·sessions'.encode());self.choose('destination')
        deadline=time.monotonic()+8
        while time.monotonic()<deadline:
            self.drain(self.first[1])
            clients=dict(r.split('\t') for r in self.control('list-clients','-F','#{client_name}\t#{session_id}').splitlines())
            if clients.get(self.first[2])==ident:break
            time.sleep(.05)
        self.assertEqual(clients[self.first[2]],ident);self.assertEqual(clients[self.second[2]],'$0')

    def test_session_cancel_returns_and_selection_closes_launcher(self):
        p=self.picker('^tmux$');self.receive(self.first[1],b'dots:');os.write(self.first[1],b'\r')
        self.receive(self.first[1],'dots·tmux:'.encode());self.choose('sessions')
        self.receive(self.first[1],'dots·tmux·sessions:'.encode());self.assertNotIn('dots·tmux·sessions:'.encode(),self.drain(self.second[1]))
        os.write(self.first[1],b'\x1b');self.receive(self.first[1],'dots·tmux:'.encode())
        os.write(self.first[1],b'\r');self.receive(self.first[1],'dots·tmux·sessions:'.encode())
        self.choose('fixture');out,err=p.communicate(timeout=15)
        self.assertEqual(p.returncode,0,err)
        self.assertFalse(list(self.base.glob('dots-menu-*')))

    def test_keys_cancel_returns_to_root_with_query(self):
        p=self.picker('^keys$');self.receive(self.first[1],b'dots:');os.write(self.first[1],b'\r')
        self.receive(self.first[1],b'Enter: open');self.choose('tmux');self.receive(self.first[1],b'tmux:')
        self.assertNotIn(b'tmux:',self.drain(self.second[1]))
        os.write(self.first[1],b'\x1bm');self.receive(self.first[1],b'modes:')
        self.assertNotIn(b'modes:',self.drain(self.second[1]))
        self.choose('prefix');self.receive(self.first[1],'tmux·prefix:'.encode())
        self.assertNotIn('tmux·prefix:'.encode(),self.drain(self.second[1]))
        os.write(self.first[1],b'\x1bm');self.receive(self.first[1],b'modes:')
        time.sleep(.2);os.write(self.first[1],b'\x1b');self.receive(self.first[1],'tmux·prefix:'.encode())
        time.sleep(.2);os.write(self.first[1],b'\x1b')
        data=self.receive(self.first[1],b'dots:');self.assertIn(b'^keys$',data)
        os.write(self.first[1],b'\x03');out,err=p.communicate(timeout=15)
        self.assertEqual(p.returncode,130,err)

    def test_long_output_scrolls_searches_and_returns_with_cwd_and_status(self):
        result=self.base/'action.json'
        child=self.base/'action.py'
        child.write_text('import os,json,sys\nfrom pathlib import Path\nPath(sys.argv[1]).write_text(json.dumps(os.getcwd()))\nprint("FIRST MARKER")\nfor i in range(200): print("Line",i)\nprint("LAST MARKER")\nsys.exit(7)\n')
        path=self.root/'bin/dots-files-list'
        path.write_text('#!/usr/bin/env bash\n# dots-summary: List fixture files\nexec '+shlex.join([sys.executable,'-B',str(child),str(result)])+'\n')
        os.write(self.first[1],b'\x02m');self.receive(self.first[1],b'dots:');self.choose('^files$')
        self.receive(self.first[1],'dots·files:'.encode());self.choose('^list$')
        data=self.receive(self.first[1],b'Back q');self.assertIn(b'Exit status: 7',data);self.assertIn(b'FIRST MARKER',data)
        self.assertNotIn(b'FIRST MARKER',self.drain(self.second[1]))
        self.assertEqual(json.loads(result.read_text()),str(self.cwd))
        os.write(self.first[1],b'G');self.receive(self.first[1],b'LAST MARKER')
        os.write(self.first[1],b'g');self.receive(self.first[1],b'FIRST MARKER')
        os.write(self.first[1],b'/Line 150\r');self.receive(self.first[1],b'Line 150')
        os.write(self.first[1],b'q');data=self.receive(self.first[1],'dots·files:'.encode());self.assertIn(b'^list$',data)
        os.write(self.first[1],b'\x1b');data=self.receive(self.first[1],b'dots:');self.assertIn(b'^files$',data)
        os.write(self.first[1],b'\x1b');time.sleep(.2)
        self.assertFalse(list(self.base.glob('dots-output-*')))
        self.assertFalse((self.home/'sentinel').exists())

    def test_f1_context_help_and_back_with_no_matches(self):
        p=self.picker('^files$');self.receive(self.first[1],b'dots:');os.write(self.first[1],b'\r')
        self.receive(self.first[1],'dots·files:'.encode());os.write(self.first[1],b'\x1bOP')
        data=self.receive(self.first[1],b'Back q');self.assertIn(b'dots help files',data)
        os.write(self.first[1],b'q');self.receive(self.first[1],'dots·files:'.encode())
        os.write(self.first[1],b'no-such-choice');time.sleep(.2);os.write(self.first[1],b'\x1b')
        self.receive(self.first[1],b'dots:');os.write(self.first[1],b'\x1b')
        out,err=p.communicate(timeout=15);self.assertEqual(p.returncode,130,err)

    def test_git_sync_preview_cancel_default_cancel_and_explicit_apply(self):
        record=self.base/'sync-events'
        child=self.base/'sync.py'
        child.write_text('import sys\nfrom pathlib import Path\np=Path('+repr(str(record))+')\nphase="preview" if "--dry-run" in sys.argv else "apply"\np.write_text((p.read_text() if p.exists() else "")+phase+"\\n")\nprint("SYNC "+phase.upper(),flush=True)\n')
        (self.root/'bin/dots-git-sync').write_text('#!/usr/bin/env bash\n# dots:summary=Fixture sync\nexec '+shlex.join([sys.executable,'-B',str(child)])+' "$@"\n')
        p=self.picker('^git$');self.receive(self.first[1],b'dots:');os.write(self.first[1],b'\r')
        self.receive(self.first[1],'dots·git:'.encode());self.choose('^sync$')
        self.receive(self.first[1],b'Back q');self.control('display-popup','-C','-c',self.first[2])
        self.receive(self.first[1],'dots·git:'.encode());self.assertEqual(record.read_text(),'preview\n')
        os.write(self.first[1],b'\r');self.receive(self.first[1],b'Back q');os.write(self.first[1],b'q')
        self.receive(self.first[1],'dots·git·sync:'.encode());os.write(self.first[1],b'\r')
        self.receive(self.first[1],'dots·git:'.encode());self.assertEqual(record.read_text(),'preview\npreview\n')
        os.write(self.first[1],b'\r');self.receive(self.first[1],b'Back q');os.write(self.first[1],b'q')
        self.receive(self.first[1],'dots·git·sync:'.encode());os.write(self.first[1],b'\x1b[B');time.sleep(.2);os.write(self.first[1],b'\r')
        self.receive(self.first[1],'dots·git:'.encode());self.assertEqual(record.read_text(),'preview\npreview\npreview\napply\n')
        self.assertNotIn(b'SYNC',self.drain(self.second[1]))
        os.write(self.first[1],b'\x03');_,err=p.communicate(timeout=15);self.assertEqual(p.returncode,130,err)

    def test_launcher_fits_40_80_120_column_clients(self):
        from menu_tmux import TmuxContext
        for width in (40,80,120):
            self.fcntl.ioctl(self.first[1],self.termios.TIOCSWINSZ,self.struct.pack('HHHH',24,width,0,0))
            context=TmuxContext.capture(client=self.first[2])
            deadline=time.monotonic()+3
            while context.verify()!=(width,24) and time.monotonic()<deadline:time.sleep(.05)
            self.assertEqual(context.verify(),(width,24));self.drain(self.first[1])
            p=self.picker()
            try:self.receive(self.first[1],b'dots:')
            except AssertionError:
                if p.poll() is not None:self.fail(repr(p.communicate(timeout=2)))
                raise
            self.choose('^themes$');self.receive(self.first[1],'dots·themes:'.encode())
            self.choose('^plugins$');self.receive(self.first[1],'dots·themes·plugins:'.encode())
            os.write(self.first[1],b'\x1b');data=self.receive(self.first[1],'dots·themes:'.encode())
            self.assertIn(b'^plugins$',data)
            os.write(self.first[1],b'\x1b');data=self.receive(self.first[1],b'dots:')
            self.assertIn(b'^themes$',data)
            os.write(self.first[1],b'\x1b')
            out,err=p.communicate(timeout=15);self.assertEqual(p.returncode,130,err)


if __name__=='__main__':
    unittest.main()

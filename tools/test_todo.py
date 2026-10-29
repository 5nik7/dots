#!/usr/bin/env python3
"""Todo behavior and safety tests, confined to disposable user/project roots."""
import base64
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import re
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib/dots'))
from todo_core import Goals, scope, validate
from todo_commands import parser


class Todo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='todo ü spaces ')
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.dots = self.home / 'dots'; self.dots.mkdir()
        self.project = self.home / 'project'; self.project.mkdir()
        self.global_dir = self.home / 'outside'; self.global_dir.mkdir()
        env = {k: v for k, v in os.environ.items() if not k.startswith(('DOTS_', 'GIT_'))
               and k not in ('TMUX', 'DOTS', 'CODEX_HOME')}
        env.update(HOME=str(self.home), USERPROFILE=str(self.home), DOTS=str(self.dots),
            XDG_CONFIG_HOME=str(self.home/'config'), XDG_STATE_HOME=str(self.home/'state'),
            XDG_DATA_HOME=str(self.home/'data'), XDG_CACHE_HOME=str(self.home/'cache'),
            APPDATA=str(self.home/'appdata'), LOCALAPPDATA=str(self.home/'local'), CODEX_HOME=str(self.home/'codex'),
            DOTS_COLOR='never', DOTS_ICONS='never', DOTS_PROGRESS='never', TERM='dumb',
            GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT='0')
        self.env = env
        self.environ = patch.dict(os.environ, env, clear=True); self.environ.start(); self.addCleanup(self.environ.stop)

    def cli(self, *args, standalone=False, cwd=None, code=0, native=False, env=None):
        target = ROOT / 'lib/dots' / ('todo_standalone.py' if standalone else 'todo_cli.py')
        command = [sys.executable, '-B', str(target), *args]
        if native:
            encoded = base64.b64encode(json.dumps(list(args)).encode()).decode()
            command = [sys.executable, '-B', str(ROOT/'lib/dots/native.py'), 'todo' if standalone else 'cli',
                       encoded if standalone else base64.b64encode(json.dumps(['todo', *args]).encode()).decode()]
        result = subprocess.run(command, cwd=cwd or self.global_dir, env=env or self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result

    def add(self, title='Goal', **options):
        flags = []
        for key, value in options.items():
            for item in value if isinstance(value, list) else [value]: flags += ['--'+key, item]
        return json.loads(self.cli('add', title, *flags, '--json').stdout)['goals'][0]

    def store(self): return Goals(scope())

    def git(self, directory, *args):
        result = subprocess.run(['git', '-C', str(directory), *args], env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def snapshot(self):
        return {str(p.relative_to(self.home)): p.read_bytes() for p in self.home.rglob('*') if p.is_file() and not p.is_symlink()}

    def test_read_only_empty_and_dry_run(self):
        before = self.snapshot()
        for args in (('list','--json'), ('path',), ('--help',), ('add','Draft','--dry-run','--json')):
            self.cli(*args)
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.dots/'.dots').exists())

    def test_prefix_options_cannot_change_output_contract(self):
        before = self.snapshot()
        self.cli('--markdown', 'add', 'Must not create', code=2)
        self.cli('--json', 'brief', '12345678', code=2)
        self.assertEqual(self.snapshot(), before)

    def test_scope_dots_auto_global_explicit(self):
        self.git(self.project, 'init', '-q')
        nested = self.project/'sub'; nested.mkdir()
        fixed = json.loads(self.cli('list','--json',cwd=nested).stdout)['scope']
        auto = json.loads(self.cli('list','--json',standalone=True,cwd=nested).stdout)['scope']
        global_ = json.loads(self.cli('list','--json',standalone=True).stdout)['scope']
        self.assertEqual(fixed['root'],str(self.dots)); self.assertEqual(auto['root'],str(self.project))
        self.assertEqual(global_['kind'],'global')
        explicit = json.loads(self.cli('--project',str(self.project),'list','--json',standalone=True).stdout)['scope']
        self.assertEqual(explicit,auto)
        self.cli('--global','list',code=1)
        self.cli('--global','--project',str(self.project),'list',standalone=True,code=2)

    def test_configured_and_nested_projects(self):
        self.git(self.project,'init','-q')
        child=self.project/'inner'; child.mkdir()
        config=self.home/'config/dots'; config.mkdir(parents=True)
        (config/'projects.json').write_text(json.dumps(dict(schema=1,projects=[str(child)])))
        result=json.loads(self.cli('list','--json',standalone=True,cwd=child).stdout)
        self.assertEqual(result['scope']['root'],str(child))
        draft=json.loads(self.cli('add','Configured','--dry-run','--json',standalone=True,cwd=child).stdout)
        self.assertEqual(draft['goals'][0]['tags'],['inner'])
        (config/'projects.json').write_text('{broken')
        self.cli('add','Must not become global',standalone=True,cwd=child,code=1)
        self.assertFalse((self.home/'state').exists())

    def test_worktree_and_nested_git(self):
        self.git(self.project,'init','-q')
        self.git(self.project,'-c','user.name=Test','-c','user.email=test@example.invalid','commit','--allow-empty','-qm','Initial')
        worktree=self.home/'worktree'
        self.git(self.project,'worktree','add','-qb','other',str(worktree))
        result=json.loads(self.cli('list','--json',standalone=True,cwd=worktree).stdout)
        self.assertEqual(result['scope']['root'],str(worktree))
        draft=json.loads(self.cli('add','Worktree','--dry-run','--json',standalone=True,cwd=worktree).stdout)
        self.assertEqual(draft['goals'][0]['tags'],['worktree'])
        child=self.project/'nested';child.mkdir();self.git(child,'init','-q')
        self.assertEqual(json.loads(self.cli('list','--json',standalone=True,cwd=child).stdout)['scope']['root'],str(child))
        draft=json.loads(self.cli('add','Nested','--dry-run','--json',standalone=True,cwd=child).stdout)
        self.assertEqual(draft['goals'][0]['tags'],['nested'])

    def test_global_creation(self):
        result=json.loads(self.cli('add','Global','--json',standalone=True).stdout)
        self.assertTrue((self.home/'state/dots/todo/global.json').is_file())
        self.assertEqual(result['scope']['kind'],'global')
        self.assertEqual(result['goals'][0]['tags'],[])
        self.assertFalse((self.dots/'.dots').exists())

    def test_lifecycle_and_noop(self):
        goal=self.add(notes='Original',tag=['ui','phone'],accept=['Works at 40 columns'])
        ident=goal['id'][:8]
        self.cli('start',ident,'--json')
        count=len(list((self.home/'state/dots/files/transactions').iterdir()))
        result=json.loads(self.cli('start',ident,'--json').stdout)
        self.assertEqual(result['status'],'unchanged')
        self.assertEqual(count,len(list((self.home/'state/dots/files/transactions').iterdir())))
        self.cli('edit',ident,'--notes','','--clear','tags','--json')
        self.assertEqual(self.store().find(ident)['notes'],'')
        self.cli('done',ident);self.assertIsNotNone(self.store().find(ident)['completed'])
        self.assertEqual(json.loads(self.cli('list','--json').stdout)['goals'],[])
        self.cli('reopen',ident);self.assertIsNone(self.store().find(ident)['completed'])
        self.cli('remove',ident,code=1)
        self.cli('remove',ident,'--json',code=2)
        self.cli('remove',ident,'--yes');self.assertIsNotNone(self.store().find(ident)['removed'])
        self.cli('restore',ident);self.assertIsNone(self.store().find(ident)['removed'])

    def test_project_tag_retention_filters_completion_and_global(self):
        from todo_completion import complete
        goal=self.add(tag=['ui','dots','phone'])
        self.assertEqual(goal['tags'],['ui','dots','phone'])
        changed=json.loads(self.cli('edit',goal['id'],'--tag','new','--json').stdout)
        self.assertEqual(changed['goals'][0]['tags'],['new','dots'])
        cleared=json.loads(self.cli('edit',goal['id'],'--clear','tags','--json').stdout)
        self.assertEqual(cleared['goals'][0]['tags'],['dots'])
        before=self.snapshot()
        noop=json.loads(self.cli('edit',goal['id'],'--clear','tags','--json').stdout)
        self.assertEqual(noop['status'],'unchanged');self.assertIsNone(noop['transaction'])
        self.assertEqual(noop['goals'],cleared['goals']);self.assertEqual(self.snapshot(),before)
        self.assertEqual(len(json.loads(self.cli('list','--tag','dots','--json').stdout)['goals']),1)
        self.assertEqual(len(json.loads(self.cli('list','--tag','DOTS','--json').stdout)['goals']),0)
        output=io.StringIO()
        with patch('sys.stdout',output):complete(['list','--tag','do'])
        self.assertIn('candidate\tdots\t',output.getvalue())
        global_goal=json.loads(self.cli('--global','add','Global','--tag','ui','--json',standalone=True).stdout)['goals'][0]
        self.assertEqual(global_goal['tags'],['ui'])
        cleared=json.loads(self.cli('--global','edit',global_goal['id'],'--clear','tags','--json',standalone=True).stdout)
        self.assertEqual(cleared['goals'][0]['tags'],[])

    def test_project_tag_names_and_rename(self):
        from todo_core import project_tag
        from pathlib import PureWindowsPath
        self.assertEqual(project_tag(dict(kind='global',root=None)),None)
        self.assertEqual(project_tag(dict(kind='project',root=self.dots.anchor)),self.dots.anchor)
        with patch('todo_core.Path',PureWindowsPath):
            self.assertEqual(project_tag(dict(kind='project',root='C:\\')), 'C:\\')
            self.assertEqual(project_tag(dict(kind='project',root='C:\\Projects\\My Project ü')), 'My Project ü')
        for name in ('My Project ü','-leading','MiXeD'):
            project=self.home/name;project.mkdir()
            result=json.loads(self.cli('--project',str(project),'add','Named','--tag='+name,'--json',standalone=True,native=True).stdout)
            self.assertEqual(result['goals'][0]['tags'],[name])
        project=self.home/'Original';project.mkdir()
        goal=json.loads(self.cli('--project',str(project),'add','Rename','--json',standalone=True).stdout)['goals'][0]
        renamed=self.home/'Renamed ü';project.rename(renamed)
        self.cli('--project',str(renamed),'edit',goal['id'],'--notes',goal['notes'],standalone=True)
        changed=json.loads(self.cli('--project',str(renamed),'show',goal['id'],'--json',standalone=True).stdout)['goals'][0]
        self.assertEqual(changed['tags'],['Original','Renamed ü'])
        self.cli('--project',str(renamed),'edit',goal['id'],'--clear','tags',standalone=True)
        self.assertEqual(Goals(scope(standalone=True,project=renamed)).find(goal['id'])['tags'],['Renamed ü'])

    def test_project_tag_legacy_backfill_preview_noop_and_undo(self):
        from todo_core import Store, state_root
        from todo_completion import complete
        base=self.add('Legacy',notes='Keep exact notes\n')
        path=Path(scope()['path'])
        for schema in (1,2):
            goals=[dict(deepcopy(base),id=f'{index+1:032x}',tags=[f'custom-{index}']) for index in range(5)]
            goals[1]['parent']=goals[0]['id']
            goals[2].update(status='done',completed=base['created'])
            goals[3]['removed']=base['created']
            goals[4]['tags'].append('dots')
            if schema==1:
                for goal in goals:goal.pop('alias')
            original=json.dumps(dict(schema=schema,goals=goals),ensure_ascii=False).encode()+b'\n'
            path.write_bytes(original);before=self.snapshot()
            for args in [('list','--all','--json'),('list','--removed','--json'),('show',goals[0]['id'],'--json'),('brief',goals[0]['id'])]:
                self.cli(*args)
            with patch('sys.stdout',io.StringIO()):complete(['list','--tag',''])
            planned=json.loads(self.cli('edit',goals[0]['id'],'--notes',base['notes'],'--dry-run','--json').stdout)
            self.assertEqual(planned['status'],'planned')
            self.assertEqual({g['id'] for g in planned['goals']},{g['id'] for g in goals[:4]})
            self.assertEqual(before,self.snapshot())
            result=json.loads(self.cli('edit',goals[0]['id'],'--notes',base['notes'],'--json').stdout)
            self.assertEqual(result['status'],'complete');self.assertTrue(result['transaction'])
            self.assertEqual({g['id'] for g in result['goals']},{g['id'] for g in goals[:4]})
            updated=self.store().goals
            for old,new in zip(goals,updated):
                expected=dict(old,alias=old.get('alias'),tags=old['tags']+([] if 'dots' in old['tags'] else ['dots']))
                if new['id']!=goals[4]['id']:
                    self.assertNotEqual(new['updated'],old['updated']);expected['updated']=new['updated']
                self.assertEqual(new,expected)
            before_noop=self.snapshot()
            noop=json.loads(self.cli('edit',goals[0]['id'],'--notes',base['notes'],'--json').stdout)
            self.assertEqual(noop['status'],'unchanged');self.assertEqual(before_noop,self.snapshot())
            store=Store(state_root());operations,guards,catalogs=store.inverse(result['transaction'])
            store.apply('undo',operations,guards,catalogs=catalogs,retain=True)
            self.assertEqual(path.read_bytes(),original)

    def test_project_tag_limits_preflight_and_failed_changes(self):
        goal=self.add(tag=['tag-'+str(i) for i in range(255)])
        self.assertEqual(len(goal['tags']),256)
        path=Path(scope()['path']);doc=json.loads(path.read_text())
        doc['goals'][0]['tags']=['tag-'+str(i) for i in range(256)]
        other=dict(deepcopy(doc['goals'][0]),id='1'*32)
        doc['goals'].append(other);path.write_text(json.dumps(doc));before=self.snapshot()
        failed=self.cli('edit',goal['id'],'--notes','Cannot save',code=1)
        self.assertIn('256 tags',failed.stderr)
        for item in doc['goals']:self.assertIn(item['id'],failed.stderr)
        self.cli('edit',goal['id'],'--title','',code=1)
        self.assertEqual(before,self.snapshot())

    def test_project_tag_backfill_stale_write_and_rollback(self):
        import transactions
        goal=self.add();path=Path(scope()['path']);doc=json.loads(path.read_text())
        doc['goals'][0]['tags']=[]
        doc['goals'].append(dict(deepcopy(doc['goals'][0]),id='1'*32))
        path.write_text(json.dumps(doc));before=path.read_bytes()
        real_save=transactions.Store.save
        def fail(store,doc):
            real_save(store,doc)
            if doc['status']=='applying':raise KeyboardInterrupt()
        with patch.object(transactions.Store,'save',fail):
            with self.assertRaises(KeyboardInterrupt):self.store().mutate('edit',goal['id'],notes=goal['notes'])
        self.assertEqual(path.read_bytes(),before)
        old=self.store();self.cli('edit',goal['id'],'--notes','Newer')
        current=path.read_bytes()
        with self.assertRaisesRegex(ValueError,'changed'):old.mutate('edit',goal['id'],notes='Stale')
        self.assertEqual(path.read_bytes(),current)

    def test_project_tag_popup_edit_keeps_required_tag(self):
        from todo_menu import edit_fields, apply
        goal=self.add(tag=['custom'])
        with patch('todo_menu.select',return_value='tags'),patch('todo_input.prompt',return_value=''):
            changes=edit_fields(goal,None)
        apply(self.store(),'edit',goal['id'],**changes)
        self.assertEqual(self.store().find(goal['id'])['tags'],['dots'])

    def test_project_tag_cli_preview_digest_guard(self):
        from todo_cli import run
        goal=self.add();path=Path(scope()['path']);doc=json.loads(path.read_text())
        doc['goals'][0]['tags']=[];path.write_text(json.dumps(doc))
        expected=self.store().guard
        arguments=['edit',goal['id'],'--notes='+goal['notes'],'--json']
        with patch('sys.stdout',io.StringIO()):
            self.assertEqual(run([*arguments,'--dry-run'],expected=expected),0)
        before=path.read_bytes()
        self.assertEqual(self.store().find(goal['id'])['tags'],[])
        with patch('sys.stdout',io.StringIO()):
            self.assertEqual(run(arguments,expected=expected),0)
        after=path.read_bytes();self.assertNotEqual(before,after)
        with self.assertRaisesRegex(ValueError,'changed'):
            run(arguments,expected=expected)
        self.assertEqual(path.read_bytes(),after)

    def test_subgoals_and_restore(self):
        parent=self.add('Parent');child=self.add('Child',parent=parent['id'])
        self.cli('done',parent['id'],code=1)
        self.cli('remove',parent['id'],'--yes',code=1)
        self.cli('done',child['id']);self.cli('done',parent['id'])
        self.cli('reopen',child['id'],code=1)
        self.cli('remove',parent['id'],'--yes','--recursive')
        self.cli('restore',child['id'],code=1)
        self.cli('restore',parent['id'],'--recursive')
        self.assertTrue(all(not g['removed'] for g in self.store().goals))

    def test_query_order_next_and_markdown(self):
        self.add('Low',priority='low')
        blocked=self.add('Blocked',priority='high')
        self.cli('edit',blocked['id'],'--status','blocked')
        target=self.add('Search target',priority='high',notes='needle detail',tag=['phone','ui'],due='2020-01-01')
        result=json.loads(self.cli('list','--query','needle','--tag','phone','--overdue','--json').stdout)
        self.assertEqual([g['id'] for g in result['goals']],[target['id']])
        self.assertEqual(json.loads(self.cli('next','--json').stdout)['goals'][0]['id'],target['id'])
        self.assertIn('Search target',self.cli('list','--markdown').stdout)

    def test_invalid_inputs_preserve_bytes(self):
        goal=self.add();before=self.snapshot()
        for opts in (('--due','2026-02-30'),('--title',''),('--due','20261028')):
            self.cli('edit',goal['id'],*opts,code=1)
        self.assertEqual(self.snapshot(),before)
        path=Path(scope()['path']);path.write_text('{broken')
        self.cli('add','Do not overwrite',code=1)
        self.assertEqual(path.read_text(),'{broken')

    def test_safe_file_types(self):
        path=Path(scope()['path']);path.parent.mkdir()
        other=self.home/'other';other.write_text('keep')
        path.symlink_to(other)
        self.cli('add','Unsafe',code=1);self.assertEqual(other.read_text(),'keep')
        path.unlink();path.mkdir()
        self.cli('list','--json',code=1)

    def test_stale_update_and_menu_selection(self):
        from todo_menu import apply
        goal=self.add();old=self.store()
        self.cli('edit',goal['id'],'--notes','Newer')
        with self.assertRaisesRegex(ValueError,'changed'):
            old.mutate('edit',goal['id'],notes='Stale')
        with self.assertRaisesRegex(ValueError,'changed'):
            apply(old,'done',goal['id'])
        self.assertEqual(self.store().find(goal['id'])['notes'],'Newer')

    def test_rollback_and_recovery_data(self):
        import transactions
        goal=self.add();before=Path(scope()['path']).read_bytes()
        real_save=transactions.Store.save
        def fail(store,doc):
            real_save(store,doc)
            if doc['status']=='applying':raise KeyboardInterrupt()
        with patch.object(transactions.Store,'save',fail):
            with self.assertRaises(KeyboardInterrupt):self.store().mutate('done',goal['id'])
        self.assertEqual(Path(scope()['path']).read_bytes(),before)
        self.cli('start',goal['id'])
        retained=list((self.home/'state/dots/files/transactions').glob('*/0-before'))
        self.assertTrue(retained)

    def test_brief_and_data_modes_are_read_only(self):
        goal=self.add('Title \x1b[31m',notes='line 1\nline 2',accept=['Verified'])
        before=self.snapshot()
        brief=self.cli('brief',goal['id']).stdout
        self.assertIn('Verified',brief);self.assertNotIn('\x1b',brief)
        forced={**self.env,'DOTS_COLOR':'always','DOTS_ICONS':'always'}
        plain=self.cli('list','--json').stdout
        self.assertEqual(plain,self.cli('list','--json',env=forced).stdout)
        self.assertEqual(self.snapshot(),before)

    def test_ambiguity_and_cycles(self):
        goal=self.add();store=self.store()
        second=deepcopy(goal);second['id']=goal['id'][:8]+'f'*24
        store.goals.append(second)
        with self.assertRaisesRegex(ValueError,'ambiguous'):store.find(goal['id'][:8])
        goal=store.goals[0];goal['parent']=second['id'];second['parent']=goal['id']
        with self.assertRaisesRegex(ValueError,'cyclic'):validate(store.document)

    def test_completion_scope_and_restore(self):
        from todo_completion import complete
        goal=self.add('Dots goal',tag=['one'])
        before=self.snapshot()
        output=io.StringIO()
        with patch('sys.stdout',output):complete(['show',''])
        self.assertIn(goal['id'],output.getvalue())
        output=io.StringIO()
        with patch('sys.stdout',output):complete(['--project',str(self.project),'show',''],standalone=True)
        self.assertNotIn(goal['id'],output.getvalue())
        self.assertEqual(before,self.snapshot())
        self.cli('remove',goal['id'],'--yes')
        for action,expected in [('restore',True),('done',False)]:
            output=io.StringIO()
            with patch('sys.stdout',output):complete([action,''])
            self.assertEqual(goal['id'] in output.getvalue(),expected)

    def test_bash_dispatch_and_completion(self):
        # Only copy owned first-party adapters, never run host extensions.
        shutil.copytree(ROOT/'lib',self.dots/'lib',ignore=shutil.ignore_patterns('__pycache__'))
        (self.dots/'bin').mkdir()
        for path in (ROOT/'bin').glob('dots-todo*'):shutil.copy2(path,self.dots/'bin'/path.name)
        shutil.copy2(ROOT/'bin/dots',self.dots/'bin/dots')
        shutil.copy2(ROOT/'bin/todo',self.dots/'bin/todo')
        goal=self.add('Literal $(never-run)')
        result=subprocess.run([str(self.dots/'bin/dots'),'todo','show',goal['id'],'--json'],env=self.env,cwd=self.project,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr);self.assertIn(goal['id'],result.stdout)
        result=subprocess.run([str(self.dots/'bin/dots'),'__complete','bash','3','--','dots','todo','show',''],env=self.env,capture_output=True,text=True)
        self.assertIn(goal['id'],result.stdout)
        result=subprocess.run([str(self.dots/'bin/dots'),'todo','note',goal['id'],'Literal ü\n$(never-run)','--json'],env=self.env,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['goals'][0]['notes'],'Literal ü\n$(never-run)')
        result=subprocess.run([str(self.dots/'bin/todo'),'--project',str(self.project),'add','--json','--','-literal'],env=self.env,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['goals'][0]['title'],'-literal')

    def test_native_standalone_literal_bridge(self):
        result=self.cli('--project',str(self.project),'add','quote " $() ü','--json',standalone=True,native=True)
        self.assertEqual(json.loads(result.stdout)['goals'][0]['title'],'quote " $() ü')

    def test_menu_missing_tools_and_cancel(self):
        from todo_menu import browse, apply, edit_fields
        from interaction import SelectionEvent
        args=parser().parse_args([])
        with patch('todo_menu.pick',return_value=None):self.assertEqual(browse(scope(),args),0)
        with patch('todo_menu.pick',side_effect=SelectionEvent('back')):
            self.assertEqual(browse(scope(),args),130)
        self.assertFalse((self.dots/'.dots').exists())

    def test_rows_sanitize_and_size(self):
        from todo_menu import rows
        from files.catalog import Presentation
        goal=self.add('Long ü title '*12,notes='\x1b]52;c;bad\x07')
        for width in (40,80,120):
            ui=Presentation(io.StringIO(),terminal=True,detail_indent=2)
            ui.color=False;ui.icons=False
            labels,previews=rows(self.store(),[goal],ui,width)
            self.assertNotIn('\x1b',labels[0]+previews[0])
            self.assertIn(goal['id'],previews[0])

    def test_editable_input_controls_are_inert_and_unchanged_text_is_preserved(self):
        from todo_input import input_text
        initial='literal\x1b[31m\nnext line'
        displayed=r'literal\x1b[31m'+'\nnext line'
        with patch('todo_input.terminal',return_value=True),patch('todo_input.shutil.which',return_value='gum'), \
             patch.dict(os.environ,TERM='xterm-256color'),patch('todo_input.subprocess.run',return_value=subprocess.CompletedProcess([],0,displayed+'\n')) as run:
            self.assertEqual(input_text(initial,'Notes',True),initial)
            self.assertEqual(run.call_args.args[0][-1],'--value='+displayed)
            self.assertNotIn('\x1b',run.call_args.args[0][-1])

    def test_picker_palette_and_plain_controls(self):
        from todo_menu import rows
        from files.catalog import Presentation
        goal=self.add('Palette goal')
        directory=self.home/'state/dots/current/theme';directory.mkdir(parents=True)
        for background,foreground in (('#111111','#eeeeee'),('#eeeeee','#111111')):
            (directory/'palette.json').write_text(json.dumps(dict(colors=dict(bright_magenta='#123456',foreground=foreground,background=background))))
            for color,no_color,expected in [('auto','',True),('auto','1',False),('always','1',True),('never','',False)]:
                with patch.dict(os.environ,DOTS_COLOR=color,NO_COLOR=no_color,DOTS_ICONS='never',TERM='xterm-256color'):
                    ui=Presentation(io.StringIO(),terminal=True,detail_indent=2)
                    labels,_=rows(self.store(),[goal],ui,80)
                    self.assertEqual('\x1b[' in labels[0],expected)
                    if expected:self.assertIn('38;2;18;52;86',labels[0])

    def test_alias_lifecycle_and_scopes(self):
        goal = self.add('Alias goal', alias='config-rework')
        for selector in ('config-rework', '@config-rework', goal['id'], goal['id'][:8]):
            self.assertEqual(self.store().find(selector)['id'], goal['id'])
        self.cli('edit', 'config-rework', '--title', 'Renamed title')
        child = self.add('Child', parent='config-rework', alias='child')
        self.assertEqual(child['parent'], goal['id'])
        self.cli('add', 'Other scope', '--alias', 'config-rework', '--json', standalone=True)
        before = self.snapshot()
        for alias in ('config-rework', 'Upper', '-bad', 'a b', 'a'*65):
            self.cli('add', 'Invalid', '--alias='+alias, code=1)
        self.assertEqual(before, self.snapshot())
        self.cli('remove', 'config-rework', '--recursive', '--yes')
        self.cli('add', 'Reserved', '--alias', 'config-rework', code=1)
        self.cli('restore', '@config-rework', '--recursive')
        self.cli('edit', 'config-rework', '--alias', 'new-name')
        self.cli('show', 'config-rework', code=1)
        self.cli('edit', 'new-name', '--clear', 'alias')
        self.assertIsNone(self.store().find(goal['id'])['alias'])
        self.add('Released name', alias='new-name')

    def test_alias_completion_and_hex_disambiguation(self):
        from todo_completion import complete
        goal = self.add('Named', alias='config-rework')
        hex_goal = self.add('Hex name', alias='dead')
        self.assertEqual(self.store().find('@dead')['id'], hex_goal['id'])
        self.cli('show', 'dead', code=1)
        long_hex = self.add('Long hex name', alias='a'*64)
        self.assertEqual(self.store().find('@'+'a'*64)['id'], long_hex['id'])
        self.cli('show', 'a'*64, code=1)
        before = self.snapshot()
        for words, expected in [(['show', 'conf'], 'config-rework'), (['show', '@conf'], '@config-rework'),
                                (['note', ''], 'config-rework'), (['note', '@d'], '@dead'),
                                (['show', goal['id'][:7]], goal['id']), (['add', '--parent', 'conf'], 'config-rework')]:
            output = io.StringIO()
            with patch('sys.stdout', output): complete(words)
            self.assertIn('candidate\t'+expected+'\t', output.getvalue())
        self.assertEqual(before, self.snapshot())
        result = json.loads(self.cli('list', '--query', 'config-rework', '--json').stdout)
        self.assertEqual([g['id'] for g in result['goals']], [goal['id']])
        self.cli('remove', 'config-rework', '--yes')
        output = io.StringIO()
        with patch('sys.stdout', output): complete(['restore', 'conf'])
        self.assertIn('config-rework', output.getvalue())

    def test_schema_one_reads_noop_migration_and_undo(self):
        from todo_core import Store, state_root
        goal = self.add('Legacy', notes='Keep exact notes\n')
        path = Path(scope()['path'])
        doc = json.loads(path.read_text()); doc['schema'] = 1
        for item in doc['goals']: item.pop('alias')
        original = json.dumps(doc, ensure_ascii=False).encode() + b'\n'
        path.write_bytes(original)
        before = self.snapshot()
        shown = json.loads(self.cli('show', goal['id'], '--json').stdout)
        self.assertEqual(shown['schema'], 2); self.assertIsNone(shown['goals'][0]['alias'])
        self.cli('edit', goal['id'], '--alias', 'legacy', '--dry-run', '--json')
        noop = json.loads(self.cli('edit', goal['id'], '--notes', goal['notes'], '--json').stdout)
        self.assertEqual(noop['status'], 'unchanged')
        self.assertEqual(before, self.snapshot())
        update = json.loads(self.cli('edit', goal['id'], '--alias', 'legacy', '--json').stdout)
        self.assertEqual(json.loads(path.read_text())['schema'], 2)
        store = Store(state_root())
        operations, guards, catalogs = store.inverse(update['transaction'])
        store.apply('undo', operations, guards, catalogs=catalogs, retain=True)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(self.store().find(goal['id'])['notes'], goal['notes'])

    def test_note_append_limits_dry_run_and_stale_write(self):
        from todo_menu import apply
        goal = self.add(notes='Original\n', alias='work')
        before = self.snapshot()
        planned = json.loads(self.cli('note', 'work', 'First\nSecond', '--dry-run', '--json').stdout)
        self.assertEqual(planned['goals'][0]['notes'], 'Original\n\nFirst\nSecond')
        for args, code in [(('note','work',''),1), (('note','work','   '),1), (('note','work','--json'),2),
                           (('note','work','x'*32768),1)]:
            self.cli(*args, code=code)
        self.assertEqual(before, self.snapshot())
        old = self.store()
        (self.dots/'bin').mkdir()
        shutil.copy2(ROOT/'bin/dots-todo-note', self.dots/'bin/dots-todo-note')
        result = json.loads(self.cli('note', 'work', 'First\nSecond', '--json', native=True).stdout)
        self.assertEqual(result['schema'], 2)
        self.assertEqual(result['goals'][0]['notes'], planned['goals'][0]['notes'])
        with self.assertRaisesRegex(ValueError, 'changed'): apply(old, 'note', goal['id'], note='Stale')
        self.cli('note', '@work', 'Literal $(never-run)\x1b[31m', '--json')
        self.assertTrue(self.store().find('work')['notes'].endswith('\n\nLiteral $(never-run)\x1b[31m'))
        self.cli('edit', 'work', '--notes', 'Replacement')
        self.assertEqual(self.store().find('work')['notes'], 'Replacement')
        self.cli('remove', 'work', '--yes')
        self.cli('note', 'work', 'Removed', code=1)

    def test_note_input_cancellation_is_inert(self):
        from todo_cli import run
        from interaction import SelectionEnded
        goal = self.add(alias='work'); before = self.snapshot()
        with patch('todo_cli.terminal', return_value=True), patch('todo_input.prompt', side_effect=SelectionEnded(130)):
            with self.assertRaises(SelectionEnded): run(['note', 'work'])
        self.assertEqual(before, self.snapshot())

    def test_semantic_spans_details_and_data_bytes(self):
        from todo_presentation import summary, detail, compact
        from files.catalog import Presentation
        from resources import cells
        goal = self.add('Long title 界 '*8, alias='config-rework', notes='First\n\nSecond', accept=['Check it'])
        directory=self.home/'state/dots/current/theme'; directory.mkdir(parents=True)
        colors=dict(accent='#123456', bright_magenta='#789abc', warning='#89abcd', hint='#234567',
                    bright_green='#6789ab', bright_red='#345678', orange='#456789', muted='#56789a')
        for bg,fg in (('#111111','#eeeeee'),('#eeeeee','#111111')):
            (directory/'palette.json').write_text(json.dumps(dict(colors=dict(colors, background=bg, foreground=fg))))
            for priority,code in [('high','1;38;2;137;171;205'),('normal','38;2;69;103;137'),('low','1;38;2;86;120;154')]:
                goal['priority']=priority
                for width in (40,80,120):
                    stream=io.StringIO()
                    with patch.dict(os.environ,DOTS_COLOR='always',DOTS_ICONS='never',TERM='xterm-256color'):
                        ui=Presentation(stream,terminal=True,detail_indent=2);ui.width=width
                        summary(ui,goal);detail(ui,goal)
                        row=compact(ui,goal,width)
                    output=stream.getvalue()
                    self.assertIn('\x1b[1;38;2;18;52;86m',output)
                    self.assertIn('\x1b[1;38;2;120;154;188mLong title',output)
                    self.assertIn('\x1b[1;38;2;120;154;188mLong title',row)
                    self.assertIn('\x1b[1;38;2;18;52;86mconfig-rework\x1b[0m',output)
                    self.assertIn('\x1b[1;38;2;103;137;171mopen\x1b[0m',output)
                    self.assertIn('\x1b[1;38;2;103;137;171mopen\x1b[0m',row)
                    self.assertIn('\x1b['+code+'m'+priority+'\x1b[0m',output)
                    self.assertIn('\x1b['+code+'m'+priority+'\x1b[0m',row)
                    plain=re.sub(r'\x1b\[[0-9;]*m','',output)
                    self.assertIn(goal['id'],plain)
                    self.assertTrue(all(cells(line)<=width for line in plain.splitlines()))
                    self.assertLessEqual(cells(re.sub(r'\x1b\[[0-9;]*m','',row)),width)
        forced=dict(self.env,DOTS_COLOR='always',DOTS_ICONS='always')
        for args in [('list','--json'),('list','--markdown'),('show','config-rework','--json'),('show','config-rework','--markdown'),('brief','config-rework'),('path',)]:
            self.assertEqual(self.cli(*args).stdout,self.cli(*args,env=forced).stdout)
        shown=self.cli('show','config-rework').stdout
        self.assertIn('Notes\n',shown);self.assertIn('UUID',shown)
        self.assertIn('Priority',shown);self.assertNotIn('\x1b',shown)

    def test_list_separates_complete_goal_blocks(self):
        from resources import cells
        # Native family dispatch discovers its routes from the fixture's metadata.
        (self.dots/'bin').mkdir()
        for name in ('dots-todo','dots-todo-list'):
            shutil.copy2(ROOT/'bin'/name,self.dots/'bin'/name)
        for count in range(4):
            if count:
                self.add(('Goal 界 '+str(count)+' ')*12, alias='goal-'+str(count))
            for width in (40,80,120):
                for mode in ('never','always'):
                    env=dict(self.env,COLUMNS=str(width),DOTS_COLOR=mode,TERM='xterm-256color')
                    listed=self.cli('list',env=env).stdout
                    plain=re.sub(r'\x1b\[[0-9;]*m','',listed)
                    self.assertEqual(plain.count('\n\n'),max(0,count-1))
                    self.assertFalse(plain.startswith('\n'))
                    self.assertFalse(plain.endswith('\n\n'))
                    self.assertTrue(all(cells(line)<=width for line in plain.splitlines()))
                    self.assertTrue(all(line.startswith('  ') and not line.startswith('   ') for line in plain.splitlines()[1:] if line))
                    self.assertIn('  Project ~/dots\n  Goals '+str(count)+'\n',plain)
                    if count:
                        blocks=plain.split('\n\n')
                        for index,block in enumerate(blocks,1):
                            self.assertEqual(len(re.findall(r'goal-\d',block)),1)
                            self.assertIn('goal-'+str(index),block)
                            self.assertIn('  goal-'+str(index)+'\n  Goal 界 '+str(index),block)
                            self.assertIn('open',block);self.assertIn('normal',block)
                    else:
                        self.assertIn('No matching goals.',plain)
            # Every printed-list entry point shares spacing, including the native bridge.
            expected=self.cli('list').stdout
            for args in ((),('--print',),('browse','--print')):
                self.assertEqual(self.cli(*args).stdout,expected)
            for native in (False,True):
                self.assertEqual(self.cli('--project',str(self.dots),'list',standalone=True,native=native).stdout,expected)
            self.assertEqual(self.cli('list',native=True).stdout,expected)

    def test_list_long_alias_and_uuid_stack_without_truncation(self):
        from resources import cells
        alias='long-'+'g'*59
        named=self.add('Named title 界 '*8,alias=alias)
        unnamed=self.add('Unnamed title 界 '*8)
        before=self.snapshot()
        for width in (40,80,120):
            output=self.cli('list',env=dict(self.env,COLUMNS=str(width))).stdout
            self.assertTrue(all(cells(line)<=width for line in output.splitlines()))
            lines=output.splitlines()[3:]
            title_index=next(i for i,line in enumerate(lines) if line.startswith('  Named title'))
            self.assertEqual(''.join(line[2:] for line in lines[:title_index]),alias)
            self.assertIn('\n  '+unnamed['id'][:8]+'\n  Unnamed title',output)
            self.assertNotIn(named['id'][:8],output)
            self.assertNotIn('…',output)
        self.assertEqual(before,self.snapshot())

    def test_todo_detail_help_results_and_preview_use_two_spaces(self):
        from todo_menu import rows
        from files.catalog import Presentation
        (self.dots/'bin').mkdir()
        for name in ('dots-todo', 'dots-todo-list'):
            shutil.copy2(ROOT/'bin'/name,self.dots/'bin'/name)
        goal=self.add('Layout goal',alias='layout',notes='Line one\n\nLine two',accept=['First check'])
        before=self.snapshot()
        for width in (40,45,80,120):
            env=dict(self.env,COLUMNS=str(width))
            shown=self.cli('show','layout',env=env).stdout
            self.assertIn('\n  Project ',shown)
            self.assertIn('\n  Alias      layout\n',shown)
            self.assertIn('\n  Status     open\n',shown)
            self.assertIn('Notes\n  Line one\n\n  Line two\n',shown)
            self.assertIn('Acceptance\n  - First check\n',shown)
            if width<45:self.assertIn('\n  '+goal['id']+'\n',shown)
            else:self.assertIn('  UUID       '+goal['id']+'\n',shown)
            help_text=self.cli('--help',standalone=True,env=env).stdout
            self.assertIn('\n  Usage ',help_text);self.assertIn('\n  list ',help_text)
            for args in (('--help',), ('list', '--help')):
                native_help=self.cli(*args,native=True,env=env).stdout
                self.assertIn('\n  Usage ',native_help)
                self.assertIn('\n  --color ',native_help)
            result=self.cli('edit','layout','--notes='+goal['notes'],'--dry-run',env=env).stdout
            self.assertIn('\n  Result ',result)
            ui=Presentation(io.StringIO(),terminal=True,detail_indent=2);ui.width=width
            _,previews=rows(self.store(),[goal],ui,width)
            self.assertIn('\n  Status     open\n',previews[0])
            self.assertIn('Notes\n  Line one',previews[0])
        self.assertEqual(before,self.snapshot())

    def test_alias_styles_and_uuid_fallbacks(self):
        from files.catalog import Presentation
        from todo_presentation import summary, compact, detail
        parent=self.add('Parent goal',alias='parent-goal')
        goal=self.add('Child goal',alias='child',parent=parent['id'])
        directory=self.home/'state/dots/current/theme';directory.mkdir(parents=True)
        (directory/'palette.json').write_text(json.dumps(dict(colors=dict(accent='#123456',blue='#234567'))))
        accent='1;38;2;18;52;86'
        for alias in (None,'child','g'*64,'dead'):
            goal['alias']=alias
            label=('@dead' if alias=='dead' else alias) or goal['id'][:8]
            for width in (40,80,120):
                with patch.dict(os.environ,DOTS_COLOR='always',DOTS_ICONS='never',TERM='xterm-256color'):
                    stream=io.StringIO();ui=Presentation(stream,terminal=True,detail_indent=2);ui.width=width
                    summary(ui,goal)
                    code=accent if alias else '94'
                    parts=re.findall(r'\x1b\['+re.escape(code)+r'm([^\x1b]*)\x1b\[0m',stream.getvalue())
                    self.assertEqual(''.join(part.strip() for part in parts),label)
                    row=compact(ui,goal,width)
                    code=accent if alias else '38;2;35;69;103'
                    self.assertTrue(row.startswith('\x1b['+code+'m'+label[:4]))
                    stream.seek(0);stream.truncate()
                    detail(ui,goal,goals=[parent,goal])
                    text=stream.getvalue()
                    self.assertIn('\x1b['+accent+'mparent-goal\x1b[0m',text)
                    parts=re.findall(r'\x1b\['+re.escape(accent)+r'm([^\x1b]*)\x1b\[0m',text)
                    self.assertEqual(''.join(parts),(label if alias else '')+'parent-goal')
                    # Unnamed or unavailable parents retain the UUID field treatment.
                    stream.seek(0);stream.truncate()
                    detail(ui,goal,goals=[dict(parent,alias=None),goal])
                    self.assertNotIn('\x1b['+accent+'m'+parent['id'],stream.getvalue())

    def test_color_fallbacks_and_plain_controls(self):
        from files.catalog import Presentation
        from todo_presentation import summary, compact
        goal=self.add('Open goal',alias='work',priority='high')
        for mode,no_color,expected in [('auto','',True),('auto','1',False),('never','',False),('always','1',True)]:
            stream=io.StringIO()
            with patch.dict(os.environ,DOTS_COLOR=mode,NO_COLOR=no_color,TERM='xterm-256color'):
                ui=Presentation(stream,terminal=True,detail_indent=2)
                summary(ui,goal)
                row=compact(ui,goal,80)
            for output in (stream.getvalue(),row):
                self.assertEqual('\x1b[1;92mopen\x1b[0m' in output,expected)
                self.assertEqual('\x1b[1;95mOpen goal\x1b[0m' in output,expected)
                self.assertEqual('\x1b[1;33mhigh\x1b[0m' in output,expected)
                self.assertEqual('\x1b[1;35m' in output,expected)
                self.assertEqual('\x1b[' in output,expected)

    @unittest.skipIf(os.name=='nt','POSIX PTY; native PowerShell has its own runner')
    def test_help_real_tty_and_redirected_color_policy(self):
        import pty,select,fcntl,termios,struct
        from resources import cells
        before=self.snapshot()
        for width,mode,no_color,action in [(40,'auto','',[]),(80,'auto','1',[]),(120,'always','1',['note']),(40,'never','',[])]:
            master,slave=pty.openpty()
            fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',24,width,0,0))
            env=dict(self.env,TERM='xterm-256color',NO_COLOR=no_color,FORCE_COLOR='1',PYTHON_COLORS='1')
            child=subprocess.Popen([sys.executable,'-B',str(ROOT/'lib/dots/todo_standalone.py'),*action,'--color',mode,'--help'],
                                   stdin=slave,stdout=slave,stderr=slave,env=env)
            os.close(slave); output=b''
            try:
                deadline=time.monotonic()+10
                while time.monotonic()<deadline:
                    if select.select([master],[],[],.1)[0]:
                        try: chunk=os.read(master,65536)
                        except OSError: break
                        if not chunk: break
                        output+=chunk
                    elif child.poll() is not None: break
                self.assertEqual(child.wait(timeout=2),0)
            finally:
                if child.poll() is None: child.kill();child.wait()
                os.close(master)
            decoded=output.decode()
            self.assertNotIn('\\x1b',decoded)
            self.assertEqual('\x1b[' in decoded,mode=='always' or (mode=='auto' and not no_color))
            plain=re.sub(r'\x1b\[[0-9;]*m','',decoded)
            self.assertNotIn('usage:',plain)
            self.assertTrue(all(cells(line)<=width for line in plain.splitlines()))
            self.assertIn('todo note ID [TEXT]',plain) if action else self.assertIn('todo [COMMAND]',plain)
        captured=self.cli('--help',standalone=True).stdout
        self.assertNotIn('\x1b',captured);self.assertNotIn('\\x1b',captured)
        self.assertEqual(before,self.snapshot())


if __name__=='__main__':unittest.main()

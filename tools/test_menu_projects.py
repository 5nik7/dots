#!/usr/bin/env python3
"""Project session actions in owned directories/servers; Android launch is mocked."""
from contextlib import redirect_stdout
from dataclasses import replace
import io
import json
import os
from pathlib import Path
import re
import subprocess
import time
import unittest
from unittest.mock import Mock, patch

from test_menus import MenuFixture, NativeMenuFixture
from interaction import RichSelector, SelectionEnded, SelectionEvent
import menu_projects as projects
import menu_sessions as sessions
import menu_session_host as host
import menu_session_ui as ui
from menu_tmux import TmuxContext


class Projects(MenuFixture):
    def repo(self, path):
        path.mkdir(parents=True); (path / '.git').mkdir()
        return path.resolve()

    def config(self, data):
        path = Path(self.env['XDG_CONFIG_HOME']) / 'dots/projects.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))

    def test_shallow_discovery_deduplication_and_explicit_paths(self):
        a = self.repo(self.home / 'repos/a ü')
        b = self.repo(self.home / 'repos/b')
        nested = self.repo(a / 'nested')
        dots = self.repo(Path(self.env['DOTS']))
        custom = self.base / 'work/-project'; custom.mkdir(parents=True)
        (self.home / 'repos/alias').symlink_to(a, target_is_directory=True)
        (self.home / 'repos/broken').symlink_to(self.base / 'missing')
        self.config(dict(schema=1, roots=[str(self.home / 'repos'), str(self.base / 'missing')], projects=[str(custom), str(a)]))
        with patch('subprocess.run', side_effect=AssertionError('discovery ran a program')):
            found = projects.discover()
        self.assertEqual({p.root for p in found}, {a, b, dots, custom})
        self.assertNotIn(nested, {p.root for p in found})

    def test_config_is_strict_and_not_needed_by_data_output(self):
        for data in ({'schema': 2}, {'schema': True}, {'schema': 1, 'projects': 'bad'}, {'schema': 1, 'roots': ['relative']}):
            self.config(data)
            with self.assertRaises(ValueError): projects.discover()
        with patch.object(sessions.Server, 'discover', return_value=None), redirect_stdout(io.StringIO()) as output:
            self.assertEqual(sessions.main(['--json']), 0)
        self.assertEqual(json.loads(output.getvalue())['items'], [])

    def test_association_precedence_and_ambiguity(self):
        a = projects.Project(self.base / 'a', 'a'); b = projects.Project(self.base / 'b', 'b')
        s = sessions.Session('$1', 'renamed', 1, 0, False, 12)
        for replies, expected in [([str(a.root)+'\n'], a), (['',str(b.root / 'sub')+'\n'], b),
                                  (['','','%1\n%2\n',str(a.root),str(b.root)], None),
                                  (['','','%1\n%2\n',str(a.root),str(a.root / 'sub')], a)]:
            self.assertEqual(projects.associate(Mock(read=Mock(side_effect=['', '', *replies])), s, (a,b)), expected)

    def test_active_inactive_generic_order_and_counts(self):
        a, b = [projects.Project(self.base / n, n) for n in ('a','b')]
        items = tuple(sessions.Session('$'+str(i), n, 1, 0, False, 12) for i,n in enumerate(('z','a','generic')))
        with patch('menu_projects.associate', side_effect=[b,b,None]):
            rows = projects.inventory(Mock(), items, (a,b))
        self.assertEqual([r.label for r in rows], ['b','a','generic'])
        self.assertEqual([s.name for s in rows[0].sessions], ['a','z'])

    def test_default_termux_marker_precedes_project_tag_without_name_heuristics(self):
        project = projects.Project(self.home, 'home')
        for name in ('termux-123', 'renamed-default'):
            record = sessions.Session('$1', name, 1, 0, False, 12)
            server = Mock(read=Mock(side_effect=['', '1\n']))
            self.assertIsNone(projects.associate(server, record, (project,)))
            self.assertEqual(server.read.call_count, 2)
            server.read.assert_called_with('show-options', '-qv', '-t', '$1', '@dots-termux-default')
        record = replace(record, name='termux-unmarked')
        self.assertEqual(projects.associate(Mock(read=Mock(side_effect=['', '', str(self.home)])), record, (project,)), project)

    def test_compact_preview_home_paths_pluralization_and_geometry(self):
        from files.catalog import Presentation
        project = projects.Project(self.home / 'repos/battery', 'battery')
        record = sessions.Session('$1', 'battery', 1, 0, False, 12)
        row = projects.Row('project', 'battery', project, (record,))
        text = ui.render((row,), Presentation(terminal=True), 76)[1][0]
        self.assertEqual(text, 'battery · [1 session]\nProject: ~/repos/battery\n  1 window · 0 attached\n')
        self.assertEqual(ui.short_path(self.home), '~')
        self.assertEqual(ui.short_path(self.base / 'elsewhere'), str(self.base / 'elsewhere'))
        self.assertEqual(ui.preview_height([text], 30), 5)
        self.assertEqual(ui.preview_height(['line\n'*20], 30), 8)
        self.assertEqual(ui.preview_height(['界'*20], 30), 3)
        self.assertEqual(ui.preview_height(['e\u0301'*20], 30), 3)
        self.assertLessEqual(ui.preview_height([text], 14), 3)
        renamed = ui.render((replace(row, sessions=(replace(record, name='other'),)),), Presentation(terminal=True), 76)[1][0]
        self.assertIn('  other: 1 window', renamed)
        inactive = ui.render((replace(row, sessions=()),), Presentation(terminal=True), 76)[1][0]
        self.assertEqual(len(inactive.splitlines()), 2); self.assertIn('[0 sessions]', inactive)
        generic = ui.render((projects.Row('$1', 'battery', sessions=(record,)),), Presentation(terminal=True), 76)[1][0]
        self.assertEqual(generic, 'battery\n  1 window · 0 attached\n')

    def test_preview_uses_published_semantic_and_directory_styles_and_color_policy(self):
        from files.catalog import Presentation
        directory = Path(self.env['XDG_STATE_HOME']) / 'dots/current/theme'
        directory.mkdir(parents=True)
        (directory/'file-styles.tsv').write_text('dots-file-styles\t1\ntype\tdir\t1;38;2;4;5;6\t-\n')
        def project(label, *items):
            return projects.Row(label,label,projects.Project(self.home/'repos'/label,label),items)
        current=sessions.Session('$1','current',1,1,True,12)
        active=sessions.Session('$2','active',2,2,False,13)
        loose=sessions.Session('$3','loose',3,0,False,14)
        rows=(project('current',current), project('active',active), project('inactive'),
              projects.Row('$3','loose',sessions=(loose,)), project('mixed',current,loose),
              projects.Row('$1','current',sessions=(current,)))
        for foreground,accent,name_style in (('#eeeeee','#112233','1;38;2;17;34;51'),
                                             ('#111111','#ccddee','1;38;2;204;221;238')):
            (directory/'palette.json').write_text(json.dumps({'colors':{'foreground':foreground,
                'muted':'#8899aa','bright_magenta':'#aabbcc','orange':'#ff8800',
                'green':'#00aa44','yellow':'#ffdd00','blue':'#2255cc','accent':accent,
                'light_foreground':'#bbccdd','red':'#ff3344','bright_green':'#44ee66'}}))
            for width in (40,80,120):
                for mode,no_color,colored in (('auto','',True),('auto','1',False),('always','1',True),('never','',False)):
                    for icons in ('always','never'):
                        with patch.dict(os.environ,DOTS_COLOR=mode,NO_COLOR=no_color,DOTS_ICONS=icons):
                            labels,previews=ui.render(rows,Presentation(terminal=True),width)
                        plain=[ui.ANSI.sub('',text) for text in previews]
                        folder='󰉋 ' if icons=='always' else ''
                        self.assertEqual(plain[1], 'active · [1 session]\nProject: '+folder+'~/repos/active\n  2 windows · 2 attached\n')
                        self.assertEqual('\x1b' in ''.join(labels+previews),colored)
                        for index,row in enumerate(rows):
                            glyph='' if row.project else ''
                            self.assertEqual(glyph in labels[index],icons=='always')
                            self.assertNotIn('󰉋',labels[index])
                        if not colored:
                            continue
                        emphasis,muted='1;38;2;170;187;204','38;2;136;153;170'
                        blue='1;38;2;34;85;204'
                        expected=(emphasis,name_style,'38;2;187;204;221',blue,emphasis,emphasis)
                        for row,label,code in zip(rows,labels,expected):
                            icon=(('' if row.project else '')+' ') if icons=='always' else ''
                            self.assertIn('\x1b['+code+'m'+icon+row.label,label)
                        for i,code in ((1,name_style),(3,blue)):
                            self.assertTrue(previews[i].startswith('\x1b['+code+'m'+rows[i].label+'\x1b[0m'))
                        for i in (0,4,5):
                            self.assertTrue(previews[i].startswith('\x1b['+emphasis+'m'+rows[i].label+'\x1b[0m'))
                        self.assertIn('\x1b['+name_style+'mloose: \x1b[0m',previews[4])
                        self.assertIn('\x1b['+emphasis+'mcurrent: \x1b[0m',previews[4])
                        count_style='38;2;255;136;0'
                        bright_green='38;2;68;238;102'
                        for i,count,code in ((0,'1 session',count_style),(1,'1 session',count_style),
                                             (2,'0 sessions','38;2;255;51;68'),(4,'2 sessions',count_style)):
                            self.assertIn('\x1b['+muted+'m · \x1b[0m\x1b['+code+'m['+count+']\x1b[0m',previews[i])
                        self.assertTrue(previews[2].startswith('\x1b[1;38;2;187;204;221minactive\x1b[0m'))
                        count='[1]' if width<52 else '1 session'
                        self.assertIn('\x1b['+count_style+'m'+count+'\x1b[0m',labels[1])
                        marker=' · '+(' ' if icons=='always' else '')+'current'
                        for i,wide,narrow in ((0,'1 session','[1]'),(4,'2 sessions','[2]'),(5,'1 win','1w')):
                            current_count=narrow if width<52 else wide
                            self.assertIn('\x1b['+count_style+'m'+current_count+'\x1b[0m'
                                          '\x1b[1;'+bright_green+'m'+marker+'\x1b[0m',labels[i])
                        self.assertIn('\x1b['+muted+'mno session\x1b[0m',labels[2])
                        self.assertIn('\x1b[38;2;0;170;68m1 window\x1b[0m',previews[0])
                        self.assertIn('\x1b[38;2;0;170;68m2 windows\x1b[0m',previews[1])
                        self.assertIn('\x1b[38;2;255;221;0m1 attached\x1b[0m',previews[0])
                        self.assertIn('\x1b[38;2;255;221;0m2 attached\x1b[0m',previews[1])
                        self.assertIn('\x1b['+muted+'m0 attached\x1b[0m',previews[3])
                        self.assertIn('\x1b['+muted+'m · \x1b[0m',previews[3])
                        self.assertIn('\x1b[1;38;2;4;5;6m'+folder+'~/repos/current\x1b[0m',previews[0])
                        for i in (0,4,5):
                            self.assertIn('\x1b[1;'+bright_green+'m · current\x1b[0m',previews[i])

    def test_named_style_fallbacks_key_compatibility_and_one_palette_read(self):
        from files.catalog import Presentation
        from picker_style import named_styles, styles
        directory=Path(self.env['XDG_STATE_HOME'])/'dots/current/theme'
        directory.mkdir(parents=True)
        path=directory/'palette.json'
        presentation=Presentation(terminal=True)
        for data in (None,'{','[]','{"colors":[]}',json.dumps({'colors':{'accent':'bad','green':'\x1b[31m','yellow':None,'blue':'bad','bright_green':'bad'}})):
            if data is not None: path.write_text(data)
            codes=named_styles(presentation)
            self.assertEqual((codes['accent'],codes['green'],codes['yellow']),('1;35','32','33'))
            self.assertEqual((codes['foreground'],codes['light_foreground'],codes['red']),('39','39','31'))
            self.assertEqual(codes['blue'],'34')
            self.assertEqual(codes['bright_green'],'92')
            self.assertEqual(styles(presentation),('2;37','1;95','38;5;208'))
        path.write_text(json.dumps({'colors':{'muted':'#112233','bright_magenta':'#445566','orange':'#778899'}}))
        self.assertEqual(styles(presentation),('38;2;17;34;51','1;38;2;68;85;102','38;2;119;136;153'))
        path.write_text(json.dumps({'colors':{'foreground':'#223344','light_foreground':'bad','red':'bad'}}))
        codes=named_styles(presentation)
        self.assertEqual(codes['light_foreground'], '38;2;34;51;68')
        self.assertEqual(codes['red'],'31')
        from resources import read_data
        row=projects.Row('inactive','inactive',projects.Project(self.home,'inactive'))
        with patch('picker_style.read_data',wraps=read_data) as read:
            ui.render((row,row,row),presentation,80)
        read.assert_called_once_with(path)

    def test_project_count_color_does_not_spread_to_duplicate_paths_or_truncation(self):
        from files.catalog import Presentation
        from resources import cells
        item=sessions.Session('$1','same',1,2,False,12)
        rows=tuple(projects.Row(str(i),'same',projects.Project(self.home/n/'same','same'),(item,))
                   for i,n in enumerate(('α'*20,'β'*20)))
        for current in (False,True):
            current_rows=tuple(replace(row,sessions=(replace(item,current=current),)) for row in rows)
            for width in (40,80,120):
                with patch.dict(os.environ,DOTS_COLOR='always',DOTS_ICONS='always'):
                    labels,previews=ui.render(current_rows,Presentation(terminal=True),width)
                count='[1]' if width<52 else '1 session'
                color='38;5;208'
                marker='\x1b[1;92m ·  current\x1b[0m' if current else ''
                for label in labels:
                    self.assertIn('\x1b['+color+'m'+count+'\x1b[0m'+marker+'\x1b[2;37m · ~/',label)
                    self.assertLessEqual(cells(ui.ANSI.sub('',label)),width)
                self.assertIn('\x1b['+color+'m[1 session]\x1b[0m',previews[0])

    def test_action_events_validate_selection_even_with_empty_search(self):
        for data, expected in [(b'q\0alt-d\0' + b'1\tlabel\0',1), (b'no match\0alt-n\0',None)]:
            frame={}
            with patch('interaction.subprocess.run', return_value=subprocess.CompletedProcess([], 0 if expected else 1, data)):
                with self.assertRaises(SelectionEvent) as event:
                    RichSelector('fzf').fzf('dots', ['a','b'], False, None, False, False, '', navigation=frame,
                                            navigation_keys={'alt-d':'delete','alt-n':'new'}, event_selection=True)
            self.assertEqual(event.exception.index, expected); self.assertEqual(event.exception.query, frame['query'])
        for token in (b'99', b'-1', b'01', b'$(touch sentinel)', b'0\0' + b'1'):
            with patch('interaction.subprocess.run', return_value=subprocess.CompletedProcess([], 0, b'\0alt-d\0'+token+b'\0')):
                with self.assertRaises(ValueError):
                    RichSelector('fzf').fzf('dots',['a','b'],False,None,False,False,'',navigation={},
                                            navigation_keys={'alt-d':'delete'},event_selection=True)

    def test_semantic_rows_and_preview_sanitize_without_losing_details(self):
        from files.catalog import Presentation
        s = sessions.Session('$1', '日本語\x1b[31m $(touch sentinel)', 3, 2, True, 12)
        rows = (projects.Row('a','日本語'*20, projects.Project(self.base / '日本語','日本語'), (s,)),)
        for width in (40,80,120):
            for mode in ('always','never'):
                with patch.dict(os.environ, DOTS_COLOR=mode, DOTS_ICONS=mode):
                    labels, previews = ui.render(rows, Presentation(terminal=True), width)
                self.assertEqual('\x1b' in labels[0], mode=='always')
                self.assertIn('current', labels[0]); self.assertEqual('\x1b' in previews[0], mode=='always')
                self.assertNotIn('\x1b[31m', previews[0]); self.assertIn(r'\x1b[31m', previews[0])
                self.assertIn(str(self.base / '日本語'), previews[0]); self.assertIn('3 windows · 2 attached', ui.ANSI.sub('',previews[0]))
        self.assertFalse((self.home/'sentinel').exists())

    def test_focus_restores_fuzzy_order_and_nontermux_hides_action(self):
        picker=RichSelector('fzf'); frame={}
        answers=[subprocess.CompletedProcess([],0,b'1\tbeta\0' + b'0\talpha\0'),
                 subprocess.CompletedProcess([],0,b'a\0esc\0' + b'0\talpha\0')]
        with patch('interaction.subprocess.run',side_effect=answers) as run:
            with self.assertRaises(SelectionEvent):
                picker.fzf('dots',['alpha','beta'],False,None,False,False,'',navigation=frame,
                           event_selection=True,query='a',focus_index=0)
        self.assertIn('--bind=load:pos(2)',run.call_args.args[0])
        self.assertEqual(run.call_args_list[0].kwargs['env']['FZF_DEFAULT_OPTS'],'')
        row=projects.Row('a','alpha',projects.Project(self.home,'alpha'))
        for termux in (False,True):
            with patch('menu_session_ui.terminal',return_value=True), patch('menu_session_ui.rich_fzf_available',return_value=True), \
                    patch.object(RichSelector,'fzf',return_value=[0]) as run:
                ui.pick((row,),termux=termux)
            self.assertEqual('alt-t' in run.call_args.kwargs['navigation_keys'],termux)
            self.assertEqual(run.call_args.kwargs['navigation_keys']['alt-h'],'keys')
            self.assertEqual(run.call_args.kwargs['header'],'Alt-H: keys')
            self.assertEqual(run.call_args.kwargs['preview_position'],'down')
            self.assertFalse(run.call_args.kwargs['preview_wrap'])

    def test_key_reference_filters_termux_and_ignores_enter(self):
        for termux in (False, True):
            with patch.object(RichSelector, 'fzf', side_effect=SelectionEvent('back')) as picker:
                ui.show_keys(termux=termux, intent='delete')
            labels = '\n'.join(picker.call_args.args[1])
            self.assertEqual('Alt-T' in labels, termux)
            self.assertIn('Choose to delete', labels)
            self.assertIn('enter:ignore', picker.call_args.kwargs['bindings'])
        with patch.object(RichSelector, 'fzf', side_effect=SelectionEnded(130)):
            with self.assertRaises(SelectionEnded): ui.show_keys()

    def test_absolute_preview_is_opt_in_and_validated(self):
        for options, flag in (({}, '--preview-window=down,55%'),
                              ({'preview_lines':5, 'preview_wrap':True}, '--preview-window=down,5,wrap')):
            with patch('interaction.subprocess.run', return_value=subprocess.CompletedProcess([],0,b'0\trow\0')) as run:
                RichSelector('fzf').fzf('dots',['row'],False,('preview {1}','',{}),False,False,'',
                                        preview_position='down', **options)
            self.assertIn(flag,run.call_args.args[0])
        for value in (0,-1,True,'5'):
            with self.assertRaises(ValueError):
                RichSelector('fzf').fzf('dots',[],False,None,False,False,'',preview_lines=value)

    def test_gum_cancel_does_not_fall_through_and_plain_input_is_literal(self):
        with patch('menu_session_host.terminal',return_value=True), patch('shutil.which',return_value='/gum'), \
                patch('subprocess.run',return_value=subprocess.CompletedProcess([],130,'')), \
                patch('builtins.input',side_effect=AssertionError('fallback after cancellation')):
            self.assertIsNone(host.prompt('initial','New session'))
        with patch('menu_session_host.terminal',return_value=True), patch('shutil.which',return_value=None), \
                patch('builtins.input',return_value='-日本語 $(touch sentinel);'),redirect_stdout(io.StringIO()):
            self.assertEqual(host.prompt('initial','New session'),'-日本語 $(touch sentinel);')
        self.assertFalse((self.home/'sentinel').exists())

    def test_termux_action_uses_literal_payload_and_string_session_action(self):
        server = sessions.Server('/tool/tmux', '/socket ü,$(touch sentinel)', 12)
        record = sessions.Session('$2', '-name;literal', 2, 1, False, 33)
        with patch('menu_session_host.is_termux', return_value=True), patch('menu_session_host.termux_transport', return_value='/tool/termux-am'), \
                patch.object(sessions.Server,'validate'), patch('menu_session_host.subprocess.run', return_value=subprocess.CompletedProcess([],0,'Starting service','')) as run:
            host.launch_termux(server, record, str(self.home))
        args=run.call_args.args[0]
        index=args.index('com.termux.execute.session_action')
        self.assertEqual(args[index-1:index+2], ['--es','com.termux.execute.session_action','0'])
        encoded=args[args.index('com.termux.execute.arguments')+1].split(',')[-1]
        with patch.object(sessions.Server,'select', return_value=0) as select, patch.dict(os.environ, TMUX='old', TMUX_PANE='%1'):
            self.assertEqual(host.attach(encoded),0)
            self.assertNotIn('TMUX',os.environ)
        self.assertEqual(select.call_args.args[0],record)
        self.assertFalse((self.home/'sentinel').exists())

    def test_termux_array_preserves_helper_path_commas_and_backslashes(self):
        import re
        server=sessions.Server('/tool/tmux','/socket',1); record=sessions.Session('$1','n',1,0,False,2)
        helper=str(self.base / r'dir,with\commas,ü' / 'menu_session_host.py')
        with patch('menu_session_host.__file__',helper), patch('menu_session_host.is_termux',return_value=True), \
                patch('menu_session_host.termux_transport',return_value='/am'), patch.object(sessions.Server,'validate'), \
                patch('subprocess.run',return_value=subprocess.CompletedProcess([],0,'','')) as run:
            host.launch_termux(server,record,str(self.home))
        args=run.call_args.args[0]
        encoded=args[args.index('com.termux.execute.arguments')+1]
        # TermuxAm IntentCmd's documented --esa decoding boundary.
        decoded=[value.replace('\\,',',') for value in re.split(r'(?<!\\),',encoded)]
        self.assertEqual(decoded[:3],['-B',helper,'attach'])

    def test_termux_launch_failures_and_non_termux_refuse(self):
        server=Mock(); record=Mock()
        with patch('menu_session_host.is_termux', return_value=False), patch('subprocess.run',side_effect=AssertionError):
            with self.assertRaisesRegex(ValueError,'only available'): host.launch_termux(server,record,str(self.home))
        server=sessions.Server('/tool/tmux','/socket',1); record=sessions.Session('$1','n',1,0,False,2)
        for result in (subprocess.CompletedProcess([],1,'','denied'), subprocess.CompletedProcess([],0,'Error: denied','')):
            with patch('menu_session_host.is_termux',return_value=True), patch('menu_session_host.termux_transport',return_value='/am'), \
                    patch.object(sessions.Server,'validate'), patch('subprocess.run',return_value=result):
                with self.assertRaisesRegex(ValueError,'still available'): host.launch_termux(server,record,str(self.home))

    def test_termux_probe_prefers_socket_falls_back_before_launch_and_is_bounded(self):
        good = subprocess.CompletedProcess([],0,'usage: startservice','')
        bad = subprocess.CompletedProcess([],1,'','Could not connect to socket: No such file or directory')
        for first in (good, bad, subprocess.TimeoutExpired(['probe'], 4), OSError('missing')):
            with patch('menu_session_host.is_termux', return_value=True), patch('shutil.which', return_value='/tools/termux-am'), \
                    patch('menu_session_host.legacy_am', return_value='/tools/am'), \
                    patch('subprocess.run', side_effect=[first, good]) as run:
                self.assertEqual(host.termux_transport(), '/tools/termux-am' if first is good else '/tools/am')
            self.assertEqual(run.call_count, 1 if first is good else 2)
            self.assertEqual(run.call_args_list[0].args[0], ['/tools/termux-am','--am-help'])
            if first is not good:
                self.assertEqual(run.call_args.args[0], ['/tools/am','--help'])
            self.assertTrue(all(call.kwargs['timeout']==4 for call in run.call_args_list))
        with patch('menu_session_host.is_termux', return_value=True), patch('shutil.which', return_value='/tools/termux-am'), \
                patch('menu_session_host.legacy_am', return_value=None), patch('subprocess.run', return_value=bad):
            with self.assertRaisesRegex(ValueError, 'termux-am: help probe status 1; Could not connect'):
                host.termux_transport()

    def test_legacy_adapter_only_uses_termux_prefix_not_path_or_system_am(self):
        prefix = self.base / 'com.termux/files/usr'
        adapter = prefix / 'bin/am'; adapter.parent.mkdir(parents=True)
        adapter.write_text('# fixture'); adapter.chmod(0o700)
        with patch.dict(os.environ, PREFIX=str(prefix), TERMUX__PREFIX=''), \
                patch('shutil.which', side_effect=AssertionError('PATH fallback')):
            self.assertEqual(host.legacy_am(), str(adapter))
        for prefix in ('/system', '/system/bin', '', 'relative/files/usr'):
            with patch.dict(os.environ, PREFIX=prefix, TERMUX__PREFIX=''):
                self.assertIsNone(host.legacy_am())

    def test_launch_failure_redacts_payload_and_never_retries(self):
        server=sessions.Server('/tool/tmux',str(self.base / 'private socket'),1)
        record=sessions.Session('$1','n',1,0,False,2)
        def fail(command, **kwargs):
            payload = command[command.index('com.termux.execute.arguments')+1]
            return subprocess.CompletedProcess(command,1,'Intent { dat='+payload+' }',
                'SecurityException: denied\x1b[31m\n'+server.socket+' '+payload)
        for failure in (fail, subprocess.TimeoutExpired(['secret command'],15)):
            with patch('menu_session_host.is_termux',return_value=True), patch.object(sessions.Server,'validate'), \
                    patch('subprocess.run',side_effect=failure) as run, \
                    patch('menu_session_host.termux_transport',side_effect=AssertionError('retried')):
                with self.assertRaises(ValueError) as error:
                    host.launch_termux(server,record,str(self.home),transport='/tools/am')
            self.assertEqual(run.call_count,1)
            message=str(error.exception)
            self.assertIn('Termux am launch',message); self.assertIn('still available',message)
            self.assertNotIn('secret command',message); self.assertNotIn(str(self.base),message)
            self.assertNotIn('eyJ',message); self.assertNotIn('\x1b',message)
            self.assertLess(len(message),700)

    def test_failed_transport_probe_does_not_create_inactive_project_session(self):
        project=projects.Project(self.home,'home'); row=projects.Row('project','home',project)
        calls=[]
        def picker(rows, **kwargs):
            calls.append(kwargs['frame'].copy())
            if len(calls)==1:
                kwargs['frame']['query']='home'
                raise SelectionEvent('termux',index=0,query='home')
            raise SelectionEnded(130)
        with patch.object(sessions.Server,'discover',return_value=None), patch('menu_projects.discover',return_value=(project,)), \
                patch('menu_session_ui.pick',side_effect=picker), patch('menu_session_host.is_termux',return_value=True), \
                patch('menu_session_host.termux_transport',side_effect=ValueError('adapter unavailable')), \
                patch('menu_sessions.show_message') as message, patch('menu_sessions.create_session') as create:
            with self.assertRaises(SelectionEnded): sessions.browse(query='home')
        create.assert_not_called(); message.assert_called_once(); self.assertEqual(calls[-1]['query'],'home')

    def test_failed_launch_keeps_created_session_and_search(self):
        project=projects.Project(self.home,'home'); record=sessions.Session('$8','new-home',1,0,False,12)
        inactive=projects.Row('project','home',project)
        active=replace(inactive,sessions=(record,)); server=Mock(socket=str(self.home/'missing-socket'))
        def picker(rows, **kwargs):
            if rows==(inactive,):
                kwargs['frame']['query']='home'
                raise SelectionEvent('termux',index=0,query='home')
            self.assertEqual(rows,(active,)); self.assertEqual(kwargs['frame']['query'],'home')
            raise SelectionEnded(130)
        with patch.object(sessions.Server,'discover',return_value=None), patch('menu_projects.discover',return_value=(project,)), \
                patch('menu_projects.inventory',side_effect=[(inactive,),(active,)]), patch('menu_session_ui.pick',side_effect=picker), \
                patch('menu_session_host.is_termux',return_value=True), patch('menu_session_host.termux_transport',return_value='/tools/am'), \
                patch('menu_session_host.prompt',return_value='new-home'), patch('menu_session_host.launch_termux',side_effect=ValueError('denied')) as launch, \
                patch('menu_sessions.create_session',return_value=(server,record)) as create, \
                patch('menu_sessions.delete_session',side_effect=AssertionError('removed created session')), patch('menu_sessions.show_message'):
            with self.assertRaises(SelectionEnded): sessions.browse(query='home')
        create.assert_called_once(); launch.assert_called_once_with(server,record,str(self.home),transport='/tools/am')

    def test_invalid_names_and_unique_suggestions(self):
        for name in ('',' ','.','a:b','a\n','a\0','x\x1b'):
            with self.assertRaises(ValueError): sessions.valid_name(name)
        record=sessions.Session('$1','café',1,0,False,2)
        self.assertEqual(sessions.suggested_name('/café',(record,)),'café-2')
        self.assertEqual(sessions.valid_name('-日本語 $(literal);'),'-日本語 $(literal);')

    def test_cancel_delete_and_action_menu_are_explicit(self):
        record=sessions.Session('$1','target',3,2,False,2)
        with patch('menu_sessions.choose',return_value=sessions.Entry('cancel','Cancel')) as choose:
            self.assertFalse(sessions.confirm_delete(record,None))
        menu=choose.call_args.args[0]
        self.assertEqual(menu.entries[0].id,'cancel')
        self.assertIn('2 attached',menu.entries[1].description)
        for termux in (False,True):
            with patch('menu_sessions.choose',return_value=None) as choose:
                sessions.action_menu(projects.Row('$1','target',sessions=(record,)),None,termux)
            self.assertEqual('termux' in [e.id for e in choose.call_args.args[0].entries],termux)


class NativeProjects(NativeMenuFixture):
    def setUp(self):
        super().setUp()
        self.control('set-option','-g','default-command', 'exec bash --noprofile --norc')
        self.project=self.home/'repos'/'-café #{literal};'
        self.project.mkdir(parents=True)
        subprocess.run(['git', 'init', '-q', str(self.project)], env=self.env, check=True)

    def context(self):
        return TmuxContext.capture(client=self.first[2],cwd=str(self.home))

    def test_marked_termux_sessions_remain_generic_and_every_session_appears_once(self):
        server=sessions.Server.discover(); project=projects.Project(self.project,self.project.name)
        for name in ('termux-default','renamed-default','termux-unmarked'):
            server,record=sessions.create_session(server,name,str(self.project),project,self.context())
            if name!='termux-unmarked':
                self.control('set-option','-t',record.id,'@dots-termux-default','1')
        inactive=projects.Project(self.home/'inactive','inactive')
        items=server.sessions(); rows=projects.inventory(server,items,(project,inactive))
        self.assertEqual([s.name for s in rows[0].sessions],['termux-unmarked'])
        self.assertEqual(rows[1].project,inactive)
        self.assertEqual({r.label for r in rows[2:]},{'fixture','termux-default','renamed-default'})
        seen=[s.id for r in rows for s in r.sessions]
        self.assertEqual(len(seen),len(set(seen))); self.assertEqual(set(seen),{s.id for s in items})

    def test_create_rename_association_and_literal_directory(self):
        server=sessions.Server.discover(); project=projects.Project(self.project, self.project.name)
        server, record=sessions.create_session(server,'-café $(touch sentinel);',str(self.project),project,self.context())
        self.assertEqual(server.read('display-message','-p','-t',record.id,'#{pane_current_path}').strip(),str(self.project))
        sessions.rename_session(server,record,'renamed;',self.context())
        self.assertEqual(projects.associate(server,record,(project,)),project)
        self.assertEqual(server.read('display-message','-p','-t',record.id,'#{session_name}').strip(),'renamed;')
        with self.assertRaises(ValueError): sessions.rename_session(server,record,'fixture',self.context())
        self.assertEqual(self.control('list-clients','-F','#{session_id}').splitlines(),['$0','$0'])
        self.assertFalse((self.project/'sentinel').exists())

    def test_delete_other_current_and_stale_sessions(self):
        server=sessions.Server.discover(); context=self.context()
        server,target=sessions.create_session(server,'other',str(self.home),context=context)
        sessions.delete_session(server,target,context)
        with self.assertRaises(ValueError): sessions.delete_session(server,target,context)
        self.assertEqual(self.control('list-clients','-F','#{session_id}').splitlines(),['$0','$0'])
        current=server.sessions()[0]
        server,other=sessions.create_session(server,'survivor',str(self.home),context=context)
        sessions.delete_session(server,current,context)
        self.assertEqual([s.name for s in server.sessions()],['survivor'])

    def picker(self,query=''):
        return self.worker("import os,sys; from menu_sessions import main; sys.exit(main(['--browse','--query',os.environ['QUERY'],'--client',os.environ['CLIENT']]))", QUERY=query)

    def test_help_roundtrip_zero_matches_enter_ignored_and_ctrl_c(self):
        for query in ('fixture','no-matching-session'):
            p=self.picker(query); self.receive(self.first[1],b'Alt-H:')
            time.sleep(.15); os.write(self.first[1],b'\x1bh')
            self.receive(self.first[1],'dots·tmux·keys'.encode())
            os.write(self.first[1],b'\r'); time.sleep(.15); self.assertIsNone(p.poll())
            os.write(self.first[1],b'\x1b'); seen=self.receive(self.first[1],'dots·tmux·sessions:'.encode())
            self.assertIn(query.encode(),seen+self.drain(self.first[1]))
            time.sleep(.15); os.write(self.first[1],b'\x1bh')
            self.receive(self.first[1],'dots·tmux·keys'.encode()); os.write(self.first[1],b'\x03')
            out,err=p.communicate(timeout=15); self.assertEqual(p.returncode,130,err)
            self.assertNotIn('dots·tmux·keys'.encode(),self.drain(self.second[1]))

    def test_help_preserves_pending_project_rename_and_focused_session(self):
        server=sessions.Server.discover(); project=projects.Project(self.project,self.project.name)
        for name in ('first','second'):
            server,record=sessions.create_session(server,name,str(self.project),project,self.context())
        p=self.picker('café'); self.receive(self.first[1],b'Alt-H:')
        time.sleep(.15); os.write(self.first[1],b'\x1br')
        self.receive(self.first[1],'dots·tmux·sessions·'.encode())
        os.write(self.first[1],b'second'); time.sleep(.15); os.write(self.first[1],b'\x1bh')
        self.receive(self.first[1],b'rename')
        os.write(self.first[1],b'\x1bh'); self.receive(self.first[1],'dots·tmux·sessions·'.encode())
        time.sleep(.15); os.write(self.first[1],b'\r'); self.receive(self.first[1],b'Name:')
        os.write(self.first[1],b'\x15renamed-second\r'); self.receive(self.first[1],b'Alt-H:')
        os.write(self.first[1],b'\x03'); out,err=p.communicate(timeout=15)
        self.assertEqual(p.returncode,130,err)
        self.assertEqual(server.read('display-message','-p','-t',record.id,'#{session_name}').strip(),'renamed-second')

    def test_actual_preview_height_at_terminal_widths(self):
        code = '''import os,sys
from pathlib import Path
from menu_session_ui import pick
from menu_projects import Project,Row
from menu_sessions import Session
from menu_tmux import TmuxContext
from interaction import RichSelector,SelectionEnded
original=RichSelector.fzf
def measured(self,title,labels,multi,preview,*args,**kwargs):
    command = 'printf "%s %s" "$FZF_PREVIEW_LINES" "$FZF_PREVIEW_COLUMNS" > "$DOTS_TEST_GEOMETRY"; ' + preview[0]
    return original(self,title,labels,multi,(command,preview[1],preview[2]),*args,**kwargs)
RichSelector.fzf=measured
project=Project(Path.home()/'repos/battery','battery')
many=os.environ['MANY']=='1'
names=['dots-22129-208387696','dots-23650-210903334'] + ['session-%02d'%i for i in range(2,10)]
items=tuple(Session('$'+str(i),name,1,0,False,12) for i,name in enumerate(names)) if many else (Session('$99','battery',1,0,False,12),)
row=Row('project','battery',project,items)
try:
    pick((row,),context=TmuxContext.capture(client=os.environ['CLIENT'],cwd=str(Path.home())))
except SelectionEnded as error:
    sys.exit(error.status)
'''
        for width,many in ((40,False),(80,False),(120,False),(53,True),(40,True),(80,True),(120,True)):
            self.fcntl.ioctl(self.first[1],self.termios.TIOCSWINSZ,self.struct.pack('HHHH',30,width,0,0))
            for _ in range(30):
                if self.context().verify()==(width,30): break
                time.sleep(.05)
            path=self.base/('geometry-'+str(width)+'-'+str(many))
            p=self.worker(code,DOTS_TEST_GEOMETRY=str(path),MANY=str(int(many)),DOTS_ICONS='always',DOTS_COLOR='always')
            seen=self.receive(self.first[1],b'Project:')
            height,columns=map(int,path.read_text().split())
            self.assertEqual(height,6 if many else 3)
            self.assertEqual(columns,width-10)
            if many:
                if b'dots-23650-210903334' not in seen:
                    seen+=self.receive(self.first[1],b'dots-23650-210903334')
                # Inspect actual tmux cursor placement, not only preview text:
                # wrapping used to place these names two screen rows apart.
                positioned=re.split(rb'\x1b\[(\d+);(\d+)H',seen)
                rows=[]
                for name in (b'dots-22129-208387696',b'dots-23650-210903334'):
                    positions=[int(positioned[i]) for i in range(1,len(positioned),3) if name in positioned[i+2]]
                    self.assertTrue(positions,repr(seen))
                    rows.append(positions[-1])
                self.assertEqual(rows[1],rows[0]+1)
                os.write(self.first[1],b'\x1bj'*30)
                self.receive(self.first[1],b'12/12')
            os.write(self.first[1],b'\x03'); out,err=p.communicate(timeout=15)
            self.assertEqual(p.returncode,130,err)

    def test_alt_rename_then_cancel_delete_refreshes_and_restores_search(self):
        server=sessions.Server.discover(); server,target=sessions.create_session(server,'target',str(self.home),context=self.context())
        p=self.picker('target'); self.receive(self.first[1],b'Alt-H:')
        time.sleep(.2); os.write(self.first[1],b'\x1br')
        self.receive(self.first[1],b'Name:')
        os.write(self.first[1],b'\x15renamed\r')
        self.receive(self.first[1],b'Alt-H:')
        # Query "target" now has no match. Escape remains an event, not an action.
        os.write(self.first[1],b'\x15renamed'); time.sleep(.2); os.write(self.first[1],b'\x1bd')
        self.receive(self.first[1],b'Keep this session'); os.write(self.first[1],b'\r')
        self.receive(self.first[1],b'Alt-H:'); os.write(self.first[1],b'\x1b')
        out,err=p.communicate(timeout=15); self.assertEqual(p.returncode,130,err)
        self.assertEqual(server.read('display-message','-p','-t',target.id,'#{session_name}').strip(),'renamed')
        self.assertFalse(list(self.base.glob('dots-menu-*')))

    def test_inactive_project_enter_creates_and_switches_only_invoker(self):
        p=self.picker('café'); self.receive(self.first[1],b'no session')
        time.sleep(.2); os.write(self.first[1],b'\r')
        out,err=p.communicate(timeout=15); self.assertEqual(p.returncode,0,err)
        server=sessions.Server.discover(); target=next(s for s in server.sessions() if s.id != '$0')
        self.assertTrue(target.name.startswith(self.project.name + '-'), target.name)
        clients=dict(row.split('\t') for row in self.control('list-clients','-F','#{client_name}\t#{session_id}').splitlines())
        self.assertEqual(clients[self.first[2]],target.id); self.assertEqual(clients[self.second[2]],'$0')
        self.assertEqual(projects.associate(server,target,projects.discover()).root,self.project)

    def test_multiple_sessions_project_submenu_then_switch(self):
        server=sessions.Server.discover(); project=projects.Project(self.project,self.project.name)
        for name in ('first','second'):
            server,target=sessions.create_session(server,name,str(self.project),project,self.context())
        p=self.picker('café'); self.receive(self.first[1],b'2 sessions')
        time.sleep(.2); os.write(self.first[1],b'\r'); self.receive(self.first[1],'dots·tmux·sessions·'.encode())
        os.write(self.first[1],b'second'); time.sleep(.2); os.write(self.first[1],b'\r')
        out,err=p.communicate(timeout=15); self.assertEqual(p.returncode,0,err)
        self.assertEqual(self.control('display-message','-p','-c',self.first[2],'#{session_name}').strip(),'second')

    def test_empty_search_alt_new_creates_from_invoking_directory(self):
        p=self.picker('does-not-match-anything'); self.receive(self.first[1],b'Alt-H:')
        time.sleep(.2); os.write(self.first[1],b'\x1bn')
        out,err=p.communicate(timeout=15); self.assertEqual(p.returncode,0,err)
        server=sessions.Server.discover(); record=next(s for s in server.sessions() if s.id!='$0')
        self.assertRegex(record.name, r'^termux-[0-9a-f]{12}$')
        self.assertEqual(server.read('display-message','-p','-t',record.id,'#{session_path}').strip(),str(self.home))

    def test_delete_other_refreshes_and_current_last_closes_browser(self):
        server=sessions.Server.discover(); server,target=sessions.create_session(server,'target',str(self.home),context=self.context())
        p=self.picker('target'); self.receive(self.first[1],b'Alt-H:')
        time.sleep(.2); os.write(self.first[1],b'\x1bd'); self.receive(self.first[1],b'Keep this session')
        os.write(self.first[1],b'delete'); time.sleep(.2); os.write(self.first[1],b'\r')
        self.receive(self.first[1],b'Alt-H:')
        self.assertNotIn(target.id,[s.id for s in server.sessions()])
        os.write(self.first[1],b'\x03'); out,err=p.communicate(timeout=15)
        self.assertEqual(p.returncode,130,err)
        p=self.picker('fixture'); self.receive(self.first[1],b'Alt-H:')
        time.sleep(.2); os.write(self.first[1],b'\x1bd'); self.receive(self.first[1],b'Keep this session')
        os.write(self.first[1],b'delete'); time.sleep(.2); os.write(self.first[1],b'\r')
        out,err=p.communicate(timeout=15); self.assertEqual(p.returncode,0,err)
        self.assertIsNone(sessions.Server.discover())

    def test_popup_widths_and_termux_controls(self):
        for width in (40,80,120):
            self.fcntl.ioctl(self.first[1],self.termios.TIOCSWINSZ,self.struct.pack('HHHH',30,width,0,0))
            for _ in range(30):
                if self.context().verify()==(width,30): break
                time.sleep(.05)
            p=self.picker(); seen=self.receive(self.first[1],b'Alt-H:')
            self.assertNotIn(b'Alt-H:',self.drain(self.second[1]))
            os.write(self.first[1],b'\x03'); out,err=p.communicate(timeout=15)
            self.assertEqual(p.returncode,130,err)


if __name__=='__main__':
    unittest.main()

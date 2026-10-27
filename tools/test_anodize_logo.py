#!/usr/bin/env python3
"""Engine-free logo policy, PTY and static-help checks in disposable roots."""
import base64
import errno
import fcntl
import io
import json
import os
from pathlib import Path
import pty
import re
import select
import shutil
import struct
import subprocess
import sys
import termios
import tempfile
import unittest
from unittest import mock

import test_bash_dots as fixture

sys.path.insert(0, str(fixture.REPO / 'lib/dots/anodize'))
from cli import Presentation
import logo
from text_gradient import gradient

SGR = re.compile(r'\x1b\[[0-9;:]*m')


def colored_cells(lines):
    """Decode generated SGR only, retaining cell coordinates for color assertions."""
    result = {}
    for y, line in enumerate(lines):
        x, code = 0, ''
        for token in re.findall(r'\x1b\[[0-9;:]*m|[^\x1b]', line):
            if token.startswith('\x1b['):
                if token.startswith('\x1b[38;2;'): code = token
                elif token in ('\x1b[0m', '\x1b[39m'): code = ''
            else:
                if token not in (' ', '\u2800'): result[x, y] = code
                x += 1
    return result


class Stream(io.StringIO):
    def __init__(self, terminal=True):
        super().__init__()
        self.terminal = terminal

    def isatty(self):
        return self.terminal


class LogoPolicy(unittest.TestCase):
    def setUp(self):
        # Unit policy checks must never inspect the developer's active theme.
        published = mock.patch.object(logo, 'published_colors', return_value={})
        self.published = published.start()
        self.addCleanup(published.stop)

    def draw(self, full=True, terminal=True, **env):
        stream = Stream(terminal)
        with mock.patch.dict(os.environ, {'TERM':'xterm-256color', 'COLUMNS':'80', 'LINES':'24', **env}, clear=True):
            logo.render(Presentation(stream), full)
        return stream.getvalue()

    def test_exact_defaults_ignore_pipes_capability_and_short_height(self):
        self.assertEqual(list(logo.BASE_LOGO), (logo.ASSETS/'logo.txt').read_text().splitlines())
        self.assertEqual((logo.ASSETS/'horizontal.txt').read_text().splitlines(), [
            '⠀⠀⠀⠀⠀⠀⠀⣰⡄⠀⠀⠀⠀⠀⠀',
            '⠀⠀⠀⠀⠀⢀⣼⣿⣿⣄⠀⠀⠀⠀⠀',
            '⠀⠀⠀⠀⠠⢾⡿⠃⠘⣿⣆⠀⠀⠀⠀⠀⣠⠟⢧⡀⠀⡟⢦⣸⠀⣾⠉⠉⡇⢸⡏⠉⣧⠀⡇⠈⣩⠝⠃⢸⡯⠭',
            '⠀⠀⠀⣰⣷⣦⣤⣀⠀⠘⣿⣦⠀⠀⠀⠀⠁⠀⠈⠁⠀⠁⠀⠉⠀⠈⠉⠉⠁⠈⠉⠉⠁⠀⠁⠈⠉⠉⠁⠈⠉⠉',
            '⠀⠀⣴⣿⡟⠙⠻⢿⣿⣶⣾⣿⣧⡀⠀',
            '⢀⣾⣿⠏⠀⠀⠀⠀⠀⠉⠛⠿⣿⣷⡀',
        ])
        with mock.patch.object(logo.subprocess, 'run', side_effect=AssertionError('unexpected renderer')):
            for width, rows in [(1,1),(8,3),(20,9),(40,24),(53,6),(80,24),(120,30)]:
                for terminal in (True, False):
                    for settings in ({}, {'DOTS_ICONS':'never'}, {'TERM':'dumb'}, {'NO_COLOR':'1'}):
                        for full in (True,False):
                            with self.subTest(width=width,rows=rows,terminal=terminal,settings=settings,full=full):
                                expected = 'horizontal.txt' if full and width >= 43 else 'logo.txt'
                                out=self.draw(full=full,terminal=terminal,COLUMNS=str(width),LINES=str(rows),DOTS_COLOR='never',**settings)
                                self.assertEqual(out,(logo.ASSETS/expected).read_text())

    def test_diagonal_gradient_endpoints_rounding_and_degenerate_regions(self):
        colors = dict(hint='#102030', info='#e01080', accent='#90a0b0')
        art = ['@@@', '@@@', '@@@']
        out = gradient(art, colors)
        cells = colored_cells(out)
        self.assertEqual(cells[0, 2], '\x1b[38;2;16;32;48m')
        self.assertEqual(cells[2, 0], '\x1b[38;2;144;160;176m')
        self.assertEqual(cells[1, 1], '\x1b[38;2;224;16;128m')
        self.assertEqual(cells[0, 1], '\x1b[38;2;120;24;88m')
        self.assertEqual(cells[2, 1], '\x1b[38;2;184;88;152m')
        self.assertEqual(cells[0, 0], cells[2, 2])
        self.assertEqual([SGR.sub('', row) for row in out], art)
        self.assertTrue(all(row.endswith('\x1b[39m') for row in out))
        for art in (['@ @'], ['@', '@'], ['@'], ['⠀ '], []):
            out = gradient(art, dict(hint='#123456', info='#123456', accent='#123456'))
            self.assertEqual([SGR.sub('', row) for row in out], art)
            self.assertEqual(set(colored_cells(out).values()), {'\x1b[38;2;18;52;86m'} if '@' in ''.join(art) else set())
        cells = colored_cells(gradient(['@@@@@'], dict(hint='#000000', info='#010305', accent='#02060a')))
        self.assertEqual(cells[1, 0], '\x1b[38;2;1;2;3m')
        self.assertEqual(cells[3, 0], '\x1b[38;2;2;5;8m')
        cells = colored_cells(gradient(['@@@'], dict(hint='#102030', info='#e01080', accent='#102030')))
        self.assertEqual(cells[0, 0], cells[2, 0])
        self.assertNotEqual(cells[0, 0], cells[1, 0])
        for colors in ({}, None, {'hint':'#abcdef','info':'\x1b[31m','accent':'#abcdef'}):
            self.assertEqual(gradient(['@@'], colors), ['@@'])
        for role in ('hint', 'info', 'accent'):
            for value in (None, '#bad', '\x1b[31m'):
                colors = dict(hint='#102030', info='#e01080', accent='#90a0b0')
                colors[role] = value
                self.assertEqual(gradient(['@@'], colors), ['@@'])

    def test_component_regions_and_preview_palette_background_restoration(self):
        sys.path.insert(0, str(fixture.REPO/'lib/dots/themes'))
        from presentation import render_preview
        colors = dict(hint='#102030', info='#e01080', accent='#90a0b0', foreground='#dddddd', background='#101010')
        self.published.side_effect = AssertionError('preview read active palette')
        with mock.patch.dict(os.environ,dict(DOTS_COLOR='always',FZF_PREVIEW_COLUMNS='80'),clear=True):
            for layout in ('base', 'horizontal', 'stacked', 'icon'):
                art = logo.text_lines(layout, 79, 16)
                self.assertEqual(len(art.regions), 2 if layout in ('horizontal', 'stacked') else 0)
                painted = gradient(art, colors, regions=art.regions)
                cells = colored_cells(painted)
                if layout == 'horizontal':
                    self.assertEqual({point: code for point, code in cells.items() if point[0] < 16},
                                     colored_cells(gradient(logo.BASE_LOGO, colors)))
                regions = art.regions or ((0, 0, 80, len(art)),)
                for left, top, right, bottom in regions:
                    codes = [value for (x, y), value in cells.items() if left <= x < right and top <= y < bottom]
                    self.assertIn('\x1b[38;2;16;32;48m', codes)
                    self.assertIn('\x1b[38;2;144;160;176m', codes)
                with mock.patch('sys.stdout', new_callable=io.StringIO) as output:
                    render_preview('fixture', colors, logo=art)
                rows = output.getvalue().splitlines()[:len(art)]
                for raw, row in zip(art, rows):
                    self.assertTrue(row.startswith('\x1b[48;2;16;16;16m'))
                    self.assertEqual(SGR.sub('', row).strip(' '), raw.strip(' '))
                    self.assertTrue(row.endswith('\x1b[0m'))
                    self.assertNotIn('\x1b[0m', row[:-4])
                    if any(c not in (' ', '\u2800') for c in raw):
                        self.assertTrue(row[:-4].rstrip(' ').endswith('\x1b[38;2;221;221;221m'))
            # Read-only CLI results use their own colors, too.
            from cli import present
            with mock.patch('sys.stdout', new_callable=io.StringIO) as output:
                present(dict(id='fixture', colors=colors))
            self.assertIn('\x1b[38;2;16;32;48m', output.getvalue())
            self.assertIn('\x1b[38;2;144;160;176m', output.getvalue())

    def test_supplied_assets_and_actual_dimensions(self):
        for layout, width, rows, name in [
            ('auto', 80, 24, 'horizontal.txt'), ('auto', 43, 12, 'horizontal.txt'),
            ('auto', 40, 24, 'logo.txt'), ('auto', 25, 24, 'logo.txt'),
            ('icon', 80, 32, 'logo-40.txt'), ('icon', 40, 28, 'logo-35.txt'),
            ('icon', 40, 24, 'logo-35.txt'), ('icon', 40, 20, 'logo-35.txt'),
            ('stacked', 40, 16, 'stacked.txt'), ('icon', 20, 24, 'logo.txt'),
        ]:
            with self.subTest(layout=layout,width=width,rows=rows):
                self.assertEqual(self.draw(COLUMNS=str(width),LINES=str(rows),ANODIZE_LOGO_LAYOUT=layout,DOTS_COLOR='never'), (logo.ASSETS/name).read_text())
        self.assertEqual(self.draw(full=False,DOTS_COLOR='never'), (logo.ASSETS/'logo.txt').read_text())
        self.assertEqual(self.draw(full=False,LINES='12',DOTS_COLOR='never'), (logo.ASSETS/'logo.txt').read_text())

    def test_complete_result_panel_uses_addressed_colors_from_first_row(self):
        from cli import present
        colors = dict(hint='#102030', info='#e01080', accent='#90a0b0', foreground='#dddddd',
                      background='#101010', warning='#fedcba', green='#abcdef')
        self.published.side_effect = AssertionError('palette result read active theme')
        result = dict(id='fixture ü', colors=colors, contrast=11.26, status='preview',
                      target='/fixture/-long path ü/' + 'x'*100, transaction='fixture',
                      notes=['Keep \x1b[31mthis inert'])
        for columns in (40, 80, 120):
            for mode in ('always', 'never'):
                with self.subTest(columns=columns, mode=mode), mock.patch.dict(os.environ,
                        dict(DOTS_COLOR=mode, DOTS_ICONS='never', FZF_PREVIEW_COLUMNS=str(columns),
                             FZF_PREVIEW_LINES='100', TERM='xterm-256color'), clear=True), \
                        mock.patch('sys.stdout', new_callable=io.StringIO) as output:
                    present(result)
                rows = output.getvalue().splitlines()
                self.assertEqual(len(rows), 100)
                if mode == 'always':
                    for row in rows:
                        self.assertTrue(row.startswith('\x1b[48;2;16;16;16m'), repr(row))
                        self.assertTrue(row.endswith('\x1b[0m'))
                        self.assertNotIn('\x1b[0m', row[:-4])
                    title = next(row for row in rows if 'Anodize' in row)
                    self.assertIn('\x1b[38;2;144;160;176m', title)
                    for label in ('Theme', 'Contrast', 'Note', 'Target', 'Transaction', 'Undo'):
                        row = next(row for row in rows if label in row)
                        self.assertTrue(row.startswith('\x1b[48;2;16;16;16m\x1b[38;2;221;221;221m'))
                    status = next(row for row in rows if 'preview' in row)
                    self.assertIn('\x1b[38;2;254;220;186m', status)
                    self.assertNotIn('\x1b[31m', output.getvalue())
                else:
                    self.assertNotIn('\x1b', output.getvalue())
                self.assertEqual([SGR.sub('', row).strip(' ') for row in rows[:6]],
                                 [row.strip(' ') for row in logo.BASE_LOGO])
                text = SGR.sub('', output.getvalue())
                self.assertLess(text.index('Note'), text.index('Preview only'))

    def test_draft_review_uses_candidate_logo_and_background(self):
        import interactive
        colors = dict(hint='#102030', info='#e01080', accent='#90a0b0',
                      background='#101010', foreground='#dddddd')
        author = mock.Mock()
        author.render.return_value = dict(colors=colors)
        doc = dict(id='draft', options=dict(light=False))
        self.published.side_effect = AssertionError('draft read active theme')
        with mock.patch.dict(os.environ, dict(DOTS_COLOR='always', TERM='xterm-256color'), clear=True), \
                mock.patch.object(interactive, 'choice', return_value='Review save'), \
                mock.patch('sys.stdout', new_callable=io.StringIO) as output:
            self.assertIs(interactive.edit_draft(author, mock.Mock(mode='normal'), doc), doc)
        author.render.assert_called_once_with(doc)
        rows = output.getvalue().splitlines()
        for row in rows:
            self.assertTrue(row.startswith('\x1b[48;2;16;16;16m'))
        cells = colored_cells(rows[:6])
        self.assertIn('\x1b[38;2;16;32;48m', cells.values())
        self.assertIn('\x1b[38;2;144;160;176m', cells.values())

    def test_usage_and_routine_text_match_for_all_layouts(self):
        for columns, rows in [(1,1), (20,9), (40,24), (80,24), (120,32)]:
            for layout in ('base','horizontal','stacked','icon'):
                for terminal in (True, False):
                    settings = dict(COLUMNS=str(columns), LINES=str(rows),
                                    ANODIZE_LOGO_LAYOUT=layout, DOTS_COLOR='never')
                    self.assertEqual(self.draw(full=False,terminal=terminal,**settings),
                                     self.draw(full=True,terminal=terminal,**settings))

    def test_preview_pipe_uses_usage_art_and_pane_dimensions(self):
        import interactive
        for columns, rows, asset in [(columns, rows, asset)
                for columns, asset in [(40,'logo.txt'), (80,'logo.txt'), (120,'logo.txt'), (25,'logo.txt')]
                for rows in (1,6,8,10,11,12,24)]:
            with self.subTest(columns=columns,rows=rows), mock.patch.dict(os.environ,
                    dict(TERM='xterm-256color', DOTS_COLOR='never',
                         FZF_PREVIEW_COLUMNS=str(columns), FZF_PREVIEW_LINES=str(rows)),clear=True):
                self.assertEqual(interactive.preview_logo(), (logo.ASSETS/asset).read_text().splitlines())
                self.assertLessEqual(max(map(len,interactive.preview_logo())), columns-4)
                self.assertLessEqual(len(interactive.preview_logo()), 16)
                for key,value in [('DOTS_ICONS','never'), ('TERM','dumb')]:
                    with mock.patch.dict(os.environ,{key:value}):
                        self.assertEqual(interactive.preview_logo(), (logo.ASSETS/asset).read_text().splitlines())
        with mock.patch.dict(os.environ,dict(TERM='xterm-256color', FZF_PREVIEW_COLUMNS='8',
                                            FZF_PREVIEW_LINES='bad'),clear=True):
            self.assertEqual(interactive.preview_logo(), list(logo.BASE_LOGO))

    def test_preview_worker_preserves_art_and_options_without_graphics(self):
        import interactive
        import completion_preview
        with tempfile.TemporaryDirectory() as tmp:
            snapshot=Path(tmp)/'preview.json'
            snapshot.write_text(json.dumps(dict(color=False,rows=[dict(id='fixture',mode='dark',
                colors={'background':'#101010','foreground':'#dddddd'})])))
            before=snapshot.read_bytes()
            env=dict(TERM='xterm-256color', FZF_PREVIEW_COLUMNS='80',FZF_PREVIEW_LINES='6',
                     ANODIZE_LOGO='chafa',DOTS_ICONS='auto')
            with mock.patch.dict(os.environ,env,clear=True), mock.patch.object(logo.subprocess,'run',side_effect=AssertionError('graphics in preview')):
                with mock.patch('sys.stdout',new_callable=io.StringIO) as output:
                    interactive.preview(str(snapshot),'0')
                expected=''.join('  '+line+'\n' for line in (logo.ASSETS/'logo.txt').read_text().splitlines())
                self.assertTrue(output.getvalue().startswith(expected))
                self.assertIn('Syntax preview',output.getvalue())
                with mock.patch.dict(os.environ,FZF_PREVIEW_COLUMNS='8'), mock.patch('sys.stdout',new_callable=io.StringIO) as tiny:
                    interactive.preview(str(snapshot),'0')
                self.assertTrue(tiny.getvalue().startswith(expected))
                completion_preview.preview_options(['anodize','--logo-layout=horizontal','show','--logo-layout','stacked','fixture'])
                self.assertEqual(interactive.preview_logo(),(logo.ASSETS/'stacked.txt').read_text().splitlines())
                completion_preview.preview_options(['dots','--icons=never','anodize','show','fixture'])
                self.assertEqual(interactive.preview_logo(),(logo.ASSETS/'stacked.txt').read_text().splitlines())
                completion_preview.preview_options(['anodize','--logo-layout','unfinished','--','--logo-layout=icon'])
                self.assertEqual(os.environ['ANODIZE_LOGO_LAYOUT'],'stacked')
            self.assertEqual(snapshot.read_bytes(),before)

    def test_future_variants_invalid_files_and_missing_base(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(logo,'ASSETS',Path(tmp)):
            root=Path(tmp)
            (root/'logo-45.txt').write_text('⣿'*45+'\n')
            (root/'logo-999.txt').write_text('⣿'*10+'\n')  # Filename is not measured width.
            (root/'logo-wide.txt').write_text('⣿'*60+'\n')
            (root/'logo-90.txt').write_text('\x1b[31mcontrol\n')
            (root/'logo-0.txt').write_text('⣿'*61+'\n')
            (root/'logo-50.txt').write_bytes(b'\xff\xfe')
            self.assertEqual(logo.text_lines('icon',70,16),['⣿'*45])
            self.assertEqual(logo.text_lines('icon',44,16),['⣿'*10])
            self.assertEqual(logo.text_lines('icon',8,3),list(logo.BASE_LOGO))
            (root/'logo.txt').write_text('⠀⣿⠀\n')
            self.assertEqual(logo.text_lines('base',8,6),list(logo.BASE_LOGO))

    def test_unicode_and_color_are_independent(self):
        for color in ({'NO_COLOR':'1'},{'DOTS_COLOR':'never'}):
            self.assertEqual(self.draw(**color),(logo.ASSETS/'horizontal.txt').read_text())
        with mock.patch.object(logo.subprocess,'run',side_effect=AssertionError('unexpected renderer')):
            for settings in ({'DOTS_ICONS':'never'},{'TERM':'dumb'}):
                self.assertEqual(self.draw(ANODIZE_LOGO='chafa',DOTS_COLOR='never',**settings),(logo.ASSETS/'horizontal.txt').read_text())
                self.assertIn('\u2800',self.draw(ANODIZE_LOGO='chafa',DOTS_COLOR='always',**settings))
            class ASCIIStream(Stream):
                @property
                def encoding(self):
                    return 'ascii'
            stream=ASCIIStream()
            with mock.patch.dict(os.environ,{'TERM':'xterm-kitty','ANODIZE_LOGO':'chafa'},clear=True):
                logo.render(Presentation(stream),full=True)
            self.assertIn(logo.BASE_LOGO[0],stream.getvalue())

    def test_destination_dimensions_and_bad_environment(self):
        stream = Stream()
        with mock.patch.object(stream, 'fileno', return_value=7), mock.patch.object(logo.os, 'get_terminal_size', return_value=os.terminal_size((40, 12))) as size:
            self.assertEqual(logo.dimensions(stream), (40, 12))
            size.assert_called_once_with(7)
        with mock.patch.dict(os.environ, {'COLUMNS':'bad','LINES':'-1'}, clear=True):
            self.assertEqual(logo.dimensions(stream), (80,24))
        self.assertEqual(self.draw(ANODIZE_LOGO='bad', ANODIZE_LOGO_LAYOUT='bad'), self.draw())

    def test_plain_redirected_and_missing_assets(self):
        with mock.patch.object(logo.subprocess, 'run', side_effect=AssertionError('unexpected renderer')):
            for mode in logo.MODES:
                self.assertNotIn('\x1b', self.draw(ANODIZE_LOGO=mode, NO_COLOR='1'))
                self.assertNotIn('\x1b', self.draw(ANODIZE_LOGO=mode, DOTS_COLOR='never'))
                self.assertNotIn('\x1b_G', self.draw(terminal=False, ANODIZE_LOGO=mode, DOTS_COLOR='always'))
            with mock.patch.object(logo, 'ASSETS', Path('/nonexistent-test-owned-assets')):
                self.assertEqual(self.draw(DOTS_COLOR='never'), '\n'.join(logo.BASE_LOGO)+'\n')

    def test_kitty_chunks_fit_and_decode_to_original(self):
        out = self.draw(ANODIZE_LOGO='kitty', TERM='xterm-kitty')
        chunks = re.findall(r'\x1b_G([^;]+);([^\x1b]+)\x1b\\', out)
        self.assertTrue(chunks)
        self.assertIn('q=2,C=1', chunks[0][0])
        self.assertTrue(chunks[-1][0].endswith('m=0'))
        self.assertTrue(all(len(data) <= 4096 for _, data in chunks))
        self.assertEqual(base64.b64decode(''.join(data for _, data in chunks)), (logo.ASSETS/'horizontal-color-white.png').read_bytes())
        for env in ({'TMUX':'fixture'}, {'STY':'fixture'}, {'ZELLIJ':'fixture'}):
            self.assertNotIn('\x1b_G', self.draw(ANODIZE_LOGO='kitty', TERM='xterm-kitty', **env))
        self.assertNotIn('\x1b_G', self.draw(ANODIZE_LOGO='kitty'))
        self.assertNotIn('\x1b_G', self.draw(ANODIZE_LOGO='kitty', TERM='xterm-kitty', DOTS_ICONS='never'))
        self.assertNotIn('\x1b_G', self.draw(ANODIZE_LOGO='kitty', TERM='xterm-kitty', COLUMNS='8', LINES='3'))

    def test_chafa_bounded_failure_and_text_policy(self):
        with mock.patch.object(logo.shutil, 'which', return_value='/fixture/chafa'), mock.patch.object(logo.subprocess, 'run') as run:
            run.return_value = subprocess.CompletedProcess([], 0, b'RENDERED\n')
            self.assertIn('RENDERED', self.draw(ANODIZE_LOGO='chafa'))
            args, kwargs = run.call_args
            self.assertIn('--symbols=braille', args[0])
            self.assertIn('--fg-only', args[0])
            self.assertIn('--probe=off', args[0])
            self.assertIn('--polite=on', args[0])
            self.assertIn('--animate=off', args[0])
            self.assertEqual(kwargs['stdin'], subprocess.DEVNULL)
            self.assertEqual(kwargs['timeout'], 1.0)
            for outcome in (subprocess.CompletedProcess([], 1, b'partial'), subprocess.CompletedProcess([], 0, b'')):
                run.return_value = outcome
                self.assertIn((logo.ASSETS/'horizontal.txt').read_text().splitlines()[0], self.draw(ANODIZE_LOGO='chafa'))
            run.side_effect = subprocess.TimeoutExpired('chafa', 1)
            self.assertIn((logo.ASSETS/'horizontal.txt').read_text().splitlines()[0], self.draw(ANODIZE_LOGO='auto'))


class LogoCLI(unittest.TestCase):
    run_dots = fixture.DotsFixture.run_dots

    def publish_colors(self, colors):
        root = Path(self.env['XDG_STATE_HOME'])/'dots/current/theme'
        root.mkdir(parents=True, exist_ok=True)
        (root/'palette.json').write_text(json.dumps(dict(colors=colors)))
        (root/'shell.tsv').write_text(''.join(f'{name}\thex\t{value}\n' for name,value in colors.items()))
        return root

    def test_gradient_bash_python_native_parity_and_no_python_help(self):
        colors = dict(hint='#c1a32f', info='#e01080', accent='#6139e7')
        self.publish_colors(colors)
        env = dict(self.env, DOTS_COLOR='always', DOTS_ICONS='never', TERM='dumb',
                   LC_ALL='C', PYTHONIOENCODING='ascii')
        for layout, width in (('base',40),('horizontal',40),('horizontal',53),('horizontal',80),('horizontal',120),('stacked',40),('icon',80)):
            art = logo.text_lines(layout, width-1, 16)
            expected = gradient(art, colors, regions=art.regions, restore='\x1b[0m')
            for argv in ([str(self.repo/'bin/anodize')], [str(self.repo/'bin/dots'),'anodize'],
                         [sys.executable,'-B',str(self.repo/'lib/dots/cli.py'),'anodize']):
                result = subprocess.run([*argv,'--logo-layout='+layout,'--help'],
                    env=dict(env,COLUMNS=str(width),LINES='3'),cwd=self.home,capture_output=True,timeout=15)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(result.stdout.decode().splitlines()[:len(art)], expected)
        expected = gradient(logo.BASE_LOGO, colors, restore='\x1b[0m')
        for argv in ([str(self.repo/'bin/anodize')], [str(self.repo/'bin/dots'),'anodize'],
                     [sys.executable,'-B',str(self.repo/'lib/dots/cli.py'),'anodize']):
            result = subprocess.run([*argv,'--logo=bad','--help'],env=env,cwd=self.home,capture_output=True,timeout=15)
            self.assertEqual(result.returncode,2,result.stderr)
            self.assertEqual(result.stdout,b'')
            self.assertEqual(result.stderr.decode().splitlines()[:6], expected)
        # Default text help can read its palette and interpolate using builtins alone.
        env.update(PATH=str(self.repo/'bin'),COLUMNS='80')
        result = subprocess.run([fixture.BASH,str(self.repo/'bin/dots'),'anodize','--help'],
            env=env,cwd=self.home,capture_output=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        art = logo.text_lines('horizontal',79,16)
        self.assertEqual(result.stdout.decode().splitlines()[:6], gradient(art, colors, regions=art.regions,restore='\x1b[0m'))

    def test_gradient_missing_invalid_state_and_color_controls(self):
        for colors in ({}, {'accent':'#aabbcc'}, {'hint':'#aabbcc','info':'#nope','accent':'#aabbcc'}):
            root = self.publish_colors(colors)
            for command in ('anodize','dots'):
                argv = [str(self.repo/'bin'/command), *(['anodize'] if command=='dots' else []), '--help']
                result = subprocess.run(argv,env=dict(self.env,DOTS_COLOR='always'),capture_output=True,text=True,timeout=15)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertIn('\x1b[95m', result.stdout)
                self.assertNotIn('\x1b[38;2;', result.stdout)
        for path in root.iterdir(): path.write_text('malformed\n')
        with mock.patch.dict(os.environ,self.env,clear=True):
            self.assertEqual(logo.published_colors(root), {})
        colors = dict(hint='#102030', info='#e01080', accent='#90a0b0')
        self.publish_colors(colors)
        for mode in ({'DOTS_COLOR':'never'}, {'DOTS_COLOR':'auto','NO_COLOR':'1'}, {'DOTS_COLOR':'auto','TERM':'dumb'}):
            result = subprocess.run([str(self.repo/'bin/dots'),'anodize','--help'],
                env=dict(self.env,**mode),capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertNotIn('\x1b',result.stdout)
            self.assertTrue(result.stdout.startswith((logo.ASSETS/'horizontal.txt').read_text()))

    def setUp(self):
        fixture.DotsFixture.setUp(self)
        for source in [fixture.REPO/'bin/anodize', *fixture.REPO.glob('bin/dots-anodize*')]:
            shutil.copy2(source, self.repo/'bin'/source.name)
        self.env.update(ANODIZE_ENGINE=str(self.root/'missing'), DOTS_COLOR='never')

    def cli(self, *args, code=0):
        result = subprocess.run([str(self.repo/'bin/anodize'), *args], env=self.env, cwd=self.home,
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, code, result.stderr)
        return result

    def terminal(self, argv, width=80, height=24, env=None, code=0):
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', height, width, 0, 0))
        output = bytearray()
        proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=slave, stderr=slave,
                                cwd=self.home, env=env or self.env)
        os.close(slave)
        try:
            while select.select([master], [], [], 15)[0]:
                try:
                    chunk = os.read(master, 65536)
                except OSError as exc:
                    if exc.errno == errno.EIO:
                        break
                    raise
                if not chunk:
                    break
                output.extend(chunk)
            self.assertEqual(proc.wait(timeout=3), code, output)
        finally:
            if proc.poll() is None:
                proc.kill(); proc.wait()
            os.close(master)
        return output.decode().replace('\r\n', '\n')

    def test_help_static_no_extension_execution_and_size_parity(self):
        command = self.repo/'bin/dots-anodize'
        command.write_text(command.read_text().replace('exec python3', 'touch "$HOME/extension-ran"\nexec python3'))
        for layout in logo.LAYOUTS:
            for width, height in [(40,24),(80,32),(120,30),(21,16),(43,12),(10,3)]:
                args=['--logo-layout='+layout,'--help']
                standalone = self.terminal([str(self.repo/'bin/anodize'), *args], width,height)
                dots = self.terminal([str(self.repo/'bin/dots'), 'anodize', *args], width,height)
                self.assertEqual(standalone.split('Anodize\n')[0], dots.split('dots anodize\n')[0])
        self.assertFalse((self.home/'extension-ran').exists())
        self.assertIn('⣰⡄', self.run_dots('help','anodize').stdout)
        prefixed = self.run_dots('anodize','--logo','text','--logo-layout=icon','preview','--help').stdout
        self.assertIn('dots anodize preview',prefixed)
        self.assertIn('--app',prefixed)
        # Static help still works when Python is unavailable.
        self.env['PATH'] = str(self.repo/'bin')
        result = subprocess.run([fixture.BASH, str(self.repo/'bin/dots'), 'anodize','--help'], env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('⣰⡄',result.stdout)

    def test_native_static_help_options_and_exact_fallback(self):
        for width, asset in ((40,'logo.txt'),(53,'horizontal.txt'),(80,'horizontal.txt'),(120,'horizontal.txt')):
            expected=(logo.ASSETS/asset).read_text()
            for words in (['help','anodize'],['anodize','--logo=text','--help'],
                          ['anodize','preview','--logo-layout','horizontal','--help']):
                result=subprocess.run([sys.executable,'-B',str(self.repo/'lib/dots/cli.py'),*words],
                    env=dict(self.env,COLUMNS=str(width),LINES='3',DOTS_ICONS='never',TERM='dumb',PYTHONIOENCODING='ascii'),
                    cwd=self.home,capture_output=True,timeout=15)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertTrue(result.stdout.startswith(expected.encode()),result.stdout)
        for words in (['anodize','--logo=bad','--help'],
                      ['help','anodize','--logo-layout=bad'],
                      ['anodize','--logo-layout']):
            result=subprocess.run([sys.executable,'-B',str(self.repo/'lib/dots/cli.py'),*words],
                env=self.env,cwd=self.home,capture_output=True,timeout=15)
            self.assertEqual(result.returncode,2,result.stderr)
            self.assertEqual(result.stdout,b'')
            self.assertTrue(result.stderr.startswith(('\n'.join(logo.BASE_LOGO)+'\n').encode()))
        assets=self.repo/'lib/dots/anodize/assets'
        for path in assets.glob('*.txt'): path.write_bytes(b'\xff')
        for argv in ([str(self.repo/'bin/dots'),'help','anodize'],
                     [sys.executable,'-B',str(self.repo/'lib/dots/cli.py'),'help','anodize']):
            result=subprocess.run(argv,env=self.env,cwd=self.home,capture_output=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue(result.stdout.startswith(('\n'.join(logo.BASE_LOGO)+'\n').encode()))

    def test_results_and_errors_match_usage_in_native_terminal(self):
        for width in (40,80,120):
            command=str(self.repo/'bin/anodize')
            banner=(logo.ASSETS/'logo.txt').read_text()
            self.assertTrue(self.terminal([command,'list'],width).startswith(banner))
            self.assertTrue(self.terminal([command,'invalid'],width,code=2).startswith(banner))
            self.assertTrue(self.terminal([command,'modes'],width,code=1).startswith(banner))
            self.assertTrue(self.terminal([str(self.repo/'bin/dots'),'anodize','--logo=bad','--help'],width,code=2).startswith(banner))
        banner=self.terminal([command,'--logo-layout=icon','--help']).split('Anodize\n')[0]
        self.assertTrue(self.terminal([str(self.repo/'bin/dots'),'anodize','--logo-layout=icon','--logo=bad','--help'],code=2).startswith(banner))

    def test_option_positions_errors_and_data(self):
        for mode in logo.MODES:
            self.assertIn('Usage',self.cli('--logo='+mode).stdout)
            self.assertIn('⣰⡄',self.cli('--logo',mode,'--help').stdout)
            self.assertIn('⣰⡄',self.cli('list','--logo='+mode,'--help').stdout)
            result=self.cli('list','--logo='+mode,'--json')
            self.assertEqual(json.loads(result.stdout), {'items':[], 'schema':1})
            self.assertEqual(result.stderr,'')
            self.assertEqual(self.cli('completion','bash','--logo='+mode).stdout, (self.repo/'lib/dots/anodize/completion/bash').read_text())
        self.assertIn('⣰⡄', self.cli('list').stdout)
        self.assertIn('⣰⡄', self.cli('invalid',code=2).stderr)
        self.assertIn('⣰⡄', self.cli('modes',code=1).stderr)
        self.cli('--logo=bad','--help',code=2)
        self.assertIn('⣰⡄',self.run_dots('anodize','--logo=bad','--help',code=2).stderr)
        self.assertFalse((self.home/'state').exists())

    def test_new_variants_and_plain_policy_match_static_help(self):
        assets=self.repo/'lib/dots/anodize/assets'
        future='⠀'+'⣿'*43+'⠀\n'
        (assets/'logo-45.txt').write_text(future)
        (assets/'logo-999.txt').write_text('⣿'*10+'\n')
        (assets/'logo-60.txt').write_text('\x1b[31munsafe\n')
        (assets/'logo-wide.txt').write_text('⣿'*60+'\n')
        args=['--logo-layout=icon','--help']
        for command, title in [(['anodize'],'Anodize\n'),(['dots','anodize'],'dots anodize\n')]:
            argv=[str(self.repo/'bin'/command[0]),*command[1:],*args]
            self.assertEqual(self.terminal(argv,80,32).split(title)[0],future)
            for settings in ({'DOTS_ICONS':'never'},{'TERM':'dumb'},
                             {'PYTHONIOENCODING':'ascii'},{'PYTHONIOENCODING':'latin-1'}, {'LC_ALL':'C'}):
                out=self.terminal(argv,80,32,dict(self.env,**settings)).split(title)[0]
                self.assertEqual(out,future,settings)


if __name__ == '__main__':
    unittest.main()

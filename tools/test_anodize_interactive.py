#!/usr/bin/env python3
"""Owned-root acceptance for Anodize storage, promotion and transient previews."""
from contextlib import redirect_stdout
import copy
import io
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import sys
import tempfile
import time
import unittest
from unittest import mock

import test_anodize as old
from transactions import Store, digest
from authoring import new_document
sys.path.insert(0, str(old.REPO / 'lib/dots/themes'))
import interactive
from presentation import render_preview, SGR, width
from cli import parser, build_document
import completion_preview


class Interactive(unittest.TestCase):
    setUpFixture = old.Anodize.setUpFixture
    setUp = old.Anodize.setUp
    cli = old.Anodize.cli
    create = old.Anodize.create
    recipe = old.Anodize.recipe
    author = old.Anodize.author
    terminal = old.Anodize.terminal
    run_command = old.Anodize.run_command
    dots = old.Anodize.dots

    def test_default_roots_discovery_and_builtin(self):
        result = self.create()
        user = self.home / 'config/dots/themes/example'
        self.assertEqual(result['target'], str(user))
        self.assertFalse((self.repo / 'themes/example').exists())
        self.create('bundled-authored', '--builtin')
        self.assertTrue((self.repo / 'themes/bundled-authored/anodize.json').is_file())
        rows = json.loads(self.cli('list', '--json').stdout)['items']
        self.assertEqual({r['storage'] for r in rows}, {'user', 'builtin'})
        self.cli('edit', 'bundled-authored', '--set', 'accent=#aabbcc', '--yes')
        self.assertIn('example', self.cli('__complete', 'bash', '2', '--', 'anodize', 'edit', '').stdout)
        self.cli('create', 'catppuccin-mocha', '--color', '#aabbcc', '--yes', code=1)
        self.cli('create', 'example', '--color', '#aabbcc', '--builtin', '--yes', code=1)
        self.cli('show', 'example', '--json')
        self.assertFalse(self.active.exists())

    def test_promote_move_copy_and_undo(self):
        self.cli('create', 'picture', '--image', self.image, '--yes')
        source = self.home / 'config/dots/themes/picture'
        (source / 'notes.txt').write_text('keep me')
        before = digest(source)
        self.cli('promote', 'picture', '--copy', '--yes', code=2)
        self.cli('promote', 'picture', '--copy', '--name', 'picture', '--yes', code=1)
        self.cli('promote', 'picture', '--copy', '--name', 'copy-picture', '--yes')
        copied = self.repo / 'themes/copy-picture'
        self.assertEqual(json.loads((copied / 'anodize.json').read_text())['id'], 'copy-picture')
        self.assertEqual((copied / 'backgrounds/wallpaper.png').read_bytes(), old.PNG)
        self.assertEqual(digest(source), before)
        self.cli('edit', 'copy-picture', '--yes')  # Fresh generated receipts.
        self.cli('promote', 'picture', '--dry-run', '--yes')
        self.assertEqual(digest(source), before)
        result = json.loads(self.cli('promote', 'picture', '--yes', '--json').stdout)
        target = self.repo / 'themes/picture'
        self.assertFalse(source.exists())
        self.assertEqual(digest(target), before)
        self.assertEqual((target / 'notes.txt').read_text(), 'keep me')
        self.assertEqual(self.image.read_bytes(), old.PNG)
        with self.author() as author:
            store = author.store()
            ops, guards, catalogs = store.inverse(result['transaction'])
            store.apply('undo', ops, guards, retain=True, catalogs=catalogs)
        self.assertFalse(target.exists())
        self.assertEqual(digest(source), before)

    def test_promotion_failure_drift_and_recovery(self):
        self.create()
        with self.author() as author:
            source = author.target('example')
            before = digest(source)
            plan = author.promote('example')
            original = Store.save
            def fail(store, record):
                original(store, record)
                if record['status'] == 'applying' and record['operations'][0]['phase'] == 'done':
                    raise OSError('injected move failure')
            with mock.patch.object(Store, 'save', fail):
                with self.assertRaises(OSError): author.save(plan)
            self.assertEqual(digest(source), before)
            self.assertFalse(Path(plan['target']).exists())
            (source / 'notes.txt').write_text('new work')
            with self.assertRaisesRegex(ValueError, 'changed after preview'): author.save(plan)
        script = '''import os,sys
sys.path[:0]=sys.argv[1:3]
from authoring import Author
from transactions import Store
original=Store.save
def crash(self, record):
 original(self,record)
 if record['status']=='applying' and record['operations'][0]['phase']=='done': os._exit(77)
a=Author();p=a.promote('example');Store.save=crash;a.save(p)
'''
        self.run_command([sys.executable, '-B', '-c', script, str(old.REPO/'lib/dots/anodize'), str(old.REPO/'lib/dots/files')], code=77)
        with self.author() as author:
            store = author.store()
            record = next(r for r in store.records() if r['status'] == 'applying')
            store.recover(record['id'])
            self.assertEqual((author.target('example') / 'notes.txt').read_text(), 'new work')
            self.assertFalse((author.themes / 'example').exists())

    def test_all_mode_candidates_and_completion_cache(self):
        self.assertEqual(completion_preview.request(['anodize', 'create', 'new', '--from=ex'], '--from=example'),
                         ('theme', ('example', True)))
        self.assertEqual(completion_preview.request(['dots', 'theme', 'colors', '--theme=ex'], '--theme=example'),
                         ('theme', ('example', False)))
        with self.author() as author:
            for light in (False, True):
                options = dict(mode='normal', light=light)
                doc = new_document('preview', author.generate(self.image, options=options), **options)
                doc['adjustments']['gamma'] = 1.1
                doc['overrides']['accent'] = '#123456'
                start = time.monotonic()
                rows = interactive.candidates(author, doc, str(self.image))
                self.assertEqual(len(rows), 23)
                for row in rows:
                    direct = copy.deepcopy(doc)
                    direct['options']['mode'] = row['id']
                    direct['baseline'] = author.generate(self.image, options=direct['options'])
                    self.assertEqual(row['colors'], author.render(direct)['colors'])
                print(f'23 image modes ({"light" if light else "dark"}): {time.monotonic()-start:.3f}s including direct comparisons')
            with tempfile.TemporaryDirectory(dir=self.root) as cache:
                words = ('anodize', 'create', 'new', '--image', str(self.image), '--mode', '')
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(completion_preview.main(cache, 'ocean', *words), 0)
                    with mock.patch.object(type(author), 'call', side_effect=AssertionError('cached hover ran engine')):
                        self.assertEqual(completion_preview.main(cache, 'forest', *words), 0)
                self.assertEqual(len(list(Path(cache).glob('*.json'))), 1)
        self.assertFalse((self.home / 'config/dots/themes').exists())
        self.assertFalse(self.state.exists())

    def test_existing_palette_completion_matches_commands(self):
        self.create('source', '--mode', 'ocean')
        with self.author() as author:
            blueprint = self.root / 'source.json'
            blueprint.write_text(json.dumps(author.load('source')))
            commands = [
                ['create', 'derived', '--from', 'source'],
                ['edit', 'source'],
                ['import', str(blueprint), '--name', 'imported', '--format', 'anodize'],
            ]
            for command in commands:
                with tempfile.TemporaryDirectory(dir=self.root) as cache, redirect_stdout(io.StringIO()):
                    self.assertEqual(completion_preview.main(cache, 'ocean', 'anodize', *command, '--mode', ''), 0)
                    rows = json.loads(next(Path(cache).glob('*.json')).read_text())
                    for row in rows:
                        args = parser().parse_args([*command, '--mode', row['id']])
                        doc, _, _ = build_document(author, args)
                        self.assertEqual(row['colors'], author.render(doc)['colors'], (command, row['id']))

    def test_picker_cleanup_and_preview_tokens(self):
        row = dict(id='literal $(touch nope)', colors=dict(background='#101010', foreground='#111111'))
        snapshots = []
        def cancel(selector, title, labels, **kwargs):
            snapshot = Path(kwargs['preview'][2]['DOTS_ANODIZE_SNAPSHOT'])
            snapshots.append(snapshot)
            self.assertTrue(snapshot.exists())
            with self.assertRaises(ValueError): interactive.preview(snapshot, '0;touch nope')
            raise interactive.SelectionEnded(130)
        with mock.patch.dict(os.environ, self.env, clear=True), mock.patch.object(interactive.RichSelector, 'pick', cancel):
            with self.assertRaises(interactive.SelectionEnded): interactive.choose('Theme', [row['id']], [row])
        self.assertFalse(snapshots[0].parent.exists())
        self.assertFalse((self.home / 'nope').exists())
        self.assertFalse(self.state.exists())

    def test_guided_draft_and_noninteractive_contract(self):
        self.cli('create', code=2)
        self.cli('show', '--json', code=2)
        self.cli('create', 'missing', '--yes', code=2)
        self.cli('--interactive', 'show', '--json', code=2)
        with self.author() as author:
            args = parser().parse_args(['create', 'draft', '--color', '#725ac1', '--mode', 'normal', '--interactive'])
            doc, _, wallpaper = build_document(author, args)
            decisions = iter(['Adjustment', 'gamma', 'Color override', 'accent', 'Review save'])
            with mock.patch.object(interactive, 'choice', side_effect=lambda *a: next(decisions)), mock.patch.object(interactive, 'entry', side_effect=['1.2', '#112233']), redirect_stdout(io.StringIO()):
                draft = interactive.edit_draft(author, args, doc, wallpaper)
            rendered = author.render(draft)
            plan = author.prepare(draft)
            author.save(plan)
            self.assertEqual(author.render(author.load('draft'))['colors'], rendered['colors'])
            self.assertEqual(rendered['colors']['accent'], '#112233')

    def test_guided_cli_review_and_approval(self):
        gum = old.test_confirmations.install_gum(self.root, self.env)
        fzf = gum.with_name('fzf')
        fzf.write_text('#!' + sys.executable + '''
import sys
rows = sys.stdin.buffer.read().split(b'\\0')
sys.stdout.buffer.write(rows[0] + b'\\0')
''')
        fzf.chmod(0o700)
        command = [old.BASH, str(self.repo / 'bin/anodize'), 'create', 'guided',
                   '--color', '#725ac1', '--mode', 'normal', '--interactive']
        self.script = shlex.join(command)
        self.env['GUM_CHOICE'] = 'Cancel'
        output = self.terminal()
        self.assertIn(b'Syntax preview', output)
        self.assertFalse((self.home / 'config/dots/themes/guided').exists())
        self.env['GUM_CHOICE'] = 'Apply'
        self.terminal()
        self.assertTrue((self.home / 'config/dots/themes/guided/anodize.json').is_file())
        self.assertFalse(self.active.exists())

    def test_exact_preview_geometry_plain_and_resets(self):
        for columns in (40, 80, 120):
            for background, foreground in (('#101010', '#111111'), ('#eeeeee', '#dddddd')):
                colors = dict(background=background, foreground=foreground, muted='#888888')
                with mock.patch.dict(os.environ, dict(DOTS_COLOR='always', FZF_PREVIEW_COLUMNS=str(columns), FZF_PREVIEW_LINES='30'), clear=False), redirect_stdout(io.StringIO()) as output:
                    render_preview('preview', colors, palette=False)
                text = output.getvalue()
                self.assertIn('Syntax preview', text)
                from presentation import escape
                self.assertIn(escape(foreground), text)
                self.assertIn(escape(background, True), text)
                self.assertEqual(len(text.splitlines()), 30)
                self.assertTrue(all(width(line) == columns for line in text.splitlines()))
                self.assertTrue(all(line.endswith('\x1b[0m') for line in text.splitlines()))
        with mock.patch.dict(os.environ, dict(DOTS_COLOR='never'), clear=False), redirect_stdout(io.StringIO()) as output:
            render_preview('plain', colors)
        self.assertNotIn('\x1b', output.getvalue())
        self.assertIn('#dddddd', output.getvalue())

    def test_native_fzf_preview_cancel(self):
        if not shutil.which('fzf'): self.skipTest('native FZF unavailable')
        self.env['DOTS_COLOR'] = 'always'
        self.env['DOTS_ICONS'] = 'always'
        self.create()
        self.create('second')
        for columns in (40, 80, 120):
            before = digest(self.home / 'config/dots/themes')
            self.script = shlex.join([old.BASH, str(self.repo / 'bin/anodize'), 'edit'])
            output = self.terminal(width=columns, code=130, steps=((b'Syntax preview', b'\x1b'),), timeout=45)
            self.assertIn(b'Syntax preview', output)
            self.assertTrue(any('\u2800' <= c <= '\u28ff' for c in output.decode(errors='replace')), 'preview omitted supplied braille artwork')
            self.assertEqual(digest(self.home / 'config/dots/themes'), before)
        self.assertFalse(self.active.exists())

    def test_native_zsh_fzf_tab_mode_preview(self):
        from bash_dots_pty import Terminal
        import fcntl
        import struct
        import termios
        plugin = Path(os.environ.get('DOTS_TEST_FZF_TAB') or Path.home() / '.local/share/zinit/plugins/Aloxaf---fzf-tab')
        if not shutil.which('zsh') or not shutil.which('fzf') or not (plugin / 'fzf-tab.plugin.zsh').is_file():
            if os.environ.get('DOTS_TEST_FZF_TAB'):
                self.fail('requested native Zsh/FZF-tab source or executable unavailable')
            self.skipTest('native Zsh/FZF-tab source unavailable')
        copied = self.root / 'fzf-tab'
        shutil.copytree(plugin, copied, ignore=shutil.ignore_patterns('.git'))
        integration = self.root / 'completion-preview.zsh'
        shutil.copy2(old.REPO / 'shells/zsh/completions.zsh', integration)
        self.env['DOTS_COLOR'] = 'always'
        cases = [(width, "anodize create draft --color '#725ac1' --mode ") for width in (40, 80, 120)]
        cases += [(80, "dots anodize create draft --color '#725ac1' --mode "),
                  (80, 'anodize show catppuccin-'), (80, 'dots anodize show catppuccin-'),
                  (80, 'dots theme show catppuccin-')]
        for columns, command in cases:
            env = dict(self.env)
            if command.startswith('dots theme '): env['ANODIZE_ENGINE'] = str(self.root / 'engine-must-not-run')
            terminal = Terminal(shutil.which('zsh'), env, self.home)
            try:
                # FZF-tab caps its menu at 2/3 of the terminal height. This
                # produces a preview shorter than 12 rows, the old failure case.
                fcntl.ioctl(terminal.master, termios.TIOCSWINSZ, struct.pack('HHHH', 24, columns, 0, 0))
                terminal.send('autoload -Uz compinit; compinit -D; source "$DOTS/lib/dots/completion/zsh"; source "$DOTS/lib/dots/anodize/completion/zsh"; has() { command -v "$1" >/dev/null; }; source ' + shlex.quote(str(old.REPO / 'shells/shared/fzf.sh')) + '; source ' + shlex.quote(str(copied / 'fzf-tab.plugin.zsh')) + '; source ' + shlex.quote(str(integration)) + '; PROMPT="READY> "; print INITIALIZED\r')
                terminal.wait(b'INITIALIZED\r\n')
                terminal.send(command + '\t')
                # The configured defaults start previews hidden; use the real
                # Ctrl-X binding to reveal the pane before checking its logo.
                terminal.wait(b'\x1b[?1000h')
                terminal.send('\x18')
                if not command.startswith('dots theme '):
                    asset = 'stacked.txt' if columns == 40 else 'horizontal.txt'
                    lines = (old.REPO / 'lib/dots/anodize/assets' / asset).read_text().splitlines()
                    # The top six artwork rows fit; the rest remains scrollable.
                    terminal.wait(lines[5].strip(' \u2800').encode(), timeout=40)
                    output = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', terminal.output.decode(errors='replace'))
                    for line in lines[:6]:
                        self.assertIn(line.strip(' \u2800'), output)
                    # Shift-Down scrolls the preview without changing selection.
                    terminal.send('\x1b[1;2B' * 8)
                terminal.wait(b'Syntax preview', timeout=40)
                terminal.send('\x1b')
                terminal.wait(b'READY>')
                terminal.send('\x03')
                terminal.wait(b'READY>')
                terminal.send('print CANCELLED\r')
                terminal.wait(b'CANCELLED\r\n')
                self.assertFalse(list(self.root.glob('dots-completion.*')))
            finally:
                terminal.close()
        self.assertFalse((self.home / 'config/dots/themes').exists())
        self.assertFalse(self.active.exists())


if __name__ == '__main__': unittest.main()

#!/usr/bin/env python3
"""Isolated picker selection, preview boundaries and native FZF acceptance."""
import argparse
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_file_operations as fixtures
import test_files_browser as browser_tests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib/dots/files'))
import picker
import manage
import mappings
from catalog import Presentation
from interaction import RichSelector, SelectionEnded
from transactions import digest


class Pickers(unittest.TestCase):
    setUp = fixtures.Operations.setUp
    write = fixtures.Operations.write
    run_cli = fixtures.Operations.run_cli
    records = fixtures.Operations.records

    def configure(self):
        self.addCleanup(patch.stopall)
        self.env.update(XDG_CACHE_HOME=str(self.home / 'cache'), XDG_DATA_HOME=str(self.home / 'data'),
                        TMPDIR=str(self.base), TERM='xterm-256color', DOTS_PROGRESS='never')
        patch.dict(os.environ, self.env, clear=True).start()

    def catalog(self):
        source = self.repo / 'config/one'
        source.write_text('safe source\n')
        self.write('.dots/files.json', dict(schema=1, repository='dots', resources=[
            dict(id='one', source='config/one', target='${CONFIG}/one', strategy='link',
                 app='example', category='config', platforms=['termux', 'linux', 'wsl']),
            dict(id='two', source='config/one', target='${CONFIG}/two', strategy='link',
                 app='example', category='config', platforms=['termux', 'linux', 'wsl'], enabled=False)]))
        return source

    def test_activation_and_conflicts(self):
        parser = argparse.ArgumentParser()
        def args(**values):
            return argparse.Namespace(**dict(dict(action='link', pick=False, yes=False, json=False,
                                             dry_run=False, directory_link=False), **values))
        with patch('interaction.terminal', return_value=True):
            self.assertTrue(picker.requested(parser, args(), []))
            self.assertFalse(picker.requested(parser, args(), ['dots:one']))
            self.assertFalse(picker.requested(parser, args(dry_run=True), []))
            self.assertTrue(picker.requested(parser, args(pick=True, dry_run=True), []))
            for kw, operands in [({'pick': True, 'yes': True}, []),
                                 ({'pick': True, 'json': True}, []),
                                 ({'pick': True}, ['dots:one']),
                                 ({'pick': True, 'new': True}, []),
                                 ({'directory_link': True, 'action': 'add'}, [])]:
                with self.subTest(kw=kw), self.assertRaises(SystemExit):
                    picker.requested(parser, args(**kw), operands)
        with patch('interaction.terminal', return_value=False):
            self.assertFalse(picker.requested(parser, args(), []))
            with self.assertRaises(SystemExit):
                picker.requested(parser, args(pick=True), [])

    def test_candidate_filters_and_literal_paths(self):
        self.configure()
        self.catalog()
        weird = self.path.parent / '-x ü\t\n$(touch nope)'
        weird.write_text('safe')
        (self.path.parent / 'secret-token').write_text('never select')
        manager = manage.Manager()
        self.assertEqual([r['id'] for r in picker.candidates(manager, 'link')], ['dots:one'])
        self.assertEqual([r['id'] for r in picker.candidates(manager, 'stash')], ['dots:one'])
        self.assertEqual([r['id'] for r in picker.candidates(manager, 'stash', restore=True)], ['dots:two'])
        rows = picker.candidates(manager, 'add', [str(weird)])
        self.assertEqual([r['candidate'] for r in rows], [str(weird)])
        self.assertNotIn('secret-token', str(picker.candidates(manager, 'add')))
        self.assertFalse((self.home / '.state').exists())

    def test_token_protocol_and_no_option_inheritance(self):
        self.configure()
        labels = ['duplicate', 'duplicate']
        selector = RichSelector()
        selector.backend = 'fzf'
        result = subprocess.CompletedProcess([], 0, b'1\tduplicate\0')
        with patch('interaction.terminal', return_value=True), patch('interaction.subprocess.run', return_value=result) as run:
            self.assertEqual(selector.pick('Files', labels), [1])
            call = run.call_args
            self.assertEqual(call.kwargs['input'], b'0\tduplicate\0' + b'1\tduplicate\0')
            self.assertEqual(call.kwargs['env']['FZF_DEFAULT_OPTS'], '')
            self.assertEqual(call.kwargs['env']['FZF_DEFAULT_OPTS_FILE'], '')
            self.assertEqual(call.kwargs['env']['BASH_ENV'], '')
        for output in (b'99\0', b'-1\0', b'$(touch x)\0', b'01\0', b'0\0' + b'1\0'):
            with self.subTest(output=output), patch('interaction.subprocess.run', return_value=subprocess.CompletedProcess([], 0, output)):
                with self.assertRaises(ValueError):
                    selector.fzf('Files', labels, False, None, False, False, '')
        for code in (130, 7):
            with patch('interaction.subprocess.run', return_value=subprocess.CompletedProcess([], code, b'')):
                if code == 130:
                    with self.assertRaises(SelectionEnded) as error:
                        selector.fzf('Files', labels, False, None, False, False, '')
                    self.assertEqual(error.exception.status, 130)
                else:
                    with self.assertRaisesRegex(ValueError, 'selector failed'):
                        selector.fzf('Files', labels, False, None, False, False, '')

    def test_private_snapshot_cleanup_exact_values_and_no_content(self):
        self.configure()
        seen = []
        path = self.path.parent / '- ü\t\n$(echo nope)'
        path.write_text('hidden file content')
        row = dict(id='dots:one', source=str(path), target=str(self.path), status='missing')
        class Fake:
            def pick(inner, title, labels, multi, preview, *rest):
                snapshot = Path(preview[2]['DOTS_PICKER_SNAPSHOT'])
                seen.append(snapshot)
                self.assertNotIn('hidden file content', snapshot.read_text())
                self.assertEqual(snapshot.stat().st_mode & 0o777, 0o600)
                self.assertNotIn(str(path), preview[0])
                self.assertIn('\\t', labels[0])
                self.assertIn('\\n', labels[0])
                return [0]
        chosen = picker.select([row], 'show', selector=Fake())
        self.assertEqual(chosen[0]['source'], str(path))
        self.assertFalse(seen[0].exists())
        self.assertFalse((self.home / '.state').exists())

    def content(self, row, field='source'):
        output = io.StringIO()
        picker.safe_content(Presentation(output), row, field)
        return output.getvalue()

    def test_content_limits_controls_credentials_and_special_files(self):
        self.configure()
        row = dict(source=str(self.path))
        self.path.write_text('visible\x1b[31m\x07\n' + 'line\n' * 250)
        text = self.content(row)
        self.assertNotIn('\x1b', text)
        self.assertIn('\\x1b', text)
        self.assertIn('truncated', text)
        self.assertEqual(text.count('  line\n'), 199)
        self.path.write_text('x' * 70000)
        self.assertIn('truncated', self.content(row))
        for data in (b'password = supersecret', b'BEGIN RSA PRIVATE KEY', b'\0binary'):
            self.path.write_bytes(data)
            text = self.content(row)
            self.assertIn('Content unavailable', text)
            self.assertNotIn(data.decode(), text)
        self.path.unlink()
        os.mkfifo(self.path)
        self.assertIn('Content unavailable', self.content(row))

    def test_managed_link_and_excluded_parent(self):
        self.configure()
        source = self.catalog()
        self.path.unlink()
        self.path.symlink_to(source)
        row = dict(source=str(source), target=str(self.path), _source_root=str(self.repo))
        self.assertIn('safe source', self.content(row, 'target'))
        row['source'] = str(source.parent / 'other')
        self.assertIn('Content unavailable', self.content(row, 'target'))
        row['source'] = str(self.path)
        self.assertIn('Content unavailable', self.content(row))
        secret = self.repo / 'config/.ssh/config/readme'
        secret.parent.mkdir(parents=True)
        secret.write_text('do not expose')
        row.update(source=str(secret))
        self.assertNotIn('do not expose', self.content(row))

    def test_directory_preview_is_bounded(self):
        self.configure()
        directory = self.path.parent
        for i in range(205):
            (directory / f'{i:03d}').write_text('not read')
        output = self.content(dict(source=str(directory)))
        self.assertIn('Directory listing truncated', output)
        self.assertNotIn('not read', output)

    def test_selected_subset_add_and_link_dry_run(self):
        self.configure()
        self.catalog()
        for action in ('add', 'link'):
            before = digest(self.repo), digest(self.home)
            output = io.StringIO()
            with patch('interaction.terminal', return_value=True), patch('picker.select', side_effect=lambda rows, *a, **k: rows[:1]), \
                 patch.object(sys, 'argv', ['manage', action, '--pick', '--dry-run']), redirect_stdout(output):
                manage.main()
            self.assertIn('Preview only', output.getvalue())
            self.assertEqual(before, (digest(self.repo), digest(self.home)))

    def test_stash_restore_edit_selection_dry_run(self):
        self.configure()
        self.catalog()
        for argv, identity in ((['stash'], 'dots:one'), (['stash', '--restore'], 'dots:two'),
                               (['edit', '--target', '${CONFIG}/new'], 'dots:one')):
            observed = []
            def choose(rows, *args, **kw):
                observed.extend(r['id'] for r in rows)
                return rows[:1]
            before = digest(self.repo), digest(self.home)
            with patch('interaction.terminal', return_value=True), patch('picker.select', side_effect=choose), redirect_stdout(io.StringIO()):
                self.assertEqual(mappings.main(argv + ['--pick', '--dry-run']), 0)
            self.assertEqual(observed[0], identity)
            self.assertEqual(before, (digest(self.repo), digest(self.home)))

    def test_data_paths_do_not_select(self):
        self.configure()
        for argv in (('add', '--pick', '--json', '--dry-run'), ('link', '--pick', '--yes'),
                     ('add', '--pick'), ('link', '--dry-run')):
            result = self.run_cli(*argv, ok=False)
            self.assertEqual(result.returncode, 2)
        self.assertFalse((self.home / '.state').exists())

    def test_selected_workflow_uses_existing_transactions(self):
        self.configure()
        other = self.path.parent / 'unselected'
        other.write_text('keep unmanaged')
        with patch('interaction.terminal', return_value=True), patch('mappings.terminal', return_value=True), \
             patch('picker.select', side_effect=lambda rows, *a, **k: rows[:1]), \
             patch.object(sys.stdin, 'isatty', return_value=True), \
             patch('manage.gum_confirm', return_value=True), patch('mappings.gum_confirm', return_value=True), \
             redirect_stdout(io.StringIO()):
            with patch.object(sys, 'argv', ['manage', 'add']):
                manage.main()
            self.assertTrue(self.path.is_symlink())
            self.assertFalse(other.is_symlink())
            source = self.path.resolve()
            mappings.main(['stash'])
            self.assertFalse(self.path.exists())
            self.assertTrue(source.exists())
            mappings.main(['stash', '--restore'])
            self.assertTrue(self.path.is_symlink())
            mappings.main(['edit', '--pick', '--target', '${CONFIG}/moved', '--apply'])
            moved = self.home / '.config/moved'
            self.assertTrue(moved.is_symlink())
            self.assertFalse(self.path.exists())
            with patch.object(sys, 'argv', ['manage', 'remove']):
                manage.main()
            self.assertFalse(moved.is_symlink())
            self.assertEqual(moved.read_text(), 'original\n')
            self.assertTrue(source.exists())
        self.assertEqual(self.records(), [])
        self.assertEqual(len(list((self.home / '.state/dots/files/transactions').glob('*/journal.json'))), 5)

    def test_preview_metadata_does_not_read_content_and_cycle(self):
        self.configure()
        snapshot = self.base / 'preview.json'
        snapshot.write_text(json.dumps(dict(rows=[dict(source=str(self.path), target=str(self.path))],
                                           action='show', color=False, icons=False)))
        out = io.StringIO()
        with patch('picker.safe_content', side_effect=AssertionError('content read')), redirect_stdout(out):
            picker.preview(str(snapshot), '0')
        self.assertIn('Details', out.getvalue())
        for mode in (1, 2, 0):
            result = subprocess.run([sys.executable, '-B', picker.__file__, 'cycle', str(snapshot)],
                                    env=self.env, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(int(snapshot.with_suffix('.mode').read_text()), mode)

    def test_published_colors_are_literal_and_styles_independent(self):
        self.configure()
        theme = self.home / '.state/dots/current/theme'
        theme.mkdir(parents=True)
        color_file = theme / 'fzf.sh'
        color_file.write_text('export _FZF_COLORS_="fg:#123456,bg:#ffffff,hl:bold:#abcdef"\n')
        with patch.dict(os.environ, DOTS_COLOR='always', DOTS_ICONS='never', NO_COLOR='1'):
            self.assertEqual(picker.fzf_colors(Presentation()), 'fg:#123456,bg:#ffffff,hl:bold:#abcdef')
        color_file.write_text('export _FZF_COLORS_="$(touch unsafe)"\n')
        with patch.dict(os.environ, DOTS_COLOR='always'):
            self.assertEqual(picker.fzf_colors(Presentation()), '')
        self.assertFalse(Path('unsafe').exists())

    def test_empty_choices_do_not_launch_tools(self):
        self.configure()
        with patch('picker.RichSelector', side_effect=AssertionError('selector launched')), redirect_stdout(io.StringIO()):
            self.assertEqual(picker.select([], 'link'), [])
            with self.assertRaisesRegex(ValueError, 'No available choices'):
                picker.choice('Owning repository', ['Cancel'])


@unittest.skipUnless(browser_tests.picker.NATIVE_FZF, 'native FZF unavailable')
class Native(browser_tests.Terminal):
    def setUp(self):
        super().setUp()
        (self.fake / 'fzf').symlink_to(browser_tests.picker.NATIVE_FZF)

    def test_widths_content_toggle_and_show(self):
        for width in (40, 80, 120):
            with self.subTest(width=width):
                out = self.terminal('"$DOTS/bin/dots" files show',
                    steps=((b'Details', b'\x1bc'), (b'Source content', b'\x1bc'),
                           (b'Target content', b'\x1bc'), (b'Details', b'\r')), width=width)
                clean = browser_tests.picker.ANSI.sub(b'', out)
                self.assertIn(b'File details', clean)
                self.assertIn(b'do not print file contents', clean)
                self.assertFalse(self.state.exists())

    def test_multiselect_keys_dry_run_and_cancel(self):
        out = self.terminal('"$DOTS/bin/dots" files link --pick --dry-run',
                            steps=((b'Details', b'\x01\x04\t\r'),))
        self.assertIn(b'Preview only', out)
        self.assertFalse(self.state.exists())
        self.terminal('"$DOTS/bin/dots" files link', steps=((b'Details', b'\x1b'),), code=130)
        self.terminal('"$DOTS/bin/dots" files link', steps=((b'Details', b'\x03'),), code=130)
        self.assertFalse(self.state.exists())

    def test_resource_id_search_selects_matching_subset(self):
        catalog = self.repo / '.dots/files.json'
        doc = json.loads(catalog.read_text())
        doc['resources'].append(dict(doc['resources'][0], id='second', target='${CONFIG}/second'))
        catalog.write_text(json.dumps(doc))
        out = self.terminal('"$DOTS/bin/dots" files link --pick --dry-run',
                            steps=((b'Details', b"'dots:app"), (b'1/2', b'\x01\x15\r')))
        clean = browser_tests.picker.ANSI.sub(b'', out).split(b'File operation preview')[-1]
        self.assertIn(b'dots:app', clean)
        self.assertNotIn(b'dots:second', clean)
        self.assertFalse(self.state.exists())

    def test_color_icon_settings_and_snapshot_cleanup(self):
        for color, icons in (('never', 'never'), ('always', 'never'), ('never', 'always')):
            env = dict(self.env, DOTS_COLOR=color, DOTS_ICONS=icons, NO_COLOR='1',
                       TMPDIR=str(self.home), FZF_DEFAULT_OPTS='--bind=start:abort')
            self.terminal('"$DOTS/bin/dots" files show', env=env,
                          steps=((b'Details', b'\x1bp\x1bp\x1bj\x1bk\r'),))
            self.assertFalse(list(self.home.glob('dots-file-picker-*')))

    def test_published_dark_and_light_widgets(self):
        theme = self.state / 'current/theme'
        theme.mkdir(parents=True)
        for foreground, background, expected in (('#abcdef', '#102030', b'171;205;239'),
                                                   ('#123456', '#ffffff', b'18;52;86')):
            (theme / 'fzf.sh').write_text(f'export _FZF_COLORS_="fg:{foreground},bg:{background},fg+:{foreground}"\n')
            before = digest(self.state)
            out = self.terminal('"$DOTS/bin/dots" files show', env=dict(self.env, DOTS_COLOR='always'),
                                steps=((b'Details', b'\r'),))
            self.assertIn(expected, out)
            self.assertEqual(digest(self.state), before)


for name in dir(browser_tests.Terminal):
    if name.startswith('test_') and name not in Native.__dict__:
        setattr(Native, name, None)

if __name__ == '__main__':
    unittest.main()

#!/usr/bin/env python3
"""Focused human file-list rendering at phone and desktop terminal widths."""
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib/dots/files'))
from catalog import Presentation
from list_view import compact_path, render_list
from resources import cells


class ListView(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / 'home'
        env = dict(HOME=str(self.home), USERPROFILE=str(self.home), TERM='xterm',
                   XDG_STATE_HOME=str(self.home / 'state'), XDG_CONFIG_HOME=str(self.home / 'config'),
                   DOTS=str(self.home / 'dots'), DOTS_PROFILE='linux')
        environment = patch.dict(os.environ, env, clear=True)
        environment.start()
        self.addCleanup(environment.stop)
        self.row = dict(id='dots:zshrc', status='linked', strategy='link',
                        source='~/dots/shells/zsh/zshrc', target='~/.zshrc')

    def render(self, rows, width=80, icons=True, color=False, view='short', platform='linux'):
        with patch.dict(os.environ, COLUMNS=str(width), DOTS_ICONS='always' if icons else 'never',
                        DOTS_COLOR='always' if color else 'never'):
            output = io.StringIO()
            ui = Presentation(output, minimum_width=1)
            render_list(ui, rows, view, platform, None)
            return output.getvalue()

    def test_link_stash_and_folder(self):
        rows = [self.row, dict(self.row, status='stashed', id='dots:waybar')]
        for width in (50, 80, 120):
            self.assertEqual(self.render(rows, width),
                             ' 󰈔 ~/dots/shells/zsh/zshrc -> 󰌷 ~/.zshrc\n  dots:waybar\n')
        for width in (40, 49):
            self.assertEqual(self.render(rows, width),
                             '\n 󰈔 ~/dots/shells/zsh/zshrc\n  󱞩 ~/.zshrc\n\n  dots:waybar\n')
            self.assertEqual(self.render(rows, width, icons=False),
                             '\n ~/dots/shells/zsh/zshrc\n  -> ~/.zshrc\n\n [stashed] dots:waybar\n')
        directory = dict(self.row, source='~/dots/main/theme/yazi',
                         target='~/.config/yazi/flavors/dots.yazi', strategy='directory-link')
        self.assertEqual(self.render([directory]), ' 󰉋 ~/dots/main/theme/yazi -> 󰌷 ~/.config/yazi/flavors/dots.yazi\n')
        directory.update(source='~/dots/yazi', target='~/.config/yazi')
        self.assertEqual(self.render([directory], 49), '\n 󰉋 ~/dots/yazi -> ~/.config/yazi\n')
        self.assertEqual(self.render([directory], 50), ' 󰉋 ~/dots/yazi -> 󰌷 ~/.config/yazi\n')
        directory.update(source='~/' + 'x' * 21, target='~/' + 'y' * 17)
        fitting = self.render([directory], 49).splitlines()
        self.assertEqual([cells(line) for line in fitting], [0, 49])
        directory['target'] += 'z'
        self.assertEqual(len(self.render([directory], 49).splitlines()), 3)
        directory.update(source='~/shared/dots/profiles/config/yazi', target='~/.config/yazi')
        self.assertEqual(self.render([directory], 49),
                         '\n 󰉋 ~/shared/dots/profiles/config/yazi\n  󱞩 ~/.config/yazi\n')
        directory.update(source='~/' + 'x' * 27, target='~/' + 'y' * 27)
        self.assertEqual(self.render([directory], 49),
                         '\n 󰉋 ' + directory['source'] + '\n  󱞩 ' + directory['target'] + '\n')
        self.assertEqual(self.render(rows, icons=False),
                         ' ~/dots/shells/zsh/zshrc -> ~/.zshrc\n [stashed] dots:waybar\n')
        native = dict(self.row, source=str(self.home / 'dots/zshrc'), target=str(self.home / '.zshrc'))
        self.assertEqual(self.render([native], icons=False),
                         f' ~{os.sep}dots{os.sep}zshrc -> ~{os.sep}.zshrc\n')

    def test_status_locations_and_empty_list(self):
        for status in ('source-missing', 'source-broken-link', 'theme-unavailable'):
            line = self.render([dict(self.row, status=status)], icons=False)
            self.assertTrue(line.startswith(' [' + status.replace('-', ' ') + '] ~/'))
        for status in ('missing', 'broken-link', 'linked-elsewhere', 'existing-file', 'conflict'):
            line = self.render([dict(self.row, status=status)], icons=False)
            self.assertIn(' -> [' + status.replace('-', ' ') + '] ~/.zshrc', line)
        unmapped = self.render([dict(self.row, target=None, status='unmapped')])
        self.assertEqual(unmapped, ' [unmapped] 󰈔 ~/dots/shells/zsh/zshrc\n')
        self.assertEqual(self.render([]), 'No matching resources.\n')
        self.assertEqual(self.render([], 49), 'No matching resources.\n')

    def test_narrow_exception_runs_spacing_and_stashes(self):
        def item(name, status, strategy='link'):
            return dict(self.row, id='dots:' + name, source='~/dots/' + name, target='~/' + name,
                        status=status, strategy=strategy)

        rows = [item('a', 'missing'), item('b', 'missing', 'directory-link'),
                item('c', 'stashed'), item('d', 'stashed'), item('e', 'replaced'),
                item('f', 'linked'), item('g', 'missing')]
        self.assertEqual(self.render(rows, 49),
                         '\n[missing]\n 󰈔 ~/dots/a\n  󱞩 ~/a\n'
                         '\n 󰉋 ~/dots/b\n  󱞩 ~/b\n'
                         '\n  dots:c\n  dots:d\n'
                         '\n[replaced]\n 󰈔 ~/dots/e\n  󱞩 ~/e\n'
                         '\n[linked]\n 󰈔 ~/dots/f\n  󱞩 ~/f\n'
                         '\n[missing]\n 󰈔 ~/dots/g\n  󱞩 ~/g\n')
        for status in ('conflict', 'source-missing', 'source-broken-link', 'existing-directory'):
            with self.subTest(status=status):
                self.assertEqual(self.render([item('a', status)], 40, icons=False),
                                 '\n[' + status.replace('-', ' ') + ']\n ~/dots/a\n  -> ~/a\n')

    def test_cell_width_and_complete_basenames(self):
        row = dict(self.row, source='~/dots/profiles/linux/common/files/東京/alpha.toml',
                   target='~/.config/app/é space/beta.toml')
        for width in (40, 49, 50, 80, 120):
            line = self.render([row], width)
            self.assertEqual(len(line.splitlines()), 3 if width < 50 else 1)
            self.assertTrue(all(cells(part) <= width for part in line.splitlines()))
            self.assertIn('alpha.toml', line)
            self.assertIn('beta.toml', line)
        self.assertIn('~/dots/profiles/linux/common/files/東京/alpha.toml', self.render([row], 120))
        narrow = self.render([row], 40)
        self.assertIn('東京/alpha.toml', narrow)
        self.assertNotIn('profiles/linux/common', narrow)
        row.update(source='~/' + 'あ' * 17, target='~/' + 'Z' * 37)
        wrapped = self.render([row], 40).splitlines()
        self.assertTrue(all(line.startswith(' ') and cells(line) <= 40 for line in wrapped if line))
        self.assertTrue(any('あ' * 17 in line for line in wrapped))
        self.assertTrue(any('Z' * 37 in line for line in wrapped))
        row['source'] += 'あ' * 25
        overflow = self.render([row], 40).splitlines()
        self.assertTrue(all(cells(line) <= 40 for line in overflow))
        self.assertIn('あ' * 42, ''.join(s.strip() for s in overflow))
        self.assertTrue(all(cells(line) <= 16 for line in self.render([row], 16).splitlines()))

    def test_shared_basenames_and_native_path_spelling(self):
        row = dict(self.row, source='~/dots/profiles/my/profile/config/left/settings.json',
                   target='~/.config/Tools/an application/right/settings.json')
        line = self.render([row], 56, platform='windows')
        self.assertIn('left/settings.json', line)
        self.assertIn('right/settings.json', line)
        self.assertNotIn('\\', line)
        for source in (r'C:\Users\me\profiles\example\app\prefs.ini',
                       r'\\server\share\profiles\example\app\prefs.ini'):
            shortened = compact_path(source, 24, windows=True)
            self.assertLessEqual(cells(shortened), 24)
            self.assertTrue(shortened.endswith(r'app\prefs.ini'))
            self.assertNotIn('/', shortened)

    def test_identical_abbreviated_pairs_show_the_distinct_directories(self):
        source = '~/.local/state/dots/current/theme/bat.tmTheme'
        rows = [dict(self.row, id='theme:codex', source=source, target='~/.codex/themes/dots.tmTheme'),
                dict(self.row, id='theme:leaf-syntax', source=source, target='~/.config/leaf/themes/dots.tmTheme')]
        output = self.render(rows, 40)
        self.assertIn('  󱞩 ~/.codex/themes/dots.tmTheme', output)
        self.assertIn('  󱞩 ~/.config/leaf/themes/dots.tmTheme', output)
        self.assertNotIn('theme:codex', output)
        self.assertTrue(all(cells(line) <= 40 for line in output.splitlines()))
        # Identical complete path pairs are still selectable by their actual IDs.
        rows[1]['target'] = rows[0]['target']
        repeated = self.render(rows, 40)
        self.assertIn('theme:codex', repeated)
        self.assertIn('theme:leaf-syntax', repeated)

    def test_color_controls_and_inert_paths(self):
        row = dict(self.row, source=str(self.home / 'dots/-a\x1b[H.sh'), target=str(self.home / '-é.conf'))
        ansi = re.compile(r'\033\[[0-9;]+m')
        plain = self.render([row], icons=False)
        styled = self.render([row], icons=False, color=True)
        self.assertNotEqual(styled, plain)
        self.assertEqual(ansi.sub('', styled), plain)
        self.assertIn('\\x1b[H.sh', plain)
        self.assertNotIn('\x1b[H', styled)

    def test_custom_file_colors_and_glyphs(self):
        theme = self.home / 'state/dots/current/theme'
        theme.mkdir(parents=True)
        (theme / 'file-styles.tsv').write_text(
            'dots-file-styles\t1\n'
            'type\tdir\t38;5;125\t-\n'
            'type\tsymlink\t38;5;126\t-\n'
            'suffix\t.toml\t38;5;127\texact\n', encoding='utf-8')
        row = dict(self.row, source='~/app/settings.toml', target='~/.config/settings')
        roles = {'files.file': 'F', 'files.symlink': 'L', 'status.stashed': 'S'}
        with patch('style_config.icon', side_effect=lambda key, fallback: roles.get(key, fallback)):
            styled = self.render([row, dict(row, status='stashed')], color=True)
        self.assertIn('\x1b[38;5;125m~/app/', styled)
        self.assertIn('\x1b[38;5;127msettings.toml', styled)
        self.assertIn('\x1b[38;5;126msettings', styled)
        self.assertEqual(re.sub(r'\033\[[0-9;]+m', '', styled),
                         ' F ~/app/settings.toml -> L ~/.config/settings\n S dots:zshrc\n')

    def test_every_arrow_uses_the_published_dark_foreground(self):
        for width, arrow in ((49, '󱞩'), (50, '->')):
            plain_theme = self.render([self.row], width, color=True)
            self.assertRegex(plain_theme, '\x1b' + r'\[90m *' + re.escape(arrow) + r' *\x1b\[0m')
        profile = self.home / 'dots/profiles/linux/profile.json'
        profile.parent.mkdir(parents=True)
        profile.write_text(json.dumps(dict(schema=1, id='linux', files=[])), encoding='utf-8')
        from style_config import current
        current.cache_clear()
        theme = self.home / 'state/dots/current/theme'
        theme.mkdir(parents=True)
        (theme / 'palette.json').write_text(json.dumps(dict(colors={
            'dark_foreground': '#314257', 'foreground': '#7394ba', 'green': '#00ff00'})), encoding='utf-8')
        directory = dict(self.row, strategy='directory-link', source='~/d/cfg', target='~/.cfg')
        error = dict(self.row, status='source-missing')
        long_pair = dict(self.row, source='~/' + 'a' * 27, target='~/' + 'b' * 27)
        for row, width, icons, arrow in ((self.row, 50, True, '->'), (long_pair, 50, True, '->'),
                                         (error, 80, False, '->'), (directory, 49, True, '->'),
                                         (self.row, 49, True, '󱞩'), (error, 40, False, '->')):
            with self.subTest(width=width, icons=icons, status=row['status']):
                output = self.render([row], width, icons=icons, color=True)
                self.assertRegex(output, '\x1b' + r'\[38;2;49;66;87m *' + re.escape(arrow) + r' *\x1b\[0m')
                self.assertNotIn('\x1b', self.render([row], width, icons=icons, color=False))

    def test_default_and_verbose_share_the_files_heading(self):
        row = dict(self.row, source_spec='${DOTS}/shells/zsh/zshrc', enabled=True)
        default = self.render([row], icons=False, view='default')
        verbose = self.render([row], icons=False, view='verbose')
        self.assertTrue(default.startswith('Files\n'))
        self.assertTrue(verbose.startswith('Files\n'))
        self.assertNotIn('Source spec', default)
        for value in ('Source spec', '${DOTS}/shells/zsh/zshrc', 'Strategy', 'Enabled'):
            self.assertIn(value, verbose)


if __name__ == '__main__':
    unittest.main()

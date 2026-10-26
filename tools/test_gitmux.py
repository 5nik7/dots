#!/usr/bin/env python3
"""Gitmux consumer and palette checks in owned Git homes and private tmux servers."""
import json
import os
from pathlib import Path
import shlex
import shutil
import runpy
import re
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

import test_tmux_status as status
import test_themes as themes

ROOT = Path(__file__).resolve().parents[1]
GITMUX = os.environ.get('DOTS_TEST_GITMUX') or shutil.which('gitmux')
GIT_IT = shutil.which('git-it')


class GitmuxAdapter(unittest.TestCase):
    def test_remote_metadata_is_limited_to_known_icons_with_a_remote(self):
        icon = runpy.run_path(str(ROOT / 'config/tmux/gitmux-status.py'))['remote_icon']
        for glyph in ('󰊤', '', '', ''):
            self.assertEqual(icon(json.dumps({'remote': 'origin', 'icon': glyph})), glyph)
            self.assertEqual(icon(json.dumps({'remote': '', 'icon': glyph})), '')
        for data in (None, [], {}, {'remote': True, 'icon': '󰊤'},
                     {'remote': 'origin', 'icon': '#[fg=red]'},
                     {'remote': 'origin', 'icon': '󰊤|'},
                     {'remote': 'origin', 'icon': '󰊤\n'}):
            self.assertEqual(icon(json.dumps(data)), '')

    def test_snapshot_providers_fail_independently_and_share_deadline(self):
        fixture = status.TmuxStatus('test_layout_and_template_ownership')
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        def provider(name, body):
            path = fixture.tools / name
            path.write_text('#!' + sys.executable + '\n' + body + '\n')
            path.chmod(0o700)
        def output(snapshot=True):
            result = subprocess.run([sys.executable, '-B', str(ROOT / 'config/tmux/gitmux-status.py'),
                                     *(['--snapshot'] if snapshot else []), str(fixture.home)],
                                    env=fixture.env, capture_output=True, text=True, timeout=3)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, '')
            return result.stdout.rstrip('\n')
        good_icon = 'print(\'{"remote":"origin","icon":"󰊤"}\')'
        provider('git-it', 'import sys\nassert sys.argv[1:] == ["info", "--json"]\n' + good_icon)
        provider('gitmux', 'print("branch|literal#{unsafe}")')
        self.assertEqual(output(), '󰊤|branch|literal##{unsafe}')
        self.assertEqual(output(False), 'branch|literal##{unsafe}')
        for bad in ('print("invalid")', 'print("x" * 65537)', 'raise SystemExit(1)',
                    'print(\'{"remote":"origin","icon":"\\\\u001b"}\')'):
            provider('git-it', bad)
            self.assertEqual(output(), '|branch|literal##{unsafe}')
        provider('git-it', good_icon)
        for bad in ('print("x" * 16385)', 'print("bad\\x1b")', 'raise SystemExit(1)'):
            provider('gitmux', bad)
            self.assertEqual(output(), '󰊤|')
        provider('gitmux', 'import time\ntime.sleep(3)')
        start = time.monotonic()
        self.assertEqual(output(), '󰊤|')
        self.assertLess(time.monotonic() - start, 1.7)
        provider('git-it', 'import time\ntime.sleep(3)')
        start = time.monotonic()
        self.assertEqual(output(), '|')
        self.assertLess(time.monotonic() - start, 1.7)
        provider('gitmux', 'print("branch")')
        self.assertEqual(output(), '|branch')
        # Executable lookup failure is independent too, with only owned PATH entries.
        (fixture.tools / 'git-it').unlink()
        fixture.env['PATH'] = str(fixture.tools)
        self.assertEqual(output(), '|branch')
        provider('git-it', good_icon)
        (fixture.tools / 'gitmux').unlink()
        self.assertEqual(output(), '󰊤|')

    def test_normalization_is_limited_to_adjacent_typed_fields(self):
        compact = runpy.run_path(str(ROOT / 'config/tmux/gitmux-status.py'))['compact_fields']
        def style(role):
            return '#[fg=#{s/^reset$/default/:@dots-gitmux-' + role + '},nobold]'
        metrics = style('added') + '+1849 ' + style('deleted') + '-340'
        self.assertEqual(compact(metrics), metrics.replace('+1849 ', '+1849'))
        divergence = style('ahead') + '⇡2' + style('behind') + '⇣1 '
        self.assertEqual(compact(divergence), style('conflict') + '⇡2' + style('conflict') + '⇣1 ')
        for text in ('branch+1849 -340', style('branch') + '+1849 ' + style('deleted') + '-340',
                     style('staged') + '+4 ' + style('deleted') + '-2',
                     style('added') + '+1849 ', style('deleted') + '-340',
                     style('ahead') + '⇡2 ', style('behind') + '⇣1 ',
                     style('branch') + '⇡2' + style('behind') + '⇣1 '):
            self.assertEqual(compact(text), text)

    def test_literal_names_preserve_configured_styles_and_reject_controls(self):
        literal = runpy.run_path(str(ROOT / 'config/tmux/gitmux-status.py'))['literal_names']
        style = '#[fg=#{s/^reset$/default/:@dots-gitmux-branch},bold]'
        self.assertEqual(literal(style + 'x#{@bad}#(touch X)#[default]\n'),
                         style + 'x##{@bad}##(touch X)#[default]')
        for text in ('bad\x1b[31m', 'bad\rline', 'bad\nline', 'bad\x7f', 'bad\x85'):
            with self.subTest(text=repr(text)), self.assertRaises(ValueError):
                literal(text)


@unittest.skipUnless(GITMUX and status.TMUX and shutil.which('git'), 'gitmux, tmux and Git required')
class Gitmux(unittest.TestCase):
    def setUp(self):
        self.fixture = status.TmuxStatus('test_layout_and_template_ownership')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.env = self.fixture.env
        self.env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_TERMINAL_PROMPT='0', GIT_AUTHOR_NAME='Fixture',
                        GIT_COMMITTER_NAME='Fixture', GIT_AUTHOR_EMAIL='fixture@example.invalid',
                        GIT_COMMITTER_EMAIL='fixture@example.invalid')
        self.binary = self.fixture.tools / 'gitmux'
        self.binary.symlink_to(Path(GITMUX).resolve())
        self.config = self.fixture.home / '.gitmux.conf'
        shutil.copy2(ROOT / 'config/gitmux/gitmux.conf', self.config)
        self.repo = self.root / '-work ü $(touch SENTINEL)'
        self.repo.mkdir()
        self.git('init', '-q', '-b', 'main')
        (self.repo / 'tracked').write_text('one\n')
        self.git('add', 'tracked')
        self.git('commit', '-qm', 'fixture')

    def git(self, *args, code=0):
        result = subprocess.run(['git', '-c', 'core.hooksPath=' + os.devnull,
                                 '-c', 'commit.gpgsign=false', *args], cwd=self.repo,
                                env=self.env, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, code, result.stderr)
        return result.stdout.strip()

    def output(self):
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'config/tmux/gitmux-status.py'), str(self.repo)],
                                cwd=self.fixture.home, env=self.env, capture_output=True, text=True, timeout=3)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return result.stdout

    def text_output(self):
        return re.sub(r'#\[[^\]]*\]', '', self.output()).strip()

    def view(self, termux=True):
        inner, base = self.fixture.server('git-inner', termux=termux)
        self.fixture.write_theme()
        cfg = self.fixture.write_config()
        inner('source-file', str(cfg))
        inner('respawn-pane', '-k', '-c', str(self.repo), 'sleep 120')
        inner('set-option', '-gw', 'automatic-rename', 'off')
        inner('rename-window', 'fixture')
        inner('set-option', '-g', 'status-interval', '1')
        outer, _ = self.fixture.server('git-view', termux=False)
        outer('set-option', '-g', 'status', 'off')
        outer('set-option', '-g', 'default-terminal', 'tmux-256color')
        attach = shlex.join(['env', '-u', 'TMUX', '-u', 'TMUX_PANE', *base, 'attach-session', '-t', 'fixture'])
        outer('new-session', '-d', '-s', 'view', '-x', '120', '-y', '24', attach)
        deadline = time.monotonic() + 5
        while not inner('list-clients', '-F', '#{client_tty}'):
            self.assertLess(time.monotonic(), deadline, 'private client must finish attaching')
            time.sleep(.05)
        self.inner, self.outer, self.row = inner, outer, 1 if termux else 0
        self.await_row(lambda row: 'main' in row)
        return cfg

    def await_row(self, predicate):
        self.inner('refresh-client', '-S')
        rows = self.fixture.await_screen(self.outer, 'view', lambda rows:
                                        len(rows) > self.row and predicate(rows[self.row]))
        return rows[self.row]

    def test_actual_states_and_compact_options(self):
        self.assertEqual(self.text_output(), 'main')
        self.git('branch', 'upstream')
        self.git('branch', '--set-upstream-to=upstream')
        (self.repo / 'tracked').write_text('two\n')
        self.git('commit', '-qam', 'ahead')
        self.assertIn('⇡1', self.output())
        self.assertNotIn('upstream', self.output())
        self.git('checkout', '-q', 'upstream')
        (self.repo / 'tracked').write_text('conflicting\n')
        self.git('commit', '-qam', 'upstream change')
        self.git('checkout', '-q', 'main')
        self.assertIn('⇡1⇣1', self.text_output())
        self.git('merge', 'upstream', code=1)
        self.assertIn('[merge]', self.output())
        self.assertIn('=1', self.output())
        self.git('merge', '--abort')
        (self.repo / 'tracked').write_text('three\n')
        (self.repo / 'new').write_text('untracked\n')
        self.assertIn('!1', self.output())
        self.assertIn('?1', self.output())
        self.git('add', 'tracked')
        self.assertIn('+1', self.output())
        self.git('stash', 'push', '-q', '-u')
        self.assertIn('*1', self.output())
        self.git('checkout', '-q', '--detach')
        self.assertIn(':', self.output())
        name = 'feature/' + 'long-' * 12
        self.git('checkout', '-qb', name)
        self.assertIn(name[:23] + '…', self.output())
        self.git('checkout', '-q', '--orphan', 'unborn')
        self.assertIn('[no commits yet]', self.output())

    @unittest.skipUnless(GIT_IT, 'optional git-it unavailable')
    def test_native_remote_hosts_aliases_and_preferred_remote(self):
        def icon():
            result = subprocess.run([sys.executable, '-B', str(ROOT / 'config/tmux/gitmux-status.py'),
                                     '--snapshot', str(self.repo)], env=self.env,
                                    capture_output=True, text=True, timeout=3)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, '')
            return result.stdout.split('|', 1)[0]
        self.assertEqual(icon(), '')
        self.git('remote', 'add', 'origin', 'https://github.com/example/repo.git')
        for flags in ([], ['--snapshot']):
            result = subprocess.run([sys.executable, '-B', str(ROOT / 'config/tmux/gitmux-status.py'),
                                     *flags, './' + self.repo.name], cwd=self.root, env=self.env,
                                    capture_output=True, text=True, timeout=3)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('main', result.stdout)
            self.assertEqual(result.stdout.startswith('󰊤|'), bool(flags))
        for url, glyph in (('https://github.com/example/repo.git', '󰊤'),
                           ('git@gitlab.com:example/repo.git', ''),
                           ('ssh://git@bitbucket.org/example/repo.git', ''),
                           ('https://unknown.invalid/example/repo.git', ''),
                           (str(self.root / 'local.git'), '')):
            self.git('remote', 'set-url', 'origin', url)
            self.assertEqual(icon(), glyph)
        config = self.fixture.config / 'git-it/config'
        config.parent.mkdir()
        config.write_text('[git-it]\n\thostAlias = work-alias=github.com\n')
        self.git('remote', 'set-url', 'origin', 'git@work-alias:example/repo.git')
        self.assertEqual(icon(), '󰊤')
        self.git('remote', 'add', 'preferred', 'https://gitlab.com/example/repo.git')
        self.git('config', 'branch.main.remote', 'preferred')
        self.assertEqual(icon(), '')
        self.git('config', 'branch.main.remote', '.')
        self.assertEqual(icon(), '󰊤')
        self.git('remote', 'remove', 'origin')
        self.assertEqual(icon(), '')

    @unittest.skipUnless(GIT_IT, 'optional git-it unavailable')
    def test_native_session_icons_widths_attributes_and_directory_changes(self):
        self.git('remote', 'add', 'origin', 'https://github.com/example/repo.git')
        self.view()
        self.inner('rename-session', 'dots')
        self.inner('rename-window', 'dots')
        row = self.await_row(lambda row: '󰊤 dots │ main' in row)
        self.assertEqual(self.fixture.colors_at(row, '󰊤'),
                         {'fg': (85, 255, 255), 'bg': (85, 102, 119)})
        self.assertTrue(self.fixture.bold_at(row, '󰊤'))
        self.assertFalse(self.fixture.underline_at(row, '󰊤'))
        self.assertTrue(self.fixture.underline_at(row, 'dots'))
        self.assertFalse(self.fixture.underline_at(row, '󰊤', -1))
        tty = self.inner('list-clients', '-F', '#{client_tty}').splitlines()[0]
        self.fixture.snapshot([tty, 'pts/99999'])
        other = self.inner('new-session', '-d', '-P', '-F', '#{session_id}', '-s', 'other', 'sleep 120')
        row = self.await_row(lambda row: '1 󰊤 dots │ main' in row)
        self.assertFalse(self.fixture.dim_at(row, '1 󰊤', 1))
        self.assertFalse(self.fixture.bold_at(row, '1 󰊤', 1))
        self.assertFalse(self.fixture.underline_at(row, '1 󰊤', 1))
        self.assertFalse(self.fixture.dim_at(row, '󰊤'))
        self.assertFalse(self.fixture.dim_at(row, 'main'))
        self.assertFalse(self.fixture.underline_at(row, '1 󰊤'))
        self.assertFalse(self.fixture.underline_at(row, '󰊤'))
        self.assertTrue(self.fixture.underline_at(row, 'dots'))
        self.assertEqual(self.fixture.colors_at(row, '│')['bg'], (34, 51, 68))
        for width in (40, 80, 120):
            self.outer('resize-window', '-t', 'view', '-x', str(width), '-y', '24')
            row = self.await_row(lambda row: '1 󰊤 ' in row and 'main' in row)
            # Measure the captured label, including padding. display-message's
            # asynchronous job cache is separate from the rendered status row.
            label = self.fixture.plain(row).split('│', 1)[0]
            self.inner('set-option', '-g', '@fixture-label', label)
            cells = self.inner('display-message', '-p', '#{w:@fixture-label}')
            self.assertLessEqual(int(cells), min(width // 4, 30))
            self.inner('set-option', '-g', '@dots-termux-default', '1')
            row = self.await_row(lambda row: '1 󰊤 │ main' in row)
            self.assertNotIn('dots', self.fixture.plain(row))
            self.inner('set-option', '-gu', '@dots-termux-default')
        self.fixture.snapshot([tty])
        self.inner('kill-session', '-t', other)
        self.inner('set-option', '-g', '@dots-termux-default', '1')
        self.await_row(lambda row: '󰊤 │ main' in row and '1 ' not in row)
        self.inner('set-option', '-gu', '@dots-termux-default')
        self.inner('new-window', '-n', 'name:colon', '-c', str(self.repo), 'sleep 120')
        row = self.await_row(lambda row: '1 name:colon' in row)
        self.assertFalse(self.fixture.dim_at(row, '1 name:colon', 1))
        self.assertFalse(self.fixture.bold_at(row, '1 name:colon', 1))
        self.assertEqual(self.fixture.colors_at(row, '1 name:colon', 1),
                         {'fg': (34, 51, 68), 'bg': (85, 102, 119)})
        self.assertFalse(self.fixture.dim_at(row, '1 name:colon', 6))
        self.assertFalse(self.fixture.bold_at(row, 'name:colon'))
        self.assertEqual(self.fixture.colors_at(row, 'name:colon'),
                         {'fg': (238, 238, 238), 'bg': (85, 102, 119)})
        self.assertEqual(self.fixture.colors_at(row, '1 name:colon'),
                         {'fg': (85, 255, 85), 'bg': (85, 102, 119)})
        # The same split preserves a pipe inside Git text.
        self.git('branch', '-m', 'main|literal')
        self.await_row(lambda row: 'main|literal' in row and '󰊤' in row)
        self.inner('split-window', '-c', str(self.fixture.home), 'sleep 120')
        self.await_row(lambda row: '󰊤' not in row and '' not in row)
        self.inner('last-pane')
        self.await_row(lambda row: '󰊤' in row and 'main|literal' in row)
        self.git('remote', 'remove', 'origin')
        self.await_row(lambda row: '󰊤' not in row and 'main|literal' in row)
        self.git('remote', 'add', 'origin', 'https://github.com/example/repo.git')
        self.inner('set-environment', '-gu', 'TERMUX_VERSION')
        self.inner('source-file', str(self.fixture.tmux_config / 'tmux.conf'))
        self.row = 0
        self.await_row(lambda row: '󰊤 dots' in row and '1 󰊤' not in row)

    def test_inline_colors_widths_and_empty_labels(self):
        self.view()
        for width in (40, 80, 120):
            with self.subTest(width=width):
                self.outer('resize-window', '-t', 'view', '-x', str(width), '-y', '24')
                row = self.await_row(lambda row: 'fixture │ main' in row)
                self.assertEqual(self.fixture.colors_at(row, 'main')['fg'], (187, 0, 187))
                self.assertFalse(self.fixture.bold_at(row, 'main'))
                self.assertNotIn('✔', self.fixture.plain(row))
                self.assertEqual(self.fixture.colors_at(row, 'main')['bg'], (17, 34, 51))
        # Rendered styles inside gitmux output follow tmux options without regenerating YAML.
        self.inner('set-option', '-g', '@dots-gitmux-branch', 'reset')
        row = self.await_row(lambda row: 'main' in row)
        self.assertEqual(self.fixture.colors_at(row, 'main')['fg'], (238, 238, 238))
        self.inner('set-option', '-g', '@dots-termux-default', '1')
        row = self.await_row(lambda row: 'main' in row and 'fixture' not in row)
        self.assertNotIn('│', self.fixture.plain(row))
        # Only the current number remains when its project name is hidden.
        tty = self.inner('list-clients', '-F', '#{client_tty}').splitlines()[0]
        self.fixture.snapshot([tty, 'pts/9999'])
        self.inner('new-session', '-d', '-s', 'other', 'sleep 120')
        row = self.await_row(lambda row: ' 1 │ main' in row)
        # Long content clips by visible cells, never the bytes of its style directives.
        self.git('branch', '-m', 'very-long-feature-' + 'x' * 40)
        for width, bound in ((40, 20), (80, 40), (120, 48)):
            self.outer('resize-window', '-t', 'view', '-x', str(width), '-y', '24')
            row = self.await_row(lambda row: 'very-' in row)
            visible = self.fixture.plain(row).split('', 1)[1].rstrip()
            self.assertLessEqual(len('' + visible), bound)
            self.assertNotIn('#[', self.fixture.plain(row))
        self.outer('resize-window', '-t', 'view', '-x', '120', '-y', '24')
        self.git('branch', '-m', 'literal-#{@bad}')
        self.inner('set-option', '-g', '@bad', 'EXPANDED')
        row = self.await_row(lambda row: 'literal-' in row)
        self.assertIn('literal-#{@bad}', self.fixture.plain(row))
        self.assertNotIn('EXPANDED', self.fixture.plain(row))
        self.git('branch', '-m', '#(touch${IFS}X)')
        row = self.await_row(lambda row: 'touch' in row)
        self.assertIn('#(touch${IFS}X)', self.fixture.plain(row))
        self.assertFalse((self.fixture.home / 'X').exists())
        self.assertFalse((self.fixture.home / 'SENTINEL').exists())

    def test_panes_failures_modes_and_reload(self):
        cfg = self.view(termux=False)
        self.inner('source-file', str(cfg))
        self.inner('set-option', '-gw', 'automatic-rename', 'off')
        self.inner('rename-window', 'fixture')
        self.await_row(lambda row: row.count('main') == 1)
        self.config.rename(self.config.with_suffix('.saved'))
        self.await_row(lambda row: '' not in row and '│' not in row)
        self.config.with_suffix('.saved').rename(self.config)
        self.await_row(lambda row: 'main' in row)
        valid = self.config.read_text()
        self.config.write_text('tmux: [invalid\n')
        self.await_row(lambda row: '' not in row)
        self.config.write_text(valid)
        self.await_row(lambda row: 'main' in row)
        self.binary.unlink()
        self.await_row(lambda row: '' not in row)
        self.binary.symlink_to(Path(GITMUX).resolve())
        self.await_row(lambda row: 'main' in row)
        original_pane = self.inner('display-message', '-p', '#{pane_id}')
        self.inner('split-window', '-h', '-c', str(self.fixture.home), 'sleep 120')
        self.await_row(lambda row: '' not in row and '│' not in row)
        self.inner('select-pane', '-t', original_pane)
        self.await_row(lambda row: 'main' in row)
        self.inner('resize-pane', '-Z')
        row = self.await_row(lambda row: 'main' in row and 'ZOOM' in row)
        self.assertLess(self.fixture.plain(row).index('main'), self.fixture.plain(row).index('ZOOM'))
        self.assertEqual(self.fixture.colors_at(row, 'ZOOM')['bg'], (0, 255, 0))
        self.inner('copy-mode', '-t', original_pane)
        tty = self.inner('list-clients', '-F', '#{client_tty}').splitlines()[0]
        self.inner('switch-client', '-c', tty, '-T', 'prefix')
        row = self.await_row(lambda row: all(text in row for text in ('main', 'COPY', 'PREFIX', 'ZOOM')))
        self.assertEqual(self.fixture.colors_at(row, 'PREFIX')['bg'], (34, 51, 68))
        for label in ('COPY', 'ZOOM'):
            self.assertEqual(self.fixture.colors_at(row, label)['bg'], (0, 255, 0))
        self.inner('switch-client', '-c', tty, '-T', 'root')
        self.inner('send-keys', '-X', '-t', original_pane, 'cancel')
        # Slow Git is killed by gitmux's deadline and the status job clears old output.
        git = self.fixture.tools / 'git'
        git.write_text('#!' + status.BASH + '\nexec sleep 3\n')
        git.chmod(0o700)
        start = time.monotonic()
        self.await_row(lambda row: '' not in row and 'ZOOM' in row)
        self.assertLess(time.monotonic() - start, 5)
        git.unlink()
        self.await_row(lambda row: 'main' in row)
        # Oversized or control-bearing consumer output is discarded, not rendered.
        self.binary.unlink()
        self.binary.write_text('#!' + sys.executable + '\nprint("x" * 17000)\n')
        self.binary.chmod(0o700)
        self.await_row(lambda row: '' not in row and 'ZOOM' in row)
        self.binary.write_text('#!' + sys.executable + '\nprint("unsafe\\x1b[31m")\n')
        row = self.await_row(lambda row: '' not in row and 'ZOOM' in row)
        self.assertNotIn('unsafe', self.fixture.plain(row))

    def test_native_starship_metrics_status_weights_and_divergence(self):
        self.view()
        (self.repo / 'tracked').write_text('two\nthree\n')
        (self.repo / 'new').write_text('untracked\n')
        for width in (40, 80, 120):
            self.outer('resize-window', '-t', 'view', '-x', str(width), '-y', '24')
            row = self.await_row(lambda row: 'main !1 ?1 +2-1' in row)
            for label, foreground, bold in [('main', (187, 0, 187), False),
                                            ('!1', (170, 170, 0), True),
                                            ('?1', (170, 0, 170), True),
                                            ('+2', (0, 204, 0), False),
                                            ('-1', (204, 0, 0), False)]:
                self.assertEqual(self.fixture.colors_at(row, label)['fg'], foreground)
                self.assertEqual(self.fixture.bold_at(row, label), bold)
        (self.repo / 'tracked').write_text('one\nextra\n')
        row = self.await_row(lambda row: 'main !1 ?1 +1' in row and '-1' not in row)
        self.assertNotIn('-0', self.fixture.plain(row))
        (self.repo / 'tracked').write_text('')
        row = self.await_row(lambda row: 'main !1 ?1 -1' in row)
        self.assertNotIn('+0', self.fixture.plain(row))
        self.git('add', 'tracked')
        row = self.await_row(lambda row: 'main +1 ?1' in row and '-1' not in row)
        self.assertEqual(self.fixture.colors_at(row, '+1')['fg'], (0, 170, 0))
        self.assertFalse(self.fixture.bold_at(row, '+1'))
        self.git('stash', 'push', '-q', '-u')
        row = self.await_row(lambda row: 'main *1' in row)
        self.assertEqual(self.fixture.colors_at(row, '*1')['fg'], (136, 136, 136))
        self.assertFalse(self.fixture.bold_at(row, '*1'))
        self.git('branch', 'upstream')
        self.git('branch', '--set-upstream-to=upstream')
        self.git('commit', '--allow-empty', '-qm', 'ahead')
        row = self.await_row(lambda row: 'main ⇡1 *1' in row)
        self.assertEqual(self.fixture.colors_at(row, '⇡1')['fg'], (0, 221, 0))
        self.git('checkout', '-q', 'upstream')
        self.git('commit', '--allow-empty', '-qm', 'upstream-only')
        self.git('checkout', '-q', 'main')
        row = self.await_row(lambda row: 'main ⇡1⇣1 *1' in row)
        for label in ('⇡1', '⇣1'):
            self.assertEqual(self.fixture.colors_at(row, label)['fg'], (170, 0, 0))
            self.assertFalse(self.fixture.bold_at(row, label))
        # Move the test-owned branch back to the common ancestor: behind only.
        self.git('reset', '--hard', 'HEAD~1')
        row = self.await_row(lambda row: 'main ⇣1 *1' in row)
        self.assertEqual(self.fixture.colors_at(row, '⇣1')['fg'], (221, 221, 0))


class GitmuxThemes(unittest.TestCase):
    setUp = themes.Themes.setUp
    run_command = themes.Themes.run_command
    dots = themes.Themes.dots
    engine = themes.Themes.engine
    shell = themes.Themes.shell
    wal_export = themes.Themes.wal_export

    def test_all_palettes_both_renderers_and_overrides(self):
        sys.path.insert(0, str(ROOT / 'lib/dots/themes'))
        from palette_native import Themes
        self.wal_export()
        (self.home / 'cache/wal/colors.json').write_text(json.dumps({
            'special': {'background': '#102030', 'foreground': '#eeeeee', 'cursor': '#abcdef'},
            'colors': {f'color{i}': f'#{i+32:02x}{i+48:02x}{i+64:02x}' for i in range(16)}}))
        identities = self.dots('theme', 'list').stdout.splitlines()
        for index, identity in enumerate([*identities, 'nord']):
            if index == len(identities):
                overlay = self.home / 'config/dots/file-colors.toml'
                overlay.parent.mkdir(parents=True, exist_ok=True)
                overlay.write_text('[git.branch]\nfg = "#123456"\n[git.clean]\nfg = "reset"\n'
                                   '[git.ahead]\nfg = "#abcdef"\n[git.behind]\nfg = "reset"\n')
            with self.subTest(theme=identity, overrides=index == len(identities)):
                out = self.root / f'bash-{index}'; out.mkdir()
                self.env.update(RENDER_THEME=identity, RENDER_OUTPUT=str(out))
                self.engine('dt_load "$RENDER_THEME" && dt_render "$RENDER_OUTPUT"')
                native = self.root / f'native-{index}'; native.mkdir()
                with patch.dict(os.environ, self.env, clear=True):
                    Themes().render(identity, native)
                raw = (out / 'tmux.conf').read_text()
                self.assertEqual(raw, (native / 'tmux.conf').read_text())
                self.assertNotIn('{{', raw)
                colors = json.loads((out / 'colors.json').read_text())['colors']
                for option, role in (('current', 'foreground'), ('inactive', 'dark_foreground')):
                    self.assertIn(f'set -g @dots-window-name-{option}-fg "{colors[role]}"', raw)
                for option, role in (('window-name-current-bg', 'selection_background'), ('window-number-inactive-fg', 'dark_foreground'), ('separator-bg', 'dark_background')):
                    self.assertIn(f'set -g @dots-{option} "{colors[role]}"', raw)
                for role in ('branch', 'staged', 'modified', 'untracked', 'conflict', 'clean', 'added', 'deleted', 'ahead', 'behind'):
                    self.assertIn(f'set -g @dots-gitmux-{role} "{colors["git"][role]}"', raw)
                if index == len(identities):
                    self.assertIn('@dots-gitmux-branch "#123456"', raw)
                    self.assertIn('@dots-gitmux-clean "reset"', raw)
                    self.assertIn('@dots-gitmux-ahead "#abcdef"', raw)
                    self.assertIn('@dots-gitmux-behind "reset"', raw)


if __name__ == '__main__':
    unittest.main()

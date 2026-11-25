#!/usr/bin/env python3
"""Complete renderer chains and actual FZF/fzf-tab handoffs in private roots."""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import unittest

import test_profile_config as fixtures
from fzf_config import validate_previewers

ROOT = fixtures.ROOT


class Preview(unittest.TestCase):
    def setUp(self):
        fixtures.ProfileConfig.setUp(self)
        shutil.copytree(ROOT / 'default', self.root / 'default')
        scripts = self.root / 'scripts'
        scripts.mkdir()
        for filename in ('_dots-fzf-preview', '_dots-fzf-preview.cmd'):
            shutil.copy2(ROOT / 'scripts' / filename, scripts)
        self.env.update(PATH=str(scripts) + os.pathsep + self.env['PATH'], TERM='xterm-256color',
                        TMPDIR=str(self.home), ZDOTDIR=str(self.home), SHELL=shutil.which('bash') or '')
        if os.name == 'nt':
            for key in ('COMSPEC', 'PATHEXT', 'SYSTEMROOT'):
                if key in os.environ:
                    self.env[key] = os.environ[key]
            self.env.update(USERPROFILE=str(self.home), APPDATA=str(self.home/'roaming'),
                            LOCALAPPDATA=str(self.home/'local'), TMP=str(self.home), TEMP=str(self.home))
        self.settings = self.root / 'profiles' / self.platform / 'config.json'

    def render(self, *args, **overrides):
        return subprocess.run([sys.executable, '-B', str(self.root / 'lib/dots/fzf_preview.py'), *args],
                              env=dict(self.env, **overrides), cwd=self.home, capture_output=True,
                              check=True, timeout=15).stdout.decode()

    def configure(self, kind, chain):
        self.settings.write_text(json.dumps({'schema': 1, 'apps': {'fzf': {'previewers': {kind: chain}}}}))

    def test_chains_templates_fallback_and_file_ownership(self):
        filename = self.home / "- ü '$(touch MARKER).py"
        filename.write_text("print('original')\n")
        self.configure('text', ['plain'])
        self.assertEqual(self.render(str(filename)), filename.read_text())
        selection = self.home / 'FZF input'
        selection.write_bytes(os.fsencode(filename) + b'\n')
        self.assertEqual(self.render('--selection', str(selection)), filename.read_text())
        self.configure('text', [['missing-renderer-123'], [sys.executable, '-c',
            "import sys; print(repr(sys.argv[1:]))", '{path}', '{width}', '{height}', '$(touch MARKER)']])
        self.assertEqual(self.render(str(filename), FZF_PREVIEW_COLUMNS='40', FZF_PREVIEW_LINES='9').strip(),
                         repr([str(filename), '40', '9', '$(touch MARKER)']))
        self.assertFalse((self.home / 'MARKER').exists())
        self.configure('text', [])
        self.assertEqual(self.render(str(filename)), '')
        self.configure('text', [['missing-renderer-123']])
        self.assertEqual(self.render(str(filename)), filename.read_text())

    def test_markdown_falls_through_to_configured_next_renderer(self):
        path = self.home / 'notes.md'
        path.write_text('# Title\n')
        self.settings.write_text(json.dumps({'schema': 1, 'apps': {
            'cli': {'markdown_viewer': 'mdcat'},
            'fzf': {'previewers': {'markdown': ['wiki', [sys.executable, '-c', 'print("SECOND")'], 'plain']}}
        }}))
        self.assertEqual(self.render(str(path), PATH=str(self.home)), 'SECOND\n')
        config = json.loads(self.settings.read_text())
        config['apps']['cli']['markdown_viewer'] = 'builtin'
        self.settings.write_text(json.dumps(config))
        self.assertEqual(self.render(str(path), PATH=str(self.home)), '# Title\n')

    @unittest.skipUnless(os.name == 'posix', 'POSIX fallback')
    def test_minimal_preview_bounds_and_filters_without_python(self):
        directory = self.home / 'commands'
        directory.mkdir()
        for tool in ('sh', 'head', 'tr', 'wc', 'ls'):
            (directory / tool).symlink_to(shutil.which(tool))
        script = self.root / 'scripts/_dots-fzf-preview'
        def preview(*args):
            return subprocess.run([shutil.which('sh'), str(script), *map(str, args)],
                                  env=dict(self.env, PATH=str(directory)), capture_output=True, timeout=5)
        path = self.home / '-literal $(marker).txt'
        path.write_bytes(b'\x1b]52;bad\x07' + b'x' * 200000)
        selection = self.home / 'selection'
        selection.write_text(str(path) + '\n')
        result = preview('--selection', selection)
        self.assertEqual(result.returncode, 0)
        self.assertNotIn(b'\x1b', result.stdout)
        self.assertNotIn(b'\x07', result.stdout)
        self.assertLessEqual(len(result.stdout), 131072)
        self.assertIn(b'xxx', result.stdout)
        self.assertEqual(preview('--completion', '--flag', '', 'help', 'options').stdout,
                         b'--flag\noptions\nhelp\n')
        selection.write_bytes(b'x' * 65537)
        self.assertNotEqual(preview('--selection', selection).returncode, 0)

    def test_binary_directories_fonts_images_markdown_and_completion(self):
        from fzf_preview import file_data
        for name, data, kind in [('notes.md', b'# Title\n', 'markdown'), ('pic', b'GIF89a00', 'image'),
                                 ('font.otf', b'', 'font'), ('binary', b'\0\1\2', 'binary')]:
            path = self.home / name
            path.write_bytes(data)
            self.assertEqual(file_data(path)[0], kind)
            self.configure(kind, ['metadata'])
            self.assertIn(kind.capitalize(), self.render(str(path)))
        self.configure('directory', ['listing'])
        self.assertIn('notes.md', self.render(str(self.home)))
        self.settings.write_text(json.dumps({'schema': 1, 'apps': {'cli': {'markdown_viewer': 'builtin'}}}))
        self.assertEqual(self.render(str(self.home / 'notes.md')), '# Title\n')
        self.assertEqual(self.render('--completion', '--flag', '', 'Option help', 'options'),
                         '--flag\noptions\nOption help\n')
        self.assertEqual(self.render('--completion', 'notes.md', str(self.home / 'notes.md'), '', ''), '# Title\n')
        if hasattr(os, 'mkfifo'):
            pipe = self.home / 'pipe'
            os.mkfifo(pipe)
            self.assertIn('Special', self.render(str(pipe)))
        for chain in ('plain', ['unknown'], [123], [['{path}']], [['tool', '\n']]):
            with self.assertRaises(ValueError):
                validate_previewers('text', chain)

    @unittest.skipUnless(os.name == 'posix', 'POSIX fixture executables')
    def test_image_protocol_and_font_fallback(self):
        import struct
        import zlib
        def chunk(tag, contents):
            return struct.pack('>I', len(contents)) + tag + contents + struct.pack('>I', zlib.crc32(tag + contents))
        image = self.home / 'sample.png'
        header = struct.pack('>IIBBBBB', 2, 2, 8, 0, 0, 0, 0)
        image.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header) +
                          chunk(b'IDAT', zlib.compress(b'\x00\xff\x00\x00\x00\xff')) + chunk(b'IEND', b''))
        graphics = '\x1b_Ga=T,f=24;YWJj\x1b\\'
        kitten = self.home / 'kitten'
        kitten.write_text('#!' + sys.executable + '\nimport sys\nsys.stdout.write(' +
                          repr(graphics + '\x1b]52;c;YmFk\x07' + 'sample') + ')\n')
        kitten.chmod(0o700)
        output = self.render(str(image), PATH=str(self.home) + os.pathsep + self.env['PATH'],
                             KITTY_WINDOW_ID='1', DOTS_COLOR='always')
        self.assertIn(graphics, output)
        self.assertNotIn('YmFk', output)
        if shutil.which('chafa'):
            self.configure('image', ['chafa', 'metadata'])
            symbols = self.render(str(image), FZF_PREVIEW_COLUMNS='20', FZF_PREVIEW_LINES='6')
            self.assertTrue(symbols.strip())
            self.assertNotIn(' bytes', symbols)
        if shutil.which('fc-scan'):
            try:
                from test_fonts import font
                path = self.home / 'Face.ttf'
                font(path, 'Sample Family')
            except ImportError:
                self.skipTest('fixture font builder unavailable')
            self.configure('font', ['font-info', 'metadata'])
            self.assertIn('Sample Family', self.render(str(path)))

    def test_config_alias_save_reaches_renderer_and_avoids_theme_generation(self):
        def run(*args):
            return fixtures.ProfileConfig.run_config(self, *args, native=os.name == 'nt')
        path = self.home / 'example.txt'
        path.write_text('readable\n')
        key = 'apps.fzf.settings.previewers.text'
        chain = [[sys.executable, '-c', 'print("configured renderer")'], 'plain']
        result = json.loads(run('set', key, json.dumps(chain), '--json-value', '--json').stdout)
        self.assertIn('next preview', str(result).lower())
        self.assertEqual(json.loads(run('get', 'settings.fzf.previewers.text', '--json').stdout)['value'], chain)
        self.assertEqual(self.render(str(path)), 'configured renderer\n')
        self.assertFalse((Path(self.env['XDG_STATE_HOME']) / 'dots/current/theme').exists())
        run('unset', 'fzf.settings.previewers.text')
        self.assertNotEqual(self.render(str(path)), 'configured renderer\n')

    @unittest.skipUnless(os.name == 'nt', 'requires native Windows cmd.exe')
    def test_windows_selection_file_launcher(self):
        filename = self.home / 'literal %USERPROFILE% & sample.txt'
        filename.write_text('Windows preview\n')
        self.configure('text', ['plain'])
        selection = self.home / 'selection data'
        selection.write_bytes(str(filename).encode('utf-8') + b'\n')
        result = subprocess.run([self.env['COMSPEC'], '/d', '/c', '_dots-fzf-preview', '--selection', str(selection)],
                                cwd=self.home, env=self.env, check=True, capture_output=True, timeout=15)
        self.assertEqual(result.stdout.decode().splitlines(), ['Windows preview'])

    @unittest.skipUnless(os.name == 'posix' and shutil.which('bash') and shutil.which('fzf'), 'FZF PTY unavailable')
    def test_generic_selection_files_at_three_widths(self):
        from bash_dots_pty import Terminal
        import fcntl
        import struct
        import termios
        path = self.home / "an odd-'$(touch marker)' file.txt"
        path.write_text('PREVIEW_CONTENT\n')
        self.configure('text', ['plain'])
        for width in (40, 80, 120):
            with self.subTest(width=width):
                terminal = Terminal(shutil.which('bash'), self.env, self.home)
                try:
                    fcntl.ioctl(terminal.master, termios.TIOCSWINSZ, struct.pack('HHHH', 24, width, 0, 0))
                    command = 'source ' + shlex.quote(str(ROOT / 'shells/shared/fzf.sh')) + '; '
                    command += "printf '%s\\n' " + shlex.quote(path.name) + " | fzf --height=100% --preview-window=down,70% > picked; test -s picked && printf 'CON''FIRMED\\n'"
                    terminal.send(command + '\r')
                    terminal.wait(b'\x1b[?1000h')
                    terminal.send('\x18')
                    terminal.wait(b'PREVIEW_CONTENT')
                    terminal.send('\r')
                    terminal.wait(b'CONFIRMED\r\n')
                    self.assertEqual((self.home / 'picked').read_text().rstrip('\n'), path.name)
                    self.assertFalse((self.home / 'marker').exists())
                finally:
                    terminal.close()

    @unittest.skipUnless(os.name == 'posix' and shutil.which('zsh') and shutil.which('fzf'), 'Zsh FZF PTY unavailable')
    def test_zsh_fzf_tab_routes_file_and_completion_preserving_insertion(self):
        from test_config_completion import FZF_TAB
        from bash_dots_pty import Terminal
        if not (FZF_TAB / 'fzf-tab.plugin.zsh').is_file():
            self.skipTest('fzf-tab unavailable')
        plugin = self.home / 'fzf-tab'
        shutil.copytree(FZF_TAB, plugin, ignore=shutil.ignore_patterns('.git'))
        self.env.update(SHELL=shutil.which('zsh'), TMPPREFIX=str(self.home / 'ztmp'))
        (self.home / 'chosen-one.txt').write_text('MATCHED_FILE_PREVIEW\n')
        (self.home / 'chosen-two.txt').write_text('MATCHED_FILE_PREVIEW\n')
        self.configure('completion', [[sys.executable, '-c', 'import sys; print("MATCHED_DESC", sys.argv[1])',
                                       '{description}']])
        setup = 'autoload -Uz compinit; compinit -D; source ' + shlex.quote(str(plugin/'fzf-tab.plugin.zsh'))
        setup += '; source ' + shlex.quote(str(ROOT/'shells/zsh/completions.zsh'))
        setup += r"""; export FZF_DEFAULT_OPTS='--preview-window=down,60%,nohidden'
zstyle ':fzf-tab:*' fzf-min-height 18
_values_with_help() { local -a values=('alpha:first choice' 'amber:second choice'); _describe 'options' values }
sample() { print -rn -- "$1" >| picked; print AC"CEPTED" }; compdef _values_with_help sample
PROMPT='READY> '; print INI"TIALIZED" """.strip().replace('\n', '; ')
        import fcntl
        import struct
        import termios
        import itertools
        cases = [('cat chosen-', b'MATCHED_FILE_PREVIEW'), ('sample a', b'MATCHED_DESC')]
        for width, (typed, marker) in itertools.product((40, 80, 120), cases):
            with self.subTest(width=width, typed=typed):
                terminal = Terminal(shutil.which('zsh'), self.env, self.home)
                try:
                    fcntl.ioctl(terminal.master, termios.TIOCSWINSZ, struct.pack('HHHH', 24, width, 0, 0))
                    terminal.send(setup + '\r')
                    terminal.wait(b'INITIALIZED\r\n')
                    terminal.send(typed + '\t')
                    terminal.wait(marker, 30)
                    if typed.startswith('sample'):
                        terminal.send('\x15amber')
                        terminal.wait(b'1/2')
                        terminal.send('\r')
                        terminal.wait(b'\x1b[?1000l')
                        terminal.send('\r')
                        terminal.wait(b'ACCEPTED\r\n')
                        self.assertEqual((self.home / 'picked').read_text(), 'amber')
                finally:
                    terminal.close()

if __name__ == '__main__':
    unittest.main()

#!/usr/bin/env python3
"""Specialized help consumers in disposable checkouts, without live providers."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SGR = re.compile(rb'\x1b\[[0-9;]*m')


class HelpAdapters(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='dots-help-adapters-')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / 'home ü'
        self.home.mkdir()
        self.root = Path(self.temp.name) / '-checkout space'
        ignore = shutil.ignore_patterns('__pycache__', '*.pyc', '.build', 'engine', 'tests')
        shutil.copytree(ROOT / 'lib/dots', self.root / 'lib/dots', ignore=ignore)
        shutil.copytree(ROOT / 'default', self.root / 'default', ignore=ignore)
        for app in ('blastoff', 'pkgs', 'anodize'):
            shutil.copytree(ROOT / 'plugins' / app, self.root / 'plugins' / app, ignore=ignore)
        for profile in ('linux', 'wsl', 'termux', 'windows'):
            target = self.root / 'profiles' / profile
            target.mkdir(parents=True)
            (target / 'profile.json').write_text(json.dumps(dict(schema=1, id=profile)))
            (target / 'colors.toml').write_text('\n'.join(
                '[apps.cli.help.'+role+']\nfg = "'+value+'"\n'
                for role,value in [('executable','#112233'), ('command','#223344'),
                                   ('subcommand','#334455'), ('option','#445566'),
                                   ('argument','#556677'), ('heading','#667788'),
                                   ('description','#778899'), ('punctuation','#8899aa')]))
        self.env = {k:v for k,v in os.environ.items() if k in
                    ('PATH','PREFIX','TERMUX_VERSION','TERMUX__PREFIX','LD_PRELOAD','SystemRoot','SYSTEMROOT')}
        self.env.update(HOME=str(self.home), USERPROFILE=str(self.home), DOTS=str(self.root),
                        TERM='xterm-256color', DOTS_COLOR='always', DOTS_ICONS='never',
                        PYTHONPATH=str(self.root / 'lib/dots'), COLUMNS='80',
                        BLASTOFF_HOME=str(self.home/'blastoff'), STARSHIP_CONFIG=str(self.home/'starship.toml'))
        for key in ('CONFIG','STATE','CACHE','DATA'):
            self.env['XDG_'+key+'_HOME'] = str(self.home/key.lower())
        self.env.update(APPDATA=str(self.home/'Roaming'), LOCALAPPDATA=str(self.home/'Local'))

    def call(self, path, args=(), *, mode='always', code=0):
        result = subprocess.run([sys.executable, '-B', str(self.root/path), *args], cwd=self.home,
                                env=dict(self.env, DOTS_COLOR=mode), capture_output=True, timeout=30)
        self.assertEqual(result.returncode, code, (path, args, result.stderr.decode(errors='replace')))
        return result

    def test_standalone_and_bundled_consumers_read_help_roles(self):
        for path,args in (
            ('lib/dots/todo_cli.py', ['--help']),
            ('lib/dots/fonts_cli.py', ['--help']),
            ('lib/dots/clipboard_cli.py', ['--help']),
            ('lib/dots/wttr/cli.py', ['--help']),
            ('lib/dots/bak_cli.py', ['--help']),
            ('lib/dots/link_cli.py', ['--help']),
            ('lib/dots/cleanup_cli.py', ['--help']),
            ('plugins/anodize/cli.py', ['--help']),
            ('plugins/blastoff/lib/blastoff.py', ['--color=always','--help']),
            ('plugins/pkgs/main.py', ['--help']),
        ):
            with self.subTest(path=path):
                result = self.call(path, args)
                self.assertIn(b'38;2;17;34;51m', result.stdout, path)
                self.assertIn(b'38;2;68;85;102m', result.stdout, path)
                self.assertIn(b'38;2;85;102;119m', result.stdout, path)
                self.assertNotIn(b'\\x1b[', result.stdout, path)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_error_usage_styles_stderr_without_touching_stdout(self):
        result = self.call('lib/dots/link_cli.py', ['--unknown'], code=2)
        self.assertEqual(result.stdout, b'')
        self.assertIn(b'38;2;17;34;51m', result.stderr)
        self.assertIn(b'38;2;68;85;102m', result.stderr)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_weather_browser_help_roles_and_plain_contract(self):
        plain = self.call('lib/dots/wttr/cli.py', ['browse', '--help'], mode='never')
        self.assertTrue(plain.stdout.startswith(
            b'Weather browser\n    Usage      wttr browse [LOCATION] [options] | dots wttr browse\n'))
        self.assertIn(b'Enter: open   Esc: back / close   Ctrl-C: cancel\n', plain.stdout)
        self.assertNotIn(b'\x1b', plain.stdout)
        self.assertEqual(plain.stderr, b'')
        colored = self.call('lib/dots/wttr/cli.py', ['browse', '--help'])
        for token, rgb in ((b'wttr', b'17;34;51'), (b'browse', b'34;51;68'),
                           (b'--query', b'68;85;102'), (b'LOCATION', b'85;102;119')):
            self.assertIn(b'38;2;' + rgb + b'm' + token, colored.stdout)
        self.assertEqual(colored.stderr, b'')
        self.assertEqual(list(self.home.iterdir()), [])

    def test_manual_usage_errors_preserve_status_stream_and_plain_bytes(self):
        fixture = self.root/'themes/fixture'
        fixture.mkdir(parents=True)
        (fixture/'colors.toml').write_text('foreground = "#eeeeee"\n')
        self.env['DOTS_THEME_SELECTION'] = 'fixture'
        for path, args, status, expected in (
            ('lib/dots/wttr/cli.py', ['get'], 2, b'wttr: usage: wttr get FIELD\n'),
            ('lib/dots/themes/theme_cli.py', ['bg', 'set'], 1,
             b'dots theme: Usage: bg set FILE [--lock-screen]\n'),
            ('lib/dots/themes/theme_cli.py', ['install'], 1,
             b'dots theme: Usage: theme install URL [--name ID]\n'),
            ('plugins/pkgs/main.py', ['completion'], 1,
             b'pkgs: Usage: pkgs completion SHELL [install|update|status|uninstall]\n'),
            ('plugins/pkgs/main.py', ['cache'], 1, b'pkgs: Usage: pkgs cache clear\n'),
            ('plugins/pkgs/main.py', ['info'], 1, b'pkgs: Usage: pkgs info NAME ...\n'),
            ('plugins/pkgs/main.py', ['cleanup', 'one', 'two'], 1,
             b'pkgs: Usage: pkgs cleanup [FILE] [--dry-run | --json]\n'),
        ):
            with self.subTest(path=path, args=args):
                plain = self.call(path, args, mode='never', code=status)
                colored = self.call(path, args, code=status)
                self.assertEqual(plain.stdout, b'')
                self.assertEqual(colored.stdout, b'')
                self.assertEqual(plain.stderr, expected)
                self.assertEqual(SGR.sub(b'', colored.stderr), expected)
                self.assertIn(b'38;2;17;34;51m', colored.stderr)
                self.assertIn(b'38;2;34;51;68m', colored.stderr)
        for args in (['info', '--json'], ['info', '--raw'], ['info', '--dry-run'],
                     ['info', '--color=never']):
            result = self.call('plugins/pkgs/main.py', args, code=1)
            self.assertEqual(result.stdout, b'')
            self.assertEqual(result.stderr, b'pkgs: Usage: pkgs info NAME ...\n')
        self.assertEqual(list(self.home.iterdir()), [])

    def test_wiki_directory_usage_error_preserves_diagnostic(self):
        plain = self.call('lib/dots/wiki_git.py', ['info', '-C'], mode='never', code=2)
        colored = self.call('lib/dots/wiki_git.py', ['info', '-C'], code=2)
        expected = (b'usage: wiki_git.py [-C DIRECTORY]\n'
                    b'wiki_git.py: error: argument -C/--directory: expected one argument\n')
        self.assertEqual(plain.stderr, expected)
        self.assertEqual(SGR.sub(b'', colored.stderr), expected)
        self.assertEqual(plain.stdout, b'')
        self.assertEqual(colored.stdout, b'')
        self.assertIn(b'38;2;17;34;51m', colored.stderr)
        self.assertIn(b'38;2;68;85;102m', colored.stderr)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_blastoff_json_help_remains_plain_under_forced_color(self):
        result = self.call('plugins/blastoff/lib/blastoff.py', ['--json','--help'])
        self.assertNotIn(b'\x1b', result.stdout)
        self.assertIn(b'Usage', result.stdout)

    def test_theme_help_keeps_addressed_palette_and_panel_background(self):
        for path in (self.root/'profiles').glob('*/colors.toml'):
            path.write_text('[apps.cli.help.command]\nfg = "blue"\n')
        palette = dict(foreground='#eeeeee', background='#101010', accent='#abcdef',
                       muted='#999999', blue='#123456', cyan='#345678', green='#456789',
                       yellow='#56789a', magenta='#6789ab')
        program = """import importlib.util,io,json,sys
from types import SimpleNamespace
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('panel',sys.argv[1]);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
palette=json.loads(sys.argv[2])
text='fixture — default\\n\\nUsage: fixture [FLAVOR] [ACTION | COLOR [FORMAT]]\\n\\nActions:\\n  set             Activate through Dots\\n\\nExamples:\\n  fixture set --dry-run\\n'
with patch.object(sys,'argv',['panel','--theme','fixture','--help-prog','fixture']), patch.object(sys,'stdin',io.StringIO(text)), patch.object(m.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=json.dumps({'colors':palette}),stderr='')):
    m.main()
"""
        result = subprocess.run([sys.executable,'-B','-c',program,
                                 str(self.root/'lib/dots/themes/presentation.py'),json.dumps(palette)],
                                cwd=self.home,env=self.env,capture_output=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn(b'38;2;18;52;86mset',result.stdout)
        self.assertIn(b'48;2;16;16;16m',result.stdout)
        self.assertIn(b'Activate through Dots',SGR.sub(b'',result.stdout))
        native_program = """import json,sys
from types import SimpleNamespace
sys.path.insert(0,sys.argv[1])
import theme_cli
palette=json.loads(sys.argv[2])
themes=SimpleNamespace(families=lambda:{'fixture':{'dark':'fixture-dark'}},
                       load=lambda _:dict(colors=palette,theme='fixture',flavor='dark'),
                       pick=lambda *args:'fixture-dark')
theme_cli.family(themes,'fixture',['--help'])
"""
        command = [sys.executable,'-B','-c',native_program,
                   str(self.root/'lib/dots/themes'),json.dumps(palette)]
        native = subprocess.run(command, cwd=self.home, env=self.env,
                                capture_output=True, timeout=15)
        self.assertEqual(native.returncode,0,native.stderr)
        for token, rgb in ((b'theme', b'18;52;86'), (b'fixture', b'103;137;171'),
                           (b'show', b'103;137;171'), (b'set', b'103;137;171'),
                           (b'dark', b'69;103;137'), (b'hex', b'69;103;137')):
            self.assertIn(b'38;2;' + rgb + b'm' + token, native.stdout)
        plain = subprocess.run(command, cwd=self.home, env=dict(self.env,DOTS_COLOR='never'),
                               capture_output=True, timeout=15)
        self.assertEqual(plain.returncode,0,plain.stderr)
        self.assertTrue(plain.stdout.startswith(b'Theme palette: fixture\n    Usage      dots theme fixture'))
        self.assertIn(b'    Flavors    dark\n',plain.stdout)
        self.assertIn(b'    Activate   set [--dry-run] [--background] [--verbose]\n',plain.stdout)
        self.assertNotIn(b'\x1b',plain.stdout)

    def test_plain_generic_help_bytes_and_literal_examples(self):
        plain = self.call('lib/dots/bak_cli.py', ['--help'], mode='never')
        colored = self.call('lib/dots/bak_cli.py', ['--help'])
        self.assertNotIn(b'\x1b', plain.stdout)
        self.assertEqual(SGR.sub(b'', colored.stdout), plain.stdout)
        literal = '$(touch injected)'
        program = ("import io; from help_adapters import HelpArgumentParser; "
                   "p=HelpArgumentParser(prog='fixture',epilog="+repr('Use fixture -- '+literal)+"); "
                   "p.add_argument('value',nargs='?'); p.print_help()")
        result = subprocess.run([sys.executable,'-B','-c',program], cwd=self.home,
                                env=self.env,capture_output=True,timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(literal.encode(), SGR.sub(b'',result.stdout))
        self.assertFalse((self.home/'injected').exists())


if __name__ == '__main__':
    unittest.main()

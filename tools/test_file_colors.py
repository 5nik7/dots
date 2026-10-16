#!/usr/bin/env python3
"""File styles, human panels and saved/published boundaries in owned roots."""
import importlib.util
import json
import os
import re
import subprocess
import unittest
from unittest.mock import patch
from test_themes import Themes, BASH, REPO

spec = importlib.util.spec_from_file_location('filecolors', REPO / 'lib/dots/themes/file-colors.py')
fc = importlib.util.module_from_spec(spec); spec.loader.exec_module(fc)

class FileColors(unittest.TestCase):
    setUp = Themes.setUp
    run_command = Themes.run_command
    dots = Themes.dots
    generation = Themes.generation

    def test_save_preview_publish_and_reset(self):
        self.dots('theme','set','catppuccin-mocha')
        original = self.generation()
        self.assertEqual(self.dots('theme','colors','type','dir','hex').stdout.strip(),'#89b4fa')
        self.dots('theme','colors','set','type','dir','--fg','red','--bold','false')
        self.assertEqual(self.generation(), original)
        self.assertEqual(self.dots('theme','colors','type','dir','hex').stdout.strip(),'#89b4fa')
        self.assertEqual(self.dots('theme','colors','type','dir','hex','--configured').stdout.strip(),'#f38ba8')
        self.assertIn('Source: Published snapshot', self.dots('theme','colors','type').stdout)
        self.assertIn('Source: Configured sources', self.dots('theme','colors','type','--configured').stdout)
        self.dots('theme','colors','set','type','dir','--fg','green','--theme','catppuccin-mocha','--apply')
        doc=json.loads(self.dots('theme','colors','export','json').stdout)
        self.assertEqual(doc['colors']['type']['dir'],'#a6e3a1')
        self.assertFalse(doc['styles']['type']['dir']['bold'])
        self.assertEqual(fc.parse_ls(doc['ls_colors'])['types']['di']['style']['fg'],'#a6e3a1')
        self.assertTrue((self.generation()/'colors.lua').is_file())
        if fc.shutil.which('lua'):
            code = 'local t=assert(loadfile(arg[1]))(); local v=assert(loadfile(arg[2]))(); v.validate(t); assert(t.colors.type.dir == "#a6e3a1"); assert(t.styles.type.dir.bold == false)'
            result=subprocess.run(['lua','-',str(self.generation()/'colors.lua'),str(REPO/'config/yazi/plugins/dots.yazi/theme.lua')], input=code, text=True, capture_output=True, env=self.env)
            self.assertEqual(result.returncode,0,result.stderr)
        self.dots('theme','colors','reset','type','dir','--theme','catppuccin-mocha')
        self.assertEqual(self.dots('theme','colors','type','dir','--configured').stdout.strip(),'#f38ba8')
        self.assertTrue(list((self.home/'state/dots').rglob('journal.json')) or list((self.home/'state/dots').rglob('*.json')))

    def test_git_styles_overrides_exports_and_old_snapshots(self):
        self.dots('theme', 'set', 'catppuccin-mocha')
        original = self.generation()
        before = json.loads(self.dots('theme', 'colors', 'export', 'json').stdout)
        self.assertEqual(before['colors']['git']['repo'], before['colors']['blue'])
        self.assertTrue(before['styles']['git']['repo']['bold'])
        self.assertEqual(len(before['styles']['git']), 17)
        self.assertIn('Git styles (17)', self.dots('theme', 'colors').stdout)
        self.assertTrue((original / 'git-styles.tsv').read_text().startswith('dots-git-styles\t1\n'))
        self.dots('theme', 'colors', 'set', 'git', 'untracked', '--fg', '#123456', '--bold', 'true')
        self.assertEqual(self.generation(), original)
        self.assertEqual(self.dots('theme', 'colors', 'git', 'untracked', '--configured').stdout, '#123456\n')
        self.assertNotEqual(self.dots('theme', 'colors', 'git', 'untracked').stdout, '#123456\n')
        self.dots('theme', 'colors', 'set', 'git', 'untracked', '--fg', '#abcdef', '--theme', 'catppuccin-mocha', '--apply')
        after = json.loads(self.dots('theme', 'colors', 'export', 'json').stdout)
        self.assertEqual(after['styles']['git']['untracked'], {'fg': '#abcdef', 'bold': True})
        self.assertEqual(before['ls_colors'], after['ls_colors'])
        for group in ('type', 'mime', 'extension'):
            self.assertEqual(before['styles'][group], after['styles'][group])
        for fmt, expected in [('hex', '#abcdef\n'), ('rgb', '171 205 239\n'),
                              ('ansi-24bit', '38;2;171;205;239\n'), ('esc', '\x1b[38;2;171;205;239m\n')]:
            self.assertEqual(self.dots('theme', 'colors', 'git', 'untracked', fmt, '--color=always').stdout, expected)
        self.assertIn('git', self.dots('theme', 'colors', 'export', 'lua').stdout)
        for shell in ('bash', 'zsh', 'fish'):
            for words, target in [(('gi',), 'git'), (('git', 'un'), 'untracked'),
                                  (('set', 'gi'), 'git'), (('set', 'git', 'un'), 'untracked')]:
                self.assertIn('candidate\t' + target + '\t', self.dots('__complete', shell, str(2 + len(words)),
                              '--', 'dots', 'theme', 'colors', *words).stdout)
        self.dots('theme', 'colors', 'reset', 'git', 'untracked', '--theme', 'catppuccin-mocha')
        self.assertEqual(self.dots('theme', 'colors', 'git', 'untracked', '--configured').stdout, '#123456\n')
        for key in ('bad/name', 'bad-key', '$(touch forbidden)'):
            self.dots('theme', 'colors', 'set', 'git', key, '--fg', 'red', code=1)
        # Model an existing schema-1 generation without the additive namespace.
        old = json.loads(json.dumps(before))
        for field in ('styles', 'colors', 'rules', 'provenance'):
            old[field].pop('git')
        (self.generation() / 'colors.json').write_text(json.dumps(old))
        self.assertIn('Git styles unavailable', self.dots('theme', 'colors').stdout)
        self.assertIn('theme refresh', self.dots('theme', 'colors', 'git', 'repo', code=1).stderr)
        self.assertEqual(self.dots('theme', 'colors', 'type', 'dir').stdout.strip(), before['colors']['type']['dir'])

    @unittest.skipUnless(fc.shutil.which('git') and os.name != 'nt', 'Native Git/PTYS required')
    def test_git_dark_light_publication_native_render(self):
        import fcntl
        import pty
        import struct
        import termios
        repo = self.home / 'repository 界'
        env = dict(self.env, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1',
                   DOTS_ICONS='never', DOTS_PROGRESS='never')
        self.run_command(['git', 'init', '--initial-branch=main', str(repo)], env=env)
        (repo / 'sample.png').write_text('fixture')
        for theme in ('catppuccin-mocha', 'catppuccin-latte'):
            self.dots('theme', 'set', theme)
            doc = json.loads(self.dots('theme', 'colors', 'export', 'json').stdout)
            for width in (40, 80, 120):
                master, slave = pty.openpty()
                try:
                    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 24, width, 0, 0))
                    result = subprocess.run([BASH, str(self.repo / 'lib/dots/git/main.bash'), 'status', '-C', str(repo)],
                        env=dict(env, DOTS_COLOR='auto', COLUMNS=str(width)), stdout=slave, stderr=subprocess.PIPE, timeout=20)
                    os.close(slave); slave = None
                    output = b''
                    while True:
                        try: chunk = os.read(master, 65536)
                        except OSError: break
                        if not chunk: break
                        output += chunk
                    self.assertEqual(result.returncode, 0, result.stderr)
                    text = output.decode()
                    for role in ('repo', 'branch', 'untracked'):
                        self.assertIn('\x1b[' + fc.sgr(doc['styles']['git'][role]) + 'm', text)
                    self.assertIn('sample.png', text)
                finally:
                    os.close(master)
                    if slave is not None: os.close(slave)

    def test_matching_mime_suffix_and_unsafe_data(self):
        self.dots('theme','colors','set','mime','image/*','--fg','red')
        self.dots('theme','colors','set','extension','.png','--fg','blue','--bg','background','--italic','true')
        path=self.home/'sample.png';path.write_text('file')
        args=('theme','colors','match',str(path),'--mime','image/png','--configured','--json')
        self.assertEqual(json.loads(self.dots(*args).stdout)['group'],'extension')
        path.chmod(0o700)
        self.assertEqual(json.loads(self.dots(*args).stdout)['key'],'executable')
        self.dots('theme','colors','set','type','dir','--fg','$(touch forbidden)',code=1)
        self.assertFalse((self.home/'forbidden').exists())
        config=self.home/'config/dots/file-colors.toml'
        original=config.read_bytes()
        self.dots('theme','colors','set','type','dir','--fg','#123456','--dry-run')
        self.assertEqual(config.read_bytes(),original)
        parsed=fc.parse_ls(r'di=0;38;2;1;2;3;48;5;123;1;22:*.a\:b=31:*.a\:b=32:ln=target')
        self.assertEqual(parsed['types']['di']['style'],{'fg':'#010203','bg':123,'bold':False,'dim':False})
        self.assertEqual([e['key'] for e in parsed['suffixes']],['*.a:b','*.a:b'])
        self.assertTrue(parsed['types']['ln']['style']['target'])

    def test_full_attributes_fallback_and_suffix_cases(self):
        with patch.dict(os.environ,self.env,clear=True), patch.object(fc,'ROOT',self.repo):
            palette = json.loads(fc.query('catppuccin-mocha'))
            doc = fc.resolve(palette, fc.query('dir','catppuccin-mocha').strip())
            doc['styles']['type']['dir'].update({k: True for k in fc.ATTRS})
            # Exercise installed Vivid grammar, then the no-Vivid basic path.
            generated = fc.generate(doc)
            self.assertTrue(all(generated['ls_rules']['types']['di']['style'][k] for k in fc.ATTRS))
            with patch.object(fc.shutil, 'which', return_value=None):
                basic = fc.generate(doc)
            self.assertEqual(basic['coverage'],'basic')
        entries=fc.parse_ls('*.txt=31:*.TXT=32')['suffixes']
        self.assertEqual(fc.suffix_match(entries,'a.txt')['sequence'],'31')
        self.assertEqual(fc.suffix_match(entries,'a.TXT')['sequence'],'32')
        self.assertIsNone(fc.suffix_match(entries,'a.Txt'))
        entries=fc.parse_ls('*.txt=31:*.TXT=31')['suffixes']
        self.assertEqual(fc.suffix_match(entries,'a.Txt')['sequence'],'31')

    def test_panels_and_data_boundaries(self):
        env={**self.env,'DOTS_COLOR':'always','COLUMNS':'40'}
        for flavor in ('night','day'):
            output=self.dots('theme','tokyonight',flavor,'--help',env=env).stdout
            self.assertIn('\x1b[48;2;',output)
            self.assertTrue(all(line.endswith('\x1b[0m') for line in output.splitlines()))
            plain=self.dots('theme','tokyonight',flavor,'--help','--color=none',env=env).stdout
            self.assertNotIn('\x1b',plain)
        active={**env,'DOTS_THEME_SELECTION':'tokyonight-day'}
        self.assertIn('tokyonight-day',self.dots('theme','tokyonight','--help',env=active).stdout)
        for extra in ({'DOTS_COLOR':'auto','NO_COLOR':'1'}, {'DOTS_COLOR':'auto','TERM':'dumb'}):
            self.assertNotIn('\x1b',self.dots('theme','tokyonight','--help',env={**env,**extra}).stdout)
        data=self.dots('theme','tokyonight','day','--color','blue','hex','--color=always',env=env).stdout
        self.assertNotIn('\x1b',data)
        self.assertRegex(data,r'^#[0-9a-fA-F]{6}\n$')
        self.assertNotIn('\x1b',self.dots('--color=none','theme','tokyonight','--help',env=env).stdout)
        for shell in ('bash','zsh','fish'):
            self.assertIn('candidate\tdir\t', self.dots('__complete',shell,'4','--','dots','theme','colors','type','di').stdout)
            self.assertIn('candidate\thex\t', self.dots('__complete',shell,'5','--','dots','theme','colors','type','dir','h').stdout)
        self.dots('commands','--check')

    def test_complete_overview_native_scope_and_no_vivid_dependency(self):
        env = {**self.env, 'DOTS_COLOR': 'always', 'COLUMNS': '120'}
        # Read-only overview queries must not launch the optional suffix generator.
        vivid = self.repo / 'bin/vivid'
        vivid.write_text('#!/bin/sh\necho unexpected-vivid >&2\nexit 77\n')
        vivid.chmod(0o755)
        args = ('--theme', 'catppuccin-mocha')
        data = json.loads(self.dots('theme','colors',*args,'--json',env=env).stdout)
        overview = self.dots('theme','colors',*args,env=env).stdout
        shown = self.dots('theme','show','catppuccin-mocha',env=env).stdout
        self.assertEqual(overview, shown)
        plain = re.sub(r'\x1b\[[0-9;:]*m', '', shown)
        for group in ('Named colors', 'Terminal colors', 'File types', 'MIME rules', 'Extension rules'):
            self.assertIn(group, plain)
        for name, value in data.items():
            if isinstance(value, str):
                self.assertRegex(plain, r'(?m)^  ' + re.escape(name) + r'\s+' + re.escape(value))
            else:
                for key in value:
                    self.assertIn(key, plain)
        self.assertLess(plain.index('color2 '), plain.index('color10 '))
        self.assertIn('Extension rules (0)', plain)
        self.assertIn('No entries.', plain)
        self.assertNotIn('{', plain)
        native = self.dots('theme','catppuccin','mocha','show',env=env).stdout
        self.assertIn('Native colors (26)', native)
        self.assertIn('rosewater', native)
        self.assertNotIn('File types', native)
        self.assertNotIn('Terminal colors', native)
        redirected = self.dots('theme','show','catppuccin-mocha').stdout
        self.assertIn('blue\t#89b4fa\n', redirected)
        self.assertNotIn('File types', redirected)
        self.assertNotIn('\x1b', redirected)

    def test_style_details_parse_and_machine_boundaries(self):
        env = {**self.env, 'DOTS_COLOR':'always', 'COLUMNS':'120'}
        args = ('--theme','catppuccin-mocha')
        rules = self.home / 'config/dots/file-colors.toml'
        rules.parent.mkdir(parents=True)
        rules.write_text('[extension.".lua"]\nfg="blue"\nbg="reset"\nbold=false\nhidden=true\n')
        style = self.dots('theme','colors','extension','.lua','--style',*args,env=env).stdout
        for text in ('Requested rule: .lua','Foreground','Background','reset','bold=false','hidden','Rule sources'):
            self.assertIn(text, style)
        self.assertNotIn('\x1b[8m', style)
        self.assertNotIn('{', style)
        path = self.home / 'test.lua'; path.write_text('')
        matched = self.dots('theme','colors','match',str(path),*args,env=env).stdout
        self.assertIn('Group: extension', matched)
        self.assertIn('Path: ', matched)
        for action in ((), ('type',), ('mime',), ('extension',), ('extension','.lua'), ('match',str(path))):
            uncolored = self.dots('theme','colors',*action,*args,'--json').stdout
            colored = self.dots('theme','colors',*action,*args,'--json',env=env).stdout
            self.assertEqual(uncolored, colored)
            json.loads(colored)
        for fmt in ('hex','rgb','ansi-24bit','esc'):
            self.assertEqual(self.dots('theme','colors','type','dir',fmt,*args).stdout,
                             self.dots('theme','colors','type','dir',fmt,*args,env=env).stdout)
        for fmt in ('lua','json','ls-colors'):
            self.assertEqual(self.dots('theme','colors','export',fmt,*args).stdout,
                             self.dots('theme','colors','export',fmt,*args,env=env).stdout)
        dry = ('theme','colors','set','type','dir','--fg','blue','--dry-run',*args)
        self.assertEqual(self.dots(*dry).stdout, self.dots(*dry,env=env).stdout)
        parsed_env = {**env,'LS_COLORS':'di=38;5;123:*.txt=31:*.txt=0:*.hide=8;5:bad=oops:*.界=38;2;1;2;3'}
        parsed = self.dots('theme','colors','parse','--env',*args,env=parsed_env).stdout
        for text in ('Filesystem rules','Suffix rules (4)','Invalid entries (1)','invalid SGR','index 123','Sequence'):
            self.assertIn(text, parsed)
        self.assertLess(parsed.index('31'), parsed.index('*.hide'))
        self.assertNotIn('\x1b[8m', parsed)
        self.assertNotIn('\x1b[5m', parsed)
        self.assertNotIn('{', parsed)
        raw = self.dots('theme','colors','parse','--env','--json',env=parsed_env).stdout
        self.assertEqual([r['sequence'] for r in json.loads(raw)['suffixes']], ['31','0','8;5','38;2;1;2;3'])
        self.assertNotIn('\x1b', raw)

    def test_color_views_terminal_widths_and_plain_policy(self):
        import errno
        import fcntl
        import pty
        import select
        import struct
        import termios
        import time
        import unicodedata
        for theme in ('catppuccin-mocha', 'catppuccin-latte'):
            for columns in (40, 80, 120):
                with self.subTest(theme=theme, columns=columns):
                    master, slave = pty.openpty()
                    try:
                        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 24, columns, 0, 0))
                        env = {**self.env, 'DOTS_COLOR':'auto'}
                        with subprocess.Popen([BASH,str(self.repo/'bin/dots'),'theme','show',theme],
                                              env=env, cwd=self.home, stdout=slave, stderr=subprocess.PIPE) as process:
                            os.close(slave); slave = None
                            output = b''
                            deadline = time.monotonic() + 30
                            while True:
                                if not select.select([master], [], [], max(0, deadline - time.monotonic()))[0]:
                                    process.kill()
                                    process.communicate()
                                    self.fail('Timed out waiting for theme preview PTY')
                                try: chunk = os.read(master, 65536)
                                except OSError as error:
                                    if error.errno == errno.EIO: break
                                    raise
                                if not chunk: break
                                output += chunk
                            _, errors = process.communicate(timeout=30)
                            self.assertEqual(process.returncode, 0, errors)
                    finally:
                        os.close(master)
                        if slave is not None: os.close(slave)
                    output = output.decode().replace('\r\n','\n')
                    self.assertIn('\x1b[48;2;', output)
                    self.assertIn('File types', output)
                    for line in output.splitlines():
                        self.assertTrue(line.endswith('\x1b[0m'))
                        text = re.sub(r'\x1b\[[0-9;:]*m','',line)
                        self.assertLessEqual(sum(0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in 'WF' else 1 for c in text), columns)
        for controls in ({'DOTS_COLOR':'never'}, {'DOTS_COLOR':'auto'},
                         {'DOTS_COLOR':'auto','NO_COLOR':'1'}, {'DOTS_COLOR':'auto','TERM':'dumb'}):
            output = self.dots('theme','colors','--theme','catppuccin-mocha',env={**self.env,**controls}).stdout
            self.assertNotIn('\x1b', output)
            self.assertIn('Named colors', output)
        output = self.dots('theme','colors','--theme','catppuccin-latte','--color=none',env={**self.env,'DOTS_COLOR':'always'}).stdout
        self.assertNotIn('\x1b', output)
        forced = self.dots('theme','colors','--theme','catppuccin-latte',env={**self.env,'DOTS_COLOR':'always','NO_COLOR':'1'}).stdout
        self.assertIn('\x1b[48;2;', forced)

    def test_long_unicode_rule_and_theme_independent_parse(self):
        name = '.' + '界e\u0301' * 25
        rules = self.home / 'config/dots/file-colors.toml'
        rules.parent.mkdir(parents=True)
        rules.write_text('[extension."' + name + '"]\nfg="blue"\n')
        env = {**self.env, 'COLUMNS':'40'}
        output = self.dots('theme','colors','extension','--theme','catppuccin-mocha',env=env).stdout
        name_lines = output.partition('Extension rules (1)')[2].partition('Foreground:')[0]
        self.assertEqual(''.join(line.strip() for line in name_lines.splitlines()), name)
        self.assertIn('Background: unset', output)
        # No selected/valid theme is required to inspect an arbitrary environment.
        env.update(DOTS_COLOR='always', LS_COLORS='di=31:*.bad=8:*.control\\e=32')
        output = self.dots('theme','colors','parse','--env','--theme','missing-theme',env=env).stdout
        self.assertIn('Filesystem rules (1)', output)
        self.assertIn('Suffix rules (2)', output)
        self.assertNotIn('\x1b', output)

def load_tests(loader, tests, pattern):
    return loader.loadTestsFromTestCase(FileColors)

if __name__=='__main__': unittest.main()

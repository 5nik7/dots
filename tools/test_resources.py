#!/usr/bin/env python3
"""Resource styling and Bash/Python parity in disposable roots; no live themes."""
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
LIB = REPO / 'lib/dots'
sys.path.insert(0, str(LIB))
from resources import Resources, suffix_rows, wrap, cells
sys.path.insert(0, str(LIB / 'files'))
from catalog import Presentation
spec = importlib.util.spec_from_file_location('filecolors', LIB / 'themes/file-colors.py')
fc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fc)
BASH = shutil.which('bash')
if os.name != 'nt':
    import fcntl
    import pty
    import termios


@unittest.skipUnless(BASH and os.name != 'nt', 'POSIX Bash resource acceptance')
class ResourcesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='dots-resources-')
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name) / 'home space ü'
        self.home.mkdir()
        self.theme = self.home / 'state/dots/current/theme'
        self.theme.mkdir(parents=True)
        self.env = dict(PATH=os.environ['PATH'], HOME=str(self.home), TERM='xterm-256color',
                        DOTS_COLOR='always', DOTS_ICONS='always', DOTS=str(REPO),
                        XDG_STATE_HOME=str(self.home / 'state'), XDG_CONFIG_HOME=str(self.home / 'config'),
                        XDG_DATA_HOME=str(self.home / 'data'), XDG_CACHE_HOME=str(self.home / 'cache'))
        if os.environ.get('LD_PRELOAD'):
            self.env['LD_PRELOAD'] = os.environ['LD_PRELOAD']
        self.doc = dict(schema=1, colors={}, styles=dict(
            type=dict(file={'fg':'#123456'}, dir={'fg':'#654321'}, symlink={'fg':'#112233'},
                      broken_symlink={'fg':'#ff0000'}, executable={'fg':'#00ff00'}),
            extension={'.special': {'fg':'#aabbcc'}},
            mime={'image/*': {'fg':'#998877'}, 'text/*': {'fg':'#123123'}}),
            provenance={'mime': {'image/*': {'fg':'custom'}, 'text/*': {'fg':str(REPO/'default/file-colors.toml')}}},
            ls_colors='di=34:*.txt=33:*.png=32:',
            ls_rules=fc.parse_ls('di=34:*.txt=33:*.png=32:'))
        fc.write_snapshot(self.doc, self.theme)

    def bash(self, path, kind='', mime='', **settings):
        env = dict(self.env, **settings)
        p = subprocess.run([BASH, '--noprofile', '--norc', '-c',
            'source "$DOTS/lib/dots/ui.bash"; dots::resource "$1" "$1" "$2" "$3"; printf "%s\\0%s" "$DOTS_RESOURCE_STYLE" "$DOTS_RESOURCE_TEXT"',
            'test', str(path), kind, mime], env=env, text=True, capture_output=True, timeout=10)
        self.assertEqual(p.returncode, 0, p.stderr)
        return p.stdout.split('\0')

    def test_published_rules_and_native_kind_parity(self):
        paths = [('file.special','file',''), ('file.png','file','image/png'),
                 ('file.txt','file','text/plain'), ('file.zz','file','text/plain'),
                 ('directory','dir',''), ('absent','missing','')]
        (self.home / 'directory').mkdir()
        for name, kind, mime in paths:
            path = self.home / name
            if kind == 'file': path.write_text('fixture')
            _, icon, code = Resources(self.theme).describe(path, mime=mime)
            style, text = self.bash(path, mime=mime)
            self.assertEqual(style, '\x1b[' + code + 'm')
            self.assertEqual(text, icon + ' ' + str(path))
        # Explicit extension > custom MIME > published suffix > default MIME.
        self.assertEqual(Resources(self.theme).describe(self.home/'file.special', mime='image/png')[2], '0;38;2;170;187;204')
        self.assertEqual(Resources(self.theme).describe(self.home/'file.png')[2], '0;38;2;153;136;119')
        self.assertEqual(Resources(self.theme).describe(self.home/'file.txt')[2], '33')

    def test_links_executable_and_planned_directory(self):
        regular = self.home/'run'; regular.write_text('fixture'); regular.chmod(0o700)
        for name, target in [('link', regular), ('broken', self.home/'no-target')]:
            (self.home/name).symlink_to(target)
        for name in ('link','broken','run'):
            path = self.home/name
            kind, icon, code = Resources(self.theme).describe(path)
            self.assertEqual(self.bash(path), ['\x1b['+code+'m', icon+' '+str(path)])
        self.assertEqual(self.bash(self.home/'planned', kind='dir')[0], '\x1b[0;38;2;101;67;33m')

    def test_old_absent_and_malformed_snapshots(self):
        path = self.home/'item.txt'
        for content in ('', 'dots-file-styles\t99\n', 'dots-file-styles\t1\ntype\tdir\t\x1b[31m\t-\n'):
            (self.theme/'file-styles.tsv').write_text(content)
            self.assertEqual(self.bash(path)[0], '\x1b[33m')
            self.assertEqual(Resources(self.theme).describe(path)[2], '33')
        (self.theme/'ls_colors').unlink()
        self.assertEqual(self.bash(path)[0], '\x1b[95m')
        self.assertEqual(Resources(self.theme).describe(path)[2], '95')

    def test_legacy_case_groups_and_disabled_executable_style(self):
        (self.theme/'file-styles.tsv').unlink()
        (self.theme/'ls_colors').write_text('*.aB=31:*.Ab=32:*.AB=32:ex=0:*.special=33:')
        for suffix in ('.ab','.aB','.Ab','.AB'):
            path = self.home/('item'+suffix)
            self.assertEqual(self.bash(path)[0], '\x1b['+Resources(self.theme).describe(path)[2]+'m')
        path=self.home/'run.special'; path.write_text('fixture'); path.chmod(0o700)
        self.assertEqual(self.bash(path)[0], '\x1b[33m')
        self.assertEqual(Resources(self.theme).describe(path)[2], '33')

    def test_literal_suffixes_case_collisions_and_injection(self):
        entries = [('.a','31'),('.A','32'),('.a','33'),('.b','34'),('.B','34')]
        rows = suffix_rows(entries, 'extension')
        (self.theme/'file-styles.tsv').write_text('dots-file-styles\t1\n'+''.join('\t'.join(row)+'\n' for row in rows))
        for name in ('item.a','item.A','item.b','item.B','$(touch forbidden).a'):
            path = self.home/name
            self.assertEqual(self.bash(path)[0], '\x1b['+Resources(self.theme).describe(path)[2]+'m')
        self.assertFalse((self.home/'forbidden').exists())
        path = self.home/'bad\x1b[31m\nname'
        style, text = self.bash(path)
        self.assertNotIn('\x1b', text)
        self.assertNotIn('\n', text)

    def test_color_and_icons_independent_and_plain_data(self):
        path = self.home/'x.png'
        self.assertEqual(self.bash(path, DOTS_COLOR='never')[0], '')
        self.assertTrue(self.bash(path, DOTS_COLOR='never')[1].startswith('󰈟 '))
        self.assertEqual(self.bash(path, DOTS_ICONS='never')[1], str(path))
        self.assertEqual(self.bash(path, DOTS_COLOR='auto', DOTS_ICONS='auto', NO_COLOR='1'), ['', str(path)])
        self.assertNotEqual(self.bash(path, NO_COLOR='1')[0], '')

    def test_python_details_wrap_without_losing_paths(self):
        path = self.home/('long ü  name '*12+'.png')
        with patch.dict(os.environ, self.env, clear=True):
            for width in (40,80,120):
                stream=io.StringIO(); ui=Presentation(stream); ui.width=width
                ui.resource_detail('Source', path)
                plain=re.sub(r'\x1b\[[0-9;]*m','',stream.getvalue())
                self.assertTrue(all(cells(line)<=width for line in plain.splitlines()))
                joined=''.join(line[15:] for line in plain.splitlines())
                self.assertEqual(joined, '󰈟 '+ui.path(path))
        self.assertEqual(''.join(wrap('wide 界  é end', 7)), 'wide 界  é end')

    def test_theme_panels_do_not_read_active_styles(self):
        spec=importlib.util.spec_from_file_location('themeview',LIB/'themes/presentation.py')
        mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        with patch.dict(os.environ,self.env,clear=True), patch.object(Resources,'rows',new_callable=unittest.mock.PropertyMock,side_effect=AssertionError('active styles read')):
            view=mod.ColorView({'foreground':'#ffffff','background':'#000000'})
            value=view.resource(self.home/'file.png')
            self.assertTrue(value.startswith('󰈟 '))
            self.assertNotIn('\x1b',value)

    def test_native_terminal_resource_rows(self):
        path = self.home / ('long 界 directory ' * 7 + 'item.png')
        for width in (40, 80, 120):
            with self.subTest(width=width):
                master, slave = pty.openpty()
                try:
                    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 24, width, 0, 0))
                    result = subprocess.run([BASH, '--noprofile', '--norc', '-c',
                        'source "$DOTS/lib/dots/ui.bash"; dots::resource_row Target "$1" "$1" file',
                        'test', str(path)], env=dict(self.env, COLUMNS=str(width)),
                        stdout=slave, stderr=slave, timeout=10)
                    os.close(slave); slave = None
                    output = b''
                    while True:
                        try: chunk = os.read(master, 65536)
                        except OSError: break
                        if not chunk: break
                        output += chunk
                    self.assertEqual(result.returncode, 0, output)
                    plain = re.sub(r'\x1b\[[0-9;]*m', '', output.decode()).replace('\r\n', '\n')
                    self.assertTrue(all(cells(line) <= width for line in plain.splitlines()), plain)
                    lines = plain.splitlines()
                    if width < 60:
                        self.assertEqual(lines.pop(0).strip(), 'Target')
                        indent = 6
                    else:
                        indent = 29
                    self.assertEqual(''.join(line[indent:] for line in lines), '󰈟 ' + str(path))
                finally:
                    os.close(master)
                    if slave is not None: os.close(slave)

    def test_plain_resource_does_not_read_styles(self):
        with patch.dict(os.environ, dict(self.env, DOTS_COLOR='never', DOTS_ICONS='never'), clear=True):
            with patch.object(Resources, 'describe', side_effect=AssertionError('styles read')):
                ui = Presentation(io.StringIO())
                self.assertEqual(ui.resource(self.home/'file'), '~/file')

    @unittest.skipUnless(shutil.which('git'), 'Git unavailable')
    def test_git_file_rows_and_undecorated_json(self):
        repo = self.home/'repository'
        repo.mkdir()
        env = dict(self.env, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1')
        subprocess.run(['git','init','--initial-branch=main',str(repo)], env=env,
                       check=True, capture_output=True)
        (repo/'sample.png').write_text('fixture')
        cmd = [BASH, str(REPO/'bin/dots'), 'git', 'status', '-C', str(repo)]
        human = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=15)
        self.assertEqual(human.returncode, 0, human.stderr)
        self.assertIn('\x1b[0;38;2;153;136;119m', human.stdout)
        self.assertIn('󰈟 sample.png', human.stdout)
        raw = subprocess.run(cmd+['--json'], env=env, capture_output=True, text=True, timeout=15)
        self.assertEqual(raw.returncode, 0, raw.stderr)
        self.assertNotIn('\x1b', raw.stdout + raw.stderr)
        self.assertEqual(json.loads(raw.stdout)['repositories'][0]['files'][0]['path'], 'sample.png')

if __name__ == '__main__': unittest.main()

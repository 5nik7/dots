#!/usr/bin/env python3
"""File styles, human panels and saved/published boundaries in owned roots."""
import importlib.util
import json
import os
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

def load_tests(loader, tests, pattern):
    return loader.loadTestsFromTestCase(FileColors)

if __name__=='__main__': unittest.main()

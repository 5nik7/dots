#!/usr/bin/env python3
"""FZF literal defaults and protected picker protocol projections."""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import unittest
from unittest.mock import patch
import test_profile_config as fixtures
from fzf_config import shell_options,picker_options,colors,validate_color
from config_values import Controls
from style_config import Styles
from theme_styles import snapshot,write_shell

class FzfConfig(unittest.TestCase):
    def setUp(self):
        fixtures.ProfileConfig.setUp(self)
        shutil.copytree(fixtures.ROOT/'default',self.root/'default')
        self.envpatch=patch.dict(os.environ,self.env,clear=True);self.envpatch.start();self.addCleanup(self.envpatch.stop)

    def test_literal_shell_and_safe_picker_projection(self):
        options=dict(default_opts=['--layout=reverse-list','--prompt=x $(touch BAD)','--read0','--print-query'],
                     bindings={'alt-z':'up','enter':'execute(touch BAD)','start':'reload(touch BAD)','alt-y':'execute(touch BAD)'},
                     preview='printf %s "literal; $(echo deliberately shell preview)"',preview_window='right:50%',colors={'bg+':'#123456','fg+':'accent:bold'})
        flags=shlex.split(shell_options(options))
        self.assertIn('--prompt=x $(touch BAD)',flags)
        self.assertIn('--preview='+options['preview'],flags)
        safe,ignored=picker_options(options)
        self.assertEqual(safe,['--layout=reverse-list','--bind=alt-z:up'])
        self.assertIn('binding:enter',ignored);self.assertIn('--print-query',ignored)
        self.assertEqual(colors(options,Styles(self.root,palette={'accent':'#aabbcc'})),'bg+:#123456,fg+:#aabbcc:bold')
        with self.assertRaises(ValueError):validate_color('red;touch BAD')

    def test_published_defaults_are_single_line_and_native_colors_parse(self):
        doc=snapshot({'accent':'#abcdef'},self.root)
        out=self.home/'generation';out.mkdir()
        (out/'fzf.sh').write_text('export _FZF_COLORS_="bg:-1"\n')
        write_shell(out,Styles(self.root),doc)
        rows=(out/'visual.tsv').read_text().splitlines()
        opts=next(row.split('\t',2)[2] for row in rows if row.startswith('env\tDOTS_THEME_FZF_OPTS\t'))
        self.assertEqual(shlex.split(opts),shlex.split(shell_options(Controls(self.root).values['apps']['fzf'])))
        if shutil.which('fzf'):
            for slot in doc['config']['apps']['fzf']['colors']:
                result=subprocess.run(['fzf','--filter=x','--color='+slot+(':'+ 'bold' if slot=='nth' else ':#123456')],input='x\n',text=True,capture_output=True,env=dict(self.env,FZF_DEFAULT_OPTS='',FZF_DEFAULT_OPTS_FILE=''))
                self.assertEqual(result.returncode,0,result.stderr)

if __name__=='__main__':unittest.main()

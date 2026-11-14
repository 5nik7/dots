#!/usr/bin/env python3
"""Progress appearance, Config activation and shell projections in owned roots."""
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_style_config as fixtures
from style_config import Styles, current
from progress_preferences import Appearance, GLYPHS, valid_symbol
from progress import Progress, terminal_columns


class ProgressStyles(unittest.TestCase):
    setUp = fixtures.StyleConfig.setUp
    run_config = fixtures.StyleConfig.run_config

    def test_config_roundtrip_validation_reset_and_next_invocation(self):
        for name, default in GLYPHS.items():
            self.assertEqual(self.run_config('get','icons.progress.bar.'+name).stdout,default+'\n')
        result=json.loads(self.run_config('set','icons.progress.bar.filled','=','--json').stdout)
        self.assertEqual(result['refresh']['consumers'],[dict(app='cli',status='next invocation')])
        for value in ('', 'xx', '界', '\u0301', '\x1b', '\u200b', '\ufe0f'):
            self.run_config('set','icons.progress.bar.filled',value,code=1)
        self.run_config('set','icons.progress.bar.left','')
        self.assertEqual(self.run_config('get','icons.progress.bar.left').stdout,'\n')
        self.run_config('unset','icons.progress.bar.filled')
        self.assertEqual(self.run_config('get','icons.progress.bar.filled').stdout,'━\n')
        result=json.loads(self.run_config('set','colors.apps.cli.progress.empty.fg','#123456','--json',native=True).stdout)
        self.assertEqual(result['refresh']['consumers'],[dict(app='cli',status='next invocation')])
        explained=json.loads(self.run_config('explain','icons.progress.bar.filled','--json').stdout)
        self.assertIn('=',explained['consumers'][0]['constraints']['examples'])
        self.assertEqual(explained['consumers'][0]['refresh'],'next invocation')
        self.assertFalse((Path(self.env['XDG_STATE_HOME'])/'dots/current/theme').exists())

    def test_appearance_inheritance_styles_ascii_and_exact_spans(self):
        parent=self.root/'profiles/linux';child=parent/'distros/progress';child.mkdir(parents=True)
        (child/'profile.json').write_text(json.dumps(dict(schema=1,id='linux/progress',extends=['linux'])))
        (parent/'icons.toml').write_text('[progress.bar]\nfilled="="\nleft="("\n')
        (child/'icons.toml').write_text('[progress.bar]\nright=""\nempty="·"\n')
        (child/'colors.toml').write_text('[apps.cli.progress.filled]\nfg="#123456"\nbg="#654321"\nitalic=true\n[apps.cli.progress.empty]\nfg="#abcdef"\n[apps.cli.progress.surround]\nfg="#fedcba"\n[apps.cli.progress.percentage]\nfg="#aabbcc"\n')
        with patch.dict(os.environ,dict(self.env,DOTS_PROFILE='linux/progress'),clear=True):
            from profile_config import context
            styles=Styles(self.root,context(self.root,'linux/progress'))
            appearance=Appearance(styles)
            self.assertEqual(appearance.symbols,dict(filled='=',empty='·',left='(',right=''))
            self.assertEqual(appearance.glyphs(False),dict(filled='=',empty='-',left='(',right=''))
            meter=Progress('activity');meter.appearance=appearance;meter.mode='both'
            meter.overall=(__import__('fractions').Fraction(1,2),'manager',1,2)
            row,cells=meter.lines(0,39,True,True)[0]
            self.assertEqual(cells,39)
            self.assertIn('\x1b[38;2;254;220;186m(\x1b[0m',row)
            self.assertIn('38;2;18;52;86',row)
            self.assertIn('48;2;101;67;33',row)
            self.assertIn('\x1b[1;38;2;170;187;204m50%\x1b[0m',row)
            self.assertIn('38;2;171;205;239m',row)

    def test_config_preview_and_batch_do_not_publish(self):
        import config_refresh
        from config_cli import StylePlan
        from profile_config import context
        with patch.dict(os.environ,self.env,clear=True):
            before=config_refresh.effective(self.root)
            colors=self.path.parent/'colors.toml'
            colors.write_text('[apps.cli.progress.empty]\nfg="#123456"\n[apps.pkgs.manager]\nfg="#abcdef"\n')
            with patch.object(config_refresh,'refresh',side_effect=AssertionError('theme publication')):
                self.assertEqual(config_refresh.after_save(self.root,before)['consumers'],[dict(app='cli',status='next invocation')])
            plan=StylePlan(self.root,context(self.root),'colors',False)
            plan.edit('apps.cli.progress.filled.fg','#778899')
            self.assertIn('no theme publication',config_refresh.preview_save(self.root,plan)['reason'])

    def test_completion_and_browser_have_only_consumed_controls(self):
        with patch.dict(os.environ,self.env,clear=True):
            from style_catalog import known_keys
            keys=known_keys('colors',Styles(self.root))
            self.assertIn('apps.cli.progress.filled.italic',keys)
            self.assertNotIn('icons.progress.bar.filled.fg',keys)
            from config_menu import Inventory
            inventory=Inventory(self.root,self.platform)
            # The browser and shell completion share supported Config keys.
            self.assertTrue(any('progress.bar.filled' in str(row) for row in inventory.rows))
        keys=subprocess.check_output([sys.executable,'-B',str(self.root/'lib/dots/profile_config.py'),'__keys'],env=self.env,text=True)
        self.assertIn('colors.apps.cli.progress.empty.fg\n',keys)
        self.assertIn('icons.progress.bar.filled\n',keys)
        self.assertIn('colors.apps.pkgs.manager.fg\n',keys)

    def test_actual_terminal_width_beats_stale_columns_and_symbol_validation(self):
        stream=io.StringIO()
        with patch('progress.os.get_terminal_size',return_value=os.terminal_size((40,20))):
            with patch.dict(os.environ,COLUMNS='120'):
                self.assertEqual(terminal_columns(sys.stderr),40)
        with patch.dict(os.environ,COLUMNS='80'):
            self.assertEqual(terminal_columns(stream),80)
        for value in ('━','#','=',' '): self.assertTrue(valid_symbol('filled',value))
        for value in ('界','\u0301','\u200b','\ufe0f','\u1160','\ud7b0','xx',''): self.assertFalse(valid_symbol('filled',value))

    def test_compiled_shell_preferences_invalidate_without_warm_python(self):
        import test_profiles
        fixture=test_profiles.Profiles();fixture.setUp();self.addCleanup(fixture.doCleanups);fixture.public()
        shutil.copytree(fixtures.ROOT/'default',fixture.root/'default')
        icons=fixture.root/'default/icons.toml';colors=fixture.root/'default/colors.toml'
        original_icons,original_colors=icons.read_text(),colors.read_text()
        for shell in ('bash','zsh'):
            if not shutil.which(shell): continue
            code='source "$DOTS/lib/dots/shell/init.'+shell+'"; printf "%s\\n%s" "${_DOTS_STYLE_ICONS[progress.bar.filled]}" "${_DOTS_STYLE_COLORS[progress.empty]}"'
            cold=fixture.run_shell(shell,code);self.assertEqual(cold.returncode,0,cold.stderr)
            self.assertTrue(cold.stdout.startswith('━\n'),cold.stdout)
            icons.write_text(original_icons.replace('filled = "━"','filled = "="'))
            colors.write_text(original_colors.replace('[apps.cli.progress.empty]\nfg = "colors.ui.muted.fg"','[apps.cli.progress.empty]\nfg = "#123456"'))
            changed=fixture.run_shell(shell,code);self.assertEqual(changed.returncode,0,changed.stderr)
            self.assertEqual(changed.stdout,'=\n38;2;18;52;86')
            shims=fixture.home/('progress-shims-'+shell);shims.mkdir()
            shim=shims/'python3';shim.write_text('#!'+shutil.which('sh')+'\nprintf UNEXPECTED_PYTHON >&2\nexit 99\n');shim.chmod(0o700)
            warm=fixture.run_shell(shell,code,PATH=str(shims)+os.pathsep+fixture.env['PATH'])
            self.assertEqual(warm.returncode,0,warm.stderr);self.assertEqual(warm.stdout,changed.stdout)
            self.assertNotIn('UNEXPECTED_PYTHON',warm.stderr)
            icons.write_text(original_icons);colors.write_text(original_colors)


if __name__=='__main__': unittest.main()

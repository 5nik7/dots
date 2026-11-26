"""The Windows group plans and restores each terminal edition in owned roots."""
from pathlib import Path
import os
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import test_font_workflows as fixtures
from fonts.commands import parser
from fonts.config import edit
from fonts.defaults import rows
from fonts.windows_terminals import WT_EDITIONS
from fonts_cli import plan_action


class WindowsTargets(unittest.TestCase):
    setUp = fixtures.Workflows.setUp
    library = fixtures.Workflows.library
    action = fixtures.Workflows.action
    seed = fixtures.Workflows.seed

    def test_setup_previews_saved_editions_and_explains_console_restore(self):
        from setup_fonts import Fonts
        target = 'windows-terminal-stable'
        path = Path(os.environ['LOCALAPPDATA']) / WT_EDITIONS[target] / 'settings.json'
        path.parent.mkdir(parents=True)
        path.write_text('{}')
        saved = dict(target=target, id='local:fixture', version='1', face='face.ttf',
                     variant='original', files={'face.ttf':'0'*64})
        applications = {target:saved, 'classic-console':dict(saved,target='classic-console')}
        args = SimpleNamespace(font_document=dict(schema=1,applications=applications),font_target=None,font_choices=[])
        installation = Mock(platform='windows')
        setup = Fonts(installation,args)
        self.assertEqual([row['target'] for row in setup.preview()],[target])
        self.assertIn('dots fonts restore classic-console',installation.item.call_args.kwargs['reason'])
        args.font_target = ['classic-console']
        with self.assertRaisesRegex(ValueError,'fonts restore classic-console'):
            setup.preview()

    def test_windows_terminal_overrides_and_inherited_profiles(self):
        original = ('\ufeff{// comment\r\n"profiles":{"defaults":{"font":{"face":"Old, Emoji","size":12}},'
                    '"list":[{"font":{"face":"Other","weight":700}},{"fontFace":"Legacy"},'
                    '{"name":"inherited","font":{"size":10}}]}}')
        expected = original.replace('Old, Emoji','New, Emoji').replace('"Other"','"New"').replace('"Legacy"','"New"')
        self.assertEqual(edit(original,'windows-terminal-preview','New'), expected)
        self.assertEqual(edit(expected,'windows-terminal-preview','New'), expected)

    def test_mintty_preserves_fallbacks_and_other_options(self):
        before = '# Comment\r\nFont=Old\r\nFontHeight=12\r\nFont1=Emoji\r\n'
        self.assertEqual(edit(before,'msys2-mintty','New'), before.replace('Font=Old','Font=New'))
        self.assertEqual(edit('', 'git-bash-mintty', 'New'), 'Font=New\n')

    def test_terminal_transaction_repeat_restore_drift_and_undo(self):
        from fontTools.ttLib import TTFont
        family = 'Fixture Nerd Font Mono'
        win32_family = 'Fixture NFM'
        def font_with_alias(path, family, **options):
            fixtures.font(path, family, **options)
            with TTFont(path) as font:
                names = font['name']
                for record in list(names.names):
                    if record.nameID == 1:
                        key = record.platformID, record.platEncID, record.langID
                        names.setName(family, 16, *key)
                        names.setName(win32_family, 1, *key)
                # GDI should use the Windows Unicode BMP name even with
                # other English legacy names in the same face.
                names.setName('Symbol family', 1, 3, 0, 0x409)
                names.setName('Full Unicode family', 1, 3, 10, 0x409)
                font.save(path)
        with patch('test_font_directories.font',side_effect=font_with_alias):
            identity, _ = self.seed(platform='windows')
        if os.name != 'nt':
            from fonts.operations import install_root
            base = install_root(self.library('windows'))
            def validate(spec):
                for path in (spec['before'],spec['after']):
                    if path is not None:
                        self.assertEqual(Path(path).parent, base)
            adapter = patch('font_registry.validate',side_effect=validate)
            adapter.start()
            self.addCleanup(adapter.stop)
        before = '{"profiles":{"defaults":{"font":{"face":"Old"}},"list":[{"font":{"face":"Other"}}]}}'
        files = []
        for target in ('windows-terminal-stable','windows-terminal-preview'):
            path = Path(os.environ['LOCALAPPDATA']) / WT_EDITIONS[target] / 'settings.json'
            path.parent.mkdir(parents=True)
            path.write_text(before)
            files.append(path)
        mintty = self.home / '.minttyrc'
        from app_paths import config_directory
        wezterm = config_directory('wezterm') / 'wezterm.lua'
        wezterm.parent.mkdir(parents=True)
        wezterm.write_text('config.font = wezterm.font("Old")\nconfig.font_size = 10\n')
        vscode = config_directory('vscode') / 'settings.json'
        vscode.parent.mkdir(parents=True)
        vscode.write_text('{"editor.fontFamily":"Keep","terminal.integrated.fontFamily":"Old, Emoji"}')
        # The two installations share their user home in this fixture.
        with patch.dict(sys.modules, {'fontTools': None, 'fontTools.ttLib': None}), \
             patch('fonts.windows_terminals.mintty_home',return_value=self.home), \
             patch('fonts_cli.system_fonts', return_value=[]), \
             patch('files.catalog.Catalog'), \
             patch('fonts.console.configure'):
            args = parser().parse_args(['set', identity, '--target', 'all-terminals','--dry-run'])
            with tempfile.TemporaryDirectory(dir=self.home/'tmp') as tmp:
                plan = plan_action(self.library('windows'),args,tmp)
                self.assertEqual(sum(op['path']==str(mintty) for op in plan.operations), 1)
                self.assertFalse(mintty.exists())
            selected = self.action('set',identity,'--target','all-terminals',platform='windows')
            self.assertTrue(all(path.read_text().count(family)==2 for path in files))
            self.assertEqual('Font=' + win32_family,mintty.read_text().strip())
            self.assertIn('font("' + family + '")',wezterm.read_text())
            self.assertIn('"editor.fontFamily":"Keep"',vscode.read_text())
            self.assertIn(family + ', Emoji',vscode.read_text())
            saved = {r['target'] for r in rows(self.library('windows'))['items']}
            self.assertTrue({'windows-terminal-stable','windows-terminal-preview','msys2-mintty','git-bash-mintty'} <= saved)
            self.assertEqual(self.action('set',identity,'--target','all-terminals',platform='windows')['status'],'unchanged')
            self.assertEqual(self.action('restore','windows-terminal-preview',platform='windows')['status'],'unchanged')
            old = files[1].read_bytes()
            files[1].write_text(before)
            with self.assertRaisesRegex(ValueError,'changed|drift'):
                self.action('restore','windows-terminal-preview',platform='windows')
            files[1].write_bytes(old)
            self.action('undo',selected['transaction'],platform='windows')
            self.assertTrue(all(path.read_text()==before for path in files))
            self.assertFalse(mintty.exists())


if __name__ == '__main__':
    unittest.main()

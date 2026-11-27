#!/usr/bin/env python3
"""Rainmeter variables rendering from the shared semantic palette."""
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import test_themes as fixture

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib/dots/themes'))
from palette_native import Themes

ROLES = ['background', 'dark_background', 'darker_background', 'lighter_background',
         'foreground', 'dark_foreground', 'light_foreground', 'muted', 'accent',
         'red', 'orange', 'yellow', 'green', 'cyan', 'blue', 'magenta',
         'bright_red', 'bright_yellow', 'bright_green', 'bright_cyan', 'bright_blue', 'bright_magenta',
         'bright_foreground', 'cursor',
         *[f'color{i}' for i in range(16)]]


def variables(text):
    lines = [line for line in text.splitlines() if line and not line.startswith(';')]
    assert lines[0] == '[Variables]', lines[0]
    return dict(line.split('=', 1) for line in lines[1:])


class RainmeterTheme(unittest.TestCase):
    setUp = fixture.Themes.setUp
    run_command = fixture.Themes.run_command
    dots = fixture.Themes.dots
    engine = fixture.Themes.engine
    shell = fixture.Themes.shell
    generation = fixture.Themes.generation
    wal_export = fixture.Themes.wal_export

    def render(self, identity):
        out = self.root / ('render-' + identity)
        out.mkdir(exist_ok=True)
        self.env.update(RENDER_THEME=identity, RENDER_OUTPUT=str(out))
        self.engine('dt_load "$RENDER_THEME" && dt_render "$RENDER_OUTPUT"')
        return out

    def test_all_palettes_and_native_renderer(self):
        self.wal_export()
        (self.home / 'cache/wal/colors.json').write_text(json.dumps({
            'special': {'background': '#102030', 'foreground': '#eeeeee', 'cursor': '#abcdef'},
            'colors': {f'color{i}': f'#{i+32:02x}{i+48:02x}{i+64:02x}' for i in range(16)}}))
        for identity in self.dots('theme', 'list').stdout.splitlines():
            with self.subTest(theme=identity):
                out = self.render(identity)
                raw = (out / 'rainmeter.inc').read_text()
                self.assertNotIn('{{', raw)
                values = variables(raw)
                colors = json.loads((out / 'colors.json').read_text())['colors']
                self.assertEqual(set(values), {'Dots_' + r for r in ['selection', *ROLES]} |
                                 {'Dots_theme_id', 'Dots_theme_family', 'Dots_theme_flavor'})
                self.assertEqual(values['Dots_theme_id'], identity)
                self.assertRegex(values['Dots_theme_family'], r'^[a-z0-9][a-z0-9_-]*$')
                self.assertRegex(values['Dots_theme_flavor'], r'^[a-z][a-z0-9_]*$')
                for role in ROLES:  # colors only (theme keys checked above)
                    self.assertRegex(values['Dots_' + role], r'^[0-9a-fA-F]{6}$')
                    self.assertEqual('#' + values['Dots_' + role], colors[role])
                native = self.root / ('native-' + identity); native.mkdir()
                with patch.dict(os.environ, self.env, clear=True):
                    Themes().render(identity, native)
                self.assertEqual(variables((native / 'rainmeter.inc').read_text()), values)


if __name__ == '__main__':
    unittest.main()

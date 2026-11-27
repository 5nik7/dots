"""Windows Terminal scheme merging and publication against disposable settings."""
import codecs
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

LIB = Path(__file__).resolve().parents[1] / 'lib/dots'
sys.path.insert(0, str(LIB))
from fonts.config import json_tree
from themes.wt_scheme import upsert_scheme, upsert_terminal_theme
from themes.wt_settings import discover_settings, sync_settings
from transactions import Store


SCHEME = {'name': 'dots', 'background': '#112233', 'foreground': '#aabbcc'}
THEME = {'name': 'dots', 'tab': {'background': '#112233'},
         'tabRow': {'background': '#445566'}, 'window': {'applicationTheme': 'dark'}}


class WindowsTerminalSettings(unittest.TestCase):
    def test_ui_theme_insert_update_and_select(self):
        for original in ('{}', '{"theme":"system","themes":[]}',
                         '{"themes":[{"name":"Other"}],"theme":{"light":"light","dark":"dark"}}'):
            with self.subTest(original=original):
                merged = upsert_terminal_theme(original, THEME)
                value = json_tree(merged).value
                self.assertEqual(value['theme'], 'dots')
                self.assertEqual(value['themes'][-1], THEME)
                self.assertEqual(value['themes'][:-1], json_tree(original).value.get('themes', []))
                self.assertEqual(upsert_terminal_theme(merged, THEME), merged)

    def test_ui_theme_merge_retains_nested_comments_and_customizations(self):
        original = ('\ufeff{\r\n  "theme": /* selected */ "Dots",\r\n'
                    '  "schemes": [{"name":"Dots"}], "themes": [{"name":"Dots",\r\n'
                    '    "custom": 1, "tab": {"color": "keep", "background": /* old */ "x"},\r\n'
                    '    "window": {"useMica": true,},\r\n  }],\r\n}\r\n')
        merged = upsert_terminal_theme(original, THEME)
        self.assertTrue(merged.startswith('\ufeff'))
        self.assertNotIn('\n', merged.replace('\r\n', ''))
        for exact in ('"theme": /* selected */ "dots"', '"schemes": [{"name":"Dots"}]',
                      '"color": "keep"', '"background": /* old */ "#112233"', '"useMica": true'):
            self.assertIn(exact, merged)
        theme = json_tree(merged[1:]).value['themes'][0]
        self.assertEqual(theme['name'], 'dots')
        self.assertEqual(theme['custom'], 1)
        self.assertEqual(theme['window'], dict(THEME['window'], useMica=True))
        self.assertEqual(upsert_terminal_theme(merged, THEME), merged)

    def test_refuse_ambiguous_ui_theme_or_selector(self):
        for original in ('{"themes":null}', '{"themes":[],"themes":[]}', '{"theme":"a","theme":"b"}',
                         '{"themes":[{"name":"dots"},{"name":"Dots"}]}',
                         '{"themes":[{"name":"dots","tab":{},"tab":{}}]}',
                         '{"themes":[{"name":"dots","window":{"applicationTheme":"x","applicationTheme":"dark"}}]}'):
            with self.subTest(original=original), self.assertRaises(ValueError):
                upsert_terminal_theme(original, THEME)

    def test_ui_theme_replaces_null_sections_and_numeric_boolean(self):
        original = ('{\r\n  "themes": [\r\n    {\r\n      "name": "dots",\r\n'
                    '      "tab": null,\r\n      "window": {"useMica": 1}\r\n    }\r\n  ]\r\n}')
        merged = upsert_terminal_theme(original, dict(THEME, window={'useMica': True}))
        self.assertIn('      "tab": {\r\n        "background": "#112233"\r\n      }', merged)
        self.assertIn('"useMica": true', merged)
        self.assertNotIn('\n', merged.replace('\r\n', ''))

    def test_insert_and_repeat(self):
        for original in ('{}', '{"profiles": {},}', '{"schemes": []}',
                         '{"schemes": [{"name":"User"}, // retain this comment\n]}'):
            with self.subTest(original=original):
                merged = upsert_scheme(original, SCHEME)
                schemes = json_tree(merged).value['schemes']
                self.assertEqual(schemes[-1], SCHEME)
                if 'User' in original:
                    self.assertEqual(schemes[0], {'name': 'User'})
                    self.assertIn('// retain this comment', merged)
                self.assertEqual(upsert_scheme(merged, SCHEME), merged)

    def test_scheme_preserves_terminal_color_spelling(self):
        original = '{"schemes":[{"name":"Dots","foreground":"#AABBCC"}]}'
        self.assertEqual(upsert_scheme(original, {'name': 'Dots', 'foreground': '#aabbcc'}), original)

    def test_update_preserves_profile_comments_and_spelling(self):
        original = ('\ufeff{\r\n  "profiles": {"defaults":{"colorScheme":"Dots"}},\r\n'
                    '  "schemes":[{"name":"Dots", "background": /* old */ "#ffffff",'
                    ' "custom": "https://example.com",}],\r\n}\r\n')
        merged = upsert_scheme(original, SCHEME)
        for exact in ('\ufeff{\r\n', '"profiles": {"defaults":{"colorScheme":"Dots"}}',
                      '"background": /* old */ "#112233"', '"custom": "https://example.com"'):
            self.assertIn(exact, merged)
        self.assertNotIn('\n', merged.replace('\r\n', ''))
        value = json_tree(merged[1:]).value['schemes'][0]
        self.assertEqual(value['name'], 'Dots')
        self.assertEqual(value['foreground'], SCHEME['foreground'])
        self.assertEqual(upsert_scheme(merged, SCHEME), merged)

    def test_refuse_invalid_or_ambiguous_edits(self):
        for original in ('{', '[]', '{"schemes":{}}', '{"schemes":[],"schemes":[]}',
                         '{"schemes":[{"name":"dots"},{"name":"Dots"}]}',
                         '{"schemes":[{"name":"dots","name":"User"}]}',
                         '{"schemes":[{"name":"dots","background":"x","background":"y"}]}'):
            with self.subTest(original=original), self.assertRaises(ValueError):
                upsert_scheme(original, SCHEME)

    def test_concurrent_edit_kept_while_other_target_updates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first, second = [root / edition / 'settings.json' for edition in ('Stable', 'Preview')]
            for path in (first, second):
                path.parent.mkdir()
                path.write_text('{}')
            apply = Store.apply
            def apply_after_user_edit(store, action, operations, *args, **kwargs):
                if operations[0]['path'] == str(first):
                    first.write_text('{"user":true}')
                return apply(store, action, operations, *args, **kwargs)
            with patch.object(Store, 'apply', apply_after_user_edit):
                results = sync_settings(SCHEME, paths=[first, second], state=root / 'state')
            self.assertEqual([row['status'] for row in results], ['error', 'updated'])
            self.assertEqual(first.read_text(), '{"user":true}')
            self.assertEqual(json_tree(second.read_text()).value['schemes'], [SCHEME])

    def test_discovery_sync_repeat_and_undo(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            local = root / 'Local'
            scoop = root / 'Scoop'
            extra = root / 'Portable/settings'
            env = dict(LOCALAPPDATA=str(local), USERPROFILE=str(root), SCOOP=str(scoop),
                       DOTS_APP_WT_CONFIG=str(extra), WT_SETTINGS_DIR=str(extra))
            targets = [local / 'Packages' / family / 'LocalState/settings.json' for family in
                       ('Microsoft.WindowsTerminal_8wekyb3d8bbwe', 'Microsoft.WindowsTerminalPreview_8wekyb3d8bbwe',
                        'Microsoft.WindowsTerminalCanary_8wekyb3d8bbwe')]
            targets.extend([local / 'Microsoft/Windows Terminal/settings.json', extra / 'settings.json',
                            scoop / 'persist/windows-terminal/settings/settings.json',
                            scoop / 'persist/windows-terminal-preview/settings/settings.json'])
            invalid = targets[1]
            before = codecs.BOM_UTF8 + b'{\r\n  "profiles": {},\r\n}\r\n'
            for path in targets:
                path.parent.mkdir(parents=True)
                path.write_bytes(b'{' if path == invalid else before)
            unrelated = root / 'Other/settings.json'
            unrelated.parent.mkdir()
            unrelated.write_bytes(b'{}')
            self.assertCountEqual(discover_settings(env=env), targets)
            state = root / 'state'
            def run(**options):
                return {Path(row['path']): row for row in sync_settings(SCHEME, env=env, state=state, **options)}
            preview = run(dry_run=True)
            for path in targets:
                self.assertEqual(preview[path]['status'], 'error' if path == invalid else 'would-update')
                self.assertEqual(path.read_bytes(), b'{' if path == invalid else before)
            self.assertFalse(state.exists())
            applied = run()
            repeated = run()
            store = Store(state)
            for path in targets:
                if path == invalid:
                    self.assertEqual(applied[path]['status'], 'error')
                    self.assertEqual(path.read_bytes(), b'{')
                    continue
                self.assertEqual(applied[path]['status'], 'updated')
                self.assertEqual(repeated[path]['status'], 'unchanged')
                self.assertTrue(path.read_bytes().startswith(codecs.BOM_UTF8))
                self.assertEqual(json_tree(path.read_bytes().decode('utf-8-sig')).value['schemes'], [SCHEME])
                operations, guards, catalogs = store.inverse(applied[path]['transaction'])
                store.apply('undo', operations, guards, catalogs=catalogs)
                self.assertEqual(path.read_bytes(), before)
            self.assertEqual(unrelated.read_bytes(), b'{}')


if __name__ == '__main__':
    unittest.main()

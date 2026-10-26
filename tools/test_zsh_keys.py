#!/usr/bin/env python3
"""Isolated personal ZLE setup, without loading the user's startup files."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
ZSH = shutil.which('zsh')
sys.path.insert(0, str(REPO / 'lib/dots'))
from keys.providers import shell_config, shell_dump


@unittest.skipUnless(ZSH, 'Zsh unavailable')
class Keys(unittest.TestCase):
    def run_zsh(self, code):
        with tempfile.TemporaryDirectory(prefix='dots-zle-unit-') as directory:
            env = dict(HOME=directory, ZDOTDIR=directory, DOTS=str(REPO),
                       PATH=os.environ['PATH'], TERM='xterm-256color')
            for key in ('LD_PRELOAD', 'PREFIX'):
                if key in os.environ:
                    env[key] = os.environ[key]
            result = subprocess.run([ZSH, '-dfc', code], cwd=directory, env=env,
                                    capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, '')
            return result.stdout

    def test_missing_plugins_and_reload_preserve_maps_and_hooks(self):
        output = self.run_zsh('''
source "$DOTS/shells/zsh/keys.zsh"
_dots_zsh_keys_finish
bindkey -M viins '^X' beginning-of-line
source "$DOTS/shells/zsh/keys.zsh"
_dots_zsh_keys_finish
bindkey -M viins '^X'
bindkey -M viins '^H'
bindkey -M viins '^?'
bindkey -M viins '^[[A'
bindkey -M vicmd k
print -r -- "callbacks:${#zvm_after_init_commands}:${#zvm_after_select_vi_mode_commands}:${#zvm_after_lazy_keybindings_commands}"
print -r -- "theme:${(M)#precmd_functions:#_dots_zsh_keys_theme}"
print -r -- "preexec:${(M)#preexec_functions:#_dots_zsh_keys_preexec}"
print -r -- "line:${widgets[zle-line-init]} keymap:${widgets[zle-keymap-select]}"
print -r -- "options:$KEYTIMEOUT:$VI_MODE_SET_CURSOR:$HISTORY_SUBSTRING_SEARCH_GLOBBING_FLAGS:$HISTORY_SUBSTRING_SEARCH_ENSURE_UNIQUE:${#HISTORY_SUBSTRING_SEARCH_FUZZY}:${#HISTORY_SUBSTRING_SEARCH_PREFIXED}:$HISTORY_SUBSTRING_SEARCH_HIGHLIGHT_TIMEOUT"
''')
        self.assertIn('"^X" beginning-of-line', output)
        self.assertIn('"^H" backward-delete-char', output)
        self.assertIn('"^?" backward-delete-char', output)
        self.assertNotIn('history-substring-search-', output)
        self.assertIn('callbacks:1:1:1', output)
        self.assertIn('theme:1', output)
        self.assertIn('preexec:1', output)
        self.assertIn('options:1:true:i:1:0:0:1', output)

    def test_widget_bindings_and_live_browser_records(self):
        output = self.run_zsh('''
source "$DOTS/shells/zsh/keys.zsh"
_stub() { :; }
for widget in history-substring-search-up history-substring-search-down fzf-history-widget zsh-system-clipboard-vicmd-vi-yank-eol zsh-system-clipboard-vicmd-vi-put-after; do
  zle -N "$widget" _stub
done
zmodload zsh/terminfo
_dots_zsh_keys_apply
bindkey -L -M viins
bindkey -L -M vicmd
''')
        rows = shell_dump('zsh', 'main', output)
        for mode in ('viins', 'vicmd'):
            for key in ('^[[A', '^[OA'):
                self.assertTrue(any(r['mode'] == mode and r['key'] == key and
                                    r['action'] == 'history-substring-search-up' for r in rows), (mode, key))
            for key in ('^[[B', '^[OB'):
                self.assertTrue(any(r['mode'] == mode and r['key'] == key and
                                    r['action'] == 'history-substring-search-down' for r in rows), (mode, key))
        for mode, key, action in (
                ('vicmd', 'k', 'history-substring-search-up'),
                ('vicmd', 'j', 'history-substring-search-down'),
                ('vicmd', 'Y', 'zsh-system-clipboard-vicmd-vi-yank-eol'),
                ('viins', '^V', 'zsh-system-clipboard-vicmd-vi-put-after'),
                ('viins', '^R', 'fzf-history-widget')):
            self.assertTrue(any((r['mode'], r['key'], r['action']) == (mode, key, action) for r in rows))

    def test_theme_refresh_and_fallback(self):
        output = self.run_zsh('''
source "$DOTS/shells/zsh/keys.zsh"
_dots_zsh_keys_theme
print -r -- "$HISTORY_SUBSTRING_SEARCH_HIGHLIGHT_FOUND|$HISTORY_SUBSTRING_SEARCH_HIGHLIGHT_NOT_FOUND"
typeset -A selection_foreground=(hex '#112233') selection_background=(hex '#ddeeff') error=(hex '#aa0000')
_dots_zsh_keys_theme
print -r -- "$HISTORY_SUBSTRING_SEARCH_HIGHLIGHT_FOUND|$HISTORY_SUBSTRING_SEARCH_HIGHLIGHT_NOT_FOUND"
selection_foreground[hex]='#eeeeee'; selection_background[hex]='#334455'; error[hex]='#ff7777'
_dots_zsh_keys_theme
print -r -- "$HISTORY_SUBSTRING_SEARCH_HIGHLIGHT_FOUND|$HISTORY_SUBSTRING_SEARCH_HIGHLIGHT_NOT_FOUND"
''')
        self.assertEqual(output.splitlines(), [
            'standout,bold|fg=red,bold',
            'fg=#112233,bg=#ddeeff,bold|fg=#aa0000,bold',
            'fg=#eeeeee,bg=#334455,bold|fg=#ff7777,bold'])

    def test_vi_plugin_owns_cursor_widgets(self):
        output = self.run_zsh('''
source "$DOTS/shells/zsh/keys.zsh"
zvm_init() { :; }
_plugin_cursor() { :; }
zle -N zle-line-init _plugin_cursor
zle -N zle-keymap-select _plugin_cursor
_dots_zsh_keys_finish
_dots_zsh_keys_finish
print -r -- "$widgets[zle-line-init]|$widgets[zle-keymap-select]"
''')
        self.assertEqual(output.strip(), 'user:_plugin_cursor|user:_plugin_cursor')

    def test_configured_browser_discovers_central_file(self):
        # An owned minimal checkout excludes profile/private configuration.
        with tempfile.TemporaryDirectory(prefix='dots-zle-browser-') as directory:
            root = Path(directory)
            (root / 'shells/zsh').mkdir(parents=True)
            shutil.copy2(REPO / 'shells/zsh/keys.zsh', root / 'shells/zsh/keys.zsh')
            (root / 'profiles').mkdir()
            from unittest.mock import patch
            env = dict(HOME=directory, DOTS=str(root), XDG_CONFIG_HOME=str(root / 'config'),
                       XDG_CACHE_HOME=str(root / 'cache'), XDG_STATE_HOME=str(root / 'state'),
                       XDG_DATA_HOME=str(root / 'data'))
            with patch.dict(os.environ, env, clear=True):
                rows = shell_config(root, 'zsh', [])
            self.assertTrue(any(r['key'] == 'k' and r['action'] == 'history-substring-search-up' for r in rows))
            self.assertTrue(all(r['evidence'] == 'configured' for r in rows))
        registry = json.loads((REPO / 'lib/dots/shell/environment.json').read_text())
        self.assertEqual(registry['observed']['KEYTIMEOUT'], 'shells/zsh/keys.zsh')
        self.assertEqual(registry['observed']['VI_MODE_SET_CURSOR'], 'shells/zsh/keys.zsh')


if __name__ == '__main__':
    unittest.main()

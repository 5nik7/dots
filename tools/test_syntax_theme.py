#!/usr/bin/env python3
"""Shared reference syntax, renderer parity and real bat colors in owned roots."""
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_themes as fixture

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib/dots/themes'))
from palette_native import Themes


def ansi_characters(raw):
    """Project actual foreground/style state onto text, excluding decorations."""
    characters, colors, attributes = [], [], []
    foreground, enabled, end = None, set(), 0
    for match in re.finditer(r'\x1b\[([0-9;]*)m', raw):
        text = raw[end:match.start()]
        characters.extend(text); colors.extend([foreground] * len(text))
        attributes.extend([frozenset(enabled)] * len(text))
        values = [int(v) if v else 0 for v in match[1].split(';')]
        i = 0
        while i < len(values):
            code = values[i]
            if code == 0: foreground = None; enabled.clear()
            elif code == 39: foreground = None
            elif code in (1, 3, 4, 9): enabled.add(code)
            elif code in (22, 23, 24, 29): enabled.discard({22:1, 23:3, 24:4, 29:9}[code])
            elif values[i:i+2] == [38, 2] and i+4 < len(values):
                foreground = '#%02x%02x%02x' % tuple(values[i+2:i+5]); i += 4
            elif values[i:i+2] == [48, 2]: i += 4
            i += 1
        end = match.end()
    text = raw[end:]
    characters.extend(text); colors.extend([foreground] * len(text))
    attributes.extend([frozenset(enabled)] * len(text))
    return ''.join(characters), colors, attributes


class SyntaxTheme(unittest.TestCase):
    setUp = fixture.Themes.setUp
    run_command = fixture.Themes.run_command
    dots = fixture.Themes.dots
    engine = fixture.Themes.engine
    shell = fixture.Themes.shell
    generation = fixture.Themes.generation
    wal_export = fixture.Themes.wal_export

    def render(self, identity, label='bash'):
        out = self.root / (label + '-' + identity); out.mkdir()
        self.env.update(RENDER_THEME=identity, RENDER_OUTPUT=str(out))
        self.engine('dt_load "$RENDER_THEME" && dt_render "$RENDER_OUTPUT"')
        return out

    def paired_render(self, identity, label=''):
        out = self.render(identity, 'bash' + label)
        native = self.root / ('native' + label + '-' + identity); native.mkdir()
        with patch.dict(os.environ, self.env, clear=True): Themes().render(identity, native)
        raw = (out/'bat.tmTheme').read_bytes()
        self.assertEqual(raw, (native/'bat.tmTheme').read_bytes())
        self.assertEqual(raw, (out/'yazi/tmtheme.xml').read_bytes())
        self.assertEqual(raw, (native/'yazi/tmtheme.xml').read_bytes())
        return out, plistlib.loads(raw)

    def test_reference_scope_order_styles_and_dynamic_colors(self):
        raw = (self.repo/'default/themed/bat.tmTheme.tpl').read_bytes()
        self.assertLessEqual(len(raw), 64 * 1024)
        doc = plistlib.loads(raw)
        self.assertEqual(set(doc), {'name', 'settings'})
        self.assertEqual(doc['name'], 'Dots')
        self.assertEqual(len(doc['settings']), 194)
        reference = doc['settings'][8:]
        contract = [(r.get('scope'), r['settings'].get('fontStyle')) for r in reference]
        digest = hashlib.sha256(json.dumps(contract, separators=(',', ':')).encode()).hexdigest()
        # Pinned upstream scope/style sequence, independently captured before adaptation.
        self.assertEqual(digest, '7664898468b4a791f6256844caf42e3e8cc1d0684259ff38c3c1417dcdacba8f')
        for row in doc['settings']:
            for key, value in row['settings'].items():
                if key != 'fontStyle': self.assertRegex(value, r'^\{\{ [a-z_0-9]+ \}\}$')
        settings = doc['settings'][0]['settings']
        self.assertEqual(settings['selection'], '{{ selection }}')
        self.assertEqual(settings['background'], '{{ background }}')
        self.assertEqual(settings['misspelling'], '{{ error }}')

    def test_all_palettes_bash_native_and_yazi(self):
        self.wal_export()
        (self.home/'cache/wal/colors.json').write_text(json.dumps({
            'special': {'background':'#102030', 'foreground':'#eeeeee', 'cursor':'#abcdef'},
            'colors': {f'color{i}':f'#{i+32:02x}{i+48:02x}{i+64:02x}' for i in range(16)}}))
        identities = self.dots('theme', 'list').stdout.splitlines()
        self.assertIn('catppuccin-latte', identities); self.assertIn('catppuccin-mocha', identities)
        for identity in identities:
            with self.subTest(theme=identity):
                out, doc = self.paired_render(identity)
                colors = json.loads((out/'colors.json').read_text())['colors']
                self.assertEqual(doc['settings'][0]['settings']['background'], colors['background'])
                for row in doc['settings']:
                    for key, value in row['settings'].items():
                        if key != 'fontStyle': self.assertRegex(value, r'^#[0-9a-fA-F]{6}$')

    def test_git_overrides_and_reset_on_both_renderers(self):
        rules = self.home/'config/dots/file-colors.toml'; rules.parent.mkdir(parents=True)
        rules.write_text('[git.added]\nfg="#123456"\n[git.deleted]\nfg="reset"\n[git.modified]\nfg="#654321"\n')
        for identity in ('catppuccin-mocha', 'catppuccin-latte'):
            out, doc = self.paired_render(identity)
            colors = json.loads((out/'colors.json').read_text())['colors']
            for row in doc['settings'][1:]:
                for scope, expected in [('markup.inserted', '#123456'), ('markup.deleted', colors['foreground']), ('markup.changed', '#654321')]:
                    if row.get('scope') in (scope, scope+'.diff'):
                        self.assertEqual(row['settings']['foreground'], expected)

    @unittest.skipUnless(shutil.which('bat'), 'bat unavailable')
    def test_real_bat_tokens_and_attributes_dark_light(self):
        samples = [
            ('Python', 'def greet(name):\n    # note\n    return "hello"\n', [('greet','blue'), ('note','muted'), ('hello','bright_green')]),
            ('Rust', 'fn greet() { let message = "hello"; }\n', [('greet','blue'), ('hello','bright_green')]),
            ('JavaScript', 'function greet() { return "hello"; }\n', [('greet','blue'), ('hello','bright_green')]),
            ('Bash', 'printf "hello"\n', [('hello','bright_green')]),
            ('JSON', '{"message": "hello", "count": 42}\n', [('hello','bright_green'), ('42','orange')]),
            ('YAML', 'message: "hello"\ncount: 42\n', [('hello','bright_green'), ('42','orange')]),
            ('Markdown', '# Heading\n\n**bold** and *italic*\n', [('bold','red'), ('italic','red')]),
            ('Diff', '--- a/file\n+++ b/file\n@@ -1 +1 @@\n-removed\n+added\n', [('removed','git.deleted'), ('added','git.added')]),
        ]
        for identity in ('catppuccin-mocha', 'catppuccin-latte'):
            self.dots('theme', 'set', identity)
            generation = self.generation()
            colors = json.loads((generation/'colors.json').read_text())['colors']
            env = dict(self.env, COLORTERM='truecolor', BAT_CONFIG_PATH=os.devnull,
                       BAT_CACHE_PATH=str(generation/'bat-cache'))
            for language, source, expected in samples:
                with self.subTest(theme=identity, language=language):
                    proc = subprocess.run(['bat','--paging=never','--style=plain','--color=always',
                        '--wrap=never','--italic-text=always','--theme=Dots','--language',language,'-'],
                        input=source,text=True,capture_output=True,env=env,timeout=15)
                    self.assertEqual(proc.returncode,0,proc.stderr)
                    text, foregrounds, styles = ansi_characters(proc.stdout)
                    self.assertEqual(text, source)
                    for word, role in expected:
                        value = colors['git'][role[4:]] if role.startswith('git.') else colors[role]
                        start = text.index(word)
                        self.assertEqual(set(foregrounds[start:start+len(word)]), {value}, (word, proc.stdout))
                    if language == 'Markdown':
                        self.assertIn(1, styles[text.index('bold')])
                        self.assertIn(3, styles[text.index('italic')])
                    if language == 'Python':
                        self.assertIn(3, styles[text.index('note')])
                        self.assertNotIn(3, styles[text.index('return')])
            before = (generation/'bat.tmTheme').read_bytes()
            raw = subprocess.run([fixture.BASH,str(self.repo/'bin/dots'),'theme','files','show','bat.tmTheme','--raw'],
                                 env=dict(self.env,DOTS_COLOR='always'),capture_output=True,timeout=15)
            self.assertEqual(raw.returncode,0,raw.stderr); self.assertEqual(raw.stdout,before)
            source = subprocess.run([fixture.BASH,str(self.repo/'bin/dots'),'theme','files','show','bat.tmTheme','--source','--raw'],
                                    env=self.env,capture_output=True,timeout=15)
            self.assertEqual(source.returncode,0,source.stderr)
            self.assertEqual(source.stdout,(self.repo/'default/themed/bat.tmTheme.tpl').read_bytes())

    @unittest.skipUnless(shutil.which('bat') and shutil.which('delta'), 'bat or delta unavailable')
    def test_delta_uses_generation_syntax_cache(self):
        normal_cache=self.home/'cache/bat'; normal_cache.mkdir(parents=True)
        sentinel=normal_cache/'sentinel'; sentinel.write_text('keep')
        self.dots('theme','set','nord'); generation=self.generation()
        env=dict(self.env,COLORTERM='truecolor',XDG_CACHE_HOME=str(generation/'delta-cache'))
        source='diff --git a/example.py b/example.py\n--- a/example.py\n+++ b/example.py\n@@ -1 +1 @@\n-print("before")\n+print("after")\n'
        result=subprocess.run(['delta','--no-gitconfig','--syntax-theme','Dots','--true-color','always',
            '--paging','never','--minus-style','syntax','--plus-style','syntax',
            '--minus-emph-style','syntax','--plus-emph-style','syntax',
            '--file-style','omit','--hunk-header-style','omit'],input=source,text=True,
            capture_output=True,env=env,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr); self.assertEqual(result.stderr,'')
        text,colors,_=ansi_characters(result.stdout)
        green=json.loads((generation/'colors.json').read_text())['colors']['bright_green']
        for word in ('before','after'):
            start=text.index(word)
            self.assertEqual(set(colors[start:start+len(word)]),{green})
        self.assertEqual(sentinel.read_text(),'keep')

    def test_template_fingerprint_and_refresh_idempotence(self):
        self.dots('theme','set','nord'); first=self.generation()
        with patch.dict(os.environ,self.env,clear=True): before=Themes().fingerprint('nord')
        template=self.repo/'default/themed/bat.tmTheme.tpl'
        template.write_text(template.read_text()+'<!-- isolated template edit -->\n')
        with patch.dict(os.environ,self.env,clear=True): self.assertNotEqual(Themes().fingerprint('nord'),before)
        self.dots('theme','refresh'); second=self.generation()
        self.assertNotEqual(first,second)
        self.assertIn(b'isolated template edit',(second/'bat.tmTheme').read_bytes())
        self.dots('theme','refresh'); self.assertEqual(self.generation(),second)


if __name__ == '__main__': unittest.main(defaultTest='SyntaxTheme', verbosity=2)

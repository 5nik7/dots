#!/usr/bin/env python3
"""Vivid and native FSH acceptance in disposable home/config/state/cache roots."""
import os
import re
from pathlib import Path
import shutil
import unittest

import test_themes as old

VIVID = shutil.which('vivid')
FSH = Path(os.environ['HOME']) / '.local/share/zinit/plugins/zdharma-continuum---fast-syntax-highlighting'


class FileThemes(old.Themes):
    def test_refresh_repairs_missing_outputs_and_active_pointer(self):
        user=self.home/'config/dots/themed'
        user.mkdir(parents=True)
        (user/'extra.conf.tpl').write_text('accent={{ accent }}\n')
        self.dots('theme','set','nord')
        for relative in ('fsh.ini','colors.json','yazi/tmtheme.xml','extra.conf','fingerprint'):
            with self.subTest(artifact=relative):
                previous=self.generation()
                (previous/relative).unlink()
                self.dots('theme','refresh')
                current=self.generation()
                self.assertNotEqual(previous,current)
                self.assertTrue((current/relative).is_file())
                self.assertTrue(previous.is_dir())
                self.assertFalse((previous/relative).exists())
        active=self.home/'state/dots/current/theme'
        active.unlink()
        self.dots('theme','refresh')
        self.assertTrue(active.is_symlink())
        self.assertEqual(active.resolve(),self.generation())
        current=self.generation()
        self.dots('theme','refresh')
        self.assertEqual(current,self.generation())

    def test_refresh_replaces_generation_with_symlinked_artifact(self):
        self.dots('theme','set','nord')
        previous=self.generation()
        foreign=self.home/'foreign.ini'; foreign.write_text('retain me\n')
        artifact=previous/'fsh.ini'; artifact.unlink(); artifact.symlink_to(foreign)
        self.dots('theme','refresh')
        self.assertNotEqual(previous,self.generation())
        self.assertFalse((self.generation()/'fsh.ini').is_symlink())
        self.assertEqual(foreign.read_text(),'retain me\n')
        self.assertTrue(artifact.is_symlink())

    @unittest.skipUnless(old.ZSH and FSH.is_dir(), 'Installed FSH and Zsh required')
    def test_native_fsh_cold_cache_and_actionable_failure_messages(self):
        self.install_fsh()
        self.env.pop('FAST_WORK_DIR')
        shutil.rmtree(self.home/'cache/fsh')
        self.dots('theme','set','nord')
        setup='''curl() { return 1; }; wget() { return 1; }
source "$HOME/fsh-plugin/fast-syntax-highlighting.plugin.zsh"
source "$DOTS/lib/dots/themes/shell.bash"
'''
        cold=self.shell(setup+'''set_theme || exit 1
[[ $FAST_THEME_NAME == dots && -s $FAST_WORK_DIR/current_theme.zsh ]] || exit 2
fast-theme --show
''',old.ZSH)
        self.assertEqual(cold.stderr,'')
        self.assertEqual(cold.stdout.count('dots'),2)
        missing=self.shell(setup+'''set_theme || exit 1
before=${FAST_HIGHLIGHT_STYLES[dotscommand]}
rm "$_DOTS_THEME_FSH_FILE"
set_theme
set_theme
[[ ${FAST_HIGHLIGHT_STYLES[dotscommand]} == "$before" ]] || exit 2
''',old.ZSH)
        self.assertEqual(missing.stdout,'')
        self.assertEqual(missing.stderr.count('generated FSH theme is unavailable'),1)
        self.assertIn('fsh.ini',missing.stderr)
        self.assertIn('dots init --setup',missing.stderr)
        self.assertNotIn('\x1b',missing.stderr)
        self.dots('theme','refresh')
        failed=self.shell(setup+'''set_theme || exit 1
before=${FAST_HIGHLIGHT_STYLES[dotscommand]}
saved=$(<"$FAST_WORK_DIR/current_theme.zsh")
print '[base]\\nunknown-token = not-a-color' > "$HOME/bad.ini"
_DOTS_THEME_FSH_FILE=$HOME/bad.ini
_dots_fsh_apply && exit 2
[[ $(<"$FAST_WORK_DIR/current_theme.zsh") == "$saved" ]] || exit 3
[[ ${FAST_HIGHLIGHT_STYLES[dotscommand]} == "$before" ]] || exit 4
_DOTS_THEME_FSH_FILE=$_DOTS_THEME_LOADED_DIR/fsh.ini
rm "$FAST_WORK_DIR/current_theme.zsh"
mkdir "$FAST_WORK_DIR/current_theme.zsh"
_dots_fsh_apply && exit 5
true
''',old.ZSH)
        self.assertIn('could not compile the FSH theme',failed.stderr)
        self.assertIn('dots theme refresh',failed.stderr)
        self.assertIn('could not save the FSH startup theme',failed.stderr)
        self.assertIn('FAST_WORK_DIR',failed.stderr)

    def test_fixture_excludes_generated_connector_without_following_it(self):
        source = self.repo / 'config/vivid'
        (source / 'themes').mkdir(parents=True)
        (source / 'themes/dots.yml').symlink_to(self.home / 'private-state.yml')
        (source / 'themes/personal.yml').write_text('public input\n')
        target = self.root / 'public-copy'
        old.copy_public_tree(source, target, repo=self.repo, fixture=target,
                             exclude=('themes/dots.yml',))
        self.assertFalse((target / 'themes/dots.yml').is_symlink())
        self.assertEqual((target / 'themes/personal.yml').read_text(), 'public input\n')
        (source / 'themes/foreign.yml').symlink_to(self.home / 'private-state.yml')
        with self.assertRaises(ValueError):
            old.copy_public_tree(source, self.root / 'refused-copy', repo=self.repo,
                                 fixture=target, exclude=('themes/dots.yml',))

    def install_zsh(self):
        shutil.copytree(old.REPO / 'shells/zsh', self.repo / 'shells/zsh')

    def install_fsh(self):
        self.install_zsh()
        plugin = self.home / 'fsh-plugin'
        shutil.copytree(FSH, plugin, ignore=shutil.ignore_patterns('.git', '*.zwc', '*_theme.zsh', 'theme_overlay.zsh'))
        # Prevent the plugin's optional secondary-theme network fetch in the
        # actual resolved work directory, not merely the plugin checkout.
        work = Path(self.env.get('FAST_WORK_DIR', str(self.home / 'cache/fsh')))
        work.mkdir(parents=True, exist_ok=True)
        (work / 'secondary_theme.zsh').touch()
        self.env['FAST_WORK_DIR'] = str(work)
        return '''source "$HOME/fsh-plugin/fast-syntax-highlighting.plugin.zsh"
source "$DOTS/shells/zsh/core/cache.zsh"
source "$DOTS/lib/dots/themes/shell.bash"
'''

    def test_connectors_overrides_and_recovery(self):
        config = self.home / 'config'
        paths = [config / 'vivid/themes/dots.yml', config / 'fsh/dots.ini']
        for path in paths:
            path.parent.mkdir(parents=True)
            path.write_text('previous\n')
        for color in ('never', 'always'):
            preview = self.dots('theme', 'set', 'nord', '--dry-run',
                                env=dict(self.env, DOTS_COLOR=color)).stdout
            for path in paths:
                self.assertIn(str(path.relative_to(self.home)), preview)
                self.assertEqual(path.read_text(), 'previous\n')
        self.dots('theme', 'set', 'nord')
        first = self.generation()
        for path, name in zip(paths, ('vivid.yml', 'fsh.ini')):
            self.assertEqual(path.readlink(), self.home / 'state/dots/current/theme' / name)
        self.dots('theme', 'refresh')
        self.assertEqual(self.generation(), first)
        user = config / 'dots/themed'
        user.mkdir(parents=True)
        for name in ('vivid.yml', 'fsh.ini'):
            template = (self.repo / 'default/themed' / (name + '.tpl')).read_text()
            override = (template + '# user Vivid override\n' if name == 'vivid.yml'
                        else template.replace('{{ blue', '{{ magenta'))
            (user / (name + '.tpl')).write_text(override)
        self.dots('theme', 'refresh')
        second = self.generation()
        for name in ('vivid.yml', 'fsh.ini'):
            self.assertNotEqual((first / name).read_bytes(), (second / name).read_bytes())
            (self.repo / 'themes/nord' / name).write_bytes((first / name).read_bytes())
        self.dots('theme', 'refresh')
        third = self.generation()
        for name in ('vivid.yml', 'fsh.ini'):
            self.assertEqual((third / name).read_bytes(), (first / name).read_bytes())
        # A connector conflict refuses publication without replacing active data.
        paths[0].unlink()
        paths[0].mkdir()
        self.dots('theme', 'refresh', code=1)
        self.assertEqual(self.generation(), third)
        paths[0].rmdir()
        paths[0].symlink_to(self.home / 'state/dots/current/theme/vivid.yml')
        for generation in (third, second, first):
            self.engine('dt_restore "' + str(generation) + '"')
        for path in paths:
            self.assertFalse(path.is_symlink())
            self.assertEqual(path.read_text(), 'previous\n')

    def test_optional_directories_broken_link_staging_and_drift(self):
        self.dots('theme', 'set', 'nord')
        config = self.home / 'config'
        self.assertFalse((config / 'vivid').exists())
        self.assertFalse((config / 'fsh').exists())
        for directory, leaf, artifact in [('vivid/themes', 'dots.yml', 'vivid.yml'),
                                           ('fsh', 'dots.ini', 'fsh.ini')]:
            app = config / directory
            app.mkdir(parents=True)
            target = app / leaf
            prior = app / '-missing ü theme'
            target.symlink_to(prior)
            self.dots('theme', 'refresh')
            first = self.generation()
            target.unlink()
            target.symlink_to(prior)
            staging = Path(str(target) + '.dots-theme-new')
            staging.symlink_to(self.home / 'state/dots/current/theme' / artifact)
            (first / 'status').write_text('prepared\n')
            self.dots('theme', 'refresh')
            self.assertEqual((first / 'status').read_text(), 'rolled-back\n')
            self.assertFalse(staging.is_symlink())
            second = self.generation()
            self.engine('dt_restore "' + str(second) + '"')
            self.assertEqual(target.readlink(), prior)
            self.dots('theme', 'refresh')
            third = self.generation()
            target.unlink()
            target.write_text('user change\n')
            self.engine('dt_restore "' + str(third) + '"', code=1)
            self.assertEqual(target.read_text(), 'user change\n')
            # Restore the expected link only inside this owned recovery fixture.
            target.unlink()
            target.symlink_to(self.home / 'state/dots/current/theme' / artifact)
            self.engine('dt_restore "' + str(third) + '"')

    @unittest.skipUnless(VIVID, 'Vivid unavailable')
    def test_native_vivid_palettes_and_shells(self):
        self.install_zsh()
        for theme in ('catppuccin-mocha', 'catppuccin-latte', 'nord'):
            self.dots('theme', 'set', theme)
            generation = self.generation()
            output = self.run_command([VIVID, 'generate', str(generation / 'vivid.yml')]).stdout.strip()
            rules = dict(item.split('=', 1) for item in output.split(':') if '=' in item)
            for kind, role in [('di', 'blue'), ('ex', 'green'), ('ln', 'cyan'), ('or', 'error'),
                               ('*.zip', 'yellow'), ('*.jpg', 'magenta'), ('*.py', 'yellow')]:
                color = self.dots('theme', 'color', role, 'rgb', '--theme', theme).stdout.strip()
                self.assertIn('38;2;' + color.replace(' ', ';'), rules[kind])
            for shell in filter(None, (old.BASH, old.ZSH)):
                body = 'source "$DOTS/lib/dots/themes/shell.bash"\n'
                if shell == old.ZSH:
                    body += 'source "$DOTS/shells/zsh/core/cache.zsh"\n'
                body += 'set_theme || exit\nprintf "%s" "$LS_COLORS"'
                self.assertEqual(self.shell(body, shell).stdout, (generation / "ls_colors").read_text().strip())

    @unittest.skipUnless(old.ZSH, 'Zsh unavailable')
    def test_vivid_cache_tracks_published_file_and_failures(self):
        self.install_zsh()
        exe = self.repo / 'bin/vivid'
        exe.write_text('#!' + old.BASH + '\nprintf "run\\n" >> "$HOME/vivid.calls"\n'
                       '[[ ! -e $HOME/fail ]] || exit 1\nprintf "di=38;2;1;2;3"\n')
        exe.chmod(0o700)
        self.dots('theme','set','nord')
        first = self.generation()
        self.shell('source "$DOTS/lib/dots/themes/shell.bash"; set_theme; set_theme', old.ZSH)
        self.assertEqual((self.home/'vivid.calls').read_text(), 'run\n')
        self.dots('theme','set','catppuccin-latte')
        self.assertNotEqual(self.generation(), first)
        self.assertEqual((self.home/'vivid.calls').read_text(), 'run\nrun\n')
        current = self.generation()
        (self.home/'fail').touch()
        rules = self.repo/'default/file-colors.toml'
        rules.write_text(rules.read_text()+'\n# Force regeneration for the failure probe\n')
        self.dots('theme','refresh',code=1)
        self.assertEqual(self.generation(), current)
        self.assertEqual(self.shell('source "$DOTS/lib/dots/themes/shell.bash"; set_theme; printf "%s" "$LS_COLORS"',old.ZSH).stdout,
                         (current/'ls_colors').read_text().strip())

    def test_no_vivid_fallback_preserves_custom_entries(self):
        # Session-only compatibility initialization retains inherited entries.
        exe = self.repo / 'bin/vivid'
        exe.write_text('#!' + old.BASH + '\nexit 1\n')
        exe.chmod(0o700)
        self.shell('''LS_COLORS='*.custom=01;31'
source "$DOTS/lib/dots/themes/shell.bash"
set_theme nord || exit 1
[[ $LS_COLORS == '*.custom=01;31:'"$DOTS_THEME_LS_COLORS" ]] || exit 2
before=$LS_COLORS
set_theme nord
[[ $LS_COLORS == "$before" ]] || exit 3
''')
        self.engine('''dt_load catppuccin mocha || exit 1
DT_SEMANTIC=()
output=$(dt_emit_init bash) || exit 2
eval "$output"
[[ $DOTS_THEME_LS_COLORS == *'or=38;2;243;139;168'* ]] || exit 3
''')

    @unittest.skipUnless(old.ZSH and FSH.is_dir(), 'Installed FSH and Zsh required')
    def test_native_fsh_highlighting_refresh_and_session_fallback(self):
        setup = self.install_fsh()
        self.dots('theme', 'set', 'nord')
        # Native plugin writes must remain in our cache, never in its own copy.
        before = {p.name: p.read_bytes() for p in (self.home / 'fsh-plugin').glob('*theme.zsh*')}
        self.shell(setup + '''set_theme || exit 1
[[ $FAST_THEME_NAME == dots && -z ${FAST_HIGHLIGHT_STYLES[dotssecondary]} ]] || exit 2
first=${FAST_HIGHLIGHT_STYLES[dotscommand]}
[[ $first == fg=* && ${FAST_HIGHLIGHT_STYLES[dotspath-to-dir]} != "$first" ]] || exit 3
PREBUFFER=''
local -a reply
-fast-highlight-process '' 'echo $(echo hello) ./missing' 0
[[ ${(j: :)reply} == *"$first"* ]] || exit 4
print -rl -- "${reply[@]}" > "$HOME/highlights"
cache="$XDG_CACHE_HOME/dots/zsh/${DOTS_PLATFORM:-linux}-$ZSH_VERSION/fsh/theme.zsh"
zstat -A initial +inode "$cache"
set_theme || exit 5
zstat -A reused +inode "$cache"
[[ $initial == $reused ]] || exit 6
"$DOTS/bin/dots-theme-set" catppuccin-latte >/dev/null || exit 7
false
_dots_theme_precmd
[[ $? == 1 && $FAST_THEME_NAME == dots && ${FAST_HIGHLIGHT_STYLES[dotscommand]} != "$first" ]] || exit 8
latest=${FAST_HIGHLIGHT_STYLES[dotscommand]}
set_theme nord || exit 9
[[ -z $_DOTS_THEME_FSH_FILE && $FAST_THEME_NAME == dots && ${FAST_HIGHLIGHT_STYLES[dotscommand]} == "$latest" ]] || exit 10
set_theme || exit 11
[[ $FAST_THEME_NAME == dots ]] || exit 12
''', old.ZSH)
        after = {p.name: p.read_bytes() for p in (self.home / 'fsh-plugin').glob('*theme.zsh*')}
        self.assertEqual(before, after)
        self.assertIn('fg=', (self.home / 'highlights').read_text())

    @unittest.skipUnless(old.ZSH and FSH.is_dir(), 'Installed FSH and Zsh required')
    def test_native_fsh_overlay_and_bad_template(self):
        setup = self.install_fsh()
        self.dots('theme', 'set', 'nord')
        self.shell(setup + '''print 'FAST_HIGHLIGHT_STYLES[${FAST_THEME_NAME}comment]=fg=#123456' > "$FAST_WORK_DIR/theme_overlay.zsh"
set_theme || exit 1
[[ ${FAST_HIGHLIGHT_STYLES[dotscomment]} == 'fg=#123456' ]] || exit 2
text=$(<"$_DOTS_THEME_FSH_FILE")
print -r -- "${text/secondary        =/secondary        = free}" > "$HOME/secondary.ini"
_DOTS_THEME_FSH_FILE=$HOME/secondary.ini
_dots_fsh_theme || exit 5
[[ ${FAST_HIGHLIGHT_STYLES[dotssecondary]} == free && ${+FAST_HIGHLIGHT_STYLES[freedefault]} == 1 ]] || exit 6
before=${FAST_HIGHLIGHT_STYLES[dotscommand]}
saved=$(<"$FAST_WORK_DIR/current_theme.zsh")
print '[base]\nunknown-token = not-a-color' > "$HOME/bad.ini"
_DOTS_THEME_FSH_FILE=$HOME/bad.ini
_dots_fsh_theme && exit 3
[[ $FAST_THEME_NAME == dots && ${FAST_HIGHLIGHT_STYLES[dotscommand]} == "$before" ]] || exit 4
[[ $(<"$FAST_WORK_DIR/current_theme.zsh") == "$saved" ]] || exit 7
''', old.ZSH)

    @unittest.skipUnless(old.ZSH and FSH.is_dir(), 'Installed FSH and Zsh required')
    def test_native_fsh_saved_startup_and_backups(self):
        setup = self.install_fsh()
        # A foreign theme is test data, not a retired personal config dependency.
        (self.home / 'njen.ini').write_text('[base]\ndefault = white\n[command-point]\ncommand = green\n')
        self.dots('theme', 'set', 'nord')
        self.shell(setup + '''fast-theme -q "$HOME/njen.ini" || exit 1
[[ $FAST_THEME_NAME == njen && -f $FAST_WORK_DIR/current_theme.zsh.zwc ]] || exit 2
cp "$FAST_WORK_DIR/current_theme.zsh" "$HOME/prior.zsh"
cp "$FAST_WORK_DIR/current_theme.zsh.zwc" "$HOME/prior.zwc"
set_theme || exit 3
[[ $FAST_THEME_NAME == dots && ! -e $FAST_WORK_DIR/current_theme.zsh.zwc ]] || exit 4
zstat -A initial +inode "$FAST_WORK_DIR/current_theme.zsh"
set_theme || exit 5
zstat -A reused +inode "$FAST_WORK_DIR/current_theme.zsh"
[[ $initial == $reused ]] || exit 6
''', old.ZSH)
        work = Path(self.env['FAST_WORK_DIR'])
        backups = list(work.glob('.dots-theme-backup.*'))
        self.assertEqual(len(backups), 1)
        self.assertEqual((backups[0] / 'current_theme.zsh').read_bytes(), (self.home / 'prior.zsh').read_bytes())
        self.assertEqual((backups[0] / 'current_theme.zsh.zwc').read_bytes(), (self.home / 'prior.zwc').read_bytes())
        self.assertEqual(backups[0].stat().st_mode & 0o777, 0o700)
        self.assertEqual((work / 'current_theme.zsh').stat().st_mode & 0o777, 0o600)
        caches = list((self.home / 'cache/dots').glob('zsh/*/fsh/theme.zsh'))
        self.assertEqual(len(caches), 1)
        caches[0].unlink()
        # Native plugin startup alone must select Dots before any Dots hook.
        result = self.shell('''source "$HOME/fsh-plugin/fast-syntax-highlighting.plugin.zsh"
[[ $FAST_THEME_NAME == dots ]] || exit 1
fast-theme --show
''', old.ZSH)
        plain = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout)
        self.assertIn('Currently active theme: dots', plain)
        self.assertIn('Main theme (loaded at startup of a session): dots', plain)
        saved = (work / 'current_theme.zsh').read_bytes()
        self.shell(setup + '''_DOTS_THEME_FSH_FILE=$HOME/missing.ini
_dots_fsh_theme && exit 1
[[ $FAST_THEME_NAME == dots ]] || exit 2
''', old.ZSH)
        self.assertEqual((work / 'current_theme.zsh').read_bytes(), saved)
        self.assertEqual(list(work.glob('.dots-theme-backup.*')), backups)

    @unittest.skipUnless(old.ZSH and FSH.is_dir(), 'Installed FSH and Zsh required')
    def test_native_fsh_saved_links_and_write_failures(self):
        self.env['FAST_WORK_DIR'] = str(self.home / '-FSH cache ü')
        setup = self.install_fsh()
        self.dots('theme', 'set', 'nord')
        self.shell(setup + '''print 'typeset -g FAST_THEME_NAME=njen' > "$HOME/prior.zsh"
print 'old compiled data' > "$HOME/prior.zwc"
ln -s "$HOME/prior.zsh" "$FAST_WORK_DIR/current_theme.zsh"
ln -s "$HOME/prior.zwc" "$FAST_WORK_DIR/current_theme.zsh.zwc"
set_theme || exit 1
[[ -f $FAST_WORK_DIR/current_theme.zsh && ! -L $FAST_WORK_DIR/current_theme.zsh ]] || exit 2
cache="$XDG_CACHE_HOME/dots/zsh/${DOTS_PLATFORM:-linux}-$ZSH_VERSION/fsh/theme.zsh"
saved=$(<"$FAST_WORK_DIR/current_theme.zsh")
mkdir "$FAST_WORK_DIR/current_theme.zsh.zwc"
_dots_fsh_save "$cache" && exit 3
[[ $(<"$FAST_WORK_DIR/current_theme.zsh") == "$saved" ]] || exit 4
rmdir "$FAST_WORK_DIR/current_theme.zsh.zwc"
mv "$FAST_WORK_DIR/current_theme.zsh" "$HOME/saved.zsh"
mkdir "$FAST_WORK_DIR/current_theme.zsh"
_dots_fsh_save "$cache" && exit 5
rmdir "$FAST_WORK_DIR/current_theme.zsh"
mv "$HOME/saved.zsh" "$FAST_WORK_DIR/current_theme.zsh"
print -r -- "$(<"$cache")" > "$HOME/changed.zsh"
print '# changed' >> "$HOME/changed.zsh"
zf_mv() { return 1; }
_dots_fsh_save "$HOME/changed.zsh" && exit 6
[[ $(<"$FAST_WORK_DIR/current_theme.zsh") == "$saved" ]] || exit 7
''', old.ZSH)
        work = Path(self.env['FAST_WORK_DIR'])
        backups = list(work.glob('.dots-theme-backup.*'))
        self.assertEqual(len(backups), 1)
        for name, original in [('current_theme.zsh', 'prior.zsh'), ('current_theme.zsh.zwc', 'prior.zwc')]:
            self.assertEqual((backups[0] / name).readlink(), self.home / original)
        self.assertEqual((self.home / 'prior.zsh').read_text(), 'typeset -g FAST_THEME_NAME=njen\n')
        self.assertFalse(list(work.glob('.dots-theme-current.*')))

    @unittest.skipUnless(old.ZSH and FSH.is_dir(), 'Installed FSH and Zsh required')
    def test_native_fsh_loads_after_widget_plugin(self):
        self.install_fsh()
        self.dots('theme', 'set', 'nord')
        self.shell('''source "$DOTS/shells/zsh/core/cache.zsh"
source "$DOTS/lib/dots/themes/shell.bash"
set_theme || exit 1
(( ! ${+FAST_HIGHLIGHT_STYLES} )) || exit 2
source "$DOTS/shells/zsh/integrations/plugins.zsh"
_dots_plugin_setup() { :; }
_dots_suggestion_plugin() { :; }
_dots_load_plugin() {
  if [[ $1 == zdharma-continuum/fast-syntax-highlighting ]]; then
    source "$HOME/fsh-plugin/fast-syntax-highlighting.plugin.zsh"
  fi
}
_dots_widget_plugins
[[ $FAST_THEME_NAME == dots ]] || exit 3
mkdir "$HOME/directory"
PREBUFFER=''
local -a reply
-fast-highlight-process '' 'cd ./directory' 0
[[ ${(j: :)reply} == *"${FAST_HIGHLIGHT_STYLES[dotspath-to-dir]}"* ]] || exit 4
-fast-highlight-process '' 'echo $(echo hello)' 0
[[ ${(M)#reply:#*${FAST_HIGHLIGHT_STYLES[dotscommand]}*} -ge 2 ]] || exit 5
''', old.ZSH)


for name in dir(old.Themes):
    if name.startswith('test_') and name not in FileThemes.__dict__:
        setattr(FileThemes, name, None)

if __name__ == '__main__':
    unittest.main()

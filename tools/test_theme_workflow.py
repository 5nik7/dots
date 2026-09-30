#!/usr/bin/env python3
"""Omarchy-style theme publication, imports and adapters in disposable homes."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tomllib
import unittest

spec = importlib.util.spec_from_file_location("oldthemes", Path(__file__).with_name("test_themes.py"))
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)


class Workflow(old.Themes):
    # Only inherit the fixture, not the older suite's cases.
    def test_application_environment_templates_and_shell_refresh(self):
        self.dots("theme", "set", "nord")
        first = self.generation()
        for name in ("fzf.sh", "gum_env.sh"):
            self.assertNotIn("{{", (first / name).read_text())
        for shell in (old.BASH, old.ZSH):
            if not shell:
                continue
            result = self.shell(r'''
FZF_DEFAULT_OPTS='--height=40% --layout=reverse'
source "$DOTS/themes/bin/theme"
set_theme || exit 1
[[ $GUM_CONFIRM_PROMPT_FOREGROUND == '#81a1c1' ]] || exit 2
[[ $_FZF_COLORS_ == *'preview-bg:#222730'* ]] || exit 3
before=$FZF_DEFAULT_OPTS
set_theme || exit 4
[[ $FZF_DEFAULT_OPTS == "$before" ]] || exit 5
"$DOTS/bin/dots-theme-set" catppuccin-latte >/dev/null || exit 6
set_theme || exit 7
[[ $GUM_CONFIRM_PROMPT_FOREGROUND == '#1e66f5' ]] || exit 10
[[ $_FZF_COLORS_ == *'prompt:#1e66f5'* ]] || exit 8
[[ $FZF_DEFAULT_OPTS == '--height=40% --layout=reverse --color='* ]] || exit 9
printf '%s\n' "$FZF_DEFAULT_OPTS"
''', shell)
            self.assertEqual(result.stdout.count("--color="), 1)
            # Start the next shell from the same initial selection.
            self.dots("theme", "set", "nord")

        # Public init output must work without loading the shell adapter.
        for shell in ("bash", "zsh", "fish"):
            executable = shutil.which(shell)
            if not executable:
                continue
            init = self.root / ("consumer." + shell)
            init.write_text(self.dots("theme", "init", "--shell", shell).stdout)
            if shell == "fish":
                body = 'set -gx FZF_DEFAULT_OPTS --height=40%; source "$INIT"; source "$INIT"; printf "%s\\n" "$GUM_CONFIRM_PROMPT_FOREGROUND" "$FZF_DEFAULT_OPTS"'
                args = [executable, "--no-config", "-c", body]
            else:
                body = 'export FZF_DEFAULT_OPTS=--height=40%; source "$INIT"; source "$INIT"; printf "%s\\n" "$GUM_CONFIRM_PROMPT_FOREGROUND" "$FZF_DEFAULT_OPTS"'
                args = [executable, "-f", "-c", body]
            result = self.run_command(args, env=dict(self.env, INIT=str(init)))
            self.assertIn("\n--height=40% --color=", result.stdout)
            self.assertEqual(result.stdout.count("--color="), 1)

    def test_application_environment_overrides_and_refusal(self):
        user = self.home / "config/dots/themed"
        user.mkdir(parents=True)
        fzf = user / "fzf.sh.tpl"
        fzf.write_text('export _FZF_COLORS_="fg:{{ foreground }},bg:-1"\n')
        self.dots("theme", "set", "nord")
        before = self.generation()
        self.assertIn('fg:#d8dee9,bg:-1', (before / "fzf.sh").read_text())
        # Bundled app files win over personal templates and participate in refresh.
        override = self.repo / "themes/nord/fzf.sh"
        override.write_text('export _FZF_COLORS_="fg:#112233"\n')
        self.dots("theme", "refresh")
        self.assertIn('fg:#112233', (self.generation() / "fzf.sh").read_text())
        override.write_text('export _FZF_COLORS_="fg:#445566"\n')
        self.dots("theme", "refresh")
        self.assertIn('fg:#445566', (self.generation() / "fzf.sh").read_text())
        override.unlink()
        self.dots("theme", "refresh")
        before = self.generation()
        for file, invalid in (
            (fzf, 'export _FZF_COLORS_="$(touch SENTINEL)"\n'),
            (fzf, 'export _FZF_COLORS_="fg:#nothex"\n'),
            (fzf, 'export _FZF_COLORS_="fg:256"\n'),
            (fzf, 'export _FZF_COLORS_="fg:#ffffff"\ntouch SENTINEL\n'),
        ):
            original = file.read_text()
            file.write_text(invalid)
            self.dots("theme", "refresh", code=1)
            self.assertEqual(self.generation(), before)
            self.assertFalse((self.home / "SENTINEL").exists())
            file.write_text(original)

    def test_shell_gum_template(self):
        self.dots("theme", "set", "nord")
        for shell in (old.BASH, old.ZSH):
            if not shell:
                continue
            with self.subTest(shell=shell):
                result = self.shell('''
source "$XDG_STATE_HOME/dots/current/theme/gum_env.sh" || exit 1
source "$XDG_STATE_HOME/dots/current/theme/gum_env.sh" || exit 2
env
''', shell)
                colors = dict(line.split("=", 1) for line in result.stdout.splitlines()
                              if line.startswith(("GUM_", "FOREGROUND=", "BACKGROUND=", "BORDER_")))
                self.assertEqual(len(colors), 116)
                for value in colors.values():
                    self.assertRegex(value, r"^#[a-fA-F0-9]{6}$")
                self.assertEqual(colors["GUM_CONFIRM_PROMPT_FOREGROUND"], "#81a1c1")
                self.assertEqual(colors["FOREGROUND"], "#d8dee9")
                self.assertEqual(colors["GUM_LOG_SEPARATOR_BACKGROUND"], "#2e3440")
                refreshed = self.shell('''
source "$XDG_STATE_HOME/dots/current/theme/gum_env.sh" || exit 1
"$DOTS/bin/dots-theme-set" catppuccin-latte >/dev/null || exit 2
source "$XDG_STATE_HOME/dots/current/theme/gum_env.sh" || exit 3
printf '%s' "$GUM_CONFIRM_PROMPT_FOREGROUND"
''', shell)
                self.assertEqual(refreshed.stdout, "#1e66f5")
                self.dots("theme", "set", "nord")
        for name in ("init.zsh", "init.fish"):
            self.assertNotIn("GUM_", (self.generation() / name).read_text())
            self.assertNotIn("gum_env.sh", (self.generation() / name).read_text())
        # Shell overrides remain inert during publication and refresh.
        user = self.home / "config/dots/themed"
        user.mkdir(parents=True)
        (user / "gum_env.sh.tpl").write_text("touch SENTINEL\nexport FOREGROUND='{{ foreground }}'\n")
        self.dots("theme", "refresh")
        self.assertEqual((self.generation() / "gum_env.sh").read_text(),
                         "touch SENTINEL\nexport FOREGROUND='#d8dee9'\n")
        override = self.repo / "themes/nord/gum_env.sh"
        override.write_text("touch SENTINEL\nexport FOREGROUND='#112233'\n")
        self.dots("theme", "refresh")
        self.assertEqual((self.generation() / "gum_env.sh").read_text(), override.read_text())
        before = self.generation()
        override.write_text("touch SENTINEL\nexport FOREGROUND='#445566'\n")
        self.dots("theme", "refresh")
        self.assertNotEqual(self.generation(), before)
        self.assertEqual((self.generation() / "gum_env.sh").read_text(), override.read_text())
        self.assertFalse((self.home / "SENTINEL").exists())

    def test_flat_palette_catalog(self):
        names = self.dots("theme", "list").stdout.splitlines()
        expected = {path.parent.name for path in (self.repo / 'themes').glob('*/colors.toml')
                    if path.is_file() and not path.is_symlink()} | {'pywal16-current'}
        self.assertEqual(set(names), expected)
        self.assertEqual(len(names), len(expected))
        for name in names:
            if name == "pywal16-current":
                self.wal_export()
            self.dots("theme", "show", name)
        palette = tomllib.loads((self.repo / 'themes/catppuccin-mocha/colors.toml').read_text())
        self.assertEqual(self.dots("theme", "color", "accent", "--theme", "catppuccin-mocha").stdout.strip(), palette['accent'])
        self.assertFalse(self.state.exists())

    def test_presentation_and_raw_theme_queries(self):
        env = dict(self.env, DOTS_COLOR="always", DOTS_ICONS="never")
        self.assertIn("theme set", self.dots("theme", env=env).stdout)
        self.assertIn("theme bg next", self.dots("theme", "bg", env=env).stdout)
        listing = self.dots("theme", "list", env=env).stdout
        self.assertIn("[+] current", listing)
        count = len(self.dots("theme", "list").stdout.splitlines())
        self.assertIn(f"{count} themes available", listing)
        self.assertIn("\x1b[48;2;", self.dots("theme", "show", "nord", env=env).stdout)
        preview = self.dots("theme", "set", "nord", "--dry-run", env=env).stdout
        self.assertIn("Theme preview", preview)
        self.assertIn("Preview only", preview)
        self.assertIn("Backgrounds", self.dots("theme", "bg", "list", env=env).stdout)
        for args in [("current",), ("dir", "nord"), ("color", "accent", "--theme", "nord"), ("init",)]:
            self.assertNotIn("\x1b", self.dots("theme", *args, env=env).stdout)
        error = self.dots("theme", "show", "absent", env=env, code=1)
        self.assertEqual(error.stdout, "")
        self.assertIn("\x1b", error.stderr)
        self.assertFalse(self.state.exists())

    def test_template_precedence_atomic_output_and_generic(self):
        user = self.home / "config/dots/themed"
        user.mkdir(parents=True)
        (user / "kitty.conf.tpl").write_text("foreground {{ red }}\n# {{ red_strip }} {{ red_rgb }}\n")
        self.dots("theme", "set", "nord", "--dry-run")
        self.assertFalse(self.state.exists())
        self.dots("theme", "set", "nord")
        active = self.home / "state/dots/current/theme"
        self.assertTrue(active.is_symlink())
        self.assertEqual(active.resolve(), self.generation())
        text = (active / "kitty.conf").read_text()
        self.assertIn("foreground #bf616a", text)
        self.assertIn("bf616a 191,97,106", text)
        data = json.loads((active / "palette.json").read_text())
        self.assertEqual(data["adapter"], "generic")
        self.assertEqual(self.dots("theme", "current").stdout, "nord\n")
        before = active.readlink()
        self.dots("theme", "set", "nord")
        self.assertEqual(active.readlink(), before)
        (user / "kitty.conf.tpl").write_text("{{ missing_color }}\n")
        self.dots("theme", "refresh", code=1)
        self.assertEqual(active.readlink(), before)
        self.assertEqual((active / "kitty.conf").read_text(), text)

    @unittest.skipUnless(old.NVIM, "Neovim unavailable")
    def test_generic_editor_and_static_completion(self):
        self.dots("theme", "set", "nord")
        from nvim_theme_fixture import install, run
        install(self)
        run(self, r'''bridge.startup()
assert(vim.g.colors_name == "anodize")
assert(hl("Normal").fg == 0xd8dee9 and hl("Normal").bg == nil)
local data=snapshot()
assert(hl("Visual").bg == tonumber(data.roles.selection:sub(2),16))
assert(require("anodize").get_palette().metadata.id == "nord")
''')
        for shell in ("bash", "zsh", "fish"):
            self.assertIn("nord", self.dots("__complete", shell, "3", "--", "dots", "theme", "set", "no").stdout)
        self.assertIn("--dry-run", self.dots("help", "theme", "set").stdout)

    def test_unpublished_native_cache_tracks_semantic_edits(self):
        command = [old.BASH, str(self.repo / "themes/bin/catppuccin"), "init"]
        before = self.run_command(command).stdout
        colors = self.repo / "themes/catppuccin-mocha/colors.toml"
        stamp = colors.stat()
        colors.write_text(colors.read_text().replace("#89b4fa", "#123456"))
        os.utime(colors, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        after = self.run_command(command).stdout
        self.assertNotEqual(after, before)
        self.assertIn("#123456", after)
        self.assertFalse(self.state.exists())

    def test_connectors_preserve_prior_objects_and_rollback(self):
        app = self.home / "config/kitty"
        app.mkdir(parents=True)
        target = app / "dots-theme.conf"
        target.write_text("original user colors\n")
        self.dots("theme", "set", "nord")
        generation = self.generation()
        self.assertTrue(target.is_symlink())
        self.assertEqual((generation / "connectors/0/old").read_text(), "original user colors\n")
        self.engine('dt_restore "' + str(generation) + '"')
        self.assertFalse(target.is_symlink())
        self.assertEqual(target.read_text(), "original user colors\n")
        self.assertFalse((self.state / "current").exists())
        self.assertFalse((self.home / "state/dots/current/theme").is_symlink())

    def test_all_application_connectors_and_tmux_include(self):
        config = self.home / "config"
        for name in ("kitty", "tmux", "btop/themes", "yazi/flavors"):
            (config / name).mkdir(parents=True)
        (self.home / ".termux").mkdir()
        original = self.home / ".termux/colors.properties"
        original.write_text("background=#010203\n")
        self.dots("theme", "set", "nord")
        active = self.home / "state/dots/current/theme"
        for path, output in [(config / "kitty/dots-theme.conf", "kitty.conf"),
                             (config / "tmux/dots-theme.conf", "tmux.conf"),
                             (config / "btop/themes/dots.theme", "btop.theme"),
                             (config / "yazi/flavors/dots.yazi", "yazi"),
                             (original, "termux.properties")]:
            self.assertTrue(path.is_symlink())
            self.assertEqual(path.resolve(), (active / output).resolve())
            self.assertTrue(path.exists())
        import xml.etree.ElementTree as ET
        ET.parse(active / "bat.tmTheme")
        self.assertIn("color15=", original.read_text())
        tmux = shutil.which("tmux")
        if tmux:
            socket = self.root / "owned-tmux.socket"
            cfg = config / "tmux/tmux.conf"
            line = next(line for line in (old.REPO / "config/tmux/tmux.conf").read_text().splitlines() if 'current_file' in line)
            cfg.write_text(line + "\n")
            command = [tmux, "-S", str(socket)]
            try:
                self.run_command(command + ["-f", "/dev/null", "new-session", "-d", "-s", "fixture", "sleep 30"])
                self.run_command(command + ["source-file", str(cfg)])
                style = self.run_command(command + ["show-options", "-gv", "status-style"]).stdout
                self.assertIn("#d8dee9", style)
                self.assertIn("bg=default", style)
            finally:
                self.run_command(command + ["kill-server"], code=None)

    def test_interrupted_active_and_connector_staging_recovery(self):
        app = self.home / "config/kitty"
        app.mkdir(parents=True)
        target = app / "dots-theme.conf"
        target.write_text("original colors\n")
        self.dots("theme", "set", "nord")
        generation = self.generation()
        active = self.home / "state/dots/current/theme"
        # Model SIGKILL immediately before the staged active/connector renames.
        target.unlink()
        target.write_text("original colors\n")
        Path(str(target) + ".dots-theme-new").symlink_to(active / "kitty.conf")
        active.unlink()
        Path(str(active) + ".new").symlink_to(generation)
        (generation / "status").write_text("prepared\n")
        self.dots("theme", "set", "nord")
        self.assertEqual((generation / "status").read_text(), "rolled-back\n")
        self.assertFalse(Path(str(active) + ".new").is_symlink())
        self.assertFalse(Path(str(target) + ".dots-theme-new").is_symlink())
        self.assertTrue(target.is_symlink())
        self.assertEqual((self.generation() / "connectors/0/old").read_text(), "original colors\n")

    def test_linux_wallpaper_adapters_and_unsupported_session(self):
        self.dots("theme", "set", "nord")
        fake = self.root / "desktopbin"
        fake.mkdir()
        for name in ("swww", "feh"):
            adapter = fake / name
            adapter.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$HOME/desktop-call"\n')
            adapter.chmod(0o755)
        env = dict(self.env, TERMUX_VERSION="", PREFIX="", WSL_DISTRO_NAME="", PATH=str(fake)+":"+self.env["PATH"])
        self.dots("theme", "bg", "next", env=dict(env, WAYLAND_DISPLAY="fixture"))
        self.assertTrue((self.home / "desktop-call").read_text().startswith("img\n"))
        self.dots("theme", "bg", "next", env=dict(env, WAYLAND_DISPLAY="", DISPLAY=":99"))
        self.assertTrue((self.home / "desktop-call").read_text().startswith("--no-fehbg\n"))
        before = self.dots("theme", "bg", "current").stdout
        self.dots("theme", "bg", "next", env=dict(env, WSL_DISTRO_NAME="fixture"), code=1)
        self.assertEqual(self.dots("theme", "bg", "current").stdout, before)

    def test_git_lifecycle_data_only_and_dirty_refusal(self):
        remote = self.root / "source theme"
        remote.mkdir()
        def git(*args):
            return subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "-C", str(remote), *args], env=self.env, capture_output=True, text=True, check=True)
        git("init", "-q")
        shutil.copy2(self.repo / "themes/nord/colors.toml", remote / "colors.toml")
        (remote / "neovim.lua").write_text('error("downloaded code must never execute")')
        git("add", "."); git("commit", "-qm", "Initial")
        env = dict(self.env, DOTS_TEST_LOCAL_GIT="always")
        self.dots("theme", "install", str(remote), "--name", "fixture", env=env)
        installed = self.home / "config/dots/themes/fixture"
        self.assertTrue(installed.is_dir())
        self.assertFalse(self.state.exists())
        (installed / "local-file").write_text("keep")
        self.dots("theme", "update", "fixture", env=env, code=1)
        self.assertEqual((installed / "local-file").read_text(), "keep")
        (installed / "local-file").unlink()
        colors = remote / "colors.toml"
        colors.write_text(colors.read_text().replace("#2e3440", "#112233"))
        git("add", "."); git("commit", "-qm", "Updated")
        self.dots("theme", "update", "fixture", env=env)
        self.assertIn("#112233", (installed / "colors.toml").read_text())
        self.dots("theme", "set", "fixture")
        self.dots("theme", "remove", "fixture", code=1)
        self.dots("theme", "set", "nord")
        self.dots("theme", "remove", "fixture")
        self.assertFalse(installed.exists())
        self.assertTrue(list((installed.parent / ".archives").iterdir()))

    def test_background_switcher_labels_preview_and_cancellation(self):
        self.dots("theme", "set", "nord")
        backgrounds = self.home / "config/dots/backgrounds/nord"
        backgrounds.mkdir(parents=True)
        image = backgrounds / "-雪 ' $(false).night.jpg"
        image.write_bytes(b"fixture")
        duplicate = backgrounds / "-雪 ' $(false).night.png"
        duplicate.write_bytes(b"fixture")
        fake = self.root / "pickerbin"
        fake.mkdir()
        picker = fake / "fzf"
        picker.write_text(f'''#!{shutil.which("python3")}
import json, os, pathlib, shlex, subprocess, sys
rows = sys.stdin.buffer.read().decode().split('\\0')
args = sys.argv[1:]
pathlib.Path(os.environ['HOME'], 'picker.json').write_text(json.dumps([args, rows]))
if os.environ.get('PICKER_CANCEL'):
    sys.exit(130)
if os.environ.get('PICKER_INVALID'):
    print(os.environ['PICKER_IMAGE'])
    sys.exit(0)
row = next(row for row in rows if row.endswith(os.environ['PICKER_IMAGE']))
if '--preview' in args:
    preview = args[args.index('--preview') + 1]
    preview = preview.replace('{{s2..}}', shlex.quote(os.environ['PICKER_IMAGE']))
    subprocess.run(preview, shell=True, check=True, env=dict(os.environ,
        FZF_PREVIEW_COLUMNS='37', FZF_PREVIEW_LINES='18'))
print(row)
''')
        picker.chmod(0o755)
        for name, output in (("chafa", "preview-call"), ("termux-wallpaper", "wallpaper-call")):
            adapter = fake / name
            adapter.write_text(f'#!/bin/sh\nprintf "%s\\n" "$@" > "$HOME/{output}"\n')
            adapter.chmod(0o755)
        env = dict(self.env, TERMUX_VERSION="fixture", PREFIX=str(self.root / "usr"),
                   PATH=str(fake) + ":" + self.env["PATH"], PICKER_IMAGE=str(image))
        self.dots("theme", "bg", "switcher", env=env)
        args, rows = json.loads((self.home / "picker.json").read_text())
        self.assertIn("--with-nth=1", args)
        self.assertIn("--nth=1", args)
        self.assertIn("--preview-window=down,70%,nohidden", args)
        for option in ('--no-height', '--layout=reverse', '--margin=0', '--padding=0'):
            self.assertIn(option, args)
        self.assertIn(image.stem + "\t" + str(image), rows)
        self.assertIn(duplicate.stem + "\t" + str(duplicate), rows)
        native_fzf = shutil.which("fzf")
        if native_fzf:
            result = subprocess.run([native_fzf, *args, '--filter=.night'],
                                    input='\0'.join(rows), text=True, capture_output=True,
                                    env=dict(self.env, FZF_DEFAULT_OPTS='--height=~90% --layout=default --margin=2 --padding=1',
                                             FZF_DEFAULT_OPTS_FILE=''),
                                    timeout=10, check=True)
            self.assertEqual(set(result.stdout.splitlines()),
                             {image.stem + "\t" + str(image), duplicate.stem + "\t" + str(duplicate)})
        self.assertEqual((self.home / "preview-call").read_text().splitlines(),
                         ['--format=symbols', '--animate=off', '--scale=max', '--size', '37x18', '--', str(image)])
        self.assertEqual(self.dots("theme", "bg", "current").stdout, str(image) + "\n")
        self.dots("theme", "bg", "switcher", env=dict(env, PICKER_CANCEL="1"), code=130)
        self.dots("theme", "bg", "switcher", env=dict(env, PICKER_INVALID="1"), code=1)
        self.assertEqual(self.dots("theme", "bg", "current").stdout, str(image) + "\n")
        # Hide only Chafa, independently of the developer's installed tools.
        startup = self.root / "no-chafa.bash"
        startup.write_text('command() {\n'
                           '  [[ $1 != -v || $2 != chafa ]] || return 1\n'
                           '  builtin command "$@"\n}\n')
        (self.home / "preview-call").write_text("not invoked")
        self.dots("theme", "bg", "switcher", env=dict(env, BASH_ENV=str(startup)))
        args, _ = json.loads((self.home / "picker.json").read_text())
        self.assertIn("--preview-window=hidden", args)
        self.assertEqual((self.home / "preview-call").read_text(), "not invoked")

    def test_wallpaper_explicit_adapter_and_failure(self):
        self.dots("theme", "set", "nord")
        fake = self.root / "fakebin"
        fake.mkdir()
        adapter = fake / "termux-wallpaper"
        adapter.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$HOME/wallpaper-call"\n')
        adapter.chmod(0o755)
        env = dict(self.env, TERMUX_VERSION="fixture", PREFIX=str(self.root / "usr"), PATH=str(fake)+":"+self.env["PATH"])
        self.assertFalse((self.home / "wallpaper-call").exists())
        self.dots("theme", "bg", "next", env=env)
        before = self.dots("theme", "bg", "current", env=env).stdout
        self.assertTrue(Path(before.strip()).is_file())
        adapter.write_text("#!/bin/sh\nexit 1\n")
        self.dots("theme", "bg", "next", env=env, code=1)
        self.assertEqual(self.dots("theme", "bg", "current", env=env).stdout, before)


# Reuse setup/helpers while excluding inherited tests from this runner.
for name in dir(old.Themes):
    if name.startswith("test_") and name not in Workflow.__dict__:
        setattr(Workflow, name, None)

if __name__ == "__main__":
    unittest.main()

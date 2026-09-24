#!/usr/bin/env python3
"""Omarchy-style theme publication, imports and adapters in disposable homes."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

spec = importlib.util.spec_from_file_location("oldthemes", Path(__file__).with_name("test_themes.py"))
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)


class Workflow(old.Themes):
    # Only inherit the fixture, not the older suite's cases.
    def test_flat_palette_catalog(self):
        names = self.dots("theme", "list").stdout.splitlines()
        self.assertEqual(len(names), 33)
        self.assertEqual(len(set(names)), 33)
        for name in names:
            if name == "pywal16-current":
                self.wal_export()
            self.dots("theme", "show", name)
        self.assertEqual(self.dots("theme", "color", "accent", "--theme", "catppuccin-mocha").stdout.strip(), "#89b4fa")
        self.assertFalse(self.state.exists())

    def test_presentation_and_raw_theme_queries(self):
        env = dict(self.env, DOTS_COLOR="always", DOTS_ICONS="never")
        self.assertIn("theme set", self.dots("theme", env=env).stdout)
        self.assertIn("theme bg next", self.dots("theme", "bg", env=env).stdout)
        listing = self.dots("theme", "list", env=env).stdout
        self.assertIn("[+] current", listing)
        self.assertIn("33 themes available", listing)
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
        util = self.root / "lua/util"
        util.mkdir(parents=True)
        for name in ("dots_theme.lua", "dots_theme_adapters.lua"):
            shutil.copy2(old.REPO / "config/nvim/lua/util" / name, util / name)
        script = self.root / "generic.lua"
        script.write_text('''vim.opt.rtp:prepend(vim.env.HOME .. "/..")
local themes = require("util.dots_theme")
themes.startup()
assert(vim.g.colors_name == "dots-nord")
local normal = vim.api.nvim_get_hl(0, { name="Normal", link=false })
assert(normal.fg == tonumber("d8dee9",16) and normal.bg == nil)
local visual = vim.api.nvim_get_hl(0, { name="Visual", link=false })
local data = vim.json.decode(table.concat(vim.fn.readfile(vim.env.XDG_STATE_HOME .. "/dots/current/theme/palette.json"), "\\n"))
assert(visual.bg == tonumber(data.roles.selection:sub(2),16))
''')
        self.run_command([old.NVIM, "--headless", "-u", "NONE", "-i", "NONE", "-l", str(script)])
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

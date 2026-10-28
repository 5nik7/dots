"""Focused, offline tests for the isolated welcome renderer."""

import ast
import importlib.util
import io
import json
import os
import re
import sys
import tempfile
import unittest
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "lib" / "welcome.py"
SPEC = importlib.util.spec_from_file_location("blastoff_welcome_test", SOURCE)
welcome = importlib.util.module_from_spec(SPEC)
# Loading by filename also works when the parent core uses Python -I.
with patch.object(sys, "dont_write_bytecode", True):
    SPEC.loader.exec_module(welcome)


class Output(io.StringIO):
    def __init__(self, tty=False):
        super().__init__()
        self.tty = tty

    def isatty(self):
        return self.tty


class WelcomeTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.env = patch.dict(os.environ, {
            "HOME": self.root.name,
            "USERPROFILE": self.root.name,
            "BLASTOFF_HOME": str(Path(self.root.name) / "missing-store"),
            "STARSHIP_CONFIG": str(Path(self.root.name) / "missing.toml"),
            "TERM": "xterm-256color", "COLUMNS": "80", "PATH": "",
        }, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def capture(self, color="auto", tty=False, json_output=False, version="0.1.0"):
        out, err = Output(tty), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            result = welcome.render(version, color, json_output)
        self.assertIsNone(result)
        self.assertEqual(err.getvalue(), "")
        return out.getvalue()

    def test_plain_redirect_contains_brand_version_and_commands(self):
        text = self.capture()
        self.assertIn("BLASTOFF", text)
        self.assertIn("Version 0.1.0", text)
        for command in ("blastoff list", "blastoff pick", "blastoff current", "blastoff --help"):
            self.assertIn(command, text)
        self.assertNotIn("\033", text)
        self.assertTrue(text.isascii())

    def test_color_modes_and_terminal_matrix(self):
        for color in ("auto", "always", "never"):
            for tty in (False, True):
                for term in ("xterm-256color", "dumb"):
                    for no_color in (None, "", "1"):
                        with self.subTest(color=color, tty=tty, term=term, no_color=no_color):
                            os.environ["TERM"] = term
                            os.environ.pop("NO_COLOR", None)
                            if no_color is not None:
                                os.environ["NO_COLOR"] = no_color
                            expected = no_color is None and (
                                color == "always" or (color == "auto" and tty and term != "dumb")
                            )
                            text = self.capture(color=color, tty=tty)
                            self.assertEqual("\033[" in text, expected)
                            if expected:
                                self.assertIn("\033[95m", text)
                                self.assertIn("\033[35m", text)
                                self.assertIn("\033[0m", text)

    def test_widths_including_narrow_and_long_version(self):
        for width in (1, 8, 12, 20, 40, 80):
            for color in ("always", "never"):
                with self.subTest(width=width, color=color):
                    os.environ["COLUMNS"] = str(width)
                    text = self.capture(color=color, version="0.1.0-" + "preview" * 10)
                    plain = re.sub(r"\x1b\[[0-9;]*m", "", text)
                    self.assertTrue(all(len(line) <= width for line in plain.splitlines()))
                    self.assertTrue(plain.isascii())
                    if width >= 20:
                        self.assertIn("BLASTOFF", plain)
                        self.assertIn("blastoff --help", plain)

    def test_narrow_layout_remains_compact(self):
        for width in (20, 40):
            os.environ["COLUMNS"] = str(width)
            self.assertLessEqual(len(self.capture().splitlines()), 12)

    def test_invalid_width_falls_back_to_stdout_terminal(self):
        for value in ("", "bad", "0", "-1"):
            with self.subTest(value=value):
                os.environ["COLUMNS"] = value
                with patch.object(Output, "fileno", return_value=99), patch.object(
                    welcome.os, "get_terminal_size", return_value=os.terminal_size((20, 24))
                ) as size:
                    text = self.capture()
                size.assert_called_once_with(99)
                self.assertTrue(all(len(line) <= 20 for line in text.splitlines()))

    def test_unavailable_terminal_uses_plain_fallback(self):
        os.environ.pop("COLUMNS")
        self.assertIn("BLASTOFF", self.capture())
        with patch.object(Output, "fileno", return_value=99), patch.object(
            welcome.os, "get_terminal_size", side_effect=OSError("no terminal")
        ):
            self.assertIn("BLASTOFF", self.capture())

    def test_json_is_one_useful_object_without_terminal_queries(self):
        with patch.object(welcome, "_columns", side_effect=AssertionError("width query")), patch.object(
            Output, "isatty", side_effect=AssertionError("TTY query")
        ):
            text = self.capture(color="always", json_output=True)
        data = json.loads(text)
        self.assertEqual(data["name"], "blastoff")
        self.assertEqual(data["version"], "0.1.0")
        self.assertIn("Starship", data["description"])
        self.assertGreaterEqual(len(data["examples"]), 3)
        self.assertIn({"command": "blastoff --help", "description": "Explore all commands"}, data["examples"])
        self.assertEqual(len(text.splitlines()), 1)
        self.assertNotIn("\033", text)

    def test_render_has_no_file_access_discovery_or_processes(self):
        sentinel = Path(self.root.name) / "sentinel"
        sentinel.write_bytes(b"unchanged")
        forbidden = (
            "builtins.open", "io.open", "os.open", "os.listdir", "os.scandir",
            "os.stat", "os.mkdir", "os.system", "subprocess.Popen", "shutil.which",
        )
        with ExitStack() as stack:
            for name in forbidden:
                stack.enter_context(patch(name, side_effect=AssertionError(name)))
            for json_output in (False, True):
                self.capture(json_output=json_output)
        self.assertEqual(sentinel.read_bytes(), b"unchanged")
        self.assertEqual(list(Path(self.root.name).iterdir()), [sentinel])

    def test_real_file_redirection_is_plain_and_read_only_elsewhere(self):
        target = Path(self.root.name) / "stdout.txt"
        with target.open("w", encoding="ascii") as out, redirect_stdout(out):
            welcome.render("9.8.7")
        self.assertNotIn("\033", target.read_text())
        self.assertIn("9.8.7", target.read_text())
        self.assertEqual(list(Path(self.root.name).iterdir()), [target])

    def test_imports_stay_small_and_no_runtime_asset_dependency(self):
        tree = ast.parse(SOURCE.read_text())
        imports = {
            alias.name for node in ast.walk(tree) if isinstance(node, ast.Import)
            for alias in node.names
        }
        self.assertLessEqual(imports, {"os", "sys", "stat", "shutil", "textwrap", "json"})
        self.assertFalse(any(isinstance(node, ast.ImportFrom) for node in ast.walk(tree)))

    def test_invalid_color_fails_before_output(self):
        out = io.StringIO()
        with redirect_stdout(out), self.assertRaises(ValueError):
            welcome.render("0.1.0", color="invalid")
        self.assertEqual(out.getvalue(), "")


if __name__ == "__main__":
    unittest.main()

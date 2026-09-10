#!/usr/bin/env python3
"""Regression checks for verifier startup; no Go tools or builds are needed."""

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


VERIFIER = Path(__file__).with_name("verify.py").resolve()
OPTIMIZATION_ERROR = (
    "portability verification failed: optimized Python is unsupported because it "
    "disables verification assertions; rerun without -O/-OO and with "
    "PYTHONOPTIMIZE unset or 0.\n"
)


def snapshot(root):
    return {
        str(path.relative_to(root)): (
            path.lstat().st_mode, path.lstat().st_size, path.lstat().st_mtime_ns,
        )
        for path in (root, *root.rglob("*"))
    }


class OptimizationRejectionTests(unittest.TestCase):
    def check_rejection(self, flags=(), optimize=None):
        with tempfile.TemporaryDirectory(prefix="dots-verifier-test-") as temporary:
            root = Path(temporary).resolve()
            for name in ("home", "repo", "config", "data", "state", "cache", "tmp", "bin"):
                (root / name).mkdir()
            env = {
                "PATH": "", "HOME": str(root / "home"), "DOTS": str(root / "repo"),
                "XDG_CONFIG_HOME": str(root / "config"), "XDG_DATA_HOME": str(root / "data"),
                "XDG_STATE_HOME": str(root / "state"), "XDG_CACHE_HOME": str(root / "cache"),
                "TMPDIR": str(root / "tmp"), "TMP": str(root / "tmp"), "TEMP": str(root / "tmp"),
                "USERPROFILE": str(root / "home"), "APPDATA": str(root / "config"),
                "LOCALAPPDATA": str(root / "data"), "PYTHONDONTWRITEBYTECODE": "1",
            }
            for key in ("SystemRoot", "WINDIR"):
                if key in os.environ:
                    env[key] = os.environ[key]
            if optimize is not None:
                env["PYTHONOPTIMIZE"] = optimize
            before = snapshot(root)
            for mode in ("build", "check", "bench", "cross", "dist", "docs", "--help"):
                with self.subTest(mode=mode):
                    result = subprocess.run(
                        [sys.executable, "-B", *flags, str(VERIFIER), mode],
                        cwd=root / "repo", env=env, capture_output=True, text=True, encoding="utf-8", timeout=10,
                    )
                    self.assertEqual(result.returncode, 1)
                    self.assertEqual(result.stdout, "")
                    self.assertEqual(result.stderr, OPTIMIZATION_ERROR)
                    self.assertEqual(snapshot(root), before, "Verifier changed test-owned roots")

    def test_optimization_flag_rejected(self):
        self.check_rejection(flags=("-O",))

    def test_optimization_environment_rejected(self):
        self.check_rejection(optimize="1")


class HarnessEnvironmentTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location("dots_verify", VERIFIER)
        self.verify = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.verify)

    def test_native_identity_and_markers(self):
        for native, expected in ((('android', 'arm64'), 'termux'), (('linux', 'amd64'), 'linux'), (('windows', 'amd64'), 'windows')):
            with self.subTest(native=native):
                env = {"PREFIX": "fixture", "TERMUX_VERSION": "fixture"}
                child = dict(env, PATH="")
                got = self.verify.configure_native(dict(zip(("GOHOSTOS", "GOHOSTARCH"), native)), env, child)
                self.assertEqual(got, (expected, *native))
                self.assertEqual((env["GOOS"], env["GOARCH"]), native)
                self.assertEqual(child["PATH"], "")
                for target in (env, child):
                    self.assertEqual("TERMUX_VERSION" in target, expected == "termux")
                    self.assertEqual("PREFIX" in target, expected == "termux")
        for native in (("linux", "arm64"), ("windows", "arm64"), ("android", "amd64")):
            with self.subTest(unsupported=native), self.assertRaisesRegex(RuntimeError, "Supported native verification hosts"):
                self.verify.configure_native(dict(zip(("GOHOSTOS", "GOHOSTARCH"), native)), {}, {})

    def test_go_configuration_is_owned_before_invocation(self):
        with tempfile.TemporaryDirectory(prefix="dots-verifier-env-") as temporary:
            root = Path(temporary).resolve()
            poison = {"HOME": "/unowned", "XDG_CONFIG_HOME": "/unowned", "GOENV": "/unowned/goenv",
                      "GOTOOLCHAIN": "auto", "GOPROXY": "https://invalid.example", "GOFLAGS": "-race",
                      "WSL_INTEROP": "untrusted", "SECRET_SENTINEL": "must not be inherited"}
            with patch.dict(os.environ, poison, clear=True):
                env, child = self.verify.environments(root, "/toolchain/bin/go")
            self.assertEqual((root / "config/go/telemetry/mode").read_text(), "off\n")
            for key in ("GOENV", "GOWORK", "GOPROXY", "GOSUMDB"):
                self.assertEqual(env[key], "off")
            self.assertEqual(env["GOVCS"], "*:off")
            self.assertEqual(env["GOTOOLCHAIN"], "local")
            for key in ("HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME", "XDG_CACHE_HOME",
                        "TMPDIR", "TMP", "TEMP", "USERPROFILE", "APPDATA", "LOCALAPPDATA",
                        "GOPATH", "GOCACHE", "GOMODCACHE", "GOTMPDIR"):
                self.assertTrue(Path(env[key]).is_relative_to(root), key)
            if os.name == "nt":
                self.assertEqual(env["HOMEDRIVE"] + env["HOMEPATH"], env["USERPROFILE"])
            self.assertNotIn("WSL_INTEROP", child)
            self.assertNotIn("SECRET_SENTINEL", env)
            self.assertFalse(any(key.startswith("GO") for key in child))
            self.assertEqual(child["PATH"], "")

    def test_executable_names_and_windows_path_redaction(self):
        self.assertEqual(self.verify.executable_name("dots-spike", "windows"), "dots-spike.exe")
        self.assertEqual(self.verify.executable_name("repeat.exe", "windows"), "repeat.exe")
        self.assertEqual(self.verify.executable_name("dots-spike", "linux"), "dots-spike")
        path = r"C:\owned path\repo"
        value = {"nested": [{"location": path + r"\file"}]}
        result = self.verify.redact(value, [(path, "<owned>")])
        self.assertEqual(result["nested"][0]["location"], r"<owned>\file")
        self.assertNotIn("owned path", self.verify.json.dumps(result))

    def test_windows_symlink_refusals(self):
        for code in (5, 50, 1314, 87):
            with self.subTest(winerror=code), tempfile.TemporaryDirectory() as temporary:
                error = OSError("fixture refusal")
                error.winerror = code
                with patch.object(Path, "symlink_to", side_effect=error):
                    if code == 87:
                        with self.assertRaises(OSError):
                            self.verify.symlink_capabilities(Path(temporary), windows=True)
                    else:
                        result = self.verify.symlink_capabilities(Path(temporary), windows=True)
                        self.assertEqual({v["status"] for v in result.values()}, {"unavailable"})
                        self.assertEqual({v["winerror"] for v in result.values()}, {code})


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
"""Regression checks for verifier startup; no Go tools or builds are needed."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


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
            for mode in ("build", "check", "bench", "cross", "docs", "--help"):
                with self.subTest(mode=mode):
                    result = subprocess.run(
                        [sys.executable, "-B", *flags, str(VERIFIER), mode],
                        cwd=root / "repo", env=env, capture_output=True, text=True, timeout=10,
                    )
                    self.assertEqual(result.returncode, 1)
                    self.assertEqual(result.stdout, "")
                    self.assertEqual(result.stderr, OPTIMIZATION_ERROR)
                    self.assertEqual(snapshot(root), before, "Verifier changed test-owned roots")

    def test_optimization_flag_rejected(self):
        self.check_rejection(flags=("-O",))

    def test_optimization_environment_rejected(self):
        self.check_rejection(optimize="1")


if __name__ == "__main__":
    unittest.main(verbosity=2)

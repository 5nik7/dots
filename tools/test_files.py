#!/usr/bin/env python3
"""Isolated file catalog and configuration link migration regressions."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("catalog", ROOT / "lib/dots/files/catalog.py")
catalog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog)
spec = importlib.util.spec_from_file_location("migration", ROOT / "tools/migrate_config_paths.py")
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


class Files(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="dots-files-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / "home ü space"
        self.repo = self.home / "dots"
        (self.repo / ".dots").mkdir(parents=True)
        (self.repo / "config/app").mkdir(parents=True)
        (self.repo / "config/app/-settings").write_text("unchanged")
        (self.repo / "configs").symlink_to("config", target_is_directory=True)
        (self.home / ".config").mkdir()
        self.link = self.home / ".config/app"
        self.link.symlink_to(self.repo / "configs/app")
        self.env = patch.dict(os.environ, {"HOME": str(self.home), "DOTS": str(self.repo), "XDG_CONFIG_HOME": str(self.home / ".config")})
        self.env.start()
        self.addCleanup(self.env.stop)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.source = dict(id="dots", path=".", roots=["config"], platforms=["termux", "linux"])
        self.write("sources", dict(schema=1, sources=[self.source, dict(id="optional", path="missing", platforms=["linux"])]))
        self.row = dict(id="app", source="config/app", app="app", category="config", platforms=["termux", "linux"], target="${CONFIG}/app", strategy="directory-link")
        self.write("files", dict(schema=1, repository="dots", resources=[self.row]))

    def write(self, name, value):
        (self.repo / f".dots/{name}.json").write_text(json.dumps(value))

    def cat(self):
        return catalog.Catalog(self.repo, "termux")

    def test_observation_and_read_only(self):
        before = {p: (p.lstat().st_mtime_ns, p.read_bytes()) for p in self.repo.rglob("*") if p.is_file() and not p.is_symlink()}
        self.assertEqual(self.cat().records()[0]["status"], "linked")
        self.assertEqual(self.cat().sources[1]["status"], "unavailable")
        self.assertEqual(self.cat().discover(), [])
        self.assertEqual(before, {p: (p.lstat().st_mtime_ns, p.read_bytes()) for p in before})
        self.assertFalse((self.repo / ".dots/files.lock").exists())
        self.link.unlink()
        self.link.symlink_to("/nonexistent-owned-test-target")
        self.assertEqual(self.cat().records()[0]["status"], "broken-link")

    def test_conflict_and_explicit_replacement(self):
        second = dict(self.row, id="other")
        self.write("files", dict(schema=1, repository="dots", resources=[self.row, second]))
        self.assertEqual({r["status"] for r in self.cat().records()}, {"conflict"})
        second["replaces"] = ["dots:app"]
        self.write("files", dict(schema=1, repository="dots", resources=[self.row, second]))
        self.assertEqual([r["status"] for r in self.cat().records()], ["replaced", "linked"])

    def test_dispatch_metadata_and_completion(self):
        shutil.copytree(ROOT / "lib/dots", self.repo / "lib/dots")
        (self.repo / "bin").mkdir()
        for src in [ROOT / "bin/dots", *ROOT.glob("bin/dots-files*")]:
            shutil.copy2(src, self.repo / "bin" / src.name)
        cmd = [str(self.repo / "bin/dots")]
        def call(*args):
            proc = subprocess.run(cmd + list(args), capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            return proc.stdout
        call("commands", "--check")
        self.assertIn("--strategy", call("help", "files", "track"))
        self.assertEqual(call("files", "source", "dots:app").strip(), str(self.repo / "config/app"))
        self.assertIn("dots:app", call("__complete", "zsh", "3", "--", "dots", "files", "show", "dots:"))
        self.assertIn("dots", call("__complete", "fish", "4", "--", "dots", "files", "list", "--repo", "d"))

    def test_directory_ownership_and_catalog_symlink_refusal(self):
        child = dict(self.row, id="child", source="config/app/-settings", strategy="link", target="${CONFIG}/app/settings")
        self.write("files", dict(schema=1, repository="dots", resources=[self.row, child]))
        self.assertEqual({r["status"] for r in self.cat().records()}, {"conflict"})
        directory = self.repo / ".dots"
        directory.rename(self.repo / ".catalog")
        directory.symlink_to(".catalog")
        with self.assertRaises(ValueError):
            self.cat()

    def test_track_round_trip_and_refusal(self):
        cmd = [sys.executable, "-B", str(ROOT / "lib/dots/files/catalog.py"), "track", "config/app/-settings", "--repo", "dots", "--id", "settings", "--app", "app", "--category", "config", "--json"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["resources"][0]["source"], "config/app/-settings")
        before = (self.repo / ".dots/files.json").stat().st_mtime_ns
        self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
        self.assertEqual(before, (self.repo / ".dots/files.json").stat().st_mtime_ns)
        cmd += ["--target", "${HOME}/../escape"]
        self.assertNotEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
        self.assertEqual(before, (self.repo / ".dots/files.json").stat().st_mtime_ns)

    def test_migration_preview_apply_rollback(self):
        rows = migration.inventory(self.home, self.repo)
        self.assertEqual(len(rows), 1)
        old = os.readlink(self.link)
        journal = self.root / "migration.json"
        cmd = [sys.executable, "-B", str(ROOT / "tools/migrate_config_paths.py"), "--home", str(self.home), "--repo", str(self.repo), "--journal", str(journal)]
        self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
        self.assertFalse(journal.exists())
        self.assertEqual(subprocess.run(cmd + ["--apply"], capture_output=True).returncode, 0)
        self.assertNotEqual(os.readlink(self.link), old)
        self.assertEqual(subprocess.run(cmd + ["--rollback"], capture_output=True).returncode, 0)
        self.assertEqual(os.readlink(self.link), old)

    def test_migration_interruption_and_drift(self):
        rows = migration.inventory(self.home, self.repo)
        doc = dict(schema=1, status="prepared", links=rows)
        journal = self.root / "recover.json"
        migration.atomic_json(journal, doc)
        migration.replace(rows[0], rows[0]["old"], rows[0]["new"])
        # Simulate interruption before recording completion.
        migration.rollback(doc, journal)
        self.assertEqual(os.readlink(self.link), rows[0]["old"])
        self.link.unlink()
        self.link.write_text("user data")
        with self.assertRaises(ValueError):
            migration.rollback(doc, journal)
        self.assertEqual(self.link.read_text(), "user data")


if __name__ == "__main__":
    unittest.main()

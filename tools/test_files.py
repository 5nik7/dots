#!/usr/bin/env python3
"""Isolated file catalog and configuration link migration regressions."""
import importlib.util
import json
import os
from pathlib import Path
import re
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
    def test_large_journal_is_readable_and_still_blocks_unfinished_work(self):
        from transactions import Store
        store = Store(self.root/'state')
        identity = 'a' * 32
        folder = store.root/identity
        folder.mkdir(parents=True)
        existing = dict(schema=1, id=identity, action='fonts-update', status='recovery-required',
                        created='2026-01-01', guards={}, operations=[{'text': 'x' * (4 * 1024 * 1024)}])
        store.save(existing)
        journal = folder/'journal.json'
        with self.assertRaisesRegex(ValueError, 'invalid catalog'):
            catalog.read_json(journal)
        self.assertEqual(store.load(identity)['status'], 'recovery-required')
        target = self.root/'page.md'
        operation = [dict(path=str(target), text='page')]
        with self.assertRaisesRegex(ValueError, 'unfinished transaction.*' + identity):
            store.apply('wiki-build', operation, {str(target): None})
        self.assertFalse(target.exists())
        existing['status'] = 'complete'
        store.save(existing)
        self.assertEqual([r['id'] for r in store.records()], [identity])
        store.apply('wiki-build', operation, {str(target): None})
        self.assertEqual(target.read_text(), 'page')

    def test_termux_prefix_target_resolution_and_boundaries(self):
        from mappings import target_spec
        prefix = self.root / 'prefix space ü' / 'usr'
        termux = catalog.Catalog(self.repo, 'termux')
        target = '${PREFIX}/share/figlet/-dots.flf'
        with patch.dict(os.environ, PREFIX=str(prefix)):
            expected = str(prefix / 'share/figlet/-dots.flf')
            self.assertEqual(termux.target(target), expected)
            self.assertEqual(target_spec(termux, expected), target)
            self.assertFalse(prefix.exists())
            for platform in ('linux', 'wsl', 'windows'):
                self.assertIsNone(catalog.Catalog(self.repo, platform).target(target))
            for suffix in ('../escape', 'share/../../escape', 'bad\nname'):
                with self.assertRaises(ValueError):
                    termux.target('${PREFIX}/' + suffix)
        for value in ('relative/usr', str(prefix / '../escape'), '/', str(prefix) + '\n', str(prefix) + '\x7f'):
            with patch.dict(os.environ, PREFIX=value):
                with self.assertRaisesRegex(ValueError, 'PREFIX must'):
                    termux.target(target)
                self.assertIsNone(catalog.Catalog(self.repo, 'windows').target(target))
        with patch.dict(os.environ, PREFIX=''):
            self.assertIsNone(termux.target(target))
        with patch.dict(os.environ):
            os.environ.pop('PREFIX', None)
            self.assertIsNone(termux.target(target))

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
        self.env = patch.dict(os.environ, {"HOME": str(self.home), "DOTS": str(self.repo), "XDG_CONFIG_HOME": str(self.home / ".config"),
                                          "XDG_STATE_HOME": str(self.home / ".state"), "XDG_CACHE_HOME": str(self.home / ".cache")})
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
        native = [sys.executable, '-B', str(self.repo / 'lib/dots/cli.py')]
        for route in ('list', 'ls'):
            help_text = call('help', 'files', route)
            for option in ('--view', '--short', '--default', '--verbose'):
                self.assertIn(option, help_text)
            expected = call('files', 'list', '-s')
            self.assertEqual(call('files', route, '-s'), expected)
            result = subprocess.run([*native, 'files', route, '-s'], text=True, capture_output=True, check=True)
            self.assertEqual(result.stdout, expected)
            choices = call('__complete', 'zsh', '4', '--', 'dots', 'files', route, '--view', '')
            for value in ('short', 'default', 'verbose'):
                self.assertIn('candidate\t' + value + '\t', choices)
        self.assertIn('--dry-run', call('help', 'files', 'check'))
        for shell in ('bash', 'zsh', 'fish'):
            self.assertIn('check', call('__complete', shell, '2', '--', 'dots', 'files', 'ch'))
            self.assertIn('--yes', call('__complete', shell, '3', '--', 'dots', 'files', 'check', '--'))
            self.assertIn('dots', call('__complete', shell, '4', '--', 'dots', 'files', 'check', '--repo', 'd'))
        self.assertEqual(json.loads(call('files', 'check', '--dry-run', '--json'))['action'], 'check')
        for route in ('stash', 'edit', 'repair'):
            self.assertIn('--dry-run', call('help', 'files', route))
            for shell in ('bash', 'zsh', 'fish'):
                self.assertIn(route, call('__complete', shell, '2', '--', 'dots', 'files', route[:2]))
                self.assertIn('--yes', call('__complete', shell, '3', '--', 'dots', 'files', route, '--'))
                self.assertIn('dots:app', call('__complete', shell, '3', '--', 'dots', 'files', route, 'dots:'))
        self.assertEqual(json.loads(call('files', 'repair', '--dry-run', '--json'))['action'], 'repair')
        self.assertIn("--strategy", call("help", "files", "track"))
        discovery_help = call("help", "files", "discover")
        for flag in ("--verbose", "--all"):
            self.assertIn(flag, discovery_help)
            self.assertIn("candidate\t" + flag + "\t", call("__complete", "zsh", "4", "--", "dots", "files", "discover", "--system", "--"))
        self.assertEqual(call("files", "source", "dots:app").strip(), str(self.repo / "config/app"))
        self.assertIn("dots:app", call("__complete", "zsh", "3", "--", "dots", "files", "show", "dots:"))
        self.assertIn("dots", call("__complete", "fish", "4", "--", "dots", "files", "list", "--repo", "d"))
        with patch.dict(os.environ, {"DOTS_COLOR": "always", "DOTS_ICONS": "always"}):
            hints = call("__complete", "zsh", "3", "--", "dots", "files", "show", "dots:")
            self.assertIn("candidate\tdots:app\t", hints)
            self.assertNotIn("\x1b", hints)


    def test_pretty_output_preserves_machine_interfaces(self):
        cmd = [sys.executable, "-B", str(ROOT / "lib/dots/files/catalog.py")]
        env = dict(os.environ, DOTS_COLOR="always", DOTS_ICONS="never", COLUMNS="40")
        def run(*args):
            p = subprocess.run(cmd + list(args), env=env, text=True, capture_output=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            return p.stdout
        display = run("list", "--default")
        self.assertIn("\x1b[", display)
        self.assertIn("[+] linked", display)
        self.assertIn("Source", display)
        self.assertIn("Target", run("show", "dots:app"))
        self.assertIn("File sources", run("sources"))
        self.assertIn("No matching resources", run("list", "--app", "absent"))
        self.assertEqual(run("source", "dots:app"), str(self.repo / "config/app") + "\n")
        self.assertNotIn("\x1b", run("list", "--json"))
        self.assertEqual(json.loads(run("list", "--json"))["resources"][0]["status"], "linked")
        self.assertFalse((self.repo / ".dots/files.lock").exists())
        env.update(DOTS_COLOR="never", DOTS_ICONS="always")
        self.assertNotIn("\x1b", run("list"))
        self.assertIn("", run("list", "--default"))
        env.update(DOTS_COLOR="auto", DOTS_ICONS="auto")
        self.assertTrue(run("list").startswith("dots:app\tlinked\t"))

    @unittest.skipIf(os.name == 'nt', 'POSIX terminal fixture')
    def test_terminal_presentation_and_no_color(self):
        import fcntl
        import pty
        import struct
        import termios
        from resources import cells
        cmd = [sys.executable, "-B", str(ROOT / "lib/dots/files/catalog.py"), "list"]
        for width, extra, colored in [(40, {}, True), (49, {}, True), (50, {}, True), (80, {"NO_COLOR": "1"}, False),
                                      (120, {"TERM": "dumb"}, False), (24, {"DOTS_COLOR": "never"}, False)]:
            env = dict(os.environ, TERM="xterm-256color", DOTS_COLOR="auto", DOTS_ICONS="never", NO_COLOR="")
            env.update(extra)
            env.pop('COLUMNS', None)
            master, slave = pty.openpty()
            try:
                fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 24, width, 0, 0))
                proc = subprocess.run(cmd, env=env, stdout=slave, stderr=subprocess.PIPE, timeout=10)
                os.close(slave); slave = None
                output = b""
                while True:
                    try:
                        chunk = os.read(master, 4096)
                    except OSError:
                        break
                    if not chunk:
                        break
                    output += chunk
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(b"\x1b[" in output, colored)
                self.assertIn(b"->", output)
                plain = re.sub(r'\x1b\[[0-9;]*m', '', output.decode())
                self.assertEqual(plain.splitlines()[0] == '', width < 50)
                self.assertTrue(all(cells(line) <= width for line in plain.splitlines()), plain)
            finally:
                if slave is not None:
                    os.close(slave)
                os.close(master)

    def test_list_groups_human_statuses_and_preserves_script_order(self):
        rows = []
        for name in ('a-missing', 'b-stashed', 'c-linked', 'd-linked', 'e-existing'):
            source = self.repo / 'config' / name
            source.write_text(name)
            if name.endswith('linked'):
                (self.home / name).symlink_to(source)
            if name == 'e-existing':
                (self.home / name).write_text('preexisting')
            rows.append(dict(self.row, id=name, source='config/' + name,
                             target='${HOME}/' + name, strategy='link', enabled=name != 'b-stashed'))
        self.write('files', dict(schema=1, repository='dots', resources=rows))
        cmd = [sys.executable, '-B', str(ROOT / 'lib/dots/files/catalog.py'), 'list']
        env = dict(os.environ, DOTS_COLOR='never', DOTS_ICONS='never', DOTS_PROGRESS='never', COLUMNS='120')
        def listing(*args, **extra):
            return subprocess.run([*cmd, *args], env=dict(env, **extra), capture_output=True,
                                  text=True, check=True, timeout=20).stdout
        grouped = ['c-linked', 'd-linked', 'b-stashed', 'a-missing', 'e-existing']
        stashes_last = ['c-linked', 'd-linked', 'a-missing', 'e-existing', 'b-stashed']
        alphabetical = sorted(grouped)
        def check_order(output, expected):
            positions = [output.index(name) for name in expected]
            self.assertEqual(positions, sorted(positions), output)
        for mode in ('short', 'default', 'verbose'):
            with self.subTest(mode=mode):
                check_order(listing('--view', mode), grouped)
                check_order(listing('--view', mode, COLUMNS='50'), grouped)
                check_order(listing('--view', mode, COLUMNS='49'), stashes_last if mode == 'short' else grouped)
                check_order(listing('--view', mode, '--sort', 'id'), alphabetical)
        for width in ('49', '50'):
            for sort in ('id', 'app'):
                check_order(listing('--short', '--sort', sort, COLUMNS=width), alphabetical)
        fallback = listing(COLUMNS='49', DOTS_MENU_CAPTURE='1')
        self.assertEqual(fallback, listing('--short', COLUMNS='49'))
        self.assertIn('\n[missing]\n', fallback)
        check_order(fallback, stashes_last)
        raw = listing()
        check_order(raw, alphabetical)
        self.assertTrue(all(len(line.split('\t')) == 4 for line in raw.splitlines()))
        self.assertEqual(listing(COLUMNS='49'), raw)
        json_rows = listing('--json')
        self.assertEqual(json_rows, listing('--json', '-s', DOTS_ICONS='always'))
        self.assertEqual(json_rows, listing('--json', '-s', COLUMNS='49', DOTS_COLOR='always', DOTS_ICONS='always'))
        self.assertEqual([row['id'] for row in json.loads(json_rows)['resources']],
                         ['dots:' + name for name in alphabetical])

        pref_dir = self.repo / 'default'
        pref_dir.mkdir()
        (pref_dir / 'config.json').write_text(json.dumps(dict(schema=1, apps={
            'files': {'list_view': 'verbose', 'group_by_status': False}})))
        report = listing(DOTS_MENU_CAPTURE='1')
        check_order(report, alphabetical)
        self.assertIn('Strategy', report)
        check_order(listing('-s', COLUMNS='49'), alphabetical)
        check_order(listing(COLUMNS='49', DOTS_MENU_CAPTURE='1'), alphabetical)
        self.assertNotIn('Strategy', listing('-s'))
        self.assertEqual(listing(), raw)
        self.assertEqual(listing('--json'), json_rows)

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

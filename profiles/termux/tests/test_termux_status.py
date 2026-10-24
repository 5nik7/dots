"""Isolated API/cache fixtures. Never request live Android permissions."""

from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
import pty
import select
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
from termux_status import cache, cli, completions, display, providers


def args(**kwargs):
    return SimpleNamespace(**dict({"cell": None, "include_self": False,
                                   "include_package": [], "exclude_package": []}, **kwargs))


class StatusTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="termux-status-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.environment = patch.dict(os.environ, {
            "HOME": str(self.root), "XDG_CACHE_HOME": str(self.root / "cache"),
            "XDG_DATA_HOME": str(self.root / "data"), "XDG_CONFIG_HOME": str(self.root / "config"),
            "BASH_COMPLETION_USER_DIR": "", "TERMUX__PREFIX": str(self.root / "prefix"),
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def invoke(self, module, *argv):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                status = cli.main(module, list(argv))
            except SystemExit as error:
                status = error.code
        return status, stdout.getvalue(), stderr.getvalue()

    def seed(self, module, provider, data, elapsed=0, error=None, enabled=True):
        document = cache.load(module)
        document["providers"][provider] = {
            "enabled": enabled, "error": error,
            "success": {**cache.stamp(), "mono": time.monotonic() - elapsed, "data": data},
        }
        cache.save(module, document)

    def test_volume_read_only_streams_and_thresholds(self):
        self.assertEqual(providers.command("volume"), ["termux-volume"])
        for value, state in [(0, "muted"), (1, "low"), (33, "low"), (34, "medium"),
                             (66, "medium"), (67, "high"), (100, "high")]:
            data = providers.volume([{"stream": "music", "volume": value, "max_volume": 100},
                                     {"stream": "ring", "volume": 3, "max_volume": 7}])
            self.seed("volume", "volume", data)
            result = json.loads(self.invoke("volume", "--cached", "--json")[1])
            self.assertEqual(result["state"], state)
            self.assertEqual(result["data"], dict(stream="music", volume=value, max_volume=100, percent=value))
            self.assertEqual(self.invoke("volume", "--cached", "--stream", "ring", "get", "percent"),
                             (0, "43\n", ""))
            self.assertEqual(self.invoke("volume", "--cached", "--stream=ring", "format", "{stream}:{percent}"),
                             (0, "ring:43\n", ""))
            self.assertIn("music:", self.invoke("volume", "--cached", "--both")[1])
        self.assertEqual(self.invoke("volume", "--cached", "--stream", "alarm", "get", "volume")[:2], (1, ""))
        self.assertEqual(self.invoke("volume", "--stream", "invalid")[0], 2)
        for raw in [None, {}, [], [None], [{"stream": []}],
                    [{"stream": "music", "volume": True, "max_volume": 10}],
                    [{"stream": "music", "volume": 11, "max_volume": 10}],
                    [{"stream": "music", "volume": 0, "max_volume": 0}],
                    [{"stream": "music", "volume": 1, "max_volume": 10}] * 2]:
            with self.subTest(raw=raw), self.assertRaises(providers.ProviderError):
                providers.volume(raw)
        self.assertFalse(cache.valid_data("volume", {"streams": {"music": {"volume": True, "max_volume": 10}}}))

    def test_volume_cache_failure_recovery_and_expiration(self):
        self.assertEqual(cache.due("volume", cache.empty()), ["volume"])
        self.assertEqual(self.invoke("volume", "--cached", "--text"), (0, "volume:?\n", ""))
        data = providers.volume([{"stream": "music", "volume": 5, "max_volume": 10}])
        with patch.object(cache, "collect", return_value=data):
            self.assertEqual(self.invoke("volume", "--refresh", "--text"), (0, "music:50%\n", ""))
        with patch.object(cache, "collect", side_effect=providers.ProviderError("command unavailable")):
            self.assertEqual(self.invoke("volume", "--refresh", "--text")[:2], (1, "music:50%~\n"))
        self.assertEqual(cache.due("volume", cache.load("volume")), [])
        with patch.object(cache, "collect", return_value=data):
            self.assertEqual(self.invoke("volume", "--refresh", "--text"), (0, "music:50%\n", ""))
        for elapsed, expected in [(6, "music:50%~"), (301, "volume:?")]:
            self.seed("volume", "volume", data, elapsed=elapsed)
            self.assertEqual(self.invoke("volume", "--cached", "--text", "--no-newline"), (0, expected, ""))

    def test_wifi_thresholds_and_invalid_strength(self):
        for rssi, level in [(-100, 0), (-86, 0), (-85, 1), (-76, 1), (-75, 2),
                            (-68, 2), (-67, 3), (-56, 3), (-55, 4), (-1, 4),
                            (-127, None), (0, None), (2147483647, None), (True, None), (None, None)]:
            with self.subTest(rssi=rssi):
                data = providers.wifi({"supplicant_state": "COMPLETED", "rssi": rssi})
                self.assertEqual(data["level"], level)
                self.assertTrue(data["connected"])
        self.assertFalse(providers.wifi({"supplicant_state": "DISCONNECTED", "rssi": -40})["connected"])
        self.assertFalse(providers.wifi({"API_ERROR": "No current connection"})["connected"])
        with self.assertRaises(providers.ProviderError):
            providers.wifi({"error": "permission"})

    def test_cells_registered_selection_ties_and_sentinels(self):
        raw = [{"registered": False, "level": 4}, {"registered": True, "level": 2, "type": "lte"},
               {"registered": True, "level": 4, "dbm": -75, "type": "nr"},
               {"registered": True, "level": 4, "dbm": -70, "type": "lte"},
               {"registered": True, "level": 2147483647, "dbm": 2147483647}]
        self.seed("cell", "cells", providers.cells(raw))
        result = display.snapshot("cell", cache.load("cell"), args())
        self.assertEqual((result["state"], result["data"]["index"], result["data"]["registered_count"]),
                         ("registered", 2, 4))
        self.assertIsNone(result["data"]["registered"][3]["dbm"])
        self.assertEqual(self.invoke("cell", "--cached", "--cell", "1", "get", "level"), (0, "2\n", ""))
        self.assertEqual(self.invoke("cell", "--cached", "--cell", "99", "get", "level")[0:2], (1, ""))

    def test_device_boolean_and_identifier_reduction(self):
        data = providers.device({"data_enabled": "true", "network_roaming": False,
                                 "network_operator_name": "Carrier", "data_state": "connected",
                                 "device_id": "SECRET", "sim_serial_number": "SECRET"})
        self.assertTrue(data["data_enabled"])
        self.assertFalse(data["roaming"])
        self.assertNotIn("SECRET", json.dumps(data))

    def test_notification_privacy_and_filters(self):
        raw = [{"packageName": package, "title": "SECRET_TITLE", "content": "SECRET_BODY",
                "lines": ["SECRET_LINES"]} for package in ("com.termux", "com.termux.api", "a.app", "a.app", "b.app")]
        with patch.object(cache, "collect", return_value=providers.notifications(raw)):
            status, output, error = self.invoke("notification", "--refresh", "--json")
        self.assertEqual((status, error), (0, ""))
        self.assertEqual(json.loads(output)["data"]["count"], 3)
        for flags, count in [((), 3), (("--include-self",), 5), (("--include-package", "a.app"), 2),
                             (("--exclude-package", "a.app"), 1),
                             (("--include-package", "a.app", "--include-package", "b.app"), 3),
                             (("--include-package", "a.app", "--exclude-package", "a.app"), 0)]:
            self.assertEqual(self.invoke("notification", "--cached", *flags, "get", "count"), (0, f"{count}\n", ""))
        artifacts = output + error + "".join(p.read_text() for p in cache.cache_dir().glob("*.json"))
        self.assertNotIn("SECRET", artifacts)
        self.assertNotIn("title", artifacts)
        self.assertNotIn("content", artifacts)

    def test_location_toggle_and_denial(self):
        for mode in range(4):
            self.assertEqual(providers.location(str(mode)), {"enabled": mode != 0, "mode": mode})
        for value in ("null", "4", "Permission denied", ""):
            with self.assertRaises(providers.ProviderError):
                providers.location(value)
        with patch.object(cache, "collect", side_effect=providers.ProviderError("request failed")):
            status, output, error = self.invoke("location", "--refresh", "--text")
        self.assertEqual((status, output), (1, "location:?\n"))
        self.assertIn("request failed", error)
        self.assertEqual(cache.due("location", cache.load("location")), [])

    def test_output_contract_and_templates(self):
        self.seed("wifi", "wifi", providers.wifi({"supplicant_state": "COMPLETED", "rssi": -60, "ssid": "Test\n\x1bnet"}))
        for flags, expected in [(("get", "level"), "3\n"), (("--get=connected",), "true\n"),
                                (("-g", "ssid", "--no-newline"), "Testnet"),
                                (("format", "{{{state}}}:{level}"), "{connected}:3\n"),
                                (("--text",), "wifi:3/4\n")]:
            self.assertEqual(self.invoke("wifi", "--cached", *flags), (0, expected, ""))
        for template in ("{nope}", "{data[level]}", "{state.foo}", "{level:02}", "{level!r}", "{"):
            self.assertEqual(self.invoke("wifi", "--cached", "format", template)[0:2], (2, ""))
        self.assertEqual(self.invoke("wifi", "--cached", "get", "error")[0:2], (1, ""))
        result = json.loads(self.invoke("wifi", "--cached", "--json")[1])
        self.assertEqual(set(result), set(display.COMMON_FIELDS) | {"data"})
        self.assertNotIn("\x1b", self.invoke("wifi", "--cached")[1])

    def test_metadata_never_touches_cache_or_api(self):
        with patch.object(cache, "request", side_effect=AssertionError("refresh")), \
                patch.object(cache, "load", side_effect=AssertionError("cache")):
            for module in providers.PROVIDERS:
                for flags in (("--help",), ("--fields", "--refresh"), ("completion", "bash", "--refresh")):
                    self.assertEqual(self.invoke(module, *flags)[0], 0)
        self.assertFalse(cache.cache_dir().exists())

    def test_cold_fresh_stale_expired_and_reboot(self):
        self.assertEqual(self.invoke("wifi", "--cached", "--text"), (0, "wifi:?\n", ""))
        self.assertFalse(cache.cache_dir().exists())
        data = providers.wifi({"supplicant_state": "DISCONNECTED"})
        for elapsed, text, stale in [(0, "wifi:off", False), (11, "wifi:off~", True), (301, "wifi:?", False)]:
            self.seed("wifi", "wifi", data, elapsed=elapsed)
            result = json.loads(self.invoke("wifi", "--cached", "--json")[1])
            self.assertEqual((result["text"], result["stale"]), (text, stale))
        with patch.object(cache, "boot_id", return_value="another-boot"):
            self.assertEqual(self.invoke("wifi", "--cached", "--text"), (0, "wifi:?\n", ""))

    def test_permission_gate_failure_and_reenable(self):
        for module in ("cell", "notification"):
            self.assertEqual(cache.due(module, cache.empty()), [])
            self.assertEqual(self.invoke(module, "--text")[0], 0)
        with patch.object(cache, "collect", return_value={"packages": {"a.app": 1}}):
            self.assertEqual(self.invoke("notification", "--refresh", "--text"), (0, "notifications:1\n", ""))
        with patch.object(cache, "collect", side_effect=providers.ProviderError("denied")):
            status, output, error = self.invoke("notification", "--refresh", "--text")
        self.assertEqual((status, output), (1, "notifications:1~\n"))
        self.assertIn("denied", error)
        self.assertEqual(cache.due("notification", cache.load("notification")), [])
        with patch.object(cache, "collect", return_value={"packages": {}}):
            self.assertEqual(self.invoke("notification", "--refresh", "--text"), (0, "notifications:0\n", ""))
        self.assertTrue(cache.load("notification")["providers"]["notifications"]["enabled"])

    def test_partial_cell_provider_failure(self):
        def collect(provider):
            if provider == "device":
                raise providers.ProviderError("denied")
            return providers.cells([{"registered": True, "level": 4}])
        with patch.object(cache, "collect", side_effect=collect):
            status, output, error = self.invoke("cell", "--refresh", "--text")
        self.assertEqual((status, output), (1, "cell:4/4\n"))
        self.assertIn("device: denied", error)
        document = cache.load("cell")
        document["providers"]["cells"]["success"]["mono"] -= 16
        self.assertEqual(cache.due("cell", document), ["cells"])
        self.assertFalse(document["providers"]["device"]["enabled"])

    def test_cell_signal_does_not_establish_data_activity_or_freshness(self):
        signal = providers.cells([{"registered": True, "level": 4}])
        self.seed("cell", "cells", signal)
        for elapsed, error in ((0, None), (20, None), (0, "command unavailable"), (301, None)):
            self.seed("cell", "device", providers.device({"data_enabled": False, "data_state": "disconnected"}),
                      elapsed=elapsed, error=error, enabled=error is None)
            result = json.loads(self.invoke("cell", "--cached", "--json")[1])
            self.assertEqual((result["state"], result["data"]["level"]), ("registered", 4))
            if elapsed > cache.MAX_AGE:
                self.assertIsNone(result["data"]["data_enabled"])
                self.assertIsNone(result["data"]["data_state"])
                self.assertIsNone(result["data"]["device_stale"])
            else:
                self.assertIs(result["data"]["data_enabled"], False)
                self.assertEqual(result["data"]["device_stale"], bool(error) or elapsed >= providers.TTL["cell"])
        # Valid device responses can omit activity fields altogether.
        self.seed("cell", "device", providers.device({"network_type": "LTE"}))
        result = json.loads(self.invoke("cell", "--cached", "--json")[1])
        self.assertIsNone(result["data"]["data_enabled"])
        self.assertIsNone(result["data"]["data_state"])
        self.assertEqual(result["data"]["level"], 4)
        # Stale signal and fresh inactive device data remain independent.
        self.seed("cell", "cells", signal, elapsed=20)
        self.seed("cell", "device", providers.device({"data_enabled": False, "data_state": "disconnected"}))
        result = json.loads(self.invoke("cell", "--cached", "--json")[1])
        self.assertTrue(result["stale"])
        self.assertIs(result["data"]["device_stale"], False)

    def test_wifi_failure_suspension_expiration_and_explicit_recovery(self):
        connected = providers.wifi({"supplicant_state": "COMPLETED", "rssi": -50})
        with patch.object(cache, "collect", return_value=connected):
            self.assertEqual(self.invoke("wifi", "--refresh", "--json")[0], 0)
        with patch.object(cache, "collect", side_effect=providers.ProviderError("command unavailable")):
            code, output, error = self.invoke("wifi", "--refresh", "--json")
        self.assertEqual(code, 1)
        self.assertTrue(json.loads(output)["stale"])
        self.assertIn("command unavailable", error)
        self.seed("wifi", "wifi", connected, elapsed=301, error="command unavailable", enabled=False)
        with patch.object(cache.subprocess, "Popen", side_effect=AssertionError("suspended worker launched")):
            for _ in range(3):
                code, output, error = self.invoke("wifi", "--json")
                self.assertEqual((code, error), (0, ""))
                self.assertIsNone(json.loads(output)["data"]["connected"])
        self.assertEqual(cache.due("wifi", cache.load("wifi")), [])
        with patch.object(cache, "collect", return_value=connected):
            code, output, error = self.invoke("wifi", "--refresh", "--json")
        self.assertEqual((code, error), (0, ""))
        self.assertTrue(json.loads(output)["data"]["connected"])
        self.assertFalse(json.loads(output)["stale"])
        self.assertTrue(cache.load("wifi")["providers"]["wifi"]["enabled"])

    def test_corrupt_cache_cannot_authorize_queries(self):
        cache.prepare()
        path = cache.cache_dir() / "notification.json"
        for value in ("bad json", "[]", '{"version":1,"providers":[]}',
                      '{"version":1,"providers":{"notifications":{"enabled":true,"error":null}}}',
                      '{"version":1,"providers":{"notifications":{"enabled":true,"error":null,"success":{"data":{}}}}}'):
            path.write_text(value)
            self.assertEqual(cache.due("notification", cache.load("notification")), [])

    def test_cache_permissions_and_exclusive_lock(self):
        descriptor = cache.acquire("wifi")
        try:
            self.assertIsNone(cache.acquire("wifi"))
            self.assertEqual(cache.request("wifi", explicit=True), ["refresh already in progress"])
        finally:
            os.close(descriptor)
        descriptor = cache.acquire("wifi")
        os.close(descriptor)
        self.seed("wifi", "wifi", providers.wifi({"supplicant_state": "DISCONNECTED"}))
        self.assertEqual(cache.cache_dir().stat().st_mode & 0o777, 0o700)
        self.assertEqual((cache.cache_dir() / "wifi.json").stat().st_mode & 0o777, 0o600)

    def test_completion_install_backup_noop_and_preflight(self):
        destination = self.root / "completion files"
        flags = ("completion", "--all", "--install", "--dir", str(destination))
        self.assertEqual(self.invoke("wifi", *flags)[0:2], (0, ""))
        self.assertEqual(len(list(destination.iterdir())), 3)
        self.assertIn("unchanged:", self.invoke("wifi", *flags)[2])
        target = destination / "_termux-wifi-status"
        target.write_text("previous")
        self.assertEqual(self.invoke("wifi", *flags)[0:2], (0, ""))
        backup = next(destination.glob("*.bak.*"))
        self.assertEqual(backup.read_text(), "previous")
        target.unlink()
        target.symlink_to(backup)
        bash_target = destination / "termux-wifi-status.bash"
        bash_target.unlink()
        self.assertEqual(self.invoke("wifi", *flags)[0:2], (1, ""))
        self.assertFalse(bash_target.exists())

    def test_completion_default_locations_and_partial_failure(self):
        targets = completions.completion_targets("termux-wifi-status", cli.SHELLS, None)
        self.assertEqual([str(p.relative_to(self.root)) for _, p in targets], [
            "data/bash-completion/completions/termux-wifi-status.bash",
            "prefix/share/zsh/site-functions/_termux-wifi-status",
            "config/fish/completions/termux-wifi-status.fish"])
        original = os.replace
        def replace(source, target):
            if target.name == "_termux-wifi-status":
                raise PermissionError("simulated denial")
            original(source, target)
        with patch.object(os, "replace", side_effect=replace):
            status, output, error = self.invoke("wifi", "completion", "--all", "--install", "--dir", str(self.root / "dest"))
        self.assertEqual((status, output), (1, ""))
        self.assertIn("installed:", error)
        self.assertIn("simulated denial", error)
        self.assertEqual(len(list((self.root / "dest").iterdir())), 1)

    def test_invalid_cli(self):
        for flags in (("--cached", "--refresh"), ("--install",), ("completion", "--all"),
                      ("completion", "bash", "--dir", "x"), ("completion", "nope"), ("--get", "bogus")):
            self.assertEqual(self.invoke("wifi", *flags)[0:2], (2, ""))
        self.assertEqual(self.invoke("cell", "--cell", "0")[0:2], (2, ""))

    def test_warm_reads_never_start_api_or_worker(self):
        self.seed("wifi", "wifi", providers.wifi({"supplicant_state": "COMPLETED", "rssi": -50}))
        with patch.object(cache.subprocess, "Popen", side_effect=AssertionError("launched worker")):
            self.assertEqual(self.invoke("wifi", "--text"), (0, "wifi:4/4\n", ""))

    def test_real_failed_cell_refresh_is_bounded_and_suspends_requests(self):
        for name in ("termux-telephony-cellinfo", "termux-telephony-deviceinfo"):
            fake = self.root / name
            fake.write_text("#!" + sys.executable + "\nimport time\ntime.sleep(60)\n")
            fake.chmod(0o700)
        with patch.dict(os.environ, {"PATH": str(self.root) + os.pathsep + os.environ["PATH"]}):
            started = time.monotonic()
            status, output, error = self.invoke("cell", "--refresh", "--text")
            elapsed = time.monotonic() - started
        self.assertEqual((status, output), (1, "cell:?\n"))
        self.assertLess(elapsed, 5)
        self.assertIn("timed out", error)
        self.assertEqual(cache.due("cell", cache.load("cell")), [])
        descriptor = cache.acquire("cell")
        self.assertIsNotNone(descriptor)
        os.close(descriptor)

    def test_api_error_diagnostics_do_not_echo_private_output(self):
        with patch.object(providers, "run_command", return_value='{"error":"SECRET_BODY"}'):
            with self.assertRaises(providers.ProviderError) as caught:
                providers.collect("notifications")
        self.assertNotIn("SECRET", str(caught.exception))
        with self.assertRaises(providers.ProviderError) as caught:
            providers.run_command([sys.executable, "-c", "import sys; print('SECRET_BODY'); print('SECRET_TITLE',file=sys.stderr); sys.exit(1)"])
        self.assertNotIn("SECRET", str(caught.exception))

    def test_parallel_readers_launch_one_worker(self):
        fake = self.root / "termux-wifi-connectioninfo"
        marker = self.root / "calls"
        fake.write_text("#!" + sys.executable + "\nimport time\nfrom pathlib import Path\n"
                        + f"with Path({str(marker)!r}).open('a') as f: f.write('call\\n')\n"
                        + "time.sleep(.5)\nprint('{\"supplicant_state\":\"COMPLETED\",\"rssi\":-50}')\n")
        fake.chmod(0o700)
        with patch.dict(os.environ, {"PATH": str(self.root) + os.pathsep + os.environ["PATH"]}):
            readers = [subprocess.Popen([sys.executable, "-B", str(ROOT / "bin/termux-wifi-status"), "--text"],
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(8)]
            for reader in readers:
                output, error = reader.communicate(timeout=5)
                self.assertEqual((reader.returncode, error), (0, b""))
                self.assertIn(output, (b"wifi:?\n", b"wifi:4/4\n"))
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if cache.load("wifi")["providers"].get("wifi", {}).get("enabled"):
                    break
                time.sleep(.03)
            else:
                self.fail("worker did not finish")
        self.assertEqual(marker.read_text(), "call\n")
        self.assertEqual(self.invoke("wifi", "--cached", "--text"), (0, "wifi:4/4\n", ""))
        fd = cache.acquire("wifi")
        self.assertIsNotNone(fd)
        os.close(fd)

    def test_timeout_kills_process_group_and_bounds_output(self):
        pidfile = self.root / "pid"
        program = ("import subprocess,sys,time; from pathlib import Path; "
                   "p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); "
                   f"Path({str(pidfile)!r}).write_text(str(p.pid)); time.sleep(60)")
        started = time.monotonic()
        with self.assertRaises(providers.ProviderError):
            providers.run_command([sys.executable, "-c", program], timeout=.7)
        self.assertLess(time.monotonic() - started, 2)
        pid = int(pidfile.read_text())
        statfile = Path(f"/proc/{pid}/stat")
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            try:
                if statfile.read_text().rsplit(")", 1)[1].split()[0] == "Z":
                    break
            except OSError:
                break
            time.sleep(.02)
        else:
            self.fail("timed-out descendant is still running")
        with self.assertRaisesRegex(providers.ProviderError, "size limit"):
            providers.run_command([sys.executable, "-c", "print('x'*3000000)"])


class NativeCompletionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="termux-wifi-status-completion-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.env = dict(os.environ, HOME=str(self.root), ZDOTDIR=str(self.root), TERM="xterm-256color",
                        XDG_DATA_HOME=str(self.root / "data"), XDG_CONFIG_HOME=str(self.root / "config"),
                        XDG_CACHE_HOME=str(self.root / "cache"))
        self.env.pop("TERMUX_APP__PID", None)
        self.marker = self.root / "helper-executed"
        executable = self.root / "termux-wifi-status"
        executable.write_text("#!" + shutil.which("sh") + "\nprintf invoked > " + shlex.quote(str(self.marker)) + "\n")
        executable.chmod(0o700)
        self.env["PATH"] = str(self.root) + os.pathsep + self.env["PATH"]
        self.sources = {}
        for shell in cli.SHELLS:
            path = self.root / ("_termux-wifi-status" if shell == "zsh" else "completion." + shell)
            path.write_text(completions.completion_source("termux-wifi-status", display.COMMON_FIELDS + display.DATA_FIELDS["wifi"], cli.OPTIONS, shell))
            self.sources[shell] = path

    def run_shell(self, shell, code):
        if not shutil.which(shell):
            self.skipTest(shell + " is not installed")
        flags = {"bash": ["--noprofile", "--norc"], "fish": ["--no-config"], "zsh": ["-f"]}[shell]
        result = subprocess.run([shell, *flags, "-c", code], env=self.env, cwd=self.root,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual((result.returncode, result.stderr), (0, ""), result)
        self.assertFalse(self.marker.exists(), "completion executed the helper")
        return result.stdout

    def test_shell_syntax(self):
        for shell, source in self.sources.items():
            with self.subTest(shell=shell):
                if not shutil.which(shell):
                    continue
                result = subprocess.run([shell, "-n", str(source)], env=self.env, capture_output=True,
                                        text=True, timeout=10)
                self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))

    def test_all_modules_shell_syntax_and_extra_flags(self):
        for module in providers.PROVIDERS:
            command = "termux-" + module + "-status"
            options = cli.OPTIONS + cli.EXTRA_OPTIONS.get(module, ())
            for shell in cli.SHELLS:
                if not shutil.which(shell):
                    continue
                source = self.root / (module + "." + shell)
                source.write_text(completions.completion_source(command, display.COMMON_FIELDS + display.DATA_FIELDS[module], options, shell))
                result = subprocess.run([shell, "-n", str(source)], capture_output=True, text=True, timeout=10)
                self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))
                if shell == "bash":
                    code = ('source ' + shlex.quote(str(source)) + '\nCOMP_WORDS=(' + command
                            + ' --); COMP_CWORD=1\n_' + command.replace('-', '_')
                            + '\nprintf "%s\\n" "${COMPREPLY[@]}"')
                    candidates = self.run_shell(shell, code).splitlines()
                elif shell == "fish":
                    code = 'source ' + shlex.quote(str(source)) + '; complete -C ' + shlex.quote(command + ' --')
                    candidates = [line.split('\t')[0] for line in self.run_shell(shell, code).splitlines()]
                else:
                    continue
                self.assertIn('--no-newline', candidates)
                for names, _, _, _ in cli.EXTRA_OPTIONS.get(module, ()):
                    self.assertIn(names[0], candidates)
                if module == "volume":
                    if shell == "bash":
                        code = ('source ' + shlex.quote(str(source)) + '\nCOMP_WORDS=(' + command
                                + ' --stream r); COMP_CWORD=2\n_termux_volume_status'
                                + '\nprintf "%s\\n" "${COMPREPLY[@]}"')
                    else:
                        code = 'source ' + shlex.quote(str(source)) + '; complete -C "termux-volume-status --stream r"'
                    self.assertIn('ring', self.run_shell(shell, code).splitlines())

    def test_bash_candidates(self):
        cases = [(('get', 'lev'), 'level'), (('--get', 'rs'), 'rssi'),
                 (('--get=le',), '--get=level'), (('completion', 'z'), 'zsh'),
                 (('--completion', 'f'), 'fish'), (('--completion', '--'), '--all'),
                 (('completion', 'bash', '--'), '--install'), (('format', '{lev'), '{level}'),
                 (('format', '{level}/{sta'), '{level}/{state}'),
                 (('--format={le',), '--format={level}')]
        for words, expected in cases:
            with self.subTest(words=words):
                code = ('source ' + shlex.quote(str(self.sources['bash']))
                        + '\nCOMP_WORDS=(termux-wifi-status ' + ' '.join(shlex.quote(word) for word in words)
                        + '); COMP_CWORD=' + str(len(words))
                        + '\n_termux_wifi_status\nprintf "%s\\n" "${COMPREPLY[@]}"')
                self.assertIn(expected, self.run_shell('bash', code).splitlines())
        (self.root / "target directory").mkdir()
        code = ('source ' + shlex.quote(str(self.sources['bash']))
                + '\nCOMP_WORDS=(termux-wifi-status completion bash --install --dir tar); COMP_CWORD=5'
                + '\n_termux_wifi_status\nprintf "%s\\n" "${COMPREPLY[@]}"')
        self.assertIn('target directory', self.run_shell('bash', code).splitlines())

    def test_fish_candidates(self):
        cases = [("get lev", "level"), ("--get rs", "rssi"), ("--get=le", "--get=level"),
                 ("completion z", "zsh"), ("completion bash --", "--install"),
                 ("--completion f", "fish"), ("--completion --", "--all"),
                 ("format '{lev", "{level}"), ("format '{level}/{sta", "{level}/{state}")]
        for words, expected in cases:
            with self.subTest(words=words):
                code = ('source ' + shlex.quote(str(self.sources['fish']))
                        + '; complete -C ' + shlex.quote('termux-wifi-status ' + words))
                candidates = [line.split('\t')[0] for line in self.run_shell('fish', code).splitlines()]
                self.assertIn(expected, candidates)
        (self.root / "target-directory").mkdir()
        code = ('source ' + shlex.quote(str(self.sources['fish']))
                + '; complete -C "termux-wifi-status completion fish --install --dir tar"')
        self.assertIn('target-directory/', self.run_shell('fish', code))

    def test_zsh_native_tab_candidates(self):
        if not shutil.which("zsh"):
            self.skipTest("zsh is not installed")
        result_path = self.root / "candidates"
        init = self.root / "init.zsh"
        init.write_text(
            'fpath=(' + shlex.quote(str(self.root)) + ' $fpath)\nautoload -Uz compinit\ncompinit -D\n'
            + 'compadd() { local -a captured; builtin compadd -A captured "$@"; '
            + 'print -rl -- "${captured[@]}" >> ' + shlex.quote(str(result_path)) + '; builtin compadd "$@"; }\n'
            + '_capture() { _main_complete; print DONE >> ' + shlex.quote(str(result_path)) + '; }\n'
            + '_record_buffer() { print -r -- "BUFFER:$BUFFER" >> ' + shlex.quote(str(result_path))
            + '; print BUFFER_DONE >> ' + shlex.quote(str(result_path)) + '; }\n'
            + 'zle -C capture complete-word _capture\nbindkey "^I" capture\n'
            + 'zle -N _record_buffer\nbindkey "^X" _record_buffer\nPROMPT="READY> "\n')
        master, slave = pty.openpty()
        process = subprocess.Popen(['zsh', '-f'], stdin=slave, stdout=slave, stderr=slave,
                                   env=self.env, cwd=self.root, start_new_session=True)
        os.close(slave)

        def wait_for(predicate):
            deadline = time.monotonic() + 5
            output = b''
            while time.monotonic() < deadline:
                if select.select([master], [], [], .03)[0]:
                    output += os.read(master, 65536)
                if predicate(output):
                    return output
            self.fail('Zsh completion timed out: ' + repr(output))

        try:
            os.write(master, ('source ' + shlex.quote(str(init)) + '\n').encode())
            wait_for(lambda output: b'READY> ' in output and b'compinit' not in output.split(b'READY> ')[-1])
            cases = [('get lev', 'level'), ('--get rs', 'rssi'), ('--get=le', 'level'),
                     ('completion z', 'zsh'), ('completion bash --', '--install'),
                     ('--completion f', 'fish'), ('--completion --', '--all'),
                     ("--format='{lev", '{level}'),
                     ("format 'before {lev", 'before {level}'),
                     ("format '{lev", '{level}'), ("format '{level}/{stat", '{level}/{state}')]
            for words, expected in cases:
                with self.subTest(words=words):
                    result_path.unlink(missing_ok=True)
                    os.write(master, b'\x15' + ('termux-wifi-status ' + words).encode() + b'\t')
                    wait_for(lambda _: result_path.exists() and result_path.read_text().endswith('DONE\n'))
                    lines = result_path.read_text().splitlines()
                    self.assertIn(expected, lines)
                    if '{' in expected:
                        os.write(master, b'\x18')
                        wait_for(lambda _: result_path.read_text().endswith('BUFFER_DONE\n'))
                        lines = result_path.read_text().splitlines()
                        buffer = next(line.removeprefix('BUFFER:') for line in lines if line.startswith('BUFFER:'))
                        wanted = '--format=' + expected if words.startswith('--format=') else expected
                        self.assertEqual(shlex.split(buffer)[-1], wanted)
            self.assertFalse(self.marker.exists(), 'completion executed the helper')
        finally:
            os.write(master, b'\x15exit\n')
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
            os.close(master)


if __name__ == "__main__":
    unittest.main()

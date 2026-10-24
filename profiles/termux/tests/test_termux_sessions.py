"""Disposable procfs fixtures; never create or terminate live terminal sessions."""

from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import pty
import runpy
import select
import shlex
import shutil
import subprocess
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "bin" / "termux-sessions"
HELPER = runpy.run_path(str(SCRIPT))


class TermuxSessionsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.proc = Path(self.directory.name)
        self.add_process(999, parent=1, tty=0, directory="self")

    def add_process(self, pid, *, parent=100, sid=None, tty=1, state="S", started=1,
                    command="zsh", directory=None):
        fields = [state, str(parent), str(pid), str(pid if sid is None else sid),
                  str(os.makedev(136, tty) if tty else 0)] + ["0"] * 15
        fields[19] = str(started)
        path = self.proc / (directory or str(pid))
        path.mkdir()
        (path / "stat").write_text(f"{pid} ({command}) {' '.join(fields)}\n")

    def invoke(self, *args, environ=None):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                status = HELPER["main"](
                    list(args), proc_root=self.proc,
                    environ={"TERMUX_APP__PID": "100"} if environ is None else environ,
                )
            except SystemExit as error:
                status = error.code
        return status, stdout.getvalue(), stderr.getvalue()

    def test_filters_and_orders_sessions(self):
        self.add_process(201, tty=10, started=20)
        self.add_process(200, tty=3, started=20, command="bash")
        self.add_process(202, tty=2, started=10, command="top")  # exec replacement
        self.add_process(203, parent=200, sid=200)  # nested shell
        self.add_process(204, parent=300)  # tmux pane or editor terminal
        self.add_process(205, tty=0)  # background command
        self.add_process(206, state="Z")
        self.add_process(207, state="X")
        self.add_process(208, sid=200)  # not a session leader
        self.assertEqual(self.invoke(), (0, "termux:3\n", ""))
        self.assertEqual(self.invoke("--count"), (0, "3\n", ""))
        self.assertEqual(self.invoke("--list"), (
            0, "PID\tTTY\tCOMMAND\n202\tpts/2\ttop\n200\tpts/3\tbash\n201\tpts/10\tzsh\n", "",
        ))
        expected = {"count": 3, "sessions": [
            {"pid": 202, "tty": "pts/2", "command": "top"},
            {"pid": 200, "tty": "pts/3", "command": "bash"},
            {"pid": 201, "tty": "pts/10", "command": "zsh"},
        ]}
        self.assertEqual(self.invoke("--json"), (0, json.dumps(expected) + "\n", ""))

    def test_empty_snapshot(self):
        for args, output in [([], "termux:0\n"), (["--count"], "0\n"),
                             (["--list"], "PID\tTTY\tCOMMAND\n"),
                             (["--json"], '{"count": 0, "sessions": []}\n')]:
            with self.subTest(args=args):
                self.assertEqual(self.invoke(*args), (0, output, ""))

    def test_process_name_is_parsed_and_escaped(self):
        name = "a (b)\n\x1b\t\u202e"
        self.add_process(200, command=name)
        self.assertEqual(self.invoke("--list"), (0, "PID\tTTY\tCOMMAND\n200\tpts/1\ta (b)????\n", ""))
        status, output, error = self.invoke("--json")
        self.assertEqual((status, error), (0, ""))
        self.assertEqual(json.loads(output)["sessions"][0]["command"], name)
        self.assertEqual(len(output.splitlines()), 1)

    def test_missing_or_invalid_app_pid(self):
        for value in (None, "", "0", "-1", "abc", "12.3", " 100", "١٠٠"):
            with self.subTest(value=value):
                env = {} if value is None else {"TERMUX_APP__PID": value}
                self.assertEqual(self.invoke(environ=env), (
                    1, "", "termux-sessions: TERMUX_APP__PID must be a positive process ID\n",
                ))

    def test_disappearing_process_is_skipped(self):
        (self.proc / "200").mkdir()  # Gone before its stat record could be read.
        self.add_process(201)
        self.assertEqual(self.invoke("--count"), (0, "1\n", ""))

    def test_unreadable_process_fails_without_partial_stdout(self):
        self.add_process(200)
        original = Path.read_text

        def read(path, *args, **kwargs):
            if path == self.proc / "200" / "stat":
                raise PermissionError("denied")
            return original(path, *args, **kwargs)

        with patch.object(Path, "read_text", read):
            self.assertEqual(self.invoke("--count"), (
                1, "", "termux-sessions: cannot inspect process 200\n",
            ))

    def test_other_user_is_excluded(self):
        self.add_process(200)
        with patch.object(os, "getuid", return_value=os.getuid() + 1):
            self.assertEqual(self.invoke("--count"), (0, "0\n", ""))

    def test_unavailable_procfs(self):
        (self.proc / "self" / "stat").unlink()
        self.assertEqual(self.invoke(), (1, "", "termux-sessions: cannot read the process table\n"))

    def test_malformed_record_fails(self):
        self.add_process(200)
        (self.proc / "200" / "stat").write_text("invalid")
        self.assertEqual(self.invoke(), (1, "", "termux-sessions: cannot inspect process 200\n"))

    def test_tty_device_decoding(self):
        self.assertEqual(HELPER["tty_name"](os.makedev(137, 2)), "pts/258")
        self.assertEqual(HELPER["tty_name"](os.makedev(4, 1)), "4:1")

    def test_help_and_invalid_arguments_need_no_discovery(self):
        status, output, error = self.invoke("--help", environ={})
        self.assertEqual((status, error), (0, ""))
        self.assertIn("TERMUX_APP__PID", output)
        for args in (("--unknown",), ("--count", "--json"), ("extra",)):
            with self.subTest(args=args):
                status, output, error = self.invoke(*args, environ={})
                self.assertEqual((status, output), (2, ""))
                self.assertIn("error:", error)

    def test_queries_and_aliases(self):
        self.add_process(200, tty=3, started=10, command="bash")
        self.add_process(201, tty=10, started=20)
        expected = {"current": "1", "number": "1", "previous": "2", "next": "2",
                    "total": "2", "pid": "200", "tty": "pts/3", "command": "bash",
                    "first": "1", "last": "2"}
        for field, value in expected.items():
            for alias in ("get", "--get", "-g"):
                with self.subTest(field=field, alias=alias):
                    self.assertEqual(self.invoke(alias, field, "--tty", "/dev/pts/3"), (0, value + "\n", ""))
        for alias in ("format", "--format", "-f"):
            self.assertEqual(self.invoke(alias, "{{{number}}}/{total}: {command}", "--pid", "201"),
                             (0, "{2}/2: zsh\n", ""))
        self.assertEqual(self.invoke("--tty", "pts/10", "get", "next"), (0, "1\n", ""))
        self.assertEqual(self.invoke("--get=number", "--pid=200"), (0, "1\n", ""))

    def test_one_session_wraps_and_empty_total(self):
        self.assertEqual(self.invoke("get", "total"), (0, "0\n", ""))
        for field in ("number", "previous", "next", "first", "last"):
            status, output, error = self.invoke("get", field, "--tty", "pts/1")
            self.assertEqual((status, output), (1, ""))
            self.assertIn("session context unavailable", error)
        self.add_process(200)
        self.assertEqual(self.invoke("format", "{current} {previous} {next} {first} {last}", "--pid", "200"),
                         (0, "1 1 1 1 1\n", ""))

    def test_invalid_templates_precede_discovery(self):
        for template in ("{", "}", "{}", "{unknown}", "{pid.x}", "{pid[0]}", "{pid!r}",
                         "{number:02}", "{number:}", "{number:{total}}"):
            with self.subTest(template=template):
                status, output, error = self.invoke("format", template, environ={})
                self.assertEqual((status, output), (2, ""))
                self.assertIn("error:", error)
        self.assertEqual(self.invoke("format", "{{literal}}"), (0, "{literal}\n", ""))
        self.assertEqual(self.invoke("format", ""), (0, "\n", ""))

    def test_process_name_get_and_format_are_sanitized(self):
        self.add_process(200, command="a\n\x1b")
        self.assertEqual(self.invoke("get", "command", "--pid", "200"), (0, "a??\n", ""))
        self.assertEqual(self.invoke("format", "first\n{command}", "--pid", "200"), (0, "first\na??\n", ""))

    def test_direct_nested_and_explicit_ancestry(self):
        self.add_process(200)
        self.add_process(201, parent=200, sid=200)
        self.add_process(202, parent=201, sid=200)
        with patch.object(os, "getppid", return_value=202):
            self.assertEqual(self.invoke("get", "pid"), (0, "200\n", ""))
        self.assertEqual(self.invoke("get", "pid", "--pid", "202"), (0, "200\n", ""))
        for args in (("--pid", "99999"), ("--tty", "pts/999")):
            self.assertEqual(self.invoke("get", "number", *args)[:2], (1, ""))

    def test_bounded_and_cyclic_ancestry(self):
        self.add_process(200, parent=201)
        self.add_process(201, parent=200)
        self.assertEqual(HELPER["ancestry"](200, self.proc), [200, 201])
        for pid in range(1000, 1260):
            self.add_process(pid, parent=pid + 1)
        self.assertEqual(len(HELPER["ancestry"](1000, self.proc)), 256)

    def test_tmux_context_and_failure_modes(self):
        self.add_process(200, tty=1)
        self.add_process(201, tty=3)
        self.add_process(300, parent=1, tty=0)  # tmux server
        self.add_process(301, parent=300, tty=4)  # pane root
        self.add_process(302, parent=301, sid=301)
        self.add_process(400, parent=201, sid=201)  # viewing client
        env = {"TERMUX_APP__PID": "100", "TMUX": "/tmp/socket,300,0", "TMUX_PANE": "%1"}
        for clients, expected in (("400 0\n", (0, "2\n")), ("400 0\n401 0\n", (1, "")),
                                  ("", (1, "")), ("99999 0\n", (1, "")),
                                  ("400 1\n", (1, "")), ("400 0\n500 1\n", (0, "2\n"))):
            with self.subTest(clients=clients), patch.object(os, "getppid", return_value=302), \
                    patch.object(subprocess, "run", side_effect=[
                        SimpleNamespace(stdout="%1 301\n"), SimpleNamespace(stdout=clients),
                    ]) as query:
                self.assertEqual(self.invoke("get", "number", environ=env)[:2], expected)
                self.assertEqual(query.call_args_list[1].args[0][3], "%1")
                for call in query.call_args_list:
                    self.assertGreater(call.kwargs["timeout"], 0)
                    self.assertLessEqual(call.kwargs["timeout"], .250)
        with patch.object(os, "getppid", return_value=302), patch.object(subprocess, "run") as query:
            query.return_value.stdout = "%other 301\n"
            self.assertEqual(self.invoke("get", "number", environ=env)[:2], (1, ""))
            self.assertEqual(query.call_count, 1)
        for error in (FileNotFoundError(), subprocess.TimeoutExpired("tmux", .250),
                      subprocess.CalledProcessError(1, "tmux")):
            with patch.object(os, "getppid", return_value=302), \
                    patch.object(subprocess, "run", side_effect=error):
                self.assertEqual(self.invoke("get", "number", environ=env)[:2], (1, ""))
        with patch.object(subprocess, "run", side_effect=AssertionError("unexpected tmux query")):
            self.assertEqual(self.invoke("get", "number", "--pid", "400", environ=env), (0, "2\n", ""))
            self.assertEqual(self.invoke("get", "total", environ=env), (0, "2\n", ""))
            self.assertEqual(self.invoke("format", "{first}/{last}", environ=env), (0, "1/2\n", ""))

    def test_fields_and_completions_without_session_environment(self):
        self.assertEqual(self.invoke("--fields", environ={}), (0, "\n".join(HELPER["FIELDS"]) + "\n", ""))
        for shell in HELPER["SHELLS"]:
            status, output, error = self.invoke("completion", shell, environ={})
            self.assertEqual((status, error), (0, ""))
            self.assertIn("termux-sessions", output)
            self.assertEqual(self.invoke("--completion", shell, environ={}), (0, output, ""))

    def test_invalid_option_combinations(self):
        cases = [("--get", "unknown"), ("get", "total", "--json"), ("--fields", "--pid", "2"),
                 ("--get", "total", "--pid", "-1"), ("--get", "total", "--tty", "garbage"),
                 ("--get", "total", "--tty", "pts/1", "--pid", "200"), ("--install",),
                 ("completion",), ("completion", "sh"), ("completion", "bash", "--dir", "/tmp"),
                 ("completion", "--all"), ("completion", "bash", "--all", "--install"),
                 ("completion", "bash", "--pid", "200"), ("completion", "bash", "--install", "--dir", "")]
        for args in cases:
            with self.subTest(args=args):
                status, output, error = self.invoke(*args, environ={})
                self.assertEqual((status, output), (2, ""))
                self.assertIn("error:", error)

    def test_default_custom_and_all_installs(self):
        env = {"HOME": str(self.proc / "home"), "XDG_DATA_HOME": str(self.proc / "data"),
               "XDG_CONFIG_HOME": str(self.proc / "config"), "PREFIX": str(self.proc / "prefix")}
        status, output, error = self.invoke("completion", "--all", "--install", environ=env)
        self.assertEqual((status, output), (0, ""))
        paths = [self.proc / "data/bash-completion/completions/termux-sessions.bash",
                 self.proc / "prefix/share/zsh/site-functions/_termux-sessions",
                 self.proc / "config/fish/completions/termux-sessions.fish"]
        for shell, path in zip(HELPER["SHELLS"], paths):
            self.assertEqual(path.read_text(), HELPER["completion_source"](shell))
        before = [path.stat().st_mtime_ns for path in paths]
        self.assertEqual(self.invoke("completion", "--all", "--install", environ=env)[:2], (0, ""))
        self.assertEqual(before, [path.stat().st_mtime_ns for path in paths])
        self.assertEqual(list(self.proc.rglob("*.bak.*")), [])
        custom = self.proc / "custom space"
        self.assertEqual(self.invoke("completion", "--all", "--install", "--dir", str(custom), environ={})[:2], (0, ""))
        self.assertEqual(sorted(p.name for p in custom.iterdir()), sorted(p.name for p in paths))

    def test_completion_directory_environment_defaults(self):
        env = {"HOME": "/example/home"}
        targets = dict(HELPER["completion_targets"](HELPER["SHELLS"], None, env))
        self.assertEqual(targets["bash"], Path("/example/home/.local/share/bash-completion/completions/termux-sessions.bash"))
        self.assertEqual(targets["zsh"], Path("/example/home/.local/share/zsh/site-functions/_termux-sessions"))
        self.assertEqual(targets["fish"], Path("/example/home/.config/fish/completions/termux-sessions.fish"))
        env.update(BASH_COMPLETION_USER_DIR=":/first:/second", TERMUX__PREFIX="/termux", PREFIX="/ignored")
        targets = dict(HELPER["completion_targets"](HELPER["SHELLS"], None, env))
        self.assertEqual(targets["bash"], Path("/first/completions/termux-sessions.bash"))
        self.assertEqual(targets["zsh"], Path("/termux/share/zsh/site-functions/_termux-sessions"))

    def test_install_backup_and_invalid_targets(self):
        destination = self.proc / "install"
        destination.mkdir()
        target = destination / "_termux-sessions"
        target.write_text("original completion\n")
        target.chmod(0o600)
        self.assertEqual(self.invoke("completion", "zsh", "--install", "--dir", str(destination))[:2], (0, ""))
        backups = list(destination.glob("_termux-sessions.bak.*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), "original completion\n")
        self.assertEqual(backups[0].stat().st_mode & 0o777, 0o600)
        target.unlink()
        target.symlink_to(backups[0])
        self.assertEqual(self.invoke("completion", "--all", "--install", "--dir", str(destination))[:2], (1, ""))
        self.assertFalse((destination / "termux-sessions.bash").exists())
        target.unlink()
        target.mkdir()
        self.assertEqual(self.invoke("completion", "zsh", "--install", "--dir", str(destination))[:2], (1, ""))
        bad_parent = self.proc / "not-a-directory"
        bad_parent.write_text("keep")
        self.assertEqual(self.invoke("completion", "bash", "--install", "--dir", str(bad_parent))[:2], (1, ""))

    def test_partial_install_failure_is_reported_and_temporary_removed(self):
        destination = self.proc / "install"
        original = os.replace

        def replace(source, target):
            if target.name == "_termux-sessions":
                raise PermissionError("test failure")
            original(source, target)

        with patch.object(os, "replace", replace):
            status, output, error = self.invoke("completion", "--all", "--install", "--dir", str(destination))
        self.assertEqual((status, output), (1, ""))
        self.assertIn("installed: " + str(destination / "termux-sessions.bash"), error)
        self.assertIn("test failure", error)
        self.assertEqual([p.name for p in destination.iterdir()], ["termux-sessions.bash"])


class NativeCompletionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="termux-sessions-completion-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.env = dict(os.environ, HOME=str(self.root), ZDOTDIR=str(self.root), TERM="xterm-256color",
                        XDG_DATA_HOME=str(self.root / "data"), XDG_CONFIG_HOME=str(self.root / "config"),
                        XDG_CACHE_HOME=str(self.root / "cache"))
        self.env.pop("TERMUX_APP__PID", None)
        self.marker = self.root / "helper-executed"
        executable = self.root / "termux-sessions"
        executable.write_text("#!" + shutil.which("sh") + "\nprintf invoked > " + shlex.quote(str(self.marker)) + "\n")
        executable.chmod(0o700)
        self.env["PATH"] = str(self.root) + os.pathsep + self.env["PATH"]
        self.sources = {}
        for shell in HELPER["SHELLS"]:
            path = self.root / ("_termux-sessions" if shell == "zsh" else "completion." + shell)
            path.write_text(HELPER["completion_source"](shell))
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

    def test_bash_candidates(self):
        cases = [(('get', 'num'), 'number'), (('--get', 'pre'), 'previous'),
                 (('--get=nu',), '--get=number'), (('completion', 'z'), 'zsh'),
                 (('--completion', 'f'), 'fish'), (('--completion', '--'), '--all'),
                 (('completion', 'bash', '--'), '--install'), (('format', '{num'), '{number}'),
                 (('format', '{number}/{to'), '{number}/{total}'),
                 (('--format={nu',), '--format={number}')]
        for words, expected in cases:
            with self.subTest(words=words):
                code = ('source ' + shlex.quote(str(self.sources['bash']))
                        + '\nCOMP_WORDS=(termux-sessions ' + ' '.join(shlex.quote(word) for word in words)
                        + '); COMP_CWORD=' + str(len(words))
                        + '\n_termux_sessions\nprintf "%s\\n" "${COMPREPLY[@]}"')
                self.assertIn(expected, self.run_shell('bash', code).splitlines())
        (self.root / "target directory").mkdir()
        code = ('source ' + shlex.quote(str(self.sources['bash']))
                + '\nCOMP_WORDS=(termux-sessions completion bash --install --dir tar); COMP_CWORD=5'
                + '\n_termux_sessions\nprintf "%s\\n" "${COMPREPLY[@]}"')
        self.assertIn('target directory', self.run_shell('bash', code).splitlines())

    def test_fish_candidates(self):
        cases = [("get num", "number"), ("--get pre", "previous"), ("--get=nu", "--get=number"),
                 ("completion z", "zsh"), ("completion bash --", "--install"),
                 ("--completion f", "fish"), ("--completion --", "--all"),
                 ("format '{num", "{number}"), ("format '{number}/{to", "{number}/{total}")]
        for words, expected in cases:
            with self.subTest(words=words):
                code = ('source ' + shlex.quote(str(self.sources['fish']))
                        + '; complete -C ' + shlex.quote('termux-sessions ' + words))
                candidates = [line.split('\t')[0] for line in self.run_shell('fish', code).splitlines()]
                self.assertIn(expected, candidates)
        (self.root / "target-directory").mkdir()
        code = ('source ' + shlex.quote(str(self.sources['fish']))
                + '; complete -C "termux-sessions completion fish --install --dir tar"')
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
            cases = [('get num', 'number'), ('--get pre', 'previous'), ('--get=nu', 'number'),
                     ('completion z', 'zsh'), ('completion bash --', '--install'),
                     ('--completion f', 'fish'), ('--completion --', '--all'),
                     ("--format='{num", '{number}'),
                     ("format 'before {num", 'before {number}'),
                     ("format '{num", '{number}'), ("format '{number}/{to", '{number}/{total}')]
            for words, expected in cases:
                with self.subTest(words=words):
                    result_path.unlink(missing_ok=True)
                    os.write(master, b'\x15' + ('termux-sessions ' + words).encode() + b'\t')
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

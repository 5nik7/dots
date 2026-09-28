#!/usr/bin/env python3
"""Run the repository's Yazi config in a disposable native PTY (Unix only)."""
import fcntl
import json
import os
from pathlib import Path
import pty
import select
import shutil
import signal
import struct
import subprocess
import tempfile
import termios
import time


PROBE = r'''--- @sync entry
return { entry = function()
  local ok, result = pcall(function()
    local git = require("dots.git")
    local projects, head = require("dots.projects"), require("dots.githead")
    local dirs = 0
    for _ in pairs(git.dirs) do dirs = dirs + 1 end
    return {
      cwd = tostring(cx.active.current.cwd),
      ratio = { rt.mgr.ratio[1], rt.mgr.ratio[2], rt.mgr.ratio[3] },
      sort = cx.active.pref.sort_by, reverse = cx.active.pref.sort_reverse,
      dirs_first = cx.active.pref.sort_dir_first,
      repo = head.name or "", branch = head.output and head.output.branch or "",
      git_dirs = dirs, projects = #projects.projects.list,
      project_name = projects.projects.list[1] and projects.projects.list[1].desc or "",
      dotline = Dotline ~= nil, yatline = Yatline ~= nil,
      githead_id = head._id, projects_id = projects._id,
      merged = require("probe").merged or 0,
    }
  end)
  local f = assert(io.open(os.getenv("HOME") .. "/probe.jsonl", "a"))
  f:write(require("dots.json").encode(ok and result or { error = tostring(result) }), "\n")
  f:close()
end, setup = function(self)
  ps.sub_remote("project-merged", function() self.merged = (self.merged or 0) + 1 end)
end }
'''


def run():
    plugin = Path(__file__).resolve().parent
    config = plugin.parent.parent
    with tempfile.TemporaryDirectory(prefix="dots-yazi-test-") as temporary:
        root = Path(temporary)
        for name in ("home", "config", "state", "cache", "data", "runtime", "tmp", "work", "outside"):
            (root / name).mkdir()
        cfg = root / "config"
        shutil.copytree(plugin, cfg / "plugins/dots.yazi")
        for name in ("init.lua", "keymap.toml", "yazi.toml"):
            shutil.copyfile(config / name, cfg / name)
        probe = cfg / "plugins/probe.yazi"
        probe.mkdir()
        (probe / "main.lua").write_text(PROBE)
        with (cfg / "init.lua").open("a") as file:
            file.write('\nrequire("probe"):setup()\n')
        with (cfg / "keymap.toml").open("a") as file:
            file.write('\n[[mgr.prepend_keymap]]\non = "~"\nrun = "plugin probe"\n')
            file.write('\n[[mgr.prepend_keymap]]\non = "!"\nrun = "plugin dots -- projects load a"\n')
            file.write('\n[[mgr.prepend_keymap]]\non = "@"\nrun = "plugin dots -- projects delete a"\n')
            for key, target in (("1", root / "outside/Downloads"), ("2", root / "outside"), ("3", root / "work")):
                file.write('\n[[mgr.prepend_keymap]]\non = ' + json.dumps(key) + '\nrun = ' + json.dumps("cd " + str(target)) + '\n')
        (root / "outside/Downloads").mkdir()
        env = os.environ.copy()
        for name in ("YAZI_ID", "YAZI_LEVEL", "APPDATA", "LOCALAPPDATA", "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
            env.pop(name, None)
        env.update(
            HOME=str(root / "home"), XDG_CONFIG_HOME=str(root / "config-root"),
            YAZI_CONFIG_HOME=str(cfg), XDG_STATE_HOME=str(root / "state"),
            XDG_CACHE_HOME=str(root / "cache"), XDG_DATA_HOME=str(root / "data"),
            XDG_RUNTIME_DIR=str(root / "runtime"), TMPDIR=str(root / "tmp"),
            YAZI_LOG="debug", TERM="xterm-256color", GIT_CONFIG_NOSYSTEM="1",
            GIT_CONFIG_GLOBAL=os.devnull,
        )
        def git(*args):
            return subprocess.run(["git", *args], cwd=root / "work", env=env, check=True, capture_output=True)
        git("init", "-b", "fixture")
        (root / "work/tracked.txt").write_text("initial\n")
        git("add", "tracked.txt")
        git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-m", "fixture")
        (root / "work/tracked.txt").write_text("modified\n")
        (root / "work/-space 路径.txt").write_text("untracked\n")
        (root / "work/link").symlink_to("-space 路径.txt")
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 30, 120, 0, 0))
        def session():
            os.setsid()
            fcntl.ioctl(0, termios.TIOCSCTTY, 0)
        process = subprocess.Popen(["yazi", str(root / "work")], stdin=slave, stdout=slave, stderr=slave,
                                   env=env, cwd=root / "work", preexec_fn=session)
        os.close(slave)
        output = bytearray()
        def pump(seconds=0.25):
            deadline = time.monotonic() + seconds
            while time.monotonic() < deadline:
                if select.select([master], [], [], 0.05)[0]:
                    try:
                        data = os.read(master, 65536)
                    except OSError:
                        break
                    output.extend(data)
                    if b"\x1b[6n" in data:
                        os.write(master, b"\x1b[1;1R")
                    if b"\x1b[0c" in data or b"\x1b[c" in data:
                        os.write(master, b"\x1b[?1;2c")
                    if b"\x1b]11;?" in data:
                        os.write(master, b"\x1b]11;rgb:0000/0000/0000\x1b\\")
        def key(value):
            os.write(master, value)
            pump()
        result_file = root / "home/probe.jsonl"
        def snapshot():
            before = len(result_file.read_text().splitlines()) if result_file.exists() else 0
            key(b"~")
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                rows = result_file.read_text().splitlines() if result_file.exists() else []
                if len(rows) > before:
                    result = json.loads(rows[-1])
                    assert "error" not in result, result
                    return result
                pump()
            raise AssertionError("probe did not respond")
        def wait_for(predicate):
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                state = snapshot()
                if predicate(state):
                    return state
                pump()
            raise AssertionError(state)
        try:
            pump(2)
            state = wait_for(lambda s: s["repo"] == "work" and s["branch"] == "fixture" and s["git_dirs"] > 0)
            assert state["dotline"] and not state["yatline"], state
            assert state["githead_id"] == "dots.githead" and state["projects_id"] == "dots.projects", state
            for action, ratio in ((b"\x18", [2, 4, 0]), (b"\x18", [2, 4, 5]), (b"X", [2, 4, 9999]), (b"X", [2, 4, 5])):
                key(action)
                assert snapshot()["ratio"] == ratio
            print("PASS native startup, module state, Git callbacks/fetcher, pane shortcuts", flush=True)
            key(b"Ps"); key(b"a"); key(b"\x15"); key(b"Fixture project\r")
            state = wait_for(lambda s: s["projects"] == 1)
            assert state["project_name"] == "Fixture project", state
            key(b"1")
            state = wait_for(lambda s: s["cwd"].endswith("/Downloads"))
            assert state["sort"] == "mtime" and state["reverse"] and not state["dirs_first"], state
            key(b"2")
            state = wait_for(lambda s: s["cwd"] == str(root / "outside"))
            assert state["sort"] == "alphabetical" and not state["reverse"] and state["dirs_first"], state
            assert state["repo"] == "", state
            key(b"PP")
            wait_for(lambda s: s["cwd"] == str(root / "work"))
            key(b"2"); key(b"!")
            wait_for(lambda s: s["cwd"] == str(root / "work"))
            # Current and all-tab merge actions must deliver their events.
            key(b"Pm"); key(b"PM")
            wait_for(lambda s: s["merged"] == 2)
            key(b"@")
            wait_for(lambda s: s["projects"] == 0)
            key(b"Ps"); key(b"a"); key(b"\r")
            wait_for(lambda s: s["projects"] == 1)
            key(b"PD")
            wait_for(lambda s: s["projects"] == 0)
            print("PASS native project save/load/last/delete/delete-all, merge event dispatch and folder rules", flush=True)
            for width in (40, 80, 160):
                fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack("HHHH", 30, width, 0, 0))
                os.kill(process.pid, signal.SIGWINCH)
                pump()
                assert snapshot()["dotline"]
            key(b"q"); pump(0.5)
            assert process.poll() == 0, process.poll()
            log = root / "state/yazi/yazi.log"
            logs = log.read_text() if log.exists() else ""
            assert "ERROR" not in logs, logs
            assert b"Failed to" not in output and b"runtime error" not in output, output[-3000:]
            print("PASS native 40/80/160-column redraw, clean exit and error log", flush=True)
        except BaseException:
            log = root / "state/yazi/yazi.log"
            print(log.read_text() if log.exists() else "No log")
            print(repr(output[-2500:]))
            raise
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=3)
            os.close(master)


if __name__ == "__main__":
    run()

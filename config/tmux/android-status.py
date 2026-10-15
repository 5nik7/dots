#!/usr/bin/env python3
"""Render the active cached network indicator before the tmux battery segment."""

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import re
import selectors
import signal
import subprocess
import sys
import time


MODULES = ("wifi", "cell")
COLORS = ("default", "brightblack", "cyan", "red", "yellow", "green")
COLOR = re.compile(r"(?:#[0-9a-fA-F]{6}|default|(?:bright)?(?:black|red|green|yellow|blue|magenta|cyan|white))\Z")
CELL_ICON = "\U000f08fa"
TIMEOUT = 1.0
MAX_BYTES = 2 * 1024 * 1024
# Nerd Font private-use glyph, optional unknown marker, optional stale suffix.
# No ANSI, tmux introducers, arbitrary labels, or terminal control characters.
ICON = re.compile(r"[\ue000-\uf8ff\U000f0000-\U000ffffd\U00100000-\U0010fffd]\??~?\Z")


def render(module, snapshot, colors=COLORS):
    """Only validated glyphs/numbers and our own color markup cross into tmux."""
    if len(colors) != 6 or not all(COLOR.fullmatch(color) for color in colors):
        raise ValueError("invalid colors")
    _, muted, _, red, yellow, green = colors
    if module not in MODULES or not isinstance(snapshot, dict) or snapshot.get("module") != module:
        raise ValueError("invalid module")
    icon, stale = snapshot.get("icon"), snapshot.get("stale")
    if (not isinstance(icon, str) or not ICON.fullmatch(icon)
            or type(stale) is not bool or icon.endswith("~") != stale):
        raise ValueError("invalid icon")
    data = snapshot.get("data")
    if not isinstance(data, dict):
        raise ValueError("invalid data")
    state = snapshot.get("state", "unknown")
    marker = "~" if stale else "?" if state == "unknown" else " "
    glyph = CELL_ICON if module == "cell" else icon[0]
    level = data.get("level")
    if level is not None and (type(level) is not int or not 0 <= level <= 4):
        raise ValueError("invalid signal level")
    if level is None and not stale:
        marker = "?"
    color = (red if level <= 1 else yellow if level == 2 else green) if level is not None else muted
    if stale or state == "unknown":
        color = muted
    # Equal glyph/marker slots keep Wi-Fi/data transitions aligned.
    return f"#[fg={color}]{glyph}{marker}#[default]"


def select_network(snapshots, colors=COLORS):
    wifi, cell = snapshots
    if wifi is None:
        return ""
    connected = wifi["data"].get("connected")
    if connected is True:
        return render("wifi", wifi, colors)
    if connected is not False:
        return ""
    data = cell["data"] if cell is not None else {}
    if data.get("data_enabled") is False or data.get("data_state") in ("disconnected", "connecting", "suspended"):
        return ""
    if data.get("data_enabled") is not True or data.get("data_state") != "connected":
        # This is an availability marker, not a claim of active mobile data.
        return f"#[fg={colors[1]}]{CELL_ICON}?#[default]"
    if wifi["stale"] and not cell["stale"]:
        # The fallback decision also relies on the cached Wi-Fi observation.
        cell = dict(cell, stale=True, icon=cell["icon"] + "~")
    return render("cell", cell, colors)


def read_snapshot(script):
    """Bound the CLI read; Androidots' detached refresh workers own API polling."""
    deadline = time.monotonic() + TIMEOUT
    process = subprocess.Popen(
        [sys.executable, "-B", str(script), "--json"],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        chunks, size = [], 0
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise ValueError("helper timed out")
                if not selector.select(remaining):
                    continue
                chunk = os.read(process.stdout.fileno(), 65536)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_BYTES:
                    raise ValueError("oversized snapshot")
                chunks.append(chunk)
        if process.wait(timeout=max(.001, deadline - time.monotonic())):
            raise ValueError("helper failed")
        return json.loads(b"".join(chunks).decode("utf-8"))
    finally:
        # Reap the helper and any non-detached children even on timeout/overflow.
        # Normal Androidots workers have their own session and keep their locks.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        process.stdout.close()


def snapshot(module):
    try:
        script = Path(__file__).resolve().parents[2] / "androidots/bin" / f"termux-{module}-status"
        result = read_snapshot(script)
        render(module, result)  # Validate before using connectivity or showing icons.
        return result
    except (OSError, ValueError, TypeError, RecursionError, subprocess.SubprocessError):
        return None


def main():
    colors = tuple(sys.argv[1:]) or COLORS
    output = ""
    if len(colors) == 6 and all(COLOR.fullmatch(color) for color in colors):
        try:
            with ThreadPoolExecutor(max_workers=len(MODULES)) as executor:
                output = select_network(list(executor.map(snapshot, MODULES)), colors)
        except (OSError, RuntimeError):
            pass
    # No orphan separator when both networks are hidden; newline clears old output.
    print(output + " " if output else "")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Render one Termux session snapshot as trusted tmux styles and numeric labels."""

import json
from pathlib import Path
import re
import subprocess
import sys


COLOR = re.compile(r"(?:#[0-9a-fA-F]{6}|default|(?:bright)?(?:black|red|green|yellow|blue|magenta|cyan|white))\Z")
TTY = re.compile(r"pts/[0-9]+\Z")


def render(snapshot, tty, colors, width=None, split_current=False, split_badge=False):
    """Preserve discovery order; never forward process names or arbitrary styles."""
    if len(colors) != 4 or not all(COLOR.fullmatch(color) for color in colors):
        raise ValueError("invalid colors")
    if not isinstance(snapshot, dict) or type(snapshot.get("count")) is not int:
        raise ValueError("invalid snapshot")
    sessions = snapshot.get("sessions")
    if not isinstance(sessions, list) or snapshot["count"] != len(sessions):
        raise ValueError("invalid session count")
    if width is not None and (type(width) is not int or width < 0):
        raise ValueError("invalid width")
    if split_current and split_badge:
        raise ValueError("conflicting split modes")
    split = split_current or split_badge
    terminals, pids = set(), set()
    entries = []
    tty = tty.removeprefix("/dev/")
    for number, session in enumerate(sessions, 1):
        if not isinstance(session, dict):
            raise ValueError("invalid session")
        terminal, pid = session.get("tty"), session.get("pid")
        if (not isinstance(terminal, str) or not TTY.fullmatch(terminal)
                or type(pid) is not int or pid <= 0 or terminal in terminals or pid in pids):
            raise ValueError("invalid session identity")
        terminals.add(terminal)
        pids.add(pid)
        current = terminal == tty
        bg, fg = colors[2:] if current else colors[:2]
        focus = "focus" if current else "on"
        directive = f"list={focus}," if width is None and not split else ""
        weight = "bold" if split_badge else "nobold"
        entries.append((f"#[{directive}bg={bg},fg={fg},{weight},nounderscore] {number} ",
                        len(str(number)) + 2, current))
    if width is None and not split:
        return "".join(entry[0] for entry in entries)
    if width is None:
        width = sum(entry[1] for entry in entries)
    if not entries or width == 0:
        return "||" if split_badge else "|" if split_current else ""
    current = next((i for i, entry in enumerate(entries) if entry[2]), 0)
    left, right = current, current + 1
    size = entries[current][1]
    if size > width:
        return "||" if split_badge else "|" if split_current else ""
    while True:
        candidates = []
        if left > 0:
            candidates.append((left - 1, right, size + entries[left - 1][1]))
        if right < len(entries):
            candidates.append((left, right + 1, size + entries[right][1]))
        candidates = [c for c in candidates
                      if c[2] + (c[0] > 0) + (c[1] < len(entries)) <= width]
        if not candidates:
            break
        left, right, size = min(candidates, key=lambda c: abs((current - c[0]) - (c[1] - current - 1)))
    # Markers use the row style, not either neighboring number's background.
    output = ("#[default]<" if left > 0 and size < width else "")
    for index in range(left, right):
        entry = entries[index]
        if split_badge and entry[2]:
            # Only a validated number crosses this boundary. The config joins
            # the optional project name and owns the whole badge's padding.
            output += f"#[default]|{index + 1}|"
        else:
            output += entry[0]
        if split_current and entry[2]:
            output += "#[default]|"
    output += "#[default]"
    if right < len(entries) and size + (left > 0) < width:
        output += ">"
    if split and "|" not in output:
        output += "||" if split_badge else "|"
    return output


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    output = ""
    try:
        width = None
        split_current = "--split-current" in args
        if split_current:
            args.remove("--split-current")
        split_badge = "--split-badge" in args
        if split_badge:
            args.remove("--split-badge")
        if args and args[-1].startswith("--width="):
            width = int(args.pop()[8:])
        if len(args) != 5 or not args[0].startswith("--tty="):
            raise ValueError("invalid arguments")
        # Directory-linked configs resolve back to the checkout. No PATH search,
        # import of private script internals, or submodule initialization.
        script = Path(__file__).resolve().parents[2] / "androidots/bin/termux-sessions"
        result = subprocess.run(
            [sys.executable, "-B", str(script), "--json"],
            capture_output=True, text=True, timeout=1, check=True,
        )
        if len(result.stdout) > 65536:
            raise ValueError("oversized snapshot")
        output = render(json.loads(result.stdout), args[0][6:], args[1:], width, split_current, split_badge)
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    # A newline clears tmux's cached successful result after errors or tab exits.
    print(output)


if __name__ == "__main__":
    main()

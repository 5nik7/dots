#!/usr/bin/env python3
"""Render one Termux session snapshot as trusted tmux styles and numeric labels."""

import json
from pathlib import Path
import re
import subprocess
import sys


COLOR = re.compile(r"(?:#[0-9a-fA-F]{6}|default|(?:bright)?(?:black|red|green|yellow|blue|magenta|cyan|white))\Z")
TTY = re.compile(r"pts/[0-9]+\Z")


def render(snapshot, tty, colors, width=None, split_current=False, split_badge=False,
           compact_badge=False, separator_fg=None, separator_bg=None, dim_inactive=True):
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
    if sum((split_current, split_badge, compact_badge)) > 1:
        raise ValueError("conflicting split modes")
    if compact_badge and (not isinstance(separator_fg, str) or not COLOR.fullmatch(separator_fg)):
        raise ValueError("invalid separator color")
    if separator_bg is not None and (not isinstance(separator_bg, str) or not COLOR.fullmatch(separator_bg)):
        raise ValueError("invalid separator color")
    split = split_current or split_badge or compact_badge
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
        weight = ("bold,noreverse," + ("dim" if dim_inactive else "nodim")) if compact_badge else "bold" if split_badge else "nobold"
        entries.append((f"#[{directive}bg={bg},fg={fg},{weight},nounderscore] {number} ",
                        len(str(number)) + 2, current))
    if compact_badge:
        return compact(entries, colors[0] if separator_bg is None else separator_bg, separator_fg, width)
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


def compact(entries, background, foreground, width):
    """Three fields with empty strings for absent groups and no boundary dividers."""
    if len(entries) < 2 or width == 0:
        return "||"
    divider = f"#[bg={background},fg={foreground},nobold,nounderscore,noreverse,nodim]│"
    current = next((i for i, entry in enumerate(entries) if entry[2]), 0)
    left, right = current, current + 1
    size = entries[current][1]
    if width is None:
        width = sum(entry[1] for entry in entries) + len(entries) - 1
    if size > width:
        return "||"
    while True:
        candidates = []
        if left:
            candidates.append((left - 1, right, size + entries[left - 1][1] + 1))
        if right < len(entries):
            candidates.append((left, right + 1, size + entries[right][1] + 1))
        # Each overflow marker also owns its adjoining divider cell.
        candidates = [c for c in candidates
                      if c[2] + 2 * (c[0] > 0) + 2 * (c[1] < len(entries)) <= width]
        if not candidates:
            break
        left, right, size = min(candidates, key=lambda c: abs((current - c[0]) - (c[1] - current - 1)))
    before, after, number = [], [], ""
    if left and size + 2 <= width:
        before.append("#[default]<")
        size += 2
    for index in range(left, right):
        if entries[index][2]:
            number = str(index + 1)
        else:
            (after if number else before).append(entries[index][0])
    if right < len(entries) and size + 2 <= width:
        (after if number else before).append("#[default]>")
    def group(parts):
        return divider.join(parts) + "#[default]" if parts else ""
    return "|".join((group(before), number, group(after)))


def render_tabs(snapshot, tty, colors, width, separator_fg, separator_bg):
    """Independent upper-row tab strip; singleton tabs emit no style or padding."""
    before, current, after = render(snapshot, tty, colors, width, compact_badge=True,
                                   separator_fg=separator_fg, separator_bg=separator_bg, dim_inactive=False).split('|')
    divider = f'#[bg={separator_bg},fg={separator_fg},nobold,nounderscore,noreverse,nodim]│#[default]'
    selected = (f'#[bg={colors[2]},fg={colors[3]},bold,nounderscore,noreverse,nodim] {current} #[default]'
                if current else '')
    return divider.join(part for part in (before, selected, after) if part)


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    output = ""
    try:
        width = None
        tabs = '--tabs' in args
        if tabs:
            args.remove('--tabs')
        split_current = "--split-current" in args
        if split_current:
            args.remove("--split-current")
        split_badge = "--split-badge" in args
        if split_badge:
            args.remove("--split-badge")
        compact_badge = "--compact-badge" in args
        if compact_badge:
            args.remove("--compact-badge")
        separator_colors = {}
        for arg in args[:]:
            if arg.startswith(("--separator-fg=", "--separator-bg=")):
                key, value = arg.split("=", 1)
                if key in separator_colors:
                    raise ValueError("duplicate separator color")
                separator_colors[key] = value
                args.remove(arg)
        if args and args[-1].startswith("--width="):
            width = int(args.pop()[8:])
        if len(args) != 5 or not args[0].startswith("--tty="):
            raise ValueError("invalid arguments")
        # Directory-linked configs resolve back to the checkout. No PATH search,
        # import of private script internals, or submodule initialization.
        script = Path(__file__).resolve().parents[2] / "profiles/termux/bin/termux-sessions"
        result = subprocess.run(
            [sys.executable, "-B", str(script), "--json"],
            capture_output=True, text=True, timeout=1, check=True,
        )
        if len(result.stdout) > 65536:
            raise ValueError("oversized snapshot")
        if tabs:
            if split_current or split_badge or compact_badge:
                raise ValueError('conflicting tab rendering modes')
            output = render_tabs(json.loads(result.stdout), args[0][6:], args[1:], width,
                                 separator_colors.get('--separator-fg'), separator_colors.get('--separator-bg'))
        else:
            output = render(json.loads(result.stdout), args[0][6:], args[1:], width,
                            split_current, split_badge, compact_badge,
                            separator_colors.get("--separator-fg"), separator_colors.get("--separator-bg"))
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    # A newline clears tmux's cached successful result after errors or tab exits.
    print(output)


if __name__ == "__main__":
    main()

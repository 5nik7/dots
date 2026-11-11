---
name: dots-clipboard-maintenance
description: Maintain Dots system clipboard adapters, local text history, watcher controls and shell-editor popup integration. Use for cpy/pst or dots clipboard; implementation work does not enable recording or a live watcher.
---

# Dots clipboard maintenance

Read [clipboard history](../../../docs/clipboard.md), [system clipboard adapters](../../../docs/shell-utils.md#system-clipboard-commands), [command guide](../../../agents/guides/commands.md) and [safety](../../../docs/safety.md). Follow command authoring for new routes, CLI presentation for human views, Config for consumer-backed preferences, and menu authoring for the popup. The family owns `cpy`/`pst`, `clipboard.py`, the `clipboard_*` controllers and generated `dots-clipboard-*` entry points.

Keep providers behind `clipboard.py`; never embed package-owned scripts in profile bins. Preserve successful-copy and exact-byte contracts, including empty strings, Unicode, trailing newlines and literal shell text. History is UTF-8 text only and records successful Dots copies only when enabled. History errors must not fail a successful copy. Help, completion, status and dry runs must not read the system clipboard or launch a worker.

`clipboard_history.py` owns a private SQLite runtime store with atomic transactions and bounded retention; it is separate from managed file installation journals. Keep deletion scopes explicit, revalidate revisions, preserve pins during automatic pruning, and validate complete imports before mutation. Never retain clipboard payloads in Dots backup journals, diagnostic text or recovery copies. Document physical-erasure limits and transient private previews accurately.

The optional watcher is explicitly started and controlled by a per-process lease token. Never signal an unverified PID, auto-start it from initialization, or test it against the user's clipboard. Preserve token checks after clipboard reads, paused capture, repeat suppression, bounded provider timeouts and stale-worker recovery. Android background reads have OS restrictions.

The shared popup uses inert sanitized previews and exact-client context. Shell widgets insert directly into Bash/Zsh/Fish/PSReadLine editors without submitting input; direct tmux insertion requires a verified idle prompt with bracketed paste enabled. Reject controls that could escape bracketed paste. Keep copy/print available in unsupported insertion contexts. Generating widget code must not activate bindings or capture.

Static grammar lives in `clipboard_commands.py`; run `tools/generate_clipboard_commands.py` after edits and its `--check` mode before finishing. Keep six-shell contextual completion, native dispatch, Config/menu ownership and docs synchronized. Typed controls and styles use existing profile precedence; never add a second settings store. Installer/bootstrap integration remains the existing checkout bin/lib deployment unless new native assets require an explicit change.

Run `python3 -B tools/test_clipboard.py`, `python3 -B tools/test_clipboard_history.py`, and `python3 -B tools/test_clipboard_ui.py` sequentially. Fixtures own providers, homes, state and tmux clients. Cover exact data, concurrency, interrupted/failed imports, watcher ownership, stale selections, configuration consumers and 40/80/120-column/short-height popups. Report real Windows, Linux/WSL desktop and Android background acceptance separately. Rebuild/check the Wiki through the documentation skills; do not commit or publish without authorization.

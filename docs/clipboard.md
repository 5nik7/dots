# Clipboard history

**Status: Implemented.** `dots clipboard` manages local UTF-8 text history on Termux, Linux, WSL and native Windows through shared Python controllers. It reuses the system providers behind [cpy and pst](shell-utils.md#system-clipboard-commands). Desktop-provider and PowerShell acceptance outside the local fixtures is listed under [verification](#verification).

## Start using it

```bash
dots clipboard add "Keep this text"
printf 'multiline\ntext\n' | dots clipboard add
dots clipboard capture                # explicitly read the system clipboard
dots clipboard                        # browser in a terminal; listing otherwise
dots clipboard search "text" --json
dots clipboard status
```

Recording of successful `cpy` and Dots copies is **off by default**. Enable it deliberately with `dots config set apps.clipboard.record_copies true`. This records only copies made through the shared adapter; `pst` remains a read without recording. To observe changes from other applications, explicitly run `dots clipboard watch start`. The watcher does not start through help, completion, shell initialization or installation.

```bash
dots clipboard watch status
dots clipboard pause                  # pause automatic copy recording and polling capture
dots clipboard resume
dots clipboard watch stop             # stop the owned worker; leave stored history
```

`watch pause` and `watch resume` are the same capture controls. Pausing does not prevent an explicit `add` or `capture`. Disabling `record_copies` controls the copy hook; stop the watcher separately. Changes captured while paused are not queued for later replay. `watch start --foreground` runs until interrupted; the default worker detaches without boot autostart. Provider failures report a degraded state without including clipboard text. Stale workers can be replaced by a subsequent explicit start.

## Commands and data

Use full IDs from `list`, `show`, JSON or completion. Shell metacharacters remain literal after the calling shell has parsed arguments. Use `--` before text beginning with a dash.

| Route | Behavior |
| --- | --- |
| `browse` | Search all stored text with the shared FZF selector; use `--limit N` to bound candidates |
| `list`, `search QUERY` | Most recently updated entries first; human previews or schema-1 `--json` |
| `show ID` | Inspect the full text and metadata; `--raw` emits exact UTF-8 bytes |
| `add [TEXT...]` | Store arguments joined by spaces, or stdin if no arguments; does not change the clipboard |
| `capture` | Read and store the current system clipboard text |
| `copy ID` | Write the entry to the system clipboard |
| `print ID` | Emit exact text without an added newline or decoration |
| `insert ID` | Insert into a verified tmux shell prompt; prefer the editor widget below |
| `pin ID...`, `unpin ID...` | Protect entries from automatic pruning, or remove that protection |
| `remove ID...` | Review and permanently remove exactly these entries |
| `clear` | Review matching unpinned entries; `--include-pinned` explicitly includes pins |
| `prune` | Review unpinned entries beyond configured count/age retention |
| `export`, `import` | Export JSON to stdout or import from stdin, with complete validation before writes |
| `status`, `pause`, `resume` | Inspect providers, bounds and capture controls; pause/resume automatic capture |
| `watch start/stop/pause/resume/status` | Control the explicitly enabled polling worker |
| `pick` | Interactive selection for shell-editor integrations; `--json` returns the chosen ID and text |
| `init SHELL` | Emit widget initialization for Bash, Zsh, Fish or PowerShell |

Lists, search, browse/pick, clear and export accept `--query`, `--limit` (`0` means all), `--since`, `--until`, `--pinned` and `--source`. `search` takes its query as positional text. Dates accept ISO dates/timestamps; dates without offsets use UTC and `--until YYYY-MM-DD` includes the whole day. The list/search default is 50 entries; clear/export and the browser default to all matching entries. Source choices are `manual`, `cpy`, `dots`, `capture`, `watch`, and `import`.

Mutation routes accept `--dry-run`; capture/watch previews neither read the system clipboard nor start a worker. `remove`, `clear` and `prune` require interactive confirmation, or `--yes` outside a terminal. Review uses exact IDs and revisions and refuses changed selections. Pins survive automatic pruning but explicit remove can delete a pinned entry. `--json` provides machine output on report routes; `print`, `export` and generated shell code always use their exact data contracts. `show --raw` cannot be combined with `--json`. Color/icon choices affect only human views. Exit statuses are 0 for success, 1 for operation errors, 2 for invalid usage and 130 for cancellation/interruption.

```bash
dots clipboard list --pinned --json
dots clipboard clear --until 2026-01-01 --dry-run --json
dots clipboard clear --until 2026-01-01 --yes
dots clipboard export > history.json
dots clipboard import --dry-run < history.json
dots clipboard import < history.json
```

Exports contain plaintext `{ "schema": 1, "entries": [{ "text": "...", "pinned": false }] }`. Imports preserve text/pin state, assign local IDs/timestamps/source, apply exclusions and deduplication, and enforce current limits. Existing history is merged; it is never implicitly cleared. Invalid batches and pinned-capacity overflow roll back atomically. Exported files are caller-owned and may contain sensitive text.

## Popup and input-buffer keys

The root menu includes **Clipboard**, with browser, status, capture, pause/resume and Config entries. Browser rows search the stored text and show source/size/pin context. The inert preview includes the full stable ID, timestamp and bounded text. Preview controls and shared popup geometry adapt to small terminals. Without optional FZF, ordinary browsing falls back to a listing; explicit `pick` reports the missing interactive capability.

| Key | Browser action |
| --- | --- |
| Enter / Alt-Y | Copy and close |
| Alt-I | Insert without submitting |
| Alt-P | Print and close |
| Alt-S | Pin/unpin and refresh, preserving query/focus |
| Alt-D | Open removal review with Cancel first |
| Alt-O | Open clipboard settings in Config |
| Alt-H / F1 | Show key help |
| Alt-J / Alt-K | Scroll the preview |
| Esc / Ctrl-C | Back / cancel |

In `pick`, Enter/Alt-I return the selected text to the editor widget. Alt-Y copies and stays in the picker. Alt-P also returns the selection to the widget. Widgets bind **Ctrl-X, Ctrl-V** explicitly; generation alone does not install bindings. Evaluate the matching command in your interactive shell, or add it to your own shell configuration:

```bash
# Bash or Zsh
eval "$(dots clipboard init bash)"      # use zsh in Zsh
```

```fish
dots clipboard init fish | source
```

```powershell
Invoke-Expression ((dots clipboard init powershell) -join [Environment]::NewLine)
```

Bash/Zsh/Fish widgets insert directly into their command editor, and PowerShell uses PSReadLine `Insert`. They preserve multiline text and do not press Enter. They require an interactive terminal, FZF, and the shell's editor (PSReadLine on PowerShell). Existing bindings for this chord are replaced only when the generated code is evaluated.

Direct `insert` and browser Alt-I can target an idle Bash/Zsh/Fish prompt on an exact tmux client (`--client CLIENT`). They verify client/pane ownership and bracketed-paste readiness before pasting. Running applications, unsupported shells, and missing context are refused with widget/copy/print guidance. Insertion rejects terminal control characters, including escape sequences and CR; LF and tab are supported. Copy and exact print preserve the original text. Nushell/Xonsh have command completion and direct history operations; editor insertion has no adapter and uses copy/print instead.

## Configuration and storage

`dots config browse --query clipboard` exposes settings with existing profile > parent > shared-default precedence. Null/unset inherits the lower layer. Settings apply on the next command or watcher poll; they do not activate a stopped watcher.

| `apps.clipboard` key | Default | Meaning |
| --- | --- | --- |
| `record_copies` | `false` | Record successful shared-adapter copies |
| `max_entries` | `500` | Hard count bound, including pins (1–10000) |
| `max_age_days` | `30` | Unpinned retention age (1–3650) |
| `max_entry_bytes` | `65536` | UTF-8 bytes per entry (1–1048576) |
| `deduplicate` | `true` | Refresh an identical entry instead of adding another |
| `exclude_patterns` | `[]` | Up to 100 case-sensitive whole-text glob patterns; `*` matches across lines |
| `poll_seconds` | `2` | Watcher interval (1–10 seconds) |
| `preview` | `true` | Show the popup preview when space permits |
| `preview_lines` | `8` | Maximum preview content lines (1–40), with bounded line widths/request size |
| `list_limit` | `50` | Default list/search result count (1–10000) |

Report styles use `colors.apps.clipboard.{heading,label,identity,text,source,timestamp,pinned,error}` with foreground, background and nullable attributes. `icons.menu.clipboard` and its supported CLI icon styles control the glyph. Existing `formatting.apps.cli` controls detail layout; `formatting.apps.menu`, menu colors and popup controls govern selector rows/placement. These saves take effect on the next view without theme publication.

The SQLite store is `<Dots state root>/clipboard/history.sqlite3`, outside the repository. POSIX uses `$XDG_STATE_HOME/dots` or `~/.local/state/dots`; native Windows uses the existing Dots local-app-data state root. WSL and Windows stores remain separate. Reads, help and completion do not create the store. POSIX directory/file permissions are 0700/0600; Windows uses the current user's application-data permissions. Storage is local plaintext, not encrypted or synchronized.

Unpinned age/count pruning runs on successful writes or explicit `prune`; reads do not prune. Pins count toward the hard count bound; a store full of pins refuses new entries instead of growing. Lowering limits does not immediately rewrite existing entries: prune/remove or subsequent writes reconcile retention; previously stored large text is retained until removed. Automatic capture suppresses repeated/self-generated text even when deduplication is disabled. History-recording errors leave a successful system copy successful and emit a text-free warning.

Deletion uses atomic SQLite transactions and secure-delete, without retained Dots payload backups. Private short-lived previews and SQLite rollback journals exist while operations run; normal completion cleans them up. There is no content undo or recovery trash. Filesystem snapshots, exports, interrupted temporary files and flash storage can retain older bytes; this is not a guarantee of physical erasure. Pause capture before clearing if a watcher could capture new content immediately afterward. See [safety](safety.md).

## Verification

`tools/test_clipboard.py` verifies providers and exact cpy/pst contracts with substitutes. `tools/test_clipboard_history.py` verifies storage, imports, capture/watcher lifecycle, literal widgets and both dispatch paths, including completion records for Bash/Zsh/Fish/PowerShell/Nushell/Xonsh. `tools/test_clipboard_ui.py` exercises Config consumers and private tmux/FZF clients at 40/80/120 columns and short heights, including multiline insertion without execution. Tests own all homes, state, providers and terminal clients.

Native Windows PowerShell 5.1/7 editor/desktop behavior, native Linux Wayland/X11, WSL interop and actual Android background-read acceptance remain pending. Android 10+ restricts background clipboard access to focused apps or the default IME, so a running watcher may report degraded while Termux is unfocused. See [Android clipboard privacy](https://developer.android.com/about/versions/10/privacy/changes#clipboard-data). No permission workaround, package installation or boot service is performed automatically.

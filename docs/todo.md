# Goals with todo

`dots todo` manages goals for the active Dots checkout. Standalone `todo` selects the deepest enclosing Git worktree or explicitly configured project, and uses global goals outside a project. Project detection shares the tmux workspace resolver and never scans a directory tree. Git errors, missing Git inside a repository, and invalid project configuration are errors, not reasons to create global goals.

```bash
dots todo add "Improve shell startup" --priority high --tag performance
todo add "Rework configuration" --alias config-rework
todo note config-rework "Keep machine-specific settings separate."
todo add "Finish settings screen" --due 2026-11-15
todo list --status open --tag ui
todo --global add "Plan next month"
todo --project "/path/with spaces" list
todo brief GOAL_ID
```

`--project` selects an existing directory explicitly, including a non-Git project. Project registrations use `dots/projects.json` under the native configuration root, with the existing `schema: 1`, `roots` and `projects` arrays. The `projects` entries define explicit project boundaries; `roots` remains a discovery setting for the session browser. Git worktrees and nested repositories have separate goal files. Scope overrides belong to standalone `todo`; `dots todo` always selects Dots.

## Commands and fields

Bare invocation opens the popup when terminal streams are interactive and the terminal is usable; redirected output lists active goals. `browse` requests the popup explicitly, while `--print`, `--json` and `--markdown` bypass it. Help does not resolve a project or inspect goal data.

| Command | Behavior |
| --- | --- |
| `add TITLE` | Create an open, normal-priority goal; omitted titles prompt interactively |
| `list` | Query goals in the selected scope |
| `show ID` | Show a goal and descendants, including removed records |
| `edit ID` | Replace supplied fields, or choose a field interactively |
| `note ID [TEXT]` | Append details to notes; omitted text opens multiline input interactively |
| `start ID` | Set status to doing |
| `done ID` | Complete the goal after all nonremoved descendants are complete |
| `reopen ID` | Set status to open; reopen a completed parent before its children |
| `remove ID` | Soft-remove a goal, retaining its fields and status |
| `restore ID` | Restore a removed goal; restore its parent first |
| `next` | Show the highest-ranked open/doing goal with no unfinished descendants |
| `brief ID` | Print a read-only `/plan` interview brief for the complete subtree |
| `plan ID` | Launch/resume the goal's named Codex thread in Plan Mode; `--new` starts a new association, `--dry-run` previews |
| `browse` | Open the goal popup |
| `path` | Print the exact storage path |

IDs are full UUID hex strings; unambiguous prefixes also work. Goals accept notes, priority (`high`, `normal`, `low`), repeatable tags, an optional ISO calendar due date and repeatable acceptance criteria. `add --parent ID` creates a subgoal; a completed parent must be reopened first. Acceptance criteria are statements to verify, not automatically evaluated checks.

Use `add --alias NAME` or `edit ID --alias NAME` to give a goal a memorable name, such as `config-rework`. Aliases begin with a lowercase letter and contain 1–64 lowercase letters, digits, dots, underscores or hyphens. Names are exact and case-sensitive, unique within the selected scope, and reserved even while a goal is removed. They do not change when titles change. `edit ID --clear alias` releases a name; restore a removed goal before changing its alias. Existing goals are not named automatically.

Every ID operand, including `--parent`, accepts an alias. `@config-rework` explicitly selects an alias. Hexadecimal-only names require this prefix, for example `@dead`; bare hexadecimal text remains a UUID/prefix selector. Completion prefers a matching alias and retains UUID completion. Internal parent references, popup selection and agent brief update commands retain full UUIDs.

`edit` supports `--title`, `--alias`, `--notes`, `--priority`, `--tag`, `--due`, `--accept`, and `--status open|doing|blocked|done`. Supplied notes, tags and acceptance criteria replace that field, with the required project tag retained. Repeat `--clear notes|due|tags|acceptance|alias` to clear fields; clearing project tags removes custom tags and leaves the project tag. Empty notes can also be supplied literally. There is no automatic reparenting or completion propagation.

Project goals automatically keep the resolved project folder name as a tag: `dots` in this checkout, for example. Names preserve case, spaces and Unicode; a filesystem-root project uses its root anchor. The tag is appended after custom tags only when that exact value is absent. Global goals have no required tag. Folder renames require the new name while retaining previous tags as ordinary editable tags. Use `--tag=-name` for a tag beginning with a dash.

Every successful goal-changing command fills missing project tags throughout that selected project's goal file, including subgoals, completed goals and removed records. The requested changes and backfill share one guarded transaction; previews/results include repaired records, and only changed records receive a new `updated` timestamp. A same-value edit can therefore repair older goals; repeating it after repair is a no-op. Reads never backfill, and other projects are not scanned. The project tag counts toward the 256-tag limit; affected goal IDs are reported and nothing is written if it will not fit. Custom tags are never silently discarded.

`note ID TEXT` appends literal, possibly multiline text to the notes field, inserting a blank line when needed without changing existing text. It adds no timestamps or independent note records. Omit TEXT for interactive multiline input; noninteractive use and `--json`/`--dry-run` require explicit text. Blank additions, removed goals and appends exceeding the notes limit are refused. Use `--` before text beginning with a dash. Cancellation writes nothing. Repeating a note intentionally appends it again.

List filters are `--query TEXT`, `--status`, `--priority`, repeatable `--tag`, `--overdue`, `--all`, and `--removed`. Query words match case-insensitively across aliases, titles, notes, tags and acceptance criteria. Filters combine; all requested tags must match. Active views exclude done and removed records. `--all` includes done but still excludes removed; `--removed` selects removed records. Overdue means unfinished and due before the local calendar date. Ordering is priority, due date (unset last), creation timestamp, then ID. `next` excludes blocked and removed goals and never changes status.

Use `--` before a title beginning with a dash. `list --markdown` and `show ID --markdown` export a readable document. `--json` produces the versioned contract described in [the specification](specification.md#todo-goal-documents). JSON, Markdown, completion, brief and path output bypass decoration. Ordinary human views share Dots semantic colors, icon controls and plain fallbacks.

Todo human views use a two-space base indent with flush-left headings. Lists put the alias (or short UUID) on its own line above the title/status/priority summary, both at the same indent, with one blank line between goals. List Project/Goals fields use a single label/value gap; other detail views retain aligned values. This spacing also applies to implicit/`--print` lists and the missing-FZF fallback; wrapped lines within a goal stay together. `show` expands each goal into a prominent title, labeled fields, notes and acceptance blocks, and full UUID metadata. Titles are bold theme bright_magenta; aliases are bold theme accent, including Alias values and parent aliases; open is bold theme bright_green; high is bold theme warning, normal is regular orange, and low is bold muted. UUID identifiers retain their existing styling. Notes and acceptance text retain normal foreground. Popup rows and previews share these styles, while popup rows stay compact. At narrow widths UUID metadata moves below its label. Help uses plain command definitions with Dots-owned styling, including on Python 3.14.

## Storage and recovery

Project files live at `.dots/todo.json`; they are portable and may be committed using the project's ordinary Git workflow. Global files live at `<Dots state root>/todo/global.json`: normally `~/.local/state/dots` on POSIX and `%LOCALAPPDATA%/dots` on Windows, or `$XDG_STATE_HOME/dots` when explicitly set. Native Windows and WSL keep separate state. This feature does not stage, commit, publish or synchronize goal files.

Only a successful mutation initializes storage. Listing, completion, help, briefs, previews and `--dry-run` do not create directories, locks or state. Updates use the existing guarded transaction engine, retain recovery copies and reject concurrent changes. Malformed documents, unsupported schemas, links, special files and unsafe parents are refused. Repeating an unchanged update writes nothing. Use the reported transaction with `dots files history`, `dots files recover`, and `dots files undo` under their existing drift rules; undo can restore an entire previous goal document, whereas `todo restore` changes only the selected removed goals.

New and updated documents use schema 2. Schema-1 files remain readable and expose null aliases in schema-2 JSON output. Reading or an unchanged update never rewrites an old file. Its next effective mutation upgrades the document in the same guarded transaction, retaining the exact prior bytes for recovery/undo. Older Todo versions that only accept schema 1 cannot read an upgraded file.

Remove asks for confirmation in a terminal and requires `--yes` otherwise. JSON removal requires `--yes` or `--dry-run`. Removing a parent with live descendants requires `--recursive`; recursive restore restores all descendants. Removed records are retained without automatic pruning. All mutating routes accept `--dry-run`. Data output never prompts. Exit statuses are 0 for success (including empty/unchanged results), 1 for operation/storage errors, 2 for argument errors and 130 for cancellation.

## Popup and agent handoff

The Dots launcher includes **todo**, opening the Dots project browser. FZF owns the popup in tmux; outside tmux and on native Windows it uses the terminal. Enter opens goal actions; Alt-N creates a goal, Alt-F changes filters, F1 shows keys, Escape returns, and Ctrl-C cancels. Preview controls are Alt-P and Alt-J/K. Empty searches retain New/Filters/Help/Back. Query and goal focus survive actions. Text entry and readers open only after the chooser closes. Optional Gum provides single/multiline input, with plain terminal input when unavailable. A failed running input is never retried through a different backend.

Previews are inert snapshots addressed by numeric tokens. Each write rereads the document and refuses stale selection. Removal offers Cancel first and identifies the affected subtree. Missing FZF or popup support lists goals with an explanation; no action is selected automatically. The tmux goal browser stays nearly full screen with a one-cell outer margin. Its bottom preview expands into all space left after the current search matches, headers and notices, recalculating while you type and when the selector resizes. Expansion keeps every matching goal visible. Crowded or zero-match results use the compact four-row preview, shrinking further on short terminals. For example, at 80×24 without a notice, one match gets 12 preview rows, five get eight, and nine or more retain four. Alt-J/K scrolls the full details. Alt-P keeps a hidden preview hidden during searches and restores its current adaptive size when shown. Outside tmux, the terminal browser uses the same adaptive policy; older FZF capabilities retain the static compact layout.

Goal actions include **add note** for multiline appending. **Edit → alias** assigns or renames a goal; an empty alias clears it. Both inputs open after the chooser closes and retain UUID-based selection when returning to the browser.

When several clients share the invoking tmux session, use `todo browse --client CLIENT` (or the Dots launcher with its `--client` option). The popup targets only that client. Direct invocation refuses an ambiguous client; native Windows uses the terminal and does not support tmux client targeting.

## Todo skills

Three repository-owned skills support different tasks and are available across projects through managed links:

| Skill | Use |
| --- | --- |
| `dots-todo` | Everyday goal management, scope selection and progress updates |
| `dots-todo-planning` | Interview about a selected goal, then save and implement its agreed linked goal tree on request |
| `dots-todo-maintenance` | Develop or debug Todo's CLI, storage, popup and Codex handoffs |

Normal automatic skill discovery remains enabled. You can also ask “Use $dots-todo-planning to plan goal config-rework” or “Use $dots-todo-maintenance to fix Todo preview sizing.” The general skill routes specialized tasks without imposing an interview on ordinary goal creation or progress updates. The maintenance skill resolves the intended Dots source checkout before reading its [maintenance guide](../agents/guides/todo.md).

The managed resources `dots:todo-skill`, `dots:todo-planning-skill` and `dots:todo-maintenance-skill` target their corresponding directories under `~/.codex/skills` on all platforms. Preview them with:

```sh
dots files link dots:todo-skill dots:todo-planning-skill dots:todo-maintenance-skill --dry-run
```

Then use the normal explicit apply workflow. Existing content follows the managed backup/recovery rules. A custom user skill directory requires an explicit resource target override; the command never changes agent settings or copies skills into arbitrary projects. Repository discovery uses `.agents/skills`. Newly opened Codex clients can discover the installed skills.

Every printed, copied and Codex-submitted planning brief optionally references `$dots-todo-planning`, retaining complete instructions when the skill is unavailable. Full goal/subgoal notes, criteria and completed context remain attached. Brief generation does not launch an agent, start a goal or expand task authorization. Briefs contain labeled POSIX and native PowerShell scope examples.

## Plan a goal in Codex

Run `todo plan ID` (or `dots todo plan ID` for Dots) to open a planning conversation for the selected goal and all nonremoved descendants. Aliases work as usual. Direct invocation uses the current terminal. **Plan in Codex** in the popup closes the menu and opens a new tmux window on the invoking server/client; outside tmux it uses the current terminal. The new tmux window uses the configured `status.todo` icon (normally 󰄬), with `todo` as the short fallback for an empty icon. Window numbers, status markers and attention styling remain available; the full title stays inside Codex. The action requires a terminal and refuses removed goals. Opening a plan does not change goal status.

Thread names follow `[project] alias — goal title`, omitting absent aliases and using `global` for global goals. Every selected goal owns its own thread; selecting a child does not reuse its parent's association. Later launches resume that thread and synchronize its name. Idle threads receive refreshed goal context. Active turns and pending questions attach without another submission. `--new` records a new association and retains the old conversation. `--dry-run` prints a preview without contacting Codex or writing state.

Termux uses the existing `codex-termux` runit server and effective runit port; it does not start/restart the service or change personal settings. The optional Python WebSocket dependency is declared in [`tools/requirements-todo-codex.txt`](../tools/requirements-todo-codex.txt). Native Linux, WSL and Windows use their native Codex daemon/proxy; starting that local daemon is part of an explicit launch. Missing runtimes, dependencies, connections or Plan Mode capabilities report an error. Model, configured Plan reasoning effort, approval and sandbox settings are inherited. The launcher uses the app-server's explicit Plan Mode and verifies it before attaching the TUI. It does not install/update Codex or alter authentication, hook trust or configuration.

Both the goal list and agent-brief reader provide these shortcuts and selectable actions:

| Key | Action |
| --- | --- |
| Alt-C | Plan in Codex |
| Alt-O | Close the popup and containing Dots menu, then print the entire brief |
| Alt-Y | Copy the entire brief and remain in the browser |

Copy retains the search and focused goal/brief line. The exported text is identical to `todo brief ID`, including its `/plan` prefix, and is never restricted to the selected line or current search matches. Printing from a tmux `run-shell` binding uses tmux's normal command-output display; it does not type into the existing pane. Clipboard writes use `termux-clipboard-set`, Wayland `wl-copy`, X11 `xclip`/`xsel`, or native PowerShell `Set-Clipboard`. Missing or failed clipboard support keeps the browser open with an explanation. Brief actions use the shared fitted FZF reader; ordinary details retain their existing read-only reader.

The brief directs Codex to inspect the project, ask focused questions in batches of one to three, and develop an agreed plan and goal tree. Work packages receive acceptance criteria; useful nested work becomes grandchildren. Existing children and completed context retain their UUIDs. The agent remains read-only in Plan Mode and finishes with a proposed plan containing the agreed goal tree and acceptance criteria. Choose Codex's normal implementation action, or leave Plan Mode and say **Implement the plan**: the agent rereads the store, creates/updates the agreed goals through scoped Todo commands, attaches children with full parent UUIDs, verifies the tree, and continues directly into implementation. No separate save request or repeat interview is required. An explicit **Save these goals** request remains save-only and stops after reporting saved IDs. New goals start open and inherit their immediate parent's priority unless agreed otherwise. During implementation, the agent starts the selected parent and starts each subgoal when work begins, leaving upcoming goals open. It appends progress and verification to notes, completes verified children before their parent, and records genuine blockers without claiming completion. Existing completed work and partial saves are reconciled rather than duplicated. The brief's instructions guide the agent; goal writes retain normal Codex permissions and Todo transaction checks. They do not switch modes themselves or override an active Plan Mode restriction. Updated briefs apply on their next submission; busy conversations still attach without injected replacement prompts.

Thread associations are private local state under `<Dots state root>/todo/codex`, separate from portable goal JSON. Project threads use the project root; global threads remember the first launch directory. A launch lock prevents simultaneous creation. A receipt is saved before submission: if delivery becomes uncertain, the next launch attaches without resending so you can inspect the thread first. Use an exported brief to continue manually or `--new` for a fresh conversation. Already-created conversations are retained on failure; local association writes and Codex conversations are outside goal-file undo transactions.

## Verification and platform limits

`python3 -B tools/test_todo.py -v` exercises isolated scope, lifecycle, query, transaction, handoff and completion behavior. `python3 -B tools/generate_todo_commands.py --check` verifies static adapters against their shared definitions. Follow [testing](testing.md#todo-goals) for planning, popup and isolated native Codex checks. Native Linux/WSL/Windows Codex daemon, terminal and clipboard acceptance remains separate from Termux and controller fixtures. Windows application destinations are unchanged. Reminders, recurring goals, structured dependency graphs and cross-project aggregation remain outside this version.

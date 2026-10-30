# Todo Maintenance Guide

Use this guide for implementation changes to Dots Todo. For managing goal contents, use the [Todo skill](../../.codex/skills/dots-todo/SKILL.md); for interviews and saving/implementing agreed goal trees, use the [planning skill](../../.codex/skills/dots-todo-planning/SKILL.md). Read the current checkout's agent contract and [worktree guide](worktrees.md), inspect Git state and preserve unrelated work.

## Locate the behavior

Read [Todo](../../docs/todo.md), [architecture](../../docs/architecture.md#todo-goals) and the [focused plan](../../plans/todo.md). Trace only the relevant path:

- `todo_core.py` owns scope, schema, aliases, hierarchy and guarded goal updates. Standalone Todo discovers project/global scope; `dots todo` pins Dots. Goal writes use the existing file transaction engine. Read [safety](../../docs/safety.md) before changing a mutation path.
- `todo_commands.py` owns parser/help/completion definitions; `generate_todo_commands.py` checks or regenerates static adapters. Follow the [command guide](commands.md) for route and metadata changes. Keep raw/JSON/path/completion output undecorated.
- `todo_menu.py`, `todo_presentation.py` and `todo_input.py` own goal views and actions through shared presentation, selector and input adapters. `todo_layout.py` consumes numeric FZF geometry and match counts; its event path must not read goal storage or execute displayed text. Use [menu authoring](../../.codex/skills/dots-menu-authoring/SKILL.md) for changes to shared popup behavior.
- `todo_brief.py` supplies complete notes, criteria and the nonremoved subtree to exported briefs and Codex submissions. Keep printed/copied text identical, including the exported `/plan` prefix; the app-server submission selects actual Plan Mode explicitly.
- `todo_plan.py`, `todo_codex.py` and `clipboard.py` own explicit launches, private thread links, native transports and clipboard writes. Keep the configured Todo icon window label separate from the descriptive Codex thread name. Preserve one thread per selected goal, name synchronization, busy attach-only behavior and no automatic retry after uncertain submission. Termux uses the existing runit service; native clients use their own daemon. Keep credentials out of output and preserve personal Codex configuration.

## Preserve the workflow

Menu rows use stable goal identities and inert preview snapshots. Revalidate after dialogs before writes, keep exact tmux client ownership, and preserve query/focus and cancellation. Print/launch handoffs close the containing menu; copy stays in the browser. Preserve full notes even when only a few preview rows are visible. Review 40/80/120-column and short-terminal layouts using the [presentation gate](../../docs/presentation.md#acceptance-gate).

Plan Mode remains read-only. In execution mode, **Implement the plan** saves/reconciles linked goals through scoped CLI mutations, verifies parent UUIDs, and continues into the work without another save gate or interview. **Save these goals** saves only. Start the parent and each subgoal as work begins, append progress/verification, and complete verified children before parents. Retain recovery data and report external blockers honestly. Existing children and completed context must not be duplicated. Goal files remain separate from machine-local Codex associations and Codex's persistent goal tools.

## Focused verification

Follow [test isolation](testing.md). Choose the affected suites; run expensive Termux suites sequentially:

- Core, command or storage changes: `python3 -B tools/test_todo.py`, `python3 -B tools/test_todo_shells.py`, and `python3 -B tools/generate_todo_commands.py --check`; add relevant native-controller/transaction cases.
- Browser/layout/input changes: `python3 -B tools/test_todo_menu.py`; shared-selector changes also need the affected `test_menus.py`, `test_menu_launcher.py` or `test_menu_pager.py` suites. Check empty/overflowing queries, notices, hidden preview state, literal labels, client isolation and cancellation.
- Planning/brief/clipboard changes: `python3 -B tools/test_todo_plan.py` and affected popup tests. The optional `DOTS_TEST_CODEX_NATIVE=1 python3 -B tools/test_todo_codex_native.py` uses an owned server, configuration, model fixture and PTY. Never substitute the user's service or account. A correctly worded prompt alone does not prove Plan Mode, restored settings, early-question delivery or the normal implementation transition.
- Skill resources: run the skill-creator validator and `python3 -B tools/test_installation.py InstallationTests.test_todo_command_and_skill_lifecycle`. Check all platform profile registrations and source roots, preview purity, repeat-operation idempotence, backup/recovery and preservation of goal documents. Follow [managed files](managed-files.md) for actual link activation.

Update the authoritative docs alongside behavior, then run relative-link and whitespace checks and follow [wiki maintenance](wiki.md). Keep fixture evidence separate from native Windows PowerShell, Linux/WSL, Android clipboard and live-account delivery. Record pending acceptance explicitly rather than weakening tests or broadening the task.

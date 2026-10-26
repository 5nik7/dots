# Dots popup menus

The managed-workspace update supersedes earlier New-session name prompts and generic automatic-Termux association: popup creation uses fresh project/default IDs without a prompt, and live all-pane metadata supplies project grouping. See the [workspace plan](tmux-status-and-sessions.md#independent-tabs-and-automatic-workspaces-2026-10-26). Rename and Delete keep their existing input/confirmation flows.

**Status: G1–G6 repository goals complete, with G6 corrections implemented and Android attachment verified. Native Linux/WSL/Windows and human visual acceptance remain explicitly pending below.**

The first delivery provided this plan, a reusable [menu-authoring skill](../.codex/skills/dots-menu-authoring/SKILL.md), and repository milestones. G2 added shared Python support and isolated tests. G3/G4 delivered the session picker, launcher and shortcuts; subsequent revisions added family navigation, scrolling, compact prompts, Git workflows and fitted reader popups. Goals live here; no persistent Codex goal is created.

## Purpose and boundaries

Make useful Dots workflows discoverable through a compact FZF launcher and add an existing-session tmux picker. Follow the established `dots keys` presentation and reuse the shared interaction layer. The approved revision uses a persistent family browser. Workflows return to their launching menu; successful tmux session selection closes the launcher.

G6 adds the approved project discovery and explicit session create/rename/delete/Termux actions. Arbitrary command execution, automatic extension enrollment and a user-defined menu action format remain outside this version. The owner now requests curated family submenus. Preserve unrelated work, existing picker defaults, key-browser routes and shell capture behavior. G1 changed planning/skill files and indexes. G2 adds shared support, tests and reference documentation; it does not activate bindings, reload tmux, commit, or publish.

## Current implementation anchors

- [Shared menus](../lib/dots/menus.py): G2 provides immutable `Menu`/`Entry` records, `add_arguments`, `dimensions`, `choose`, `dots_argv` and `run_action`. Actions remain separate from display records. [Tmux context](../lib/dots/menu_tmux.py) and the [private worker](../lib/dots/menu_host.py) own exact-client selection and terminal handoff.
- [Session menu](../lib/dots/menu_sessions.py): G3 implements inventory, typed data, exact-client switching and external attachment behind matching Bash/native routes. It pins the server socket/PID and rechecks session identity before action.
- [Shared interaction](../lib/dots/interaction.py): `RichSelector.fzf` accepts scoped popup, height, query, preview-size, header and child-environment arguments; numeric tokens keep labels out of execution paths. An explicit validated backend avoids repeating capability probes without changing default backend selection for existing callers.
- [Key browser](../lib/dots/keys_cli.py) and [presentation](../lib/dots/keys/presentation.py): category selection, content-sized menus, 99% binding popups and 45% previews already exist. These are examples, not a requirement that every future menu use the binding-browser dimensions.
- [Tmux configuration](../config/tmux/tmux.conf): Prefix ? launches the existing browser with its current pane-target bridge and quiet shortcut cancellation. Preserve the actual checked-out launcher, including newer shell-capture changes.
- [Static command metadata](../lib/dots/command_metadata.py) and [native dispatch](../lib/dots/cli.py): descriptions and route discovery are data-only; native PowerShell uses shared controllers. `dots menu tmux keys` already exists. `dots menu tmux sessions` now uses the shared session controller; the root launcher now uses targeted static metadata and fixed action arrays.

## Implemented routes and launcher entries

| Route | Behavior |
| --- | --- |
| `dots menu` | **Implemented (G4):** choose a curated Dots workflow. |
| `dots menu tmux sessions` | **Implemented (G3):** choose an existing session, switch the invoking client inside tmux, or attach outside it. |

The implemented launcher order and fixed command mapping are documented in [launcher commands](../docs/commands.md#dots-workflow-menu), with the registry maintained in `lib/dots/menu_cli.py`.

Labels and order belong to the launcher registry; descriptions come from static command metadata where available. The registry declares fixed argument arrays, terminal requirements and availability, never shell command text assembled from a selected label. Preserve the caller's working directory. Registry construction checks static header/command presence, required tmux/Git executable presence and platform/Python limits without executing a tool. FZF and workflow capability probes stay at their selected interaction boundaries; opening the launcher must not collect underlying inventories or run extensions to populate descriptions. Keep unavailable entries visible with a reason and refuse their actions.

### Interaction and output

- New routes accept `--query TEXT` and mutually exclusive `--browse`, `--print`, `--json`. Ordinary interactive invocation opens FZF; `--browse` also permits a validated background tmux context. Outside tmux, browsing requires terminal input/output. Printed, JSON and redirected default views never select or execute actions. Query text filters their listings; an interactive query seeds FZF.
- Print concise choices and explicit unavailable reasons through the existing Python `Presentation` renderer. G2 implements the exact [schema-1 menu record](../docs/specification.md#shared-menu-records): `schema`, `menu`, `title`, `items`, with item `id`, `label`, `description`, `available` and `reason`. JSON bypasses decoration even when color/icons are forced and excludes executable callbacks, arguments, icons and temporary transport paths. G3 extends session items with `name`, `windows`, `attached_clients` and `current`; G2 itself exposed no route.
- Missing FZF produces a useful plain listing with a stderr explanation. Missing popup capability in a background tmux invocation produces a diagnostic and a plain listing rather than trying to prompt without a terminal. Do not retry a selector that has already failed through another backend. Help, completion and printed/JSON views must not probe FZF or launch a UI.
- Use shared semantic colors, current published palette values, optional icons and content-sized chooser geometry clamped to the invoking client. Keep unstyled views meaningful. FZF owns the chooser popup; unrelated picker defaults remain unchanged.
- A menu selection opens a workflow; it does not approve its mutations. File/theme actions keep their existing review, confirmation and transaction paths. Previews contain inert metadata and never invoke the action being previewed.
- Preserve CLI cancellation as 130. Shortcut wrappers map only 130 to success, preserving other statuses and diagnostics. Empty session inventories succeed with an empty result; actual command failures remain errors. The internal action runner retains the workflow status; the persistent launcher displays errors and returns to its menu.

### Terminal handoff

Close the launcher's FZF chooser before starting the selected workflow. Popup-owning browsers launch directly. Other workflows receive a tmux terminal popup with inline interaction after the chooser has closed; never place a second popup-owning browser inside that host. Static output uses the scrollable less/FZF reader in both normal and hosted terminals, including failures, while preserving the command's original status. Interactive workflows inherit their terminal or the explicit host.

Carry the initiating server, exact client, pane and working directory explicitly across the handoff. G2 implements `TmuxContext.capture`/`from_environment`, `verify`, a scoped FZF tmux adapter and the private terminal host. `run_action(kind='popup')` forwards a private context to a cooperating child; G4 integrates its consumption into both the key category/app chooser and binding browser while retaining its mode/preview environment. Use a fixed helper and inert argument transport for any shell-command boundary; do not evaluate labels, session names, query text or paths. Do not inject commands into a user's running shell or bypass its existing key-capture bridge.

### Tmux sessions and shortcuts

List session names, window counts, attached-client counts and current-session state. Keep session IDs separate from sanitized labels. Do not capture pane contents or start a tmux server for discovery. Retain the selected server and use exact session IDs for attach/switch; revalidate immediately before execution. Selecting the current session is a successful no-op. A vanished session, client or server produces a clear diagnostic without choosing a different target or creating a session.

Inside tmux, switch only the invoking client, including when several clients view the same pane/session. Outside tmux, attach on the caller's terminal without detaching other clients. The implemented route accepts `--client CLIENT` to identify the exact invoking client when inherited server/pane context exists. A cooperating launcher may instead forward `DOTS_MENU_CONTEXT`; a conflicting explicit client is rejected. Data views do not capture clients. If client identity is ambiguous, refuse the switch rather than relying on tmux's most-recent-client inference. Tests must cover that distinction; the current key menu's sizing helper alone does not establish exact-client targeting.

G4 adds Prefix m for the launcher and Prefix s for sessions using `run-shell -b` with explicit originating context and shortcut-only cancellation handling. These replace tmux's stock mark-pane and session-tree bindings respectively. Preserve Prefix ?, `dots keys`, and `dots menu tmux keys`. Configuration edits and isolated tests do not authorize a live reload; report activation as pending unless separately requested.

### Platforms and compatibility

Both Bash and native PowerShell dispatch the new routes to shared Python behavior, with matching flags, metadata and completions. Native Windows uses ordinary terminal FZF; tmux session functionality is explicitly unavailable and must not invoke WSL. Keep the session entry visible with that reason, and make the direct route report the limitation. Windows app destinations, profiles and state paths are unchanged.

The shared menu layer must not add work to shell startup or ordinary direct command dispatch. New direct routes retain longest-prefix resolution, including the existing `menu tmux keys` descendant. Avoid a general registry scan or persistent cache for the curated launcher. Follow [commands](../agents/guides/commands.md), [native PowerShell](../docs/powershell.md) and the [parity plan](powershell-parity.md).

## Repository goals

| Goal | Status | Depends on | Completion criteria |
| --- | --- | --- | --- |
| G1 — Planning and authoring kit | Completed | — | Plan, skill, worked example, copyable template, discovery link and indexes delivered; validation recorded below. |
| G2 — Shared menu support | Completed | G1 | Shared data/selection/context/terminal support and skill examples delivered; 87 focused/regression checks passed, with native acceptance limits below. |
| G3 — Tmux session picker | Completed | G2 | Inventory, exact-client switching, external attachment, current/empty/stale cases and cancellation pass isolated tests. |
| G4 — Launcher and shortcuts | Completed | G2, G3 | Launcher and shortcuts delivered; subsequent family/Git/reader revisions and their evidence are recorded below. |
| G4 revision — Family menus and scrolling | Completed | G4 | Compact root, curated submenus, persistent navigation, paged reports/wiki documents and isolated acceptance. |
| G5 — Documentation and acceptance | Completed | G3, G4 and approved revisions | Final mapping/docs/skill review and local acceptance passed; native/manual gaps are named in the G5 matrix below. |
| G6 — Projects and session actions | Completed | G5 | Project groups, semantic rows, explicit session actions and Termux tab adapter; local acceptance passed, native/manual limits below. |

G4 and the subsequent family/Git/reader revisions are delivered. G5 consolidates their documentation and local acceptance evidence, with explicit remaining native/manual checks. Required documentation and tests accompanied each implementation goal.

## Verification and documentation gates

### G1 delivery

- Validate the skill with the bundled skill-creator validator; verify its UI metadata, relative discovery link, reference paths and intentional template fields.
- Exercise the authoring guidance as a read-only walkthrough of the existing category menu: trace route → controller → tokenized selector → return value, checking the cited helpers and native route without creating a runtime menu.
- Run `python3 -B tools/verify_docs.py` and `git diff --check`; separately check links in the skill tree because the documentation checker covers README/AGENTS/guides/docs/plans rather than `.codex`.
- Inspect both checkouts, preview `dots wiki build --dry-run`, build and check the available wiki. If no exported inputs changed, record the no-op. If unavailable, run source-only validation and record synchronization pending. Plans/skills remain source-repository documents; no new wiki page or implemented README command is required for G1.

### G2–G5 implementation

Apply the [presentation acceptance gate](../docs/presentation.md#acceptance-gate) with the shared Python renderer/FZF adapter: populated, empty, unavailable and error views; 40/80/120 columns; light/dark themes; disabled color/icons; Unicode and long labels. Test printed/redirected output and exact undecorated JSON separately from UI views.

G2 adds `python3 -B tools/test_menus.py`; extend it or add focused suites when G3/G4 land. Cover fixed argv dispatch, unknown selector tokens, nonexecuting previews/help/completion, missing FZF/popup support, cancellation and failure propagation. Verify no inventory/provider work occurs during ordinary dispatch, help or shell startup. Record a representative launcher-opening measurement in G4 when that route exists; benchmark dispatcher lookup only if its implementation changes.

Use test-owned home/config/state/cache/repository roots, private tmux sockets and owned PTYs. Exercise two clients on the same pane, stable IDs with similar names, spaces, Unicode, leading dashes, shell metacharacters, current-session no-op, no server/sessions, stale targets and client disconnects. Check inherited cwd, host closure before handoff, readable static results, and child statuses. Never load the user's tmux configuration, run real file/theme mutations or use live sessions as test fixtures.

Run applicable existing suites sequentially: `tools/test_keys.py`, `tools/test_keys_defaults.py`, `tools/test_tmux_keys.py`, `tools/test_tmux_sessions.py`, `tools/test_file_pickers.py`, `tools/test_theme_picker.py`, `tools/test_bash_dots.py` and `tools/test_native_cli.py`. Scope broader regressions to shared behavior actually changed. Actual Windows PowerShell 5.1/7, native Linux and WSL terminal acceptance remain named pending checks where unavailable; Termux/controller fixtures do not satisfy them. Human font/color acceptance is separate from automated PTY coverage.

As behavior lands, update the command metadata and completion tests, README, command and presentation references, architecture/data contracts, testing guidance, PowerShell/platform limits, affected key docs and this plan. Review the new menu-authoring examples against the implemented shared layer. Synchronize the wiki from canonical sources in the same changes. Preserve existing confirmation/transaction rules; update safety documentation if implementation changes those rules rather than merely delegating to them.

## Delivery evidence

G1 completed on 2026-10-26 in the existing Termux checkout. The skill is discoverable through the relative `.agents/skills/dots-menu-authoring` link and its UI metadata retains automatic discovery. The command and presentation skills link to the authoring workflow.

- The bundled skill-creator validator passed. All 46 relative links across the new skill resources, workflow index and two referring skills resolve; discovery-target and UI metadata checks passed.
- The worked Python fragment compiles, and its imported symbols resolve in the current source by static inspection. The route/controller/selector walkthrough confirms index-to-identity selection and separate capability checks. No selector, application action or live tmux test was executed for G1.
- `python3 -B tools/verify_docs.py` passed: 816 relative links across 126 files. `git diff --check` passed, with separate whitespace checks for new untracked files.
- Wiki preview contained no operations; the build returned `unchanged`, and the full wiki check returned healthy. Plans and skill files do not change the current exported inputs. Existing source and wiki changes were preserved.

At G1 delivery, G2–G5 remained proposed. G1 did not add runtime routes, activate shortcuts, commit or publish.

### G2 shared support

Completed on 2026-10-26 in Termux with tmux 3.8 and FZF 0.74 (devel). Existing entry points and shortcut bindings were not migrated. No startup/dispatch import was added; launcher-opening measurement belongs to G4.

- `tools/test_menus.py`: 22 checks passed, including six native private-server cases. Coverage includes two clients on one session, 40/80/120-column chooser opening/closing, exact client routing, stale/ambiguous context refusal, Escape/Ctrl-C, literal argv/cwd/environment, held results, premature host closure, published light/dark color settings and exact data output. Completed child status 129 remains distinct from a popup hangup before a result exists.
- Existing regressions passed sequentially: file pickers 19, keys 20, theme picker 16 and tmux keys 8. Native CLI metadata/targeted-resolution and literal argument bridge checks passed (2); these are controller fixtures, not native Windows evidence. Total focused/regression checks: 87.
- Skill validation, 32 skill/reference links, both Python example fragments and new-source syntax/whitespace checks passed. Repository documentation validation passed: 834 links in 126 files; `git diff --check` passed.
- The local wiki was previewed, rebuilt and checked healthy. The final build updated Platforms, PowerShell, Testing and inventory through retained transaction `4c3a96ad64b04ae0bf0b331c167114a8`; other canonical exports were already synchronized at build time. Existing dirty source/wiki work was preserved; nothing was committed or published.

Native Linux/WSL and Windows PowerShell 5.1/7 terminal acceptance and human light/dark font review remain pending. At G2 delivery there was no new public menu command or live shortcut activation. G3 subsequently implemented the session picker; G4 adds the launcher, its child-context integration and Prefix m/s.

### G3 tmux session picker

Completed on 2026-10-26 in the existing Termux checkout. The Bash wrapper and native Python dispatcher now expose `dots menu tmux sessions`, with static help and completion for the common modes/query and explicit `--client`. Native Windows returns an unavailable diagnostic without launching tmux or WSL. No binding or live server configuration was changed by G3.

- The controller pins the server socket/PID, retains literal names separately from `$N` IDs, and checks session creation identity before switching or attaching. It consumes the shared private context when forwarded by a cooperating menu. Discovery forces UTF-8 tmux output so C-locale external clients preserve Unicode paths/names and format delimiters. No server and an empty running server both return successful empty inventories.
- `tools/test_menu_sessions.py`: 18 checks passed, including nine native private-server cases. Native coverage includes both dispatchers' typed JSON, similar names, leading dashes, Unicode/shell punctuation, two clients on one session, exact-client switching, current-session no-op, ambiguous/stale clients, vanished sessions, server replacement reusing `$0`, Escape/Ctrl-C, no server/empty server and external attachment retaining another client. Portable checks cover errors, literal argv/status, inherited context, nonexecuting data/help/completion and native Windows refusal.
- Regressions passed sequentially: shared menus 22, Bash dispatcher 24, existing tmux keys 8, shared-shell tmux sessions 3 and native CLI metadata/argument bridge 2. Total focused/regression checks: 77. Shared-menu coverage includes 40/80/120 columns and published light/dark palette settings; human visual acceptance remains separate.
- A private ten-session inventory took a median 236.6 ms over five in-process discovery/inventory samples (173.1–248.4 ms). This includes separate literal name observations and identity checks, excluding Python startup and FZF. No startup imports, dispatch algorithm changes or caches were introduced; G4 still owns launcher-opening measurement.
- Skill validation, 34 skill/reference links, both Python example fragments, source syntax/whitespace, Bash syntax and ShellCheck passed. Repository documentation validation passed: 839 relative links across 126 files; `git diff --check` passed.
- Canonical docs and the authoring reference were synchronized. The local wiki was previewed, rebuilt and checked healthy with retained transactions `77911f7d89a04038979f2c7825cdcd00` and `0d51274cd68a4c2d8f261a861fdc912f`. Existing dirty source/wiki work was preserved; nothing was committed or published.

Native Linux/WSL and Windows PowerShell 5.1/7 acceptance and human font/color review remain pending. At G3 delivery, G4 was next: the eight-entry launcher, child-context integration for keys and Prefix m/s shortcuts. G3 itself did not add those routes or bindings.

### G4 launcher and shortcuts

Completed on 2026-10-26 in the existing Termux checkout. `dots menu` now exposes the eight fixed workflows through both dispatchers, with matching modes, query/client flags and static help/completion. The registry reads only targeted first-party headers and lightweight availability checks. Root launcher JSON uses the existing base schema without action arguments or environment.

- Prefix m/s are implemented in the repository configuration with explicit socket, pane, client and cwd context. They replace stock mark-pane/session-tree bindings, normalize only status 130 and preserve other statuses/diagnostics. Private servers verified the actual binding lines; the live server was not reloaded. Prefix ? and its live-shell capture invocation were preserved.
- The key category/app chooser and binding browser consume forwarded context and merge the scoped tmux adapter with their existing mode/preview environment. Actual keys/session child popups run on the initiating client without a terminal host around them. Files/theme workflows retain their controllers and review paths; static results and failures remain visible in a terminal host until dismissed. Literal cwd tests included spaces, Unicode, quotes, shell substitutions and a trailing semicolon.
- Final sequential checks: launcher 13, shared menus 22, session menu 18, keys 20, key browser 9, tmux keys 8, key IPC 11, Bash dispatcher 24 and native CLI metadata/argument bridge 2. Total: 127 checks, 126 passed and one native PowerShell browser check skipped because that engine is unavailable. The launcher suite includes seven native private-server cases, all eight action mappings, both frontend metadata/data paths, unavailable choices, 40/80/120-column menus and status/cwd preservation. An early resize run missed a popup; the isolated reproduction and final full serial runs passed without reproducing a controller error. Human visual review remains separate.
- Five fresh Bash-frontend launcher invocations reached the first visible popup in 735.4, 729.6, 1069.6, 758.0 and 798.4 ms (median 758.0 ms). Each invocation's cancellation/exit completed before the next sample. This local measurement includes dispatch, exact-client checks and FZF popup startup, excludes selected-workflow startup and does not establish a native desktop budget. Ordinary dispatch/startup imports and resolver algorithms were not changed; no cache was introduced.
- Documentation validation passed: 841 relative links across 126 files. Skill validation, 38 skill/reference links, three Python example fragments, source syntax/whitespace, Bash syntax, ShellCheck and `git diff --check` passed. The authoring reference now includes the actual registry and a minimal `Action` example for explicitly requested additions.
- Canonical docs and the generated local wiki were synchronized. The wiki preview/build/check completed with retained transaction `a2f993e028b64c9b9a3f5d6d725f7f1a`; the check reports healthy. Existing dirty source/wiki work was preserved. Nothing was committed or published.

At G4 delivery, the approved revision below and G5 final review remained ahead. The G5 acceptance matrix now records the native Linux/WSL, PowerShell 5.1/7 and human light/dark font checks. Isolated configuration tests do not establish live shortcut activation.

## Approved navigation and scrolling revision

These historical requirements were implemented before Git was added. The current mapping is maintained in [launcher commands](../docs/commands.md#dots-workflow-menu).

Implement the exact root order `keys, tmux, files, theme, themes, anodize, debug, profile, profiles, wiki, env`, retaining icons and hiding descriptions in interactive rows. Use curated common-workflow submenus; reuse existing key/file/theme/Anodize browsers and confirmations. Preserve schema-1 nonexecuting root listings and existing public routes/flags.

Escape returns one menu level, root Escape closes with 130, and Ctrl-C at a menu closes the launcher. F1 opens contextual help. Preserve each frame's query on return, clear it on first entry into a different submenu, and return to the launching menu after completed/canceled workflows. Only completed session selection closes the launcher; canceled, empty or failed session selection returns to the tmux menu.

Output actions run once and capture complete stdout/stderr in private temporary storage. Use less with search, page/arrow keys and mouse scrolling; q returns. Supply a read-only FZF viewer when less is absent. Preserve command status separately from reader status and remove captures after use. Interactive wiki browsing also pages the selected document; raw/JSON/redirected data paths remain unchanged. No live tmux reload, commit or publication is authorized by this revision.


### Revision delivery evidence

Completed on 2026-10-26 in Termux. The eleven root names/icons and curated family actions now use a persistent navigation stack, contextual help, per-menu queries and the explicit session-success exit exception. The former root IDs/order are superseded; the schema-1 envelope, modes and flags are unchanged. The authoring skill now shows a minimal family registration and explains report paging versus interactive handoff.

- Sequential checks: launcher 15, shared menus 23, pager 7, sessions 18, file pickers 19, theme picker 16, keys 20, key browser 13, tmux keys 8, key IPC 11, Bash dispatcher 24, wiki 18, wiki Git 10 and native CLI metadata/argument bridge 2. Total: 204 checks, 203 passed and one native PowerShell browser case skipped because the engine is unavailable. Two native launcher reader/help cases were rerun after the final reader adjustment and passed.
- Native owned-terminal evidence covers the actual Prefix m/s lines, two-client isolation, root layouts at 40/80/120 columns, F1, Back with zero matches, query preservation, workflow return, key mode controls, canceled/current session outcomes, scrolling/search through a 200-line report and its exit status, FZF fallback, and short output outside tmux that stays open until q. Reader status screens expose no private capture path. Complete stdout/stderr is captured once, with private permissions and cleanup on dismissal or popup closure. Existing interactive workflow confirmation behavior is retained.
- Empty-search Back initially exposed FZF status 1 despite an expected-key result; navigation now parses expected keys on both 0 and 1. A popup-close check exposed orphaned reader files; hosted captures now live under the caller-owned request directory and are removed with it. Both regression cases pass.
- Five fresh Bash-frontend invocations reached the first visible popup in 756.1, 813.8, 738.9, 772.2 and 782.0 ms (median 772.2 ms), completing each cancellation before the next sample. The prior G4 median was 758.0 ms; this 14.2 ms local difference does not establish a performance regression or desktop guarantee. Startup imports and resolver algorithms remain unchanged, with no cache added.
- Canonical documentation, skill instructions and examples are synchronized. Skill validation, 40 skill/reference links, three Python fragments, source syntax, Bash syntax, ShellCheck, 841 relative Markdown links across 126 files and whitespace checks passed.
- The local wiki preview/build/check passed with retained transaction `ae00d8ba100f44d784ba204a6da16f00`. Existing dirty source/wiki changes were preserved. Nothing was committed, published or reloaded in the live tmux server.

At this revision delivery, G5 remained next. Actual native Linux/WSL and Windows PowerShell 5.1/7 terminal acceptance, plus human light/dark font review, remain pending; Termux fixtures do not satisfy those checks. Existing bindings use the changed controller immediately; installing/loading previously absent Prefix m/s bindings still requires configuration activation.


### Compact prompt and Unicode reader correction

**Completed on 2026-10-26.** The approved prompt format applies only to launcher root/family menus: `dots: `, `dots·files: ` and `dots·themes·plugins: `. Printed headings, JSON titles, delegated picker prompts and existing navigation are preserved. The shared chooser now accepts an optional interactive prompt override and sizes against that prompt.

The less reader must render Nerd Font private-use characters directly using reader-local `LESSCHARSET=utf-8` and `LESSUTFCHARDEF=E000-F8FF:p,F0000-FFFFD:p,100000-10FFFD:p`. Keep control escaping, ANSI color support, capture bytes, status/cleanup and FZF fallback intact. Check root/family/nested prompts and restored searches at 40/80/120 columns, actual glyph output outside tmux and in a private popup, and unchanged data/delegated paths. Both frontends share this Python behavior; native Windows visual acceptance remains pending. Refresh canonical docs, authoring guidance and the local wiki without live reload or publication.


- All 69 focused checks passed: launcher 15, shared menus 24, pager 8, sessions 18, native CLI metadata/argument bridge 2 and wiki browse/data/cancellation checks 2. Native Termux PTYs verified root, family and nested breadcrumb prompts at 40/80/120 columns, Back/query preservation, exact-client handoff and real less output for all three private-use ranges. Both ordinary-terminal and popup checks retained safe control display; FZF fallback and captured command status/cleanup passed.
- The Unicode fixture now attaches tmux clients explicitly in UTF-8 mode. Expanding the width test exposed a fixture shutdown stall while a client flushed unread redraws; cleanup now closes the PTY before a bounded wait, with termination restricted to owned test clients. The width case and full affected suites passed after that correction. The initial timed-out run is not counted as a pass.
- Source/test syntax, whitespace, skill validation, 40 skill/reference links, three Python fragments and all 841 relative documentation links passed. The local wiki was previewed, rebuilt and checked healthy with retained transaction `01061a7e550a4d93af8850287bd354f2`; existing source/wiki work was preserved. No live reload, commit or publication occurred. Native Windows visual acceptance remains pending.


### Git menu and fitted reader popups

The staged-only menu defaults recorded in this historical delivery are superseded by [Publish all from both Git menus](#publish-all-from-both-git-menus).

**Completed on 2026-10-26.** Add Git after Files, with status/info, submodule inspection, wiki inspection/operations, publish and sync. Publish delegates to its existing confirmation; sync requires a successful normally dismissed dry-run preview followed by explicit Cancel/Sync confirmation. Preserve existing repository scope and command defaults.

Fit every reader popup to its rendered rows at the existing 90% width, with a six-row minimum and 90% height cap. Capture once in a small cancellable loading host before opening the fitted reader; messages skip capture. Wiki selection hands a prepared document back to the parent before the reader opens. Count title/status, wrapping, Unicode/tabs and reader controls without modifying output. Keep command status separate from reader cancellation, exact-client targeting and private cleanup. Verify owned terminals/repositories and both frontend contracts, update canonical docs/authoring guidance and synchronize the local wiki. No live Git operation, configuration reload or publication is part of implementation.


Completion evidence:

- Git follows Files in the root, retaining icons and breadcrumb prompts. Fixed family/submodule/wiki mappings share both frontends. Publish retains its terminal confirmation and staged-only defaults. Sync requires successful preview status, normal reader dismissal and explicit Sync after default Cancel; no implicit approval, initialization or remote-advancement flags are introduced.
- All 129 final focused/regression checks passed sequentially: launcher 18, pager 15, shared menus 24, session menu 18, wiki 18, wiki Git 10, Bash dispatcher 24 and native CLI metadata/argument bridge 2. Native Termux tests measured actual less terminals at 40/80/120 client columns for short, wrapped and capped long reports, measured fitted FZF controls/wrapping, exercised loading/reader cancellation and deferred documents, and confirmed less-to-FZF fallback executes the command only once. Harmless sync stand-ins verified preview closure, default Cancel and explicit Sync; no live Git operations were used.
- Two fixture issues were corrected before final passes: the FZF geometry probe now reads terminal stderr because stdout is deliberately discarded, and the host receipt test supplies dimensions from its mocked context. Neither initial failed run is counted as a pass. Existing private-use glyph rendering, original command status, exact-client isolation and cleanup checks pass.
- Source/test syntax and whitespace, the authoring skill validator, 40 skill/reference links, three Python fragments and all 842 documentation links passed. The authoring skill and template describe output/document handoff, fitted reader ownership and the separate review/confirmation gate. The local wiki was previewed, rebuilt and checked healthy with retained transaction `4a6d0f49a73241a788539d5f4125933b`.
- Native Linux/WSL and Windows PowerShell 5.1/7 terminal rendering/input remain pending acceptance; portable/native-controller fixtures are not Windows runtime evidence. Windows retains ordinary terminal readers and the shared Git menu, with no app-destination changes or WSL bridge. No live tmux reload, commit or publication occurred. At this delivery, G5 final acceptance review remained next.


## G5 final documentation and acceptance

**Completed on 2026-10-26.** Reviewed the final launcher/session behavior after all approved revisions: public routes and flags, fixed action mappings, native controller handoff, data schemas, user documentation and authoring examples. Ran focused and applicable compatibility suites sequentially in owned fixtures, verified documentation/skill links and synchronized the local wiki. Earlier measured startup baselines remain intact; G5 changed documentation only, with no dispatch changes or added caches.

G5 closes the repository documentation and local acceptance review with the passing evidence and named native/manual checks below. It does not certify an unavailable platform or activate configuration on a running server.

| Acceptance area | Evidence and remaining check |
| --- | --- |
| Termux menus and readers | Owned PTYs and private two-client tmux servers cover root/family navigation, Back/F1/search restoration, session selection, handoff, short/wrapped/long reports, Unicode glyphs, fallback and cancellation at 40/80/120 columns. |
| Data, metadata and native routing | Shared fixtures cover static help/completion, exact undecorated JSON, redirected nonexecution, literal arguments, default-Cancel sync review and native-controller routes without Bash. These fixtures are not Windows runtime evidence. |
| Palette and font presentation | Automated light/dark semantic colors, icon policies and Unicode bytes are covered. Human review remains pending for actual Nerd Font glyph appearance, contrast, focus indicators and mouse scrolling in representative root/family/session/report views at 40/80/120 columns. |
| Native Linux and WSL | Pending separate native terminal runs of the launcher/shared-menu/pager/session suites and ordinary-terminal/inside-tmux interaction; include two-client targeting, client resize/closure and external attachment. Termux does not substitute for either host. |
| Windows PowerShell 5.1 and 7 | Pending on each actual Windows engine: entry-point/completion parity, Unicode and literal arguments, FZF navigation and previews, optional native less/FZF reading, cancellation, Git preview/default-Cancel confirmation against owned stand-ins, and status-2 tmux refusal without WSL. No Windows app destinations change. See [native parity](powershell-parity.md). |
| Live shortcuts and publication | Local isolated tests cover the tracked Prefix m/s/? behavior. G5 does not reload live configuration, commit or publish source/wiki changes. Source-only work does not establish live shortcut activation or hosted wiki rendering. |


### G5 completion evidence

- The final registry's 61 leaf/help mappings resolve to first-party metadata and native controller handoff without executing workflows. All 12 root IDs/order match README, command documentation and the JSON contract. Every action's fixed flags are advertised, including dry-run support for both sync routes. Both entry points expose all five menu flags in four help checks and eight Bash/Zsh/Fish/native completion cases without executing Git, tmux or FZF.
- Fresh sequential acceptance ran 229 tests: **226 passed, three skipped, zero failures**. Suite totals: launcher 18, shared menus 24, pager 15, session menu 18, keys 20, key defaults 11, key browser 11, tmux keys 8, key IPC 11, shared tmux sessions 3, file pickers 19, theme picker 16, Bash dispatcher 24, selected native CLI checks 3, wiki 18 and wiki Git 10. The three skips were PowerShell Codex caller capture, native PowerShell key preview and native CLI engine checks because neither `pwsh` nor `powershell` is installed. They remain pending, not passes.
- Runtime evidence is from Termux with Python 3.14.8, tmux 3.8 and FZF 0.74 (devel), using private servers/PTYs and owned home/config/state/cache/repository roots. Both ordinary-terminal and popup readers, exact-client handoff, Unicode, cancellation, default-Cancel sync confirmation, inert data/help and existing picker defaults passed. G5 did not modify menu runtime source or its tests.
- Added the missing workflow-menu entry to the native parity plan and removed stale pre-launcher wording from testing documentation. The menu-authoring skill validator, relative discovery link/UI metadata, 40 skill/reference links and three Python fragments passed; ten menu source/test files parsed and passed whitespace checks. Bash syntax and ShellCheck passed for the three menu wrappers. Repository relative-link and `git diff --check` validation passed.
- The local wiki was previewed, rebuilt and checked healthy with retained transaction `954a19b49d734b5db8aba1fdcdaceb0b`. The generator refreshed Testing plus pending Command-reference/Themes source projections; existing unrelated source/wiki work was preserved. No live reload, commit or publication occurred. The five planned repository goals are complete; the acceptance matrix records the remaining native/manual work without presenting it as verified.


## G6 project-aware session actions

**Completed on 2026-10-26.** Extend the existing session route and Prefix s with
project groups, keys-style semantic rows and an inert responsive preview. Discover
Git checkouts directly under `~/repos`, include Dots and allow additional roots
and explicit projects in optional `dots/projects.json` (schema 1). Associate
sessions by `@dots-project-root`, starting directory, then unambiguous pane paths.
Order active projects, inactive projects, then generic sessions. Multiple sessions
open a project submenu; preserve query and selection through actions.

Enter opens/switches (creating for an inactive project); Alt-N creates, Alt-R
renames, Alt-D opens default-Cancel deletion confirmation, and F1 lists contextual
actions. Alt-T appears only on Termux and opens a terminal tab attached to the
chosen session without detaching the current client. All commands use literal
arguments after chooser closure, revalidate identities, and never modify project
files. Delete-current exits navigation before killing the session. Name input uses
an optional Gum host with a plain terminal fallback. Termux failures do not change
Android settings or automatically kill a newly created session.

Preserve schema-1 JSON, print and redirected live-session listings. Native Windows
continues its explicit tmux exception; no app destinations or WSL bridge change.
Shared selector events gain opt-in validated row/query data; existing callers keep
their contracts. Factor reusable presentation helpers without loading key providers.

Acceptance: owned project/config roots; private tmux servers and two-client PTYs;
create/rename/delete/switch and stale identity/confirmation cases; empty inventories
and searches; literal Unicode paths/names; 40/80/120-column styles and preview;
mocked Android argv and failure checks; affected selector/key/launcher/metadata
regressions and documentation/wiki synchronization. Actual Android tab creation,
Linux/WSL and Windows engines plus human font/contrast review remain named native
acceptance checks. No live session mutations, reload, commits or pushes.


### G6 completion evidence (original delivery)

- Project grouping and action controls are implemented on the existing route and
  shortcut. Names/counts/current state share key-popup semantic styles; previews
  retain full details. FZF event tokens and restored fuzzy ordering remain inert.
  Explicit name hosts and default-Cancel deletion confirmations close before
  commands execute. Counts/warnings remain visible at narrow widths.
- Final isolated acceptance: **222 tests, 219 passed, three skipped, zero failures**.
  Suites: project/actions 21, sessions 19, shared menus 24, launcher 18, keys 20,
  key defaults 11, key browser 11, tmux keys 8, file pickers 19, theme picker 16,
  Bash dispatcher 24, selected native CLI 3, wiki 18 and wiki Git 10. The skips
  require unavailable PowerShell engines (Codex caller capture, native key preview
  and native engine checks). Termux mocks are not Windows runtime evidence.
- Private two-client tmux/PTY checks cover actual Alt controls, creation from
  inactive projects and empty searches, multiple-session submenus, name input,
  rename/collisions, default-Cancel and explicit deletion, current/last-session
  exit, exact-client switching, stable identity checks and 40/80/120-column
  popups. The inherited data contract, no-server observation, external attach,
  explicit creation on an owned default server and actual Prefix m/s bindings
  pass. Android launch arguments, string session action, comma/backslash paths,
  platform visibility and failures are mocked; no live Android tab was opened.
- Initial stale-prompt fixtures and a readiness check that matched preview text
  were corrected for the new project flow. The final focused reruns pass; failed
  exploratory runs are not counted as acceptance. Existing key/file/theme
  selectors retain their defaults after the shared API/style extraction.
- Five fresh session browser openings with 12 owned projects and seven sessions
  measured 1362.7, 1107.2, 1147.0, 1155.6 and 1403.8 ms (median 1155.6 ms).
  Each cancellation completed before the next sample. This records the new
  project/session workload, not a comparison with the differently scoped G4
  launcher measurement. No cache or startup/dispatch scan was introduced.
- Skill validation, 45 authoring-reference links, source syntax/whitespace,
  wrapper syntax, repository links and whitespace checks passed. Canonical docs
  and the local wiki were synchronized; retained wiki transaction
  `ce42ebb1f8d1471baada8cf9d78005fe` checked healthy. Existing unrelated work remains.
- Native Android tab launch/attachment, Linux/WSL terminal runs, Windows
  PowerShell 5.1/7 exceptions and human font/contrast review remain pending.
  Windows destinations are unchanged. No live session mutation, configuration
  reload, commit or publication was performed.


### G6 correction: generic Termux sessions, launch fallback and compact UI

**Completed, 2026-10-26.** Keep sessions marked `@dots-termux-default=1`
generic, ahead of all project-association rules. Add action-local bounded
transport probes, preferring `termux-am` and falling back to the Termux-installed
`am`; select transport before session creation and never retry a launch request.
Show useful bounded diagnostics without payloads or private paths.

Replace session/project headers with `Alt-H: keys`. A separate read-only shortcut
popup retains exact-client ownership, query/focus and pending actions; Escape or
Alt-H returns, Ctrl-C cancels, and Enter executes nothing. F1 stays Actions.
Use one control table for labels and bindings. Preview output becomes compact,
colored and home-abbreviated, with singular/plural counts and no repeated single
session name. Put it below the list, normally five rows including borders and at
most eight, based on the largest wrapped preview in the view. Shared selector
absolute sizing/wrapping is opt-in; other pickers keep their defaults.

Validate marker precedence and inventory uniqueness, help with zero matches and
submenus, five/eight-row preview geometry at 40/80/120 columns, palettes and paths,
transport/failure/nonretry contracts and existing picker/data behavior. Include
one explicitly requested device smoke check using a disposable Termux tab and a
private tmux server, preserving existing clients and cleaning only owned test
resources. Update canonical docs/authoring guidance and regenerate/check the wiki.
Native Linux/WSL/Windows acceptance remains separate; no settings, installation,
configuration reload, commits or publication are included.

Correction evidence:

- Read-only inspection of the live server now represents all six sessions exactly
  once. The three `termux-*` sessions with automatic-session markers are separate
  generic rows; existing project associations remain intact.
- Bounded device probes found the installed socket adapter unavailable (socket
  missing) and the Termux-installed legacy adapter usable. A disposable real
  Termux tab attached through the fixed helper to a private server. Both original
  fixture clients and the existing live client remained attached. Detaching only
  the owned test client exited its helper; the private server and roots were
  cleaned. No Android settings or permissions were changed.
- Early fixture failures exposed FZF's cursor-motion compression and the preview
  border/padding width. Readiness checks now use unambiguous screen text, and
  actual preview content dimensions verify five/six-row short panes and the
  eight-row cap at 40/80/120 columns. Long previews scroll to their final line.
  An initial device harness process-name parse failed after attachment; it was
  corrected and the complete attachment/client-preservation/cleanup check passed.
- Authoring skill validation and all 45 skill links pass. Canonical documentation
  links and whitespace pass; the local wiki build/check is healthy, with retained
  transaction `f0a2230cf2bd44cf8f2cd42f1951274e`. Windows destinations and tmux's
  native Windows exception are unchanged. Native Linux/WSL/PowerShell and human
  font/contrast review remain separate acceptance checks.

- Final correction acceptance: **248 tests, 246 passed, 2 skipped, zero failures**
  across project/actions (35), shared menus (24), sessions (19), launcher (18),
  pager (15), keys (20), key defaults (11), key browser (11), tmux keys (8), file
  pickers (19), theme picker (16), Bash dispatcher (24), wiki (18) and wiki Git
  (10). The two skips require unavailable PowerShell caller/preview engines;
  they do not establish native Windows acceptance. Existing picker percentage
  defaults, data/help interfaces and exact-client handoffs pass unchanged.

### Session icon and count-color refinement

**Completed.** Use `` for project rows and style each project/session icon
with its name. Non-current entries with sessions use bold theme accent in the
list and preview, including individual names in mixed-session previews. Preserve
current emphasis and inactive-project styling. Preview session totals (including
brackets) use orange, window counts green, and positive attached-client counts
yellow; zero attached clients and separators stay muted. All colors follow the
published palette with bounded terminal fallbacks. Preserve the shared key-style
tuple, color/icon policy, geometry, actions and data contracts.

Validate current/non-current/inactive and mixed-session rows, light/dark and
missing palettes, icons, color resets and Unicode at 40/80/120 columns. Run
focused session/shared-picker/key regressions using owned fixtures and update
canonical docs, authoring guidance and the local wiki. Both frontends retain the
shared controller; native Windows still reports tmux unavailable. No Windows
destinations change. Native Linux/WSL/PowerShell and human font/contrast review
remain separate acceptance checks.

Refinement acceptance: **155 passed, 2 skipped, zero failures** across
project/actions (36), session contracts (19), shared menus (24), keys (20), key
defaults (11), key browser (11), tmux keys (8), wiki (18) and wiki Git (10). The
skips require unavailable PowerShell engines. Palette fixtures cover the full
state/color/icon matrix at 40/80/120 columns, mixed-session preview names,
complete count spans/reset boundaries, malformed/missing palette fallbacks,
legacy key-style compatibility and one palette read per rendered view. Private
PTY checks preserve navigation and preview dimensions. Python syntax, source
links/whitespace, skill validation and 45 authoring links pass. The local wiki
was rebuilt and checked healthy with retained transaction
`fcf644f43eb94eb9b087d524967317d5`. No live reload, theme publication, commit or
push was performed.

### Conditional session totals and compact preview labels

**Completed.** Add a muted ` · ` before preview project totals. Use orange
only when the project contains the invoking session, foreground for other
positive totals (including compact/expanded menu counts), and red for preview
`[0 sessions]`; keep list `no session` muted. Empty-project preview titles use
bold `light_foreground`. Add `󰉋` after `Project:` using the same published
directory style as the abbreviated path, respecting icon preferences. Preview
client labels become `N attached`, retaining yellow for positive counts and
muted zero. Preserve current/accent name styles, geometry, actions and all
public data/route contracts. Shared palette styles add foreground, light
foreground and red with bounded fallbacks and retain key-picker compatibility.

Validate the state/color/icon matrix, title separators, count/reset spans,
empty/positive client labels, missing palette roles, literal Unicode paths,
40/80/120-column preview sizing and scrolling, and shared picker/session/key
regressions in owned fixtures. Update canonical docs, authoring guidance and
the local wiki. Both frontends retain shared behavior; native Windows keeps
tmux unavailable and unchanged destinations. Native Linux/WSL/PowerShell and
human font review remain separate checks.

Label refinement acceptance: **114 passed, 1 skipped, zero failures** across
project/actions (37), session contracts (19), keys (20), key browser (11), wiki
(18) and wiki Git (10). The skipped case requires unavailable PowerShell.
Palette fixtures cover conditional count colors, light-foreground empty titles,
folder/path styles with icons on/off, shortened attached labels, isolated
metadata colors for duplicate Unicode paths, reset boundaries and palette
fallbacks. Private PTYs verify five-row short previews with folder icons at
40/80/120 columns and scrolling within the eight-row cap for long previews.
Source syntax/links/whitespace, skill validation and 45 authoring links pass.
The local wiki was rebuilt and checked healthy with retained transaction
`143827614c5741a099026edc48cda8b9`. No live reload, theme publication, commit or
push was performed.

### Empty-project, count and generic-session colors

**Implemented locally.** Use normal-weight theme `light_foreground` for
empty-project list icons/names, retaining bold `light_foreground` preview titles.
Non-current positive project totals use bold, dimmed theme yellow in both list
forms and the preview, including brackets. Generic non-current session icons,
names and preview titles use bold theme blue. Current names retain bold magenta;
current project totals and markers retain orange. Project-associated names keep
their accent style. Zero-session and attached-client styles remain unchanged.

Use the existing shared palette lookup and renderer, retaining the key-style
tuple, selected-row colors, plain/data output, geometry and actions. Both Bash
and native PowerShell retain their shared controller; native Windows continues
to report tmux unavailable, and Windows app destinations do not change.

Validate the existing state/color/icon matrix at 40/80/120 columns, published and
missing palette roles, complete count/reset spans, duplicate Unicode paths and
mixed-session previews. Run project/session and affected key-picker regressions
in owned fixtures, source links/whitespace, and local wiki build/check. Native
Linux/WSL/PowerShell and human font/contrast acceptance remain separate checks.

Color refinement acceptance: **114 passed, 1 skipped, zero failures** across
project/actions (37), session contracts (19), keys (20), key browser (11), wiki
(18) and wiki Git (10). The skip requires an unavailable native PowerShell
engine. Palette assertions cover the requested colors and bold/dim attributes,
current-session priority, icon/name consistency, unchanged attached-client
styles, reset boundaries, fallback roles and key-style compatibility. Private
PTYs verify preview geometry and navigation at 40/80/120 columns. Python syntax,
source links (882 across 127 files), 45 menu-authoring links and whitespace
checks pass. The local wiki was rebuilt and checked healthy with retained
transaction `f6fa00378afd48fabdb4a674e318ee3c`. Reopening the popup loads these
source changes; no live reload, theme publication, commit or push was performed.

### Bold muted non-current session counts

**Implemented locally.** Supersede the preceding yellow-count styling with
bold theme `muted` for non-current positive project totals in the list and
preview, including `[N]`, expanded counts and `[N sessions]`. Keep current
totals orange, zero totals red and the other name/client styles unchanged.
Both entry points retain the shared renderer; native Windows remains tmux
unavailable, with no destination or data-contract change.

All three focused existing color, fallback and reset-boundary tests pass,
including the 40/80/120-column, color/icon and light/dark palette matrix.
Source links and whitespace checks pass. The local wiki rebuild used retained
transaction `cf6d6cc9a06f4f0bb2c1bb28cba75892`. Native platform and human visual
acceptance limits recorded above still apply; reopening the popup loads the
change without a live reload.

### Orange/yellow session indicators

**Implemented locally.** Supersede the preceding count colors with normal-weight
theme orange for non-current positive project totals and theme yellow for the
current project in both list forms and preview headers. Style the full current
marker (`·  current` or `· current`) in bold theme yellow. Split clipped list
details into count, marker and trailing path spans so only the marker is bold
and duplicate-project paths stay muted. Preserve name, zero-total and client
styles, plain text, geometry, actions and data contracts. Both frontends use
the shared renderer; native Windows remains tmux unavailable, with unchanged
app destinations.

All three focused existing color/fallback/reset tests pass. They cover
40/80/120-column layouts, light/dark palettes, icons and color preferences,
current/non-current/mixed/generic rows, complete marker styling and duplicate
Unicode path clipping without style leakage. Source links and whitespace pass.
The local wiki rebuild used retained transaction
`bb7fb0b07b5a4853a1427bbc45b81989`. Native platform and human visual acceptance
remain separate; reopen the popup to load the change without a live reload.

### Orange current counts and bright-green markers

**Implemented locally.** Current project counts now use normal-weight theme
orange in the list and preview, matching other positive project totals. The
full `·  current` / `· current` marker uses bold theme `bright_green`.
The shared palette lookup adds `bright_green` with terminal bright-green
fallback while preserving the key-style tuple. Keep names, zero counts,
attached-client colors, plain/data output and selection behavior unchanged.
Both frontends retain the shared renderer and existing native Windows tmux
unavailability; no app destinations change.

All three existing focused color/fallback/reset tests pass, covering the
40/80/120-column state, icon and palette matrix, current marker boundaries,
duplicate Unicode paths and malformed/missing palette roles. Source links and
whitespace pass. The local wiki rebuild used retained transaction
`ecd365db67ff4f3b8748e34880990a6d`. Native platform and human visual acceptance
remain separate; reopening the popup applies the change without a live reload.


### Publish all from both Git menus

**Completed on 2026-10-26.** Git → Publish runs `dots git publish --all`, and Git → Wiki → Publish runs `dots git wiki publish --all`. Both retain their existing terminal preview and confirmation, with no `--yes`. Direct CLI publication remains staged-only by default; sync retains its existing preview, default-Cancel confirmation and arguments. Labels, icons, output/data contracts and repository selection remain unchanged under the [presentation contract](../docs/presentation.md#acceptance-gate).

The two fixed action arrays live in the shared controller for Bash and native PowerShell. Verify exact arguments through both command builders, preserve the existing no-`--yes` and sync assertions, and run isolated launcher/Git publication tests with test-owned repositories and local remotes. Update canonical documentation, validate links/whitespace, and preview/build/check the available wiki. No Windows app destinations change; native PowerShell runtime acceptance remains pending where its engine is unavailable. No live publication or tmux reload is part of this change.

Completion evidence: all 73 tests passed sequentially (launcher 18, Git operations 27, wiki Git 10, wiki generation 18). The launcher checks both complete command arrays on Bash and the native Windows builder, no automatic `--yes`, and unchanged sync preview/confirmation arguments. Git regressions verify direct staged-only defaults, all-mode staging, ignore/gitlink handling, confirmation and cancellation using owned repositories/local remotes. Source/test syntax and whitespace, 883 relative links in 127 files, and `git diff --check` passed. The local wiki was previewed, rebuilt and checked healthy through retained transaction `ffdbef60fbe044b09de85084e57678d4`. Neither PowerShell engine is installed here, so this establishes shared-controller/argument parity and Termux runtime evidence, with native Windows PowerShell 5.1/7 acceptance still pending. Existing source/wiki changes were preserved; no commit, push or live tmux reload occurred.


### Consecutive session preview rows

**Implemented and verified locally.** Session previews disable wrapping and clip overflow at the right edge, including long names and project paths. Preview data retains the full text and existing colors/icons; each session occupies one screen row. Height uses logical line counts with the existing borders, terminal bound and eight-row cap. The shared selector's defaults and other menus are unchanged.

The former wrapped continuation of `attached` looked like a blank separator at a 53-column client width. The private-terminal geometry check now uses the reported long session names and inspects actual cursor placement to require adjacent rows. It reproduced the old two-row spacing before the change. Verify that case alongside 40/80/120-column geometry, short previews, capped many-session scrolling, cancellation and existing color/Unicode/data contracts under the [presentation acceptance gate](../docs/presentation.md#acceptance-gate).

Bash and native PowerShell retain the shared controller and existing native Windows tmux unavailability; no routes, data schemas or Windows app destinations change. Termux PTY evidence is separate from native Linux/WSL/Windows acceptance. Reopening the popup loads the source change; no live reload, commit or publication is required.

Acceptance: all 85 tests passed sequentially (project/session actions 37, session contracts 20, wiki generation 18 and wiki Git 10). The native geometry case first failed on the old wrapped display, then passed with adjacent rows at 40/53/80/120 columns, compact short previews, capped scrolling and cancellation. Existing color, Unicode and data checks passed. Python parsing, 920 relative links across 129 files and source/wiki whitespace checks passed. The local wiki was rebuilt in retained transaction `74c51162ff884d74b8b3c1e247b8a51f` and `dots wiki check` reports healthy. Native platform acceptance limits above still apply.

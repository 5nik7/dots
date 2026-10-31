# Architecture

**Status: Implemented system**

## Font management

`fonts_cli.py` owns the shared controller. `fonts/commands.py` defines static
metadata, parsing and generated adapters; `model.py` loads the library and builds
guarded plans. `providers.py` handles bounded official-source requests and archive
validation; `operations.py` plans the lifecycle; `config.py` edits inert app settings.
`workspace.py` combines personal and directory plans into one guarded collection transaction. `inventory.py` discovers installed fonts and verifies adoptable sources; `payloads.py` retains partial families and merges compatible additions. `actions.py` owns batch transfers. `defaults.py` coordinates app selection, active-profile retention and explicit preference restoration; low-level config editors remain independent. `menus.py` owns the action-first popup and installed/downloaded workflows.

`destinations.py` resolves backend `*FONTS` names through `profile_environment.py`; `directories.py` plans independent directory storage and explicit activation. Each directory retains payloads in `.dots-fonts/library` while its inventory remains in the shared local collection. Activation copies into the personal library before registration or app changes, in the same guarded transaction.
`browser.py` reuses shared context and numeric preview snapshots; `preview.py`
optionally renders downloaded fonts. `legacy.py` implements getnf/chnf compatibility.
All durable writes use `files/transactions.py`; its narrow `font_registry.py`
adapter journals fixed-key HKCU registrations alongside files. Reload/notification
occurs after commit with separate failure reporting. The checkout installer owns
command adapters; uninstalling those does not remove the personal font collection.
See [fonts](fonts.md).

The repository owns live configuration under `config/`, shell adapters under `shells/`, executable entry points under `bin/`, and shared controllers under `lib/dots/`. Keep the temporary `configs -> config` aliases until a separately reviewed cleanup. Optional repositories retain their own Git histories and are never initialized merely to run general checks.

Bash and PowerShell dispatch to shared Python controllers for managed file operations, installation, Git and theme publication. Platform adapters own filesystem and shell differences. The independent `plugins/anodize/engine/` engine authors palettes; the theme controller owns their publication and recovery. See [data contracts](specification.md) and [safety](safety.md) for state ownership.

## Live Bash Framework

`bin/dots` locates the installation and delegates to `lib/dots/dispatch.bash`.
Routing probes only candidate filenames. `catalog.bash` owns static header parsing
and the shared built-in/help model; `ui.bash` is a sourceable presentation library;
`complete.bash` computes literal suggestions. Native adapter sources live under
`lib/dots/completion` and are linked into the repository's shell completion trees.
Only help/discovery/completion load the catalog. The dispatcher has no persistent catalog cache. Managed mutations belong to the shared Python transaction engine. See [decision 0006](decisions/0006-bash-command-framework.md).

The [presentation contract](presentation.md) owns human output policy. `ui.bash` implements the shared Bash renderer; the file catalog's Python `Presentation` class mirrors it and requires policy parity checks when changed. Domain commands own their result data and choose human or data views explicitly. The dispatcher preserves extension streams; it does not decorate arbitrary output.

`lib/dots/plugin_presentation.py` adapts the existing Python renderer for application reports, resolving human/capture context and report color precedence without loading the renderer for data or ordinary redirected output. Blastoff and pkgs own their report layouts inside their plugins and pass already-collected data. Shared code resolves from the executing checkout, including isolated Python entry points. Presentation adds no backend discovery or per-row subprocesses.

The optional `lib/dots/interactive.bash` adapter is loaded only by interactive
command paths. It owns Gum/FZF capability selection, child-only presentation
policy and plain numbered prompts; the existing `ui.bash` remains subprocess-free.
The theme switcher locally prefers FZF for live palette browsing while retaining
the shared backend for review actions. Its review loop validates selection and
previews through the existing theme engine before delegating Apply to its unchanged publisher.

`keys_cli.py` and `keys/` own shared keybinding records, inert configuration readers, live evidence reconciliation and presentation. Interactive shell adapters supply caller maps on demand through a pipe; the Neovim configuration exports inert JSON for its current buffer. FZF selection reuses the shared selector and published colors. `dots-menu-tmux-keys` delegates to the same controller. Bundled Yazi/Codex reference data and provenance live in `keys/data/`; provider readers compare literal user overrides without executing applications or downloading defaults. No startup scans or persistent binding caches are introduced. See [keybindings](keys.md).

`keys/browser.py` fits aligned columns to the visible list pane and owns compact mode selection over an in-memory snapshot. The controller closes each selector before opening the next, retaining the binding query and original numeric preview identities. The main menu counts one source/default-filtered snapshot and reuses it after selection; neither app nor mode selection recaptures providers. Direct app routes retain targeted collection. A private temporary JSON file supplies full preview records; mode selection needs no shell reload helper. The shared selector's event map, initial subset, horizontal scrolling and preview placement are opt-in controls. The shared detail renderer accepts scoped indentation, used for unindented key previews. Both frontends use the controller and existing native preview-shell adapter without Bash on Windows.

`shell/keys-ipc.zsh` owns the Zsh prompt socket and its cleanup hooks;
`keys/zsh_bridge.py` owns bounded client/worker transport. The tmux launcher
identifies the source pane, and `keys_cli.py` requests its maps before counting the
main menu or collecting a relevant direct route, unless a Zsh snapshot was supplied
or configured-only evidence was requested. Server/pane checks and private runtime
endpoints keep sessions separate. No resident daemon, periodic snapshot or
application startup is introduced. See [live Zsh capture](keys.md#live-zsh-bindings-from-the-tmux-shortcut).

## Shared menu support

`lib/dots/menus.py` owns immutable display records, schema-1 snapshots, filtering, plain output, scoped FZF selection and explicit action handoff. `menu_tmux.py` captures and revalidates the originating socket/client PID/pane/session and owns transient transport; `menu_host.py` runs a selected literal argument array on the caller's terminal or a private popup terminal. Library imports do not discover tools or execute providers. `menu_sessions.py` implements `dots menu tmux sessions` for both dispatchers: it reads only the selected server, pins its socket/PID, retains literal names separately from stable IDs and revalidates before switching or attaching. Session data views inspect tmux but never probe FZF or select a client. `menu_cli.py` owns the family registry, navigation stack, per-menu search queries and fixed action arrays, using targeted static-header reads and lightweight tool-presence checks. `menu_pager.py` owns private output capture, display-row counting and the less/FZF reader. A compact loading host captures a command once and records its completed status, then closes; the parent opens a separately sized reader on the exact client. `review_output` retains command status and normal reader dismissal separately. Already rendered messages skip the loading stage. Cooperating document actions, including wiki browsing, prepare their document through a private handoff and close the selection host before the reader opens. Captures share the caller-owned transport directory and are removed after reading or cancellation. It never inventories child workflows before selection. Files/themes keep their existing controllers and confirmation paths. Git reports and publish use existing routes; menu sync adds a successful preview/read plus explicit Cancel/Sync gate before invoking the existing sync controller.

The interactive session controller also coordinates project discovery in `menu_projects.py`, inert rows/previews in `menu_session_ui.py`, and compact name input/Termux handoff in `menu_session_host.py`. `picker_style.py` supplies shared palette-derived field styles and cell fitting to keys and sessions without loading key providers. Name/confirmation hosts and the Alt-H key reference open after the selector closes. The session control table supplies event mappings and reference labels; query/focus and pending actions remain in the navigation frame. The shared selector offers opt-in absolute preview rows and wrapping while other callers retain percentage sizing. Creation, rename and deletion remain explicit controller actions; session deletion has no managed-file rollback. The public session listing schema remains separate from project inventory. The Android helper probes the socket adapter then the app-installed legacy adapter before creation, and submits exactly one launch request. It is a Termux-only adapter using the app's [execution constants](https://github.com/termux/termux-app/blob/v0.119.0-beta.3/termux-shared/src/main/java/com/termux/shared/termux/TermuxConstants.java); Linux/WSL omit it and Windows keeps its existing tmux exception.

The selector scopes a temporary tmux adapter to FZF alone, forces its client-popup path and supplies an explicit client to `display-popup`. This accommodates [FZF's popup invocation](https://github.com/junegunn/fzf/blob/master/src/tmux.go), which does not itself pass a client, using [tmux's target-client option](https://man.openbsd.org/tmux#display-popup). An unsupported adapter request fails rather than selecting another client. The host opens only after selection returns, and popup-owning children instead receive a private context that they must consume through `TmuxContext.from_environment()`. The key browser consumes that context for category/app and binding selection, using exact-client dimensions and merging the scoped tmux adapter with its mode/preview environment. Its existing mode controls and pane-target shell capture remain intact. Prefix ? retains its previous invocation; Prefix m/s provide explicit context through their own background launchers.

The internal menu [data contract](specification.md#shared-menu-records) excludes commands and environment. Private handoff requests may carry the caller's arguments and environment in a temporary directory accessible only to that user, with mode-0600 files on POSIX; they are never logged, retained in state, or included in public JSON. They are subprocess transport, not configuration files or a replacement transaction engine. Child workflows retain their existing authorization, mutation and recovery semantics.

## Existing tmux configuration

`profiles/termux/bin/termux-bar` owns per-tab startup and attachment; `shells/shared/termux-tmux.sh` integrates it at the end of Bash/Zsh interactive initialization. The launcher verifies Termux process ancestry and derives an immutable origin from root PID/start time. It marks its sessions with `@dots-termux-default=1` and registers them with `lib/dots/tmux_workspaces.py`. Reattachment finds that stored origin even after automatic or manual renaming. Only marked legacy `termux-PID-START` sessions may be adopted; unmarked sessions remain untouched. The launcher reports confirmed normal tmux exit with internal status 20 so the startup hook exits the outer shell. Detach and unexpected server loss retain the shell. See [startup behavior](shell-init.md#termux-tmux-startup). Fish and the explicit `t` helper retain their behavior.

`tmux_workspaces.py` is the private shared controller for Prefix C, popup creation, launcher registration, project reconciliation and creation-order numbering within project/label groups. Session-local metadata owns identity, origin, automatic/manual mode, expected name and observed project roots. It serializes mutations with a server-specific lock (up to 15 seconds waiting), then starts a separate work budget: three seconds for routine project observation and 15 seconds for creation, adoption or a complete numbering pass. It uses native session IDs and refuses name collisions. `shells/shared/tmux-workspaces.sh` queues bounded background workers on changed Bash/Zsh pane directories; tmux lifecycle hooks cover creation, closure and manual renaming. Project reconciliation targets only the affected workspace and sessions sharing its windows; group numbering separately observes the complete inventory through the picker association helper and updates only changed values. Incomplete numbering observations retain previous numbers without aborting successful creation/reconciliation; controller-owned renames skip redundant callbacks. All live panes across windows contribute canonical Git/worktree or explicit project roots. Zero/one/multiple roots select termux/project/multi prefixes without changing IDs, windows or processes. Manually changed names disable automatic naming while project association continues updating. Status providers only observe; they never rename or create sessions.

`config/tmux/tmux.conf` owns the status row count and layouts after sourcing the optional generated theme. On Termux, a system row with clock, independent Termux tab numbers and battery sits above the current tmux session badge followed by windows; outside Termux only the tmux row appears. Reloads reset `status-format` to tmux's standard layout and save that window row in `@dots-tmux-row`, retaining its mouse ranges and scrolling. `default/themed/tmux.conf.tpl` publishes semantic color options, including `bright_green` current-window numbers and accent markers on `selection_background`, bold `bright_foreground` current names on `selection_background`, `foreground` inactive Codex names with `magenta` numbers, `dark_foreground` ordinary inactive names/numbers, and the `selection` active-pane border. The main configuration owns conditional weights, session labels without underlining, single-space number/name separators and `│` section boundaries on `dark_background`. Theme-only refreshes update styling without changing either layout.

`config/tmux/termux-status.py` resolves the directory-linked adapter to the repository and invokes `profiles/termux/bin/termux-sessions --json` once per asynchronous job with a one-second timeout. It validates the snapshot and emits only numeric labels and controlled tmux styles. `client_tty` selects the viewing tab. Its `--tabs` output follows the clock, hides for a singleton and clips around the current tab while reserving clock/battery space. Earlier compact/split modes remain compatible. The lower row reads session-local tmux numbers maintained within project/label groups by lifecycle and reconciliation events, independent of tab discovery and failures. Both layouts display only the current tmux badge, without underlining and with a quarter-width budget capped at 30 columns. Managed labels omit immutable IDs; default labels stay hidden. Visibility tests use plain fields rather than recursively rendering complete styled rows. Native window scrolling/mouse ranges remain intact. Window numbers depend only on the current session’s window count; duplicate names disappear before clipping. Session labels and both current and inactive windows retain padding; warning brackets omit it. No persistent discovery cache, daemon, Android API access or tab switching is introduced.

`config/tmux/gitmux-status.py` bounds the optional gitmux process to one second and 16 KiB, suppresses errors, rejects control characters and escapes literal Git names while preserving configured tmux style spans. Gitmux owns Git discovery and counts; the adapter only joins adjacent Dots-styled line totals and assigns conflict coloring to an adjacent ahead/behind pair before escaping ordinary text. Its opt-in snapshot mode concurrently calls optional `git-it info --json` in the active pane directory under the same one-second deadline with a separate 64 KiB limit. That provider owns remote selection and host aliases, matching dots.yazi. The adapter retains only a supported host icon when a remote exists, combines it with Gitmux output using a first-delimiter split, and clears each failed provider independently. Both label consumers reuse one asynchronous job; no metadata cache or network request is added. The original Gitmux-only interface remains available. The linked gitmux YAML owns layout and refers to semantic options from the existing tmux theme include. The canonical tmux config owns inline placement, separators and width limits; native Windows has no consumer.

`config/tmux/codex-status.py` owns local foreground Codex detection. Each client status context shares one asynchronous job across windows: one tmux pane inventory reduces titles to boolean Working and explicit Waiting/Action Required flags, then one same-user procfs scan matches process name, foreground process group and controlling terminal. This handles shell/Node wrappers without reading argv, environment or session files. Explicit Waiting or Action Required overrides a lingering Working title in the same pane; across separate panes, Working wins over waiting, then idle. Stopped/background/exited processes and retained dead panes are excluded. Only validated window IDs and idle/waiting/working tokens leave the helper. The one-second total deadline bounds a 128 KiB/2048-pane inventory and 8192 process records of at most 4096 bytes each. Failure clears the snapshot; no persistent cache, daemon or network access is added. Theme options supply magenta for inactive Codex numbers, foreground for inactive Codex names, dark_foreground for ordinary inactive names/numbers, accent for current/inactive markers, and bright_foreground/selection_background for current names. Tmux owns bold inactive digits and bold, dimmed inactive names, Working/current marker boldness, trailing ``/`` markers with a single separator after visible label text, numberless labels and warning priority. When a singleton window has no visible name or alert, its marker moves into the session label; layout formats reserve its width before clipping the name and share the same existing inventory job. Session markers use bold accent on the session background. The current name span is bold on selection_background; inactive backgrounds remain unchanged. Each span restores the section style afterward so markers and padding retain their existing styling. Warning labels retain bold red priority throughout. Procfs is available on Termux/Linux/WSL; unsupported or inaccessible process metadata falls back to ordinary styling. Native Windows has no consumer.

`config/tmux/android-status.py` (retained for independent consumers; disabled in the shipped bar) owns only the selected network indicator before the battery. Two concurrent, one-second, size-bounded CLI reads call the adjacent Wi-Fi and cellular Androidots scripts with `--json` through the same Python interpreter. It does not import their internals or collect Android APIs; the scripts own caches, permission gates and detached refresh workers. The adapter validates icons, signal levels and theme-color arguments, then emits an equal-width icon/marker slot with controlled tmux styles. Connected Wi-Fi wins; cellular requires explicitly disconnected Wi-Fi, enabled mobile data and a connected data state. Missing, invalid, expired or unknown Wi-Fi produces a neutral muted `?`, as does disconnected Wi-Fi with unavailable cellular activity. Only fresh disconnected Wi-Fi plus fresh confirmed inactive telephony-device data hides the segment; registered-cell signal cannot establish activity or device freshness. Retained positive connection observations remain eligible with `~`; an uncertain decision involving either retained stale snapshot shows `?~`. An absent network emits no separator. Notification, volume and location commands remain standalone and are not polled by tmux. The status layout and semantic colors follow the [tmux theme contract](themes.md#tmux).

`config/tmux/battery-status.sh` remains a tmux-format adapter for `~/repos/battery/battery`, validating its colored icon/percentage record and translating ANSI red/yellow/green into tmux styles. The external battery project owns Android API access, charging glyphs and thresholds. Its fixed-width mode uses one space after the icon and pads after the percentage. Its style reset inherits the top row's background. Helpers are loaded from `${XDG_CONFIG_HOME:-$HOME/.config}/tmux`; Python 3 is required for session discovery and Bash for the battery adapter. The config defaults to five-second asynchronous refreshes.

The shared Bash/Zsh `t` function belongs to `shells/shared/functions.sh`, not the Dots dispatcher. It selects an exact named session, creating only when missing, and switches rather than nesting when already inside tmux. Plain `t` resolves the Git worktree root on demand and derives the session name from its basename; an explicit name bypasses detection. Git is not required for startup or the non-repository Work fallback. See [shared commands](shared-shells.md).

## Existing Yazi Configuration

`config/yazi/plugins/dots.yazi` is the active, remote-installed Yazi plugin bundle. The standalone `dots.yazi` repository owns runtime source; publish there and update this copy through `ya pkg upgrade 5nik7/dots` so the package manager retains revision/hash ownership. Its `main.lua` exposes setup, command dispatch, image/Markdown preview and seek routing, and Git fetching; internal Lua modules retain separate Yazi-managed state. Dotline is the bundled Yatline-derived renderer, with a combined Git-head/repository module, a local `hover.lua` component for the hovered path, icon/name, and symlink target, and a bundled hostname/user component. The Git-head module owns both display getters and one shared refresh generation, including optional host icon and ownership metadata obtained through one asynchronous local `git-it info --json` call. It retains only validated icon/ownership fields, rejects stale results with the status, and spawns no commands during rendering; git-it owns remote selection, aliases, and configured owner matching. Borders, folder rules, projects, and pane toggles share the same plugin directory. The LS_COLORS module owns startup parsing and one metadata-based style resolver shared by file-pane rendering and the hovered header item; Dotline accepts full styles without mixing escape codes into measured text. Hover splits the fitted link target into directory and basename spans for independent styling while retaining one path-fitting budget. It owns per-part source selection, style overrides, visibility, and icon spacing; it clones base styles before overrides and uses only existing metadata for the directory prefix, without redraw filesystem calls.

The bundled `dots.preview` module owns optional image/Markdown previews, platform overrides, bounded asynchronous renderer commands and per-tab source toggling. It uses stable numeric Yazi tab IDs and rejects stale preview results; theme refresh does not reset its state. The personal configuration selects Chafa/vhalf on Termux, mdcat for Markdown and Alt+m to toggle Bat source view.

The Yazi `init.lua` owns personal options, while its keymap and fetcher rules address `dots`. Original merged plugin directories remain inactive for reference and are no longer package dependencies. The [plugin README](../config/yazi/plugins/dots.yazi/README.md) owns configuration and command details. This is application configuration, independent of the Dots CLI and managed-file transaction engine.

## Shell initialization ownership

`lib/dots/init.bash` emits integration-only hooks before extension discovery.
`lib/dots/shell/` owns settings definitions, native adapters, derived paths,
portable palette data, and prompt refresh. `shells/` owns personal preferences
and minimal native startup wrappers. `bin/dots.ps1` provides native PowerShell generation plus bounded setup, inspection and recovery. `dots env` reports resolved Dots values without inspecting
private shell state. Its human layout lives in `lib/dots/shell/env-view.bash` and
uses the shared Bash UI helpers; scalar, JSON and ordinary redirected output
bypass that renderer. See [shell environment](shell-environment.md).

`bin/lib/common.sh` owns shared sourceable Bash/Zsh utility, logging, formatting, spinner and color-array helpers. Loading only defines helpers; startup no longer allocates the legacy 256-color arrays. The former `bin/colors.env` and its startup-created named globals are removed. Human helpers obtain styles lazily from the renderer; caller-owned variables remain untouched. Path operations, case conversion and quiet checks use builtins; human messages lazily reuse `lib/dots/ui.bash`, with a plain fallback for standalone copies. Optional eza formatting is confined to explicitly requested filename/icon helpers. See [shell utilities](shell-utils.md).

PowerShell personal startup uses `profile.ps1` (with the installer-compatible host entry), `init.ps1` and a guarded `interactive.ps1`. Helper definitions live separately from explicitly dot-sourced optional integrations; the shared native adapter remains responsible for settings, paths, published colors and prompt refresh. See [PowerShell startup](shell-init.md#powershell-profile).

## Existing Zsh Configuration

`shells/zsh/zshrc` resolves its own file through symlinks and sources the adjacent `init.zsh` directly; `interactive.zsh` owns startup order; `keys.zsh` owns personal ZLE preferences, plugin-aware bindings and cursor/history-search hooks; its `core/`, `integrations/`, and `platforms/` modules separate shared setup, tool activation, and execution-environment detection. Existing public module entry points remain available. Generated shell data belongs in user cache directories, not the repository. See the [Zsh guide](../shells/zsh/README.md).

## Local Development Worktree Tooling

`tools/worktree_lifecycle.py` manages explicitly enrolled development worktrees independently of the public CLI and transaction architecture. It owns only Git-local enrollment/lock metadata and guarded calls to non-force Git worktree removal. Ordinary maintenance uses the existing checkout without invoking this helper. Optional worktree procedures, known-live-use review and platform limitations are defined in the [agent worktree guide](../agents/guides/worktrees.md). No CLI command, configuration loader, hook or background service is added.

## File Catalog and Configuration Layout

`lib/dots/files/mappings.py` owns stash/restore, interactive mapping edits and
explicit new mappings. It validates candidate catalogs in memory, uses shared
presentation/interaction adapters, and composes changes through Installation and
Store. No source contents are exposed by these commands. Installation's shared
apply accepts catalog locks and receipt-free metadata-only batches; original
baseline ownership remains in its single installation receipt.

`config/` is the canonical source directory; `configs -> config` is a temporary
compatibility alias in the parent and platform repositories. The parent owns the
Neovim gitlink at `config/nvim`; Neovim retains independent Git history.
`tools/migrate_config_paths.py` previews and journals identity-preserving retargeting
of existing home links. It is separate from a future general installation engine.

`.dots/sources.json` owns repository composition and exclusions. Every base platform profile owns its complete `files.dots` inventory in `profile.json`, alongside bundled platform mappings. Independent repositories may retain `.dots/files.json` catalogs. `style_config.py` resolves shared/default and per-profile visual preferences; `theme_styles.py` produces inert native consumer data during explicit theme publication. `lib/dots/files/catalog.py` owns terminal presentation using the Bash UI color/icon policy, validation,
read-only observation/discovery, classification and atomic metadata tracking. Thin
`bin/dots-files-*` commands expose this through the Bash dispatcher; completion uses
the same data reader directly without extension execution. See [files](files.md).

`lib/dots/files/check.py` owns absent-source inspection and interactive catalog-only
removal. It consumes the same catalog, resource presentation and optional Gum
confirmation helpers, and submits guarded metadata operations to the existing
transaction Store. Bash and native PowerShell delegate to this controller; no
target mutation or separate recovery engine is introduced.

`lib/dots/files/repair.py` owns current-platform destination inspection, automatic eligibility, prepared decisions and batch application. `repair_picker.py` supplies the optional terminal issue helper and inert metadata previews through the shared FZF/Gum/numbered selector. Internal issue/action identities are separate from display text. Repair composes catalog ownership, receipt/latest-transaction evidence and existing installation receipt updates, then delegates replacement and recovery to the shared Store. It never calls the installation/theme planner, edits source catalogs or recursively discovers repair targets; selected objects are hashed for drift protection. Both Bash and native PowerShell route to this controller.

## Shared Theme Engine

`lib/dots/themes` owns native palette loading, semantic colors, literal template
rendering, cached initialization, compatibility APIs, journaled publication, fixed
application connectors, Git source lifecycle and explicit wallpaper adapters.
Bash/Zsh color arrays project resolved Dots colors over native palette extras, with generation-time format calculations and explicit ownership for stale-name cleanup; the [shell API](themes.md#shell-and-neovim-behavior) defines compatibility and reserved names.
Its `app-env.bash` adapter validates rendered FZF assignments as literal data
and adds their colors to published Bash/Zsh and Fish initialization. The Gum shell
template is rendered without execution during publication. The small `gum-env.bash`
adapter loads the published artifact in interactive Bash startup and the Bash/Zsh
`set_theme` published-palette path, including Bash/Zsh prompt refresh. Noninteractive
startup and generated theme-init output remain independent.
`bin/dots-theme-*` exposes the sole theme CLI, including native palette discovery and queries. The data-only `discovery.bash` module owns flat theme IDs, current-ID resolution and native family/flavor enumeration for commands, switcher, views and completion. Sourcing only defines helpers; scans remain on demand. Listing retains ID validation/deduplication, while completion preserves its existing literal hints; selection validation remains in the loader. Shared view/initialization helpers serve the CLI and palette helper APIs; there is no separate plural parser.
Legacy `themes/bin` entry points have been removed; shell integration lives in
`lib/dots/shell` and shared theme helpers in `lib/dots/themes`.

Flat `themes/ID` variants own semantic `colors.toml`, optional native `palette.toml`
and backgrounds. `default/themed` owns bundled templates; profile-local `themed`
overrides them. User-installed themes contribute data only. The stable XDG state
`dots/current/theme` symlink selects a generation under `dots/themes/generations`.
Codex consumes the existing rendered bat syntax theme through a fixed
`CODEX_HOME/themes/dots.tmTheme` connector; Codex-Termux shares that home. No
additional renderer, wrapper integration or startup scan is needed.
`lib/dots/themes/bat_cache.py` owns Bat configuration discovery, bounded custom
syntax snapshots, compiler/input fingerprints and private cache compilation for
both the Bash and native Python/PowerShell publishers and inactive setup paths.
Publication fingerprints include these inputs; cached shell initialization stays
independent of syntax discovery. The existing publishers retain journal,
activation and recovery ownership. See [custom Bat syntaxes](themes.md#custom-bat-syntaxes).
Leaf consumes a generated UI TOML plus the same bat syntax artifact through two fixed connectors. Its external syntax support is maintained as a [source patch](leaf-build.md) for a separate Leaf checkout; Dots does not vendor Leaf; its optional setup component builds the pinned source in owned cache storage.
Vivid and FSH consume generated semantic templates through fixed XDG connectors.
The Bash/Zsh adapter selects the published Vivid file; Zsh caches its data output.
The Zsh-only FSH adapter runs after plugin loading and generation changes, using
FSH's native INI loader in an isolated Dots cache and preserving user overlays.
Validated data is also saved as the native FSH startup script in `FAST_WORK_DIR`,
with non-Dots selection backups and stale compiled-code invalidation; subsequent
shells can load the last good palette independently of the Dots build cache.
Journals preserve previous pointers and fixed app connector objects. Application
settings remain in `config`; generated palettes, bat caches, backups and wallpaper
selection records belong in machine-local state. Connector paths beneath symlinked
app directories may physically reside in a repository and must not be published as
machine-specific configuration.

The separate local Anodize.nvim plugin owns Neovim palette normalization, rendering
and reload lifecycle. `config/nvim/lua/util/dots_theme.lua` preserves the startup,
reload and dashboard interfaces; `dots_theme_legacy.lua` retains bounded raw data
for compatibility helpers only. Personal highlights and lualine configuration
remain Dots-owned. The old native adapter module is retained for compatibility,
but is not part of startup or automatic reload. Zsh continues reading generated
shell data. Wallpaper actions remain explicit capability-checked adapters. See
[themes](themes.md), [Anodize](anodize.md#neovim-integration), and
[decision 0008](decisions/0008-config-catalog-and-theme-apps.md).

## Git and file operation engines

Under [decision 0010](decisions/0010-git-and-managed-file-operations.md), `lib/dots/git` owns the adapted, attributed Git engine and uses shared Bash UI helpers. Inspection and mutation are separate modules, with static command metadata and no standalone git-it dependency. Git operations are incremental and preserve partial results. The shared
`lib/dots/git/inspection.py` owns new repository facts, safe descendant discovery,
submodule completion and publication selection for both frontends. New views use
Python Presentation/resources/progress. Bash and native publication engines
consume the selected forest and revalidate its registration digest without
adding excluded ancestors to their mutable parent maps.

`lib/dots/files/browser.py` owns the interactive tracked-config controller and
uses the catalog's observation/detail renderer plus the existing Manager planner
and Store transaction engine. `lib/dots/interaction.py` owns shared Python
selection and optional confirmation plumbing, with `interactive-select.bash` as
its private argv/result bridge to the Bash interaction adapter: keyboard stdin,
terminal UI on the provided stderr stream, and exact selection on stdout. The
browser supplies its visible stdout terminal as that UI stream; file and Anodize
confirmations supply stderr, keeping captured results separate. No shell
expressions are evaluated from selection labels. The browser retains approved
operations and source/target/catalog guards in memory until Apply.

`lib/dots/files/manage.py` composes location registries, catalog ownership, preview and presentation. `transactions.py` owns durable staging, object integrity, locks, replacement, rollback, snapshots and recovery. Every mutating file route uses it; `track` remains metadata-only. Catalog and location data belong to their owning repositories. User preferences and transaction/backup records belong in XDG config/state.

## Progress rendering

`lib/dots/progress.bash` and `lib/dots/progress.py` own equivalent [progress policy](presentation.md#operation-progress). Controllers opt in after excluding data and preview-only modes. Bash uses a private control pipe and rendering child; Python uses a scoped rendering thread. Actual work stays in its original calling context, and no progress files or persistent state are created. Existing human renderers stop the Bash display before messages; Python contexts suspend rendering around verbose action rows and finish before ordinary controller output. The file engine reports phases after durable boundaries without changing its journal schema. Prompt-capable/direct-output children run with animation stopped; private Anodize bridges suppress nested progress. The Bash dispatcher and shell startup do not load the rendering backend. Help, completion and data paths never start rendering workers or probe optional progress tools.

## Anodize authoring boundary

`plugins/anodize/logo.py` owns the [LOGO1/LOGO2 contract](anodize.md#terminal-logo), exact fallback artwork and explicit alternative graphics/layout choices. Routine and embedded previews default to LOGO1; help uses LOGO2 when it fits. The pure shared `text_gradient.py` helper interpolates hint/info/accent stops within independently identified artwork regions; the builtin Bash renderer follows the same integer formula. Colored banners read bounded published palette snapshots, while addressed palette colors flow directly into results and the shared preview renderer. Palette-bearing results and draft review compose branding, metadata, body and notes in one ColorView, including its background from the first row. No theme resolution or startup work is added. Core-owned `logo.bash` supplies equivalent static Bash help without Python or extension execution; native help imports the core Python renderer. Only Anodize help/dispatch loads its logo options. Interactive Preview/Extract render their result once into the shared document handoff/reader after selection, preserving terminal styling while closing the picker host before the fitted reader opens. Branding and static help do not call the engine, authoring operations or transaction store.

`plugins/anodize/engine/` is an independent pure Go color engine; `plugins/anodize/` owns Python authoring and the private Bash publication bridge. It reuses `files/transactions.py` and existing theme rendering/publication. `bin/anodize` and static `dots-anodize-*` routes provide CLI access. No engine calls occur during shell startup. See [decision 0011](decisions/0011-anodize-authoring.md).

Anodize standalone completion reuses generated copies of the shared Bash/Zsh/Fish adapters. Its private query bridge translates the standalone command line into the Dots completion protocol, reading bundled static headers and the selected theme repository without executing leaf commands or the Go engine. `tools/generate_anodize_integration.py` owns reproducible adapter generation and `man/anodize.1`; command and option text in the manual comes from the Python parser.

## Local theme plugin execution

The Bash theme publisher invokes the Python plugin coordinator once after commit.
Anodize continues to delegate apply to that publisher. The coordinator reads the
immutable generation's normalized palette JSON, serializes execution under the
existing publication lock and a plugin lock, and runs explicitly selected Bash
children. Neither downloaded themes nor shell startup discover executable hooks.

Bundled GTK 3 and Qt6ct adapters consume rendered template data and use the existing
file Store for app copies, narrow configuration registration and ownership receipts
in one retained-backup transaction. Custom user hook effects are outside that Store
and publication rollback. The [plugin contract](theme-plugins.md) owns discovery,
selection, runtime environment and retry behavior.

## Shared interactive shells

`shells/shared/` owns portable public environment settings, platform detection, runtime paths, FZF settings and user-facing functions/aliases for Bash and Zsh. `bin/lib/common.sh` remains the script utility library. Native startup routing, completion engines, ZLE/Readline hooks and tool activation remain in shell adapters; old function/alias files delegate to the shared resources. Zsh private/platform modules remain native. See [shared shells](shared-shells.md) for precedence, compatibility, prompt refresh and supported integrations.

## Unified theme command ownership

`bin/theme` forwards to the live Dots dispatcher. The shared theme handler owns
family queries as well as full-ID operations; generated wrappers contain no
independent parsing or palette logic. Data-only family metadata readers serve
help, completion and command generation. The theme publisher and Git importer
share a journaled command-generation pointer under theme state. Shell startup
loads published initialization and completion registrations directly, without
scanning theme directories. Family logos live in `themes/FAMILY/logo.txt`;
the Catppuccin PNG asset lives alongside its text logo. See [themes](themes.md#unified-commands-and-family-shortcuts).

## Shared file styles and Yazi snapshots

The theme file-color engine resolves declarative style layers and derives Vivid,
LS_COLORS and versioned JSON/Lua snapshots from one palette. Publication owns the
complete generation; shell adapters consume its LS_COLORS without regenerating it.
Rule edits reuse the existing file Store rather than introducing another journal.
The shared theme presentation module renders structured palette/style tables for
human queries and native previews. It consumes the resolved or published palette
directly for full views; it does not regenerate Vivid suffixes to display them.
Machine interfaces bypass that renderer.
After publication, an optional bounded Yazi DDS notification requests refresh.
The plugin reads its own configured state root, validates a complete snapshot and
updates UI colors without re-running feature setup or doing redraw-time I/O.
See [file colors](file-colors.md) for ownership and matching boundaries.

## Checkout setup ownership

`lib/dots/files/install.py` owns bounded installation planning, ownership receipts and source-update orchestration. Root shell/PowerShell scripts and `dots init --setup` delegate to it. `file_platform.py` supplies native locks, safe object checks, file/directory flushing and state roots to the existing catalog and transaction Store. Installation receipts are final operations in the same file transaction as target changes.

The theme publisher shares its immutable generation preparation with the setup bridge. Setup holds theme/command publication locks and publishes generated pointers/connectors through the file Store; ordinary theme commands retain their existing publisher. Fixed config connectors share a TSV definition. Setup never runs app reloads, wallpaper actions or theme hooks. See [installation](installation.md).

### Shared resource presentation

`lib/dots/resources.py` and `resources.bash` implement lazy, read-only file-style
matching for human renderers. `resources.tsv` is their shared icon and filename/MIME
registry. Theme publication produces the data-only `file-styles.tsv` projection
from resolved rules. The Bash UI loads its resource adapter only on first use;
Python Presentation creates a lazy resolver. Help and data routes need no style
snapshot or classifier process. Native PowerShell help/bootstrap uses `ui.ps1`;
POSIX bootstrap dependency errors use `bootstrap-ui.sh` before Python is available.
These adapters own presentation only; installation and transaction logic remain
in their existing owners.

### Git presentation roles

The file-style resolver also owns the sibling `git` namespace and its existing override layers. Theme publication exports its full styles in JSON/Lua and a separate `git-styles.tsv` projection. `lib/dots/ui.bash` exposes lazy Git-role lookup backed by `lib/dots/git-styles.bash`; the Git renderer chooses roles without resolving a palette or spawning per-row tools. Resource rows accept an optional label style while keeping filename matching independent. See [Git styles](file-colors.md#git-styles) and [the projection contract](themes.md#cli-git-style-projection).

The Yazi color-reference namespace preserves tokens through configuration cloning and resolves them from validated snapshots during setup/refresh. Git indicators cache complete styles separately from Git status; header defaults use the same role namespace. CLI ownership highlighting caches local fetch-remote matches per repository without changing publish policy or structured output.

The Starship/Blastoff integration uses the default palette template and bundled theme-plugin lifecycle. `starship.py` owns TOML section scanning, configuration-path resolution, palette-only edits and Blastoff lock coordination; the shared file transaction store owns backups/replacement/recovery. The saved personal `dots` theme owns module styles independently of generated palette values. No Blastoff core dependency or prompt-time palette process is added.

The Git theme consumer uses a generated include and the fixed connector table.
Git's Delta processes read generation-local bat assets through an isolated XDG
cache root. The file manager's `git_platform.py` owns the bounded platform-selector
plan shared by install, direct link and mapping apply/restore; generic catalog
overlap rules remain unchanged. The consolidation migration uses existing mapping
transactions/receipts rather than a separate mutation engine.

Verbose file-operation output uses an optional Store observer with a human renderer in
`lib/dots/files/events.py`. Bash theme operations use `lib/dots/verbose.bash`.
Both reuse existing resource styling and progress suspension; observers carry no
persistent state and do not own transaction decisions. See [verbose output](presentation.md#verbose-operations).

### Interactive file selection

The Python interaction adapter owns scoped FZF-first rich selection. The files
picker owns candidate metadata and bounded content previews, shared by file
controllers and the browser. Selection returns exact catalog IDs or paths to the
existing planners; it never applies transactions or grants approval. Private
transient snapshots carry opaque selection tokens and metadata, not file contents.

## Native PowerShell command adapter

`bin/dots.ps1` owns dependency-free native help/init and transports literal argument arrays through `lib/dots/native.py` to `lib/dots/cli.py`. Shared built-in headers live in `lib/dots/metadata/`; `command_metadata.py` reads extension headers without executing them. The native CLI reuses the existing file controllers, `Store`, presentation/resources, progress and interaction adapters. `files/app_paths.py` owns Windows app destinations and the shared cross-platform eza and Television destination resolvers used by both theme publishers. `git/cli.py` invokes Git with explicit argument vectors. `themes/palette_native.py`, `theme_cli.py`, `setup.py` and `bridge.py` supply native theme data, publication, inactive setup preparation and Anodize integration. Native generated commands have verified manifests; filesystem replacement stays in the existing transaction engine.

Bash's established Git/theme frontends remain during native acceptance. Do not maintain competing catalogs, transaction implementations or shell-specific flag semantics. The [PowerShell reference](powershell.md) records actual capabilities and pending native checks; the [parity plan](../plans/powershell-parity.md) owns rollout status.

Anodize authoring resolves both user and repository theme roots; explicit built-in
saves and journaled promotion remain in its Python controller and the shared Store.
`plugins/anodize/interactive.py` owns transient drafts and token-based preview snapshots.
`anodize/completion_preview.py` serves explicitly displayed Zsh FZF-tab previews,
with cache lifetime owned by the FZF invocation. Ordinary static completion remains
engine-free. Both Dots and Anodize call `themes/presentation.py` for palette syntax
previews; unsaved drafts pass resolved colors without publishing a theme.

## Androidots location and local completions

The bundled Termux profile owns `termux-geo`, its Bash acquisition/cache/controller code, jq normalization, static completion templates, installer, and command tests. It reuses the parent Dots Bash UI/progress/resource helpers when available, with plain standalone output. Device coordinates remain separate from reverse-geocoder object positions. Its private disposable cache is independent of the status-indicator caches and managed-file transactions.

Personal Termux shell adapters register fixed Androidots-local completion paths: Zsh before compinit, Bash through the native bash-completion user-base list, and Fish through fish_complete_path. Generic `dots init` remains integration-only. The installer writes only explicit completion targets, preserving differing originals as sibling backups; it does not modify shell configuration. See the [helper reference](https://github.com/5nik7/androidots/blob/66bbe8bfd7a8a5c4fc7e69a837d79cd0cc256a6b/docs/termux-geo.md).

## Weather command and daylight adapter

`bin/wttr`, `bin/wttr.ps1` and the `dots wttr` family are thin native entries into `lib/dots/wttr/cli.py`. Static Dots adapters and standalone completion artifacts are generated by `tools/generate_wttr_commands.py` from the weather vocabulary. The weather package owns j1 HTTP transport, separate stock curl passthrough, configuration, format fields, cache locking/cooldowns and bounded on-demand workers; it reuses the existing Androidots termux-geo interface and never duplicates device providers. `metadata.py` supplies parser/help/completion options. Weather styling classifies temperature/condition colors and encodes explicit widget formats; shared Presentation styled spans wrap inert text before adding colors. The common Dots Presentation/progress modules render human views; completion installation uses the shared file transaction Store. `wttr/browser.py` owns session-only location/units, inert cached preview snapshots and numeric action identities. It reuses shared selection, input, exact-client tmux context and fitted output capture. Report actions invoke the weather controller once; opening/filtering/previews never acquire weather or location.

The Termux clock adapter accepts fixed daylight tokens only, leaving color mapping in tmux and palette values in the theme template. Network adapters are not invoked by the shipped layout. Battery and lower-row ownership are unchanged. Cache paths, timezone assumptions, background/foreground location boundaries and native Windows limits are defined in [the weather reference](wttr.md).

The Git named-navigation adapter (`lib/dots/git/submodule.py`) resolves direct
registered edges and delegates actions to existing inspection/publication
controllers on both shell surfaces. It projects static action metadata for help
and completion. `lib/dots/git_identity.py` and the shared `git/hosts.tsv` own
human identity decoration and cached optional host lookups; domain records remain
undecorated.

### Generated theme inspection

`lib/dots/themes/inspection.py` owns read-only active-generation inventory, current template resolution, connector observation, content views and browsing for both shell frontends. It consumes the fixed connector registry, existing app path adapters and bounded completed file-transaction metadata. Its `consumer_checks.py` helper reads bounded evidence, and `file_preview.py` owns directory listings and optional bounded bat rendering without cache generation. It never calls preparation, publication, recovery or plugin execution. Generic views use shared Python resource presentation and optional selectors; completion invokes only data readers. No new persistent state is introduced. See [theme files](themes.md#generated-theme-files).

## Platform profile resolution

`lib/dots/platform_info.py` owns controller platform facts; native Bash/Zsh
detection follows the same contract. `profiles.py` resolves literal definitions
and inheritance. `environment.py` combines the settings and application registry
for diagnostics and preparation. `startup.py` compiles Bash/Zsh bundles;
`native_startup.py` prepares PowerShell/Fish environment adapters. Personal
interactive modules remain under `shells`, with shared session setup consolidated
in `shells/shared/session.sh`. See [profiles](profiles.md) and
[decision 0011](decisions/0011-platform-profiles.md).

Profile detail views reuse the profile resolver, file-catalog validation and
command metadata. The debug controller owns read-only diagnostic reports and
explicit child-shell execution. Runtime-owned fixtures support curated self-tests
without importing unrestricted repository test runners. Native startup markers
carry source/timing metadata through a dedicated channel; compiled bundles retain
original module identities. See [debugging](debug.md).

`lib/dots/files/identities.py` owns canonical platform file-source names. Catalog and installation readers use it for legacy persisted IDs; CLI parsers reject the retired names. The transaction store continues to preserve historical journal data unchanged.

The debug subsystem now separates native observation, bounded in-memory state comparisons, session PATH evidence and shared tree presentation. Startup bundle source maps connect observed generated locations to unchanged authored lines. Current-session recording is installed through explicitly evaluated native code; an external CLI only reads its metadata. PowerShell sanitizes native state deltas before persistent transport, while Bash/Zsh use an anonymous in-memory snapshot channel.

## Wiki projection and repository association

The shared wiki controller reads canonical source documents plus first-party static metadata and a page/navigation manifest. It generates a deterministic, independently versioned wiki projection and sidebar; the source repository remains authoritative. The shared Git association adapter adds the external wiki without treating it as a submodule or changing parent indexes. Bash and native entry points delegate associated operations to the existing Python workflow. Ordinary standalone/submodule engines retain their contracts. Builds use the common transaction store; Git operations remain incremental. See [wiki](wiki.md).

The optional less standout style is owned by `lib/dots/less_style.py` for Python consumers and builtin-only adapters under `lib/dots/shell/less.*` for native shells. Existing shell theme-refresh boundaries consume published color records. Popup readers resolve the published palette at invocation, without extending command discovery, shell startup scans or theme publication. See [global less colors](shell-environment.md#global-less-colors).

## Bundled applications

`plugins/blastoff/` and `plugins/pkgs/` contain first-party application sources absorbed from their standalone repositories; `plugins/manifest.json` records import provenance. Both command forms share their application cores; the cores reuse selected Dots services for presentation and guarded file writes. `bin/blastoff` and `bin/pkgs` resolve the owning checkout and execute those cores; Dots-prefixed routes forward the same argument vector. Native PowerShell reaches them through the shared Python dispatcher and `lib/dots/bundled_apps.py`, without Bash.

`tools/generate_bundled_apps.py` reads pure application grammars to generate static route headers and completion metadata. Help/discovery never execute an extension or package backend. The shared checkout installer owns command/completion/manual publication and removal; imported standalone lifecycle helpers are retained historical tooling and are never used by Dots setup. Application actions retain their own established backup or package-manager semantics. See [bundled applications](bundled-applications.md).

## Application plugin ownership

The three first-party application source trees live under `plugins/`, declared by its manifest. Anodize owns its Python adapters and independent Go engine there; shared Dots services remain in `lib/dots`. Static launchers resolve one selected plugin without discovery. The installation controller owns combined assets and receipt-led legacy migration through the existing Store. See [application plugins](plugins.md).

### Codex attention bridge

`config/tmux/codex-alerts.py` owns observational hook ingestion, event deduplication, foreground thread/pane association, focus acknowledgement and optional Termux delivery. Its one-per-server worker publishes bounded expiring attention snapshots; `codex-status.py` remains a read-only renderer. The worker also observes session membership, attached-client TTYs and validated Termux tab identities. Shared `lib/dots/codex_attention.py` validates and aggregates its expiring overview for `termux-status.py` and the interactive session menu. Those consumers neither collect events nor deliver notifications; ordinary menu JSON/scalar modes bypass the overview. `tools/configure_codex_notifications.py` owns the explicit setup preview and delegates all personal-file writes/undo to the existing Store. Repository preferences and hook templates are source; private queue/snapshot and personal Codex files are not. See [notification behavior](themes.md#codex-attention-notifications) and the [maintenance guide](../agents/guides/codex-notifications.md).

## Todo ownership

`todo_brief.py` owns the shared exported planning prompt. `todo_plan.py` owns explicit launch, private thread associations and exact-context window handoff with a configured Todo icon separate from the descriptive Codex thread name; `todo_codex.py` owns bounded app-server RPC and native/Termux connection adapters. They are loaded only by the selected planning route. `clipboard.py` owns native clipboard writes. The Todo browser returns an explicit handoff result for print/launch so its containing launcher closes. The shared pager's opt-in `action_page` uses the validated selector and fitted document geometry, returning action identities while retaining query/focused line; other read-only readers retain their existing behavior.

`todo_core.py` owns scope, validation, aliases, goal lifecycle, note appends and guarded updates through the existing file transaction store. Versioned goal JSON is serialized through the store's UTF-8 text operation, independent of catalog schema validation, with retained byte-exact recovery copies. `todo_cli.py` owns command behavior and data views; `todo_presentation.py` shares inert semantic spans and expanded details with the popup. The standalone adapter selects automatic scope, while Dots dispatch pins its checkout. `todo_commands.py` defines parser/help/completion metadata and the checked static adapter generator. `todo_completion.py` is an inert, on-demand core reader. `todo_menu.py` and `todo_input.py` own goal-specific previews, field input and action handling using the shared selector, context, palette and reader. `todo_layout.py` owns read-only preview geometry from numeric FZF match counts and dimensions. Trusted result/resize bindings resize the existing selector without reading goal storage or rebuilding the popup; native adapters invoke the same lightweight Python helper. Goal selection never executes stored text.

Project discovery reuses the read-only workspace resolver, without requiring tmux. Project files remain in their owning checkout, global files use the native Dots state root, and no persistent registry or startup scan is added. The general Todo, Todo planning and Todo maintenance skill sources stay under the repository's `.codex/skills`; only their three narrow source roots are added to the file catalog. Generated briefs optionally reference the planning skill while retaining complete standalone interview, save-only and save-and-implement instructions. Agent-driven progress uses the existing scoped Todo lifecycle; launching planning does not mutate goals or intercept the TUI's mode transition. The maintenance skill routes to the Todo guide in the resolved source checkout. See [todo](todo.md).

`lib/dots/profile_config.py` owns configuration selection, settings validation and profile-aware paths. `config_cli.py` handles inert inspection, edits and legacy migration through the existing Store. `config_menu.py` owns interactive inventories, private preview snapshots and reviewed config plans. It uses the shared menu input adapter (`menu_input.py`, also exposed through the Todo compatibility entry point), exact-client tmux context and existing file workflow handoffs. The catalog resolves profile resource lists and serializes edits into the active manifest; all planning guards include the contributing manifests. Format-specific consumers retain their own parsers. Startup compilers project profile settings into native adapters; runtime state and user theme authoring remain outside the checkout. See [profile configuration](profiles.md#profile-configuration).

## Profile backend ownership

`files/registry.py` validates core identities/platforms and schema-3 historical-ID mappings; `files/identities.py` shares current-ID validation and receipt resolution. Candidate document overrides let `files/mappings.py` validate checkout-wide renames and selected-profile edits before writing. `files/catalog.py` joins it with source ownership and selected profile implementations before existing file planners run. `Catalog.updates()` can produce both registry and profile writes; callers journal the complete set together, including affected receipt identities. Legacy readers remain for older compositions and recovery.

`profile_environment.py` generates active, canonical and alias path namespaces and native maps for all declared profiles. Startup compilers consume this model and its manifest/directory inputs; `native_environment.py` transfers inert data to Nu/Xonsh. Application declarations remain in `environment.py`. Shell adapters never source profile `.env` files or duplicate path definitions. See [generated paths](profiles.md#generated-profile-paths).


Visual configuration uses `style_config.py` for layer-first resolution and `style_catalog.py` for supported consumer bindings. `config_refresh.py` shares guarded visual-only publication between the config CLI and popup. It uses existing Store publication locks/journals and first-party reload adapters; source preferences, theme palettes and runtime generations retain distinct ownership.

`menu_popup.py` projects `apps.menu.popup` into shared FZF selectors and per-popup tmux host flags. Auto retains controller dimensions; explicit sizes use the addressed client's viewport transported by `selector_environment`, with inert display-cell measurement for fit and preserved preview budgets. Reader layout uses the same bounds. The next invocation reads effective preferences; popup-only saves do not publish a theme or mutate tmux server options. `config_values.py` supplies typed constraints to explain, Config dialogs and both completion frontends without executing consumer commands.

Shared menu selection resolves popup geometry before final column rendering. Its low-level selector handoff retains the measured dimensions so `fit` cannot resize a percentage column a second time. Multiline content measurement counts display lines independently of numeric selection identities.

Typed UI/application preferences are resolved by `config_values.py`, edited by
`config_cli.py`/`config_menu.py`, and projected by `theme_styles.py`.
`config_wttr.py` delegates to wttr's native configuration validator rather than
creating profile weather storage. Read-only native weather discovery avoids mutation imports; draft editors and `NativePlan` explicitly capture transaction guards. `row_layout.py` supplies shared Python cell-based key columns for CLI and popup renderers. Bash uses validated `__format.*` literal settings, also embedded by the startup compiler with defaults-file invalidation, without adding a warm-start process. `fzf_config.py` separates shell preferences
from the protected picker projection. `tmux_config.py` compiles named placement;
Neovim's nested `util/dots_config.lua` consumes published literal preferences.
`todo_tree.py` projects hierarchy and filters private snapshots without store
access. The maintenance-only `tools/audit_config.py` scanner is never a startup,
help, completion or ordinary dispatch dependency.

## Existing-source registration controller

`lib/dots/files/registration.py` classifies repository sources and existing links and supplies bounded candidates to catalog discovery, Add scans and the shared picker. It does not mutate files. The existing manage controller serializes catalog updates and uses Installation for new link receipts; Store retains exclusive transaction, rollback and recovery ownership. Native and Bash frontends share this controller.

## Package workflow ownership

Within `plugins/pkgs/pkgs_lib`, policies validates literal recipes, scopes selects
user-wide ownership, go_tools reads binary metadata, workflows prepares/executes
commands, streams owns concurrent output and process status, and manifests owns
portable package data and desired-state restoration. `lib/dots/config_pkgs.py`
edits authoritative native JSON through Store; `package_setup.py` supplies the
optional package stage to the existing installer. `package_publish.py` supplies
a guarded manifest snapshot to the shared Git publisher; explicit publication
updates stage only that manifest in addition to the normal selection. Package effects are separate
from managed-file rollback. Help/static completion load grammar only. See
[package contracts](packages.md).

## Selective setup coordination

`files/setup_components.py` classifies installer ownership; `setup_wizard.py` creates a read-only selection draft through shared presentation/interaction and Config. `setup_stages.py` coordinates explicit preparation and journaled outcome records. `setup_leaf.py` owns pinned builds in private cache roots, and `setup_fonts.py` composes the Fonts planner with installer baselines. `files/install.py` and Store retain one final guarded publication/receipt transaction. `managed_destination.py` translates only validated catalog directory mappings for child writes; it does not weaken general parent-link refusal. Native WinGet discovery and mutation boundaries live in `plugins/pkgs/pkgs_lib/winget.py` and its fixed PowerShell bridge.

## Documentation readers and manual

Canonical prose remains in `docs/`; `.dots/wiki.json` owns stable page mapping and navigation. `wiki_commands.py` extracts inert first-party metadata through the shared bounded parser and a revision-aware Reader. Both wiki export and `tools/generate_dots_manual.py` use that inventory. Wiki provenance tracks all generation helpers and the literal global-option table.

`wiki_topics.py` builds ephemeral source/heading records and ranks queries without a persistent index or exported checkout. `wiki_browser.py` owns page/section selection and hands prepared text to the shared reader after selection closes. The launcher prompts for topic queries as literal arguments. Topic lookup does not execute extensions, initialize submodules, or publish documentation. The installer owns the generated manual's core asset and native destination.

`wiki_presentation.py` specializes the shared Python renderer for Wiki reports and document highlighting. Source selectors reuse shared menu field styles, layout and numeric transport. Config defaults/catalogs own the supported Wiki controls; rendering adds no settings store or startup scan. Raw/JSON/scalar interfaces bypass presentation, and ordinary redirected reports retain their established layout.

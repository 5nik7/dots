# Native PowerShell parity

**Status: Implementation complete; native Windows acceptance pending.**

Fonts add shared-controller routes, flags, a standalone adapter, completion, JSON
and popup actions. Fixed HKCU font values participate in file journals and inverse
operations. Remaining native acceptance: PowerShell 5.1/7 invocation/completion;
per-user install/removal/recovery with locked fonts; Windows Terminal GUID/default
edits, VS Code/WezTerm visibility, clipboard and terminal FZF. Termux and mocked
registry evidence is separate; see [the fonts plan](fonts.md).

The directory follow-up adds shared `DOTFONTS`, literal backend `*FONTS` selection, per-directory version history, storage-only install/update, explicit Use/Set and the same directory chooser/completion on both frontends. The shared Windows activation planner and journal are covered with owned-path registry substitutes on Termux; actual PowerShell 5.1/7, native path handling, locked-file recovery and desktop visibility remain pending.

The approved target is the existing first-party command surface on Bash
(Termux, Linux, WSL) and native Windows PowerShell 5.1 / PowerShell 7, without
Bash, MSYS2 or WSL dependencies on Windows.

## Delivery and acceptance

The [root-help update](usage-help.md) keeps one top-level row per visible command/group across Bash, the shared native controller and Python-free PowerShell help. Full contextual help, command inventory and completion remain available. The PowerShell fixture checks aliases, implicit/hidden groups and 40/80/120-column footer wrapping with Python absent from PATH. Native Windows PowerShell 5.1/7 and visible terminal acceptance remain pending; Windows app destinations are unchanged.

1. Shared static command metadata, literal native argument transport, dispatch,
   contextual help and completion; preserve dependency-free help/startup.
2. Shared file, Git, environment, theme and Anodize behavior; preserve aliases,
   exact data outputs, verbose actions, colors, resource icons and progress.
3. Native FZF/Gum adapters and safe token-based previews; retain selection,
   cancellation and approval boundaries.
4. Verified Windows app destinations, explicit link capability failures, native
   desktop equivalents and recovery-safe publication.
5. Permanent dual-shell contributor requirements, synchronized user docs,
   native CI and owner-run terminal/desktop acceptance.

Every first-party route and flag must be accounted for. Platform-specific actions
remain discoverable with explicit unavailability; missing native implementations
are unfinished work, not platform exceptions. Arbitrary external Bash scripts
are not automatically portable.

Keep existing state roots and journals. Links remain the default; never silently
copy, elevate, enable Developer Mode, initialize private sources, or translate
Windows/WSL paths. All managed changes use existing guarded transactions.

## Verification record

Record focused tests and actual native evidence here as stages land. Windows
PowerShell and pwsh are unavailable on the current Termux host. Linux, WSL and
Windows runtime/terminal claims require their own evidence. Owner Windows checks
must cover both engines, actual profiles/app locations, FZF keys/previews,
40/80/120-column rendering, cancellation and desktop actions.

## Implemented surfaces

| Surface | Implementation | Evidence / remaining acceptance |
| --- | --- | --- |
| Dispatch/help/argv | Native `.ps1` entry, shared static built-ins/first-party headers, targeted resolution, encoded literal argv | Static/native-controller tests; both real engines required in CI |
| Completion | Native AST reader and contextual controller, file IDs/paths, theme palettes/formats/styles/plugins; generated-command refresh | Controller assertions; real Tab acceptance pending |
| Files/setup/recovery | Existing Python controllers enabled natively; app paths and native inactive theme preparation | File/installer/picker regression suites; Windows privilege/reparse-point acceptance pending |
| Git | Native explicit-argv controller; recursive status/sync/publish safety | 24 portable safety cases passed on Termux; Windows signal/terminal acceptance pending |
| Theme queries/rendering | Literal native palette reader and shared style/template renderer | All static catalog palettes compare with Bash; scalar/decorated output tests |
| Theme publication | Guarded `Store` transaction, command manifests, locks, native wrappers, cache preparation, connectors | Isolated dry-run/idempotence/drift/undo and injected rollback checks; Windows app rendering pending |
| Theme interactions/plugins/background | Token-only FZF previews, Apply/Back/Cancel, `.ps1` hooks, Windows desktop wallpaper adapter | Native preview contract fixtures; desktop/interactive acceptance pending |
| Anodize | Existing engine `.exe` selection, shared authoring Store and native theme bridge | Existing engine unchanged; native Windows executable acceptance pending |
| Workflow menus | Shared launcher/family navigation, Git review gate, ordinary terminal FZF and less/FZF readers; native tmux/project-session actions unavailable, no WSL bridge | Shared-controller/argv fixtures and Termux popup tests; Windows PowerShell 5.1/7 keyboard, UTF-8, cancellation and reader acceptance pending. See the [menu acceptance record](popup-menus.md#g5-final-documentation-and-acceptance). |
| Future maintenance | AGENTS/guides/skills require both shell surfaces; platform/source-of-truth docs synchronized | Documentation checks and CI configuration; no new remote run claimed |

Bash's existing theme/Git frontends remain in place to preserve their established
behavior during native acceptance. Shared transactions, metadata, file controllers,
style renderers and interaction primitives are reused. Converging the remaining
frontend implementations requires matching terminal/output evidence.

The presentation gate is [the shared contract](../docs/presentation.md). Required
native acceptance includes ordinary and forced color/icon modes, NO_COLOR,
JSON/scalar/init outputs, verbose links/backups without interrupted progress,
FZF cancellation and previews, and 40/80/120-column light/dark views.

## Verification notes

- Global less styling uses a native PowerShell adapter on POSIX. Native Windows less retains stock colors because its console renderer has no equivalent termcap RGB path; no Bash/WSL bridge or app destination changes are introduced. Shared policy and publication fixtures pass on Termux; actual PowerShell engine checks remain pending. See the [less styling acceptance record](less-style.md).

- Managed-file repair and its interactive issue helper use the shared controller with native destination adapters and static completion. Isolated controller/adapter cases cover preview, JSON, queued relink/replacement, cancellation, numbered fallback and link-capability refusal. Windows PowerShell 5.1/7 repair/recovery and terminal acceptance remain pending; see [repair acceptance](files-repair.md).

- eza uses the same semantic template in Bash and the native Python renderer, a shared destination resolver, and the existing native connector transaction. Native Windows PowerShell 5.1/7 link and eza rendering acceptance remains pending; see the [eza plan](eza-theme.md).

- Existing file operations: 21 passed; file picker contracts: 19 passed.
- Bash dispatcher: all 24 cases passed after the completion additions.
- Installation lifecycle: 22/23 passed initially. The fresh-checkout fixture lacked
  the new app-path module; after including it and shared metadata, that case passed.
- Native Git: 24 portable cases passed. Three hardcoded Bash/PTY cases remain in
  their original suite and are not presented as native evidence.
- Native CLI: 11 passed, one explicit PowerShell skip. Coverage includes completion,
  rollback after an injected failure, all 33 static palettes compared with Bash,
  and Git theme install/update/remove with local-change refusal. The source test
  found an index-refresh side effect; disabling optional Git locks fixed it.
- Native Anodize: all three authoring/export/bridge/publication cases passed with
  the existing engine and desktop reloads stubbed.
- Native Git styling: all seven cases passed after correcting conflict reasons
  and tracking/event styles. Shared file colors and resources: 11 cases each passed.
- Installation adapters: five passed, four platform/runtime skips. Theme plugins:
  20 passed initially; the synthetic availability-row failure was fixed and its
  focused rerun passed.
- PowerShell 5.1/7 are unavailable on this host. CI jobs now require each engine;
  no Windows run or owner desktop acceptance is claimed.

Anodize user saves use the existing platform configuration adapter: XDG when
explicit, otherwise `~/.config/dots/themes` on POSIX and `%APPDATA%/dots/themes`
on Windows. `--builtin` and `promote` target the selected native checkout. Both
frontends share the authoring/picker controller and journal; Windows application
connector destinations are unchanged. Native PowerShell 5.1/7 FZF keyboard,
preview and interruption acceptance remains pending where engines are unavailable.

## Lean profile acceptance (2026-10-21)

Native PowerShell 7 and Windows PowerShell 5.1 profile fixtures now pass, including linked startup and prompt refresh. See the [focused profile plan](powershell-profile.md) for exact tests, timings and pending terminal/desktop checks. This supersedes earlier engine-unavailable notes only for these profile checks; full CLI/app parity acceptance remains separate.

The same follow-up now links Core/Desktop all-host profiles to the shared source, enables Starship and the respective terminal integration, and resolves Core Blastoff storage to repository themes. See the [profile follow-up](powershell-profile.md#coredesktop-starship-and-blastoff-follow-up) for native evidence and keyboard limits. App destinations and broader CLI parity claims are unchanged.

### Termux location exception

The Androidots `termux-geo` helper and its personal Bash/Zsh/Fish completion-path additions are explicitly Android/Termux-specific. Native Windows PowerShell has no Termux:API acquisition equivalent in this slice; Windows app destinations and completion behavior are unchanged. See [the focused plan](termux-geo.md) and [platform exception](../docs/platforms.md#androidots-location-adapter-exception).

### wttr acceptance

The standalone native `bin/wttr.ps1` entry and `dots wttr` family share weather options, stock request syntax, formatting, cache logic, progress and completion metadata with Bash. Both explicit `browse` routes use cached previews, session-only controls and the shared reader in the native terminal; missing FZF/terminal support falls back to the ordinary report. Stock requests require native curl.exe and bypass PowerShell aliases. Configuration resolves to APPDATA/wttr with the existing XDG override. Termux device acquisition and tmux daylight styling are explicit platform exceptions; manual/default weather is shared. Native Windows PowerShell 5.1/7 argv/completion/browser/PTY, cache locking and ACL checks remain pending on this Termux implementation host; see [the focused plan](wttr.md).

Television integration uses the shared native renderer, destination resolver and Store connector transaction. The LOCALAPPDATA default and explicit overrides have fixture coverage; native PowerShell 5.1/7 publication, rollback, link-capability refusal and Television visual acceptance remain pending. See the [focused plan](television-theme.md).

## Git submodule extension

Git info, submodule tree/status and scoped publication now have matching native
routes and static completion metadata. Shared inspection/selection uses native
Git without Bash. `--all-submodules` selects child trees; `--all` selects unstaged
files. Windows app destinations are unchanged. Native Windows PowerShell 5.1/7
runtime, confirmation/interruption, completion and 40/80/120-column light/dark
visual acceptance remain pending; portable controller tests are not that evidence.

Generated theme-file inspection shares the Python controller, metadata, data outputs and completion providers across both frontends. Native destination adapters are reused. Windows PowerShell 5.1/7 runtime, app-link behavior and browser/40/80/120-column terminal acceptance remain pending; see [the focused plan](theme-files.md).

The theme-file refinement adds shared directory/highlighted previews and read-only consumer evidence with explicit `check --consumers`. Native Windows bat/PowerShell terminal and app-configuration acceptance remains pending; controller and native-path fixtures are reported separately.


## Platform profiles and bootstrap (2026-10-24)

`dots profile` (including `list` and `check --all`), expanded `dots env`, profile command/catalog
resolution and `dots init --bootstrap powershell` use shared controllers and
metadata. PowerShell prepares a native environment adapter on cold startup;
warm startup validates metadata and loads native code. Windows configuration
and state remain APPDATA/LOCALAPPDATA-based unless explicitly overridden, with
Windows app destinations separate from WSL. Bash is not a native prerequisite.
Portable controller/installation fixtures pass; this slice has no new native
PowerShell 5.1/7 evidence. Native missing-checkout acquisition, startup/reload,
profile inheritance, PATH order, literal arguments, completions, and terminal
presentation acceptance remain pending. See the [profile plan](platform-profiles.md).

## Profile and debug diagnostics

Profile subcommands and `debug check|startup|path|command|cache|test` have shared
native routing, metadata and completions. PowerShell has native phase events and
Windows child ownership; no Bash dependency. PowerShell 5.1/7 live profile chains,
Job Object cleanup, redirected/terminal behavior and visual checks remain pending.
See the [focused plan](profile-debug.md).

Wiki commands and associated repository operations share Python controllers across Bash and native PowerShell. Native Windows PowerShell 5.1/7 acceptance remains pending; fixtures must not be reported as native evidence. See [wiki implementation](wiki.md).


Detailed debug trees, state capture and current-session PATH recording now have shared routes and a native PowerShell adapter. Actual PowerShell 5.1/7 breakpoint behavior, private-file ACLs, process identity and normal-exit cleanup remain pending native acceptance; portable fixtures do not establish these claims.

Keybinding browser: shared routes/options and PSReadLine on-demand JSON capture are implemented. Native PowerShell 5.1/7 caller capture, UTF-8 pipeline and FZF terminal acceptance remain pending where engines are unavailable. No Bash bridge is used on Windows.

Anodize LOGO1/LOGO2 static-help parity and Preview/Extract reader handling use shared native controllers. Engine-free help/metadata/completion fixtures and native-controller authoring checks passed on Termux; native PowerShell 5.1/7 UTF-8, keyboard and reader acceptance remains pending. See [logo acceptance](anodize-logo.md). Windows app destinations are unchanged.

Anodize hint/info/accent text gradients use the shared Python helper on native Windows and a builtin Bash counterpart on POSIX. Colors come from bounded published data or explicit candidate palettes. Palette result headers and draft review share the selected background/foreground from the logo onward. No native Windows destinations or shell startup paths change; native PowerShell rendering acceptance remains pending.

Blastoff and pkgs absorption adds standalone PowerShell launchers and shared native routes/completion. The explicit Blastoff session opt-in forwards to the bundled launcher on 5.1/7 without importing an external module. pkgs package operations are an explicit native Windows exception (status 3), while help/version remain available. Native 5.1/7 and WSL acceptance remains pending; see [bundled application plan](bundled-applications.md).

Codex attention notifications (2026-10-28): explicit native-Windows exception for the tmux/procfs worker and Termux device calls; no Windows destination or Bash invocation is added. Shared event/configuration logic remains Python-testable. Termux native fixtures do not establish native PowerShell execution or Linux/WSL visual acceptance. See the [focused notification plan](tmux-status-and-sessions.md#codex-attention-notifications-2026-10-28).

## Todo follow-up

The shared todo controller, native standalone literal bridge, scope-aware completion and terminal FZF/PowerShell previews are implemented. Explicit aliases, schema-2 JSON, note appends and semantic detail views share this controller; no native-only storage or Bash fallback is added. Native Windows PowerShell 5.1/7 execution, interactive editing/completion, cancellation and managed skill-link privilege acceptance remain pending. See [todo plan](todo.md) and [todo documentation](../docs/todo.md).

Profile configuration adds shared native `config` routes, profile/key completion and manifest-backed settings/mappings. Native Windows PowerShell 5.1/7 migration, reload, link privilege and terminal acceptance remain pending; see [the focused plan](profile-configs.md). Windows app destinations and WSL separation are unchanged.

Profile backend acceptance: shared registry/profile controllers and generated native hashtables implemented; native PowerShell 5.1/7 alias reload, `$PROFILE` preservation and Windows app-destination execution remain pending. Termux fixtures and renderer assertions are not native Windows evidence.

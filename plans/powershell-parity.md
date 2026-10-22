# Native PowerShell parity

**Status: Implementation complete; native Windows acceptance pending.**

The approved target is the existing first-party command surface on Bash
(Termux, Linux, WSL) and native Windows PowerShell 5.1 / PowerShell 7, without
Bash, MSYS2 or WSL dependencies on Windows. General Go migration stays paused.

## Delivery and acceptance

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
| Future maintenance | AGENTS/guides/skills require both shell surfaces; platform/source-of-truth docs synchronized | Documentation checks and CI configuration; no new remote run claimed |

Bash's existing theme/Git frontends remain in place to preserve their established
behavior during native acceptance. Shared transactions, metadata, file controllers,
style renderers and interaction primitives are reused. Converging the remaining
frontend implementations requires matching terminal/output evidence; it is not a
reason to resume the paused Go migration.

The presentation gate is [the shared contract](../docs/presentation.md). Required
native acceptance includes ordinary and forced color/icon modes, NO_COLOR,
JSON/scalar/init outputs, verbose links/backups without interrupted progress,
FZF cancellation and previews, and 40/80/120-column light/dark views.

## Verification notes

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

The standalone native `bin/wttr.ps1` entry shares weather options, stock request syntax, formatting, cache logic, progress and completion metadata with Bash. Stock requests require native curl.exe and bypass PowerShell aliases. The managed configuration has an APPDATA/wttr destination. Termux device acquisition and tmux daylight styling are explicit platform exceptions; manual/default weather is shared. Native Windows PowerShell 5.1/7 argv/completion/PTY, cache locking and ACL checks remain pending on this Termux implementation host; see [the focused plan](wttr.md).

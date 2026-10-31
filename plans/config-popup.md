# Configuration popup

## Completion recovery and shared row alignment (2026-10-31)

Status: implemented and verified on Termux. The user selected shared Dots CLI and popup rows. Configuration assessment: extend existing `formatting.apps.cli` and `formatting.apps.menu` label width/gap/alignment controls instead of adding a second settings store. Width accepts nonnegative character cells or an integer percentage of the terminal/popup width; zero uses spacing-only rows. Gap sets literal spaces, and alignment places the key within its column. Preserve complete long keys/values and use bounded wrapping/stacking on narrow terminals. Explicit domain layouts retain their overrides; JSON, scalar get, completion records and ordinary redirected output stay exact.

Menu assessment: update the Config browser's currently unaligned key/value rows and expose the new width syntax/presets through existing explain/edit/completion. Apply shared menu width against actual popup content bounds, honoring popup sizing. Bash human row/resource helpers and shared Python renderers use the same preferences; compiled Bash/Zsh settings carry inert data without adding warm-start processes. Native PowerShell continues through shared Python; Windows destinations are unchanged.

Completion recovery separates read-only wttr key discovery from mutation imports/guards. Guarded browser edits and NativePlan retain their transaction checks. Invalid optional weather data cannot hide unrelated core keys. Verify get/set/unset/explain completion with weather config present, literal bracket keys, fresh subprocesses and real shell Tab in test-owned homes.

Acceptance includes percentage/fixed/spacing alignment, Unicode/ANSI cells, narrow 40/80/120-column CLI/popups, plain/light/dark views, guarded saves/reset, literal rejection, next-invocation activation and exact data modes. Run affected config, presentation/resources, weather, shell/startup and menu suites sequentially. Validate metadata, docs, skills and local wiki. Native Windows and desktop Linux/WSL evidence remains separately pending; no live reload, install, commit or push is required.

Verification for this follow-up:

- Nine new completion/alignment checks passed, including real Zsh Tab, fresh Bash/Zsh/Fish/native providers with weather present, fixed/percentage/spacing-only and left/center/right rows, icon cell alignment, compiled Bash/Zsh literals/default invalidation, multiline fit measurement and private two-client 40/80/120-column popup selection. Shared menu geometry is retained after fitting, with an emitted-argument/row check preventing a second fit calculation from changing percentage columns.
- Related suites passed: resources 17; native wttr edits 1; typed values 12; live config 11; Config menu 15; shared menus 24; config presentation 2; shell environment 11; Todo 41; popup config 6; Bash CLI 27. Native shared CLI ran 23 with two unavailable PowerShell skips. Seven focused shell-init checks passed; the full Zsh fixture now copies typed defaults alongside the profile overrides it already copied, and its affected case passed again.
- Isolated literal-reader timing (same loader, seven samples of ten loads) measured Bash 9.617 ms without formatting rows versus 10.314 ms with them; Zsh 9.245 versus 9.261 ms. This measures the additional rows, not full shell startup; no extra warm-start process was introduced.
- Bash/Zsh and Python syntax, 234 static command definitions, four updated skill validators/links, 1180 relative documentation links and `git diff --check` passed. Full ShellCheck was not repeated after earlier resource-limited attempts; no new complete ShellCheck claim is made.
- Local wiki build transactions `b1f03cf55996485192ee748c481eda96` and `bf4b351df42744cab84f73ee4ba4c483` completed, and final wiki check reported healthy. Shared-menu, popup-config and Config-menu suites passed again after the fit alignment fix. Source recovery and test logs are retained at `/data/data/com.termux/files/usr/tmp/dots-config-alignment-57npd76k`.

Native Windows PowerShell 5.1/7 and desktop Linux/WSL runtime/visual checks remain pending. Tests used owned homes, configuration, state and private tmux clients; no live preferences or shell reload were applied.

Follow-up: [core updates](core-updates.md) adds List/Get/Set navigation and guided
empty get/set calls. Earlier verification below remains historical evidence.

Status: implemented and verified on Termux; native acceptance limits below. Builds on [profile configuration](profile-configs.md) and [profile presentation](profile-presentation.md).

Menu assessment: **add** `dots config browse` and a Config entry in `dots menu`.
Bare `dots config` browses in a terminal; explicit reports and JSON stay direct.
This supersedes the earlier decision to leave config out of menus. No tmux binding is added.

The shared Python browser owns settings, environment declarations, colors, icons
and read-only mapping inspection. Profile and category selectors retain independent
query/focus frames. Stable keys select rows; display labels are never commands.
Snapshots contain sanitized previews only, with private numeric-token transport.
FZF owns selection, and closes before shared Gum/readline input or terminal handoff.
The existing private tmux context pins each popup to its initiating client.

Edits use existing config plans and retained transactions. Review old/new values
and the destination before default-Cancel Save. Apply the reviewed plan with its
original guards; reject changes made during review. Reset removes only a profile
override and previews inheritance. Shared defaults are set-only. Empty icons are
valid. Environment secrets remain redacted and accept variable references only.
Mapping actions reuse `dots files` for the active profile only, without approval
flags. Saving config never activates a profile or publishes a theme.

Escape returns from nested dialogs; Ctrl-C exits with 130. Missing FZF/popup
capability produces a styled report and explanation. JSON, help and completion
must never capture tmux context or probe interactive tools. Shared Python handles
Bash and native PowerShell; native Windows uses its own terminal and preview shell.

Acceptance: isolated transaction/undo, inheritance, drift, cancellation, typed
values, empty icons, secrets, file handoff, static metadata and data nonexecution;
PTY layouts at 40/80/120 columns; private multi-client tmux ownership and cleanup;
shared input and launcher regressions; documentation links and wiki build/check.
Actual native Windows PowerShell 5.1/7 popup acceptance is pending a native runner.


The shared readline fallback accepts `/cancel` when Gum is unavailable. Help and
Details use the same inert preview selector, keeping Escape and Ctrl-C distinct.
Configuration inspections and edits use the active presentation policy even when
editing another profile. Shared defaults are edited without applying a theme.


## Verification evidence — 2026-10-29–30

- Config popup: 13 isolated cases passed. After the final redaction, completion
  and preview changes, all 10 controller cases and the native width/client case
  passed again. Coverage includes literal Unicode, empty icons, inherited reset,
  reviewed save/undo, stale-plan refusal, default Cancel, interrupted input,
  secret redaction, fallback, Bash/native frontend completion and data parity.
- Native terminals: standalone FZF, private two-client tmux at 40/80/120 columns,
  plain and dark/light palette fixtures, inert previews, empty-search Back,
  default-Cancel/Save, Gum Escape/Ctrl-C handoff and temporary-file cleanup passed.
- Related suites passed: Todo menu 9; shared menus 24; profile config 10; styles 7;
  Bash CLI 24; native shared CLI 17 with one PowerShell-unavailable skip. Launcher
  20 cases passed initially; its remaining metadata case passed after updating
  the expected entry count from 15 to 16.
- Static command validation passed for 212 external commands; Python/Bash syntax, ShellCheck,
  relative documentation links and `git diff --check` passed.
- Wiki rebuilt with retained transaction `a0fadb3617ae48e6bded05fae4befaa5`;
  `dots wiki check` reported healthy.
- Pre-change source/status and suite logs are retained outside the checkout at
  `/data/data/com.termux/files/usr/tmp/dots-config-popup-baseline-g7rpd59x`.

No live profile setting, theme publication or installation was changed by the
verification. Native Windows PowerShell 5.1/7 and native Linux/WSL desktop terminal
acceptance remain pending; Termux fixtures do not establish those native results.

The [live visual configuration follow-up](config-live.md) supersedes the earlier save-only visual behavior: icon/color saves refresh affected active consumers, while profile activation and file installation remain separate. Details report effective values and a reviewed Refresh action applies direct edits/retries.

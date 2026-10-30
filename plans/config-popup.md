# Configuration popup

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

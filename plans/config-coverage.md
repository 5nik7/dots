# Configuration coverage

Status: implemented and verified on Termux and owned fixtures. Goal `ee7a14f733f04acfa276d1e0c66e5819` (`config-coverage`), normal priority. Work used the existing dirty checkout and preserved unrelated changes. No commit, push or user-wide skill installation.

## Agreed contracts

Create and run `dots-config-audit` with a read-only static helper, then implement the named integrations. Additional findings remain an explicit evidence-backed backlog. Completed goals `ad4dd159482a4810a29d808ac20dbafb`, `1b5eb9b806a843b0b992d92c889d29c3` and `343d5be6948e4ee19e18783e5a909b23` are context, never reopened.

Recognized configuration reads resolve selected profile, parents, defaults, then null; unknown keys and invalid files remain errors. Null means inheritance when editing nullable overrides; false, zero and empty strings retain meaning. Human null uses muted foreground, while data remains undecorated. Preserve native map keys with literal bracket quoting. Shared formatting/application defaults live in `default/config.json`; profile overrides use `formatting` and `apps` manifest sections. Existing colors/icons retain their files and app precedence.

Wttr edits its active native TOML file without adding profile inheritance. FZF defaults cover shell usage and Dots pickers, including bindings/previews while protecting picker protocols. Neovim integration covers personal highlights/icons/editor UI options through the nested configuration and public Anodize APIs. Existing tmux/lualine components gain placement controls, preserving default arrangements. Todo human CLI and popup lists default to tree, with regular selectable, stable ordering and muted non-actionable ancestor context for filtered matches. JSON, Markdown, brief and goal storage contracts remain intact.

All displayed Todo fields and popup entry parts gain supported styles; icons gain nullable independent colors. Preserve customized defaults and assign semantic styles to previously unstyled fields. Formatting controls must reach actual consumers. Update config, authoring and related skills/docs for future integrations.

## Work packages

| Package | Goal UUID | Dependencies |
| --- | --- | --- |
| A: audit skill/helper and reviewed coverage | `bb69019f6ef24f718aeec5250338b6ad` | None |
| B: typed controls and resolution | `3a98ab24a66148819ce30d01b406ef07` | A |
| C: icons, popup styles and formatting | `b88f517f0a5244b88b5e898ec6e0fb64` | B |
| D: native wttr configuration | `0ed2253515b24ec7be58fe567fc29ae4` | B |
| E: FZF colors/defaults | `d466ba632d3d4f72807d0a7a22594ab4` | B, C |
| F: Neovim appearance/editor UI | `c0f0e37da9ef48d18d4b5cce9e6bb2b1` | B, C |
| G: tmux/lualine placement | `f42889c557b54b14977ba6ba2a4b6314` | B, F |
| H: Todo styling/tree views | `7ec0508dec4046379229cea946b7d48e` | B, C |
| I: verification/docs/Termux activation | `22b251b8907445bab7707bfba9acc20c` | A–H |

Each saved goal contains its observable acceptance criteria and full dependency UUIDs. Reconcile scoped JSON before every Todo write, start each package as it begins, and complete verified children before the parent. Serialize Store-backed writes, including wiki builds and Todo notes.

## Verification and rollout

Use owned roots, native-command substitutes, private PTYs/tmux and isolated Neovim fixtures. Cover nullable resolution, native keys, validation, stale writes, recovery, idempotence, exact data, actual consumer values, literal/control-character safety and popup cancellation/protocol protection. Review applicable human views at 40/80/120 columns with light/dark and independent color/icon modes. Compare startup-sensitive paths before/after; no extra scans during normal startup, help or completion.

Maintain Bash/Termux/Linux/WSL and native PowerShell controller parity, with native runtime evidence reported separately. Update canonical documentation and skills, metadata/completion, source links and available wiki. After isolated checks, activate verified owned Termux preferences and relevant consumers using existing safe refresh/reload paths, retaining the selected theme, personal values and recovery. Unknown/unavailable live consumers are reported separately, never forcibly restarted.

Configuration assessment: add/update the agreed supported integrations. Menu assessment: update the existing Config popup and affected family views; no separate automatic audit command or runtime repository scan.

## Audit evidence

The static candidate inventory is emitted by `tools/audit_config.py`; source/line findings need ownership and consumer review. Current literal bindings show gaps in native wttr options, FZF defaults/native color slots, Neovim highlights/preferences, popup entry parts and Todo field formatting. These are the named work packages above. Palette algorithm constants, authored artwork and test fixtures are not automatically configuration candidates. Private/excluded sources, generated/build assets, arbitrary symlinks and uninitialized dependencies stay outside the scan.

Initial inventory and baseline recovery data: `/data/data/com.termux/files/usr/tmp/dots-config-coverage-3a1310ti`. Verification and remaining findings will be recorded as packages finish.

## Reviewed discovery dispositions

Initial static coverage: 1,392 source files and 12,820 candidate/declaration hits.
The JSON evidence retained beside the baseline patch gives exact source/line
identities; hits are not a count of missing settings.

| Area | Files | Hits | Disposition |
| --- | ---: | ---: | --- |
| defaults | 23 | 671 | Supported declarations and templates reviewed; named integrations implemented. |
| profiles | 106 | 979 | Profile precedence retained; active Termux configuration validated. |
| configuration | 248 | 6,374 | Wttr, Neovim, tmux and shared styles integrated; independent app owners retained. |
| shells | 278 | 1,373 | Native FZF preference publication wired; generated/completion literals are not separate settings. |
| command adapters | 251 | 251 | Metadata/help candidates route through shared controllers. |
| scripts | 89 | 465 | Existing utilities retain their contracts; additional candidates need separate owner review. |
| libraries | 234 | 1,549 | Shared controls, popup styles, Todo fields and tree projection integrated. |
| tools | 32 | 114 | Maintenance-only scan and publication controls; no runtime scan added. |
| plugins | 131 | 1,044 | Existing palette authoring/bundled app owners retained; no arbitrary remapping of their algorithms. |

Additional backlog: `config/yazi/init.lua` around lines 76–89 has application UI
layout/highlight candidates outside the named integrations; review them with
Yazi's existing theme/plugin ownership. `config/tmux/android-status.py` contains native Android indicator presentation
that should be reviewed with its adapter owner before new dedicated controls. Native Neovim icon styling
beyond diagnostic signs should map to real application highlight consumers before
additional dedicated `icon_styles` names are advertised. Shared Bash-only legacy
helper presentation should be reviewed against its native-shell counterpart
before adding controls. These are recorded discovery findings, not newly saved
or implicitly authorized goals.

No-change examples: `scripts/ansi:119` implements the ANSI color encoder itself;
its byte protocol is not a user color preference. The `MARKER` in
`profiles/termux/bin/termux-bar:12` is a launcher protocol identity, not a glyph. `plugins/anodize/authoring.py:22`
declares palette names/aliases, which remain the palette engine's data contract.
Authored dashboard animation artwork and algorithm constants retain their owners.
The scan skips private/excluded sources, links, secrets, binaries, large files,
generated assets and tests; it does not prove exhaustive semantic coverage.

## Consumer verification

Typed config checks passed (12), live configuration publication/recovery checks
passed (11), and the full Config popup suite passed (15). The expanded catalog
had 2,783 rows in the owned profiling fixture. Profiling found 11.13 seconds spent eagerly
formatting all previews; the popup now transports bounded inert, redacted row
snapshots and renders only the selected preview. A subsequent measurement was
1.32 seconds for inventory and 0.96 seconds for picker preparation, including
the 1.47 MB private snapshot. No runtime repository scan was added.

Shared presentation checks passed (2), shared menus passed (24), style-config
checks passed (7), FZF controls passed (2), and shell environment checks passed
(11). Todo core checks passed (41), and tree projection/protection checks passed
(2). Copied public Anodize/Neovim bridge checks passed (5); the focused Neovim
consumer check also passed for editor options, highlight/icon reset, native
section placement, padding and both separator sides. Private tmux layout checks
passed, preserving default rows and exercising reordered sections at
40/80/120 columns.

Static command validation reports 234 external routes; Todo and weather metadata
generators match their checked-in adapters. Twelve affected skills validate.
Native Windows PowerShell 5.1/7, Linux/WSL desktops, Xonsh and native Windows GUI
consumer evidence remain separate pending platform acceptance. Shared-controller
and isolated Termux evidence do not claim those native environments were tested.

The complete weather suite passed: 49 tests with one unavailable-PowerShell skip.
It covers native fg/bg/attributes while rejecting invalid whole style entries;
individual null edits retain reset semantics. Native TOML edit/recovery tests
also pass. The complete Todo popup suite passed all 10 tests, including filtered
trees, context-only selection, preview geometry, cancellation and brief handoff.
Its observer now waits for one probe to complete before sending another, avoiding
an artificial queue of synchronous FZF transforms. A focused check also verifies
that nullable Todo status/priority value styles are discoverable without replacing
their specialized default colors. Private preview snapshots retain redaction.

## Termux activation and recovery

Published generation `g.2a2a7653b91d4f27bce026aaf0383fc6` through retained transaction
`ecbe6ee99fc94dd4a5acbc264ab4747b`; the preceding publication is retained as
`6425d2df2c3f46ce808ebce8cccc3c80`. The selected `catppuccin-mocha` identity, exact
palette bytes and existing Termux profile/icon/color/weather files were verified
unchanged. A second refresh preview reports no publication. The verified owned
live tmux server was notified and reports the configured two top status rows.
CLI values apply on invocation, shells on their next prompt, and Gitmux on its
next status read. Starship required no symbol changes.

No Yazi instance was running: its IPC notification returned connection refused,
so the refresh report honestly retains a pending notification. Published Yazi
artifacts are ready for the next launch; no application was forcibly started.
No live Neovim instance was restarted; its published preferences load on startup,
focus or `:DotsThemeReload`. These unavailable live instances do not prevent
publication or verified owned consumer activation. Native GUI/platform evidence
remains scoped as above.

Recovery uses the existing `dots files undo TRANSACTION` workflow with its drift
checks. The retained task evidence directory contains baseline dirty-tree patches,
isolated test logs, audit findings, publication results and live hash verification.

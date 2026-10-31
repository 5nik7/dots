# Live visual configuration

Status: implemented and verified on Termux; native desktop acceptance remains
explicitly pending below. Todo parent: `ad4dd159482a4810a29d808ac20dbafb` (`config-cmd-update`).

The agreed precedence is shared defaults, inherited profiles, selected profile;
within each layer, app overrides follow general values. Empty icons and false
attributes remain intentional. One applications.codex identity role retains
navigation.codex as a compatibility alias. Existing working/waiting and Todo
labels stay separate.

The shared supported-control catalog governs editing and completion. Existing
unused entries remain inspectable/resettable. New controls cover shared UI
borders/cursors/matches/separators, Todo statuses/priorities and tmux window/pane
styles, with platform defaults preserving existing appearance.

`config explain` and browser details report effective values, origins, consumers
and publication state. Existing get/list data interfaces remain compatible.
Visual saves refresh affected active consumers unless `--no-refresh` is explicit;
`config refresh` applies direct edits/retries. Menu assessment: update the existing
List/Get/Set browser with details and reviewed Refresh; no new launcher.

Refresh stages a complete successor to the current generation using its published
palette, preserves unrelated artifacts and connectors, and journals guarded
pointer changes through Store. Publication locks coordinate with both theme
publishers. Native shell adapters read literal visual data when generations
change. Verified tmux servers, Yazi, Gitmux and opted-in prompt symbols use bounded
first-party adapters; arbitrary plugins and full theme changes are excluded.
Saved config survives refresh failure. Publication failure retains the prior
active generation; reload failure reports pending consumers and retry guidance.

Work packages: resolver/explanation `9aca9f8d54fe4e5080d87379f9d1e0cc`; existing
controls child `1391c9df2ed94e70b00008288edc22a0`; refresh
`06abe6a1b6284cea98fd611e1d618713`; verification/live activation
`4517623e659845fe8b4317d70c013f02`. Controls depend on resolution, refresh depends
on both, and verification depends on all. Preserve original metadata and append
progress through Todo CLI only.

Acceptance covers layer/alias/field resolution; safe literals; supported bindings;
read-only purity; retained undo, stale inputs and publication/reload failure;
no-op/inactive saves; owned multi-server tmux and shell generation changes;
40/80/120-column light/dark/plain views; scalar/JSON/completion compatibility;
Bash and native PowerShell surfaces. Native Windows 5.1/7 and Linux/WSL desktop
acceptance must be reported separately from Termux fixtures. Canonical docs and
the available wiki are synchronized before completion.

The user authorized final recoverable migration of the existing Termux glyph
`󱈸` from apps.cli.applications.codex to applications.codex, followed by active
managed visual refresh and verification. Preserve theme identity, session/window
identities and unrelated bindings. No commit or push is authorized.

## Verification

Termux evidence, 2026-10-30:

- Config-live: 11 cases passed, including rollback/undo, stale inputs, literal
  Yazi edits, previews, no-op/inactive saves, failure retention, owned multi-server
  tmux and generation updates in Bash, Zsh, Fish and Nushell. Bash/Zsh also check
  100 warm prompts without Python/readlink invocation or duplicated FZF options.
- Style configuration: 7 passed; profile configuration: 10 passed; Config menu:
  15 passed, including 40/80/120-column plain/dark/light private terminal views;
  Todo menu: 9 passed.
- Tmux status: 18 passed, 1 optional case skipped, with failed fixture cases
  rerun after correcting isolated profile detection and stale color expectations.
  The expectations now match the existing template defaults.
- Theme publication/rollback/Bash compatibility/Zsh hooks: all 4 selected cases
  passed. Native command controller: 21 passed, 2 unavailable-runtime skips.
  Shell initialization: 13 passed, 18 capability/environment skips.
- Static command metadata validates 234 commands. ShellCheck, Zsh syntax,
  relative Markdown links and whitespace checks pass.

The live Termux profile now declares `applications.codex = "󱈸"` without the
redundant CLI override. Live tmux's Codex option and both resolver aliases agree.
The selected `catppuccin-mocha` palette remains byte-identical; tmux server PID,
session/window identities and bindings are unchanged. Only owned visual
artifacts changed; a repeat refresh preview proposes no publication.

Retained recovery transactions: common icon save
`e59029d5b5db4d99a9531d2f76d7168f`; redundant override removal
`ba8f40238a2b4b5a9f51e9482052834e`; visual publication
`ae5f429434d54f07a4b793293fdb68a7`. The active generation is
`g.40b3d2886b754ebfa91622bfc28d529d`. Normal drift-aware undo rules apply.

Native PowerShell 5.1/7, Xonsh, Windows application destinations and native
Linux/WSL desktop rendering remain named acceptance checks. Termux execution of
the shared native controller does not establish Windows runtime evidence.
Yazi notification succeeded; that proves delivery was attempted successfully,
not that every open application has visibly redrawn. Existing shells need the
updated integration loaded before its new next-prompt behavior is available.

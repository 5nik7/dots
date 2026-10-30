# Profile presentation and complete inventories

**Status: Implemented; native acceptance limits below.** Follow-up to goal `profile-configs`.

## Accepted design

Human reports use the existing Dots renderers; arrays and objects require explicit `--json` for serialization. Scalar/path/raw/completion/generated-shell contracts remain exact. Audit first-party CLI, standalone app reports and popup capture. The original slice kept configuration editing direct. The approved [configuration popup](config-popup.md) now adds interactive browsing and editing while preserving direct routes.

Each base platform profile owns its applicable `files.dots` list. Remove the root catalog after comparing all four effective inventories; retain source identities, paths, overrides, receipts and legacy independent catalogs. No live installation accompanies the metadata migration.

Shared `default/icons.toml` and `default/colors.toml` define named visual roles, overridden per key by inherited/selected profiles. `dots config` exposes these groups, contextual keys and `--defaults` editing. Equivalent roles are standardized across Dots-owned commands and active managed configs, with explicit per-app overrides. Existing palette/file-color ownership stays intact; third-party code, theme collections, scalar utilities and authored artwork are exclusions. CLI preferences are read on the next invocation; application fragments update through explicit theme refresh. Never publish or reload as an incidental read.

## Implementation and acceptance

- [x] Profile-only root inventories, validated equivalent on Termux/Linux/WSL/Windows.
- [x] Human config objects, metadata/completion and exact data modes.
- [x] Validated style inputs, inherited/default editing and retained undo.
- [x] Shared Python/Bash presentation and native startup integration.
- [x] Managed consumer binding inventory, shared roles and safe native outputs.
- [x] Isolated tests, PTYs at 40/80/120, injection safety and startup measurements.
- [x] Canonical docs/wiki, verification evidence and goal completion.

Native Windows PowerShell 5.1/7, Linux/WSL desktop applications and unavailable shells require separate native acceptance. Source edits do not authorize live refresh, commit or push. Preserve concurrent Todo and other checkout work.

Pre-change source/status evidence: `/data/data/com.termux/files/usr/tmp/dots-style-config-baseline-yusr89o8`.

## Verification evidence — 2026-10-29

- `files.dots` arrays exactly match applicable rows from the pre-change shared catalog: Termux/Linux/WSL 42 each, Windows 14. The root catalog is absent. Effective catalog equivalence was checked before/after the move; resource IDs, sources, disabled entries and destination templates are preserved. Evidence: `inventory-verification.json` in the retained baseline directory above.
- Profile configuration: 10 tests passed. Visual preferences: 7 tests passed, including retained undo, default/profile inheritance, empty icons, hostile literals, Bash/native-controller data parity, actual PTYs at 40/80/120, missing versus empty inventories, completion and Python-free warm Bash/Zsh startup after preference changes. Profiles: 14 passed.
- Bash CLI: 24 passed. Native shared CLI: 17 passed, one unavailable-runtime skip. Resource presentation: 17 passed. Menu launcher: 21 passed. Keys: 19 initially passed; the affected color assertion now passes after honoring the view's palette and updating the muted fallback expectation. Utility scripts passed syntax checks and plain help checks without invoking file operations.
- Theme publication/idempotence/rollback/drift: 3 focused cases passed. Gitmux adapter: 4 passed; both theme renderers matched across all 35 palette/override cases. Git dark/light publication/native rendering passed. The old tmux assertions expected orange/magenta while the saved pre-change template already used bright/dark foreground; those two assertions now match the existing source.
- Tmux session/order/width/layout: 3 passed. The private native attention/reload case passed after making initial icon fallback options quiet when already present. Gitmux executable tests were skipped because that binary is unavailable.
- Yazi Lua dispatch, Githead rendering, shared symbol refresh, render purity, color references and last-good snapshot tests passed. A native Yazi terminal launch did not complete terminal negotiation in the isolated PTY; visible native icon rendering remains pending. No live application was reloaded.
- Starship palette transactions: 8/9 passed. The existing installed-module coverage check fails because this Starship build lists `claude_context`, absent from the unchanged saved theme. Preference symbol parsing/idempotence and hostile literal handling pass in the new owned fixture. This does not claim a completely green broad suite.
- Installation adapters: 10 tests, five unavailable native Windows/PowerShell checks skipped; all available cases passed. Source fixtures now include the configuration reader's new dependencies.
- Sequential alternating warm samples (9 per case) measured Bash median 125.16 ms before / 137.71 ms after, Zsh 103.74 / 102.73 ms. Added literal preference rows and input stamps extend the startup bundle; the warm path still launches no Python. Measurements ran on the shared Termux device alongside validation, so small differences are not a performance guarantee. Results: `startup-timing.json` in the retained baseline directory.
- 211 command definitions and all four profile checks passed. Python AST, Bash syntax and `git diff --check` passed. Wiki build `232ea14a6139475d9a648872152c97f4` completed and the subsequent check was healthy; build `fb87c3b9f8b244e28e843479e1c65cd7` incorporated the utility binding note. Final build `0709a71a4e7a4160ab57211dc6c622dc` includes concurrent Todo documentation updates; the final wiki check returned `healthy: true`.

Bindings and exclusions are documented in `docs/profiles.md`: existing theme-connected consumers share configurable roles; imported presets, application-specific native fields, authored artwork and pre-Python bootstrap fallbacks retain their owners. The menu review adds no new action: editing remains explicit CLI work, while existing menu glyphs consume preferences.

Native Windows PowerShell 5.1/7 and Linux/WSL desktop execution remain named acceptance checks. No commit, push, live theme publication or application reload was performed. Existing user work remains in place.

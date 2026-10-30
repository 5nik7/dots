# Personal font management

**Status: Implemented; native desktop and live activation acceptance pending.** Implements the approved fonts plan for Todo
`1420613a8fb94c28a526104af9eba164`, plus its directory/version follow-up `2ad86387e0e74b998275dd3803aea3f4`.

## Contract

Equivalent `dots fonts` and standalone `fonts` frontends use one Python controller.
Manage per-user fonts on Termux, Linux, WSL and native Windows. Official Nerd Fonts
releases and the Google Fonts repository supply fonts, licenses and exact revisions.
Explicit Update refreshes catalogs; ordinary browsing is offline. Downloads retain
versions separately from installation. Pins prevent upgrades; rollback selects an
exact retained version. One version of a family/variant is registered at a time.
Active Termux-only selections also upgrade/roll back without desktop registration.

Install all styles of a selected Nerd Font/Mono/Propo variant. Set changes explicitly
selected Termux, Kitty, WezTerm, Windows Terminal or VS Code editor/terminal targets.
Preserve sizes, fallback families and unrelated settings. Managed sources retain
ownership; copied targets require receipts and drift checks. Termux uses its local
font.ttf and reloads after commit unless --no-reload is given. Other applications
retain their normal reload behavior. WSL never changes Windows host settings.

Use shared file transactions, retained backups, complete preflight and drift-aware
undo. Extend that engine narrowly for per-user Windows font registrations. Review
mutations interactively; scripted changes require --yes. Dry runs leave no persistent writes.
Imported legacy fonts are copied, preserving originals and unknown provenance.
getnf/chnf become shared-controller compatibility wrappers with documented flags.

Menu assessment: **add** Fonts to the launcher for repeated selection, with font
management and icon search. Keep path, recovery and data interfaces direct.
Use shared FZF/tmux ownership, readers, presentation and cancellation. Actual font
samples use optional ImageMagick/Chafa; absent renderers show labeled metadata.
Icon Enter/Alt-Y copies and closes; Alt-I inserts literally into the verified
originating tmux pane without Enter; Alt-P prints. Outside tmux use copy/print.
No global bindings, privileged installs, font patching or custom variable axes.

## Work packages

1. Catalogs and versioned library: official providers, selective downloads,
   validation, licenses, provenance, imports and offline reads.
2. Installation and recovery (depends on 1): native adapters, pins, upgrade,
   rollback, uninstall, removal and shared-engine undo.
3. App connectors (depends on 2): bounded configuration edits, ownership,
   explicit destinations and post-commit reload reporting.
4. Compatibility (depends on 1–3): import legacy fonts and wrap getnf/chnf.
5. Font popup (depends on 1–3): browse, query retention, details, preview and
   reviewed actions. Icon popup depends on 1's versioned glyph metadata.
6. Acceptance/docs (depends on all): command/completion parity, isolation,
   presentation, canonical references and generated wiki.

## Acceptance

Test provider failures, rate limits, invalid archives/fonts, interrupted downloads,
unknown versions and offline reads. Test collisions, pins, missing upgrade faces,
registration failures, rollback, drift, idempotence and stale plans. Test each app
with comments, fallback settings, links/copies and ambiguous/dynamic declarations.
Use test-owned home/config/state/cache/data/repository roots and private tmux clients.
Check Bash/native controllers, Bash/Zsh/Fish/PowerShell completion, exact data,
40/80/120-column presentation, missing optional tools and cancelled/stale actions.
Follow the [presentation gate](../docs/presentation.md#acceptance-gate).

Run focused font checks plus affected command, native-controller, file-platform,
transaction, profile and menu suites sequentially. Run docs/whitespace checks and
wiki preview/build/check. Record native Linux/WSL/Windows checks as pending unless
actually observed. A real Termux font activation/reload/restoration check requires
separate live authorization; fixtures cannot establish visible device activation.

## Evidence

### Installed fonts and application defaults follow-up

Same-selection repair: explicitly configured targets are synchronized even when their old target record is identical. This backfills profile retention and preferences for pre-update selections while leaving matching active font bytes untouched. The isolated regression checks preview, exact retained face/version, unchanged active-file inode/mtime, repeat no-op and transactional undo. Menu assessment: no menu change; existing Set actions use the corrected shared controller on both frontends.

Repair verification on 2026-10-30: all 18 workflow cases passed. At the user's explicit request, the existing JetBrainsMono Nerd Font Regular v3.5.1 Termux selection was reconciled through Set transaction `fd1a2c5c3f15467c929978e33e388d5f`. The profile now retains its single TTF and OFL.txt and records the exact default in fonts.json. Stored/active/preference SHA256 values match; the active font's inode, modification time and bytes are unchanged. Reload was skipped. This is live metadata/retention evidence, not a visible device-font reload test.

**Implemented; verified in isolated Termux fixtures, with native desktop acceptance pending.** Agreed goals: inventory/partial retention `843b750136864c10a973e119aa4f4b9b`; action menu/transfers `66ce98cf1b284eae86600b89a8a945f2` (depends on inventory); app retention/preferences/Restore `db437e53aa064cc3b585103cd8701bae` (depends on both).

Plain interactive fonts opens an action menu; direct browse/query and existing JSON/plain interfaces remain available. Menu assessment: update the main Fonts menu and launcher with installed, Set, downloaded, defaults and Restore workflows. Copy/Migrate and batch install belong in selection actions; recovery remains a direct reviewed command. Installed discovery is explicit, bounded and never part of startup/help/completion.

Copy preserves originals. Migrate adopts proven user-owned installations with receipts/backups and preserves lookup paths using POSIX links or native Windows copies/registrations. System/package-owned or uncertain sources are copy-only. Transfers preflight the whole selection and skip identical content. Extend partial version retention additively, preserving existing files, provenance and history.

Set/use --target retain one TTF for Termux and the chosen family variant's styles for desktop apps in the active profile fonts directory. Preserve the prior custom Termux font on first replacement. Missing selected catalog versions download before mutation. Store exact app choices in profiles/<active-profile>/fonts.json; explicit Restore uses them without upgrading or running during startup. Missing app configs retain existing managed/explicit-config requirements. Store, native registration, app config, preference and inventory writes share one transaction.

Acceptance covers independent stores, partial/full expansion, batch conflicts, ownership, installed-source drift, exact restore, missing imports/download failures, rollback, idempotence and multi-app updates. Use owned roots and private tmux at 40/80/120 columns; maintain Bash/native PowerShell metadata/completion/data parity. Update canonical docs and wiki. Native desktop/device activation remains a separate acceptance check; no live activation, commit or publication is included in implementation verification.

Follow-up verification on 2026-10-30:

- Original fonts: 21 passed; installed/app workflows: 17 passed; directory lifecycle: 13 passed; private tmux/FZF: 6 passed, including the new action menu at 40/80/120 columns, client isolation and cancellation. Workflow cases include partial expansion, original Termux preservation, desktop variant styles, exact-face inference, batch conflicts/no-ops, copied/migrated ownership, migration undo/cache refresh, exact Restore after absent remote state, missing local imports, failed downloads, Windows registration adapters and rollback after preference-write failure.
- Bash CLI: 24 passed; shared native controller: 16 passed and one unavailable-runtime skip; launcher: 21 passed; local completion: 6 passed. Total focused and affected suites: **124 passed, 1 skipped**. Windows registration fixtures use test-owned paths and registry substitutes, not a native Windows session.
- Generated adapters, Python/Bash syntax, 246-command metadata validation, whitespace checks and 1,105 relative Markdown links in 143 files passed. Source documentation and the local generated wiki are synchronized; wiki transaction `cf2e85aaf6704ba4ac13a183870c23c2` passed the export check. No publication occurred.
- Logs: `/data/data/com.termux/files/usr/tmp/dots-font-workflow-checks-kxpvgrjj`. No startup/discovery path was extended; installed-font discovery remains explicit. Tests now own the Dots checkout as well as HOME/XDG roots, including any profile preferences and retained payloads. No live fonts, app settings, reloads, commits or pushes were changed. The native/device checks listed below remain pending.

### Directory follow-up

Todo `2ad86387e0e74b998275dd3803aea3f4`: **Implemented and verified in isolated Termux fixtures; native desktop acceptance pending.**
The user selected storage-only directory installs, with explicit use/set activation.
Add backend-owned DOTFONTS, plus `--directory` accepting a backend font variable
or its absolute path. Keep the default user library unchanged. `directories` lists
destinations; the existing browser gains a directory chooser and preserves scope.
Menu assessment: update the font browser for repeated destination/version selection and add the read-only directory report to its launcher submenu; keep recovery commands direct.

Use the existing collection journal, with a separate inventory for each normalized
destination and payloads under its `.dots-fonts/library` directory. Retain version
records after explicit uninstall, including provenance/checksums and availability.
Directory update/upgrade stores new versions without activation. Explicit use copies
the selected payload into the user library and registers it; set applies named app
targets (Termux-only Set need not register desktop fonts). Store, user-library and
activation changes share one transaction; origin references expose active selections
per directory. Removing a directory copy never removes an activated user copy.

Test separate directories, exact versions, history after uninstall/reinstall,
activation origins, dry runs, stale manifests/collections/payloads, rollback and
idempotence. Verify Bash/native controllers and all generated shell environments,
completion, private popup handoff, source docs and wiki. Native desktop/PowerShell
and live font activation remain separate acceptance checks. Preserve unrelated
work, including existing deletions beneath the repository fonts directory.

Directory follow-up verification on 2026-10-30:

- Corrected the shared variable to **DOTFONTS** at the user's request. The backend exports it as `<checkout>/fonts`; literal directory selection and completion use the same model. No alias for the earlier spelling is emitted.
- Directory lifecycle: 13 passed; original font suite: 21 passed; private tmux/FZF browser suite: 5 passed, including Alt-D and 40/80/120-column rendering. Backend: 14 passed, including the corrected variable, override refusal, native exports, checkout switching and reload.
- Across these and profile config/profiles, shell environment/init, Bash/native CLI, launcher and local completion suites: **168 passed, 19 skipped**. Skips retain existing unavailable-runtime/optional-fixture boundaries. Directory Windows lifecycle uses owned POSIX destinations and mocked registrations on Termux; the existing font suite separately exercises Windows-path registration validation.
- Generated font adapters and syntax checks passed; static metadata validated 241 commands. Relative Markdown checks validated 1,105 links in 143 files; whitespace checks passed. The local wiki was rebuilt and checked, with final transaction `ee6b8d6f8abf43258b530fc0c257e0e5`. No publication occurred.
- Startup comparison used disposable public fixtures and the pre-follow-up backend. The first 20 alternating warm samples measured Bash 62.182/67.778 ms and Zsh 298.949/324.166 ms (before/after). A 40-sample repeat measured Bash 76.933/60.416 ms and Zsh 330.967/329.033 ms. The direction did not reproduce; device/load variation limits conclusions. Warm initialization still passed with Python removed from fixture PATH. Single cold observations ranged 650.831–1,096.315 ms for Bash and 961.781–1,515.716 ms for Zsh; these are not cold-start guarantees. The backend change adds one scalar without new startup discovery or cache inputs.
- Evidence: `/data/data/com.termux/files/usr/tmp/dots-font-directory-checks-u34771rf` contains suite logs and both timing runs. No live font installation, app activation, shell reload, commit or push was performed. Native PowerShell 5.1/7 and visible Linux/WSL/Windows/Termux activation remain pending as described below.

### Original font feature evidence

Recorded on 2026-10-30 in Termux, with owned HOME/XDG roots and private tmux clients:

- `tools/test_fonts.py`: 21 passed. Includes provider/archive/license fixtures,
  imports, idempotence, pins, active Termux upgrade/rollback, drift, shared registry
  rollback, managed links/copies, CRLF/comments/fallback preservation, literal Lua
  refusal, legacy flags, optional dependency failures and exact data output.
- `tools/test_fonts_browser.py`: 4 passed. Actual FZF/tmux at 40/80/120 columns;
  exact-client isolation, Esc, Enter/Alt-Y copy through a test clipboard, Alt-P
  exact print, and Alt-I literal insertion without Enter in a test shell.
- Actual ImageMagick/Chafa rendered the synthetic font. fontTools 4.68.0 was loaded
  from a temporary test dependency directory; no global package installation.
- Direct HTTPS smoke checks loaded 2,138 official families and 10,995 glyphs.
  Google `ofl/abel` at commit `6157dfaa640ca5738b4d1a7070fe389c3036d7fc` validated
  one face plus OFL.txt. Nerd Fonts v3.5.1 ProggyClean validated nine faces,
  Licence.txt and Mono/Nerd/Propo variants. Downloads stayed in temporary roots;
  the smoke process bypassed the environment's package proxy. Runtime requests
  retain normal configured proxy behavior. A separate request through this
  execution environment's configured proxy failed; no proxy settings were changed.
- File-platform: 5 passed; shared file operations: 22 passed. Installation:
  27/28 passed, including the new standalone fonts install/repeat/restore case.
  Adapter suite: 5 passed, 5 native-platform skips. Bash CLI: 24 passed; shared
  native controller: 16 passed, 1 unavailable-runtime skip. Launcher: 21 passed;
  local completion: 6 passed. Native PowerShell was not available on this host.
- Wiki generation: 18 passed. Wiki Git workflows: 9/10 passed. Relative Markdown
  links, generated fonts adapter checks, static command metadata, Python/shell
  syntax and whitespace checks pass. Canonical font docs and wiki mapping were
  added; the local wiki was rebuilt and checked, without publication.

Broader failures were preserved and reported: the WSL full-checkout installer
republishes theme pointers on its second apply (also reproduced alone; its existing
bundled-only test documents that baseline exception). The wiki Git all-mode fixture
is blocked by push host/namespace ownership for its disposable remotes. Neither
failure identifies a fonts path, and neither policy was weakened to pass tests.

Pending acceptance: actual PowerShell 5.1/7, native Windows HKCU/font visibility,
locked-file recovery, Windows Terminal/VS Code/WezTerm and native Linux/WSL desktop
rendering. A visible Termux font activation/reload/restoration test still requires
live authorization. Mocked registry and private-terminal evidence do not establish
those results. No live fonts, commits or remote publication were changed. Todo progress for the selected follow-up is tracked separately through the Todo CLI.

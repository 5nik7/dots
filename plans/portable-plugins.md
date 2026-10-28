# Portable plugins and application menus

**Status: Implemented and locally verified; authorized live migration completed. Native Windows/WSL acceptance remains pending.**

## Goals

- [x] Consolidate Anodize, Blastoff and pkgs under `plugins/`, with one declarative installation manifest and unchanged command contracts. Keep shared Dots services in the core, preserve original repositories, and retain a source recovery snapshot before moving uncommitted work.
- [x] Inventory and migrate verified legacy installation assets through the existing Store and installation receipt. `dots files migrate-apps` previews by default; `--yes` applies and `--dry-run` wins. Preserve application data, unknown/edited files and existing backups. Migration does not install unrelated configuration or publish themes. Live migration with retained backups is authorized after isolated validation.
- [x] Add `dots menu blastoff` and `dots menu pkgs` plus main launcher groups for common workflows, with existing confirmations, exact-client handoff, output readers, cancellation and inert data modes.
- [x] Maintain canonical docs/wiki and add a plugin-maintenance skill. Require an add/update/no-menu assessment for every new or changed command.

## Boundaries and menu assessment

All three plugins install together within Dots. Independent distributions and enable/disable controls are outside scope. Preserve standalone and Dots-prefixed subcommands, raw/JSON output and documented environment overrides. Native Windows pkgs operations remain unavailable except help/version; native Windows and WSL acceptance must be reported separately from local fixtures.

Blastoff and pkgs: **add menus** for common existing workflows. Anodize: **retain existing menu**, update its paths and regression coverage. Application migration: **no menu** because this infrequent installation/recovery operation requires explicit inspection of a complete plan. Do not create a package-manager shortcut, bypass application approval, execute previews, or add `--yes`/`--force` to menu actions.

Blastoff entries: pick, current, theme list/edit/save, module show, backup list, doctor, help. pkgs entries: search/install/uninstall/list/upgrade/refresh/managers/doctor/help. Use reports for noninteractive output and terminal handoff for pickers/editors/transactions; return to the invoking family afterwards. Preserve Back/F1 and query restoration. Direct family routes start in that family; Back exits.

## Acceptance

Use disposable home/config/state/cache/repository roots. Verify relocated source paths, literal arguments, unchanged streams/status, metadata, completions and first/repeat installation. Migration tests must cover spoofed or changed receipts, guarded legacy files, overlapping completion ownership, unknown files, rollback, interrupted recovery, no-op repetition and drift-aware uninstall. No tests may change host packages or active configuration.

Run application suites, relevant Dots installer/dispatcher/native/menu suites, offline Anodize build checks, shell syntax, scoped whitespace, documentation links and generated wiki validation. Review human output at narrow and normal widths with semantic colors/plain fallbacks. Exercise private tmux/PTY handoff, missing tools, cancellation and inert preview/data paths. Preserve the previously reproduced whole-theme idempotence failure as a separate baseline finding.

Only after tests and a concrete live preview, apply the authorized application migration and verify command resolution/completion assets without package transactions, theme activation, shell reloads, commits or pushes.

## Evidence

Planning audit: Termux Blastoff receipt hashes match all 125 recorded files; standalone pkgs lives in the user-local library and its completion receipt overlaps Dots-managed Fish files. Original source repositories and existing user changes are retained. Implementation evidence will be recorded here.


## Implementation evidence (2026-10-28)

- Source recovery snapshot: `/data/data/com.termux/files/usr/tmp/dots-plugin-recovery-plhv4ohn`. Both original repositories remain clean; all 177 Blastoff and 31 pkgs tracked files remain present under their plugins.
- Live application-only migration completed under transaction `ac70d16449664ab0893525dc59c86ba3`; its immediate repeat was unchanged. Private audit output is retained at `/data/data/com.termux/files/usr/tmp/dots-app-migration-live-4ywr_uuz`. Hashes of active Starship configuration, Blastoff configuration/themes and edit recovery were unchanged. Old bytecode and earlier recovery backups remain explicitly retained.
- Ten synthetic migration cases pass, including process death after retirement, journal recovery, forged/changed receipts, startup-reference refusal, manifest path escapes, exact baseline restoration and repeated migration. Full-checkout bundled install/repeat/uninstall passes independently of the previously recorded whole-theme idempotence failure.
- Application routing/lifecycle suite: 17 cases passed with one native PowerShell skip, plus subsequent installed-Anodize and hosted-FZF capability checks. Blastoff core: 233 cases passed with three optional skips. pkgs core: 85 tests passed after the final popup capability adjustment.
- Menus: 20 existing/shared cases pass; the additional private two-client test passes for both new application-family terminal handoffs, literal cwd/arguments and cancellation return. Bash dispatcher 24 cases pass; native CLI 14 cases pass with one native engine skip; local completion 6 cases pass; installation adapters 10 cases pass with five native skips.
- Anodize: isolated Go build/test/vet pass; authoring 18 tests pass; interactive 13 cases pass with one optional skip; artwork/PTY 22 tests pass; completion/manual integration 5 tests pass. Native Windows/WSL and real PowerShell 5.1/7 remain named pending acceptance checks.
- Direct dispatch, 15 measured samples after three warmups on Termux: no extra routes 66.682 ms before / 63.270 ms after; 1,000 routes 64.621 ms before / 65.940 ms after. No route-count scaling regression observed locally.

The local wiki export is rebuilt and healthy. Canonical and plugin-relative links, generated metadata, scoped whitespace, launcher syntax/ShellCheck and all three maintenance skills validate. Native Anodize controller tests (3) and isolated build-environment tests (2) also pass. No commits, pushes, package operations or live theme activation were performed.

## Report presentation follow-up

**Status: Implemented and locally verified; native Windows/Linux/WSL visual acceptance remains pending.** Apply the [presentation acceptance gate](../docs/presentation.md#acceptance-gate) to Blastoff current/theme-list/save/backup-list/doctor and pkgs list/managers/doctor, including aliases and both standalone/Dots command forms. Menu assessment: **update existing views**, retaining action mappings, terminal ownership and confirmations. Shared report settings and resource styling belong to Dots; application-specific layouts stay in their plugins. Human capture is explicit even without color/icons. Keep ordinary redirected formats and all JSON/raw/completion bytes, mutation guards and package-manager streams intact.

Verify populated/empty/error reports, exact versus modified provenance, malformed/missing backups, nested completion diagnostics, save cancellation/collisions, per-stream controls and 40/80/120-column PTYs/private tmux readers. Use isolated roots and mocked package backends. Both shell frontends share the renderer; Windows Starship/Blastoff paths and overrides remain unchanged, and native Windows pkgs remains help/version only. Native PowerShell 5.1/7, Linux and WSL visual acceptance remain pending where unavailable. Record checks and representative report timings after implementation; synchronize canonical documentation and the local wiki without installation, theme activation or Git publication.

### Local verification (2026-10-28)

- Blastoff core: 233 tests, three optional skips; pkgs core: 85 tests. Shared integration checks pass: bundled commands 18 tests (one native PowerShell skip), menus 24, pager 15, launcher 21 and resources 15.
- The focused report suite runs ten cases with one native Windows PowerShell skip. It verifies actual private tmux readers at 40/80/120 columns, exact-client ownership, long-package-list scrolling, color-disabled popup layouts, forced-decoration data bytes, command aliases/frontend equivalence and isolated save/cancellation. Additional final Blastoff presentation/help/save checks pass; native PowerShell engines are unavailable locally.
- Reviewed fixture layouts at 40/80 columns and enforced display-cell bounds at 40/80/120. Long values remain complete; concise doctor labels align with resource fields. Published file-style fixtures are used without querying tools per row. The relocated asset-free fixture includes the shared Dots runtime.
- Termux timing: 15 samples after three warmups, interleaved `current` subprocesses, median 408.725 ms plain redirected versus 516.144 ms styled. The additional shared renderer/resource path costs about 107 ms in this fixture; this is a same-tree mode comparison, not a pristine pre-change baseline. Rendering 1,000 mocked package rows has a 276.794 ms median with exactly one inventory request and no backend subprocesses. No cache or extra discovery was introduced.
- Canonical Markdown links, generated metadata and both command validators pass. Task-scoped whitespace passes; the full checkout check retains the pre-existing extra EOF blank line in `config/blastoff/themes/dots.toml`. Blastoff manual lint is clean; pkgs retains its imported date/long-line lint warnings. The local wiki is rebuilt and checked after canonical updates; no publication, installation, active configuration change or package transaction is performed.

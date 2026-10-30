# Core registry and generated profile environments

Status: implemented; focused acceptance passed. Native Windows/Xonsh acceptance and the existing full-theme repeat failure remain separately recorded below.

Keep `.dots/sources.json` as source ownership and `.dots/files.json` as a
schema-2 registry of qualified identities and supported platforms. Profile
`files.REPOSITORY` arrays own implementation fields, without platform lists or
cross-platform target maps. Resolve the join before existing file planning;
guard and journal registry/profile writes together. Keep recovery identities and
legacy input normalization. No installation accompanies this source migration.

Generate active `PROFILE`/`PROFILEBIN`/`PROFILECONFIGS` and all declared profile
namespaces in one backend model. Always define config/configs, bin, scripts, lib,
fonts, shells, docs and skills; discover other visible immediate directories.
Generate canonical prefixes plus optional non-inherited aliases. Keep shared
root variables unchanged. Named maps use profile IDs and aliases, with native
PowerShell, Nushell and Fish equivalents. Preserve `$PROFILE` in PowerShell.

Remove the two profile .env files and duplicate path definitions in personal
hooks; retain navigation aliases and documented legacy variable/map bridges.
Application environment declarations can reference generated paths but cannot
define backend-owned names. Native adapters compile the same model, invalidate
on any relevant profile/directory change and keep warm startup free of Python
and directory scans. Preserve failed-generation atomicity and clean stale names.

Menu assessment: update the existing config popup with `profile.alias` editing
and correct mapping provenance. No additional menu family. Maintain help,
completion, environment/profile inspection and exact data contracts.

Add repository-local dots-profile-maintenance and dots-files-maintenance skills,
update related guidance, canonical docs and wiki. Preserve unrelated work.

Acceptance: before/after effective inventories on all four platforms; registry
validation and multi-file journal rollback/undo/drift; profile aliases, collisions,
inactive profiles, missing/new directories, cache invalidation, repeated init,
checkout switching, literal values, all shell adapters; affected file/config/menu
and shell suites in owned roots; sequential cold/warm startup measurements;
40/80/120-column human views, data nonexecution, metadata, syntax/ShellCheck,
skill validation, relative links and wiki synchronization. Native Windows,
Linux/WSL desktop and absent-shell acceptance must be reported separately.

Pre-change sources and inventory evidence:
`/data/data/com.termux/files/usr/tmp/dots-profile-backend-baseline-8ypn1z7o`.

## Implementation and verification evidence

- Restored the schema-2 core registry and source composition; profile implementation
  rows contain no platform lists or target maps. External Neovim mappings are explicit
  profile entries. Applicable inventory comparison is exact: Termux 49, Linux 45,
  WSL 45, Windows 40, including IDs, owners, sources, destinations, strategies,
  enabled state and replacement metadata. No live installation accompanied migration.
- Generated all declared profile namespaces, standard/immediate directory keys,
  active paths, aliases and native maps. Removed both profile `.env` links and
  duplicate hook definitions; retained legacy bridges and personal aliases.
  All file writers serialize against the core registry lock; config edits guard
  and lock profile manifests for namespace consistency across state stores.
- Added `profile.alias` CLI/popup/completion support and repository-local
  `dots-profile-maintenance` / `dots-files-maintenance` skills with discovery links.
  Both skills validate. Config popup built-in backup default now agrees with the
  file controller (false). Profile human reports summarize mapping/settings objects.
- Latest focused backend suite: 14 passed, covering schema joins and absence,
  combined writes/rollback/drift/undo, adoption/removal, eligibility preservation,
  explicit base versus active leaf edits, aliases/completion/popup at 40/80/120
  columns, inactive-profile cache invalidation and failed reload, literal paths,
  application templates and Bash/Zsh/Fish maps. Native PowerShell renderer assertions
  preserve automatic `$PROFILE`; execution remains pending.
- The [font directory follow-up](fonts.md#directory-follow-up) adds shared `DOTFONTS` for `<checkout>/fonts`, with override refusal, native exports and checkout-switch/reload coverage in the backend suite. Its separate startup comparison and native acceptance limits are recorded in the fonts plan.
- Selected broader suites: 359 recorded tests across 20 suites, 309 passed,
  49 skipped, one failure. Profile/config/menu, catalog/mapping/file operations,
  check/repair, native controller, dispatcher, style, retirement, platform adapter,
  shell environment and startup coverage passed. Native PowerShell was unavailable;
  the installed Xonsh launcher names an unavailable interpreter. No launcher or
  interpreter was installed or changed for these checks.
- Installation: 26/27 passed. The remaining
  `test_fresh_checkout_wsl_setup_connectors_check_and_restore` failure is the
  existing full-theme repeat/fingerprint issue: a second install republishes
  `theme:catppuccin-mocha`, selection and active pointers instead of reporting
  unchanged. The existing bundled-lifecycle fixture already names this baseline
  limitation; bundled install/repeat/removal passes. File inventory equivalence
  and focused idempotence tests pass independently. This is not native WSL evidence.
- Updated stale fixture assumptions: complete installation copies now include
  profile manifests; legacy Todo fixtures join registry eligibility; integration
  startup does not activate Mise; retired 256-color arrays stay absent and RST
  retains its escape sequence. Human style assertions follow semantic coloring.
- Syntax, `git diff --check`, relative Markdown targets, 212-command metadata
  validation and read-only live config/all-four-profile checks passed. ShellCheck
  passed with SC1090 excluded for generated dynamic source paths. Wiki source and
  export checks passed after local build transaction
  `026c942156f94c07b057ca983f1d9097`.

### Startup measurements

All startup measurements use disposable public fixtures and no personal hooks.
The first separate runs varied materially with device load, so the final comparison
alternated baseline/current launches with 30 warm samples per shell. Median warm
Bash changed from 54.649 to 59.770 ms; Zsh from 298.861 to 304.009 ms. The roughly
5 ms increase covers the additional exported paths/native maps and metadata guards
for inactive manifests and directory inventories. Compound native assignments keep
this bounded; warm startup still performs no Python launch or directory scan.
The paired cold observations (one per side) were Bash 746.612/607.594 ms and Zsh
801.067/931.778 ms; these are observations, not stable cold-start guarantees.
Original three-cold/fifteen-warm and subsequent comparison runs are retained too.

Evidence directory: `/data/data/com.termux/files/usr/tmp/dots-profile-backend-baseline-8ypn1z7o`.
It contains pre-change sources/inventories, per-suite logs, `verification-summary.json`,
`inventory-verification.json` and `startup-paired.json`. No commits, pushes, live
shell reload, theme publication or managed file installation were performed.

# Fresh-machine bootstrap, safe links, and unified backups

**Status: implemented; local acceptance complete, named native checks pending.**

The approved plan extends setup on Termux, Linux, WSL and native Windows. Bash,
Zsh, Fish, PowerShell, Nushell and Xonsh share the command contracts. Existing
installer work remains complete; this is a separate follow-up, not a reopening.

## Goal tree and ordering

Parent: `aec3df20995c40fbb7e5ccee0f1b6e9a` (high priority).

| Package | ID | Dependencies |
| --- | --- | --- |
| B1 Shared backup catalog and bak lifecycle | `819667f2a00f4cbc981d3040cdaeb3b3` | None |
| B2 Safe link command and shell aliases | `af406d4f97ee41478aec6e3512c745e7` | B1 |
| B3 Fresh-machine acquisition and prerequisites | `c57a88506fa741b49643fa6cd7abc19d` | None |
| B4 Shell precedence and PowerShell parity | `8374f9f98160430b97ff912dbc01972c` | B2 |
| B5 Linked Blastoff themes and generated theme commands | `64cda7ce8ae94f0e9671f0eca1e6b909` | B1, B2 |
| B6 Integrated installer and uninstall recovery | `b7c1d3140aeb434e96f407d56fe3a0d1` | B1–B5 |
| B7 Acceptance, documentation and maintenance guidance | `c8a92c0709ee4deb9a7bb71009d4fcb7` | B1–B6 |

Completed installer goal `022292f71f29492c8d9e1a3ddad7f556` and its seven
children retain their IDs, relationships, notes, criteria and status. Separate
Leaf verification `2aa8ff8e6974413482e72c076c1e2459` remains outside this scope.

## Approved behavior

- Fresh-machine POSIX/PowerShell bootstrap acquires or reuses a checkout and
  converges on the existing shared installer. Defaults: public HTTPS Dots source,
  main, `~/dots`; explicit source/ref/destination overrides. Record the commit;
  never reset or implicitly update an existing checkout.
- Review required dependencies of selected components only; the full profile
  package list stays optional. Default components require Python 3.11+. Native
  package managers are preferred; Windows without WinGet offers verified official
  Git/Python installers. Selected Anodize engine builds use checked-in requirements.
  Windows offers Developer Mode explicitly if symlinks are unavailable. No silent
  link-to-copy fallback, package-manager bootstrap or automatic elevation.
- Retain preparation/final reviews, cancellation, noninteractive flags and
  no-write/no-download dry runs. Stop before managed publication on preparation
  failure. Keep login-shell selection unchanged.
- Dots launchers win PATH. Review and back up competing user-owned old launchers;
  preserve package-manager installations. Configure Git and its existing bounded
  gitplatform companion, shell links and generated outputs through installer receipts.
- Review and replace changed destinations while keeping both their edited content
  and the first uninstall baseline. Correct links to edited repository sources are
  no-ops. Preserve unrelated changes.
- `dots link`, `dots-link`, and `.ln` use ln-style target-directory rules, with
  `-T/--no-target-directory` for an exact destination. Preflight the batch and apply
  immediately with backups; correct links do nothing. Absolute source paths by
  default, optional relative links, explicit allow-missing. Preserve source link
  identity; guard parents/concurrency and reject overlapping operations.
- Link output: `󰡯 ~/sourcefile -> ~/target`, using shared resource styling and
  home-boundary abbreviation. Quiet suppresses routine output, never errors. JSON
  uses undecorated full paths. Do not invoke external classifiers per file.
- `bak PATH...`/`bak create` move by default; explicit copy retains the original.
  Default store `~/.bakstore`; adjacent mode uses `filename.{UTC-timestamp}.bak`.
  Stable IDs and recorded original paths disambiguate identical basenames.
- Commands: create/list/show/restore/delete/prune/import/browse. Bare bak browses
  in a terminal, shows help otherwise. `bak -- NAME` escapes action-name collisions.
  Restore retains the saved version and backs up an occupied destination. Import
  registers legacy objects in place; unknown originals need an explicit restore
  destination. No automatic pruning. Explicit prune filters/confirmation protect
  pending recovery data and installation baselines.
- New manual/link/setup backups share a catalog; old journals remain readable.
  Restoring a managed baseline reconciles the owning receipt in the same transaction.
- `--no-backup` itself permits replacement without retention. Temporary rollback
  copies remain until commit; existing retained baselines are never deleted by this
  flag. Report when uninstall cannot recreate a deliberately discarded original.
- Port applicable Zsh helpers to PowerShell. Discover each installed 5.1/7 engine's
  per-user all-hosts profile; retain host-specific customizations. Keep native
  dots.ps1/shared Python controllers and generated theme wrappers, not a wholesale
  module conversion. Avoid eager optional imports; measure startup.
- Fresh theme is Catppuccin Mocha; repeats keep the selected theme. Generate family
  and full-ID theme commands on both frontends, preserving unrelated collisions.
- Starship links directly to the saved Blastoff theme, default dots. Honor nonempty
  STARSHIP_CONFIG, otherwise `~/.config/starship.toml`. Back up link replacements;
  materialize presets without clobbering local themes. Linked edits update the saved
  theme with existing locks/backups; protect the active theme from deletion. Prepare
  the current/default palette first, preserve unrelated TOML and retain no-op repeats.

## Integration decisions

Family owner for link/bak: managed-files maintenance. Shell/profile, plugin and
Blastoff maintenance retain their respective boundaries. Configuration: add backup
store/location/mode controls and consumer-backed presentation through existing
inheritance; no persisted backup opt-out. Menu: add backup management and update
setup; link remains operand-driven. Static metadata, completion and native adapters
must agree. Canonical docs, README, safety/data contracts, platform claims and
maintenance guidance ship with behavior; rebuild/check available wiki sources.

## Acceptance and execution

Test only owned home/config/state/cache/checkout roots. Cover move/copy, symlinks,
directories, spaces/Unicode/leading dashes, same-name backups, linked parents,
cross-filesystem transfer, stale inputs, interruption, reverse rollback and legacy
recovery. Exercise complete fresh/repeat/selective-uninstall sequences, failed or
declined preparation, native capability failures, custom Starship paths and command
collisions. Verify 40/80/120-column, plain/quiet/data output and cancellation; help,
completion and dry-run stay inert. Run relevant existing suites sequentially and
record cold/warm startup. Native Windows 5.1/7, Linux and WSL evidence stays separate
from fixtures and is named pending when unavailable.

Use Todo CLI-only updates, rereading scoped JSON before each mutation. Start each
package when work begins; append evidence and complete verified children before
the parent. Continue independent work around genuine external blockers. No live
installation, package changes, profile reloads, commits or pushes are authorized
by this source-implementation task.

## Verification — 2026-11-11

The implementation is present in the checkout. Acceptance applies to the local
scope below; native checks remain explicitly pending. No live installation,
package change, profile reload, commit or push was performed.

- Backup catalog: 11/11; backup frontend/browser: 7/7. Covers move/copy,
  directories/broken links, adjacent/store retention, import, original paths,
  stale previews, protected baselines, retained restore and failure recovery.
- Safe links: eight original cases plus the added 40/80/120-column/data case
  pass. Quiet/data interfaces, batches, exact destinations, linked parents,
  source-link identity, overlap refusal and reverse rollback are covered.
- Bootstrap: six POSIX cases pass; one native Windows case skips. Acquisition
  uses local remotes, fake managers and literal operands; no private submodules
  or host package acquisition. Developer Mode and official Windows installer
  execution remain named native acceptance checks.
- Shell environment: 11/11. Shell init: all available cases in the 31-case runner
  pass after correcting the first-start Zsh PATH order and old order expectations;
  18 optional/native cases skip. Public .ln invocation: five shells pass (Bash,
  Zsh, Fish, Nushell, Xonsh); PowerShell skips. The Zsh test evaluates a subsequent
  input line because -c parses aliases before sourcing the generated hook.
- Installation: all 28 cases pass across the full run and three focused reruns.
  The initial old foreign-link refusal expectation was replaced with reviewed
  backup/restoration acceptance. Two complete checkout fixtures exceeded the old
  120-second cold Go build budget; both passed with a 600-second fixture budget.
  The actual checkout dry-run succeeds with 81 planned items and zero conflicts.
  Actual isolated Anodize tests/builds and repeat artifact reuse ran on Termux
  (Go 1.27.3, checked-in minimum 1.27.1).
- Setup integration: 6/6; file-platform: 5/5; setup components: 5/5; preparation
  stages: 5/5; wizard: 7/7. Native adapters: five pass/five explicit skips.
  Bundled app adapters/lifecycle: 17 pass/one PowerShell skip. Menu contracts:
  15/15, including backup navigation and approval-free setup handoff.
- Blastoff linked-theme frontend: four cases pass, including custom active path,
  exact destination backup, linked edits, preset name collisions and no-op repeat.
  Shared locks coordinate application writes with installer palette publication.
  Tracking repairs, alias archival, concurrent target edits/retargeting and
  active-theme deletion protection pass. Independent active/source fixtures use
  explicit --replace-link; they no longer assume default copy-on-apply.
- Full Blastoff application audit: 233 cases, 222 pass, eight known presentation
  assertions fail, three optional/native skips (339.012 seconds). The same eight
  failures reproduce using HEAD's Blastoff implementation against the existing
  shared presentation code: test_assets.OptionalAssets (one), test_current
  (three), test_list_output (one), test_output_policy (three). They expect old
  bright ANSI codes where the shared renderer supplies configurable semantic
  colors. These pre-existing failures remain outside this behavioral change;
  no functional failure remains in the final application run.
- Test-isolation correction: older discovery/picker fixtures inherited the host
  XDG state directory despite owning HOME. Seventeen test-only backup records
  were removed through guarded Store transactions, preserving other entries;
  the host catalog is empty after cleanup. Audit journals are retained. Both
  fixtures now own XDG state/data, and the application runner supplies an outer
  temporary HOME/XDG boundary. No installed command or personal file was replaced.
- Startup, milliseconds (owned public fixtures, theme/completion/plugins disabled;
  nine alternating sequential warm samples, prior shell sources from HEAD):

  | Shell | Cold before / after | Warm median before / after |
  | --- | --- | --- |
  | Bash | 1321.780 / 1454.489 | 399.385 / 435.765 |
  | Zsh | 4582.427 / 3119.379 | 660.375 / 706.759 |

  Warm fixture medians increase by about 36 ms / 46 ms (9% / 7%). The changed
  startup path makes a final normalization pass to keep Dots ahead of personal
  shell PATH additions; no new startup subprocess or eager optional import was
  added. Cold measurements and device scheduling vary. Native PowerShell startup
  measurement remains pending, so no native performance benefit is claimed for
  the retained script/shared-controller design.
- Static metadata validates 255 routes; backup/bundled generators and generated
  manual are current. Changed Python sources parse without bytecode; Bash/Fish
  syntax and both modified maintenance-skill validators pass. Relative Markdown
  file links pass (1381 across 183 files before the final evidence update).
- Final focused reruns: Blastoff links 4/4, setup integration 6/6 and bootstrap 6 pass/one native skip. Config values: the 13-case run had one old drift-refusal expectation; the corrected copy/drift/uninstall case and new backup controls test both pass (14 distinct cases verified overall).
- Wiki rebuilt through transaction `eb991798234d4bd295b1bfbc797136b4`; `wiki check --json` reports healthy=true. Both the main and wiki working trees retain unrelated prior work. No commits or pushes.

## Backup and picker follow-up (2026-11-11)

Implemented the requested correction to Blastoff's inherited FZF options: normal
picker-owned preview/prompt/bindings are silently replaced (verbose diagnostics
remain), while malformed or unreadable settings still warn. Preserve the
nonexecuting option allowlist and opaque picker identities.

Unified new Blastoff snapshots with `BackupPlan`, including linked apply, copy
apply, edits, stored replacements/removal and explicit backup creation. Automatic
snapshots copy before mutation; manual `bak` still moves by default. Keep legacy
Blastoff pairs readable/restorable/deletable without migrating live state. Update
backup listing, preview and contextual completion for shared catalog IDs.

Deletion/pruning removes a proven transaction-created UUID container when it
contains only that payload, including already-missing payloads. Never remove
adjacent/import parents or containers with other files. Guard the whole container
and catalog, and verify rollback and concurrent-change refusal. Internal Store
recovery copies, editor scratch files and build staging remain internal machinery.

Configuration review: update Blastoff backup creation to consume existing
`apps.bak.store` and `apps.bak.location`; no new settings. Menu review: existing
backup list/delete/picker and Bak browser routes remain sufficient; update their
shared inventory behavior. No new routes. Verify both frontend contracts with
isolated fixtures; native PowerShell execution remains named pending below.

### Follow-up audit and verification

- Audited manual/Bash/PowerShell backup adapters, `link_cli`, installation
  `retain_destination`, and setup Starship/font/Leaf/Anodize publication. These
  already compose user snapshots through `BackupPlan`. Build `copy2` calls copy
  inputs into owned staging; Store recovery payloads and editor scratch files
  retain their separate internal purpose.
- Replaced Blastoff's remaining app backup writer and the link operation's
  duplicate legacy content-pair writer with `shared_backups`. Config create,
  copy/linked apply, module load, edit, restore, stored replacement/delete and
  migration replacements now use that catalog. Old pairs stay readable without
  host migration; content restore and exact-link restoration stay distinct.
- Final sequential checks: backup model 15/15; backup frontend 7/7; safe links
  9/9; linked Blastoff 4/4; bootstrap integration 6/6. Final Blastoff subset:
  35 run, 34 passed, one unavailable native PowerShell skip. It includes six
  shared-backup cases, all 13 completion cases (including installed symlinks),
  eight FZF cases with real option parsing at 40/80/120 columns, PowerShell
  adapter source checks and the timeout case below. Total: 75 passed/one skip.
- Broad Blastoff run: 241 cases, 229 passed, the same eight previously recorded
  ANSI-code expectation failures, one five-second subprocess timeout and three
  optional/native skips. The timed-out active-config case passed the final
  focused rerun without changing its timeout or behavior. No unresolved
  functional failure was found. Native Windows execution remains pending.
- Metadata validates 255 routes; generated backup/bundled adapters and manual
  are current. Python/Bash/Zsh/Fish syntax, both maintenance skills, whitespace,
  canonical and changed Markdown relative-link checks pass.
- Wiki build reports unchanged and the full checkout check reports `healthy=true`;
  the canonical documentation and available export are synchronized.
- The user's existing Blastoff provenance changes and backups were preserved.
  No live apply, installer, package operation, shell reload, commit or push ran.

## Named pending native acceptance

Windows PowerShell 5.1 and 7: fresh acquisition with and without WinGet, signed
fallback installers, declined/approved Developer Mode and unavailable link
capability, both all-hosts profiles with host-specific content, native .ln/bak,
Windows app destinations, palette links, recovery and 40/80/120-column views.
Native Linux and WSL: fresh bootstrap and real app/shell consumers. Termux tests
that inject Linux/WSL paths establish fixture behavior only. The separately
tracked real patched Leaf build remains outside this follow-up.

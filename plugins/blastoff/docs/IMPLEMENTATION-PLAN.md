# 0.1.12 default Starship path and active aliases

Owner-approved: preserve the default-path config symlink, implement guarded target
writes, retain explicit overrides and --replace-link, verify and upgrade the live
Termux installation using its existing installer. No Git publication or theme apply.

- [x] Shared active-target resolution, drift guards, locks and provenance compatibility
- [x] Focused/full isolated suites, shell/manual checks and upgrade rehearsal
- [x] Final docs, checksums, verified package and authorized Termux upgrade

# 0.1.11 platform detection and frontend parity

- [x] Shared read-only host classification, visible SYSTEM and native defaults
- [x] MSYS2/Git Bash guidance and incompatible-runtime guards before writes
- [x] Legacy PowerShell transport, runtime filtering and missing-Python status 3
- [x] Native parity discovery, completion setup repair and expanded host/argv/state checks
- [x] Current version/docs/man/changelog updated; historical evidence preserved
- [x] Full suite, shell/manual checks, benchmarks and genuine 0.1.10 upgrade rehearsal
- [x] Final evidence, checksums, reproducible packages and extracted verification

PowerShell 7+ remains the contract. Native Windows/PowerShell/WSL and interactive
gates are pending where unavailable. All lifecycle checks use temporary roots;
no live installation, profile edits or Git publication are part of this work.

# 0.1.10 no-argument help follow-up

- [x] Shared parser handles bare/global-flags-only human help before application imports
- [x] Preserve explicit JSON welcome, nested help, version and invalid-option errors
- [x] Exact-output/core/Bash/PTY/import checks and PowerShell/installed parity cases
- [x] Current help descriptions/examples reconciled; historical checkpoints retained
- [x] Full suite (266 tests, seven skips), available shell/manual checks and separate Python/Bash startup samples
- [x] Final evidence, checksums and separately located verified review archives

Retain the current review version and existing work. No live installation or Git
publication. Native Windows/PowerShell and human visual gates remain separate.

# 0.1.10 theme-list readability — implementation checkpoint

- [x] Shared styles and list renderer; trusted origin/current/modified markers
- [x] Bounded read-only inspection and concurrent-change detection
- [x] Focused tests and PowerShell parity cases; help/docs/preferences reconciled
- [x] Available native checks, paired baseline comparison and isolated lifecycle verification (261 tests, seven skips)
- [x] Final evidence, checksum/archive generation and verification

No JSON/CLI/storage changes. Preserve the existing 0.1.9 work and historical records.
Native PowerShell/Windows/WSL and human visuals remain unverified until run. Manual
acceptance is still paused at step 5, without implying previous passes or installation.

# 0.1.9 backup-list readability — implementation checkpoint

- [x] Shared sanitized token output and reusable accents in lib/blastoff.py
- [x] Spaced/narrow records, aware UTC and inspected byte sizes in lib/backups.py
- [x] Guidelines, examples, manual and current-version references reconciled
- [x] Focused/full tests, help/completion checks and native evidence recorded (248 tests; seven skips)
- [x] Focused empty/populated baseline comparison and reproducible package/upgrade verification

No CLI/JSON/schema/storage changes. Preserve existing work and historical evidence.
Manual review remains paused at step 5; native PowerShell and human visuals remain
pending until run. Finish evidence/doc edits before final checksum/archive creation.

# 0.1.8 follow-up — implementation checkpoint

Approved follow-up: fancy defaults across browsers, explicit basic --fzf,
correct fzf/bat inheritance, human output by default, PowerShell 7+ parity,
CurrentUser root PowerShell lifecycle, lightweight completion and measured startup.
Preserve the existing 0.1.7 work, data/ownership protections and shared Python core.

- [x] Human output policy and backup renderer
- [x] Shared fancy/basic syntax and configuration inheritance
- [x] PowerShell forwarding, completion and native-host boundaries
- [x] Root PowerShell lifecycle using shared ownership/atomic-write helpers
- [x] All help/completion/manual/docs/workflow surfaces reconciled
- [x] Focused/full native Termux checks and isolated lifecycle verification (242 tests; seven explicit skips)
- [x] Baseline and follow-up performance evidence; unavailable hosts deferred
- [x] Final source inventory, checksums, reproducible archives and extracted-install checks

Implementation files: lib/cli.py, blastoff.py, backups.py, operations.py,
picker_ui.py, preview.py, argv_transport.py and completion_names.py;
powershell/blastoff.psm1, blastoff.psd1 and runtime.ps1; root install.ps1 and
uninstall.ps1; scripts/powershell_lifecycle.ps1, powershell_install.py, install.py,
integration.py, interactive_check.py, benchmark.py, benchmark-powershell.ps1,
package.py and verify.py. Shell completion, native-session/lifecycle harnesses,
fixture tests and platform documentation ship together. Runtime business logic
remains in the shared core; the lifecycle layout uses the shared transaction engine.

Manual acceptance is paused at step 5 (backup deletion). Earlier steps and live
installation are not assumed passed. Native Windows/WSL/PowerShell and real fzf
checks remain pending where unavailable. Human appearance is separate from tests.
Final packaging follows all code, documentation and evidence edits. No live
installation, profile/config changes, commit, tag or publication is authorized.

The following checkpoint is historical; its default-basic picker and related
configuration/output descriptions are superseded by the 0.1.8 contract.

# 0.1.7 implementation checkpoint

Approved scope: shared verbose/dry-run; versioned provenance; staged active editing;
interactive save; safe multi-backup deletion; basic/fancy responsive pickers;
module viewing; four-shell completion, documentation and release verification.

- [x] Shared preparation and diagnostics
- [x] Provenance, backup metadata and current status
- [x] Editor and interactive save
- [x] Backup deletion
- [x] Shared previews, picker styles and module viewing
- [x] Completion/help/manual/documentation consistency
- [x] Focused/full native tests and performance (221 tests; five explicit platform/tool skips)
- [x] Final checksums, reproducible archives and isolated 0.1.6 upgrade/uninstall

Implementation map (0.1.7; actual verification is recorded in STATUS.md):

| Requirement | Deliverables and acceptance |
|---|---|
| Shared safety/output | `lib/cli.py`, `lib/blastoff.py`, `lib/operations.py`; global flags, read-only preflight, stderr diagnostics, unchanged shell entry points; `test_dry_run.py` and existing core/storage tests |
| Backup deletion | `lib/backups.py`; frozen selection, aliases/escaping, confirmation, payload/metadata guards, partial failures; `test_backup_delete.py` |
| Edit and save | `lib/editor.py`, `lib/operations.py`; waiting argv, staged recovery, destination/config/tracking concurrency; `test_edit.py`, `test_theme_save.py` |
| Provenance | `lib/provenance.py`; path-associated versioned state, pending failure marker, backup snapshot, no guessed destination; `test_provenance.py`, `test_current.py` |
| Pickers and modules | `lib/picker_ui.py`, `lib/preview.py`; reviewed options, basic/fancy, Ctrl-X, responsive bat/plain source, numeric IDs; picker/preview/options/module tests |
| User and shell contract | `lib/cli.py`, all four completions, `man/blastoff.1`; actual Bash/Zsh/Fish contexts and static/optional PowerShell checks; `test_completions.py`, `test_powershell_completion.py`, `test_docs_contract.py` |
| Lifecycle | `scripts/install.py`, `scripts/package.py`, existing wrappers/ownership engine; installed siblings, actual historical-version upgrade, data retention; installed/public/planning/packaging tests |
| Documentation | README, quickstart, CLI contract, installation/migration/recovery, UX/check guides, decisions, preferences/agent/pi workflows, changelog/version and this checkpoint; preserve historical evidence |

Remaining release gates are explicit: real fzf selection/resizing and fancy
visuals, human terminal/plugin checks, and native Windows/PowerShell parity.
These are not implied by fixture/static checks. Rendered prompt previews are
excluded from this release because no safe execution isolation is provided.

Native Windows is deferred. Human visuals and unavailable native tools must remain
unverified until run. No live install/profile/config changes or Git publication.
Final packaging follows all code and documentation edits; rebuild after any later
edit. The older continuation plan below is historical and superseded by this
checklist, CLI-CONTRACT.md and decisions/0002-provenance-and-interactive-editing.md.

# Implementation and continuation plan

The 0.1.0 review build is already in the actual repository; no staging copy,
archive integration or branch change is needed. Native verification evidence
and remaining platform gates are recorded in STATUS.md and TERMUX-AUDIT.md.
Follow the contract and use old implementations as references, never as an
automatic migration.

| Slice | Deliverable | Acceptance | Current state |
|---|---|---|---|
| 0. Audit | Preserve sources, inspect local repo, preferences, contract and architecture | Path/behavior differences recorded; unrelated work protected | Actual repo inspected; incoming inventory differences recorded in TERMUX-AUDIT.md |
| 1. Read-only core | Help/version/list/current/doctor | No writes; no required Starship for local paths; missing dirs usable | Implemented; Linux and native Termux checks |
| 2. Theme mutations | Apply/save/copy/import/delete/backup/restore/migrate | Safe names, TOML validation, backup, staging, collisions, links and locks | Implemented; native Termux regression fixes verified |
| 3. Modules | Save/load/list/delete explicit tables | Nested tables, custom modules, strings, unrelated settings and failure recovery | Implemented; unsupported layouts refused |
| 4. Frontends | Bash and PowerShell module, old aliases | Same shared arguments/results; native stream/TTY/exit tests | Implemented; native PowerShell gate pending |
| 5. UX | Purple/magenta output, JSON, optional fzf/gum/number picker, completions | Clean pipes/NO_COLOR; cancellation; actual shell completion cases | Native positional matrix and real editor/picker PTYs verified; human visual/plugin checks pending |
| 6. Lifecycle | Battery-style public wrappers, native discovery, owned integration, legacy migration, immutable runtime | No-write dry-run; conflicts block; target commit before resumable cleanup; profile backups/data retained | 0.1.4 implemented; current verification results recorded separately in STATUS.md |
| 7. Release | Native evidence, changelog, docs, reproducible packaging and performance | Termux ARM64 + native Linux + native Windows gates; honest evidence | Historical Linux and native Termux evidence; Windows and interactive gates open |

## Continuation in the real repository

1. Recheck Git status and current guidance before each slice. Preserve unrelated
   working-tree changes and `.local/src` / `.local/logo` references.
2. The moved package has already been audited; see TERMUX-AUDIT.md for renamed
   references and unmatched images. Do not repeat integration or assume missing
   assets can be reconstructed.
3. Reuse recorded native evidence; run focused regressions for changed behavior
   and concrete gaps, not an automatic repeat of settled suites. Keep storage,
   config and installation fixtures isolated.
4. Follow TERMUX-QUICKSTART.md for everyday operations and the smallest useful
   remaining human check. Review TERMUX-INSTALL-PLAN.md and `bash install.sh
   --dry-run` before any live install. Native Termux now defaults to `$PREFIX`;
   verified legacy `~/.local` ownership migrates when the target differs. Preserve
   unrelated dots commands and resolve shadowing without overwriting them.
   No live installation or real-profile change is authorized by this plan.
5. Native Windows is explicitly deferred while unavailable; preserve
   WINDOWS-CHECKS.md unchanged for a future native run. It does not block Termux
   development or the separately approved Termux installation. Linux PowerShell
   or WSL must not substitute for native Windows evidence.
6. Update `docs/STATUS.md` with exact commands, versions and observations.
7. Fix real findings in bounded changes. Do not merely mark unchecked items done.

## 0.1.6 linked-storage slice

Support configured storage-root symlinks/junctions by pinning their canonical
existing target; allow ordinary missing non-linked paths without read-only writes.
Keep child-directory, leaf-file, active-config and lifecycle guards strict.
Verify alias lock contention, recovery, retargeting, broken/looping links and
offline completion in isolated roots. Record native Termux evidence in STATUS.md;
Windows junction/PowerShell execution remains a separate gate. Versioned upgrade
rehearsals use temporary prefixes, never the live installation.

## 0.1.4 lifecycle acceptance focus

Public install/uninstall need no action word or `--yes`; legacy entry points remain
available with manual activation unless already owning integration. Review native
Bash/Fish/man discovery and both Zsh completion destinations: canonical
site-functions and Termux's compiled Completion/Unix autoload directory. Custom
prefix hooks must preserve unrelated profile bytes/encoding; linked profiles and
targets must remain untouched on refusal. Check retained profile backups, Fish
conf.d and absolute versioned PowerShell imports without claiming Windows evidence.

Verify source-integrity refusal, no-write/no-probe dry-run, NO_COLOR, support-file
repair, immutable runtime rejection, no downgrade, conflict-before-write behavior
and resumable legacy cleanup after target commit. Use isolated fixture roots only.
These are acceptance requirements, not new test-pass claims. Documentation-only
work does not refresh checksums; reviewed deliberate source changes use
`bash scripts/build.sh` in the separate build/verification step.

## Before public release

- Measure warm startup for core/Bash/PowerShell separately, record sample count,
  hardware, runtime and p50/p95. Set realistic budgets from those measurements.
- Establish verified Starship minimum version rather than inventing a version
  from memory. Exercise supported preset output and command failure/timeout.
- Positional completion, source/destination contexts and paired backup IDs now
  have native coverage without invoking Starship. Continue human/plugin checks
  from INTERACTIVE-CHECKS.md; do not infer visual approval from automated PTYs.
- Assess abrupt-kill backup/install/migration recovery. Current implementation
  is per-file atomic, not multi-file crash transactional. Decide whether to add
  a durable transaction journal based on evidence.
- Review the module scanner against quoted keys, arrays-of-tables, multiline
  strings and inline/dotted layouts. Expand conservatively or adopt a tested TOML
  editing library through a documented dependency decision.
- Improve picker presentation and compact branding without expensive startup or
  command-executing previews. Keep supplied logo assets intact.
- Add CI for Linux, Bash/Zsh/Fish and native Windows PowerShell/core checks; keep
  Termux evidence separate. Do not claim an unrun CI configuration is passing.
- Preserve the repository's existing MIT license. Release version changes must
  remain consistent; do not invent a new license.
- Rebuild source checksums/package, verify archives and review installation scope
  before running a real install. Only create tags/push/publish when instructed.

## Definition of done

Every requested command and path works in the documented native environments;
frontends agree; file failures/cancellation preserve data; common paths meet
measured budgets; completions and manual match help; install/uninstall preserve
user configs; source/assets and unrelated work remain intact; open limitations
are explicit; release identity and verification artifacts agree.

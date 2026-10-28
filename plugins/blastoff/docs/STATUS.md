# 0.1.12 default Starship configuration and file aliases — 2026-10-21

Implemented the owner-approved default-path workflow. Normal active-file writes
preserve symlink chains, guard retargeting, lock the physical target and keep
canonical provenance. Explicit --replace-link still converts a link. Configured
and resolved paths are visible; default lookup requires no STARSHIP_CONFIG.
Historical alias tracking is read conservatively and archived on explicit writes.
See [decision 0004](decisions/0004-active-config-links.md).

Native host: Termux, Android 15/aarch64, Python 3.14.8.

- Full suite: 287 run, 280 passed, seven skipped, 215.296 seconds.
- After the final library-write/read boundary refinement: 99 affected tests,
  98 passed, one native-Windows skip, 67.888 seconds. Twelve focused tests cover
  default links, apply/module/save/restore, no-op writes, backup metadata, physical
  locks, retargeting before/after locks and atomic publication, external edits,
  unsafe parents/targets, canonical/legacy/conflicting/pending tracking and Windows
  extended path spelling. Editor tests verify preserved links and recovery.
- Bash/Zsh/Fish syntax, Python compilation without bytecode, mandoc lint and
  whitespace checks passed. Native PowerShell/Windows execution is unavailable;
  file-link privilege, junction/reparse and native lifecycle checks remain pending
  in WINDOWS-CHECKS.md. POSIX tests and spelling fixtures do not establish parity.

Startup sampling alternated the current source and checksum-verified 0.1.11 from
Git HEAD, 20 samples after five warmups per command, after test suites finished.
This working-device sample shows no meaningful startup regression or speedup.

| Entry | 0.1.11 p50 ms | 0.1.12 p50 ms | 0.1.12 p95 ms |
| --- | ---: | ---: | ---: |
| python-version | 79.005 | 76.076 | 87.032 |
| bash-version | 92.721 | 92.47 | 102.558 |
| python-help | 197.119 | 200.251 | 279.707 |
| bash-help | 210.89 | 215.499 | 279.002 |
| python-current | 237.611 | 243.958 | 307.427 |
| bash-current | 267.743 | 259.752 | 332.866 |

Both ZIP and tar.gz extracted inventories verified all 176 source files. The
isolated archive lifecycle test passed in 11.351 seconds using actual verified
0.1.11 source: upgrade, old-payload preservation, relocated-source execution,
installed defaults/links/history, completions, manual, uninstall and data retention.

The separately authorized live Termux upgrade passed after reviewing the public
installer dry-run: install the 41-file 0.1.12 runtime and refresh launcher/manual,
with no profile changes. Installed version/doctor/current pass with STARSHIP_CONFIG
removed from the child environment. The configured default resolves to the existing
repository target; its link and content hashes and all 135 Blastoff application
data files match the pre-upgrade snapshot. Existing edited-origin history remains
available. No theme was applied or prompt/custom command executed on live data.

Final package/checksum verification and local documentation-link checks passed.
The installer rehearsal uses only disposable homes/prefixes. No commit, tag, push
or publication occurred. Native Windows/PowerShell acceptance remains pending.
Historical evidence follows.

# 0.1.11 platform detection and frontend parity — 2026-10-16

Implemented shared lifecycle host classification and SYSTEM output, native Termux
and WSL defaults, MSYS2/Git Bash/Cygwin guidance, and Bash/runtime mismatch refusal
before destination planning. Missing Python now returns 3 from the Bash command
as well as lifecycle/PowerShell entry points. The legacy PowerShell installer uses
the shared literal argv transport without application alias rewriting; automatic
runtime selection excludes batch launchers. Public application JSON, storage and
ownership formats remain unchanged. PowerShell remains 7+, Python remains 3.11+.

Host: native Termux, Android 15/aarch64, kernel
`5.4.274-qgki-30957850-abG996USQSJHZB1`; Python 3.14.6, Bash 5.3.20, Zsh 5.9.2,
Fish 4.9.3. PowerShell and groff are unavailable; mandoc is available.

## Verification and limits

- Focused platform/transport/package/PowerShell-backend/static-completion/docs run:
  **34 tests passed** in 16.563 seconds. Classifier fixtures cover native Android,
  inherited markers, WSL, Linux, Windows, MSYS2 variants and no-write refusals;
  they do not establish native execution on those other hosts.
- Full `python3 -B -m unittest discover -s tests -v` rerun: **275 tests,
  268 passed, seven skipped**, 195.156 seconds. Evidence: `test-termux-0.1.11.txt`.
  Skips: four native PowerShell tests, one Windows junction, opt-in real Starship
  presets, and the separately run archive rehearsal.
- Initial full run: one numbered-picker Ctrl-C PTY timeout (275 tests,
  238.328 seconds). The identical timeout reproduced once in three runs against
  the preserved, unchanged 0.1.10 source; three focused 0.1.11 runs passed.
  The picker code was not changed. This intermittent issue remains open; the
  successful rerun is not proof it is fixed. Both initial and comparison output
  are preserved in `test-termux-0.1.11-initial.txt` and
  `test-termux-0.1.11-pty-comparison.txt`.
- Native Bash install dry-run, isolated HOME/PATH/prefix: SYSTEM reported
  `Termux (Android)`; verbose evidence reported android/posix/linux-android.
  The full fixture inventory was unchanged, including no destination creation.
- Bash syntax checks passed individually for all shipped shell scripts and the
  command/completion; native Zsh/Fish syntax, `mandoc -Tlint`, Python compilation
  without bytecode and `git diff --check` passed.
- Packaged Bash rehearsal using the actual verified 0.1.10 source: upgrade,
  idempotence, dry-run, relocated-source operation, missing-Python status 3,
  installed helper/completion/manual resolution, uninstall and data retention
  passed in 12.290 seconds. Evidence: `test-termux-0.1.11-archive.txt`.
- A separate genuine 0.1.10 -> 0.1.11 CurrentUser-layout Python-backend rehearsal
  passed on Termux: old payload retained during upgrade, current profile/version,
  repeat no-op, installed core/helpers, installed uninstaller and modified-file/
  application-data retention. This exercised Python's shared lifecycle backend,
  not a PowerShell engine or Windows filesystem.
- Native PowerShell completion fixture setup now imports sys. Unittest invokes
  parity.ps1 when pwsh exists. Its independent baseline preserves literal argv;
  probes cover available native argument modes, module/legacy forwarding, raw
  TOML, errors and independent mutation/provenance state. The native lifecycle
  harness covers repair, source relocation, retention and optional -PriorSource
  upgrade. These scripts have not executed on this host; native PowerShell 7.0,
  7.2/current, Windows, WSL/MSYS2, interactive Ctrl-C and human visuals remain gates.

## Startup measurements

`startup-termux-0.1.11.json`: 60 fresh-process samples per command after five
warmups, alternating current and verified 0.1.10 sources on the same device.
The test suites had finished. These are working-device measurements, not a
controlled idle-host budget; no optimization or speedup is claimed. Python and
Bash are measured separately; PowerShell remains unmeasured.

| Entry | 0.1.10 p50 ms | 0.1.11 p50 ms | 0.1.11 p95 ms |
|---|---:|---:|---:|
| python-version | 79.358 | 80.959 | 114.614 |
| bash-version | 92.828 | 91.616 | 129.107 |
| python-help | 199.252 | 198.978 | 279.946 |
| bash-help | 212.237 | 216.213 | 314.041 |
| python-bare | 199.547 | 199.319 | 257.733 |
| bash-bare | 184.674 | 211.628 | 401.905 |
| python-current | 208.952 | 209.106 | 321.725 |
| bash-current | 252.855 | 249.650 | 412.879 |

The initial bare-Bash p50 increased by 26.954 ms with broad sample spread. A
focused 60-sample paired repeat measured 0.1.11 p50/p95 at 211.356/277.682 ms,
versus 0.1.10 at 213.814/283.836 ms. See
`startup-termux-0.1.11-bare-recheck.json`. The initial difference did not persist;
these results do not establish a consistent startup regression or speedup.

## Packaging and boundaries

Two builds produced byte-identical ZIP, tar.gz and SHA256SUMS. Source and both
extracted inventories verified **173 files**; outer SHA-256 sums matched. These
checks are repeated after the final evidence-only edits. The final archive also
receives an isolated installation rehearsal, reported separately at completion.
Review artifacts stay outside the checkout. No live install, profile/PATH/config changes, commits, tags, pushes
or publication were performed. Historical evidence below remains intact.

# Blastoff 0.1.10 no-argument help follow-up — 2026-10-14

Bare `blastoff`, `-h` and `--help` now produce identical full root help, exit 0
and empty stderr. Global flags without a command also show full help; explicit
`--json` retains the existing JSON welcome object. Invalid flags/values still
fail. Arguments are parsed once before application imports, so implicit help
does not initialize storage, inspect active configuration or launch tools.
Both shell frontends retain the shared core. Branding and completion bytes are
unchanged. The current 0.1.10 review identity is retained as requested.

The starting checkout passed source verification (162 files); a separate baseline
was preserved before editing. Existing tracked/untracked work and all historical
evidence below are retained. Current README, contract, UX/quickstart, manual,
changelog and implementation checklist describe the new behavior.

## Verification

Native Android 15 aarch64 / Termux; Python 3.14.6, Bash 5.3.20, Zsh 5.9.2,
Fish 4.9.3. The focused help suite passed **15 tests in 20.383 seconds**.
The full suite ran **266 tests in 214.540 seconds: 259 passed, seven skipped**:

```sh
BLASTOFF_TEST_ARCHIVE=<temporary-review-ZIP> BLASTOFF_TEST_STARSHIP=1 \
  python3 -B -m unittest discover -s tests -v
```

Evidence: `test-termux-0.1.10-help.txt`. Coverage includes exact stdout/stderr/status
equivalence, flags-only help, JSON compatibility, invalid arguments, import bounds,
no application reads/writes/subprocesses, Bash forwarding, narrow/color PTYs and
installed help after source relocation. The installed lifecycle used isolated
prefixes and a synthetic 0.0.0 prior version, not an actual historical upgrade.
Separate byte comparisons confirmed JSON welcome, version, nested help and JSON
usage errors match the preserved baseline exactly.

Bash/Zsh/Fish syntax, Python AST parsing, mandoc lint and diff-whitespace checks
passed. Groff is unavailable. Seven skips cover three fzf cases, three native
PowerShell cases and a Windows junction case. PowerShell parity cases now include
bare/flags-only/JSON help, but the harness cannot run without pwsh. Native Windows,
PowerShell and human visual acceptance remain unverified; manual acceptance remains
paused at step 5. No real install/profile/config changes or Git publication occurred.

## Startup and review artifacts

60 samples after five warmups, alternating baseline/current order, no concurrent
suite, isolated roots and redirected stdout. Command:

```sh
python3 -B scripts/benchmark.py --samples 60 \
  --only python-bare --only python-help --only bash-bare --only bash-help \
  --compare-root <preserved-source-baseline>
```

| Invocation | Before p50 / p95 ms | After p50 / p95 ms |
|---|---:|---:|
| Python, bare | 122.065 / 148.742 | 194.410 / 247.473 |
| Python, help | 196.735 / 255.180 | 193.513 / 253.660 |
| Bash, bare | 135.171 / 159.595 | 207.522 / 262.243 |
| Bash, help | 204.425 / 264.013 | 206.697 / 284.382 |

Raw evidence: `startup-termux-0.1.10-help.json`. Bare invocation now pays for full
parser/help construction, adding about 72 ms median compared with the old compact
welcome on this host; it is now comparable to explicit help. These are host-specific
samples, not PowerShell timing or a speedup claim.

Final source checksums and ZIP/TAR.GZ archives are regenerated after documentation
and evidence edits. Source/extracted inventories, outer SHA-256 sums and repeat-build
reproducibility are verified. New archives are in
`/data/data/com.termux/files/usr/tmp/blastoff-help-review-j93am4ac/artifacts/`,
separate from existing review archives; they are not installed or published.

# Blastoff 0.1.10 theme-list checkpoint — 2026-10-14

Shared theme-list formatting, available native checks, paired performance sampling
and isolated package lifecycle verification are complete. Started from checksum-
verified 0.1.9 (157 source files), preserving the full baseline outside the checkout
and retaining all pre-existing tracked/untracked work and historical evidence.

## Behavior and compatibility

Human list/theme-list/-l/--list use dim purple source prefixes, bright-white names,
and bold pink identified names/markers. Trusted provenance marks unchanged loaded
bytes [current]; edits retain [last loaded; modified]. Changed/unavailable local
sources, missing active content and unlisted origins are explicit. Unknown,
invalid or pending tracking never guesses a source from the library. Save-as keeps
last-loaded history independent from the save destination. Preset definitions are
not regenerated to check matching. Concurrent stat changes suppress a current claim.

Inspection reads the record, active config and at most one local source; it creates
no files or subprocesses. Existing preset name discovery remains. JSON retains the
same schema and skips identity inspection. Color controls, plain redirected output,
empty results and preset diagnostics remain. Source-unreadability details go to
verbose stderr without hiding choices. The shared core supplies both frontends.

Help, manual, current guides, preferences/AGENTS, decision notes and planning records
are reconciled. All three shell completion files and artwork files are byte-identical
to the preserved baseline; no CLI syntax, dependency, storage, installer ownership
or resource-layout changes were needed. Version identities are 0.1.10.

## Native verification

Host: Android 15 aarch64; Python 3.14.6, Bash 5.3.20, Zsh 5.9.2, Fish 4.9.3.
A packaged disposable copy passed **261 tests in 197.677 seconds: 254 passed,
seven skipped**. Evidence: test-termux-0.1.10.txt. Invocation:
`BLASTOFF_TEST_ARCHIVE=<0.1.10-ZIP> BLASTOFF_TEST_PRIOR_SOURCE=<preserved-0.1.9-source>
BLASTOFF_TEST_STARSHIP=1 python3 -B -m unittest discover -s tests -v`.

The 13 new tests cover local/preset identity, same-name sources, equal-content
copies, modified/save-as history, changed/deleted sources, missing/corrupt/future/
pending state, linked active paths, unsafe source links, permission diagnostics,
concurrent config/source/record/pending changes, read bounds, no writes, alias and
dry-run equivalence, JSON bypass, color roles/resets/controls and native Bash PTY.
The suite also passed existing backup safety, lifecycle, actual Bash/Zsh/Fish
completion and help checks. Native shell syntax checks, Python compilation without
bytecode, mandoc lint and diff-whitespace checks passed. Groff is unavailable.

After extending the installed check to assert both list markers following source
relocation, that test passed separately in **8.935 seconds**. Evidence:
test-termux-0.1.10-archive.txt. It exercises an actual preserved 0.1.9 upgrade,
repeat install, dry-run, installed helper/manual/completion resolution, uninstall
and user-data retention entirely in disposable paths. Runtime bytes are unchanged
from the full-suite run; subsequent edits were evidence/docs and this test extension.

The seven skips are three fzf cases, three native PowerShell cases and a Windows
junction case. PowerShell parity now includes human/plain/color/JSON listings and
modified origins in paths with spaces and Unicode, but execution remains pending.
Native Windows/PowerShell/WSL and human appearance are not certified by fixtures.

## Performance

60 samples after five warmups, alternating baseline/current order per sample, with
no concurrent suite. Python and Bash launches are measured separately. The empty
store used `scripts/benchmark.py --only python-list-human --only bash-list-human
--compare-root <preserved-0.1.9-source>`, retaining normal preset-name discovery.
Raw results: startup-termux-0.1.10-list.json.

| Human list | 0.1.9 p50 / p95 ms | 0.1.10 p50 / p95 ms |
|---|---:|---:|
| Python, empty store | 247.956 / 294.924 | 252.281 / 279.513 |
| Bash, empty store | 264.266 / 298.313 | 277.127 / 313.952 |
| Python, 1,000 themes | 270.471 / 346.083 | 291.226 / 366.219 |
| Bash, 1,000 themes | 283.323 / 362.080 | 298.528 / 387.788 |

The populated fixture used 1,000 small TOML files, a tracked theme0, isolated
storage/config, child-only empty PATH (no Starship), NO_COLOR=1 and redirected
stdout. The same alternating method ran both absolute Python and Bash entrypoints;
all fixture bytes/modes/mtimes remained unchanged. Method and raw samples:
startup-termux-0.1.10-list-populated.json. Added median latency was 4.325–20.755 ms
(about 1.7–7.7%); these are host-specific measurements, not a speedup claim or a
native PowerShell timing result. The focused read-count test establishes constant
content reads as the library grows; filename discovery still scales with the list.

## Artifacts and review gates

Final code/docs/evidence edits precede regeneration of source checksums and
reproducible ZIP/TAR.GZ review archives. The source inventory, extracted inventories,
outer SHA-256 sums and byte-for-byte reproducibility are verified at packaging.
Artifacts: ../blastoff-rebuild-0.1.10.zip, ../blastoff-rebuild-0.1.10.tar.gz and
../blastoff-rebuild-0.1.10.SHA256SUMS. These are local review builds, not published.

Use the read-only source preview in TERMINAL-UX.md to review contrast and markers.
Manual acceptance remains paused at step 5 (backup deletion); earlier passes and
installation are not inferred. No live installation, configuration, profile or
backup-data changes, commit, tag or publication were performed. The checkpoints
below preserve their original evidence.

# Blastoff 0.1.9 readability checkpoint — 2026-10-14

Shared-core formatting, available native validation, performance checks and
review archive verification are complete.
Source began at verified 0.1.8 (153 inventory files), with 53 modified tracked
files and 44 untracked status entries. A complete source baseline was preserved
outside the checkout; existing work and historical records remain intact.

## Change and compatibility

Backup records have complete bright-white IDs, purple labels, bright-pink values,
dim neutral separators, blank record separators and two-space metadata indentation.
Size moves to its own line when the unstyled Kind/Size row does not fit. Source,
Reason, missing-file notices, sorted ordering, counts, errors and statuses remain.
Recognized ID timestamps are explicitly UTC (the writer uses gmtime); unknown
values stay unknown. Exact byte sizes reuse inspection data. Shared token output
sanitizes text before trusted ANSI; App.status and ordinary emit callers retain
their existing appearance. JSON bypasses human formatting and retains its schema.

Updated AGENTS/preferences, output contract, UX/quickstart/README, manual examples,
interactive checks, plans, changelog and current release/path identities. Help
syntax and all completion definitions are unchanged and verified. No new resources,
dependencies, installer rules or data migrations are required. Runtime identities
are 0.1.9; installing is a separate user action, not a side effect of source edits.

## Native verification

Host: Android 15 aarch64, Python 3.14.6, Bash 5.3.20, Zsh 5.9.2, Fish 4.9.3.
Final suite in a packaged disposable source: **248 tests in 132.665 seconds;
241 passed, seven skipped**. Log: test-termux-0.1.9.txt. Invocation:
`BLASTOFF_TEST_ARCHIVE=<0.1.9-ZIP> BLASTOFF_TEST_PRIOR_SOURCE=<preserved-0.1.8-source>
BLASTOFF_TEST_STARSHIP=1 python3 -B -m unittest discover -s tests -v`.

Nine focused output tests passed, including a real native Bash PTY, exact role
colors/resets and ANSI-stripped equivalence, automatic TTY/redirect, forced color,
NO_COLOR, complete 96-character IDs, record ordering/spacing, precise width
boundaries, very narrow screens, leap/invalid dates under different TZ settings,
missing/malformed entries, exact sizes, unchanged JSON and fixture snapshots.
Human/JSON paths use equal metadata-read/regular-file inspection counts; listing
starts no presentation subprocesses. Source/Reason control text cannot inject ANSI.

The suite also passed actual Bash/Zsh/Fish completion and help checks, backup/data
safety regressions, a real 0.1.8 to 0.1.9 isolated upgrade, installed helpers after
source relocation and uninstall retention. Bash/Zsh/Fish syntax, mandoc lint,
Python compilation without bytecode and diff-whitespace checks passed. Branding
and completion bytes match the preserved baseline.

The seven skips are three fzf cases, three PowerShell engine/session/lifecycle
cases and one Windows-junction case. The populated PowerShell parity harness now
compares human/JSON listings at 80 and 24 columns, but native execution is pending.
Groff is unavailable; mandoc was used. Human appearance is not certified by PTYs.

## Performance

60 samples after five warmups, alternating baseline/current order each sample;
no concurrent test suite. `scripts/benchmark.py --only python-backup-list-human
--only bash-backup-list-human --compare-root <preserved-0.1.8-source>` used isolated
empty storage and redirected output. Raw results: startup-termux-0.1.9-backup-list.json.

| Entry | 0.1.8 p50 / p95 ms | 0.1.9 p50 / p95 ms |
|---|---:|---:|
| Python | 160.884 / 169.692 | 161.859 / 169.609 |
| Bash | 168.813 / 175.333 | 170.664 / 177.093 |

These empty-list medians differ by about 0.6% and 1.1%; they are host-specific
startup observations, not a general performance guarantee.
A separate Python-entry comparison used 20 disposable backups of 6,056 bytes each,
valid UTC IDs and Source/Reason metadata, width 80 and forced color (NO_COLOR removed
only in the child environment). It also alternated order for 60 samples after five
warmups, with no competing tests. Baseline p50/p95: **243.976/279.065 ms**; current:
**247.723/270.157 ms**. Median increased 1.5% (3.747 ms); p95 decreased 8.908 ms.
The fixture bytes/modes/mtimes remained unchanged. Raw method/results are in
startup-termux-0.1.9-backup-populated.json. No native PowerShell timing is claimed.

## Review artifacts and remaining gates

Version identities are aligned at 0.1.9. Source checksums, ZIP/TAR.GZ extracted
inventories and outer SHA-256 sums verified; archives reproduce byte-for-byte.
The final archive-based install/actual-0.1.8-upgrade/source-relocation/uninstall
check passed separately: one test in 5.032 seconds, recorded in
test-termux-0.1.9-archive.txt. It ran only in disposable roots. Final evidence
bookkeeping is followed by checksum/archive regeneration and verification;
runtime/test bytes match the source that passed the full suite.

Local review artifacts: ../blastoff-rebuild-0.1.9.zip,
../blastoff-rebuild-0.1.9.tar.gz and ../blastoff-rebuild-0.1.9.SHA256SUMS.
These are local review builds, not a tag or published release.

Manual acceptance remains paused at step 5; earlier steps and a live review
installation are not assumed passed. Use the read-only source-preview command in
TERMINAL-UX.md, including --color never and resizing. Native PowerShell/Windows/WSL,
fzf and human visual gates remain separate and pending where unavailable.
No live installation, configuration, profile or backup changes, commit, tag or
publication were performed. The checkpoints below retain their original evidence.

# Blastoff 0.1.8 review follow-up — 2026-10-13

Implementation, available native validation and review archives are complete.
Manual acceptance remains paused at **step 5, backup deletion**. Steps 1–4 and
installation of a review build are not assumed passed. No live installation,
profile/config changes, commit, tag or publication was performed.

## Implemented and reconciled

- Fancy Unicode is the shared default for theme, module and backup browsers;
  --fzf requests basic user presentation. Preserve ASCII, Ctrl-X, responsive source
  previews, safe selection/cancellation and frozen backup deletion scope.
- Correct fzf hex-color option parsing and retain reviewed environment/file
  customization. Bat now retains normal configuration, theme overrides and custom
  cache discovery. Fixture and real-tool-configuration appearance checks are
  distinct; no prompt rendering/theme command execution is introduced.
- Human output is explicit across commands, including compact backup metadata.
  JSON remains opt-in with unchanged schemas; diagnostics use stderr, raw content
  stays raw, and redirected human output does not become JSON.
- PowerShell 7+ uses the shared core, a private argv envelope and deferred native
  tool discovery. Import/static completion starts no external tools. Dynamic
  completion is bounded/cached; Unix hosts lacking UnixMode use a private bounded
  Python filename helper. No PowerShell 5.1 or native Windows test claim is made.
- Root install.ps1/uninstall.ps1 provide WhatIf/DryRun/Verbose, CurrentUser module
  discovery, exact profile plans, backups, immutable versions and independent
  ownership. Both lifecycle frontends share transaction/preflight helpers.
- Reconciled AGENTS/preferences/pi workflows, README/quickstart, contracts,
  installation/migration/recovery, platform/parity/interactive/troubleshooting
  guides, decisions, plans, help, four completions, manual, changelog and identities.
  Historical records are retained; SOURCE-AUDIT links to the current inventory.

Work began on main at 74414be with **49 modified tracked and 19 untracked files**,
source 0.1.7 and a verified 128-file inventory. A complete baseline was preserved
outside the checkout. The then-PATH launcher reported 0.1.6; no live upgrade was
performed. Existing work, .local references and branding/artwork bytes remain.

Confirmed application defects were bat configuration suppression, the fzf lexer's
handling of embedded # color values, and the shared emitter's implicit JSON
fallback. Separately, the old HOME/XDG test isolation could hide user tool settings
and theme caches; NO_COLOR and installed/source identity affect appearance too.
Native fzf is absent here, so its version-specific behavior and the user's actual
palette remain unverified. See TERMINAL-UX.md for fixture versus user-mode checks.

## Native evidence

Host: Android 15 aarch64, Python 3.14.6, Bash 5.3.20, Zsh 5.9.2, Fish 4.9.3,
Starship 1.26.0 and bat 0.26.1. Gum/mandoc are available; fzf/pwsh/groff are absent.

Final suite in a refreshed packaged disposable source copy: **242 tests in
153.643 seconds: 235 passed, seven skipped**. Full output: test-termux-0.1.8.txt.
Command: `BLASTOFF_TEST_ARCHIVE=<0.1.8-ZIP>
BLASTOFF_TEST_PRIOR_SOURCE=<preserved-0.1.7-source> BLASTOFF_TEST_STARSHIP=1
python3 -B -m unittest discover -s tests -v`.

Passed real 0.1.7 to 0.1.8 isolated shell-prefix upgrade, installed helper/runtime
resolution after source relocation, three native completions, uninstall retention,
CurrentUser backend clean/repeat/upgrade/repair/conflict/uninstall and frontend
coexistence. The latter tests execute Python on Termux, not native PowerShell.
Safety cases include cancellation/default No, malformed state, concurrent edits,
locks, symlink hazards, spaces/Unicode, missing tools, clean JSON/stderr, no-write
dry-run snapshots, profile encoding/content retention and modified ownership.
Skipped: three fzf cases, PowerShell completion plus two native-session/lifecycle
adapter cases, and one Windows-junction case. Real Starship preset generation and
native bat fixture checks ran; no live prompt/custom theme commands were executed.

Available shell syntax, Python source compilation without bytecode, mandoc lint
and diff-whitespace checks passed. Native Bash/Zsh/Fish completion behavior and
native bat custom config/cache fixtures are exercised by the suite; fixtures never
rebuild user caches or change live data. Native PowerShell/session/lifecycle tests
are implemented but skipped here, not claimed as execution evidence.

An initial final-validation run found an outdated minimal packaging fixture that
omitted the new required PowerShell payload. Its 242-test result (one failure,
seven skips) is preserved in test-termux-0.1.8-initial.txt. The fixture was corrected;
all seven focused packaging tests then passed. This was not an installer failure.

## Performance evidence

Each ordinary case used 60 samples after five warmups with isolated empty roots,
NO_COLOR and redirected output, without a concurrent test suite. Preserve the
initial sequential before/after measurements in startup-termux-0.1.8-before.json
and startup-termux-0.1.8-after.json. Device timings varied substantially, so the
follow-up alternated current/baseline and reversed order each sample using
`scripts/benchmark.py --compare-root <preserved-0.1.7-source>`.
Raw results: startup-termux-0.1.8-paired.json.

| Command | 0.1.7 p50 / p95 ms | 0.1.8 p50 / p95 ms |
|---|---:|---:|
| python-version | 105.643 / 185.133 | 110.504 / 298.246 |
| python-help | 222.653 / 465.358 | 230.684 / 509.652 |
| python-current | 298.294 / 540.447 | 297.716 / 561.375 |
| python-module-list | 287.270 / 380.806 | 295.716 / 394.453 |
| bash-version | 115.199 / 129.532 | 114.144 / 128.703 |
| bash-help | 271.424 / 348.479 | 272.497 / 342.697 |
| bash-current | 258.859 / 310.830 | 256.892 / 323.303 |
| bash-module-list | 246.365 / 303.592 | 244.592 / 303.478 |
| python-backup-list-human | 298.552 / 376.763 | 295.972 / 358.172 |
| bash-backup-list-human | 249.620 / 292.931 | 255.696 / 289.685 |

Backup-list timings compare the old JSON default with the new human default and
therefore are not identical-format workloads. Common medians in the paired run
remained within 5%; tail samples were noisy. Python-version p95 initially rose to
298.246 ms from 185.133 ms. A focused, noncompeting 120-sample alternating recheck
(`--only python-version --samples 120`) measured **61.956 / 76.725 ms** current
versus **63.066 / 76.205 ms** baseline, recorded in
startup-termux-0.1.8-version-recheck.json. The tail spike did not reproduce; this
supports host/scheduling variability as an explanation, not a universal speed claim.

The 1,000-theme feature run (60 samples/five warmups, separate from tests) is in
startup-termux-0.1.8-features.json. Picker option parsing p50/p95: 0.152/0.183 ms;
first plain in-process preview: 43.619/50.051 ms; cached preview: 0.098/0.104 ms.
Python save dry-run: 249.094/404.330 ms; Bash: 301.099/457.976 ms. The fixture
snapshot remained unchanged. Native bat startup is covered functionally, not by
these plain-preview measurements. PowerShell import, fresh-process startup,
first-command and completion timings remain **unmeasured** here; the separate
benchmark-powershell.ps1 harness includes empty/1,000/10,000-name libraries.

## Packaging and remaining gates

Version identities are 0.1.8 throughout the core, manifest, manual and changelog.
The source inventory/checksums, ZIP and TAR.GZ archives and outer SHA-256 sums
were regenerated after code/documentation edits and verified after extraction.
Both archives reproduce byte-for-byte. Final evidence bookkeeping is followed by
another regeneration and verification; no source edits are left outside checksums.

The archive-based isolated shell install/actual-0.1.7-upgrade/uninstall check also
passed separately (one test, 9.994 seconds; test-termux-0.1.8-archive.txt). An
extracted archive's CurrentUser Python backend passed verified no-write planning,
install, installed-core invocation, source relocation and installed-backend
uninstall with profile/config retention. This is native Termux Python evidence,
not execution of the PowerShell adapters. Final runtime/test bytes match the
passed full-suite source; later edits only record results and inventories.

Review artifacts are `../blastoff-rebuild-0.1.8.zip`,
`../blastoff-rebuild-0.1.8.tar.gz` and `../blastoff-rebuild-0.1.8.SHA256SUMS`.
They are local review archives, not a tag or published release.

- Native fzf configuration/version behavior, connected borders, Ctrl-X/resizing,
  backup multiselection and actual user bat/fzf appearance remain pending.
- Native Windows PowerShell, Linux PowerShell and WSL execution/version ranges,
  profile discovery/encoding/ACL/reparse/locking behavior, GUI editor waiting,
  cancellation and fresh-session completion/performance remain distinct gates.
- Human visual acceptance remains pending. Follow INTERACTIVE-CHECKS.md from
  step 5 after recording source/installed identity; earlier steps keep their own
  evidence. No rendered prompt preview is implemented or claimed.

The following 0.1.7 and older checkpoints are historical. Their basic-default,
bat-isolation and prior support descriptions are superseded by CLI-CONTRACT.md,
POWERSHELL.md and decision 0003. Their original test records remain unchanged.

# Blastoff 0.1.7 checkpoint — 2026-10-13

## Implemented scope

The 0.1.7 review build implements shared verbose/dry-run, safe backup deletion,
staged active-theme editing, independent provenance and interactive save,
basic/fancy fzf presentation with Ctrl-X source previews, and stored module
viewing. Bash and PowerShell continue forwarding to one Python 3.11+ standard-
library core. No new runtime dependencies or storage migrations were introduced.
Reference/logo assets, storage paths, root install/uninstall interface and owned-
file/data-retention protections remain intact.

The version-1 tracking record separates last-loaded history from a save destination.
Pending markers prevent incomplete operations authorizing implicit overwrites.
Content/state publication is not a multi-file crash transaction; failed editor
work is retained at a reported path. See CLI-CONTRACT.md, RECOVERY.md and decision
0002 for the precise failure and concurrent-change contract.

Updated README/quickstart, CLI/help/manual, all four completions, installation/
upgrade/uninstall/migration guidance, recovery, interactive/Windows checks,
architecture, preferences, agent/pi workflow instructions, implementation plan,
changelog and release identities. Old results below and old audit/benchmark logs
remain historical. This section supersedes older exact-match-only identification,
required save-name, default styled picker, Alt-P/hidden-preview and blanket fzf
option-isolation descriptions. Rendered prompt previews are deliberately excluded;
only sanitized source is shown and no theme-defined commands are executed.

## Native evidence

Host: Android 15 aarch64, Python 3.14.6, Bash 5.3.20, Zsh 5.9.2, Fish 4.9.3,
Starship 1.26.0, bat 0.26.1 and Neovim 0.12.6. Gum and mandoc are available;
fzf, pwsh and groff are absent.

- Final runtime/tests in a packaged disposable source copy: **221 tests in
  108.066 seconds: 216 passed, 5 skipped**. Command: `BLASTOFF_TEST_ARCHIVE=<ZIP>
  BLASTOFF_TEST_PRIOR_SOURCE=<actual preserved 0.1.6 source>
  BLASTOFF_TEST_STARSHIP=1 python3 -B -m unittest discover -s tests -v`.
  Full output: `test-termux-0.1.7.txt`. Runtime/scripts/tests match the working tree;
  evidence/documentation bookkeeping follows the test run before final packaging.
- Passed cancellation/default-No and case variants, alias/literal scope, frozen
  all-selection, missing/malformed/linked backup members, simulated active-file
  identity alias, partial unlink failure, editor invalid/failure/interruption and
  atomic-save recovery, concurrent config/destination/tracking changes, missing
  tools, paths with spaces, noninteractive gates and dry-run snapshots including
  directory/file modes, mtimes, bytes and provenance. Termux Python lacks os.link;
  the new backup identity test simulates identity, not a native hardlink operation.
- Passed actual Bash/Zsh/Fish completion behavior, shell PTYs and safe fallback
  picking; source/helper subprocess quoting and session cache tests; native bat
  color/plain/no-pager handling and a real headless Neovim edit in an isolated PTY.
  All real Starship presets were generated/applied in temporary roots without
  rendering prompts. PowerShell completion source guards pass; engine is skipped.
- Isolated actual 0.1.6 to 0.1.7 upgrade passed. Installed commands, preview helpers,
  provenance, module display, backup deletion, three native completions and manual
  work after source relocation. Uninstall preserves config, linked storage, themes,
  modules, backups, provenance and unrelated files. Public lifecycle planning,
  dry-run, immutable runtime, ownership/conflict and recovery tests also pass.
- Python source compilation without bytecode writes, individual Bash syntax checks
  (entry point, legacy/public lifecycle wrappers and completion), Zsh/Fish syntax,
  `mandoc -Tlint man/blastoff.1` and `git diff --check` passed. Groff is unavailable.
- Initial validation exposed old backup-list error-schema assertions and a logo
  fixture inheriting TERM=dumb. Assertions now cover per-entry errors/stderr and
  the logo fixture specifies a Unicode terminal. All final checks above passed.

## Performance evidence

Ran the preserved 0.1.6 benchmark, then current `scripts/benchmark.py`, sequentially
without a competing test suite. Each command has 60 samples after 5 warmups,
isolated empty roots, NO_COLOR and redirected output. PowerShell is unavailable.
Raw host/results: `startup-termux-0.1.7-before.json` and
`startup-termux-0.1.7-after.json`.

| Entry/command | 0.1.6 p50 / p95 ms | 0.1.7 p50 / p95 ms |
|---|---:|---:|
| python-version | 53.825 / 58.504 | 51.330 / 54.362 |
| python-help | 130.774 / 152.209 | 132.603 / 164.424 |
| python-current | 152.880 / 187.723 | 157.388 / 188.450 |
| python-module-list | 153.861 / 200.783 | 152.507 / 168.134 |
| bash-version | 64.142 / 67.747 | 64.375 / 67.333 |
| bash-help | 139.950 / 177.231 | 143.322 / 177.338 |
| bash-current | 162.611 / 200.785 | 167.448 / 194.518 |
| bash-module-list | 162.417 / 202.435 | 163.859 / 203.888 |

Common-command median regressions stayed within 3% in this run; these are single-
host observations, not a general speedup or strict latency guarantee. The separate
`--features` run uses 1,000 background local themes plus the tracked save target:
Python save dry-run p50/p95 173.460/218.397 ms, Bash 180.888/227.220 ms; module show
Python 162.435/194.944 ms, Bash 171.995/220.325 ms. All fixture bytes were unchanged.
See `startup-termux-0.1.7-features.json`. A focused save test rejects any library
scan. Existing explicit current matching retains its compatibility scan; ordinary
provenance/save work reads only named files. Shared helpers load once per process,
and previews generate/cache visited presets on demand with bounded output/cache.

## Final packaging and remaining gates

All **128 source files** verify against the regenerated CHECKSUMS.json. ZIP,
tar.gz and outer SHA-256 sums reproduce byte-for-byte in a second temporary output
directory; both extracted archives pass verify.py. Final artifacts are
`../blastoff-rebuild-0.1.7.{zip,tar.gz,SHA256SUMS}`. The separate final-archive
installed lifecycle test passes using the actual 0.1.6 source. Public install and
uninstall --dry-run --verbose pass with isolated HOME/PATH/prefix and create no
HOME/prefix files. Runtime/scripts/tests/completion bytes match the full-suite
validation copy. This final evidence/checklist edit is followed by package
regeneration and the same source/archive/reproducibility checks.

The documentation consistency review covers command grammar, aliases, defaults,
confirmation authority, editor rules, dry-run/verbose streams, keybindings, version
identities, support claims and completion contexts. Final documentation contract
checks and manual/shell syntax checks pass. No rendered-prompt implementation or
human/native-Windows verification is claimed.

Native Windows/PowerShell execution remains deferred. Three native fzf tests,
one PowerShell engine test and one Windows junction test were skipped. Fzf basic/
fancy selection, multi-selection, preview resizing/Ctrl-X and actual inherited
option compatibility still need a real installed fzf; fixture/static tests do not
certify that executable. Human Unicode/ASCII appearance, touch keyboard, GUI-editor
waiting and shell-plugin integration remain unverified. Use INTERACTIVE-CHECKS.md
and WINDOWS-CHECKS.md for those gates. No new native Linux gate was run here.

Work remains uncommitted on main, based on 74414be. No live install, profile/PATH,
active config or user storage changes, dependency installation, commit, tag, push
or publication were performed. All mutation/lifecycle tests used temporary roots.

---

Historical checkpoints below retain their original results and versions.

# Blastoff rebuild checkpoint — 2026-10-01

## Implemented

0.1.6 review build with one Python 3.11+ standard-library core, Bash entry point
and PowerShell 7+ module. Includes requested storage/config paths, read-only
local/preset listing, theme apply/save/copy/import/delete, backups/restore, module
save/load/delete, explicit legacy copying, optional picker, JSON/color, static
Bash/Zsh/Fish completions, offline PowerShell completion on module import,
manpage, versioned install/uninstall and checksums.

Planning bundle includes preference guide with evidence distinctions, AGENTS,
command contract, source audit, architecture decision, implementation plan,
pi setup guide, four pi workflow skills and four prompt templates. The moved
working tree is now audited; see `TERMUX-AUDIT.md` for renamed references and
missing package images. Existing `.local/src` and `.local/logo` files were left
untouched. No live config, real-prefix installation, shell profile or PATH was
changed. No commit, push, tag or publication was performed.

## Linked dotfiles storage — 0.1.6

Storage-root links now resolve once to a canonical directory before deriving
storage children or locks. Relative/chained links and linked ancestors work;
links must target existing directories. Ordinary missing storage paths remain
non-mutating until a write. Unknown Windows reparse types, broken links, loops
and non-directory targets fail. Linked storage children/leaf files and active
config/installer/profile protections remain unchanged. Root aliases share locks;
retargeting an alias does not redirect an already-resolved invocation.

Doctor/results/new stored-backup metadata use canonical storage paths with
unchanged JSON keys. Offline shell completion accepts root links while retaining
child/file exclusions. PowerShell checks bounded root aliases and retains remote
root exclusions. No dependency or wrapper argument/exit contract changed.

The original root-refusal regression failed before the fix with the user's exact
error. Initial focused evidence: 12 storage tests passed; all 37 core/lifecycle
tests passed after reviewed checksum rebuilding. The new native Bash/Zsh/Fish
completion test initially exposed their separate root-link exclusions; after
correction it passed all nine shell/context cases. Seven PowerShell checks ran:
six static checks passed, engine execution skipped because pwsh is unavailable.
Review also found strict resolution skipped Windows root-only targets; a fixture
now covers both accepted link tags and existing/missing extended drive/UNC roots.
These are path-grammar fixtures, not native Windows evidence. A native Windows
junction mutation/lock test is included but cannot run on this host.

A first full run had 170 tests: 166 passed, 3 skipped, and one host-dependent
manual lookup failure. Investigation showed the managed MANPATH was correct,
but native mandoc preferred the already-installed indexed page over the temporary
unindexed page when its default search path was included. The fixture now asserts
the exact exported MANPATH and removes only its trailing default expansion for
the isolated lookup; that focused rerun passed. Installer behavior is unchanged.
Bare mandoc priority with multiple installations remains a host limitation; use
`MANPATH=/absolute/prefix/share/man man blastoff` to select a custom prefix.

Deletion now compares file identity, not resolved path spelling, to protect an
active config reached through Windows extended-path/junction aliases (and hard
links). An isolated simulated-spelling regression failed before this correction
and passed afterward; the native Windows fixture also checks this protection.

Final native Termux evidence (Android 15 aarch64, Python 3.14.6):

- Fresh temporary 0.1.6 ZIP plus `BLASTOFF_TEST_ARCHIVE="$temporary/blastoff-rebuild-0.1.6.zip"
  python3 -B -m unittest discover -s tests -v`: **171 tests in 113.021 s,
  168 passed, 3 skipped**. Skips: opt-in real Starship, unavailable PowerShell
  engine, and native Windows junction fixture. Installed-package upgrade,
  source-independent linked-storage operations/completions and uninstall data/link
  retention passed. No native Windows claim is made.
- `bash -n bin/blastoff scripts/install.sh completions/blastoff.bash install.sh
  uninstall.sh`, `zsh -n completions/blastoff.zsh`, `fish -n
  completions/blastoff.fish`, `mandoc -Tlint man/blastoff.1` and `git diff --check`
  passed. Groff is unavailable; mandoc supplies native manual checks.
- Configured Ruff diagnostics report warnings, not errors (including a nested
  test context-manager style warning). The optional ty server is unavailable;
  install it or update its command in `pi-lsp.json` before claiming type coverage.
- Read-only `bash bin/blastoff doctor --json` reported 0.1.6 and the user's real
  storage root `/data/data/com.termux/files/home/dots/config/blastoff`.
- `python3 -B scripts/benchmark.py`: 60 samples plus 5 warmups per command,
  isolated empty roots, redirected output, NO_COLOR. Full host/results are in
  `startup-termux-storage-links.json`. Python p50/p95 milliseconds: version
  79.720/84.185, help 187.244/218.978, current 214.052/243.330, module-list
  216.035/259.491. Bash: version 94.801/109.623, help 201.286/271.412, current
  229.075/270.129, module-list 231.259/269.812. PowerShell unavailable. These are
  host measurements, not an idle before/after speedup claim.

Release verification: all **109 source files** and both extracted 0.1.6 archives
passed `scripts/verify.py`; outer SHA-256 sums matched. ZIP, tar.gz and sums
reproduced byte-for-byte in a second output directory. Isolated public
install/uninstall dry-runs passed without creating a prefix or HOME state.
Artifacts are `../blastoff-rebuild-0.1.6.{zip,tar.gz,SHA256SUMS}`; final checkpoint
edits are rebuilt and reverified with the same checks. No live installation,
config/storage/profile edit, commit or publication is part of this change.

## Supplied gradient header and readable status — 0.1.5

Welcome and root/nested help now render `lib/artwork/logo` unchanged: 37 columns,
13 rows of Braille artwork, with the existing left-to-right purple-to-pink gradient.
NO_COLOR retains fitting artwork without color. Narrow, non-Unicode, dumb and
redirected output retain the ASCII fallback. Optional reads remain bounded,
regular-file-only and character-validated; no original ANSI artwork is replayed.
Old reference assets are not used as runtime headers or modified by this change.

`current` (including bare `-t`/`--theme`) and `doctor` now default to labeled human
output with purple titles and pink labels, without repeating the large logo.
Current preserves local byte-match semantics, including multiple matches and
missing/unmatched config cases. Doctor reports paths/presence/tool availability,
not TOML validity or successful tool execution. Both remain read-only, do not
launch discovered tools, honor NO_COLOR/redirection and escape terminal controls
in human path values. Explicit `--json` keeps the existing schemas and exact paths.
Version 0.1.5 permits an upgrade without rewriting older immutable runtimes.

Native Termux evidence (Python 3.14.6, aarch64; no native Windows or PowerShell):

- `test_current.py`: 12 passed in 5.348 s; default human/explicit JSON, aliases,
  exact schemas, missing/multiple matches, symlinks, control escaping, color policy,
  native PTY/Bash parity, no config reads/tool launches for doctor and no writes.
- Fresh temporary 0.1.5 ZIP plus `python3 -B -m unittest discover -s tests -v`:
  **154 tests in 82.680 s: 152 passed, 2 skipped**. Includes gradient/header safety,
  installed artwork after source removal, lifecycle/migration/discovery regression
  coverage, and unchanged data-safety checks. Real-Starship opt-in and unavailable
  PowerShell execution were skipped; Windows remains explicitly deferred.
- Bash wrappers/completion, Zsh and Fish syntax checks passed. Manual lint initially
  caught one overlong input line; wrapping it yielded clean `mandoc -Tlint`.
  `git diff --check` passed. Ruff diagnostics contained warnings, not errors;
  no new type-check or native Windows claim is made.
- Source inventory review found added `lib/artwork/logo`, `tests/test_current.py`
  and a reference `.local/logo/logo`, plus an independently edited reference
  `.local/logo/blastoff.txt`. The two reference files are identical logo text with
  trailing whitespace/control data; they are preserved verbatim as archival
  references, never selected or executed by the runtime. Packaging boundaries
  remain unchanged; task logs, bytecode and build output stay excluded.

Final documentation/manual changes are followed by the existing build workflow,
source/archive/outer-checksum verification and public install/uninstall dry-runs.
No live installation, configuration/profile edit, commit or publication is made.
Human font/gradient appearance and native Windows remain separate unverified gates.

## Battery-style public lifecycle — 0.1.4

Implemented root `install.sh` / `uninstall.sh` wrappers: normal execution needs
neither an action word nor `--yes`; `--dry-run` is read-only and `--prefix` wins.
Native Termux defaults to `$PREFIX`, other POSIX hosts to `~/.local`, and Windows
to LOCALAPPDATA/Programs/Blastoff (or `~/.local`). Legacy entry points retain their
explicit-approval/manual-integration compatibility. Runtime identity is 0.1.4;
versioned storage and ownership remain internal implementation details.

The driver now inspects and plans before applying changes. It installs runtime,
artwork, command, completions and manual together; conditionally manages owned
integration only when discovery needs it. Linked profiles and their targets are
preserved. Normal Termux discovery does not need profile edits. This native Zsh's
compiled fpath omits site-functions, so the canonical completion is accompanied
by an owned copy in `share/zsh/functions/Completion/Unix/_blastoff`. Fish vendor
and Bash framework paths were inspected with isolated native shell probes.
Bash frameworks supporting command-relative completion use that automatic path.

Public installation plans migration of the verified `~/.local` installation to
a different selected prefix. Target ownership commits before old verified files
are retired; pending cleanup is recorded and retryable. Modified/unrelated files
and unsafe paths cause refusal. Newer installed versions are not downgraded;
repeat install reuses immutable runtime and restores missing owned support files.
Uninstall preserves user data and unrelated profile text. Profile recovery backups
remain after uninstall; reinstall chooses a fresh backup name rather than adopting
or overwriting an unowned retained backup. This is not a crash-atomic transaction.

Safety review findings were reproduced as failing unit tests before correction:
retrying an integrated migration, transferring retained completion ownership, and
install/uninstall/reinstall with retained profile backups. All three regressions
now pass. No runtime/profile/config live installation was performed. Inspection
found installed 0.1.3 under `~/.local`; unlike older observations, the Dots legacy
`~/dots/scripts/blastoff` pathname is absent. Nothing was committed or published.

Native Termux verification:

- `bash install.sh --dry-run`: exit 0; VERSION 0.1.4, PREFIX
  `/data/data/com.termux/files/usr`, CURRENT 0.1.3 in `~/.local`. The plan identifies
  the shadowing owned `~/.local/bin/blastoff`, runtime/support migration and the
  native Zsh discovery copy. No profile edits are planned. Ends with
  `DONE preview complete; no files changed`.
- `python3 -B -m unittest discover -s tests -p test_lifecycle_planning.py -v`:
  11 passed (4.005 s); default-prefix branches, newer-version skip, concurrent
  edits, target rollback, resumable cleanup, linked/owned integration boundaries,
  BOM/CRLF preservation and actual Zsh compinit discovery in a temporary
  projection of its native autoload directory.
- `python3 -B -m unittest discover -s tests -p test_installer_public.py -v`:
  14 passed (19.208 s); isolated public wrappers, dry-run snapshots, repeat repair,
  source-independent installed runtime, format-1 migration, conflict refusals,
  preservation and actual fresh Bash/Zsh/Fish command/completion discovery plus
  native man lookup. These shells used temporary HOME/XDG/ZDOTDIR/prefix roots,
  never real profiles. No live `$PREFIX` install was used as test evidence.
- Packaging/wrapper diagnostics: 7 tests passed (1.088 s), including archive
  contents/modes, exclusions, exact argv/streams/status and actionable integrity
  errors. The explicit inventory now contains 104 source files.
- Full suite using a freshly built temporary ZIP:
  `BLASTOFF_TEST_ARCHIVE="$temporary/blastoff-rebuild-0.1.4.zip" python3 -B -m
  unittest discover -s tests -v`: 140 tests in 88.662 s, **138 passed, 2 skipped**.
  The installed-package upgrade/uninstall rehearsal passed. Real-Starship opt-in
  and unavailable PowerShell engine checks were skipped. Native Windows remains
  deferred; platform-branch fixtures are not native Windows certification.
- Separate Bash wrapper/completion syntax checks, Zsh/Fish completion syntax and
  `git diff --check` passed. A single manual overlong-line warning was wrapped
  after the suite; final packaging repeats manual lint and source verification.
  Ruff reported warnings, not errors; optional `ty` remains unavailable (install
  it or update the configured command before claiming type-check coverage).

Final packages are rebuilt through `bash scripts/build.sh` after documentation
edits. Source/ZIP/tar.gz inventories, outer SHA256SUMS and repeat-build identity
are checked before handoff. Integrity is never auto-refreshed by installation;
errors distinguish reviewed development rebuilding from restoring unknown source
changes. Old release artifacts and original reference assets are not overwritten.

## Installation inventory repair — 0.1.3

The exact `bash scripts/install.sh install --dry-run` initially failed the
source-inventory check. The previous manifest listed 97 files; the reviewed
source boundary found 99. Added: `scripts/integration.py` and
`tests/test_powershell_completion.py`. Missing: none. The existing
`powershell/blastoff.psm1` also had an intentionally changed checksum.

Both new files belong in the existing source allowlist. The packaging boundary
was not widened: `.pi/tasks`, sessions, bytecode, top-level build output and
private/ambient files remain excluded. `.local/src` and `.local/logo` remain
explicit reference-only inclusions, not installed assets. Added fixture cases
to the existing packaging test cover installer/integration/PowerShell files and
private/build exclusions. The integration planner is included but is not yet
called by `scripts/install.py`; no profile-management feature is activated.

After rebuilding the reviewed manifest, the same dry-run exposed a second
blocker: the changed PowerShell module could not overwrite the already-installed
immutable 0.1.2 payload. Bumped VERSION/core/PowerShell manifest/manual and current
installation examples to 0.1.3 instead. Source verification and immutable-version
checks are unchanged. No installed file, live profile/PATH or config was modified;
all actual install/upgrade/uninstall testing used disposable fixture roots.

Native Termux evidence:

- `python3 -B scripts/package.py --output-dir "$temporary"` then
  `python3 -B scripts/verify.py`: 99 source files verified.
- `bash scripts/install.sh install --dry-run`: exit 0, proposes 0.1.3 under
  `/data/data/com.termux/files/home/.local`, prints the versioned PowerShell import
  path and preservation notice; performs no installation.
- `BLASTOFF_TEST_ARCHIVE="$temporary/blastoff-rebuild-0.1.3.zip" python3 -B -m
  unittest discover -s tests -v`: 110 tests in 61.564 s, 108 passed, 2 skipped.
  Includes the actual temporary installed-package upgrade/uninstall rehearsal,
  inventory exclusions, ownership/tamper checks, version consistency and five
  static PowerShell completion checks. Real-Starship opt-in and the unavailable
  PowerShell engine test were skipped; no native Windows verification is implied.
- Separate Bash syntax checks for launcher/installer/completion, Zsh/Fish
  completion syntax checks and `mandoc -Tlint man/blastoff.1`: exit 0.
  Ruff reports one pre-existing import-order warning in `tests/test_packaging.py`;
  the optional `ty` server remains unavailable.

The rebuilt 0.1.2 archives from the initial inventory-only repair are superseded
by 0.1.3; they are not an upgrade path for the installed immutable 0.1.2 payload.
Final deliverables use `blastoff-rebuild-0.1.3.{zip,tar.gz,SHA256SUMS}` in the
repository's parent directory. No release was tagged, published or installed.

## Shared branded help — 0.1.2

The user reports installed 0.1.1 welcome works but help was still plain argparse.
This slice shares one branded header across welcome, -h, --help and nested help.
It uses verbatim copies of the original 60-column compact / 96-column wide text
wordmarks when terminal width/encoding permit; narrow, redirected, dumb or
non-Unicode output falls back to ASCII. Original scripts, text, ANSI and image
assets are untouched. Cursor-controlling original ANSI assets are never replayed.
Optional runtime artwork is regular-file-only, bounded, validated block text;
missing, malformed or unsafe files fall back rather than breaking help.

Help colors headings and command/option names, keeps descriptions plain, and
groups commands by task without duplicated brace-enclosed lists. The complete
parser grammar (options, descriptions, aliases and subcommands) is now in the
lightweight shared `lib/cli.py`; application/safety logic remains in the core.
Help exits before importing subprocess/TOML/hash/application modules; no presets
are discovered and no application state is read/written. Color flags normalize
before help processing, so before/after and nested forms agree. NO_COLOR wins;
JSON never gains ANSI or block artwork. Native help with --json remains text.

0.1.2 permits a versioned upgrade from immutable installed 0.1.1. No live install,
config/profile/PATH or original asset was changed. Windows is still deferred.
See TERMINAL-UX.md and TERMUX-INSTALL-PLAN.md for source preview/update commands.
Focused native Termux evidence (Android 15 aarch64, Python 3.14.6):

| Command | Result |
|---|---|
| `python3 -m unittest discover -s tests -p test_help.py -v` | 8 passed, 8.377 s: order-independent root/nested color flags, NO_COLOR/JSON, complete grammar descriptions, 40/60/96-column headers, actual PTYs, missing/unsafe/FIFO assets and fast-path import tracing |
| `python3 -m unittest discover -s tests -p test_welcome.py -v` | 11 passed, 0.069 s; prior welcome behavior/JSON/color/read-only coverage retained |
| `python3 -m unittest discover -s tests -p test_everyday.py -v` | 3 passed, 2.613 s; safety regressions and nested help explanations |
| `python3 -m unittest discover -s tests -p test_blastoff.py -k Contract -v` | 33 passed; one updated test had a bytes/string assertion error (34 tests, 13.398 s), not an application failure |
| `python3 -m unittest discover -s tests -p test_blastoff.py -k version_consistency -v` | Corrected test passed, 0.514 s; all 34 distinct contract tests now pass across these runs |
| `python3 -m unittest discover -s tests -p test_assets.py -v` | 1 passed, 1.573 s; optional-original-asset independence and no bytecode writes |
| `BLASTOFF_TEST_ARCHIVE="$temporary/blastoff-rebuild-0.1.2.zip" python3 -m unittest discover -s tests -p test_installed_package.py -v` | 1 passed, 6.691 s; isolated version upgrade, installed artwork/header in a native PTY after source removal, helper/completion/manual resolution, data retention and uninstall |

The first new PTY assertion also needed to strip trusted gradient SGR between
characters before comparing visible artwork; subsequent actual PTY checks pass.
Original asset and WINDOWS-CHECKS.md hashes matched the preceding manifest
(21 preserved reference/handoff files). The artwork copies match their originals
byte-for-byte. Python compile checks and git diff --check pass. Manual wrapping
also resolves the two historical long-line mandoc notices.

Startup: 20 samples/3 warmups, isolated roots, redirected stdout, NO_COLOR.
Python welcome p50/p95 **104.927/126.455 ms**; Python help **154.885/162.335 ms**;
Bash help **170.177/224.972 ms**. See startup-termux-help.json for exact commands.
Concurrent checks may affect timing; this is not an idle comparison or speedup
claim. Help now derives from the shared parser, rather than a cached argparse
string. Import tracing confirms it exits before application/discovery imports.

58 distinct checks pass across these focused runs and corrected test reruns.
`python3 scripts/package.py --output-dir "$temporary"` regenerates 0.1.2 ZIP/tar.gz
and CHECKSUMS.json; `python3 scripts/verify.py` verifies the working tree and both
extracted **97-file** inventories. Outer SHA256SUMS are also checked. Temporary
archives are removed, not published. Original assets, live install/config and
profiles/PATH remain unchanged. Windows remains deferred.

Next: visually inspect source welcome and help at your normal width (compact
ASCII below 60 columns), then at 60+ for the actual artwork. Review the 0.1.2
install dry-run before upgrading the installed 0.1.1 copy. Exact commands are in
TERMINAL-UX.md and TERMUX-INSTALL-PLAN.md. Automated PTYs verify bytes/layout
bounds, not font quality or your terminal's visual appearance.

## Terminal UX slice — 0.1.1

The user reports that Blastoff is installed and working, 37 themes migrated, and
12 presets listed. These are user-reported live results, not a new agent-run
installation. This slice does not modify that installed copy or its data.

- Bare invocation now renders a compact ASCII BLASTOFF welcome/version/examples
  in purple/pink on capable terminals, without discovery or subprocesses. Width,
  NO_COLOR, forced/disabled color, redirection and no-command JSON are supported.
  Complete --help is retained. Shipped helper loading disables bytecode writes.
- Inspected the current `.local/logo` README/text branding for inspiration;
  assets were not executed, copied over or modified. No runtime image dependency.
- Fzf now has a deliberate palette, border/title, source labels and key guide.
  Alt-P toggles a configuration-only preview, below the list on narrow screens,
  initially hidden on short screens. Gum/numbered menus have labels/instructions
  but no pane. Inherited picker options remain stripped.
- `lib/preview.py` accepts an opaque numeric row ID, never a theme/path shell
  fragment. It sanitizes terminal controls and bounds local display/preset work;
  generated output and failures are cached only in a disposable picker session.
  No live prompt or theme custom command is rendered/executed. Config/storage
  cancellation snapshots and existing backup/symlink protections are retained.
- The source identity is 0.1.1 (core, VERSION, manifest and man). This deliberately
  avoids rewriting the installed immutable 0.1.0 payload. Use the explicit update
  commands in TERMUX-INSTALL-PLAN.md after reviewing dry-run scope. No live update,
  profile/PATH edit, commit/tag/push or publication was performed.

See TERMINAL-UX.md for exact safe source preview commands and remaining human
visual checks. Native Windows, PowerShell preview execution, terminal appearance
and Android Alt-P ergonomics remain unverified; no cross-platform claim is made.
Focused automated evidence on native Termux (Android 15 aarch64, Python 3.14.6):

| Command | Result |
|---|---|
| `python3 -m unittest discover -s tests -p test_welcome.py -v` | 11 tests passed, 0.063 s: widths/color/NO_COLOR/redirect/JSON and no rendering-time discovery, subprocess or file access |
| `python3 -m unittest discover -s tests -p test_preview.py -v` | Final 7 tests passed, 2.994 s: real fzf preview at 50x28, Alt-P opens hidden preview at 40x16, Ctrl-C preserves config/storage and removes the session; unsafe text, quoted paths, bounds, cache and symlink tests |
| `python3 -m unittest discover -s tests -p test_picker.py -v` | 10 tests passed, 8.233 s, across actual fzf/gum/numbered backends and cancellation |
| `python3 -m unittest discover -s tests -p test_discovery.py -v` | 6 tests passed, 2.769 s; graceful discovery and strict preset errors preserved |
| `python3 -m unittest discover -s tests -p test_assets.py -v` | Final 1 test passed, 1.373 s, without optional branding assets or runtime bytecode creation |
| `python3 -m unittest discover -s tests -p test_blastoff.py -k version -k entry_point -k read_only -v` | 3 tests passed, 2.110 s; release identity, Bash/core output and read-only behavior |
| `BLASTOFF_TEST_ARCHIVE="$temporary/blastoff-rebuild-0.1.1.zip" python3 -m unittest discover -s tests -p test_installed_package.py -v` | 1 passed, 4.988 s: isolated synthetic-prior-version upgrade, installed welcome/preview helpers after source removal, installed completions/manual, data operations and uninstall retention |

39 distinct focused tests passed; settled broad suites were not rerun. The first
synthetic upgrade fixture copied __pycache__ and reused old same-size/timestamp
bytecode after its version edit; excluding bytecode from that temporary clone
fixed the harness. This was not a live installation failure or an installer
workaround. The prior identity is synthetic, not certification of a historical
binary. The actual installed helper preview ran via `python3 -I` from the versioned
payload, including paths with spaces/Unicode. Native Windows remains deferred.

Final ZIP/tar.gz packaging is regenerated with `python3 scripts/package.py
--output-dir "$temporary"`; working tree and both extracted inventories are
verified with `python3 scripts/verify.py`, plus outer SHA256SUMS. The final
0.1.1 inventory has **92 source files**. Only disposable archives are created,
then removed; CHECKSUMS.json remains. Python `compile()` and `git diff --check`
pass. `mandoc -Tlint man/blastoff.1` has no errors (two pre-existing long-line
style notices). No source assets or live installation/config/profile/PATH were
changed, and nothing was committed/tagged/pushed/published.

Startup (20 samples, 3 warmups, isolated roots, redirected stdout): Python welcome
p50/p95 **84.367/95.180 ms**, Bash welcome **103.307/129.571 ms**, cached Python
help **61.605/66.968 ms**. Commands/data are in startup-termux-welcome.json. Other
checks may have overlapped; this is not an idle-machine comparison or speedup
claim. No PowerShell timings or native Windows evidence are implied.

## Optional preset discovery fix — 2026-10-01

The previously recorded failed-Starship listing/picker limitation is resolved.
Combined list/aliases/theme-list retain local results and exit 0 when optional
preset discovery fails, even if both groups are empty. Human output warns once
on stderr and labels presets unavailable; JSON output includes an additive
`preset_discovery` status/error object and leaves stderr empty. Executable
presence (`starship_available`) is still distinct from successful discovery.
Successful empty preset output is `ok`, not a warning. Picker uses available
locals, cancels with 130, or returns 1 without opening a picker if no choices
remain. Explicit preset operations still fail with status 3 for discovery errors.
See CLI-CONTRACT.md for exact output/exit semantics.

The fix is confined to shared-core discovery, list and picker composition.
Missing/unlaunchable executable, nonzero exit, timeout, oversized output, invalid
UTF-8 and unusable/mixed/reserved-name list output are covered. All nonblank
lines must validate, rather than silently dropping invalid lines. Interruptions
are not caught by the optional fallback. Wrappers, completion scripts and
file-mutation protections are unchanged; Windows remains explicitly deferred.

Focused commands on native Termux (no broad preparation/full-suite rerun):

| Command | Result |
|---|---|
| `python3 -m unittest discover -s tests -p test_discovery.py -v` | 6 tests passed, 2.445 s; matrix covers 9 failure modes, aliases, JSON/human streams, strict preset requests, empty/success cases and real failing-process Bash/numbered-picker PTY |
| `python3 -m unittest discover -s tests -p test_picker.py -v` | 10 tests passed, 8.616 s; real fzf/gum/numbered selection and cancellation, snapshots, empty/invalid choices, redirects and ambient-option protection |
| `python3 -m unittest discover -s tests -p test_blastoff.py -k list -k presets -k read_only -k entry_point -v` | 4 affected regressions passed, 2.886 s |
| `python3 -I lib/blastoff.py list --json` with an isolated executable that sleeps 30 seconds | Actual subprocess timeout after 10.216 s: exit 0, local theme retained, unavailable/timed-out JSON status, empty stderr and unchanged fixture files; no config/cache created |
| `python3 -I lib/blastoff.py list --json` compared to `starship preset --list` in temporary HOME/config/storage/cache roots | Real Starship 1.26.0: all 12 names accepted, status ok, no config/storage writes. Comparison ignores blank lines per contract; the initial raw comparison included Starship's trailing blank line |
| `compile()` on changed Python; `git diff --check`; comparison against previous CHECKSUMS.json | Passed; all 20 original reference files and WINDOWS-CHECKS.md retain their prior hashes |

Baseline: the new matrix failed before the fix (69 failed subcases, 9 errors;
6 tests, 1.312 s), including real Bash listing exiting 3 instead of returning
locals. Failure propagation from optional discovery and silent filtering of
invalid list lines were the causes. Regression tests now exercise these caller
boundaries directly. Most failure variants use mocked subprocess outcomes with
real temporary config/storage; the Bash/PTY failure probe uses an actual local
executable. Automated PTY evidence is not human visual approval.

Quickstart, contract, manual and install-plan behavior notes are updated,
including correcting the example preset to the actual `plain-text-symbols` name.
The real installation plan and its separate approval boundary are unchanged.
No live installation/config/profile/PATH/original asset was changed; no Git
commit/push/tag or publication. Earlier installation, real-preset, completion,
safety and startup evidence is reused rather than repeated.

`python3 scripts/package.py --output-dir "$temporary"` rebuilt ZIP and tar.gz;
`python3 scripts/verify.py` passed for the working tree and both extracted
**85-file** inventories. Outer SHA256SUMS matched. Only temporary archives were
created and removed; CHECKSUMS.json is retained. Final documentation-only edits
receive the same package/inventory verification. `mandoc -Tlint man/blastoff.1`
has no errors; the two previously recorded long-line style notices remain.

## Everyday Termux readiness — 2026-10-01

**Native Windows is explicitly deferred and nonblocking for Termux.** Preserve
`WINDOWS-CHECKS.md` for when native hardware is available; no Windows preparation
or substitute Linux PowerShell/WSL execution was repeated in this slice.

Review against the original preferences/contract found every requested command
family implemented. No new rename/editor command is needed. Remaining everyday
work is hardening and documentation, not a missing theme/module subsystem:

- Fixed deletion of a regular active config whose configured pathname is itself
  a stored theme/module. Both regular paths and active symlink targets now refuse
  deletion, even with `--force`, before creating a backup or unlinking content.
- Backup list/restore reject non-object JSON metadata with clean status-1 errors;
  restore leaves the config unchanged. Invalid JSON already used clean handling.
- Nested mutation help now describes prefixes, replacement/backup behavior,
  explicit-table module limitations and shared options. Cached root help and
  version fast paths are unchanged; no startup speedup is claimed.
- Corrected stale README integration guidance, shell syntax-check instructions
  and the manual's distinction between stored-theme and stored-module recovery.
- Added `TERMUX-QUICKSTART.md` (sandbox examples and smallest human check) and
  `TERMUX-INSTALL-PLAN.md` (approval-ready plan, **not performed**). The existing
  `~/dots/scripts/blastoff` wins PATH lookup; preserve it and invoke a future
  `~/.local/bin/blastoff` explicitly. No live config contents were read for the
  installation plan, and no real installation/profile/PATH/assets were changed.

Historical follow-up, now resolved by the optional-discovery slice above:
failed/timed-out Starship used to hide combined local listing/picker choices.
Explicit preset errors remain strict. Optional improvements:
compact branding, broader TOML editing, controlled performance budgets, durable
multi-file transaction recovery and additional plugin/version matrices. Missing
optional images do not block commands (previous asset-isolation evidence stands).

Focused native Termux evidence (same host/runtime versions as below):

| Command | Result |
|---|---|
| `python3 -m unittest discover -s tests -p test_everyday.py -v` | 3 tests passed, 3.509 s: regular active-path deletion refusal, metadata error handling, help with no state writes |
| `python3 -m unittest discover -s tests -p test_blastoff.py -k delete -k backup -k read_only -k entry_point -v` | 9 affected regressions passed, 6.041 s, including existing symlink guards and Bash forwarding |
| Package rehearsal in INSTALLATION.md | Initial run passed, 1 test/4.024 s; changed-source archive run passed, 1 test/3.983 s, no missing-runtime PENDING lines |
| `mandoc -Tlint man/blastoff.1` | No errors; two pre-existing over-80-column style notices; installed UTF-8 rendering checked by rehearsal |
| `compile()` on changed Python sources; `git diff --check` | Passed |

Before fixes, the 3 new tests reproduced 10 failed subcases and 4 metadata
traceback/JSON-parse errors (3.010 s). After the fix, only a help test's literal
whitespace assertion failed when argparse wrapped a phrase; normalizing help
whitespace fixed that assertion, not production behavior. No broad full-suite
rerun was performed. Prior 67-test native suite, 12 real presets, editor/picker
PTYs, completions and startup measurements are reused.

Installed-package coverage used a disposable space/Unicode prefix and config/
storage roots. It verified dry-run creates no prefix; executable mode and actual
Termux Bash shebang; default Python and BLASTOFF_PYTHON selection; missing
interpreter status 127; child-only command resolution; and execution after the
extracted source was renamed away. Installed theme save/copy/apply, module
save/load and backup create/restore passed. Installed Bash/Zsh/Fish completion
callbacks ran with an empty child PATH, script bytes matched CLI completion
output, and the correctly placed manpage rendered with native mandoc. The
installed lifecycle script uninstalled all manifest-owned files while retaining
config/themes/modules/backups, shell-generated isolated state and an unrelated
prefix sentinel byte-for-byte. This is automated evidence, not human terminal
visual approval.

ZIP and tar.gz were rebuilt in temporary directories; both extracted inventories
verified **84 source files**, and outer SHA256SUMS matched. Disposable archives
were removed, not published. Final documentation-only updates are followed by
another package/checksum and extracted-inventory verification, not another full
suite. The retained CHECKSUMS.json describes the final working tree.

**Termux readiness:** implemented and sandbox-validated for everyday use; the
failed-Starship availability limitation is now resolved. Ready for the small
human check and a separately approved installation; not a cross-platform release
certification. Native Windows remains deferred. No live installation was done.

## Native Windows handoff preparation — 2026-10-01

**Native Windows execution remains pending.** This host still has neither native
Windows nor `pwsh`/`powershell`. No Linux PowerShell, WSL or mocked branch is
counted as Windows evidence. `WINDOWS-CHECKS.md` now supplies prerequisites,
exact isolated PowerShell commands, expected statuses, stream/argv assertions,
environment overrides, data operations, sharing/reparse probes, temporary-prefix
lifecycle checks and reporting/cleanup guidance.

Preparation changes:

- `tests/parity.ps1` now requires native Windows and a disposable PowerShell 7.2+
  process (native stderr behavior changed in 7.2). Start with 7.4+ per the guide.
  The module's declared 7.0+ range is unchanged and **not** certified. Older hosts,
  Legacy argument passing and binary stream semantics remain separate gates.
- Parity now isolates HOME/USERPROFILE and Starship/XDG caches as well as config/
  storage; checks import without Python startup; verifies empty/quoted/Unicode/
  trailing-backslash argv against an independent echo fixture; asserts expected
  0/1/2 statuses and separate text streams; and retains failed fixtures. The
  expanded PowerShell script was reviewed but **not parsed or executed by a
  PowerShell engine here**. Its 13-case summary is an expected result, not a pass.
- Python test fixes: compare JSON path fields directly rather than through escaped
  dictionary repr; preserve installed bytes during tamper recovery rather than
  translate LF to CRLF; require POSIX for POSIX shell tests even when Git Bash/WSL
  is discoverable; and test unowned-file refusal using the common manpage
  destination, not a Bash-only launcher. Shared-core/lifecycle tests still run
  on Windows. Existing privilege-dependent Windows skips remain explicit.
- One installer branch fix: fresh native Windows installs do not discover or
  create the top-level POSIX Bash launcher. A mocked NT selection with
  `C:\\Program Files\\Git\\bin\\bash.exe` reproduced an erroneous shebang-space
  refusal before the fix. The native PowerShell payload remains present; POSIX
  launcher behavior is unchanged. This is a branch regression, not a native
  Windows filesystem/installer validation.

Focused evidence on Termux only (full output: `test-windows-handoff-prep-termux.txt`):

| Command | Result |
|---|---|
| `python3 -m unittest discover -s tests -p test_windows_handoff.py -v` | 1 platform-branch unit test passed, 0.014 s; failed before the installer fix |
| `python3 -m unittest discover -s tests -p test_blastoff.py -k Lifecycle -v` | 3 isolated lifecycle tests passed, 2.095 s |
| `python3 -m unittest discover -s tests -p test_native.py -k empty_overrides_and_tilde_paths -v` | 1 affected path-assertion test passed, 1.438 s |

Affected Python files also passed `compile()` checks and `git diff --check`.
`python3 scripts/package.py --output-dir "$temporary"` regenerated ZIP/tar.gz;
both extracted inventories verified **80 source files**, and outer SHA256SUMS
matched. Only disposable archives were created, then removed. After this final
evidence-only entry, `python3 scripts/package.py --checksums-only` and
`python3 scripts/verify.py` refresh/verify the final working-tree inventory.

In-memory probes also demonstrated escaped-backslash repr containment failure
and LF→CRLF byte changes. No native Windows run is implied by either probe.
Settled Termux picker/completion/preset and startup checks were not repeated:
the shared core, PowerShell module, completions and original assets were not
changed in this slice. The earlier Termux evidence below remains historical.

## Interactive/completion slice — 2026-10-01

Same native Termux host/runtimes recorded below; actual optional tools:
**fzf 0.74.4 (a140afeb)** and **gum 2.0.0**. No tools were installed. Earlier
symlink-deletion and module-merge safety fixes remain intact and tested.

### Changes

- Bash/Zsh/Fish now dispatch completion by argument position. Global options
  and their values are consumed correctly before/after commands and operands;
  source/destination contexts differ. Added `local:`/`preset:` source prefixes,
  paired backup filename IDs, and space-safe import/directory path completion.
  Portable names/device names/symlinks/nonregular candidates are filtered.
  Free destination names, preset names and module-save routes do not trigger
  application lookup or TOML parsing. Backup metadata/kind/checksum remain
  unverified until an actual restore. See the CLI contract for exact coverage.
- Picker children ignore ambient `FZF_*`/`GUM_*` variables. A real fzf fixture
  previously auto-applied a theme via inherited `--filter`; that regression now
  cancels normally. No preview, binding or listener options are inherited.
- Numbered Escape+Enter cancels with 130. Replaced `input()` with a flushed prompt
  plus `sys.stdin.readline()`: a native standalone probe reproduced `input()`
  deferring Ctrl-C until another newline, while TextIO reacted immediately.
- Local discovery/picker now rejects reserved names such as CON/LPT1 consistently
  with apply/save validation. Existing files are never removed or rewritten.
- Added a disposable `scripts/interactive_check.py` helper and exact human-check
  instructions in `INTERACTIVE-CHECKS.md`. Optional branding remains unnecessary
  for runtime help/version/list/current/doctor/completion; originals are untouched.

### Commands and evidence

- `python3 -m unittest discover -s tests -p test_completions.py -v`:
  **10 tests passed in 7.452 s**, with a matrix of Bash/Zsh/Fish subcases covering
  commands/actions, flags, aliases, option positions, safe names, source prefixes,
  paired backup IDs, empty/missing stores, root overrides and space-containing
  paths. Empty child PATH prevents application startup. Snapshots confirm no
  completion-triggered HOME/storage changes. The local Fish build creates its
  own XDG scaffold even for `--no-config --private -c true`; the test initializes
  that empty-shell state before measuring completion writes.
- `python3 -m unittest discover -s tests -p test_shell_tty.py -v`:
  **three consecutive passes**, 1.077 / 0.730 / 0.738 s. Actual Bash Readline,
  Zsh ZLE and Fish editor Tab inserted `local:alpha` and a correctly quoted path
  containing spaces at 50 columns. The driver answers conservative terminal
  capability queries, uses an empty child PATH and a sentinel command, and
  never submits the completed application line. This is automated PTY evidence,
  not a human visual or fzf-tab/plugin approval.
- `python3 scripts/package.py --checksums-only`, then
  `BLASTOFF_TEST_STARSHIP=1 python3 -m unittest discover -s tests -v`:
  **67 tests passed in 44.476 s, no skips**; full output in
  `test-interactive-termux.txt`. This includes all previous safety/lifecycle and
  real Starship checks, the matrix above, optional-asset independence, and ten
  picker tests. Real fzf/gum and the numbered fallback selected correctly at
  40/50 columns, including 96-character names. Escape/Ctrl-C (Escape+Enter in the
  line-oriented fallback), EOF/blank fallback input, empty choices, invalid
  numbered input, JSON and one-/two-sided redirects were checked. Cancellation
  snapshots preserved config/storage contents and directories. Missing optional
  tools and fzf precedence were exercised with isolated per-child tool exposure.
- Human-check helper automated smoke: numbered `--expect select` returned PASS
  with child exit 0; `--expect cancel` returned PASS with child exit 130 and
  `config/storage unchanged=True`. Human appearance has **not** been checked.
- Separate `bash -n bin/blastoff`, `bash -n scripts/install.sh`,
  `bash -n completions/blastoff.bash`, `zsh -n completions/blastoff.zsh`, and
  `fish -n completions/blastoff.fish`: exit 0. All Python source compiled with
  `compile()` without writing bytecode; `git diff --check` passed.
- Ruff LSP on six new helper/test files: nine warnings (import ordering, explicit
  `check` suggestions, interpreter-invoked script mode), no errors. Optional
  `ty` remains unavailable; no native Windows/type-check coverage is claimed.

### Post-slice packaging

`python3 scripts/package.py --output-dir "$temporary/first"` and a second build
under `"$temporary/second"` produced byte-identical ZIP, tar.gz and SHA256SUMS.
Both extracted inventories passed `verify(extracted_root)` for **77 files**;
outer SHA256SUMS matched. Core bytes did not change during packaging. Archives
were generated/checked only in disposable roots, then removed; nothing was
installed, published or written over an existing release artifact. This final
evidence entry is documentation-only; checksums are refreshed and verified once
more afterward with `python3 scripts/package.py --checksums-only` and
`python3 scripts/verify.py`.

### Post-slice startup

`python3 scripts/benchmark.py`: 60 fresh-process samples per command after five
warmups, same Android 15/aarch64/Python 3.14.6 host. Output is retained in
`startup-termux-interactive.json`. Test suites had finished; documentation work
continued, so this is not a controlled idle-host comparison. No runtime/import
optimization was made or speedup claimed. PowerShell remains unmeasured.

| Entry | p50 ms | p95 ms |
|---|---:|---:|
| Python version | 74.425 | 93.828 |
| Python help | 75.096 | 83.530 |
| Bash version | 85.662 | 100.747 |
| Bash help | 87.239 | 96.040 |
| Python current JSON | 164.921 | 245.274 |
| Bash current JSON | 192.110 | 260.390 |
| Python module list JSON | 169.925 | 223.265 |
| Bash module list JSON | 189.497 | 263.233 |

Initial verification failures were investigated, not ignored: obsolete smoke
expectations were updated for the added `preset:` candidate; PTY Ctrl-X prefix
bindings were replaced by a single-key capture binding; Fish capability-query
handshakes are answered before waiting for a prompt. One early driver mistakenly
submitted a line and reached an ambient legacy command, which exited at the
missing **temporary-HOME** theme directory. Final tests prevent submission or
application startup with both an empty PATH and a sentinel. No live config or
real-prefix operation occurred.

## Native Termux verification — 2026-09-30

Host: Android 15, aarch64, kernel `5.4.274-qgki-30957850-abG996USQSJHZB1`;
Python 3.14.6, Bash 5.3.20, Zsh 5.9.2, Fish 4.9.3, Starship 1.26.0.
PowerShell and groff are unavailable. This is native Termux, not proot/WSL.

The initial `python3 -m unittest discover -s tests -v` ran 35 tests and failed
cached-help whitespace parity and source-inventory verification (14.792 s).
The inventory mismatch was investigated before refreshing checksums, not hidden
by copying the archive over the repository. Two additional data-safety bugs
were reproduced and fixed: deletion through linked storage subdirectories and
external config edits lost during module merging. See `TERMUX-AUDIT.md`.

Final commands and results:

- `python3 scripts/package.py --checksums-only`: refreshed the bounded source
  inventory after intentional edits. Packaging no longer captures `.pi/tasks`,
  sessions or arbitrary checkout files or rewrites Python core help.
- `BLASTOFF_TEST_STARSHIP=1 python3 -m unittest discover -s tests -v`:
  **45 tests passed in 34.398 s**, no skips; full output in `test-termux.txt`.
  Includes temporary-prefix install/dry-run/uninstall, installed absolute Bash
  shebang execution, ownership/tamper checks, literal quotes/spaces/Unicode and
  empty-argument forwarding, separate config/storage overrides, empty overrides,
  tilde expansion, relative-path refusal, safety regressions and prior tests.
- `bash -n bin/blastoff`, `bash -n scripts/install.sh`,
  `bash -n completions/blastoff.bash`, `zsh -n completions/blastoff.zsh`,
  `fish -n completions/blastoff.fish`: each exit 0, no diagnostics. Bash checks
  were run separately because `bash -n file1 file2` only parses the first file.
- Native completion tests: Bash function invocation with an empty child PATH;
  Zsh dispatch with captured `compadd` outside ZLE; Fish `--no-config` plus
  `complete -C "blastoff theme apply p"`. Local name smoke cases passed.
  These do not prove interactive completion, fzf-tab, or the full position matrix.
- Actual `starship preset --list` returned 12 presets. For every name,
  `starship preset NAME` parsed as TOML, and `preset save` / `preset apply`
  matched its exact bytes. Previous active bytes were backed up. Invalid names
  failed without changing config (Blastoff exit 1; direct Starship exit 2).
  HOME, storage, active config, XDG paths and Starship cache were sandboxed.
  Starship may create its own cache directory; Blastoff list created neither
  storage nor active-config directories. No prompt or custom command was run.
- Python `compile()` checks passed for all Python source files without writing
  bytecode. Ruff LSP reported 30 warnings, mainly existing style/import-order,
  explicit `check` and source executable-mode warnings. No blanket autofix was
  applied; moving core imports would undermine cheap help/version startup.
  The new merge-test closure warning is benign: it runs synchronously inside
  each iteration. Optional `ty` was unavailable; install it or adjust its
  configured command in `pi-lsp.json` before claiming type-check coverage.

### Packaging and final review

- `python3 scripts/package.py --output-dir "$temporary/first"` and the same
  command with `"$temporary/second"`: ZIP, tar.gz and SHA256SUMS were byte-identical
  across two builds. Both archives were extracted into temporary roots and
  `scripts/verify.py`'s `verify(extracted_root)` accepted all **68 source files**.
  Outer SHA256SUMS matched both archive bytes. Core bytes were unchanged by
  packaging. All generated archives were removed with their temporary root;
  nothing was published or written into a real installation prefix.
- After this final evidence entry, `python3 scripts/package.py --checksums-only`
  and `python3 scripts/verify.py` refresh/check the final documentation inventory.
  Archive reproducibility above was checked just before this evidence-only edit.
- `git diff --check`: passed. Existing README modifications remained unchanged;
  the only added tracked-file edit is `.pi/tasks/` in `.gitignore`. Rebuild
  sources are still untracked, as they were at the initial audit.

### Native startup evidence

`python3 scripts/benchmark.py` produced `startup-termux.json`: 60 fresh-process
samples per entry after five warmups, temporary config/storage/HOME, no writes
to config/storage. Verification tasks ran concurrently: this is a measured
working-load baseline, not an idle-host regression threshold or a comparison
with the historical Linux machine. Hardware identity beyond aarch64 was not
collected. PowerShell startup remains unmeasured.

| Entry | p50 ms | p95 ms |
|---|---:|---:|
| Python version | 80.769 | 118.287 |
| Python help | 82.907 | 106.126 |
| Bash version | 106.257 | 132.690 |
| Bash help | 93.878 | 128.510 |
| Python current JSON | 235.961 | 342.156 |
| Bash current JSON | 286.024 | 377.728 |
| Python module list JSON | 251.868 | 345.614 |
| Bash module list JSON | 286.307 | 376.501 |

No performance optimization or speedup is claimed from these noisy samples.
Repeat sequentially on an idle device before choosing budgets or profiling the
slower full-parser paths.

## Historical Linux package evidence (not rerun here)

Host: Linux x86_64, kernel 6.18.44, glibc 2.39, Python 3.12.14.
Bash and Zsh are present; PowerShell, Fish and Starship are absent.

- `python3 -m unittest discover -s tests -v`: 35 isolated tests passed in 3.740 seconds;
  the exact result is recorded in `test-linux.txt`. Tests cover core
  contracts, Bash forwarding, invalid TOML, collisions, backups/checksums,
  link/FIFO/parent refusal, file modes, stale locks, external edits, failed
  replacement, module layouts, preset fixtures and lifecycle ownership/tampering.
- `bash -n bin/blastoff scripts/install.sh completions/blastoff.bash`: passed.
- `zsh -n completions/blastoff.zsh`: passed.
- `groff -Tutf8 -man man/blastoff.1`: rendered without diagnostics.
- Project skill metadata/name/explicit-relative-link checks and pi settings-path
  checks: passed for four skill directories and all explicit resource links.
- Source inventory/checksums and deterministic ZIP/tar.gz packaging: verified
  in the final packaging step. See `CHECKSUMS.json` and the outer SHA256SUMS.
- Real pi startup/reload and real Starship preset behavior were not run. The
  preset tests use an offline fake executable; documentation was checked against
  official upstream pi/Starship pages on this date.

## Startup evidence

`startup-linux.json` contains 60 samples per command after five warmups.
It measures fresh command processes, with isolated config/storage and no writes.
The final cached-help/launcher sample recorded:

| Entry | p50 ms | p95 ms |
|---|---:|---:|
| Python version | 20.149 | 29.702 |
| Python help | 19.511 | 25.491 |
| Bash version | 20.878 | 24.558 |
| Bash help | 20.709 | 24.811 |

Small differences are scheduling noise, not proof that wrappers beat the core.
Before cached help, Bash help p50 was about 53 ms on this host. The final helper
avoids unrelated imports. This still has Python startup overhead and is not a
single-digit-millisecond compiled command. Nick selected this shared-core
architecture; collect native-host measurements before setting budgets or
revisiting the runtime. These historical files contain no native Termux/Windows
performance result; the new Termux measurements are reported separately above.

## Pending release gates

| Gate | Required evidence |
|---|---|
| Native Termux ARM64 | Core/Bash, temporary lifecycle/shebang, modes, picker cancellation and native editor PTYs verified; human terminal visual checks and controlled performance budgets pending |
| Native Windows PowerShell | Explicitly deferred; does not block Termux. Preserved WINDOWS-CHECKS.md handoff; all native execution, streams/argv, filesystem/reparse, lifecycle and version-range evidence remain pending |
| Fish | Native positional matrix and editor PTY checks passed; human terminal/plugin approval pending |
| Bash/Zsh completion UX | Positional matrix, backup IDs and real editor PTYs passed; fzf-tab/plugins and human narrow-terminal appearance pending |
| Picker | Real fzf/gum/fallback automated PTYs passed, including cancellation and 40/50 columns; human visual/touch-keyboard sessions pending |
| Starship | 1.26.0 list/all 12 presets/save/apply/invalid-name checks passed; timeout/interruption and supported minimum-version matrix pending |
| pi | Confirm skills/prompts/context discovery and `/reload` in Nick's installed version |
| Real repository | Audited in place; no integration needed. Two incoming images unmatched; see TERMUX-AUDIT.md |
| Lifecycle resilience | Additional interruption/upgrade tests; optional durable transaction journal decision |

## Known limits

- Requires Python 3.11+; shared behavior is implemented, native wrapper parity
  remains unproven until the Windows script runs.
- Module edits support explicit table forms and safely refuse unsupported
  inline/root-dotted forms. Comments in replaced table blocks may move/change;
  unrelated values are verified and unrelated block text is retained.
- Generic TOML validation is not full Starship schema/runtime validation. Module
  loading does not add missing palette/format dependencies or run custom commands.
- No symlink/reparse parent writes, even for intentional dotfile directory links.
  Use explicitly configured real paths. Active link conversion is opt-in.
- Per-file atomic replacement and cooperating locks do not provide malicious-race
  protection or full multi-file/power-loss transactions. Locks are not auto-broken.
- Completion is intentionally offline; no live preset lookup or active-config
  module-route parsing. Backup candidates are filenames, not validated restores.
  Automated native coverage does not establish plugin/human visual behavior.
- The supplied wide ANSI banner is archived, not replayed. Welcome/help use the
  supplied Braille logo with generated gradient colors; human font appearance
  remains a separate visual check.
- The actual repository has an MIT license; it was retained unchanged.

## Next bounded task

Review `bash install.sh --dry-run` from the source root. If its native-prefix
migration and integration plan is wanted, run `bash install.sh` yourself. This
agent has not performed that live installation or changed real profiles. See
TERMUX-INSTALL-PLAN.md for migration and data-preservation details. Human visual
checks in TERMINAL-UX.md remain separate from automated PTYs. Native Windows
stays deferred, with its original handoff retained.

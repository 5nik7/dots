# Overkill Windows and WSL parity

Status: source implementation and isolated verification; Windows activation packets 1–2 completed and packet 3 skill links restored, remaining activation pending. Native Termux records include the six-suite acceptance at `b6daf0f7`, subsequent theme/GitTheme repairs, profile/environment/Git at `1c215417`, transaction/Bak at `5b70964d`, bounded bootstrap/installation at `23a5bfa5`, local-Git source-update at `135d6b57`, and nine native theme methods at `8838841c`. Full-checkout acceptance at `5d5fca2e` now includes one native Termux-profile lifecycle and two separately classified WSL-profile regressions on Android. Broader return and live acceptance remain pending; clipboard outcomes are recorded separately for each handoff. Baseline: clean Windows
`C:\Users\njen\dots` and Ubuntu `/home/njen/dots`, both at
`800988ea331c132f29eaf5b645a00b068e38c96a`, audited 2026-11-13 Pacific.
Windows Terminal Preview is the selected native terminal. Keep its profiles,
font, theme and existing desktop notifier until explicit activation review.

## Authorization and coordination

Source repairs and isolated tests are approved. Implement one coherent patch in
the Windows source checkout; test POSIX behavior in owned WSL public snapshots.
Do not modify the live WSL checkout or synchronize Git implicitly. No commits,
pushes, worktrees, Todo changes, live startup, packages, services, registry,
themes or clipboard changes are included. Repository link restoration and Git
configuration changes require their separately reviewed activation packet.
The first subsequent explicit approval authorized packets 1–2 only. A later
explicit approval authorized packet 3's 29 Windows repository skill links;
their completed live effects and recovery records are documented below. This
does not authorize packets 4–6 or a Git symlink-policy change.

Subsequent explicit authorization also covered committing/pushing the coherent
source repairs to GitHub `main`, and the phone's bounded fast-forward from
`ba376c99` to `b6daf0f7`. These do not authorize further live activation. Native
Termux handoff clipboard delivery has its own narrow exception below; it does
not authorize clipboard use as a test fixture or recording/history services.

Three workers own disjoint source/test sets: Windows startup/help, installation
and link safety, and POSIX/ancillary-shell adapters. The lead owns integration,
documentation, remaining family work and all live-operation review. Source
profiles, Yazi and Neovim have live links/junctions: source changes can affect
subsequent launches even without installation.

## Hosted CI development pause — 2026-11-14

The owner requested stopping repeated failure emails during cross-platform development, authorizing repair or temporary removal of the two named workflows. Repository checks and Checkout installation now retain their complete jobs under manual `workflow_dispatch` only; automatic push and pull-request triggers are temporarily removed. This is a CI scheduling change, not a test repair or a successful CI claim. Completion checks and Development worktree lifecycle are unchanged. No notification account setting, branch policy, package, runtime configuration or acceptance assertion is altered.

Read-only inspection found these actual hosted failures at `31e07b3a54d5ba00528bf0d0f2aeb2480295c31b`:

| Hosted run/job | Observed failure | Repair required before restoring automatic runs |
| --- | --- | --- |
| [Repository checks](https://github.com/5nik7/dots/actions/runs/43582538292), Windows | `test_native_and_link_text_checkouts`: broken fixture link `README.md -> alias` | Inspect native link construction/resolution with actual Windows links; preserve link-text checkout coverage. |
| Same run, Ubuntu | Wiki preference provenance expects `profiles/linux/profile.json`, but receives `profiles/linux/config.json` | Reconcile the assertion with the current preference-file contract and retain inheritance/reset/consumer checks. |
| [Checkout installation](https://github.com/5nik7/dots/actions/runs/43582538378), Windows native authoring | Both PowerShell jobs fail native palette publication; inspected PS5.1 job reports a `cp1252` `UnicodeEncodeError` writing icons in `theme_styles.py` | Repair explicit UTF-8 serialization and test without ambient UTF-8 mode; rerun both required engines. |
| Same run, Windows lifecycle | Five failures: two theme preparations hit the encoding error; Fonts/Todo launcher strings and a restored-link assertion disagree on `RUNNER~1` versus `runneradmin` | Resolve fixture path identity without weakening drift/link protections; rerun the full lifecycle. |
| Same run, Ubuntu lifecycle | Both the fresh-checkout WSL fixture and full bundled-install fixture encounter Go older than the required 1.27.1 | Inspect provider isolation and prerequisite setup, then run both strict unchanged-repeat/recovery cases. Hosted simulated WSL remains distinct from native Ubuntu WSL evidence. |

The Ubuntu PowerShell/controller job in the installation run succeeded; this is Linux runtime evidence only. Later steps in failed jobs were skipped, so fixing the first failure does not establish their acceptance. A separate [Completion checks run](https://github.com/5nik7/dots/actions/runs/43579636166) at `d31824db` failed the FSH editor PTY timeout; it was a separate hosted gap when these two workflows were paused. Its subsequent repair and successful hosted acceptance are recorded below; its automatic triggers remain enabled. Earlier native Termux passes are preserved.

Re-enable these two workflows after isolated repairs and successful explicit manual runs of the full Linux/Windows matrices. Restore only the original trigger/filter blocks from `31e07b3a54d5ba00528bf0d0f2aeb2480295c31b`, preserving later job fixes; retain manual dispatch if useful. The [testing reference](../docs/testing.md#hosted-ci-during-platform-development) contains exact manual-run commands. This scheduling change needs no Termux update/test/activation and has no CLI, configuration/menu, completion or installer interface effects. Local documentation, source-only wiki and workflow-structure checks apply; no failing workflow is deliberately rerun merely to verify the pause.

## Completion CI repair — 2026-11-14

The owner requested fixing Completion checks after [run 43647279257](https://github.com/5nik7/dots/actions/runs/43647279257)
failed at `1c2154177330fdda270c290a2393080f48cb098b`. Its FSH suite passed seven
cases and failed the editor case while awaiting initialization. The retained
terminal output shows `compinit -D` stopped at the insecure-directory trust
prompt, before Tab insertion; the four later provider/inventory steps were
skipped. This is a fixture setup failure, not evidence of incorrect insertion
or a reason to increase its deadline.

The FSH private terminal and Blastoff autoload fixture now use `compinit -i -D`
and require successful initialization. Compinit still audits permissions but
excludes insecure function paths without prompting. No `-u`/`-C`, host chmod,
skip conversion or timeout increase is used. A new FSH case creates a single
owned world-writable completion directory, proves the audit detects it, and
requires its path/provider to be absent after initialization. Both that case
and the original editor case retain exact `dots git ` insertion, FSH span and
nonexecution assertions. Runtime startup and completion implementations are
unchanged; configuration/menu, installer and public interface changes are not
needed. The two paused workflows remain manual-only; Completion checks retains
its automatic triggers and all existing steps.

Pre-push source context: Windows `616956a3` plus this fixture/documentation patch;
execution uses Ubuntu WSL Python 3.12.3 and native Bash/Zsh in the owned public
snapshot `/tmp/dots-completion-ci-epvcfx6a`. The existing clean FSH source matches
the workflow pin `4672ad5dd9ad68a7effc1476d65afb7c584ce2b3`; only its committed
files were exported into the fixture. No source acquisition or package change
was required. Owned home/config/data/state/cache/temp roots and an explicit
tool directory exclude personal startup, Git settings and installed consumers.

| Workflow command/check | WSL result | Wall seconds |
| --- | --- | ---: |
| Completion catalog | 1 passed; 296 routes, 299 prefixes, 1030 contexts | 55.366 |
| Delegated/native records | 1 passed | 3.687 |
| Zinit lazy helpers | 1 passed | 0.247 |
| Full FSH input/editor suite | 9 passed, no skips | 10.283 |
| Project completion audit | 7 passed | 0.051 |
| pkgs semantic types | 3 passed | 0.084 |
| Blastoff completion suite | 14 methods completed, no failures/errors; 83 Fish method/subtest skips | 1.491 |
| Anodize selected semantic types | 1 passed | 7.039 |

The owned baseline restored only the old `compinit -D` invocation and ran the
new insecure-path regression: it reproduced the same prompt and timeout in
18.151 seconds. That failed log remains separate from final results. Fish was
unavailable in WSL; skip counts are not independent test-method counts. Commands
ran sequentially, raw bytes/results/environments were retained, and the final
owned-process scan was empty. Local WSL evidence is distinct from the required
fresh hosted run after publication. No native Windows or Termux suite ran in
this batch. Prior phone acceptance is unchanged; the new fixture regression is
not yet native Termux evidence and needs no live phone activation. Source
rollback is limited to the two fixture edits and matching documentation. Wiki
export synchronization remains pending while its checkout is absent.

The first repair was published as `0350bcda2f4d945e19fded5396153d4f0090852f`.
[Hosted run 43648835662](https://github.com/5nik7/dots/actions/runs/43648835662)
passed all nine FSH cases and the project/pkgs steps, confirming the original
blocker was fixed. It exposed the next previously skipped failure: Blastoff's
empty-PATH autoload fixture made compaudit's local `getent` fallback report
`getent:6: command not found: grep`. Anodize remained skipped in that hosted run.

The follow-up enrolls only native `grep` in a test-owned directory while Zsh
initializes, then restores empty PATH, clears command lookup and asserts `grep`
is absent before invoking Blastoff completion. No host PATH restoration or live
permission change is used. A separate owned insecure-directory case proves
audit detection, path/provider exclusion and poison nonexecution. Restoring only
the empty audit PATH in an owned baseline reproduces the exact hosted stderr
in 0.542 seconds. The final WSL Blastoff suite completes 15 methods with no
failures/errors and the same 83 Fish method/subtest skips in 1.702 seconds.
These logs are retained under `blastoff-empty-audit-path/` and
`blastoff-audit-tools/` in the same evidence root. The public completion provider
and its no-external-tools contract remain unchanged. Hosted acceptance must cover
the entire workflow at the follow-up revision, including the unreached Anodize
step; the first repair's partial hosted success is not a whole-workflow pass.

**Hosted acceptance passed:** [run 43649259319](https://github.com/5nik7/dots/actions/runs/43649259319)
completed successfully on 2026-11-14 at repair revision
`e2b60f569b27e6048842044950c00930f18085b4`. All eight test steps and job cleanup
succeeded: catalog 1 case/1030 contexts, records 1, lazy loader 1, FSH 9, project
audit 7, pkgs 3, Blastoff 15 methods and Anodize 1. Blastoff retained 83
unavailable-Fish method/subtest skips; no workflow step was skipped. The full
run closes both reproduced hosted fixture failures. Completion checks remains
automatic; the two separately paused workflows remain manual-only. This hosted
Ubuntu evidence does not replace native Windows/Termux or live visual gates.

## Baseline and evidence boundaries

- Windows: PowerShell 5.1.26100.9818, stable 7.6.10 and preferred Preview
  7.7.0-rc.1; tool shell 7.6.9 is distinct. Python 3.15.2/3.14.10; Go 1.27.4.
- Ubuntu WSL2: Python 3.12.3, Bash 5.2.21, Zsh 5.9; Go 1.22.2 is below
  Anodize's 1.27.1 requirement. Linux and Windows state remain separate.
- Both inventories contain 295 static routes. Auxiliary coverage includes 95
  scripts, 73 distinct shared aliases and 67 shared functions; source inventory
  does not establish runtime or desktop acceptance.
- All 72 tracked Windows links are text placeholders. Do not restore obsolete
  absolute Termux/Clink targets blindly. Canonical palette files still load.
- Windows has no installation receipt. WSL owns only two theme pointers; 24
  applicable mappings are missing and six destinations are occupied. Existing
  correct links do not establish installer ownership.
- Windows Bat inherits a Scoop package-junction configuration destination;
  current preview correctly refuses that reparse point. Preserve that refusal.
- Required baseline suites contain fixture assembly/encoding/runtime-selection
  defects. Retain baseline failures, skips and post-fix evidence separately.
- At the initial audit, no desktop, real clipboard, notification, package activation,
  remote-session continuity or native Termux acceptance was claimed. Later native
  Termux fixture evidence and handoff clipboard delivery are recorded below.
  Wiki checkouts are absent on both hosts; source-only validation is required.

## Batches

### B1: verification, startup and paths

- [x] Repair owned fixture dependencies, stdin, native filenames and narrowly
  proven PowerShell runtime paths without allowing arbitrary writes.
- [x] Fix native help roles, C/UTF-8 literal paths/output, Nu/Xonsh native
  completion/state and standalone registration, and PS5 script encoding.
- [x] Fix Wttr fresh-process generator imports and Wiki CRLF metadata parsing.
- [x] Prepare guarded link restoration inventory; preserve actual live sources.
- [x] Run required native anchors and comparable isolated cold/warm benchmarks.

### B2: bootstrap, files and recovery

- [x] Fix bootstrap PowerShell parsing and native restart argument/status flow.
- [x] Share bounded link-target comparison across installer, Fonts and themes;
  preserve stored digests, reparse refusal and original uninstall baselines.
- [x] Verify native Windows installation, recovery, interruption, rollback and unchanged repeat.
- [x] Prepare selective live plans and Bat user-environment correction after
  source verification; no package-directory replacement or implicit adoption.

### B3: themes, applications and packages

- [x] Add guarded additive Windows Terminal Preview/WezTerm palette connectors.
- [x] Verify native Anodize and bundled literal forwarding; legacy migration activation remains pending.
- [x] Verify Fonts using test-owned dependencies and mocked registrations.
- [x] Repair WinGet fixtures and stale documentation; installed Client
  1.29.380 already satisfies the declared module prerequisite.
- [x] Preserve current theme selection; prepare app-specific activation and
  rollback packets, including separately reviewed WSL Go prerequisite changes.

### B4: interaction and native capabilities

- [x] Align helpers: gitcheck, gitsubmodule, ff, mkcd, Yazi success/cancellation
  and bounded gup publication. Preserve permanent-delete versus recycle meaning.
- [x] Implement Linux/WSL Cleanup providers and native Windows read-only inventory
  with owner-proven roots and active-use refusal. Replace legacy Clear-Cache
  broad deletion with the guarded workflow; never run live cleanup tests.
- [x] Implement bounded native Windows cache/log deletion and private receipts
  with owned native process/handle fixtures. Actual Restart Manager acceptance
  remains pending; build-cache and checkpoint adapters remain separate work.
- [x] Implement native Windows npm/uv-tool/pip/gem/Go adapters under existing
  grammar/scopes; no invented Cargo manager.
- [x] Deliver project selection and native shell handoff through existing menu
  metadata and shared controllers, preserving optional dependencies.
- [ ] Deliver native attention pane/thread/focus/acknowledgement through its
  owner; existing host-owned notification delivery still needs acceptance.
- [x] Add the 19 native utility adapters from the static inventory below;
  preserve named native UX differences and remaining CHT helper gaps. Do not
  count existing equivalent routes or optional demos as absent core behavior.
- [x] Keep exact Android/tmux/X11 mechanisms explicitly OS-specific. Implement
  the supported Windows user-level lock-screen API with literal transport,
  read-only capability preflight and owned async projection checks. Visible
  activation remains pending; no policy/elevation workaround.

### B5: activation and return

- [x] Prepare per-component packets with exact targets, classifications,
  recovery commands, package effects and reload needs; capture new backup and
  receipt IDs only during an approved apply.
- [x] Update canonical documentation, generated manual and source-only Wiki
  checks. No Wiki checkout is available.
- [ ] Rebuild/check the Wiki export when its checkout is available; no implicit
  clone or publication.
- [x] Supply an uncommitted return patch with SHA-256 provenance, shared behavior
  changes and native Termux gates; validate application in an owned baseline tree.
- [x] Harden and preflight the profile/preferences/environment and bounded Git return batch.
- [x] Record native Termux acceptance of that batch at `1c215417`: 49 test-method executions across eight commands, with no failures, errors or method/subtest skips. This closes only the selected gate below.
- [x] Repair native Windows repeat-link identity and preflight the bounded transaction/Bak return batch in owned Windows/WSL roots.
- [x] Record the seven-command native Termux transaction/Bak gate at `5b70964d`: 70 passed and three named skips out of 73 methods; earlier accepted batches stay separate.
- [x] Record bounded native Termux bootstrap/installation acceptance at `23a5bfa5`: 42 passed and six named capability skips out of 48 methods. Full-checkout builds, live applications and desktop acceptance remain separate.
- [x] Preflight the four local-Git installation cases on native Windows/WSL; harden owned templates and fresh, pinned, nonrecursive optional acquisition.
- [x] Record native Termux acceptance of the focused Git-fixture/source-update patch at `135d6b57`: eight methods passed, with no failures, errors or method/subtest skips.
- [x] Harden full-checkout fixture isolation; verify both WSL lifecycle cases, nine theme cases, and separate native Windows connector/controller/Anodize gates.
- [x] Record the focused phone follow-up at `8838841c`: nine native Termux theme methods and two separately classified WSL-profile full-checkout simulations on Android passed, with no failures/errors/skips/timeouts.
- [x] Verify full-checkout native Windows `install.ps1`/`uninstall.ps1` on PowerShell 5.1 and 7, with owned profile discovery destinations, offline native build, unchanged repeat and restoration. Actual KnownFolders and visible/live acceptance remain separate.
- [x] Add the Termux-profile full-checkout fixture and preflight it on WSL alongside both existing WSL-profile lifecycle regressions.
- [x] Record the separate native phone gate at `5d5fca2e`: one Termux-profile full-checkout lifecycle and two WSL-profile regressions on Android, all passed with no failures/errors/skips/timeouts.
- [x] Rehearse packet 3 with all 29 skill links in an owned native Windows
  transaction, including interruption/recovery.
- [x] Apply the separately approved packet 3 with retained backups; verify all
  links, unchanged repeat and native PowerShell undo previews.

### Profile and Git return preflight — 2026-11-14

Source identity: Windows `main` at `358b939f1f2d0cae331f649717e166491f6b06df`
plus this patch. Tests use an owned Ubuntu WSL source snapshot or native Windows
fixture roots. The live `/home/njen/dots` checkout is unchanged. Earlier Termux
records, including the accepted GitTheme follow-up at `788a7fdf`, remain separate;
none of these PC checks establish the next phone gate.

The Git fixture previously inherited arbitrary startup/Python/SSH-agent/Dots
variables and permitted real HTTP(S) transport. It now keeps only inspected
runtime/locale inputs, owns home/config/data/state/cache/runtime/AppData/temp
roots, and permits file transport until its local fake SSH helper is installed.
The new containment suite uses owned poisoning and fake transport positive
controls, plus a portable native Python/Git configuration check. No test contacts
a network service or uses personal Git settings. Callers still supply bounded
executable discovery; Bash publication requires `sha256sum`.

Shell-environment tests now retain the outer runner's inspected Termux prefix,
identity and loader variables and disable autostart. The shared debug fixture
retains `LD_PRELOAD` for Android script execution. Selected-submodule output uses
an explicit owned `modified` color instead of assuming the old ANSI 93 default;
index/HEAD/remote preservation, unchanged repeat, reset and lock assertions stay.
These are fixture repairs, not changes to Git publication, preferences, ordinary
startup, defaults or output contracts. No configuration/menu, completion or
installer integration change is needed. Source rollback restores these fixture
and documentation edits; there are no package or live-application effects.

| Check | Execution | Final result | Wall seconds |
| --- | --- | --- | ---: |
| `test_git_fixture.py` | Ubuntu WSL, Python 3.12.3 | 4/4 passed | 0.191 |
| Same containment suite | Native Windows, Python 3.15.2 | 1 passed, 3 POSIX transport skips | 2.191 |
| `test_profile_backend.py` | Ubuntu WSL, owned source | 13 passed, 1 Linux-context skip out of 14 methods | 8.325 |
| `test_preference_files.py` | Ubuntu WSL, owned source | 8/8 passed | 6.002 |
| `test_shell_environment.py` | Ubuntu WSL, Bash/Zsh | 11 methods completed; 20 Fish/Nu subtest skips, no failures/errors | 14.235 |
| Two `gup` contract/completion cases in `test_shared_shells.py` | Ubuntu WSL, Bash | 2/2 passed | 0.686 |
| Four selected `test_git_operations.py` publication cases | Ubuntu WSL, Bash frontend | 4/4 passed | 2.160 |
| Same four cases, `DOTS_TEST_GIT_FRONTEND=native` | Ubuntu WSL, Python controller | 4/4 passed | 1.260 |
| Selected-submodule index/remote case in `test_git_submodules.py` | Ubuntu WSL, Bash and Python controller | 2/2 passed | 3.386 |

The four Git cases cover staged-only/existing commits, explicit broad staging
with ownership refusal, confirmation/pure preview, and push-URL/configuration
conflicts. The submodule cases use only disposable nested repositories and local
remotes. Controller evidence on WSL is not native Windows shell acceptance.
Fish/Nu were absent from WSL; some backend loops omit unavailable shells without
unittest skips. The backend skip's exact reason is `Linux-context fixture requires
a POSIX host`; actual execution was WSL. Report subtest skips separately from
test-method counts. Durations are process wall time, not startup benchmarks.

Retained failed harness attempts: plain Windows `git archive` applied CRLF
conversion to LF Git blobs, producing `/.` followed by carriage return in a
generated root. The initial backend run had one failure/one skip, and the initial
shell-environment run had three failures/20 subtest skips. Re-exporting with
command-scoped `core.autocrlf=false` and `core.eol=lf`, comparing the TSV blob and
excluding three external absolute links resolved these failures without a
product path change. The first four Bash Git cases also failed because the
outer allowlist lacked `sha256sum`; the first submodule pair included that
harness issue and the stale color assertion. All original outputs remain apart
from the successful final runs; no source assertion was removed.

WSL evidence: `/tmp/dots-return-preflight-sg7n_s6i`, with separate `repo space ü`
and corrected `repo-lf space ü` snapshots, source overlay hashes, owned runtime
tools and per-command raw streams/environment/result records. Native Windows
containment evidence: `%TEMP%/dots-git-fixture-native-f3vti61k`. No personal
startup, packages, themes, services, clipboard or live checkout synchronization
ran. Source-link/manual/source-only wiki validation applies; export synchronization
remains pending without a wiki checkout.

The subsequent Termux prompt named the published repair SHA and authorized only a
clean fast-forward preserving the existing transport, then these eight bounded
commands sequentially and independently. It required fixture/helper inspection,
an owned public source snapshot, native Bash/Zsh and available Fish/Nu, owned
prefix `bin/env`/interpreters, inspected loader variables, explicit tools including
`sha256sum`, raw byte logs and before/after Git/process checks. The result is recorded below, preserving previous acceptance records and the authorized literal-stdin `cpy` delivery instruction. Transactions/Bak, broader packages/cleanup, visible terminals,
desktop consumers and live application acceptance remain subsequent gates.

### Native Termux profile and Git acceptance — 2026-11-14

Evidence source: the receiving Termux agent's inline handoff, supplied by the user. The Windows/WSL lead did not rerun these commands or access the phone's retained files. The physical checkout `/data/data/com.termux/files/home/dots` on `main` fast-forwarded from `31e07b3a54d5ba00528bf0d0f2aeb2480295c31b` to exactly `1c2154177330fdda270c290a2393080f48cb098b`. The authorized `git -c submodule.recurse=false -c gc.auto=0 -c maintenance.auto=false pull --ff-only --no-recurse-submodules origin main` exited 0 in 2.522 seconds. Origin remained `git@github.com:5nik7/dots.git`; no persistent transport change or submodule initialization/update occurred. Preflight found no active update hooks, filters, fsmonitor or custom merge drivers. Required ancestry passed; final `main`, HEAD and cached `origin/main` matched the required commit.

Native context: Android 15/API 35, Termux 0.119.0-beta.3, aarch64, kernel `5.4.274-qgki-30957850-abG996USQSJHZB1`; Python 3.14.10, Git 2.56.1, Bash 5.3.20(1)-release, Zsh 5.9.2, Fish 4.9.3 and Nu 0.117.0. Locale was `C.UTF-8`, preferred encoding UTF-8, Python UTF-8 mode 0. Before command 1, the corrected outer environment was verified as Dots platform `termux`, runtime `android`.

All eight commands ran sequentially, independently and once each from an owned source snapshot. Every command exited 0 with empty stdout and a complete verbose unittest report ending in `OK` on stderr. **49 test-method executions passed, with zero failures, errors, method skips or subtest skips.** Durations are whole-process wall time, not startup benchmarks.

| # | Command or selected cases | Passed / methods | Wall seconds |
| --- | --- | ---: | ---: |
| 1 | `test_git_fixture.py -v` | 4 / 4 | 1.608 |
| 2 | `test_profile_backend.py -v` | 14 / 14 | 39.761 |
| 3 | `test_preference_files.py -v` | 8 / 8 | 22.129 |
| 4 | `test_shell_environment.py -v` | 11 / 11 | 107.521 |
| 5 | Two `SharedShells` `gup` cases below | 2 / 2 | 4.105 |
| 6 | Four `GitOperations` cases below, `DOTS_TEST_GIT_FRONTEND=bash` | 4 / 4 | 16.295 |
| 7 | Same four cases, `DOTS_TEST_GIT_FRONTEND=native` | 4 / 4 | 11.464 |
| 8 | Selected-submodule publication, Bash and Python controller | 2 / 2 | 27.858 |
| Total | Eight commands | 49 / 49 | 230.741 |

Exact commands under the inspected owned environment:

```sh
python -B tools/test_git_fixture.py -v
python -B tools/test_profile_backend.py -v
python -B tools/test_preference_files.py -v
python -B tools/test_shell_environment.py -v
python -B tools/test_shared_shells.py SharedShells.test_gup_uses_bounded_core_publish_and_preserves_status SharedShells.test_gup_completion_reuses_bounded_publish_options -v
DOTS_TEST_GIT_FRONTEND=bash python -B tools/test_git_operations.py GitOperations.test_publish_staged_only_and_existing_commits GitOperations.test_publish_all_and_ownership_block GitOperations.test_publish_requires_confirmation_and_no_dry_run_writes GitOperations.test_publish_checks_push_url_and_conflicting_configuration -v
DOTS_TEST_GIT_FRONTEND=native python -B tools/test_git_operations.py GitOperations.test_publish_staged_only_and_existing_commits GitOperations.test_publish_all_and_ownership_block GitOperations.test_publish_requires_confirmation_and_no_dry_run_writes GitOperations.test_publish_checks_push_url_and_conflicting_configuration -v
python -B tools/test_git_submodules.py Bash.test_selected_publish_preserves_outer_index_and_remote Native.test_selected_publish_preserves_outer_index_and_remote -v
```

Here `native` selects the shared Python controller running on Termux; it does not mean Windows execution. `test_native_git.py` was not substituted. Both frontend values were explicitly supplied and retained in their environment records. Bash/Zsh/Fish were exercised by backend map/checkout-switch loops; Bash/Zsh by inactive-profile reload and `gup`; all four enrolled shells, including Fish/Nu palette refresh, by shell-environment loops. Missing-shell omission did not reduce those loops. PowerShell and Xonsh execution were outside this batch; generated PowerShell assertions provide no native Windows evidence.

The accepted coverage includes Git fixture startup/Python/agent/configuration scrubbing and refusal of forbidden transports before fake helpers execute; profile namespaces, alias collisions, owned mapping/adoption, rollback/undo/drift, preference precedence/migration/import and reload; environment data bytes, provenance, control characters, display-only home abbreviation and owned 40/80/120-column PTYs. Both publication frontends covered staged-only/existing commits, explicit broad staging with ownership refusal, confirmation/pure previews and push-URL/configuration conflicts. Both selected-submodule cases covered child-before-parent publication, outer index/HEAD/remote preservation, explicit amber pending output with reset, unchanged repeat, remote equality and lock removal. No selected assertion was left unreached through failure or skip. Broader Git suites were not run.

Isolation: a command-scoped LF `git archive` snapshot of the required revision was checked against every regular-file Git blob, with modes/internal links preserved. Three external absolute links and the contents of four optional/private Gitlinks were excluded. The 2,849-entry manifest was unchanged after testing. Each command had fresh owned HOME/config/data/state/cache/runtime/temp and Windows-style profile roots, plus `PREFIX` and `TERMUX__PREFIX` ending in `/prefix/usr` with owned `bin/env` and interpreters. An explicit native-tool allowlist included Git upload/receive helpers and `sha256sum`, with resolved paths/hashes retained. No broad host PATH, credentials, agent, ambient Python search path or personal startup settings entered the fixtures. Only inspected Termux version/loader inputs were retained. Git used disposable repositories, inert hooks, synthetic identities and local remotes; SSH and HTTP(S) positive controls used owned fake helpers, with no real test network transport or live package/desktop consumer.

Two preparation issues were caught before command 1 and are excluded from suite totals:

- Initial enrollment stopped at `prepare.py:57` with `AssertionError: getconf`; inventory also found `locale` absent. Neither was needed by the selected execution paths, so enrollment omitted them without a host PATH fallback. The original traceback/attempt record exists as tool-transcript text, without separate original raw subprocess streams or full elapsed time. A bounded reproduction of that exact allowlist assertion exited 1 and retained raw streams, argv, environment and timing under `prepare-allowlist-reproduction/`.
- An owned prefix ending in `/prefix` initially produced platform `linux`, runtime `android`, evidence `operating-system`. Inspection of `platform_info.detect()` showed that an owned prefix used with `TERMUX_VERSION` must end in `/usr`. Changing only the harness to `/prefix/usr` produced platform `termux`, runtime `android`, evidence `termux-prefix` before any suite ran. Both probes are retained; no product source, assertion or deadline changed.

Evidence was reported retained outside the checkout at `/data/data/com.termux/files/home/dots-review-evidence/termux-profile-git-20261114T222231Z`. Directories `01/`–`08/` contain exact argv/environments, raw streams, exit/timing/count/hash results and process scans. Root records include `summary.json`, `run_suite.py` (command numbers 1–8 and an optional fresh evidence label), `base-environment.json`, `allowlist.json`, `source.tar`, `source/`, before/after snapshot manifests, preflight/update/provenance/final Git evidence, preparation attempts/probes/reproduction, `handoff.md` and clipboard records. The inline handoff is the lead's evidence; access to these phone paths is not assumed.

Every post-command scan and the final same-UID `/proc` scan reported no surviving owned processes or permission-denied scans; all eight process groups were gone. Final status including untracked files and submodules was clean, and `git diff --check` exited 0. All four live submodule states matched preflight, including the uninitialized Rainmeter child. Apart from the authorized fast-forward, owned fixture/evidence writes and authorized clipboard attempts, no source edits, commits, pushes, packages, live configuration/themes, personal-shell reloads, services, cleanup or optional/private submodule operations occurred.

**Clipboard delivery failed separately from acceptance.** The inspected `scripts/cpy` wrapper used the real Termux provider with literal stdin and an owned empty preference context verified as `record_copies=false`. Attempt 1 exited 1 after 8.176 seconds with empty stdout and `cpy: Clipboard write timed out (termux-clipboard-set)` on stderr. A single bounded retry supplied only inspected `ANDROID_ROOT`, `ANDROID_DATA`, `ANDROID_ART_ROOT`, `ANDROID_I18N_ROOT` and `ANDROID_TZDATA_ROOT`, retaining the same deadline/history policy; it also exited 1 after 8.169 seconds with the same message. The environment hypothesis was not confirmed. Both temporary provider children exited on their own before any signal, and final scans were empty. No clipboard readback, longer deadline, history/watcher/service change or configuration change was used. Original and retry evidence remain in `clipboard/delivery.json` and `clipboard/delivery-final.json`, with completion process/Git records. The complete handoff was returned normally. Clipboard delivery remains unresolved; these timeouts do not reopen the 49 passing test executions or justify an unreviewed live repair.

**Subsequent user direction — 2026-11-14:** the user reported having to tell the Termux agent to use `termux-clipboard-set` because `cpy` was not working. Future handoff delivery must invoke the inspected native `termux-clipboard-set` directly, bypassing `cpy`. This is the requested delivery workaround; it does not establish the cause of the wrapper timeout or constitute a `cpy` repair. No direct-provider exit code, timing or readback evidence was supplied in this follow-up. Retain the two failed wrapper attempts above and keep the 49 passing tests accepted.

Carry this current instruction into every subsequent Termux prompt:

> Before your final reply, automatically copy the complete handoff addressed to the Windows/WSL lead to the native Termux system clipboard using `termux-clipboard-set` directly, with the handoff text supplied literally on stdin. Do not route this delivery through `cpy`. This clipboard write is explicitly authorized by the user as an exception to an otherwise read-only task boundary. Inspect command resolution and the selected executable or wrapper before use; do not evaluate embedded shell text. Report success or failure and still provide the complete handoff in your final reply. Do not enable clipboard history, watchers or services, or change configuration for delivery. If delivery fails, retain the evidence and provide the handoff normally. Carry this instruction forward.

Include the exact required commit, bounded checks and explicit checkout-update authorization preserving a valid existing SSH/HTTPS transport in acceptance prompts. The provider choice above supersedes earlier `cpy` delivery instructions; their historical success/failure records remain unchanged.

Historical records remain separate: the six-suite acceptance at `b6daf0f7`, subsequent theme repair batches and GitTheme's two distinct passing cases at `788a7fdfe286a13e6e718fa5b1b850ddfdf3e1a9` were not rerun or added to these totals. The phone reported that their four documented `/usr/tmp` evidence directories were already absent; none was removed or recreated during this task. Preserve the committed inline summaries while treating those raw retention paths as unavailable. This batch provides automated native Termux fixture/owned-PTY evidence only. Broader transaction/Bak, package/cleanup, Windows/WSL execution and live/visual application gates remain separate.

### Transaction and Bak follow-up — 2026-11-14

Scope: preflight the seven bounded durability/catalog/Bak/managed-operation/link/completion runners before native Termux acceptance. Work starts from `cbe6ebb23082f2562fb6c479cef388bf492bae15` in the Windows source checkout; WSL runs an owned LF public snapshot, leaving its live checkout unchanged. No package, clipboard, startup, live backup, installation receipt or desktop activation is part of this batch.

Native Windows reproduced an existing `dots link` idempotence defect: `Links.test_replace_backup_noop_and_exact_directory` returned `complete` on repeat instead of `unchanged`. `link_cli.prepare()` compared raw Windows readlink substitution text with an ordinary absolute source path. The repair uses the existing bounded `file_platform.native_link_text()` adapter for comparison only; the original link text, journal digests and source symlink identity remain intact. Extend the existing test to require unchanged link text/digest, backup catalog and transaction history, and exercise the actual PowerShell bridges separately.

Fixture work adds explicitly selected native PowerShell 5.1/7 Bak coverage, preserves the seven POSIX CLI cases, excludes insecure Zsh completion directories while retaining the permission audit, carries the outer owned Termux loader prefix into shell children, and reconciles stale static registration assertions with shared Nu/Xonsh completion metadata. Keep failed harness attempts and unavailable runtime skips separate from final results. Native Termux must run its own selected batch at the eventual published repair commit.

Delivery assessment: file maintenance owns the link repair; no route, option, alias, metadata, human/data output schema or completion grammar changes. No configuration integration change needed: correct-link identity is an existing invariant, not a preference. No menu change needed: existing link entry points and approval semantics remain. Existing core installer delivery already includes the shared controller; no new assets/dependencies. No startup performance path changes. Termux uses the same helper with Windows normalization disabled; its selected safe-link and backup gates remain required. Source rollback restores this bounded comparison/fixture patch; journal schemas and payload layouts do not change, and no live operation is performed by this verification. README/backups/testing documentation describes the corrected existing contract and new native fixture. Source-only wiki validation applies; the wiki checkout remains absent.

Actual contexts: Windows Python 3.15.2, PowerShell 5.1.26100.9818 at `C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe` and PowerShell 7.6.10 at `C:\Program Files\PowerShell\7\pwsh.exe`, explicitly selected per suite. The tool host's bundled PowerShell 7.6.9 was not substituted as the acceptance engine. Ubuntu WSL ran as `njen`/UID 1000, Python 3.12.3, Ubuntu 24.04.5 LTS, kernel `6.18.58.1-microsoft-standard-WSL2`, using native `/usr/bin` executables enrolled into an owned allowlist. Bash/Zsh were available; Fish/Nu/Xonsh/PowerShell were absent from that WSL allowlist. The live WSL checkout was not synchronized or used for tests.

| Runner / selected cases | Execution | Final result | Runner wall seconds |
| --- | --- | --- | ---: |
| `test_file_platform.py -v` | Native Windows | 9 passed, 1 POSIX umask skip | 0.880 |
| `test_backup_catalog.py -v` | Native Windows | 15 passed | 2.586 |
| `test_backup_cli.py NativeBackupCLI -v` | Native Windows PowerShell 5.1 | 6 passed | 38.576 |
| Same native class | Native Windows PowerShell 7 | 6 passed | 23.326 |
| Final preview/cache negative controls | Native Windows PowerShell 7 | 1 passed, repeated subset | 6.353 |
| `Links.test_replace_backup_noop_and_exact_directory` | Native Windows Python | 1 passed after repair | 0.439 |
| `test_file_platform.py -v` | Ubuntu WSL | 8 passed, 2 Windows executable-mode skips | 0.843 |
| `test_backup_catalog.py -v` | Ubuntu WSL | 15 passed | 5.350 |
| `test_backup_cli.py BackupCLI -v` | Ubuntu WSL, Bash/Python controller | 7 passed | 3.790 |
| `test_file_operations.py -v` | Ubuntu WSL, Python controller and owned PTYs | 22 passed | 8.459 |
| `test_safe_link.py -v` | Ubuntu WSL, Bash/Python controller | 9 passed | 3.192 |
| `test_backup_completion.py Completion -v` | Ubuntu WSL | 3 passed | 1.944 |
| `test_backup_shell_completion.py -v` | Ubuntu WSL, installed-shell callbacks | 3 passed, 4 unavailable-shell skips | 1.738 |

The seven final WSL commands count **73 methods: 67 passed and 6 skipped**, with no failures/errors. The shell skips are exactly `fish`, `nu`, `xonsh` and `powershell`, each reported unavailable with no native verification. The platform skips are the two `Windows filename-derived executable mode` cases. Native Windows's one skip is `POSIX permission and umask contract`. No missing requested Windows engine was counted as a skip: an explicit nonexistent engine exited 1 before collection (0.236 seconds). The repeated PowerShell 7 preview case is additional execution of one of its six cases, not a seventh distinct case. Timings include runner overhead/source checks and are not startup benchmarks.

Coverage includes default move/copy and retained restore, occupied-target preservation, whole-batch refusal, catalog/container races, deletion/prune ownership, uninstall baseline protection, rollback, actual abrupt child interruption and recovery, legacy unsuffixed payload reading, native Windows executable-suffixed undo/drift, plain/JSON/quiet and literal/empty operands, source symlink identity on POSIX, and unchanged correct links on both platforms. Core repeat-link assertions retain raw link text/digest, catalog and transaction-history identity; the two real Windows shell bridges also check absolute/relative links, source bytes/mode/mtime and unchanged backup count. Provider tests verify emitted shared Bak names and Nu/Xonsh consumers; installed-shell tests invoke callbacks, not complete editor-insertion or visible-terminal acceptance.

Preserved failures and negative controls:

- The original native repeat-link case failed once with `complete != unchanged` (0.434 seconds). After the comparison repair, that case and both actual Windows shell routes passed. Native UNC execution was not tested; bounded UNC normalization remains fixture evidence.
- WSL's initial completion-provider run had 2 passes/1 failure (1.888 seconds): a stale assertion required literal `dots-bak` text in `init.nu`, although names now come from shared metadata. The replacement checks real inert JSON emission, unchanged owned files, and both consumers; the three final cases passed.
- The new insecure-Zsh-path regression passed. Restoring only the old `compinit -D` in an owned diagnostic copy failed the same case (0.334 seconds) with `not interactive and can't open terminal` / `compinit: initialization aborted`; no production source was reverted.
- Initial native PowerShell harness attempts passed an array as one argument instead of splatting it: 5 failures on 5.1 (9.325 seconds), 5 on 7 (5.519 seconds). The corrected invocation then exposed only owned native startup artifacts: 5.1 had 4 passes/1 failure (24.950 seconds), 7 had 1 pass/4 failures (14.292 seconds), and one focused cache diagnosis failed as expected (3.534 seconds). Core-only profiling suppression left 5.1 with 1 pass/5 Framework-cache failures (25.040 seconds). These are retained harness attempts, not final product failures.

Final Windows containment precreates standard owned AppData directories, redirects module analysis into an owned runtime sibling and suppresses child .NET Core profile gathering. Framework's one exact regular, non-reparse `AppData/Local/Microsoft/Windows/PowerShell/StartupProfileData-NonInteractive` and its precreated parent's mtime are permitted; all other home/config/data/state/cache bytes/modes/mtimes remain asserted. Negative controls reject an unrelated cache file and a directory at the allowed profile filename. This is the existing native-runtime exception, not blanket cache exclusion or a live environment change.

Windows evidence: `C:\Users\njen\dots-review-evidence\bak-native-core-20261114-150105-f5985f56`, with each attempt's raw streams, argv/environment/runtime/source hashes and timings, `summary-final.json` and `owned-process-check.json` (zero remaining owned Python/PowerShell processes). WSL evidence: `/home/njen/dots-review-evidence/transaction-bak-20261114T230136Z`, with original/final 2,849-entry public-source manifests, per-file patch hashes, context/tool identities, owned environments, raw streams, argv/results and process-group records for every attempt. Its command-scoped LF archive excludes the three external absolute links and optional/private Gitlink contents. Every WSL command reported an unchanged source snapshot, no timeout, no cleanup signal and no surviving owned process group. The retained supervisor/archive are also at `C:\Users\njen\dots-review-evidence\transaction-bak-20261114T230136Z`. No live backup, configuration, receipt, package, clipboard, service or personal startup was used as a fixture.

The originally requested phone gate is now accepted in the following record. Broader bootstrap/install repeat/baseline/font/application readers, interruption at every journal boundary, native Windows UNC and editor/desktop acceptance, packages and cleanup remain separate subsequent gates.

### Native Termux transaction/Bak receipt — 2026-11-14

The lead received the inline native report for `5b70964dc099d22430700fca7bbff288cd95d425`, containing transaction repair `64ebcd499103d840cb8de184056f3501f8853b6a`. The phone was already clean on `main` at that revision before and after testing; no fetch, pull or source edit occurred. The separately supplied Windows Python-cache cleanup receipt is acknowledged and closed. Earlier acceptance records remain separate.

Seven commands ran sequentially once each from 23:39:49 to 23:41:55 UTC: **73 collected, 70 passed, three method skips, zero subtest skips/failures/errors/timeouts**, all exit 0. File-platform: 8 passed/2 skipped (2.878 seconds); backup-catalog: 15 passed (4.484); `BackupCLI`: 7 (23.778); file-operations: 22 (52.937); safe-link: 9 (17.780); backup `Completion`: 3 (11.779); backup-shell-completion: 6 passed/1 skipped (12.003). Total supervisor wall time was 125.639 seconds. The two file-platform executable-mode methods skipped with `Windows filename-derived executable mode`; shell `test_powershell` skipped with `powershell is unavailable; no native verification`. Bash, Zsh, Fish, Nu and Xonsh callbacks, including the insecure-Zsh exclusion, passed. Explicit class selections exclude native/imported duplicate classes rather than counting them as skips.

Native context: Android 15/API 35, aarch64, Termux 0.119.0-beta.3, Python 3.14.10, Git 2.56.1, Bash 5.3.20, Zsh 5.9.2, Fish 4.9.3, Nu 0.117.0 and Xonsh 0.25.0; C.UTF-8. The stripped environment explicitly detected `termux`/`android`. Owned roots, a 55-command allowlist, inspected loader variables, owned `/usr` prefixes and a Python `-B` Xonsh wrapper excluded live providers and installed-bytecode writes. Each suite had a fresh process group and a 600-second supervisor bound, with existing per-operation limits unchanged. No harness correction or retry was needed.

Durable phone evidence: `/data/data/com.termux/files/home/dots-review-evidence/termux-transaction-bak-20261114T233626Z`. The lead received inline evidence, not direct artifact access. The report records unchanged 2,833-entry public snapshot, 2,836 tracked live entries and all 38 existing local cache files; clean index/worktree/submodules; `git diff --check` exit 0; no surviving owned processes or denied same-UID scans. No packages, live backups/configuration/themes, startup, services, submodule changes or publication occurred. This closes the bounded phone fixture gate, not native Windows durability, live receipts or desktop acceptance. Direct `termux-clipboard-set` remains the handoff provider; this inline report did not include its delivery exit status, so clipboard delivery is unconfirmed independently of the passing tests.

### Bootstrap and installation preflight — 2026-11-14

Base revision: `5b70964dc099d22430700fca7bbff288cd95d425`. Windows source edits stay in the existing checkout; native Windows and Ubuntu tests use separate owned LF snapshots plus the reviewed patch. Preserve the two pre-existing untracked attachment images. No live WSL checkout update or installation/activation is authorized by these fixtures.

Scope: repair native `install.ps1` runtime discovery, which set `PYLAUNCHER_ALLOW_INSTALL=0` and left `PYLAUNCHER_ALWAYS_INSTALL` active. Both legacy variables enable acquisition by their presence. The installer now uses bootstrap's existing remove-and-restore contract, with inert success/exception/nonzero controls. Harden bootstrap environments, local Git transport, required-engine selection and real-provider tripwires; strengthen adapter preview snapshots and cache-type checks. Keep bootstrap/integration, selective components, preparation and bounded lifecycle checks separate from full checkout/build/consumer acceptance.

Owner: files maintenance and bootstrap guide. Interfaces, help, completion, JSON/human presentation, shared defaults and profile precedence are unchanged. **No configuration integration change needed**: discovery enforces existing acquisition boundaries without a new preference. **No menu change needed**: existing setup/preparation approval remains the interface. Installer delivery is the existing root script; Bash behavior is unchanged and its fixtures remain required. No startup performance path changes. Source rollback restores this reviewed patch; no package or live filesystem transaction needs undo because none is performed. Termux impact is fixture hardening only; the initially pending native phone bootstrap/lifecycle gate is accepted in the separate receipt below.

Actual native contexts: Windows 11 build 26300, Python 3.15.2, PowerShell 5.1.26100.9818 and stable 7.6.10, selected by explicit absolute paths. Git for acquisition was the inspected `C:\Program Files\Git\cmd\git.exe` 2.56.0.windows.4, not the separately installed Scoop shim. Ubuntu 24.04.5 WSL ran as `njen`/UID 1000 with Python 3.12.3, Bash 5.2.21, Git 2.43.0 and kernel `6.18.58.1-microsoft-standard-WSL2`. Test execution crossed 2026-11-14/15 UTC; the user's local date was November 14. The live WSL checkout was not used or updated.

| Runner / selection | Execution platform and shell | Final methods | Wall seconds |
| --- | --- | --- | ---: |
| `test_file_platform.py -v` | Native Windows Python | 9 passed, 1 POSIX skip | 1.056 |
| `test_bootstrap_entry.py NativeBootstrap -v` | Native Windows PowerShell 5.1 | 6 passed | 10.039 |
| `test_installation_adapters.py Adapters -v` | Native Windows PowerShell 5.1 | 9 passed, 3 POSIX skips | 25.094 |
| NativeBootstrap, same selection | Native Windows PowerShell 7 | 6 passed | 9.602 |
| Adapters, same selection | Native Windows PowerShell 7 | 9 passed, 3 POSIX skips | 17.536 |
| `test_bootstrap_integration.py BootstrapIntegration -v` | Native Windows Python | 6 passed | 2.106 |
| `test_setup_components.py SetupComponents -v` | Native Windows Python | 5 passed | 1.041 |
| `test_setup_stages.py SetupStages -v` | Native Windows Python | 5 passed | 0.836 |
| `test_installation.py`, 13 lifecycle methods plus native restart | Native Windows Python/filesystem | 14 passed | 10.357 |
| `test_bootstrap_entry.py Bootstrap -v` | Native Ubuntu WSL POSIX shell/Python | 7 passed | 1.003 |
| BootstrapIntegration, same selection | Native Ubuntu WSL Python | 6 passed | 3.607 |
| SetupComponents, same selection | Native Ubuntu WSL Python | 5 passed | 1.202 |
| SetupStages, same selection | Native Ubuntu WSL Python | 5 passed | 0.548 |
| Adapters, same selection | Native Ubuntu WSL Bash/Python and owned PTYs | 6 passed, 6 capability skips | 4.913 |
| `test_installation.py`, 13 lifecycle methods | Native Ubuntu WSL Python/filesystem | 13 passed | 7.719 |

Final totals count executions by selected runtime: **Windows 76 collected, 69 passed, seven skips; WSL 48 collected, 42 passed, six skips**. Both final sets have zero failures/errors/timeouts. Repeated scenarios across engines/platforms are not additional distinct cases. The two focused Windows controls and earlier attempts are excluded from these totals. Windows skips are the file-platform POSIX umask case and adapter Bash hook, POSIX entry-point and owned-terminal cases per engine. WSL skips are `test_native_catalog_check`, `test_native_installer_python_probe_disables_acquisition_and_restores_environment`, `test_native_mapping_routes`, `test_native_powershell_wrappers`, `test_native_repair_route` (PowerShell absent), and `test_native_windows_link_or_explicit_refusal` (native Windows only). No requested Windows engine or symlink capability was skipped. The WSL file-platform prerequisite remains the earlier passing record; its implementation did not change in this batch.

The exact 13 lifecycle selectors are `InstallationTests.test_dry_run_and_idempotent_install_restore`, `test_fonts_command_install_and_restore`, `test_todo_command_and_skill_lifecycle`, `test_backup_survives_reconciliation`, `test_preserves_preexisting_matching_link_and_user_drift`, `test_reviewed_foreign_link_is_backed_up_and_restored`, `test_catalog_drift_after_preview`, `test_failure_rolls_back_links_and_receipt`, `test_undo_install_restores_receipt`, `test_declined_noninteractive_and_bad_options`, `test_source_drift_after_preview`, `test_interrupted_transaction_recovers_before_retry`, and `test_link_capability_refusal_preserves_existing_config` (each in the same class). Windows additionally runs `test_source_restart_preserves_literal_arguments_and_child_status`. Font/Todo checks install owned command/skill fixtures, not actual fonts or personal goal data. Components, backups and failed preparation retain baselines and refuse drift; the restart case preserves literal/empty operands and child status 47. The adapter PTY case covers 40/80/120 columns, semantic color, completion text and cursor behavior. It is not visible desktop evidence.

Retained failures/controls: the first PS5.1 adapter attempt had 5 passes, four failures and three skips (11.294 seconds), because executable-only Python links in the outer harness could not load adjacent DLLs (`3221225781`); the installer then reached the fixture's intentionally absent bootstrap. Enrolling the inspected Python directory (only Python/Pythonw executables, DLLs and data; no Scripts/package tools) corrected this harness error. An earlier two-case focused run passed but its supervisor terminated one still-exiting owned job process immediately after the runner exited; a bounded three-second exit grace removed the cleanup race, and the two focused cases passed again (1.214 seconds) without termination. No live process was targeted. The initial six bootstrap cases also passed before the final no-user-site/Core-profile suppression adjustment; the table uses the final run.

The initial WSL Adapters run had 5 passes, one failure and six skips (3.150 seconds): the test expected `Planning install`, while the unchanged controller emits `Plan install`. The unmodified HEAD fixture reproduced the same assertion failure in an owned baseline (1.294 seconds). Only the expected text changed; all later color, completion and cursor assertions passed in the final full adapter run. This POSIX-only assertion change does not invalidate the earlier native Windows methods, which skip that method. No renderer or shared presentation behavior changed.

Two intentional controls remain separate: an explicitly missing PowerShell engine exits 1 before collection (0.526 seconds), and restoring the unsafe launcher assignment inside an owned discovery function makes the new inert regression fail on `guarded=false` (1.556 seconds). Restoring the corrected source returns the snapshot to its recorded hash. The actual launcher was not permitted to install anything.

Windows evidence: `C:\Users\njen\dots-review-evidence\bootstrap-native-20261114T235300Z`; WSL evidence: `/home/njen/dots-review-evidence/bootstrap-bounded-20261114T235355Z`, with its supervisor/archive also in the corresponding Windows evidence directory. Each retains raw streams, explicit environments/argv, native context, source/overlay hashes and process records. Both start with 2,833 public source entries, exclude three absolute external links and optional/private Gitlink contents, and use owned homes/config/data/state/cache/temp/runtime roots. Windows uses a kill-on-close job assigned before resuming each runner; WSL uses owned process groups. Final runs show unchanged source snapshots, no timeouts or cleanup signals, and no remaining owned processes. Acquisition uses local repositories and file-only Git transport; native download/package/elevation boundaries are substituted, and no live consumer or startup hook is exposed.

The six-command phone gate is accepted in the following receipt, preserving the accepted transaction/Bak result at `5b70964d` and all earlier batches. Full 29-method installation, Git source-update cases, Go/Anodize full-checkout builds, theme/consumer repairs, package/SDK acquisition, live startup and desktop acceptance remain separately reviewed gates. The simulated fresh-checkout WSL test has not been rerun in this batch and does not establish today's native full-install result. No additional live packet is activated here.

### Native Termux bootstrap/installation receipt — 2026-11-15 UTC

The lead received the inline native report at `23a5bfa52c0a51694f5a2f75a84aa9dfa9e3ba34`. Physical checkout: `/data/data/com.termux/files/home/dots`, branch `main`. The authorized explicit fetch (1.915 seconds) and fast-forward merge (0.164 seconds) moved clean HEAD from `5b70964dc099d22430700fca7bbff288cd95d425` to the required commit. Only that commit was incoming; all ancestry checks passed. Origin remained `git@github.com:5nik7/dots.git`, with no configuration or submodule changes. Existing `pull.rebase=true` was bypassed by the explicit fetch/merge sequence. Final HEAD and cached `origin/main` matched the required revision.

All six requested commands ran once, independently and sequentially, from 00:18:57 to 00:19:47 UTC: **48 collected, 42 passed, six method skips, zero subtest skips/product failures/errors/timeouts**, all exit 0. Supervisor wall time totaled 49.729 seconds.

| Runner / selection | Passed / collected | Skipped | Wall seconds |
| --- | ---: | ---: | ---: |
| `test_bootstrap_entry.py Bootstrap -v` | 7 / 7 | 0 | 3.233 |
| `test_bootstrap_integration.py BootstrapIntegration -v` | 6 / 6 | 0 | 2.891 |
| `test_setup_components.py SetupComponents -v` | 5 / 5 | 0 | 1.777 |
| `test_setup_stages.py SetupStages -v` | 5 / 5 | 0 | 1.120 |
| `test_installation_adapters.py Adapters -v` | 6 / 12 | 6 | 15.030 |
| `test_installation.py`, the 13 lifecycle selectors listed above | 13 / 13 | 0 | 25.678 |

The exact adapter skips were `test_native_catalog_check` (`PowerShell unavailable; native check route not verified`), `test_native_installer_python_probe_disables_acquisition_and_restores_environment` (`PowerShell unavailable; installer Python guard not verified`), `test_native_mapping_routes` (`PowerShell unavailable; native mapping routes not verified`), `test_native_powershell_wrappers` (`PowerShell unavailable`), `test_native_repair_route` (`PowerShell unavailable; native repair acceptance pending`), and `test_native_windows_link_or_explicit_refusal` (`Native Windows capability check`). `NativeBootstrap` was excluded by the requested class selector, not counted as skipped. No assertion in the 42 executed methods was cut short. Earlier broad batches and the unchanged file-platform prerequisite were not rerun.

Native context: Android 15/API 35, aarch64, Termux 0.119.0-beta.3, Python 3.14.10, Git 2.56.1 and Bash 5.3.20; `sh` resolves to Dash, version 0.5.13.5 from installed package metadata. PowerShell engines were absent. Locale was C.UTF-8; the actual stripped environment detected `termux`/`android` with `termux-prefix` evidence. The public LF snapshot retained 2,833 blob-verified entries and internal links/modes, excluding three external absolute links and four optional/private Gitlink contents. Each command owned its home/config/data/state/cache/runtime/temp/application/agent roots, used owned `/usr` prefixes and inspected loader inputs, and had a 52-command native allowlist. Git used file-only transport, isolated configuration, empty templates, inert hooks and disabled fsmonitor/signing. No real package manager or desktop consumer was exposed; the fake bootstrap `pkg` stayed owned. Per-operation assertions/deadlines were unchanged under a 600-second process-group backstop.

A resolved pre-suite harness issue remains separate: `sh --version` exited 2 in 0.018 seconds with `sh: 0: Illegal option --`, causing the external preflight assertion to fail. Dash does not support that option. The external driver switched to `sh -c 'printf shell-ready'` (exit 0, 0.010 seconds) plus read-only installed package metadata. No product/fixture/assertion/deadline changed. All six acceptance commands subsequently ran once; there was no product diagnostic rerun or proposed source repair.

Durable phone evidence: `/data/data/com.termux/files/home/dots-review-evidence/termux-bootstrap-installation-20261115T001500Z`. The lead received the inline report, not direct artifact access. It records clean final Git state and `git diff --check` exit 0; unchanged 2,836 tracked live entries after the fast-forward, all 38 existing cache files, all 2,833 snapshot entries and 151 prior evidence files. Every post-command scan found zero owned survivors; the final same-UID scan covered 40 processes with no permission denials, timeout or termination. The authorized update, owned fixtures and separately authorized clipboard delivery are distinct; no live setup, packages, themes, personal-shell reloads, services, submodule operations or publication occurred on the phone.

This closes only the bounded native Termux bootstrap/installation gate. Its measured 42/48 result is independent of the supplied Windows/WSL totals. Full-checkout/build, remaining Git source-update/acquisition and theme/consumer cases, actual package providers and live/visual installation remain pending. The following section records the subsequent four-case local-Git preflight; no additional phone action is required by this receipt alone. Direct `termux-clipboard-set` remains the required handoff provider. The inline report names `clipboard-delivery.json` but omits the actual delivery exit status, so clipboard success is unconfirmed independently of the accepted test gate.

### Local Git source-update preflight — 2026-11-15 UTC

Scope: `23a5bfa52c0a51694f5a2f75a84aa9dfa9e3ba34` plus the three test-file changes in this batch. No installer runtime, route, preference, shared default, startup or application file changed. `tools/test_git_operations.py` now supplies an empty owned `GIT_TEMPLATE_DIR`; `tools/test_git_fixture.py` proves ambient templates are excluded using an inert marker and an owned positive control. The optional-source case in `tools/test_installation.py` now uses a fresh clone without a cached child, advances the local source beyond the recorded gitlink, verifies acquisition at that exact pin, and requires the nested child to remain uninitialized. No real network or optional/private repository is involved.

| Check | Native Windows | Native Ubuntu WSL |
| --- | --- | --- |
| `tools/test_git_fixture.py` | 4 collected: 1 passed, 3 POSIX-only skips; exit 0, 1.906 seconds | 4/4 passed; exit 0, 0.344 seconds |
| Four [source-update selectors](../docs/testing.md#checkout-installation) | 4/4 passed; exit 0, 51.514 seconds | 4/4 passed; exit 0, 3.995 seconds |

Windows executed the shared Python controller on Windows 11 build 26300 using Python 3.15.2 and native Git 2.56.0.windows.4. PowerShell launched the supervisor, but these methods do not test PowerShell wrappers. The three Windows skips are `test_ambient_startup_agents_and_configuration_are_not_inherited`, `test_forbidden_transports_refuse_before_owned_helpers_execute`, and `test_owned_remote_enables_only_local_ssh_and_preserves_push`, each with reason `requires native POSIX Bash and Git for owned transport fixtures`. Native Windows symlink capability was available; no installation case skipped. Git's own bundled shell utilities implement its submodule machinery; Dots invokes the native shared Python controller without Bash or WSL routing.

WSL executed explicitly in Ubuntu as user `njen` (UID 1000), using Python 3.12.3, Git 2.43.0 and Bash 5.2.21 on Ubuntu 24.04.5 LTS, kernel `6.18.58.1-microsoft-standard-WSL2`. The separate live `/home/njen/dots` checkout was not updated. These are eight method executions per platform (Windows five passes/three skips; WSL eight passes), not sixteen distinct cases or full installation acceptance. Durations are whole-command wall time, not startup benchmarks. Every final command exited 0, with no timeout, forced termination or surviving owned process, and an unchanged input snapshot.

The tests retain preview HEAD/FETCH_HEAD preservation, original backup recovery after fast-forward, dirty/diverged refusal, ignored-content preservation and collision refusal, explicit optional selection, exact pinning and nonrecursion. They do not claim preservation of every ref/object during preview or absence of fetch metadata after a divergence refusal. A separate WSL negative control added `--recursive` only to the disposable controller snapshot. The optional-source case failed at the new nested `.git` assertion (one expected failure, exit 1, 1.741 seconds); the original controller bytes were restored and SHA-256 verified. This deliberate failure is excluded from passing totals.

Evidence roots: `C:\Users\njen\dots-review-evidence\source-update-native-20261115T003000Z` and `/home/njen/dots-review-evidence/source-update-wsl-20261115T003000Z`; the WSL supervisor/archive also reside in the corresponding Windows evidence directory. Each snapshot starts from 2,833 public entries, excluding three absolute external links and optional/private Gitlink contents. Retained overlays identify the exact test bytes; native and WSL normalized hashes match. Homes, configuration, state, cache, temp, templates, hooks, identities and local remotes are owned; tool allowlists exclude package managers and live consumers. Windows uses a kill-on-close job assigned before resume; WSL uses an owned process group, both with a 600-second command backstop. Raw streams, argv/environment, timings, source manifests and process records remain available. A preparation-script marker lookup failed before any suite (`ValueError: substring not found`); correcting that external helper enabled preparation without changing source assertions or deadlines. It is not a product-test failure.

Owner: files maintenance for installation and Git maintenance for shared fixture containment. Configuration/menu/presentation integration: no change needed because only tests and documentation changed; both shell entry points, completion and machine-output contracts remain unchanged. Termux impact is stronger portable fixture coverage, with no activation step or live configuration effect. The subsequent receipt accepts Git fixture containment and the four selected installation methods at `135d6b57`; all previous accepted phone records remain separate. Full-checkout/Go builds, theme/consumer installation, native wrapper/desktop and live packets remain separate. Relative-link validation passed (1,465 links in 175 files), source-only wiki validation is healthy, and `git diff --check` passed. The configured `C:\Users\njen\repos\dots.wiki` checkout is absent, so wiki export synchronization remains pending. Rollback of this test/documentation patch has no live installation or package effects; preserve prior acceptance records when reverting any fixture change.

### Native Termux local-Git source-update receipt — 2026-11-15 UTC

Evidence source: the receiving Termux agent's inline handoff supplied by the user. The lead did not rerun phone commands or access phone-local artifacts. The physical checkout `/data/data/com.termux/files/home/dots`, owned by native Termux UID 11043 on `main`, fast-forwarded from `23a5bfa52c0a51694f5a2f75a84aa9dfa9e3ba34` to exactly `135d6b57ddac789b18a82d7e4dadb2540e627c8d`. The explicit nonrecursive, no-prune/no-tags fetch and exact-commit `merge --ff-only --no-autostash` exited 0 in 1.491 and 0.205 seconds. Both ancestry gates, incoming-history/stat inspection and final required ancestry passed. Only the expected seven test/documentation files arrived. Origin remained `git@github.com:5nik7/dots.git`; clean status, configuration, inactive sample hooks and real submodule states were preserved.

| Exact bounded command | Collected / passed | Method / subtest skips | Exit | Wall time |
| --- | --- | --- | --- | --- |
| `python -B tools/test_git_fixture.py GitFixture -v` | 4 / 4 | 0 / 0 | 0 | 2.081 s |
| `python -B tools/test_installation.py InstallationTests.test_update_fast_forward_and_original_backup InstallationTests.test_update_dirty_and_diverged_refused InstallationTests.test_update_preserves_ignored_content InstallationTests.test_optional_source_download_is_explicit_and_nonrecursive -v` | 4 / 4 | 0 / 0 | 0 | 21.837 s |

Both commands ran once, sequentially and independently, beginning at 00:48:09.825160 and 00:48:11.969472 UTC. Total whole-command time was 23.918 seconds; unittest times were 1.436 and 21.254 seconds. All eight methods passed with no failures, errors, missing prerequisites, timeouts or unreached selected assertions. All three POSIX GitFixture cases skipped on Windows executed here. No acceptance-harness correction, source fix, assertion/deadline change or phone negative-control mutation was needed. The intentional recursive WSL control remains separate PC evidence.

Native runtime: Android 15/API 35, aarch64, Termux 0.119.0-beta.3, Python 3.14.10, Git 2.56.1, Bash 5.3.20(1)-release and native Dash 0.5.13.5 (installed metadata plus a passing shell smoke probe), locale `C.UTF-8`. The actual outer environment reported platform `termux`, runtime `android`, architecture `aarch64`, evidence `termux-prefix`. The revision-bound LF snapshot verified all 2,833 public file/link entries against Git blobs, preserved executable modes/internal links and excluded three external absolute links and all four Gitlink contents. Snapshot manifest SHA-256: `1039bd7d720ef050d9b38bd3a4ed904c81278fa1afb1a520307683dd79fbecd2`.

Each command owned HOME/config/data/state/cache/runtime/temp/application/agent roots, with both prefixes ending in `/usr`, owned `bin/env` and interpreters, and a 52-command allowlist. Only inspected Termux version/loader inputs were retained. Git used an owned literal-argv launcher/helper directory; its child-PATH probe showed only owned helper and prefix directories. Configuration/templates/hooks were owned, signing/fsmonitor disabled, and installation transport file-only. GitFixture's positive controls used owned fake HTTP/HTTPS/SSH helpers and local repositories. No real network helper, credential, package manager or live consumer entered the fixtures. Owned process groups had a 600-second backstop; existing 40-second GitFixture and 90-second installation CLI deadlines remained unchanged. This is scoped environment/process containment, not an OS security sandbox.

The accepted assertions cover template exclusion and its marker-copy control, startup/configuration containment, forbidden transport refusal, local fake SSH publication, preview HEAD/FETCH_HEAD preservation, fast-forward and original backup restoration, dirty/diverged refusal, ignored collision refusal, and explicit acquisition of the exact optional pin from a fresh clone with no nested checkout/sentinel. They do not establish every ref/object's immutability during preview or absence of fetch metadata after divergence refusal.

Durable evidence: `/data/data/com.termux/files/home/dots-review-evidence/termux-local-git-20261115T004551Z`. It retains update/provenance journals, archive/manifests, helper/runtime hashes, fixture/supervisor review, per-command argv/environment/raw streams/results/process checks in `01` and `02`, preservation records and `lead-handoff.txt`. Final HEAD and cached `origin/main` matched the tested revision; status including untracked files/submodules and staged/unstaged diffs was empty, and `git diff --check` passed. All 2,836 post-update live tracked entries, 2,833 snapshot entries, 38 existing local caches and 229 recorded historical evidence files remained unchanged. Each post-command scan and the final same-UID 33-process scan found zero owned survivors, with no permission denials or forced termination.

This closes only the eight-method native Termux GitFixture/local-Git source-update gate. Preserve bootstrap/installation at `23a5bfa5` (42 passes/six capability skips), transaction/Bak at `5b70964d`, the cache-cleanup receipt and all earlier records independently. Native PowerShell wrappers, full-checkout/build, remaining theme/consumer installation, actual package providers and live/visual acceptance remain separate. No additional phone action or source repair is required by this receipt. The handoff refers to separate clipboard metadata but supplies no actual provider exit status, so delivery success is unconfirmed; direct `termux-clipboard-set` with normal native runtime and literal stdin remains the required future delivery method.

The following preflight covers `test_fresh_checkout_wsl_setup_connectors_check_and_restore` and `test_full_checkout_bundled_install_repeat_and_restore`, their theme/consumer dependencies and owned Anodize build inputs. Both current methods skip native Windows and force WSL detection on POSIX; running them on Termux remains WSL-profile simulation. Native Windows lifecycle coverage and live packets retain their separate boundaries.

### Full-checkout and theme lifecycle preflight — 2026-11-15 UTC

Scope: `135d6b57ddac789b18a82d7e4dadb2540e627c8d` plus this batch's `tools/test_installation.py` fixture patch. No runtime implementation changed. The full-checkout environment previously discarded outer Git transport/template controls and Go safeguards. It now constructs empty owned templates/hooks, file-only Git transport, disabled signing/automatic maintenance, local/offline Go and owned compiler temporary storage. Installation uses `--offline`; uninstall keeps its supported arguments. An owned telemetry `mode` file disables collection after the unchanged pure-preview assertion and before compilation. Retaining `TERMUX__PREFIX` supports owned loader redirection; the fixture explicitly checks WSL detection and refuses a canonical live Termux prefix that would override it.

Anodize's module requires Go 1.27.1 and currently has no external module dependencies. WSL's default `/usr/bin/go` resolves to Go 1.22.2 and was not used for acceptance. The already installed native `/home/njen/go/pkg/mod/golang.org/toolchain@v0.0.1-go1.27.1.linux-amd64/bin/go` supplied the build without acquisition. Windows used `C:\Program Files\Go\bin\go.exe`; an owned native version probe reported `go1.27.4 windows/amd64`, and `go env GOTELEMETRY GOTELEMETRYDIR` confirmed `off` in the owned config root. Setting a `GOTELEMETRY` environment variable alone is not effective. No compiler, package or dependency was installed or upgraded.

| Final bounded command / selectors | Execution | Result | Wall time |
| --- | --- | --- | --- |
| `tools/test_installation.py InstallationTests.test_fresh_checkout_wsl_setup_connectors_check_and_restore -v` | Native Ubuntu WSL, explicit WSL-profile fixture | 1/1 passed | 15.127 s |
| `tools/test_installation.py InstallationTests.test_full_checkout_bundled_install_repeat_and_restore -v` | Native Ubuntu WSL, explicit WSL-profile fixture | 1/1 passed | 15.799 s |
| Nine theme lifecycle selectors below | Native Ubuntu WSL | 9/9 passed | 49.828 s |
| `tools/test_installation.py` eza and Leaf connector selectors | Native Windows Python controller | 2/2 passed | 7.587 s |
| `tools/test_native_cli.py` four setup/publication selectors below | Native Windows Python controller | 4/4 passed | 12.385 s |
| `tools/verify_anodize.py check` | Native Windows Go build/test/vet and Python authoring/publication | Go checks passed; 3/3 Python methods passed | 38.436 s |

All Python commands use `-B`; the Windows supervisor also uses `-s`. Final results have no failures, errors, method skips, timeouts, forced terminations or surviving owned processes. Windows totals nine Python methods plus Go build/test/vet; WSL totals eleven methods, including real Anodize Go tests/build during each full installation. These are separate runtime executions, not a single rerun of all 29 installation methods. PowerShell launches the Windows supervisor but these selected cases invoke Python directly; no new PowerShell 5.1/7 wrapper acceptance is claimed.

The nine WSL theme selectors, all in `InstallationTests`, are `test_eza_setup_respects_destination_and_restore`, `test_leaf_setup_two_connectors_and_restore`, `test_legacy_vivid_setup_notice_json_and_repeat`, `test_legacy_vivid_setup_human_notice_and_custom_failure`, `test_theme_output_and_pointer_repair_retains_baseline`, `test_failed_theme_repair_does_not_publish_or_change_receipt`, `test_theme_repair_publication_failure_rolls_back`, `test_incomplete_preparation_and_foreign_pointer_are_refused`, and `test_real_theme_install_repeat_and_restore`. Windows runs the first two separately. The four `NativeCLI` selectors are `test_native_setup_inspection_is_read_only`, `test_native_setup_preparation_flushes_without_publication`, `test_native_publication_undo_idempotence_and_drift`, and `test_native_publication_rolls_back_after_live_replacement`.

The strict full case verifies unchanged second installation, all prepared template artifacts, fixed connector targets, FSH dry-run checking, uninstall and source retention. The bundled case verifies Blastoff/pkgs assets, repeat and removal but permits theme changes on repeat; it does not replace the strict no-op case. Theme cases retain old baselines through missing-output/pointer repair, custom-render failure, injected publication failure, incomplete generation and foreign-pointer refusal, plus normal publication and uninstall under POSIX umasks `022` and `077`. Native cases cover real filesystem connectors, pure inspection, preparation without active-pointer publication, idempotence, drift refusal and recovery; app reloads are substituted. Leaf is connector configuration only, not a Rust build. Native Anodize exercises actual engine authoring/export/bridge and owned palette publication, not visible rendering.

Retained earlier attempts remain separate. The unmodified strict case passed under policy-enforcing owned wrappers (15.652 seconds), establishing no reproduced runtime failure. The first hardened fixture applied the install-only `--offline` flag to uninstall and failed there after successful install/repeat (one failure, exit 1, 11.740 seconds); the controller correctly rejected it. The fixture now supplies the flag only for `install.sh`. Initial corrected strict/bundled runs also passed (16.057/15.862 seconds); both were rerun after adding the explicit WSL-prefix guard. No assertion or deadline was weakened. Final Go wrappers assert the fixture's offline/local/telemetry/cache controls rather than adding missing controls; final Git uses the native binary without a policy-repair wrapper.

Windows evidence: `C:\Users\njen\dots-review-evidence\full-install-native-20261115T010000Z`. WSL evidence: `/home/njen/dots-review-evidence/full-install-20261115T010000Z`, with its archive/supervisors also in the corresponding Windows directory. Each owns a 2,833-entry public LF snapshot, excluding three external absolute links and optional/private Gitlink contents. Only the WSL snapshot receives an owned Git index for source enumeration; no live refs/remotes are copied. Both preserve source manifests and raw logs, argv/environment, patch/tool hashes, timings and process checks. WSL uses Python 3.12.3 and native Git/Bash; Windows uses Python 3.15.2. Owned homes/config/state/cache/temp, native-tool allowlists and process groups/jobs keep consumers and build effects outside live installations. No native application clients or real Vivid provider are enrolled; the legacy Vivid cases use the existing owned stub. The whole-command backstop and existing operation deadlines remain bounded. The two existing untracked image attachments are preserved.

Owner: files maintenance, with theme and Anodize maintenance review. Configuration/menu/presentation assessment: no change needed because only tests and documentation changed; all routes, defaults, output contracts and application configuration remain unchanged. Source rollback removes the fixture patch without undoing any live installation/package effect. The following receipt accepts the bounded phone follow-up: nine native theme methods and two separately classified WSL-profile simulations. Preserve all accepted earlier batches. Native Termux-profile full-checkout installation, native Windows full-checkout wrapper equivalence, real Leaf/package acquisition, application/desktop rendering and live packets remain separate. Relative-link checks passed (1,468 links in 175 files), source-only wiki checks are healthy, and `git diff --check` passed. Wiki export synchronization remains pending while the configured checkout is absent.

### Native Termux theme and simulated full-checkout receipt — 2026-11-15 UTC

Evidence source: the receiving Termux agent's inline handoff supplied by the user. The lead did not rerun phone commands or access its retained artifacts. The same-UID-owned physical checkout `/data/data/com.termux/files/home/dots` (UID 11043), on `main`, fast-forwarded from `135d6b57ddac789b18a82d7e4dadb2540e627c8d` to exactly `8838841cd6d48dd8ef37bc5259317a5b48ed5fbd`. The explicit nonrecursive fetch and exact-commit `merge --ff-only --no-autostash` exited 0 in 1.470 and 0.310 seconds. Required/upstream and old-HEAD/required ancestry, incoming history/stat and final ancestry checks passed. Only the expected five fixture/documentation files arrived (92 insertions, nine deletions). Origin remained `git@github.com:5nik7/dots.git`; clean status, configuration, inactive sample hooks and real submodule states were preserved.

| Command, each using `python -B tools/test_installation.py ... -v` | Execution context | Collected / passed | Wall time / unittest time |
| --- | --- | --- | --- |
| Nine theme/connector selectors listed in the preceding PC preflight | Native Termux profile on Android | 9 / 9 | 323.066 / 322.452 s |
| `InstallationTests.test_fresh_checkout_wsl_setup_connectors_check_and_restore` | WSL-profile simulation on native Android | 1 / 1 | 88.523 / 87.854 s |
| `InstallationTests.test_full_checkout_bundled_install_repeat_and_restore` | WSL-profile simulation on native Android | 1 / 1 | 87.104 / 86.440 s |

All three commands ran once, sequentially and independently, starting at 01:17:32.073552, 01:22:55.212115 and 01:24:23.801933 UTC. All exited 0; stdout was empty. Eleven methods passed with zero failures, errors, method/subtest skips, timeouts or unreached selected assertions. Total whole-command time was 498.693 seconds, not a startup benchmark. Keep the nine native profile cases distinct from the two simulated-profile cases; neither is a rerun of earlier accepted batches or native Windows evidence.

Native context: Android 15/API 35, aarch64, Termux 0.119.0-beta.3, Python 3.14.10, Git 2.56.1, Bash 5.3.20(1)-release, Dash 0.5.13.5 (installed metadata plus smoke probe), locale `C.UTF-8`. The actual outer environment selected `termux`/`android` with `termux-prefix` evidence. The already installed native Go resolved to `/data/data/com.termux/files/usr/lib/go/bin/go`; an isolated offline probe reported `go1.27.3 android/arm64`, with native GOROOT `/data/data/com.termux/files/usr/lib/go`. No compiler/package was acquired. Executable SHA-256: `ad103cdd7d64525e119d6061dd92747c9084e70ede77a87f0d1190be377b85b5`.

The full fixtures explicitly omitted `PREFIX`/`TERMUX_VERSION`, retained the owned `TERMUX__PREFIX` loader alias, set `WSL_DISTRO_NAME=Fixture` and asserted WSL detection. The Go invocation audit observed inner Dots platform `wsl`, runtime `linux`, evidence `wsl-environment`; the physical host and compiler target remained Android/arm64. These are not native Termux-profile full installations or native WSL-host runs. Both executed real `go test ./...` and `go build -trimpath -o <owned-work>/anodize-engine ./cmd/anodize-engine`, each exiting 0. Strict test/build times were 21.789/12.926 seconds; bundled times were 17.742/13.142 seconds. Version/reuse probes passed. The engine package reported `ok`; three other packages reported `[no test files]`, not Python method skips. No separate phone vet/authoring batch ran.

Both builds recorded source identity `246b1b814610c28b3cda96811489b72aa1e98d146b0518c29c6da853a0dd5664` and produced a 4,925,068-byte artifact with SHA-256 `df2bf8722d8d6e99fd4f0d3774e0662febd59b1ad6123fc997ea51e30a182529`. The native theme cases retained artifact-repair subtests for `fsh.ini`, `colors.json` and `yazi/tmtheme.xml`, plus normal publication/restoration under umasks `022` and `077`. Reload/after-publication callbacks were substituted. The strict full case accepted unchanged repeat, default components, generated artifacts/connectors, FSH checking, optional-source noninitialization, uninstall and source retention. The bundled case accepted its asset/removal checks but permits theme-only repeat changes and does not replace the strict case. Leaf remains connector configuration, not a Rust build.

Isolation: 2,833 public snapshot entries were verified against committed bytes, modes and internal link targets, excluding three external absolute links and all four Gitlink contents. Test-file LF SHA-256 matched `950147fd2b1475ecc58bcc627fe2bac2279392a1181d895a1a25587a5824b3b5`; snapshot manifest SHA-256 was `9ad55b450bf294c1d5bca23bd8579f7378b5526e0e0ff31fd6fd3fb4158fba4c`. The owned source index contained exactly those entries with no commits, refs or remotes; its unchanged SHA-256 was `979b38c346b9afc018a7a2c8ce04f97b4493b927b3a3d706924d5487c2e3c7ed`. Each command owned home/config/data/state/cache/runtime/temp/application/agent roots and used a 54-command allowlist, including all theme prerequisites, inspected native helpers and guarded Go. Live consumers, real Vivid, package managers, credentials and broad host PATH were absent. Legacy Vivid stubs were unchanged. The Go guard verified offline/local/no-VCS behavior, owned cache/temp/GOPATH roots and real telemetry `mode=off` files without supplying missing controls. The source module had no external dependencies. Owned process groups used a 600-second command backstop, preserving original 90-second ordinary CLI, 600-second full CLI/Go and 20-second version deadlines. No timeout or cleanup signal occurred.

One external preparation error remains separate: the first owned-index verifier assumed every index hash equaled the raw committed source hash and failed on `shells/powershell/Scripts/Get-Scripts.ps1` before acceptance or Go execution. A bounded diagnostic proved exactly two pre-existing CRLF blobs, that file and `show-notification.ps1`, were normalized to LF only in the owned index by reviewed `* text=auto`; source bytes remained identical to the committed blobs. The corrected external verifier validated all 2,833 entries/modes and those exact conversions. No repository source, fixture assertion or deadline changed. Future owned-index preparation must distinguish verified source bytes from reviewed Git clean normalization rather than assuming universal hash equality. No product failure, missing prerequisite, containment failure or negative-control mutation occurred.

Durable evidence: `/data/data/com.termux/files/home/dots-review-evidence/termux-theme-full-checkout-20261115T011251Z`. It retains update/provenance journals, snapshot/index and preservation manifests, reviewed fixtures/supervisors, runtime/Go identities and controls, raw Go build/test streams and artifact identities, command directories `01`/`02`/`03`, the resolved preparation diagnostic, process checks and `lead-handoff.txt`. Final HEAD/cached `origin/main` matched the required revision; full status and staged/unstaged diffs were empty, and `git diff --check` exited 0. All 2,836 post-update live tracked entries, 2,833 snapshot entries, the owned index, 38 pre-existing Python caches and 281 historical evidence files were preserved. The native tool/helper hashes, Go executable and eight tool binaries were unchanged. Per-command and final same-UID scans found zero owned survivors; the final scan covered 33 visible processes with zero permission denials or forced termination.

Disposition: this closes the nine-method native Termux theme gate and the two explicitly simulated WSL-profile full-checkout gates at `8838841c`, independently of earlier phone and PC records. No source repair or additional phone action is required by this receipt. Native Termux-profile full-checkout installation, native Windows PowerShell wrapper equivalence, actual package/Leaf acquisition and visible/live acceptance remain pending. Clipboard delivery metadata is referenced, but no actual provider exit status appears in the supplied handoff, so delivery success remains unconfirmed. Future delivery continues to require direct `termux-clipboard-set` with literal stdin and normal native runtime, independently of test acceptance.

Next bounded PC preflight: establish full-checkout lifecycle coverage through native Windows `install.ps1`/`uninstall.ps1` on PowerShell 5.1 and 7. Review native `$PROFILE` discovery, application destinations, link capability and Go preparation under owned roots before executing wrappers. Existing Python-controller and POSIX full-checkout passes do not satisfy that gate. Keep live activation packets and package acquisition outside this fixture work; a separate native Termux-profile full-checkout gate must preserve its own prefix mappings rather than relabeling the accepted WSL simulation.

#### Native Windows full-wrapper acceptance — 2026-11-15 UTC

Added `tools/test_native_installation.py`; source identity is `8838841cd6d48dd8ef37bc5259317a5b48ed5fbd` plus this Windows-only test and documentation patch. No product implementation changed. The actual native wrappers, child-engine discovery/JSON transport and default six-component preparation remain intact. Only the copied discovery payload and launching process bind `$PROFILE.CurrentUserAllHosts` to two owned paths under a Unicode redirected-Documents fixture. This is injected destination coverage, not real KnownFolders or desktop acceptance. The fixture copies tracked public inputs, excluding Gitlinks and external absolute links, including native scripts and Windows resources. It constructs owned app/config/state/build roots, uses offline preinstalled Go and explicit runtime enrollment, and rejects lexical/resolved preview target escapes before apply.

Both serial commands were `python -B tools/test_native_installation.py -v` (the outer supervisor also disables user-site loading with `-s`), selecting the engine through an explicit `DOTS_TEST_POWERSHELL` path:

| Selected wrapper engine | Collected / passed | Failures / errors / skips | Whole-command / unittest time |
| --- | ---: | --- | --- |
| Windows PowerShell 5.1.26100.9818 | 1 / 1 | 0 / 0 / 0 | 49.070 / 48.017 s |
| Native PowerShell 7.6.9 | 1 / 1 | 0 / 0 / 0 | 47.947 / 46.722 s |

These are two successful executions of one lifecycle method, not two distinct methods. Both native engines participated in child-profile discovery in each execution. Accepted assertions include pure preview with narrow runtime-cache allowances; both owned profile destinations; all six default components; actual Windows PE Anodize compilation/publication; generated template artifacts; bundled native commands; unchanged second apply and exact receipt; drift-preserving uninstall preview without modifying the injected edit; restored original profile bytes; removed managed launchers/artifacts; preserved source files; and no initialized optional/private repositories. The drift check is a read-only uninstall preview, not an additional destructive uninstall with drift. No failures, diagnostic reruns, timeout extensions or weakened assertions occurred after the preflight review.

Runtime: native Windows 11 Pro build 26300, Python 3.15.2, Git for Windows 2.56.0.windows.4, Go 1.27.4 windows/amd64. PowerShell 5.1 was `C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe`. The previously recorded `C:\Program Files\PowerShell\7\pwsh.exe` was absent during this preflight, so the selected native 7.6.9 executable was the inspected Codex runtime at `C:\Program Files\WindowsApps\OpenAI.CodexPrimaryRuntime.v26-1110-778-0_26.1110.778.0_x64__3k8sg7r9htsxt\dependencies\native\powershell\pwsh.exe`. No WindowsApps execution alias, updating launcher or personal profile was invoked. The separate owned Go probe confirmed `GOTELEMETRY=off` and an owned telemetry directory; no compiler acquisition occurred.

Evidence root: `C:\Users\njen\dots-review-evidence\windows-full-wrappers-20261115T020000Z`. It retains the LF archive/public snapshot and owned index, overlay/source manifests, inspected runner, initial configured context and corrected engine path, `ps51-first` and `ps7-first` argv/environments/raw streams/results, and `native-go-probe` identity/output. The final test-file SHA-256 is `f45349957ba8e12bd591923be1c79fd63d4e177326391a15f155579a48bdb98d`. Each Windows Job Object contained 531 processes, finished with zero active children and required no termination; both source snapshots remained unchanged. The 600-second supervisor and per-wrapper deadlines remained intact. Runtime-only startup files were permitted narrowly, not by excluding all cache changes.

No interface/help/completion/presentation, configuration/menu integration, shared-default or startup change was needed. Existing file-platform and shared lifecycle prerequisites remain historical passing evidence rather than rerun totals. Test/docs rollback removes only this reviewed patch; no live transaction or package effect needs undo. Native Termux requires no new acceptance for this Windows-only fixture; its accepted receipt above remains separate. Real KnownFolders/redirected Documents, personal-shell activation, package/Leaf acquisition, native Termux-profile full-checkout installation and visible desktop behavior remain named gates. Source documentation/link and source-only wiki validation passed; wiki export remains pending because its checkout is absent. No live activation packet was applied.

### Native Termux-profile full-checkout preflight — 2026-11-15 UTC

Added `InstallationTests.test_fresh_checkout_termux_setup_connectors_check_and_restore` to the existing owned full-checkout helper. The two existing callers retain their WSL selection and both passed as regressions. The helper now includes profile `config.json`; the Termux case also copies tracked Termux configuration and the core manual. Both owned prefix variables end in the same `/usr`, with native interpreter aliases and `TERMUX_VERSION`. Every reported target must remain lexically and physically inside the fixture before apply. The two absolute phone-local source links are excluded, then the copied fixture receives a separate regular source-color baseline plus original home `.termux` colors/note and prefix Figlet/manual files. Accepted assertions retain pure preview at the byte/mode/link/directory-population level; six default components; actual offline Anodize build; physical color connector/receipt ownership through the managed `.termux` directory; exact unchanged receipt/repeat; bundled assets; and restoration of all seeded originals and source bytes. No Android consumer or personal shell is invoked.

Files maintenance owns this test-only batch. No product route, preference, presentation, menu, startup, package or shared-default change was needed; no new configuration integration is needed. Source identity is `43f17eea5c09d8973c1dc187ba345e439915ac8a` plus this fixture/documentation patch. Tests ran serially from an LF public snapshot under native Ubuntu WSL, user `njen` UID 1000, Python 3.12.3, kernel `6.18.58.1-microsoft-standard-WSL2`. The preinstalled Linux Go 1.27.1 binary was explicitly enrolled and guarded against missing local/offline/cache/telemetry controls; its SHA-256 remained `30969f97169d7f43fe6a085873d75613adc21e30818a8c61d95bd27275df4624`. No package/compiler acquisition occurred. The actual detector selects `termux`/`android` in the new case because of its fixture prefix/version inputs; that does not change the physical WSL host or Linux compiler into native Android evidence.

| Final selector in `tools/test_installation.py` | Classification | Collected / passed | Whole-command / unittest time |
| --- | --- | ---: | --- |
| `InstallationTests.test_fresh_checkout_termux_setup_connectors_check_and_restore` | Termux-profile simulation on WSL | 1 / 1 | 16.499 / 16.167 s |
| `InstallationTests.test_fresh_checkout_wsl_setup_connectors_check_and_restore` | WSL profile on WSL | 1 / 1 | 15.697 / 15.351 s |
| `InstallationTests.test_full_checkout_bundled_install_repeat_and_restore` | WSL profile on WSL | 1 / 1 | 15.248 / 14.895 s |

All three final commands exited 0, with zero failures/errors/skips/timeouts, no cleanup signals or surviving owned processes, and unchanged source snapshots. They ran independently with native tool allowlists, owned homes/config/data/state/cache/temp/application/agent roots, inert Git templates/hooks and file-only transport, plus a 600-second process-group supervisor. Existing 600-second full-wrapper/Go and 20-second Go-version limits remained unchanged. The initial Termux-profile attempt also passed in 16.714 seconds; after read-only review removed an unnecessary separate `python` PATH prerequisite by binding both Python aliases to the vetted current interpreter, the final case above was rerun. That earlier execution is not added to the three-method total. Windows native-wrapper and prior phone batches were not rerun.

A separate owned negative control changed the copied test's prefix to another owned evidence directory outside its per-test base. The new preview path assertion failed as intended before build/apply: test exit 1 in 1.275 seconds, control harness exit 0, no Go invocation, unchanged independent canary and no survivors. The copied source was restored. Its first design instead put an absolute literal target in the copied profile; the catalog rejected that unsupported syntax earlier (`target must start with a supported destination token`, test exit 1 in 0.911 seconds). The external control harness then failed its overly specific expectation of the canary path in stderr. Both original outputs remain diagnostic history, separate from successful product tests; only the external control design changed, not an assertion or deadline in the published suite.

Evidence roots: `/home/njen/dots-review-evidence/termux-full-profile-20261115T020000Z` for the source snapshot/index, tools/Go guards, raw per-command streams/results, negative controls and manifests; `C:\Users\njen\dots-review-evidence\termux-full-profile-20261115T020000Z` for archive export, preparation/control scripts and the return prompt. The final test-file LF SHA-256 is `0d9dc9182d28b45990589eb9ca871c695c4ee0dd4df791c3494d269fef60e330`. The snapshot excludes three external absolute links and all optional/private Gitlink contents; the owned source-color replacement is explicit fixture input. No live WSL checkout was updated.

Native phone acceptance was pending at this preflight and is now recorded in the following receipt. The user reported the phone already pulled `43f17eea`; the new published fixture revision required its own authorized fast-forward only if absent. The return prompt selected these three methods independently: one native Termux-profile case and two separately labeled WSL-profile simulations on Android, with real offline native Go. Preserve earlier acceptance records rather than combining their totals. Keep direct `termux-clipboard-set` delivery separate from testing. Rollback removes this fixture/documentation patch, with no live activation to undo. No real package/Leaf acquisition, Android API, terminal reload, native Windows KnownFolders or visible/desktop acceptance is established here.

### Native Termux full-checkout receipt — 2026-11-15 UTC

The supplied phone handoff accepts all three selected methods at `5d5fca2eeb3ce4fb1d1aa7126e697491fe9c0dcc`. Physical checkout `/data/data/com.termux/files/home/dots`, UID 11043, branch `main`, fast-forwarded from parent `43f17eea5c09d8973c1dc187ba345e439915ac8a` after clean ownership/status/hook/filter/fsmonitor checks. Origin fetch/push remained `git@github.com:5nik7/dots.git`. Explicit nonrecursive fetch took 1.506 seconds and the exact-revision `merge --ff-only --no-autostash` took 0.160 seconds; every ancestry/update command exited 0. Only the expected five test/documentation files arrived, 147 insertions/eight deletions, with no product runtime changes. No reset, stash, force, rebase, real submodule operation, local source edit, commit or push occurred on the phone.

Each command was `python -B tools/test_installation.py SELECTOR -v`, executed once, serially and independently:

| Selector | Physical host / logical profile | Collected / passed | UTC start | Wall / unittest seconds |
| --- | --- | ---: | --- | --- |
| `InstallationTests.test_fresh_checkout_termux_setup_connectors_check_and_restore` | Android / native Termux | 1 / 1 | 02:11:13.342688 | 133.238 / 132.407 |
| `InstallationTests.test_fresh_checkout_wsl_setup_connectors_check_and_restore` | Android / simulated WSL | 1 / 1 | 02:13:26.668346 | 100.292 / 99.414 |
| `InstallationTests.test_full_checkout_bundled_install_repeat_and_restore` | Android / simulated WSL | 1 / 1 | 02:15:07.043471 | 116.183 / 115.368 |

All three exited 0, with zero failures, errors, method/subtest skips or timeouts. Total supervised wall time was 349.713 seconds, not a performance benchmark. Stdout was empty; each complete verbose stderr ended `Ran 1 test` and `OK`. No product/harness/containment failure, diagnostic rerun or negative-control mutation occurred. No selected assertion was left unreached through a failure or skip. Earlier broad phone batches were not rerun or added to these totals. The supplied WSL preflight and its negative controls remain PC evidence, separate from these native phone measurements.

Native identities: Android 15/API 35, aarch64, kernel `5.4.274-qgki-30957850-abG996USQSJHZB1`, Termux 0.119.0-beta.3, Python 3.14.10, Git 2.56.1 and Bash 5.3.20(1)-release. Inspected native Dash passed a shell-ready probe without `sh --version`. Actual outer detection was `termux`/`android`, corroborated by independent Android/kernel/architecture observations. Inner Go audit records selected `termux`/`android` for the first case and `wsl`/`linux` for the two simulations, but all compilers physically executed on Android/arm64.

Preinstalled Go 1.27.3 at `/data/data/com.termux/files/usr/lib/go/bin/go` satisfied the 1.27.1 module minimum; executable SHA-256 `ad103cdd7d64525e119d6061dd92747c9084e70ede77a87f0d1190be377b85b5`. Each case ran real offline `go test ./...` and `go build -trimpath -o <owned-artifact> ./cmd/anodize-engine`, all exiting 0. Test/build times were respectively 24.134/16.109, 22.692/16.590 and 23.769/16.511 seconds. The engine package passed; three packages reporting `[no test files]` are not unittest skips. Repeat installation reused the verified build after native version checks. All three used source identity `246b1b814610c28b3cda96811489b72aa1e98d146b0518c29c6da853a0dd5664` and produced a 4,925,068-byte artifact with SHA-256 `df2bf8722d8d6e99fd4f0d3774e0662febd59b1ad6123fc997ea51e30a182529`. No compiler/package was acquired.

Isolation used the exact revision's public LF archive, 2,834 verified entries, internal link identities and executable modes, excluding three external absolute links and all four Gitlink contents. The source index was owned, with no commits/refs/remotes or live Git metadata. The two documented PowerShell CRLF-to-LF index conversions were correctly accounted for without an index-verifier failure. Test-file LF SHA-256 remained `0d9dc9182d28b45990589eb9ca871c695c4ee0dd4df791c3494d269fef60e330`; archive SHA-256 was `8713d5d514492fa56036311d84c165c28846eb6c045f7ac50d6100c7cbd0ab2c`, snapshot manifest SHA-256 `eb86dd8e724365467d9408d5883ab7502cd2cfca8bc4554b53f94c8ad9efbdcf`, and unchanged owned-index SHA-256 `82a9a6a749f7cb49a1749187df955f7e93cfb0aab8d2b81b8ddb26540b4e1e55`.

Every command owned home/profile/config/data/state/cache/runtime/temp/application/agent roots and ran under a fresh process session with the unchanged 600-second supervisor. Both outer prefixes ended in owned `/usr`; the inspected native loader/version inputs and explicit 54-command allowlist supplied the required interpreters/basic utilities and theme tools. Broad host PATH, credentials, personal configuration, real package managers and desktop/notification clients were absent. Git used isolated configuration, empty templates/hooks, restricted helpers and file-only transport. The legacy Vivid stub stayed fixture-owned. The Go guard verified, without adding missing controls, local/offline/no-VCS settings, owned caches/temp and a real telemetry `mode=off` file seeded after pure preview; a separate owned native probe confirmed telemetry off. Per-operation deadlines and assertions were unchanged.

The native Termux case accepted pure preview/containment, six default components, the managed `.termux` directory and physical color publication/receipt ownership, original backups, actual engine build, connectors/artifacts, unchanged repeat and exact receipt, bundled assets, uninstall with an empty receipt, and restoration of original home/source/prefix bytes/modes/link identities and directory population. Both WSL-profile lifecycle regressions also passed. These are fixture results; no actual Android app reload, live setup or visible terminal behavior was exercised.

Durable evidence root: `/data/data/com.termux/files/home/dots-review-evidence/termux-native-full-checkout-20261115T020808Z`. It retains update/provenance and preservation journals, source/archive/index manifests, fixture/supervisor/Go-guard review, exact argv/environments and raw streams/results/process records in `01`/`02`/`03`, Go invocation/output/artifact audits, final verification and `lead-handoff.txt`. Final HEAD and cached `origin/main` equaled the tested SHA; full status and staged/unstaged diffs were empty, and `git diff --check` passed. All 2,837 post-update live tracked entries, 2,834 snapshot entries, the source index, 38 local Python caches and 379 historical evidence files were preserved. Tracked cache count remained zero. Real submodules, origin/config/hooks, allowlisted tools, Go and eight compiler tools were unchanged. Per-command scans and the final same-UID scan of 33 visible processes found zero survivors/permission denials; no cleanup signals were needed.

Disposition: the planned native Termux-profile full-checkout gate and both Android-hosted WSL-profile regressions are accepted at `5d5fca2e`. No follow-up source repair or additional phone test is indicated by this receipt. Earlier cache-cleanup, transaction/Bak, bootstrap, source-update and theme records remain separately accepted. Real package/Leaf acquisition, live activation, native Windows KnownFolders, attention/desktop integration and visible rendering remain separate gates. The handoff retains direct `termux-clipboard-set` delivery instructions but supplies no actual delivery exit status; clipboard success is therefore unconfirmed. Future delivery must continue using that inspected native provider with literal stdin and normal native runtime, independently of test isolation.

Next bounded stage: refresh packet 4's Windows terminal-appearance inventory and exact publication/rollback review, preserving current Windows Terminal Preview profile/font/scheme and existing app ownership. Packets 4–6 remain unapproved; accepted installation fixtures do not authorize live publication, consumer selection, package changes or WSL synchronization.

### Packet 4 refreshed review — 2026-11-15 UTC

**Proposed, awaiting live approval: packet 4A publishes the initial Windows Dots generation and registers its Terminal scheme.** Source baseline is `de3fc5a4c898027415af2b087ffbfdb3d26b3af0`. This review and its native rehearsals made no live application, state, profile, package, policy or WSL changes. The two pre-existing untracked attachment images remain outside the patch. Theme/files maintenance own the reviewed publication and transactions; documentation/wiki maintenance own this record. There is no new command, configuration store, shared-default change or menu/completion/installer change.

Native read-only inventory:

| Capability/target | Current evidence | Next action / acceptance |
| --- | --- | --- |
| Windows Terminal Preview | Package `1.26.3133.0`; regular user-owned `C:\Users\njen\AppData\Local\Packages\Microsoft.WindowsTerminalPreview_8wekyb3d8bbwe\LocalState\settings.json`, SHA-256 `48efae03c94f03d7bd210570248b6a7776566266a5af25161c89047679157664`. Default PowerShell Preview `{e0294b21-6d76-47a4-b22e-60c21712aa8e}`, `wal`, JetBrainsMono Nerd Font 12 normal, acrylic/95 opacity, ClearType. | Preserve all settings. Later explicit Preview desktop acceptance must establish scheme discovery/rendering; file inspection is not visible evidence. |
| Windows Terminal Stable | Package `1.25.3131.0`; regular `C:\Users\njen\AppData\Local\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\settings.json`, SHA-256 `424c09acdf21ff41296dd023adb816a109f90bd6e89387ce8298cf13b8290363`. Default Windows PowerShell and `wal`. The OS-owned bare `wt.exe` alias points to Stable. | Preserve settings and alias. Do not use bare `wt` to claim Preview acceptance. |
| Dots native generation/connector | Effective selection is `catppuccin-mocha` from the default setting. State is `C:\Users\njen\AppData\Local\dots`; `current/theme`, `themes/current` and `themes/commands/current` are absent. `theme_cli.connectors()` returned no eligible connectors, and enabled theme plugins are empty. Dedicated Terminal fragment directory is absent. | First publication is necessary; an existing generation cannot simply be linked. Revalidate inputs and exact connector set immediately before any approved mutation. |
| WezTerm | Source configuration exists separately at `profiles/windows/config/wezterm/wezterm.lua`; no active executable, package, process or configuration was found in inspected conventional locations, and configuration overrides are unset. A custom portable installation is not ruled out. | Defer activation until an actual consumer/configuration path is established; no acquisition or inferred portable destination. |

The selected Terminal settings files are independent regular files, not links to Dots source. Their inspected ancestors are ordinary directories. The proposed UTF-8 fragment contains only one `schemes` entry named `Dots`, with no profiles or settings updates, following the [native terminal contract](../docs/themes.md#native-terminal-schemes) and Microsoft's [fragment format/location](https://learn.microsoft.com/en-us/windows/terminal/json-fragment-extensions). Its preview SHA-256 is `361bcbde9e98c1362bc161d8faadcd740d0e85bd03e9e350ed6103da5e76fd87`. Background/foreground already match `wal` (`#1e1e2e`/`#cdd6f4`); the scheme tables differ in cursor, selection background, black, white and bright white. Existing profile cursor overrides remain authoritative. Merely registering this scheme does not select it.

#### Exact proposed live effects and rollback

1. Recheck checkout inputs, both settings hashes, all three absent pointers, no enabled plugins, no existing fragment, and the empty eligible connector set. Preserve current state/receipt baselines and record native renderer identities. Refuse if destinations, ownership, preferences or connector scope changed. Use the existing `Store` with guards to create only the absent dedicated `C:\Users\njen\AppData\Local\Microsoft\Windows Terminal\Fragments\Dots` directory from an owned empty directory; retain that directory transaction ID. No Terminal settings file is an operation target.
2. In a single child environment, retain the reviewed Windows HOME/config/state roots and restrict PATH to native Python plus reviewed native Bat/Vivid executables. Use the explicitly inspected Codex-bundled PowerShell 7.6.9 executable with `-NoProfile`, `DOTNET_MultiCoreJitNoProfileGather=1`, owned `PSModuleAnalysisCachePath` and TEMP/TMP roots, and the rehearsed telemetry/update-check guards. `-NoProfile` alone does not contain Windows PowerShell 5.1 startup-cache writes; do not substitute that engine for the live child. Exclude `ya` and other consumer clients; keep selected theme plugins empty. This prevents reload/notification execution without editing preferences or replacing shared publication code. Preview through native `bin/dots.ps1 theme set catppuccin-mocha --dry-run` and require exactly one connector. If preparation or preview fails, stop and review undo of the directory transaction.
3. Apply the same existing native route. Its five journaled operations are the new `%LOCALAPPDATA%/dots/themes/generations/g.<id>` directory (generated artifacts and isolated Bat syntax cache), the `Fragments/Dots/dots.json` link to `%LOCALAPPDATA%/dots/current/theme/windows-terminal.json`, `themes/commands/current`, `themes/current`, and `current/theme`. Record the publication transaction ID and actual generation path. Journals, retained backups, locks and owned preparation/runtime scratch files are additional filesystem writes, not additional consumer targets. Existing settings, installation receipt, packages, repository preferences and shell startup files are not targets. Publication exposes generated theme data/commands to later Dots consumers; it is more than a standalone fragment-file copy.
4. Verify payload/hash, link identity, committed journal, exact operation set, unchanged settings/installation receipt and unchanged second apply. No app launch, personal-shell reload or scheme selection is included in packet 4A. The subsequent visible Preview check and explicit choice of `Dots` are packet 4B, still pending review/approval.
5. Recovery uses `dots files undo <publication-id> --dry-run`, then `--yes` only after its drift checks pass; undo the earlier directory transaction afterward using the same preview/apply sequence. The first removes/restores the five publication targets; the second removes only its unchanged empty dedicated directory. Retained journals/backups remain. Newly created ancestor directories may be removed only if still empty and verified as created by this packet. Any unfinished transaction uses the existing `dots files recover <id>` review path. Drift requires review, never forced restoration. No package rollback is involved; any later consumer selection needs its own separate restoration.

#### Native rehearsal evidence

Evidence is retained outside the checkout at `C:\Users\njen\dots-review-evidence\windows-terminal-packet4-20261115`. Inputs came from a revision-bound LF public archive (2,834 file/link entries; three external links and optional/private Gitlink contents excluded). Fresh owned HOME/config/data/state/cache/temp/application roots and a Python/Bat/Vivid-only child PATH excluded real desktop consumers and personal startup. Native Bat `0.26.1` and Vivid `0.11.1` executable paths/hashes are retained; no renderer/package was acquired. Native executable version commands were not used to discover these package versions. The original inspected Windows Job Object supervisor retained raw streams, argv/environment and a 600-second outer bound; each frontend subprocess retained a 90-second bound.

| Native Windows check | Result | Evidence limit |
| --- | --- | --- |
| PowerShell 5.1 first-publication rehearsal | 1/1 method, exit 0, 16.614 seconds wall time | Actual native frontend, generated payload, links and journal; owned settings sentinel, no desktop |
| PowerShell 7.6.9 first-publication rehearsal | 1/1 method, exit 0, 11.929 seconds wall time | Same fresh-owned lifecycle; Codex-bundled native engine, not the absent former Program Files installation |
| Existing `test_theme_files.py` connector-policy and additive-terminal cases | 2/2 methods, exit 0, 1.682 seconds wall time | All bundled inert scheme templates and native destination policy; not rendered desktop acceptance |

Each rehearsal verified no-write preview, exactly five publication operations, the matching proposed JSON bytes, unchanged second apply without a new journal, explicit drift refusal, successful reverse undo through the native CLI, removal of the dedicated directory via its own transaction, and unchanged owned consumer settings. Both owned native process groups completed without timeout, termination or survivors; source snapshots were unchanged. These are two executions of one rehearsal case plus two existing methods, not four independent product suites. Independent review confirmed the publication/undo scope and added the explicit live-child runtime-cache conditions above; those controls were already present in the successful PowerShell 7 rehearsal. Earlier broad or Termux suites were not rerun. No runtime repair is indicated; this Windows-only activation review requires no phone source update/test. Preserve the accepted Termux records and direct `termux-clipboard-set` instruction for any later phone handoff. Relative-link validation passed (1,475 links in 175 files), source-only wiki validation is healthy, and `git diff --check` passed. Wiki export synchronization remains pending while its checkout is absent.

### Packet 3 refreshed review — 2026-11-14

**Historical review; subsequently approved and applied below.** Native Windows read-only inventory at `358b939f`
finds all 72 tracked symlink entries materialized as exact plain-text Git blobs.
Only the 29 `.agents/skills/<name>` entries are selected. Their canonical
`.codex/skills/<name>/SKILL.md` files exist; none of the discovery paths currently
traverses as a directory. The other 43 entries remain outside this packet.
Current session skill metadata already lists canonical skills, which does not
prove discovery in a fresh CLI session.

The exact path/blob/target/guard inventory is retained under
`C:\Users\njen\AppData\Local\Temp\dots-windows-skill-audit-doydvovp` in
`skills-restoration-plan.json` (SHA-256
`247af6582fb59cf5ed0690e561410e096dc23327ee278cf835d71238dcc1fb33`). The companion
`tracked-symlink-inventory.json` digest is
`c8a9fc2261aaae2033f2f85d7126e7ec6ddaef816e7c9f7cab0a91b7d1412a92`.

Nonadministrator native link creation succeeds with a relative Windows target
such as `..\..\.codex\skills\dots-theme-maintenance` and `directory=True`.
Passing the Git blob's forward-slash spelling produced a nontraversable native
link in the owned probe; use the tested native spelling. An owned index check
retains Git cleanliness with the current `core.symlinks=false`. Do not change
Developer Mode, elevation, Git configuration/index/refs or canonical skill files.
Future checkouts may materialize placeholders again while that Git setting
remains false; changing that policy is separate work.

The reviewed apply procedure requires rechecking every placeholder byte/hash, index blob,
contained canonical target and ordinary parent, then use the existing managed
transaction Store at `C:\Users\njen\AppData\Local\dots` for these 29 guarded
operations. Retain exact original bytes and the returned transaction ID. A
second unchanged plan must yield 29 no-ops without new journals. Review
`dots files undo ID --dry-run --json` before a drift-refusing undo; never force
through changed links or traverse/delete canonical target directories. No live
transaction ID existed at review time. Fresh CLI skill discovery is an independent final
gate; the [official skills documentation](https://learn.chatgpt.com/docs/build-skills)
describes repository `.agents/skills` and `/skills` inspection.

The owned native Windows Store rehearsal passed **5/5**, zero skips, in 3.951
seconds with Python 3.15.2 and a nonadministrator token. It covered all 29
apply/traversal/no-op/undo paths with exact byte restoration; injected failure
after seven publications with reverse rollback; abrupt child exit after seven
durable publications with cross-process reverse recovery; stale-preview refusal;
and post-apply wrong-link drift refusal without mutation. Reports and raw log
remain in that evidence root under `store-native-validation-dt_wptwd/report.json`
and `store-validation.log`. All live placeholders and `.git/config` hashes remain
unchanged. This validates the proposed mechanics, not live Codex discovery.

### Approved packet 3 activation — 2026-11-14

The user explicitly approved Windows packet 3 after reviewing the frozen
29-entry plan and owned transaction rehearsal. At source revision
`1c2154177330fdda270c290a2393080f48cb098b`, the lead revalidated the plan digest,
every Git mode/blob and exact placeholder byte sequence, ordinary parent paths,
contained canonical directories/SKILL hashes, unchanged transaction engine and
Git configuration/index. The intervening source commit changed no selected skill
or transaction inputs. No unfinished Store transaction was present.

Native Windows nonadministrator apply completed at 2026-11-14 22:24 UTC:

- Transaction and retained backup ID: `9ebe9c7e05a94f209c4c3343e0f0f03b`.
- Store: `C:\Users\njen\AppData\Local\dots`.
- Exactly 29 `.agents/skills/<name>` placeholders became relative native directory
  symlinks to the matching `.codex/skills/<name>` directories. Each linked
  `SKILL.md` is traversable and byte-identical to its canonical file.
- All 43 excluded tracked links, canonical skill contents, `.git/config` and the
  Git index remained unchanged. The tracked worktree remained clean; the two
  pre-existing untracked `.codex-attachments` images were preserved.
- The repeated classification produced 29 no-ops. Store returned `unchanged`
  without a new transaction or journal modification.
- Inverse planning verified all 29 exact original before-images in reverse
  operation order. Public `files undo --dry-run --json` passed in native
  Windows PowerShell 5.1 and stable PowerShell 7 with 29 items, exit 0 and empty
  stderr; journal hashes were unchanged. Undo was not executed.

The guarded helper ran with Python `-B`; no bytecode, canonical source, Git
configuration/index/ref, Developer Mode, elevation, package, theme, service or
personal-shell changes were part of this activation. The native CLI previews
used no-profile engines and child-only state selection, not personal startup.
The current Git symlink policy remains false; a future checkout can rematerialize
placeholders. This known limitation is separate from the completed restoration.

Evidence stays under the previously recorded
`dots-windows-skill-audit-doydvovp` root: `packet3-preflight.json`,
`packet3-applied.json`, `packet3-verification.json`, `packet3-undo-preview.json`,
`packet3-native-undo-preview.json` and both engines' raw preview streams. The
retained transaction contains all original bytes. Recovery is:

```powershell
dots files undo 9ebe9c7e05a94f209c4c3343e0f0f03b --dry-run --json
# Only when rollback is wanted, after reviewing the preview:
dots files undo 9ebe9c7e05a94f209c4c3343e0f0f03b --yes --backup
```

Select the recorded Windows state root if a child environment overrides
`XDG_STATE_HOME`; do not substitute WSL state. Undo refuses later link drift and
restores placeholders without deleting the canonical directories. Keep retained
recovery payloads until the rollback obligation ends.

This is a Windows working-tree representation change. Git skill blobs, shared
defaults, configuration precedence and Termux behavior are unchanged; the prior
Termux prompt requiring `1c215417` still applies without an additional phone gate.
Native fresh-process Codex discovery is recorded separately from filesystem
traversal; current receiving-session metadata alone is not acceptance.

An independent native inspection confirmed Codex CLI **0.169.0**, using the
direct standalone AMD64 executable rather than an updating wrapper. Version,
help and protocol-schema commands ran in empty, credential-free temporary roots.
Actual user configuration has zero skill exclusions; repository
`.codex/config.toml` is absent. The independent link check also verified 29/29
canonical byte matches. Evidence is retained at
`%TEMP%/dots-codex-skills-probe-kbgtqm5e` in `probe-report.json`,
`prepared-protocol.jsonl` and `restored-link-check.json`.

**Pending user check:** open a fresh native Windows Codex CLI in
`C:\Users\njen\dots`, run `/skills` (or use `$`) and confirm the repository
skills appear. No model task is needed. The programmatic `skills/list` schema
was verified, but app-server was not started: release-matched startup includes
an immediate online model-catalog refresh and plugin tasks, so a metadata-only
RPC would not itself bound those effects. No personal Codex configuration,
authentication, memory store, hooks or integrations were changed. Filesystem
activation is complete; fresh personal picker visibility remains unverified.

## Delivery and verification contract

Follow [presentation acceptance](../docs/presentation.md#acceptance-gate),
[testing](../agents/guides/testing.md) and
[command delivery](../agents/guides/commands.md#command-and-script-delivery).
Use owned home/config/data/state/cache/repository roots and fake package,
registry, clipboard, network and desktop providers. Keep fixture, native
runtime and visible desktop evidence separate. Missing engines are pending,
never passes. Run benchmarks serially after correctness, not during other tests.

Existing-command repairs keep their family owners from
[the authoritative index](../.codex/README.md#command-family-owners). B1/B2
correctness fixes need no new configuration integration or menu entries:
existing controls, routes, menus and component delivery remain authoritative.
Native completion coverage updates existing registrations. New connectors,
providers and helper interfaces require explicit owner-backed configuration,
menu and installer assessments before their checklist can be completed.

All shared fixes require Termux regression before phone rollout. Preserve
default/profile precedence, machine output and warm startup. File undo does not
undo package acquisition, cleanup, notification delivery or application reloads.

## Implementation evidence

Current uncommitted source patch is based on `800988ea`; no Git publication or
live WSL synchronization occurred. Tests below are native runtime fixtures, not
live application acceptance. Counts include the explicitly stated skips.

| Check | Execution/result | Limits |
| --- | --- | --- |
| PowerShell initialization | Earlier full runs: 5.1 31/31, stable 7 and Preview 32/32 each; subsequent Clear-Cache case on 5.1, FZF 2 cases and final Python boundary 5 cases on each engine OK | Current 37 methods covered by full plus focused runs; not a single final full-suite claim |
| Installation | Windows Python 3.15: 29 tests OK, 9 skips | POSIX/WSL theme lifecycle excluded |
| Installation adapters | PS5.1 and stable PS7: 10 each OK, 3 skips each | Separate native engines; no live profiles |
| Bootstrap entry | 10 OK, 6 skips; native cases exercise PS5.1/7 | Local fixture repositories, no real updates |
| Bootstrap acquisition boundary | Added focused test OK on native 5.1/7, covering absent/0/1 flags and missing runtime | Owned fake launcher; no acquisition |
| File platform | 10 OK, 1 skip | Real owned native links and executable payloads |
| Bootstrap integration/components/Leaf/Bak | 6/5/6/15 OK | Fake acquisition/build providers |
| WSL shell initialization/Bash/clipboard | 32/33/15 OK; 17/2/2 skips | Owned public source snapshot, optional shells missing |
| Shared completion helper | Initial Windows/WSL 6 OK each; native PowerShell completion 9 OK each on 5.1/7, adapter case checks 3 OK | Nu/Xonsh engines absent |
| Python invocation guards | Final 5 focused cases OK on 5.1, stable 7 and Preview | Real owned Python child; legacy flags absent, caller values restored; optional Nu runtime test skipped |
| Native clipboard transport | Focused file-provider case OK on all three PowerShell engines | Empty/multiline scalar strings, literal Unicode/arguments; no real clipboard |
| Native CLI | 27 OK, 1 skip each on 5.1/stable 7; final Preview 27 OK, 1 skip in 82.799s | Earlier intermittent copy-integrity failure retained below |
| Windows portable package adapters | 10 OK | Native Node executes owned script; no package queries/mutations |
| WSL portable packages/workflows/Go/output/pip | 10/39/3/14/7 OK; one Windows-only skip | Fake package providers |
| WinGet | 8 OK | Structured bridge mocks; no real WinGet operations |
| Bundled literal forwarding | 1 exhaustive route case OK | Exact stdout/stderr/status, fixture-only plugins |
| Anodize | Native offline build, Go tests/vet, 3 authoring cases OK | Go 1.27.4; all outputs and state temporary |
| Fonts | 22 cases: 18 pass, 3 skips, one fixture error repaired and focused rerun passed | fontTools 4.68.0 in temporary venv; registry mocked |
| Theme files | Windows 15 OK, 2 skips; WSL 15 OK | WSL 40/80/120-column light/dark/plain PTYs; no desktop |
| Project menus | Windows handoff 3 OK; WSL 40 OK, 12 skips | Child shell mocked; literal cwd/status/cancel checked |
| Project completion | WSL filtered catalog: 1 OK, 2 contexts | 296 static routes; no extension execution |
| Shared gup | WSL 2 OK | Bounded dispatch and completion, fake Git delegate |
| Cleanup | WSL 42 OK, 2 skips; Windows 7 OK, 2 skips | No live cleanup; ambient WSL process refusal retained |
| Wiki | Windows 19 OK, 2 skips | CRLF/LF extraction, transaction/undo/recovery; local fixture Git |
| Documentation | Relative links and source-only wiki healthy; generated manual/current adapters checked | Wiki checkout absent; export synchronization pending |

The fixture repairs retain actual safety assertions. They provide complete
controller inputs, native executable suffixes, exact fixture bytes and explicit
platform tests. Native Windows `bash.exe` is not accepted as a POSIX fixture.
Shared Windows source exports normalize only Git-index LF files and reconstruct
contained links in owned WSL snapshots. The live WSL checkout is unchanged.
Regenerating the manual also incorporates pre-existing static metadata omitted
from its baseline export (including debug demos and Git view options); those
routes were already implemented and are not new capabilities in this patch.

One earlier Preview native-CLI run failed the theme-source copy-integrity guard
during preparation, before publication. Its immediate focused rerun and three
fresh instrumented lifecycle repetitions passed. The original log cannot
distinguish source drift from a copied-object difference; background Git writes
and readonly-mode races remain unproven. No guard was weakened and no automatic
retry was added. A final Preview full-suite run also passed (27 cases, one skip).
Retain this intermittent failure alongside subsequent evidence.

Final review also corrected an unsafe initial acquisition guard: legacy
`PYLAUNCHER_ALLOW_INSTALL=0` still enables installation. Invocation guards remove
both legacy install flags and restore caller values; the separate install-manager
setting is false. Tests assert absence in a real owned child process. See
[the Python launcher contract](https://docs.python.org/3/using/windows.html#install-on-demand).

### Comparable startup measurements

Values below are baseline `800988ea` → current medians in milliseconds. Both
use the same complete owned ASCII-path fixture builder and frozen source inputs.
Five direct Python cold environment preparations are measured separately.
Warm profiles consume a prebuilt cache: one initial sample plus ten measured
fresh PowerShell processes per mode. PSReadLine, Starship, terminal integration
and visible desktop startup are excluded; Unicode cache correctness has its
separate native fixture gate.

| Native engine | Cold environment | Warm profile | First prompt | Whole process | No-profile process |
| --- | --- | --- | --- | --- | --- |
| 5.1.26100.9818 | 198.71 → 188.66 | 1316.82 → 1323.48 | 1321.10 → 1327.85 | 2129.52 → 2139.57 | 1111.09 → 1109.46 |
| 7.6.10 | 190.98 → 194.34 | 295.93 → 293.75 | 299.36 → 297.26 | 715.78 → 717.08 | 466.19 → 468.38 |
| 7.7.0-rc.1 | 188.99 → 190.89 | 292.29 → 296.74 | 295.72 → 300.14 | 718.97 → 723.88 | 470.04 → 468.28 |

Warm profile medians differ by at most 6.66 ms. Preview's current maximum was
405.84 ms versus baseline 297.55 ms; retain this variability without attributing
it to the patch or claiming an optimization. Raw comparisons, fixture manifests
and runner are retained under the test-owned temporary directory
`dots-windows-b1-validation-j7rd7g2u` as
`{ps51,stable,preview}-startup-compare.json` and `compare_startup.py`.

## Interface and delivery decisions

- New `dots menu projects` belongs to menu authoring. Static metadata supplies
  help/completion; both frontends dispatch the same Python controller. The root
  menu adds a Projects action. Configuration: **no new integration needed**;
  existing `projects.json`, native shell selection and menu visual controls own
  the behavior. Core delivery includes the route; the return patch must mark
  `bin/dots-menu-projects` executable (`100755`) on POSIX.
- Terminal connectors: **update** existing template/connector catalog; no new
  preferences. Semantic palette values and existing personal templates remain
  authoritative. Application-owned scheme selection stays manual. Existing
  theme menus inspect/publish them; no additional picker needed.
- Portable managers reuse existing grammar, scope, configuration, package menus
  and core plugin delivery. No new manager names or settings. Unknown native
  shell shims refuse; existing platform package ownership remains conservative.
- Cleanup reuses its existing route/menu/configuration/receipts. Group output
  adds scan/run capability flags and platform-specific descriptions. Windows
  removal remains missing implementation, not a native-equivalence claim.
- Existing helper repairs use current Git review and FZF preferences; no new
  store or menu. `gup` broad staging/approval now requires explicit options;
  shared Bash users have a named Termux gate before adoption.

## Concrete live review packets

Packets 1–2 were subsequently approved and completed; see the activation record
below. Packet 3's skill restoration was separately approved and applied in the
record above. Packets 4–6 remain unexecuted.

1. **Windows core launchers.** Actual read-only preview:
   `python -B lib/dots/files/install.py install --component core --dry-run --offline --json`.
   No preparation/packages. Creates only `.local/bin/{dots,todo,fonts,bak,dots-link}.ps1`
   under `C:\Users\njen`; stashed lsd/mpv remain skipped. Apply would create the
   native installation receipt under `%LOCALAPPDATA%/dots/installation.json` and
   its journal. No backup ID exists before apply. Retain the returned transaction
   ID; review `dots files undo ID --dry-run` before undo, or selective
   `dots files uninstall --component core --dry-run`. Recheck PATH afterward;
   do not start a real profile as an automated test.
2. **Bat environment.** `%APPDATA%/bat` is already a symbolic link to
   `C:\Users\njen\dots\config\bat`. A child-only preview with
   `BAT_CONFIG_DIR=C:\Users\njen\AppData\Roaming\bat`, selecting only
   `--component files --resource dots:bat`, reports **unchanged** and no preparation.
   The actual user/process override still points at
   `C:\Users\njen\scoop\apps\bat\current`; correct only the user override to
   `%APPDATA%/bat` after approval, saving the exact prior value/type first.
   Preserve the machine value and Scoop junction. Rollback restores that user
   value and opens a fresh shell. No package install or Bat relink is required.
3. **Repository skill/link discovery.** Fresh index inventory: all 72 mode-120000
   entries are still text placeholders. All 29 `.agents/skills/<name>` entries
   target existing canonical `.codex/skills/<name>` directories. There are 69
   contained existing targets; three absolute historical Termux/Clink targets
   are excluded. Before any approved restoration, retain placeholder bytes and
   Git configuration, revalidate each exact path/target, and restore only the
   reviewed set. No Developer Mode, elevation, Git setting, or link was changed.
   A fresh CLI session must verify skill discovery afterward. Existing receiving
   session skill visibility does not establish this gate. The [refreshed packet](#packet-3-refreshed-review--2026-11-14)
   selects only the 29 skill links and records the native transaction rehearsal;
   the subsequent approval and live restoration are recorded immediately below it.
4. **Terminal appearance.** Keep Windows Terminal Preview and its current
   profile/font/scheme. Approved publication may create the dedicated
   `%LOCALAPPDATA%/Microsoft/Windows Terminal/Fragments/Dots` directory and link
   `dots.json`. WezTerm requires its reviewed configuration directory's `colors`
   subdirectory and `dots.toml`; never infer the portable executable directory.
   Preview publication before apply, record its journal, then separately select
   Dots in the intended consumer. Undo restores the connector; restore the prior
   scheme selection separately and remove only newly created empty directories.
5. **WSL installation/plugins.** First review and transfer the coherent patch
   into `/home/njen/dots` under separate synchronization authorization. Preview
   selective core/files/plugin stages there with its own user/state/receipts.
   Preserve occupied configurations and existing Blastoff/pkgs installations;
   use the current migration planner, not legacy installers. Go 1.22.2 does not
   satisfy Anodize 1.27.1: acquisition is a separate package decision. Repeat and
   recovery acceptance must run natively after the prerequisite is resolved.
6. **Fonts/packages/Codex.** No real package, font registration or hook operation
   ran. Keep the installed WinGet Client module and existing application-owned
   Codex notifier/trusted hooks. Review exact package/version/scope, registration
   and hook definitions before their acceptance stage. Never copy Termux absolute
   paths, authentication, trust/security settings or generated memories.

## Approved Windows activation, 2026-11-13 Pacific

Core installation transaction `51ca24351008496ea51aa2e01554cf48` created the five
reviewed PowerShell launchers and the installation receipt. These are generated
forwarding files (the installer's generic result calls them `linked`), not
filesystem symbolic links. All targets were absent beforehand, so undo removes
them after checking drift. The unchanged repeat preview reports no mutations.
`dots files undo 51ca24351008496ea51aa2e01554cf48 --dry-run --json` verified the
inverse for the five files and receipt; undo was not executed.

The HKCU `BAT_CONFIG_DIR` value is now `C:\Users\njen\AppData\Roaming\bat`
with its original `String` type. The prior value/type and a drift-refusing
PowerShell restoration script were saved before the write. The machine value,
Scoop junction and existing Bat configuration link were preserved. A child-only
preview using the persisted user value reports `dots:bat` unchanged. Existing
terminal processes retain their inherited environment; restart the terminal
application for the new user value.

Installed-launcher help verification exposed a missed standalone Fonts bridge
allowlist entry, despite nested `dots fonts` coverage. The shared native bridge
now dispatches `fonts` to the existing `fonts_cli.py`. No route, configuration,
menu, destination or installer interface changes were needed. Two isolated
regressions per native engine cover standalone root/install help and literal
bridge arguments; help creates no Dots state. Final help checks pass for all five
installed launchers on all three native engines (12 unchanged passes plus three
corrected Fonts checks). Font registration is still pending.

Activation evidence, original launcher-check failures, final checks, exact Bat
backup and recovery script are retained under `%LOCALAPPDATA%/dots/activation-evidence/`
in `overkill-20261113-214137-15491cfe`. No real startup hook, package operation,
WSL synchronization, skill-link restoration, theme publication or Git publication
was performed in this activation stage.

## Remaining implementation and acceptance

### Termux acceptance text repair

The owner ran the initial phone acceptance batch after publication of `95fb42e1`.
Fixture isolation passed two tests; utility completion passed three with one
native-Windows skip. Bash ran 33 tests and stopped with one decoding error:
`test_text_keeps_utf8_literal_and_controls_inert_in_c_locale` emitted raw `0xff`.
The following shell-init, shared-shell and completion-catalog suites did not run
because the batch used `&&`.

The shared Bash human sanitizer validated malformed bytes only in its
byte-oriented branch. Its Unicode-aware branch reproduced the exact raw-byte
failure under WSL `C.UTF-8`. The repair distinguishes a decoded character from a
malformed byte through builtin Unicode round-trip validation; an ASCII sentinel
prevents an incomplete sequence from retaining decoder state and corrupting later
valid characters. Illegal scalars are inert escapes. The ASCII fast path stays
unchanged and no subprocess, cache, dependency or locale mutation is introduced.

This is a shared Bash fix useful to Termux/Linux/WSL. Native PowerShell uses its
existing renderer and has no changed route or output contract. Configuration,
menu and completion integration: **no change needed**, because this corrects
human sanitization without adding controls or grammar. Installer delivery is the
existing `lib/dots/ui.bash` source. Defaults, managed resources and preference
precedence are unchanged. Data-output paths continue to bypass the sanitizer.
Source rollback is limited to this follow-up patch; no live activation is needed.
The phone rerun was pending at publication; the native fixture acceptance below
subsequently closes this sanitizer gate at `b6daf0f7`.

Verification in the owned Ubuntu WSL snapshot: the original failure reproduces
with the pre-fix sanitizer under `C.UTF-8`; both focused regressions pass after
the repair. The full Bash suite runs 34 cases with 32 passes and two
missing-shell skips. The final expanded regression matrix also passes, including
interleaved valid text, private-use characters and invalid scalar boundaries.
The resource suite runs 18 cases with 11 passes and seven Python style/layout
failures; all seven reproduce when only `ui.bash` is restored to `95fb42e1` in
the owned snapshot. That is a narrow source comparison, not a full revision
baseline. Keep these separate failures open; they do not establish phone results.

### Termux acceptance shared-shell repair

The owner subsequently reported 21 shared-shell tests with five failures. Four
tests used integration-only `dots init bash` while expecting the full Bash
profile's aliases, prompt and tool activations. The fifth expected `.sb`, renamed
to `.dsb` in `cc0ce86a`. These assertions now use the documented public startup
entry point and current alias. The minimal shared fixture does not publish a
theme, so theme initialization is explicitly disabled there; this warning was
not evidence of a broken live phone theme.

Full-startup coverage also exposed a product defect in `tools.bash`: `c2455f55`
removed the rbenv case but left its loop entry, allowing the unmatched case to
succeed and evaluate stale `REPLY`. A successful mise hook could run twice.
Remove the retired entry and fail closed for unknown entries. Preserve the
existing mise migration, user rbenv files and failed-tool retry behavior. A new
boundary regression verifies integration-only exclusion, full-profile local
overrides, once-only mise activation and retired rbenv nonactivation.

Fixtures own HOME/XDG roots, tool stubs, both prefix variables, the inert base
completion file and the public Anodize provider. They explicitly disable tmux
autostart, use non-TTY Bash and retain the private-module exclusion. The palette
refresh test continues to use a separate owned theme fixture.

At source base `ba376c99` plus this patch, Ubuntu WSL's owned public snapshot
passes all 22 shared-shell tests, both normally and with simulated Termux
detection. The new boundary/runtime checks failed before the source repair.
Shell-init runs 32 cases with 17 missing-runtime skips; shell-environment runs
11 methods successfully with 20 unavailable-shell subtest skips. The completion
catalog passes all 1,030 contexts across 296 routes and 299 prefixes. These are
fixture results, not native phone or desktop acceptance. The subsequent phone
handoff below supplies the separate native shared-shell and completion-catalog
results after pulling the repair.

Owner: shell integration. This Bash-only correction benefits Termux/Linux/WSL;
native PowerShell adapters and Zsh activation are unchanged. Configuration,
menu, completion grammar and presentation integration: **no change needed**,
because no public route, preference or human/data output contract changes.
Shared defaults, dependencies and generated profile namespaces are unchanged.
Delivery is through the existing checkout-managed Bash source; a fresh shell
uses the repair. No live startup, package or consumer activation was performed.
Rollback is the narrow source patch and does not undo prior tool side effects.
Documentation/source-only wiki checks apply; the absent wiki export remains a
named synchronization gap. Native Termux acceptance was pending at publication;
the next section records its bounded completion.

### Native Termux fixture acceptance — 2026-11-14

**Accepted from the owner's native-agent handoff, not rerun by the PC lead.**
Physical checkout `/data/data/com.termux/files/home/dots`, branch `main`, moved
from `ba376c992bad42048f027374323b1621fe4f64db` to
`b6daf0f7452d418d9b5b44a442ff066d6cbad36b`. The authorized fast-forward exited 0
in 1.990 seconds; required ancestry and final diff checks passed. Status was
clean before updating, after updating and after testing, including untracked
files and submodules. No source fixes were made on the phone. The earlier
revision-blocked handoff at `ba376c99` ran no suites and is not a test failure.

Preflight found `git@github.com:5nik7/dots.git`, inactive sample hooks only, no
custom hooks/fsmonitor/filter setup. Pull used `--ff-only`,
`--no-recurse-submodules`, `submodule.recurse=false`, `gc.auto=0` and
`maintenance.auto=false`. A command-scoped HTTPS URL added a second URL rather
than replacing the configured SSH URL; the expected repository was fetched over
SSH. Persistent remote configuration and optional/private submodules were not
changed. Future transport selection must not assume a command-scoped URL
overrides a multi-valued remote setting.

Native runtime: Android 15 / API 35, Termux 0.119.0-beta.3, aarch64, kernel
`5.4.274-qgki-30957850-abG996USQSJHZB1`; Python 3.14.10, Bash 5.3.20,
Zsh 5.9.2, Fish 4.9.3, Nu 0.117.0 and Xonsh 0.25.0. Both PowerShell engines
were absent. LANG/LC_ALL/LC_CTYPE were `C.UTF-8`, Python UTF-8 mode was 0.
Xonsh's version came from distribution metadata; shell-init exercised its native
runtime. These runtime results do not establish all Nu/Xonsh interactive paths.

The agent inspected suites/helpers before execution and ran each sequentially
and independently under an additional clean outer harness. HOME, config, data,
state, cache, runtime, prefix and executable roots were owned; the executable
directory linked required shells/basic tools and excluded real app clients,
package managers and optional activation tools. Each suite also retained its
own fixtures. The harness and raw streams remain on the phone.

| Suite (`python -B tools/…`) | Counted | Passed | Skipped | Failures/errors | Exit | Wall seconds |
| --- | ---: | ---: | ---: | --- | ---: | ---: |
| `test_public_fixture.py` | 2 | 2 | 0 | 0 / 0 | 0 | 0.141 |
| `test_utility_completion.py` | 4 | 3 | 1 | 0 / 0 | 0 | 1.680 |
| `test_bash_dots.py` (corrected harness) | 34 | 34 | 0 | 0 / 0 | 0 | 66.161 |
| `test_shell_init.py` | 32 | 29 | 3 | 0 / 0 | 0 | 73.280 |
| `test_shared_shells.py` | 22 | 22 | 0 | 0 / 0 | 0 | 88.235 |
| `test_completion_catalog.py` | 1 | 1 | 0 | 0 / 0 | 0 | 378.665 |
| **Final-run total** | **95** | **91** | **4** | **0 / 0** | | |

Skips: `UtilityCompletion.test_powershell_real_tab_expansion_preserves_literal_insertion`
requires native Windows editor acceptance; `InitTests.test_native_powershell_adapter`,
`test_powershell_environment` and `test_powershell_portable_links` lack PowerShell.
The utility skip was printed by its verbose runner; shell-init skip identities
were matched to runner order/current branches and independently verified engine
absence. Timings are whole-process observations, not startup benchmarks.

Native accepted coverage includes both `C`/`C.UTF-8` sanitizer regressions, the
Bash/Zsh/Fish Tab fixture, integration-only versus full Bash startup, tool and
completion failure/retry, prompt composition, private-module/rbenv boundaries,
and all 1,030 completion contexts across 296 routes and 299 prefixes. This closes
the six listed automated phone gates, including both acceptance repairs. It does
not close native Windows PowerShell/editor gates, visible 40/80/120-column
appearance, live consumer/reload, Android integrations, remote continuity or the
remaining transaction/profile/theme/package/cleanup return suites.

**Retained diagnostic history and separate fixture follow-ups:**

- Initial Bash attempt: 34 tests, 32 errors, exit 1, 24.690 seconds. The outer
  harness lacked `TERMUX__PREFIX/bin/env`, breaking Termux redirection of
  `#!/usr/bin/env bash` in copied scripts. There were 31 `FileNotFoundError`
  reports and one secondary `UnboundLocalError`. Linking only the owned
  `prefix/usr/bin` to the owned executable directory repaired the harness.
  Two focused cases then passed in 0.921 seconds, followed by the full pass above.
  No source or assertion changed; preserve this attempt outside final-run totals.
- **Original recommendation, now implemented below; command-maintenance owner:** keep root help-role assertions inside
  each locale subtest in `tools/test_bash_dots.py` (`test_help_roles_tagline_and_literal_examples`).
  Currently a launch failure before assigning `root` can produce a secondary
  unbound-variable error. Preserve both locale assertions and inject a launch
  failure to verify that only its original cause is reported.
- **Original recommendation, now implemented below; theme-maintenance owner:** bound executable discovery in
  `tools/test_themes.py:Themes.setUp`. It includes the Bash directory on PATH;
  `theme_cli.py:reload_apps` invokes discovered `ya pub-to` without requiring an
  explicit live-session variable. The shared-shell theme case uses this fixture.
  The phone outer harness excluded the real client before execution; no live
  notification was reported. Use owned consumer stubs/bounded PATH and prove an
  installed host consumer cannot be invoked. Do not treat the accepted run as
  proof that the bare fixture is contained on an arbitrary host.

Evidence root on the phone:
`/data/data/com.termux/files/usr/tmp/dots-termux-acceptance-gcpj2j44/`.
It retains `suite-results.json`, `context.json`, `commands.json`, `hooks.json`,
`skips.json`, isolation/update notes, update/final Git evidence and `run_suite.py`.
Final suite directories retain raw stdout/stderr, result and sanitized environment
JSON; `bash-dots/` retains the failed attempt, `bash-harness-focus/` the two-case
confirmation. Full handoff: `handoff-for-windows-wsl-lead.txt`. The lead has the
inline handoff evidence, not direct access to those artifacts. A targeted Xonsh
bytecode audit found no writes since the task began; this is not a device-wide
filesystem audit.

The agent reported `cpy` exit 0 and exact clipboard readback for the complete
handoff, after wrapper inspection. This is handoff-delivery evidence, not the
clipboard feature suite. No clipboard history, watcher or service was enabled.
The historical instruction was as follows. Its provider choice is superseded by the [current direct Termux delivery instruction](#native-termux-profile-and-git-acceptance--2026-11-14); retain this quotation as the instruction used for this earlier run:

> Before your final reply, automatically copy the complete final handoff addressed to the Windows/WSL lead to the native Termux system clipboard using `cpy` with the handoff text on stdin. This clipboard write is explicitly authorized by the user as an exception to an otherwise read-only task boundary. Inspect command resolution and the selected wrapper, pass text literally without evaluating embedded commands, report success or failure, and still provide the complete handoff in your final reply. Do not enable clipboard history, watchers, services, or change configuration for delivery. Carry this instruction forward.

### Fixture containment follow-up

Authorized after the native handoff, based on source `afc924bc`. This batch changes
tests and their documentation only; no product route, theme, preference, installer,
startup or live-state behavior changes. Configuration/menu/completion integration:
**no change needed**, because this is test containment and failure reporting.
No new skill or settings store is needed; the existing testing guide now records
the cross-host handoff procedure and the existing clipboard instruction is retained.

`Themes.setUp` now builds an explicit tools directory and uses only that directory
and the owned command directory on PATH. Both prefix variables resolve there,
including `bin/env` and native shell/Python links for Termux redirection. It never
adds the Bash installation directory or `/usr/bin` as a fallback. A regression
places synthetic `ya`, tmux, Kitty and Termux clients beside Bash and runs actual
publication with the corresponding session indicators; none may execute. The
old PATH behavior reproduces the failure against these owned fake clients.

Specific eza, Lua, Bat and Delta cases explicitly enroll only their selected
native renderer in the owned tools directory, retaining existing availability
gates and isolated application config/cache. Neovim and other existing absolute
consumer paths remain separate, explicit fixture operations. Native Windows
skips the POSIX theme fixture instead of following `bash.exe` into WSL.

The Bash help assertions now run within both locale subtests. An injected launch
failure proves each original error survives without the secondary unbound-variable
exception; the regression fails with the previous assertion placement.

Verification at this stage:

- Owned WSL full Bash suite: 35 cases, 33 passes, two missing-shell skips.
- Focused theme containment/publication/idempotence/rollback: three passes;
  shared-shell theme refresh: one pass. The old PATH reproduces the fake-client
  marker failure. No live application was used in this comparison.
- Native Batcat highlight/cache case: one pass. eza, Lua, Delta and the `bat`
  command are absent in this WSL runtime; seven explicitly selected renderer
  cases skip. The Lua branch remains unverified because its parent color test
  stops at the baseline import failure below.
- Native Windows theme runner: all 34 cases explicitly skip as POSIX-only;
  these are not Windows runtime passes. Native PowerShell sources are unchanged.
- The first full WSL theme run exposed two missing public Neovim files in the
  owned source snapshot. After supplying only the referenced public Lua sources,
  both Neovim cases passed. This was snapshot assembly, not a product fix. The
  final full theme run has 34 cases: 32 passes and the two baseline failures below.
- Two theme failures reproduce with the prior fixture PATH/setup in the same
  owned snapshot: `test_hyphenated_completion_and_zsh_roundtrip` (Vivid/Zsh
  roundtrip) and `test_zsh_refresh_status_and_hooks` (Gum refresh expectation).
  Consumer commands in that baseline were owned inert stubs. The color case
  `test_save_preview_publish_and_reset` also fails with both fixtures at the
  existing `help_adapters` import in `file-colors.py`. Keep these separate
  baseline failures open; this is a narrow fixture comparison, not a full
  repository-revision comparison.

Native Termux verification of this follow-up is pending. Preserve the previous
six-suite acceptance at `b6daf0f7`; use a new revision-specific phone batch for
these fixture changes and report any baseline failures independently. Source
rollback removes only the test/documentation patch and cannot undo external
effects. No package installation, theme activation, WSL checkout synchronization
or real shell reload was performed. Wiki export remains unavailable; source-only
documentation validation is required before publication.

### Native fixture follow-up report and repair

The owner's 2026-11-14 native Termux handoff at
`24a5977e6f0f88bdf3bae90bf5bc584b24ef407a` reports **46 tests: 40 passed, three
failed, three errored, zero skipped**, over 1,325.340 seconds. It fast-forwarded
from `b6daf0f7` in 2.251 seconds, preserved SSH transport and finished clean.
The original six-suite acceptance at `b6daf0f7` remains separate and accepted.
No product implementation changed in that phone update and no source was fixed
on the phone. The containment regression, help diagnostics, shared-shell theme
refresh and native eza/Bat/Delta/cache-preview cases passed.

| Phone command group | Counted | Passed | Failed | Errors |
| --- | ---: | ---: | ---: | ---: |
| Selected Bash help | 2 | 2 | 0 | 0 |
| Full Themes | 34 | 31 | 2 | 1 |
| Shared-shell theme refresh | 1 | 1 | 0 | 0 |
| Native eza | 1 | 1 | 0 | 0 |
| FileColors save/preview/publish/reset | 1 | 0 | 1 | 0 |
| GitTheme | 2 | 0 | 0 | 2 |
| Bash/native Bat cache | 2 | 2 | 0 | 0 |
| Bat/Delta syntax | 2 | 2 | 0 | 0 |
| Native theme-file preview | 1 | 1 | 0 | 0 |

Context: native Android 15/API 35 aarch64, Termux 0.119.0-beta.3, Python 3.14.10,
Bash 5.3.20, Zsh 5.9.2, Fish 4.9.3, Nu 0.117.0, Git 2.56.1, eza 0.23.5,
Bat 0.26.1, Delta 0.20.1, Lua 5.4.9 and Neovim 0.12.6; outer locale C.UTF-8.
Neovim used copied public Anodize source `992e4ff8` and nvim config `fabfc6ac`.
No optional renderers were missing. The evidence root is
`/data/data/com.termux/files/usr/tmp/dots-termux-theme-acceptance-720zzagv`, with
raw streams/results/environments per group, `batch-results.json`, final Git and
owned-process checks, the outer runner and instrumented Zsh/Neovim diagnostics.
The lead received inline traces, not direct phone filesystem access. Clipboard
delivery exited 0 with matching readback; no history/watcher/service was enabled.

The report isolated five causes: a failing Vivid stub incorrectly used to model
absence; stale Gum color and incomplete public startup inputs; file-colors parser
importing `help_adapters` before bootstrap; absent optional Git fallback source;
and 14 Neovim publications sharing one 40-second invocation deadline. Measured
phone publications took roughly 12–14 seconds each. Additional focused phone
runs reproduced the two Zsh failures and Neovim timeout without changing any
assertions or the deadline. Later assertions and the Git/FileColors workflows
were not accepted from that failed run.

The bounded repair, based on `24a5977e`, implements:

- **Theme/file-colors owner:** bootstrap shared Python paths from `__file__`
  before parser construction. Fresh standalone processes and both frontends
  exercise help/query/save/reset without caller `PYTHONPATH`.
- **Theme fixture owner:** test genuinely absent Vivid, plus a separate failing
  installed provider that must preserve the previous publication. Retain the
  inherited custom suffix assertion for session-only selection; after publication
  check an explicit owned suffix rule and exact published LS_COLORS, matching the
  current documented contract. Supply full public compiler inputs without running
  personal startup; use the current blue Gum role and require no startup warnings.
- **Shell integration owner:** the newly reached C-locale assertion reproduced
  FSH's `%x` prompt expansion escaping Unicode path bytes. Load the adjacent
  adapter through literal `$DOTS` instead. A focused regression fails before
  this source fix and passes after it; there is no locale mutation or new cache.
- **Git/theme fixture owner:** replace optional/personal Git config copies with
  owned representative include/fallback/platform data. Read only the two shipped
  pager/filter values with includes disabled. Verify source preservation, include
  precedence, generated overrides, idempotence and fallback after owned removal.
- **Editor fixture owner:** keep all 13 palette transitions and final source edit,
  splitting publications into separate 40-second editor invocations. A private
  POSIX process group bounds publication children; success/timeout kill remaining
  members, reap the direct editor and retain raw timeout output. The OS reaps
  orphan grandchildren; no global subreaper setting changes. Fake-process tests
  cover cleanup without a live editor. Windows retains its existing runner.

Focused verification: Windows native Python file-colors bootstrap/controller
2/2 passes; WSL full file-colors 13 passes/one Windows-only skip; four focused
Zsh/Vivid cases pass; eight actual public-FSH cases pass; two real Neovim cases
pass, including all split publications; three fake-editor cleanup cases pass.
The final full WSL theme suite passes all 36 cases in 152.274 seconds.
Windows skips those three POSIX cleanup cases. WSL lacks `bat`/Delta for the two
GitTheme renderer cases: owned native Git include/fallback checks pass, while
actual renderer acceptance remains a named Termux gate. These results are not
substitutes for the phone follow-up.

Public routes, preferences, output grammar, completions and menus are unchanged;
configuration/menu integration: **no change needed**, because the product edits
restore existing import and literal-path behavior. Shared defaults and managed
resources are unchanged. Existing checkout delivery supplies the two library
fixes; the test changes need no installer step. No package, theme, startup hook,
live WSL checkout or service was activated. Source rollback is limited to this
patch; retain phone evidence independently. Documentation/source-only wiki checks
must pass before publication; the absent wiki export remains pending.

### Native repair acceptance and GitTheme assertion follow-up

The owner's 2026-11-14 native Termux report at
`d31824db6db3f6fa6a0c9837ad1df6558106280e` records **32 tests: 30 passed, one
failed, one skipped, zero errors**, in 813.246 seconds. The authorized SSH
fast-forward from `24a5977e` took 2.012800 seconds; final checkout/branch remained
clean at the required revision. The accepted `b6daf0f7` batch and the earlier
`24a5977e` findings remain separate historical records.

| Phone group | Counted | Passed | Failed | Skipped |
| --- | ---: | ---: | ---: | ---: |
| Fake-editor process cleanup | 3 | 3 | 0 | 0 |
| FileColors | 14 | 13 | 0 | 1 |
| Selected theme/Neovim repairs | 5 | 5 | 0 | 0 |
| GitTheme | 2 | 1 | 1 | 0 |
| Public FSH plugin | 8 | 8 | 0 | 0 |

The sole skip is `StandaloneBootstrap.test_native_query_save_reset_without_publication`
because it requires the Windows controller. Native context remained Android 15 /
API 35, Termux 0.119.0-beta.3 aarch64, Python 3.14.10, Bash 5.3.20, Zsh 5.9.2,
Git 2.56.1, Bat 0.26.1, Delta 0.20.1, Lua 5.4.9 and Neovim 0.12.6; outer locale
C.UTF-8. Public inputs: Anodize `992e4ff8`, nvim config `fabfc6ac`, FSH `4672ad5d`.
The installed FSH source's existing untracked `..ini` was preserved and excluded
by exporting committed public files into the owned fixture.

Accepted native gates: FileColors bootstrap and previously unreached workflow;
Vivid absence/failure distinctions; Zsh round-trip, Gum and warning-free startup;
literal FSH Unicode/C-locale loading and all eight plugin cases; all 13 Neovim
palette transitions and final source invalidation under separate 40-second
deadlines; all process cleanup cases; and native GitTheme dark/light rendering,
include/fallback preservation and idempotence. No surviving test-owned process
was reported. Full Themes and earlier broad batches were intentionally not rerun.

The remaining `test_role_overrides_reset_and_missing_cache` failure is a fixture
assertion: Delta returned 0 with empty stderr and correct visible `x=1`/`x=2`,
but token-level SGR sequences interrupted the raw substrings. A focused phone
rerun retained the same failure and raw bytes, confirming visible text without
altering assertions. The later cache/include assertions were not reached.

This test-only follow-up strips SGR solely for the two visible-text assertions.
It also explicitly requires raw styling and reset sequences; exit status, empty
stderr, include-contract and cache-sentinel checks remain. Synthetic checks
against the actual assertion block accept split-token SGR, reject a missing
payload and reject unstyled output. Actual Bat/Delta acceptance was pending
on Termux at publication; the native follow-up below closes that gate. No product renderer, command,
configuration/menu/completion interface, shared default or managed resource is
changed. Rollback is the narrow test/documentation patch; no activation is needed.

Phone evidence remains at
`/data/data/com.termux/files/usr/tmp/dots-termux-repair-acceptance-5hiqnnc9`, with
raw per-suite streams, runtime/source identities, final Git/process checks and
`focus-git-fallback/` raw/visible diagnostics. The lead received the inline
handoff, not direct artifact access. Clipboard delivery exited 0 with literal
stdin and no history/watchers/services. Continue carrying the recorded clipboard
instruction into the next prompt, with an exact repair revision and only the
focused fallback case followed by the full two-case GitTheme suite.

### Native GitTheme acceptance — 2026-11-14

The owner's native Termux handoff records **2/2 distinct GitTheme suite cases passed** at `788a7fdfe286a13e6e718fa5b1b850ddfdf3e1a9`, plus a separate successful focused execution of the missing-cache case. These are three successful test executions covering two distinct cases, with zero failures, errors or skips. This closes the assertion gate reported at `d31824db`; no further repair is indicated. The `b6daf0f7`, `24a5977e` and `d31824db` reports remain separate historical records, and their broader batches were not rerun.

The physical checkout `/data/data/com.termux/files/home/dots` remained on `main`. The authorized fast-forward from `d31824db6db3f6fa6a0c9837ad1df6558106280e` to the required revision exited 0 in 2.144410 seconds, preserving origin `git@github.com:5nik7/dots.git` and SSH transport. Preflight found a clean checkout, no divergence from the cached upstream and no active update hooks. Required-commit ancestry checks passed. No submodules were initialized or updated, and no local source edits were made.

| Native Termux command | Tests | Passed | Failed/errors/skipped | Exit | Wall seconds |
| --- | ---: | ---: | --- | ---: | ---: |
| `python -B tools/test_git_theme.py GitTheme.test_role_overrides_reset_and_missing_cache` | 1 | 1 | 0 / 0 / 0 | 0 | 19.387 |
| `python -B tools/test_git_theme.py` | 2 | 2 | 0 / 0 / 0 | 0 | 74.569 |

Commands ran sequentially with fresh fixtures. Native context: Android 15 / API 35, Termux 0.119.0-beta.3, aarch64, kernel `5.4.274-qgki-30957850-abG996USQSJHZB1`, Python 3.14.10, Bash 5.3.20(1)-release, Git 2.56.1, Bat 0.26.1 and Delta 0.20.1. Inspected executables resolved under `/data/data/com.termux/files/usr/bin`; version probes did not load personal startup. Locale was C.UTF-8, preferred encoding UTF-8 and Python UTF-8 mode 0. Durations are whole-process wall times, not performance benchmarks.

The inspected outer harness owned HOME/config/data/state/cache/runtime/temp and both Termux prefix roots, retained required loader variables and exposed an explicit executable allowlist with owned `bin/env` and interpreter links. GitTheme separately enrolled actual Bat/Delta, synthetic Git identity/include/fallback files and disposable repositories with inert hooks. It read only shipped pager/filter values with includes disabled. Personal Git configuration, broad host PATH and live notification/desktop clients were excluded.

Both missing-cache executions accepted exit 0, empty stderr, raw SGR styling/reset, visible `x=1` and `x=2`, include-contract preservation and the ordinary cache sentinel. The full suite also accepted native dark/light pager/filter rendering, generated syntax-cache discovery, role/reset behavior, fallback/include precedence and idempotence. Previously unreached assertions now passed. Both commands' stdout was empty; raw streams were retained and decoded as UTF-8 without errors. Post-command and final scans reported no surviving test-owned processes.

Final branch and HEAD were unchanged; status including untracked files and submodules was clean, and `git diff --check` exited 0. No packages, live configuration/themes, personal shells, services or unrelated files were changed. The authorized fast-forward, owned fixture/evidence writes and clipboard delivery were the only reported mutations.

Evidence is retained at `/data/data/com.termux/files/usr/tmp/dots-termux-git-theme-acceptance-te5fie4b`: `01-git-fallback-focused/` and `02-git-theme-suite/` contain raw streams, result/environment records and process scans. Root artifacts include command/runtime/update/final-Git records, `run_suite.py`, `handoff.md` and clipboard inspection/delivery records. The lead received the inline handoff, not direct artifact access. The inspected `cpy` wrapper received the handoff literally on stdin and exited 0; no clipboard history, watchers, services or configuration changes were enabled. Carry the existing automatic clipboard delivery instruction into every future Termux handoff prompt.

This is automated native Termux Bat/Delta fixture acceptance at the recorded revision. No Windows or WSL tests ran in that session, and visible terminal, desktop and live-application acceptance remain independent gates. This documentation-only record changes no runtime behavior or shared defaults and requires no phone retest or activation. Source documentation checks apply; wiki export synchronization remains pending while its checkout is absent.

### Native adapter follow-up source stage

This follow-up uses the same Windows working checkout at `800988e` plus the
uncommitted patch; Ubuntu results use an owned snapshot of those sources, not
the live WSL checkout. The existing activation packets 1–2 are unchanged. Source
edits to already linked resources can affect a later explicit invocation.

| Capability / route | Execution and revision | Status / evidence | Owner and next action | Acceptance / Termux impact |
| --- | --- | --- | --- | --- |
| Windows `cleanup scan/run/history/report` | Native Python, PowerShell surface; `800988e` + patch | Implemented; 55 native suite cases: 18 pass, 37 POSIX skips. Handles, ACL, cwd/mapping refusal and append-only storage use real owned Windows files; Restart Manager is substituted | Cleanup maintenance; separately review actual API integration before live cache use | Actual API and approved cache acceptance pending. Shared engine hooks retain POSIX path; Termux cleanup regression pending |
| POSIX cleanup regression | Ubuntu WSL Python 3.12, owned snapshot | 55 cases: 40 pass, 15 Windows skips; no live caches | Cleanup maintenance; retain process-visibility refusal | WSL fixture evidence only; no phone acceptance |
| `theme bg set FILE --lock-screen` | Native Windows OS PowerShell WinRT from shared controller; `800988e` + patch | Implemented; three owned tests pass; read-only API support reports true. Setter substituted; StorageFile/action projection exercised on disposable file | Theme maintenance; approved visible image acceptance next | Confirm lock-screen display and recovery manually; external API failure may leave changed image. Shared journal/background regression remains in phone gate |
| Standalone utility contextual completion | PowerShell 5.1, stable 7 and Preview 7; same patch | Four cases per engine, three pass and one POSIX skip; resolved scripts and functions verified. WSL: three pass, one Windows skip. Termux at `b6daf0f7`: three pass, one native-Windows skip; full context above | Command/shell maintenance; retain inert metadata and platform option differences | No providers/extensions execute. Native Termux fixture gate accepted; Nu/Xonsh utility editor interactions and visible acceptance remain pending |
| Native attention identity/storage/exact acknowledgement | Native Python; same patch | Implemented source with independent handle review and owned concurrency validation; no live hook or notifier activation | Codex attention owner; preserve unknown pane/focus and application delivery ownership | Hook trust, duplicate suppression, real delivery and continuity remain pending; POSIX baseline failures recorded separately |
| Native standalone utilities | PowerShell 5.1, stable 7 and Preview 7; same patch | 18 cases pass per engine: 14 shared/provider fixtures plus four native wrapper cases, including all 19 help entries; these are repeated scenarios, not 54 independent scenarios | Shell/command/menu family owners; preserve literal provider boundary and named CHT gaps | Live clipboard/network/browser/editor and visible 40/80/120-column checks pending. Termux utility-completion fixture passes at `b6daf0f7`; this does not establish every utility's live behavior |

Attention follow-up: independent review reproduced metadata-only handles allowing
rename/write despite the intended pin. The corrected adapter requests actual
file-data/directory-list access. Separate-process controls first prove unpinned
operations succeed, then verify parent/root rename, DB replacement and writes
are denied without relying on SQLite locks. An independent repeat confirms the
fix. The final native suite has 13 cases: 12 pass and one POSIX skip; owned WSL
has two pass and 11 Windows skips. Actual SQLite create/reopen, WAL/SHM and failed
write rollback pass with strict ancestor pins. New private `pending`/`ack-event`
inspection is Windows-only: POSIX refuses before opening SQLite, avoiding a
read-only WAL connection creating sidecars. Existing POSIX tmux acknowledgement
and event recording are unchanged.

Utility configuration integration: **no new integration needed**. Pickers retain
existing FZF/menu presentation settings; `fzopt` edits the caller's existing
`FZF_DEFAULT_OPTS`, and explicit CHT writes retain its app-owned `.cht.sh` files.
Menu assessment: **no new Dots launcher needed**; standalone pickers already own
selection, and scalar/network helpers remain direct commands. Completion is
updated in Bash/Zsh/Fish/PowerShell and the shared Nu/Xonsh provider. Installer
assessment: the existing generated environment already adds checkout `scripts`
to PATH; no new destination, link or manifest is required. New source adapters
are available on next explicit invocation where that PATH is active; completion
registration needs a shell reload. No real startup hook was run.

Utility logs are retained in the owned Windows temporary directory
`dots-native-utilities-703fd270058b4f39bd4296a984e7d18f`. Native providers must
resolve to `.exe`/`.com`, preserving literal arguments instead of invoking a
command shell. FIGlet filtering accepts one executable argv. Native ripgrep
pickers refresh explicitly with Ctrl-R. CHT native stealth monitoring,
persistent line editing/history and standalone installer/self-update adapters
remain missing functionality, not OS-impossible capabilities. No provider was
installed or exercised against a live desktop/network/clipboard.

Sequential startup comparison uses the existing `bench_powershell_profile.py`
runner and identical owned profiles, replacing only the completion source with
the previous stage's validated patch for the baseline. One initial and ten warm
fresh-process samples per mode exclude PSReadLine, Starship, real startup files
and environment generation. Warm profile medians in milliseconds were:

| Engine | Previous completion | Current completion | Current maximum |
| --- | ---: | ---: | ---: |
| Windows PowerShell 5.1 | 1336.00 | 1343.83 | 1594.14 |
| Stable PowerShell 7 | 296.86 | 299.24 | 303.32 |
| Preview PowerShell 7 | 295.35 | 297.80 | 364.11 |

Median increases are about 0.6–0.8%; this stage adds static completion
registrations and makes no startup speedup claim. The larger PS5.1/Preview
maximum samples are retained, with no established cause or extra caching added.
No other agent tests ran during these measurements. Initial samples, no-profile
controls, full process times and the harness remain in
`%TEMP%/dots-overkill-followup-wf9g8r6q`.

The existing native completion suite additionally passes nine cases with one
Nu skip on each of PS5.1, stable 7 and Preview 7. WSL's corresponding suite passes
eight with two platform/runtime skips. Wallpaper WSL regression: two selected
background tests pass; `test_linux_wallpaper_adapters_and_unsupported_session`
fails because it simulates Linux without hiding the actual WSL kernel. Restoring
the HEAD `backgrounds.bash` in the owned snapshot reproduces that same refusal;
this is a narrow source baseline, not a complete HEAD suite pass.

Final frozen-source WSL snapshot `/tmp/dots-b1-public-dr2ubupo`: utility suite
18 cases (13 pass, five native skips); utility completion four (three pass, one
Windows skip); attention 13 (two pass, 11 Windows skips); wallpaper three (one
portable transport pass, two Windows skips). Source normalization and executable
mode repair occur only inside that fixture. The live `/home/njen/dots` checkout
is unchanged. The final URL-provider regression preserves HTTP(S) ports and IPv6
brackets while removing credentials; SSH transport ports do not become browser
ports. Its focused native test and the final WSL utility suite pass with mocked
network/browser providers.

The lock-screen adapter has no new route, preference or menu: existing `bg set`
metadata/completion owns `--lock-screen`, and background selection remains the
existing picker. Configuration integration: **no change needed**, because this
is an explicit native action with no persistent policy. Installation delivery:
the shared controller and adjacent native helper ship with the checkout.
The journal-owning controller directly owns the PowerShell child deadline;
nested deadlines must not leave an orphan setter. Source rollback does not
restore an external image; retain the prior image separately for live acceptance.

Attention configuration/menu integration: **no change needed**. The helper's
private inspection/exact-event interface uses existing event policy and storage;
there is no public native pane menu until identity/focus is reliable. The native
setup helper continues to refuse activation. Termux preferences and notifier
ownership are unchanged.

Cleanup configuration/menu integration: **no change needed**. Existing groups,
approvals, launcher and output contracts expose supported native rules. The
same state root now holds Windows append-only schema-1 JSONL snapshots; keep
the new reader after any future native run, even during source rollback.

The WSL attention baseline has separate limitations: the original alerts suite
has missing optional `tomlkit` errors and tmux 3.4 fixture failures involving
`extended-keys-format`; the attention-style suite's two failures reproduce with
HEAD attention sources in an owned baseline. No package or live tmux changes
were made to conceal those failures.

- Native Windows cleanup now implements default npm/pip cache contents and
  named Neovim logs, exclusive native handles and private JSONL receipts. Actual
  Restart Manager integration is pending; build caches, custom roots and
  checkpoints remain missing adapters. Linux/WSL unknown process visibility
  still blocks deletion rather than weakening the safety guard.
- Native Dots pane/thread/focus/acknowledgement topology is missing; tmux/procfs
  and Android adapters do not apply to Windows. Existing application-owned Codex
  notifications may cover host delivery after focus, duplicate, approval and
  completion acceptance. Preserve that owner instead of adding a second queue.
- Windows lock-screen support is implemented through a native WinRT adapter;
  read-only availability and owned async projection pass. The actual setter
  and visible outcome remain pending. Android/X11 mechanisms are OS-specific.
- Implemented native utility adapters from current `scripts/` and PowerShell
  helper comparison: `linked`/`lnkd` (files/shell integration), `cpwd`
  (clipboard/shell integration), `pathout`/`dirout`/`isdir`/`isfile` (shell
  integration), `fzcmd`/`fzenv`/`fzfd`/`fzfig`/`fzg`/`fzopt`/`fzpyfig`/`fzrg`/
  `fzrg3` (menu/shell integration), and `cht`/`httpGet`/`www` (command
  maintenance). Their remaining CHT helper gaps are listed above.
  Each next source batch must retain literal arguments, cancellation, optional
  dependencies, data output and native completion. Use owned providers and
  40/80/120-column interaction checks; clipboard/network/editor activation is
  separately reviewed. Source rollback removes only its reviewed adapter patch.
  `dots git publish` already supplies native publication and `rwd.ps1` exists;
  do not list those as absent. Optional color/art demos and third-party `bat-*`
  scripts require separate inventory decisions.
- Nu/Xonsh interactions beyond the accepted Termux shell-init fixtures, visible desktop applications, native clipboard/editor,
  notification delivery, remote-session continuity and approved package effects
  retain separate named acceptance gates. Configured CI is not a successful run.
- **Termux return gate:** the six native suites above are accepted at `b6daf0f7`; retain the later theme/FSH and GitTheme acceptance records at their exact revisions. The bounded profile/preferences/environment, `gup`, Git publication and selected-submodule gate is accepted at `1c215417`, transaction/Bak at `5b70964d`, bounded bootstrap/installation at `23a5bfa5`, and local-Git source-update at `135d6b57`. At `8838841c`, nine native theme methods and two separately classified WSL-profile full-checkout simulations on Android are accepted. At `5d5fca2e`, the native Termux-profile full-checkout lifecycle and two separate Android-hosted WSL-profile regressions are accepted. Broader Git review, other theme/connector and affected package/cleanup checks remain pending before their phone rollout; do not rerun or reopen accepted batches merely to combine totals. Existing preference defaults and
  precedence are unchanged; shared default templates add artifacts, and shared
  startup/output/recovery behavior changes. In addition,
  `gup` changes its default approval/staging behavior. No PC test marks this gate
  complete. The original published source identities were `95fb42e1`, `ba376c99` and `b6daf0f7`;
  the original return patch remains historical evidence for its recorded scope.
- Source-only rollback before live activation restores the reviewed patch.
  After any live suffixed executable journals exist, keep the updated reader
  until undo is finished; older readers do not understand those payload names.
  File rollback cannot undo packages, notifications, cleanup or consumer reloads.

# Overkill Windows and WSL parity

Status: source implementation and isolated verification; Windows activation packets 1–2 completed, remaining activation pending. Six native Termux fixture suites accepted at `b6daf0f7` on 2026-11-14; broader return and live acceptance remain pending. Baseline: clean Windows
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
The subsequent explicit approval authorizes packets 1–2 only; their completed
live effects and recovery records are documented below.

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
below. Packets 3–6 remain unexecuted.

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
   session skill visibility does not establish this gate.
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
Carry this user instruction verbatim into subsequent Termux-agent prompts:

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
- **Termux return gate:** the six native suites above are accepted at `b6daf0f7`;
  run broader Git review, profile/preferences, transaction/Bak, theme/connector and
  affected package/cleanup suites before their phone rollout. Existing preference defaults and
  precedence are unchanged; shared default templates add artifacts, and shared
  startup/output/recovery behavior changes. In addition,
  `gup` changes its default approval/staging behavior. No PC test marks this gate
  complete. Published source identities are `95fb42e1`, `ba376c99` and `b6daf0f7`;
  the original return patch remains historical evidence for its recorded scope.
- Source-only rollback before live activation restores the reviewed patch.
  After any live suffixed executable journals exist, keep the updated reader
  until undo is finished; older readers do not understand those payload names.
  File rollback cannot undo packages, notifications, cleanup or consumer reloads.

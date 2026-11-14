# Overkill Windows and WSL parity

Status: source implementation and isolated verification; Windows activation packets 1–2 completed, remaining activation pending. Baseline: clean Windows
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
- No desktop, real clipboard, notification, package activation, remote-session
  continuity or native Termux acceptance has been claimed. Wiki checkouts are
  absent on both hosts; source-only validation is required.

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
| Standalone utility contextual completion | PowerShell 5.1, stable 7 and Preview 7; same patch | Four cases per engine, three pass and one POSIX skip; resolved scripts and functions verified. WSL: three pass, one Windows skip | Command/shell maintenance; retain inert metadata and platform option differences | No providers/extensions execute. Actual Nu/Xonsh and Termux shell completion remain pending |
| Native attention identity/storage/exact acknowledgement | Native Python; same patch | Implemented source with independent handle review and owned concurrency validation; no live hook or notifier activation | Codex attention owner; preserve unknown pane/focus and application delivery ownership | Hook trust, duplicate suppression, real delivery and continuity remain pending; POSIX baseline failures recorded separately |
| Native standalone utilities | PowerShell 5.1, stable 7 and Preview 7; same patch | 18 cases pass per engine: 14 shared/provider fixtures plus four native wrapper cases, including all 19 help entries; these are repeated scenarios, not 54 independent scenarios | Shell/command/menu family owners; preserve literal provider boundary and named CHT gaps | Live clipboard/network/browser/editor and visible 40/80/120-column checks pending. POSIX completion additions require Termux return checks |

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
- Actual Nu/Xonsh, visible desktop applications, native clipboard/editor,
  notification delivery, remote-session continuity and approved package effects
  retain separate named acceptance gates. Configured CI is not a successful run.
- **Termux return gate:** rerun shell/dispatch, shared helper/Git review,
  profile/preferences, completion, transaction/Bak, theme/connector and affected
  package/cleanup suites before phone rollout. Existing preference defaults and
  precedence are unchanged; shared default templates add artifacts, and shared
  startup/output/recovery behavior changes. In addition,
  `gup` changes its default approval/staging behavior. No PC test marks this gate
  complete. The generated return patch is the source identity until an explicitly
  authorized commit exists.
- Source-only rollback before live activation restores the reviewed patch.
  After any live suffixed executable journals exist, keep the updated reader
  until undo is finished; older readers do not understand those payload names.
  File rollback cannot undo packages, notifications, cleanup or consumer reloads.

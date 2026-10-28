# PowerShell 7+ frontend and CurrentUser lifecycle — 0.1.12

The module uses the same Python 3.11+ core as Bash. Native Windows needs neither
Bash nor WSL. Implementation is shared; native Windows, Linux PowerShell, WSL and
version-range execution are separate verification gates. See STATUS.md for actual
results. Windows PowerShell 5.1 is not supported.

## Parity matrix

| Surface | Implementation | Native acceptance |
|---|---|---|
| Theme list, presets, apply, save, edit, copy, import, delete, migration | Shared core | Args, Unicode, paths, TOML and host-native editor waiting |
| Provenance and interactive save | Shared origin/pending records and prompts | y/as/N, concurrent active/source edits, retained failed editor content |
| Backup create/list/restore/delete | Shared human/JSON output, aliases, frozen scope, confirmation | Multiselect, all, literal IDs after --, default No, Ctrl-C |
| Module save/load/list/show/delete | Shared operations and read-only source preview | Raw redirected TOML, unrelated values preserved |
| Fancy/basic pickers | Fancy Unicode default; --fzf selects basic | Actual fzf colors, bat config/themes/cache, Ctrl-X, resize/cancel |
| Output | Human by default; explicit --json; diagnostics on stderr | NO_COLOR, redirection, Unicode, verbose, exit status |
| Dry-run and safety | Shared preflight, locks, path guards and ownership | No persistent writes; Windows ACL/sharing/reparse tests |
| Help and completion | Shared CLI plus offline registered completer | Fresh-session TabExpansion2 before first command, remove/reimport |
| Lifecycle | Root PowerShell adapter and shared Python transaction engine | Clean/repeat/upgrade/WhatIf/uninstall, profiles and retention |

`Invoke-Blastoff` is deliberately not an advanced function. GNU flags remain CLI
arguments. It exposes native status in `$LASTEXITCODE`; it does not set the parent
shell process's exit code. A private versioned base64 JSON argv envelope preserves
empty strings, quotes and Unicode across native argument-passing modes. It is a
frontend transport, not a user output format. Legacy -help/-list/-theme apply only
at the command position, never to literal operands. No eval or profile sourcing.
The wrapper scopes ErrorActionPreference=Continue and disables native exit-code
error promotion locally, preserving native status without changing the caller's
preferences. PowerShell before 7.2 handles redirected native stderr differently;
its text/error-stream behavior still needs native acceptance. See the official
[preference-variable documentation](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_preference_variables#erroractionpreference).

Python discovery happens on command invocation: nonempty BLASTOFF_PYTHON (an
executable path, not a command string), Windows py -3, python3, python. Tools must
match the executing host. Linux PowerShell, including pwsh inside WSL, uses Linux
paths/tools/profile/storage; Windows PowerShell uses Windows ones. No automatic
Windows/WSL executable or path translation. Optional Starship/fzf/bat/editor
checks occur only when their operation needs them. Native Windows previews use
PowerShell 7 from the invoking host. Batch editor wrappers remain refused; select
a native editor executable where required (see RECOVERY.md).

Both explicit and discovered runtime candidates reject .cmd/.bat/.ps1 launchers.
Missing Python returns status 3 in both Bash and PowerShell. The legacy prefix
bridge `scripts/install.ps1` now uses the same resolver and versioned argument
envelope, with installer arguments preserved literally instead of CLI alias
rewriting. Its prefix ownership/layout remains separate from root install.ps1.
Lifecycle plans display SYSTEM plus native platform identity; -Verbose adds the
evidence and Python executable. MSYS2/Git Bash users are directed to this native
PowerShell workflow, without automatic execution or path translation.

## Install and remove

From a reviewed source archive with current CHECKSUMS.json:

```powershell
.\install.ps1 -WhatIf -Verbose
.\install.ps1
.\uninstall.ps1 -WhatIf
.\uninstall.ps1
```

`-DryRun` is equivalent to `-WhatIf` for no-write planning. `-Verbose` is the
idiomatic PowerShell diagnostic stream; application `blastoff --verbose` uses
stderr. WhatIf lists exact file destinations, profile diff, ownership actions and
conflicts. It creates no directories, locks, backups, bytecode or tracking data.
No downloads, execution-policy changes, persistent PATH/PSModulePath changes or
profile execution occur. Missing Python is an actionable failure, not a download.

`-ModuleRoot ABSOLUTE_PATH` selects a Modules parent. Windows defaults to the
redirected Documents known folder plus PowerShell/Modules. Non-Windows defaults
to XDG_DATA_HOME/powershell/Modules or ~/.local/share/powershell/Modules. An
unambiguous CurrentUser powershell.config.json PSModulePath is honored; ambiguous
custom paths require -ModuleRoot. The first writable PSModulePath entry is never
chosen arbitrarily. Unsafe linked/reparse write parents remain refused.

The self-contained module is `<ModuleRoot>/blastoff/0.1.12/blastoff.psd1`, with the
nested module, Python runtime, preview/lifecycle helpers, artwork, completions,
manual and docs beside it. Ownership is `<ModuleRoot>/blastoff/.blastoff/install.json`
(format 3); recovery profile backups remain in `.blastoff/profile-backups`.

Newer managed releases install side by side. A repeat installation restores
missing owned files and is otherwise idempotent. Modified files and a different
payload under the same immutable version are conflicts; downgrades are refused.
Always use the reviewed source to install/upgrade. The installed `uninstall.ps1`
also works when that source is gone, with the original -ModuleRoot for a custom
location. Source checksum verification is mandatory on install, including WhatIf.

## Profiles and coexistence

One marked Import-Module block targets `$PROFILE.CurrentUserAllHosts`, imports the
exact versioned manifest, and registers command/completion without tool processes.
Use `-ProfilePath ABSOLUTE_PATH` for another regular profile or `-NoProfile` to
manage imports yourself; these choices are exclusive. Profiles retain encoding,
BOM, line endings and unrelated bytes, with a pre-change backup and fingerprint
checks. Existing imports/foreign managed blocks are reported, never adopted or
removed. Resolve their owner explicitly or use -NoProfile. On a later upgrade,
-NoProfile leaves an already owned block unchanged, so it keeps its old version
until the user requests profile integration again.

The shell-prefix and CurrentUser module payloads are independent. The shell
installer recognizes an independent managed PowerShell block and leaves it alone.
Moving from legacy `scripts/install.ps1 install --yes` is not a silent migration:
that bridge retains its prefix layout/ownership. Review/remove its old integration
with its owning installer before requesting a new root-script profile block.
Removing either frontend must not remove the other's payload or integration.

Uninstall removes only unchanged owned files and exact blocks. Modified content,
user data (themes/modules/backups/provenance), active Starship configuration,
recovery backups and unrelated profile code remain. It never recursively deletes
user directories or breaks locks. A loaded module/completer may remain in the
current process until `Remove-Module blastoff` or a new session. Installation
prints the exact `Import-Module '.../blastoff.psd1' -Force` activation command.

## Startup, completion and verification

Import defines the wrapper and registers completion without Python, Starship,
fzf, bat, preset/theme scans, dependency probes, network calls or checksums.
Static completion performs no filesystem discovery. Dynamic completion examines
only filenames under the requested storage directory, with no TOML reads; modern
hosts use native metadata without subprocesses. Its memory cache lasts two seconds (up to eight directory keys); each
scan is bounded to 4,096 entries/100 ms. Huge libraries may have partial advisory
completion. Commands still accept valid explicit names. Network roots and unsafe
children are excluded. PowerShell 7.0 Unix lacks UnixMode unless PSUnixFileStat
is enabled. On that host only, dynamic names use a private filename-only Python
helper with a two-second process deadline and the same bounded scan/cache. Static
completion/import still launches nothing. Missing Python gives no dynamic names,
without noise or state changes. No experimental feature is enabled automatically.
This compatibility exception reuses the shared path/name rules; it reads no TOML
or backup metadata. Its native performance/version checks remain pending.
See [PowerShell 7.0 type definitions](https://github.com/PowerShell/PowerShell/blob/v7.0.0/src/System.Management.Automation/engine/TypeTable_Types_Ps1Xml.cs#L8215).

Reimport refreshes state. Removal disables that module's callback and clears its
cache; it does not unregister another tool's later callback. An inert registration
can remain until replaced or the shell closes. No private registry reflection.

Run in fresh disposable sessions:

```powershell
pwsh -NoProfile -File tests/powershell_session.ps1
pwsh -NoProfile -File tests/parity.ps1
pwsh -NoProfile -File tests/powershell_lifecycle.ps1
pwsh -NoProfile -File scripts/benchmark-powershell.ps1
```

On Linux/WSL use `tests/parity.ps1 -AllowNonWindows` and label evidence accordingly.
Unittest discovery runs that parity script when pwsh exists and explicitly skips
it otherwise. The harness feeds the core exact arguments through an independent
fixture decoder, checks literal forwarding in available native argument modes,
and compares raw TOML and isolated mutation/provenance results. It does not
mistake generated file fingerprints or fixture paths for frontend differences.
The lifecycle harness uses explicit temporary ModuleRoot/ProfilePath. Record
PowerShell 7.0/7.2/current separately, native argument mode, platform, optional tool
versions, stderr/status and Ctrl-C behavior. Text parity does not promise binary
pipeline fidelity across PowerShell versions. Import, fresh-process baseline,
minimal temporary profile import, first command and cold/warm completion are
separate benchmark cases; report actual p50/p95 and skips, not inferred Windows
performance. See WINDOWS-CHECKS.md for retained native filesystem/interactive gates.

Theme-list presentation since 0.1.10 is supplied entirely by the shared core, including
quiet prefixes and current/modified origin markers. `tests/parity.ps1` compares
plain, forced-color and JSON listings before and after a disposable active edit.
Native PowerShell/Windows/WSL execution remains a separate unverified gate until run.

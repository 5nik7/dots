# 0.1.12 native platform and PowerShell follow-up (pending until run)

Current additions: confirm SYSTEM is Windows under native PowerShell even with
inherited MSYSTEM/WSL variables, and WSL (Linux) inside Linux pwsh. Verify
MSYS2/Git Bash refuses shell installation before Python and directs users to the
native PowerShell installer. Record real hosts separately from classifier fixtures.
Run unittest discovery: it now invokes parity.ps1 automatically when pwsh exists.
Check missing Python status 3, automatic batch-runtime exclusion, and legacy
installer literal empty/Unicode/quoted operands. Parity probes cover available
Legacy/Standard/Windows modes without changing the caller's lasting preferences.

Rehearse 0.1.11 to 0.1.12 using verified old/new sources and temporary ModuleRoot
and ProfilePath. The current native lifecycle harness accepts -PriorSource for
this check. Test source relocation, modified-file retention and shell/module
ownership separately. No native pass is implied until the scripts run.

# 0.1.8 native PowerShell follow-up (pending until run)

Use [POWERSHELL.md](POWERSHELL.md) for the current parity matrix and root lifecycle.
Run `tests/powershell_session.ps1`, `tests/parity.ps1`,
`tests/powershell_lifecycle.ps1` and `scripts/benchmark-powershell.ps1` in fresh
native sessions. The first completes commands before any Blastoff invocation;
the lifecycle script uses explicit temporary ModuleRoot/ProfilePath. Test the
manifest's PowerShell 7.0+ range independently; do not imply 5.1 support.

Current root commands: `.\install.ps1 -WhatIf [-Verbose]`, `.\install.ps1`,
`.\uninstall.ps1 -WhatIf`, `.\uninstall.ps1`; -DryRun is equivalent to WhatIf.
-NoProfile opts out; custom roots/profile paths are explicit. Do not substitute
old prefix-install tests for redirected Documents/profile/CurrentUser testing.
Native Windows, Linux PowerShell and WSL runs need distinct evidence. For an
explicit Linux/WSL parity run use -AllowNonWindows; it does not certify Windows.

The retained detailed handoff below includes legacy prefix lifecycle tests and
historical counts. Run current VERSION and record actual counts, not old totals.
The private argv-envelope probe now asserts the literal original arguments using
an independent decoder. Ctrl-C, Unicode text, ACL/reparse/locking, actual fzf/bat
inheritance, GUI editors and visual checks remain native gates.

# Native Windows validation handoff

**Execution pending.** This guide and the test changes were reviewed on Termux;
no native Windows or PowerShell engine was available there. Linux PowerShell,
WSL, static review and the completed Termux runs do not satisfy this gate.

## Prerequisites and boundaries

- Native Windows, a normal user account, and a local writable NTFS checkout or
  extracted verified archive. Avoid OneDrive, junction/symlink parent directories,
  network drives and antivirus-controlled folders for the baseline. Record any
  subsequent tests on those filesystems separately.
- Use **PowerShell 7.4 or newer** for the first run, not Windows PowerShell 5.1.
  The module currently advertises 7.0+, which remains unverified. The current parity
  harness permits 7.0+; its stderr/status checks must be run separately on 7.0/7.2
  because native stderr redirection semantics changed in 7.2. Native empty/embedded-quote argument behavior changed in 7.3; older hosts
  and `Legacy` argument mode are separate compatibility gates, not assumed passes.
- Native Python **3.11+**, selected by absolute executable path. Bash, WSL,
  Starship, fzf and gum are not prerequisites for core/module/lifecycle checks.
  If Starship is present, listing may use it; its cache is redirected below.
- Run in a fresh **`pwsh -NoProfile`** process. Do not dot-source test/install
  scripts, alter execution policy, install tools, edit profiles/PATH, or run an
  installer without an explicit temporary `--prefix`. If execution policy blocks
  scripts, report `Get-ExecutionPolicy -List` and stop; do not bypass it silently.
- Use a verified source package with its existing `CHECKSUMS.json`. If transfer,
  extraction or Git line-ending conversion causes verification failure, stop and
  investigate. Do **not** regenerate checksums merely to bless a damaged copy.
- All snippets below belong to the same disposable PowerShell process. Exiting it
  discards process-only environment changes. `$HOME` is a PowerShell automatic
  variable and is **not** reassigned; always use the explicit fixture variables.

## 1. Start, identify runtimes, and establish the sandbox

Start `pwsh -NoProfile`, then replace only the example repository path:

```powershell
$Repo = (Resolve-Path -LiteralPath 'C:\work\Blastoff review ü').Path
Set-Location -LiteralPath $Repo
if (-not $IsWindows) { throw 'Native Windows only; WSL/Linux is not this gate.' }
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false # assert expected native failures ourselves
$Pwsh = (Get-Process -Id $PID).Path

# If py.exe is unavailable, set $Python to an already-installed absolute python.exe path.
$Python = (& py -3 -c 'import sys; print(sys.executable)').Trim()
if ($LASTEXITCODE -ne 0) { throw 'Python discovery failed' }
& $Python -c 'import os,sys; print(os.name,sys.version,sys.executable); assert sys.version_info >= (3,11)'
if ($LASTEXITCODE -ne 0) { throw 'Python 3.11+ required' }
if ((& $Python -c 'import os; print(os.name)') -ne 'nt') { throw 'Python is not native Windows' }

$Run = Join-Path ([IO.Path]::GetTempPath()) ('blastoff-windows-' + [guid]::NewGuid().ToString('N'))
$Report = Join-Path $Run 'report'
$FixtureHome = Join-Path $Run 'home ü'
New-Item -ItemType Directory -Path $Report,$FixtureHome | Out-Null
$env:HOME = $FixtureHome
$env:USERPROFILE = $FixtureHome
$env:BLASTOFF_HOME = Join-Path $Run 'storage space ü'
$env:STARSHIP_CONFIG = Join-Path $Run 'config space ü\starship.toml'
$env:BLASTOFF_PYTHON = $Python
$env:XDG_CONFIG_HOME = Join-Path $Run 'xdg'
$env:XDG_CACHE_HOME = Join-Path $Run 'cache'
$env:STARSHIP_CACHE = Join-Path $Run 'starship-cache'
$env:NO_COLOR = '1'
Remove-Item Env:BLASTOFF_TEST_STARSHIP -ErrorAction SilentlyContinue
$Config = $env:STARSHIP_CONFIG
$Store = $env:BLASTOFF_HOME
$Utf8 = [Text.UTF8Encoding]::new($false)

$PSVersionTable | Out-String | Set-Content -LiteralPath (Join-Path $Report 'powershell.txt')
Get-Variable PSNativeCommandArgumentPassing -ErrorAction SilentlyContinue |
    Out-String | Add-Content -LiteralPath (Join-Path $Report 'powershell.txt')
Get-ExecutionPolicy -List | Out-String | Add-Content -LiteralPath (Join-Path $Report 'powershell.txt')
& $Python -c 'import platform,sys; print(platform.platform(),platform.machine(),sys.version)' |
    Set-Content -LiteralPath (Join-Path $Report 'python.txt')
Write-Host "Disposable root: $Run"
Write-Host "Keep reports from: $Report"

& $Python scripts/verify.py
if ($LASTEXITCODE -ne 0) { throw 'Source verification failed; do not install or refresh checksums.' }
```

Expected: native `nt`, supported Python, and successful source verification.
These commands neither change PATH nor select the real active Starship config.
Record whether the default argument mode is `Windows` or `Standard`; do not
force it just to make a failing literal-argument test pass.

## 2. Automated core and PowerShell parity checks

```powershell
& $Python -m unittest discover -s tests -v `
    1> (Join-Path $Report 'core.out.txt') 2> (Join-Path $Report 'core.err.txt')
$coreExit = $LASTEXITCODE
Get-Content -LiteralPath (Join-Path $Report 'core.err.txt')
if ($coreExit -ne 0) { throw "Core tests failed: $coreExit; retain both logs" }

& $Pwsh -NoProfile -File .\tests\parity.ps1 `
    1> (Join-Path $Report 'parity.out.txt') 2> (Join-Path $Report 'parity.err.txt')
$parityExit = $LASTEXITCODE
Get-Content -LiteralPath (Join-Path $Report 'parity.out.txt')
if ($parityExit -ne 0) { throw "Parity failed: $parityExit; inspect parity.err.txt and the retained fixture" }
```

Expected: both processes exit 0; unittest reports `OK` with explicit platform
skips, and parity reports literal argv/import checks, **13** read/error cases
and three mutations. Record the actual totals and every skip reason. POSIX modes,
FIFOs, shell/PTYS and privilege-dependent symlinks are not Windows passes.

The parity script isolates HOME/USERPROFILE, config, storage and Starship cache;
it never changes PATH. A copied, unchanged PowerShell module plus an argv-echo
Python companion checks empty strings, spaces, Unicode, embedded double quotes,
trailing backslashes and case-sensitive legacy-alias behavior against literal
expected values—not merely against another equally misquoted call. The real
core then checks expected status plus separate stdout/stderr text. Import is
checked with a nonexistent interpreter override to prove it does not start Python.
Failure fixtures are retained; `-KeepSandbox` also retains successful fixtures.
This harness compares **text**, not arbitrary binary stream fidelity.

Do not accept a failed empty/quote case as a harmless difference. Report the
PowerShell version and argument mode; the manifest's older compatibility range
may require a deliberate wrapper or minimum-version decision after native evidence.

## 3. Import and observable stream/exit behavior

```powershell
Import-Module .\powershell\blastoff.psd1 -Force
Get-Command Invoke-Blastoff,blastoff | Format-Table Name,CommandType,Source
blastoff --version
if ($LASTEXITCODE -ne 0) { throw 'Version failed' }
blastoff --help
if ($LASTEXITCODE -ne 0) { throw 'Help failed' }
if ((Test-Path -LiteralPath $Store) -or (Test-Path -LiteralPath $Config)) {
    throw 'Import/help/version created user-state fixtures unexpectedly'
}

blastoff theme apply --json `
    1> (Join-Path $Report 'usage.out.txt') 2> (Join-Path $Report 'usage.err.txt')
$usageExit = $LASTEXITCODE # capture immediately, before running another native program
if ($usageExit -ne 2) { throw "Expected usage exit 2, got $usageExit" }
if ([IO.File]::ReadAllText((Join-Path $Report 'usage.out.txt')).Length -ne 0) { throw 'Error leaked to stdout' }
$usage = Get-Content -Raw -LiteralPath (Join-Path $Report 'usage.err.txt') | ConvertFrom-Json
if ($usage.code -ne 2) { throw 'Expected one JSON error on stderr' }
```

Expected: version matching VERSION (currently `blastoff 0.1.12`), plain help, clean streams, and the shell remains
open after status 2. A function exposes `$LASTEXITCODE`; it does **not** terminate
the calling shell or set that shell process's eventual exit status. To propagate
status from a separate automation process, explicitly `exit $LASTEXITCODE` there.

Use this small assertion helper for the remaining JSON operations; logs stay
outside the source checkout:

```powershell
$script:CaseNumber = 0
function Check-Blastoff {
    param([string[]]$Words, [int]$Expected = 0)
    $script:CaseNumber++
    $errFile = Join-Path $Report ("case-{0}.err.txt" -f $script:CaseNumber)
    $outFile = Join-Path $Report ("case-{0}.out.txt" -f $script:CaseNumber)
    $text = (blastoff @Words --json 2> $errFile | Out-String)
    $code = $LASTEXITCODE
    [IO.File]::WriteAllText($outFile, $text, $Utf8)
    $errors = [IO.File]::ReadAllText($errFile)
    if ($code -ne $Expected) { throw "Case $script:CaseNumber expected $Expected, got $code; $errors" }
    if ($Expected -eq 0) {
        if ($errors.Length -ne 0) { throw "Unexpected stderr: $errors" }
        return ($text | ConvertFrom-Json)
    }
    if ($text.Trim().Length -ne 0) { throw 'Failure wrote stdout' }
    $failure = $errors | ConvertFrom-Json
    if ($failure.code -ne $Expected) { throw 'JSON error code mismatch' }
    return $failure
}
```

## 4. Environment overrides and round-trip data operations

```powershell
$d = Check-Blastoff @('doctor')
if ($d.config -ne $Config -or $d.blastoff_home -ne $Store) { throw 'Overrides ignored' }
try {
    $env:STARSHIP_CONFIG = ''
    $env:BLASTOFF_HOME = ''
    $d = Check-Blastoff @('doctor')
    if ($d.config -ne (Join-Path $FixtureHome '.config\starship.toml')) { throw 'Empty override fallback wrong' }
    if ($d.blastoff_home -ne (Join-Path $FixtureHome '.config\blastoff')) { throw 'Storage fallback wrong' }
    $env:STARSHIP_CONFIG = '~/custom/active.toml'
    if ((Check-Blastoff @('doctor')).config -ne (Join-Path $FixtureHome 'custom\active.toml')) { throw 'Tilde expansion wrong' }
    $env:STARSHIP_CONFIG = 'relative.toml'
    Check-Blastoff @('doctor') 2 | Out-Null
} finally {
    $env:STARSHIP_CONFIG = $Config
    $env:BLASTOFF_HOME = $Store
}

$Source = Join-Path $Run "source with spaces ü's.toml"
$Original = @'
format = "$all"
[directory]
style = "purple"
[git_branch]
style = "green"
'@
[IO.File]::WriteAllText($Source, $Original, $Utf8)
Check-Blastoff @('theme','import',$Source,'work') | Out-Null
Check-Blastoff @('theme','apply','local:work') | Out-Null
if ((Get-FileHash -LiteralPath $Source).Hash -ne (Get-FileHash -LiteralPath $Config).Hash) { throw 'Apply changed bytes' }
Check-Blastoff @('theme','save','saved') | Out-Null
Check-Blastoff @('theme','copy','work','copy') | Out-Null
Check-Blastoff @('theme','copy','work','copy') 1 | Out-Null # collision
Check-Blastoff @('theme','copy','work','copy','--force') | Out-Null
Check-Blastoff @('theme','delete','copy') 2 | Out-Null
Check-Blastoff @('theme','delete','copy','--force') | Out-Null
Check-Blastoff @('module','save','directory','compact') | Out-Null
[IO.File]::WriteAllText($Config, $Original.Replace('"purple"','"red"'), $Utf8)
Check-Blastoff @('module','load','compact') | Out-Null
$Merged = [IO.File]::ReadAllText($Config)
if (-not $Merged.Contains('style = "purple"') -or -not $Merged.Contains('style = "green"')) { throw 'Module merge changed unrelated values' }

$beforeRestore = (Get-FileHash -LiteralPath $Config).Hash
$id = (Check-Blastoff @('backup','create')).backup
[IO.File]::WriteAllText($Config, 'format = "$directory"', $Utf8)
Check-Blastoff @('backup','restore',$id) | Out-Null
if ((Get-FileHash -LiteralPath $Config).Hash -ne $beforeRestore) { throw 'Restore mismatch' }
Check-Blastoff @('backup','list') | Out-Null
Check-Blastoff @('module','delete','compact','--force') | Out-Null
```

Expected: exit 0 except the two explicitly expected refusals; files only in the
sandbox. Forced replacement/deletion and changed active writes create backups.
Inspect paired `.toml`/`.json` files under `$Store\backups`: source path, kind,
SHA-256, and bytes should match the replaced/deleted fixture. Never run theme
custom commands or render a live Starship prompt as validation.

Also run `blastoff current` and `blastoff theme copy work human-copy` **without**
`--json`; record Unicode rendering, stdout/stderr and `$LASTEXITCODE`. The expected
status is 0. A Unicode encoding failure after a mutation is a bug to report, not
permission to retry against live data. JSON success alone does not certify human
Unicode output under every Windows code page.

## 5. File safety, Windows sharing and reparse points

```powershell
$before = (Get-FileHash -LiteralPath $Config).Hash
$bad = Join-Path $Run 'invalid.toml'
[IO.File]::WriteAllText($bad, '[broken', $Utf8)
Check-Blastoff @('theme','import',$bad,'bad') 1 | Out-Null
Check-Blastoff @('theme','save','CON') 2 | Out-Null
Check-Blastoff @('theme','save','..\escape') 2 | Out-Null
if ((Get-FileHash -LiteralPath $Config).Hash -ne $before) { throw 'Refusal changed config' }

$lock = Join-Path $Store '.operation.lock'
New-Item -ItemType Directory -Path $lock | Out-Null
try { Check-Blastoff @('theme','apply','work') 1 | Out-Null }
finally { Remove-Item -LiteralPath $lock } # only the empty fixture lock created above
$handle = [IO.File]::Open($Config, [IO.FileMode]::Open, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
try { Check-Blastoff @('theme','apply','work') 1 | Out-Null }
finally { $handle.Dispose() }
if ((Get-FileHash -LiteralPath $Config).Hash -ne $before) { throw 'Sharing/lock refusal changed config' }

$snapshot = Join-Path $Store ("backups\{0}.toml" -f $id)
[IO.File]::WriteAllText($snapshot, 'tampered = true', $Utf8)
Check-Blastoff @('backup','restore',$id) 1 | Out-Null
if ((Get-FileHash -LiteralPath $Config).Hash -ne $before) { throw 'Checksum refusal changed config' }
```

Use an ordinary-user junction test (all targets remain inside `$Run`):

```powershell
$targetDir = Join-Path $Run 'junction target'
$linkDir = Join-Path $Run 'junction parent'
New-Item -ItemType Directory -Path $targetDir | Out-Null
New-Item -ItemType Junction -Path $linkDir -Target $targetDir | Out-Null
try {
    $env:STARSHIP_CONFIG = Join-Path $linkDir 'new.toml'
    Check-Blastoff @('theme','apply','work') 1 | Out-Null
    if (Test-Path -LiteralPath (Join-Path $targetDir 'new.toml')) { throw 'Wrote through junction parent' }
} finally {
    $env:STARSHIP_CONFIG = $Config
    Remove-Item -LiteralPath $linkDir -Force # remove link only, no recursion
}
```

If junction creation itself fails, record the filesystem/error and leave this
check pending. Do not reinterpret an assertion failure after successful creation
as a privilege skip. No admin elevation or system policy changes are required.

File-symlink testing needs existing Developer Mode/symlink privilege. If unavailable,
record **SKIP: privilege unavailable** rather than enabling it automatically:

```powershell
$link = Join-Path $Run 'linked-active.toml'
$target = Join-Path $Run 'link-target.toml'
[IO.File]::WriteAllText($target, 'format = "$all"', $Utf8)
# Stop here and report SKIP if this creation is denied.
New-Item -ItemType SymbolicLink -Path $link -Target $target | Out-Null
$targetHash = (Get-FileHash -LiteralPath $target).Hash
try {
    $env:STARSHIP_CONFIG = $link
    Check-Blastoff @('theme','apply','work') | Out-Null
    if (-not ((Get-Item -LiteralPath $link).Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Link was replaced' }
    if ((Get-FileHash -LiteralPath $target).Hash -ne (Get-FileHash -LiteralPath (Join-Path $Store 'themes/work.toml')).Hash) { throw 'Target not updated' }
    [IO.File]::WriteAllText($target, 'format = "$all"', $Utf8)
    $converted = Check-Blastoff @('theme','apply','work','--replace-link')
    if ((Get-Item -LiteralPath $link).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Link not replaced' }
    if ((Get-FileHash -LiteralPath $target).Hash -ne $targetHash) { throw 'Link target changed' }
    $meta = Get-Content -Raw -LiteralPath (Join-Path $Store ("backups\{0}.json" -f $converted.backup)) | ConvertFrom-Json
    if (-not $meta.symlink_target) { throw 'Missing original link metadata' }
} finally { $env:STARSHIP_CONFIG = $Config }
```

Remaining native safety gates include junctioned storage-child deletion, deliberate
ACL denial, read-only files, interruption recovery and network/cloud filesystem
behavior. Exercise only disposable fixtures; do not change ACLs on the repository,
user profile or real Starship config. Python POSIX permission tests do not certify
Windows ACL or reparse semantics.

## 6. Isolated install/uninstall (never the real prefix)

```powershell
$Prefix = Join-Path $Run 'install prefix ü'
$Version = ([IO.File]::ReadAllText((Join-Path $Repo 'VERSION'))).Trim()
$activeHash = (Get-FileHash -LiteralPath $Config).Hash
& $Pwsh -NoProfile -File .\scripts\install.ps1 install --prefix $Prefix --dry-run
if ($LASTEXITCODE -ne 0 -or (Test-Path -LiteralPath $Prefix)) { throw 'Dry-run wrote or failed' }
& $Pwsh -NoProfile -File .\scripts\install.ps1 install --prefix $Prefix --yes
if ($LASTEXITCODE -ne 0) { throw 'Isolated install failed' }
$Manifest = Join-Path $Prefix 'share\blastoff\install.json'
$ownership = Get-Content -Raw -LiteralPath $Manifest | ConvertFrom-Json
$Payload = Join-Path $Prefix ("share\blastoff\versions\{0}" -f $Version)
Remove-Module blastoff -Force
Import-Module (Join-Path $Payload 'powershell\blastoff.psd1') -Force
blastoff --version
if ($LASTEXITCODE -ne 0) { throw 'Installed module failed' }

$unrelated = Join-Path $Prefix 'keep-me.txt'
[IO.File]::WriteAllText($unrelated, 'unrelated fixture', $Utf8)
$installedCore = Join-Path $Payload 'lib\blastoff.py'
$ownedBytes = [IO.File]::ReadAllBytes($installedCore)
[IO.File]::AppendAllText($installedCore, "`n# tampered fixture`n", $Utf8)
& $Pwsh -NoProfile -File .\scripts\install.ps1 uninstall --prefix $Prefix --yes
if ($LASTEXITCODE -ne 1 -or -not (Test-Path -LiteralPath $Manifest)) { throw 'Modified-owned-file refusal failed' }
[IO.File]::WriteAllBytes($installedCore, $ownedBytes) # restore our fixture, not user data
& $Pwsh -NoProfile -File .\scripts\install.ps1 uninstall --prefix $Prefix --dry-run
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $Manifest)) { throw 'Uninstall dry-run failed' }
Remove-Module blastoff -Force
& $Pwsh -NoProfile -File .\scripts\install.ps1 uninstall --prefix $Prefix --yes
if ($LASTEXITCODE -ne 0) { throw 'Uninstall failed' }
foreach ($entry in $ownership.files.PSObject.Properties.Name) {
    if (Test-Path -LiteralPath $entry) { throw "Owned file remains: $entry" }
}
if (Test-Path -LiteralPath $Manifest) { throw 'Manifest remains' }
if ([IO.File]::ReadAllText($unrelated) -ne 'unrelated fixture') { throw 'Unrelated file changed' }
if ((Get-FileHash -LiteralPath $Config).Hash -ne $activeHash) { throw 'Lifecycle changed active config' }
if (-not (Test-Path -LiteralPath (Join-Path $Store 'themes\work.toml'))) { throw 'Lifecycle removed storage' }
Import-Module .\powershell\blastoff.psd1 -Force
```

Expected: dry-runs do not mutate, tampered owned content is refused, verified
owned files are removed, unrelated files and config/storage remain. Empty prefix
directories or unowned bytecode may remain by design. Git Bash/WSL on PATH does
not prove native Bash launcher support; the installed PowerShell module is the
Windows entry point under test. Fresh Windows installs deliberately omit the
top-level `bin/blastoff` launcher regardless of Git Bash/WSL discovery. Never
execute the POSIX shebang file as a Windows process and call that PowerShell parity.

## 7. Report and follow-up gates

Keep `$Report` and the printed sandbox paths until reviewed. Report:

1. Windows edition/build, architecture, filesystem/physical path, PowerShell and
   Python versions/executable paths, argument mode, execution policy restrictions,
   and optional Starship/Bash presence. Do not include credentials or live configs.
2. Each exact command, exit status, stdout/stderr logs, unittest counts and skip
   reasons, parity summary, and the first failing assertion. Mark **PASS / FAIL /
   SKIP / NOT RUN** separately; never count a skip as native evidence.
3. Empty/quote/trailing-backslash argv outcomes, Unicode paths/output, environment
   defaults/overrides, native sharing/junction/symlink outcomes, and retained
   fixture paths. A failing test may have already made changes in its sandbox;
   inspect rather than retry blindly.
4. Install/uninstall manifest and preservation results. No real installation,
   profile/PATH change or publication is part of this handoff.

Optional subsequent commands, still with the sandbox environment active:

```powershell
& $Python scripts/benchmark.py --samples 60 1> (Join-Path $Report 'startup-windows.json')
if ($LASTEXITCODE -ne 0) { throw 'Benchmark failed' }
# Only if native Starship is already installed and its real preset gate is desired:
$env:BLASTOFF_TEST_STARSHIP = '1'
& $Python -m unittest discover -s tests -p test_native.py -v
Remove-Item Env:BLASTOFF_TEST_STARSHIP
```

Report Python vs PowerShell-process startup separately; the latter includes host
startup/module import. TTY Ctrl-C, Windows picker tools, human Unicode rendering,
older PowerShell/Legacy argument modes, and interruption/ACL tests remain separate
gates. Never substitute Termux PTYs, Linux PowerShell or WSL for them.

Exit the disposable `pwsh` session when done. Retain reports; remove only explicitly
identified fixture directories after inspection, removing any remaining reparse
links first. No broad cleanup command over `%TEMP%`, HOME or a real prefix is needed.

## Sources

- [Microsoft: preference variables, native argument passing and native error handling](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_preference_variables?view=powershell-7.5)
- Local contract: `CLI-CONTRACT.md`; current evidence: `STATUS.md`.


## 0.1.7 extension — deferred native execution

The earlier handoff remains historical; run the current VERSION and parity harness,
not historical expected counts. Add no-write dry-run/verbose stream tests; backup
multi-ID/alias/literal -- selection and authorization; module show raw/JSON/browser;
and provenance across apply, edit, save-as and restore. Verify malformed/pending
state, active/source concurrent changes, symlink/junction/hardlink protections,
and default-No confirmations in a disposable Windows root.

EDITOR uses native quoted argv rules; test paths with spaces/backslashes/quotes,
waiting GUI editors, atomic file replacement, cancellation and retained invalid
work. Batch/shell editor launchers are refused with guidance to a native executable.
Test PowerShell TabExpansion2 for backup IDs, module show, repeated operands,
--fancy values and alias escaping without starting Python. Verify installed helper
resolution and ownership under a temporary prefix. The source update and Termux
fixtures do not certify any of these native Windows cases.

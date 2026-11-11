# Shared Dots, Blastoff and pkgs lifecycle.
param(
    [switch] $Bootstrap, [switch] $NoBackup, [switch] $Offline,
    [switch] $DryRun, [switch] $Yes, [switch] $Json, [switch] $Update,
    [string[]] $WithSource = @(),
    [string] $Packages,
    [switch] $Interactive, [switch] $NonInteractive, [switch] $NoClear, [switch] $NoLogo,
    [ValidateSet('core','files','themes','anodize','blastoff','pkgs','packages','fonts','leaf')][string[]] $Component = @(),
    [string[]] $Resource = @(),
    [switch] $WithDependencies, [switch] $SaveChoices,
    [string] $Fonts, [string[]] $FontTarget = @(),
    [ValidateSet('auto', 'always', 'never')][string] $Color,
    [ValidateSet('auto', 'always', 'never')][string] $Icons,
    [Parameter(ValueFromRemainingArguments = $true)][string[]] $Arguments = @()
)
$ErrorActionPreference = 'Stop'
$cli = @('install')
if ($NoBackup) { $cli += '--no-backup' }
if ($Offline) { $cli += '--offline' }
if ($PSBoundParameters['Verbose']) { $cli += '--verbose' }
. (Join-Path $PSScriptRoot 'lib/dots/files/entry.ps1')
. (Join-Path $PSScriptRoot 'lib/dots/ui.ps1')
if ($Interactive) { $cli += '--interactive' }
if ($NonInteractive) { $cli += '--non-interactive' }
if ($NoClear) { $cli += '--no-clear' }
if ($NoLogo) { $cli += '--no-logo' }
foreach ($item in $Component) { $cli += @('--component', $item) }
foreach ($item in $Resource) { $cli += @('--resource', $item) }
if ($WithDependencies) { $cli += '--with-dependencies' }
if ($SaveChoices) { $cli += '--save-choices' }
if ($Fonts) { $cli += @('--fonts', $Fonts) }
foreach ($item in $FontTarget) { $cli += @('--font-target', $item) }
if ($DryRun) { $cli += '--dry-run' }
if ($Yes) { $cli += '--yes' }
if ($Json) { $cli += '--json' }
if ($Update) { $cli += '--update' }
foreach ($source in $WithSource) { $cli += @('--with-source', $source) }
if ($Packages) { $cli += @('--packages', $Packages) }
if ($Color) { $cli += "--color=$Color" }
if ($Icons) { $cli += "--icons=$Icons" }
try {
    $setupPython = $null
    $oldAutomatic, $oldLauncher = $env:PYTHON_MANAGER_AUTOMATIC_INSTALL, $env:PYLAUNCHER_ALLOW_INSTALL
    try {
        $env:PYTHON_MANAGER_AUTOMATIC_INSTALL = 'false'; $env:PYLAUNCHER_ALLOW_INSTALL = '0'
        foreach ($candidate in @(Get-Command py, python3, python -CommandType Application -ErrorAction SilentlyContinue)) {
            if ($candidate.Source -like '*\WindowsApps\*' -and $candidate.Name -ne 'py.exe') { continue }
            $prefix = @(); if ($candidate.Name -in @('py','py.exe')) { $prefix = @('-3') }
            try { $found = & $candidate.Source @prefix -B -c 'import sys;sys.exit(1) if sys.version_info < (3,11) else print(sys.executable)' 2>$null } catch { continue }
            if ($LASTEXITCODE -eq 0 -and $found -and (Test-Path -LiteralPath ([string]@($found)[-1]) -PathType Leaf)) { $setupPython = [string]@($found)[-1]; break }
        }
    } finally { $env:PYTHON_MANAGER_AUTOMATIC_INSTALL = $oldAutomatic; $env:PYLAUNCHER_ALLOW_INSTALL = $oldLauncher }
    if ($Bootstrap -or -not $setupPython) {
        & (Join-Path $PSScriptRoot 'bootstrap.ps1') --destination $PSScriptRoot @($cli | Select-Object -Skip 1) @Arguments
        exit $LASTEXITCODE
    }
    Invoke-DotsFiles $PSScriptRoot 'install' ($cli + $Arguments) @{} $setupPython
    exit $script:DotsFilesExitCode
}
catch {
    $style = @{}
    if ($Color) { $style['color'] = $Color }
    if ($Icons) { $style['icons'] = $Icons }
    Write-DotsMessage ('dots setup: ' + $_.Exception.Message) error $style
    exit 1
}

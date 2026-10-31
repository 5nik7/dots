# Shared Dots, Blastoff and pkgs lifecycle.
param(
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
    Invoke-DotsFiles $PSScriptRoot 'install' ($cli + $Arguments)
    exit $script:DotsFilesExitCode
}
catch {
    $style = @{}
    if ($Color) { $style['color'] = $Color }
    if ($Icons) { $style['icons'] = $Icons }
    Write-DotsMessage ('dots setup: ' + $_.Exception.Message) error $style
    exit 1
}

# Shared Dots, Blastoff and pkgs lifecycle.
param(
    [switch] $DryRun, [switch] $Yes, [switch] $Json,
    [switch] $Interactive, [switch] $NonInteractive, [switch] $NoClear, [switch] $NoLogo,
    [ValidateSet('core','files','themes','anodize','blastoff','pkgs','packages','fonts','leaf')][string[]] $Component = @(),
    [string[]] $Resource = @(),
    [ValidateSet('auto', 'always', 'never')][string] $Color,
    [ValidateSet('auto', 'always', 'never')][string] $Icons,
    [Parameter(ValueFromRemainingArguments = $true)][string[]] $Arguments = @()
)
$ErrorActionPreference = 'Stop'
$cli = @('uninstall')
if ($PSBoundParameters['Verbose']) { $cli += '--verbose' }
. (Join-Path $PSScriptRoot 'lib/dots/files/entry.ps1')
. (Join-Path $PSScriptRoot 'lib/dots/ui.ps1')
if ($Interactive) { $cli += '--interactive' }
if ($NonInteractive) { $cli += '--non-interactive' }
if ($NoClear) { $cli += '--no-clear' }
if ($NoLogo) { $cli += '--no-logo' }
foreach ($item in $Component) { $cli += @('--component', $item) }
foreach ($item in $Resource) { $cli += @('--resource', $item) }
if ($DryRun) { $cli += '--dry-run' }
if ($Yes) { $cli += '--yes' }
if ($Json) { $cli += '--json' }
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

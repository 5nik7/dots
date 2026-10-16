param(
    [switch] $DryRun, [switch] $Yes, [switch] $Json,
    [ValidateSet('auto', 'always', 'never')][string] $Color,
    [ValidateSet('auto', 'always', 'never')][string] $Icons,
    [Parameter(ValueFromRemainingArguments = $true)][string[]] $Arguments = @()
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'lib/dots/files/entry.ps1')
. (Join-Path $PSScriptRoot 'lib/dots/ui.ps1')
$cli = @('uninstall')
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

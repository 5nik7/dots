param(
    [switch] $DryRun, [switch] $Yes, [switch] $Json, [switch] $Update,
    [string[]] $WithSource = @(),
    [ValidateSet('auto', 'always', 'never')][string] $Color,
    [ValidateSet('auto', 'always', 'never')][string] $Icons,
    [Parameter(ValueFromRemainingArguments = $true)][string[]] $Arguments = @()
)
$ErrorActionPreference = 'Stop'
$dotsBundleRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$cli = @('install')
if ($PSBoundParameters['Verbose']) { $cli += '--verbose' }
. (Join-Path $dotsBundleRoot 'lib/dots/files/entry.ps1')
. (Join-Path $dotsBundleRoot 'lib/dots/ui.ps1')
if ($DryRun) { $cli += '--dry-run' }
if ($Yes) { $cli += '--yes' }
if ($Json) { $cli += '--json' }
if ($Update) { $cli += '--update' }
foreach ($source in $WithSource) { $cli += @('--with-source', $source) }
if ($Color) { $cli += "--color=$Color" }
if ($Icons) { $cli += "--icons=$Icons" }
try {
    Invoke-DotsFiles $dotsBundleRoot 'install' ($cli + $Arguments)
    exit $script:DotsFilesExitCode
}
catch {
    $style = @{}
    if ($Color) { $style['color'] = $Color }
    if ($Icons) { $style['icons'] = $Icons }
    Write-DotsMessage ('dots setup: ' + $_.Exception.Message) error $style
    exit 1
}

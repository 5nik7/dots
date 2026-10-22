# Native entry; literal argv goes to the same Python 3.11+ controller.
$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $root 'lib/dots/ui.ps1')
try {
    . (Join-Path $root 'lib/dots/files/entry.ps1')
    Invoke-DotsFiles $root 'wttr' @($args | ForEach-Object { [string] $_ })
    exit $script:DotsFilesExitCode
} catch {
    Write-DotsMessage ('wttr: ' + $_.Exception.Message) error @{}
    exit 1
}

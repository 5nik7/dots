# Native backup bridge; literal arguments and shared transactions.
$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $root 'lib/dots/ui.ps1')
try {
    . (Join-Path $root 'lib/dots/files/entry.ps1')
    Invoke-DotsFiles $root 'bak' @($args | ForEach-Object { [string] $_ })
    exit $script:DotsFilesExitCode
} catch {
    Write-DotsMessage ('bak: ' + $_.Exception.Message) error @{}
    exit 1
}

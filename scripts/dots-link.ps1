# Native standalone link bridge; shared guards, backups and recovery.
$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $root 'lib/dots/ui.ps1')
try {
    . (Join-Path $root 'lib/dots/files/entry.ps1')
    Invoke-DotsFiles $root 'link' @($args | ForEach-Object { [string] $_ })
    exit $script:DotsFilesExitCode
} catch {
    Write-DotsMessage ('dots link: ' + $_.Exception.Message) error @{}
    exit 1
}

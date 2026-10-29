# Literal native argument bridge; no Bash or WSL dependency.
$root = if ($env:DOTS) { $env:DOTS } else { Split-Path -Parent $PSScriptRoot }
. (Join-Path $root 'lib/dots/ui.ps1')
try {
    . (Join-Path $root 'lib/dots/files/entry.ps1')
    Invoke-DotsFiles $root 'todo' @($args | ForEach-Object { [string] $_ })
    exit $script:DotsFilesExitCode
} catch {
    Write-DotsMessage ('todo: ' + $_.Exception.Message) error @{}
    exit 1
}

using namespace System.Management.Automation
using namespace System.Management.Automation.Language

$env:DOTS = "$env:USERPROFILE\dots"
$Global:DOTS = $env:DOTS

$env:SHELLS = "$env:DOTS\shells"
$Global:SHELLS = $env:SHELLS

$env:PSDOT = "$env:SHELLS\powershell"
$Global:PSDOT = $env:PSDOT

$env:PSCOMPONENT = "$env:PSDOT\component"
$Global:PSCOMPONENT = $env:PSCOMPONENT

foreach ( $includeFile in ("util", "env", "functions", "path", "aliases", "modules", "readline", "completions", "prompt") ) {
    Unblock-File "$env:PSCOMPONENT\$includeFile.ps1"
    . "$env:PSCOMPONENT\$includeFile.ps1"
}

$powersecrets = "$Env:DOTS\secrets\secrets.ps1"
if (Test-Path "$powersecrets") {
    Unblock-File "$powersecrets"
    . "$powersecrets"
}

if ($fzFile) {
    Unblock-File "$env:PSCOMPONENT\$FzFile.ps1"
    . "$env:PSCOMPONENT\$FzFile.ps1"
}

$fzFile = if (Test-CommandExists fzf) { 'fzf' }
if ($fzFile) {
    Unblock-File "$env:PSCOMPONENT\$FzFile.ps1"
    . "$env:PSCOMPONENT\$FzFile.ps1"
}

if ($env:isReloading) {
    Clear-Host
    Write-Box -border "DarkGray" -color "Green" -text "Profile reloaded."
    $env:isReloading = $false
}

function rl {
    [CmdletBinding()]
    param ()
    [bool]$env:isReloading = "$true"

    $env:isReloading = $true
    Clear-Host
    Write-Box -border "DarkGray" -color "Blue" -text "Restarting PowerShell.."
    # linebreak 1; Write-Color Cyan "     $($util.symbols.'nf-cod-debug_restart'.icon)" -inline; Write-Color Blue " Restarting PowerShell..."; linebreak 1
    & pwsh -NoExit -Command "Set-Location -Path $(Get-Location)'"
    exit
}

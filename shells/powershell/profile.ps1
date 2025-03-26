using namespace System.Management.Automation
using namespace System.Management.Automation.Language

$env:DOTS = "$HOME\dots"
$Global:DOTS = $env:DOTS
$SHELLS = "$DOTS\shells"
$PSDOTS = "$SHELLS\powershell"
$PSCOMPONENT = "$PSDOTS\component"

$psource = ("util", "functions")
foreach ( $piece in $psource ) {
    Unblock-File "$PSCOMPONENT\$piece.ps1"
    . "$PSCOMPONENT\$piece.ps1"
}

function dotenv {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory = $true)]
        [string]$path,
        [switch]$v
    )
    $envFilePath = Join-Path -Path $path -ChildPath ".env"
    if (Test-Path $envFilePath) {
        if ($v) {
            wh "Loading environment variables from $envFilePath" green -box -border darkgray -bb 1 -ba 1 -padout 2
        }
        Get-Content $envFilePath | ForEach-Object {
            $name, $value = $_.split('=')

            if ([string]::IsNullOrWhiteSpace($name) -or $name.Contains('#')) {
                continue
            }
            $expandedName = [Environment]::ExpandEnvironmentVariables($name)
            $expandedValue = [Environment]::ExpandEnvironmentVariables($value)

            Set-Item -Path "env:$expandedName" -Value $expandedValue
            if ($v) {
                wh '' darkgray $expandedName yellow "=" darkgray $expandedValue white -bb 1 -ba 1 -pad 2
            }
        }
    }
}
dotenv $env:DOTS
dotenv $env:secretdir

$psource = ("path", "aliases", "fzf", "modules", "readline", "completions", "prompt")
foreach ( $piece in $psource ) {
    Unblock-File "$PSCOMPONENT\$piece.ps1"
    . "$PSCOMPONENT\$piece.ps1"
}

if ($env:isReloading) {
    Clear-Host
    wh "Profile reloaded." green -box -border darkgray -bb 1 -ba 1 -padout 2
    $env:isReloading = $false
}

function rl {
    [CmdletBinding()]
    param ()
    [bool]$env:isReloading = "$true"

    $env:isReloading = $true
    Clear-Host
    wh "Restarting PowerShell.." blue -box -border darkgray -bb 1 -ba 1 -padout 2
    & pwsh -NoExit -Command "Set-Location -Path $(Get-Location)'"
    exit
}

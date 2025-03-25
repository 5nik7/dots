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
            wh '' -c darkgray -sp 0 -bb 0 -pad 2; wh $expandedName -c yellow -sp 1; wh "=" -c darkgray; wh $expandedValue -c white -ba 1
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
                wh '' -c darkgray -sp 0 -bb 0 -pad 2; wh $expandedName -c yellow -sp 1; wh "=" -c darkgray; wh $expandedValue -c white -ba 1
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

using namespace System.Management.Automation
using namespace System.Management.Automation.Language

$env:DOTS = "$env:USERPROFILE\dots"
$Global:DOTS = $env:DOTS

$env:SHELLS = "$env:DOTS\shells"
$Global:SHELLS = $env:SHELLS

$env:PSDOTS = "$env:SHELLS\powershell"
$PSDOTS = $env:PSDOTS

$env:PSCOMPONENT = "$env:PSDOTS\component"
$Global:PSCOMPONENT = $env:PSCOMPONENT

function psenv {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory = $true)]
        [string]$path
    )
    $envFilePath = Join-Path -Path $path -ChildPath ".env"
    if (Test-Path $envFilePath) {
        Get-Content $envFilePath | ForEach-Object {
            $name, $value = $_.split('=')

            if ([string]::IsNullOrWhiteSpace($name) -or $name.Contains('#')) {
                continue
            }
            $expandedName = [Environment]::ExpandEnvironmentVariables($name)
            $expandedValue = [Environment]::ExpandEnvironmentVariables($value)

            Set-Item -Path "env:$expandedName" -Value $expandedValue
        }
    }
}

psenv -path $env:PSDOTS
$env:secretdir = "$Env:DOTS\secrets"
psenv -path $env:secretdir

# $powersecrets = "$secretdir\secrets.ps1"
# if (Test-Path "$powersecrets") {
#     Unblock-File "$powersecrets"
#     . "$powersecrets"
# }

foreach ( $includeFile in ("util", "env", "functions", "path", "aliases", "fzf", "modules", "readline", "completions", "prompt") ) {
    Unblock-File "$env:PSCOMPONENT\$includeFile.ps1"
    . "$env:PSCOMPONENT\$includeFile.ps1"
}

$powersecrets = "$Env:DOTS\secrets\secrets.ps1"
if (Test-Path "$powersecrets") {
    Unblock-File "$powersecrets"
    . "$powersecrets"
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

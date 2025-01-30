function Get-PowerMod {
    [CmdletBinding()]
    param (
        [Parameter()]
        $Name
    )
    if (Get-Module $Name -ListAvailable) {
        Import-Module -Name $Name
    } else {
        Install-Module $Name -Scope CurrentUser -Force
    }
}

Get-PowerMod -Name PowerShellGet
Get-PowerMod -Name Terminal-Icons
Get-PowerMod -Name PSScriptAnalyzer
Get-PowerMod -Name Pester
Get-PowerMod -Name Plaster
Get-PowerMod -Name Microsoft.WinGet.CommandNotFound


Import-Module "$Env:PSMODS\winwal\winwal.psm1"
Add-Path -Path "$Env:PSMODS\winwal\colortool"

Import-Module "$Env:PSMODS\psdots\psdots.psm1"
Import-Module "$($(Get-Item $(Get-Command scoop.ps1).Path).Directory.Parent.FullName)\modules\scoop-completion"

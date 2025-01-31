function Import-PSMod {
    [CmdletBinding()]
    param (
        [Parameter()]
        $Name,
        [switch]$Core,
        [switch]$Desktop,
        [switch]$Local
    )
    if ($Core -and $PSEdition -ne 'Core') {
        return
    }
    if ($Desktop -and $PSEdition -ne 'Desktop') {
        return
    }
    if ($Local) {
        $localModulePath = "$env:PSMODS\$Name\$Name.psm1"
        if (Test-Path $localModulePath) {
            Import-Module -Name $localModulePath
            return
        }
    }
    if (Get-Module $Name -ListAvailable) {
        Import-Module -Name $Name
    } else {
        Install-Module $Name -Scope CurrentUser -Force
    }
}

Import-PSMod -Name PowerShellGet
Import-PSMod -Name Terminal-Icons
Import-PSMod -Name PSScriptAnalyzer
Import-PSMod -Name Pester
Import-PSMod -Name Plaster
Import-PSMod -Core -Name Microsoft.WinGet.CommandNotFound

Import-PSMod -Local -Name psdots

Import-PSMod -Local -Name winwal
if ((Get-Module winwal -ListAvailable) -and (Test-Path "$env:PSMODS\winwal\colortool")) {
    Add-Path -Path "$env:PSMODS\winwal\colortool"
}

function Import-PSMod {
    [CmdletBinding()]
    param (
        [Parameter()]
        $Name,
        [switch]$Core,
        [switch]$Desktop,
        [switch]$Local,
        [string]$Version
    )
    if ($Core -and $PSEdition -ne 'Core') {
        return
    }
    if ($Desktop -and $PSEdition -ne 'Desktop') {
        return
    }
    if (!($Local)) {
        if (Get-Module $Name -ListAvailable) {
            Import-Module -Name $Name
        }
        else {
            Install-Module $Name -Scope CurrentUser -Force
        }
        return
    }
    if ($Local) {
        $LocalModulesDir = "$env:PSDOT/Modules"
        if ($Version) {
            $LocalModuleRootDir = "$LocalModulesDir/$Name/$Version"
        }
        else {
            $LocalModuleRootDir = "$LocalModulesDir/$Name"
        }
        $LocalModulePath = "$LocalModuleRootDir/$Name.psm1"
        if (Test-Path $LocalModulePath) {
            Import-Module $LocalModulePath
        }
    }
}

Import-PSMod -Name "PowerShellGet"
Import-PSMod -Name "Terminal-Icons"
Import-PSMod -Name "PSScriptAnalyzer"
Import-PSMod -Name "Pester"
Import-PSMod -Name "Plaster"
Import-PSMod -Core -Name "Microsoft.WinGet.CommandNotFound"

Import-PSMod -Local -Name "powernerd"
Import-PSMod -Local -Name "winwal"
Import-PSMod -Local -Name "lab"
Import-PSMod -Local -Name "PSDots" -Version "0.0.1"
Import-PSMod -Local -Name "powerpath" -Version "0.0.1"

if ((Get-Module winwal -ListAvailable) -and (Test-Path "$env:PSMODS\winwal\colortool")) {
    Add-Path -Path "$env:PSMODS\winwal\colortool"
}

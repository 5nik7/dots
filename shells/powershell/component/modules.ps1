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
    $LocalModulesDir = "$env:PSDOTS/Modules"
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

if (Test-CommandExists fzf) { Import-Module 'PsFzf' }

Import-PSMod -Name 'CompletionPredictor'
Import-PSMod -Name 'PowerShellGet'
Import-PSMod -Name 'Terminal-Icons'
# Import-PSMod -Name 'PSScriptAnalyzer'
# Import-PSMod -Name 'Pester'
# Import-PSMod -Name 'Plaster'
# Import-PSMod -Core -Name 'Microsoft.WinGet.CommandNotFound'

Import-PSMod -Local -Name 'powernerd'
Import-PSMod -Local -Name 'winwal'

if ((Get-Module winwal -ListAvailable) -and (Test-Path "$env:PSMODS\winwal\colortool")) {
  Add-Path -Path "$env:PSMODS\winwal\colortool"
}

function AllDaColorScripts {
  $colorful_scripts = ('00default', 'alpha', 'arch', 'awk-rgb-test', 'bars', 'blocks1', 'blocks2', 'bloks', 'colorbars', 'colortest-slim', 'colortest', 'colorview', 'colorwheel', 'crowns', 'crunch', 'crunchbang-mini', 'crunchbang', 'darthvader', 'debian', 'dna', 'doom-original', 'doom-outlined', 'dotx', 'elfman', 'faces', 'fade', 'ghosts', 'guns', 'hearts', 'hedgehogs', 'hex-blocks', 'hex', 'illumina', 'jangofett', 'kaisen', 'manjaro', 'monster', 'mouseface', 'mouseface2', 'pacman', 'panes', 'pinguco', 'pukeskull', 'rails', 'rally-x', 'rupees', 'six', 'space-invaders', 'spectrum', 'square', 'suckless', 'tanks', 'thebat', 'thebat2', 'thisisfine', 'tiefighter1-no-invo', 'tiefighter1', 'tiefighter1row', 'tiefighter2', 'tux', 'tvs', 'unowns', 'xmonad', 'zwaves')
  foreach ( $colscript in $colorful_scripts ) {
    wh "$colscript" -box
    Show-ColorScript -Name "$colscript"
  }
}

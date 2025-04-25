Add-PSModulePath -Path $env:PSMODS

Import-PSMod -Name 'CompletionPredictor'
Import-PSMod -Name 'PowerShellGet'
Import-PSMod -Name 'Terminal-Icons'
# Import-PSMod -Name 'PSScriptAnalyzer'
# Import-PSMod -Name 'Pester'
# Import-PSMod -Name 'Plaster'
# Import-PSMod -Core -Name 'Microsoft.WinGet.CommandNotFound'

Import-PSMod -Local -Name 'catppuccin'
$Flavor = $Catppuccin['Mocha']
$Global:Flavor = $Flavor

Import-PSMod -Local -Name 'PSDots'
Import-PSMod -Local -Name 'powernerd'
Import-PSMod -Local -Name 'winwal'
Import-PSMod -Local -Name 'lab'

if ((Get-Module winwal -ListAvailable) -and (Test-Path "$env:PSMODS\winwal\colortool")) {
  Add-Path -Path "$env:PSMODS\winwal\colortool"
}

Import-ScoopModule -Name 'scoop-completion'
if (Test-CommandExists fzf) { Import-ScoopModule -Name 'PsFzf' }

function AllDaColorScripts {
  $colorful_scripts = ('00default', 'alpha', 'arch', 'awk-rgb-test', 'bars', 'blocks1', 'blocks2', 'bloks', 'colorbars', 'colortest-slim', 'colortest', 'colorview', 'colorwheel', 'crowns', 'crunch', 'crunchbang-mini', 'crunchbang', 'darthvader', 'debian', 'dna', 'doom-original', 'doom-outlined', 'dotx', 'elfman', 'faces', 'fade', 'ghosts', 'guns', 'hearts', 'hedgehogs', 'hex-blocks', 'hex', 'illumina', 'jangofett', 'kaisen', 'manjaro', 'monster', 'mouseface', 'mouseface2', 'pacman', 'panes', 'pinguco', 'pukeskull', 'rails', 'rally-x', 'rupees', 'six', 'space-invaders', 'spectrum', 'square', 'suckless', 'tanks', 'thebat', 'thebat2', 'thisisfine', 'tiefighter1-no-invo', 'tiefighter1', 'tiefighter1row', 'tiefighter2', 'tux', 'tvs', 'unowns', 'xmonad', 'zwaves')
  foreach ( $colscript in $colorful_scripts ) {
    wh "$colscript" -box
    Show-ColorScript -Name "$colscript"
  }
}

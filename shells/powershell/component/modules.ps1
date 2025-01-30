if (-not (Get-Module Terminal-Icons -ListAvailable)) {
    Install-Module Terminal-Icons -Scope CurrentUser -Force
}
Import-Module -Name Terminal-Icons

Import-Module "$Env:PSMODS\winwal\winwal.psm1"
Add-Path -Path "$Env:PSMODS\winwal\colortool"

Import-Module "$Env:PSMODS\psdots\psdots.psm1"
Import-Module "$($(Get-Item $(Get-Command scoop.ps1).Path).Directory.Parent.FullName)\modules\scoop-completion"

Invoke-Expression (& { (zoxide init powershell | Out-String) })

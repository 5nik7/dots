using namespace System.Management.Automation
using namespace System.Management.Automation.Language

$env:HOME = "$env:HOMEPATH"
$DOTS = "$env:HOME\dots"
$env:DOTS = $DOTS
$Global:DOTS = $env:DOTS
$SHELLS = "$DOTS\shells"
$env:SHELLS = $SHELLS
$Global:SHELLS = $env:SHELLS
$PSDOTS = "$SHELLS\powershell"
$env:PSDOTS = $PSDOTS
$Global:PSDOTS = $env:PSDOTS
$PSCOMPONENT = "$PSDOTS\component"
$env:PSCOMPONENT = $PSCOMPONENT
$Global:PSCOMPONENT = $env:PSCOMPONENT

if (Test-Path "$PSCOMPONENT\util.ps1") {
  Unblock-File "$PSCOMPONENT\util.ps1"
  . "$PSCOMPONENT\util.ps1"
}

if (Test-Path "$PSCOMPONENT\functions.ps1") {
  Unblock-File "$PSCOMPONENT\functions.ps1"
  . "$PSCOMPONENT\functions.ps1"
}

dotenv $env:DOTS
dotenv $env:secretdir

$psource = ( 'readline', 'prompt', 'modules', 'fzf', 'aliases', 'completions')
if ($PSEdition -eq 'Core') {
  $psource += ('copilot')
}
foreach ( $piece in $psource ) {
  if (Test-Path "$PSCOMPONENT\$piece.ps1") {
    Unblock-File "$PSCOMPONENT\$piece.ps1"
    . "$PSCOMPONENT\$piece.ps1"
  }
}

Invoke-Expression (& { ( zoxide init powershell --cmd cd | Out-String ) })
Remove-DuplicatePaths

if ($env:isReloading) {
  Clear-Host
  wh 'Profile reloaded.' green -box -border black -bb 1 -ba 1 -pad $env:padding
  $env:isReloading = $false
}

function rl {
  [CmdletBinding()]
  param ()
  [bool]$env:isReloading = "$true"

  $env:isReloading = $true
  Clear-Host
  wh 'Restarting PowerShell..' blue -box -border darkgray -bb 1 -ba 1 -pad $env:padding
  & pwsh -NoExit -Command "Set-Location -Path $(Get-Location)'"
  exit
}

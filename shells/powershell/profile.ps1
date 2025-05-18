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

$psource = ('util')
foreach ( $piece in $psource ) {
  if (Test-Path "$PSCOMPONENT\$piece.ps1") {
    Unblock-File "$PSCOMPONENT\$piece.ps1"
    . "$PSCOMPONENT\$piece.ps1"
  }
}

function dotenv {
  [CmdletBinding()]
  param (
    [Parameter(Mandatory = $true)]
    [string]$path,
    [switch]$v
  )
  $envFilePath = Join-Path -Path $path -ChildPath '.dotenv'
  if (Test-Path $envFilePath) {
    if ($v) {
      wh -box -border 0 -bb 1 -ba 1 -pad $env:padding 'DOTENV' white ' │ ' darkgray 'LOADING' darkgray ' │ ' darkgray "$path\" blue '.env' green
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
        wh -bb 0 -ba 0 -nl -pad $env:padding '' darkgray $expandedName Yellow ' = ' DarkGray $expandedValue Gray
      }
    }
    if ($v) {
      linebreak 2
    }
  }
}
dotenv $env:DOTS
dotenv $env:secretdir

$psource = ('functions', 'path', 'modules', 'fzf', 'readline', 'prompt', 'aliases', 'completions', 'copilot')
foreach ( $piece in $psource ) {
  if (Test-Path "$PSCOMPONENT\$piece.ps1") {
    Unblock-File "$PSCOMPONENT\$piece.ps1"
    . "$PSCOMPONENT\$piece.ps1"
  }
}

Invoke-Expression (& { (zoxide init powershell | Out-String) })

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

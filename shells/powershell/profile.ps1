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

$psource = ('util', 'functions')
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
  $envFilePath = Join-Path -Path $path -ChildPath '.dotenv'
  if (Test-Path $envFilePath) {
    if ($v) {
      wh 'DOTENV' white ' │ ' darkgray 'LOADING' darkgray ' │ ' darkgray "$env:DOTS\" blue '.env' green -box -border 0 -bb 1 -ba 1 -padout $env:padding
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
        wh '' darkgray $expandedName yellow ' = ' darkgray $expandedValue white -bb 1 -ba 1 -padout $env:padding
      }
    }
  }
}
dotenv $env:DOTS
dotenv $env:secretdir

$psource = ('path', 'fzf', 'modules', 'readline', 'prompt', 'aliases', 'completions')
foreach ( $piece in $psource ) {
  Unblock-File "$PSCOMPONENT\$piece.ps1"
  . "$PSCOMPONENT\$piece.ps1"
}

Invoke-Expression (& { (zoxide init powershell | Out-String) })

if ($env:isReloading) {
  Clear-Host
  wh 'Profile reloaded.' green -box -border darkgray -bb 1 -ba 1 -padout $env:padding
  $env:isReloading = $false
}

function rl {
  [CmdletBinding()]
  param ()
  [bool]$env:isReloading = "$true"

  $env:isReloading = $true
  Clear-Host
  wh 'Restarting PowerShell..' blue -box -border darkgray -bb 1 -ba 1 -padout $env:padding
  & pwsh -NoExit -Command "Set-Location -Path $(Get-Location)'"
  exit
}

. 'C:\Users\njen\Documents\PowerShell\gh-copilot.ps1'

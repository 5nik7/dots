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

function Find-WindotsRepository {
  <#
    .SYNOPSIS
        Finds the local Windots repository.
    #>
  [CmdletBinding()]
  param (
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$ProfilePath
  )

  Write-Verbose 'Resolving the symbolic link for the profile'
  $profileSymbolicLink = Get-ChildItem $ProfilePath | Where-Object FullName -EQ $PROFILE.CurrentUserAllHosts
  return Split-Path $profileSymbolicLink.Target
}

$psource = ('util', 'functions', 'env')
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

$psource = ('path', 'fzf', 'modules', 'hooks', 'readline', 'prompt', 'aliases', 'completions')
foreach ( $piece in $psource ) {
  Unblock-File "$PSCOMPONENT\$piece.ps1"
  . "$PSCOMPONENT\$piece.ps1"
}

# Invoke-Expression "$(direnv hook pwsh)"

# (& pyenv-venv init)

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

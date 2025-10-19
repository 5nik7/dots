if ($Host.UI.RawUI -and -not $IsWindows -or $Host.Name -ne 'ServerRemoteHost') {
}

Import-Module 'PSDots'

if (Test-Path "$PSCOMPONENT\functions.ps1") {
  Unblock-File "$PSCOMPONENT\functions.ps1" -ErrorAction SilentlyContinue
  . "$PSCOMPONENT\functions.ps1"
}

if ($Host.UI.RawUI) {
  dotenv $env:DOTS -ErrorAction SilentlyContinue
  dotenv $env:secretdir -ErrorAction SilentlyContinue

  $psource = ( 'readline', 'prompt', 'aliases')
  if ($PSEdition -eq 'Core') { $psource += 'copilot' }
  foreach ($piece in $psource) {
    $pfile = Join-Path $PSCOMPONENT "$piece.ps1"
    if (Test-Path $pfile) {
      Unblock-File $pfile -ErrorAction SilentlyContinue
      . $pfile
    }
  }

  Set-FuzzyOpts -ErrorAction SilentlyContinue

  if (Get-Command fzf -ErrorAction SilentlyContinue) {
    Import-ScoopModule -Name 'PsFzf' -ErrorAction SilentlyContinue
    Set-PsFzfOption -TabExpansion -ErrorAction SilentlyContinue
  }
}

$ChocolateyProfile = "$env:ChocolateyInstall\helpers\chocolateyProfile.psm1"
if (Test-Path($ChocolateyProfile)) {
  Import-Module "$ChocolateyProfile"
}

$null = Register-EngineEvent -SourceIdentifier 'PowerShell.OnIdle' -MaxTriggerCount 1 -Action {
  Import-Module 'Terminal-Icons'
  Import-Module 'blastoff'
  # Import-Module 'powernerd'
  # Import-Module 'winwal'
  Import-Module 'lab'
  Import-Module 'UsefulArgumentCompleters'

  if (Get-Command scoop -ErrorAction SilentlyContinue) { Import-ScoopModule -Name 'scoop-completion' -ErrorAction SilentlyContinue }
  Import-Module 'git-completion'
  Import-Module 'PSToml'
  Import-Module 'powershell-yaml'

  try { if (Get-Command vivid -ErrorAction SilentlyContinue) { $env:LS_COLORS = "$(vivid generate catppuccin-mocha)" } } catch { }

  # Register winget completer after modules are available
  Register-ArgumentCompleter -Native -CommandName winget -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)
    [Console]::InputEncoding = [Console]::OutputEncoding = $OutputEncoding = [System.Text.Utf8Encoding]::new()
    $Local:word = $wordToComplete.Replace('"', '""')
    $Local:ast = $commandAst.ToString().Replace('"', '""')
    winget complete --word="$Local:word" --commandline "$Local:ast" --position $cursorPosition | ForEach-Object {
      [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
    }
  }
}
# Remove-DuplicatePaths

if ($env:isReloading) {
  Clear-Host
  wh ' ' white 'PROFILE ' gray 'RELOADED' green  -box -border black -bb 1 -ba 2 -pad $env:padding
  $env:isReloading = $false
}

function rl {
  [CmdletBinding()]
  param ()
  [bool]$env:isReloading = "$true"

  $env:isReloading = $true
  Clear-Host
  wh 'RELOADING ' darkgray ' ' white 'PROFILE' gray -box -border black -bb 1 -ba 2 -pad $env:padding
  & pwsh -NoExit -Command "Set-Location -Path $(Get-Location)'"
  exit
}

Invoke-Expression "$(vfox activate pwsh)"

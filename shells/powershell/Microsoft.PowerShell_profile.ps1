if ($Host.UI.RawUI -and -not $IsWindows -or $Host.Name -ne 'ServerRemoteHost')
{
}

Import-Module 'PSDots'

if (Test-Path "$PSCOMPONENT\functions.ps1")
{
  Unblock-File "$PSCOMPONENT\functions.ps1" -ErrorAction SilentlyContinue
  . "$PSCOMPONENT\functions.ps1"
}

if ($Host.UI.RawUI)
{
  dotenv $env:DOTS -ErrorAction SilentlyContinue
  dotenv $env:secretdir -ErrorAction SilentlyContinue

  $psource = ( 'readline', 'prompt', 'aliases')
  if ($PSEdition -eq 'Core') { $psource += 'copilot' }
  foreach ($piece in $psource)
  {
    $pfile = Join-Path $PSCOMPONENT "$piece.ps1"
    if (Test-Path $pfile)
    {
      Unblock-File $pfile -ErrorAction SilentlyContinue
      . $pfile
    }
  }

  Set-FuzzyOpts -ErrorAction SilentlyContinue

  if (Get-Command fzf -ErrorAction SilentlyContinue)
  {
    Import-ScoopModule -Name 'PsFzf' -ErrorAction SilentlyContinue
    Set-PsFzfOption -TabExpansion -ErrorAction SilentlyContinue
  }
}

$ChocolateyProfile = "$env:ChocolateyInstall\helpers\chocolateyProfile.psm1"
if (Test-Path($ChocolateyProfile))
{
  Import-Module "$ChocolateyProfile"
}

$null = Register-EngineEvent -SourceIdentifier 'PowerShell.OnIdle' -MaxTriggerCount 1 -Action {
  Import-Module -Global -Name 'Terminal-Icons'
  Import-Module -Global -Name 'lab'
  Import-Module -Global -Name 'blastoff'
  Import-Module -Global -Name 'powernerd'
  Import-Module -Global -Name 'winwal'
  Import-Module -Global -Name 'UsefulArgumentCompleters'

  if (Get-Command scoop -ErrorAction SilentlyContinue) { Import-ScoopModule -Name 'scoop-completion' -ErrorAction SilentlyContinue }
  Import-Module -Global -Name 'git-completion'
  Import-Module -Global -Name 'PSToml'
  Import-Module -Global -Name 'powershell-yaml'

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

Invoke-Expression "$(vfox activate pwsh)"
function rl
{
  wh 'RELOADING ' darkgray ' ' white 'PROFILE' gray -box -border black -bb 1 -ba 1 -pad $env:padding
  & $PROFILE
  wh ' ' white 'PROFILE ' gray 'RELOADED' green -box -border black -bb 0 -ba 1 -pad $env:padding
}

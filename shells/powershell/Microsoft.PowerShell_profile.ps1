Import-Module -Name 'PSDots' -Global

if (Test-Path "$PSCOMPONENT\functions.ps1") {
  Unblock-File "$PSCOMPONENT\functions.ps1"
  . "$PSCOMPONENT\functions.ps1"
}

dotenv $env:DOTS
dotenv $env:secretdir

$psource = ( 'readline', 'prompt', 'aliases')
if ($PSEdition -eq 'Core') {
  $psource += ('copilot')
}
foreach ( $piece in $psource ) {
  if (Test-Path "$PSCOMPONENT\$piece.ps1") {
    Unblock-File "$PSCOMPONENT\$piece.ps1"
    . "$PSCOMPONENT\$piece.ps1"
  }
}

Set-FuzzyOpts

if (Test-CommandExists fzf) {
  Import-ScoopModule -Name 'PsFzf'
  Set-PsFzfOption -TabExpansion
}

# Import-Module -Name 'PowerShellGet' -Global
Import-Module -Name 'Terminal-Icons' -Global
Import-Module -Name 'blastoff' -Global
# Import-Module -Name 'powernerd' -Global
# Import-Module -Name 'winwal' -Global
Import-Module -Name 'lab' -Global
Import-Module -Name 'UsefulArgumentCompleters' -Global

Import-ScoopModule -Name 'scoop-completion'
Import-Module -Name 'git-completion' -Global
Import-Module -Name 'PSToml' -Global
Import-Module -Name 'powershell-yaml' -Global

& starship completions power-shell | Out-String | Invoke-Expression
& bat --completion ps1 | Out-String | Invoke-Expression
& gh completion -s powershell | Out-String | Invoke-Expression
& uv generate-shell-completion powershell | Out-String | Invoke-Expression
& uvx --generate-shell-completion powershell | Out-String | Invoke-Expression
& glow completion powershell | Out-String | Invoke-Expression
& gowall completion powershell | Out-String | Invoke-Expression
& volta completions powershell | Out-String | Invoke-Expression

Register-ArgumentCompleter -Native -CommandName winget -ScriptBlock {
  param($wordToComplete, $commandAst, $cursorPosition)
  [Console]::InputEncoding = [Console]::OutputEncoding = $OutputEncoding = [System.Text.Utf8Encoding]::new()
  $Local:word = $wordToComplete.Replace('"', '""')
  $Local:ast = $commandAst.ToString().Replace('"', '""')
  winget complete --word="$Local:word" --commandline "$Local:ast" --position $cursorPosition | ForEach-Object {
    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
  }
}

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

$ChocolateyProfile = "$env:ChocolateyInstall\helpers\chocolateyProfile.psm1"
if (Test-Path($ChocolateyProfile)) {
  Import-Module "$ChocolateyProfile"
}

$null = Register-EngineEvent -SourceIdentifier 'PowerShell.OnIdle' -MaxTriggerCount 1 -Action {
  $Global:PSDefaultParameterValues.Add("Out-Default:OutVariable", "__")
  $Global:PSDefaultParameterValues.Add("Update-Help:UICulture", [cultureinfo]::new("en-US"))
  if ($Host.Name -ne 'Windows PowerShell ISE Host') {
    Set-PSReadlineKeyHandler -Chord CTRL+Tab -Function TabCompleteNext
    Set-PSReadlineKeyHandler -Chord ALT+F4   -Function ViExit
    Set-PSReadLineKeyHandler -Chord CTRL+l   -ScriptBlock {
      Clear-Host
      [Microsoft.PowerShell.PSConsoleReadLine]::InvokePrompt($null, 0)
    }
  }
  $env:LS_COLORS = "$(vivid generate catppuccin-mocha)"
  Remove-DuplicatePaths
}

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
  Add-PSModulePath -Path $env:PSMODS
  Import-Module -Name 'PowerShellGet' -Global
  Import-Module -Name 'Terminal-Icons' -Global
  Import-Module -Name 'PSDots' -Global
  Import-Module -Name 'blastoff' -Global
  Import-Module -Name 'powernerd' -Global
  Import-Module -Name 'winwal' -Global
  Import-Module -Name 'lab' -Global
  Import-Module -Name UsefulArgumentCompleters -Global
  # Import-UsefulArgumentCompleterSet -OptionalCompleter Hyperv
  (& pyenv-venv completion) | Out-String | Invoke-Expression
  (& starship completions power-shell) | Out-String | Invoke-Expression
  (& bat --completion ps1) | Out-String | Invoke-Expression
  (& gh completion -s powershell) | Out-String | Invoke-Expression
  (& tree-sitter complete --shell power-shell) | Out-String | Invoke-Expression
  (& uv generate-shell-completion powershell) | Out-String | Invoke-Expression
  (& uvx --generate-shell-completion powershell) | Out-String | Invoke-Expression
  (& glow completion powershell) | Out-String | Invoke-Expression
  (& wezterm shell-completion --shell power-shell) | Out-String | Invoke-Expression
  Register-ArgumentCompleter -Native -CommandName winget -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)
    [Console]::InputEncoding = [Console]::OutputEncoding = $OutputEncoding = [System.Text.Utf8Encoding]::new()
    $Local:word = $wordToComplete.Replace('"', '""')
    $Local:ast = $commandAst.ToString().Replace('"', '""')
    winget complete --word="$Local:word" --commandline "$Local:ast" --position $cursorPosition | ForEach-Object {
      [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
    }
  }
  Import-ScoopModule -Name 'scoop-completion'
  Import-Module -Name 'git-completion' -Global
  $env:LS_COLORS = "$(vivid generate catppuccin-mocha)"

  Set-FuzzyOpts

}

if (Test-CommandExists fzf) {
  Import-ScoopModule -Name 'PsFzf'
  Set-PsFzfOption -TabExpansion
}

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

$ChocolateyProfile = "$env:ChocolateyInstall\helpers\chocolateyProfile.psm1"
if (Test-Path($ChocolateyProfile)) {
  Import-Module "$ChocolateyProfile"
}

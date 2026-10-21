# Lean personal setup. Dots environment/theme/completion belong to lib/dots/shell.
if ($global:_DotsLeanPowerShellReady) { return }
. (Join-Path $env:PWSH 'helpers.ps1')

$global:DOTS = $env:DOTS
$global:DOTFILES = $env:DOTFILES
$global:DOTSBIN = $env:DOTBIN
$env:DOTSBIN = $env:DOTBIN
$global:DOTSCRIPTS = $env:DOTSCRIPTS

Set-Alias edit Edit-Item
Set-Alias e Edit-Item
Set-Alias ep Edit-Profile
Set-Alias ls Invoke-eza -Option AllScope
Set-Alias lg lazygit
Set-Alias g git
Set-Alias d y
Set-Alias dev cdev
Set-Alias fixhistory Remove-DuplicatePSReadlineHistory

# Replace only the personal prompt underneath Dots' existing refresh wrapper.
$global:_DotsLeanPrompt = { '[' + $PWD.Path + '] $ ' }
if ($global:_DotsPromptInstalled) { $global:_DotsPreviousPrompt = $global:_DotsLeanPrompt }
else { Set-Item Function:global:prompt $global:_DotsLeanPrompt }

# PSReadLine is the sole interactive module loaded eagerly. No module inventory.
if ($Host.Name -eq 'ConsoleHost' -and -not [Console]::IsInputRedirected) {
  try {
    Import-Module PSReadLine -Global -ErrorAction Stop
    Set-PSReadLineOption -EditMode Vi -BellStyle None -HistoryNoDuplicates `
      -HistorySearchCursorMovesToEnd -MaximumHistoryCount 50000
    Set-PSReadLineKeyHandler -Key Tab -Function TabCompleteNext
    Set-PSReadLineKeyHandler -Chord 'Alt+f' -ScriptBlock { Invoke-DotsFuzzyCompletion }
  } catch { Write-Warning ('Dots line editing: ' + $_.Exception.Message) }
}
$global:_DotsLeanPowerShellReady = $true

# Starship supports both Desktop 5.1 and Core. Generate its full script in one
# process; optional completion generators and transient prompt hooks stay off.
$dotsStarshipCommand = & {
  # Missing executables must not trigger an inventory of installed modules.
  $PSModuleAutoLoadingPreference = 'None'
  Get-Command starship -CommandType Application -TotalCount 1 -ErrorAction Ignore
}
if ($dotsStarshipCommand) {
  try { . (Join-Path $env:PWSH 'optional.ps1') starship }
  catch {
    Install-DotsPrompt -Renderer $global:_DotsLeanPrompt
    Write-Warning ('Dots Starship: ' + $_.Exception.Message)
  }
}

# Use this engine's own profile directory, including redirected Documents.
$dotsTerminalIntegration = Join-Path (Split-Path -Parent $PROFILE.CurrentUserAllHosts) 'shell-integration_v7.ps1'
if (Test-Path -LiteralPath $dotsTerminalIntegration -PathType Leaf) {
  try { . (Join-Path $env:PWSH 'optional.ps1') terminal }
  catch { Write-Warning ('Dots terminal integration: ' + $_.Exception.Message) }
}
Remove-Variable dotsTerminalIntegration, dotsStarshipCommand -ErrorAction Ignore

function Fresh {
  & $PROFILE
  Write-Host -ForegroundColor DarkGray '┌───────────────────┐'
  Write-Host -ForegroundColor DarkGray '│' -NoNewline
  Write-Host -ForegroundColor Cyan ' Profile reloaded. ' -NoNewline
  Write-Host -ForegroundColor DarkGray '│'
  Write-Host -ForegroundColor DarkGray '└───────────────────┘'
}

If (Test-Path "C:\miniconda3\Scripts\conda.exe") {
    (& "C:\miniconda3\Scripts\conda.exe" "shell.powershell" "hook") | Out-String | ? { $_ } | Invoke-Expression
}

Import-Module "$($(Get-Item $(Get-Command scoop.ps1).Path).Directory.Parent.FullName)\modules\scoop-completion"
Import-Module npm-completion

$profileDirectory = [System.IO.Path]::GetDirectoryName($PROFILE)
foreach ( $includeFile in ("environment", "functions", "aliases", "secrets") ) {
  if (Test-Path $profileDirectory\$includeFile.ps1) {
    Unblock-File $profileDirectory\$includeFile.ps1
    . "$profileDirectory\$includeFile.ps1"
  }
}

$scriptsPath = "$profileDirectory\Scripts"
if (-not ($env:Path -split ';' | Select-String -SimpleMatch $scriptsPath)) {
  Add-Path -Path $scriptsPath
}

$ChocolateyProfile = "$env:ChocolateyInstall\helpers\chocolateyProfile.psm1"
if (Test-Path($ChocolateyProfile)) {
  Import-Module "$ChocolateyProfile"
}

$env:FZF_DEFAULT_OPTS = if (Test-CommandExists fzf) {
  "--ansi --layout reverse --info inline --height 80% --cycle --border sharp
--prompt ' ' --pointer ' ' --marker ' '
--color 'fg:-1,bg:-1,hl:5:underline,fg+:3,bg+:-1,hl+:5:underline,gutter:-1,border:0'
--color 'info:2,prompt:5,spinner:2,pointer:6,marker:4'
--no-scrollbar"
}



if ($host.Name -eq 'ConsoleHost') {
  Import-Module PSReadLine

  $PSReadLineOptions = @{
    HistoryNoDuplicates           = $true
    HistorySearchCursorMovesToEnd = $true
    HistorySearchCaseSensitive    = $false
    MaximumHistoryCount           = "10000"
    ShowToolTips                  = $true
    ContinuationPrompt            = " "
    BellStyle                     = "None"
    PredictionSource              = "History"
    EditMode                      = "Vi"
    TerminateOrphanedConsoleApps  = $true
    PredictionViewStyle           = "InlineView"
    Colors                        = @{
      Comment                = 'DarkGray'
      Command                = 'Green'
      Number                 = 'Magenta'
      Member                 = 'Red'
      Operator               = 'DarkYellow'
      Type                   = 'Cyan'
      Variable               = 'DarkCyan'
      Parameter              = 'Yellow'
      ContinuationPrompt     = 'Black'
      Default                = 'White'
      InlinePrediction       = 'DarkGray'
      ListPrediction         = 'DarkGray'
      ListPredictionSelected = 'DarkGray'
    }
  }
  Set-PSReadLineOption @PSReadLineOptions
}
Set-PSReadLineOption -AddToHistoryHandler {
  param($line)
  $line -notmatch '(^\s+|^rm|^Remove-Item|fl$)'
}
Set-PsFzfOption -PSReadlineChordProvider 'Ctrl+t' -PSReadlineChordReverseHistory 'Ctrl+r'

Set-PSReadLineKeyHandler -Key Tab -ScriptBlock { Invoke-FzfTabCompletion }
# Set-PSReadlineKeyHandler -Key Tab -Function MenuComplete
Set-PSReadLineKeyHandler -Key UpArrow -Function HistorySearchBackward
Set-PSReadLineKeyHandler -Key DownArrow -Function HistorySearchForward
Set-PSReadLineKeyHandler -Chord Enter -Function ValidateAndAcceptLine

Set-PsFzfOption -TabExpansion

function Invoke-Starship-TransientFunction {
  &starship module character
}
Invoke-Expression (&starship init powershell)
Enable-TransientPrompt

function OnViModeChange {
  if ($args[0] -eq 'Command') {

    # Set the cursor to a solid block.
    Write-Host -NoNewLine "`e[2 q"
  }
  else {
    # Set the cursor to a blinking line.
    Write-Host -NoNewLine "`e[5 q"
  }
}
Set-PSReadLineOption -ViModeIndicator Script -ViModeChangeHandler $Function:OnViModeChange
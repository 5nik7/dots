﻿$ENV:DOTS = "$HOME\dev\dots"
# $DOTS = $ENV:DOTS

$ENV:DOTFILES = "$ENV:DOTS\configs"
# $DOTFILES = $ENV:DOTFILES

$ENV:PSDOT = "$ENV:DOTS\shells\powershell"
# $PSDOT = $ENV:PSDOT

$ENV:BASHDOT = "$ENV:DOTS\shells\bash"
# $BASHDOT = $ENV:BASHDOT

$ENV:ZSHDOT = "$ENV:DOTS\shells\zsh"
# $ZSHDOT = $ENV:ZSHDOT

$ENV:PROJECTS = "$HOME\dev"
# $PROJECTS = $ENV:PROJECTS

foreach ( $includeFile in ("environment", "functions", "aliases", "lab") ) {
  Unblock-File "$ENV:PSDOT\$includeFile.ps1"
  . "$ENV:PSDOT\$includeFile.ps1"
}

$ENV:dotscripts = "$ENV:PSDOT\Scripts"
if (Test-Path($ENV:dotscripts)) {
  Add-Path -Path $ENV:dotscripts
}

$ENV:DOTBIN = "$ENV:DOTS\bin"
if (Test-Path($ENV:DOTBIN)) {
  Add-Path -Path $ENV:DOTBIN
}

# pyenv-venv init

function ReloadProfile {
  & $PROFILE
  Write-Host -ForegroundColor DarkGray '┌───────────────────┐'
  Write-Host -ForegroundColor DarkGray '│' -NoNewline
  Write-Host -ForegroundColor Cyan ' Profile reloaded. ' -NoNewline
  Write-Host -ForegroundColor DarkGray '│'
  Write-Host -ForegroundColor DarkGray '└───────────────────┘'
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
    PredictionViewStyle           = "InlineView"
    Colors                        = @{
      Comment                = 'DarkGray'
      Command                = 'DarkGreen'
      Emphasis               = 'Cyan'
      Number                 = 'Yellow'
      Member                 = 'Blue'
      Operator               = 'Blue'
      Type                   = 'Yellow'
      String                 = 'Green'
      Variable               = 'Cyan'
      Parameter              = 'Blue'
      ContinuationPrompt     = 'Black'
      Default                = 'White'
      InlinePrediction       = 'DarkGray'
      ListPrediction         = 'DarkGray'
      ListPredictionSelected = 'DarkGray'
      ListPredictionTooltip  = 'DarkGray'
    }
  }
  Set-PSReadLineOption @PSReadLineOptions
}

Set-PSReadlineKeyHandler -Key Tab -Function MenuComplete
Set-PSReadLineKeyHandler -Key UpArrow -Function HistorySearchBackward
Set-PSReadLineKeyHandler -Key DownArrow -Function HistorySearchForward
Set-PSReadLineKeyHandler -Chord Enter -Function ValidateAndAcceptLine


Invoke-Expression (&starship init powershell)
Enable-TransientPrompt
function Invoke-Starship-TransientFunction {
  &starship module character
}

Set-PSReadLineOption -ViModeIndicator script -ViModeChangeHandler {
  [Microsoft.PowerShell.PSConsoleReadLine]::InvokePrompt()
  if ($args[0] -eq 'Command') {
    # Set the cursor to a solid block.
    Write-Host -NoNewLine "`e[2 q"
  }
  else {
    # Set the cursor to a blinking line.
    Write-Host -NoNewLine "`e[5 q"
  }
}
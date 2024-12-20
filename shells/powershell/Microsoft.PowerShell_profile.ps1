﻿$ENV:DOTS = "$ENV:USERPROFILE\dev\dots"
$ENV:DOTFILES = "$ENV:DOTS\configs"
$ENV:PSDOT = "$ENV:DOTS\shells\powershell"
$ENV:BASHDOT = "$ENV:DOTS\shells\bash"
$ENV:ZSHDOT = "$ENV:DOTS\shells\zsh"
$ENV:PROJECTS = "$ENV:USERPROFILE\dev"
$ENV:DEV = "$ENV:USERPROFILE\dev"
$ENV:WINDOTCONF = "$ENV:USERPROFILE\.config"

$ENV:DRIP = "$ENV:DOTS\drip"
$ENV:DRIP_COLS = "$ENV:DRIP\colorschemes"
$ENV:DRIP_TEMPS = "$ENV:DRIP\tenplates"
$ENV:WALLS = "$ENV:DOTS\walls"

$ENV:NVM_HOME = "$ENV:APPDATA\nvm"
$ENV:NVM_SYMLINK = "$ENV:HOMEDRIVE\node"
$ENV:GOPATH = "$ENV:USERPROFILE\go"
$ENV:GOBIN = "$ENV:USERPROFILE\go\bin"

$ENV:DOCUMENTS = [Environment]::GetFolderPath("mydocuments")
$ENV:DOWNLOADS = "$ENV:USERPROFILE\Downloads"

$ENV:STARSHIP_CACHE = "$ENV:LOCALAPPDATA\Temp"
$ENV:BAT_CONFIG_PATH = "$ENV:DOTFILES\bat\bat.conf"
$ENV:YAZI_CONFIG_HOME = "$ENV:DOTFILES\yazi"
$GITBIN = "C:\Git\usr\bin"
$ENV:YAZI_FILE_ONE = "$GITBIN\file.exe"
$BAT_THEME = if ($ENV:THEME) { $ENV:THEME }
else { 'base16' }
$ENV:BAT_THEME = $BAT_THEME

$TIC = (Get-ItemProperty 'HKCU:\Control Panel\Desktop' TranscodedImageCache -ErrorAction Stop).TranscodedImageCache
$wallout = [System.Text.Encoding]::Unicode.GetString($TIC) -replace '(.+)([A-Z]:[0-9a-zA-Z\\])+', '$2'
$ENV:WALLPAPER = $wallout

foreach ( $includeFile in ("functions", "aliases", "lab") ) {
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

if ($host.Name -eq 'ConsoleHost') {
  Import-Module PSReadLine

  $PSReadLineOptions = @{
    HistoryNoDuplicates           = $true
    HistorySearchCursorMovesToEnd = $true
    HistorySearchCaseSensitive    = $false
    MaximumHistoryCount           = "50000"
    ShowToolTips                  = $true
    ContinuationPrompt            = " "
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
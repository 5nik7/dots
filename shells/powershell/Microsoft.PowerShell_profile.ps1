$ENV:PROJECTS = "C:\projects"
$PROJECTS = $ENV:PROJECTS

$ENV:DOTS = $ENV:PROJECTS + "\dots"
$DOTS = $ENV:DOTS

$ENV:DOTFILES = $ENV:DOTS + "\configs"
$DOTFILES = $ENV:DOTFILES

$ENV:DOTSHELL = $DOTS + "\shells"
$DOTSHELL = $ENV:DOTSHELL

$ENV:PSDOT = $DOTSHELL + "\powershell"
$PSDOT = $ENV:PSDOT

$ENV:BASHDOT = $DOTSHELL + "\bash"
$BASHDOT = $ENV:BASHDOT

$ENV:ZSHDOT = $DOTSHELL + "\zsh"
$ZSHDOT = $ENV:ZSHDOT

foreach ( $includeFile in ("environment", "functions", "aliases", "lab") ) {
  Unblock-File $PSDOT\$includeFile.ps1
  . "$PSDOT\$includeFile.ps1"
}

$ENV:scriptsPath = "$PSDOT\Scripts"
$scriptsPath = $ENV:scriptsPath
if (Test-Path($scriptsPath)) {
  Add-Path -Path $scriptsPath
}

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
      Command                = 'Green'
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
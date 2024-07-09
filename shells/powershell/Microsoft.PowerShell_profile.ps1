$profileDirectory = [System.IO.Path]::GetDirectoryName($PROFILE)
foreach ( $includeFile in ("environment", "functions", "aliases") ) {
  Unblock-File $profileDirectory\$includeFile.ps1
  . "$profileDirectory\$includeFile.ps1"
}
$scriptsPath = "$profileDirectory\Scripts"
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
    TerminateOrphanedConsoleApps  = $true
    PredictionViewStyle           = "InlineView"
    Colors                        = @{
      Comment                = 'DarkGray'
      Command                = 'Magenta'
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
Invoke-Expression (&starship init powershell)

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
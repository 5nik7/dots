if ($isAdmin) {
  $env:AdminSymbol = '#'
}
else {
  $env:AdminSymbol = ''
}

function Invoke-Starship-PreCommand {
  $WarningPreference = 'SilentlyContinue'
  $ErrorActionPreference = 'SilentlyContinue'
}

Invoke-Expression (&starship init powershell)
Enable-TransientPrompt
function Invoke-Starship-TransientFunction {
  &starship module character
}

function OnViModeChangeCore {
  [Microsoft.PowerShell.PSConsoleReadLine]::InvokePrompt()
  if ($args[0] -eq 'Command') {
    [Microsoft.PowerShell.PSConsoleReadLine]::ForwardChar()
    Write-Host -NoNewLine "`e[2 q"
  }
  else {
    Write-Host -NoNewLine "`e[5 q"
  }
}

function OnViModeChangeDesktop {
  [Microsoft.PowerShell.PSConsoleReadLine]::InvokePrompt()
}

if ($PSEdition -eq 'Core') {
  Set-PSReadLineOption -ViModeIndicator Script -ViModeChangeHandler $Function:OnViModeChangeCore
}

if ($PSEdition -eq 'Desktop') {
  Set-PSReadLineOption -ViModeIndicator Script -ViModeChangeHandler $Function:OnViModeChangeDesktop
}

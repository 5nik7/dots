function Invoke-Starship-TransientFunction {
  &starship module character
}

Invoke-Expression (&starship init powershell)
Enable-TransientPrompt
Invoke-Expression (& { ( zoxide init powershell --cmd cd | Out-String ) })

function OnViModeChangeCore {
  [Microsoft.PowerShell.PSConsoleReadLine]::InvokePrompt()
  if ($args[0] -eq 'Command') {
    [Microsoft.PowerShell.PSConsoleReadLine]::ForwardChar()
    Write-Host -NoNewLine "`e[2 q"
  }
  else {
    Write-Host -NoNewLine "`e[5 q"
  }1
}

# Set-PSReadLineOption -ViModeIndicator Script -ViModeChangeHandler $Function:OnViModeChangeCore


function OnViModeChangeDesktop {
  [Microsoft.PowerShell.PSConsoleReadLine]::InvokePrompt()
}

if ($PSEdition -eq 'Core') {
  Set-PSReadLineOption -ViModeIndicator Script -ViModeChangeHandler $Function:OnViModeChangeCore
}

if ($PSEdition -eq 'Desktop') {
  Set-PSReadLineOption -ViModeIndicator Script -ViModeChangeHandler $Function:OnViModeChangeDesktop
}

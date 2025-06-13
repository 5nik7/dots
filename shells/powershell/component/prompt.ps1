function Invoke-Starship-TransientFunction { &starship module character }
Invoke-Expression (&starship init powershell)
Enable-TransientPrompt

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

function OnViModeChangeDesktop { [Microsoft.PowerShell.PSConsoleReadLine]::InvokePrompt() }

if ($PSEdition -eq 'Core') { Set-PSReadLineOption -ViModeIndicator Script -ViModeChangeHandler $Function:OnViModeChangeCore }

if ($PSEdition -eq 'Desktop') { Set-PSReadLineOption -ViModeIndicator Script -ViModeChangeHandler $Function:OnViModeChangeDesktop }

if (Get-Command zoxide -ErrorAction SilentlyContinue) {
  Invoke-Expression (& { (zoxide init --cmd cd powershell | Out-String) })
}
else {
  Write-Host 'zoxide command not found. Attempting to install via winget...'
  try {
    winget install -e --id ajeetdsouza.zoxide
    Write-Host 'zoxide installed successfully. Initializing...'
    Invoke-Expression (& { (zoxide init powershell | Out-String) })
  }
  catch {
    Write-Error "Failed to install zoxide. Error: $_"
  }
}
Set-Alias -Name z -Value __zoxide_z -Option AllScope -Scope Global -Force
Set-Alias -Name zi -Value __zoxide_zi -Option AllScope -Scope Global -Force

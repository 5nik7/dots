Invoke-Expression (&starship init powershell)
Enable-TransientPrompt
function Invoke-Starship-TransientFunction {
    &starship module character
}

Set-PSReadLineOption -ViModeIndicator script -ViModeChangeHandler {
    [Microsoft.PowerShell.PSConsoleReadLine]::InvokePrompt()
    if ($args[0] -eq 'Command') {
        # Set the cursor to a solid block.
        [Microsoft.PowerShell.PSConsoleReadLine]::ForwardChar()
        Write-Host -NoNewLine "`e[2 q"
    }
    else {
        # Set the cursor to a blinking line.
        Write-Host -NoNewLine "`e[5 q"
    }
}
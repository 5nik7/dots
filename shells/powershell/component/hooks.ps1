
Invoke-Expression (& { (zoxide init powershell | Out-String) })

Invoke-Expression "$(direnv hook pwsh)"

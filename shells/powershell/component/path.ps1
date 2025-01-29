$Env:PSCRIPTS = "$Env:PSDOT\Scripts"
if (Test-Path($Env:PSCRIPTS)) {
    Add-Path -Path $Env:PSCRIPTS
}

$Env:DOTBIN = "$Env:DOTS\bin"
if (Test-Path($Env:DOTBIN)) {
    Add-Path -Path $Env:DOTBIN
}

$localbin = "$Env:USERPROFILE\.local\bin"
if (Test-Path($localbin)) {
    Add-Path -Path $localbin
}

$python3exePath = Split-Path -Parent (& { (pyenv which python3 | Out-String) }).Trim()
Add-PrependPath -Path $python3exePath

$pipexePath = Split-Path -Parent (& { (pyenv which pip | Out-String) }).Trim()
Add-PrependPath -Path $pipexePath
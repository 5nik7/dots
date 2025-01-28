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
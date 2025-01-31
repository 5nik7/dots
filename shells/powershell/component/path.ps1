$env:PSCRIPTS = "$env:PSDOT\Scripts"
$Global:PSCRIPTS = $env:PSCRIPTS
Add-Path -Path $env:PSCRIPTS

$env:DOTBIN = "$env:DOTS\bin"
Add-Path -Path $env:DOTBIN

$env:LOCALBIN = "$HOME\.local\bin"
Add-Path -Path $env:LOCALBIN

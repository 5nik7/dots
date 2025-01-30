$Env:PSCRIPTS = "$Env:PSDOT\Scripts"
Add-Path -Path $Env:PSCRIPTS

$Env:DOTBIN = "$Env:DOTS\bin"
Add-Path -Path $Env:DOTBIN

$localbin = "$Env:USERPROFILE\.local\bin"
Add-Path -Path $localbin

Add-Path -Path "$Env:PSMODS\winwal\colortool"

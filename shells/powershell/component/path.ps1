Add-Path -Path "$env:PSCRIPTS"
Add-Path -Path "$env:DOTBIN"
Add-Path -Path "$env:LOCALBIN"
Add-Path -Path "$env:LOCALAPPDATA\Microsoft\WindowsApps"

Remove-DuplicatePaths

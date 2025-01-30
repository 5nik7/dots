Set-Alias -Name cat -Value Get-ContentPretty -Option AllScope
Set-Alias -Name c -Value Clear-Host
Set-Alias -Name path -Value Get-Path
Set-Alias -Name env -Value Get-Env
# Set-Alias -Name ls -Value Get-ChildItemPretty -Option AllScope
Set-Alias -Name ll -Value Get-ChildItemPretty
Set-Alias -Name la -Value Get-ChildItemPretty
Set-Alias -Name l -Value Get-ChildItemPretty
Set-Alias -Name lt -Value Get-ChildItemPrettyTree
Set-Alias -Name which -Value Show-Command
Set-Alias -Name touch -Value New-File
Set-Alias -Name d -Value yy

Set-Alias -Name rlp -Value ReloadProfile
Set-Alias -Name g -Value git
Set-Alias -Name clo -Value Get-Repo

Set-Alias -Name edit -Value edit-item
Set-Alias -Name e -Value edit-item
Set-Alias -Name ep -Value Edit-Profile
Set-Alias -Name v -Value Invoke-Nvim

Set-Alias -Name ln -Value Set-Link

Set-Alias -Name weather -Value weather.ps1

Set-Alias -Name fetch -Value Get-Fetch

Set-Alias -Name lg -Value lazygit.exe
Set-Alias -Name NerdFonts -Value Invoke-NerdFontInstaller
Set-Alias -Name dev -Value cdprojects

Set-Alias -Name concol -Value list-console-colors
Set-Alias -Name rlp -Value Fresh

Set-Alias -Name edit -Value edit-item
Set-Alias -Name vim -Value edit-item
Set-Alias -Name vi -Value edit-item
Set-Alias -Name v -Value edit-item
Set-Alias -Name vp -Value Edit-Profile

Set-Alias -Name c -Value Clear-Host
Set-Alias -Name ln -Value Set-Link
Set-Alias -Name path -Value Get-Path
Set-Alias -Name env -Value Get-Env
Set-Alias -Name export -Value Export-EnvironmentVariable

Set-Alias -Name clhist -Value Remove-DuplicatePSReadlineHistory
Set-Alias -Name vhist -Value edit-history

# [alias]
# st = status -sb
# co = checkout
# c = commit --short
# ci = commit --short
# p = push
# l = log --graph --pretty=format:'%Cred%h%Creset -%C(yellow)%d%Creset %s %Cgreen(%cr) %C(bold blue)<%an>%Creset' --abbrev-commit --decorate --date=short
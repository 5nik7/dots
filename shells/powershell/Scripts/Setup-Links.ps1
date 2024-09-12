param(
    [switch] $v,
    [switch] $i
)

Write-Host ''
Set-Link "$ENV:DOTFILES\git\gitconfig" "$ENV:USERPROFILE\.gitconfig" -v:$v -i:$i
Set-Link "$ENV:DOTFILES\wsl\wslconfig" "$ENV:USERPROFILE\.wslconfig" -v:$v -i:$i
Set-Link "$ENV:DOTFILES\wal" "$ENV:USERPROFILE\.config\wal" -v:$v -i:$i
Set-Link "$ENV:DOTFILES\yasb" "$ENV:USERPROFILE\.config\yasb" -v:$v -i:$i
Set-Link "$ENV:DOTFILES\clink" "$ENV:LOCALAPPDATA\clink" -v:$v -i:$i
Set-Link "$ENV:DOTFILES\alacritty" "$ENV:LOCALAPPDATA\alacritty" -v:$v -i:$i
Set-Link "$ENV:DOTFILES\alacritty" "$ENV:APPDATA\alacritty" -v:$v -i:$i
Set-Link "$ENV:DOTFILES\yazi" "$ENV:APPDATA\yazi\config" -v:$v -i:$i
Set-Link "$ENV:DOTFILES\lsd" "$ENV:APPDATA\lsd" -v:$v -i:$i
Set-Link "$ENV:DOTFILES\vifm" "$ENV:APPDATA\vifm" -v:$v -i:$i
Set-Link "$ENV:DOTFILES\bat" "$ENV:APPDATA\bat" -v:$v -i:$i
Set-Link "$ENV:DOTFILES\glaze-wm" "$ENV:USERPROFILE\.glaze-wm" -v:$v -i:$i
Set-Link "$ENV:DOTFILES\komorebi\komorebi.json" "$ENV:USERPROFILE\komorebi.json" -v:$v -i:$i
Set-Link "$ENV:DOTFILES\komorebi\whkdrc" "$ENV:USERPROFILE\.config\whkdrc" -v:$v -i:$i
Set-Link "$ENV:PROJECTS\nvim" "$ENV:LOCALAPPDATA\nvim" -v:$v -i:$i
Set-Link "$ENV:PROJECTS\5ui7e" "$ENV:DOCUMENTS\Rainmeter\Skins\5ui7e" -v:$v -i:$i
Write-Host ''
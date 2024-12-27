param(
    [switch] $v,
    [switch] $i
)

Write-Host ''
Write-Host ' Setting up links...' -ForegroundColor Cyan

Set-link "$env:DRIP_COLS" "$ENV:WINDOTCONF\wal\colorschemes" 
Set-link "$env:DRIP_TEMPS" "$ENV:WINDOTCONF\wal\templates"

Set-Link "$ENV:DOTFILES\komorebi\komorebi.json" "$ENV:USERPROFILE\komorebi.json" -v:$v -i:$i
Set-Link "$ENV:DOTFILES\komorebi\komorebi.bar.json" "$ENV:USERPROFILE\komorebi.bar.json" -v:$v -i:$i
Set-Link "$ENV:DOTFILES\komorebi\whkdrc" "$env:WINDOTCONF\whkdrc" -v:$v -i:$i

Set-Link "$ENV:DOTFILES\xonsh" "$env:WINDOTCONF\xonsh" -v:$v -i:$i
Set-Link "$ENV:DOTFILES\yasb" "$ENV:WINDOTCONF\yasb" -v:$v -i:$i
Set-Link "$ENV:DOTFILES\komorebi\whkdrc" "$ENV:WINDOTCONF\whkdrc" -v:$v -i:$i

# $ENV:USERPROFILE FILES
Set-Link "$ENV:DOTFILES\git\gitconfig" "$ENV:USERPROFILE\.gitconfig" -v:$v -i:$i
Set-Link "$ENV:DOTFILES\wsl\wslconfig" "$ENV:USERPROFILE\.wslconfig" -v:$v -i:$i
Set-Link "$ENV:DOTFILES\glaze-wm" "$ENV:USERPROFILE\.glaze-wm" -v:$v -i:$i
Set-Link "$ENV:DOTFILES\komorebi\komorebi.json" "$ENV:USERPROFILE\komorebi.json" -v:$v -i:$i

# $HOME\appData\Roaming FILES
Set-Link "$ENV:DOTFILES\alacritty" "$ENV:APPDATA\alacritty" -v:$v -i:$i
Set-Link "$ENV:DOTFILES\yazi" "$ENV:APPDATA\yazi\config" -v:$v -i:$i
Set-Link "$ENV:DOTFILES\lsd" "$ENV:APPDATA\lsd" -v:$v -i:$i
Set-Link "$ENV:DOTFILES\vifm" "$ENV:APPDATA\vifm" -v:$v -i:$i
Set-Link "$ENV:DOTFILES\bat" "$ENV:APPDATA\bat" -v:$v -i:$i

# $HOME\appData\Local FILES
Set-Link "$ENV:DEV\nvim" "$ENV:LOCALAPPDATA\nvim" -v:$v -i:$i
Set-Link "$ENV:DOTFILES\clink" "$ENV:LOCALAPPDATA\clink" -v:$v -i:$i
Set-Link "$ENV:DOTFILES\alacritty" "$ENV:LOCALAPPDATA\alacritty" -v:$v -i:$i

# $HOME\Docusments FILES
Set-Link "$ENV:DEV\5ui7e" "$ENV:DOCUMENTS\Rainmeter\Skins\5ui7e" -v:$v -i:$i

Write-Host ''
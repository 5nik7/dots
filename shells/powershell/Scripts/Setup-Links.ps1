param(
    [switch] $v,
    [switch] $i
)

Write-Host ''
Write-Host ' Setting up links...' -ForegroundColor Cyan



# Set-link "$Env:DRIP_COLS" "$Env:WINDOTCONF\wal\colorschemes" 
# Set-link "$Env:DRIP_TEMPS" "$Env:WINDOTCONF\wal\templates"

Set-Link "$Env:DOTFILES\komorebi" "$Env:WINDOTCONF\komorebi" -v:$v -i:$i
Set-Link "$Env:DOTFILES\whkdrc" "$Env:WINDOTCONF\whkdrc" -v:$v -i:$i

# Set-Link "$Env:DOTFILES\xonsh" "$Env:WINDOTCONF\xonsh" -v:$v -i:$i
# Set-Link "$Env:DOTFILES\yasb" "$Env:WINDOTCONF\yasb" -v:$v -i:$i
# Set-Link "$Env:DOTFILES\komorebi\whkdrc" "$Env:WINDOTCONF\whkdrc" -v:$v -i:$i

# # $Env:USERPROFILE FILES
# Set-Link "$Env:DOTFILES\git\gitconfig" "$Env:USERPROFILE\.gitconfig" -v:$v -i:$i
# Set-Link "$Env:DOTFILES\wsl\wslconfig" "$Env:USERPROFILE\.wslconfig" -v:$v -i:$i
# Set-Link "$Env:DOTFILES\glaze-wm" "$Env:USERPROFILE\.glaze-wm" -v:$v -i:$i
# Set-Link "$Env:DOTFILES\komorebi\komorebi.json" "$Env:USERPROFILE\komorebi.json" -v:$v -i:$i

# # $HOME\appData\Roaming FILES
# Set-Link "$Env:DOTFILES\alacritty" "$Env:APPDATA\alacritty" -v:$v -i:$i
# Set-Link "$Env:DOTFILES\yazi" "$Env:APPDATA\yazi\config" -v:$v -i:$i
# Set-Link "$Env:DOTFILES\lsd" "$Env:APPDATA\lsd" -v:$v -i:$i
# Set-Link "$Env:DOTFILES\vifm" "$Env:APPDATA\vifm" -v:$v -i:$i
# Set-Link "$Env:DOTFILES\bat" "$Env:APPDATA\bat" -v:$v -i:$i

# # $HOME\appData\Local FILES
# Set-Link "$Env:DEV\nvim" "$Env:LOCALAPPDATA\nvim" -v:$v -i:$i
# Set-Link "$Env:DOTFILES\clink" "$Env:LOCALAPPDATA\clink" -v:$v -i:$i
# Set-Link "$Env:DOTFILES\alacritty" "$Env:LOCALAPPDATA\alacritty" -v:$v -i:$i

# # $HOME\Docusments FILES
# Set-Link "$Env:DEV\5ui7e" "$Env:DOCUMENTS\Rainmeter\Skins\5ui7e" -v:$v -i:$i

Write-Host ''
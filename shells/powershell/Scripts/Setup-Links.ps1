param(
    [switch] $v,
    [switch] $i
)
linebreak
Write-Info ' Setting up links...'

Set-Link "$env:DOTFILES\bat" "$env:SCOOPDATA\bat" -v:$v -i:$i
# Set-Link "$DOTFILES\komorebi" "$CONF\komorebi" -v:$v -i:$i
# Set-Link "$DOTFILES\whkdrc" "$CONF\whkdrc" -v:$v -i:$i

# Set-Link "$DOTFILES\xonsh" "$CONF\xonsh" -v:$v -i:$i
# Set-Link "$DOTFILES\yasb" "$CONF\yasb" -v:$v -i:$i
# Set-Link "$DOTFILES\komorebi\whkdrc" "$CONF\whkdrc" -v:$v -i:$i

# # $USERPROFILE FILES
# Set-Link "$DOTFILES\git\gitconfig" "$USERPROFILE\.gitconfig" -v:$v -i:$i
# Set-Link "$DOTFILES\wsl\wslconfig" "$USERPROFILE\.wslconfig" -v:$v -i:$i
# Set-Link "$DOTFILES\glaze-wm" "$USERPROFILE\.glaze-wm" -v:$v -i:$i
# Set-Link "$DOTFILES\komorebi\komorebi.json" "$USERPROFILE\komorebi.json" -v:$v -i:$i

# # $HOME\appData\Roaming FILES
# Set-Link "$DOTFILES\alacritty" "$APPDATA\alacritty" -v:$v -i:$i
# Set-Link "$DOTFILES\yazi" "$APPDATA\yazi\config" -v:$v -i:$i
# Set-Link "$DOTFILES\lsd" "$APPDATA\lsd" -v:$v -i:$i
# Set-Link "$DOTFILES\vifm" "$APPDATA\vifm" -v:$v -i:$i
# Set-Link "$DOTFILES\bat" "$APPDATA\bat" -v:$v -i:$i

# # $HOME\appData\Local FILES
# Set-Link "$DEV\nvim" "$LOCALAPPDATA\nvim" -v:$v -i:$i
# Set-Link "$DOTFILES\clink" "$LOCALAPPDATA\clink" -v:$v -i:$i
# Set-Link "$DOTFILES\alacritty" "$LOCALAPPDATA\alacritty" -v:$v -i:$i

# # $HOME\Docusments FILES
# Set-Link "$DEV\5ui7e" "$DOCS\Rainmeter\Skins\5ui7e" -v:$v -i:$i

linebreak

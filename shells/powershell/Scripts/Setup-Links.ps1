param(
    [switch] $i
)
linebreak
Write-Info ' Setting up links...'

Set-Link "$env:DOTFILES\bat" "$env:SCOOPDATA\bat" -i:$i
# Set-Link "$DOTFILES\komorebi" "$CONF\komorebi" -i:$i
# Set-Link "$DOTFILES\whkdrc" "$CONF\whkdrc" -i:$i

# Set-Link "$DOTFILES\xonsh" "$CONF\xonsh" -i:$i
# Set-Link "$DOTFILES\yasb" "$CONF\yasb" -i:$i
# Set-Link "$DOTFILES\komorebi\whkdrc" "$CONF\whkdrc" -i:$i

# # $USERPROFILE FILES
# Set-Link "$DOTFILES\git\gitconfig" "$USERPROFILE\.gitconfig" -i:$i
# Set-Link "$DOTFILES\wsl\wslconfig" "$USERPROFILE\.wslconfig" -i:$i
# Set-Link "$DOTFILES\glaze-wm" "$USERPROFILE\.glaze-wm" -i:$i
# Set-Link "$DOTFILES\komorebi\komorebi.json" "$USERPROFILE\komorebi.json" -i:$i

# # $HOME\appData\Roaming FILES
# Set-Link "$DOTFILES\alacritty" "$APPDATA\alacritty" -i:$i
# Set-Link "$DOTFILES\yazi" "$APPDATA\yazi\config" -i:$i
# Set-Link "$DOTFILES\lsd" "$APPDATA\lsd" -i:$i
# Set-Link "$DOTFILES\vifm" "$APPDATA\vifm" -i:$i
# Set-Link "$DOTFILES\bat" "$APPDATA\bat" -i:$i

# # $HOME\appData\Local FILES
# Set-Link "$DEV\nvim" "$LOCALAPPDATA\nvim" -i:$i
# Set-Link "$DOTFILES\clink" "$LOCALAPPDATA\clink" -i:$i
# Set-Link "$DOTFILES\alacritty" "$LOCALAPPDATA\alacritty" -i:$i

# # $HOME\Docusments FILES
# Set-Link "$DEV\5ui7e" "$DOCS\Rainmeter\Skins\5ui7e" -i:$i

linebreak

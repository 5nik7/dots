$ENV:PROJECTS = "$ENV:HOMEDRIVE\projects"

$ENV:DOTS = "$ENV:PROJECTS\dots"
$ENV:DOTFILES = "$ENV:DOTS\configs"
$ENV:DRIP = "$ENV:DOTS\drip"
$ENV:WALLS = "$ENV:DOTS\walls"

$ENV:NVM_HOME = "$ENV:APPDATA\nvm"
$ENV:NVM_SYMLINK = "$ENV:HOMEDRIVE\node"
$ENV:GOPATH = "$ENV:USERPROFILE\go"
$ENV:GOBIN = "$ENV:USERPROFILE\go\bin"

$ENV:DOCUMENTS = [Environment]::GetFolderPath("mydocuments")
$ENV:DOWNLOADS = "$ENV:USERPROFILE\Downloads"

$ENV:STARSHIP_CONFIG = "$ENV:DOTFILES\starship\starship.toml"
$ENV:STARSHIP_CACHE = "$ENV:LOCALAPPDATA\Temp"
$ENV:BAT_CONFIG_PATH = "$ENV:DOTFILES\bat\bat.conf"
$ENV:YAZI_CONFIG_HOME = "$ENV:DOTFILES\yazi"
$GITBIN = "C:\Git\usr\bin"
$ENV:YAZI_FILE_ONE = "$GITBIN\file.exe"
$BAT_THEME = if ($ENV:THEME) { $ENV:THEME }
else { 'base16' }
$ENV:BAT_THEME = $BAT_THEME

$TIC = (Get-ItemProperty 'HKCU:\Control Panel\Desktop' TranscodedImageCache -ErrorAction Stop).TranscodedImageCache
$wallout = [System.Text.Encoding]::Unicode.GetString($TIC) -replace '(.+)([A-Z]:[0-9a-zA-Z\\])+', '$2'
$ENV:WALLPAPER = $wallout
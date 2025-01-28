$Env:DOTFILES = "$Env:DOTS\configs"
$Env:DOTCACHE = "$Env:DOTS\cache"

$Env:PSCOMPS = "$Env:PSDOT\completions"
$Env:PSMODS = "$Env:PSDOT\Modules"

$Env:BASHDOT = "$Env:DOTS\shells\bash"
$Env:ZSHDOT = "$Env:DOTS\shells\zsh"
$Env:PROJECTS = "$Env:USERPROFILE\dev"
$Env:DEV = "$Env:USERPROFILE\dev"
$Env:WINDOTCONF = "$Env:USERPROFILE\.config"

$Env:DRIP = "$Env:DOTS\drip"
$Env:DRIP_COLS = "$Env:DRIP\colorschemes"
$Env:DRIP_TEMPS = "$Env:DRIP\tenplates"
$Env:WALLS = "$Env:DOTS\walls"

$Env:NVM_HOME = "$Env:APPDATA\nvm"
$Env:NVM_SYMLINK = "$Env:HOMEDRIVE\node"
$Env:GOPATH = "$Env:USERPROFILE\go"
$Env:GOBIN = "$Env:USERPROFILE\go\bin"

$Env:DOCUMENTS = [Environment]::GetFolderPath("mydocuments")
$Env:DOWNLOADS = "$Env:USERPROFILE\Downloads"

$Env:STARSHIP_CACHE = "$Env:LOCALAPPDATA\Temp"
$Env:STARSHIP_CONFIG = "$Env:DOTFILES\starship\starship.toml"
$Env:BAT_CONFIG_PATH = "$Env:DOTFILES\bat\config"
$Env:YAZI_CONFIG_HOME = "$Env:DOTFILES\yazi"

$GITBIN = "C:\Git\usr\bin"
$Env:YAZI_FILE_ONE = "$GITBIN\file.exe"
$BAT_THEME = 'wal'
$Env:BAT_THEME = $BAT_THEME
$Env:KOMOREBI_CONFIG_HOME = "$Env:WINDOTCONF\komorebi"

$TIC = (Get-ItemProperty 'HKCU:\Control Panel\Desktop' TranscodedImageCache -ErrorAction Stop).TranscodedImageCache
$wallout = [System.Text.Encoding]::Unicode.GetString($TIC) -replace '(.+)([A-Z]:[0-9a-zA-Z\\])+', '$2'
$Env:WALLPAPER = $wallout
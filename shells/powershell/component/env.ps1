$Global:USERPROFILE = $env:USERPROFILE

$env:DOTFILES = "$DOTS\configs"
$Global:DOTFILES = $env:DOTFILES

$env:DOTCACHE = "$DOTS\cache"
$Global:DOTCACHE = $env:DOTCACHE

$env:PSCOMPS = "$env:PSDOT\completions"
$Global:PSCOMPS = $env:PSCOMPS

$env:PSMODS = "$env:PSDOT\Modules"
$Global:PSMODS = $env:PSMODS

$env:BASHDOT = "$SHELLS\bash"
$Global:BASHDOT = $env:BASHDOT

$env:ZSHDOT = "$SHELLS\zsh"
$Global:ZSHDOT = $env:ZSHDOT

$env:PROJECTS = "$USERPROFILE\dev"
$env:DEV = "$USERPROFILE\dev"
$Global:DEV = $env:DEV

$env:CONF = "$USERPROFILE\.config"
$Global:CONF = $env:CONF

$env:DRIP = "$DOTS\drip"
$env:DRIP_COLS = "$env:DRIP\colorschemes"
$env:DRIP_TEMPS = "$env:DRIP\tenplates"

$env:WALLS = "$DOTS\walls"

$env:NVM_HOME = "$env:APPDATA\nvm"
$env:NVM_SYMLINK = "$env:HOMEDRIVE\node"
$env:GOPATH = "$USERPROFILE\go"
$env:GOBIN = "$USERPROFILE\go\bin"

$env:DOCUMENTS = [environment]::GetFolderPath("MyDocuments")
$Global:DOCS = $env:DOCUMENTS

$env:DOWNLOADS = "$USERPROFILE\Downloads"
$Global:DOWNLOADS = $env:DOWNLOADS

$Global:APPDATA = [environment]::GetFolderPath("ApplicationData")
$Global:LOCALAPPDATA = [environment]::GetFolderPath("LocalApplicationData")

$env:STARSHIP_CACHE = "$LOCALAPPDATA\Temp"
$env:STARSHIP_CONFIG = "$DOTFILES\starship\starship.toml"
$env:BAT_CONFIG_PATH = "$DOTFILES\bat\config"
$env:YAZI_CONFIG_HOME = "$DOTFILES\yazi"

$GITBIN = "C:\Git\usr\bin"
$env:YAZI_FILE_ONE = "$GITBIN\file.exe"
$BAT_THEME = 'wal'
$env:BAT_THEME = $BAT_THEME
$env:KOMOREBI_CONFIG_HOME = "$CONF\komorebi"

$TIC = (Get-ItemProperty 'HKCU:\Control Panel\Desktop' TranscodedImageCache -ErrorAction Stop).TranscodedImageCache
$wallout = [System.Text.Encoding]::Unicode.GetString($TIC) -replace '(.+)([A-Z]:[0-9a-zA-Z\\])+', '$2'
$env:WALLPAPER = $wallout

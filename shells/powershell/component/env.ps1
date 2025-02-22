$Global:USERPROFILE = $env:USERPROFILE

$env:BACKUPS = "$env:USERPROFILE\backups"
$Global:BACKUPS = $env:BACKUPS

$env:DOTFILES = "$env:DOTS\configs"
$Global:DOTFILES = $env:DOTFILES

$env:DOTCACHE = "$env:DOTS\cache"
$Global:DOTCACHE = $env:DOTCACHE

$env:PSCOMPS = "$env:PSDOT\completions"
$Global:PSCOMPS = $env:PSCOMPS

$env:PSMODS = "$env:PSDOT\Modules"
$Global:PSMODS = $env:PSMODS

$env:BASHDOT = "$env:SHELLS\bash"
$Global:BASHDOT = $env:BASHDOT

$env:ZSHDOT = "$env:SHELLS\zsh"
$Global:ZSHDOT = $env:ZSHDOT

$env:PROJECTS = "$env:USERPROFILE\dev"
$env:DEV = "$env:USERPROFILE\dev"
$Global:DEV = $env:DEV

$env:CONF = "$env:USERPROFILE\.config"
$Global:CONF = $env:CONF

$env:WALLS = "$env:DOTS\walls"
$Global:WALLS = $env:WALLS

$env:NVM_HOME = "$env:APPDATA\nvm"
$env:NVM_SYMLINK = "$env:HOMEDRIVE\nodejs"
$env:GOPATH = "$env:USERPROFILE\go"
$env:GOBIN = "$env:USERPROFILE\go\bin"

$env:DOCUMENTS = [environment]::GetFolderPath("MyDocuments")
$Global:DOCS = $env:DOCUMENTS

$env:DOWNLOADS = "$env:USERPROFILE\Downloads"
$Global:DOWNLOADS = $env:DOWNLOADS

$Global:APPDATA = [environment]::GetFolderPath("ApplicationData")
$Global:LOCALAPPDATA = [environment]::GetFolderPath("LocalApplicationData")

$env:SCOOPDATA = "$env:USERPROFILE\scoop\persist"
$Global:SCOOPDATA = $env:SCOOPDATA

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
$env:wallout = [System.Text.Encoding]::Unicode.GetString($TIC) -replace '(.+)([A-Z]:[0-9a-zA-Z\\])+', '$2'
$env:WALLPAPER = (Get-ItemProperty 'HKCU:\Control Panel\Desktop').WallPaper

Invoke-Expression (& { (zoxide init powershell | Out-String) })

# $env:BACKUPS = "$env:USERPROFILE\backups"

# $env:DOTFILES = "$env:DOTS\configs"

# $env:DOTCACHE = "$env:DOTS\cache"

# $env:PSCOMPS = "$env:PSDOTS\completions"

# $env:PSMODS = "$env:PSDOTS\Modules"

# $env:BASHDOT = "$env:SHELLS\bash"

# $env:ZSHDOT = "$env:SHELLS\zsh"

# $env:PROJECTS = "$env:USERPROFILE\dev"
# $env:DEV = "$env:USERPROFILE\dev"

# $env:WALLS = "$env:DOTS\walls"

# $env:NVM_HOME = "$env:APPDATA\nvm"
# $env:NVM_SYMLINK = "$env:HOMEDRIVE\nodejs"
# $env:GOPATH = "$env:USERPROFILE\go"
# $env:GOBIN = "$env:USERPROFILE\go\bin"

$env:DOCUMENTS = [environment]::GetFolderPath("MyDocuments")
$Global:DOCS = $env:DOCUMENTS

$env:DOWNLOADS = "$env:USERPROFILE\Downloads"

$Global:APPDATA = [environment]::GetFolderPath("ApplicationData")
$Global:LOCALAPPDATA = [environment]::GetFolderPath("LocalApplicationData")

# $env:SCOOPDATA = "$env:USERPROFILE\scoop\persist"

# $env:STARSHIP_CACHE = "$LOCALAPPDATA\Temp"
# $env:STARSHIP_CONFIG = "$DOTFILES\starship\starship.toml"
# $env:BAT_CONFIG_PATH = "$DOTFILES\bat\config"
# $env:YAZI_CONFIG_HOME = "$DOTFILES\yazi"

# $GITBIN = "C:\Git\usr\bin"
# $env:YAZI_FILE_ONE = "$GITBIN\file.exe"
# $BAT_THEME = 'wal'
# $env:BAT_THEME = $BAT_THEME
# $env:KOMOREBI_CONFIG_HOME = "$CONF\komorebi"

# $TIC = (Get-ItemProperty 'HKCU:\Control Panel\Desktop' TranscodedImageCache -ErrorAction Stop).TranscodedImageCache
# $env:wallout = [System.Text.Encoding]::Unicode.GetString($TIC) -replace '(.+)([A-Z]:[0-9a-zA-Z\\])+', '$2'
# $env:WALLPAPER = (Get-ItemProperty 'HKCU:\Control Panel\Desktop').WallPaper

$TIC = (Get-ItemProperty 'HKCU:\Control Panel\Desktop' TranscodedImageCache -ErrorAction Stop).TranscodedImageCache
$wallout = [System.Text.Encoding]::Unicode.GetString($TIC) -replace '(.+)([A-Z]:[0-9a-zA-Z\\])+', '$2'

$env:WALLPAPER = $wallout

$env:DOCS = "$env:USERPROFILE\Documents"
$env:DOWNLOADS = "$env:USERPROFILE\Downloads"
$env:RMSKINS = "$env:DOCS\Rainmeter\Skins"
$env:WINCONFIG = "$env:USERPROFILE\.config"

$env:PROJECTS = "$env:USERPROFILE\projects"
$env:REPOS = "$env:PROJECTS"
$env:DOTS = "$env:USERPROFILE\.dots"
$env:DRIP = "$env:DOTS\drip"
$env:WALLS = "$env:DOTS\walls"
$env:DOTSHELL = "$env:DOTS\shells"
$env:PSHELL = "$env:DOTSHELL\powershell"
$env:ZSHELL = "$env:DOTSHELL\zsh"
$env:BASHELL = "$env:DOTSHELL\bash"
$env:DOTFILES = "$env:DOTS\configs"

$env:NVM_HOME = "$env:USERPROFILE\.nvm"
$env:NVM_SYMLINK = "$env:HOMEDRIVE\nodejs"
$env:GOPATH = "$env:USERPROFILE\go"
$env:GOBIN = "$env:USERPROFILE\go\bin"

$env:STARSHIP_CONFIG = "$env:DOTFILES\starship\starship.toml"
$env:STARSHIP_CACHE = "$env:USERPROFILE\AppData\Local\Temp"
$env:BAT_CONFIG_PATH = "$env:DOTFILES\bat\bat.conf"
$env:YAZI_CONFIG_HOME = "$env:DOTFILES\yazi"
$env:YAZI_CONFIG_HOME = "$env:DOTFILES\yazi"
$env:YAZI_FILE_ONE = 'C:\Users\nickf\scoop\apps\git\current\usr\bin\file.exe'
$env:BOXES = "$env:DOTFILES\boxes\boxes-config"
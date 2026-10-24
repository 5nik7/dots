# WINDOT NOTES

```powershell
# VSCode Settings Path:
$configpath = "$env:APPDATA\Code\User\settings.json"
Set-Link -force -base "$env:WINDOTS\configs\vscode\settings.json"  -target "$configpath"

# WinGet Settings Path:
"$env:LOCALAPPDATA\Packages\Microsoft.DesktopAppInstaller_8wekyb3d8bbwe\LocalState\settings.json"
Set-Link -force -base "$env:WINDOTS\configs\winget\settings.json"  -target "$env:LOCALAPPDATA\Packages\Microsoft.DesktopAppInstaller_8wekyb3d8bbwe\LocalState\settings.json"
```

```powershell
$env:DIRENV_CONFIG = $env:LOCALAPPDATA\direnv
$env:GITBIN = $env:HOMEDRIVE\Git\usr\bin
$env:YAZI_FILE_ONE = $env:GITBIN\file.exe
$env:KOMOREBI_CONFIG_HOME = path\komorebi
```

## Starship and Clink

Clink uses Starship's default `%USERPROFILE%/.config/starship.toml` without setting
`STARSHIP_CONFIG`. It clears recognized inherited Dots paths, including the former
hardcoded checkout path, while retaining deliberate custom overrides. The parent
Dots catalog owns the default config link. Lua fixtures verify cleanup on Termux;
native Windows Clink startup remains a separate acceptance check.

# Powershell Notes

Set WSLENV from pwsh
```powershell
[Environment]::SetEnvironmentVariable("WSLENV", $env:WSLENV + "USERPROFILE/p:", [System.EnvironmentVariableTarget]::User)
```

﻿SymLink bat
```powershell
New-Item -ItemType SymbolicLink -Path "$(bat --config-dir)" -Target "C:\projects\dots\configs\bat" -ErrorAction Stop
```

Set pyenv environment variable

```powershell
[System.Environment]::SetEnvironmentVariable('PYENV',$env:USERPROFILE + "\.pyenv\pyenv-win\","User")

[System.Environment]::SetEnvironmentVariable('PYENV_ROOT',$env:USERPROFILE + "\.pyenv\pyenv-win\","User")

[System.Environment]::SetEnvironmentVariable('PYENV_HOME',$env:USERPROFILE + "\.pyenv\pyenv-win\","User")

[System.Environment]::SetEnvironmentVariable('path', $env:USERPROFILE + "\.pyenv\pyenv-win\bin;" + $env:USERPROFILE + "\.pyenv\pyenv-win\shims;" + [System.Environment]::GetEnvironmentVariable('path', "User"),"User")

[System.Environment]::SetEnvironmentVariable('path', $env:DOCUMENTS + "\PowerShell\Scripts;" + [System.Environment]::GetEnvironmentVariable('path', "User"),"User")

```

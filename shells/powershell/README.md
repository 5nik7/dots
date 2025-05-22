# Set WSLENV from pwsh

```powershell
[Environment]::SetEnvironmentVariable("WSLENV", $env:WSLENV + "USERPROFILE/p:", [System.EnvironmentVariableTarget]::User)
```

﻿# SymLink

```powershell
New-Item -ItemType SymbolicLink -Path "$(bat --config-dir)" -Target "C:\projects\dots\configs\bat" -ErrorAction Stop
```

# Set $env:

```powershell 
[System.Environment]::SetEnvironmentVariable('PYENV',$env:USERPROFILE + "\.pyenv\pyenv-win\","User")

[System.Environment]::SetEnvironmentVariable('PYENV_ROOT',$env:USERPROFILE + "\.pyenv\pyenv-win\","User")

[System.Environment]::SetEnvironmentVariable('PYENV_HOME',$env:USERPROFILE + "\.pyenv\pyenv-win\","User")

[System.Environment]::SetEnvironmentVariable('path', $env:USERPROFILE + "\.pyenv\pyenv-win\bin;" + $env:USERPROFILE + "\.pyenv\pyenv-win\shims;" + [System.Environment]::GetEnvironmentVariable('path', "User"),"User")
```

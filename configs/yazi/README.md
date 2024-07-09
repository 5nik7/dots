# Yazi config location

```
C:\Users\USERNAME\AppData\Roaming\yazi\config\yazi.toml
$ENV:APPDATA\yazi\config\yazi.toml
```

```powershell
New-Item -ItemType SymbolicLink -Path "$ENV:APPDATA\yazi\config" -Target "$ENV:DOTS\configs\yazi" -ErrorAction Stop
```

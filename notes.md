# 6/11/24

Utilize Where-Object to search for the ReparsePoint file attribute.

```powershell
Get-ChildItem | Where-Object { $_.Attributes -match "ReparsePoint" }
```



For those that want to check if a resource is a hardlink or symlink:


```powershell
(Get-Item ".\some_resource").LinkType -eq "HardLink"

(Get-Item ".\some_resource").LinkType -eq "SymbolicLink"

```

```powershell
Function Test-Symlink($Path){
    ((Get-Item $Path).Attributes.ToString() -match "ReparsePoint")
}
```

```powershell
Get-ChildItem -path C:\Windows\system -file -recurse -force | 
    foreach-object {
        if ((fsutil hardlink list $_.fullname).count -ge 2) {
            $_.PSChildname + ":Hardlinked:" + $_.Length
        } else {
            $_.PSChildname + ":RegularFile:" + $_.Length
        }
    } > c:\hardlinks.txt
```


```powershell
Get-ChildItem -Path "C:\Windows\","c:\","$env:USERPROFILE" -Force |
    Where-Object { $_.LinkType -ne $null -or $_.Attributes -match "ReparsePoint" } |
    ft FullName,Length,Attributes,Linktype,Target
```


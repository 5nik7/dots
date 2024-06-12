Get-ChildItem -Path "C:\Windows\","c:\","$env:USERPROFILE" -Force |
    Where-Object { $_.LinkType -ne $null -or $_.Attributes -match "ReparsePoint" } |
    ft FullName,Length,Attributes,Linktype,Target
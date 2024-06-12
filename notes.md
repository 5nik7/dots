# 6/11/24

Utilize Where-Object to search for the ReparsePoint file attribute.

```
Get-ChildItem | Where-Object { $_.Attributes -match "ReparsePoint" }
```



For those that want to check if a resource is a hardlink or symlink:

(Get-Item ".\some_resource").LinkType -eq "HardLink"

(Get-Item ".\some_resource").LinkType -eq "SymbolicLink"


Function Test-Symlink($Path){
    ((Get-Item $Path).Attributes.ToString() -match "ReparsePoint")
}

Get-ChildItem -path C:\Windows\system -file -recurse -force | 
    foreach-object {
        if ((fsutil hardlink list $_.fullname).count -ge 2) {
            $_.PSChildname + ":Hardlinked:" + $_.Length
        } else {
            $_.PSChildname + ":RegularFile:" + $_.Length
        }
    } > c:\hardlinks.txt


### ReparsePoint + Directory + Junction = mklink /j 
### ReparsePoint + Directory + SymbolicLink = mklink /d 
### ReparsePoint + SymbolicLink = mklink 

"cd $( $pwd.Path )"; Get-ChildItem | ? { $_.Attributes -match 'ReparsePoint' -and $_.Target -ne $null } | % {
    $linktype = $_.LinkType
    $target = Resolve-Path -Path $_.Target
    if ($_.Attributes -match 'Directory') {
        if ($linktype -eq "Junction") {
            "mklink /j `"$($_.Name)`" `"$target`""
        } else {
            "mklink /d `"$($_.Name)`" `"$target`""
        }
    } else {
        "mklink `"$($_.Name)`" `"$target`""
    }
}


Get-ChildItem -Path "C:\Windows\","c:\","$env:USERPROFILE" -Force |
    Where-Object { $_.LinkType -ne $null -or $_.Attributes -match "ReparsePoint" } |
    ft FullName,Length,Attributes,Linktype,Target


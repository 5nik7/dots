$dir1 = "C:\Users\njen\Documents\PowerShell\Scripts"
$dir2 = "C:\Users\njen\Documents\WindowsPowerShell\Scripts"

$files1 = Get-ChildItem $dir1 -File -Recurse | ForEach-Object {
    $_.FullName.Substring($dir1.Length).TrimStart('\')
}

$files2 = Get-ChildItem $dir2 -File -Recurse | ForEach-Object {
    $_.FullName.Substring($dir2.Length).TrimStart('\')
}

Compare-Object $files1 $files2

. 'C:\Users\njen\dots\shells\powershell\Microsoft.PowerShell_profile.ps1'
Write-Host "Profile sourced"
$res = Get-ArgumentCompleter -CommandName gh
if ($res) { $res | Format-List -Force } else { Write-Host 'No completer objects found' }

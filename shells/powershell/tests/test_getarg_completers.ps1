# Test: ensure Get-ArgumentCompleter returns a completer for gh after sourcing gh.ps1
. 'C:\Users\njen\dots\shells\powershell\Microsoft.PowerShell_profile.ps1'
$p = Join-Path $env:LOCALAPPDATA 'dots\ps-completions\gh.ps1'
if (-not (Test-Path $p)) { Write-Error "Missing cached gh.ps1 at $p"; exit 2 }
. $p
Write-Host "Sourced $p"
$res = Get-ArgumentCompleter -CommandName gh -IncludeLazy
if ($res -and $res.Count -gt 0) {
    Write-Host "PASS: Get-ArgumentCompleter returned $($res.Count) entries for 'gh'"
    $res | Format-Table -AutoSize
    exit 0
} else {
    Write-Host "FAIL: no completers returned for 'gh'"
    exit 3
}

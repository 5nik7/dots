# Force no early load, source profile, and invoke the lazy wrapper so it must dot-source the cached gh.ps1
$env:DOTS_LOAD_CACHED_COMPLETIONS = '0'
Remove-Variable -Name '__ghCompleterBlock' -Scope Global -ErrorAction SilentlyContinue
. 'C:\Users\njen\dots\shells\powershell\Microsoft.PowerShell_profile.ps1'
if (Get-Variable -Name '__lazy_gh' -Scope Global -ErrorAction SilentlyContinue) {
	Write-Host 'Invoking lazy wrapper' ; & (Get-Variable -Name '__lazy_gh' -Scope Global).Value -WordToComplete '' -CommandAst $null -CursorPosition 0
} else { Write-Host 'Lazy wrapper not found' }
# Show recent lines from lazy-load.log and regen.log
Write-Host '--- lazy-load.log tail ---'
if (Test-Path "$env:LOCALAPPDATA\dots\logs\lazy-load.log") { Get-Content "$env:LOCALAPPDATA\dots\logs\lazy-load.log" -Tail 40 } else { Write-Host '(no lazy-load.log)' }
Write-Host '--- regen.log tail ---'
Get-Content "$env:LOCALAPPDATA\dots\logs\regen.log" -Tail 40

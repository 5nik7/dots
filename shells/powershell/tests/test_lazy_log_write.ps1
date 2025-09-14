# Source profile and call Dots-LogLazyLoad directly to test log writing
. 'C:\Users\njen\dots\shells\powershell\Microsoft.PowerShell_profile.ps1'
Write-Host "Invoking Dots-LogLazyLoad test entry..."
try {
	Dots-LogLazyLoad -Name 'TEST' -File 'C:\temp\fake.ps1' -ElapsedMs 123
	Write-Host 'Called Dots-LogLazyLoad'
} catch {
	Write-Host "Error calling Dots-LogLazyLoad: $($_.Exception.Message)"
}

Write-Host '--- lazy-load.log tail ---'
if (Test-Path "$env:LOCALAPPDATA\dots\logs\lazy-load.log") { Get-Content "$env:LOCALAPPDATA\dots\logs\lazy-load.log" -Tail 40 } else { Write-Host '(no lazy-load.log)' }

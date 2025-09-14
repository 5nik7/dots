<#
Unregister the scheduled task created by register_regen_task.ps1
#>
$taskName = 'DotsRegenAtLogon'
try {
	Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
	Write-Host "Unregistered $taskName"
} catch {
	Write-Warning "Failed to unregister $taskName: $_"
}
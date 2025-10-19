<#
Create a Scheduled Task that runs the regenerate_completions.ps1 at logon when idle.
Usage: run in an elevated prompt or a user prompt (will register to current user).
#>
$taskName = 'DotsRegenAtLogon'
$script = Join-Path $PSScriptRoot 'regenerate_completions.ps1'
if (-not (Test-Path $script)) { Write-Error "regenerate_completions.ps1 not found in $PSScriptRoot"; exit 1 }
$action = New-ScheduledTaskAction -Execute 'pwsh.exe' -Argument "-NoProfile -WindowStyle Hidden -File '$script' -Force"
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew
# Idle settings: start the task only if computer has been idle for 60 seconds
$settings.IdleSettings = New-ScheduledTaskIdleSettings -StartWhenIdle -IdleDuration 00:01:00
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Force
Write-Host "Registered scheduled task $taskName (runs regenerate_completions.ps1 at logon when idle)"
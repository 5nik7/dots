if ($env:DOTS_DEBUG_EVENTS -and -not (Get-Variable _DotsDebugCount -Scope Global -ErrorAction Ignore)) { $global:_DotsDebugCount = 0 }
# Opt-in source/timing metadata. Never write invocation arguments or values.
function global:Write-DotsDebugEvent {
    param([string]$Event, [string]$Name, [string]$Kind = 'module', [int]$Status = 0)
    if (-not $env:DOTS_DEBUG_EVENTS) { return }
    if ($global:_DotsDebugCount -ge 10000) { return }
    $global:_DotsDebugCount++
    if ($Kind -eq 'module' -and -not [IO.Path]::IsPathRooted($Name)) { $Name = Join-Path $env:DOTS $Name }
    $now = ([DateTime]::UtcNow.Ticks - 621355968000000000) / 10000000.0
    $row = @{event=$Event; time=$now; name=$Name; kind=$Kind; status=$Status; pid=$PID}
    try { [IO.File]::AppendAllText($env:DOTS_DEBUG_EVENTS, (($row | ConvertTo-Json -Compress) + "`n"), [Text.UTF8Encoding]::new($false)) }
    catch { } # Diagnostic output must not change startup behavior.
}

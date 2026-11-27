param([Parameter(Mandatory = $true)][int]$TimeoutMilliseconds)

$ErrorActionPreference = 'Stop'
$timer = [Diagnostics.Stopwatch]::StartNew()
$watcher = $null
try {
    Add-Type -AssemblyName System.Device
    $watcher = New-Object System.Device.Location.GeoCoordinateWatcher
    $remaining = [Math]::Max(1, $TimeoutMilliseconds - $timer.ElapsedMilliseconds)
    [void]$watcher.TryStart($true, [TimeSpan]::FromMilliseconds($remaining))
    do {
        if ($watcher.Permission -eq 'Denied' -or $watcher.Status -eq 'Disabled') { exit 3 }
        $fix = $watcher.Position
        if (-not $fix.Location.IsUnknown -and
            $fix.Timestamp -ge [DateTimeOffset]::UtcNow.AddSeconds(-60)) {
            [Console]::WriteLine((@{
                latitude = $fix.Location.Latitude
                longitude = $fix.Location.Longitude
                timestamp = $fix.Timestamp.ToUnixTimeSeconds()
            } | ConvertTo-Json -Compress))
            exit 0
        }
        Start-Sleep -Milliseconds 100
    } while ($timer.ElapsedMilliseconds -lt $TimeoutMilliseconds)
    exit 4
} catch {
    exit 5
} finally {
    if ($null -ne $watcher) { $watcher.Dispose() }
}

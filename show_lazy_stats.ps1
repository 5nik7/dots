$statsPath = Join-Path $env:LOCALAPPDATA 'dots\logs\lazy-load-stats.json'
if (Test-Path $statsPath) {
    try {
        $text = Get-Content -Path $statsPath -Raw -ErrorAction Stop
        Write-Output $text
    } catch {
        Write-Output "ERROR: $($_.Exception.Message)"
    }
} else {
    Write-Output 'MISSING'
}

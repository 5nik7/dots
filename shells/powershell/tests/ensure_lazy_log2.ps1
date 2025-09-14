$logdir = Join-Path $env:LOCALAPPDATA 'dots\logs'
if (-not (Test-Path $logdir)) { New-Item -ItemType Directory -Path $logdir -Force | Out-Null }
$f = Join-Path $logdir 'lazy-load.log'
if (-not (Test-Path $f)) { Set-Content -Path $f -Value '' }
Write-Output "Created or ensured: $f"

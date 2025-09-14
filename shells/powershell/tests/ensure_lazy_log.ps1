$logdir = Join-Path $env:LOCALAPPDATA 'dots\logs'
if (-not (Test-Path $logdir)) { New-Item -ItemType Directory -Path $logdir -Force | Out-Null }
$f = Join-Path $logdir 'lazy-load.log'
if (-not (Test-Path $f)) { New-Item -ItemType File -Path $f -Force | Out-Null }
Get-Item $f | Format-List Name, FullName, Length

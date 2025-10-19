$gitBeforeRepo = $(Split-Path $(git rev-parse --show-toplevel 2>$null) -Parent) -replace [regex]::Escape($HOME), '~'

Write-Host "$gitBeforeRepo/"

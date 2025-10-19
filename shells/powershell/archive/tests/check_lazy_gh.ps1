$p = Join-Path $env:LOCALAPPDATA 'dots\ps-completions\gh.ps1'
Write-Host "Dot-sourcing: $p"
. $p
Write-Host "__ghCompleterBlock present: $([bool](Get-Variable -Name '__ghCompleterBlock' -Scope Global -ErrorAction SilentlyContinue))"
Write-Host "__lazy_gh present: $([bool](Get-Variable -Name '__lazy_gh' -Scope Global -ErrorAction SilentlyContinue))"

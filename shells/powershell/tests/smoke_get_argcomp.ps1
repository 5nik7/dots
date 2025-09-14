$p = Join-Path $env:LOCALAPPDATA 'dots\ps-completions\gh.ps1'
if (Test-Path $p) { . $p; Write-Host "SOURCED: $p" } else { Write-Host "MISSING: $p" }
$v = Get-Variable -Name '__ghCompleterBlock' -Scope Global -ErrorAction SilentlyContinue
if ($v) { Write-Host "VAR present: $($v.Name) (type: $($v.Value.GetType().FullName))" } else { Write-Host 'VAR missing' }
$res = Get-ArgumentCompleter -CommandName gh
if ($res) { $res | Format-List -Force } else { Write-Host 'No completer objects found' }

# Test invoking completer scriptblocks directly
$cache = Join-Path $env:LOCALAPPDATA 'dots\ps-completions'
$p = Join-Path $cache 'gh.ps1'
Write-Host "Loading: $p"
. $p
if (Get-Variable -Name '__ghCompleterBlock' -Scope Global -ErrorAction SilentlyContinue) {
	$sb = Get-Variable -Name '__ghCompleterBlock' -Scope Global -ErrorAction SilentlyContinue
	Write-Host "Invoking __ghCompleterBlock as scriptblock..."
	try {
		$res = & $sb.Value -WordToComplete 're' -CommandAst $null -CursorPosition 3
		if ($res) { $res | ForEach-Object { Write-Host "OUT: $_" } } else { Write-Host 'No output' }
	} catch { Write-Host "Error invoking completer: $($_.Exception.Message)" }
} else {
	Write-Host '__ghCompleterBlock not found'
}

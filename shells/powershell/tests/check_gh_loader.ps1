Write-Host "PowerShell version: $($PSVersionTable.PSVersion) Edition: $($PSVersionTable.PSEdition)"
Write-Host "Register-ArgumentCompleter present: $(if (Get-Command Register-ArgumentCompleter -ErrorAction SilentlyContinue) { 'yes' } else { 'no' })"
Write-Host "Get-ArgumentCompleter present: $(if (Get-Command Get-ArgumentCompleter -ErrorAction SilentlyContinue) { 'yes' } else { 'no' })"

$cache = Join-Path $env:LOCALAPPDATA 'dots\ps-completions'
if (-not (Test-Path $cache)) { Write-Host "Cache dir not found: $cache"; exit 1 }

Get-ChildItem -Path $cache -Filter '*.ps1' | ForEach-Object {
	Write-Host "--- Loading $($_.Name) ---"
	try {
		. $_.FullName
	} catch {
		Write-Host "Dot-source error: $($_.Exception.Message)"
	}
	$varName = '__' + ($_.BaseName) + 'CompleterBlock'
	$v = Get-Variable -Name $varName -Scope Global -ErrorAction SilentlyContinue
	if ($v) { Write-Host "Variable $varName exists (Length: $($v.Value.ToString().Length))" } else { Write-Host "Variable $varName not found" }
	# list any argument completers for the command matching the base name
	$cmdName = $_.BaseName
	try {
		$ac = Get-ArgumentCompleter -CommandName $cmdName -ErrorAction SilentlyContinue
		if ($ac) { Write-Host "Registered argument completers for $($cmdName):"; $ac | Format-List -Force } else { Write-Host "No registered argument completers for $($cmdName)" }
	} catch {
		Write-Host "Get-ArgumentCompleter not available or failed: $($_.Exception.Message)"
	}
}

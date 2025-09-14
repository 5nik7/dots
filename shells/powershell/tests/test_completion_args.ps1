$tools = @('starship', 'bat', 'gh', 'uv', 'uvx', 'glow', 'gowall', 'volta')
foreach ($t in $tools) {
	$cmd = Get-Command $t -ErrorAction SilentlyContinue
	if ($cmd) { Write-Host '---' $t $cmd.Source } else { Write-Host '---' $t '<missing>' }
}
Write-Host '--- Testing sample args ---'
function TryCmd($c, $args) {
	try {
		$out = & $c @($args) 2>&1
		if ($out -and ($out -match '\\S')) {
			$len = ($out | Out-String).Length
			Write-Host "$c $args -> LENGTH=$len"
			$out | Select-Object -First 3 | ForEach-Object { Write-Host '  >' $_ }
		}
		else { Write-Host "$c $args -> <empty>" }
	}
	catch { Write-Host "$c $args -> ERROR: $_" }
}

TryCmd starship 'completions power-shell'
TryCmd starship 'completions powershell'
TryCmd bat '--completion ps1'
TryCmd bat '--completion powershell'
TryCmd gh 'completion --shell powershell'
TryCmd gh 'completion -s powershell'
TryCmd uv 'generate-shell-completion powershell'
TryCmd uv '--generate-shell-completion powershell'
TryCmd uvx '--generate-shell-completion powershell'
TryCmd glow 'completion powershell'
TryCmd gowall 'completion powershell'
TryCmd volta 'completions powershell'
TryCmd volta 'completions --shell powershell'

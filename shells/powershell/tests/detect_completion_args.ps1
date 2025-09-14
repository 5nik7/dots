# Map tool -> list of candidate argument strings to try (first successful wins)
$candidates = @{
		'starship' = @('completions power-shell','completions powershell','completions --shell power-shell','completions --shell powershell')
		'bat'      = @('--completion ps1','--completion powershell','--completion bash')
		'gh'       = @('completion --shell powershell','completion -s powershell','completion powershell')
		'uv'       = @('generate-shell-completion powershell','--generate-shell-completion powershell')
		'uvx'      = @('--generate-shell-completion powershell','generate-shell-completion powershell')
		'glow'     = @('completion powershell','completion --shell powershell')
		'gowall'   = @('completion powershell')
		'volta'    = @('completions --shell power-shell','completions --shell powershell','completions powershell')
}

foreach ($tool in $candidates.Keys) {
	Write-Host "--- $tool ---"
	$cmd = Get-Command $tool -ErrorAction SilentlyContinue
	if (-not $cmd) { Write-Host "(not installed)"; continue }
	foreach ($arg in $candidates[$tool]) {
		Write-Host "Trying: $tool $arg"
		try {
			$parts = ($arg -split ' ' | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' })
			$sb = {
				param($toolName, $parts)
				& $toolName @($parts) 2>&1 | Out-String
			}
			$job = Start-Job -ScriptBlock $sb -ArgumentList $tool, $parts
			$finished = Wait-Job -Job $job -Timeout 8
			if (-not $finished) {
				Write-Host ' -> timeout'
				Stop-Job -Job $job | Out-Null
				Remove-Job -Job $job | Out-Null
				continue
			}
			$out = Receive-Job -Job $job -ErrorAction SilentlyContinue
			Remove-Job -Job $job | Out-Null
			if ($out -and ($out -match '\\S')) {
				$len = ($out).Length
				Write-Host " -> OK (len=$len)"
				$out -split("`n") | Select-Object -First 5 | ForEach-Object { Write-Host "   > $_" }
				break
			} else {
				Write-Host ' -> empty'
			}
		} catch {
			Write-Host " -> error: $($_.Exception.Message)"
		}
	}
}

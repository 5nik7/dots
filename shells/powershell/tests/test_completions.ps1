# Test completions by loading the user's profile and querying the completion engine
$profilePath = 'C:\Users\njen\dots\shells\powershell\Microsoft.PowerShell_profile.ps1'
Write-Host "Loading profile: $profilePath"
. $profilePath

$tests = @('gh','glow','gowall','starship','bat','uv','uvx','volta')
foreach ($t in $tests) {
	try {
		$input = "$t "
		$cursor = $input.Length
		Write-Host "\n--- Testing: $t ---"
	$tokens = $null; $errors = $null
	$ast = [System.Management.Automation.Language.Parser]::ParseInput($input, [ref]$tokens, [ref]$errors)
	$res = [System.Management.Automation.CommandCompletion]::CompleteInput($input, $cursor, $ast, $tokens)
		if ($res -and $res.CompletionMatches) {
			$texts = $res.CompletionMatches | Select-Object -ExpandProperty CompletionText -Unique
			if ($texts) { $texts | Select-Object -First 10 | ForEach-Object { Write-Host "  -> $_" } }
			else { Write-Host "  -> no matches (empty list)" }
		}
		else { Write-Host "  -> no completion result" }
	} catch {
		Write-Host "  -> error: $($_.Exception.Message)"
	}
}
Write-Host "\nDone."

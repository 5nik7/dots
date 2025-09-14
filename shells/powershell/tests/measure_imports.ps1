$mods = @('PSDots','Terminal-Icons','blastoff','lab','UsefulArgumentCompleters','git-completion','PSToml','powershell-yaml')
$results = foreach ($m in $mods) {
	$t = Measure-Command { Import-Module -Name $m -ErrorAction SilentlyContinue }
	[PSCustomObject]@{Module=$m;Milliseconds=[math]::Round($t.TotalMilliseconds,2)}
}
$results | Format-Table -AutoSize

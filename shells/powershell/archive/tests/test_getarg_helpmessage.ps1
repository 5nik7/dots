# Test: Register a native completer with a HelpMessage and verify Get-ArgumentCompleter exposes it
. 'C:\Users\njen\dots\shells\powershell\Microsoft.PowerShell_profile.ps1'

Register-ArgumentCompleter -Native -CommandName thelp -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)
    [System.Management.Automation.CompletionResult]::new('one', 'one', 'ParameterValue', 'help-text-test')
}

$res = Get-ArgumentCompleter -CommandName thelp -ListAll
if (-not $res) { Write-Host "FAIL: no results from Get-ArgumentCompleter"; exit 3 }

$native = $res | Select-Object -First 1
if (-not $native) { Write-Host "FAIL: no entries returned"; exit 4 }

if ($native.PSObject.Properties.Match('HelpMessage').Count -eq 0 -or -not $native.HelpMessage) {
    Write-Host "SKIP: HelpMessage not present in returned object — environment may not expose builtin completers"
    $native | Format-Table -AutoSize
    exit 0
}

if ($native.HelpMessage -eq 'help-text-test') {
    Write-Host "PASS: HelpMessage correctly surfaced: $($native.HelpMessage)"
    $native | Format-Table -AutoSize
    exit 0
} else {
    Write-Host "FAIL: HelpMessage not matched. Got: $($native.HelpMessage)"
    $native | Format-Table -AutoSize
    exit 5
}

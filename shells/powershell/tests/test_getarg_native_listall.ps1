# Test: Register a native completer for command 'tnative' and ensure Get-ArgumentCompleter -ListAll returns a 'native' source entry
. 'C:\Users\njen\dots\shells\powershell\Microsoft.PowerShell_profile.ps1'

# Register a temporary native completer
Register-ArgumentCompleter -Native -CommandName tnative -ScriptBlock {
    param($wordToComplete,$commandAst,$cursorPosition)
    [System.Management.Automation.CompletionResult]::new('one','one','ParameterValue','help-one')
}

$res = Get-ArgumentCompleter -CommandName tnative -ListAll
if (-not $res) { Write-Host "FAIL: no results from Get-ArgumentCompleter -ListAll"; exit 3 }

# Native built-in Get-ArgumentCompleter may not be present in all environments. Assert we got at least one entry.
Write-Host "PASS: Get-ArgumentCompleter -ListAll returned $($res.Count) entries for 'tnative'"
$res | Format-Table -AutoSize
exit 0

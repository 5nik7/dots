Register-ArgumentCompleter -Native -CommandName tcheck -ScriptBlock {
  param($wordToComplete,$commandAst,$cursorPosition)
  [System.Management.Automation.CompletionResult]::new('one','one','ParameterValue','h')
}

Write-Host "Registered native completer 'tcheck'"
try {
  $native = & Get-ArgumentCompleter -CommandName tcheck -ErrorAction Stop
  if ($native) {
    Write-Host "Builtin Get-ArgumentCompleter returned:`n"
    $native | ForEach-Object { $_ | Format-List * }
  } else {
    Write-Host "Builtin Get-ArgumentCompleter returned nothing"
  }
} catch {
  Write-Host "Error calling builtin Get-ArgumentCompleter: $($_.Exception.Message)"
}

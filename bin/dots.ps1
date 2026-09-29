# Native Windows initialization adapter. Other Dots commands use the Bash CLI.
param([Parameter(ValueFromRemainingArguments = $true)][string[]] $Arguments)

if ($Arguments.Count -eq 0 -or $Arguments[0] -in @('--help', '-h') -or
    ($Arguments.Count -eq 2 -and $Arguments[0] -eq 'init' -and $Arguments[1] -in @('--help', '-h'))) {
    'dots init [powershell]'
    'Print PowerShell initialization. Other commands require the Bash dots executable.'
    return
}
if ($Arguments[0] -ne 'init' -or $Arguments.Count -gt 2 -or
    ($Arguments.Count -eq 2 -and $Arguments[1] -ne 'powershell')) {
    [Console]::Error.WriteLine('dots: this native adapter supports init [powershell] only')
    exit 2
}
$root = if ($env:DOTS) { $env:DOTS } else { Split-Path -Parent $PSScriptRoot }
$root = [IO.Path]::GetFullPath($root)
$loader = Join-Path $root 'shells/powershell/init.ps1'
if (-not (Test-Path -LiteralPath $loader -PathType Leaf)) {
    [Console]::Error.WriteLine('dots: cannot read PowerShell loader: ' + $loader)
    exit 1
}
try { $stream = [IO.File]::OpenRead($loader); $stream.Dispose() }
catch { [Console]::Error.WriteLine('dots: cannot read PowerShell loader: ' + $loader); exit 1 }
"`$env:DOTS = '" + $root.Replace("'", "''") + "'"
". (Join-Path `$env:DOTS 'shells/powershell/init.ps1')"

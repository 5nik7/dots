# Native PowerShell entry point. Dots flags remain literal arguments, not cmdlet parameters.
$Arguments = @($args | ForEach-Object { [string] $_ })
$setupRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $setupRoot 'lib/dots/ui.ps1')
$presentation = @{}
$originalArguments = @($Arguments)
while ($Arguments.Count -gt 0 -and $Arguments[0] -match '^--(color|icons)=(auto|always|never|none)$') {
    if ($Matches[1] -eq 'icons' -and $Matches[2] -eq 'none') { break }
    $presentation[$Matches[1]] = if ($Matches[2] -eq 'none') { 'never' } else { $Matches[2] }
    $Arguments = @($Arguments | Select-Object -Skip 1)
}
$dynamicThemeHelp = $Arguments.Count -eq 3 -and $Arguments[0] -eq 'help' -and $Arguments[1] -eq 'theme' -and -not (Test-Path -LiteralPath (Join-Path $setupRoot ('bin/dots-theme-' + $Arguments[2])))
if (-not $dynamicThemeHelp -and ($Arguments.Count -eq 0 -or $Arguments[0] -in @('help', '--help', '-h'))) {
    . (Join-Path $setupRoot 'lib/dots/help.ps1')
    try { Show-DotsHelp $setupRoot @($Arguments | Select-Object -Skip 1) $presentation; exit 0 }
    catch { Write-DotsMessage ('dots: ' + $_.Exception.Message) error $presentation; exit 1 }
}
if ($Arguments.Count -gt 0 -and $Arguments[0] -eq 'init' -and
    ($Arguments.Count -eq 1 -or ($Arguments.Count -eq 2 -and $Arguments[1] -eq 'powershell'))) {
$root = if ($env:DOTS) { $env:DOTS } else { Split-Path -Parent $PSScriptRoot }
$root = [IO.Path]::GetFullPath($root)
. (Join-Path $root 'lib/dots/shell/path.ps1')
try { $root = Resolve-DotsStartupPath $root }
finally { Remove-Item Function:\Resolve-DotsStartupPath }
$loader = Join-Path $root 'lib/dots/shell/init.ps1'
if (-not (Test-Path -LiteralPath $loader -PathType Leaf)) {
    [Console]::Error.WriteLine('dots: cannot read PowerShell loader: ' + $loader)
    exit 1
}
try { $stream = [IO.File]::OpenRead($loader); $stream.Dispose() }
catch { [Console]::Error.WriteLine('dots: cannot read PowerShell loader: ' + $loader); exit 1 }
"`$env:DOTS = '" + $root.Replace("'", "''") + "'"
". (Join-Path `$env:DOTS 'lib/dots/shell/init.ps1')"

    exit 0
}
try {
    . (Join-Path $setupRoot 'lib/dots/files/entry.ps1')
    Invoke-DotsFiles $setupRoot 'cli' $originalArguments $presentation
    exit $script:DotsFilesExitCode
} catch {
    Write-DotsMessage ('dots: ' + $_.Exception.Message) error $presentation
    exit 1
}

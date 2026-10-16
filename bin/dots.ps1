# Native Windows initialization adapter. Other Dots commands use the Bash CLI.
param([Parameter(ValueFromRemainingArguments = $true)][string[]] $Arguments = @())

$presentation = @{}
while ($Arguments.Count -gt 0 -and $Arguments[0] -match '^--(color|icons)=(auto|always|never)$') {
    $presentation[$Matches[1]] = $Matches[2]
    $Arguments = @($Arguments | Select-Object -Skip 1)
}
$setupRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $setupRoot 'lib/dots/ui.ps1')
$controller = $null
$forwarded = @()
if ($Arguments.Count -ge 2 -and $Arguments[0] -eq 'init' -and $Arguments[1] -eq '--setup') {
    $controller = 'install'
    $forwarded = @('install') + @($Arguments | Select-Object -Skip 2)
}
elseif ($Arguments.Count -ge 2 -and $Arguments[0] -eq 'files') {
    if ($Arguments[1] -in @('stash', 'edit')) {
        $controller = 'mappings'
        $forwarded = @($Arguments | Select-Object -Skip 1)
    }
    elseif ($Arguments[1] -eq 'check') {
        $controller = 'check'
        $forwarded = @($Arguments | Select-Object -Skip 2)
    }
    elseif ($Arguments[1] -in @('install', 'uninstall')) {
        $controller = 'install'
        $forwarded = @($Arguments | Select-Object -Skip 1)
    }
    elseif ($Arguments[1] -in @('list', 'sources', 'show', 'source', 'target')) {
        $controller = 'catalog'
        $forwarded = @($Arguments | Select-Object -Skip 1)
    }
    elseif ($Arguments[1] -in @('history', 'undo', 'recover')) {
        $controller = 'manage'
        $forwarded = @($Arguments | Select-Object -Skip 1)
    }
    elseif ($Arguments.Count -ge 3 -and $Arguments[1] -eq 'backups' -and $Arguments[2] -in @('list', 'show', 'restore')) {
        $controller = 'manage'
        $forwarded = @('backups-' + $Arguments[2]) + @($Arguments | Select-Object -Skip 3)
    }
}
if ($controller) {
    try {
        . (Join-Path $setupRoot 'lib/dots/files/entry.ps1')
        Invoke-DotsFiles $setupRoot $controller $forwarded $presentation
        exit $script:DotsFilesExitCode
    }
    catch { Write-DotsMessage ('dots: ' + $_.Exception.Message) error $presentation; exit 1 }
}
if ($Arguments.Count -eq 0 -or $Arguments[0] -in @('--help', '-h') -or
    ($Arguments.Count -eq 2 -and $Arguments[0] -eq 'init' -and $Arguments[1] -in @('--help', '-h'))) {
    Write-DotsMessage 'Dots' heading $presentation
    Write-DotsMessage 'dots init [powershell]' info $presentation
    Write-DotsMessage 'dots init --setup [OPTIONS]' info $presentation
    Write-DotsMessage 'dots files install|uninstall|check|stash|edit|list|sources|show|source|target|history|undo|recover|backups [OPTIONS]' info $presentation
    Write-DotsMessage 'Print PowerShell initialization or manage the bounded native installation. Other commands require Bash.' info $presentation
    return
}
if ($Arguments[0] -ne 'init' -or $Arguments.Count -gt 2 -or
    ($Arguments.Count -eq 2 -and $Arguments[1] -ne 'powershell')) {
    Write-DotsMessage 'dots: use native init, setup or supported files routes; other commands require Bash' error $presentation
    exit 2
}
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

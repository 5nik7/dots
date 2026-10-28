# Definitions only: importing this file never discovers or launches a runtime.
function Get-BlastoffRuntime {
    if ($env:BLASTOFF_PYTHON) {
        $application = Get-Command -Name $env:BLASTOFF_PYTHON -CommandType Application -ErrorAction Stop | Select-Object -First 1
        if ([IO.Path]::GetExtension($application.Source) -in @('.cmd','.bat','.ps1')) { throw 'BLASTOFF_PYTHON must name a native interpreter executable, not a shell launcher.' }
        return @{ Executable=$application.Source; Prefix=@() }
    }
    $names = if ($IsWindows) { @('py','python3','python') } else { @('python3','python') }
    foreach ($name in $names) {
        $application = Get-Command -Name $name -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($application -and [IO.Path]::GetExtension($application.Source) -notin @('.cmd','.bat','.ps1')) {
            $prefixArguments=@(); if ($name -eq 'py') { $prefixArguments=@('-3') }
            return @{ Executable=$application.Source; Prefix=$prefixArguments }
        }
    }
    throw 'Python 3.11+ is required; set BLASTOFF_PYTHON to a native executable path.'
}
function ConvertTo-BlastoffEnvelope {
    param([AllowEmptyCollection()][object[]]$Arguments)
    $nativeHost = if ($IsWindows) { 'nt' } else { 'posix' }
    $executable = Join-Path $PSHOME $(if ($IsWindows) { 'pwsh.exe' } else { 'pwsh' })
    $values = [string[]]@($Arguments | ForEach-Object { [string]$_ })
    $json = ConvertTo-Json -Compress -Depth 5 -InputObject @{version=1;host=$nativeHost;shell=$executable;argv=$values}
    [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
}
function Get-BlastoffLegacyCompletionNames {
    param([string]$Root,[string]$Kind,[string]$CacheKey)
    # PowerShell 7.0 Unix lacks UnixMode unless PSUnixFileStat is enabled. Use
    # the already-required native Python only for this dynamic filename case.
    $now=[DateTime]::UtcNow
    $key='legacy|'+$CacheKey
    if ($script:CompletionCache.ContainsKey($key) -and ($now-$script:CompletionCache[$key].Time).TotalSeconds -lt 2) {
        return $script:CompletionCache[$key].Names
    }
    $process=$null
    try {
        $selection=Get-BlastoffRuntime
        $context=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes((ConvertTo-Json -Compress -InputObject @{root=$Root;kind=$Kind})))
        $start=[Diagnostics.ProcessStartInfo]::new()
        $start.FileName=$selection.Executable;$start.UseShellExecute=$false
        $start.RedirectStandardOutput=$true;$start.RedirectStandardError=$true;$start.CreateNoWindow=$true
        foreach ($argument in @($selection.Prefix)+@('-I','-B',(Join-Path (Split-Path $PSScriptRoot -Parent) 'lib/completion_names.py'),$context)) {
            $start.ArgumentList.Add([string]$argument)
        }
        $process=[Diagnostics.Process]::new();$process.StartInfo=$start
        if (-not $process.Start()) { return @() }
        $output=$process.StandardOutput.ReadToEndAsync();$errors=$process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit(2000)) { $process.Kill();return @() }
        if (-not $output.Wait(100) -or -not $errors.Wait(100) -or $process.ExitCode -ne 0 -or $output.Result.Length -gt 524288) { return @() }
        $doc=$output.Result | ConvertFrom-Json -ErrorAction Stop
        $names=@($doc.names | Where-Object { $_ -cmatch '\A[A-Za-z0-9][A-Za-z0-9_-]{0,95}\z' })
        if ($names.Count -gt 4096) { return @() }
        if ($script:CompletionCache.Count -ge 8) {$script:CompletionCache.Clear()}
        $script:CompletionCache[$key]=@{Time=$now;Names=$names}
        return $names
    } catch { return @() }
    finally { if ($process) { $process.Dispose() } }
}

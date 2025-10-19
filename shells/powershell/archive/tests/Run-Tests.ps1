<#
Run-Tests.ps1
Usage:
  .\Run-Tests.ps1 gh glow
  .\Run-Tests.ps1 all

This runner maps short names to test scripts in this folder and runs them sequentially.
It times each run and prints a concise summary table at the end.
#>
[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments=$true)][string[]]$Targets = @()
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$testsDir = $scriptDir

# Mapping from alias -> script filename (relative to this folder)
$map = @{
    'gh' = 'trigger_lazy_gh.ps1'
    'check-gh' = 'check_gh_loader.ps1'
    'check-lazy-gh' = 'check_lazy_gh.ps1'
    'detect' = 'detect_completion_args.ps1'
    'measure' = 'measure_imports.ps1'
    'invoke-gh' = 'invoke_completer_test.ps1'
    'test-completions' = 'test_completions.ps1'
    'test-args' = 'test_completion_args.ps1'
    'ensure-log' = 'ensure_lazy_log.ps1'
    'ensure-log2' = 'ensure_lazy_log2.ps1'
    'force-lazy' = 'test_force_lazy_log.ps1'
    'lazy-write' = 'test_lazy_log_write.ps1'
    'trigger-gh' = 'trigger_lazy_gh.ps1'
}

if (-not $Targets -or $Targets -contains 'all') {
    $Targets = $map.Keys
}

$results = @()
foreach ($t in $Targets) {
    $script = $null
    if ($map.ContainsKey($t)) { $script = Join-Path $testsDir $map[$t] }
    elseif (Test-Path (Join-Path $testsDir $t)) { $script = Join-Path $testsDir $t }
    else { Write-Warning "Unknown target: $t"; continue }

    Write-Host "---- Running: $t -> $script ----"
    $start = Get-Date
    try {
        & pwsh -NoProfile -ExecutionPolicy Bypass -File $script 2>&1 | ForEach-Object { Write-Host "  $_" }
        $status = 'OK'
    } catch {
        Write-Host "  ERROR: $($_.Exception.Message)"
        $status = 'FAIL'
    }
    $end = Get-Date
    $ms = [int]((New-TimeSpan -Start $start -End $end).TotalMilliseconds)
    $results += [pscustomobject]@{Target=$t;Script=$script;Status=$status;ElapsedMs=$ms}
}

Write-Host "`nSummary:`n"
$results | Sort-Object -Property ElapsedMs -Descending | Format-Table -AutoSize

# exit with non-zero code if any failures
if ($results | Where-Object { $_.Status -ne 'OK' }) { exit 2 }
exit 0

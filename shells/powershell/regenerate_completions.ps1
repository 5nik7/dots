<#
Regenerate completions for supported tools and store them in the dots ps-completions cache.
Usage:
  .\regenerate_completions.ps1           # regenerates only if missing or older than 24h
  .\regenerate_completions.ps1 -Force   # force regenerate all
#>
[CmdletBinding()]
param(
  [switch]$Force
)

$cacheDir = Join-Path $env:LOCALAPPDATA 'dots\ps-completions'
if (-not (Test-Path $cacheDir)) { New-Item -ItemType Directory -Path $cacheDir -Force | Out-Null }

$logsDir = Join-Path $env:LOCALAPPDATA 'dots\logs'
if (-not (Test-Path $logsDir)) { New-Item -ItemType Directory -Path $logsDir -Force | Out-Null }
$logFile = Join-Path $logsDir 'regen.log'

# Log rotation settings
$maxBytes = 5MB
$backups = 3
if ($env:DOTS_REGEN_LOG_MAX_BYTES) { try { $maxBytes = [int]$env:DOTS_REGEN_LOG_MAX_BYTES } catch { } }
if ($env:DOTS_REGEN_LOG_BACKUPS) { try { $backups = [int]$env:DOTS_REGEN_LOG_BACKUPS } catch { } }

function Rotate-Log {
  try {
    if (Test-Path $logFile) {
      $len = (Get-Item $logFile).Length
      if ($len -gt $maxBytes) {
        for ($i = $backups - 1; $i -ge 0; $i--) {
          $src = if ($i -eq 0) { $logFile } else { "$logFile.$i" }
          $dst = "$logFile.$($i + 1)"
          if (Test-Path $src) { Move-Item -Path $src -Destination $dst -Force -ErrorAction SilentlyContinue }
        }
      }
    }
  }
  catch { }
}

function Log-Write { param($msg) Rotate-Log; $line = "$(Get-Date -Format o) `t $msg"; Add-Content -Path $logFile -Value $line }

$items = @(
  @{Name = 'starship'; Cmd = 'starship'; AutoDetect = $true; Args = @(); File = 'starship.ps1' },
  @{Name = 'bat'; Cmd = 'bat'; AutoDetect = $true; Args = @(); File = 'bat.ps1' },
  @{Name = 'gh'; Cmd = 'gh'; AutoDetect = $true; Args = @(); File = 'gh.ps1' },
  @{Name = 'uv'; Cmd = 'uv'; AutoDetect = $true; Args = @(); File = 'uv.ps1' },
  @{Name = 'uvx'; Cmd = 'uvx'; AutoDetect = $true; Args = @(); File = 'uvx.ps1' },
  @{Name = 'glow'; Cmd = 'glow'; AutoDetect = $true; Args = @(); File = 'glow.ps1' },
  @{Name = 'gowall'; Cmd = 'gowall'; AutoDetect = $true; Args = @(); File = 'gowall.ps1' },
  @{Name = 'volta'; Cmd = 'volta'; AutoDetect = $true; Args = @(); File = 'volta.ps1' }
)

# Heuristic detection of preferred completion arguments per tool. This runs only when the regeneration script runs (manual or background).
function Get-CommandHelpText { param($cmd) try { $out = & $cmd --help 2>&1; if ($out) { return $out -join "`n" } } catch { } try { $out = & $cmd -h 2>&1; if ($out) { return $out -join "`n" } } catch { } return '' }

function Get-PreferredCompletionArgs {
  param($cmd)
  $help = Get-CommandHelpText $cmd
  switch -Wildcard ($cmd) {
    'starship' {
      # starship expects 'power-shell' (with hyphen) on many versions
      return @('completions power-shell', 'completions powershell')
    }
    'bat' {
      # prefer ps1 which is the PowerShell-compatible completion token
      return @('--completion ps1', '--completion powershell', '--completion ps')
    }
    'gh' {
      # gh supports: 'completion --shell powershell'
      return @('completion --shell powershell', 'completion powershell', 'completion -s powershell')
    }
    'uv' { return @('generate-shell-completion powershell', '--generate-shell-completion powershell') }
    'uvx' { return @('--generate-shell-completion powershell', '--generate-shell-completion=power-shell') }
    'glow' { return @('completion powershell', 'completion --shell powershell') }
    'gowall' { return @('completion powershell') }
    'volta' { return @('completions powershell', 'completions --shell powershell') }
    default { return @() }
  }
}

foreach ($i in $items) {
  if ($i.AutoDetect -and -not $i.Args) {
    $i.Args = Get-PreferredCompletionArgs $i.Cmd
  }
  if (-not (Get-Command $($i.Cmd) -ErrorAction SilentlyContinue)) { Write-Verbose "Skipping $($i.Name): command not found"; Log-Write "SKIP $($i.Name) - command not found"; continue }
  $outFile = Join-Path $cacheDir $($i.File)
  $should = $Force.IsPresent -or -not (Test-Path $outFile) -or ((Get-Date) - (Get-Item $outFile).LastWriteTime).TotalHours -gt 24
  if ($should) {
    Write-Host "Regenerating $($i.Name) -> $outFile"
    Log-Write "START $($i.Name) -> $outFile"
    try {
      $succeeded = $false
      foreach ($a in $($i.Args)) {
        # Run command with argument array to avoid shell parsing issues
        $argArray = @()
        if ($a) { $argArray = $a -split ' ' }
        try {
          $output = & $($i.Cmd) @argArray 2>&1
          if ($output -and ($output -match '\S')) {
            $outputStr = $output -join "`n"
            # Basic sanity check: ensure the generated output contains PowerShell-specific completion markers
            if ($outputStr -match '(?i)Register-ArgumentCompleter|completerBlock|Register-ArgumentCompleter') {
              $outputStr | Out-File -FilePath $outFile -Encoding utf8
              if ((Get-Item $outFile).Length -gt 16) { $succeeded = $true; break }
            }
            else {
              # Not PowerShell completion output; skip
              Write-Verbose "Output for $($i.Name) did not look like PowerShell completion (skipping)"
              # ensure no stale file remains
              Remove-Item -LiteralPath $outFile -ErrorAction SilentlyContinue
            }
          }
        }
        catch { }
      }
      if ($succeeded) { Log-Write "OK $($i.Name)" } else { Log-Write "FAIL $($i.Name) - no supported completion args or empty output" }
    }
    catch {
      Log-Write "ERROR $($i.Name) - $_"
    }
  }
  else {
    Write-Host "Skipping $($i.Name) (up-to-date)"
    Log-Write "SKIP $($i.Name) - up-to-date"
  }
}

Write-Host "Completed regenerating completions."

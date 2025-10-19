# Only run interactive initialization when in an interactive host
if ($Host.UI.RawUI -and -not $IsWindows -or $Host.Name -ne 'ServerRemoteHost') {
}

# Lightweight helper: import module if available (silently ignore failures)
function Try-ImportModule { param($Name) Import-Module -Name $Name -Global -ErrorAction SilentlyContinue }

# Avoid repeatedly calling Unblock-File unnecessarily; only unblock if AlternateDataStream exists
function Unblock-IfNeeded { param($Path) if (Test-Path $Path) { try { if ((Get-Item -LiteralPath $Path -Stream "Zone.Identifier" -ErrorAction SilentlyContinue)) { Unblock-File -Path $Path -ErrorAction SilentlyContinue } } catch { } } }

Try-ImportModule 'PSDots'

if (Test-Path "$PSCOMPONENT\functions.ps1") {
  Unblock-IfNeeded "$PSCOMPONENT\functions.ps1"
  . "$PSCOMPONENT\functions.ps1"
}

# Load dotenv only in interactive shells (saves time for non-interactive scripts)
if ($Host.UI.RawUI) {
  dotenv $env:DOTS -ErrorAction SilentlyContinue
  dotenv $env:secretdir -ErrorAction SilentlyContinue

  $psource = ( 'readline', 'prompt', 'aliases')
  if ($PSEdition -eq 'Core') { $psource += 'copilot' }
  foreach ($piece in $psource) {
    $pfile = Join-Path $PSCOMPONENT "$piece.ps1"
    if (Test-Path $pfile) {
      Unblock-IfNeeded $pfile
      . $pfile
    }
  }

  Set-FuzzyOpts -ErrorAction SilentlyContinue

  if (Get-Command fzf -ErrorAction SilentlyContinue) {
    Import-ScoopModule -Name 'PsFzf' -ErrorAction SilentlyContinue
    Set-PsFzfOption -TabExpansion -ErrorAction SilentlyContinue
  }
}

# Provide a unified Get-ArgumentCompleter wrapper that prefers the built-in cmdlet
# but also returns cached/lazy completers created by this profile (variables like
# __<cmd>CompleterBlock and __lazy_<cmd>). This ensures callers can inspect
# available completers even if the built-in returns nothing.
function Get-ArgumentCompleter {
  [CmdletBinding()]
  param(
    [Parameter(Position = 0)][string]$CommandName,
    [switch]$ListAll,
    [switch]$IncludeLazy
  )
  if (-not $CommandName) { Write-Error 'CommandName is required'; return }

  $results = @()

  # 1) Prefer the builtin cmdlet (module-qualified) if present
  try {
    # Prefer the builtin cmdlet if available. Use an unqualified lookup which works
    # in more environments (module qualification may fail in some non-interactive hosts).
    if (Get-Command -Name Get-ArgumentCompleter -ErrorAction SilentlyContinue) {
      try { $native = & Get-ArgumentCompleter -CommandName $CommandName -ErrorAction SilentlyContinue } catch { $native = $null }
      if ($native) {
        # Normalize native results into a consistent shape
        foreach ($n in $native) {
          $results += [pscustomobject]@{
            CommandName     = $n.CommandName
            ParameterName   = ($n.ParameterName -as [string])
            ScriptBlock     = $n.ScriptBlock
            ScriptBlockType = ($n.ScriptBlock -is [scriptblock]) ? 'ScriptBlock' : ($n.ScriptBlock.GetType().FullName)
            Source          = 'native'
            HelpMessage     = ($n.HelpMessage -as [string])
          }
        }
        if (-not $ListAll -and $results.Count -gt 0) { return $results }
      }
    }
  }
  catch { }

  # 2) Cached completer scriptblock: __<cmd>CompleterBlock
  try {
    $varName = "__${CommandName}CompleterBlock"
    $v = Get-Variable -Name $varName -Scope Global -ErrorAction SilentlyContinue
    if ($v -and $v.Value -is [scriptblock]) {
      $results += [pscustomobject]@{
        CommandName     = $CommandName
        ParameterName   = ''
        ScriptBlock     = $v.Value
        ScriptBlockType = 'ScriptBlock'
        Source          = 'dots:cached'
        HelpMessage     = ''
      }
      if (-not $ListAll) { return $results }
    }
  }
  catch { }

  # 3) Lazy wrapper variable __lazy_<cmd> (include only when requested)
  if ($IncludeLazy -or $ListAll) {
    try {
      $lazyVar = "__lazy_${CommandName}"
      $lv = Get-Variable -Name $lazyVar -Scope Global -ErrorAction SilentlyContinue
      if ($lv -and $lv.Value -is [scriptblock]) {
        $results += [pscustomobject]@{
          CommandName     = $CommandName
          ParameterName   = ''
          ScriptBlock     = $lv.Value
          ScriptBlockType = 'ScriptBlock'
          Source          = 'dots:lazy-wrapper'
          HelpMessage     = ''
        }
      }
    }
    catch { }
  }

  if ($results.Count -gt 0) { return $results }
  return $null
}

# Import-Module -Name 'PowerShellGet' -Global
# Import lightweight modules lazily; only import if available to avoid timeouts
# Defer heavier imports and non-critical setup until the host is idle so the prompt appears quickly.
$null = Register-EngineEvent -SourceIdentifier 'PowerShell.OnIdle' -MaxTriggerCount 1 -Action {
  Try-ImportModule 'Terminal-Icons'
  Try-ImportModule 'blastoff'
  # Try-ImportModule 'powernerd'
  # Try-ImportModule 'winwal'
  Try-ImportModule 'lab'
  Try-ImportModule 'UsefulArgumentCompleters'

  if (Get-Command scoop -ErrorAction SilentlyContinue) { Import-ScoopModule -Name 'scoop-completion' -ErrorAction SilentlyContinue }
  Try-ImportModule 'git-completion'
  Try-ImportModule 'PSToml'
  Try-ImportModule 'powershell-yaml'

  try { if (Get-Command vivid -ErrorAction SilentlyContinue) { $env:LS_COLORS = "$(vivid generate catppuccin-mocha)" } } catch { }

  # Register winget completer after modules are available
  Register-ArgumentCompleter -Native -CommandName winget -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)
    [Console]::InputEncoding = [Console]::OutputEncoding = $OutputEncoding = [System.Text.Utf8Encoding]::new()
    $Local:word = $wordToComplete.Replace('"', '""')
    $Local:ast = $commandAst.ToString().Replace('"', '""')
    winget complete --word="$Local:word" --commandline "$Local:ast" --position $cursorPosition | ForEach-Object {
      [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
    }
  }
}

if ($Host.UI.RawUI) {
  # Cache directory for generated completions to avoid blocking on each startup
  $cacheDir = Join-Path $env:LOCALAPPDATA 'dots\ps-completions'
  if (-not (Test-Path $cacheDir)) { New-Item -ItemType Directory -Path $cacheDir -Force | Out-Null }

  # By default do not dot-source all cached completion files at startup (keeps startup minimal).
  # Set DOTS_LOAD_CACHED_COMPLETIONS=1 to opt-in to early loading. Otherwise we rely on lazy wrappers.
  $loadCached = $false
  if ($env:DOTS_LOAD_CACHED_COMPLETIONS -and $env:DOTS_LOAD_CACHED_COMPLETIONS -eq '1') { $loadCached = $true }
  if ($loadCached) {
    try {
      Get-ChildItem -Path $cacheDir -Filter '*.ps1' -File -ErrorAction SilentlyContinue | ForEach-Object {
        try { . $_.FullName } catch { Write-Verbose "Failed to dot-source cached completion $($_.Name): $($_.Exception.Message)" }
      }
    }
    catch { }
  }

  # Lazy-load logging helper
  $lazyLogsDir = Join-Path $env:LOCALAPPDATA 'dots\logs'
  if (-not (Test-Path $lazyLogsDir)) { New-Item -ItemType Directory -Path $lazyLogsDir -Force | Out-Null }
  $lazyLogFile = Join-Path $lazyLogsDir 'lazy-load.log'
  $lazyMaxBytes = 1MB
  $lazyBackups = 3

  function Dots-LogLazyLoad {
    param(
      [Parameter(Mandatory = $true)][string]$Name,
      [Parameter(Mandatory = $true)][string]$File,
      [int]$ElapsedMs
    )
    # Always attempt to write a timestamped lazy-load entry. If writing the dedicated lazy log
    # fails for any reason, fall back to appending to regen.log so the event is still observable.
    try {
      if (Test-Path $lazyLogFile) {
        $len = (Get-Item $lazyLogFile).Length
        if ($len -gt $lazyMaxBytes) {
          for ($i = $lazyBackups - 1; $i -ge 0; $i--) {
            $src = if ($i -eq 0) { $lazyLogFile } else { "$lazyLogFile.$i" }
            $dst = "$lazyLogFile.$($i + 1)"
            if (Test-Path $src) { Move-Item -Path $src -Destination $dst -Force -ErrorAction SilentlyContinue }
          }
        }
      }
      $line = "$(Get-Date -Format o)`tLAZYLOAD`t$Name`t$File`tElapsedMs=$ElapsedMs"
      Add-Content -Path $lazyLogFile -Value $line -ErrorAction Stop
      # Also update per-command aggregate stats (counts, totalMs, avgMs, lastMs)
      try {
        if (-not (Test-Path $lazyLogsDir)) { New-Item -ItemType Directory -Path $lazyLogsDir -Force | Out-Null }
        $statsFile = Join-Path $lazyLogsDir 'lazy-load-stats.json'
        function Dots-RecordLazyStats {
          param(
            [Parameter(Mandatory = $true)][string]$Name,
            [Parameter(Mandatory = $true)][int]$ElapsedMs
          )
          try {
            $data = @{}
            if (Test-Path $statsFile) {
              try { $content = Get-Content -Path $statsFile -Raw -ErrorAction SilentlyContinue; if ($content) { $data = ConvertFrom-Json $content } } catch { $data = @{} }
            }

            if (-not $data.ContainsKey($Name)) {
              $data[$Name] = @{ count = 0; totalMs = 0; avgMs = 0; lastMs = 0; lastAt = "" }
            }
            $entry = $data[$Name]
            $entry.count = [int]$entry.count + 1
            $entry.totalMs = [int]$entry.totalMs + $ElapsedMs
            $entry.lastMs = $ElapsedMs
            $entry.avgMs = [int]([math]::Round(($entry.totalMs / $entry.count)))
            $entry.lastAt = (Get-Date -Format o)
            $data[$Name] = $entry

            $json = $data | ConvertTo-Json -Depth 5
            # Atomic write: write to temp then move
            $tmp = "$statsFile.tmp"
            Set-Content -Path $tmp -Value $json -Encoding UTF8 -Force
            Move-Item -Path $tmp -Destination $statsFile -Force
          }
          catch { }
        }
        # Record this event
        Dots-RecordLazyStats -Name $Name -ElapsedMs $ElapsedMs
      }
      catch { }
      # Optionally print a visible notice when the env var DOTS_LAZY_VERBOSE=1
      if ($env:DOTS_LAZY_VERBOSE -eq '1') { Write-Host "[dots] lazy-loaded $Name from $File" }
      Write-Verbose "Dots-LogLazyLoad: $Name -> $File"
    }
    catch {
      # Fallback: append to regen.log so events are still captured.
      try { Add-Content -Path (Join-Path $env:LOCALAPPDATA 'dots\logs\regen.log') -Value ("$(Get-Date -Format o)`tLAZYLOAD-FALLBACK`t$Name`t$File") -ErrorAction SilentlyContinue } catch { }
    }
  }

  # Register lazy-loading argument completers: these are small, fast scriptblocks
  # that dot-source the cached completion file on first invocation and then
  # forward the completion request to the loaded completer.
  function Register-LazyCompleter {
    param(
      [string]$CommandName,
      [string]$CacheFile
    )

    $globalVarName = "__lazy_${CommandName}"

    $sb = {
      param($wordToComplete, $commandAst, $cursorPosition)
      try {
        # If the real completer scriptblock variable is already present, call it directly
        $realVar = Get-Variable -Name ("__" + $using:CommandName + "CompleterBlock") -Scope Global -ErrorAction SilentlyContinue
        if ($realVar -and $realVar.Value -is [scriptblock]) {
          return & $realVar.Value -WordToComplete $wordToComplete -CommandAst $commandAst -CursorPosition $cursorPosition
        }

        # Try to dot-source cached completion file (may be slow on first use)
        if ($using:CacheFile -and (Test-Path $using:CacheFile)) {
          try {
            . $using:CacheFile
            # Measure how long the dot-sourcing took and log it (milliseconds)
            try {
              $sw = [System.Diagnostics.Stopwatch]::StartNew()
              . $using:CacheFile
              $sw.Stop()
              $elapsed = [int]$sw.ElapsedMilliseconds
              try { Dots-LogLazyLoad -Name $using:CommandName -File $using:CacheFile -ElapsedMs $elapsed } catch {
                # Fallback: if dedicated lazy log write fails, append a minimal marker to regen.log
                try { Add-Content -Path (Join-Path $env:LOCALAPPDATA 'dots\logs\regen.log') -Value ("$(Get-Date -Format o)`tLAZYLOAD-FALLBACK`t$($using:CommandName)`t$($using:CacheFile)`tElapsedMs=$elapsed") -ErrorAction SilentlyContinue } catch { }
              }
              if ($env:DOTS_LAZY_VERBOSE -eq '1') { Write-Host "[dots] lazy-loaded $($using:CommandName) from $($using:CacheFile) in ${elapsed}ms" }
            }
            catch { }
            # Verbose/host diagnostic
            if ($env:DOTS_LAZY_VERBOSE -eq '1') { Write-Host "[dots] lazy-loaded $($using:CommandName) from $($using:CacheFile)" }
          }
          catch { }
        }

        # After loading, attempt to find and call the real completer
        $realVar = Get-Variable -Name ("__" + $using:CommandName + "CompleterBlock") -Scope Global -ErrorAction SilentlyContinue
        if ($realVar -and $realVar.Value -is [scriptblock]) {
          return & $realVar.Value -WordToComplete $wordToComplete -CommandAst $commandAst -CursorPosition $cursorPosition
        }

        # Nothing available; return nothing (no completions)
        return
      }
      catch {
        return
      }
    }

    # Store the wrapper in a predictable global variable so tests can call it
    try { Set-Variable -Name $globalVarName -Value $sb -Scope Global -Force } catch { }
    try { Register-ArgumentCompleter -Native -CommandName $CommandName -ScriptBlock (Get-Variable -Name $globalVarName -Scope Global).Value -ErrorAction SilentlyContinue } catch { }
  }

  # Register lazy completers for the known set
  $dotCacheDir = $cacheDir
  Register-LazyCompleter -CommandName 'starship' -CacheFile (Join-Path $dotCacheDir 'starship.ps1')
  Register-LazyCompleter -CommandName 'bat' -CacheFile (Join-Path $dotCacheDir 'bat.ps1')
  Register-LazyCompleter -CommandName 'gh' -CacheFile (Join-Path $dotCacheDir 'gh.ps1')
  Register-LazyCompleter -CommandName 'uv' -CacheFile (Join-Path $dotCacheDir 'uv.ps1')
  Register-LazyCompleter -CommandName 'uvx' -CacheFile (Join-Path $dotCacheDir 'uvx.ps1')
  Register-LazyCompleter -CommandName 'glow' -CacheFile (Join-Path $dotCacheDir 'glow.ps1')
  Register-LazyCompleter -CommandName 'gowall' -CacheFile (Join-Path $dotCacheDir 'gowall.ps1')
  Register-LazyCompleter -CommandName 'volta' -CacheFile (Join-Path $dotCacheDir 'volta.ps1')

  function Ensure-Completion {
    param($Name, $Command, $Args, $Filename)
    $file = Join-Path $cacheDir $Filename
    $regen = $false
    if (-not (Test-Path $file)) { $regen = $true }
    else { $age = (Get-Date) - (Get-Item $file).LastWriteTime; if ($age.TotalHours -gt 24) { $regen = $true } }

    if (-not (Get-Command $Command -ErrorAction SilentlyContinue)) { return }

    # If a cached file exists, dot-source it so any functions/scriptblocks are registered in this session.
    if (Test-Path $file) { try { . $file } catch { } }

    # Background regeneration: controlled by DOTS_REGEN_COMPLETIONS (env var). If set to '1', schedule a single named job to regenerate all completions when CPU is below threshold.
    if ($regen -and ($env:DOTS_REGEN_COMPLETIONS -eq '1')) {
      try {
        # Clean up old completed jobs > 24h
        try { Get-Job -Name 'DotsRegen' -State Completed -ErrorAction SilentlyContinue | Where-Object { ($_.EndTime -ne $null) -and ((Get-Date) - $_.EndTime).TotalHours -gt 24 } | Remove-Job -Force -ErrorAction SilentlyContinue } catch { }

        # If a DotsRegen job is already running, skip
        $existing = Get-Job -Name 'DotsRegen' -ErrorAction SilentlyContinue | Where-Object { $_.State -in @('Running', 'NotStarted') }
        if ($existing) { return }

        # CPU-threshold check (percent). Default 25 unless DOTS_REGEN_CPU_THRESHOLD set.
        $threshold = 25
        if ($env:DOTS_REGEN_CPU_THRESHOLD) { try { $threshold = [int]$env:DOTS_REGEN_CPU_THRESHOLD } catch { } }

        try {
          $cpu = 0
          if ($PSVersionTable.PSEdition -eq 'Core') {
            $cpu = (Get-Counter '\Processor(_Total)\% Processor Time' -SampleInterval 0.5 -MaxSamples 1).CounterSamples[0].CookedValue
          }
          else {
            $cpu = (Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average
          }
        }
        catch { $cpu = 0 }

        # Idle-time check: only start background job if system idle >= DOTS_REGEN_IDLE_SECONDS (default 60)
        $idleSeconds = 60
        if ($env:DOTS_REGEN_IDLE_SECONDS) { try { $idleSeconds = [int]$env:DOTS_REGEN_IDLE_SECONDS } catch { } }
        function Get-IdleSeconds {
          try {
            if ($IsWindows) {
              $wmi = Get-CimInstance -ClassName Win32_PerfFormattedData_PerfOS_System -ErrorAction SilentlyContinue
              if ($wmi -and $wmi.SystemUpTime) { return [int]$wmi.SystemUpTime }
            }
          }
          catch { }
          return 0
        }

        $idle = Get-IdleSeconds
        if ($cpu -lt $threshold -and $idle -ge $idleSeconds) {
          # Start a named single job that runs the regeneration script (logs inside script)
          $regenScript = Join-Path $env:PSDOTS 'regenerate_completions.ps1'
          if (Test-Path $regenScript) {
            try { Start-Job -Name 'DotsRegen' -ScriptBlock { & $using:regenScript -Force } | Out-Null } catch { }
          }
        }
      }
      catch { }
    }
  }

  Ensure-Completion 'starship' 'starship' 'completions power-shell' 'starship.ps1'
  Ensure-Completion 'bat' 'bat' '--completion ps1' 'bat.ps1'
  Ensure-Completion 'gh' 'gh' 'completion -s powershell' 'gh.ps1'
  Ensure-Completion 'uv' 'uv' 'generate-shell-completion powershell' 'uv.ps1'
  Ensure-Completion 'uvx' 'uvx' '--generate-shell-completion powershell' 'uvx.ps1'
  Ensure-Completion 'glow' 'glow' 'completion powershell' 'glow.ps1'
  Ensure-Completion 'gowall' 'gowall' 'completion powershell' 'gowall.ps1'
  Ensure-Completion 'volta' 'volta' 'completions powershell' 'volta.ps1'
}

# DotsRegen status helper and optional prompt integration
function Get-DotsRegenStatus {
  $job = Get-Job -Name 'DotsRegen' -ErrorAction SilentlyContinue
  if (-not $job) { return 'regen:idle' }
  switch ($job.State) {
    'Running' { return 'regen:running' }
    'Completed' { return 'regen:completed' }
    'Failed' { return 'regen:failed' }
    default { return "regen:$($job.State)" }
  }
}

# Utility: show aggregated lazy-load stats
function Get-DotsLazyStats {
  [CmdletBinding()]
  param(
    [int]$Top = 10,
    [ValidateSet('avgMs', 'totalMs', 'count', 'lastAt')][string]$SortBy = 'avgMs',
    [switch]$Descending
  )

  $statsFile = Join-Path $lazyLogsDir 'lazy-load-stats.json'
  if (-not (Test-Path $statsFile)) { Write-Error "Lazy stats file not found: $statsFile"; return }
  try {
    $json = Get-Content -Path $statsFile -Raw -ErrorAction Stop
    $data = ConvertFrom-Json $json
    $objects = @()
    foreach ($k in $data.PSObject.Properties.Name) {
      $entry = $data.$k
      $objects += [pscustomobject]@{
        Name    = $k
        Count   = [int]$entry.count
        TotalMs = [int]$entry.totalMs
        AvgMs   = [int]$entry.avgMs
        LastMs  = [int]$entry.lastMs
        LastAt  = $entry.lastAt
      }
    }
    if ($SortBy) {
      if ($Descending) { $objects = $objects | Sort-Object -Property $SortBy -Descending } else { $objects = $objects | Sort-Object -Property $SortBy }
    }
    $objects | Select-Object -First $Top | Format-Table -AutoSize
  }
  catch {
    Write-Error "Failed to read lazy stats: $($_.Exception.Message)"
  }
}

# If user opts in, append the regen status to the prompt. Enable with DOTS_REGEN_PROMPT_INTEGRATE=1
if ($env:DOTS_REGEN_PROMPT_INTEGRATE -eq '1') {
  if (Get-Command -Name 'prompt' -ErrorAction SilentlyContinue) {
    function global:prompt {
      $status = Get-DotsRegenStatus
      "$(Get-Location) [$status]> "
    }
  }
}

# winget completer is registered in the OnIdle handler so it doesn't block startup

$ChocolateyProfile = "$env:ChocolateyInstall\helpers\chocolateyProfile.psm1"
if (Test-Path($ChocolateyProfile)) {
  Import-Module "$ChocolateyProfile"
}

if (Get-Command vivid -ErrorAction SilentlyContinue) { $env:LS_COLORS = "$(vivid generate catppuccin-mocha)" }
Remove-DuplicatePaths

if ($env:isReloading) {
  Clear-Host
  wh ' ' white 'PROFILE ' gray 'RELOADED' green  -box -border black -bb 1 -ba 2 -pad $env:padding
  $env:isReloading = $false
}

function rl {
  [CmdletBinding()]
  param ()
  [bool]$env:isReloading = "$true"

  $env:isReloading = $true
  Clear-Host
  wh 'RELOADING ' darkgray ' ' white 'PROFILE' gray -box -border black -bb 1 -ba 2 -pad $env:padding
  & pwsh -NoExit -Command "Set-Location -Path $(Get-Location)'"
  exit
}

Invoke-Expression "$(vfox activate pwsh)"

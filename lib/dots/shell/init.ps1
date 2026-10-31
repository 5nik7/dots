& {
Remove-Item Env:DOTRUBY, Env:RUBYCOMP -ErrorAction Ignore
$dotsRetiredRoots = @($env:DOTS, $env:DOTS_PROFILE_CHECKOUT, (Join-Path $HOME 'dots')) | Where-Object { $_ }
$dotsRetiredPaths = @($dotsRetiredRoots | ForEach-Object { Join-Path $_ 'ruby/completion' })
$dotsWindowsPaths = [IO.Path]::DirectorySeparatorChar -eq '\'
$dotsPathComparison = if ($dotsWindowsPaths) { [StringComparison]::OrdinalIgnoreCase } else { [StringComparison]::Ordinal }
$dotsRetainedPaths = foreach ($entry in ($env:PATH -split [regex]::Escape([string][IO.Path]::PathSeparator))) {
    $retired = $false
    $normalizedEntry = if ($dotsWindowsPaths) { $entry.Replace('\', '/').TrimEnd('/') } else { $entry.TrimEnd('/') }
    foreach ($path in $dotsRetiredPaths) {
        $normalizedPath = if ($dotsWindowsPaths) { $path.Replace('\', '/').TrimEnd('/') } else { $path.TrimEnd('/') }
        if ([string]::Equals($normalizedEntry, $normalizedPath, $dotsPathComparison)) { $retired = $true }
    }
    if (-not $retired) { $entry }
}
$env:PATH = $dotsRetainedPaths -join [IO.Path]::PathSeparator
foreach ($name in @('DOTS_ENV_HOOKS','DOTS_ENV_ORIGINS')) {
    $value = [Environment]::GetEnvironmentVariable($name)
    if ($null -ne $value) { [Environment]::SetEnvironmentVariable($name, (($value -split ';' | Where-Object { $_ -and $_ -notmatch '^(DOTRUBY|RUBYCOMP)[:|]' }) -join ';'), 'Process') }
}
if (Get-Variable DotsEnvironmentApplied -Scope Global -ErrorAction Ignore) {
    [void]$global:DotsEnvironmentApplied.Remove('DOTRUBY'); [void]$global:DotsEnvironmentApplied.Remove('RUBYCOMP')
}

. (Join-Path $env:DOTS 'lib/dots/shell/debug.ps1')
Write-DotsDebugEvent begin 'lib/dots/shell/init.ps1' module
# Native Windows adapter. Shared profile/environment resolution uses Python.
$dotsEnvironmentCacheRoot = if ($env:XDG_CACHE_HOME) { $env:XDG_CACHE_HOME } elseif ($env:LOCALAPPDATA) { Join-Path $env:LOCALAPPDATA 'cache' } else { Join-Path $HOME '.cache' }
$dotsEnvironmentCache = Join-Path $dotsEnvironmentCacheRoot 'dots/startup/environment.ps1'
$dotsEnvironmentReady = $false
if (Test-Path -LiteralPath $dotsEnvironmentCache -PathType Leaf) { $dotsEnvironmentReady = . $dotsEnvironmentCache }
if (-not $dotsEnvironmentReady) {
    $dotsEnvironmentPython = Get-Command python3, python -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($dotsEnvironmentPython) {
        & $dotsEnvironmentPython.Source -B (Join-Path $env:DOTS 'lib/dots/native_startup.py') powershell $dotsEnvironmentCache
        if ($LASTEXITCODE -eq 0) { $dotsEnvironmentReady = . $dotsEnvironmentCache }
    }
    if (-not $dotsEnvironmentReady -and $global:DotsGeneratedPaths) { Write-Warning 'dots: profile environment preparation failed; previous profile environment retained'; return }
    if (-not $dotsEnvironmentReady) { Write-Warning 'dots: profile environment preparation unavailable; retaining minimal integration' }
}
$dotsSchema = @{}
$dotsValues = @{}
$dotsOrigins = @{}
foreach ($line in [IO.File]::ReadAllLines((Join-Path $env:DOTS 'lib/dots/shell/settings.tsv'))) {
    $fields = $line.Split("`t")
    $dotsSchema[$fields[0]] = $fields[1]
    $dotsValues[$fields[0]] = $fields[2]
    $dotsOrigins[$fields[0]] = 'default'
}
$dotsConfigRoot = if ($env:XDG_CONFIG_HOME) { $env:XDG_CONFIG_HOME } elseif ($IsWindows -or $env:OS -eq 'Windows_NT') { $env:APPDATA } else { Join-Path $HOME '.config' }
$dotsConfigFile = if ($env:DOTS_CONFIG_FILE) { $env:DOTS_CONFIG_FILE } else { Join-Path $dotsConfigRoot 'dots/config.env' }
$dotsValid = {
    param($kind, $value)
    switch ($kind) {
        bool { $value -cin @('0', '1') }
        style { $value -cin @('auto', 'always', 'never') }
        suggestions { $value -cin @('deja', 'autosuggestions', 'none') }
        id { $value -cmatch '^[a-z][a-z0-9_]*(-[a-z0-9_]+)*$' }
        default { $false }
    }
}
$dotsSeen = @{}
if (Test-Path -LiteralPath $dotsConfigFile) {
    foreach ($line in [IO.File]::ReadAllLines($dotsConfigFile)) {
        $line = $line.Trim()
        if (-not $line -or $line.StartsWith('#')) { continue }
        $pair = $line -split '=', 2
        $key = $pair[0].Trim()
        if ($pair.Count -ne 2 -or -not $dotsSchema.ContainsKey($key) -or $dotsSeen.ContainsKey($key) -or $key -cnotmatch '^DOTS_[A-Z_]+$') { throw 'dots: invalid setting' }
        $value = $pair[1].Trim()
        if ($value.Length -ge 2 -and ($value[0] -eq '"' -or $value[0] -eq "'") -and $value[0] -eq $value[-1]) { $value = $value.Substring(1, $value.Length - 2) }
        if (-not (& $dotsValid $dotsSchema[$key] $value)) { throw "dots: invalid $key" }
        $dotsValues[$key] = $value
        $dotsOrigins[$key] = 'config'
        $dotsSeen[$key] = $true
    }
}
if (-not $env:DOTS_CONFIG_FILE -and $dotsEnvironmentReady) {
    foreach ($key in @($global:DotsProfileSettings.Keys)) {
        $dotsValues[$key] = $global:DotsProfileSettings[$key]
        $dotsOrigins[$key] = $global:DotsProfileSettingOrigins[$key]
    }
}
foreach ($key in @($dotsSchema.Keys)) {
    $override = [Environment]::GetEnvironmentVariable($key)
    if ($override) { $dotsValues[$key] = $override; $dotsOrigins[$key] = 'environment' }
    $value = $dotsValues[$key]
    $valid = & $dotsValid $dotsSchema[$key] $value
    if (-not $valid) { throw "dots: invalid $key" }
}
$global:dots_options = $dotsValues
$global:dots_option_sources = $dotsOrigins
$global:dot = @{}
foreach ($line in [IO.File]::ReadAllLines((Join-Path $env:DOTS 'lib/dots/shell/paths.tsv'))) {
    $fields = $line.Split("`t")
    $value = if ($fields[2] -eq '.') { $env:DOTS } else { Join-Path $env:DOTS $fields[2] }
    if ($fields[0] -ne '-') { [Environment]::SetEnvironmentVariable($fields[0], $value, 'Process') }
    if ($fields[1] -ne '-') { $global:dot[$fields[1]] = $value }
}
$global:dot.config = $dotsConfigFile
if (-not $env:DOTS_CONFIG_FILE -and $dotsEnvironmentReady -and $global:DotsProfileConfigPath) {
    $global:dot.config = $global:DotsProfileConfigPath
}
$stateRoot = if ($env:XDG_STATE_HOME) { $env:XDG_STATE_HOME } elseif ($IsWindows -or $env:OS -eq 'Windows_NT') { $env:LOCALAPPDATA } else { Join-Path $HOME '.local/state' }
$global:dot.state = Join-Path $stateRoot 'dots'
$env:THEMESCMD = Join-Path $dot.bin 'theme.ps1'
$env:THEMESBIN = Join-Path $dot.state 'themes/commands/current/bin'
$entries = @($env:PATH -split [regex]::Escape([string][IO.Path]::PathSeparator) | Where-Object { $_ -cne $env:THEMESBIN -and $_ -cne (Join-Path $env:DOTS 'themes/bin') })
foreach ($directory in @($env:DOTBIN, $env:DOTSCRIPTS)) {
    if ((Test-Path -LiteralPath $directory -PathType Container) -and $entries -cnotcontains $directory) { $entries = @($directory) + $entries }
}
if ($dots_options.DOTS_INIT_COMMANDS -eq '1') { $entries += $env:THEMESBIN }
$profileEntries = @($env:DOTS_PROFILE_PATHS -split [regex]::Escape([string][IO.Path]::PathSeparator) | Where-Object { $_ })
$env:PATH = (@($profileEntries + $entries | Select-Object -Unique) -join [IO.Path]::PathSeparator)
$dotsArgs = [Environment]::GetCommandLineArgs()
$dotsInteractive = $dotsArgs -notcontains '-NonInteractive' -and ($dotsArgs -contains '-NoExit' -or -not ($dotsArgs | Where-Object { $_ -match '^-(Command|c|File|f|EncodedCommand|ec)$' }))
if ($dotsInteractive) {
    . (Join-Path $env:DOTS 'lib/dots/shell/less.ps1')
    if ($dots_options.DOTS_INIT_COLORS -eq '0') { $global:dots_colors = @{} }
    # PowerShell identifiers are case insensitive: esc/ESC and rst/RST share values.
    if ($global:esc -cne [string][char]27) { $global:esc = [string][char]27 }
    if ($global:rst -cne ([string][char]27 + '[0m')) { $global:rst = [string][char]27 + '[0m' }
    . (Join-Path $env:DOTS 'lib/dots/shell/keys.ps1')
    function global:Update-DotsTheme {
        if ($dots_options.DOTS_INIT_THEME -ne '1') {
            Update-DotsLessStyle '' '' 'auto' '0'
            return
        }
        try {
            $currentFile = Join-Path $dot.state 'themes/current'
            if (-not [IO.File]::Exists($currentFile)) { return }
            $generation = [IO.File]::ReadAllText($currentFile).Trim()
            if ($generation -eq $global:_DotsThemeGeneration -or $generation -cnotmatch '^g\.[a-zA-Z0-9]+$') { return }
            $data = @{}
            foreach ($line in [IO.File]::ReadAllLines((Join-Path $dot.state "themes/generations/$generation/shell.tsv"))) {
                $fields = $line.Split("`t")
                if ($fields.Count -ne 3 -or $fields[0] -cnotmatch '^(@theme|@palette|@role|[a-z_][a-zA-Z0-9_]*)$' -or $fields[1] -cnotmatch '^[a-zA-Z0-9_-]+$') { return }
                if (-not $data.ContainsKey($fields[0])) { $data[$fields[0]] = @{} }
                $data[$fields[0]][$fields[1]] = $fields[2]
            }
            if (-not $data['@theme']['id']) { return }
        } catch { return }
        $lessForeground = if ($data['foreground']) { $data['foreground']['hex'] } else { $data['@role']['foreground'] }
        $lessBackground = if ($data['lighter_background']) { $data['lighter_background']['hex'] } elseif ($data['background']) { $data['background']['hex'] } else { $data['@role']['background'] }
        Update-DotsLessStyle $lessForeground $lessBackground $dots_options.DOTS_COLOR '1'
        $global:dots_colors = @{}
        if ($dots_options.DOTS_INIT_COLORS -eq '1') {
            foreach ($name in $data.Keys) {
                if (-not $name.StartsWith('@')) { $global:dots_colors[$name] = $data[$name] }
            }
        }
        $global:dots_palette = $data['@palette']; $global:dots_roles = $data['@role']
        $env:THEME = $data['@theme']['family']; $env:FLAVOR = $data['@theme']['flavor']; $env:DOTS_THEME_ID = $data['@theme']['id']
        $global:dot.theme = $env:DOTS_THEME_ID
        $lsFile = Join-Path $dot.state "themes/generations/$generation/ls_colors"
        if (Test-Path -LiteralPath $lsFile -PathType Leaf) { $env:LS_COLORS = [IO.File]::ReadAllText($lsFile).TrimEnd("`r", "`n") }
        $batCache = Join-Path $dot.state "themes/generations/$generation/bat-cache"
        if (Test-Path -LiteralPath $batCache -PathType Container) {
            $env:BAT_THEME = 'Dots'
            $env:BAT_CACHE_PATH = $batCache
        }
        $visualFile = Join-Path $dot.state "themes/generations/$generation/visual.tsv"
        if (Test-Path -LiteralPath $visualFile -PathType Leaf) {
            $visualIcons = @{}; $visualColors = @{}; $visualEnv = @{}
            foreach ($line in [IO.File]::ReadAllLines($visualFile)) {
                $fields = $line.Split("`t", 3)
                if ($fields.Count -ne 3) { return }
                switch -CaseSensitive ($fields[0]) {
                    icon { $visualIcons[$fields[1]] = $fields[2] }
                    color { $visualColors[$fields[1]] = $fields[2] }
                    env {
                        if ($fields[1] -cnotmatch '^[A-Z][A-Z0-9_]*$') { return }
                        $visualEnv[$fields[1]] = $fields[2]
                    }
                    default { return }
                }
            }
            $global:DotsStyleIcons = $visualIcons; $global:DotsStyleColors = $visualColors
            foreach ($name in $visualEnv.Keys) { [Environment]::SetEnvironmentVariable($name, $visualEnv[$name], 'Process') }
            if ($visualEnv.ContainsKey('DOTS_THEME_FZF_COLORS')) {
                if ($null -eq $global:DotsVisualFzfBase) { $global:DotsVisualFzfBase = [string]$env:FZF_DEFAULT_OPTS }
                $fzfBase = $global:DotsVisualFzfBase
                if ($visualEnv.ContainsKey('DOTS_THEME_FZF_OPTS')) { $fzfBase = $visualEnv['DOTS_THEME_FZF_OPTS'] }
                $env:FZF_DEFAULT_OPTS = $fzfBase + ' --color=' + $visualEnv['DOTS_THEME_FZF_COLORS']
            }
        }
        $global:_DotsThemeGeneration = $generation
    }
    $global:_DotsThemeGeneration = $null
    Update-DotsTheme
    function global:Update-DotsCompletion {
        if ($dots_options.DOTS_INIT_COMPLETION -ne '1') { return }
        $fingerprintFile = Join-Path $dot.state 'themes/commands/current/fingerprint'
        $token = if (Test-Path -LiteralPath $fingerprintFile -PathType Leaf) { [IO.File]::ReadAllText($fingerprintFile).Trim() } else { 'none' }
        if ($token -eq $global:_DotsCommandFingerprint) { return }
        $global:_DotsCommandFingerprint = $token
        # The shared completion source has no .ps1 suffix. Windows cannot
        # dot-source extensionless files as scripts; evaluate its trusted text.
        . ([scriptblock]::Create([IO.File]::ReadAllText((Join-Path $env:DOTS 'lib/dots/completion/powershell'))))
    }
    $global:_DotsCommandFingerprint = $null
    Update-DotsCompletion
    function global:Install-DotsPrompt {
        param([scriptblock] $Renderer)
        if ($Renderer) { $global:_DotsPreviousPrompt = $Renderer }
        if (-not $global:_DotsPromptWrapper) {
            $global:_DotsPromptWrapper = {
                $previousSuccess = $?
                $previousExit = $global:LASTEXITCODE
                Update-DotsCompletion
                if ($dots_options.DOTS_THEME_AUTO_UPDATE -eq '1') { Update-DotsTheme }
                $global:LASTEXITCODE = $previousExit
                if ($previousSuccess) { $null = $true }
                else { Get-Variable '__Dots_NoSuchVariable__' -ErrorAction Ignore }
                & $global:_DotsPreviousPrompt
            }
        }
        Set-Item Function:\global:prompt $global:_DotsPromptWrapper
        $global:_DotsPromptInstalled = $true
    }
    # Terminal integration can wrap us. Refresh data without wrapping the outer
    # prompt again, which would create a cycle through our own renderer.
    if (-not $global:_DotsPromptInstalled) {
        Install-DotsPrompt -Renderer (Get-Item Function:prompt).ScriptBlock
    }
}

Write-DotsDebugEvent end 'lib/dots/shell/init.ps1' module ([int](-not $?))

}

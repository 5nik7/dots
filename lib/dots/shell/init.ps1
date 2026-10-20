& {
# Native Windows adapter: neither Bash nor Python is required.
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
$stateRoot = if ($env:XDG_STATE_HOME) { $env:XDG_STATE_HOME } elseif ($IsWindows -or $env:OS -eq 'Windows_NT') { $env:LOCALAPPDATA } else { Join-Path $HOME '.local/state' }
$global:dot.state = Join-Path $stateRoot 'dots'
$env:THEMESCMD = Join-Path $dot.bin 'theme.ps1'
$env:THEMESBIN = Join-Path $dot.state 'themes/commands/current/bin'
$entries = @($env:PATH -split [regex]::Escape([string][IO.Path]::PathSeparator) | Where-Object { $_ -cne $env:THEMESBIN -and $_ -cne (Join-Path $env:DOTS 'themes/bin') })
foreach ($directory in @($env:DOTBIN, $env:DOTSCRIPTS)) {
    if ((Test-Path -LiteralPath $directory -PathType Container) -and $entries -cnotcontains $directory) { $entries = @($directory) + $entries }
}
if ($dots_options.DOTS_INIT_COMMANDS -eq '1') { $entries += $env:THEMESBIN }
$env:PATH = $entries -join [IO.Path]::PathSeparator
$dotsArgs = [Environment]::GetCommandLineArgs()
$dotsInteractive = $dotsArgs -notcontains '-NonInteractive' -and ($dotsArgs -contains '-NoExit' -or -not ($dotsArgs | Where-Object { $_ -match '^-(Command|c|File|f|EncodedCommand|ec)$' }))
if ($dotsInteractive) {
    if ($dots_options.DOTS_INIT_COLORS -eq '0') { $global:dots_colors = @{} }
    # PowerShell identifiers are case insensitive: rst and RST are one value.
    if ($global:rst -cne ([string][char]27 + '[0m')) { $global:rst = [string][char]27 + '[0m' }
    function global:Update-DotsTheme {
        if ($dots_options.DOTS_INIT_THEME -ne '1') { return }
        try {
            $generation = [IO.File]::ReadAllText((Join-Path $dot.state 'themes/current')).Trim()
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
        . (Join-Path $env:DOTS 'lib/dots/completion/powershell')
    }
    $global:_DotsCommandFingerprint = $null
    Update-DotsCompletion
    if (-not $global:_DotsPromptInstalled -or (Get-Item Function:prompt).ScriptBlock.ToString() -notmatch 'Update-DotsTheme') {
        $global:_DotsPreviousPrompt = (Get-Item Function:prompt).ScriptBlock
        function global:prompt {
            $previousExit = $global:LASTEXITCODE
            Update-DotsCompletion
            if ($dots_options.DOTS_THEME_AUTO_UPDATE -eq '1') { Update-DotsTheme }
            $global:LASTEXITCODE = $previousExit
            & $global:_DotsPreviousPrompt
        }
        $global:_DotsPromptInstalled = $true
    }
}

}

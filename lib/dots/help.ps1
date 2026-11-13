# Static help remains usable before Python is installed. Never execute extensions.
function Write-DotsUsageLogo {
    param([string] $Root, [hashtable] $Presentation)
    $path = Join-Path $Root 'logo.txt'
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { return }
    try {
        . (Join-Path $Root 'lib/dots/files/entry.ps1')
        Invoke-DotsFiles $Root 'usage-logo' @() $Presentation
        if ($script:DotsFilesExitCode -eq 0) { [Console]::Out.WriteLine(); return }
    } catch { } # Basic help keeps the classic artwork without a Python runtime.
    $lines = [IO.File]::ReadAllLines($path)
    $mode = if ($Presentation.ContainsKey('color')) { $Presentation['color'] } elseif ($env:DOTS_COLOR) { $env:DOTS_COLOR } else { 'auto' }
    $colored = $mode -eq 'always' -or ($mode -eq 'auto' -and -not [Console]::IsOutputRedirected -and
        $env:TERM -ne 'dumb' -and $Host.UI.SupportsVirtualTerminal -and -not $env:NO_COLOR)
    $steps = [Math]::Max(1, $lines.Count - 1)
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($colored) {
            $green = 96 + [int][Math]::Floor(159 * $i / $steps)
            [Console]::Out.WriteLine(([string][char]27 + '[38;2;0;' + $green + ';255m') + $lines[$i] + ([string][char]27 + '[0m'))
        } else { [Console]::Out.WriteLine($lines[$i]) }
    }
    [Console]::Out.WriteLine()
}

function Show-DotsHelp {
    param([string] $Root, [string[]] $Route, [hashtable] $Presentation = @{})
    . (Join-Path $Root 'lib/dots/help-style.ps1')
    $preferences = Get-DotsHelpPreferences $Root
    $stem = $Route -join '-'
    if ($stem -and $stem -cnotmatch '^[a-z][a-z0-9]*(?:-[a-z][a-z0-9]*)*$') { throw 'invalid help route' }
    $files = @()
    if (-not $stem -or $stem -in @('help', 'commands', 'completion', 'init')) {
        $files += @(Get-ChildItem -LiteralPath (Join-Path $Root 'lib/dots/metadata') -Filter '*.meta' |
            Where-Object { -not $stem -or $_.BaseName -eq $stem })
    }
    foreach ($directory in @((Join-Path $Root 'bin'), (Join-Path $Root 'local/bin'))) {
        if (Test-Path -LiteralPath $directory) {
            $files += @(Get-ChildItem -LiteralPath $directory -Filter 'dots-*' -File |
                Where-Object { $_.Name -cmatch '^dots-[a-z][a-z0-9]*(?:-[a-z][a-z0-9]*)*(?:\.ps1)?$' -and
                    (-not $stem -or $_.BaseName -eq ('dots-' + $stem) -or $_.BaseName.StartsWith('dots-' + $stem + '-')) })
        }
    }
    if (-not $files.Count) { throw ('unknown command: ' + ($Route -join ' ')) }
    $commands = @($files | ForEach-Object { ($_.BaseName -replace '^dots-', '').Replace('-', ' ') })
    if (-not $stem) {
        Write-DotsUsageLogo $Root $Presentation
        if ($preferences.tagline) {
            Write-DotsHelpLine $preferences.tagline tagline $preferences $Presentation
            Write-DotsHelpLine '' description $preferences $Presentation
        }
        Write-DotsHelpLine 'Usage' heading $preferences $Presentation
        Write-DotsHelpLine '  dots [OPTIONS] COMMAND [ARGS...]' syntax $preferences $Presentation @() $commands
        Write-DotsHelpLine '' description $preferences $Presentation
        Write-DotsHelpLine 'Commands' heading $preferences $Presentation
    } else { Write-DotsHelpLine ('dots ' + ($Route -join ' ')) syntax $preferences $Presentation $Route $commands }
    $rootGroups = [ordered]@{}
    foreach ($file in $files | Sort-Object Name) {
        $name = $file.BaseName -replace '^dots-', ''
        $summary = ''; $usage = ''; $options = @(); $hidden = $false
        $reader = [IO.File]::OpenText($file.FullName)
        try {
            $count = 0; $size = 0
            while ($null -ne ($line = $reader.ReadLine())) {
                if ($line.Trim() -and -not $line.StartsWith('#')) { break }
                $count++; $size += [Text.Encoding]::UTF8.GetByteCount($line) + 1
                if ($count -gt 128 -or $size -gt 16384) { throw 'metadata header exceeds limit' }
                if ($line.StartsWith('# dots:summary=')) { $summary = $line.Substring(15) }
                elseif ($line.StartsWith('# dots:usage=')) { $usage = $line.Substring(13) }
                elseif ($line.StartsWith('# dots:option=')) { $options += $line.Substring(14) }
                elseif ($line -eq '# dots:hidden=true') { $hidden = $true }
            }
        } finally { $reader.Dispose() }
        if ($hidden -and $stem -ne $name) { continue }
        if (-not $stem) {
            $group = $name.Split('-')[0]
            if (-not $rootGroups.Contains($group)) { $rootGroups[$group] = 'Command group' }
            if ($group -eq $name) { $rootGroups[$group] = $summary }
            continue
        }
        Write-DotsHelpRow ($name.Replace('-', ' ')) $summary command $preferences $Presentation $Route $commands
        if ($stem -eq $name) {
            $syntax = @([pscustomobject]@{ Text = '  Usage: '; Role = 'heading' })
            $syntax += @(Get-DotsHelpSpans ('dots ' + ($Route -join ' ') + ' ' + $usage) syntax $Route $commands)
            Write-DotsHelpSpans $syntax $preferences $Presentation
            $optionTypes = @{}
            foreach ($option in $options) {
                $fields = $option.Split('|')
                if ($fields.Count -ne 4) { throw 'invalid option metadata' }
                foreach ($flag in @($fields[0], $fields[1])) { if ($flag) { $optionTypes[$flag] = $fields[2] -ne 'flag' } }
            }
            foreach ($option in $options) {
                $fields = $option.Split('|')
                if ($fields.Count -ne 4) { throw 'invalid option metadata' }
                Write-DotsHelpRow ($fields[0] + $(if ($fields[1]) { ', ' + $fields[1] })) $fields[3] option $preferences $Presentation $Route $commands $optionTypes
            }
        }
    }
    if (-not $stem) {
        foreach ($entry in $rootGroups.GetEnumerator()) {
            Write-DotsHelpRow $entry.Key $entry.Value command $preferences $Presentation @() $commands
        }
        Write-DotsHelpLine '' description $preferences $Presentation
        Write-DotsHelpLine 'Global options (before the command)' heading $preferences $Presentation
        $source = [IO.File]::ReadAllText((Join-Path $Root 'lib/dots/catalog.bash'))
        $table = [regex]::Match($source, '(?ms)^DOTS_GLOBAL_OPTIONS=\(\r?\n(.*?)^\)')
        if (-not $table.Success) { throw 'missing static global option metadata' }
        foreach ($line in $table.Groups[1].Value.TrimEnd().Split([char]10)) {
            $item = [regex]::Match($line, "^\s*'([^'\n]+)'\s*$")
            if (-not $item.Success) { throw 'invalid static global option metadata' }
            $fields = $item.Groups[1].Value.Split('|')
            if ($fields.Count -ne 4) { throw 'invalid static global option metadata' }
            $label = $fields[0]
            if ($fields[2] -eq 'directory') { $label += ' DIRECTORY' }
            elseif ($fields[2].StartsWith('choice:')) { $label += '=auto|always|never' }
            if ($fields[1]) { $label = $fields[1] + ', ' + $label }
            Write-DotsHelpRow $label $fields[3] option $preferences $Presentation @() $commands
        }
        Write-DotsHelpLine '' description $preferences $Presentation
        $columns = $env:COLUMNS -as [int]
        if (-not $columns) {
            try { $columns = [Console]::WindowWidth } catch { $columns = 80 }
        }
        if ($columns -le 0) { $columns = 80 }
        $columns = [Math]::Max(20, $columns)
        Write-DotsHelpLine 'Use dots help COMMAND for details; dots commands for all commands.' description $preferences $Presentation @() $commands @{} $columns
    }
}

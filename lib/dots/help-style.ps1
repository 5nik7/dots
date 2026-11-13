# Help-only spans and literal settings. No Bash, extension execution or writes.
function Get-DotsHelpPreferences {
    param([string] $Root)
    $result = @{ tagline = 'Manage your dotfiles and more...'; styles = @{
        executable = '36'; command = '34'; subcommand = '35'; option = '33'; argument = '32'
        heading = '1;96'; description = '39'; punctuation = '90'; tagline = '39'
    } }
    $python = Get-Command py, python3, python -CommandType Application -ErrorAction SilentlyContinue |
        Where-Object { $_.Source -notlike '*\Microsoft\WindowsApps\*' -and
            ([IO.Path]::GetExtension($_.Source) -eq '.exe' -or $env:OS -ne 'Windows_NT') } |
        Select-Object -First 1
    if (-not $python) { return $result }
    $prefix = @()
    if ($python.Name -eq 'py.exe' -or $python.Name -eq 'py') { $prefix = @('-3') }
    $oldDots, $oldEncoding, $oldUtf8 = $env:DOTS, $env:PYTHONIOENCODING, $env:PYTHONUTF8
    $oldConsoleEncoding = [Console]::OutputEncoding
    try {
        $env:DOTS = $Root; $env:PYTHONIOENCODING = 'utf-8'; $env:PYTHONUTF8 = '1'
        [Console]::OutputEncoding = New-Object Text.UTF8Encoding($false)
        $rows = @(& $python.Source @prefix -B (Join-Path $Root 'lib/dots/profile_config.py') '__settings')
        if ($LASTEXITCODE -ne 0) { throw 'cannot read help preferences' }
        foreach ($line in $rows) {
            $parts = ([string] $line).Split([char]9)
            if ($parts.Count -lt 2) { continue }
            if ($parts[0] -eq '__help.tagline') { $result.tagline = $parts[1] }
            elseif ($parts[0].StartsWith('__help.color.')) {
                $role = $parts[0].Substring(13)
                if ($result.styles.ContainsKey($role) -and $parts[1] -match '^[0-9;]*$') {
                    $result.styles[$role] = $parts[1]
                }
            }
        }
    } finally {
        $env:DOTS = $oldDots; $env:PYTHONIOENCODING = $oldEncoding; $env:PYTHONUTF8 = $oldUtf8
        [Console]::OutputEncoding = $oldConsoleEncoding
    }
    return $result
}

function Get-DotsHelpSpans {
    param([string] $Text, [string] $Kind = 'syntax', [string[]] $Route = @(),
          [string[]] $Commands = @(), [hashtable] $Options = @{})
    $safe = [regex]::Replace($Text, '[\x00-\x1f\x7f-\x9f]', { param($m) '\u{0:x4}' -f [int][char]$m.Value })
    if ($Kind -in @('heading', 'tagline')) {
        [pscustomobject]@{ Text = $safe; Role = $Kind }; return
    }
    $routes = @('help', 'commands', 'completion', 'init') + $Commands
    if ($Route.Count) { $routes += ($Route -join ' ') }
    $depth = 0; $reference = $false; $literal = $false; $pending = $false; $commandPath = ''
    $groups = New-Object 'System.Collections.Generic.List[object]'; $lastRole = ''
    $pattern = '(?:"(?:\\.|[^"\\])*"|''[^'']*''|\\.|[^\s\[\]{}(),|=;<>]+)|\s+|.'
    foreach ($match in [regex]::Matches($safe, $pattern)) {
        $word = $match.Value; $role = 'description'
        if ($word -match '^\s+$') { }
        elseif ($word -in @('[', ']', '{', '}', '(', ')', ',', '|', '=', ';', '<', '>')) {
            $role = 'punctuation'
            if ($word -in @('[', '{', '(')) {
                $groups.Add(@{ path = $commandPath; depth = $depth; pending = $pending; reference = $reference })
            } elseif ($word -in @(']', '}', ')') -and $groups.Count) {
                $groups.RemoveAt($groups.Count - 1); $pending = $false
            } elseif ($word -in @(',', '|')) {
                if ($groups.Count) {
                    $group = $groups[$groups.Count - 1]
                    $commandPath = $group.path; $depth = $group.depth; $pending = $group.pending; $reference = $group.reference
                } elseif ($lastRole -in @('command', 'subcommand') -and $depth -gt 0) {
                    $commandPath = $commandPath -replace '(?:^| )[^ ]+$', ''; $depth--
                }
            }
            if ($word -eq ';') { $reference = $false; $depth = 0; $commandPath = '' }
        }
        elseif ($literal) { $role = 'argument' }
        elseif ($pending -and -not $word.StartsWith('-')) {
            if ($Kind -ne 'description' -or $word -match '^[A-Z][A-Z0-9_.-]*$') { $role = 'argument' }
            $pending = $false
        }
        elseif ($word -eq 'dots' -or $word -like 'dots-*') {
            $role = 'executable'; $reference = $true; $depth = 0; $commandPath = ''; $literal = $false
        }
        elseif ($word -eq '--') { $role = 'option'; $literal = $true }
        elseif ($word -match '^--?[A-Za-z0-9][A-Za-z0-9_-]*$') {
            $role = 'option'; $pending = $Options.ContainsKey($word) -and $Options[$word]
        }
        elseif ($Kind -eq 'argument') { $role = 'argument' }
        elseif ($word -in @('OPTIONS', 'FLAGS') -or ($word -eq 'options' -and $Kind -ne 'description')) { $role = 'option' }
        elseif ($word -in @('COMMAND', 'COMMAND...', 'COMMANDS')) { $role = 'command' }
        elseif ($word -in @('SUBCOMMAND', 'SUBCOMMAND...')) { $role = 'subcommand' }
        elseif ($Kind -ne 'description' -and $word -match '^[A-Z][A-Z0-9_.-]*$') { $role = 'argument' }
        elseif ($Kind -eq 'command' -and $depth -eq 0) {
            $role = 'command'; $depth = 1; $reference = $true; $commandPath = $word
        }
        elseif ($reference) {
            $candidate = $(if ($commandPath) { $commandPath + ' ' }) + $word
            $found = $false
            foreach ($item in $routes) {
                if ($item -ceq $candidate -or $item.StartsWith($candidate + ' ', [StringComparison]::Ordinal)) { $found = $true; break }
            }
            if ($found) {
                $role = if ($depth -eq 0) { 'command' } else { 'subcommand' }; $depth++; $commandPath = $candidate
            } elseif ($Kind -eq 'description') { $reference = $false }
            else { $role = 'argument' }
        }
        elseif ($Kind -in @('syntax', 'example', 'option')) { $role = 'argument' }
        if ($role -ne 'punctuation' -and $word.Trim()) { $lastRole = $role }
        if ($word.EndsWith('...') -and $word.Length -gt 3 -and $role -ne 'description') {
            [pscustomobject]@{ Text = $word.Substring(0, $word.Length - 3); Role = $role }
            [pscustomobject]@{ Text = '...'; Role = 'punctuation' }
        } else { [pscustomobject]@{ Text = $word; Role = $role } }
    }
}

function Write-DotsHelpSpans {
    param([object[]] $Spans, [hashtable] $Preferences, [hashtable] $Presentation = @{}, [int] $Columns = 0)
    $mode = if ($Presentation.ContainsKey('color')) { $Presentation['color'] } elseif ($env:DOTS_COLOR) { $env:DOTS_COLOR } else { 'auto' }
    $terminal = -not [Console]::IsOutputRedirected -and $env:TERM -ne 'dumb' -and $Host.UI.SupportsVirtualTerminal
    $colored = $mode -eq 'always' -or ($mode -eq 'auto' -and $terminal -and -not $env:NO_COLOR)
    $text = -join @($Spans | ForEach-Object { $_.Text })
    $breaks = New-Object 'System.Collections.Generic.HashSet[int]'
    $skip = New-Object 'System.Collections.Generic.HashSet[int]'
    if ($Columns -gt 0) {
        $used = 0
        foreach ($match in [regex]::Matches($text, '\S+\s*')) {
            $size = $match.Value.TrimEnd().Length
            if ($used -gt 0 -and $used + $size -gt $Columns) {
                [void] $breaks.Add($match.Index); $used = 0
                for ($before = $match.Index - 1; $before -ge 0 -and [char]::IsWhiteSpace($text[$before]); $before--) { [void] $skip.Add($before) }
            }
            $used += $match.Length
        }
    }
    $offset = 0
    foreach ($span in $Spans) {
        $piece = ''
        for ($i = 0; $i -lt $span.Text.Length; $i++) {
            if ($skip.Contains($offset + $i)) { continue }
            if ($breaks.Contains($offset + $i)) {
                if ($piece) {
                    if ($colored -and $Preferences.styles[$span.Role]) { [Console]::Out.Write(([string][char]27 + '[' + $Preferences.styles[$span.Role] + 'm') + $piece + ([string][char]27 + '[0m')) }
                    else { [Console]::Out.Write($piece) }
                    $piece = ''
                }
                [Console]::Out.WriteLine()
            }
            $piece += $span.Text[$i]
        }
        if ($piece) {
            if ($colored -and $Preferences.styles[$span.Role] -and $piece.Trim()) { [Console]::Out.Write(([string][char]27 + '[' + $Preferences.styles[$span.Role] + 'm') + $piece + ([string][char]27 + '[0m')) }
            else { [Console]::Out.Write($piece) }
        }
        $offset += $span.Text.Length
    }
    [Console]::Out.WriteLine()
}

function Write-DotsHelpLine {
    param([string] $Text, [string] $Kind = 'description', [hashtable] $Preferences,
          [hashtable] $Presentation = @{}, [string[]] $Route = @(), [string[]] $Commands = @(),
          [hashtable] $Options = @{}, [int] $Columns = 0)
    $spans = @(Get-DotsHelpSpans $Text $Kind $Route $Commands $Options)
    Write-DotsHelpSpans $spans $Preferences $Presentation $Columns
}

function Write-DotsHelpRow {
    param([string] $Label, [string] $Description, [string] $Kind = 'syntax', [hashtable] $Preferences,
          [hashtable] $Presentation = @{}, [string[]] $Route = @(), [string[]] $Commands = @(),
          [hashtable] $Options = @{})
    $spans = @([pscustomobject]@{ Text = '  '; Role = 'description' })
    $spans += @(Get-DotsHelpSpans $Label $Kind $Route $Commands $Options)
    $spans += [pscustomobject]@{ Text = '  '; Role = 'description' }
    $spans += @(Get-DotsHelpSpans $Description 'description' $Route $Commands $Options)
    Write-DotsHelpSpans $spans $Preferences $Presentation
}

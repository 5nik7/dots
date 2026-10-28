# Native PowerShell entry point for the same core used by Bash.
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'runtime.ps1')
$script:CompletionActive = $true
$script:CompletionCache = @{}
$ExecutionContext.SessionState.Module.OnRemove = { $script:CompletionActive = $false; $script:CompletionCache.Clear() }
$script:CorePath = Join-Path (Split-Path $PSScriptRoot -Parent) 'lib/blastoff.py'
function Invoke-Blastoff {
    <#
    .SYNOPSIS
    Manage Starship themes and stored module configurations.
    .EXAMPLE
    blastoff --list
    .EXAMPLE
    blastoff module save directory compact-directory
    .NOTES
    PowerShell 7+ and native Python 3.11+; no Bash/WSL dependency on Windows.
    Native exit status is available in $LASTEXITCODE, not the parent's process code.
    Human output is default; --json requests structured output; --verbose uses stderr.
    pick/module show/backup delete --pick use fancy Unicode; --fzf requests basic.
    Ctrl-X toggles source previews; Enter selects; Escape/Ctrl-C cancels.
    Import/static completion launches no tools. See docs/POWERSHELL.md for
    root install.ps1/uninstall.ps1 -WhatIf, CurrentUser profiles and native gates.
    #>
    # Deliberately not an advanced function: preserve GNU options verbatim.
    try {
        $selection = Get-BlastoffRuntime
        $runtime = $selection.Executable; $prefix = @($selection.Prefix)
        $envelope = ConvertTo-BlastoffEnvelope -Arguments $args
        # Local preference only; expected native failures remain command statuses.
        $PSNativeCommandUseErrorActionPreference = $false
        # Scoped to this function: pre-7.2 redirected native stderr must not
        # become a terminating PowerShell error instead of the native status.
        $ErrorActionPreference='Continue'
        & $runtime @prefix -I -B $script:CorePath --_powershell-argv-v1 $envelope
        $global:LASTEXITCODE = $LASTEXITCODE
    } catch [System.Management.Automation.PipelineStoppedException] {
        $global:LASTEXITCODE = 130
    } catch {
        $global:LASTEXITCODE = 3
        [Console]::Error.WriteLine('blastoff: runtime launch failed: '+$_.Exception.Message)
    }
}
Set-Alias -Name blastoff -Value Invoke-Blastoff

# Register at import, without discovering/running Python or Starship. The wrapper
# deliberately has no declared parameters: PowerShell uses native completion for
# its unbound arguments too. -Native callbacks take THREE arguments, not the five
# arguments used by a named PowerShell parameter completer.
Register-ArgumentCompleter -Native -CommandName blastoff, Invoke-Blastoff -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)

    if (-not $script:CompletionActive) { return }
    $words = @()
    foreach ($element in $commandAst.CommandElements | Select-Object -Skip 1) {
        # Ignore the token being completed, and any tokens after the cursor.
        if ($element.Extent.EndOffset -ge $cursorPosition) { break }
        if ($element -is [System.Management.Automation.Language.StringConstantExpressionAst]) {
            $words += $element.Value
        } elseif ($element -is [System.Management.Automation.Language.CommandParameterAst]) {
            $words += $element.Extent.Text
        } else {
            # Never evaluate variables, subexpressions, or expandable strings.
            return
        }
    }
    $positionals = @()
    $pendingColor = $false
    $pendingFancy = $false
    $selection = $false
    $pickerSelection = $false
    $presentation = $null
    $literal = $false
    foreach ($word in $words) {
        if ($pendingColor) { $pendingColor = $false; continue }
        if ($pendingFancy) {
            $pendingFancy = $false
            if ($word -cin @('unicode','ascii')) { continue }
        }
        if (-not $literal) {
            if ($word -ceq '--') { $literal = $true; continue }
            if ($word -cin @('--json', '--force', '--replace-link', '-v', '--verbose', '--dry-run', '-y', '--yes')) { continue }
            if ($word -cin @('--all','--pick')) { $selection = $true; if ($word -ceq '--pick') { $pickerSelection=$true }; continue }
            if ($word -ceq '--fzf') { $presentation='fzf'; continue }
            if ($word -ceq '--fancy') { $presentation='fancy'; $pendingFancy = $true; continue }
            if ($word.StartsWith('--fancy=', [StringComparison]::Ordinal)) { $presentation='fancy'; continue }
            if ($word -ceq '--color') { $pendingColor = $true; continue }
            if ($word.StartsWith('--color=', [StringComparison]::Ordinal)) { continue }
            if ($positionals.Count -eq 0) {
                if ($word -cin @('-l', '--list', '-list')) { $positionals += 'list'; continue }
                if ($word -cin @('-t', '--theme', '-theme')) {
                    $positionals += 'theme', 'apply'; continue
                }
            }
        }
        $positionals += $word
    }
    $current = ([string]$wordToComplete).Trim("'" + '"')
    $candidates = @()
    $kind = ''
    $prefix = ''
    if ($pendingColor) {
        $candidates = @('auto', 'always', 'never')
    } elseif ($pendingFancy) {
        $candidates = @('unicode','ascii')
    } elseif (-not $literal -and $current.StartsWith('--fancy=', [StringComparison]::Ordinal)) {
        $candidates = @('--fancy=unicode','--fancy=ascii')
    } elseif (-not $literal -and $current.StartsWith('--color=', [StringComparison]::Ordinal)) {
        $candidates = @('--color=auto', '--color=always', '--color=never')
    } elseif (-not $literal -and $current.StartsWith('-')) {
        $candidates = @('-h', '--help', '--json', '--color', '--force', '--replace-link', '-v', '--verbose', '--dry-run')
        if (($positionals.Count -gt 0 -and $positionals[0] -ceq 'pick') -or ($positionals.Count -eq 2 -and ($positionals -join ':') -ceq 'module:show') -or ($positionals.Count -ge 2 -and ($positionals[0..1] -join ':') -ceq 'backup:delete' -and $pickerSelection)) { $candidates += '--fancy','--fzf' }
        if (-not $pendingFancy -and -not $pendingColor -and $positionals.Count -ge 2 -and $positionals[0] -ceq 'backup' -and $positionals[1] -ceq 'delete') { $candidates += '--pick','--all','-y','--yes' }
        if ($positionals.Count -eq 0) {
            $candidates += '--version', '-l', '--list', '-t', '--theme', '-help', '-list', '-theme'
        }
    } elseif ($positionals.Count -eq 0) {
        $candidates = @('list', 'current', 'pick', 'doctor', 'theme', 'preset', 'module', 'backup', 'migrate', 'completion')
    } elseif ($positionals.Count -eq 1) {
        switch -CaseSensitive ($positionals[0]) {
            theme { $candidates = @('list', 'apply', 'save', 'copy', 'import', 'delete', 'edit') }
            preset { $candidates = @('list', 'apply', 'save') }
            module { $candidates = @('list', 'save', 'load', 'delete', 'show') }
            backup { $candidates = @('create', 'list', 'restore', 'delete') }
            pick { $candidates = @('fancy','fzf') }
            completion { $candidates = @('bash', 'zsh', 'fish') }
        }
    } elseif ($positionals.Count -eq 2) {
        switch -CaseSensitive ($positionals -join ':') {
            { $_ -cin @('theme:apply', 'theme:copy') } {
                $kind = 'themes'
                if ($current.StartsWith('local:', [StringComparison]::Ordinal)) { $prefix = 'local:' }
                elseif ($current.StartsWith('preset:', [StringComparison]::Ordinal)) { $kind = '' }
                else { $candidates = @('local:', 'preset:') }
            }
            'theme:delete' { $kind = 'themes' }
            'backup:restore' { $kind = 'backups' }
            { $_ -cin @('module:load', 'module:delete', 'module:show') } { $kind = 'modules' }
        }
    }
    if (-not $pendingFancy -and -not $pendingColor -and $positionals.Count -ge 2 -and $positionals[0] -ceq 'backup' -and $positionals[1] -ceq 'delete' -and ($literal -or -not $current.StartsWith('-'))) {
        if (-not $pendingFancy -and -not $pendingColor -and -not $literal -and $positionals.Count -gt 2 -and $positionals[2] -ieq 'all') { $selection = $true }
        if (-not $selection) {
            $kind = 'backups'
            if (-not $literal) {
                if ($positionals.Count -eq 2) { $candidates += 'all' }
                else { $candidates += 'y','yes' }
            }
        } elseif (-not $literal) { $candidates = @('y','yes') }
    }
    if (-not $pendingFancy -and -not $pendingColor -and -not $literal -and $positionals.Count -gt 2 -and $positionals[0] -ceq 'backup' -and $positionals[1] -ceq 'delete' -and -not $current.StartsWith('-') -and $positionals[-1] -imatch '^(y|yes)$') {
        $kind = $null; $candidates = @()
    }
    # Only inspect filenames for existing-name operands. Destination names,
    # module-save routes and preset names intentionally stay free text. Backup IDs are unverified filename pairs.
    # Path operands are left to the shell; this is not config/TOML validation.
    if ($kind) {
        try {
            $root = $env:BLASTOFF_HOME
            if (-not $root) { $root = Join-Path $HOME '.config/blastoff' }
            elseif ($root -eq '~') { $root = $HOME }
            elseif ($root.StartsWith('~/') -or ($IsWindows -and $root.StartsWith('~\'))) {
                $root = Join-Path $HOME $root.Substring(2)
            }
            # Follow only storage-root aliases; child/file links stay excluded.
            # Inspect each target before following it: Tab must not probe UNC or
            # mapped network drives. Target/LinkType also work on PowerShell 7.0.
            for ($redirect = 0; ; $redirect++) {
                if (-not [IO.Path]::IsPathFullyQualified($root) -or $root -match '^[\\/]{2}') { return }
                if ($IsWindows -and ([IO.DriveInfo]::new([IO.Path]::GetPathRoot($root))).DriveType -eq 'Network') { return }
                $item = Get-Item -LiteralPath $root -Force -ErrorAction Stop
                if (-not $item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::Device)) { return }
                if (-not ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) { break }
                if ($redirect -ge 40 -or $item.LinkType -notin @('SymbolicLink', 'Junction')) { return }
                $targets = @($item.Target)
                if ($targets.Count -ne 1 -or -not $targets[0]) { return }
                $target = [string]$targets[0]
                if ($IsWindows -and ($target.StartsWith('\??\') -or $target.StartsWith('\\?\'))) {
                    $target = $target.Substring(4)
                    if ($target.StartsWith('UNC\', [StringComparison]::OrdinalIgnoreCase)) { return }
                }
                $root = [IO.Path]::GetFullPath($target, [IO.Path]::GetDirectoryName($item.FullName))
            }
            $directory = Join-Path $root $kind
            $unsafe = [IO.FileAttributes]::ReparsePoint -bor [IO.FileAttributes]::Device
            $item = Get-Item -LiteralPath $directory -Force -ErrorAction Stop
            if (-not $item.PSIsContainer -or ($item.Attributes -band $unsafe)) { return }
            $cacheKey = $directory+'|'+$item.LastWriteTimeUtc.Ticks+'|'+$item.CreationTimeUtc.Ticks
            if (-not $IsWindows -and -not $item.PSObject.Properties['UnixMode']) {
                foreach ($name in @(Get-BlastoffLegacyCompletionNames -Root $root -Kind $kind -CacheKey $cacheKey)) {
                    if ($kind -ceq 'backups' -and -not $literal -and $positionals[1] -ceq 'delete' -and $name -imatch '^(all|y|yes)$') { continue }
                    $candidates += "$prefix$name"
                }
            } else {
            $now = [DateTime]::UtcNow
            if ($script:CompletionCache.ContainsKey($cacheKey) -and ($now-$script:CompletionCache[$cacheKey].Time).TotalSeconds -lt 2) {
                $files = $script:CompletionCache[$cacheKey].Files
            } else {
                if ($script:CompletionCache.Count -ge 8) { $script:CompletionCache.Clear() }
                $files = [Collections.Generic.List[object]]::new()
                $timer = [Diagnostics.Stopwatch]::StartNew()
                foreach ($candidatePath in [IO.Directory]::EnumerateFiles($directory, '*.toml')) {
                    if ($files.Count -ge 4096 -or $timer.ElapsedMilliseconds -ge 100) { break }
                    $candidateFile = Get-Item -LiteralPath $candidatePath -Force -ErrorAction SilentlyContinue
                    if ($candidateFile) { $files.Add($candidateFile) }
                }
                $script:CompletionCache[$cacheKey] = @{Time=$now;Files=$files.ToArray()}
            }
            foreach ($file in $files) {
                if ($file.Attributes -band $unsafe) { continue }
                # Fail closed on Unix hosts lacking file-type metadata rather
                # than offer a FIFO/device as a regular stored configuration.
                if (-not $IsWindows) {
                    if (-not $file.PSObject.Properties['UnixMode'] -or $file.UnixMode -notlike '-*') { continue }
                }
                if ($file.Extension -cne '.toml') { continue }
                $name = $file.BaseName
                if ($name -cnotmatch '\A[A-Za-z0-9][A-Za-z0-9_-]{0,95}\z') { continue }
                if ($name -match '\A(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])\z') { continue }
                if ($kind -ceq 'backups') {
                    if (-not $literal -and $positionals[1] -ceq 'delete' -and $name -match '^(all|y|yes)$') { continue }
                    $paired = Get-Item -LiteralPath (Join-Path $directory ($name + '.json')) -Force -ErrorAction SilentlyContinue
                    if (-not $paired -or $paired.PSIsContainer -or ($paired.Attributes -band $unsafe)) { continue }
                    if (-not $IsWindows -and (-not $paired.PSObject.Properties['UnixMode'] -or $paired.UnixMode -notlike '-*')) { continue }
                }
                $candidates += "$prefix$name"
            }
            }
        } catch {
            # Missing/inaccessible stores are ordinary empty completion sources.
        }
    }
    if ($positionals.Count -ge 2 -and $positionals[0] -ceq 'pick' -and $positionals[1] -cin @('fancy','fzf')) { $presentation=$positionals[1] }
    foreach ($candidate in $candidates | Sort-Object -CaseSensitive -Unique) {
        if ($presentation -ceq 'fancy' -and $candidate -cin @('--fzf','fzf')) { continue }
        if ($presentation -ceq 'fzf' -and ($candidate -ceq 'fancy' -or $candidate.StartsWith('--fancy',[StringComparison]::Ordinal))) { continue }
        if ($candidate.StartsWith($current, [StringComparison]::OrdinalIgnoreCase)) {
            # Every emitted token is static or a validated portable ASCII name;
            # no user filename can inject PowerShell quoting or executable text.
            [System.Management.Automation.CompletionResult]::new($candidate, $candidate, 'ParameterValue', $candidate)
        }
    }
}
Export-ModuleMember -Function Invoke-Blastoff -Alias blastoff

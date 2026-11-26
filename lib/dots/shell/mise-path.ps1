if (Test-Path -LiteralPath $shim -PathType Container) {
    if ($env:MISE_SHELL -and $env:__MISE_ORIG_PATH) {
        $comparer = if ([IO.Path]::DirectorySeparatorChar -eq '\') { [StringComparer]::OrdinalIgnoreCase } else { [StringComparer]::Ordinal }
        $original = [Collections.Generic.HashSet[string]]::new($comparer)
        $skipped = [Collections.Generic.HashSet[string]]::new($comparer)
        $pathKey = { param([string]$Path)
            if ([IO.Path]::DirectorySeparatorChar -eq '\') { $Path = $Path.Replace('\', '/') }
            if ($Path -and $Path -notmatch '^(/+|[A-Za-z]:/+)$') { return $Path.TrimEnd('/') }
            return $Path
        }
        $key = & $pathKey $shim
        foreach ($entry in $env:__MISE_ORIG_PATH.Split([IO.Path]::PathSeparator)) {
            if ($entry) { [void]$original.Add((& $pathKey $entry)) }
        }
        foreach ($entry in ($previousProfilePaths + $profilePaths + @($env:DOTBIN, $env:DOTSCRIPTS, $env:THEMESBIN))) {
            if ($entry) { [void]$skipped.Add((& $pathKey $entry)) }
        }
        $activePath = [Collections.Generic.List[string]]::new()
        $anchor = -1
        $position = -1
        foreach ($entry in $toolPaths) {
            $entryKey = & $pathKey $entry
            if ($comparer.Equals($key, $entryKey)) {
                if ($position -lt 0) { $position = $activePath.Count }
            } else {
                if ($anchor -lt 0 -and $original.Contains($entryKey) -and -not $skipped.Contains($entryKey)) {
                    $anchor = $activePath.Count
                }
                $activePath.Add($entry)
            }
        }
        if ($position -lt 0) { $position = if ($anchor -lt 0) { $activePath.Count } else { $anchor } }
        $activePath.Insert($position, $shim)
        $env:PATH = $activePath -join [IO.Path]::PathSeparator
        $previousProfilePaths = @($previousProfilePaths | Where-Object { -not $comparer.Equals((& $pathKey $_), $key) })
    } else { $profilePaths += $shim }
}

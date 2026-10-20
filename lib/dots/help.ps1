# Static help remains usable before Python is installed. Never execute extensions.
function Show-DotsHelp {
    param([string] $Root, [string[]] $Route, [hashtable] $Presentation = @{})
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
    Write-DotsMessage $(if ($stem) { 'dots ' + ($Route -join ' ') } else { 'Dots' }) heading $Presentation
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
        Write-DotsMessage ('  ' + $name.Replace('-', ' ') + '  ' + $summary) info $Presentation
        if ($stem -eq $name) {
            Write-DotsMessage ('  Usage: dots ' + ($Route -join ' ') + ' ' + $usage) info $Presentation
            foreach ($option in $options) {
                $fields = $option.Split('|')
                if ($fields.Count -ne 4) { throw 'invalid option metadata' }
                Write-DotsMessage ('  ' + $fields[0] + $(if ($fields[1]) { ', ' + $fields[1] }) + '  ' + $fields[3]) info $Presentation
            }
        }
    }
}

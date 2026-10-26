# On-demand PSReadLine metadata; do not serialize scriptblock bodies.
if (-not (Test-Path Function:\dots) -or $global:_DotsKeysWrapper) {
    function global:dots {
        $forward = @($args)
        $route = @($forward | Where-Object { $_ -notmatch '^--(?:color|icons)=' })
        $capture = $true
        for ($i = 1; $i -lt $route.Count; $i++) {
            if ($route[$i] -in @('--query', '--mode', '--source')) {
                if ($route[$i] -eq '--source' -and $i + 1 -lt $route.Count -and $route[$i + 1] -eq 'configured') { $capture = $false }
                $i++
            } elseif ($route[$i] -in @('--source=configured', '--snapshot', '--help', '-h') -or $route[$i] -like '--snapshot=*') {
                $capture = $false
            } elseif ($route[$i] -in @('bash', 'zsh', 'tmux', 'nvim', 'yazi', 'codex', 'fzf', 'kitty', 'television')) {
                $capture = $false
            }
        }
        if ($route.Count -and $route[0] -eq 'keys' -and $capture) {
            $rows = @()
            if (Get-Command Get-PSReadLineKeyHandler -ErrorAction SilentlyContinue) {
                foreach ($binding in Get-PSReadLineKeyHandler -Bound) {
                    $rows += @{key=[string]$binding.Key; mode='Readline'; action=[string]$binding.Function;
                        description=[string]$binding.Description; scope='session'}
                }
            }
            $previous = $env:DOTS_KEYS_CAPTURE
            try {
                $env:DOTS_KEYS_CAPTURE='json'
                $OutputEncoding = [Text.UTF8Encoding]::new($false)
                $python=Get-Command python3,python -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
                if (-not $python) { throw 'Python is required for dots keys' }
                @{version=1;app='powershell';rows=$rows} | ConvertTo-Json -Depth 5 -Compress |
                    & $python.Source -B (Join-Path $env:DOTS 'lib/dots/cli.py') @forward
            } finally { $env:DOTS_KEYS_CAPTURE=$previous }
        } else {
            & (Join-Path $env:DOTS 'bin/dots.ps1') @forward
        }
    }
    $global:_DotsKeysWrapper=$true
}

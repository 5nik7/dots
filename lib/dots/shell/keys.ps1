# On-demand PSReadLine metadata; do not serialize scriptblock bodies.
if (-not (Test-Path Function:\dots) -or $global:_DotsKeysWrapper) {
    function global:dots {
        $forward = @($args)
        $route = @($forward | Where-Object { $_ -notmatch '^--(?:color|icons)=' })
        if ($route.Count -and $route[0] -eq 'keys' -and $route -notcontains '--help' -and $route -notcontains '-h') {
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

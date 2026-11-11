# Discover native engines only during setup; never load their user profiles.
function Get-DotsPowerShellProfiles {
    $scriptText = '[Console]::OutputEncoding = New-Object Text.UTF8Encoding($false); @{path=$PROFILE.CurrentUserAllHosts; version=$PSVersionTable.PSVersion.ToString()} | ConvertTo-Json -Compress'
    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($scriptText))
    $engines = @((Get-Process -Id $PID).Path)
    $engines += @(Get-Command pwsh, powershell -CommandType Application -ErrorAction SilentlyContinue | ForEach-Object { $_.Source })
    $rows = @()
    foreach ($engine in @($engines | Select-Object -Unique)) {
        $info = New-Object Diagnostics.ProcessStartInfo
        $info.FileName = $engine
        $info.Arguments = '-NoLogo -NoProfile -NonInteractive -EncodedCommand ' + $encoded
        $info.UseShellExecute = $false
        $info.CreateNoWindow = $true
        $info.RedirectStandardOutput = $true
        $info.RedirectStandardError = $true
        $info.StandardOutputEncoding = New-Object Text.UTF8Encoding($false)
        $process = [Diagnostics.Process]::Start($info)
        try {
            $output = $process.StandardOutput.ReadToEndAsync()
            $errors = $process.StandardError.ReadToEndAsync()
            if (-not $process.WaitForExit(15000)) { $process.Kill(); throw ('PowerShell profile discovery timed out: ' + $engine) }
            if ($process.ExitCode -ne 0) { throw ('PowerShell profile discovery failed: ' + $engine) }
            $row = $output.Result | ConvertFrom-Json
            if (-not [IO.Path]::IsPathRooted($row.path)) { throw 'PowerShell returned a relative profile path' }
            $rows += @{ path=[string]$row.path; version=[string]$row.version; engine=$engine }
        } finally { $process.Dispose() }
    }
    ConvertTo-Json -InputObject @($rows) -Compress
}

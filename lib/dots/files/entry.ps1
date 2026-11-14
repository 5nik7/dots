# Native adapter; all planning, backups and mutations live in the Python engine.
function Invoke-DotsFiles {
    param([string] $Root, [string] $Controller, [string[]] $CliArguments, [hashtable] $Presentation = @{}, [string] $PythonCommand = '')
    $python = if ($PythonCommand) { Get-Command -Name $PythonCommand -CommandType Application -TotalCount 1 -ErrorAction Stop } else { Get-Command py, python3, python -CommandType Application -All -ErrorAction SilentlyContinue |
        Where-Object { $_.Source -notlike '*\Microsoft\WindowsApps\*' -and
            ([IO.Path]::GetExtension($_.Source) -eq '.exe' -or $env:OS -ne 'Windows_NT') } |
        Select-Object -First 1 }
    if (-not $python) { throw 'dots setup requires Python 3.11 or newer' }
    $prefix = @()
    if ($python.Name -eq 'py.exe' -or $python.Name -eq 'py') { $prefix = @('-3') }
    $oldDots, $oldProfile = $env:DOTS, $env:DOTS_POWERSHELL_PROFILE
    $oldProfiles = $env:DOTS_POWERSHELL_PROFILES
    $oldColor, $oldIcons = $env:DOTS_COLOR, $env:DOTS_ICONS
    $oldTerm = $env:TERM
    $oldEncoding = $env:PYTHONIOENCODING
    $oldUtf8 = $env:PYTHONUTF8
    $oldShell = $env:DOTS_POWERSHELL
    $oldManagerInstall, $oldLauncherInstall = $env:PYTHON_MANAGER_AUTOMATIC_INSTALL, $env:PYLAUNCHER_ALLOW_INSTALL
    $oldLauncherAlways = $env:PYLAUNCHER_ALWAYS_INSTALL
    $oldConsoleEncoding = [Console]::OutputEncoding
    $oldOutputEncoding = $OutputEncoding
    try {
        $env:DOTS = $Root
        $env:DOTS_POWERSHELL_PROFILE = $PROFILE.CurrentUserAllHosts
        if ($env:OS -eq 'Windows_NT' -and $Controller -eq 'install' -and $CliArguments -contains 'install' -and $CliArguments -notcontains '--help' -and $CliArguments -notcontains '-h') {
            . (Join-Path $Root 'lib/dots/files/powershell_profiles.ps1')
            $env:DOTS_POWERSHELL_PROFILES = Get-DotsPowerShellProfiles
        }
        if ($Presentation.ContainsKey('color')) { $env:DOTS_COLOR = $Presentation['color'] }
        if ($Presentation.ContainsKey('icons')) { $env:DOTS_ICONS = $Presentation['icons'] }
        if (-not $env:TERM -and $Host.UI.SupportsVirtualTerminal) { $env:TERM = 'xterm-256color' }
        $env:PYTHONIOENCODING = 'utf-8'
        $env:PYTHONUTF8 = '1'
        $env:PYTHON_MANAGER_AUTOMATIC_INSTALL = 'false'; $env:PYLAUNCHER_ALLOW_INSTALL = $null; $env:PYLAUNCHER_ALWAYS_INSTALL = $null
        [Console]::OutputEncoding = New-Object Text.UTF8Encoding($false)
        $OutputEncoding = New-Object Text.UTF8Encoding($false)
        $env:DOTS_POWERSHELL = (Get-Process -Id $PID).Path
        # Only ASCII base64 crosses PowerShell's version-dependent native argv
        # conversion. Do not use stdin: selectors and confirmations own it.
        $json = ConvertTo-Json -InputObject @($CliArguments) -Compress
        $encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
        & $python.Source @prefix -B (Join-Path $Root 'lib/dots/native.py') $Controller $encoded
        $script:DotsFilesExitCode = $LASTEXITCODE
    }
    finally {
        $env:DOTS = $oldDots
        $env:DOTS_POWERSHELL_PROFILE = $oldProfile
        $env:DOTS_POWERSHELL_PROFILES = $oldProfiles
        $env:DOTS_COLOR = $oldColor
        $env:DOTS_ICONS = $oldIcons
        $env:TERM = $oldTerm
        $env:PYTHONIOENCODING = $oldEncoding
        $env:PYTHONUTF8 = $oldUtf8
        $env:DOTS_POWERSHELL = $oldShell
        $env:PYTHON_MANAGER_AUTOMATIC_INSTALL = $oldManagerInstall; $env:PYLAUNCHER_ALLOW_INSTALL = $oldLauncherInstall
        $env:PYLAUNCHER_ALWAYS_INSTALL = $oldLauncherAlways
        [Console]::OutputEncoding = $oldConsoleEncoding
        $OutputEncoding = $oldOutputEncoding
    }
}

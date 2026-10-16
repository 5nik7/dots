# Native adapter; all planning, backups and mutations live in the Python engine.
function Invoke-DotsFiles {
    param([string] $Root, [string] $Controller, [string[]] $CliArguments, [hashtable] $Presentation = @{})
    $python = Get-Command py, python3, python -CommandType Application -ErrorAction SilentlyContinue |
        Where-Object { $_.Source -notlike '*\Microsoft\WindowsApps\*' } |
        Select-Object -First 1
    if (-not $python) { throw 'dots setup requires Python 3.9 or newer' }
    $prefix = @()
    if ($python.Name -eq 'py.exe' -or $python.Name -eq 'py') { $prefix = @('-3') }
    $oldDots, $oldProfile = $env:DOTS, $env:DOTS_POWERSHELL_PROFILE
    $oldColor, $oldIcons = $env:DOTS_COLOR, $env:DOTS_ICONS
    $oldTerm = $env:TERM
    try {
        $env:DOTS = $Root
        $env:DOTS_POWERSHELL_PROFILE = $PROFILE.CurrentUserCurrentHost
        if ($Presentation.ContainsKey('color')) { $env:DOTS_COLOR = $Presentation['color'] }
        if ($Presentation.ContainsKey('icons')) { $env:DOTS_ICONS = $Presentation['icons'] }
        if (-not $env:TERM -and $Host.UI.SupportsVirtualTerminal) { $env:TERM = 'xterm-256color' }
        & $python.Source @prefix -B (Join-Path $Root "lib/dots/files/$Controller.py") @CliArguments
        $script:DotsFilesExitCode = $LASTEXITCODE
    }
    finally {
        $env:DOTS = $oldDots
        $env:DOTS_POWERSHELL_PROFILE = $oldProfile
        $env:DOTS_COLOR = $oldColor
        $env:DOTS_ICONS = $oldIcons
        $env:TERM = $oldTerm
    }
}

param([string] $StartupDirectory)

if (-not $StartupDirectory) {
    # Native filesystem resolution, including symlinked parents and junctions.
    # Startup files must find the checkout before shared helpers can be located.
    function Resolve-DotsStartupPath {
        param([string] $Path, [int] $Links = 0)
        if ($Links -gt 40) { throw 'dots: PowerShell startup symlink loop' }
        $absolute = [IO.Path]::GetFullPath($Path)
        $resolved = [IO.Path]::GetPathRoot($absolute)
        $parts = $absolute.Substring($resolved.Length).Split([IO.Path]::DirectorySeparatorChar)
        foreach ($part in $parts) {
            if (-not $part) { continue }
            $candidate = Join-Path $resolved $part
            $item = Get-Item -LiteralPath $candidate -Force -ErrorAction Stop
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
                $target = @($item.Target)[0]
                if (-not $target) { throw 'dots: unsupported PowerShell startup link' }
                if (-not [IO.Path]::IsPathRooted($target)) { $target = Join-Path $resolved $target }
                $resolved = Resolve-DotsStartupPath $target ($Links + 1)
            } else { $resolved = $candidate }
        }
        return $resolved
    }
    try {
        $dotsStartupFile = Resolve-DotsStartupPath $PSCommandPath
        $dotsStartupDirectory = Split-Path -Parent $dotsStartupFile
        $dotsStartupRoot = Split-Path -Parent (Split-Path -Parent $dotsStartupDirectory)
        if (-not (Test-Path -LiteralPath (Join-Path $dotsStartupDirectory 'environment.ps1') -PathType Leaf) -or
            -not (Test-Path -LiteralPath (Join-Path $dotsStartupRoot 'bin/dots.ps1') -PathType Leaf)) {
            throw 'dots: PowerShell startup requires the Dots checkout layout'
        }
    } finally { Remove-Item Function:\Resolve-DotsStartupPath }

} else {
    $dotsStartupDirectory = $StartupDirectory
    $dotsStartupRoot = Split-Path -Parent (Split-Path -Parent $StartupDirectory)
}
$env:DOTS = $dotsStartupRoot
Remove-Variable dotsStartupFile, dotsStartupDirectory, dotsStartupRoot, StartupDirectory -ErrorAction Ignore
. (Join-Path $env:DOTS 'lib/dots/shell/debug.ps1')
Write-DotsDebugEvent begin 'shells/powershell/environment.ps1' module
. (Join-Path $env:DOTS 'shells/powershell/environment.ps1')
Write-DotsDebugEvent end 'shells/powershell/environment.ps1' module ([int](-not $?))
$dotsLaunchArgs = [Environment]::GetCommandLineArgs()
$dotsInteractive = $dotsLaunchArgs -notcontains '-NonInteractive' -and
    ($dotsLaunchArgs -contains '-NoExit' -or
     -not ($dotsLaunchArgs | Where-Object { $_ -match '^-(Command|c|File|f|EncodedCommand|ec)$' }))
if ($dotsInteractive) {
    Write-DotsDebugEvent begin 'shells/powershell/interactive.ps1' module
    . (Join-Path $env:DOTS 'shells/powershell/interactive.ps1')
    Write-DotsDebugEvent end 'shells/powershell/interactive.ps1' module ([int](-not $?))
}

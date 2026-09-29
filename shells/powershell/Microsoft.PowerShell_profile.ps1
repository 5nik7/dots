# Native filesystem resolution, including symlinked parents and junctions.
# Kept self-contained in both entry points: helpers cannot be located yet.
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
. (Join-Path $dotsStartupDirectory 'init.ps1')

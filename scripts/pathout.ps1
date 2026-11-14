# Native adapter for the existing pathout utility. No Bash or WSL.
$source = $PSCommandPath
for ($links = 0; ; $links++) {
    $item = Get-Item -LiteralPath $source -Force -ErrorAction Stop
    if (-not $item.LinkType -or -not $item.Target) { break }
    if ($links -ge 40) { throw 'pathout: executable symlink loop' }
    $target = @($item.Target)[0]
    $source = if ([IO.Path]::IsPathRooted($target)) { $target } else {
        Join-Path (Split-Path -Parent $item.FullName) $target
    }
}
$root = Split-Path -Parent (Split-Path -Parent $item.FullName)
. (Join-Path $root 'lib/dots/utility.ps1')
Invoke-DotsUtility $root 'pathout' @($args)
exit $LASTEXITCODE

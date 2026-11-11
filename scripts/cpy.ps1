# Native clipboard entry point; resolve the launcher rather than inherited DOTS.
$source = $PSCommandPath
for ($links = 0; ; $links++) {
  $item = Get-Item -LiteralPath $source -Force -ErrorAction Stop
  if (-not $item.LinkType -or -not $item.Target) { break }
  if ($links -ge 40) { throw 'cpy: executable symlink loop' }
  $target = @($item.Target)[0]
  $source = if ([IO.Path]::IsPathRooted($target)) { $target } else {
    Join-Path (Split-Path -Parent $item.FullName) $target
  }
}
$root = Split-Path -Parent (Split-Path -Parent $item.FullName)
. (Join-Path $root 'lib/dots/clipboard.ps1')
$values = @($input | ForEach-Object { [string] $_ })
Invoke-DotsClipboard -Root $root -Command 'cpy' -CliArguments @($args) -PipelineInput $values -PipelineUsed $MyInvocation.ExpectingInput
exit $LASTEXITCODE

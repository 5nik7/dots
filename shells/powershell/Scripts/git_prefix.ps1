$gitPrefix = git rev-parse --show-prefix
if ($gitPrefix)
{
  $gitPrefix = $gitPrefix.TrimEnd('/')
}
Write-Output $gitPrefix

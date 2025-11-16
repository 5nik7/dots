# Get the remote URL (origin first, then generic)
$gitRemote = git remote get-url origin 2>$null
if (-not $gitRemote) { $gitRemote = git ls-remote --get-url 2>$null }

# Normalize to: host/user/repo   (no scheme, creds, port, or .git)
$normalized = $null
if ($gitRemote)
{
  $s = $gitRemote.Trim() -replace '\.git$', ''

  # Try standard URI (https://..., ssh://..., etc.)
  $uri = $null
  if ([Uri]::TryCreate($s, [UriKind]::Absolute, [ref]$uri))
  {
    $uriHost = $uri.Host
    $path = $uri.AbsolutePath.Trim('/')
    $normalized = ($uriHost + '/' + $path).TrimEnd('/')
  }

  # Fallback for scp-like forms: [user@]host[:port]/path or [user@]host:path
  if (-not $normalized)
  {
    if ($s -match '^(?:(?<user>.+)@)?(?<host>[^:\/]+):(?:(?<port>\d+)\/)?(?<path>.+)$')
    {
      $normalized = ($Matches['host'] + '/' + $Matches['path']).TrimEnd('/')
    }
    else
    {
      # Last resort: strip optional scheme/creds if present
      $normalized = ($s -replace '^(?:https?:\/\/)?(?:.+@)?', '').TrimEnd('/')
    }
  }
}

# Remove the last segment -> host/user
$repoBase = ''
if ($normalized)
{
  $parts = $normalized -split '/'
  $repoBase = if ($parts.Length -gt 1) { ($parts[0..($parts.Length - 2)] -join '/') } else { $normalized }
}

# Output with trailing slash (Bash echoed "$REPO_BASE/")
if ($repoBase)
{
  Write-Output ($repoBase.TrimEnd('/') + '/')
}
else
{
  Write-Output '/'
}

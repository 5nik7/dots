# Get the remote URL
$gitRemote = git remote get-url origin 2>$null
if (-not $gitRemote) { $gitRemote = git ls-remote --get-url 2>$null }

if (-not $gitRemote) {
  return
}

# Remove .git suffix and normalize
$url = $gitRemote.Trim() -replace '\\.git$', ''

# Handle scp-style: user@host:path
if ($url -match '^(?:.+@)?([^:/]+):(?:\\d+/)?(.+)$') {
  $hostname = $Matches[1]
  $path = $Matches[2]
}
# Handle standard URLs
elseif ($url -match '^(?:https?://|ssh://)?(?:.+@)?([^:/]+)(?::\\d+)?/(.+)$') {
  $hostname = $Matches[1]
  $path = $Matches[2]
}
else {
  return
}

# Remove last segment from path (repo name)
$pathParts = $path.Trim('/') -split '/'
if ($pathParts.Length -gt 1) {
  $base = $pathParts[0..($pathParts.Length - 2)] -join '/'
  Write-Output "$hostname/$base/"
}
else {
  Write-Output "$hostname/"
}

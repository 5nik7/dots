$gitRemote = git remote get-url origin 2>$null
  if ([string]::IsNullOrEmpty($gitRemote))
  {
    $gitRemote = git ls-remote --get-url 2>$null
  }

  if (-not [string]::IsNullOrEmpty($gitRemote))
  {
    $gitRemoteUrl = $gitRemote.Trim() -replace '^https?:\\/\\/(.+@)?' -replace '\\.git$' -replace '.+@(.+):(\\d+)\\/(.+)$', '$1/$3' -replace '.+@(.+):(.+)$', '$1/$2' -replace '\\/$'
    $repoName = $gitRemoteUrl -replace '.+\/([^\/]+)$', '$1'
    $repoName
  }

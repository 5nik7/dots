$gitRemote = git ls-remote --get-url
$symbol = '' # If no Git Remote is returned.
switch -regex ($gitRemote)
{
  'github' { $symbol = '' }
  'gitlab' { $symbol = '' }
  'bitbucket' { $symbol = '' }
  default { $symbol = '' }
}
Write-Host $symbol

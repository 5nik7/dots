$remote = git ls-remote --get-url 2>$null

if ($remote)
{
  $remote = $remote.ToLower()
}
switch -regex ($remote)
{
  'github' { $symbol = '󰊤' }
  'gitlab' { $symbol = '' }
  'bitbucket' { $symbol = '' }
  default { $symbol = '' }
}
if ($symbol)
{
  Write-Host $symbol -NoNewline
}

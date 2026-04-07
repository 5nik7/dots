if (git remote get-url origin 2>$null) {
  $script:want_icon = $true
}

if ($script:want_icon) {
  $icon = (git-it -i 2>$null) -replace '\s+', ''
  if ($icon) {
    Write-Host $icon
  }
}

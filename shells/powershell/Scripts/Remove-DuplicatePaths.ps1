$paths = $env:Path -split ';'
$uniquePaths = [System.Collections.Generic.HashSet[string]]::new()
$newPath = @()

foreach ($path in $paths) {
  if ($uniquePaths.Add($path)) {
    $newPath += $path
  }
  else {
    Write-Verbose "Duplicate path detected and removed: $path"
  }
}

$env:Path = $newPath -join ';'
Write-Verbose "Duplicate paths have been removed. Updated PATH: $env:Path"

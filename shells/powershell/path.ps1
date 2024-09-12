$dotbin = "$ENV:DOTS\bin"
if (Test-Path($dotbin)) {
  Add-Path -Path $dotbin
}

$scriptsPath = "$profileDirectory\Scripts"
if (Test-Path($scriptsPath)) {
  Add-Path -Path $scriptsPath
}
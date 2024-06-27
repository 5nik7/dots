$profileDirectory = [System.IO.Path]::GetDirectoryName($PROFILE)
$PSCore = "$profileDirectory\core.ps1"
if (Test-Path $PSCore) {
  Unblock-File $PSCore
  . $PSCore
}
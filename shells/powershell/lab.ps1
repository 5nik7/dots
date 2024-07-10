$env:Lab = "$env:USERPROFILE\lab"
$LabPath = $env:Lab

$PSLab = "$LabPath\PowerShell\1"
if (Test-Path($PSLab)) {
  Add-Path -Path $PSLab
}
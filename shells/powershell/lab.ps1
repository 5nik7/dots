$env:Lab  = "$env:USERPROFILE\lab"
$LabPath = $env:Lab

$PSLab = "$LabPath\PowerShell\Scripts"
if (Test-Path($PSLab)) {
  Add-Path -Path $PSLab
}
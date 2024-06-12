param($SearchFor, [switch]$Wow6432Node)
$results = @()
$keys = Get-ChildItem HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall |
ForEach-Object {
  class x64 {
    [string]$GUID
    [string]$Publisher
    [string]$DisplayName
    [string]$DisplayVersion
    [string]$InstallLocation
    [string]$InstallDate
    [string]$UninstallString
    [string]$Wow6432Node
    [string]$RegistryKeyPath
  }
  $x64 = [x64]::new()
  $x64.GUID = $_.pschildname
  $x64.Publisher = $_.GetValue('Publisher')
  $x64.DisplayName = $_.GetValue('DisplayName')
  $x64.DisplayVersion = $_.GetValue('DisplayVersion')
  $x64.InstallLocation = $_.GetValue('InstallLocation')
  $x64.InstallDate = $_.GetValue('InstallDate')
  $x64.UninstallString = $_.GetValue('UninstallString')
  $x64.RegistryKeyPath = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\$($_.pschildname)"
  if ($Wow6432Node) { $x64.Wow6432Node = 'No' }
  $results += $x64
}
if ($Wow6432Node) {
  $keys = Get-ChildItem HKLM:\SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall |
  ForEach-Object {
    class x86 {
      [string]$GUID
      [string]$Publisher
      [string]$DisplayName
      [string]$DisplayVersion
      [string]$InstallLocation
      [string]$InstallDate
      [string]$UninstallString
      [string]$Wow6432Node
      [string]$RegistryKeyPath
    }
    $x86 = [x86]::new()
    $x86.GUID = $_.pschildname
    $x86.Publisher = $_.GetValue('Publisher')
    $x86.DisplayName = $_.GetValue('DisplayName')
    $x86.DisplayVersion = $_.GetValue('DisplayVersion')
    $x86.InstallLocation = $_.GetValue('InstallLocation')
    $x86.InstallDate = $_.GetValue('InstallDate')
    $x86.UninstallString = $_.GetValue('UninstallString')
    $x86.Wow6432Node = 'Yes'
    $x86.RegistryKeyPath = "HKLM:\SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\$($_.pschildname)"
    $results += $x86
  }
}
$results | Sort-Object DisplayName | Where-Object { $_.DisplayName -match $SearchFor }
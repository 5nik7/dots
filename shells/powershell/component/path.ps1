function Get-PyenvVersion
{
  $PYVER = (Get-Content "$Env:PYENV\version") -replace '\n', ''
  return $PYVER
}
$Global:PYVER = Get-PyenvVersion
$Env:PYVER = $Global:PYVER

function PyenvExePath
{
  $PYENVBIN = (Join-Path $env:PYENV "bin")
  return $PYENVBIN
}
$Global:PYENVBIN = PyenvExePath
$Env:PYENVBIN = $Global:PYENVBIN

function Get-PyenvExeDir
{
  $PYEXEDIR = (Join-Path "$env:PYENV" "versions\$PYVER")
  return $PYEXEDIR
}
$Global:PYEXEDIR = Get-PyenvExeDir
$Env:PYEXEDIR = $Global:PYEXEDIR

function Get-PyenvScripts
{
  $PYENVSCRIPTS = (Join-Path $PYEXEDIR "Scripts")
  return $PYENVSCRIPTS
}
$Global:PYENVSCRIPTS = Get-PyenvScripts
$Env:PYENVSCRIPTS = $Global:PYENVSCRIPTS

function Get-PyenvShims
{
  $PYENVSHIMS = (Join-Path $env:PYENV "shims")
  return $PYENVSHIMS
}
$Global:PYENVSHIMS = Get-PyenvShims
$Env:PYENVSHIMS = $Global:PYENVSHIMS

function Set-Pyenv
{
  @(
    "$Env:PYENVBIN",
    "$Env:PYEXEDIR",
    "$Env:PYENVSCRIPTS",
    "$Env:PYENVSHIMS"
  ) | ForEach-Object {
    $Path = "$_"
    if ($debug)
    { Write-Host "$_" 
    }
    Remove-Path -Path "$Path"
    Add-Path -Path "$Path"
    return
  }
}

Set-Pyenv -append

$env:PSCRIPTS = "$env:PSDOT\Scripts"
$Global:PSCRIPTS = $env:PSCRIPTS
Add-Path -Path "$env:PSCRIPTS"

$env:DOTBIN = "$env:DOTS\bin"
Add-Path -Path "$env:DOTBIN"

$env:LOCALBIN = "$HOME\.local\bin"
Remove-Path -Path "$env:LOCALBIN"
Add-Path -Path "$env:LOCALBIN"

Remove-Path -Path "$Env:LOCALAPPDATA\Microsoft\WindowsApps"
Add-Path -Path "$Env:LOCALAPPDATA\Microsoft\WindowsApps"

Remove-DuplicatePaths

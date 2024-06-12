<#
.SYNOPSIS
Symbolic link a file or directory to another file or directory.

.PARAMETER base
Base directory for the symbolic link.

.PARAMETER target
Target directory for the symbolic link.
#>

param(
  [Parameter(Mandatory = $true)]
  [string]$base,

  [Parameter(Mandatory = $true)]
  [string]$target
)
$backupDir = "$env:USERPROFILE\Backups"
$arrow = "  -->  "
$bakDate = Get-Date -Format "yyyy-MM-dd_HH-mm"
$backupFileName = "$target.$bakDate.bak"

$basedir = [System.IO.Path]::GetDirectoryName($base)
$parentDir = Split-Path $basedir -Parent
if ($basedir -eq $env:DOTFILES -or $parentDir -eq $env:DOTFILES) {
  $basedircolor = "Magenta"
  $basedir = "  "
}
else {
  $basedircolor = "DarkBlue"
  $basedir = "$basedir"
}
$baseleaf = Split-Path -Path $base -Leaf

$targetdir = [System.IO.Path]::GetDirectoryName($target)
if ($targetdir -eq $env:USERPROFILE) {
  $targetdircolor = "DarkBlue"
  $targetdir = "~/"
}
else {
  $targetdircolor = "DarkBlue"
  $targetdir = "$targetdir\"
}
$tagetleaf = Split-Path -Path $target -Leaf

try {
  if ((Test-Path -Path $target) -and (Get-Item -Path $target).Target -eq $base) {
    Write-Host -ForegroundColor DarkGray "$baseleaf already linked."
  }
  elseif (Test-Path -Path $target) {
    Write-Host ''
    Write-Host -ForegroundColor Yellow "Creating a backup file: " -NoNewline
    Write-Host -ForegroundColor White $backupFileName
    Write-Host ''
    Rename-Item -Path $target -NewName $backupFileName -ErrorAction Stop | Out-Null
    Move-Item -Path $backupFileName -Destination $backupDir -ErrorAction Stop | Out-Null
    New-Item -ItemType SymbolicLink -Path $target -Target $base -ErrorAction Stop | Out-Null
    Write-Host -ForegroundColor $basedircolor "$basedir" -NoNewline
    Write-Host -ForegroundColor Cyan "$baseleaf" -NoNewline
    Write-Host -ForegroundColor DarkGray "$arrow" -NoNewline
    Write-Host -ForegroundColor $targetdircolor "$targetdir" -NoNewline
    Write-Host -ForegroundColor Cyan "$tagetleaf"
    Write-Host ''
  }
  else {
    New-Item -ItemType SymbolicLink -Path $target -Target $base -ErrorAction Stop | Out-Null
    Write-Host ''
    Write-Host -ForegroundColor $basedircolor "$basedir" -NoNewline
    Write-Host -ForegroundColor Cyan "$baseleaf" -NoNewline
    Write-Host -ForegroundColor DarkGray "$arrow" -NoNewline
    Write-Host -ForegroundColor $targetdircolor "$targetdir" -NoNewline
    Write-Host -ForegroundColor Cyan "$tagetleaf"
    Write-Host ''
  }
}
catch {
  Write-Output "Failed to create symbolic link: $_"
}
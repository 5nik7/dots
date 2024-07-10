<#
.SYNOPSIS
Symbolic link a file or directory to another file or directory.

.PARAMETER base
Base directory for the symbolic link.

.PARAMETER target
Target directory for the symbolic link.
#>

param(
  $base = (Resolve-Path $baseinput).Path,
  $target = (Resolve-Path $targetinput).Path
)

# Check and resolve the base path
# if (Test-Path $base) {
#   return
# }
# else {
#   Write-Error "Base path '$base' does not exist."
#   exit
# }

$backupDir = "$env:USERPROFILE\backups"
$arrow = "  -->  "
$bakDate = Get-Date -Format "yyyy-MM-dd_HH-mm"
# $basedir = [System.IO.Path]::GetDirectoryName($base)
$basedir = Split-Path $base -Parent
$parentDir = Split-Path $basedir -Parent
$baseleaf = Split-Path -Path $base -Leaf
$basedircolor = "DarkBlue"
$targetdir = Split-Path $target -Parent
$targetleaf = Split-Path -Path $target -Leaf
$backupFileName = "$targetleaf.$bakDate.bak"
$targetdircolor = "DarkBlue"

if ($basedir -eq $env:DOTS -or $parentDir -eq $env:DOTFILES) {
  $basedircolor = "Magenta"
  $basedir = "   "
}
else {
  $basedir = " $basedir\"
}

$targetdir = " $targetdir\"
function CreateBackup {
  if (Test-Path -Path $backupDir) {
    return
  }
  else {
    Write-Host -ForegroundColor Yellow "Creating backup directory: " -NoNewline
    New-Item -ItemType Directory -Path $backupDir -ErrorAction Stop | Out-Null
    Write-Host -ForegroundColor White "$backupDir"
  }
  Write-Host ''
  Write-Host -ForegroundColor Yellow "Creating a backup file: " -NoNewline
  Rename-Item -Path $target -NewName $backupFileName -ErrorAction Stop | Out-Null
  Move-Item -Path $backupFileName -Destination $backupDir -ErrorAction Stop | Out-Null
  Write-Host -ForegroundColor White "$backupDir\$backupFileName"
}
function CreateLink {
  New-Item -ItemType SymbolicLink -Path $target -Target $base -ErrorAction Stop | Out-Null
  Write-Host ''
  Write-Host -ForegroundColor $basedircolor "$basedir" -NoNewline
  Write-Host -ForegroundColor Cyan "$baseleaf" -NoNewline
  Write-Host -ForegroundColor DarkGray "$arrow" -NoNewline
  Write-Host -ForegroundColor $targetdircolor "$targetdir" -NoNewline
  Write-Host -ForegroundColor Cyan "$targetleaf"
  Write-Host ''
}

try {
  if ((Test-Path -Path $target) -and (Get-Item -Path $target).Target -eq $base) {
    Write-Host -ForegroundColor DarkGray "Already linked."
  }
  elseif (Test-Path -Path $target) {
    $userChoice = Read-Host "The target '$target' already exists. Overwrite? [Y/N]"
    if ($userChoice -eq 'Y') {
      CreateBackup
      CreateLink
    }
    else {
      Write-Host "Operation cancelled by the user."
      exit
    }
  }
  else {
    CreateLink
  }
}
catch {
  Write-Output "Failed to create symbolic link: $_"
}
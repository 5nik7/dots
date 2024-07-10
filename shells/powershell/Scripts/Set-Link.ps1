<#
.SYNOPSIS
Symbolic link a file or directory to another file or directory.

.PARAMETER base
Base directory for the symbolic link.

.PARAMETER target
Target directory for the symbolic link.
#>

param(
  [Parameter(Mandatory = $true, Position = 0)]
  [string] $base = (Resolve-Path $base).Path,

  [Parameter(Mandatory = $true, Position = 1)]
  [string] $target = (Resolve-Path $target).Path
)

if (-not (Test-Path -Path $base)) {
  Write-Host ''
  Write-Host " $base does not exist." -ForegroundColor Red
  exit
}

function CreateBackup {
  $backupDir = "$env:USERPROFILE\backups"
  $bakDate = Get-Date -Format "MM-dd-yyyy-HH-mm"
  $targetleaf = (Get-Item $target).Name
  $backupFileName = "$targetleaf.$bakDate.bak"
  if (!(Test-Path -Path $backupDir)) {
    Write-Host -ForegroundColor Yellow "  Creating backup directory: " -NoNewline
    New-Item -ItemType Directory -Path $backupDir -ErrorAction Stop | Out-Null
    Write-Host -ForegroundColor White "$backupDir"
  }
  Write-Host ''
  Write-Host -ForegroundColor Yellow " Backup: " -NoNewline
  Rename-Item -Path $target -NewName $backupFileName -ErrorAction Stop | Out-Null
  Move-Item -Path $backupFileName -Destination $backupDir -ErrorAction Stop | Out-Null
  Write-Host -ForegroundColor White "$backupDir\$backupFileName"
}
function CreateLink {
  New-Item -ItemType SymbolicLink -Path $target -Target ((Get-Item $base).FullName) -ErrorAction Stop | Out-Null

  $arrow = "  -->  "
  $basepath = [System.IO.Path]::GetFullPath($base)
  $basedir = [System.IO.Path]::GetDirectoryName($basepath)
  $parentDir = Split-Path $basepath -Parent
  $baseleaf = Split-Path -Path $basepath -Leaf
  $basedircolor = "DarkBlue"
  $targetpath = [System.IO.Path]::GetFullPath($target)
  $targetdir = Split-Path $targetpath -Parent
  $targetleaf = Split-Path -Path $targetpath -Leaf
  $targetdircolor = "DarkBlue"
  if ($basedir -eq $env:DOTS -or $parentDir -eq $env:DOTFILES) {
    $basedircolor = "Magenta"
    $basedir = "   "
  }
  else {
    $basedir = " $basedir\"
  }

  $targetdir = "$targetdir\"
  Write-Host ''
  Write-Host -ForegroundColor $basedircolor "$basedir" -NoNewline
  Write-Host -ForegroundColor Cyan "$baseleaf" -NoNewline
  Write-Host -ForegroundColor DarkGray "$arrow" -NoNewline
  Write-Host -ForegroundColor $targetdircolor "$targetdir" -NoNewline
  Write-Host -ForegroundColor Cyan "$targetleaf"
  Write-Host ''
}

if (!(Test-Path -Path $target)) {
  CreateLink
  exit
}

try {
  if (Test-Path -Path $target) {
    if ((Get-Item -Path $target).Target -eq ((Get-Item $base).FullName)) {
      Write-Host ''
      Write-Host -ForegroundColor DarkGray " $base and $target already linked."
      exit
    }
    else {
      Write-Host ''
      Write-Host " $((Get-Item $target).FullName) " -ForegroundColor Magenta -NoNewline
      Write-Host "already exists. " -ForegroundColor Gray
      Write-Host " Create backup file and symlink? " -ForegroundColor Cyan -NoNewline
      $userChoice = Read-Host "[Y/n]"
      if (($userChoice -eq 'Y') -or ($userChoice -eq 'y') -or ($userChoice -eq '')) {
        CreateBackup
        CreateLink
      }
      else {
        Write-Host ''
        Write-Host " Operation cancelled." -ForegroundColor Red
        Write-Host ''
        exit
      }
    }
  }
}
catch {
  Write-Output " Failed to create symbolic link: $_"
}
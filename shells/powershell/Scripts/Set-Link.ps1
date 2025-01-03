<#
.SYNOPSIS
Symbolic link a file or directory to another file or directory.

.DESCRIPTION
This command creates a symbolic link from the base directory to the target directory. If the target

.PARAMETER base
Base directory for the symbolic link.

.PARAMETER target
Target directory for the symbolic link.

.PARAMETER v
Verbose output. Display the full path of the base and target directories.

.PARAMETER i
Interactive mode. Prompt the user to overwrite the target if it already exists.
#>

param(
  [Parameter(Mandatory = $true, Position = 0)]
  [string] $base = (Resolve-Path $base).Path,

  [Parameter(Mandatory = $true, Position = 1)]
  [string] $target = (Resolve-Path $target).Path,

  [switch] $v,
  [switch] $i
)

$basedircolor = "Blue"
$baseleafcolor = "DarkGreen"
$targetdircolor = "Blue"
$targetleafcolor = "DarkCyan"
$arrowcolor = "DarkGray"
$arrow = "  -->  "
$dotcolor = "Green"
$doticon = "󰑊 "
$psdotcolor = "Cyan"
$psdoticon = " "
$devcolor = "Magenta"
$devicon = "󰵮 "
$homecolor = "Blue"
$homeicon = "~/"
$basepath = [System.IO.Path]::GetFullPath($base)
$basedir = [System.IO.Path]::GetDirectoryName($basepath)
$parentDir = Split-Path $basedir -Parent
$baseleaf = (Get-Item $basepath).Name
$targetpath = [System.IO.Path]::GetFullPath($target)
$targetdir = Split-Path $targetpath -Parent
$targetleaf = Split-Path -Path $targetpath -Leaf

$backupDir = "$env:USERPROFILE\backups"
$bakDate = Get-Date -Format "MM-dd-yyyy-HH.mm.ss"
$backupFileName = "$targetleaf.$bakDate.bak"
$backupFilePath = Join-Path -Path (Split-Path -Path $target -Parent) -ChildPath $backupFileName

if ($v) {
  $basedir = "$basedir\"
}
elseif ($basedir -eq $env:DOTFILES -or $parentDir -eq $env:DOTFILES) {
  $basedircolor = $dotcolor
  $basedir = $doticon
}
elseif ($basedir -eq $env:PSDOT) {
  $basedircolor = $psdotcolor
  $basedir = $psdoticon
}
elseif ($basedir -eq $env:USERPROFILE) {
  $basedircolor = $homecolor
  $basedir = $homeicon
}
elseif ($basedir -eq $env:DEV) {
  $basedircolor = $devcolor
  $basedir = $devicon
}
else {
  $basedir = "$basedir\"
}

if ($v) {
  $targetdir = "$targetdir\"
}
elseif ($targetdir -eq $ENV:USERPROFILE) {
  $targetdircolor = $homecolor
  $targetdir = $homeicon
}
elseif ($targetdir -eq $env:DEV) {
  $targetdircolor = $devcolor
  $targetdir = $devicon
}
else {
  $targetdir = "$targetdir\"
}

if (-not (Test-Path -Path $base)) {
  Write-Host ''
  Write-Host " $base does not exist." -ForegroundColor Red
  Write-Host ''
  exit
}

function CreateBackup {
  if (!(Test-Path -Path $backupDir)) {
    Write-Host ''
    Write-Host -ForegroundColor Green "  Creating backup directory: " -NoNewline
    New-Item -ItemType Directory -Path $backupDir -ErrorAction Stop | Out-Null
    Write-Host -ForegroundColor White "$backupDir"
  } 
  Rename-Item -Path $target -NewName $backupFileName -ErrorAction Stop | Out-Null
  Move-Item -Path $backupFilePath -Destination $backupDir -ErrorAction Stop | Out-Null
  Write-Host ''
  Write-Host -ForegroundColor DarkGray " Backup: " -NoNewline
  Write-Host -ForegroundColor White "$backupDir\$backupFileName"
  Write-Host ''
}
function CreateLink {
  New-Item -ItemType SymbolicLink -Path $target -Target ((Get-Item $base).FullName) -ErrorAction Stop | Out-Null
  Write-Host -ForegroundColor $basedircolor " $basedir" -NoNewline
  Write-Host -ForegroundColor $baseleafcolor "$baseleaf" -NoNewline
  Write-Host -ForegroundColor $arrowcolor "$arrow" -NoNewline
  Write-Host -ForegroundColor $targetdircolor "$targetdir" -NoNewline
  Write-Host -ForegroundColor $targetleafcolor "$targetleaf"
  Write-Host ''
}

if (!(Test-Path -Path $target)) {
  Write-Host ''
  CreateLink
  exit
}

try {
  if (Test-Path -Path $target) {
    if ((Get-Item -Path $target).Target -eq ((Get-Item $base).FullName)) {
      Write-Host -ForegroundColor DarkGray " $basedir$baseleaf = $targetdir$targetleaf"
      exit
    }
    else {
      if ($i) {
        Write-Host ''
        Write-Host " $((Get-Item $target).FullName) " -ForegroundColor Magenta -NoNewline
        Write-Host "already exists. " -ForegroundColor Gray
        Write-Host " Overwrite? " -ForegroundColor Cyan -NoNewline
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
      else {
        CreateBackup
        CreateLink
      }
    }
  }
}
catch {
  Write-Output " Failed to create symbolic link: $_"
}
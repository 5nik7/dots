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
$devicon = " "
$homecolor = "Blue"
$homeicon = "~/"
$basepath = [System.IO.Path]::GetFullPath($base)
$basedir = [System.IO.Path]::GetDirectoryName($basepath)
$parentDir = Split-Path $basedir -Parent
$baseleaf = (Get-Item $basepath).Name
$targetpath = [System.IO.Path]::GetFullPath($target)
$targetdir = Split-Path $targetpath -Parent
$targetleaf = Split-Path -Path $targetpath -Leaf

# $backupDir = "$env:USERPROFILE\backups"
# $bakDate = Get-Date -Format "MM-dd-yyyy-HH.mm.ss"
# $backupFileName = "$targetleaf.$bakDate.bak"
# $backupFilePath = Join-Path -Path (Split-Path -Path $target -Parent) -ChildPath $backupFileName

if ($basedir -eq "C:\") {
    $basedir = "$basedir"
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

if ($basedir -eq "C:\") {
    $basedir = "$basedir"
}
elseif ($targetdir -eq $env:DOTFILES -or $parentDir -eq $env:DOTFILES) {
    $targetdircolor = $dotcolor
    $targetdir = $doticon
}
elseif ($targetdir -eq $env:PSDOT) {
    $targetdircolor = $psdotcolor
    $targetdir = $psdoticon
}
elseif ($targetdir -eq $env:USERPROFILE) {
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
    Write-Warn "$base does not exist."
    exit
}
if ($base -eq $target) {
    Write-Warn "You can't SymLink a file to itself."
    exit
}

function CreateBackup {
    param (
        [string]$target = $target
    )
    New-Backup -target $target
}
function CreateLink {
    New-Item -ItemType SymbolicLink -Path $target -Target ((Get-Item $base).FullName) -ErrorAction Stop | Out-Null
    Write-Color $basedircolor " $basedir" -inline
    Write-Color $baseleafcolor "$baseleaf" -inline
    Write-Color $arrowcolor "$arrow" -inline
    Write-Color $targetdircolor "$targetdir" -inline
    Write-Color $targetleafcolor "$targetleaf"
    linebreak
}

if (!(Test-Path -Path $target)) {
    linebreak
    CreateLink
    exit
}

try {
    if (Test-Path -Path $target) {
        if ((Get-Item -Path $target).Target -eq ((Get-Item $base).FullName)) {
            Write-Color DarkGray " $basedir$baseleaf = $targetdir$targetleaf"
            exit
        }
        else {
            if ($i) {
                linebreak
                Write-Color Magenta " $((Get-Item $target).FullName) " -inline
                Write-Color Gray "already exists. "
                Write-Color Cyan " Overwrite? " -inline
                $userChoice = Read-Host "[Y/n]"
                if (($userChoice -eq 'Y') -or ($userChoice -eq 'y') -or ($userChoice -eq '')) {
                    CreateBackup
                    CreateLink
                }
                else {
                    Write-Info " Operation cancelled."
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
    Write-Err " Failed to create symbolic link: $_"
}

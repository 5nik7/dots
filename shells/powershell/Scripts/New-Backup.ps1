<#
.SYNOPSIS
        Creates a backup of the target file.
.DESCRIPTION
        Creates a backup of the target file.
.PARAMETER target
        Specifies the target to backup.
.EXAMPLE
        PS> New-Backup -target" $env:USERPROFILE\Documents\file.txt"
.NOTES
        Author: njen
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$target
)

if (-not $target) {
    Write-Error "Usage: New-Backup -target <path_to_target_file>"
    return
}

if (!(Test-Path $target)) {
    Write-Err | Write-Color White "$target does not exist,"
    return
}

$targetpath = [System.IO.Path]::GetFullPath($target)
$targetleaf = Split-Path -Path $targetpath -Leaf
if ($env:BACKUPS) {
    $backupDir = "$env:BACKUPS"
}
else {
    $backupDir = "$env:USERPROFILE\backups"
}
$backupParent = Split-Path -Path $backupDir -Parent
$backupFolder = Split-Path -Path $backupDir -Leaf
$bakDate = Get-Date -Format "MM-dd-yyyy-HH.mm.ss"
$backupFileName = "$targetleaf.$bakDate.bak"
$backupFilePath = Join-Path -Path (Split-Path -Path $target -Parent) -ChildPath $backupFileName

if (!(Test-Path -Path $backupDir)) {
    linebreak
    Write-Color Green " Creating backup directory: " -inline
    New-Item -Path $backupDir -ItemType Directory -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Path $backupDir -ErrorAction Stop | Out-Null
    Write-Color DarkBlue " $backupParent\" -inline
    Write-Color Blue "$backupFolder"
    linebreak
}
Rename-Item -Path $target -NewName $backupFileName -ErrorAction Stop | Out-Null
Move-Item -Path $backupFilePath -Destination $backupDir -ErrorAction Stop | Out-Null
linebreak
Write-Color DarkBlue "  $backupParent\" -inline
Write-Color Blue "$backupFolder\" -inline
Write-Color White "$targetleaf" -inline
Write-Color DarkGray ".$bakDate.bak"
linebreak

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

try {
  if ((Test-Path -Path $target) -and (Get-Item -Path $target).Target -eq $base) {
    Write-Host ''
    Write-Host -ForegroundColor Yellow "Already a symlink."
    Write-Host ''
  }
  elseif (Test-Path -Path $target) {
    $bakDate = Get-Date -Format "yyyy-MM-dd_HH-mm"
    $backupFileName = "$target.$bakDate.bak"
    Rename-Item -Path $target -NewName $backupFileName -ErrorAction Stop | Out-Null
    Write-Host ''
    Write-Host -ForegroundColor Yellow "Creating a backup file: " -NoNewline
    Write-Host -ForegroundColor White $backupFileName
    Write-Host ''
    New-Item -ItemType SymbolicLink -Path $target -Target $base -ErrorAction Stop | Out-Null
    Write-Host -ForegroundColor DarkCyan "$base" -NoNewline
    Write-Host -ForegroundColor DarkGray " 󱦰 " -NoNewline
    Write-Host -ForegroundColor DarkBlue "$target"
    Write-Host ''
  }
  else {
    New-Item -ItemType SymbolicLink -Path $target -Target $base -ErrorAction Stop | Out-Null
    Write-Host ''
    Write-Host -ForegroundColor DarkCyan "$base" -NoNewline
    Write-Host -ForegroundColor DarkGray " 󱦰 " -NoNewline
    Write-Host -ForegroundColor DarkBlue "$target"
    Write-Host ''
  }
}
catch {
  Write-Output "Failed to create symbolic link: $_"
}
$modulePath = $PSScriptRoot

$env:HOME = $env:USERPROFILE
$Global:DOTS = Join-Path -Path $env:USERPROFILE -ChildPath "dots"
$env:DOTS = $Global:DOTS
$Global:DOTFILES = Join-Path -Path $env:DOTS -ChildPath "configs"
$env:DOTFILES = $Global:DOTFILES
$Global:SHELLS = Join-Path -Path $env:DOTS -ChildPath "shells"
$env:SHELLS = $Global:SHELLS

$Global:PSDOTS = Join-Path -Path $env:SHELLS -ChildPath "powershell"
$env:PSDOTS = $Global:PSDOTS
$Global:PSCOMPONENT = Join-Path -Path $env:PSDOTS -ChildPath "component"
$env:PSCOMPONENT = $Global:PSCOMPONENT
$Global:PSCRIPTS = Join-Path -Path $env:PSDOTS -ChildPath "Scripts"
$env:PSCRIPTS = $Global:PSCRIPTS
$Global:PSMODS = Join-Path -Path $env:PSDOTS -ChildPath "Modules"
$env:PSMODS = $Global:PSMODS

$Global:DOTCACHE = Join-Path -Path $env:DOTS -ChildPath "cache"
$env:DOTCACHE = $Global:DOTCACHE
$Global:DOTBIN = Join-Path -Path $env:DOTS -ChildPath "bin"
$env:DOTBIN = $Global:DOTBIN

$Global:WALLS = Join-Path -Path $env:DOTS -ChildPath "walls"
$env:WALLS = $Global:WALLS

$Global:BASHDOT = Join-Path -Path $env:SHELLS -ChildPath "bash"
$env:BASHDOT = $Global:BASHDOT
$Global:ZSHDOT = Join-Path -Path $env:SHELLS -ChildPath "zsh"
$env:ZSHDOT = $Global:ZSHDOT

$util = @{
  colors = @{
    Black       = 0
    DarkRed     = 1
    DarkGreen   = 2
    DarkYellow  = 3
    DarkBlue    = 4
    DarkMagenta = 5
    DarkCyan    = 6
    Gray        = 7
    DarkGray    = 8
    Red         = 9
    Green       = 10
    Yellow      = 11
    Blue        = 12
    Magenta     = 13
    Cyan        = 14
    White       = 15
  }
  alerts = @{
    info    = @{
      text  = 'Info'
      icon  = ' '
      color = 'cyan'
    }
    success = @{
      text  = 'Success'
      icon  = ' '
      color = 'green'
    }
    warn    = @{
      text  = 'Warning'
      icon  = ' '
      color = 'yellow'
    }
    err     = @{
      text  = 'Error'
      icon  = ' '
      color = 'red'
    }
  }
}
$spacer = ' │ '
$successcolor = $($util.alerts.success.color)
$successicon = $($util.alerts.success.icon)
$successtext = $($util.alerts.success.text)
$errcolor = $($util.alerts.err.color)
$erricon = $($util.alerts.err.icon)
$errtext = $($util.alerts.err.text)
$warncolor = $($util.alerts.warn.color)
$warnicon = $($util.alerts.warn.icon)
$warntext = $($util.alerts.warn.text)
$infocolor = $($util.alerts.info.color)
$infoicon = $($util.alerts.info.icon)
$infotext = $($util.alerts.info.text)

function linebreak {
  param (
    [int]$count = 1
  )
  for ($i = 0; $i -lt $count; $i++) {
    Write-Host ''
  }
}

function Write-Info {
  param(
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$pairs,
    [int]$bb = 1,
    [int]$ba = 1,
    [int]$pad,
    [switch]$box,
    [string]$border = 'DarkGray'
  )
  if (!($box)) {
    $spacer = ': '
  }
  $pairs = @($infoicon, $infocolor, $infotext, $infocolor, $spacer, $border) + $pairs
  wh -pairs $pairs -bb $bb -ba $ba -pad $env:padding -box:$box -border:$border
}

function Write-Success {
  param(
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$pairs,
    [int]$bb = 1,
    [int]$ba = 1,
    [int]$pad,
    [switch]$box,
    [string]$border = 'DarkGray'
  )
  if (!($box)) {
    $spacer = ': '
  }
  $pairs = @($successicon, $successcolor, $successtext, $successcolor, $spacer, $border) + $pairs
  wh -pairs $pairs -bb $bb -ba $ba -pad $env:padding -box:$box -border:$border
}

function Write-Err {
  param(
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$pairs,
    [int]$bb = 1,
    [int]$ba = 1,
    [int]$pad,
    [switch]$box,
    [string]$border = 'DarkGray'
  )
  if (!($box)) {
    $spacer = ': '
  }
  $pairs = @($erricon, $errcolor, $errtext, $errcolor, $spacer, $border) + $pairs
  wh -pairs $pairs -bb $bb -ba $ba -pad $env:padding -box:$box -border:$border
}

function Write-Warn {
  param(
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$pairs,
    [int]$bb = 1,
    [int]$ba = 1,
    [int]$pad,
    [switch]$box,
    [string]$border = 'DarkGray'
  )
  if (!($box)) {
    $spacer = ': '
  }
  $pairs = @($warnicon, $warncolor, $warntext, $warncolor, $spacer, $border) + $pairs
  wh -pairs $pairs -bb $bb -ba $ba -pad $env:padding -box:$box -border:$border
}



function Join-Profile {
  <#
    .SYNOPSIS
        Sets up PowerShell profile links.
    .DESCRIPTION
        This function sets up symbolic links for PowerShell profiles to a specified profile script.
    .PARAMETER i
        Interactive mode. Prompts the user before overwriting existing links.
    .EXAMPLE
        Join-Profile -i
        # This will set up the profile links interactively.
    .NOTES
        Author: njen
        Version: 1.0.0
    #>
  param(
    [switch] $i
  )
  $Global:PSDOTPROFILE = "$env:PSDOTS\Microsoft.PowerShell_profile.ps1"
  $env:PSDOTPROFILE = $Global:PSDOTPROFILE
  $ProfileTargets = ('Microsoft.PowerShell_profile.ps1', 'Microsoft.VSCode_profile.ps1')
  $ProfileDocVersions = ('PowerShell', 'WindowsPowerShell')

  linebreak
  Write-Host ' Setting up PowerShell Profile links...' -ForegroundColor Cyan
  foreach ( $ProfileDocVersions in $ProfileDocVersions) {
    foreach ( $ProfileTarget in $ProfileTargets ) {
      Set-Link $PSDOTPROFILE "$env:DOCUMENTS\$ProfileDocVersions\$ProfileTargets"
    }
  }
  linebreak
}

function New-Backup {
  <#
    .SYNOPSIS
        Creates a backup of the target file.
    .DESCRIPTION
        This function creates a backup of the specified target file. The backup file is named with the current date and time.
    .PARAMETER target
        Specifies the target file to backup.
    .PARAMETER copy
        If specified, the target file will be copied instead of renamed.
    .EXAMPLE
        New-Backup -target "$env:USERPROFILE\Documents\file.txt"
        # This will create a backup of the specified file.
    .NOTES
        Author: njen
        Version: 1.0.1
    #>
  param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string] $target,

    [switch] $copy
  )

  if (!(Test-Path $target)) {
    Write-Error "$target does not exist."
    return
  }

  $targetpath = [System.IO.Path]::GetFullPath("$target")
  $targetleaf = Split-Path -Path $targetpath -Leaf
  $backupDir = Join-Path -Path $env:USERPROFILE -ChildPath "backups"
  $bakDate = Get-Date -Format 'MM-dd-yyyy-HH.mm.ss'
  $backupFileName = "$targetleaf.$bakDate.bak"
  $backupFilePath = Join-Path -Path $backupDir -ChildPath $backupFileName

  if (!(Test-Path -Path $backupDir)) {
    New-Item -ItemType Directory -Path $backupDir -ErrorAction Stop | Out-Null
  }

  if ($copy) {
    Copy-Item -Path $target -Destination $backupFilePath -ErrorAction Stop | Out-Null
  }
  else {
    Rename-Item -Path $target -NewName $backupFileName -ErrorAction Stop | Out-Null
    Move-Item -Path $backupFileName -Destination $backupDir -ErrorAction Stop | Out-Null
  }

  Write-Host "Backup created: $backupFilePath"
}

function Set-Link {
  <#
    .SYNOPSIS
        Creates a symbolic link from a source file or directory to a target location.

    .DESCRIPTION
        This function creates a symbolic link at the specified target path, pointing to the specified base (source) file or directory.
        If the target already exists, it can prompt the user for confirmation (interactive mode) and will create a backup of the existing target before replacing it.
        Supports force mode to overwrite without prompting.

    .PARAMETER base
        The source file or directory to link from.

    .PARAMETER target
        The destination path where the symbolic link will be created.

    .PARAMETER i
        Interactive mode. Prompts the user before overwriting or backing up an existing target.

    .PARAMETER force
        Forces the creation of the symbolic link, overwriting the target if it exists, without prompting.

    .EXAMPLE
        Set-Link -base "$env:DOTFILES\profile.ps1" -target "$env:USERPROFILE\Documents\PowerShell\Microsoft.PowerShell_profile.ps1" -i

        Prompts before overwriting and creates a backup if the target exists, then creates a symbolic link.

    .EXAMPLE
        Set-Link -base "C:\source\file.txt" -target "C:\dest\file.txt" -force

        Overwrites the target without prompting and creates a symbolic link.

    .NOTES
        Author: njen
        Version: 1.0.1
 #>
  param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string] $base,

    [Parameter(Mandatory = $true, Position = 1)]
    [string] $target,

    [switch] $i,
    [Alias('f')]
    [switch] $force
  )

  if (!(Test-Path -Path $base)) {
    Write-Warning "$base does not exist."
    return
  }
  if ($base -eq $target) {
    Write-Warning "You can't SymLink a file to itself."
    return
  }

  if (Test-Path -Path $target) {
    if ($i) {
      $userChoice = Read-Host "Target exists. Create backup? [Y/n]"
      if ($userChoice -eq 'n') {
        Write-Warning "Operation cancelled."
        return
      }
      New-Backup -target $target
    }
    elseif ($force) {
      New-Backup -target $target
    }
  }

  New-Item -ItemType SymbolicLink -Path $target -Target $base -Force:$force -ErrorAction Stop | Out-Null
  Write-Host "Symbolic link created: $target -> $base"
}

function Show-DotsUsage {
  <#
    .SYNOPSIS
        Sets up symbolic links for specified files or directories.
    .DESCRIPTION
        This function displays a help message with usage information for the Dots module.
    .NOTES
        Author: njen
        Version: 1.0.0
    #>
  $bannerPath = Join-Path -Path $modulePath -ChildPath 'banner'
  if (Test-Path -Path $bannerPath) {
    linebreak 2
    Get-Content -Path $bannerPath | Write-Host
  }
  else {
    linebreak 2
    Write-Host -foregroundColor Yellow ' DOTS'
  }
  linebreak
  Write-Host -foregroundColor DarkMagenta ' Dotfiles utility for PowerShell.'
  linebreak
  Write-Host ' Usage: dots [options]'
  linebreak
  Write-Host -foregroundColor Yellow "`t-help: " -NoNewline
  Write-Host 'Display this help message.'
  linebreak 2

}

function Invoke-Dots {
  <#
    .SYNOPSIS
        Sets up PowerShell profile links.
    .DESCRIPTION
        This function sets up symbolic links for PowerShell profiles to a specified profile script.
    .PARAMETER help
        Displays usage information for the dots command when specified.
    .EXAMPLE
        dots -help
        # This will display the usage information for the dots command.
    .NOTES
        Author: njen
        Version: 1.0.0
    #>
  param(
    [switch] $help
  )
  if ($help) {
    Show-DotsUsage
    return
  }
  else {
    Show-DotsUsage
  }

}

Export-ModuleMember -Function linebreak
Export-ModuleMember -Function wh
Export-ModuleMember -Function Write-Err
Export-ModuleMember -Function Write-Info
Export-ModuleMember -Function Write-Success
Export-ModuleMember -Function Write-Warn
Export-ModuleMember -Function Join-Profile
Export-ModuleMember -Function New-Backup
Export-ModuleMember -Function Set-Link
Export-ModuleMember -Function Invoke-Dots
New-Alias -Name dots -Scope Global -Value Invoke-Dots -ErrorAction Ignore

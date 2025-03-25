$PadddingOutSpaces = 4
$PadddingOut = " " * $PadddingOutSpaces

function linebreak {
    param (
        [int]$count = 1
    )
    for ($i = 0; $i -lt $count; $i++) {
        Write-Host ''
    }
}

$modulePath = $PSScriptRoot

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
    $env:PSDOTPROFILE = "$env:PSDOTS\profile.ps1"
    $Global:PSDOTPROFILE = $env:PSDOTPROFILE
    $ProfileTargets = ("Microsoft.PowerShell_profile.ps1", "Microsoft.VSCode_profile.ps1")
    $ProfileDocVersions = ("PowerShell", "WindowsPowerShell")

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
        Version: 1.0.0
    #>
    param(
        [Parameter(Mandatory = $true, Position = 0)]
        [string] $target,

        [switch] $copy
    )

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
    $copyFileName = "$target.$bakDate.bak"
    $backupFileName = "$targetleaf.$bakDate.bak"
    $backupFilePath = Join-Path -Path (Split-Path -Path $target -Parent) -ChildPath $backupFileName

    if (!(Test-Path -Path $backupDir)) {
        linebreak
        Write-Color Green " Creating backup directory: " -inline
        New-Item -ItemType Directory -Path $backupDir -ErrorAction Stop | Out-Null
        Write-Color DarkBlue " $backupParent\" -inline
        Write-Color Blue "$backupFolder"
        linebreak
    }

    if ($copy) {
        Copy-Item -Path $target -Destination $copyFileName -ErrorAction Stop | Out-Null
        Move-Item -Path $copyFileName -Destination $backupDir -ErrorAction Stop | Out-Null

    }
    else {
        Rename-Item -Path $target -NewName $backupFileName -ErrorAction Stop | Out-Null
        Move-Item -Path $backupFilePath -Destination $backupDir -ErrorAction Stop | Out-Null
    }
    linebreak
    Write-Color DarkBlue "$PadddingOut  $backupParent\" -inline
    Write-Color Blue "$backupFolder\" -inline
    Write-Color DarkYellow "  " -inline
    Write-Color White "$targetleaf" -inline
    Write-Color DarkGray ".$bakDate.bak"
    linebreak
    return
}

function Set-Link {
    <#
    .SYNOPSIS
        Creates a backup of the target file.
    .DESCRIPTION
        This command creates a symbolic link from the base directory to the target directory. If the target is already present, it may prompt for confirmation depending on the interactive mode setting. This override will prevent accidental data loss.
    .PARAMETER base
        Base directory for the symbolic link.
    .PARAMETER target
        Target directory for the symbolic link.
    .PARAMETER i
        Interactive mode. Prompt the user to overwrite the target if it already exists.
    .NOTES
        Author: njen
        Version: 1.0.0
 #>
    param(
        [Parameter(Mandatory = $true, Position = 0)]
        [string] $base,

        [Parameter(Mandatory = $true, Position = 1)]
        [string] $target,

        [switch] $i
    )

    if (-not (Test-Path -Path $base)) {
        Write-Warn "$base does not exist."
        return
    }
    if ($base -eq $target) {
        Write-Warn "You can't SymLink a file to itself."
        return
    }

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

    if ($basedir -eq "C:\") {
        $basedir = "$basedir"
    }
    elseif ($basedir -eq $env:DOTFILES -or $parentDir -eq $env:DOTFILES) {
        $basedircolor = $dotcolor
        $basedir = $doticon
    }
    elseif ($basedir -eq $env:PSDOTS) {
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
    elseif ($targetdir -eq $env:PSDOTS) {
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

    $symlinker = {
        New-Item -ItemType SymbolicLink -Path $target -Target ((Get-Item $base).FullName) -ErrorAction Stop | Out-Null
        Write-Color $basedircolor "$PadddingOut $basedir" -inline
        Write-Color $baseleafcolor "$baseleaf" -inline
        Write-Color $arrowcolor "$arrow" -inline
        Write-Color $targetdircolor "$targetdir" -inline
        Write-Color $targetleafcolor "$targetleaf"
    }

    if (Test-Path -Path $target) {
        if ((Get-Item -Path $target).Target -eq ((Get-Item $base).FullName)) {
            Write-Info "$basedir$baseleaf = $targetdir$targetleaf"
            return
        }
        if ($i -and (Test-Path $target)) {
            linebreak
            Write-Color Magenta "$PadddingOut $((Get-Item $target).FullName) " -inline
            Write-Color Gray "already exists. "
            Write-Color Cyan "$PadddingOut Create backup? " -inline
            $userChoice = Read-Host "[Y/n]"
            if ($userChoice -eq "n") {
                Write-Warn "Operation cancelled."
                return
            }
        }
        New-Backup -target $target
    }
    if ($i) {
        linebreak
        Write-Color Cyan "$PadddingOut Create SymLink? " -inline
        $userChoice = Read-Host "[Y/n]"
        if ($userChoice -eq "n") {
            Write-Warn "Operation cancelled."
            return
        }
    }
    linebreak
    &$symlinker
    linebreak
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
    $bannerPath = Join-Path -Path $modulePath -ChildPath "banner"
    if (Test-Path -Path $bannerPath) {
        linebreak 2
        Get-Content -Path $bannerPath | Write-Host
    }
    else {
        linebreak 2
        Write-Host -foregroundColor Yellow " DOTS"
    }
    linebreak
    Write-Host -foregroundColor DarkMagenta " Dotfiles utility for PowerShell."
    linebreak
    Write-Host " Usage: dots [options]"
    linebreak
    Write-Host -foregroundColor Yellow "`t-help: " -NoNewline
    Write-Host "Display this help message."
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

Export-ModuleMember -Function Join-Profile
Export-ModuleMember -Function New-Backup
Export-ModuleMember -Function Set-Link
Export-ModuleMember -Function Invoke-Dots
New-Alias -Name dots -Scope Global -Value Invoke-Dots -ErrorAction Ignore

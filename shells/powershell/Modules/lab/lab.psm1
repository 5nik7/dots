function linebreak {
    param (
        [int]$count = 1
    )
    for ($i = 0; $i -lt $count; $i++) {
        Write-Host ''
    }
}
$modulePath = $PSScriptRoot

$actioncolor = 'White'
$pslabsymbol = (nf cod-terminal_powershell)
$dircolor = 'DarkGray'

$arrowcolor = 'DarkGray'
$arrow = " --> "

$labsymbol = (nf md-flask_outline)
$labsymbolcolor = 'Cyan'
$labscriptcolor = 'White'
$pscriptscolor = 'Blue'

if ($env:LAB) {
    $Global:LAB = $env:LAB
}
else {
    $env:LAB = "$env:DEV\lab"
    $Global:LAB = $env:LAB
}

$env:LAB = "$env:DEV\lab"
$Global:LAB = $env:LAB

$env:PSLAB = "$LAB\PowerShell"
$Global:PSLAB = $env:PSLAB

if (Test-Path($PSLAB)) {
    Add-Path -Path $PSLAB
}

function Get-LabUsage {
    $bannerPath = Join-Path -Path $modulePath -ChildPath "banner"
    if (Test-Path -Path $bannerPath) {
        linebreak 2
        Get-Content -Path $bannerPath | Write-Host
    }
    else {
        linebreak 2
        Write-Host -foregroundColor Cyan " LAB"
    }
    linebreak
    Write-Output @"
 Usage: lab [-new] [-edit] [-tested] [-delete] [-filename <string>] [-list] [-help]

    -new       : Creates a new script in the lab.
    -edit      : Edit lab script.
    -tested    : Indicates if the script has been tested.
    -delete    : Removes the script from the lab.
    -filename  : The name of the file to be moved.
    -list      : Lists all lab scripts.
    -help      : Displays this help message.
"@
    linebreak 2
    return
}


function Get-LabScripts {
    # PowerShellIcon = $pslabsymbol
    # PSLabIcon =(nf md-flask_outline)

    <#
    .SYNOPSIS
        Provides functions for testing PowerShell scripts.
    .DESCRIPTION
        This module contains functions and utilities to assist with testing PowerShell scripts.
    .EXAMPLE
        Import-Module -Name lab
        # This will import the lab module for use in your PowerShell session.
    .NOTES
        Author: njen
        Version: 1.0.0
    #>

    $sysparams = @(
        'Verbose', 'Debug', 'ErrorAction', 'WarningAction', 'InformationAction', 'ErrorVariable',
        'WarningVariable', 'InformationVariable', 'OutVariable', 'OutBuffer', 'PipelineVariable'
    )

    $aliases = @{}

    Get-Alias | ForEach-Object { if ($null -eq $aliases[$_.Definition]) { $aliases.Add($_.Definition, $_.Name) } }

    $scriptsPath = $PSLAB

    Get-Command -CommandType ExternalScript | ForEach-Object `
    {
        $name = [IO.Path]::GetFileNameWithoutExtension($_.Name)
        if ($_.Source -like "$scriptsPath\*") {
            Write-Host "$name " -NoNewline

            $parameters = $_.Parameters
            if ($null -ne $parameters) {
                $parameters.Keys | Where-Object { $sysparams -notcontains $_ } | ForEach-Object `
                {
                    $p = $parameters[$_]
                    $c = if ($p.ParameterType -like 'Switch') { 'DarkGray' } else { 'DarkCyan' }
                    Write-Host "-$_ " -NoNewline -ForegroundColor $c
                }
            }

            $alias = $aliases[$name]
            if ($alias) {
                Write-Host " ($alias)" -ForegroundColor DarkGreen -NoNewline
            }

            Write-Host
        }
    }
}


function lab {
    <#
    .SYNOPSIS
        Powershell script testing.
    .DESCRIPTION
        This function provides options to create, test, list, and delete PowerShell scripts within the lab environment.
    .PARAMETER new
        Creates a new script in the lab.
    .PARAMETER tested
        Indicates if the script has been tested.
    .PARAMETER edit
        Edits an existing script in the lab.
    .PARAMETER delete
        Removes the script from the lab.
    .PARAMETER filename
        The name of the file to be created, moved, or deleted.
    .PARAMETER list
        Lists all lab scripts.
    .PARAMETER help
        Displays the help message for this function.
    .EXAMPLE
        lab -new -filename "NewScript"
        # This will create a new script "NewScript.ps1" in the lab.
    .EXAMPLE
        lab -tested -filename "TestScript"
        # This will move the tested script "TestScript.ps1" from the lab to the scripts directory.
    .EXAMPLE
        lab -delete -filename "OldScript"
        # This will delete the script "OldScript.ps1" from the lab.
    .EXAMPLE
        lab -list
        # This will list all the lab scripts.
    .EXAMPLE
        lab -help
        # This will display the help message.
    .NOTES
        Author: njen
        Version: 1.0.0
    #>
    param (
        [switch]$help,
        [switch]$new,
        [switch]$edit,
        [switch]$tested,
        [switch]$delete,
        [string]$filename,
        [switch]$list
    )
    $PadddingOutSpaces = 4
    $PadddingOut = " " * $PadddingOutSpaces

    if ($help) {
        Get-LabUsage
        return
    }

    if ($new) {
        $actioncolor = 'Green'
        $filePath = "$PSLAB\$filename.ps1"
        if (!(Test-Path $filePath)) {
            New-Item -Path $filePath -ItemType File -ErrorAction Stop | Out-Null
            linebreak
            Write-Color $actioncolor "$PadddingOut Created: " -inline
            Write-Color $dircolor "$PSLAB\" -inline
            Write-Color $labsymbolcolor $labsymbol -inline
            Write-Color $labscriptcolor  " $filename.ps1"
            linebreak
            return
        }
        else {
            Write-Err "File $filename.ps1 already exists in $PSLAB."
            return
        }
    }

    if ($edit) {
        $filePath = "$PSLAB\$filename.ps1"
        if (Test-Path $filePath) {
            if ($env:EDITOR) {
                & $env:EDITOR $filePath
                return
            }
            else {
                Write-Err "EDITOR environment variable not set."
                return
            }
        }
        else {
            Write-Err "File $filename.ps1 not found in $PSLAB."
            return
        }
    }

    if ($tested) {
        $actioncolor = 'Yellow'
        $filePath = "$PSLAB\$filename.ps1"
        if (Test-Path $filePath) {
            $destination = "$env:PSCRIPTS\$filename.ps1"
            Move-Item -Path $filePath -Destination $destination -ErrorAction Stop | Out-Null
            linebreak
            Write-Color $actioncolor "$PadddingOut Moved: " -inline
            Write-Color $dircolor "$PSLAB\" -inline
            Write-Color $labsymbolcolor $labsymbol -inline
            Write-Color $labscriptcolor  " $filename.ps1" -inline
            Write-Color $arrowcolor $arrow -inline
            Write-Color $dircolor "$env:PSCRIPTS\" -inline
            Write-Color $pscriptscolor $pslabsymbol -inline
            Write-Color $labscriptcolor " $filename.ps1"
            linebreak
            return
        }
        else {
            Write-Err "File $filename.ps1 not found in $PSLAB."
            return
        }
    }

    if ($delete) {
        $actioncolor = 'Red'
        $filePath = "$PSLAB\$filename.ps1"
        if (Test-Path $filePath) {
            Remove-Item -Path $filePath -ErrorAction Stop | Out-Null
            linebreak
            Write-Color $actioncolor "$PadddingOut Deleted: " -inline
            Write-Color $dircolor "$PSLAB\" -inline
            Write-Color $labsymbolcolor $labsymbol -inline
            Write-Color $labscriptcolor  " $filename.ps1"
            linebreak
            return
        }
        else {
            Write-Err "File $filename.ps1 not found in $PSLAB."
            return
        }
    }
    if ($list) {
        Get-LabScripts
        return
    }
    Get-LabUsage
    return
}

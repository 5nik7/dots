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
$psdoticon = (nf cod-terminal_powershell)
$dircolor = 'DarkGray'

$arrowcolor = 'DarkGray'
$arrow = " --> "

$labicon = (nf md-flask_outline)
$labiconcolor = 'Cyan'
$labscriptcolor = 'White'
$pscriptscolor = 'Blue'

function SetupLab {
    param (
        [string]$labPath,
        [switch]$quiet
    )
    if (-not $Env:LAB) {
        if ($labPath) {
            $env:LAB = $labPath
        }
        else {
            if ($env:DOTS) {
                $env:LAB = "$env:DOTS\lab"
            }
            else {
                $env:LAB = "$Env:USERPROFILE\lab"
            }
        }
        if (-not $quiet) {
            Write-Info "Setting up lab environment in $Env:LAB" -box
        }
    }
    if ($labPath) {
        if (Test-Path $labPath) {
            if ($labPath -ne $Env:LAB) {
                $oldLab = "$Env:LAB\PowerShell"
                Remove-Path -Path $oldLab
                if (-not $quiet) {
                    Write-Info "Removed $oldLab from the PATH" -box
                }
                $Env:LAB = $labPath
                if (-not $quiet) {
                    Write-Info "Setting up lab environment in $Env:LAB" -box
                }
            }
            else {
                if (-not $quiet) {
                    Write-Warn "Lab environment already set up in $Env:LAB" -box
                }
                return
            }
        }
        else {
            if (-not $quiet) {
                Write-Err "Path $labPath does not exist." -box
            }
            return
        }
    }
    $labPath = $Env:LAB
    $Global:LAB = $env:LAB

    if (!(Test-Path($env:LAB))) {
        New-Item -ItemType Directory -Path $env:LAB -ErrorAction Stop | Out-Null
        if (-not $quiet) {
            Write-Success "Created lab directory: $env:LAB" -box
        }
    }
    $env:PSLAB = "$env:LAB\PowerShell"
    $Global:PSLAB = $env:PSLAB
    if (!(Test-Path($env:PSLAB))) {
        New-Item -ItemType Directory -Path $env:PSLAB -ErrorAction Stop | Out-Null
        if (-not $quiet) {
            Write-Success "Created PowerShell lab directory: $env:PSLAB" -box
        }
    }
    if ($env:PATH -notlike "*$env:PSLAB*") {
        Add-Path -Path $env:PSLAB
        if (-not $quiet) {
            Write-Success "Added $env:PSLAB to the PATH" -box
        }

    }
    if (-not $quiet) {
        Write-Success "Lab environment set up in $env:LAB" -box
    }
}
if (!($env:LAB)) {
    SetupLab -quiet
}

if ($env:PSCRIPTS) {
    if (Test-Path -Path $env:PSCRIPTS) {
        $Global:PSCRIPTS = $env:PSCRIPTS
    }
}
else {
    $PSScriptsDir = (Get-ItemProperty -Path $PROFILE).DirectoryName + "\Scripts"
    if (Test-Path -Path $PSScriptsDir) {
        $env:PSCRIPTS = $PSScriptsDir
        $Global:PSCRIPTS = $env:PSCRIPTS
    }
}

function Get-LabUsage {
    $bannerPath = Join-Path -Path $modulePath -ChildPath "banner"
    if (Test-Path -Path $bannerPath) {
        wh '' -bb 2
        Get-Content -Path $bannerPath | Write-Host
    }
    else {
        wh "LAB" cyan -bb 2 -padout 2
    }
    wh '' -bb 2
    Write-Output @"
 Usage: lab [-new] [-edit] [-tested] [-delete] [-filename <string>] [-list] [-help] [-dot] [-cat] [-setup] [-labPath <string>] [-quiet]

    -new       : Creates a new script in the lab.
    -edit      : Edit lab script.
    -tested    : Indicates if the script has been tested.
    -delete    : Removes the script from the lab.
    -filename  : The name of the file to be created, moved, edited, or deleted.
    -list      : Lists all lab scripts.
    -help      : Displays this help message.
    -dot       : Indicates that the script should be moved to the scripts directory.
    -cat       : Displays the content of the script file.
    -setup     : Sets up the lab environment.
    -labPath   : Specifies the path to the lab directory.
    -quiet     : Suppresses output messages.
"@
    wh '' -bb 1
    return
}


function Get-LabScripts {
    # PowerShellIcon = $psdoticon
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
    param (
        [string]$TargetScriptDir,
        [string]$targeticon,
        [string]$targetcolor
    )

    $sysparams = @(
        'Verbose', 'Debug', 'ErrorAction', 'WarningAction', 'InformationAction', 'ErrorVariable',
        'WarningVariable', 'InformationVariable', 'OutVariable', 'OutBuffer', 'PipelineVariable'
    )

    $aliases = @{}

    Get-Alias | ForEach-Object { if ($null -eq $aliases[$_.Definition]) { $aliases.Add($_.Definition, $_.Name) } }

    $scriptsPath = $TargetScriptDir

    wh "Listing scripts in $scriptsPath" $targetcolor -bb 1 -ba 1 -padout 2 -border darkgray -box
    Get-Command -CommandType ExternalScript | ForEach-Object `
    {
        $name = [IO.Path]::GetFileNameWithoutExtension($_.Name)
        if ($_.Source -like "$scriptsPath\*") {
            wh "$PadddingOut $name " -padout 2

            $parameters = $_.Parameters
            if ($null -ne $parameters) {
                $parameters.Keys | Where-Object { $sysparams -notcontains $_ } | ForEach-Object `
                {
                    $p = $parameters[$_]
                    $c = if ($p.ParameterType -like 'Switch') { 'DarkGray' } else { 'DarkCyan' }
                    wh "-$_ " $c
                }
            }

            $alias = $aliases[$name]
            if ($alias) {
                wh " ($alias)" DarkGreen
            }

            Write-Host
        }
    }
    wh '' -bb 1
}


function lab {
    <#
    .SYNOPSIS
        Powershell script management for lab environment.
    .DESCRIPTION
        This function provides options to create, test, list, edit, and delete PowerShell scripts within the lab environment.
    .PARAMETER new
        Creates a new script in the lab.
    .PARAMETER tested
        Moves the tested script from the lab to the scripts directory.
    .PARAMETER edit
        Edits an existing script in the lab.
    .PARAMETER delete
        Removes the script from the lab.
    .PARAMETER filename
        The name of the file to be created, moved, edited, or deleted.
    .PARAMETER list
        Lists all the lab scripts.
    .PARAMETER help
        Displays the help message for this function.
    .PARAMETER dot
        Indicates that the script should be moved to the scripts directory.
    .PARAMETER cat
        Displays the content of the script file.
    .PARAMETER setup
        Sets up the lab environment.
    .PARAMETER labPath
        Specifies the path to the lab directory.
    .PARAMETER quiet
        Suppresses output messages.
    .EXAMPLE
        lab -new -filename "NewScript"
        # This will create a new script "NewScript.ps1" in the lab.
    .EXAMPLE
        lab -tested -filename "TestScript"
        # This will move the tested script "TestScript.ps1" from the lab to the scripts directory.
    .EXAMPLE
        lab -edit -filename "EditScript"
        # This will open the script "EditScript.ps1" in the default editor.
    .EXAMPLE
        lab -delete -filename "OldScript"
        # This will delete the script "OldScript.ps1" from the lab.
    .EXAMPLE
        lab -list
        # This will list all the lab scripts.
    .EXAMPLE
        lab -help
        # This will display the help message.
    .EXAMPLE
        lab -cat -filename "ViewScript"
        # This will display the content of the script "ViewScript.ps1".
    .NOTES
        Author: njen
        Version: 1.0.0
    #>
    param (
        [switch]$help,
        [switch]$dot,
        [switch]$new,
        [switch]$edit,
        [switch]$tested,
        [switch]$delete,
        [string]$filename,
        [switch]$list,
        [switch]$cat,
        [switch]$setup,
        [string]$labPath,
        [switch]$quiet = $false
    )

    $TargetScriptDir = $env:PSLAB
    $targeticon = $labicon
    $targetcolor = $labiconcolor


    if ($setup) {
        if ($labPath) {
            SetupLab -labPath $labPath -quiet:$quiet
            return
        }
        SetupLab -quiet:$quiet
        return
    }



    if ($dot) {
        $TargetScriptDir = $env:PSCRIPTS
        $targeticon = $psdoticon
        $targetcolor = $pscriptscolor
    }

    if ($help) {
        Get-LabUsage
        return
    }

    if ($new) {
        $actioncolor = 'Green'
        $filePath = "$TargetScriptDir\$filename.ps1"
        if (!(Test-Path $filePath)) {
            New-Item -Path $filePath -ItemType File -ErrorAction Stop | Out-Null
            wh " Created: " $actioncolor "$TargetScriptDir\ " $dircolor "$targeticon" $targetcolor " $filename.ps1" $labscriptcolor -bb 1 -ba 1 -padout 2 -box -border darkgray
            return
        }
        else {
            Write-Err "File $filename.ps1 already exists in $TargetScriptDir." -box
            return
        }
    }

    if ($edit) {
        if ($edit -eq '') {
            $Path = "$TargetScriptDir"
            $patherror = "$TargetScriptDir not found."
        }
        else {
            $Path = "$TargetScriptDir\$filename.ps1"
            $patherror = "File $filename.ps1 not found in $TargetScriptDir."
        }
        if (Test-Path $Path) {
            if ($env:EDITOR) {
                & $env:EDITOR $Path
                return
            }
            else {
                Write-Err "EDITOR environment variable not set." -box
                return
            }
        }
        else {
            Write-Err "$patherror" -box
            return
        }
    }

    if ($tested) {
        $actioncolor = 'Yellow'
        $filePath = "$PSLAB\$filename.ps1"
        if (Test-Path $filePath) {
            $destination = "$env:PSCRIPTS\$filename.ps1"
            Move-Item -Path $filePath -Destination $destination -ErrorAction Stop | Out-Null
            wh " Moved: " $actioncolor "$PSLAB\ " $dircolor "$labicon" $labiconcolor " $filename.ps1" $labscriptcolor "$arrow" $arrowcolor "$env:PSCRIPTS" $dircolor "$psdoticon" $pscriptscolor " $filename.ps1" $labscriptcolor -bb 1 -ba 1 -padout 2 -box -border darkgray
            return
        }
        else {
            Write-Err "File $filename.ps1 not found in $PSLAB." -box
            return
        }
    }

    if ($delete) {
        $actioncolor = 'Red'
        $filePath = "$TargetScriptDir\$filename.ps1"
        if (Test-Path $filePath) {
            Remove-Item -Path $filePath -ErrorAction Stop | Out-Null
            wh " Deleted: " $actioncolor "$TargetScriptDir\ " $dircolor "$targeticon" $targetcolor "$filename.ps1" $labscriptcolor -bb 1 -ba 1 -padout 2 -box -border darkgray
            return
        }
        else {
            Write-Err "File $filename.ps1 not found in $TargetScriptDir."
            return
        }
    }

    if ($cat) {
        $command = if (Test-CommandExists Get-ContentPretty) { 'Get-ContentPretty' }
        elseif (Test-CommandExists bat) { 'bat' }
        elseif (Test-CommandExists cat) { 'cat' }
        else {
            Write-Err "No command found to display file contents." -box -bb 1 -ba 1 -padout 2
            return
        }
        $filePath = "$TargetScriptDir\$filename.ps1"
        if (Test-Path $filePath) {
            & $command $filePath
            return
        }
        else {
            Write-Err "File $filename.ps1 not found in $TargetScriptDir." -box
            return
        }
    }

    if ($list) {
        Get-LabScripts $TargetScriptDir $targeticon $targetcolor
        return
    }
    Get-LabUsage
    return
}

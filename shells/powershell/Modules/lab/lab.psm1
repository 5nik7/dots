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

# PowerShellIcon = ($($util.symbols.'nf-cod-terminal_powershell'.icon))
# PSLabIcon = ($($util.symbols.'nf-md-flask_outline'.icon))

<#
.SYNOPSIS
List all external scripts and their parameter names. These are all of the
scripts implemented in your WindowsPowerShell profile Modules/Scripts folder.

.DESCRIPTION
Any aliases are listed along with each command.
#>

function Get-LabScripts {
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

<#
.DESCRIPTION
    Updates the desktop wallpaper.
#>
function lab {
    param (
        [switch]$tested,
        [string]$filename,
        [switch]$list,
        [switch]$help
    )

    if ($help -or -not $tested -and -not $filename -and -not $list) {
        Write-Output @"
Usage: lab [-tested] [-filename <string>] [-list] [-help]

Parameters:
    -tested    : Indicates if the script has been tested.
    -filename  : The name of the file to be moved.
    -list      : Lists all lab scripts.
    -help      : Displays this help message.
"@
        return
    }

    if ($tested) {
        $filePath = "$PSLAB\$filename.ps1"
        if (Test-Path $filePath) {
            $destination = "$env:PSCRIPTS\$filename.ps1"
            Move-Item -Path $filePath -Destination $destination -ErrorAction Stop | Out-Null
            linebreak
            Write-Color White "Moved " -inline
            Write-Color Cyan  ($($util.symbols.'nf-md-flask_outline'.icon)) -inline
            Write-Color White " $filename.ps1" -inline
            Write-Color White " to " -inline
            Write-Color Blue ($($util.symbols.'nf-cod-terminal_powershell'.icon)) -inline
            Write-Color Green " $filename.ps1"
            linebreak
        }
        else {
            Write-Err "File $filename.ps1 not found in $PSLAB."
        }
    }
    if ($list) {
        Get-LabScripts
    }
}

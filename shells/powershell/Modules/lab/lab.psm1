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
        [switch]$list
    )

    if ($tested) {
        $filePath = "$PSLAB\$filename.ps1"
        if (Test-Path $filePath) {
            $destination = "$env:PSCRIPTS\$filename.ps1"
            Move-Item -Path $filePath -Destination $destination
            Write-Success "Moved $filename.ps1 to $destination"
            Write-Host "$filePath moved to $destination"
            Write-Host ''
        }
        else {
            Write-Err "File $filename.ps1 not found in $PSLAB."
        }
    }
    if ($list) {
        Get-LabScripts
    }
}

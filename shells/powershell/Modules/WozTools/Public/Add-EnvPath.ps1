Function Add-EnvPath {
    <#
    .SYNOPSIS
    Add a Folder to Environment Variable PATH

    .DESCRIPTION
    Add Folders to Environment Variable PATH for Machine, User or Process scope
    And removes missing PATH locations

    .PARAMETER Path
    Folder or Folders to add to PATH

    .PARAMETER VariableTarget
    Which Env Path the directory gets added to.
    Machine, User or Process

    .PARAMETER PassThru
    Display updated PATH variable

    .INPUTS
    [String] - Folder Path, accepts multiple folders

    .OUTPUTS
    String - List of the New Path Variable

    .EXAMPLE
    Add-EnvPath -Path 'C:\temp' -VariableTarget Machine
#>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory, ValueFromPipeline)]
        [ValidateScript({
                if (-not (Test-Path -Path $_ -PathType Container -IsValid)) {
                    throw 'Invalid Folder Path'
                }
                return $true
            })]
        [String[]]$Path,
        [System.EnvironmentVariableTarget]$VariableTarget = [System.EnvironmentVariableTarget]::User,
        [switch]$PassThru
    )
    begin {
        $MyParamValues = Get-ParameterValues
        if ($MyParamValues.VariableTarget -eq 'Machine') {
            if (-not (Test-IfAdmin)) {
                throw 'Run as admin or change VariableTarget to "User"'
            }
        }
        $PathSepChar = [System.IO.Path]::PathSeparator
        $DirSepChar = [System.IO.Path]::DirectorySeparatorChar
        $OldPath = [string[]][System.Environment]::GetEnvironmentVariable('PATH', $VariableTarget).Split($PathSepChar).TrimEnd($DirSepChar).Where({ $_ -ne '' })
        $NewPath = [System.Collections.Generic.List[string]]::new()
        $NewPath.AddRange($OldPath)
    }
    process {
        foreach ($NDir in $Path) {
            $NDir = Convert-Path -Path $NDir.TrimEnd($DirSepChar)
            if ($NewPath -notcontains $NDir) { $null = $NewPath.Add($NDir) }
            else { Write-Warning -Message ('SKIPPING DUPLICATE: {0}' -f $NDir) }
        }
    }
    end {
        [System.Environment]::SetEnvironmentVariable('PATH', (($NewPath | Sort-Object -Unique) -join $PathSepChar), $VariableTarget)
        if ($PassThru) {
            $Confirm = [System.Environment]::GetEnvironmentVariable('PATH', $VariableTarget).Split($PathSepChar)
            return $Confirm
        }
    }
}

function Add-Path {
    param (
        [Parameter(Mandatory = $true)]
        [string]$Path
    )
    if (Test-Path $Path) {
        if (-not ($env:Path -split ';' | Select-String -SimpleMatch $Path)) {
            $env:Path += ";$Path"
        }
    }
    else {
        Write-Error "Path '$Path' does not exist"
    }
}

function Add-PrependPath {
    param (
        [Parameter(Mandatory = $true)]
        [string]$Path
    )
    if (Test-Path $Path) {
        if (-not ($env:Path -split ';' | Select-String -SimpleMatch $Path)) {
            $env:Path = "$Path;$env:Path"
        }
    }
    else {
        Write-Error "Path '$Path' does not exist"
    }
}

function Remove-Path {
    param (
        [Parameter(Mandatory = $true)]
        [string]$Path
    )
    if ($env:Path -split ';' | Select-String -SimpleMatch $Path) {
        $env:Path = ($env:Path -split ';' | Where-Object { $_ -ne $Path }) -join ';'
    }
}

function Remove-DuplicatePaths {
    $paths = $env:Path -split ';'
    $uniquePaths = [System.Collections.Generic.HashSet[string]]::new()
    $newPath = @()

    foreach ($path in $paths) {
        if ($uniquePaths.Add($path)) {
            $newPath += $path
        }
    }

    $env:Path = $newPath -join ';'
}

function powerpath {
    [CmdletBinding()]
    param (
        [switch]$help,
        [switch]$v,
        [switch]$i,
        [string]$Path,
        [switch]$rm,
        [switch]$append,
        [switch]$prepend
    )

    if ($help -or $path -eq '') {
        Write-Host "Usage: Add-Path -Path <string> [-prepend] [-f] [-v] [-i]"
    }

    if (Test-Path -PathType Container -Path $Path) {
        $Path = Resolve-Path $Path
        if ($v) { Write-Host "Path exists." }
        if ($rm) {
            if ($env:Path -split ';' | Select-String -SimpleMatch $Path) {
                if ($v) { Write-Host "$Path is on the Path." }
                if ($i) {
                    $chice = (ask "Would you like renove $Oath from the path?")
                    if ($chice -eq $true) {
                        Remove-Path -Path $Path
                        if ($v) { Write-Host "$Path has been removed." }
                    }
                    else {
                        if ($v) { Write-Host "Exiting." }
                        return
                    }
                }
                else {
                    Remove-Path -Path $Path
                    if ($v) { Write-Host "$Path has been removed." }
                }
            }
            else {
                if ($v) { Write-Host "$Path is not on the path." }
            }
        }
        if ($append) {
            if ($i) {
                $chice = (ask "Would you like to add $Path to the end of the path?")
                if ($chice -eq $true) {
                    Remove-Path -Path $Path
                    Add-Path -Path $Path
                    if ($v) { Write-Host "$Path has been added to the end of the path." }
                }
                else {
                    if ($v) { Write-Host "Exiting" }
                }
            }
            else {
                Remove-Path -Path $Path
                Add-Path -Path $Path
                if ($v) { Write-Host "$Path has been added to the end of the path." }
            }
        }
        elseif ($prepend) {
            if ($i) {
                $chice = (ask "Would you like to add $Path to the beginning of the path?")
                if ($chice -eq $true) {
                    Remove-Path -Path $Path
                    Add-PrependPath -Path $Path
                    if ($v) { Write-Host "$Path has been added to the beginning of the path." }
                }
                else {
                    if ($v) { Write-Host "Exiting" }
                }
            }
            else {
                Remove-Path -Path $Path
                Add-PrependPath -Path $Path
                if ($v) { Write-Host "$Path has been added to the beginning of the path." }
            }
        }
        else { return }
    }
    else {
        if ($v) { Write-Host "Path does not exist." }
        return
    }
}

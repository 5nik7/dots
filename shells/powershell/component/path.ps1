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
        Write-Err "Path $Path does not exist"
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
        Write-Err "Path $Path does not exist"
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
    else {
        Write-Err "Path $Path does not exist"
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
        else {
            Write-Verbose "Duplicate path detected and removed: $path"
        }
    }

    $env:Path = $newPath -join ';'
    Write-Verbose "Duplicate paths have been removed. Updated PATH: $env:Path"
}

function Get-PyenvVersion {
    $PYVER = (Get-Content "$env:PYENV\version") -replace '\n', ''
    return $PYVER
}
$PYVER = Get-PyenvVersion
$env:PYVER = $PYVER

function PyenvExePath {
    $PYENVBIN = (Join-Path $env:PYENV 'bin')
    return $PYENVBIN
}
$PYENVBIN = PyenvExePath
$env:PYENVBIN = $PYENVBIN

function Get-PyenvExeDir {
    $PYEXEDIR = (Join-Path "$env:PYENV" "versions\$PYVER")
    return $PYEXEDIR
}
$PYEXEDIR = Get-PyenvExeDir
$env:PYEXEDIR = $PYEXEDIR

function Get-PyenvScripts {
    $PYENVSCRIPTS = (Join-Path $PYEXEDIR 'Scripts')
    return $PYENVSCRIPTS
}
$PYENVSCRIPTS = Get-PyenvScripts
$env:PYENVSCRIPTS = $PYENVSCRIPTS

function Get-PyenvShims {
    $PYENVSHIMS = (Join-Path $env:PYENV 'shims')
    return $PYENVSHIMS
}
$PYENVSHIMS = Get-PyenvShims
$env:PYENVSHIMS = $PYENVSHIMS

function Set-Pyenv {
    param (
        [switch]$pre = $false
    )
    try {
        @(
            "$env:PYENVBIN",
            "$env:PYEXEDIR",
            "$env:PYENVSCRIPTS",
            "$env:PYENVSHIMS"
        ) | ForEach-Object {
            $Path = "$_"
            if ($v) {
                Write-Host "$_"
            }
            if ($pre) {
                Add-PrependPath -Path "$Path"
            }
            else {
                Add-Path -Path "$Path"
            }
            Remove-DuplicatePaths
        }
    }
    catch {
        Write-Host "An error occurred: $_"
        return
    }
}
Set-Pyenv

$env:PSCRIPTS = "$env:PSDOTS\Scripts"
Add-Path -Path "$env:PSCRIPTS"

$env:DOTBIN = "$env:DOTS\bin"
Add-Path -Path "$env:DOTBIN"

$env:LOCALBIN = "$HOME\.local\bin"
Add-Path -Path "$env:LOCALBIN"

Add-Path -Path "$env:LOCALAPPDATA\Microsoft\WindowsApps"

Remove-DuplicatePaths

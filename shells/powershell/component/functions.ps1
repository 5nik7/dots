$Global:isAdmin = (New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

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

function winutil {
    Invoke-RestMethod "https://github.com/ChrisTitusTech/winutil/releases/latest/download/winutil.ps1" | Invoke-Expression
}

function .. {
    Set-Location ".."
}
function ... {
    Set-Location "..."
}
function .... {
    Set-Location "...."
}

function yy {
    $tmp = [System.IO.Path]::GetTempFileName()
    yazi $args --cwd-file="$tmp"
    $cwd = Get-Content -Path $tmp
    if (-not [String]::IsNullOrEmpty($cwd) -and $cwd -ne $PWD.Path) {
        Set-Location -LiteralPath $cwd
    }
    Remove-Item -Path $tmp
}

function Get-Fetch {
    Write-Host ""
    fastfetch
    Write-Host ""
}

function Get-ContentPretty {
    <#
    .SYNOPSIS
        Runs eza with a specific set of arguments. Plus some line breaks before and after the output.
        Alias: ls, ll, la, l
    #>
    [CmdletBinding()]
    param (
        [Parameter(Mandatory = $true, Position = 1)]
        [string]$file
    )

    Write-Host ""
    bat $file
    Write-Host ""
}

function Get-ChildItemPretty {
    <#
    .SYNOPSIS
        Runs eza with a specific set of arguments. Plus some line breaks before and after the output.
        Alias: ls, ll, la, l
    #>
    [CmdletBinding()]
    param (
        [Parameter(Mandatory = $false, Position = 0)]
        [string]$Path = $PWD
    )

    Write-Host ""
    eza -a -l --group-directories-first --git-repos --git --icons --time-style relative $Path
    Write-Host ""
}

function Get-ChildItemPrettyTree {
    <#
    .SYNOPSIS
        Runs eza with a specific set of arguments. Plus some line breaks before and after the output.
        Alias: ls, ll, la, l
    #>
    [CmdletBinding()]
    param (
        [Parameter(Mandatory = $false, Position = 0)]
        [string]$Path = $PWD
    )

    Write-Host ""
    eza --icons --git-repos --git  -ln --time-style=relative --tree $Path
    Write-Host ""
}

function New-File {
    <#
    .SYNOPSIS
        Creates a new file with the specified name and extension. Alias: touch
    #>
    [CmdletBinding()]
    param (
        [Parameter(Mandatory = $true, Position = 0)]
        [string]$Name
    )

    Write-Verbose "Creating new file '$Name'"
    New-Item -ItemType File -Name $Name -Path $PWD | Out-Null
}

function Show-Command {
    <#
    .SYNOPSIS
        Displays the definition of a command. Alias: which
    #>
    [CmdletBinding()]
    param (
        [Parameter(Mandatory = $true, Position = 0)]
        [string]$Name
    )
    Write-Verbose "Showing definition of '$Name'"
    Get-Command $Name | Select-Object -ExpandProperty Definition
}

function gup {
    if (Test-Path .git) {
        $commitDate = Get-Date -Format "MM-dd-yyyy HH:mm"
        Write-Host ""
        git add .
        git commit -m "Update @ $commitDate"
        git push
        Write-Host ""
    }
    else {
        Write-Error "This directory does not contain a .git directory"
    }
}

function Edit-Profile {
  (& $env:EDITOR ([IO.Path]::GetDirectoryName($profile)))
}

function Get-Functions {
    Get-ChildItem function:\
}

function Test-CommandExists {
    param($command)
    $exists = $null -ne (Get-Command $command -ErrorAction SilentlyContinue)
    return $exists
}

# Editor Configuration
$EDITOR = if (Test-CommandExists code) { 'code' }
elseif (Test-CommandExists code) { 'nvim' }
elseif (Test-CommandExists vim) { 'vim' }
elseif (Test-CommandExists vi) { 'vi' }
else { 'notepad' }
$env:EDITOR = $EDITOR
function edit-item {
    param (
        [string]$Path = $PWD
    )

    if ($Path) {
        & $env:EDITOR $Path
    }
    else {
        & $env:EDITOR
    }
}

function dd {
    $currentDirectory = Resolve-Path "$PWD"
    start-process explorer.exe "$currentDirectory"
}

Function Search-Alias {
    param (
        [string]$alias
    )
    if ($alias) {
        Get-Alias | Where-Object DisplayName -Match $alias
    }
    else {
        Get-Alias
    }
}

function .d {
    Set-Location "$DOTS"
}


function cdev {
    Set-Location "$env:DEV"
}

function q {
    Exit
}

# when "reload" is typed in the terminal, the profile is reloaded
# use sendkeys to send the enter key to the terminal
function reload {
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.SendKeys]::SendWait(". $")
    [System.Windows.Forms.SendKeys]::SendWait("PROFILE")
    [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
}

function Add-Path {
  param (
    [Parameter(Mandatory = $true)]
    [string]$Path
  )
  if (-not ($env:Path -split ';' | Select-String -SimpleMatch $Path)) {
    $env:Path += ";$Path"
  }
}

function wtb {
  Invoke-RestMethod "https://github.com/ChrisTitusTech/winutil/releases/latest/download/winutil.ps1" | Invoke-Expression
}

function .. {
  Set-Location ".."
}

function ya {
  $tmp = [System.IO.Path]::GetTempFileName()
  yazi $args --cwd-file="$tmp"
  $cwd = Get-Content -Path $tmp
  if (-not [String]::IsNullOrEmpty($cwd) -and $cwd -ne $PWD.Path) {
    Set-Location -Path $cwd
  }
  Remove-Item -Path $tmp
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
    git add .
    git commit -m "Update @ $commitDate"
    git push
  }
  else {
    Write-Error "This directory does not contain a .git directory"
  }
}


function Get-Weather($arg) {
  if ($arg -eq "help") {
    curl -s "wttr.in/:help"
  }
  elseif ($arg -eq "0") {
    curl -s "wttr.in/Yakima?0uFq"
  }
  elseif ($arg -eq "1") {
    curl -s "wttr.in/Yakima?1uFq"
  }
  elseif ($arg -eq "2") {
    curl -s "wttr.in/Yakima?2uFq"
  }
  elseif ($arg -eq "all") {
    curl -s "wttr.in/Yakima?uFq"
  }
  else {
    curl -s "wttr.in/Yakima?0uFq"
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
elseif (Test-CommandExists nvim) { 'nvim' }
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
  param (
    [string]$Path
  )

  if ($Path) {
    explorer $Path
  }
  else {
    explorer $PWD
  }
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
  Set-Location "$env:PROJECTS\dots"
}


function pro {
  Set-Location "$env:PROJECTS"
}

function q {
  Exit
}

function colors {
  $colors = [enum]::GetValues([System.ConsoleColor])

  Foreach ($bgcolor in $colors) {
    Foreach ($fgcolor in $colors) { Write-Host "$fgcolor|"  -ForegroundColor $fgcolor -BackgroundColor $bgcolor -NoNewLine }

    Write-Host " on $bgcolor"
  }
}
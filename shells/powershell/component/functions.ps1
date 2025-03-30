function yy {
  $tmp = [System.IO.Path]::GetTempFileName()
  yazi $args --cwd-file="$tmp"
  $cwd = Get-Content -Path $tmp
  if (-not [String]::IsNullOrEmpty($cwd) -and $cwd -ne $PWD.Path) {
    Set-Location -LiteralPath $cwd
  }
  Remove-Item -Path $tmp
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

function gup {
  if (Test-Path .git) {
    $commitDate = Get-Date -Format 'MM-dd-yyyy HH:mm'
    Write-Host ''
    git add .
    git commit -m "Update @ $commitDate"
    git push
    Write-Host ''
  }
  else {
    Write-Error 'This directory does not contain a .git directory'
  }
}

function q {
  Exit
}

function Find-File {
  <#
    .SYNOPSIS
        Finds a file in the current directory and all subdirectories. Alias: ff
    #>
  [CmdletBinding()]
  param (
    [Parameter(ValueFromPipeline, Mandatory = $true, Position = 0)]
    [string]$SearchTerm
  )

  Write-Verbose "Searching for '$SearchTerm' in current directory and subdirectories"
  $result = Get-ChildItem -Recurse -Filter "*$SearchTerm*" -ErrorAction SilentlyContinue

  Write-Verbose 'Outputting results to table'
  $result | Format-Table -AutoSize
}

function Find-String {
  <#
    .SYNOPSIS
        Searches for a string in a file or directory. Alias: grep
    #>
  [CmdletBinding()]
  param (
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$SearchTerm,
    [Parameter(ValueFromPipeline, Mandatory = $false, Position = 1)]
    [string]$Directory,
    [Parameter(Mandatory = $false)]
    [switch]$Recurse
  )

  Write-Verbose "Searching for '$SearchTerm' in '$Directory'"
  if ($Directory) {
    if ($Recurse) {
      Write-Verbose "Searching for '$SearchTerm' in '$Directory' and subdirectories"
      Get-ChildItem -Recurse $Directory | Select-String $SearchTerm
      return
    }

    Write-Verbose "Searching for '$SearchTerm' in '$Directory'"
    Get-ChildItem $Directory | Select-String $SearchTerm
    return
  }

  if ($Recurse) {
    Write-Verbose "Searching for '$SearchTerm' in current directory and subdirectories"
    Get-ChildItem -Recurse | Select-String $SearchTerm
    return
  }

  Write-Verbose "Searching for '$SearchTerm' in current directory"
  Get-ChildItem | Select-String $SearchTerm
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

function Test-CommandExists {
  param($command)
  $exists = $null -ne (Get-Command $command -ErrorAction SilentlyContinue)
  return $exists
}

function Show-Command {
  [CmdletBinding()]
  param (
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Name
  )
  if (-not (Test-CommandExists $Name)) {
    Write-Err "$Name" -box
    return
  }
  Write-Verbose "Showing definition of '$Name'"
  Get-Command $Name | Select-Object -ExpandProperty Definition
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

  linebreak
  bat $file
  linebreak
}

function .d {
  Set-Location "$env:DOTS"
}

function cdev {
  Set-Location "$env:DEV"
}

function Edit-Profile {
  (& $env:EDITOR ([IO.Path]::GetDirectoryName($profile)))
}

function .. {
  Set-Location '..'
}
function ... {
  Set-Location '...'
}
function .... {
  Set-Location '....'
}
function ..... {
  Set-Location '.....'
}

function Get-Functions {
  Get-ChildItem function:\
}

function winutil {
  Invoke-RestMethod 'https://github.com/ChrisTitusTech/winutil/releases/latest/download/winutil.ps1' | Invoke-Expression
}

function nerdfonts {
  param (
    [Parameter(ValueFromRemainingArguments = $true)]
    $OptionalParameters
  )
  & ([scriptblock]::Create((Invoke-WebRequest 'https://to.loredo.me/Install-NerdFont.ps1').Content)) @OptionalParameters
}

function find-ln {
  Get-ChildItem | Where-Object { $_.Attributes -match 'ReparsePoint' }
}

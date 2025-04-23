# Initial GitHub.com connectivity check with 1 second timeout
$global:canConnectToGitHub = Test-Connection github.com -Count 1 -Quiet

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

function Update-PowerShell {
  try {
    Write-Host 'Checking for PowerShell updates...' -ForegroundColor Cyan
    $updateNeeded = $false
    $currentVersion = $PSVersionTable.PSVersion.ToString()
    $gitHubApiUrl = 'https://api.github.com/repos/PowerShell/PowerShell/releases/latest'
    $latestReleaseInfo = Invoke-RestMethod -Uri $gitHubApiUrl
    $latestVersion = $latestReleaseInfo.tag_name.Trim('v')
    if ($currentVersion -lt $latestVersion) {
      $updateNeeded = $true
    }

    if ($updateNeeded) {
      Write-Host 'Updating PowerShell...' -ForegroundColor Yellow
      Start-Process powershell.exe -ArgumentList '-NoProfile -Command winget upgrade Microsoft.PowerShell --accept-source-agreements --accept-package-agreements' -Wait -NoNewWindow
      Write-Host 'PowerShell has been updated. Please restart your shell to reflect changes' -ForegroundColor Magenta
    }
    else {
      Write-Host 'Your PowerShell is up to date.' -ForegroundColor Green
    }
  }
  catch {
    Write-Error "Failed to update PowerShell. Error: $_"
  }
}

function Clear-Cache {
  # add clear cache logic here
  Write-Host 'Clearing cache...' -ForegroundColor Cyan

  # Clear Windows Prefetch
  Write-Host 'Clearing Windows Prefetch...' -ForegroundColor Yellow
  Remove-Item -Path "$env:SystemRoot\Prefetch\*" -Force -ErrorAction SilentlyContinue

  # Clear Windows Temp
  Write-Host 'Clearing Windows Temp...' -ForegroundColor Yellow
  Remove-Item -Path "$env:SystemRoot\Temp\*" -Recurse -Force -ErrorAction SilentlyContinue

  # Clear User Temp
  Write-Host 'Clearing User Temp...' -ForegroundColor Yellow
  Remove-Item -Path "$env:TEMP\*" -Recurse -Force -ErrorAction SilentlyContinue

  # Clear Internet Explorer Cache
  Write-Host 'Clearing Internet Explorer Cache...' -ForegroundColor Yellow
  Remove-Item -Path "$env:LOCALAPPDATA\Microsoft\Windows\INetCache\*" -Recurse -Force -ErrorAction SilentlyContinue

  Write-Host 'Cache clearing completed.' -ForegroundColor Green
}

function Test-CommandExists {
  param($command)
  $exists = $null -ne (Get-Command $command -ErrorAction SilentlyContinue)
  return $exists
}
# Editor Configuration
$EDITOR = if (Test-CommandExists nvim) {
  'nvim'
}
elseif (Test-CommandExists code) {
  'code'
}
elseif (Test-CommandExists vim) {
  'vim'
}
elseif (Test-CommandExists vi) {
  'vi'
}
else {
  'notepad'
}
$env:EDITOR = $EDITOR
function Edit-Item {
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
Set-Alias -Name edit -Value Edit-Item
Set-Alias -Name e -Value Edit-Item

if (Test-CommandExists yazi) {
  function y {
    $tmp = [System.IO.Path]::GetTempFileName()
    yazi $args --cwd-file="$tmp"
    $cwd = Get-Content -Path $tmp -Encoding UTF8
    if (-not [String]::IsNullOrEmpty($cwd) -and $cwd -ne $PWD.Path) {
      Set-Location -LiteralPath ([System.IO.Path]::GetFullPath($cwd))
    }
    Remove-Item -Path $tmp
  }
  Set-Alias -Name d -Value y
}

# Clipboard Utilities
function cpy {
  Set-Clipboard $args[0]
}

function pst {
  Get-Clipboard
}

function touch($file) {
  '' | Out-File $file -Encoding ASCII
}

# Network Utilities
function Get-PubIP {
  (Invoke-WebRequest http://ifconfig.me/ip).Content
}

function sed($file, $find, $replace) {
  (Get-Content $file).replace("$find", $replace) | Set-Content $file
}

function which($name) {
  Get-Command $name | Select-Object -ExpandProperty Definition
}

function export($name, $value) {
  set-item -force -path "env:$name" -value $value;
}

function pkill($name) {
  Get-Process $name -ErrorAction SilentlyContinue | Stop-Process
}

function pgrep($name) {
  Get-Process $name
}

function head {
  param($Path, $n = 10)
  Get-Content $Path -Head $n
}

function tail {
  param($Path, $n = 10, [switch]$f = $false)
  Get-Content $Path -Tail $n -Wait:$f
}

function df {
  get-volume
}
# Directory Management
function mkcd {
  param($dir) mkdir $dir -Force; Set-Location $dir
}

function sysinfo {
  Get-ComputerInfo
}

function unzip ($file) {
  Write-Output('Extracting', $file, 'to', $pwd)
  $fullFile = Get-ChildItem -Path $pwd -Filter $file | ForEach-Object { $_.FullName }
  Expand-Archive -Path $fullFile -DestinationPath $pwd
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

function Show-Command {
  [CmdletBinding()]
  param (
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Name
  )
  if (-not (Test-CommandExists $Name)) {
    Write-Err $Name Magenta ' not found'
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

# Navigation Shortcuts
function docs {
  $docs = if (([Environment]::GetFolderPath('MyDocuments'))) {
    ([Environment]::GetFolderPath('MyDocuments'))
  }
  else {
    $HOME + '\Documents'
  }
  Set-Location -Path $docs
}

function .d {
  Set-Location "$env:DOTS"
}

function cdev {
  Set-Location "$env:DEV"
}
Set-Alias -Name dev -Value cdev

function Edit-Profile {
  & $env:EDITOR $PROFILE
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
  if ($isAdmin) {
    Invoke-RestMethod 'https://christitus.com/win' | Invoke-Expression
  }
  else {
    Write-Host 'You need to run this command as an administrator.' -ForegroundColor Red
    return
  }
  # Invoke-RestMethod 'https://github.com/ChrisTitusTech/winutil/releases/latest/download/winutil.ps1' | Invoke-Expression
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

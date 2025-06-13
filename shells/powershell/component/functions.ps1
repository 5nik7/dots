function dotenv {
  [CmdletBinding()]
  param (
    [Parameter(Mandatory = $true)]
    [string]$path,
    [switch]$v
  )
  $envFilePath = Join-Path -Path $path -ChildPath '.dotenv'
  if (Test-Path $envFilePath) {
    if ($v) {
      wh -box -border 0 -bb 1 -ba 1 -pad $env:padding 'DOTENV' white ' │ ' darkgray 'LOADING' darkgray ' │ ' darkgray "$path\" blue '.env' green
    }
    Get-Content $envFilePath | ForEach-Object {
      $name, $value = $_.split('=')

      if ([string]::IsNullOrWhiteSpace($name) -or $name.Contains('#')) {
        continue
      }

      $expandedName = [Environment]::ExpandEnvironmentVariables($name)
      $expandedValue = [Environment]::ExpandEnvironmentVariables($value)

      Set-Item -Path "env:$expandedName" -Value $expandedValue

      if ($v) {
        wh -bb 0 -ba 0 -nl -pad $env:padding '' darkgray $expandedName Yellow ' = ' DarkGray $expandedValue Gray
      }
    }
    if ($v) {
      linebreak 2
    }
  }
}

function Add-PSModulePath {
  param (
    [Parameter(Mandatory = $true)]
    [string]$Path
  )
  if (Test-Path $Path) {
    if (-not ($env:PSModulePath -split ';' | Select-String -SimpleMatch $Path)) {
      $env:PSModulePath = $env:PSModulePath + $Path
    }
  }
  else {
    Write-Err $Path Magenta ' does not exist.'
  }
}

function Import-PSMod {
  [CmdletBinding()]
  param (
    [Parameter()]
    $Name,
    [switch]$Local,
    [string]$RequiredVersion
  )

  if ($Local) {
    $LocalModule = "$env:PSMODS\$Name"
    if (Test-Path $LocalModule) {
      Import-Module -Name $LocalModule
    }
  }
  else {
    if (Get-Module $Name -ListAvailable) {
      Import-Module -Name $Name
    }
    else {
      Install-Module -Name $Name -Scope CurrentUser -Force
    }
    return
  }
}

function Import-ScoopModule {
  param (
    [Parameter()]
    $Name
  )
  Import-Module "$($(Get-Item $(Get-Command scoop.ps1).Path).Directory.Parent.FullName)\modules\$Name"
}

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
    Write-Err $Path Magenta ' does not exist.'
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
    Write-Err $Path Magenta ' does not exist.'
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
    Write-Err $Path Magenta ' does not exist.'
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

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
function prompt {
  if ($isAdmin) { '[' + (Get-Location) + '] # ' } else { '[' + (Get-Location) + '] $ ' }
}
$adminSuffix = if ($isAdmin) { ' [ADMIN]' } else { '' }
$Host.UI.RawUI.WindowTitle = "$adminSuffix PowerShell {0}" -f $PSVersionTable.PSVersion.ToString()

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

function Edit-Profile { & $env:EDITOR $PROFILE.CurrentUserAllHosts }
Set-Alias -Name ep -Value Edit-Profile

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

function Get-PubIP { (Invoke-WebRequest http://ifconfig.me/ip).Content }

function winutil { Invoke-RestMethod https://christitus.com/win | Invoke-Expression }


function trash($path) {
  $fullPath = (Resolve-Path -Path $path).Path

  if (Test-Path $fullPath) {
    $item = Get-Item $fullPath

    if ($item.PSIsContainer) {
      # Handle directory
      $parentPath = $item.Parent.FullName
    }
    else {
      # Handle file
      $parentPath = $item.DirectoryName
    }

    $shell = New-Object -ComObject 'Shell.Application'
    $shellItem = $shell.NameSpace($parentPath).ParseName($item.Name)

    if ($item) {
      $shellItem.InvokeVerb('delete')
      Write-Host "Item '$fullPath' has been moved to the Recycle Bin."
    }
    else {
      Write-Host "Error: Could not find the item '$fullPath' to trash."
    }
  }
  else {
    Write-Host "Error: Item '$fullPath' does not exist."
  }
}

# Clipboard Utilities
function cpy { Set-Clipboard $args[0] }

function pst { Get-Clipboard }

function touch($file) { '' | Out-File $file -Encoding ASCII -Force }

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

function grep($regex, $dir) {
  if ( $dir ) {
    Get-ChildItem $dir | select-string $regex
    return
  }
  $input | select-string $regex
}

function pgrep($name) { Get-Process $name }

function head {
  param($Path, $n = 10)
  Get-Content $Path -Head $n
}

function tail {
  param($Path, $n = 10, [switch]$f = $false)
  Get-Content $Path -Tail $n -Wait:$f
}

function df { get-volume }
# Directory Management
function mkcd {
  param($dir) mkdir $dir -Force; Set-Location $dir
}

function sysinfo { Get-ComputerInfo }

function unzip ($file) {
  Write-Output('Extracting', $file, 'to', $pwd)
  $fullFile = Get-ChildItem -Path $pwd -Filter $file | ForEach-Object { $_.FullName }
  Expand-Archive -Path $fullFile -DestinationPath $pwd
}

function docs {
  $docs = if (([Environment]::GetFolderPath('MyDocuments'))) { ([Environment]::GetFolderPath('MyDocuments')) } else { $HOME + '\Documents' }
  Set-Location -Path $docs
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

function mdat($1) { ich -y -a square -S black -e -d 1 --rst --csv --theme catppuccin-mocha -m $1 }

function q { Exit }

function .d { Set-Location "$env:DOTS" }

function cdev { Set-Location "$env:DEV" }
Set-Alias -Name dev -Value cdev

function .. { Set-Location '..' }
function ... { Set-Location '...' }
function .... { Set-Location '....' }
function ..... { Set-Location '.....' }

function Get-Functions { Get-ChildItem function:\ }

function find-ln { Get-ChildItem | Where-Object { $_.Attributes -match 'ReparsePoint' } }

function nerdfonts {
  param (
    [Parameter(ValueFromRemainingArguments = $true)]
    $OptionalParameters
  )
  & ([scriptblock]::Create((Invoke-WebRequest 'https://to.loredo.me/Install-NerdFont.ps1').Content)) @OptionalParameters
}

function Show-Help {
  $helpText = @"
$($PSStyle.Foreground.Cyan)PowerShell Profile Help$($PSStyle.Reset)
$($PSStyle.Foreground.Yellow)=======================$($PSStyle.Reset)

$($PSStyle.Foreground.Green)Update-Profile$($PSStyle.Reset) - Checks for profile updates from a remote repository and updates if necessary.

$($PSStyle.Foreground.Green)Update-PowerShell$($PSStyle.Reset) - Checks for the latest PowerShell release and updates if a new version is available.

$($PSStyle.Foreground.Green)Edit-Profile$($PSStyle.Reset) - Opens the current user's profile for editing using the configured editor.

$($PSStyle.Foreground.Green)touch$($PSStyle.Reset) <file> - Creates a new empty file.

$($PSStyle.Foreground.Green)ff$($PSStyle.Reset) <name> - Finds files recursively with the specified name.

$($PSStyle.Foreground.Green)Get-PubIP$($PSStyle.Reset) - Retrieves the public IP address of the machine.

$($PSStyle.Foreground.Green)winutil$($PSStyle.Reset) - Runs the latest WinUtil full-release script from Chris Titus Tech.

$($PSStyle.Foreground.Green)winutildev$($PSStyle.Reset) - Runs the latest WinUtil pre-release script from Chris Titus Tech.

$($PSStyle.Foreground.Green)uptime$($PSStyle.Reset) - Displays the system uptime.

$($PSStyle.Foreground.Green)reload-profile$($PSStyle.Reset) - Reloads the current user's PowerShell profile.

$($PSStyle.Foreground.Green)unzip$($PSStyle.Reset) <file> - Extracts a zip file to the current directory.

$($PSStyle.Foreground.Green)hb$($PSStyle.Reset) <file> - Uploads the specified file's content to a hastebin-like service and returns the URL.

$($PSStyle.Foreground.Green)grep$($PSStyle.Reset) <regex> [dir] - Searches for a regex pattern in files within the specified directory or from the pipeline input.

$($PSStyle.Foreground.Green)df$($PSStyle.Reset) - Displays information about volumes.

$($PSStyle.Foreground.Green)sed$($PSStyle.Reset) <file> <find> <replace> - Replaces text in a file.

$($PSStyle.Foreground.Green)which$($PSStyle.Reset) <name> - Shows the path of the command.

$($PSStyle.Foreground.Green)export$($PSStyle.Reset) <name> <value> - Sets an environment variable.

$($PSStyle.Foreground.Green)pkill$($PSStyle.Reset) <name> - Kills processes by name.

$($PSStyle.Foreground.Green)pgrep$($PSStyle.Reset) <name> - Lists processes by name.

$($PSStyle.Foreground.Green)head$($PSStyle.Reset) <path> [n] - Displays the first n lines of a file (default 10).

$($PSStyle.Foreground.Green)tail$($PSStyle.Reset) <path> [n] - Displays the last n lines of a file (default 10).

$($PSStyle.Foreground.Green)nf$($PSStyle.Reset) <name> - Creates a new file with the specified name.

$($PSStyle.Foreground.Green)mkcd$($PSStyle.Reset) <dir> - Creates and changes to a new directory.

$($PSStyle.Foreground.Green)docs$($PSStyle.Reset) - Changes the current directory to the user's Documents folder.

$($PSStyle.Foreground.Green)dtop$($PSStyle.Reset) - Changes the current directory to the user's Desktop folder.

$($PSStyle.Foreground.Green)ep$($PSStyle.Reset) - Opens the profile for editing.

$($PSStyle.Foreground.Green)k9$($PSStyle.Reset) <name> - Kills a process by name.

$($PSStyle.Foreground.Green)la$($PSStyle.Reset) - Lists all files in the current directory with detailed formatting.

$($PSStyle.Foreground.Green)ll$($PSStyle.Reset) - Lists all files, including hidden, in the current directory with detailed formatting.

$($PSStyle.Foreground.Green)gs$($PSStyle.Reset) - Shortcut for 'git status'.

$($PSStyle.Foreground.Green)ga$($PSStyle.Reset) - Shortcut for 'git add .'.

$($PSStyle.Foreground.Green)gc$($PSStyle.Reset) <message> - Shortcut for 'git commit -m'.

$($PSStyle.Foreground.Green)gp$($PSStyle.Reset) - Shortcut for 'git push'.

$($PSStyle.Foreground.Green)g$($PSStyle.Reset) - Changes to the GitHub directory.

$($PSStyle.Foreground.Green)gcom$($PSStyle.Reset) <message> - Adds all changes and commits with the specified message.

$($PSStyle.Foreground.Green)lazyg$($PSStyle.Reset) <message> - Adds all changes, commits with the specified message, and pushes to the remote repository.

$($PSStyle.Foreground.Green)sysinfo$($PSStyle.Reset) - Displays detailed system information.

$($PSStyle.Foreground.Green)flushdns$($PSStyle.Reset) - Clears the DNS cache.

$($PSStyle.Foreground.Green)cpy$($PSStyle.Reset) <text> - Copies the specified text to the clipboard.

$($PSStyle.Foreground.Green)pst$($PSStyle.Reset) - Retrieves text from the clipboard.

Use '$($PSStyle.Foreground.Magenta)Show-Help$($PSStyle.Reset)' to display this help message.
"@
  Write-Host $helpText
}

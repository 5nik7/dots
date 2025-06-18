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
      Import-Module -Name $LocalModule -Global
    }
  }
  else {
    if (Get-Module $Name -ListAvailable) {
      Import-Module -Name $Name -Global
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
  Import-Module "$($(Get-Item $(Get-Command scoop.ps1).Path).Directory.Parent.FullName)\modules\$Name" -Global
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
  $trashicon = ''
  if (-not $path) {
    Write-Host -foregroundColor Blue -NoNewline "$trashicon Usage: "
    Write-Host -foregroundColor Cyan -NoNewline "trash "
    Write-Host -foregroundColor White "<path-to-file-or-directory>"
    return
  }

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
      Write-Host -foregroundColor Green "$trashicon Item '$fullPath' has been moved to the Recycle Bin."
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

function mdat($1) { rich --text-full -y -a square -S black -e -d 1 --theme catppuccin-mocha -m $1 }
function mdpre($1) { rich --text-full -y -e -d 1 --theme catppuccin-mocha -m $1 }

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

function Remove-DuplicatePSReadlineHistory {
  $historyPath = (Get-PSReadLineOption).HistorySavePath

  # backup
  $directory = (Get-Item $historyPath).DirectoryName
  $basename = (Get-Item $historyPath).Basename
  $extension = (Get-Item $historyPath).Extension
  $timestamp = (Get-Date).ToString('yyyy-MM-ddTHH-mm-ssZ')

  $backupPath = "$directory\$basename-$timestamp-backup$extension"

  Copy-Item $historyPath $backupPath

  # remove duplicate history
  $uniqueHistory = @()
  $history = Get-Content $historyPath

  [Array]::Reverse($history)

  $history | ForEach-Object {
    if (-Not $uniqueHistory.Contains($_)) {
      $uniqueHistory += $_
    }
  }

  [Array]::Reverse($uniqueHistory)

  Clear-Content $historyPath

  $uniqueHistory | Out-File -Append $historyPath
}

Set-Alias -Name fixhistory -Value Remove-DuplicatePSReadlineHistory

function Set-FuzzyOpts {
  param (
    [switch]$d,
    [hashtable]$opts,
    [hashtable]$colors,
    [hashtable]$keybinds,
    [string]$previewlabel,
    [string]$borderlabel,
    [string]$inputlabel,
    [string]$listlabel,
    [string]$headerlabel
  )
  $env:FZF_DEFAULT_OPTS = ''

  $Env:FZF_FILE_OPTS = "--preview=`"bat --style=numbers --color=always {}`""
  $Env:FZF_DIRECTORY_OPTS = "--preview=`"eza -la --color=always --group-directories-first --icons --no-permissions --no-time --no-filesize --no-user --git-repos --git --follow-symlinks --no-quotes --stdin {}`""

  if ($d) {
    $Env:FZF_DEFAULT_COMMAND = 'fd --type d --strip-cwd-prefix --hidden --exclude .git'
    $previewString = $Env:FZF_DIRECTORY_OPTS
  }
  else {
    $Env:FZF_DEFAULT_COMMAND = 'fd --type f --strip-cwd-prefix --hidden --exclude .git'
    $previewString = $Env:FZF_FILE_OPTS
  }
  try {
    # Default opts
    $defaultOpts = @{
      style         = 'minimal'
      layout        = 'reverse'
      height        = '~90%'
      margin        = '0'
      border        = 'none'
      previewwindow = 'right:70%:hidden'
      prompt        = @{ symbol = ' > ' }
      pointer       = @{ symbol = '' }
      marker        = @{ symbol = '┃' }
    }
    if ($opts) {
      foreach ($k in $opts.Keys) { $defaultOpts[$k] = $opts[$k] }
    }
    $opts = $defaultOpts

    # Default colors
    $defaultColors = @{
      'fg'             = $Flavor.Subtext0.Hex()
      'hl'             = ($Flavor.Green.Hex() + ':underline')
      'fg+'            = ($Flavor.Lavender.Hex() + ':bold:reverse')
      'hl+'            = ($Flavor.Green.Hex() + ':bold:underline:reverse')
      'bg'             = 'transparent'
      'bg+'            = 'transparent'
      'preview-bg'     = 'transparent'
      'list-bg'        = 'transparent'
      'input-bg'       = 'transparent'
      'preview-border' = $Flavor.Surface0.Hex()
      'list-border'    = $Flavor.Surface0.Hex()
      'border'         = $Flavor.Surface0.Hex()
      'input-border'   = $Flavor.Surface1.Hex()
      'pointer'        = $Flavor.Base.Hex()
      'label'          = $Flavor.Surface2.Hex()
      'gutter'         = 'transparent'
      'marker'         = $Flavor.Yellow.Hex()
      'spinner'        = $Flavor.Surface1.Hex()
      'separator'      = $Flavor.Base.Hex()
      'query'          = $Flavor.Text.Hex()
      'info'           = $Flavor.Surface1.Hex()
      'prompt'         = $Flavor.Surface1.Hex()
      'preview-label'  = $Flavor.Surface0.Hex()
      'selected-bg'    = $Flavor.Mantle.Hex()
    }
    if ($colors) {
      foreach ($k in $colors.Keys) { $defaultColors[$k] = $colors[$k] }
    }
    $colors = $defaultColors

    # Default keybinds
    $defaultKeybinds = @{
      'ctrl-x' = 'toggle-preview'
    }
    if ($keybinds) {
      foreach ($k in $keybinds.Keys) { $defaultKeybinds[$k] = $keybinds[$k] }
    }
    $keybinds = $defaultKeybinds

    $colorString = ($colors.GetEnumerator() | ForEach-Object {
        if ($_.Value -eq 'transparent') {
          $_.Value = '-1'
        }
        "$($_.Key):$($_.Value)"
      }) -join ','
    $colorArg = "--color $colorString"

    $bindString = ($keybinds.GetEnumerator() | ForEach-Object { "$($_.Key):$($_.Value)" }) -join ','
    $keybindsArg = "--bind $bindString"

    $key_mapping = @{
      minheight     = 'min-height'
      listborder    = 'list-border'
      inputborder   = 'input-border'
      previewwindow = 'preview-window'
    }

    $optsString = ($opts.GetEnumerator() | ForEach-Object {
        $key = if ($key_mapping.ContainsKey($_.Key)) {
          $key_mapping[$_.Key]
        }
        else {
          $_.Key
        }
        if ($_.Value.enabled -eq $false) {
          '--no-{0}' -f $key
        }
        elseif ($_.Value.symbol) {
          "--{0} '{1}'" -f $key, $_.Value.symbol
        }
        else {
          '--{0} {1}' -f $key, $_.Value
        }
      }) -join ' '

    $FZF_DEFAULT_OPTS = $optsString + ' ' + $colorArg + ' ' + $keybindsArg + ' ' + $previewString
    if ($previewlabel) {
      $FZF_DEFAULT_OPTS += " --preview-label=' $previewlabel '"
    }
    if ($borderlabel) {
      $FZF_DEFAULT_OPTS += " --border-label=' $borderlabel '"
    }
    if ($inputlabel) {
      $FZF_DEFAULT_OPTS += " --input-label=' $inputlabel '"
    }
    if ($listlabel) {
      $FZF_DEFAULT_OPTS += " --list-label=' $listlabel '"
    }
    if ($headerlabel) {
      $FZF_DEFAULT_OPTS += " --header-label=' $headerlabel '"
    }
    $env:FZF_DEFAULT_OPTS = $FZF_DEFAULT_OPTS
  }
  catch {
    Write-Host "Error: $_"
  }
}


# Example usage:
# Set-FuzzyColor 'fg+' ($Flavor.Lavender.Hex() + ':underline:reverse')
function Set-FuzzyColor {
  param (
    [Parameter(Mandatory)]
    [string]$Key,
    [Parameter(Mandatory)]
    [string]$Value
  )
  $fuzzyOpts = @{ colors = @{ $Key = $Value } }
  Set-FuzzyOpts @fuzzyOpts
}

# Example usage:
#   Set-FuzzyKeybind 'ctrl-y' 'accept'
function Set-FuzzyKeybind {
  param (
    [Parameter(Mandatory)]
    [string]$Key,
    [Parameter(Mandatory)]
    [string]$Value
  )
  $fuzzyOpts = @{ keybinds = @{ $Key = $Value } }
  Set-FuzzyOpts @fuzzyOpts
}

function Set-FuzzyOpt {
  param (
    [Parameter(Mandatory)]
    [string]$Key,
    [Parameter(Mandatory)]
    [object]$Value
  )
  $fuzzyOpts = @{ opts = @{ $Key = $Value } }
  Set-FuzzyOpts @fuzzyOpts
}
$env:DOTS = "$HOME\dots"

$env:STARSHIP_CONFIG = "$env:DOTS\configs\starship\starship.toml"
$env:STARSHIP_THEMES = "$env:DOTS\configs\starship\themes"

function Test-CommandExists {
  param($command)
  $exists = $null -ne (Get-Command $command -ErrorAction SilentlyContinue)
  return $exists
}

$EDITOR = if (Test-CommandExists code) { 'code' }
elseif (Test-CommandExists nvim) { 'nvim' }
elseif (Test-CommandExists vim) { 'vim' }
elseif (Test-CommandExists vi) { 'vi' }
else { 'notepad' }
$env:EDITOR = $EDITOR
function Edit-Item
{
  param (
    [string]$Path = $PWD
  )
  if ($Path)
  {
    & $env:EDITOR $Path
  }
  else
  {
    & $env:EDITOR
  }
}
Set-Alias -Name edit -Value Edit-Item
Set-Alias -Name e -Value Edit-Item

Import-Module blastoff

function d {
    $tmp = (New-TemporaryFile).FullName
    yazi.exe $args --cwd-file="$tmp"
    $cwd = Get-Content -Path $tmp -Encoding UTF8
    if (-not [String]::IsNullOrEmpty($cwd) -and $cwd -ne $PWD.Path) {
        Set-Location -LiteralPath (Resolve-Path -LiteralPath $cwd).Path
    }
    Remove-Item -Path $tmp
}

function c {
    Clear-Host
}

function Invoke-eza {
    param (
        [Parameter(ValueFromRemainingArguments = $true)]
        $Args
    )
    eza --icons=always --group-directories-first --git --git-repos @Args
}

Set-Alias -Name ls -Value Invoke-eza

function env {
    Get-ChildItem env:
}

function RepeatString {
    param(
        [string]$Text,
        [int]$Count
    )

    if ($Count -le 0 -or $null -eq $Text) {
        return ''
    }

    $Text * $Count
}

Import-Module Terminal-Icons
Import-Module PSFzf
Set-PSReadLineKeyHandler -Key Tab -ScriptBlock { Invoke-FzfTabCompletion }
Set-PsFzfOption -TabExpansion

Import-Module Catppuccin
$Flavor = $Catppuccin['Mocha']

# $ENV:FZF_DEFAULT_OPTS = @"
# --color=bg+:$($Flavor.Surface0),bg:$($Flavor.Base),spinner:$($Flavor.Rosewater)
# --color=hl:$($Flavor.Red),fg:$($Flavor.Text),header:$($Flavor.Red)
# --color=info:$($Flavor.Mauve),pointer:$($Flavor.Rosewater),marker:$($Flavor.Rosewater)
# --color=fg+:$($Flavor.Text),prompt:$($Flavor.Mauve),hl+:$($Flavor.Red)
# --color=border:$($Flavor.Surface2)
# "@

# $Colors = @{
# 	# Largely based on the Code Editor style guide
# 	# Emphasis, ListPrediction and ListPredictionSelected are inspired by the Catppuccin fzf theme
	
# 	# Powershell colours
# 	ContinuationPrompt     = $Flavor.Teal.Foreground()
# 	Emphasis               = $Flavor.Red.Foreground()
# 	Selection              = $Flavor.Surface0.Background()
	
# 	# PSReadLine prediction colours
# 	InlinePrediction       = $Flavor.Overlay0.Foreground()
# 	ListPrediction         = $Flavor.Mauve.Foreground()
# 	ListPredictionSelected = $Flavor.Surface0.Background()

# 	# Syntax highlighting
# 	Command                = $Flavor.Blue.Foreground()
# 	Comment                = $Flavor.Overlay0.Foreground()
# 	Default                = $Flavor.Text.Foreground()
# 	Error                  = $Flavor.Red.Foreground()
# 	Keyword                = $Flavor.Mauve.Foreground()
# 	Member                 = $Flavor.Rosewater.Foreground()
# 	Number                 = $Flavor.Peach.Foreground()
# 	Operator               = $Flavor.Sky.Foreground()
# 	Parameter              = $Flavor.Pink.Foreground()
# 	String                 = $Flavor.Green.Foreground()
# 	Type                   = $Flavor.Yellow.Foreground()
# 	Variable               = $Flavor.Lavender.Foreground()
# }

# Set-PSReadLineOption -Colors $Colors

# $PSStyle.Formatting.Debug = $Flavor.Sky.Foreground()
# $PSStyle.Formatting.Error = $Flavor.Red.Foreground()
# $PSStyle.Formatting.ErrorAccent = $Flavor.Blue.Foreground()
# $PSStyle.Formatting.FormatAccent = $Flavor.Teal.Foreground()
# $PSStyle.Formatting.TableHeader = $Flavor.Rosewater.Foreground()
# $PSStyle.Formatting.Verbose = $Flavor.Yellow.Foreground()
# $PSStyle.Formatting.Warning = $Flavor.Peach.Foreground()




function Import-ScoopModule {
  param (
    [Parameter()]
    $Name
  )
  Import-Module "$($(Get-Item $(Get-Command scoop.ps1).Path).Directory.Parent.FullName)\modules\$Name" -Global
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

function datb($1) {
  if ($catppuccin.Macchiato.Base) { $border = $catppuccin.Macchiato.Base.ToString() } else { $border = 'black' };
  rich -y -a square -S $border -d 1 --theme catppuccin-mocha -m $1
}
function dat($1) { rich --pager --text-full -y -e -d 1 -m $1 }

function open {
  param (
    [Parameter(Mandatory = $true, ValueFromRemainingArguments = $true)]
    [string[]]$Paths
  )
  foreach ($path in $Paths) {
    Start-Process $path
  }
}

function google {
  param (
    [Parameter(Mandatory = $true, ValueFromRemainingArguments = $true)]
    [string[]]$QueryParts
  )
  $query = [string]::Join(' ', $QueryParts)
  $encodedQuery = [System.Web.HttpUtility]::UrlEncode($query)
  $url = "https://www.google.com/search?q=$encodedQuery"
  Start-Process $url
}

function q { Exit }

function .d { Set-Location "$env:DOTS" }

function cdev { Set-Location "$env:DEV" }
Set-Alias -Name dev -Value cdev

function .. { Set-Location '..' }
function ... { Set-Location '..\..' }
function .... { Set-Location '..\..\..' }
function ..... { Set-Location '..\..\..\..' }

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

# function Set-FuzzyOpts {
#   param (
#     [switch]$d,
#     [hashtable]$opts,
#     [hashtable]$colors,
#     [hashtable]$keybinds,
#     [string]$previewlabel,
#     [string]$borderlabel,
#     [string]$inputlabel,
#     [string]$listlabel,
#     [string]$headerlabel
#   )
#   $env:FZF_DEFAULT_OPTS = ''

#   $Env:FZF_FILE_OPTS = "--preview=`"bat --style=numbers --color=always {}`""
#   $Env:FZF_DIRECTORY_OPTS = "--preview=`"eza -la --color=always --group-directories-first --icons --no-permissions --no-time --no-filesize --no-user --git-repos --git --follow-symlinks --no-quotes --stdin {}`""

#   if ($d) {
#     $Env:FZF_DEFAULT_COMMAND = 'fd --type d --strip-cwd-prefix --hidden --exclude .git'
#     $previewString = $Env:FZF_DIRECTORY_OPTS
#   }
#   else {
#     $Env:FZF_DEFAULT_COMMAND = 'fd --type f --strip-cwd-prefix --hidden --exclude .git'
#     $previewString = $Env:FZF_FILE_OPTS
#   }
#   try {
#     # Default opts
#     $defaultOpts = @{
#       style         = 'default'
#       layout        = 'reverse'
#       height        = '~90%'
#       margin        = '0'
#       border        = 'none'
#       previewwindow = 'right:70%:hidden:border-sharp'
#       prompt        = @{ symbol = ' 󰅂 ' }
#       pointer       = @{ symbol = '┃' }
#       marker        = @{ symbol = '┃' }
#       gutter        = @{ symbol = '┃' }
#       gutterraw     = @{ symbol = '┃' }
#     }
#     if ($opts) {
#       foreach ($k in $opts.Keys) { $defaultOpts[$k] = $opts[$k] }
#     }
#     $opts = $defaultOpts

#     # Default colors
#     $defaultColors = @{
#       'fg'             = $Flavor.Subtext0.Hex()
#       'hl'             = ($Flavor.Teal.Hex() + ':bold:underline')
#       'fg+'            = ($Flavor.Text.Hex() + ':bold:reverse')
#       'hl+'            = ($Flavor.Teal.Hex() + ':bold:reverse')
#       'bg'             = 'transparent'
#       'bg+'            = 'transparent'
#       'preview-bg'     = 'transparent'
#       'list-bg'        = 'transparent'
#       'input-bg'       = 'transparent'
#       'preview-border' = $Flavor.Surface0.Hex()
#       'list-border'    = $Flavor.Surface0.Hex()
#       'border'         = $Flavor.Surface0.Hex()
#       'input-border'   = $Flavor.surface0.Hex()
#       'pointer'        = $Flavor.surface1.Hex()
#       'label'          = $Flavor.Surface2.Hex()
#       'gutter'         = $Flavor.Surface0.Hex()
#       'marker'         = $Flavor.Yellow.Hex()
#       'spinner'        = $Flavor.Surface1.Hex()
#       'separator'      = $Flavor.Base.Hex()
#       'query'          = $Flavor.Text.Hex()
#       'info'           = $Flavor.Surface1.Hex()
#       'prompt'         = $Flavor.Surface1.Hex()
#       'preview-label'  = $Flavor.Surface0.Hex()
#       'nomatch'        = 'strip:' + $Flavor.Surface0.Hex() + ':italic'
#     }
#     if ($colors) {
#       foreach ($k in $colors.Keys) { $defaultColors[$k] = $colors[$k] }
#     }
#     $colors = $defaultColors

#     # Default keybinds
#     $defaultKeybinds = @{
#       'ctrl-x'     = 'toggle-preview'
#       'ctrl-alt-r' = 'toggle-raw'
#       'up'         = 'up-match'
#       'down'       = 'down-match'
#     }
#     if ($keybinds) {
#       foreach ($k in $keybinds.Keys) { $defaultKeybinds[$k] = $keybinds[$k] }
#     }
#     $keybinds = $defaultKeybinds

#     $colorString = ($colors.GetEnumerator() | ForEach-Object {
#         if ($_.Value -eq 'transparent') {
#           $_.Value = '-1'
#         }
#         "$($_.Key):$($_.Value)"
#       }) -join ','
#     $colorArg = "--color $colorString"

#     $bindString = ($keybinds.GetEnumerator() | ForEach-Object { "$($_.Key):$($_.Value)" }) -join ','
#     $keybindsArg = "--bind $bindString"

#     $key_mapping = @{
#       minheight     = 'min-height'
#       listborder    = 'list-border'
#       inputborder   = 'input-border'
#       previewwindow = 'preview-window'
#       gutterraw     = 'gutter-raw'
#     }

#     $optsString = ($opts.GetEnumerator() | ForEach-Object {
#         $key = if ($key_mapping.ContainsKey($_.Key)) {
#           $key_mapping[$_.Key]
#         }
#         else {
#           $_.Key
#         }
#         if ($_.Value.enabled -eq $false) {
#           '--no-{0}' -f $key
#         }
#         elseif ($_.Value.symbol) {
#           "--{0} '{1}'" -f $key, $_.Value.symbol
#         }
#         else {
#           '--{0} {1}' -f $key, $_.Value
#         }
#       }) -join ' '

#     $FZF_DEFAULT_OPTS = $optsString + ' ' + $colorArg + ' ' + $keybindsArg + ' ' + $previewString
#     if ($previewlabel) {
#       $FZF_DEFAULT_OPTS += " --preview-label=' $previewlabel '"
#     }
#     if ($borderlabel) {
#       $FZF_DEFAULT_OPTS += " --border-label=' $borderlabel '"
#     }
#     if ($inputlabel) {
#       $FZF_DEFAULT_OPTS += " --input-label=' $inputlabel '"
#     }
#     if ($listlabel) {
#       $FZF_DEFAULT_OPTS += " --list-label=' $listlabel '"
#     }
#     if ($headerlabel) {
#       $FZF_DEFAULT_OPTS += " --header-label=' $headerlabel '"
#     }
#     $env:FZF_DEFAULT_OPTS = $FZF_DEFAULT_OPTS
#   }
#   catch {
#     Write-Host "Error: $_"
#   }
# }


# # Example usage:
# # Set-FuzzyColor 'fg+' ($Flavor.Lavender.Hex() + ':underline:reverse')
# function Set-FuzzyColor {
#   param (
#     [Parameter(Mandatory)]
#     [string]$Key,
#     [Parameter(Mandatory)]
#     [string]$Value
#   )
#   $fuzzyOpts = @{ colors = @{ $Key = $Value } }
#   Set-FuzzyOpts @fuzzyOpts
# }

# # Example usage:
# #   Set-FuzzyKeybind 'ctrl-y' 'accept'
# function Set-FuzzyKeybind {
#   param (
#     [Parameter(Mandatory)]
#     [string]$Key,
#     [Parameter(Mandatory)]
#     [string]$Value
#   )
#   $fuzzyOpts = @{ keybinds = @{ $Key = $Value } }
#   Set-FuzzyOpts @fuzzyOpts
# }

# function Set-FuzzyOpt {
#   param (
#     [Parameter(Mandatory)]
#     [string]$Key,
#     [Parameter(Mandatory)]
#     [object]$Value
#   )
#   $fuzzyOpts = @{ opts = @{ $Key = $Value } }
#   Set-FuzzyOpts @fuzzyOpts
# }

function git_all {
  param(
    [Parameter(ValueFromRemainingArguments = $true)]
    $Args
  )
  $gitusername = git config get --global user.name
  if (Test-Path .git) {
    # Check remote access before running commands
    $hasAccess = $true
    $remoteUrl = git remote get-url origin 2>$null
    if (-not $remoteUrl -or ($remoteUrl -notmatch $gitusername)) {
      # Write-Host "Remote does not contain username '$gitusername'. Cannot run git commands." -ForegroundColor Yellow
      return
    }
    try {
      git ls-remote > $null 2>&1
    }
    catch {
      $hasAccess = $false
    }
    if (-not $hasAccess) {
      # Write-Host "Skipping main repo (no remote access or permission denied)" -ForegroundColor Yellow
      return
    }
    git @Args
    # Get submodule paths from .gitmodules
    $submodules = @()
    if (Test-Path .gitmodules) {
      $submodules = git config --file .gitmodules --get-regexp path | ForEach-Object {
        $_ -replace '^[^ ]+ ', ''
      }
    }
    foreach ($sub in $submodules) {
      if (Test-Path $sub) {
        Push-Location $sub
        # Try a harmless git command to check access
        $subHasAccess = $true
        $subRemoteUrl = git remote get-url origin 2>$null
        if (-not $subRemoteUrl -or ($subRemoteUrl -notmatch $gitusername)) {
          # Write-Host "Submodule '$sub' remote does not contain username '$gitusername'. Skipping." -ForegroundColor Yellow
          Pop-Location
          continue
        }
        try {
          git ls-remote > $null 2>&1
        }
        catch {
          $subHasAccess = $false
        }
        if ($subHasAccess) {
          git @Args
        }
        else {
          # Write-Host "Skipping submodule '$sub' (no permission or inaccessible)" -ForegroundColor Yellow
        }
        Pop-Location
      }
    }
  }
  else {
    Write-Error 'This directory does not contain a .git directory'
  }
}

function gup {
  param(
    [Parameter(Position = 0)]
    [string]$Message,
    [switch]$All
  )
  $gitusername = git config get --global user.name
  if (Test-Path .git) {
    $remoteUrl = git remote get-url origin 2>$null
    if (-not $remoteUrl -or ($remoteUrl -notmatch $gitusername)) {
      # Write-Host "Remote does not contain username '$gitusername'. Cannot push or fetch from remote." -ForegroundColor Yellow
      return
    }
    $commitMessage = if ($Message) { $Message } else { "Update @ $(Get-Date -Format 'MM-dd-yyyy HH:mm')" }
    if ($All) {
      git_all add .
      # Check for staged changes
      $status = git_all diff --cached --name-only
      if ($status) {
        git_all commit -m "$commitMessage"
        git_all push
      }
      else {
        Write-Host "No changes to commit." -ForegroundColor Yellow
      }
    }
    else {
      git add .
      $status = git diff --cached --name-only
      if ($status) {
        git commit -m "$commitMessage"
        git push
      }
      else {
        Write-Host "No changes to commit." -ForegroundColor Yellow
      }
    }
  }
  else {
    Write-Error 'This directory does not contain a .git directory'
  }
}

function New-Backup
{
  <#
    .SYNOPSIS
        Creates a backup of the target file or directory.
    .DESCRIPTION
        This function creates a backup of the specified target file or directory. The backup is named with the current date and time.
    .PARAMETER target
        Specifies the target file or directory to backup.
    .PARAMETER copy
        If specified, the target will be copied instead of moved.
    .PARAMETER store
        If specified, the backup will be stored in ~/.bakstore instead of the same directory.
    .EXAMPLE
        New-Backup -target "$env:USERPROFILE\Documents\file.txt"
        # This will create a backup of the specified file.
    .NOTES
        Author: njen
        Version: 1.0.2
    #>
  param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string] $target,
    [switch] $store,
    [switch] $copy
  )

  $target = if (Resolve-Path $target) { Resolve-Path $target } else { $target }
  $item = Get-Item $target
  $targetpath = $item.FullName

  if (!(Test-Path $targetpath))
  {
    Write-Error "$targetpath does not exist."
    return
  }
  $tarname = $item.Name
  $targetname = $tarname.ToString()
  $targetdir = $item.DirectoryName | ForEach-Object { Resolve-Path $_ }
  $bakDate = Get-Date -Format 'MM-dd-yyyy-HH.mm.ss'
  $backupname = "$targetname.$bakDate.bak"
  
  if ($store)
  {
    $bakstore = "$HOME\.bakstore"
    if (!(Test-Path $bakstore))
    {
      New-Item -ItemType Directory -Path $bakstore -ErrorAction Stop | Out-Null
    }
    $backupFilePath = Join-Path "$bakstore" + "$backupname"
  } else {
    $backupFilePath = Join-Path "$targetdir" + "$backupname"
  }

  if ($copy)
  {
    if ($item.PSIsContainer)
    {
      Copy-Item -Path $target -Destination $backupFilePath -Recurse -ErrorAction Stop | Out-Null
    }
    else
    {
      Copy-Item -Path $target -Destination $backupFilePath -ErrorAction Stop | Out-Null
    }
  }
  else
  {
    if ($item.PSIsContainer)
    {
      Move-Item -Path $target -Destination $backupFilePath -ErrorAction Stop | Out-Null
    }
    else
    {
      Move-Item -Path $target -Destination $backupFilePath -ErrorAction Stop | Out-Null
    }
  }

  Write-Host "Backup created: $backupFilePath"
}

try { if (Get-Command vivid -ErrorAction SilentlyContinue) { $env:LS_COLORS = "$(vivid generate tokyonight-night)" } } catch { }

Invoke-Expression (@(starship completions powershell) -replace " ''\)$"," ' ')" -join "`n")

Invoke-Expression (@(gh completion -s powershell) -replace " ''\)$"," ' ')" -join "`n")

Invoke-Expression (@(bat --completion ps1) -replace " ''\)$"," ' ')" -join "`n")

Invoke-Expression (@(uv generate-shell-completion powershell) -replace " ''\)$"," ' ')" -join "`n")

Invoke-Expression (@(uvx --generate-shell-completion powershell) -replace " ''\)$"," ' ')" -join "`n")

Register-ArgumentCompleter -Native -CommandName winget -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)
        [Console]::InputEncoding = [Console]::OutputEncoding = $OutputEncoding = [System.Text.Utf8Encoding]::new()
        $Local:word = $wordToComplete.Replace('"', '""')
        $Local:ast = $commandAst.ToString().Replace('"', '""')
        winget complete --word="$Local:word" --commandline "$Local:ast" --position $cursorPosition | ForEach-Object {
            [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
        }
}

Import-Module pscompletions

Invoke-Expression (&starship init powershell)

Invoke-Expression "$(vfox activate pwsh)"

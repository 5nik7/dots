$DOTS = "$HOME\dots"
$env:DOTS = $DOTS
$Global:DOTS = $DOTS

$DOTFILES = "$DOTS\configs"
$env:DOTFILES = $DOTFILES
$Global:DOTFILES = $DOTFILES

$DOTSBIN = "$OOTS\bin"
$env:DOTSBIN = $DOTSBIN
$Global:DOTSBIN = $DOTSBIN

$DOTSCRIPTS = "$OOTS\scripts"
$env:DOTSCRIPTS = $DOTSCRIPTS
$Global:DOTSCRIPTS = $DOTSCRIPTS

$env:STARSHIP_CONFIG = "$env:DOTFILES\starship\starship.toml"
$env:STARSHIP_DIR = [System.IO.Path]::GetDirectoryName($env:STARSHIP_CONFIG)
$env:STARSHIP_THEMES = "$env:DOTFILES\starship\themes"

function Test-CommandExists {
  param($command)
  $exists = $null -ne (Get-Command $command -ErrorAction SilentlyContinue)
  return $exists
}

$EDITOR = if (Test-CommandExists code) { 'nvim' }
elseif (Test-CommandExists nvim) { 'code' }
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

if (Test-CommandExists lazygit) {
  Set-Alias -Name lg -Value lazygit.exe
}

if (Test-CommandExists git) {
  Set-Alias -Name g -Value git
}

Import-Module blastoff

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

Set-Alias -Name ls -Value Invoke-eza -Option AllScope

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

function Edit-Profile { & $env:EDITOR $PROFILE.CurrentUserAllHosts }
Set-Alias -Name ep -Value Edit-Profile

if (Test-CommandExists yazi) {
  function y {
    $tmp = (New-TemporaryFile).FullName
    yazi.exe $args --cwd-file="$tmp"
    $cwd = Get-Content -Path $tmp -Encoding UTF8
    if ($cwd -and $cwd -ne $PWD.Path -and (Test-Path -LiteralPath $cwd -PathType Container)) {
      Set-Location -LiteralPath (Resolve-Path -LiteralPath $cwd).Path
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
function cpy { clip.exe }

function pst { Get-Clipboard }

function touch($file) { '' | Out-File $file -Encoding ASCII -Force }

function export($name, $value) {
  set-item -force -path "env:$name" -value $value;
}

function pkill($name) {
  Get-Process $name -ErrorAction SilentlyContinue | Stop-Process
}

function greps($regex, $dir) {
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
function .df { Set-Location "$env:DOTFILES" }

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

function New-Backup {
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

  if (!(Test-Path $targetpath)) {
    Write-Error "$targetpath does not exist."
    return
  }
  $tarname = $item.Name
  $targetname = $tarname.ToString()
  $targetdir = $item.DirectoryName | ForEach-Object { Resolve-Path $_ }
  $bakDate = Get-Date -Format 'MM-dd-yyyy-HH.mm.ss'
  $backupname = "$targetname.$bakDate.bak"

  if ($store) {
    $bakstore = "$HOME\.bakstore"
    if (!(Test-Path $bakstore)) {
      New-Item -ItemType Directory -Path $bakstore -ErrorAction Stop | Out-Null
    }
    $backupFilePath = Join-Path "$bakstore" + "$backupname"
  }
  else {
    $backupFilePath = Join-Path "$targetdir" + "$backupname"
  }

  if ($copy) {
    if ($item.PSIsContainer) {
      Copy-Item -Path $target -Destination $backupFilePath -Recurse -ErrorAction Stop | Out-Null
    }
    else {
      Copy-Item -Path $target -Destination $backupFilePath -ErrorAction Stop | Out-Null
    }
  }
  else {
    if ($item.PSIsContainer) {
      Move-Item -Path $target -Destination $backupFilePath -ErrorAction Stop | Out-Null
    }
    else {
      Move-Item -Path $target -Destination $backupFilePath -ErrorAction Stop | Out-Null
    }
  }

  Write-Host "Backup created: $backupFilePath"
}

try { if (Get-Command vivid -ErrorAction SilentlyContinue) { $env:LS_COLORS = "$(vivid generate tokyonight-night)" } } catch { }

Invoke-Expression (@(starship completions powershell) -replace " ''\)$", " ' ')" -join "`n")

Invoke-Expression (@(gh completion -s powershell) -replace " ''\)$", " ' ')" -join "`n")

Invoke-Expression (@(bat --completion ps1) -replace " ''\)$", " ' ')" -join "`n")

Invoke-Expression (@(uv generate-shell-completion powershell) -replace " ''\)$", " ' ')" -join "`n")

Invoke-Expression (@(uvx --generate-shell-completion powershell) -replace " ''\)$", " ' ')" -join "`n")

Register-ArgumentCompleter -Native -CommandName winget -ScriptBlock {
  param($wordToComplete, $commandAst, $cursorPosition)
  [Console]::InputEncoding = [Console]::OutputEncoding = $OutputEncoding = [System.Text.Utf8Encoding]::new()
  $Local:word = $wordToComplete.Replace('"', '""')
  $Local:ast = $commandAst.ToString().Replace('"', '""')
  winget complete --word="$Local:word" --commandline "$Local:ast" --position $cursorPosition | ForEach-Object {
    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
  }
}

# $ENV:FZF_DEFAULT_OPTS = @"
# --color=bg+:$($Flavor.Surface0),bg:$($Flavor.Base),spinner:$($Flavor.Rosewater)
# --color=hl:$($Flavor.Red),fg:$($Flavor.Text),header:$($Flavor.Red)
# --color=info:$($Flavor.Mauve),pointer:$($Flavor.Rosewater),marker:$($Flavor.Rosewater)
# --color=fg+:$($Flavor.Text),prompt:$($Flavor.Mauve),hl+:$($Flavor.Red)
# --color=border:$($Flavor.Surface2)
# "@

$PSReadLineOptions = @{
  HistoryNoDuplicates           = $true
  HistorySearchCursorMovesToEnd = $true
  HistorySearchCaseSensitive    = $false
  MaximumHistoryCount           = '50000'
  BellStyle                     = 'None'
  EditMode                      = 'Vi' # "Vi" or "Emacs" or "Windows"
  Colors                        = @{
    Command   = 'Blue'
    Comment   = 'DarkGray'
    Parameter = 'Cyan'
    String    = 'Green'
    Variable  = 'Yellow'
    # Keyword                   = "`e[92m"
    # ListPrediction            = "`e[33m"
    # ListPredictionSelected    = "`e[48;5;238m"
    # ListPredictionTooltip     = "`e[97;2;3m"
    # Member                    = "`e[37m"
    # Number                    = "`e[97m"
    # Type                      = "`e[37m"
    # Operator                  = "`e[90m"
    # ContinuationPrompt        = "`e[37m"
    # Emphasis                  = "`e[96m"
    # Error                     = "`e[91m"
  }
}

Set-PSReadLineOption @PSReadLineOptions

if ($PSEdition -eq 'Core') {
  Set-PSReadLineOption -PredictionViewStyle 'InlineView'
  Set-PSReadLineOption -Colors @{InlinePrediction = 'DarkGray' }
}


Import-Module pscompletions

if (Test-CommandExists zoxide) { Invoke-Expression (& { (zoxide init powershell | Out-String) }) }

function Invoke-Starship-PreCommand {
  # This is a workaround for a bug in starship where the prompt doesn't update after certain commands
  # that change the directory, such as 'cd' or 'd'.
  # By invoking a no-op command before each prompt, we can force starship to update the prompt with the new directory.
  $null = Get-ChildItem -Path $PWD
}

function Invoke-Starship-TransientFunction { &starship module character }
function OnViModeChangeCore {
  if ($args[0] -eq 'Command') {
    [Microsoft.PowerShell.PSConsoleReadLine]::ForwardChar()
    Write-Host -NoNewLine "`e[2 q"
  }
  else {
    Write-Host -NoNewLine "`e[5 q"
  }
}

function OnViModeChangeDesktop {
    [Microsoft.PowerShell.PSConsoleReadLine]::ForwardChar()
}

function OnViModeChangeDesktop { [Microsoft.PowerShell.PSConsoleReadLine]::InvokePrompt() }

if ($PSEdition -eq 'Core') { Set-PSReadLineOption -ViModeIndicator Script -ViModeChangeHandler $Function:OnViModeChangeCore }

if ($PSEdition -eq 'Desktop') { Set-PSReadLineOption -ViModeIndicator Script -ViModeChangeHandler $Function:OnViModeChangeDesktop }

Invoke-Expression (&starship init powershell)
Enable-TransientPrompt

Invoke-Expression "$(vfox activate pwsh)"

$ChocolateyProfile = "$env:ChocolateyInstall\helpers\chocolateyProfile.psm1"
if (Test-Path($ChocolateyProfile)) {
  Import-Module "$ChocolateyProfile"
}

(&mise activate pwsh) | Out-String | Invoke-Expression

# >>> intelligent-terminal shell-integration >>>
# Auto-generated by Intelligent Terminal. Do not edit between markers.
# Documents is resolved at runtime so this survives OneDrive Known
# Folder Move and is a silent no-op on machines without IT installed.
$__it_si = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'PowerShell\shell-integration_v6.ps1'
if (Test-Path -LiteralPath $__it_si) { . $__it_si }
Remove-Variable __it_si -ErrorAction SilentlyContinue
# <<< intelligent-terminal shell-integration <<<

# DO NOT MODIFY -- coreutils -- 60b36fc6-2d59-49df-be51-28dd2f4c3c9a
# vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
# Inlining the template into the profile shaves off ~10ms (25%).
$script:__COREUTILS__ = [System.Collections.Generic.HashSet[string]]::new(
    [string[]]@('arch','b2sum','base32','base64','basename','basenc','cat','cksum','comm','cp','csplit','cut','date','df','dirname','du','echo','env','expr','factor','false','find','fmt','fold','grep','head','hostname','join','la','link','ln','ls','md5sum','mkdir','mktemp','mv','nl','nproc','numfmt','od','paste','pathchk','pr','printenv','printf','ptx','pwd','readlink','realpath','rm','rmdir','seq','sha1sum','sha224sum','sha256sum','sha384sum','sha512sum','shuf','sleep','sort','split','stat','sum','tac','tail','tee','test','touch','tr','true','truncate','tsort','unexpand','uniq','unlink','uptime','wc','xargs','yes'),
    [System.StringComparer]::OrdinalIgnoreCase
)

$script:__COREUTILS_FAST_SKIP__ = [regex]::new(
    '\b(?:' + ($script:__COREUTILS__ -join '|') + ')\b',
    [System.Text.RegularExpressions.RegexOptions]::Compiled -bor `
        [System.Text.RegularExpressions.RegexOptions]::IgnoreCase
)

# Casting the scriptblock to Func<Ast,bool> once and reusing it avoids the
# per-FindAll scriptblock-to-delegate wrapping overhead (~1.7x faster).
$script:__COREUTILS_CMD_PREDICATE__ = [System.Func[System.Management.Automation.Language.Ast, bool]] {
    param($n) $n -is [System.Management.Automation.Language.CommandAst]
}

$script:__COREUTILS_ARG_SPECIAL__ = [char[]] @("'", '"', '`', '$')

# Wrap arguments into quotes. By being a function we can properly handle $variables.
# As per MSVCRT, any `\` before `"` must be doubled to escape them.
function global:__coreutils_q {
    param($s)
    '"' + (([string]$s) -replace '(\\*)"', '$1$1\"' -replace '(\\+)$', '$1$1') + '"'
}

# PowerShell tokenizes `*"a"*` as [BareWord] instead of the expected [DoubleQuoted, BareWord, DoubleQuoted].
# To work around that we use... regex. Group 1 = 'single', 2 = "double", 3 = `escape, 4 = bare run.
$script:__COREUTILS_ARG_RX__ = [regex]::new(
    "'((?:[^']|'')*)'|""((?:[^""``]|""""|``.)*)""|``(.)|([^'""``]+)",
    [System.Text.RegularExpressions.RegexOptions]::Compiled
)
$script:__COREUTILS_ARG_EVAL__ = [System.Text.RegularExpressions.MatchEvaluator] {
    param($m)
    if ($m.Groups[1].Success) {
        # Single-quoted: literal. PS '' -> ', then MSVCRT-quote.
        $body = $m.Groups[1].Value.Replace("''", "'")
        if ($body -match '^(.*?)(\\+)$') {
            return '"' + ($matches[1] -replace '(\\*)"', '$1$1\"') + '"' + $matches[2]
        }
        return '"' + ($body -replace '(\\*)"', '$1$1\"') + '"'
    }
    if ($m.Groups[2].Success) {
        # Double-quoted: collapse PS quote-escapes to raw " / ', let ExpandString
        # resolve `n / `t / $var, then MSVCRT-quote.
        $body = $m.Groups[2].Value.
        Replace('`"', '"').
        Replace("``'", "'").
        Replace('""', '"')
        $body = $ExecutionContext.InvokeCommand.ExpandString($body)
        if ($body -match '^(.*?)(\\+)$') {
            return '"' + ($matches[1] -replace '(\\*)"', '$1$1\"') + '"' + $matches[2]
        }
        return '"' + ($body -replace '(\\*)"', '$1$1\"') + '"'
    }
    if ($m.Groups[3].Success) {
        # Backtick-escaped char outside a string: " -> \"; everything else
        # becomes a one-char quoted region so glob metas stay literal.
        $c = $m.Groups[3].Value
        if ($c -eq '"') {
            return '\"'
        }
        return '"' + $c + '"'
    }
    # Bare run: passed through unquoted so coreutils can glob it; expand $vars.
    return $ExecutionContext.InvokeCommand.ExpandString($m.Groups[4].Value)
}

# 0: not tested, 1: coreutils not installed, 2: coreutils installed.
$script:__COREUTILS_CMD_DIR_TEST__ = 0

# PSConsoleHostReadLine override that rewrites coreutils command names to their
# .cmd equivalents after PSReadLine returns (history keeps the original).
#
# Why .cmd over .exe: PSNativeCommandArgumentPassing = 'Windows' results in a behavior
# where passing bare quotes to CreateProcess() is impossible. This prevents us from
# passing "*" as "*" to coreutils and instead will be given as a bare *.
# This causes it to treat it as a glob pattern. "*.cmd" files however are automatically
# treated as PSNativeCommandArgumentPassing = 'Legacy', which preserves quotes.
# It is the only possible workaround and the only way coreutils can work at all.
function PSConsoleHostReadLine {
    [System.Diagnostics.DebuggerHidden()]
    param()

    $lastRunStatus = $?
    Microsoft.PowerShell.Core\Set-StrictMode -Off
    $line = [Microsoft.PowerShell.PSConsoleReadLine]::ReadLine($host.Runspace, $ExecutionContext, $lastRunStatus)

    # If the line contains no coreutils name, we don't need to parse the AST at all.
    if (-not $script:__COREUTILS_FAST_SKIP__.IsMatch($line)) {
        return $line
    }

    # Roamed/synced profiles can load this snippet on machines where coreutils is not installed.
    # Test for the existence of the command directory once and remember the result.
    if ($script:__COREUTILS_CMD_DIR_TEST__ -eq 0) {
        $script:__COREUTILS_CMD_DIR_TEST__ = 1
        if (Test-Path -LiteralPath 'C:\Program Files\coreutils\cmd\' -PathType Container -ErrorAction Ignore) {
            $script:__COREUTILS_CMD_DIR_TEST__ = 2
        }
    }
    if ($script:__COREUTILS_CMD_DIR_TEST__ -ne 2) {
        return $line
    }

    $ast = [System.Management.Automation.Language.Parser]::ParseInput($line, [ref]$null, [ref]$null)
    $commands = $ast.FindAll($script:__COREUTILS_CMD_PREDICATE__, $true)

    # Process right-to-left so earlier offsets stay valid after each splice.
    # In-place reverse beats Sort-Object for the typical 1-command line.
    if ($commands.Count -gt 1) {
        $commands = [System.Collections.Generic.List[object]]::new($commands)
        $commands.Reverse()
    }

    foreach ($cmd in $commands) {
        $name = $cmd.GetCommandName()
        if (!$name) {
            continue
        }

        $baseName = $name
        if ($name.EndsWith('.exe') -or $name.EndsWith('.cmd')) {
            $baseName = $name.Substring(0, $name.Length - 4)
        }
        if (!$script:__COREUTILS__.Contains($baseName)) {
            continue
        }

        # ls/la get colour + listing flags injected; la also rewrites to ls.
        $cmdElement = $cmd.CommandElements[0]
        $start = $cmdElement.Extent.StartOffset
        $end = $cmdElement.Extent.EndOffset
        $replacement = "& 'C:\Program Files\coreutils\cmd\"

        switch ($baseName) {
            'la' { $replacement += "ls.cmd' --color=auto -AFhl" }
            'ls' { $replacement += "ls.cmd' --color=auto" }
            default { $replacement += "$baseName.cmd'" }
        }

        # Walk command elements, merging adjacent ones whose extents touch
        # (e.g. `'a'*` parses as [SingleQuoted, BareWord] but is one shell word).
        # The inverse case `*'a'*` parses as a single BareWord whose text
        # contains the embedded quotes, which is why AST-only analysis
        # isn't enough and we still need to re-tokenize the source span.
        $argsStart = $end
        $argsEnd = $cmd.Extent.EndOffset
        $rewrittenArgs = ''
        $elements = $cmd.CommandElements
        $count = $elements.Count
        $i = 1
        while ($i -lt $count) {
            $first = $elements[$i]
            $wordStart = $first.Extent.StartOffset
            $wordEnd = $first.Extent.EndOffset
            $merged = $false
            while ($i + 1 -lt $count -and $elements[$i + 1].Extent.StartOffset -eq $wordEnd) {
                $i++
                $wordEnd = $elements[$i].Extent.EndOffset
                $merged = $true
            }
            $source = $line.Substring($wordStart, $wordEnd - $wordStart)
            $rewrittenArgs += $line.Substring($argsStart, $wordStart - $argsStart)
            $argsStart = $wordEnd
            # IndexOfAny beats running the regex per arg.
            if ($source.IndexOfAny($script:__COREUTILS_ARG_SPECIAL__) -lt 0) {
                $rewrittenArgs += $source
                $i++
                continue
            }
            # A single un-merged PS expression that needs $var resolution
            # (bare $var, "...$var...", $x.Member, $($expr), etc.).
            # Defer evaluation to runtime so the value reaches coreutils as a literal arg.
            # This matches POSIX behaviour where variable expansions don't result in globbing.
            if (-not $merged -and
                ($first -is [System.Management.Automation.Language.VariableExpressionAst] -or
                $first -is [System.Management.Automation.Language.ExpandableStringExpressionAst] -or
                $first -is [System.Management.Automation.Language.MemberExpressionAst])) {
                $rewrittenArgs += '(__coreutils_q ' + $source + ')'
                $i++
                continue
            }
            # Slow path: re-tokenise and re-emit as MSVCRT-style quoting,
            # then wrap in PS single quotes so PS hands the body verbatim.
            $windowsQuoted = $script:__COREUTILS_ARG_RX__.Replace($source, $script:__COREUTILS_ARG_EVAL__)
            $rewrittenArgs += "'" + $windowsQuoted.Replace("'", "''") + "'"
            $i++
        }
        $rewrittenArgs += $line.Substring($argsStart, $argsEnd - $argsStart)

        $line = $line.Substring(0, $start) + $replacement + $rewrittenArgs + $line.Substring($argsEnd)
    }

    return $line
}
# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# DO NOT MODIFY -- coreutils -- 60b36fc6-2d59-49df-be51-28dd2f4c3c9a

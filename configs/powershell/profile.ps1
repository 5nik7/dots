using namespace System.Management.Automation
using namespace System.Management.Automation.Language


Import-Module Get-ChildItemColor
Import-Module PSFzf

$profileDirectory = [System.IO.Path]::GetDirectoryName($PROFILE)
$envFilePath = Join-Path -Path $profileDirectory -ChildPath ".env"

if (Test-Path $envFilePath) {
  Get-Content $envFilePath | ForEach-Object {
    $name, $value = $_.split('=')

    if ([string]::IsNullOrWhiteSpace($name) -or $name.Contains('#')) {
      continue
    }

    Set-Item -force -Path "env:$name" -Value $value
  }
}

function Highlight {
  param($text = '', $color = 'DarkYellow')
  $text | Write-Host -ForegroundColor $color
}

function Fresh {
  & $PROFILE.AllUsersAllHosts
  Write-Host ''
  Highlight ' Profile reloaded. '
}
Set-Alias -Name rlp -Value Fresh

Set-Alias -Name c -Value Clear-Host

Set-Alias -Name v -Value $env:EDITOR

Set-Alias -Name open -Value explorer.exe

Set-Alias -Name code -Value "C:\Users\nickf\AppData\Local\Programs\Microsoft VS Code Insiders\Code - Insiders.exe"

Set-Alias -Name npmup -Value "npm install -g npm@latest"

function ya {
  $tmp = [System.IO.Path]::GetTempFileName()
  yazi $args --cwd-file="$tmp"
  $cwd = Get-Content -Path $tmp
  if (-not [String]::IsNullOrEmpty($cwd) -and $cwd -ne $PWD.Path) {
    Set-Location -Path $cwd
  }
  Remove-Item -Path $tmp
}
Set-Alias -Name d -Value ya

function Remove-DuplicatePSReadlineHistory {
  $historyPath = (Get-PSReadLineOption).HistorySavePath

  # backup
  $directory = (Get-Item $historyPath).DirectoryName
  $basename = (Get-Item $historyPath).Basename
  $extension = (Get-Item $historyPath).Extension
  $timestamp = (Get-Date).ToString("yyyy-MM-ddTHH-mm-ssZ")

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

Set-Alias -Name clhist -Value Remove-DuplicatePSReadlineHistory

$TERMINAL = "wt"
$EDITOR = "nvim"

$ENV:RG_DEFAULT_COMMAND = "rg -p -l -L --hidden"

$ENV:FZF_DEFAULT_COMMAND = "fd --hidden --follow --exclude=.git --exclude=node_modules"
$ENV:FZF_CTRL_T_COMMAND = $ENV:FZF_DEFAULT_COMMAND

$ENV:FZF_DEFAULT_OPTS = "
--layout=reverse --info=inline --height=80% --multi --cycle --margin=1 --border=sharp
--prompt=' ' --pointer=' ' --marker=' '
--color fg:-1,bg:-1,hl:5:underline,fg+:3,bg+:-1,hl+:5:underline,gutter:-1,border:0
--color info:2,prompt:-1,spinner:2,pointer:6,marker:4
--preview-window='border-sharp'
--no-scrollbar
--preview-window='right,65%,border-left,+{2}+3/3,~3'
--bind '?:toggle-preview'
--bind 'ctrl-a:select-all'
--bind 'ctrl-y:execute-silent(echo {+} | win32yank.exe -i)'
--bind 'ctrl-e:execute($TERMINAL $EDITOR {+})+reload(fzf)'"

function ln {
  param(
    [Parameter(Mandatory = $true)]
    [string]$base,

    [Parameter(Mandatory = $true)]
    [string]$target
  )

  try {
    if ((Test-Path -Path $target) -and (Get-Item -Path $target).Target -eq $base) {
      Write-Output "Already a symlink"
    }
    elseif (Test-Path -Path $target) {
      Rename-Item -Path $target -NewName "$target.bak" -ErrorAction Stop
      Write-Output "Creating a backup file: $target.bak"
      New-Item -ItemType SymbolicLink -Path $target -Target $base -ErrorAction Stop
      Write-Output "$base -> $target"
    }
    else {
      New-Item -ItemType SymbolicLink -Path $target -Target $base -ErrorAction Stop
      Write-Output "$base -> $target"
    }
  }
  catch {
    Write-Output "Failed to create symbolic link: $_"
  }
}


function colors {
  $colors = [enum]::GetValues([System.ConsoleColor])

  Foreach ($bgcolor in $colors) {
    Foreach ($fgcolor in $colors) { Write-Host "$fgcolor|"  -ForegroundColor $fgcolor -BackgroundColor $bgcolor -NoNewLine }

    Write-Host " on $bgcolor"
  }
}

function ll {
  Write-Host " "
  eza -lA --git --git-repos --icons --group-directories-first --no-quotes
}

function l {
  Write-Host " "
  eza -lA --git --git-repos --icons --group-directories-first --no-quotes --no-permissions --no-filesize --no-user --no-time
}

function envl {
  Get-ChildItem Env:
}

function touch($file) {
  "" | Out-File $file -Encoding ASCII
}

function which($name) {
  Get-Command $name | Select-Object -ExpandProperty Definition
}

function export($name, $value) {
  set-item -force -path "env:$name" -value $value;
}

function rm([string]$path) {
  Remove-Item -Recurse -Force $path
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

function q {
  Exit
}

function repos {
  cd "$env:REPOS"
}
function dot {
  cd "$env:DOTS"
}

# function cdc {
#   param(
#     [string]$path = $null
#   )
#   if ($path) {
#     Set-Location -Path (Join-Path -Path $HOMEDRIVE\ -ChildPath $path)
#   }
#   else {
#     Set-Location -Path $HOMEDRIVE\
#   }
# }
# Set-Alias -Name c/ -Value cdc
function path {
  $env:Path -split ';'
}

function .. {
  cd ".."
}

function lg {
  lazygit
}

function cdeza {
  param(
    [string]$Path = $HOME
  )
  if (-not (Test-Path $Path)) {
    Write-Host -ForegroundColor 'DarkRed' "  "
    Write-Host -ForegroundColor 'DarkGray' "  '$Path' is not a directory."
    return
  }
  Set-Location -Path $Path
  Write-Host " "
  eza -lA --git --git-repos --icons --group-directories-first --no-quotes --no-permissions --no-filesize --no-user --no-time
}
Set-Alias -Name cd -Value cdeza -force -option 'AllScope'

$OnViModeChange = [scriptblock] {
  if ($args[0] -eq 'Command') {
    # Set the cursor to a blinking block.
    Write-Host -NoNewLine "`e[1 q"
  }
  else {
    # Set the cursor to a blinking line.
    Write-Host -NoNewLine "`e[5 q"
  }
}

if ($host.Name -eq 'ConsoleHost') {
  Import-Module PSReadLine

  $PSReadLineOptions = @{
    HistoryNoDuplicates           = $true
    HistorySearchCursorMovesToEnd = $true
    MaximumHistoryCount           = "10000"
    ShowToolTips                  = $true
    ContinuationPrompt            = ">>"
    BellStyle                     = "None"
    PredictionSource              = "History"
    PredictionViewStyle           = "InlineView"
    Colors                        = @{
      InlinePrediction   = 'DarkGray'
      Comment            = 'DarkGray'
      Command            = 'Green'
      Number             = 'Yellow'
      Member             = 'Red'
      Operator           = 'DarkYellow'
      Type               = 'Cyan'
      Variable           = 'Blue'
      Parameter          = 'White'
      ContinuationPrompt = 'Black'
      Default            = 'White'
    }
  }
  Set-PSReadLineOption @PSReadLineOptions
}

Set-PSReadLineOption -AddToHistoryHandler {
  param($line)
  $line -notmatch '(^\s+|^rm|^Remove-Item|fl$)'
}

function edit-history {
  code (Get-PSReadLineOption).HistorySavePath
}

Set-PSReadlineKeyHandler -Key Tab -Function MenuComplete
Set-PSReadLineKeyHandler -Key UpArrow -Function HistorySearchBackward
Set-PSReadLineKeyHandler -Key DownArrow -Function HistorySearchForward
Set-PSReadlineOption -HistorySearchCursorMovesToEnd

$ChocolateyProfile = "$env:ChocolateyInstall\helpers\chocolateyProfile.psm1"
if (Test-Path($ChocolateyProfile)) {
  Import-Module "$ChocolateyProfile"
}

$Global:__LastHistoryId = -1

function Global:__Terminal-Get-LastExitCode {
  if ($? -eq $True) {
    return 0
  }
  $LastHistoryEntry = $(Get-History -Count 1)
  $IsPowerShellError = $Error[0].InvocationInfo.HistoryId -eq $LastHistoryEntry.Id
  if ($IsPowerShellError) {
    return -1
  }
  return $LastExitCode
}

function prompt {

  # First, emit a mark for the _end_ of the previous command.

  $gle = $(__Terminal-Get-LastExitCode);
  $LastHistoryEntry = $(Get-History -Count 1)
  # Skip finishing the command if the first command has not yet started
  if ($Global:__LastHistoryId -ne -1) {
    if ($LastHistoryEntry.Id -eq $Global:__LastHistoryId) {
      # Don't provide a command line or exit code if there was no history entry (eg. ctrl+c, enter on no command)
      $out += "`e]133;D`a"
    }
    else {
      $out += "`e]133;D;$gle`a"
    }
  }


  $loc = $($executionContext.SessionState.Path.CurrentLocation);

  # Prompt started
  $out += "`e]133;A$([char]07)";

  # CWD
  $out += "`e]9;9;`"$loc`"$([char]07)";

  # (your prompt here)
  $out += "PWSH $loc$('>' * ($nestedPromptLevel + 1)) ";

  # Prompt ended, Command started
  $out += "`e]133;B$([char]07)";

  $Global:__LastHistoryId = $LastHistoryEntry.Id

  return $out
}

function Invoke-Starship-PreCommand {
  $WarningPreference = "SilentlyContinue"
  $ErrorActionPreference = "SilentlyContinue"
}

Invoke-Expression (&starship init powershell)

$OnViModeChange = [scriptblock] {
  if ($args[0] -eq 'Command') {
    # Set the cursor to a blinking block.
    Write-Host -NoNewLine "`e[1 q"
  }
  else {
    # Set the cursor to a blinking line.
    Write-Host -NoNewLine "`e[5 q"
  }
}
Set-PsReadLineOption -EditMode Vi
Set-PSReadLineOption -ViModeIndicator Script -ViModeChangeHandler $OnViModeChange

Set-PSReadLineKeyHandler -Chord '"', "'" `
  -BriefDescription SmartInsertQuote `
  -LongDescription "Insert paired quotes if not already on a quote" `
  -ScriptBlock {
  param($key, $arg)

  $line = $null
  $cursor = $null
  [Microsoft.PowerShell.PSConsoleReadLine]::GetBufferState([ref]$line, [ref]$cursor)

  if ($line.Length -gt $cursor -and $line[$cursor] -eq $key.KeyChar) {
    # Just move the cursor
    [Microsoft.PowerShell.PSConsoleReadLine]::SetCursorPosition($cursor + 1)
  }
  else {
    # Insert matching quotes, move cursor to be in between the quotes
    [Microsoft.PowerShell.PSConsoleReadLine]::Insert("$($key.KeyChar)" * 2)
    [Microsoft.PowerShell.PSConsoleReadLine]::GetBufferState([ref]$line, [ref]$cursor)
    [Microsoft.PowerShell.PSConsoleReadLine]::SetCursorPosition($cursor - 1)
  }
}

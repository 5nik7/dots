$ENV:REPOS = "C:\repos"
$ENV:DOTS = "$ENV:REPOS\dots"
$ENV:DOTFILES = "$ENV:DOTS\configs"
$ENV:NVM_HOME = "$HOME\.nvm"
$ENV:NVM_SYMLINK = "C:\nodejs"
$ENV:STARSHIP_CONFIG = "$ENV:DOTFILES\starship\starship.toml"
$ENV:STARSHIP_CACHE = "$HOME\AppData\Local\Temp"
$ENV:PSHELL = "$ENV:DOTFILES\powershell"
$ENV:GOPATH = "$HOME\go"
$ENV:GOBIN = "$HOME\go\bin"
$ENV:EDITOR = "nvim"
$ENV:TERMINAL = "wt"
$ENV:VISUAL = "nvim"
$ENV:WINCONFIG = "$HOME\.config"
$ENV:BAT_CONFIG_PATH = "$ENV:DOTFILES\bat\bat.conf"
$ENV:YAZI_CONFIG_HOME = "$ENV:DOTFILES\yazi"
$ENV:BOXES = "$ENV:DOTFILES\boxes\boxes-config"

Import-Module Get-ChildItemColor
Import-Module PSFzf

#region conda initialize
# !! Contents within this block are managed by 'conda init' !!
If (Test-Path "C:\ProgramData\miniconda3\Scripts\conda.exe") {
    (& "C:\ProgramData\miniconda3\Scripts\conda.exe" "shell.powershell" "hook") | Out-String | Where-Object { $_ } | Invoke-Expression
}
#endregion

$ChocolateyProfile = "$env:ChocolateyInstall\helpers\chocolateyProfile.psm1"
if (Test-Path($ChocolateyProfile)) {
  Import-Module "$ChocolateyProfile"
}

Invoke-Expression (& { (zoxide init powershell | Out-String) })

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
  & $PROFILE
  Write-Host ''
  Highlight ' Profile reloaded. '
}
Set-Alias -Name rlp -Value Fresh

Set-Alias -Name c -Value Clear-Host

Set-Alias -Name v -Value $env:EDITOR

Set-Alias -Name open -Value explorer.exe

Set-Alias -Name py -Value python
Set-Alias -Name py3 -Value python
Set-Alias -Name pytonr3 -Value python

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


# $ENV:RG_DEFAULT_COMMAND = "rg -p -l -L --hidden"

# $ENV:FZF_DEFAULT_COMMAND = "fd --hidden --follow --exclude=.git --exclude=node_modules"
# $ENV:FZF_CTRL_T_COMMAND = $ENV:FZF_DEFAULT_COMMAND

$ENV:FZF_DEFAULT_OPTS = "
--layout=reverse --info=inline --height=80% --multi --cycle --margin=1 --border=sharp
--prompt=' ' --pointer=' ' --marker=' '
--color fg:-1,bg:-1,hl:5:underline,fg+:3,bg+:-1,hl+:5:underline,gutter:-1,border:0
--color info:2,prompt:-1,spinner:2,pointer:6,marker:4
--preview-window='border-sharp'
--no-scrollbar"

# $ENV:FZF_DEFAULT_OPTS = "
# --layout=reverse --info=inline --height=80% --multi --cycle --margin=1 --border=sharp
# --prompt=' ' --pointer=' ' --marker=' '
# --color fg:-1,bg:-1,hl:5:underline,fg+:3,bg+:-1,hl+:5:underline,gutter:-1,border:0
# --color info:2,prompt:-1,spinner:2,pointer:6,marker:4
# --preview-window='border-sharp'
# --no-scrollbar
# --preview-window='right,65%,border-left,+{2}+3/3,~3'
# --bind '?:toggle-preview'
# --bind 'ctrl-a:select-all'
# --bind 'ctrl-y:execute-silent(echo {+} | win32yank.exe -i)'
# --bind 'ctrl-e:execute($TERMINAL $EDITOR {+})+reload(fzf)'"

function ln {
  param(
    [Parameter(Mandatory = $true)]
    [string]$base,

    [Parameter(Mandatory = $true)]
    [string]$target
  )

  try {
    if ((Test-Path -Path $target) -and (Get-Item -Path $target).Target -eq $base) {
      Write-Host ''
      Write-Host -ForegroundColor Yellow "Already a symlink."
      Write-Host ''
    }
    elseif (Test-Path -Path $target) {
      $bakDate = Get-Date -Format "yyyy-MM-dd_HH-mm"
      Rename-Item -Path $target -NewName "$target.$bakDate.bak" -ErrorAction Stop | Out-Null
      Write-Host ''
      Write-Host -ForegroundColor White "Creating a backup file: " -NoNewline
      Write-Host -ForegroundColor Green "$target.$bakDate.bak"
      Write-Host ''
      New-Item -ItemType SymbolicLink -Path $target -Target $base -ErrorAction Stop | Out-Null
      Write-Host -ForegroundColor Blue "$base" -NoNewline
      Write-Host -ForegroundColor DarkGray "  " -NoNewline
      Write-Host -ForegroundColor Cyan "$target"
      Write-Host ''
    }
    else {
      New-Item -ItemType SymbolicLink -Path $target -Target $base -ErrorAction Stop | Out-Null
      Write-Host ''
      Write-Host -ForegroundColor Blue "$base" -NoNewline
      Write-Host -ForegroundColor Yellow "  " -NoNewline
      Write-Host -ForegroundColor Cyan "$target"
      Write-Host ''
    }
  }
  catch {
    Write-Output "Failed to create symbolic link: $_"
  }
}

function bak {
  param(
    [Parameter(Mandatory = $false)]
    [string]$Path = (Get-Location).Path,
    [switch]$s
  )

  $bakFiles = Get-ChildItem -Path $Path -Filter "*.bak" -Recurse -Force -ErrorAction SilentlyContinue
  $backupPath = Join-Path -Path $env:USERPROFILE -ChildPath "backups"

  foreach ($file in $bakFiles) {
    if ($s -and $file.FullName -notlike "$backupPath\*") {
      $destination = Join-Path -Path $backupPath -ChildPath $file.
      Move-Item -Path $file.FullName -Destination $destination -Force | Out-Null
      Write-Host "Moved $file.FullName to $destination"
    }
    else {
      Write-Host $file.FullName
    }
  }
}
function fbak {
  $command = "fd --hidden --follow -e bak"
  Invoke-Expression $command
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

function Export-EnvironmentVariable {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Name,
    [Parameter(Mandatory = $true)]
    [string]$Value
  )
  Set-Item -Force -Path "env:$Name" -Value $Value
}
Set-Alias -Name export -Value Export-EnvironmentVariable

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
  Set-Location ".."
}

function lg {
  lazygit
}

Set-Alias -Name cd -Value z -force -option 'AllScope'

# function Invoke-Starship-PreCommand {
#   $WarningPreference = "SilentlyContinue"
#   $ErrorActionPreference = "SilentlyContinue"
# }

# function Invoke-Starship-TransientFunction {
#   &starship module character
# }

Invoke-Expression (&starship init powershell)

# Enable-TransientPrompt

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
      Command            = 'Magenta'
      Number             = 'Yellow'
      Member             = 'Red'
      Operator           = 'DarkYellow'
      Type               = 'Cyan'
      Variable           = 'Blue'
      Parameter          = 'Yellow'
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
  & $env:EDITOR (Get-PSReadLineOption).HistorySavePath
}
Set-Alias -Name ehist -Value edit-history

Set-PSReadLineKeyHandler -Key Tab -ScriptBlock { Invoke-FzfTabCompletion }
# Set-PSReadlineKeyHandler -Key Tab -Function MenuComplete
Set-PSReadLineKeyHandler -Key UpArrow -Function HistorySearchBackward
Set-PSReadLineKeyHandler -Key DownArrow -Function HistorySearchForward
Set-PSReadlineOption -HistorySearchCursorMovesToEnd

Set-PSFzfOption -TabExpansion -EnableAliasFuzzyEdit -EnableAliasFuzzyHistory -EnableAliasFuzzyKillProcess -EnableAliasFuzzyScoop -EnableAliasFuzzyGitStatus

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

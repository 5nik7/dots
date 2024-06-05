
function Add-PathPrefix {
  param (
    [Parameter(Mandatory = $true)]
    [string]$Path
  )
  if (-not ($env:Path -split ';' | Select-String -SimpleMatch $Path)) {
    $env:Path = "$Path;" + $env:Path
  }
}

function Add-Path {
  param (
    [Parameter(Mandatory = $true)]
    [string]$Path
  )
  if (-not ($env:Path -split ';' | Select-String -SimpleMatch $Path)) {
    $env:Path += ";$Path"
  }
}

$ENV:REPOS = "C:\repos"
$ENV:DOTS = "$ENV:REPOS\dots"
$ENV:DOTFILES = "$ENV:DOTS\configs"
$ENV:PROJECTS = "C:\projects"
$ENV:NVM_HOME = "$HOME\.nvm"
$ENV:NVM_SYMLINK = "C:\nodejs"
$ENV:STARSHIP_CONFIG = "$ENV:DOTFILES\starship\starship.toml"
$ENV:STARSHIP_CACHE = "$HOME\AppData\Local\Temp"
$ENV:PSHELL = "$ENV:DOTFILES\powershell"
$ENV:GOPATH = "$HOME\go"
$ENV:GOBIN = "$HOME\go\bin"
$ENV:GOEXE = "C:\Program Files\Go\bin\go.exe"
$ENV:WINCONFIG = "$HOME\.config"
$ENV:BAT_CONFIG_PATH = "$ENV:DOTFILES\bat\bat.conf"
$ENV:YAZI_CONFIG_HOME = "$ENV:DOTFILES\yazi"
$ENV:BOXES = "$ENV:DOTFILES\boxes\boxes-config"

function repos {
  Set-Location "$ENV:REPOS"
}

function dots {
  Set-Location "$ENV:DOTS"
}

function dotfiles {
  Set-Location "$ENV:DOTFILES"
}

function projects {
  Set-Location "$ENV:PROJECTS"
}

# Utility Functions
function Test-CommandExists {
  param($command)
  $exists = $null -ne (Get-Command $command -ErrorAction SilentlyContinue)
  return $exists
}

# Editor Configuration
$EDITOR = if (Test-CommandExists nvim) { 'nvim' }
elseif (Test-CommandExists code) { 'code' }
elseif (Test-CommandExists vim) { 'vim' }
elseif (Test-CommandExists vi) { 'vi' }
else { 'notepad' }

$ENV:EDITOR = $EDITOR

Set-Alias -Name vim -Value $EDITOR
Set-Alias -Name v -Value $EDITOR


function Edit-Profile {
  vim $PROFILE
}

# Set-Variable -Name TERMINAL -Value wt

Import-Module PSFzf

$ChocolateyProfile = "$env:ChocolateyInstall\helpers\chocolateyProfile.psm1"
if (Test-Path($ChocolateyProfile)) {
  Import-Module "$ChocolateyProfile"
}

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

Set-Alias -Name c -Value Clear-Host
Set-Alias -Name path -Value Get-Path

function open {
  param (
    [string]$Path = $PWD
  )

  if ($Path) {
    explorer.exe $Path
  }
  else {
    explorer.exe
  }
}

# Set-Alias -Name npmup -Value "npm install -g npm@latest"

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

$ENV:FZF_DEFAULT_OPTS = if (Test-CommandExists fzf) {
  "--ansi --layout reverse --info inline --height 80% --cycle --border sharp
--prompt ' ' --pointer ' ' --marker ' '
--color 'fg:-1,bg:-1,hl:5:underline,fg+:3,bg+:-1,hl+:5:underline,gutter:-1,border:0'
--color 'info:2,prompt:5,spinner:2,pointer:6,marker:4'
--no-scrollbar"
}


# $FZFEXE = Get-Command fzf | Select-Object -ExpandProperty Definition

# Set-Alias -Name cd -Value z -force -option 'AllScope'

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
    EditMode                      = "Vi"
    PredictionViewStyle           = "InlineView"
    Colors                        = @{
      InlinePrediction   = 'DarkGray'
      Comment            = 'DarkGray'
      Command            = 'DarkMagenta'
      Number             = 'Magenta'
      Member             = 'Red'
      Operator           = 'DarkYellow'
      Type               = 'Cyan'
      Variable           = 'DarkCyan'
      Parameter          = '#7faadb'
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

Set-PsFzfOption -TabExpansion -EnableFd

# Set-PSReadLineKeyHandler -Chord 'Ctrl+D2' -Function MenuComplete
Set-PSReadLineKeyHandler -Key F7 -ScriptBlock { Invoke-FzfTabCompletion }

Set-PSReadlineKeyHandler -Key Tab -Function MenuComplete
Set-PSReadLineKeyHandler -Key UpArrow -Function HistorySearchBackward
Set-PSReadLineKeyHandler -Key DownArrow -Function HistorySearchForward

$profileDir = "$ENV:DOTFILES\powershell"
foreach ( $includeFile in ("common") ) {
  Unblock-File $profileDir\$includeFile.ps1
  . "$profileDir\$includeFile.ps1"
}

$scriptsPath = "$profileDir\Scripts"
if (-not ($env:Path -split ';' | Select-String -SimpleMatch $scriptsPath)) {
  Add-Path -Path $scriptsPath
}

Invoke-Expression (&starship init powershell)

# function OnViModeChange {
#   if ($args[0] -eq 'Command') {

#     # Set the cursor to a solid block.
#     Write-Host -NoNewLine "`e[2 q"
#   }
#   else {
#     # Set the cursor to a blinking line.
#     Write-Host -NoNewLine "`e[5 q"
#   }
# }
# Set-PSReadLineOption -ViModeIndicator Script -ViModeChangeHandler $Function:OnViModeChange
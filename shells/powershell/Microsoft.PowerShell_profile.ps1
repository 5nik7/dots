$ENV:REPOS = "C:\repos"
$ENV:DOTS = "$ENV:REPOS\dots"
$ENV:DOTSHELL = "$ENV:DOTS\shells"
$ENV:PSHELL = "$ENV:DOTSHELL\powershell"
$ENV:ZSHELL = "$ENV:DOTSHELL\zsh"
$ENV:BASHELL = "$ENV:DOTSHELL\bash"
$ENV:DOTCONF = "$ENV:DOTS\configs"
$ENV:XDG_CONFIG_HOME = "$ENV:USERPROFILE\.config"
$ENV:PROJECTS = "C:\projects"

$ENV:NVM_HOME = "$ENV:USERPROFILE\.nvm"
$ENV:NVM_SYMLINK = "C:\nodejs"
$ENV:GOPATH = "$ENV:USERPROFILE\go"
$ENV:GOBIN = "$ENV:USERPROFILE\go\bin"

$ENV:STARSHIP_CONFIG = "$ENV:DOTCONF\starship\starship.toml"
$ENV:STARSHIP_CACHE = "$ENV:USERPROFILE\AppData\Local\Temp"
$ENV:BAT_CONFIG_PATH = "$ENV:DOTCONF\bat\bat.conf"
$ENV:YAZI_CONFIG_HOME = "$ENV:DOTCONF\yazi"
$ENV:BOXES = "$ENV:DOTCONF\boxes\boxes-config"

If (Test-Path "C:\miniconda3\Scripts\conda.exe") {
    (& "C:\miniconda3\Scripts\conda.exe" "shell.powershell" "hook") | Out-String | ? { $_ } | Invoke-Expression
}

$profileDirectory = [System.IO.Path]::GetDirectoryName($PROFILE)
foreach ( $includeFile in ("functions", "aliases", "secrets") ) {
  if (Test-Path $profileDirectory\$includeFile.ps1) {
    Unblock-File $profileDirectory\$includeFile.ps1
    . "$profileDirectory\$includeFile.ps1"
  }
}

$scriptsPath = "$profileDirectory\Scripts"
if (-not ($env:Path -split ';' | Select-String -SimpleMatch $scriptsPath)) {
  Add-Path -Path $scriptsPath
}

$ChocolateyProfile = "$env:ChocolateyInstall\helpers\chocolateyProfile.psm1"
if (Test-Path($ChocolateyProfile)) {
  Import-Module "$ChocolateyProfile"
}

$ENV:FZF_DEFAULT_OPTS = if (Test-CommandExists fzf) {
  "--ansi --layout reverse --info inline --height 80% --cycle --border sharp
--prompt ' ' --pointer ' ' --marker ' '
--color 'fg:-1,bg:-1,hl:5:underline,fg+:3,bg+:-1,hl+:5:underline,gutter:-1,border:0'
--color 'info:2,prompt:5,spinner:2,pointer:6,marker:4'
--no-scrollbar"
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

Set-PsFzfOption -TabExpansion -EnableFd

# Set-PSReadLineKeyHandler -Chord 'Ctrl+D2' -Function MenuComplete
Set-PSReadLineKeyHandler -Key F7 -ScriptBlock { Invoke-FzfTabCompletion }

Set-PSReadlineKeyHandler -Key Tab -Function MenuComplete
Set-PSReadLineKeyHandler -Key UpArrow -Function HistorySearchBackward
Set-PSReadLineKeyHandler -Key DownArrow -Function HistorySearchForward

Invoke-Expression (&starship init powershell)

# oh-my-posh init pwsh | Invoke-Expression

function OnViModeChange {
  if ($args[0] -eq 'Command') {

    # Set the cursor to a solid block.
    Write-Host -NoNewLine "`e[2 q"
  }
  else {
    # Set the cursor to a blinking line.
    Write-Host -NoNewLine "`e[5 q"
  }
}
Set-PSReadLineOption -ViModeIndicator Script -ViModeChangeHandler $Function:OnViModeChange
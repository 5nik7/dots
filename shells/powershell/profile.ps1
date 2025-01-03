$Env:DOTS = "$Env:USERPROFILE\dots"
$Env:DOTFILES = "$Env:DOTS\configs"

$Env:PSDOT = "$Env:DOTS\shells\powershell"
$Env:PSCOMPS = "$Env:PSDOT\completions"
$Env:PSMODS = "$Env:PSDOT\Modules"

$Env:BASHDOT = "$Env:DOTS\shells\bash"
$Env:ZSHDOT = "$Env:DOTS\shells\zsh"
$Env:PROJECTS = "$Env:USERPROFILE\dev"
$Env:DEV = "$Env:USERPROFILE\dev"
$Env:WINDOTCONF = "$Env:USERPROFILE\.config"

$Env:DRIP = "$Env:DOTS\drip"
$Env:DRIP_COLS = "$Env:DRIP\colorschemes"
$Env:DRIP_TEMPS = "$Env:DRIP\tenplates"
$Env:WALLS = "$Env:DOTS\walls"

$Env:NVM_HOME = "$Env:APPDATA\nvm"
$Env:NVM_SYMLINK = "$Env:HOMEDRIVE\node"
$Env:GOPATH = "$Env:USERPROFILE\go"
$Env:GOBIN = "$Env:USERPROFILE\go\bin"

$Env:DOCUMENTS = [Environment]::GetFolderPath("mydocuments")
$Env:DOWNLOADS = "$Env:USERPROFILE\Downloads"

$Env:STARSHIP_CACHE = "$Env:LOCALAPPDATA\Temp"
$Env:STARSHIP_CONFIG = "$Env:DOTFILES\starship\starship.toml"
$Env:BAT_CONFIG_PATH = "$Env:DOTFILES\bat\config"
$Env:YAZI_CONFIG_HOME = "$Env:DOTFILES\yazi"
$GITBIN = "C:\Git\usr\bin"
$Env:YAZI_FILE_ONE = "$GITBIN\file.exe"
$BAT_THEME = if ($Env:THEME) { $Env:THEME }
else { 'base16' }
$Env:BAT_THEME = $BAT_THEME
$Env:KOMOREBI_CONFIG_HOME = "$Env:WINDOTCONF\komorebi"

# FZF Options
# $Env:FZF_DEFAULT_COMMAND = "fd --type f --strip-cwd-prefix --hidden --exclude .git"
# $Env:FZF_DEFAULT_OPTS = "--preview=`"bat --style=numbers --color=always {}`" --preview-window=border-rounded --preview-label=`" PREVIEW `" --border=rounded --border-label=`" FILES `" --tabstop=2 --color=16 --bind=ctrl-d:preview-half-page-down,ctrl-u:preview-half-page-up"
# $Env:FZF_DIRECTORY_OPTS = "--preview=`"pwsh -NoProfile -Command Get-ChildItem -Force -LiteralPath '{}'`" --preview-window=border-rounded --preview-label=`" PREVIEW `" --border=rounded --border-label=`" DIRECTORIES `" --tabstop=2 --color=16 --bind=ctrl-d:preview-half-page-down,ctrl-u:preview-half-page-up"

$TIC = (Get-ItemProperty 'HKCU:\Control Panel\Desktop' TranscodedImageCache -ErrorAction Stop).TranscodedImageCache
$wallout = [System.Text.Encoding]::Unicode.GetString($TIC) -replace '(.+)([A-Z]:[0-9a-zA-Z\\])+', '$2'
$Env:WALLPAPER = $wallout

foreach ( $includeFile in ("functions", "aliases", "lab") ) {
    Unblock-File "$Env:PSDOT\$includeFile.ps1"
    . "$Env:PSDOT\$includeFile.ps1"
}

foreach ($compFile in Get-ChildItem -Path "$Env:PSCOMPS" -Filter "*.ps1") {
    Unblock-File -Path $compFile.FullName
    . $compFile.FullName
}

Import-Module "$Env:PSMODS\winwal\winwal.psm1"
Import-Module "$Env:PSMODS\psdots\psdots.psm1"
Import-Module -Name Terminal-Icons
Import-Module -Name Microsoft.WinGet.CommandNotFound
Import-Module "$($(Get-Item $(Get-Command scoop.ps1).Path).Directory.Parent.FullName)\modules\scoop-completion"

$Env:PSCRIPTS = "$Env:PSDOT\Scripts"
if (Test-Path($Env:PSCRIPTS)) {
    Add-Path -Path $Env:PSCRIPTS
}

$Env:DOTBIN = "$Env:DOTS\bin"
if (Test-Path($Env:DOTBIN)) {
    Add-Path -Path $Env:DOTBIN
}

$localbin = "$Env:USERPROFILE\.local\bin"
if (Test-Path($localbin)) {
    Add-Path -Path $localbin
}

if ($host.Name -eq 'ConsoleHost') {
    Import-Module PSReadLine

    $PSReadLineOptions = @{
        HistoryNoDuplicates           = $true
        HistorySearchCursorMovesToEnd = $true
        HistorySearchCaseSensitive    = $false
        MaximumHistoryCount           = "50000"
        ShowToolTips                  = $true
        ContinuationPrompt            = " "
        BellStyle                     = "None"
        PredictionSource              = "History"
        EditMode                      = "Vi"
        PredictionViewStyle           = "InlineView"
        Colors                        = @{
            Comment                = 'DarkGray'
            Command                = 'DarkGreen'
            Emphasis               = 'Cyan'
            Number                 = 'Yellow'
            Member                 = 'Blue'
            Operator               = 'Blue'
            Type                   = 'Yellow'
            String                 = 'Green'
            Variable               = 'Cyan'
            Parameter              = 'Blue'
            ContinuationPrompt     = 'Black'
            Default                = 'White'
            InlinePrediction       = 'DarkGray'
            ListPrediction         = 'DarkGray'
            ListPredictionSelected = 'DarkGray'
            ListPredictionTooltip  = 'DarkGray'
        }
    }
    Set-PSReadLineOption @PSReadLineOptions
}

Set-PSReadlineKeyHandler -Key Tab -Function MenuComplete
Set-PSReadLineKeyHandler -Key UpArrow -Function HistorySearchBackward
Set-PSReadLineKeyHandler -Key DownArrow -Function HistorySearchForward
Set-PSReadLineKeyHandler -Chord Enter -Function ValidateAndAcceptLine

Invoke-Expression (&starship init powershell)
Enable-TransientPrompt
function Invoke-Starship-TransientFunction {
    &starship module character
}

Set-PSReadLineOption -ViModeIndicator script -ViModeChangeHandler {
    [Microsoft.PowerShell.PSConsoleReadLine]::InvokePrompt()
    if ($args[0] -eq 'Command') {
        # Set the cursor to a solid block.
        [Microsoft.PowerShell.PSConsoleReadLine]::ForwardChar()
        Write-Host -NoNewLine "`e[2 q"
    }
    else {
        # Set the cursor to a blinking line.
        Write-Host -NoNewLine "`e[5 q"
    }
}
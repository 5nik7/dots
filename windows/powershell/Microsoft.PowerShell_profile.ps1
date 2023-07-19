# File for Current User, All Hosts - $PROFILE.CurrentUserAllHosts

if ($host.Name -eq 'ConsoleHost') {
    Import-Module PSReadLine
}

Import-Module Catppuccin

$Flavor = $Catppuccin['Mocha']

$Colors = @{
    # Largely based on the Code Editor style guide
    # Emphasis, ListPrediction and ListPredictionSelected are inspired by the Catppuccin fzf theme

    # Powershell colours
    ContinuationPrompt     = $Flavor.Teal.Foreground()
    Emphasis               = $Flavor.Red.Foreground()
    Selection              = $Flavor.Surface0.Background()

    # PSReadLine prediction colours
    InlinePrediction       = $Flavor.Overlay0.Foreground()
    ListPrediction         = $Flavor.Mauve.Foreground()
    ListPredictionSelected = $Flavor.Surface0.Background()

    # Syntax highlighting
    Command                = $Flavor.Blue.Foreground()
    Comment                = $Flavor.Overlay0.Foreground()
    Default                = $Flavor.Text.Foreground()
    Error                  = $Flavor.Red.Foreground()
    Keyword                = $Flavor.Mauve.Foreground()
    Member                 = $Flavor.Rosewater.Foreground()
    Number                 = $Flavor.Peach.Foreground()
    Operator               = $Flavor.Sky.Foreground()
    Parameter              = $Flavor.Pink.Foreground()
    String                 = $Flavor.Green.Foreground()
    Type                   = $Flavor.Yellow.Foreground()
    Variable               = $Flavor.Lavender.Foreground()
}

# Set the colours
Set-PSReadLineOption -Colors $Colors

$PSStyle.Formatting.Debug = $Flavor.Sky.Foreground()
$PSStyle.Formatting.Error = $Flavor.Red.Foreground()
$PSStyle.Formatting.ErrorAccent = $Flavor.Blue.Foreground()
$PSStyle.Formatting.FormatAccent = $Flavor.Teal.Foreground()
$PSStyle.Formatting.TableHeader = $Flavor.Rosewater.Foreground()
$PSStyle.Formatting.Verbose = $Flavor.Yellow.Foreground()
$PSStyle.Formatting.Warning = $Flavor.Peach.Foreground()

$ENV:FZF_DEFAULT_OPTS = @"
--color=bg+:$($Flavor.Surface0),bg:$($Flavor.Base),spinner:$($Flavor.Rosewater)
--color=hl:$($Flavor.Red),fg:$($Flavor.Text),header:$($Flavor.Red)
--color=info:$($Flavor.Mauve),pointer:$($Flavor.Rosewater),marker:$($Flavor.Rosewater)
--color=fg+:$($Flavor.Text),prompt:$($Flavor.Mauve),hl+:$($Flavor.Red)
--color=border:$($Flavor.Surface2)
"@

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

# PSReadLine
Set-PSReadLineOption -BellStyle None
Set-PSReadlineOption -ShowToolTips
Set-PSReadLineOption -PredictionSource History
Set-PSReadLineOption -PredictionViewStyle ListView
Set-PSReadlineKeyHandler -Key Tab -Function MenuComplete
Set-PSReadLineKeyHandler -Key UpArrow -Function HistorySearchBackward
Set-PSReadLineKeyHandler -Key DownArrow -Function HistorySearchForward
Set-PSReadlineOption -HistorySearchCursorMovesToEnd

# PSFzf
Set-PSFzfOption -PSReadLineChordProvider 'Ctrl+f' -PSReadLineChordReverseHistory 'Ctrl+r'

Set-Alias -Name alias -Value Search-Alias

Set-Alias -Name c -Value Clear-Host

function lg {
    lazygit
}

function dots {
    Set-Location "x:\hub\repos\do75\"
}
function hub {
    Set-Location "x:\hub\"
}
function repos {
    Set-Location "x:\hub\repos\"
}
function q {
    Exit
}
function ps {
    Get-Process
}
function kill($psid) {
    Stop-Process -Name "$psid" -Force
}

function ll { exa -xHighmnSlFuU --all --git --octal-permissions --group-directories-first --icons }

function ls { exa -F --all --long --no-filesize --no-user --no-time --git --group-directories-first --icons --no-permissions }

function l { exa -F --all --long --no-filesize --no-user --no-time --git --group-directories-first --icons --no-permissions }

function .. {
    Set-Location ..
}

function ... {
    Set-Location ..\..
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

function path {
    $env:Path -split ';'
}

function ln($file1, $file2) {
    if (Test-Path $file1) {
        Remove-Item -Recurse -Force $file1
        New-Item -ItemType SymbolicLink -Path $file1 -Target $file2
    }
    else {
        New-Item -ItemType SymbolicLink -Path $file1 -Target $file2
    }
}
function lnk($file, $path1, $path2) {
    New-Item -ItemType SymbolicLink -Path "$path1\$file" -Target "$path2\$file"
}

function rlp {
    & $profile
}

function find-file($name) {
    Get-ChildItem -recurse -filter "*${name}*" -ErrorAction SilentlyContinue | ForEach-Object {
        $place_path = $_.directory
        Write-Output "${place_path}\${_}"
    }
}

function unzip ($file) {
    Write-Output("Extracting", $file, "to", $pwd)
    $fullFile = Get-ChildItem -Path $pwd -Filter .\cove.zip | ForEach-Object { $_.FullName }
    Expand-Archive -Path $fullFile -DestinationPath $pwd
}

function grep($regex, $dir) {
    if ( $dir ) {
        Get-ChildItem $dir | select-string $regex
        return
    }
    $input | select-string $regex
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

function rmf([string]$path) {
    Remove-Item -Recurse -Force $path
}

# Modules
Import-Module Terminal-Icons

$ChocolateyProfile = "$env:ChocolateyInstall\helpers\chocolateyProfile.psm1"
if (Test-Path($ChocolateyProfile)) {
    Import-Module "$ChocolateyProfile"
}


Invoke-Expression (&starship init powershell)

$ENV:STARSHIP_CACHE = "$HOME\AppData\Local\Temp"

Invoke-Expression -Command $(gh completion -s powershell | Out-String)

$WarningPreference = "SilentlyContinue"
# File for Current User, All Hosts - $PROFILE.CurrentUserAllHosts

if ($host.Name -eq 'ConsoleHost') {
    Import-Module PSReadLine
}

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

function ln($file1, $file2) {
    if (Test-Path $file1 = true) {
        Remove-Item -Recurse -Force $file1
        New-Item -ItemType SymbolicLink -Path $file1 -Target $file2
    } else {
        New-Item -ItemType SymbolicLink -Path $file1 -Target $file2
    }
}

function dots {
    Set-Location "x:\hub\repos\dots\"
    Clear-Host
    exa -F --all --long --no-filesize --no-user --no-time --git --group-directories-first --icons --no-permissions
}
function hub {
    Set-Location "x:\hub\"
    Clear-Host
    exa -F --all --long --no-filesize --no-user --no-time --git --group-directories-first --icons --no-permissions
}
function repos {
    Set-Location "x:\hub\repos\"
    Clear-Host
    exa -F --all --long --no-filesize --no-user --no-time --git --group-directories-first --icons --no-permissions
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
    Clear-Host
    exa -F --all --long --no-filesize --no-user --no-time --git --group-directories-first --icons --no-permissions
}

function ... {
    Set-Location ..\..
    Clear-Host
    exa -F --all --long --no-filesize --no-user --no-time --git --group-directories-first --icons --no-permissions
}

Function Search-Alias {
    param (
        [string]$alias
    )
    if ($alias){
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
    if (Test-Path $file1 = true) {
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
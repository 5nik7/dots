# if (Get-Module PSFzf -ListAvailable) {
#     Import-Module -Name PSFzf
# }
# Set-PSReadLineKeyHandler -Key Tab -ScriptBlock { Invoke-FzfTabCompletion }
# Set-PsFzfOption -TabExpansion

. "$Env:DOTCACHE\wal\wal.ps1"

$script:RunningInWindowsTerminal = [bool]($env:WT_Session) -or [bool]($env:ConEmuANSI)
if ($script:RunningInWindowsTerminal -and (Test-CommandExists fd)) {
    $script:DefaultFileSystemFdCmd = "fd.exe --color always --type f --fixed-strings --strip-cwd-prefix --hidden --exclude .git"
} else {
    $script:DefaultFileSystemFdCmd = "fd.exe --type f --fixed-strings --strip-cwd-prefix --hidden --exclude .git"
}
$script:DefaultFileSystemFdCmd = $FZF_DEFAULT_COMMAND
$env:FZF_DEFAULT_COMMAND = $FZF_DEFAULT_COMMAND

$FzfPreview = "bat --style=numbers --color=always {}"
$previewString = "--preview='$FzfPreview'"

$fzfOptions = @{
    style = "full"
    padding = 0
    margin = 0
    ansi = $true
    layout = "reverse"
    multi = $true
    height = "80%"
    minheight = 20
    tabstop = 2
    border = "sharp"
    listborder = "sharp"
    inputborder = "sharp"
    info = "inline"
    previewwindow = "right:60%,border-sharp"
    delimiter = ":"
    prompt = @{ symbol = "> " }
    pointer = @{ symbol = "┃" }
    marker = @{ symbol = "│" }
    separator = [FzfSymbolOpts]@{ 
        enabled = $false
        symbol = "-"
        }
    scrollbar = [FzfSymbolOpts]@{ 
        enabled = $false
        symbol = '│'
        }
 }


$colorOptions = @{
    'label' = '7'
    'selected-bg' = '0'
    'header' = '8'
    'gutter' = '-1'
    'marker' = '14'
    'fg+' = '6'
    'spinner' = '8'
    'query' = '5'
    'border' = '0'
    'pointer' = '14'
    'info' = '8'
    'preview-bg' = "$bg"
    'list-border' = '0'
    'bg+' = '-1'
    'preview-border' = '0'
    'bg' = '-1'
    'hl' = '8:underline'
    'prompt' = '8'
    'fg' = '0'
    'preview-label' = '0'
    'hl+' = '2:underline'
    'input-border' = '0'
    'separator' = "$bg"
}

$colorString = ($colorOptions.GetEnumerator() | ForEach-Object { "$($_.Key):$($_.Value)" }) -join ','
$colorArg = "--color=$colorString"

$key_mapping = @{
    minheight = "min-height"
    listborder = "list-border"
    inputborder = "input-border"
    previewwindow = "preview-window"
}

$fzfString = ($fzfOptions.GetEnumerator() | ForEach-Object {
    $key = if ($key_mapping.ContainsKey($_.Key)) { $key_mapping[$_.Key] } else { $_.Key }
    if ($_.Value -is [bool]) { "--{0}" -f $key }
    elseif ($_.Value -is [FzfSymbolOpts] -and $_.Value.enabled -eq $false) { "--no-{0}" -f $key }
    elseif ($_.Value.symbol) { "--{0}='{1}'" -f $key, $_.Value.symbol }
    else { "--{0}={1}" -f $key, $_.Value }
}) -join ' '


$env:FZF_DEFAULT_OPTS = $fzfString + ' ' + $colorArg + ' ' + $previewString
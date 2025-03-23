. "$Env:DOTCACHE\wal\wal.ps1"

function FuzzyOpts {
    param (
        [switch]$f,
        [switch]$d
    )

    $Env:FZF_FILE_OPTS = "--preview=`"bat --style=numbers --color=always {}`" --preview-window=border-sharp --preview-label=`" PREVIEW `" --border=sharp --border-label=`" FILES `" --tabstop=2 --color=16 --bind=ctrl-d:preview-half-page-down,ctrl-u:preview-half-page-up"
    $Env:FZF_DIRECTORY_OPTS = "--preview=`"eza -la --color=always --group-directories-first --icons --no-permissions --no-time --no-filesize --no-user --git-repos --git --follow-symlinks --no-quotes --stdin {}`" --preview-window=border-sharp --preview-label=`" PREVIEW `" --border=sharp --border-label=`" DIRECTORIES `" --tabstop=2 --color=16 --bind=ctrl-d:preview-half-page-down,ctrl-u:preview-half-page-up"

    $Env:FZF_DEFAULT_COMMAND = "fd --type f --strip-cwd-prefix --hidden --exclude .git"
    $previewString = ''

     if ($f) {
        $Env:FZF_DEFAULT_COMMAND = "fd --type f --strip-cwd-prefix --hidden --exclude .git"
        $previewString = $Env:FZF_FILE_OPTS
    }
    if ($d) {
        $Env:FZF_DEFAULT_COMMAND = "fd --type d --strip-cwd-prefix --hidden --exclude .git"
        $previewString = $Env:FZF_DIRECTORY_OPTS
    }
    try {

    class FzfSymbolOpts {
        [bool]$enabled
        [string]$symbol
    }

    $fzfOptions = @{
        style         = "full"
        padding       = 0
        margin        = 0
        ansi          = $true
        layout        = "reverse"
        multi         = $true
        height        = "80%"
        minheight     = 20
        tabstop       = 2
        border        = "sharp"
        listborder    = "sharp"
        inputborder   = "sharp"
        info          = "inline"
        previewwindow = "right:60%,border-sharp"
        delimiter     = ":"
        prompt        = @{ symbol = "> " }
        pointer       = @{ symbol = "┃" }
        marker        = @{ symbol = "│" }
        separator     = [FzfSymbolOpts]@{
            enabled = $false
            symbol  = "-"
        }
        scrollbar     = [FzfSymbolOpts]@{
            enabled = $false
            symbol  = '│'
        }
    }

    $colorOptions = @{
        'fg'             = '8'
        'hl'             = '7:underline'
        'fg+'            = '6'
        'hl+'            = '2:underline'
        'bg'             = '-1'
        'bg+'            = '-1'
        'preview-bg'     = "$bg"
        'preview-border' = '0'
        'list-border'    = '0'
        'border'         = '0'
        'input-border'   = '0'
        'pointer'        = '6'
        'label'          = '7'
        'header'         = '8'
        'gutter'         = '-1'
        'marker'         = '14'
        'spinner'        = '8'
        'query'          = '5'
        'info'           = '8'
        'prompt'         = '2'
        'preview-label'  = '0'
        'selected-bg'    = '0'
        'separator'      = "$bg"
    }

    $colorString = ($colorOptions.GetEnumerator() | ForEach-Object { "$($_.Key):$($_.Value)" }) -join ','
    $colorArg = "--color=$colorString"

    $key_mapping = @{
        minheight     = "min-height"
        listborder    = "list-border"
        inputborder   = "input-border"
        previewwindow = "preview-window"
    }

    $fzfString = ($fzfOptions.GetEnumerator() | ForEach-Object {
        $key = if ($key_mapping.ContainsKey($_.Key)) { $key_mapping[$_.Key] } else { $_.Key }
        if ($_.Value -is [bool]) { "--{0}" -f $key }
        elseif ($_.Value -is [FzfSymbolOpts] -and $_.Value.enabled -eq $false) { "--no-{0}" -f $key }
        elseif ($_.Value.symbol) { "--{0}='{1}'" -f $key, $_.Value.symbol }
        else { "--{0}={1}" -f $key, $_.Value }
    }) -join ' '

    $Global:FZF_DEFAULT_OPTS = $fzfString + ' ' + $colorArg + ' ' + $previewString
    $Env:FZF_DEFAULT_OPTS = $Global:FZF_DEFAULT_OPTS
    return $Global:FZF_DEFAULT_OPTS
} catch {
    Write-Host "Error: $_"
    }
}

$Global:FZF_DEFAULT_OPTS = FuzzyOpts


function fh {

  $Global:FZF_DEFAULT_OPTS = FuzzyOpts

    # Searches your command history, sets your clipboard to the selected item - Usage: fh [<string>]
    $find = $args
    $Global:FZF_DEFAULT_OPTS += ' ' + "--border-label=`" HISTORY `" --tabstop=2 --color=16"
    # $Env:FZF_DEFAULT_OPTS = $FZF_DEFAULT_OPTS
    $selected = Get-Content (Get-PSReadlineOption).HistorySavePath | ? {$_ -like "*$find*"} | Sort-Object -Unique -Descending | fzf
    if (![string]::IsNullOrWhiteSpace($selected)) { Set-Clipboard $selected }
}

function fzc {

   $Global:FZF_DEFAULT_OPTS = FuzzyOpts -f
    # Runs fzf searching files then cd's to the directory of the selected file - Usage: fzc [d | u | c]
    if ($args -eq "d" -or $args.Count -eq 0) { cd $Env:DOTS }
    elseif ($args -eq "u") { cd $Env:USERPROFILE }
    elseif ($args -eq "c") { cd C:\ }
    else {
        echo "Invalid argument: $args"
        return
    }
    $Host.UI.RawUI.WindowTitle = "FZF"
    $selected = fzf
    if (![string]::IsNullOrWhiteSpace($selected)) {
        $parent = Split-Path -parent -path $selected
        cd $parent
    } else { cd C:\ }
}

function fze {

    $Global:FZF_DEFAULT_OPTS = FuzzyOpts -f

    # Runs fzf searching files then opens the directory of the selected file in explorer - Usage: fze [d | u | c]
    if ($args -eq "d" -or $args.Count -eq 0) { cd $Env:DOTS }
    elseif ($args -eq "u") { cd $Env:USERPROFILE }
    elseif ($args -eq "c") { cd C:\ }
    else {
        echo "Invalid argument: $args"
        return
    }
    $Host.UI.RawUI.WindowTitle = "FZF"
    $selected = fzf
    if (![string]::IsNullOrWhiteSpace($selected)) {
        $parent = Split-Path -parent -path $selected
        cd $parent
        explorer .
    } else { cd C:\ }
}

function fzn {

   $Global:FZF_DEFAULT_OPTS = FuzzyOpts -f

    # Runs fzf searching files then opens the directory of the selected file in neovim - Usage: fzn [d | u | c]
    if ($args -eq "d" -or $args.Count -eq 0) { cd $Env:DOTS }
    elseif ($args -eq "u") { cd $Env:USERPROFILE }
    elseif ($args -eq "c") { cd C:\ }
    else {
        echo "Invalid argument: $args"
        return
    }
    $Host.UI.RawUI.WindowTitle = "FZF"
    $selected = fzf
    if (![string]::IsNullOrWhiteSpace($selected)) {
        $parent = Split-Path -parent -path $selected
        cd $parent
        $p = Split-Path -leaf -path (Get-Location)
        $Host.UI.RawUI.WindowTitle = "$p"
        nvim .
    } else { cd C:\ }
}

function dzc {

   $Global:FZF_DEFAULT_OPTS = FuzzyOpts -d

    # Runs fzf searching directories then cd's to the selected directory - Usage: dzc [d | u | c]
    if ($args -eq "d" -or $args.Count -eq 0) { cd $Env:DOTS }
    elseif ($args -eq "u") { cd $Env:USERPROFILE }
    elseif ($args -eq "c") { cd C:\ }
    else {
        echo "Invalid argument: $args"
        return
    }
    $Host.UI.RawUI.WindowTitle = "FZF"
    $selected = fzf
    if (![string]::IsNullOrWhiteSpace($selected)) { cd $selected }
    else { cd C:\ }
}

function dze {

     $Global:FZF_DEFAULT_OPTS = FuzzyOpts -d

    # Runs fzf searching directories then opens the selected directory in explorer - Usage: dze [d | u | c]
    if ($args -eq "d" -or $args.Count -eq 0) { cd $Env:DOTS }
    elseif ($args -eq "u") { cd $Env:USERPROFILE }
    elseif ($args -eq "c") { cd C:\ }
    else {
        echo "Invalid argument: $args"
        return
    }
    $Host.UI.RawUI.WindowTitle = "FZF"
    $selected = fzf
    if (![string]::IsNullOrWhiteSpace($selected)) {
        cd $selected
        explorer .
    } else { cd C:\ }
}

function dzn {

    $Global:FZF_DEFAULT_OPTS = FuzzyOpts -d

    # Runs fzf searching directories then opens the selected directory in neovim - Usage: dzn [d | u | c]
    if ($args -eq "d" -or $args.Count -eq 0) { cd $Env:DOTS }
    elseif ($args -eq "u") { cd $Env:USERPROFILE }
    elseif ($args -eq "c") { cd C:\ }
    else {
        echo "Invalid argument: $args"
        return
    }
    $Host.UI.RawUI.WindowTitle = "FZF"
    $selected = fzf
    if (![string]::IsNullOrWhiteSpace($selected)) {
        cd $selected
        $p = Split-Path -leaf -path (Get-Location)
        $Host.UI.RawUI.WindowTitle = "$p"
        nvim .
    } else { cd C:\ }
}

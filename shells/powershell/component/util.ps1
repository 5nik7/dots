if ([int]$env:padding) { [int]$padding = [int]$env:padding }
else { [int]$padding = 0 }

$util = @{
    colors = @{
        Black       = 0
        DarkRed     = 1
        DarkGreen   = 2
        DarkYellow  = 3
        DarkBlue    = 4
        DarkMagenta = 5
        DarkCyan    = 6
        Gray        = 7
        DarkGray    = 8
        Red         = 9
        Green       = 10
        Yellow      = 11
        Blue        = 12
        Magenta     = 13
        Cyan        = 14
        White       = 15
    }
    alerts = @{
        info    = @{
            text  = 'Info'
            icon  = "󰋽 "
            color = 'Magenta'
        }
        success = @{
            text  = 'Success'
            icon  = " "
            color = 'green'
        }
        warn    = @{
            text  = 'Warning'
            icon  = " "
            color = 'yellow'
        }
        err     = @{
            text  = 'Error'
            icon  = " "
            color = 'red'
        }
        symbols = @{
            "smallprompt"                     = @{ icon = "󰅂" }
            "smline"                          = @{ icon = "󱪼" }
            "ine"                             = @{ icon = "│" }
            "readhost"                        = @{ icon = "󱪼" }
            "block"                           = @{ icon = "" }
            "Google"                          = @{ icon = "" }
            "Apps"                            = @{ icon = "" }
            "nf-cod-circle_slash"             = @{ icon = "" }
            "nf-cod-chevron_right"            = @{ icon = "" }
            "nf-fa-angle_right"               = @{ icon = "" }
            "nf-fa-chevron_right"             = @{ icon = "" }
            "nf-oct-diff"                     = @{ icon = "" }
            "nf-md-alert"                     = @{ icon = "󰀦" }
            "nf-oct-alert"                    = @{ icon = "" }
            "nf-seti-error"                   = @{ icon = "" }
            "nf-fa-exclamation_triangle"      = @{ icon = "" }
            "nf-fa-triangle_exclamation"      = @{ icon = "" }
            "nf-md-solid"                     = @{ icon = "󰚍" }
            "nf-md-square"                    = @{ icon = "󰝤" }
            "nf-fa-square_full"               = @{ icon = "" }
            "nf-fa-square_o"                  = @{ icon = "" }
            "nf-md-card_outline"              = @{ icon = "󰭶" }
            "nf-seti-css"                     = @{ icon = "" }
            "nf-md-pound"                     = @{ icon = "󰐣" }
            "nf-md-regex"                     = @{ icon = "󰑑" }
            "nf-seti-search"                  = @{icon = "" }
            "nf-fa-times"                     = @{ icon = "" }
            "nf-cod-chrome_close"             = @{ icon = "" }
            "nf-fae-thin_close"               = @{ icon = "" }
            "nf-iec-power_off"                = @{ icon = "⭘" }
            "nf-cod-circle_large"             = @{ icon = "" }
            "nf-md-check_bold"                = @{ icon = "󰸞" }
            "nf-md-checkbox_blank"            = @{ icon = "󰄮" }
            "nf-md-rectangle"                 = @{ icon = "󰹞" }
            "nf-md-checkbox_intermediate"     = @{ icon = "󰡖" }
            "nf-md-circle_small"              = @{ icon = "󰧟" }
            "nf-md-circle_medium"             = @{ icon = "󰧞" }
            "nf-cod-circle_filled"            = @{ icon = "" }
            "nf-md-record"                    = @{ icon = "󰑊" }
            "nf-fa-asterisk"                  = @{ icon = "" }
            "nf-fa-at"                        = @{ icon = "" }
            "nf-md-at"                        = @{ icon = "󰁥" }
            "nf-oct-mention"                  = @{ icon = "" }
            "nf-fa-ban"                       = @{ icon = "" }
            "nf-fa-bolt"                      = @{ icon = "" }
            "nf-fa-certificate"               = @{ icon = "" }
            "nf-fa-genderless"                = @{ icon = "" }
            "nf-oct-dot"                      = @{ icon = "" }
            "nf-weather-degrees"              = @{ icon = "" }
            "nf-weather-fahrenheit"           = @{ icon = "" }
            "nf-weather-celsius"              = @{ icon = "" }
            "nf-fa-microsoft"                 = @{ icon = "" }
            "nf-fa-windows"                   = @{ icon = "" }
            "nf-cod-terminal_powershell"      = @{ icon = "" }
            "nf-seti-powershell"              = @{ icon = "" }
            "nf-md-debian"                    = @{ icon = "󰣚" }
            "nf-md-refresh"                   = @{ icon = "" }
            "nf-md-ubuntu"                    = @{ icon = "󰑐" }
            "nf-cod-debug_restart"            = @{ icon = "" }
            "nf-fa-repeat"                    = @{ icon = "" }
            "nf-md-restore"                   = @{ icon = "" }
            "nf-md-reload"                    = @{ icon = "󰑓" }
            "nf-md-sync"                      = @{ icon = "󰦛" }
            "nf-fa-question"                  = @{ icon = "" }
            "nf-oct-rel_file_path"            = @{ icon = "" }
            "nf-fa-search"                    = @{ icon = "" }
            "nf-md-magnify"                   = @{ icon = "󰍉" }
            "nf-fa-usd"                       = @{ icon = "" }
            "nf-fa-dollar_sign"               = @{ icon = "" }
            "nf-seti-shell"                   = @{ icon = "" }
            "nf-linux-neovim"                 = @{ icon = "" }
            "nf-md-ampersand"                 = @{ icon = "󰪍" }
            "nf-md-asterisk"                  = @{ icon = "󰛄" }
            "nf-fa-trash_can"                 = @{ icon = "" }
            "nf-fa-trash_o"                   = @{ icon = "" }
            "nf-md-flask_outline"             = @{ icon = "󰂖" }
            "nf-md-alert_rhombus_outline"     = @{ icon = "󱇏" }
            "nf-fa-star_o"                    = @{ icon = "" }
            "nf-oct-star"                     = @{ icon = "" }
            "nf-fa-star"                      = @{ icon = "" }
            "nf-oct-star_fill"                = @{ icon = "" }
            "nf-md-star"                      = @{ icon = "" }
            "nf-cod-star_full"                = @{ icon = "󰓎" }
            "nf-cod-star_empty"               = @{ icon = "" }
            "nf-md-star_outline"              = @{ icon = "󰓒" }
            "nf-md-star_box_outline"          = @{ icon = "󰩴" }
            "nf-md-star_face"                 = @{ icon = "󰦥" }
            "nf-oct-north_star"               = @{ icon = "" }
            "nf-md-format_letter_starts_with" = @{ icon = "󰾺" }
        }
    }
}
$spacer = " "
$divider = ": "
$successcolor = $($util.alerts.success.color)
$successicon = ($($util.alerts.success.icon) + $spacer)
$successtext = ($($util.alerts.success.text) + $divider)
$errcolor = $($util.alerts.err.color)
$erricon = ($($util.alerts.err.icon) + $spacer)
$errtext = ($($util.alerts.err.text) + $divider)
$warncolor = $($util.alerts.warn.color)
$warnicon = ($($util.alerts.warn.icon) + $spacer)
$warntext = ($($util.alerts.warn.text) + $divider)
$infocolor = $($util.alerts.info.color)
$infoicon = ($($util.alerts.info.icon) + $spacer)
$infotext = ($($util.alerts.info.text) + $divider)
# $textcolor = "White"

function linebreak {
    param (
        [int]$count = 1
    )
    for ($i = 0; $i -lt $count; $i++) {
        Write-Host ''
    }
}

<#
.SYNOPSIS
    Writes colored text to the console with optional boxing and padding.

.DESCRIPTION
    The wh function writes colored text to the console. It supports inline text, padding, and boxing.

.PARAMETER pairs
    The text and color pairs to be displayed. Each text should be followed by its color.

.PARAMETER nl
    If specified, adds a newline after the text.

.PARAMETER bb
    The number of blank lines before the text.

.PARAMETER ba
    The number of blank lines after the text.

.PARAMETER padout
    The amount of padding outside the box.

.PARAMETER padin
    The amount of padding inside the box.

.PARAMETER box
    If specified, displays the text inside a box.

.PARAMETER border
    The color of the box border. Default is "DarkGray".

.EXAMPLE
    wh -pairs "Hello", "Red", "World", "Green"
    Writes "Hello" in red and "World" in green to the console.

.EXAMPLE
    wh -pairs "Hello", "Red", "World", "Green" -box
    Writes "Hello" in red and "World" in green inside a box to the console.

.NOTES
    Author: njen
#>
function wh {
    [CmdletBinding()]
    param(
        [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
        [string[]]$pairs,
        [switch]$nl,
        [int]$bb = 0,
        [int]$ba = 0,
        [int]$padout = 0,
        [int]$padin = 1,
        [switch]$box,
        [string]$border = "DarkGray",
        [string]$esc,
        [string]$escol = "White"
    )
    if ($env:padding) {
        $padout = $env:padding
    }

    $boxSymbolTopLeft = "┌"
    $boxSymbolTopRight = "┐"
    $boxSymbolBottomLeft = "└"
    $boxSymbolBottomRight = "┘"
    $boxSymbolHorizontal = "─"
    $boxSymbolVertical = "│"

    linebreak $bb

    $pairsList = @()  # will hold objects like @{ text="Hello"; color="White"; length=... }
    $totalLength = 0

    # Collect pairs without printing right away
    for ($i = 0; $i -lt $pairs.Count; $i += 2) {
        $txt = $pairs[$i]
        $clr = if ($i + 1 -lt $pairs.Count) { $pairs[$i + 1] } else { 'White' }

        if ($clr -match '^\d+$') {
            $clr = $util.colors.GetEnumerator() | Where-Object { $_.Value -eq [int]$clr } | Select-Object -ExpandProperty Key
        }
        $colorEnum = [System.ConsoleColor]::GetValues([System.ConsoleColor]) | Where-Object { $_ -eq $clr }
        if (-not $colorEnum) {
            Write-Err "Invalid color: $clr"
            return
        }

        $pairsList += [pscustomobject]@{ text = $txt; color = $clr }
        $totalLength += $txt.Length
    }
    $totalLength += ($padin * 2)
    # Build the box lines (if -box is set)
    $boxTop = (" " * $padout) + $boxSymbolTopLeft + ($boxSymbolHorizontal * $totalLength) + $boxSymbolTopRight
    $boxBottom = (" " * $padout) + $boxSymbolBottomLeft + ($boxSymbolHorizontal * $totalLength) + $boxSymbolBottomRight
    $boxLeft = (" " * $padout) + $boxSymbolVertical + (" " * $padin)
    $boxRight = (" " * $padin) + $boxSymbolVertical

    if ($box) {
        # Print top line
        Write-Host $boxTop -ForegroundColor $border
        # Print middle line start
        Write-Host -NoNewline $boxLeft -ForegroundColor $border
        # Print each pair with its color inside the box
        foreach ($pair in $pairsList) {
            Write-Host -NoNewline $pair.text -ForegroundColor $pair.color
        }
        # Print right boundary
        if ($esc) {
            $escOutput = (" " * $padin) + $esc
            Write-Host -NoNewline $boxRight -ForegroundColor $border
            Write-Host $escOutput -ForegroundColor $escol
        }
        else {
            Write-Host $boxRight -ForegroundColor $border
        }
        # Print bottom line
        Write-Host $boxBottom -ForegroundColor $border
    }
    else {
        # No box: just print each pair
        foreach ($pair in $pairsList) {
            Write-Host -NoNewline $pair.text -ForegroundColor $pair.color
        }
    }

    if ($nl) { linebreak }
    linebreak $ba
}

function Write-Info {
    param(
        [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
        [string[]]$pairs,
        [switch]$box
    )
    $pairs = @($infoicon, $infocolor, $infotext, $infocolor) + $pairs
    wh -pairs $pairs -bb 1 -padout $padding -box:$box
}

function Write-Success {
    param(
        [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
        [string[]]$pairs,
        [switch]$box
    )
    $pairs = @($successicon, $successcolor, $successtext, $successcolor) + $pairs
    wh -pairs $pairs -bb 1 -padout $padding -box:$box
}

function Write-Err {
    param(
        [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
        [string[]]$pairs,
        [switch]$box
    )
    $pairs = @($erricon, $errcolor, $errtext, $errcolor) + $pairs
    wh -pairs $pairs -bb 1 -padout $padding -box:$box
}

function Write-Warn {
    param(
        [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
        [string[]]$pairs,
        [switch]$box
    )
    $pairs = @($warnicon, $warncolor, $warntext, $warncolor) + $pairs
    wh -pairs $pairs -bb 1 -padout $padding -box:$box
}

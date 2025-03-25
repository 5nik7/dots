
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
            text  = "Info:"
            icon  = "󰋽"
            color = "Magenta"
        }
        success = @{
            text  = "Success:"
            icon  = ""
            color = "Green"
        }
        warn    = @{
            text  = "Warning:"
            icon  = ""
            color = "Yellow"
        }
        err     = @{
            text  = "Error:"
            icon  = "󰱥"
            color = "Red"
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
$successcolor = $($util.alerts.success.color)
$successicon = $($util.alerts.success.icon)
$successtext = $($util.alerts.success.text)
$errcolor = $($util.alerts.err.color)
$erricon = $($util.alerts.err.icon)
$errtext = $($util.alerts.err.text)
$warncolor = $($util.alerts.warn.color)
$warnicon = $($util.alerts.warn.icon)
$warntext = $($util.alerts.warn.text)
$infocolor = $($util.alerts.info.color)
$infoicon = $($util.alerts.info.icon)
$infotext = $($util.alerts.info.text)
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
    Writes colored text to the console.

.DESCRIPTION
    The Write-Color function writes colored text to the console. It supports inline text, color tables, and help information.

.PARAMETER inline
    If specified, writes the text inline without a newline at the end.

.PARAMETER color
    The color of the text. Default is an empty string, which prompts the user to input a color.

.PARAMETER text
    The text to be displayed. If not specified, prompts the user to input the text.

.PARAMETER table
    If specified, displays a color table with available colors.

.PARAMETER help
    If specified, displays help information on how to use the function.

.EXAMPLE
    Write-Color -color "Red" -text "Hello, World!"
    Writes "Hello, World!" in red color to the console.

.EXAMPLE
    Write-Color -table
    Displays a color table with available colors.

.NOTES
    Author: njen
#>
function Write-Color {
    [CmdletBinding()]
    param (
        [switch]$inline,
        [string]$color = "",
        [Parameter(ValueFromRemainingArguments = $true)]
        [string]$text,
        [switch]$table,
        [switch]$help
    )

    if ($help) {
        Get-Help -Name Write-Color -Full
        return
    }

    if ($table) {
        $borderColor = "DarkGray"
        Write-Box -text "Color Table" -border $borderColor -color $borderColor
        foreach ($colorName in $util.colors.Keys | Sort-Object { $util.colors[$_] }) {
            $colorSpacer = 4
            $colorSpacerOut = " " * $colorSpacer
            $colorDivider = "│"
            $colorValue = $util.colors[$colorName]
            if ($colorValue -lt 10) { $colorValue = "$colorValue " }
            Write-Host -foregroundColor $colorName ($colorSpacerOut + (nf md-solid)) -NoNewline
            Write-Host -foregroundColor $borderColor "  $colorDivider " -NoNewline
            Write-Host -foregroundColor $colorName "$colorValue" -NoNewline
            Write-Host -foregroundColor $borderColor " $colorDivider " -NoNewline
            Write-Host -foregroundColor $colorName "$colorName"
        }
        linebreak 2
        return
    }

    if ($color -eq "") { $color = Read-Host "Color" }
    if (-not $text) { $text = Read-Host "Text" }

    # Check if the color is a numeric value and map it to the corresponding color name
    if ($color -match '^\d+$') {
        $color = $util.colors.GetEnumerator() | Where-Object { $_.Value -eq [int]$color } | Select-Object -ExpandProperty Key
    }

    $colorEnum = [System.ConsoleColor]::GetValues([System.ConsoleColor]) | Where-Object { $_ -eq $color }
    if ($null -eq $colorEnum) {
        Write-Err "Invalid color: $color"
        return
    }

    $outputText = $text -join " "

    if ($inline) {
        Write-Host -foregroundColor $color "$outputText" -NoNewline
        return
    }
    Write-Host -foregroundColor $color "$outputText"
}

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
        [string]$border = "DarkGray"
    )

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
        Write-Host $boxRight -ForegroundColor $border
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
        [string]$t = "",
        [string]$tc = $infocolor,
        [string]$ii = $infoicon,
        [string]$ic = $infocolor,
        [string]$it = $infotext
    )
    $iconout = wh -t "$ii $it" -c $ic -bb 1 -pad $padding
    $txtout = wh -t "$t" -c $tc -ba 1
    $iconout + $txtout
}

function Write-Success {
    param(
        [string]$t = "",
        [string]$tc = $successcolor,
        [string]$si = $successicon,
        [string]$sc = $successcolor,
        [string]$st = $successtext
    )
    $iconout = wh -t "$si $st" -c $sc -bb 1 -pad $padding
    $txtout = wh -t "$t" -c $tc -ba 1
    $iconout + $txtout
}

function Write-Warn {
    param(
        [string]$t = "",
        [string]$tc = $warncolor,
        [string]$wi = $warnicon,
        [string]$wc = $warncolor,
        [string]$wt = $warntext
    )
    $iconout = wh -t "$wi $wt" -c $wc -bb 1 -pad $padding
    $txtout = wh -t "$t" -c $tc -ba 1
    $iconout + $txtout
}

function Write-Err {
    param(
        [string]$t = "",
        [string]$tc = $errcolor,
        [string]$ei = $erricon,
        [string]$ec = $errcolor,
        [string]$et = $errtext
    )
    $iconout = wh -t "$ei $et" -c $ec -bb 1 -pad $padding
    $txtout = wh -t "$t" -c $tc -ba 1
    $iconout + $txtout

}

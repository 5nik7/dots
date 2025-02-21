$util = @{
    colors  = @{
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
    symbols = @{
        info                          = @{
            text  = "INFO:"
            icon  = ""
            color = "Green"
        }
        success                       = @{
            text  = "SUCCESS:"
            icon  = ""
            color = "Green"
        }
        warn                          = @{
            text  = "WARNING:"
            icon  = ""
            color = "Yellow"
        }
        err                           = @{
            text  = "ERROR:"
            icon  = "󰱥"
            color = "Red"
        }
        "smallprompt"                 = @{ icon = "󰅂" }
        "smline"                      = @{ icon = "󱪼" }
        "ine"                         = @{ icon = "│" }
        "readhost"                    = @{ icon = "󱪼" }
        "block"                       = @{ icon = "" }
        "Google"                      = @{ icon = "" }
        "Apps"                        = @{ icon = "" }
        "nf-cod-circle_slash"         = @{ icon = "" }
        "nf-cod-chevron_right"        = @{ icon = "" }
        "nf-fa-angle_right"           = @{ icon = "" }
        "nf-fa-chevron_right"         = @{ icon = "" }
        "nf-oct-diff"                 = @{ icon = "" }
        "nf-md-alert"                 = @{ icon = "󰀦" }
        "nf-oct-alert"                = @{ icon = "" }
        "nf-seti-error"               = @{ icon = "" }
        "nf-fa-exclamation_triangle"  = @{ icon = "" }
        "nf-fa-triangle_exclamation"  = @{ icon = "" }
        "nf-md-solid"                 = @{ icon = "󰚍" }
        "nf-md-square"                = @{ icon = "󰝤" }
        "nf-fa-square_full"           = @{ icon = "" }
        "nf-fa-square_o"              = @{ icon = "" }
        "nf-md-card_outline"          = @{ icon = "󰭶" }
        "nf-seti-css"                 = @{ icon = "" }
        "nf-md-pound"                 = @{ icon = "󰐣" }
        "nf-md-regex"                 = @{ icon = "󰑑" }
        "nf-seti-search"              = @{icon = "" }
        "nf-fa-times"                 = @{ icon = "" }
        "nf-cod-chrome_close"         = @{ icon = "" }
        "nf-fae-thin_close"           = @{ icon = "" }
        "nf-iec-power_off"            = @{ icon = "⭘" }
        "nf-cod-circle_large"         = @{ icon = "" }
        "nf-md-check_bold"            = @{ icon = "󰸞" }
        "nf-md-checkbox_blank"        = @{ icon = "󰄮" }
        "nf-md-rectangle"             = @{ icon = "󰹞" }
        "nf-md-checkbox_intermediate" = @{ icon = "󰡖" }
        "nf-md-circle_small"          = @{ icon = "󰧟" }
        "nf-md-circle_medium"         = @{ icon = "󰧞" }
        "nf-cod-circle_filled"        = @{ icon = "" }
        "nf-md-record"                = @{ icon = "󰑊" }
        "nf-fa-asterisk"              = @{ icon = "" }
        "nf-fa-at"                    = @{ icon = "" }
        "nf-md-at"                    = @{ icon = "󰁥" }
        "nf-oct-mention"              = @{ icon = "" }
        "nf-fa-ban"                   = @{ icon = "" }
        "nf-fa-bolt"                  = @{ icon = "" }
        "nf-fa-certificate"           = @{ icon = "" }
        "nf-fa-genderless"            = @{ icon = "" }
        "nf-oct-dot"                  = @{ icon = "" }
        "nf-weather-degrees"          = @{ icon = "" }
        "nf-weather-fahrenheit"       = @{ icon = "" }
        "nf-weather-celsius"          = @{ icon = "" }
        "nf-fa-microsoft"             = @{ icon = "" }
        "nf-fa-windows"               = @{ icon = "" }
        "nf-cod-terminal_powershell"  = @{ icon = "" }
        "nf-seti-powershell"          = @{ icon = "" }
        "nf-md-debian"                = @{ icon = "󰣚" }
        "nf-md-refresh"               = @{ icon = "" }
        "nf-md-ubuntu"                = @{ icon = "󰑐" }
        "nf-cod-debug_restart"        = @{ icon = "" }
        "nf-fa-repeat"                = @{ icon = "" }
        "nf-md-restore"               = @{ icon = "" }
        "nf-md-reload"                = @{ icon = "󰑓" }
        "nf-md-sync"                  = @{ icon = "󰦛" }
        "nf-fa-question"              = @{ icon = "" }
        "nf-oct-rel_file_path"        = @{ icon = "" }
        "nf-fa-search"                = @{ icon = "" }
        "nf-md-magnify"               = @{ icon = "󰍉" }
        "nf-fa-star"                  = @{ icon = "" }
        "nf-fa-usd"                   = @{ icon = "" }
        "nf-fa-dollar_sign"           = @{ icon = "" }
        "nf-seti-shell"               = @{ icon = "" }
        "nf-linux-neovim"             = @{ icon = "" }
        "nf-md-ampersand"             = @{ icon = "󰪍" }
        "nf-md-asterisk"              = @{ icon = "󰛄" }
        "nf-fa-trash_can"             = @{ icon = "" }
        "nf-fa-trash_o"               = @{ icon = "" }
        "nf-md-flask_outline"         = @{ icon = "󰂖" }
    }
}

# Create a reverse mapping of colors
$c = @{}
foreach ($color in $util.colors.GetEnumerator()) {
    $c[$color.Value] = $color.Key
}

function linebreak {
    param (
        [int]$count = 1
    )
    for ($i = 0; $i -lt $count; $i++) {
        Write-Host ''
    }
}

function Write-Color {
    [CmdletBinding()]
    param (
        [string]$color = "",
        [Parameter(ValueFromRemainingArguments = $true)]
        [string]$text,
        [switch]$inline,
        [switch]$table
    )
    if ($table) {
        foreach ($colorName in $util.colors.Keys | Sort-Object { $util.colors[$_] }) {
            $colorValue = $util.colors[$colorName]
            Write-Host -foregroundColor $colorName "$($util.symbols.'nf-md-solid'.icon)" -NoNewline
            Write-Host -foregroundColor White " $colorValue" -NoNewline
            Write-Host -foregroundColor $colorName " = " -NoNewline
            Write-Host -foregroundColor White "$colorName"
        }
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

function Write-Info {
    param([string]$text = "")
    if ($text -eq "" ) {
        linebreak 1
        Write-Color "$($util.symbols.info.color)" " $($util.symbols.info.icon) $($util.symbols.info.text) " -inline
        return
    }
    linebreak 1
    Write-Color "$($util.symbols.info.color)" " $($util.symbols.info.icon) $($util.symbols.info.text) " -inline
    Write-Color White $text
    linebreak
}

function Write-Success {
    param([string]$text = "")
    if ($text -eq "" ) {
        linebreak 1
        Write-Color "$($util.symbols.success.color)" " $($util.symbols.success.icon) $($util.symbols.success.text) " -inline
        return
    }
    linebreak 1
    Write-Color "$($util.symbols.success.color)" " $($util.symbols.success.icon) $($util.symbols.success.text) " -inline
    Write-Color White $text
    linebreak
}

function Write-Warn {
    param([string]$text = "")
    if ($text -eq "" ) {
        linebreak 1
        Write-Color "$($util.symbols.warn.color)" " $($util.symbols.warn.icon) $($util.symbols.warn.text) " -inline
        return
    }
    linebreak 1
    Write-Color "$($util.symbols.warn.color)" " $($util.symbols.warn.icon) $($util.symbols.warn.text) " -inline
    Write-Color White $text
    linebreak
}

function Write-Err {
    param([string]$text = "")
    if ($text -eq "" ) {
        linebreak 1
        Write-Color "$($util.symbols.err.color)" " $($util.symbols.err.icon) $($util.symbols.err.text) " -inline
        return
    }
    linebreak 1
    Write-Color "$($util.symbols.err.color)" " $($util.symbols.err.icon) $($util.symbols.err.text) " -inline
    Write-Color White $text
    linebreak
}

function Write-Box {
    param (
        [string]$message,
        [string]$borderColor = "DarkGray",
        [string]$textColor = "White"
    )

    $boxPadddingOut = 2
    $boxPadddingIn = 1

    $boxPadddingOutSpaces = " " * $boxPadddingOut
    $boxPadddingInSpaces = " " * $boxPadddingIn

    $boxSymbolTopLeft = "┌"
    $boxSymbolTopRight = "┐"
    $boxSymbolBottomLeft = "└"
    $boxSymbolBottomRight = "┘"
    $boxSymbolHorizontal = "─"
    $boxSymbolVertical = "│"

    $paddingLength = $boxPadddingIn * 2
    $length = $message.Length + $paddingLength

    $boxTop = $boxPadddingOutSpaces + $boxSymbolTopLeft + ($boxSymbolHorizontal * $length) + $boxSymbolTopRight
    $boxMiddleLeft = $boxPadddingOutSpaces + $boxSymbolVertical + $boxPadddingInSpaces
    $boxMiddleRight = $boxPadddingInSpaces + $boxSymbolVertical
    $boxTopBottom = $boxPadddingOutSpaces + $boxSymbolBottomLeft + ($boxSymbolHorizontal * $length) + $boxSymbolBottomRight

    linebreak
    Write-Color $borderColor $boxTop
    Write-Color $borderColor $boxMiddleLeft -inline
    Write-Color $textColor $message -inline
    Write-Color $borderColor $boxMiddleRight
    Write-Color $borderColor $boxTopBottom
    linebreak
}

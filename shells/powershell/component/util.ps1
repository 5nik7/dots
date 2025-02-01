$util = @{
    colors  = @{
        "Black"       = 0
        "DarkRed"     = 1
        "DarkGreen"   = 2
        "DarkYellow"  = 3
        "DarkBlue"    = 4
        "DarkMagenta" = 5
        "DarkCyan"    = 6
        "Gray"        = 7
        "DarkGray"    = 8
        "Red"         = 9
        "Green"       = 10
        "Yellow"      = 11
        "Blue"        = 12
        "Magenta"     = 13
        "Cyan"        = 14
        "White"       = 15
    }
    symbols = @{
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
        smallprompt                   = @{ icon = "󰅂󱪼" }
        smline                        = @{ icon = "󱪼" }
        ine                           = @{ icon = "│" }
        readhost                      = @{ icon = "󱪼" }
        diameter                      = @{ icon = "" }
        block                         = @{ icon = "" }
        Google                        = @{ icon = "" }
        Apps                          = @{ icon = "" }
        "nf-seti-css"                 = @{ icon = "" }
        "nf-seti-search"              = @{icon = "" }
        "nf-weather-fahrenheit"       = @{ icon = "" }
        "nf-cod-chrome_close"         = @{ icon = "" }
        "nf-fae-thin_close"           = @{ icon = "" }
        "nf-iec-power_off"            = @{ icon = "⭘" }
        "nf-md-check_bold"            = @{ icon = "󰸞" }
        "nf-md-checkbox_blank"        = @{ icon = "󰄮" }
        "nf-md-checkbox_intermediate" = @{ icon = "󰡖" }
        "nf-md-circle_small"          = @{ icon = "󰧟" }
        "nf-md-circle_medium"         = @{ icon = "󰧞" }
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
        [string[]]$text,
        [switch]$inline,
        [switch]$table
    )
    if ($table) {
        foreach ($colorName in $util.colors.Keys | Sort-Object { $util.colors[$_] }) {
            $colorValue = $util.colors[$colorName]
            Write-Host -foregroundColor $colorName "$colorValue - $colorName"
            Write-Host -foregroundColor $colorName "$colorValue - $colorName"
        }
        return
    }

    if ($color -eq "") { $color = Read-Host "Color" }
    if (-not $text) { $text = Read-Host "Text" }

    $colorEnum = [System.ConsoleColor]::GetValues([System.ConsoleColor]) | Where-Object { $_ -eq $color }
    if (-not $colorEnum) {
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

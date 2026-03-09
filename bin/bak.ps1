[CmdletBinding()]
param(
    [Alias('h')]
    [switch]$Help,

    [Alias('s')]
    [switch]$Store,

    [Alias('y')]
    [switch]$Yes,

    [Alias('q')]
    [switch]$Quiet,

    [Alias('v')]
    [switch]$VerboseMode,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Paths
)

Set-StrictMode -Version Latest

$Esc = [char]27
$c_reset     = "$Esc[0m"
$bold        = "$Esc[1m"
$dim         = "$Esc[2m"
$italic      = "$Esc[3m"
$underline   = "$Esc[4m"
$rev         = "$Esc[7m"

$fg_black    = "$Esc[1;30m"
$fg_red      = "$Esc[1;31m"
$fg_green    = "$Esc[1;32m"
$fg_yellow   = "$Esc[1;33m"
$fg_darkblue = "$Esc[0;34m"
$fg_blue     = "$Esc[1;34m"
$fg_magenta  = "$Esc[1;35m"
$fg_cyan     = "$Esc[1;36m"
$fg_white    = "$Esc[1;37m"

$trashico   = ""
$arrowico_l = "<-"
$arrowico_r = "->"
$arrowcolor = $fg_black
$errico     = ""
$errcolor   = $fg_red
$warnico    = ""
$warncolor  = $fg_yellow
$trashcolor = $fg_green
$dircolor   = $fg_darkblue

$BOLD      = $bold
$UNDERLINE = $underline
$ITALIC    = $italic
$DIM       = $dim
$INVERT    = $rev
$BLINK     = ""
$INVIS     = ""
$GREY      = $fg_white
$BLACK     = $fg_black
$RED       = $fg_red
$GREEN     = $fg_green
$YELLOW    = $fg_yellow
$BLUE      = $fg_blue
$DARKBLUE  = $fg_darkblue
$MAGENTA   = $fg_magenta
$CYAN      = $fg_cyan
$NO_COLOR  = $c_reset

function Write-OutputLine {
    param([Parameter(ValueFromRemainingArguments = $true)][object[]]$Message)
    Write-Host (" " + ($Message -join ' '))
}

function Write-ErrorLine {
    param([Parameter(ValueFromRemainingArguments = $true)][object[]]$Message)
    [Console]::Error.WriteLine(" {0}{1} {2}{3}" -f $errcolor, $errico, ($Message -join ' '), $NO_COLOR)
}

function Write-WarnLine {
    param([Parameter(ValueFromRemainingArguments = $true)][object[]]$Message)
    Write-Host (" {0}{1} {2}{3}" -f $warncolor, $warnico, ($Message -join ' '), $NO_COLOR)
}

function Write-InfoLine {
    param([Parameter(ValueFromRemainingArguments = $true)][object[]]$Message)
    Write-Host (" {0}{1}{2}" -f $GREY, ($Message -join ' '), $NO_COLOR)
}

function Write-DiscLine {
    param([Parameter(ValueFromRemainingArguments = $true)][object[]]$Message)
    Write-Host (" {0}{1}{2}" -f $GREEN, ($Message -join ' '), $NO_COLOR)
}

function Write-LogoLine {
    param([Parameter(ValueFromRemainingArguments = $true)][object[]]$Message)
    Write-Host ("{0}{1}{2}" -f $MAGENTA, ($Message -join "`n"), $NO_COLOR)
}

function Write-FlagLine {
    param(
        [string]$Name,
        [string]$Description
    )
    $left = "{0}{1}{2}" -f $BOLD, $CYAN, $Name
    $left += $NO_COLOR
    $right = " {0}{1}{2}" -f $GREEN, $Description, $NO_COLOR
    Write-Host ("  {0,-28} {1}" -f $left, $right)
}

function Format-HomePath {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    try {
        $homeResolved = [System.IO.Path]::GetFullPath($HOME)
        $fullResolved = [System.IO.Path]::GetFullPath($Path)
    }
    catch {
        return $Path
    }

    if ($fullResolved.StartsWith($homeResolved, [System.StringComparison]::OrdinalIgnoreCase)) {
        return "~" + $fullResolved.Substring($homeResolved.Length)
    }

    return $fullResolved
}

function Show-Usage {
    param(
        [switch]$ShowHeader
    )

    if ($ShowHeader) {
        $banner = @"
 █▀▀▀▄ ▄▀▀▀▄ █  ▄▀
 █▀▀▀▄ █▀▀▀█ █▀▀▄
 ▀▀▀▀  ▀   ▀ ▀   ▀
"@
        Write-LogoLine $banner
        Write-DiscLine "Utility for backing up your files"
        Write-InfoLine ("usage: {0}bak{1} {2}[options]{1} {3}<file|dir>{1} {3}{4}[more files/dirs...]{1}" -f ($MAGENTA + $BOLD), $NO_COLOR, $CYAN, $BLUE, $DIM)
        Write-Host ""
    }

    Write-InfoLine "Options:"
    Write-FlagLine "-h, --help"    "Displays help"
    Write-FlagLine "-s, --store"   "Place backups into ~/.bakstore"
    Write-FlagLine "-y, --yes"     "Auto yes to prompts"
    Write-FlagLine "-q, --quiet"   "Suppress output"
    Write-FlagLine "-v, --verbose" "All the output"
    Write-Host ""
}

function Confirm-Bak {
    param(
        [Parameter(Mandatory)]
        [string]$Prompt
    )

    if ($Yes) {
        return $true
    }

    try {
        $reply = Read-Host -Prompt $Prompt
    }
    catch {
        Write-ErrorLine "cannot prompt (no TTY). Use --yes to auto-create."
        return $false
    }

    if ($reply -match '^(?i:y|yes)$') {
        return $true
    }

    return $false
}

function Get-BackupTimestamp {
    Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
}

function Get-DisplayEntry {
    param(
        [Parameter(Mandatory)]
        [string]$LiteralPath
    )

    try {
        $item = Get-Item -LiteralPath $LiteralPath -Force -ErrorAction Stop
    }
    catch {
        return (Format-HomePath -Path $LiteralPath)
    }

    $full = Format-HomePath -Path $item.FullName

    if ($item.PSIsContainer) {
        return "{0}{1}{2}" -f $dircolor, $full, $NO_COLOR
    }

    return $full
}

function Invoke-Bak {
    if ($Help) {
        Show-Usage -ShowHeader
        return 0
    }

    if (-not $Paths -or $Paths.Count -eq 0) {
        Show-Usage -ShowHeader
        return 1
    }

    if (-not $Quiet) {
        Write-Host ""
    }

    $storeDir = $null
    if ($Store) {
        $storeDir = Join-Path $HOME ".bakstore"

        if (-not (Test-Path -LiteralPath $storeDir -PathType Container)) {
            if (Confirm-Bak -Prompt "~/.bakstore does not exist. Create it now? [y/N]") {
                try {
                    New-Item -ItemType Directory -Path $storeDir -Force -ErrorAction Stop | Out-Null
                }
                catch {
                    Write-ErrorLine "failed to create '$storeDir'"
                    return 1
                }
            }
            else {
                Write-ErrorLine "store directory not created; aborting."
                return 1
            }
        }
    }

    foreach ($src in $Paths) {
        if (-not (Test-Path -LiteralPath $src)) {
            if (-not $Quiet) {
                $rawPath = try {
                    [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $src))
                } catch {
                    $src
                }

                $srcDir = Split-Path -Parent $rawPath
                $srcName = Split-Path -Leaf $rawPath
                $srcDir = if ($srcDir) { Format-HomePath -Path $srcDir } else { "." }

                Write-ErrorLine ("'{0}{1}\{2}{3}{4}' does not exist" -f $MAGENTA, $srcDir, $BOLD, $srcName, $NO_COLOR + $RED)
            }
            continue
        }

        $resolved = Get-Item -LiteralPath $src -Force -ErrorAction Stop

        if ($resolved.Name -like "*.bak.*") {
            continue
        }

        $timestamp = Get-BackupTimestamp
        $bakName = "{0}.bak.{1}" -f $resolved.Name, $timestamp

        if ($Store) {
            $bakPath = Join-Path $storeDir $bakName
        }
        else {
            $parent = Split-Path -Parent $resolved.FullName
            $leaf   = Split-Path -Leaf $resolved.FullName
            $bakPath = Join-Path $parent ("{0}.bak.{1}" -f $leaf, $timestamp)
        }

        while (Test-Path -LiteralPath $bakPath) {
            Write-WarnLine "'$bakPath' already exists, retrying..."
            Start-Sleep -Seconds 1
            $timestamp = Get-BackupTimestamp
            $bakName = "{0}.bak.{1}" -f $resolved.Name, $timestamp

            if ($Store) {
                $bakPath = Join-Path $storeDir $bakName
            }
            else {
                $parent = Split-Path -Parent $resolved.FullName
                $leaf   = Split-Path -Leaf $resolved.FullName
                $bakPath = Join-Path $parent ("{0}.bak.{1}" -f $leaf, $timestamp)
            }
        }

        try {
            if ($resolved.PSIsContainer) {
                Copy-Item -LiteralPath $resolved.FullName -Destination $bakPath -Recurse -Force -ErrorAction Stop
            }
            else {
                Copy-Item -LiteralPath $resolved.FullName -Destination $bakPath -Force -ErrorAction Stop
            }

            if ($VerboseMode) {
                Write-InfoLine ("copied '{0}' -> '{1}'" -f (Format-HomePath -Path $resolved.FullName), (Format-HomePath -Path $bakPath))
            }
            elseif (-not $Quiet) {
                $srcOut = Get-DisplayEntry -LiteralPath $resolved.FullName
                $bakOut = Get-DisplayEntry -LiteralPath $bakPath
                Write-OutputLine "$srcOut $arrowcolor$arrowico_r$c_reset $bakOut"
            }
        }
        catch {
            Write-ErrorLine ("failed to back up '{0}': {1}" -f $resolved.FullName, $_.Exception.Message)
            continue
        }
    }

    if (-not $Quiet) {
        Write-Host ""
    }

    return 0
}

exit (Invoke-Bak)


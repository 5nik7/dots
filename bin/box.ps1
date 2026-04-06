#!/usr/bin/env pwsh
Set-StrictMode -Version Latest

$RST = "$([char]27)[0m"

function Repeat-Char {
    param(
        [Parameter(Mandatory)]
        [string]$Char,
        [Parameter(Mandatory)]
        [int]$Count
    )

    if ($Count -le 0) { return '' }
    return ($Char * $Count)
}

function Strip-Ansi {
    param([AllowNull()][string]$Text)
    if ($null -eq $Text) { return '' }
    return [regex]::Replace($Text, '\x1b\[[0-9;?]*[@-~]', '')
}

function Get-DisplayLength {
    param([AllowNull()][string]$Text)
    return (Strip-Ansi $Text).Length
}

function Show-Usage {
    $prog = if ($PSCommandPath) { Split-Path -Leaf $PSCommandPath } else { 'box.ps1' }
@"
Usage:
  $prog [-t <title>] [options] [text...]
  "hello world" | $prog
  Get-Content file.txt | $prog

Options:
  -h, -Help, --help  Print this message and exit
  -bc <color>        ANSI escape sequence for the box color
  -tc <color>        ANSI escape sequence for the title color
  -vp <padding>      Vertical padding inside the box (default: 0)
  -hp <padding>      Horizontal padding inside the box (default: 0)
  -s <sep>           Separator character/string for columns
  -t <title>         Title for the box
  -Theme <theme>     Theme: unicode, ascii, plain
  -th <theme>        Short alias for -Theme
  -T <theme>         Compatibility alias for theme
"@
}

function Fatal {
    param([Parameter(ValueFromRemainingArguments = $true)][object[]]$Message)
    [Console]::Error.WriteLine("[FATAL] " + ($Message -join ' '))
    exit 1
}

function Render-Box {
    param(
        [string[]]$InputLines,
        [string]$Color,
        [string]$TitleColor,
        [int]$VerticalPadding,
        [int]$HorizontalPadding,
        [string]$Separator,
        [string]$Title,
        [ValidateSet('unicode', 'ascii', 'plain')]
        [string]$ThemeName
    )

    $hpadding = Repeat-Char ' ' $HorizontalPadding

    switch ($ThemeName) {
        'unicode' {
            $WE  = '─'
            $NS  = '│'
            $SE  = '┌'
            $NE  = '└'
            $SW  = '┐'
            $NW  = '┘'
            $SWE = '┬'
            $NWE = '┴'
        }
        'ascii' {
            $WE  = '-'
            $NS  = '|'
            $SE  = '+'
            $NE  = '+'
            $SW  = '+'
            $NW  = '+'
            $SWE = '+'
            $NWE = '+'
        }
        'plain' {
            $WE  = ' '
            $NS  = ' '
            $SE  = ' '
            $NE  = ' '
            $SW  = ' '
            $NW  = ' '
            $SWE = ' '
            $NWE = ' '
        }
        default {
            Fatal "invalid theme name: $ThemeName"
        }
    }

    if (-not $InputLines -or $InputLines.Count -eq 0) {
        $InputLines = @('')
    }

    $maxCols = @()
    $numCols = 1

    foreach ($line in $InputLines) {
        $lineText = if ($null -eq $line) { '' } else { [string]$line }

        if ($Separator -ne '') {
            $cells = $lineText -split [regex]::Escape($Separator), -1
            $lineCols = $cells.Count
        } else {
            $cells = @($lineText)
            $lineCols = 1
        }

        if ($lineCols -gt $numCols) {
            $numCols = $lineCols
        }

        for ($i = 0; $i -lt $lineCols; $i++) {
            $cellValue = if ($i -lt $cells.Count) { $cells[$i] } else { '' }
            $cell = $hpadding + $cellValue + $hpadding
            $cellLen = Get-DisplayLength $cell

            if ($i -ge $maxCols.Count) {
                $maxCols += $cellLen
            } elseif ($cellLen -gt $maxCols[$i]) {
                $maxCols[$i] = $cellLen
            }
        }
    }

    for ($i = $maxCols.Count; $i -lt $numCols; $i++) {
        $maxCols += 0
    }

    $line = $Color + $SE + $WE + $RST
    $line += $TitleColor + $Title + $RST + $Color

    $offset = $Title.Length + 1
    for ($i = 0; $i -lt $numCols; $i++) {
        $maxLen = $maxCols[$i]
        $copy = $maxLen
        if ($i -lt ($numCols - 1)) { $copy++ }

        if ($offset -gt 0) { $maxLen -= $offset }

        if ($maxLen -lt 0) {
            $offset -= $copy
            continue
        }

        $offset = 0
        $line += Repeat-Char $WE $maxLen
        if ($i -lt ($numCols - 1)) { $line += $SWE }
    }

    $line += $SW + $RST
    Write-Output $line

    if ($VerticalPadding -gt 0) {
        $padLine = if ($Separator -ne '') {
            $parts = for ($i = 0; $i -lt $numCols; $i++) { '' }
            ($parts -join $Separator)
        } else {
            ''
        }

        $padded = @()
        for ($i = 0; $i -lt $VerticalPadding; $i++) { $padded += $padLine }
        $padded += $InputLines
        for ($i = 0; $i -lt $VerticalPadding; $i++) { $padded += $padLine }
        $InputLines = $padded
    }

    foreach ($row in $InputLines) {
        $rowText = if ($null -eq $row) { '' } else { [string]$row }

        if ($Separator -ne '') {
            $cells = $rowText -split [regex]::Escape($Separator), -1
        } else {
            $cells = @($rowText)
        }

        $outLine = $Color + $NS + $RST

        for ($i = 0; $i -lt $numCols; $i++) {
            $cellValue = if ($i -lt $cells.Count) { $cells[$i] } else { '' }
            $cell = $hpadding + $cellValue + $hpadding
            $len = Get-DisplayLength $cell
            $maxLen = $maxCols[$i]

            $outLine += $cell
            $outLine += Repeat-Char ' ' ($maxLen - $len)
            $outLine += $Color + $NS + $RST
        }

        Write-Output $outLine
    }

    $line = $Color + $NE
    for ($i = 0; $i -lt $numCols; $i++) {
        $maxLen = $maxCols[$i]
        $line += Repeat-Char $WE $maxLen
        if ($i -lt ($numCols - 1)) { $line += $NWE }
    }
    $line += $NW + $RST
    Write-Output $line
}

# Parse args manually
$Help = $false
$bc = ''
$tc = ''
$vp = 0
$hp = 0
$s = ''
$t = ''
$Theme = 'unicode'
$Text = [System.Collections.Generic.List[string]]::new()

$argv = @($args)
$i = 0
while ($i -lt $argv.Count) {
    $arg = [string]$argv[$i]

    switch -Regex ($arg) {
        '^(?:-h|-Help|--help)$' {
            $Help = $true
            $i++
            continue
        }
        '^-bc$' {
            if ($i + 1 -ge $argv.Count) { Fatal "missing value for -bc" }
            $bc = [string]$argv[$i + 1]
            $i += 2
            continue
        }
        '^-tc$' {
            if ($i + 1 -ge $argv.Count) { Fatal "missing value for -tc" }
            $tc = [string]$argv[$i + 1]
            $i += 2
            continue
        }
        '^-vp$' {
            if ($i + 1 -ge $argv.Count) { Fatal "missing value for -vp" }
            try { $vp = [int]$argv[$i + 1] } catch { Fatal "invalid integer for -vp: $($argv[$i + 1])" }
            $i += 2
            continue
        }
        '^-hp$' {
            if ($i + 1 -ge $argv.Count) { Fatal "missing value for -hp" }
            try { $hp = [int]$argv[$i + 1] } catch { Fatal "invalid integer for -hp: $($argv[$i + 1])" }
            $i += 2
            continue
        }
        '^-s$' {
            if ($i + 1 -ge $argv.Count) { Fatal "missing value for -s" }
            $s = [string]$argv[$i + 1]
            $i += 2
            continue
        }
        '^-t$' {
            if ($i + 1 -ge $argv.Count) { Fatal "missing value for -t" }
            $t = [string]$argv[$i + 1]
            $i += 2
            continue
        }
        '^(?:-Theme|-th|-T)$' {
            if ($i + 1 -ge $argv.Count) { Fatal "missing value for $arg" }
            $candidate = [string]$argv[$i + 1]
            if ($candidate -notin @('unicode', 'ascii', 'plain')) {
                Fatal "invalid theme name: $candidate"
            }
            $Theme = $candidate
            $i += 2
            continue
        }
        '^--$' {
            for ($j = $i + 1; $j -lt $argv.Count; $j++) {
                $Text.Add([string]$argv[$j])
            }
            break
        }
        '^-.*' {
            Fatal "invalid argument: $arg"
        }
        default {
            $Text.Add($arg)
            $i++
            continue
        }
    }

    break
}

if ($Help) {
    Show-Usage
    exit 0
}

if ($vp -lt 0) { Fatal "vertical padding must be >= 0" }
if ($hp -lt 0) { Fatal "horizontal padding must be >= 0" }

# Collect pipeline input at script scope
$PipelineLines = @($input | ForEach-Object {
    if ($null -eq $_) { '' } else { [string]$_ }
})

$InputLines =
    if ($PipelineLines.Count -gt 0) {
        $PipelineLines
    } elseif ($Text.Count -gt 0) {
        @($Text)
    } else {
        @('')
    }

Render-Box `
    -InputLines $InputLines `
    -Color $bc `
    -TitleColor $tc `
    -VerticalPadding $vp `
    -HorizontalPadding $hp `
    -Separator $s `
    -Title $t `
    -ThemeName $Theme
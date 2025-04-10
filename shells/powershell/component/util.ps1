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
      icon  = ' '
      color = 'cyan'
    }
    success = @{
      text  = 'Success'
      icon  = ' '
      color = 'green'
    }
    warn    = @{
      text  = 'Warning'
      icon  = ' '
      color = 'yellow'
    }
    err     = @{
      text  = 'Error'
      icon  = ' '
      color = 'red'
    }
  }
}
$spacer = ' '
$divider = ': '
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
    [int]$padout,
    [int]$padin = 1,
    [switch]$box,
    [string]$border = 'DarkGray',
    [string]$esc,
    [string]$escol = 'White'
  )
  if ($env:padding) {
    $padout = $env:padding
  }

  $boxSymbolTopLeft = '┌'
  $boxSymbolTopRight = '┐'
  $boxSymbolBottomLeft = '└'
  $boxSymbolBottomRight = '┘'
  $boxSymbolHorizontal = '─'
  $boxSymbolVertical = '│'

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

  $boxTop = (' ' * $padout) + $boxSymbolTopLeft + ($boxSymbolHorizontal * $totalLength) + $boxSymbolTopRight
  $boxBottom = (' ' * $padout) + $boxSymbolBottomLeft + ($boxSymbolHorizontal * $totalLength) + $boxSymbolBottomRight
  $boxLeft = (' ' * $padout) + $boxSymbolVertical + (' ' * $padin)
  $boxRight = (' ' * $padin) + $boxSymbolVertical

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
      $escOutput = (' ' * $padin) + $esc
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
    $padline = (' ' * $padout)
    # No box: just print each pair
    Write-Host -NoNewline $padline
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
    [int]$bb = 0,
    [int]$ba = 0,
    [int]$padout,
    [switch]$box,
    [string]$border = 'DarkGray'
  )
  $pairs = @($infoicon, $infocolor, $infotext, $infocolor) + $pairs
  wh -pairs $pairs -padout $env:padding -box:$box -border:$border
}

function Write-Success {
  param(
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$pairs,
    [int]$bb = 0,
    [int]$ba = 0,
    [int]$padout,
    [switch]$box,
    [string]$border = 'DarkGray'
  )
  $pairs = @($successicon, $successcolor, $successtext, $successcolor) + $pairs
  wh -pairs $pairs -padout $env:padding -box:$box -border:$border
}

function Write-Err {
  param(
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$pairs,
    [int]$bb = 0,
    [int]$ba = 0,
    [int]$padout,
    [switch]$box,
    [string]$border = 'DarkGray'
  )
  $pairs = @($erricon, $errcolor, $errtext, $errcolor) + $pairs
  wh -pairs $pairs -padout $env:padding -box:$box -border:$border
}

function Write-Warn {
  param(
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$pairs,
    [int]$bb = 0,
    [int]$ba = 0,
    [int]$padout,
    [switch]$box,
    [string]$border = 'DarkGray'
  )
  $pairs = @($warnicon, $warncolor, $warntext, $warncolor) + $pairs
  wh -pairs $pairs -padout $env:padding -box:$box -border:$border
}

function ask {
  param([string]$message = '')

  $message += ' ' + '[Y/n]'

  # $configData = (Get-Content -Path $terminalProfile | ConvertFrom-Json) | Where-Object { $_ -ne $null }
  try {
    $choice = Read-Host $message
    if ($choice -eq 'y' -or $choice -eq 'Y' -or $choice -eq 'yes' -or $choice -eq 'Yes' -or $choice -eq 'YES' -or $choice -eq '') {
      return $true
    }
    elseif ($choice -eq 'n' -or $choice -eq 'N' -or $choice -eq 'no' -or $choice -eq 'No' -or $choice -eq 'NO') {
      return $false
    }
    else {
      Write-Err "Invalid choice. Please enter 'y' or 'n'." -box
      return $null
    }
  }
  catch {
    Write-Error "Error in line $($_.InvocationInfo.ScriptLineNumber): $($Error[0])"
    return $null
  }
}

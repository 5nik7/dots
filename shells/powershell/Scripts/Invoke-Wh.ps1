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
[CmdletBinding()]
param(
  [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
  [string[]]$pairs,
  [int]$bb = 0,
  [int]$ba = 0,
  [switch]$box,
  [int]$pad = 1,
  [int]$padin = 1,
  [string]$border = 'Black',
  [switch]$nl
)

if ($pairs.Count -eq 0) {
  Write-Host 'No text provided.'
  return
}

$boxSymbolTopLeft = '┌'
$boxSymbolTopRight = '┐'
$boxSymbolBottomLeft = '└'
$boxSymbolBottomRight = '┘'
$boxSymbolHorizontal = '─'
$boxSymbolVertical = '│'

function linebreak {
  param (
    [int]$count = 1
  )
  for ($i = 0; $i -lt $count; $i++) {
    Write-Host ''
  }
}

linebreak $bb

$pairsList = @()  # will hold objects like @{ text="Hello"; color="White"; length=... }
$totalLength = 0
# Collect pairs without printing right away
for ($i = 0; $i -lt $pairs.Count; $i += 2) {
  $txt = $pairs[$i]
  $clr = if ($i + 1 -lt $pairs.Count) { $pairs[$i + 1] } else { 'White' }

  # Validate $clr directly against [System.ConsoleColor]
  $colorEnum = [System.ConsoleColor]::GetValues([System.ConsoleColor]) | Where-Object { $_.ToString() -eq $clr }

  $pairsList += [pscustomobject]@{ text = $txt; color = $colorEnum }
  $totalLength += $txt.Length
}
$totalLength += ($padin * 2)

$boxTop = (' ' * $pad) + $boxSymbolTopLeft + ($boxSymbolHorizontal * $totalLength) + $boxSymbolTopRight
$boxBottom = (' ' * $pad) + $boxSymbolBottomLeft + ($boxSymbolHorizontal * $totalLength) + $boxSymbolBottomRight
$boxLeft = (' ' * $pad) + $boxSymbolVertical + (' ' * $padin)
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
  Write-Host $boxRight -ForegroundColor $border
  Write-Host -NoNewline $boxBottom -ForegroundColor $border
}
else {
  $padline = (' ' * $pad)
  # No box: just print each pair
  Write-Host -NoNewline $padline
  foreach ($pair in $pairsList) {
    Write-Host -NoNewline $pair.text -ForegroundColor $pair.color
  }
}

if ($nl) { linebreak }
linebreak $ba


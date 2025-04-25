<#
.SYNOPSIS
    Print text in white.
.DESCRIPTION
    The color of the text is white.
.PARAMETER text
    The text to print.
.PARAMETER inline
    Print the text inline.
.EXAMPLE
    PS> Write-White "This is white text."
.NOTES
    Author: njen
#>
[CmdletBinding()]
param (
  [string]$text = '',
  [switch]$inline
)
if ($text -eq '' ) { $text = Read-Host 'text?' }
$color = 'White'
if ($inline) {
  Write-Host -foregroundColor $color "$text" -NoNewline
  return
}
Write-Host -foregroundColor $color "$text"

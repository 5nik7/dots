<#
.SYNOPSIS
    Print text in yellow.
.DESCRIPTION
    The color of the text is yellow.
.PARAMETER text
    The text to print.
.PARAMETER inline
    Print the text inline.
.EXAMPLE
    PS> Write-Yellow "This is yellow text."
.NOTES
    Author: njen
#>
[CmdletBinding()]
param (
  [string]$text = '',
  [switch]$inline
)
if ($text -eq '' ) { $text = Read-Host 'text?' }
$color = 'Yellow'
if ($inline) {
  Write-Host -foregroundColor $color "$text" -NoNewline
  return
}
Write-Host -foregroundColor $color "$text"

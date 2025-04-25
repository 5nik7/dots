<#
.SYNOPSIS
    Print text in black.
.DESCRIPTION
    The color of the text is black.
.PARAMETER text
    The text to print.
.PARAMETER inline
    Print the text inline.
.EXAMPLE
    PS> Write-Black "This is dark gray text."
.NOTES
    Author: njen
#>
[CmdletBinding()]
param (
  [string]$text = '',
  [switch]$inline
)
if ($text -eq '' ) { $text = Read-Host 'text?' }
$color = 'Black'
if ($inline) {
  Write-Host -foregroundColor $color "$text" -NoNewline
  return
}
Write-Host -foregroundColor $color "$text"
